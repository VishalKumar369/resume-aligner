import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.note import Note
from app.repositories.note_repo import NoteRepository
from app.schemas.note import NoteCreate, NoteOut, NoteUpdate

router = APIRouter()

MAX_PAGE_SIZE = 200


@router.post("", response_model=NoteOut, status_code=201)
async def create_note(
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    repo = NoteRepository(Note, db)
    note = await repo.create(obj_in={**payload.model_dump(), "owner_id": owner_id})
    await db.commit()
    return note


@router.get("", response_model=List[NoteOut])
async def list_notes(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    repo = NoteRepository(Note, db)
    return await repo.list_by_owner(owner_id, skip=skip, limit=limit)


@router.get("/{note_id}", response_model=NoteOut)
async def get_note(
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    repo = NoteRepository(Note, db)
    note = await repo.get(note_id)
    # A note owned by someone else is indistinguishable from one that does not
    # exist, so ownership is never leaked.
    if not note or note.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.patch("/{note_id}", response_model=NoteOut)
async def update_note(
    note_id: uuid.UUID,
    payload: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    repo = NoteRepository(Note, db)
    note = await repo.get(note_id)
    if not note or note.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="Note not found")

    changes = payload.model_dump(exclude_unset=True)
    if changes:
        note = await repo.update(db_obj=note, obj_in=changes)
    await db.commit()
    return note


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    owner_id: uuid.UUID = Depends(get_current_user_id),
):
    repo = NoteRepository(Note, db)
    note = await repo.get(note_id)
    if not note or note.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="Note not found")
    await repo.remove(id=note_id)
    await db.commit()
