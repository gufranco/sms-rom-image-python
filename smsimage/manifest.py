from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, override

from .errors import Malformed, NoAuthority
from .identity import AUTHORITATIVE, measure

ACCEPTED = "accepted"
BAD_DUMP = "a known bad dump"
WRONG_CONTENT = "the right length, the wrong content"
WRONG_SIZE = "a length nothing declares"
UNDECLARED = "undeclared"

VERDICTS = (ACCEPTED, BAD_DUMP, WRONG_CONTENT, WRONG_SIZE, UNDECLARED)


class Match:
    __slots__ = ("found", "key", "verdict", "why")

    def __init__(
        self, key: str, verdict: str, found: Mapping[str, Any], why: str | None = None
    ) -> None:
        self.key = key
        self.verdict = verdict
        self.found = found
        self.why = why

    def __bool__(self) -> bool:
        return self.verdict == ACCEPTED

    @override
    def __repr__(self) -> str:
        return f"<Match {self.key}: {self.verdict}>"


class Manifest:
    __slots__ = ("_artifacts",)

    def __init__(self, document: Any) -> None:
        if not isinstance(document, Mapping):
            raise Malformed("a manifest is a mapping, and this is not one")

        artifacts = document.get("artifacts")
        if not isinstance(artifacts, Mapping) or not artifacts:
            raise Malformed("a manifest declares artifacts, and this declares none")

        for key, entry in artifacts.items():
            if not isinstance(entry, Mapping):
                raise Malformed(f"{key}: an artifact is a mapping, and this is not one")

            accepted = entry.get("accepted")
            if not isinstance(accepted, Sequence) or not accepted:
                raise Malformed(f"{key}: an artifact accepts something, and this accepts nothing")

            for one in accepted:
                if not isinstance(one, Mapping) or AUTHORITATIVE not in one:
                    raise NoAuthority(
                        f"{key}: an accepted file with no {AUTHORITATIVE} to decide on"
                    )

        self._artifacts = artifacts

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(self._artifacts)

    def name(self, key: str) -> str:
        entry = self._artifacts.get(key, {})
        named = entry.get("name")
        return str(named) if named else key

    def match(self, key: str, data: bytes) -> Match:
        found = measure(data)
        entry = self._artifacts.get(key)
        if entry is None:
            return Match(key, UNDECLARED, found)

        deciding = str(found[AUTHORITATIVE]).lower()

        for one in entry["accepted"]:
            if str(one[AUTHORITATIVE]).lower() == deciding:
                return Match(key, ACCEPTED, found)

        for one in entry.get("badDumps", []):
            if str(one.get(AUTHORITATIVE, "")).lower() == deciding:
                return Match(key, BAD_DUMP, found, one.get("why"))

        lengths = {one.get("size") for one in entry["accepted"]}
        if found["size"] in lengths:
            return Match(key, WRONG_CONTENT, found)

        return Match(key, WRONG_SIZE, found)


def read(path: Path | str) -> Manifest:
    return Manifest(json.loads(Path(path).read_text()))
