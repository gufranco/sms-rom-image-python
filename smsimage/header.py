from __future__ import annotations

MAGIC = b"TMR SEGA"

LENGTH = 0x10

CANDIDATES = (0x7FF0, 0x3FF0, 0x1FF0)

CHECKSUM = slice(0x0A, 0x0C)

REGION_AND_SIZE = 0x0F

SMS_JAPAN = "sms-japan"
SMS_EXPORT = "sms-export"
GG_JAPAN = "gg-japan"
GG_EXPORT = "gg-export"
GG_INTERNATIONAL = "gg-international"

REGIONS = {
    0x3: SMS_JAPAN,
    0x4: SMS_EXPORT,
    0x5: GG_JAPAN,
    0x6: GG_EXPORT,
    0x7: GG_INTERNATIONAL,
}

KILOBYTE = 1024

SIZES = {
    0x0: 256 * KILOBYTE,
    0x1: 512 * KILOBYTE,
    0x2: 1024 * KILOBYTE,
    0xA: 8 * KILOBYTE,
    0xB: 16 * KILOBYTE,
    0xC: 32 * KILOBYTE,
    0xD: 48 * KILOBYTE,
    0xE: 64 * KILOBYTE,
    0xF: 128 * KILOBYTE,
}

LOW_SIXTEEN_BITS = 0xFFFF


def _region_code(region_and_size: int) -> int:
    return region_and_size >> 4


def _size_code(region_and_size: int) -> int:
    return region_and_size & 0x0F


def anchors_in(image: bytes) -> tuple[int, ...]:
    return tuple(where for where in CANDIDATES if image[where : where + len(MAGIC)] == MAGIC)


def anchor_of(image: bytes) -> int | None:
    largest_first = anchors_in(image)
    return largest_first[0] if largest_first else None


def carried(image: bytes) -> int | None:
    anchor = anchor_of(image)
    if anchor is None:
        return None
    return int.from_bytes(image[anchor + CHECKSUM.start : anchor + CHECKSUM.stop], "little")


def declared_size(image: bytes) -> int | None:
    anchor = anchor_of(image)
    if anchor is None:
        return None
    return SIZES.get(_size_code(image[anchor + REGION_AND_SIZE]))


def region_of(image: bytes) -> str | None:
    anchor = anchor_of(image)
    if anchor is None:
        return None
    return REGIONS.get(_region_code(image[anchor + REGION_AND_SIZE]))


def checksum(image: bytes) -> int | None:
    anchor = anchor_of(image)
    declared = declared_size(image)
    if anchor is None or declared is None:
        return None
    summed_until = min(len(image), declared)
    before_the_header = sum(image[:anchor])
    after_the_header = sum(image[anchor + LENGTH : summed_until])
    return (before_the_header + after_the_header) & LOW_SIXTEEN_BITS


def agrees(image: bytes) -> bool | None:
    computed = checksum(image)
    if computed is None:
        return None
    return computed == carried(image)
