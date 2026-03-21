from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy.orm import Session

from ...models.opportunity import Opportunity
from .. import gemini, qdrant_store
from .base import RawOpportunity
from .greenhouse import GreenhouseConnector
from .lever import LeverConnector
from .yc_hn import YCHNConnector

logger = logging.getLogger(__name__)


async def run_all_connectors(db: Session, *, user_id: UUID) -> int:
    connectors = [
        GreenhouseConnector(),
        LeverConnector(),
        YCHNConnector(),
    ]

    all_raw: list[RawOpportunity] = []
    results = await asyncio.gather(
        *[c.fetch() for c in connectors],
        return_exceptions=True,
    )

    for result in results:
        if isinstance(result, list):
            all_raw.extend(result)
        else:
            logger.error("Connector error: %s", result)

    # Dedupe by (source, source_id) globally — matches the DB unique constraint
    existing_ids = {
        (r.source, r.source_id)
        for r in db.query(Opportunity.source, Opportunity.source_id).all()
    }

    new_opps: list[RawOpportunity] = []
    for raw in all_raw:
        if (raw.source, raw.source_id) not in existing_ids:
            new_opps.append(raw)

    # Store and embed
    count = 0
    for raw in new_opps:
        opp = Opportunity(
            user_id=user_id,
            source=raw.source,
            source_id=raw.source_id,
            company=raw.company,
            title=raw.title,
            location=raw.location,
            description=raw.description,
            url=raw.url,
            raw_json=raw.raw_json,
        )
        db.add(opp)
        try:
            db.flush()
        except Exception as e:
            # Handle race condition with unique constraint
            db.rollback()
            logger.warning("Skipping duplicate opportunity %s/%s: %s", raw.source, raw.source_id, e)
            continue

        # Embed description for vector search
        try:
            embed_text = f"{raw.title} at {raw.company}. {raw.description or ''}"[:2000]
            embedding = await gemini.embed_text(embed_text)
            point_id = str(opp.id)
            qdrant_store.upsert_embedding(
                "secretairy_opportunities", point_id, embedding,
                payload={"company": raw.company, "title": raw.title, "source": raw.source},
            )
            opp.embedding_id = point_id
        except Exception as e:
            logger.warning("Embedding failed for %s: %s", raw.source_id, e)

        count += 1

    db.commit()
    logger.info(
        "Ingested %d new opportunities for user %s (total raw: %d)",
        count, user_id, len(all_raw),
    )
    return count
