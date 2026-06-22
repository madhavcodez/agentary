"""Generate insights from accumulated observations using Gemini."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from ...models.evidence import Evidence, EvidenceType
from ...models.insight import Insight, InsightType
from ...models.observation import Observation

logger = logging.getLogger(__name__)

_INSIGHT_SCHEMA_HINT = """{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "insight_type": {"type": "string", "enum": ["trend","risk","opportunity","anomaly","summary","comparison"]},
      "title": {"type": "string"},
      "content": {"type": "string"},
      "confidence": {"type": "number"},
      "supporting_observation_indices": {"type": "array", "items": {"type": "integer"}}
    }
  }
}"""


def _type_label(obs_type: object) -> str:
    return obs_type.value if hasattr(obs_type, "value") else str(obs_type)


class InsightGenerator:
    """Synthesizes observations into insights via Gemini."""

    def __init__(self, db: Session) -> None:
        self.db = db

    async def generate_for_entity(
        self, entity_id: UUID, project_id: UUID
    ) -> list[Insight]:
        """Generate insights from an entity's observations."""
        observations = (
            self.db.query(Observation)
            .filter(
                Observation.entity_id == entity_id,
                Observation.is_stale.is_(False),
            )
            .order_by(Observation.created_at.desc())
            .limit(50)
            .all()
        )

        if len(observations) < 3:
            return []  # Need minimum observations to synthesize

        return await self._generate(observations, project_id, entity_id)

    async def generate_for_project(
        self, project_id: UUID
    ) -> list[Insight]:
        """Generate project-level insights from all observations."""
        observations = (
            self.db.query(Observation)
            .filter(
                Observation.project_id == project_id,
                Observation.is_stale.is_(False),
            )
            .order_by(Observation.created_at.desc())
            .limit(100)
            .all()
        )

        if len(observations) < 5:
            return []

        # Cap for prompt size
        return await self._generate(observations[:50], project_id, entity_id=None)

    async def _generate(
        self,
        observations: list[Observation],
        project_id: UUID,
        entity_id: UUID | None,
    ) -> list[Insight]:
        """Core generation logic shared by entity and project flows."""
        from ..gemini import generate_structured

        obs_text = "\n".join(
            [
                f"- [{_type_label(o.observation_type)}] {o.subject}: "
                f"{o.content} (confidence: {o.confidence or 'N/A'}, "
                f"source: {o.source_name or 'unknown'})"
                for o in observations
            ]
        )

        scope = "entity" if entity_id else "project"
        min_insights = 2 if entity_id is None else 1
        max_insights = 5

        prompt = (
            f"Analyze these observations and generate insights. "
            f"Return a JSON array of insights.\n\n"
            f"Each insight should have:\n"
            f"- insight_type: one of trend, risk, opportunity, anomaly, summary, comparison\n"
            f"- title: concise title (under 100 chars)\n"
            f"- content: 2-3 sentence explanation\n"
            f"- confidence: 0.0-1.0 (based on evidence strength)\n"
            f"- supporting_observation_indices: array of 0-based indices of observations\n\n"
            f"Observations ({scope} scope):\n{obs_text}\n\n"
            f"Generate {min_insights}-{max_insights} insights. "
            f"Focus on the most significant patterns."
        )

        try:
            result = await generate_structured(
                prompt=prompt, schema_hint=_INSIGHT_SCHEMA_HINT
            )
        except Exception:
            logger.exception(
                "Insight generation failed for %s %s",
                scope,
                entity_id or project_id,
            )
            return []

        if not isinstance(result, list):
            # The model returned a single object; wrap it
            result = [result] if isinstance(result, dict) else []

        insights: list[Insight] = []
        for item in result[:max_insights]:
            raw_type = item.get("insight_type", "summary")
            try:
                insight_type = InsightType(raw_type)
            except ValueError:
                insight_type = InsightType.summary

            insight = Insight(
                project_id=project_id,
                entity_id=entity_id,
                insight_type=insight_type,
                title=item.get("title", "Untitled insight")[:500],
                content=item.get("content", ""),
                confidence=min(max(float(item.get("confidence", 0.5)), 0.0), 1.0),
                freshness_at=datetime.now(UTC),
            )
            self.db.add(insight)
            self.db.flush()

            # Link supporting observations as evidence
            indices = item.get("supporting_observation_indices", [])
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(observations):
                    evidence = Evidence(
                        observation_id=observations[idx].id,
                        insight_id=insight.id,
                        evidence_type=EvidenceType.supporting,
                        weight=1.0,
                    )
                    self.db.add(evidence)

            insights.append(insight)

        self.db.flush()
        return insights
