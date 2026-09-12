"""Storage factory: pick a backend from `settings.STORAGE_TYPE`.

Adding a provider is a two-line change: implement `StorageBackend` in its own
module and register it in `_BACKENDS`. Optional-SDK backends are imported lazily
so `local` (the default) never pulls in httpx/cloudinary/firebase, and a
misconfigured provider fails fast with a clear message instead of silently
losing files. Unknown values fall back to local, so behaviour is unchanged.
"""

import logging
from typing import Callable, Dict

from app.core.config import settings
from app.services.storage.base import StorageBackend
from app.services.storage.local import LocalStorage

logger = logging.getLogger(__name__)

# Backward-compat alias: some callers/tests referenced the old class name.
StorageAdapter = LocalStorage


def _make_supabase() -> StorageBackend:
    from app.services.storage.supabase import SupabaseStorage
    return SupabaseStorage()


def _make_cloudinary() -> StorageBackend:
    from app.services.storage.cloudinary import CloudinaryStorage
    return CloudinaryStorage()


def _make_firebase() -> StorageBackend:
    from app.services.storage.firebase import FirebaseStorage
    return FirebaseStorage()


# name -> factory. Extend this to add a provider.
_BACKENDS: Dict[str, Callable[[], StorageBackend]] = {
    "local": LocalStorage,
    "supabase": _make_supabase,
    "cloudinary": _make_cloudinary,
    "firebase": _make_firebase,
}


def get_storage() -> StorageBackend:
    """The storage backend for the configured `STORAGE_TYPE` (default: local)."""
    kind = (settings.STORAGE_TYPE or "local").strip().lower()
    factory = _BACKENDS.get(kind)
    if factory is None:
        logger.warning("Unknown STORAGE_TYPE %r; using local storage.", kind)
        return LocalStorage()
    return factory()
