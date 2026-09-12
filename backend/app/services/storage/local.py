import os
import shutil
import uuid
from typing import BinaryIO

from app.core.config import settings
from app.services.storage.base import StorageBackend, sanitize_filename


class LocalStorage(StorageBackend):
    """The default backend: files live under `settings.UPLOAD_DIR` and the handle
    is the local filesystem path. Behaviour is unchanged from the original
    single-adapter implementation."""

    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

    async def upload_file(self, file: BinaryIO, filename: str) -> str:
        if hasattr(file, "seek"):
            file.seek(0)

        safe_name = sanitize_filename(filename or "upload.bin")
        file_path = self._build_unique_path(safe_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file, buffer)
        return file_path

    async def get_file_content(self, file_path: str) -> bytes:
        with open(file_path, "rb") as f:
            return f.read()

    async def delete_file(self, file_path: str) -> None:
        if os.path.exists(file_path):
            os.remove(file_path)

    def _build_unique_path(self, filename: str) -> str:
        candidate = os.path.join(self.upload_dir, filename)
        if not os.path.exists(candidate):
            return candidate

        stem, ext = os.path.splitext(filename)
        while True:
            suffix = uuid.uuid4().hex[:8]
            candidate = os.path.join(self.upload_dir, f"{stem}-{suffix}{ext}")
            if not os.path.exists(candidate):
                return candidate
