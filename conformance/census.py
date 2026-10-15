import collections
import hashlib
import json
import sys
import zipfile
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from smsimage import dump, header, identity

SUFFIXES = (".sms", ".gg", ".sg")

IDEMPOTENT_STRIP = "stripping twice changes nothing the second time"
ANCHOR_IS_A_CANDIDATE = "an anchor is one of the offsets a header is looked for at"
MAGIC_AT_THE_ANCHOR = "the magic really sits where the anchor says"
CHECKSUM_IN_RANGE = "a computed checksum fits in sixteen bits"
AGREEMENT_FOLLOWS_A_CHECKSUM = "agreement is answered exactly when a checksum exists"
MEASUREMENT_IS_STABLE = "measuring the same bytes twice gives the same values"

PROPERTIES = (
    IDEMPOTENT_STRIP,
    ANCHOR_IS_A_CANDIDATE,
    MAGIC_AT_THE_ANCHOR,
    CHECKSUM_IN_RANGE,
    AGREEMENT_FOLLOWS_A_CHECKSUM,
    MEASUREMENT_IS_STABLE,
)

OBSERVATIONS = ("carried",)

CORPUS = Path(__file__).resolve().parent / "corpus.json"


def images_in(where: Path) -> Iterator[bytes]:
    if where.is_dir():
        for path in sorted(where.rglob("*")):
            if path.is_file() and path.suffix.lower() in SUFFIXES:
                yield path.read_bytes()
        return
    if where.is_file() and where.suffix.lower() == ".zip":
        with zipfile.ZipFile(where) as bundle:
            for entry in bundle.infolist():
                if entry.is_dir():
                    continue
                if Path(entry.filename).suffix.lower() in SUFFIXES:
                    yield bundle.read(entry)
        return
    if where.is_file() and where.suffix.lower() in SUFFIXES:
        yield where.read_bytes()


def broken_properties(raw: bytes) -> list[str]:
    broken = []
    image = dump.strip_copier_stub(raw)

    if dump.strip_copier_stub(image) != image:
        broken.append(IDEMPOTENT_STRIP)

    anchor = header.anchor_of(image)
    if anchor is not None and anchor not in header.CANDIDATES:
        broken.append(ANCHOR_IS_A_CANDIDATE)

    if anchor is not None and image[anchor : anchor + len(header.MAGIC)] != header.MAGIC:
        broken.append(MAGIC_AT_THE_ANCHOR)

    computed = header.checksum(image)
    if computed is not None and not 0 <= computed <= 0xFFFF:
        broken.append(CHECKSUM_IN_RANGE)

    if (computed is None) != (header.agrees(image) is None):
        broken.append(AGREEMENT_FOLLOWS_A_CHECKSUM)

    if identity.measure(image) != identity.measure(image):
        broken.append(MEASUREMENT_IS_STABLE)

    return broken


def observe(raw: bytes) -> Mapping[str, Any]:
    image = dump.strip_copier_stub(raw)
    return {
        "form": dump.form(raw),
        "size": len(image),
        "anchor": header.anchor_of(image),
        "region": header.region_of(image),
        "declared": header.declared_size(image),
        "carried": header.agrees(image),
    }


def take(paths: list[Path]) -> Mapping[str, Any]:
    seen: set[str] = set()
    listings = 0
    broken: collections.Counter[str] = collections.Counter()
    combinations: collections.Counter[tuple[Any, ...]] = collections.Counter()

    for where in paths:
        for raw in images_in(where):
            listings += 1
            digest = hashlib.sha256(raw).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            for name in broken_properties(raw):
                broken[name] += 1
            found = observe(raw)
            combinations[tuple(found[key] for key in sorted(found))] += 1

    keys = sorted(observe(b"")) if combinations else []
    corpus = [
        {**dict(zip(keys, values, strict=True)), "count": count}
        for values, count in sorted(combinations.items(), key=lambda one: -one[1])
    ]

    return {
        "listings": listings,
        "distinct": len(seen),
        "broken": dict(broken),
        "corpus": corpus,
    }


def main(argv: list[str], into: Path = CORPUS) -> int:
    if not argv:
        print("usage: python3 -m conformance.census <path> [path ...]")
        return 2

    paths = [Path(one) for one in argv]
    absent = [one for one in paths if not one.exists()]
    for one in absent:
        print(f"absent: {one}")

    taken = take([one for one in paths if one.exists()])

    print(f"archive entries and files read: {taken['listings']}")
    print(f"distinct images:                {taken['distinct']}")
    print(f"duplicate listings:             {taken['listings'] - taken['distinct']}")

    if not taken["distinct"]:
        print("nothing was examined, so nothing was checked")
        return 1 if absent else 0

    print()
    print(
        f"properties held on {taken['distinct'] - sum(taken['broken'].values())} of {taken['distinct']}"
    )
    for name in PROPERTIES:
        count = taken["broken"].get(name, 0)
        print(f"  {'broken' if count else 'held  '}  {name}" + (f"  on {count}" if count else ""))

    agreed = sum(one["count"] for one in taken["corpus"] if one["carried"] is True)
    judged = sum(one["count"] for one in taken["corpus"] if one["carried"] is not None)
    print()
    print(
        f"carried    true of {agreed} of {judged} images with a header and a size this reading knows"
    )
    print(
        f"           the remaining {taken['distinct'] - judged} carry no header, or declare a size it does not"
    )
    print()
    print(f"distinct combinations: {len(taken['corpus'])}")

    into.write_text(json.dumps(taken["corpus"], indent=1) + "\n")
    print(f"corpus written, {len(taken['corpus'])} combinations, no content and no title")
    return 1 if taken["broken"] or absent else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
