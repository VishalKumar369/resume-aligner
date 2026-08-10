_ENCODINGS = ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp1252", "latin-1")


def extract_plain_text(file_bytes: bytes) -> str:
    """Decode a text-like upload, trying the encodings resumes actually use."""
    for encoding in _ENCODINGS:
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("latin-1", errors="ignore")
