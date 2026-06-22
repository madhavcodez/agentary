"""Generate recommendations from insights using Gemini."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from ...models.evidence import Evidence, EvidenceType
from ...models.insight import Insight
from ...models.recommendation import (
    Recommendation,
    RecommendationPriority,
    RecommendationType,
)

logger = logging.getLogger(__name__)

_RECOMMENDATION_SCHEMA_HINT = """{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "recommendation_type": {"type": "string", "enum": ["investigate","monitor","contact","update","review","escalate"]},
      "title": {"type": "string"},
      "rationale": {"type": "string"},
      "priority": {"type": "string", "enum": ["critical","high","medium","low"]},
      "confidence": {"type": "number"},
      "supporting_insight_indices": {"type": "array", "items": {"type": "integer"}}
    }
  }
}"""


class RecommendationGenerator:
    """Synthesizes insights into actionable recommendations via Gemini."""

    def __init__(self, db: Session) -> None:
        self.db = db

    async def generate_from_insights(
        self, project_id: UUID, entity_id: UUID | None = None
    ) -> list[Recommendation]:
        """Generate recommendations from active, non-stale insights."""
        q = self.db.query(Insight).filter(
            Insight.project_id == project_id,
            Insight.is_active.is_(True),
            Insight.is_stale.is_(False),
        )
        if entity_id:
            q = q.filter(Insight.entity_id == entity_id)

        insights = q.order_by(Insight.confidence.desc()).limit(20).all()
        if not insights:
            return []

        return await self._generate(insights, project_id, entity_id)

    async def _generate(
        self,
        insights: list[Insight],
        project_id: UUID,
        entity_id: UUID | None,
    ) -> list[Recommendation]:
        """Core generation logic."""
        from ..gemini import generate_structured

        def _type_label(t: object) -> str:
            return t.value if hasattr(t, "value") else str(t)

        insight_text = "\n".join(
            [
                f"- [{_type_label(i.insight_type)}] {i.title}: "
                f"{i.content} (confidence: {i.confidence})"
                for i in insights
            ]
        )

        prompt = (
            "Based on these insights, generate actionable recommendations. "
            "Return a JSON array.\n\n"
            "Each recommendation:\n"
            "- recommendation_type: one of investigate, monitor, contact, update, review, escalate\n"
            "- title: concise action title\n"
            "- rationale: why this is recommended (2-3 sentences)\n"
            "- priority: one of critical, high, medium, low\n"
            "- confidence: 0.0-1.0\n"
            "- supporting_insight_indices: array of insight indices supporting this\n\n"
            f"Insights:\n{insight_text}\n\n"
            "Generate 1-5 recommendations. Be specific and actionable."
        )

        try:
            result = await generate_structured(
                prompt=prompt, schema_hint=_RECOMMENDATION_SCHEMA_HINT
            )
        except Exception:
            logger.exception("Recommendation generation failed for project %s", project_id)
            return []

        if not isinstance(result, list):
            result = [result] if isinstance(result, dict) else []

        recs: list[Recommendation] = []
        for item in result[:5]:
            raw_type = item.get("recommendation_type", "review")
            try:
                rec_type = RecommendationType(raw_type)
            except ValueError:
                rec_type = RecommendationType.review

            raw_priority = item.get("priority", "medium")
            try:
                priority = RecommendationPriority(raw_priority)
            except ValueError:
                priority = RecommendationPriority.medium

            rec = Recommendation(
                project_id=project_id,
                entity_id=entity_id,
                insight_id=insights[0].id if insights else None,
                recommendation_type=rec_type,
                title=item.get("title", "Untitled")[:500],
                rationale=item.get("rationale", ""),
                confidence=min(max(float(item.get("confidence", 0.5)), 0.0), 1.0),
                priority=priority,
            )
            self.db.add(rec)
            self.db.flush()

            # Link evidence from supporting insights' observations
            indices = item.get("supporting_insight_indices", [])
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(insights):
                    insight_evidence = (
                        self.db.query(Evidence)
                        .filter(Evidence.insight_id == insights[idx].id)
                        .all()
                    )
                    for ev in insight_evidence:
                        rec_evidence = Evidence(
                            observation_id=ev.observation_id,
                            recommendation_id=rec.id,
                            evidence_type=EvidenceType.supporting,
                            weight=ev.weight,
                        )
                        self.db.add(rec_evidence)

            recs.append(rec)

        self.db.flush()
        return recs
