import os
import shutil
from typing import BinaryIO
from app.core.config import settings

class StorageAdapter:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)

    async def upload_file(self, file: BinaryIO, filename: str) -> str:
        """
        Saves file to local storage.
        """
        file_path = os.path.join(self.upload_dir, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file, buffer)
        return file_path

    async def get_file_content(self, file_path: str) -> bytes:
        with open(file_path, "rb") as f:
            return f.read()

    async def delete_file(self, file_path: str):
        if os.path.exists(file_path):
            os.remove(file_path)

# In a real app, we'd use a Factory for Cloudinary/Firebase
def get_storage():
    return StorageAdapter()
