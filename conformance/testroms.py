import hashlib
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from conformance import census
from smsimage import dump, header

RECORD = Path(__file__).resolve().parent / "testroms.json"

PLACES = "TEST_CARTRIDGES"

NOTHING_TO_READ = 2

USAGE_ERROR = 3

INDENT = 2

USAGE = "usage: python3 -m conformance.testroms [--write] [image, folder or zip ...]"


def record(where: Path | str | None = None) -> dict[str, Any]:
    held = json.loads(Path(where or RECORD).read_text())
    assert isinstance(held, dict), "the record does not hold an object"
    return held


def reading(raw: bytes) -> dict[str, Any]:
    image = dump.strip_copier_stub(raw)
    return {
        **census.observe(raw),
        "stored": header.carried(image),
        "computed": header.checksum(image),
    }


def images(places: Sequence[Path], wanted: set[str]) -> dict[str, bytes]:
    found: dict[str, bytes] = {}
    for place in places:
        for raw in census.images_in(place):
            digest = hashlib.sha256(raw).hexdigest()
            if digest in wanted:
                found[digest] = raw
    return found


def options(argv: Sequence[str]) -> tuple[bool, list[Path]] | None:
    write = "--write" in argv
    rest = [one for one in argv if one != "--write"]
    if any(one.startswith("--") for one in rest):
        return None
    return write, [Path(one) for one in rest]


def places_from(given: list[Path]) -> list[Path]:
    if given:
        return given
    named = os.environ.get(PLACES, "")
    return [Path(one) for one in named.split(os.pathsep) if one]


def judged(one: dict[str, Any], found: dict[str, Any]) -> bool:
    same = found == one.get("read")
    print(f"{'read' if same else 'DIFFERS'} {one['id']}: {json.dumps(found, sort_keys=True)}")
    return same


def main(argv: Sequence[str], where: Path | str | None = None) -> int:
    parsed = options(argv)
    if parsed is None:
        print(USAGE)
        return USAGE_ERROR
    write, given = parsed
    held = record(where)
    wanted = [one for one in held["cartridges"] if one["outcome"] == "read"]
    found = images(places_from(given), {one["sha256"] for one in wanted})
    if not found:
        print(f"SKIPPED none of the {len(wanted)} pinned images is on this machine")
        return NOTHING_TO_READ
    good = True
    for one in wanted:
        if one["sha256"] not in found:
            print(f"SKIPPED {one['id']}: not on this machine")
            continue
        measured = reading(found[one["sha256"]])
        good = judged(one, measured) and good
        one["read"] = measured
    print(f"{len(found)} of {len(wanted)} pinned images read")
    if write:
        Path(where or RECORD).write_text(json.dumps(held, indent=INDENT) + "\n")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
