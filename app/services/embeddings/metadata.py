import hashlib


def compute_content_hash(text: str) -> str:
    """
    Calculate a deterministic SHA-256 hash of chunk content.
    """

    if not isinstance(text, str):
        raise TypeError("Chunk content must be a string.")

    if not text:
        raise ValueError("Chunk content cannot be empty.")

    normalized = text.encode("utf-8")

    return hashlib.sha256(normalized).hexdigest()