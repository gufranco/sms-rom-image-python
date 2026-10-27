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

KEPT = Path(__file__).resolve().parent.parent / "external"

NOTHING_TO_READ = 2

USAGE_ERROR = 3

INDENT = 2

READ_OUTCOMES = ("read", "run")

BOOT_PROGRAM = "bios-"

SUMMED = 0x2000

SUM_ENTRY = 4

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


def boot_sum(image: bytes) -> int:
    return sum(image[:SUMMED]) & 0xFFFF


def sum_table(suite: bytes, table: int, count: int) -> list[int]:
    return [
        int.from_bytes(suite[at : at + 2], "little")
        for at in range(table, table + count * SUM_ENTRY, SUM_ENTRY)
    ]


def identified(suite: bytes, one: dict[str, Any], boots: dict[str, bytes]) -> dict[str, Any]:
    sums = sum_table(suite, one["sumTable"], one["sumEntries"])
    found = {name: boot_sum(image) for name, image in boots.items()}
    return {
        name: {"sum": f"{value:04x}", "entry": sums.index(value) if value in sums else None}
        for name, value in found.items()
    }


def sums_judged(held: dict[str, Any], found: dict[str, bytes]) -> bool:
    good = True
    boots = {
        one["id"]: found[one["sha256"]]
        for one in held["cartridges"]
        if one["id"].startswith(BOOT_PROGRAM) and one["sha256"] in found
    }
    for one in held["cartridges"]:
        if "sumTable" not in one or one["sha256"] not in found:
            continue
        measured = identified(found[one["sha256"]], one, boots)
        same = measured == one.get("bootSums")
        print(f"{'ran' if same else 'DIFFERS'} {one['id']}: {json.dumps(measured)}")
        good = same and good
        one["bootSums"] = measured
    return good


def options(argv: Sequence[str]) -> tuple[bool, list[Path]] | None:
    write = "--write" in argv
    rest = [one for one in argv if one != "--write"]
    if any(one.startswith("--") for one in rest):
        return None
    return write, [Path(one) for one in rest]


def places_from(given: list[Path], kept: Path) -> list[Path]:
    if given:
        return given
    named = os.environ.get(PLACES, "")
    listed = [Path(one) for one in named.split(os.pathsep) if one]
    return listed or [*sorted(kept.glob("*.zip")), kept]


def judged(one: dict[str, Any], found: dict[str, Any]) -> bool:
    same = found == one.get("read")
    print(f"{'read' if same else 'DIFFERS'} {one['id']}: {json.dumps(found, sort_keys=True)}")
    return same


def main(argv: Sequence[str], where: Path | str | None = None, kept: Path = KEPT) -> int:
    parsed = options(argv)
    if parsed is None:
        print(USAGE)
        return USAGE_ERROR
    write, given = parsed
    held = record(where)
    wanted = [one for one in held["cartridges"] if one["outcome"] in READ_OUTCOMES]
    found = images(places_from(given, kept), {one["sha256"] for one in wanted})
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
    good = sums_judged(held, found) and good
    print(f"{len(found)} of {len(wanted)} pinned images read")
    if write:
        Path(where or RECORD).write_text(json.dumps(held, indent=INDENT) + "\n")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
