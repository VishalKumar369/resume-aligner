"""Account settings endpoints, all scoped to the signed-in user (`/me`).

Design: reads are aggregated into one `GET /me` so the settings page loads in a
single round-trip; writes are split per concern so each section sends only its
own fields. Every route resolves the caller from the JWT and never accepts a
user id in the path, so one account can never read or mutate another's data.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core import security
from app.db.session import get_db
from app.models.alignment import AlignmentScore
from app.models.jd import JobDescription
from app.models.resume import Resume
from app.models.settings import NotificationSettings
from app.models.user import User
from app.repositories.alignment_repo import AlignmentRepository
from app.repositories.jd_repo import JDRepository
from app.repositories.resume_repo import ResumeRepository
from app.repositories.settings_repo import NotificationSettingsRepository
from app.repositories.user_repo import UserRepository
from app.schemas.settings import (
    MeOut,
    NotificationOut,
    NotificationUpdate,
    ProfileOut,
    ProfileUpdate,
    DeleteAccountIn,
)

router = APIRouter()


@router.get("", response_model=MeOut)
async def read_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Profile, notification preferences, and account metadata in one payload."""
    settings_repo = NotificationSettingsRepository(NotificationSettings, db)
    notifications = await settings_repo.get_or_create(current_user.id)
    return MeOut(
        profile=ProfileOut.model_validate(current_user),
        notifications=NotificationOut.model_validate(notifications),
        account=current_user,
    )


@router.patch("/profile", response_model=ProfileOut)
async def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update editable profile fields. Only provided fields are changed."""
    changes = payload.model_dump(exclude_unset=True)
    if changes:
        repo = UserRepository(User, db)
        await repo.update(db_obj=current_user, obj_in=changes)
    return ProfileOut.model_validate(current_user)


@router.patch("/notifications", response_model=NotificationOut)
async def update_notifications(
    payload: NotificationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle notification preferences. Only provided toggles are changed."""
    repo = NotificationSettingsRepository(NotificationSettings, db)
    settings_row = await repo.get_or_create(current_user.id)
    changes = payload.model_dump(exclude_unset=True)
    if changes:
        await repo.update(db_obj=settings_row, obj_in=changes)
    return NotificationOut.model_validate(settings_row)


@router.get("/export")
async def export_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download every record this account owns as a single JSON file.

    Owner-scoped by construction — each query filters on `current_user.id`, so
    the export can only ever contain the caller's own data.
    """
    resumes = await ResumeRepository(Resume, db).get_by_owner(current_user.id, limit=1000)
    jds = await JDRepository(JobDescription, db).get_by_owner(current_user.id, limit=1000)
    alignments = await AlignmentRepository(AlignmentScore, db).list_alignments(
        owner_id=current_user.id, limit=1000
    )
    settings_row = await NotificationSettingsRepository(
        NotificationSettings, db
    ).get_or_create(current_user.id)

    payload = {
        "profile": {
            "id": str(current_user.id),
            "full_name": current_user.full_name,
            "email": current_user.email,
            "target_role": current_user.target_role,
            "created_at": current_user.created_at.isoformat()
            if current_user.created_at
            else None,
        },
        "notifications": {
            "email_alerts_on_new_matches": settings_row.email_alerts_on_new_matches,
            "weekly_career_readiness_report": settings_row.weekly_career_readiness_report,
        },
        "resumes": [
            {
                "id": str(r.id),
                "filename": r.filename,
                "label": r.label,
                "structured_data": r.structured_data,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in resumes
        ],
        "job_descriptions": [
            {
                "id": str(j.id),
                "title": j.title,
                "company_name": j.company_name,
                "url": j.url,
                "structured_data": j.structured_data,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jds
        ],
        "alignments": [
            {
                "id": str(a.id),
                "resume_id": str(a.resume_id),
                "jd_id": str(a.jd_id),
                "total_alignment_score": a.total_alignment_score,
                "ats_score": a.ats_score,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alignments
        ],
    }
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": 'attachment; filename="resume-jd-aligner-export.json"'
        },
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    payload: DeleteAccountIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete the account after re-confirming the current password.

    Destructive and irreversible from the user's side, so we re-verify the
    password even though the request is already authenticated — a stolen token
    alone must not be enough to delete the account.
    """
    if not security.verify_password(payload.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect password"
        )
    current_user.is_active = False
    current_user.is_deleted = True
    db.add(current_user)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
