import os
import re
import shutil
import uuid
from typing import BinaryIO
from app.core.config import settings


class StorageAdapter:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

    async def upload_file(self, file: BinaryIO, filename: str) -> str:
        """
        Saves file to local storage with a safe, unique filename.
        """
        if hasattr(file, "seek"):
            file.seek(0)

        safe_name = self._sanitize_filename(filename or "upload.bin")
        file_path = self._build_unique_path(safe_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file, buffer)
        return file_path

    async def get_file_content(self, file_path: str) -> bytes:
        with open(file_path, "rb") as f:
            return f.read()

    async def delete_file(self, file_path: str):
        if os.path.exists(file_path):
            os.remove(file_path)

    def _sanitize_filename(self, filename: str) -> str:
        name = os.path.basename(filename or "upload.bin")
        stem, ext = os.path.splitext(name)
        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._") or "upload"
        return f"{safe_stem}{ext.lower()}" if ext else safe_stem

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


# In a real app, we'd use a Factory for Cloudinary/Firebase
def get_storage():
    return StorageAdapter()
