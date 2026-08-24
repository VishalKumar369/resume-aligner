"""JD update endpoint (verify step).

DB-free, matching test_me_settings: the repository is replaced with an in-memory
fake so these assert the handler logic — applying the user's verified role and
company and keeping structured_data in step.
"""

import uuid
from types import SimpleNamespace

import pytest

from app.api.v1 import jd_routes
from app.schemas.jd import JDUpdateSchema

OWNER_ID = uuid.uuid4()


class FakeDB:
    async def commit(self):
        pass

    async def refresh(self, obj):
        pass


def _jd(**overrides):
    row = SimpleNamespace(
        id=uuid.uuid4(),
        owner_id=OWNER_ID,
        title="Untitled role",
        company_name=None,
        structured_data={"role": "Untitled role", "company": None, "schema_version": "1.0"},
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def _stub_repo(monkeypatch, jd):
    class FakeRepo:
        def __init__(self, model, db):
            pass

        async def get(self, jd_id):
            return jd

    monkeypatch.setattr(jd_routes, "JDRepository", FakeRepo)


class TestUpdateJD:
    @pytest.mark.asyncio
    async def test_applies_role_and_company_and_syncs_structured_data(self, monkeypatch):
        jd = _jd()
        _stub_repo(monkeypatch, jd)

        result = await jd_routes.update_jd(
            jd_id=jd.id,
            payload=JDUpdateSchema(title="Backend Engineer", company_name="Acme"),
            db=FakeDB(),
            owner_id=OWNER_ID,
        )

        assert result.title == "Backend Engineer"
        assert result.company_name == "Acme"
        # Downstream views read structured_data, so it must agree.
        assert result.structured_data["role"] == "Backend Engineer"
        assert result.structured_data["company"] == "Acme"

    @pytest.mark.asyncio
    async def test_blank_company_clears_it_to_none(self, monkeypatch):
        jd = _jd(company_name="Old Corp", structured_data={"company": "Old Corp"})
        _stub_repo(monkeypatch, jd)

        result = await jd_routes.update_jd(
            jd_id=jd.id, payload=JDUpdateSchema(company_name="   "),
            db=FakeDB(), owner_id=OWNER_ID,
        )

        assert result.company_name is None
        assert result.structured_data["company"] is None

    @pytest.mark.asyncio
    async def test_a_partial_update_leaves_the_other_field(self, monkeypatch):
        jd = _jd(title="Data Scientist")
        _stub_repo(monkeypatch, jd)

        result = await jd_routes.update_jd(
            jd_id=jd.id, payload=JDUpdateSchema(company_name="Globex"),
            db=FakeDB(), owner_id=OWNER_ID,
        )

        assert result.title == "Data Scientist"
        assert result.company_name == "Globex"

    @pytest.mark.asyncio
    async def test_a_blank_title_is_ignored_rather_than_wiping_it(self, monkeypatch):
        jd = _jd(title="Data Scientist")
        _stub_repo(monkeypatch, jd)

        result = await jd_routes.update_jd(
            jd_id=jd.id, payload=JDUpdateSchema(title="   "),
            db=FakeDB(), owner_id=OWNER_ID,
        )

        assert result.title == "Data Scientist"

    @pytest.mark.asyncio
    async def test_rejects_another_users_jd(self, monkeypatch):
        jd = _jd(owner_id=uuid.uuid4())
        _stub_repo(monkeypatch, jd)

        with pytest.raises(Exception) as caught:
            await jd_routes.update_jd(
                jd_id=jd.id, payload=JDUpdateSchema(title="X"),
                db=FakeDB(), owner_id=OWNER_ID,
            )
        assert getattr(caught.value, "status_code", None) == 404
