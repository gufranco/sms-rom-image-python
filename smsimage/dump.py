"""What the dumping device added, and how to get back to the bytes the console saw.

A cartridge is a whole number of kilobytes. A copier writes its own 512-byte
block in front of the image it took, so a file carrying one is a whole number of
kilobytes plus 512, and nothing else on a shelf of dumps has that shape.

That rule was measured rather than assumed. Across 2,610 distinct images in the
Master System and Game Gear libraries, 17 have a length that is a multiple of
1,024 plus 512. Every one of the 17 carries no header at any of the offsets a
header sits at, and 16 of them carry one at exactly 512 bytes past the largest of
those offsets. So the length identifies the block and stripping it puts the
header back where a reader expects it.

The seventeenth is not a counterexample. It is a stubbed file whose cartridge
carried no header at all, which is a state 205 images in the same library are in
without a copier having touched them.

The rule is a length rule and says so. It cannot see a copier that wrote a block
of some other size, and it would misread an image that is genuinely a multiple of
1,024 plus 512 bytes long. No such image was found, and the check that would
notice one is the census rather than this module.
"""

from __future__ import annotations

from pathlib import Path

STUB = 512
"""The block a copier writes in front of the image it took."""

ALIGNMENT = 1024
"""The unit a cartridge is a whole number of."""

BARE = "bare"
"""The file is the image, with nothing in front of it."""

STUBBED = "stubbed"
"""The file is a copier block followed by the image."""


def form(data: bytes) -> str:
    """Which of the two shapes this file has.

    A file no longer than the block itself is bare whatever its length says,
    because a block with no image behind it is not a dump of anything.
    """
    if len(data) <= STUB:
        return BARE
    return STUBBED if len(data) % ALIGNMENT == STUB else BARE


def strip_copier_stub(data: bytes) -> bytes:
    """The image the console saw, with any copier block removed.

    Safe to run twice: what comes back is bare, so a second call finds nothing
    to remove.
    """
    return data[STUB:] if form(data) == STUBBED else data


def read(path: Path | str) -> bytes:
    """The image in a file, with any copier block removed."""
    return strip_copier_stub(Path(path).read_bytes())
