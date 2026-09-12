from typing import BinaryIO, Optional

import httpx

from app.core.config import settings
from app.services.storage.base import StorageBackend, unique_object_key

_UPLOAD_TIMEOUT = 60.0


class SupabaseStorage(StorageBackend):
    """Supabase Storage via its REST API. The handle is the object key inside the
    bucket. Uses the service key, so the bucket can (and should) be private."""

    def __init__(self):
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise ValueError(
                "Supabase storage requires SUPABASE_URL and SUPABASE_SERVICE_KEY."
            )
        self._base = settings.SUPABASE_URL.rstrip("/")
        self._bucket = settings.SUPABASE_BUCKET_NAME
        self._key = settings.SUPABASE_SERVICE_KEY

    def _headers(self, extra: Optional[dict] = None) -> dict:
        headers = {"Authorization": f"Bearer {self._key}", "apikey": self._key}
        if extra:
            headers.update(extra)
        return headers

    def _object_url(self, object_key: str) -> str:
        return f"{self._base}/storage/v1/object/{self._bucket}/{object_key}"

    async def upload_file(self, file: BinaryIO, filename: str) -> str:
        if hasattr(file, "seek"):
            file.seek(0)
        data = file.read()
        object_key = unique_object_key(filename)

        async with httpx.AsyncClient(timeout=_UPLOAD_TIMEOUT) as client:
            resp = await client.post(
                self._object_url(object_key),
                headers=self._headers({
                    "content-type": "application/octet-stream",
                    "x-upsert": "true",
                }),
                content=data,
            )
            resp.raise_for_status()
        return object_key

    async def get_file_content(self, file_path: str) -> bytes:
        async with httpx.AsyncClient(timeout=_UPLOAD_TIMEOUT) as client:
            resp = await client.get(self._object_url(file_path), headers=self._headers())
            resp.raise_for_status()
            return resp.content

    async def delete_file(self, file_path: str) -> None:
        async with httpx.AsyncClient(timeout=_UPLOAD_TIMEOUT) as client:
            resp = await client.delete(self._object_url(file_path), headers=self._headers())
            if resp.status_code not in (200, 404):
                resp.raise_for_status()
