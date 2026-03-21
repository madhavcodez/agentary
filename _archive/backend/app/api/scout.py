from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["scout"])


def _get_db() -> Session:
    """Create a fresh session for the WebSocket handler (not an HTTP dependency)."""
    return SessionLocal()


@router.websocket("/scout/run")
async def scout_run(ws: WebSocket) -> None:
    await ws.accept()

    db = _get_db()
    try:
        # Read config from client (first message must contain token + config)
        raw = await ws.receive_text()
        config = json.loads(raw)
        token = config.get("token")
        mode = config.get("mode", "rank_all")
        skills_filter: list[str] = config.get("skills_filter", [])

        # Verify token manually (WebSocket does not use HTTP auth headers)
        from ..auth import verify_token
        from ..models.user import User

        try:
            user_id: UUID = verify_token(token)
        except Exception:
            await ws.send_json({"type": "error", "message": "Unauthorized"})
            await ws.close()
            return

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await ws.send_json({"type": "error", "message": "Unauthorized"})
            await ws.close()
            return

        # ── Pause / cancel machinery ─────────────────────────────────
        cancelled = asyncio.Event()
        paused = asyncio.Event()
        paused.set()  # not paused initially

        async def send_event(event: dict) -> None:
            await paused.wait()
            if cancelled.is_set():
                raise asyncio.CancelledError()
            await ws.send_json(event)

        async def listen_commands() -> None:
            try:
                while True:
                    msg = json.loads(await ws.receive_text())
                    action = msg.get("action")
                    if action == "pause":
                        paused.clear()
                        await ws.send_json({"type": "control", "status": "paused"})
                    elif action == "resume":
                        paused.set()
                        await ws.send_json({"type": "control", "status": "resumed"})
                    elif action == "cancel":
                        cancelled.set()
                        paused.set()  # unpause so main loop can exit
                        await ws.send_json({"type": "control", "status": "cancelled"})
                        break
            except WebSocketDisconnect:
                cancelled.set()
                paused.set()

        cmd_task = asyncio.create_task(listen_commands())

        try:
            # ═══════════════════════════════════════════════════════════
            # PHASE 1 — INGEST
            # ═══════════════════════════════════════════════════════════
            await send_event({"type": "phase", "phase": "ingest", "status": "started"})

            from ..models.opportunity import Opportunity
            from ..services.ingest.greenhouse import GreenhouseConnector
            from ..services.ingest.lever import LeverConnector
            from ..services.ingest.yc_hn import YCHNConnector

            connectors = [
                ("Greenhouse", GreenhouseConnector()),
                ("Lever", LeverConnector()),
                ("HN Who's Hiring", YCHNConnector()),
            ]

            all_raw = []
            for source_name, connector in connectors:
                await send_event({"type": "source", "source": source_name, "status": "fetching"})
                try:
                    results = await connector.fetch()
                    all_raw.extend(results)
                    await send_event({
                        "type": "source",
                        "source": source_name,
                        "status": "done",
                        "jobs_found": len(results),
                    })
                except Exception as exc:
                    logger.error("Connector %s failed: %s", source_name, exc)
                    await send_event({
                        "type": "source",
                        "source": source_name,
                        "status": "error",
                        "error": str(exc),
                    })

            await send_event({
                "type": "phase",
                "phase": "ingest",
                "status": "done",
                "total_raw": len(all_raw),
            })

            # Dedupe against existing rows
            existing_ids = {
                (r.source, r.source_id)
                for r in db.query(Opportunity.source, Opportunity.source_id).all()
            }
            new_raw = [r for r in all_raw if (r.source, r.source_id) not in existing_ids]

            # ── Store new opportunities ───────────────────────────────
            await send_event({
                "type": "phase",
                "phase": "storing",
                "status": "started",
                "new_jobs": len(new_raw),
            })

            stored = 0
            for raw in new_raw:
                try:
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
                    db.flush()
                    stored += 1
                    if stored % 10 == 0:
                        await send_event({
                            "type": "progress",
                            "phase": "storing",
                            "current": stored,
                            "total": len(new_raw),
                        })
                except Exception:
                    db.rollback()
                    continue
            db.commit()

            await send_event({
                "type": "phase",
                "phase": "storing",
                "status": "done",
                "stored": stored,
            })

            # ═══════════════════════════════════════════════════════════
            # PHASE 2 — FILTERING
            # ═══════════════════════════════════════════════════════════
            await send_event({
                "type": "phase",
                "phase": "filtering",
                "status": "started",
                "mode": mode,
            })

            all_opps = (
                db.query(Opportunity).filter(Opportunity.user_id == user_id).all()
            )

            if mode == "strict_filter" and skills_filter:
                filtered = []
                for opp in all_opps:
                    text = f"{opp.title} {opp.description or ''}".lower()
                    matched_skill = next(
                        (s for s in skills_filter if s.lower() in text), None
                    )
                    if matched_skill:
                        filtered.append(opp)
                        await send_event({
                            "type": "filter_match",
                            "title": opp.title,
                            "company": opp.company,
                            "skill_matched": matched_skill,
                        })
                to_score = filtered
            else:
                to_score = all_opps
                for skill in skills_filter:
                    count = sum(
                        1
                        for o in all_opps
                        if skill.lower() in f"{o.title} {o.description or ''}".lower()
                    )
                    await send_event({
                        "type": "filter",
                        "skill": skill,
                        "matches": count,
                    })

            await send_event({
                "type": "phase",
                "phase": "filtering",
                "status": "done",
                "to_score": len(to_score),
            })

            # ═══════════════════════════════════════════════════════════
            # PHASE 3 — SCORING
            # ═══════════════════════════════════════════════════════════
            from ..models.match import Match
            from ..models.profile import Profile
            from ..services import gemini

            profile = db.query(Profile).filter(Profile.user_id == user_id).first()
            if not profile:
                await send_event({
                    "type": "error",
                    "message": "No profile found. Upload your resume first.",
                })
                return

            await send_event({
                "type": "phase",
                "phase": "scoring",
                "status": "started",
                "total": len(to_score),
            })

            existing_match_opp_ids = {
                m.opportunity_id
                for m in db.query(Match.opportunity_id)
                .filter(Match.user_id == user_id)
                .all()
            }

            unscored = [o for o in to_score if o.id not in existing_match_opp_ids]
            already_scored = len(to_score) - len(unscored)

            if already_scored > 0:
                await send_event({
                    "type": "info",
                    "message": f"{already_scored} already scored, scoring {len(unscored)} new",
                })

            scored_count = 0
            for opp in unscored:
                try:
                    skills_text = (
                        ", ".join(skills_filter)
                        if skills_filter
                        else "general software engineering"
                    )
                    prompt = (
                        f"Score this job match (0-100) for a candidate with these skills: {skills_text}\n\n"
                        f"Candidate profile: {profile.summary or profile.name}\n"
                        f"Job: {opp.title} at {opp.company}\n"
                        f"Description: {(opp.description or '')[:1500]}\n\n"
                        'Return JSON: {"score": <0-100>, "rationale": "<1-2 sentences>"}'
                    )

                    result = await gemini.generate_structured(
                        prompt, schema_hint='{"score": 0, "rationale": ""}'
                    )

                    score = result.get("score", 50) if isinstance(result, dict) else 50
                    rationale = (
                        result.get("rationale", "")
                        if isinstance(result, dict)
                        else str(result)
                    )

                    match = Match(
                        user_id=user_id,
                        opportunity_id=opp.id,
                        profile_id=profile.id,
                        llm_score=score / 100.0,
                        composite_score=float(score),
                        rationale=rationale,
                        status="new",
                        pipeline_stage="lead",
                    )
                    db.add(match)
                    db.flush()

                    scored_count += 1
                    await send_event({
                        "type": "scored",
                        "progress": f"{scored_count}/{len(unscored)}",
                        "job": {
                            "id": str(opp.id),
                            "match_id": str(match.id),
                            "title": opp.title,
                            "company": opp.company,
                            "location": opp.location or "",
                            "score": score,
                            "rationale": rationale,
                        },
                    })

                    if scored_count % 5 == 0:
                        db.commit()

                except asyncio.CancelledError:
                    db.commit()
                    raise
                except Exception as exc:
                    logger.error("Scoring failed for %s: %s", opp.title, exc)
                    await send_event({
                        "type": "score_error",
                        "title": opp.title,
                        "error": str(exc),
                    })
                    continue

            db.commit()
            await send_event({
                "type": "phase",
                "phase": "scoring",
                "status": "done",
                "scored": scored_count,
            })
            await send_event({
                "type": "complete",
                "total_scored": scored_count + already_scored,
                "new_scored": scored_count,
            })

        except asyncio.CancelledError:
            try:
                await ws.send_json({"type": "complete", "status": "cancelled"})
            except Exception:
                pass
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.exception("Scout run error")
            try:
                await ws.send_json({"type": "error", "message": str(exc)})
            except Exception:
                pass
        finally:
            cmd_task.cancel()
    finally:
        db.close()
