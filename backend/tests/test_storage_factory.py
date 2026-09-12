"""The storage factory selects a backend from STORAGE_TYPE, and `local` (the
default) behaves exactly as the original single adapter."""

import io
import os

import pytest

from app.core.config import settings
from app.services.storage.local import LocalStorage
from app.services.storage.storage_adapter import get_storage


class TestFactory:
    def test_default_is_local(self, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_TYPE", "local")
        assert isinstance(get_storage(), LocalStorage)

    def test_unknown_type_falls_back_to_local(self, monkeypatch):
        # Never break signup/upload on a typo — just log and use local.
        monkeypatch.setattr(settings, "STORAGE_TYPE", "dropbox?")
        assert isinstance(get_storage(), LocalStorage)

    def test_supabase_is_selected_when_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_TYPE", "supabase")
        monkeypatch.setattr(settings, "SUPABASE_URL", "https://proj.supabase.co")
        monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", "service-key")
        from app.services.storage.supabase import SupabaseStorage
        assert isinstance(get_storage(), SupabaseStorage)

    def test_supabase_without_config_fails_fast(self, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_TYPE", "supabase")
        monkeypatch.setattr(settings, "SUPABASE_URL", None)
        monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", None)
        with pytest.raises(ValueError):
            get_storage()


class TestLocalUnchanged:
    @pytest.mark.asyncio
    async def test_upload_get_delete_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_TYPE", "local")
        monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

        storage = get_storage()
        path = await storage.upload_file(io.BytesIO(b"hello"), "My Résumé!.pdf")

        assert path.endswith(".pdf")
        assert await storage.get_file_content(path) == b"hello"
        await storage.delete_file(path)
        assert not os.path.exists(path)

    @pytest.mark.asyncio
    async def test_same_name_does_not_overwrite(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "STORAGE_TYPE", "local")
        monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

        storage = get_storage()
        first = await storage.upload_file(io.BytesIO(b"a"), "resume.pdf")
        second = await storage.upload_file(io.BytesIO(b"b"), "resume.pdf")

        assert first != second
        assert await storage.get_file_content(first) == b"a"
        assert await storage.get_file_content(second) == b"b"
