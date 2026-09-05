"""Personal notes CRUD, scoped to the owner.

DB-free, matching test_jd_routes: the repository is replaced with an in-memory
fake so these assert the handler logic — owner scoping, partial updates, and the
404-not-403 privacy on someone else's note — without a live database.
"""

import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.api.v1 import note_routes
from app.schemas.note import NoteCreate, NoteUpdate

OWNER_ID = uuid.uuid4()


class FakeDB:
    async def commit(self):
        pass


def _note(**overrides):
    row = SimpleNamespace(
        id=uuid.uuid4(),
        owner_id=OWNER_ID,
        title="Learn Kafka",
        content="Cover the basics this week.",
        category="Goal",
        color="primary",
        target_date=None,
        is_pinned=False,
        is_completed=False,
        created_at=datetime(2026, 9, 1),
        updated_at=None,
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def _stub_repo(monkeypatch, note=None, listed=None):
    captured = {}

    class FakeRepo:
        def __init__(self, model, db):
            pass

        async def create(self, *, obj_in):
            captured["created"] = obj_in
            return _note(**obj_in)

        async def list_by_owner(self, owner_id, *, skip=0, limit=200):
            captured["listed_owner"] = owner_id
            return listed or []

        async def get(self, note_id):
            return note

        async def update(self, *, db_obj, obj_in):
            captured["updated"] = obj_in
            for field, value in obj_in.items():
                setattr(db_obj, field, value)
            return db_obj

        async def remove(self, *, id):
            captured["removed"] = id

    monkeypatch.setattr(note_routes, "NoteRepository", FakeRepo)
    return captured


class TestCreate:
    @pytest.mark.asyncio
    async def test_creates_a_note_owned_by_the_caller(self, monkeypatch):
        captured = _stub_repo(monkeypatch)

        result = await note_routes.create_note(
            payload=NoteCreate(title="Ship the portfolio", content="by Friday", category="Goal"),
            db=FakeDB(), owner_id=OWNER_ID,
        )

        assert result.title == "Ship the portfolio"
        assert captured["created"]["owner_id"] == OWNER_ID
        assert captured["created"]["category"] == "Goal"


class TestList:
    @pytest.mark.asyncio
    async def test_lists_only_the_callers_notes(self, monkeypatch):
        captured = _stub_repo(monkeypatch, listed=[_note(), _note(title="Second")])

        result = await note_routes.list_notes(skip=0, limit=200, db=FakeDB(), owner_id=OWNER_ID)

        assert len(result) == 2
        assert captured["listed_owner"] == OWNER_ID


class TestGet:
    @pytest.mark.asyncio
    async def test_returns_the_note_to_its_owner(self, monkeypatch):
        note = _note()
        _stub_repo(monkeypatch, note=note)

        result = await note_routes.get_note(note_id=note.id, db=FakeDB(), owner_id=OWNER_ID)
        assert result is note

    @pytest.mark.asyncio
    async def test_hides_another_users_note_as_a_404(self, monkeypatch):
        _stub_repo(monkeypatch, note=_note(owner_id=uuid.uuid4()))

        with pytest.raises(Exception) as caught:
            await note_routes.get_note(note_id=uuid.uuid4(), db=FakeDB(), owner_id=OWNER_ID)
        assert getattr(caught.value, "status_code", None) == 404

    @pytest.mark.asyncio
    async def test_missing_note_is_a_404(self, monkeypatch):
        _stub_repo(monkeypatch, note=None)

        with pytest.raises(Exception) as caught:
            await note_routes.get_note(note_id=uuid.uuid4(), db=FakeDB(), owner_id=OWNER_ID)
        assert getattr(caught.value, "status_code", None) == 404


class TestUpdate:
    @pytest.mark.asyncio
    async def test_applies_only_the_fields_sent(self, monkeypatch):
        note = _note()
        captured = _stub_repo(monkeypatch, note=note)

        result = await note_routes.update_note(
            note_id=note.id, payload=NoteUpdate(is_completed=True), db=FakeDB(), owner_id=OWNER_ID,
        )

        assert result.is_completed is True
        # A partial update touches only what was sent.
        assert captured["updated"] == {"is_completed": True}

    @pytest.mark.asyncio
    async def test_cannot_update_another_users_note(self, monkeypatch):
        _stub_repo(monkeypatch, note=_note(owner_id=uuid.uuid4()))

        with pytest.raises(Exception) as caught:
            await note_routes.update_note(
                note_id=uuid.uuid4(), payload=NoteUpdate(title="Hijack"), db=FakeDB(), owner_id=OWNER_ID,
            )
        assert getattr(caught.value, "status_code", None) == 404


class TestDelete:
    @pytest.mark.asyncio
    async def test_soft_deletes_the_owners_note(self, monkeypatch):
        note = _note()
        captured = _stub_repo(monkeypatch, note=note)

        await note_routes.delete_note(note_id=note.id, db=FakeDB(), owner_id=OWNER_ID)
        assert captured["removed"] == note.id

    @pytest.mark.asyncio
    async def test_cannot_delete_another_users_note(self, monkeypatch):
        _stub_repo(monkeypatch, note=_note(owner_id=uuid.uuid4()))

        with pytest.raises(Exception) as caught:
            await note_routes.delete_note(note_id=uuid.uuid4(), db=FakeDB(), owner_id=OWNER_ID)
        assert getattr(caught.value, "status_code", None) == 404


class TestSchema:
    def test_blank_title_is_rejected(self):
        with pytest.raises(Exception):
            NoteCreate(title="   ")

    def test_unknown_colour_falls_back_to_primary(self):
        assert NoteCreate(title="x", color="chartreuse").color == "primary"
        assert NoteCreate(title="x", color="success").color == "success"

    def test_update_ignores_unset_fields(self):
        changes = NoteUpdate(is_pinned=True).model_dump(exclude_unset=True)
        assert changes == {"is_pinned": True}
