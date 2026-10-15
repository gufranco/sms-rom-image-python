from __future__ import annotations

import hashlib
import zlib
from collections.abc import Mapping
from typing import Any

from .errors import NoAuthority

AUTHORITATIVE = "sha256"

CROSS_REFERENCE = ("size", "crc32", "md5", "sha1")


def measure(data: bytes) -> Mapping[str, Any]:
    return {
        "size": len(data),
        "crc32": f"{zlib.crc32(data):08x}",
        "md5": hashlib.md5(data).hexdigest(),
        "sha1": hashlib.sha1(data).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def agrees(found: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    for side in (found, expected):
        if AUTHORITATIVE not in side:
            raise NoAuthority(f"nothing decides: no {AUTHORITATIVE} to compare")
    return str(found[AUTHORITATIVE]).lower() == str(expected[AUTHORITATIVE]).lower()
