"""Feedback submission — anonymous from the landing page, attributed when
signed in. DB-free: the repository is stubbed."""

import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.api.v1 import feedback_routes
from app.schemas.feedback import FeedbackCreate


class FakeDB:
    async def commit(self):
        pass


def _stub_repo(monkeypatch):
    captured = {}

    class FakeRepo:
        def __init__(self, model, db):
            pass

        async def create(self, *, obj_in):
            captured["created"] = obj_in
            return SimpleNamespace(
                id=uuid.uuid4(),
                rating=obj_in.get("rating"),
                message=obj_in["message"],
                created_at=datetime(2026, 9, 9),
            )

    monkeypatch.setattr(feedback_routes, "FeedbackRepository", FakeRepo)
    return captured


class TestSubmit:
    @pytest.mark.asyncio
    async def test_anonymous_feedback_has_no_owner(self, monkeypatch):
        captured = _stub_repo(monkeypatch)

        result = await feedback_routes.submit_feedback(
            payload=FeedbackCreate(message="Love it", rating=5, source="landing"),
            db=FakeDB(), user=None,
        )

        assert result.message == "Love it"
        assert captured["created"].get("owner_id") is None

    @pytest.mark.asyncio
    async def test_signed_in_feedback_is_attributed_to_the_account(self, monkeypatch):
        captured = _stub_repo(monkeypatch)
        user = SimpleNamespace(id=uuid.uuid4(), email="vishal@x.com")

        await feedback_routes.submit_feedback(
            payload=FeedbackCreate(message="Useful", source="settings"),
            db=FakeDB(), user=user,
        )

        assert captured["created"]["owner_id"] == user.id
        assert captured["created"]["email"] == "vishal@x.com"


class TestSchema:
    def test_blank_message_is_rejected(self):
        with pytest.raises(Exception):
            FeedbackCreate(message="   ")

    def test_rating_must_be_one_to_five(self):
        with pytest.raises(Exception):
            FeedbackCreate(message="x", rating=9)
        assert FeedbackCreate(message="x", rating=4).rating == 4

    def test_unknown_source_is_dropped(self):
        assert FeedbackCreate(message="x", source="somewhere").source is None
        assert FeedbackCreate(message="x", source="landing").source == "landing"
