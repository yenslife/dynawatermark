from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonicalize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return canonicalize(value.model_dump(mode="json"))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): canonicalize(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [canonicalize(item) for item in value]
    if isinstance(value, float):
        return round(value, 6)
    return value


def canonical_json_bytes(value: Any) -> bytes:
    normalized = canonicalize(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
