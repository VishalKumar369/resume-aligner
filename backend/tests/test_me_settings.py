"""Account-settings endpoint behaviour (`/me`).

DB-free, matching the style of test_auth_scoping.py: the repositories the route
handlers instantiate are replaced with in-memory fakes, so these assert the
handler logic — aggregation, partial updates, input normalization, and the
password gate on deletion — without a live database.
"""

import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.api.v1 import me_routes
from app.core import security
from app.schemas.settings import (
    DeleteAccountIn,
    NotificationUpdate,
    ProfileUpdate,
)


# --------------------------------------------------------------------- fakes

class FakeUserRepo:
    def __init__(self, model, db):
        pass

    async def update(self, *, db_obj, obj_in):
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        return db_obj


class FakeNotifRepo:
    """One shared settings row, created on first access like the real repo."""

    row = None

    def __init__(self, model, db):
        pass

    async def get_or_create(self, user_id):
        if FakeNotifRepo.row is None:
            FakeNotifRepo.row = SimpleNamespace(
                user_id=user_id,
                email_alerts_on_new_matches=True,
                weekly_career_readiness_report=True,
            )
        return FakeNotifRepo.row

    async def update(self, *, db_obj, obj_in):
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        return db_obj


class FakeDB:
    """Stands in for the AsyncSession the delete handler writes through."""

    def add(self, _obj):
        pass

    async def flush(self):
        pass


def make_user(password: str = "Secret123!"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Existing Name",
        email="user@example.com",
        target_role=None,
        created_at=datetime(2026, 1, 1, 12, 0, 0),
        is_active=True,
        is_deleted=False,
        hashed_password=security.get_password_hash(password),
    )


@pytest.fixture(autouse=True)
def stub_repos(monkeypatch):
    FakeNotifRepo.row = None
    monkeypatch.setattr(me_routes, "UserRepository", FakeUserRepo)
    monkeypatch.setattr(me_routes, "NotificationSettingsRepository", FakeNotifRepo)


# ----------------------------------------------------------------- read /me

class TestReadMe:
    @pytest.mark.asyncio
    async def test_aggregates_profile_notifications_and_account(self):
        user = make_user()
        result = await me_routes.read_me(current_user=user, db=FakeDB())

        assert result.profile.email == "user@example.com"
        assert result.profile.full_name == "Existing Name"
        assert result.account.id == user.id
        # Notifications default to on when the row is created lazily.
        assert result.notifications.email_alerts_on_new_matches is True
        assert result.notifications.weekly_career_readiness_report is True


# --------------------------------------------------------------- update profile

class TestUpdateProfile:
    @pytest.mark.asyncio
    async def test_normalizes_and_persists_provided_fields(self):
        user = make_user()
        payload = ProfileUpdate(full_name="jane   backend  dev", target_role="  Staff Engineer ")

        result = await me_routes.update_profile(payload=payload, current_user=user, db=FakeDB())

        assert result.full_name == "Jane Backend Dev"  # title-cased, collapsed spaces
        assert result.target_role == "Staff Engineer"  # trimmed
        assert user.full_name == "Jane Backend Dev"  # written back to the row

    @pytest.mark.asyncio
    async def test_omitted_fields_are_left_untouched(self):
        user = make_user()
        user.target_role = "Original Role"
        # Only full_name supplied; target_role must not be cleared.
        payload = ProfileUpdate(full_name="new name")

        await me_routes.update_profile(payload=payload, current_user=user, db=FakeDB())

        assert user.full_name == "New Name"
        assert user.target_role == "Original Role"


# ----------------------------------------------------------- update notifications

class TestUpdateNotifications:
    @pytest.mark.asyncio
    async def test_partial_toggle_leaves_other_flag_unchanged(self):
        user = make_user()
        payload = NotificationUpdate(email_alerts_on_new_matches=False)

        result = await me_routes.update_notifications(
            payload=payload, current_user=user, db=FakeDB()
        )

        assert result.email_alerts_on_new_matches is False
        assert result.weekly_career_readiness_report is True  # untouched


# -------------------------------------------------------------- delete account

class TestDeleteAccount:
    @pytest.mark.asyncio
    async def test_wrong_password_is_rejected_and_account_untouched(self):
        user = make_user(password="correct-horse")
        payload = DeleteAccountIn(password="wrong")

        with pytest.raises(Exception) as caught:
            await me_routes.delete_my_account(payload=payload, current_user=user, db=FakeDB())

        assert caught.value.status_code == 400
        assert user.is_deleted is False
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_correct_password_soft_deletes_the_account(self):
        user = make_user(password="correct-horse")
        payload = DeleteAccountIn(password="correct-horse")

        response = await me_routes.delete_my_account(
            payload=payload, current_user=user, db=FakeDB()
        )

        assert response.status_code == 204
        assert user.is_deleted is True
        assert user.is_active is False
