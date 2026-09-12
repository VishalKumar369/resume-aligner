import asyncio
from typing import BinaryIO

from app.core.config import settings
from app.services.storage.base import StorageBackend, sanitize_filename

_FOLDER = "resume-aligner"


class CloudinaryStorage(StorageBackend):
    """Cloudinary backend. Resumes are non-image files, so they're stored as
    `resource_type="raw"`. The handle is the Cloudinary public_id."""

    def __init__(self):
        if not (
            settings.CLOUDINARY_CLOUD_NAME
            and settings.CLOUDINARY_API_KEY
            and settings.CLOUDINARY_API_SECRET
        ):
            raise ValueError(
                "Cloudinary storage requires CLOUDINARY_CLOUD_NAME, "
                "CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET."
            )
        try:
            import cloudinary
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ValueError(
                "Cloudinary storage needs the 'cloudinary' package (pip install cloudinary)."
            ) from exc

        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
        self._cloudinary = cloudinary

    async def upload_file(self, file: BinaryIO, filename: str) -> str:
        if hasattr(file, "seek"):
            file.seek(0)
        data = file.read()
        base_name = sanitize_filename(filename)

        def _upload():
            import cloudinary.uploader
            result = cloudinary.uploader.upload(
                data,
                resource_type="raw",
                folder=_FOLDER,
                public_id=base_name,
                use_filename=True,
                unique_filename=True,
                overwrite=False,
            )
            return result["public_id"]

        return await asyncio.to_thread(_upload)

    async def get_file_content(self, file_path: str) -> bytes:
        import httpx

        def _url():
            url, _opts = self._cloudinary.utils.cloudinary_url(
                file_path, resource_type="raw", secure=True
            )
            return url

        url = await asyncio.to_thread(_url)
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content

    async def delete_file(self, file_path: str) -> None:
        def _destroy():
            import cloudinary.uploader
            cloudinary.uploader.destroy(file_path, resource_type="raw", invalidate=True)

        await asyncio.to_thread(_destroy)
