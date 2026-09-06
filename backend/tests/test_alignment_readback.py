import uuid
from datetime import datetime
from io import BytesIO
from types import SimpleNamespace

import pytest
from starlette.datastructures import Headers, UploadFile

from app.api.v1 import alignment_routes, resume_routes
from app.api.v1.alignment_routes import _to_detail, _to_summary, delete_alignment


def stored_row(**overrides):
    """A row as SQLAlchemy would hand it back."""
    row = SimpleNamespace(
        id=uuid.uuid4(),
        resume_id=uuid.uuid4(),
        jd_id=uuid.uuid4(),
        total_alignment_score=68.3,
        ats_score=75.36,
        skill_match_score=89.09,
        experience_match_score=63.33,
        created_at=datetime(2026, 8, 11, 12, 0, 0),
        analysis_data={
            "missing_keywords": ["Kafka"],
            "matched_skills": ["Python", "FastAPI"],
            "partial_skills": [{"skill": "Kubernetes", "covered_by": "Docker"}],
            "missing_skills": [
                {"skill": "Kafka", "importance": "preferred", "priority": "P3", "weight": 0.25}
            ],
            "breakdown": {"skill_match": 89.09, "seniority_match": 63.33},
            "component_weights": {"skill_match": 0.5, "seniority_match": 0.5},
            "ats_breakdown": {"keyword_coverage": 57.14},
            "ats_warnings": ["Add measurable results."],
            "feedback": "Reasonable match.",
            "improvement_suggestions": ["Add evidence of Kafka."],
            "extraction_health": {"resume_ok": True, "jd_ok": True, "warnings": []},
        },
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


class TestSummaryMapping:
    def test_maps_the_stored_column_to_the_api_field_name(self):
        row = stored_row()
        summary = _to_summary(row)

        # The column is total_alignment_score; the API says alignment_score,
        # matching the generate response.
        assert summary.alignment_score == row.total_alignment_score
        assert summary.ats_score == row.ats_score
        assert summary.id == row.id
        assert summary.created_at == row.created_at

    def test_null_scores_become_zero(self):
        summary = _to_summary(stored_row(total_alignment_score=None, ats_score=None))
        assert summary.alignment_score == 0.0
        assert summary.ats_score == 0.0

    def test_labels_the_run_with_its_company_role_and_resume(self):
        jd = SimpleNamespace(id=uuid.uuid4(), title="Senior Backend Engineer", company_name="Acme")
        resume = SimpleNamespace(id=uuid.uuid4(), label="Main Tech Resume", filename="cv.pdf")

        summary = _to_summary(stored_row(), jd=jd, resume=resume)

        assert summary.company == "Acme"
        assert summary.role == "Senior Backend Engineer"
        assert summary.resume_label == "Main Tech Resume"

    def test_falls_back_to_the_filename_when_the_resume_has_no_label(self):
        resume = SimpleNamespace(id=uuid.uuid4(), label=None, filename="cv.pdf")
        assert _to_summary(stored_row(), resume=resume).resume_label == "cv.pdf"

    def test_labels_are_none_on_a_single_run_read(self):
        # get_alignment / _to_detail pass no JD or resume.
        summary = _to_summary(stored_row())
        assert summary.company is None
        assert summary.role is None
        assert summary.resume_label is None

    def test_company_is_none_when_the_jd_has_no_company_name(self):
        jd = SimpleNamespace(id=uuid.uuid4(), title="Engineer", company_name=None)
        assert _to_summary(stored_row(), jd=jd).company is None

    def test_summary_carries_no_analysis_payload(self):
        # List rows stay small as history grows.
        fields = _to_summary(stored_row()).model_dump()
        for heavy in ("breakdown", "matched_skills", "missing_skills", "ats_breakdown"):
            assert heavy not in fields


class TestDetailMapping:
    def test_unpacks_the_stored_analysis(self):
        detail = _to_detail(stored_row())

        assert detail.matched_skills == ["Python", "FastAPI"]
        assert detail.partial_skills[0]["covered_by"] == "Docker"
        assert detail.missing_skills[0]["priority"] == "P3"
        assert detail.breakdown["skill_match"] == 89.09
        assert detail.ats_warnings == ["Add measurable results."]
        assert detail.feedback == "Reasonable match."
        assert detail.extraction_health.resume_ok is True

    def test_detail_includes_the_summary_fields(self):
        row = stored_row()
        detail = _to_detail(row)
        assert detail.id == row.id
        assert detail.alignment_score == row.total_alignment_score

    def test_a_row_with_no_analysis_still_maps(self):
        # Rows written before Phase 4 have a thinner analysis_data blob.
        detail = _to_detail(stored_row(analysis_data=None))

        assert detail.breakdown == {}
        assert detail.matched_skills == []
        assert detail.feedback == ""
        assert detail.extraction_health is None

    def test_partial_analysis_fills_the_gaps(self):
        detail = _to_detail(stored_row(analysis_data={"missing_keywords": ["Kafka"]}))

        assert detail.missing_keywords == ["Kafka"]
        assert detail.ats_breakdown == {}
        assert detail.improvement_suggestions == []


OWNER_ID = uuid.uuid4()


class _Result:
    def __init__(self, first_value):
        self._first = first_value

    def first(self):
        return self._first


class _FakeDB:
    """Enough of an AsyncSession for the delete cascade: the first execute is the
    sibling-run SELECT, any later one is the versions UPDATE."""

    def __init__(self, *, sibling=None, jd=None):
        self._sibling = sibling
        self._jd = jd
        self.execute_calls = 0
        self.versions_retired = False
        self.committed = False

    async def execute(self, _stmt):
        self.execute_calls += 1
        if self.execute_calls == 1:
            return _Result(self._sibling)
        self.versions_retired = True
        return _Result(None)

    async def get(self, _model, _id):
        return self._jd

    async def commit(self):
        self.committed = True


def _stub_delete_repo(monkeypatch, row, owned=True):
    class FakeRepo:
        def __init__(self, model, db):
            pass

        async def get(self, _id):
            return row

        async def is_owned_by(self, _row, _owner_id, _db):
            return owned

    monkeypatch.setattr(alignment_routes, "AlignmentRepository", FakeRepo)


class TestDeleteAlignment:
    @pytest.mark.asyncio
    async def test_retires_the_jd_and_versions_when_it_was_the_last_run(self, monkeypatch):
        row = stored_row(is_deleted=False)
        jd = SimpleNamespace(id=row.jd_id, owner_id=OWNER_ID, is_deleted=False)
        _stub_delete_repo(monkeypatch, row)
        db = _FakeDB(sibling=None, jd=jd)

        result = await delete_alignment(alignment_id=row.id, db=db, owner_id=OWNER_ID)

        assert result.status_code == 204
        assert row.is_deleted is True          # the analysis
        assert jd.is_deleted is True           # the posting (leaves Company Intel)
        assert db.versions_retired is True     # its tailored resume versions
        assert db.committed is True

    @pytest.mark.asyncio
    async def test_keeps_the_jd_when_a_sibling_run_remains(self, monkeypatch):
        row = stored_row(is_deleted=False)
        jd = SimpleNamespace(id=row.jd_id, owner_id=OWNER_ID, is_deleted=False)
        _stub_delete_repo(monkeypatch, row)
        # A re-run of the same posting still exists.
        db = _FakeDB(sibling=SimpleNamespace(id=uuid.uuid4()), jd=jd)

        await delete_alignment(alignment_id=row.id, db=db, owner_id=OWNER_ID)

        assert row.is_deleted is True
        assert jd.is_deleted is False          # other runs still need it
        assert db.versions_retired is False
        assert db.committed is True

    @pytest.mark.asyncio
    async def test_missing_run_is_a_404(self, monkeypatch):
        _stub_delete_repo(monkeypatch, row=None)

        with pytest.raises(Exception) as caught:
            await delete_alignment(alignment_id=uuid.uuid4(), db=_FakeDB(), owner_id=OWNER_ID)
        assert getattr(caught.value, "status_code", None) == 404

    @pytest.mark.asyncio
    async def test_another_users_run_is_a_404(self, monkeypatch):
        _stub_delete_repo(monkeypatch, row=stored_row(is_deleted=False), owned=False)

        with pytest.raises(Exception) as caught:
            await delete_alignment(alignment_id=uuid.uuid4(), db=_FakeDB(), owner_id=OWNER_ID)
        assert getattr(caught.value, "status_code", None) == 404


def _upload(payload: bytes = b"%PDF-1.4 fake", filename: str = "resume.pdf") -> UploadFile:
    return UploadFile(
        file=BytesIO(payload),
        filename=filename,
        headers=Headers({"content-type": "application/pdf"}),
    )


class TestUploadDedupe:
    @pytest.fixture
    def existing_resume(self):
        return SimpleNamespace(
            id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            filename="resume.pdf",
            label="Main Tech Resume",
            s3_path="uploads/resume.pdf",
            created_at=datetime(2026, 8, 9, 10, 0, 0),
            structured_data={"schema_version": "1.0"},
            extraction_meta={"method": "pdf_text"},
        )

    def _stub_repo(self, monkeypatch, found):
        seen = {}

        class FakeRepo:
            def __init__(self, model, db):
                pass

            async def get_by_content_hash(self, owner_id, content_hash):
                seen["content_hash"] = content_hash
                return found

            async def create(self, *, obj_in):  # pragma: no cover - must not run
                raise AssertionError("a duplicate upload must not create a record")

        monkeypatch.setattr(resume_routes, "ResumeRepository", FakeRepo)
        return seen

    @pytest.mark.asyncio
    async def test_returns_the_existing_record_for_identical_content(
        self, monkeypatch, existing_resume
    ):
        self._stub_repo(monkeypatch, found=existing_resume)

        result = await resume_routes.upload_resume(file=_upload(), label=None, db=None, owner_id=OWNER_ID)

        assert result.id == existing_resume.id
        assert result.duplicate_of_existing is True
        assert result.label == "Main Tech Resume"

    @pytest.mark.asyncio
    async def test_does_not_reparse_or_store_a_duplicate(self, monkeypatch, existing_resume):
        self._stub_repo(monkeypatch, found=existing_resume)

        def _explode(*args, **kwargs):  # pragma: no cover - must not run
            raise AssertionError("a duplicate upload must not be parsed again")

        monkeypatch.setattr(resume_routes.ResumeParserService, "extract", _explode)
        monkeypatch.setattr(resume_routes, "get_storage", _explode)

        result = await resume_routes.upload_resume(file=_upload(), label=None, db=None, owner_id=OWNER_ID)
        assert result.duplicate_of_existing is True

    @pytest.mark.asyncio
    async def test_looks_up_by_the_sha256_of_the_bytes(self, monkeypatch, existing_resume):
        import hashlib

        payload = b"%PDF-1.4 specific bytes"
        seen = self._stub_repo(monkeypatch, found=existing_resume)

        await resume_routes.upload_resume(file=_upload(payload), label=None, db=None, owner_id=OWNER_ID)

        assert seen["content_hash"] == hashlib.sha256(payload).hexdigest()

    @pytest.mark.asyncio
    async def test_an_empty_upload_is_still_rejected_before_the_hash_lookup(self, monkeypatch):
        self._stub_repo(monkeypatch, found=None)

        with pytest.raises(Exception) as caught:
            await resume_routes.upload_resume(file=_upload(b""), label=None, db=None, owner_id=OWNER_ID)

        assert getattr(caught.value, "status_code", None) == 400
