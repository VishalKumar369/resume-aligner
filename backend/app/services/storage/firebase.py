import asyncio
from typing import BinaryIO

from app.core.config import settings
from app.services.storage.base import StorageBackend, unique_object_key

_PREFIX = "resume-aligner"


class FirebaseStorage(StorageBackend):
    """Firebase / Google Cloud Storage backend via firebase_admin. The handle is
    the blob path within the configured bucket."""

    def __init__(self):
        if not (settings.FIREBASE_CREDENTIALS_PATH and settings.FIREBASE_STORAGE_BUCKET):
            raise ValueError(
                "Firebase storage requires FIREBASE_CREDENTIALS_PATH and FIREBASE_STORAGE_BUCKET."
            )
        try:
            import firebase_admin
            from firebase_admin import credentials
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ValueError(
                "Firebase storage needs the 'firebase-admin' package (pip install firebase-admin)."
            ) from exc

        # initialize_app must run once per process.
        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred, {"storageBucket": settings.FIREBASE_STORAGE_BUCKET})

    def _bucket(self):
        from firebase_admin import storage
        return storage.bucket()

    async def upload_file(self, file: BinaryIO, filename: str) -> str:
        if hasattr(file, "seek"):
            file.seek(0)
        data = file.read()
        blob_path = f"{_PREFIX}/{unique_object_key(filename)}"

        def _upload():
            self._bucket().blob(blob_path).upload_from_string(data)
            return blob_path

        return await asyncio.to_thread(_upload)

    async def get_file_content(self, file_path: str) -> bytes:
        def _download():
            return self._bucket().blob(file_path).download_as_bytes()

        return await asyncio.to_thread(_download)

    async def delete_file(self, file_path: str) -> None:
        def _delete():
            blob = self._bucket().blob(file_path)
            if blob.exists():
                blob.delete()

        await asyncio.to_thread(_delete)
