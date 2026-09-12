"""Storage backend contract shared by every provider.

A backend takes an uploaded file and returns an opaque *handle* (a local path,
an object key, a URL — whatever that provider needs). The app stores that handle
(e.g. `resume.s3_path`) and later passes it back to `get_file_content` /
`delete_file`. Handles are only ever meaningful to the backend that made them, so
switching STORAGE_TYPE affects new uploads only, not files already stored.
"""

import os
import re
import uuid
from abc import ABC, abstractmethod
from typing import BinaryIO


def sanitize_filename(filename: str) -> str:
    """A safe display filename: keep [A-Za-z0-9._-], collapse the rest."""
    name = os.path.basename(filename or "upload.bin")
    stem, ext = os.path.splitext(name)
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._") or "upload"
    return f"{safe_stem}{ext.lower()}" if ext else safe_stem


def unique_object_key(filename: str) -> str:
    """A collision-resistant object key for cloud stores: '<name>-<rand><ext>'."""
    safe = sanitize_filename(filename)
    stem, ext = os.path.splitext(safe)
    return f"{stem}-{uuid.uuid4().hex[:12]}{ext}"


class StorageBackend(ABC):
    """The interface every storage provider implements."""

    @abstractmethod
    async def upload_file(self, file: BinaryIO, filename: str) -> str:
        """Store the file and return the handle to read/delete it later."""

    @abstractmethod
    async def get_file_content(self, file_path: str) -> bytes:
        """Return the bytes for a handle produced by `upload_file`."""

    @abstractmethod
    async def delete_file(self, file_path: str) -> None:
        """Remove the file for a handle; a missing file is not an error."""
