"""Signup/login/verify with the email-verification flag. DB-free: the user
repo and the OTP helpers are stubbed."""

import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.security import OAuth2PasswordRequestForm

from app.api.v1 import auth_routes
from app.core.config import settings
from app.schemas.user import UserCreate, VerifyEmailRequest


class FakeDB:
    async def commit(self):
        pass


def _stub_repo(monkeypatch, users=None, sink=None):
    users = users or {}

    class FakeRepo:
        def __init__(self, model, db):
            pass

        async def get_by_email(self, email):
            return users.get(email)

        async def create(self, *, obj_in):
            user = SimpleNamespace(
                id=uuid.uuid4(),
                created_at=datetime(2026, 9, 9),
                email=obj_in["email"],
                email_verified=obj_in["email_verified"],
            )
            if sink is not None:
                sink["obj_in"] = obj_in
            return user

    monkeypatch.setattr(auth_routes, "UserRepository", FakeRepo)


def _stub_otp(monkeypatch, *, code_ok=True):
    issued = []

    async def fake_issue(db, email):
        issued.append(email)

    async def fake_check(db, email, code):
        return code_ok

    monkeypatch.setattr(auth_routes, "issue_code", fake_issue)
    monkeypatch.setattr(auth_routes, "check_code", fake_check)
    return issued


def _login_form(email, password="secret123"):
    return OAuth2PasswordRequestForm(username=email, password=password)


class TestSignup:
    @pytest.mark.asyncio
    async def test_flag_on_creates_unverified_and_sends_code(self, monkeypatch):
        monkeypatch.setattr(settings, "EMAIL_VERIFICATION_ENABLED", True)
        sink = {}
        _stub_repo(monkeypatch, sink=sink)
        issued = _stub_otp(monkeypatch)

        user = await auth_routes.signup(
            UserCreate(email="New@x.com", password="secret123", full_name="New"), db=FakeDB()
        )

        assert user.email_verified is False
        assert sink["obj_in"]["email_verified"] is False
        assert issued == ["new@x.com"]

    @pytest.mark.asyncio
    async def test_flag_off_verifies_immediately_and_sends_nothing(self, monkeypatch):
        monkeypatch.setattr(settings, "EMAIL_VERIFICATION_ENABLED", False)
        _stub_repo(monkeypatch)
        issued = _stub_otp(monkeypatch)

        user = await auth_routes.signup(
            UserCreate(email="new@x.com", password="secret123"), db=FakeDB()
        )

        assert user.email_verified is True
        assert issued == []


class TestLogin:
    @pytest.mark.asyncio
    async def test_unverified_is_blocked_when_flag_on(self, monkeypatch):
        monkeypatch.setattr(settings, "EMAIL_VERIFICATION_ENABLED", True)
        user = SimpleNamespace(id=uuid.uuid4(), email="u@x.com", email_verified=False,
                               hashed_password="h")
        monkeypatch.setattr(auth_routes.security, "verify_password", lambda *a: True)
        _stub_repo(monkeypatch, users={"u@x.com": user})

        with pytest.raises(Exception) as caught:
            await auth_routes.login(_login_form("u@x.com"), db=FakeDB())
        assert getattr(caught.value, "status_code", None) == 403

    @pytest.mark.asyncio
    async def test_verified_gets_a_token(self, monkeypatch):
        monkeypatch.setattr(settings, "EMAIL_VERIFICATION_ENABLED", True)
        user = SimpleNamespace(id=uuid.uuid4(), email="u@x.com", email_verified=True,
                               hashed_password="h")
        monkeypatch.setattr(auth_routes.security, "verify_password", lambda *a: True)
        _stub_repo(monkeypatch, users={"u@x.com": user})

        token = await auth_routes.login(_login_form("u@x.com"), db=FakeDB())
        assert token["access_token"]


class TestVerifyEmail:
    @pytest.mark.asyncio
    async def test_valid_code_verifies_and_returns_token(self, monkeypatch):
        monkeypatch.setattr(settings, "EMAIL_VERIFICATION_ENABLED", True)
        user = SimpleNamespace(id=uuid.uuid4(), email="u@x.com", email_verified=False)
        _stub_repo(monkeypatch, users={"u@x.com": user})
        _stub_otp(monkeypatch, code_ok=True)

        token = await auth_routes.verify_email(
            VerifyEmailRequest(email="u@x.com", code="123456"), db=FakeDB()
        )
        assert token["access_token"]
        assert user.email_verified is True

    @pytest.mark.asyncio
    async def test_wrong_code_is_rejected(self, monkeypatch):
        monkeypatch.setattr(settings, "EMAIL_VERIFICATION_ENABLED", True)
        user = SimpleNamespace(id=uuid.uuid4(), email="u@x.com", email_verified=False)
        _stub_repo(monkeypatch, users={"u@x.com": user})
        _stub_otp(monkeypatch, code_ok=False)

        with pytest.raises(Exception) as caught:
            await auth_routes.verify_email(VerifyEmailRequest(email="u@x.com", code="000000"), db=FakeDB())
        assert getattr(caught.value, "status_code", None) == 400

    @pytest.mark.asyncio
    async def test_already_verified_never_hands_out_a_token(self, monkeypatch):
        monkeypatch.setattr(settings, "EMAIL_VERIFICATION_ENABLED", True)
        user = SimpleNamespace(id=uuid.uuid4(), email="u@x.com", email_verified=True)
        _stub_repo(monkeypatch, users={"u@x.com": user})
        _stub_otp(monkeypatch, code_ok=True)

        with pytest.raises(Exception) as caught:
            await auth_routes.verify_email(VerifyEmailRequest(email="u@x.com", code="123456"), db=FakeDB())
        assert getattr(caught.value, "status_code", None) == 400


class TestConfig:
    @pytest.mark.asyncio
    async def test_reports_the_flag(self, monkeypatch):
        monkeypatch.setattr(settings, "EMAIL_VERIFICATION_ENABLED", True)
        assert (await auth_routes.auth_config())["email_verification_enabled"] is True
