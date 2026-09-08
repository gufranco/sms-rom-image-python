"""What a project expects a reader to supply, and which wrong a wrong file is.

This package reads files it cannot ship. A boot program, a cartridge library, a
corpus: every one of them is absent on somebody's machine, and the difference
between a useful refusal and a useless one is whether it says which kind of wrong
happened.

Five answers, and the four unhappy ones are the reason this module exists:

- **accepted**, the deciding digest matches something the project declared.
- **a known bad dump**, declared separately so a corrupt file is diagnosed as
  corrupt rather than as the wrong file. A reader who knows their dump is short
  looks for a better one; a reader told only that it does not match goes looking
  for the wrong thing.
- **the right length, the wrong content**, which is a modified or patched file
  rather than a different one, and says to check what modified it.
- **a length nothing declares**, which is a different file entirely.
- **undeclared**, the project never said anything about this artifact.

The deciding digest is SHA-256 and only SHA-256. The other values are published
so a reader can find the row in a database built before anybody keyed one on it,
and a manifest that declares them without the deciding one is refused at read
time rather than silently graded on whichever weaker value is present.

Nothing here says where to obtain anything. A tool that fetches on a reader's
behalf is a tool that decides for them what they are allowed to be given.
"""

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
"""Every answer a match can give, in the order a reader meets them."""


class Match:
    """What a supplied file turned out to be."""

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
    """What a project declares about the files a reader has to supply."""

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
        """Every artifact this project declares, by the key it declares it under."""
        return tuple(self._artifacts)

    def name(self, key: str) -> str:
        """What a reader would call this artifact, or its key when unnamed."""
        entry = self._artifacts.get(key, {})
        named = entry.get("name")
        return str(named) if named else key

    def match(self, key: str, data: bytes) -> Match:
        """Which of the five this file is, for the artifact declared under that key."""
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
    """The manifest a project ships, read from the file it ships it in."""
    return Manifest(json.loads(Path(path).read_text()))
