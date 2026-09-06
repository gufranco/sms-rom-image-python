"""A Sega cartridge image as a file, rather than as an address space.

Four questions, in the order they have to be asked. What did the dumping device
add or split off, and how do we get back to the bytes the console saw. What makes
this file itself, and which of those values is allowed to decide. What does the
cartridge say about itself, and how is that changed without breaking the checksum
that covers it. And when a reader supplies the wrong file, which of the several
reasons it could be wrong is it.

Master System, Game Gear and SG-1000 images are all read here, because the three
share a container and a header convention rather than a console. An SG-1000 image
usually carries no header at all, and saying so is one of the answers this package
has to be able to give.

Nothing is implemented yet. The interface below grows one module at a time, each
one settled against the cartridges before it is written.
"""

from . import errors as errors
from .errors import Malformed, NoAuthority, NoParts
from .version import VERSION

__version__ = VERSION

__all__ = [
    "Malformed",
    "NoAuthority",
    "NoParts",
    "__version__",
]
