import collections
import hashlib
import sys
from collections.abc import Iterable
from pathlib import Path

from conformance import census
from smsimage import dump, header

PRINTED_TAIL = b"  "

LOW_SIXTEEN_BITS = 0xFFFF

SHOWN = 3


def carries_the_printed_tail(image: bytes) -> bool | None:
    anchor = header.anchor_of(image)
    if anchor is None:
        return None
    start = anchor + len(header.MAGIC)
    return image[start : start + len(PRINTED_TAIL)] == PRINTED_TAIL


def document_rule_agrees(image: bytes) -> bool | None:
    anchor = header.anchor_of(image)
    declared = header.declared_size(image)
    if anchor is None or declared is None:
        return None
    end = min(len(image), declared)
    held = image[anchor + header.CHECKSUM.start : anchor + header.CHECKSUM.stop]
    left_out = sum(held) if anchor + header.CHECKSUM.stop <= end else 0
    return (sum(image[:end]) - left_out) & LOW_SIXTEEN_BITS == header.carried(image)


def tails(images: Iterable[bytes]) -> list[tuple[str, int]]:
    counted: collections.Counter[str] = collections.Counter()
    for one in images:
        anchor = header.anchor_of(one)
        if anchor is None:
            continue
        start = anchor + len(header.MAGIC)
        counted[one[start : start + len(PRINTED_TAIL)].hex()] += 1
    return counted.most_common()


def distinct_images(paths: Iterable[Path]) -> list[bytes]:
    seen: dict[str, bytes] = {}
    for where in paths:
        for raw in census.images_in(where):
            seen.setdefault(hashlib.sha256(raw).hexdigest(), dump.strip_copier_stub(raw))
    return list(seen.values())


def tally(images: Iterable[bytes]) -> dict[str, int]:
    held = list(images)
    tails = [carries_the_printed_tail(one) for one in held]
    rules = [document_rule_agrees(one) for one in held]
    stored = [header.carried(one) for one in held]
    return {
        "anchored": sum(one is not None for one in tails),
        "withTheTwoSpaces": sum(one is True for one in tails),
        "judged": sum(one is not None for one in rules),
        "documentRuleAgrees": sum(one is True for one in rules),
        "storesZero": sum(one == 0 for one in stored),
        "packageRuleAgrees": sum(header.agrees(one) is True for one in held),
    }


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python3 -m conformance.divergences <library> [library ...]")
        return 2
    images = distinct_images([Path(one) for one in argv])
    counted = tally(images)
    if not counted["anchored"]:
        print("nothing was examined, so nothing was measured")
        return 1
    print(f"the two printed spaces: {counted['withTheTwoSpaces']} of {counted['anchored']}")
    print(f"the manual's checksum rule: {counted['documentRuleAgrees']} of {counted['judged']}")
    print(f"storing zero: {counted['storesZero']} of {counted['anchored']}")
    print(f"the package's checksum rule: {counted['packageRuleAgrees']} of {counted['judged']}")
    for tail, count in tails(images)[:SHOWN]:
        print(f"after the magic: {tail} on {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
