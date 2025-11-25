"""Hashing utilities for ZotWatch."""

import hashlib


def hash_content(*parts: str) -> str:
    """Generate SHA256 hash from content parts."""
    sha = hashlib.sha256()
    for part in parts:
        if part:
            sha.update(part.encode("utf-8"))
    return sha.hexdigest()


__all__ = ["hash_content"]
