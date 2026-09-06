"""Everything this package raises, in one place.

One module so a caller can see the whole set at once, and so `except` has
somewhere to import from. It imports nothing from the rest of the package, which
is what keeps it from ever closing a cycle: everything here raises, so everything
here imports this, and an import running the other way would make the order
modules happen to load in decide whether the package works at all.
"""

from __future__ import annotations


class NoParts(Exception):
    """The folder holds no numbered part of a split dump.

    Raised rather than answered with an empty image, because those are different
    answers to different questions. An empty image says the dump was empty; this
    says there was no dump.
    """


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
