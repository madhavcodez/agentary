"""Pipeline engine — advances matches through CRM stages.

Only moves forward unless the trigger is ``"manual"``, which
allows arbitrary stage changes (including backward and to
terminal states like paused / closed_lost).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.match import Match
from ..models.pipeline import PipelineStage, PipelineTransition, STAGE_ORDER


def advance_stage(
    db: Session,
    match_id: UUID,
    new_stage: PipelineStage,
    trigger: str,
) -> bool:
    """Advance a match to *new_stage*.

    Returns ``True`` when the transition is recorded, ``False``
    if the match was not found or the transition is not permitted.
    """
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        return False

    current_order = STAGE_ORDER.get(
        PipelineStage(match.pipeline_stage), 0,
    )
    new_order = STAGE_ORDER.get(new_stage, 0)

    # Only advance forward unless the trigger is manual
    if trigger != "manual" and new_order <= current_order:
        return False

    old_stage = match.pipeline_stage
    match.pipeline_stage = new_stage.value
    match.stage_changed_at = datetime.utcnow()

    transition = PipelineTransition(
        match_id=match_id,
        from_stage=old_stage,
        to_stage=new_stage.value,
        trigger=trigger,
    )
    db.add(transition)
    db.commit()
    return True
