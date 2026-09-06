"""What the cartridge says about itself, and where it says it.

Sixteen bytes: eight of magic, two the reading calls reserved, two holding a
checksum the cartridge computed over itself, three of product code and revision,
and one carrying a region nibble and a size nibble.

Everything here was measured across 2,610 distinct images from the Master System
and Game Gear libraries, because no manufacturer document for this format has
been located and the cartridges are therefore the highest rung available.

**Where it sits.** With any copier block stripped first: at `0x7FF0` on 2,406
images, at `0x3FF0` on 8, at `0x1FF0` on 5, and at both `0x3FF0` and `0x7FF0` on
2. It is absent entirely from 189, and only 18 of those are too short to hold
one, so an image having no header is a normal state rather than a defect.

**Which candidate wins.** The largest that matches, which is what the two
ambiguous images make a real decision rather than a hypothetical one. Nothing
here settles which one the console's own boot program would read, so `anchors_in`
reports every match and a caller who cares can see the ambiguity rather than
having it hidden.

**Searching for the magic anywhere is wrong.** 141 images carry it outside the
candidates, 27 of them with no header at a candidate at all, at positions like
`0x81F0` and at bank boundaries, which is what a multi-cart or an overdump looks
like. Only the three candidates are searched.

**The two bytes the reading calls reserved are not reserved.** `00 00` appears on
1,104 images, `FF FF` on 520 and `20 20` on 395, with a long tail after that. They
are read here as neither, because nothing establishes what they mean.

**The checksum rule.** Sum every byte up to the header, then from just past the
header to the size the header declares, and keep the low sixteen bits. On retail
Master System cartridges it reproduces the stored value on 370 of the 397 that
carry a header and declare a size this reading knows. Across every Master System
image in the library, retail or not, 922 of 1,337. Translations and modified
images fall far below that, which is what changing content without recomputing
looks like.

**A Game Gear cartridge usually stores nothing.** Of the 1,084 that carry a
header, 1,001 store the value zero, and 43 reproduce the rule. So this is not a
rule that fails on the Game Gear; it is a field the Game Gear mostly leaves
empty, because its boot path does not check one. On the Master System only 29 of
1,337 store zero. `agrees` reports `False` for an empty field, and that is a
statement about the console rather than about the file, which is why nothing here
treats disagreement as a defect.
"""

from __future__ import annotations

MAGIC = b"TMR SEGA"
"""The eight bytes that mark a header."""

LENGTH = 0x10
"""How many bytes the header occupies, magic included."""

CANDIDATES = (0x7FF0, 0x3FF0, 0x1FF0)
"""The offsets a header sits at, searched largest first."""

CHECKSUM = slice(0x0A, 0x0C)
"""Where the cartridge stores the value it computed, little endian."""

REGION_AND_SIZE = 0x0F
"""One byte: the region in the high nibble, the size in the low one."""

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
"""What each region nibble is read as.

49 images carry a header whose region nibble is in no reading found so far, so it
resolves to nothing rather than to a guess.
"""

SIZES = {
    0x0: 256 * 1024,
    0x1: 512 * 1024,
    0x2: 1024 * 1024,
    0xA: 8 * 1024,
    0xB: 16 * 1024,
    0xC: 32 * 1024,
    0xD: 48 * 1024,
    0xE: 64 * 1024,
    0xF: 128 * 1024,
}
"""What each size nibble is read as.

Three images in the library declare a nibble that is not here, and those resolve
to nothing rather than to the nearest plausible size.
"""


def anchors_in(image: bytes) -> tuple[int, ...]:
    """Every candidate offset carrying the magic, largest first."""
    return tuple(where for where in CANDIDATES if image[where : where + len(MAGIC)] == MAGIC)


def anchor_of(image: bytes) -> int | None:
    """Where the header sits, or nothing when the image carries none."""
    found = anchors_in(image)
    return found[0] if found else None


def carried(image: bytes) -> int | None:
    """The value the cartridge stored, or nothing when there is no header."""
    anchor = anchor_of(image)
    if anchor is None:
        return None
    return int.from_bytes(image[anchor + CHECKSUM.start : anchor + CHECKSUM.stop], "little")


def declared_size(image: bytes) -> int | None:
    """The size the header declares, or nothing when it declares one unread."""
    anchor = anchor_of(image)
    if anchor is None:
        return None
    return SIZES.get(image[anchor + REGION_AND_SIZE] & 0x0F)


def region_of(image: bytes) -> str | None:
    """The region the header declares, or nothing when it declares one unread."""
    anchor = anchor_of(image)
    if anchor is None:
        return None
    return REGIONS.get(image[anchor + REGION_AND_SIZE] >> 4)


def checksum(image: bytes) -> int | None:
    """The value this image's own bytes produce under the rule.

    Stops at the end of the file when the declared size runs past it, because a
    header declaring more than the file holds is common in this library and
    summing to the declared size would read past the end.
    """
    anchor = anchor_of(image)
    declared = declared_size(image)
    if anchor is None or declared is None:
        return None
    upto = min(len(image), declared)
    return (sum(image[:anchor]) + sum(image[anchor + LENGTH : upto])) & 0xFFFF


def agrees(image: bytes) -> bool | None:
    """Whether the computed value matches the stored one.

    Nothing when the image carries no header or declares a size outside the
    reading, because those are different answers from a disagreement.
    """
    computed = checksum(image)
    if computed is None:
        return None
    return computed == carried(image)
