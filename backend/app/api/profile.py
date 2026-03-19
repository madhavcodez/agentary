from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models.profile import Experience, Preference, Profile, Skill
from ..schemas.profile import ProfileResponse, ProfileUpdate, ResumeUpload

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse | None)
def get_profile(db: Session = Depends(get_db)):
    profile = db.query(Profile).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found. Upload a resume first.")
    return profile


@router.post("/resume", response_model=ProfileResponse)
async def upload_resume(body: ResumeUpload, db: Session = Depends(get_db)):
    from ..services.profile_builder import build_profile
    profile = await build_profile(db, body.resume_text)
    return profile


@router.put("", response_model=ProfileResponse)
def update_profile(body: ProfileUpdate, db: Session = Depends(get_db)):
    profile = db.query(Profile).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found.")

    if body.name is not None:
        profile.name = body.name
    if body.email is not None:
        profile.email = body.email
    if body.phone is not None:
        profile.phone = body.phone
    if body.location is not None:
        profile.location = body.location
    if body.summary is not None:
        profile.summary = body.summary

    if body.skills is not None:
        db.query(Skill).filter(Skill.profile_id == profile.id).delete()
        for s in body.skills:
            db.add(Skill(profile_id=profile.id, name=s.name, category=s.category,
                         years_experience=s.years_experience, proficiency=s.proficiency))

    if body.experiences is not None:
        db.query(Experience).filter(Experience.profile_id == profile.id).delete()
        for e in body.experiences:
            db.add(Experience(profile_id=profile.id, company=e.company, title=e.title,
                              start_date=e.start_date, end_date=e.end_date,
                              description=e.description, evidence=e.evidence))

    if body.preferences is not None:
        db.query(Preference).filter(Preference.profile_id == profile.id).delete()
        for p in body.preferences:
            db.add(Preference(profile_id=profile.id, key=p.key, value=p.value))

    db.commit()
    db.refresh(profile)
    return profile
