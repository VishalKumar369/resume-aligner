import uuid
from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.api import deps
from app.core import security


class FakeUserRepo:
    """Stands in for UserRepository so these tests need no database."""

    users = {}

    def __init__(self, model, db):
        pass

    async def get(self, user_id):
        return FakeUserRepo.users.get(user_id)


@pytest.fixture(autouse=True)
def stub_user_lookup(monkeypatch):
    FakeUserRepo.users = {}
    monkeypatch.setattr(deps, "UserRepository", FakeUserRepo)
    return FakeUserRepo


def register(active: bool = True) -> uuid.UUID:
    user_id = uuid.uuid4()
    FakeUserRepo.users[user_id] = SimpleNamespace(id=user_id, is_active=active)
    return user_id


class TestTokenResolution:
    @pytest.mark.asyncio
    async def test_resolves_the_user_a_valid_token_names(self):
        user_id = register()
        token = security.create_access_token(user_id)

        user = await deps.get_current_user(token=token, db=None)
        assert user.id == user_id

    @pytest.mark.asyncio
    async def test_rejects_a_token_signed_with_another_secret(self):
        from jose import jwt

        user_id = register()
        forged = jwt.encode({"sub": str(user_id)}, "not-the-real-secret", algorithm="HS256")

        with pytest.raises(Exception) as caught:
            await deps.get_current_user(token=forged, db=None)
        assert caught.value.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_an_expired_token(self):
        user_id = register()
        expired = security.create_access_token(user_id, expires_delta=timedelta(seconds=-30))

        with pytest.raises(Exception) as caught:
            await deps.get_current_user(token=expired, db=None)
        assert caught.value.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_garbage(self):
        with pytest.raises(Exception) as caught:
            await deps.get_current_user(token="not-a-jwt", db=None)
        assert caught.value.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_a_token_for_a_user_that_no_longer_exists(self):
        # Valid signature, but the account was removed.
        token = security.create_access_token(uuid.uuid4())

        with pytest.raises(Exception) as caught:
            await deps.get_current_user(token=token, db=None)
        assert caught.value.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_a_deactivated_account(self):
        token = security.create_access_token(register(active=False))

        with pytest.raises(Exception) as caught:
            await deps.get_current_user(token=token, db=None)
        assert caught.value.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_a_subject_that_is_not_a_uuid(self):
        from jose import jwt

        from app.core.config import settings

        token = jwt.encode({"sub": "admin"}, settings.SECRET_KEY, algorithm=security.ALGORITHM)
        with pytest.raises(Exception) as caught:
            await deps.get_current_user(token=token, db=None)
        assert caught.value.status_code == 401


class TestOptionalUser:
    @pytest.mark.asyncio
    async def test_no_token_yields_none_rather_than_raising(self):
        assert await deps.get_current_user_optional(token=None, db=None) is None

    @pytest.mark.asyncio
    async def test_an_invalid_token_yields_none(self):
        assert await deps.get_current_user_optional(token="nonsense", db=None) is None

    @pytest.mark.asyncio
    async def test_a_valid_token_yields_the_user(self):
        user_id = register()
        user = await deps.get_current_user_optional(
            token=security.create_access_token(user_id), db=None
        )
        assert user is not None and user.id == user_id


class TestOwnershipScoping:
    """The queries that keep one account's data out of another's responses."""

    def test_alignment_listing_filters_by_owned_resumes(self):
        from app.models.alignment import AlignmentScore
        from app.repositories.alignment_repo import AlignmentRepository

        repo = AlignmentRepository(AlignmentScore, db=None)
        rendered = str(repo._owned_resume_ids(uuid.uuid4()))

        # Alignments carry no owner column, so they must be constrained through
        # the resume that produced them.
        assert "resumes.owner_id" in rendered

    def test_dashboard_filters_by_owned_resumes(self):
        from app.services.dashboard.analytics import DashboardAnalyticsService

        rendered = str(DashboardAnalyticsService()._owned_resumes(uuid.uuid4()))
        assert "resumes.owner_id" in rendered
        assert "resumes.is_deleted" in rendered
