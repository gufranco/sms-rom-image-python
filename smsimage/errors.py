"""Everything this package raises, in one place.

One module so a caller can see the whole set at once, and so `except` has
somewhere to import from. It imports nothing from the rest of the package, which
is what keeps it from ever closing a cycle: everything here raises, so everything
here imports this, and an import running the other way would make the order
modules happen to load in decide whether the package works at all.

Nothing here is defined ahead of something raising it. The SNES member publishes
a refusal for a split dump with no numbered part, and this one does not, because
no split dump was found across 5,063 archive entries in the two libraries this
was measured on: every file carries a whole image. An exception nothing raises is
an interface promise with no behaviour behind it, and adding one the day a split
dump turns up costs less than keeping one that never fires.
"""

from __future__ import annotations


class NoAuthority(Exception):
    """Nothing in the record can decide what this file is.

    A file is identified by several digests and exactly one of them decides. A
    record that publishes the others and not that one publishes decoration, so
    the refusal names the gap rather than falling back to a weaker digest that
    happens to be present.
    """


class Malformed(Exception):
    """The manifest is not a manifest.

    Raised where the file is read rather than where a field is missed, so a
    caller learns the whole document is unusable in one place instead of meeting
    a different failure per artifact. The message says which part of the shape is
    absent.
    """
