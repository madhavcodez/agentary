from __future__ import annotations

from sqlalchemy.orm import Session

from ..models.profile import Experience, Preference, Profile, Skill
from . import gemini, qdrant_store

PROFILE_SCHEMA = """{
  "name": "string",
  "email": "string or null",
  "phone": "string or null",
  "location": "string or null",
  "summary": "string (2-3 sentence professional summary)",
  "skills": [{"name": "string", "category": "string (languages|frameworks|tools|concepts)", "years_experience": "string or null", "proficiency": "string (expert|advanced|intermediate|beginner)"}],
  "experiences": [{"company": "string", "title": "string", "start_date": "string or null", "end_date": "string or null", "description": "string", "evidence": "string (key achievements/metrics)"}],
  "preferences": [{"key": "string (location_pref|role_type|company_size|industry)", "value": "string"}]
}"""


async def build_profile(db: Session, resume_text: str) -> Profile:
    existing = db.query(Profile).first()
    if existing:
        db.query(Skill).filter(Skill.profile_id == existing.id).delete()
        db.query(Experience).filter(Experience.profile_id == existing.id).delete()
        db.query(Preference).filter(Preference.profile_id == existing.id).delete()
        db.delete(existing)
        db.flush()

    prompt = f"Extract structured profile data from this resume:\n\n{resume_text}"
    data = await gemini.generate_structured(prompt, schema_hint=PROFILE_SCHEMA)

    profile = Profile(
        name=data.get("name", "Unknown"),
        email=data.get("email"),
        phone=data.get("phone"),
        location=data.get("location"),
        summary=data.get("summary"),
        resume_text=resume_text,
    )
    db.add(profile)
    db.flush()

    for s in data.get("skills", []):
        db.add(Skill(
            profile_id=profile.id,
            name=s["name"],
            category=s.get("category"),
            years_experience=s.get("years_experience"),
            proficiency=s.get("proficiency"),
        ))

    for e in data.get("experiences", []):
        db.add(Experience(
            profile_id=profile.id,
            company=e["company"],
            title=e["title"],
            start_date=e.get("start_date"),
            end_date=e.get("end_date"),
            description=e.get("description"),
            evidence=e.get("evidence"),
        ))

    for p in data.get("preferences", []):
        db.add(Preference(
            profile_id=profile.id,
            key=p["key"],
            value=p["value"],
        ))

    db.commit()
    db.refresh(profile)

    # Embed profile for vector search
    embedding = await gemini.embed_text(resume_text, task_type="RETRIEVAL_DOCUMENT")
    point_id = str(profile.id)
    qdrant_store.upsert_embedding(
        "secretairy_profiles", point_id, embedding,
        payload={"name": profile.name, "summary": profile.summary},
    )
    profile.embedding_id = point_id
    db.commit()

    return profile
