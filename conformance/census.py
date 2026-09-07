"""Take a census of a cartridge library you own, and check this package on all of it.

A header is sixteen bytes in which the cartridge describes how it is built: where
it sits, which region it declares, how much ROM it carries, and a checksum it
computed over itself. Those are facts about a physical object. They are not
authored, they carry none of the game, and a count of how many cartridges share a
combination is a measurement rather than a copy.

So this reads those bytes from every image in a library and writes down the
distinct combinations it found. It records no title, because a title is the one
header field that is a name rather than a measurement, and the corpus it produces
holds nothing from which any part of any cartridge could be reconstructed.

Everything is keyed on the digest of the image bytes. A library organised by
series lists the same image several times, and in the one this was built against
5,111 archive entries were 2,610 distinct images. Counting filenames would have
put nearly half of every figure out.

**Properties gate. Observations report.** A property must hold on every image,
whatever it is, and a failure is a defect in this package. An observation is
measured and printed without gating, because the thing it measures is a statement
about the cartridge as much as about the code.

The one that matters is `carried`: whether the checksum this package computes is
the one the cartridge already stored. It is the only check here that asks the
artifact rather than asking the code whether it agrees with itself, and it is
therefore the only one a rule wrong the same way every time cannot pass. Making it
a property would turn every modified image into a failure and drown the handful of
retail cartridges that genuinely disagree: translations reproduce it on 67 of 214
and modified images on 8 of 43, while retail Master System cartridges reach 370 of
397.

An image whose header cannot be found is counted as carrying none rather than
guessed at. 189 in that library carry none, only 18 of them too short to hold one,
and inventing a header for the rest would put fiction into a corpus of facts.
"""

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
"""What must hold on every image, whatever it is. A failure here is a defect.

One that was here and is not any more: that a stripped image is a whole number
of kilobytes. A file is classified stubbed only when its length is a multiple of
1,024 plus 512, so removing 512 always leaves a multiple of 1,024. No input can
break it. A property nothing can violate is a line in a report rather than a
check, and the test that tried to break it is what showed that.
"""

OBSERVATIONS = ("carried",)
"""What is measured and reported without gating the verdict."""

CORPUS = Path(__file__).resolve().parent / "corpus.json"
"""Where the combinations are written, so a suite can replay them with no library."""


def images_in(where: Path) -> Iterator[bytes]:
    """Every cartridge image under a directory, or inside an archive."""
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
    """Every property this image breaks, named. Empty is the expected answer."""
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
    """What this image is, in the fields a corpus of facts may hold."""
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
    """Walk every path, and report what was found rather than whether it passed."""
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
