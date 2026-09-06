"""What makes this file itself, and which of those values is allowed to decide.

Four values are published and one decides. The other three exist so a reader can
cross-reference against a database that was built before anybody keyed one on
SHA-256, and they are never allowed to answer the question the deciding value
answers.

The split matters because the weak values are the ones already written down
everywhere. A 32-bit checksum is an error code with 2^32 room, and collisions in
it are constructed rather than stumbled upon; MD5 and SHA-1 are both broken for
collision resistance. Any of the three is fine for finding a candidate row in
somebody's list and none of them is fine for deciding that a file is the file.

So `agrees` reads one field and refuses when it is absent, rather than falling
back to whichever weaker value happens to be present. A record that publishes the
cross-reference values and not the deciding one has published decoration, and
saying so is more useful than quietly grading it on a curve.
"""

from __future__ import annotations

import hashlib
import zlib
from collections.abc import Mapping
from typing import Any

from .errors import NoAuthority

AUTHORITATIVE = "sha256"
"""The one value that decides whether a file is the file."""

CROSS_REFERENCE = ("size", "crc32", "md5", "sha1")
"""Published so a reader can find the row, never so anything can decide."""


def measure(data: bytes) -> Mapping[str, Any]:
    """Every published value for these bytes, the deciding one among them."""
    return {
        "size": len(data),
        "crc32": f"{zlib.crc32(data):08x}",
        "md5": hashlib.md5(data).hexdigest(),
        "sha1": hashlib.sha1(data).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def agrees(found: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    """Whether the one value that decides matches.

    Every other field is ignored, whether it agrees or not. A record whose weaker
    values match and whose deciding value does not is a record about a different
    file, and one whose deciding value matches has already answered the question
    the others were asked to help with.
    """
    for side in (found, expected):
        if AUTHORITATIVE not in side:
            raise NoAuthority(f"nothing decides: no {AUTHORITATIVE} to compare")
    return str(found[AUTHORITATIVE]).lower() == str(expected[AUTHORITATIVE]).lower()
