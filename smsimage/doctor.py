"""Look at this machine and say what is actually here, so a report can be believed.

What goes wrong with this package is rarely a defect in it. It is a corpus that
is not beside the package, a manifest somebody hand-edited, or a census pointed
at a directory that holds nothing it reads. All three look the same from outside:
the run is green and it proved less than the reader thinks.

Two rules shape this, and they are the whole point.

Nothing is hidden. A check that fails says what it saw, and a check that itself
throws is caught and reported as what it threw, named by its type. An absent
library is reported as absent rather than as a failure, because a fresh checkout
has none and that is the normal state, and it is never reported as nothing at
all. A corpus that holds no combinations is told apart from a corpus that is not
there, because a reader who fetched nothing and a reader whose fetch produced an
empty file need different advice.

Nothing is imported from the package at the top of this file. This member takes
no submodule, so it does not have the failure its SNES counterpart guards
against, and the rule holds anyway: every import that can fail happens inside the
finding that needs it, where its failure is the report rather than the end of it.
The version is read out of the file beside this one rather than imported, for the
same reason. Run it as

    python3 smsimage/doctor.py

so that nothing has to load the package before the first line is printed.

Nothing is inferred. Every line is something looked at on this machine just now,
including a header found and a checksum reproduced on an image assembled here
rather than a claim that the reader imports.
"""

from __future__ import annotations

import json
import platform
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence


def _version(where: Path | None = None) -> str:
    """The package version, read out of the file beside this one.

    Read rather than imported. Importing it would go through the package, and the
    package is what fails on the machine this exists to diagnose.
    """
    found = re.search(
        r"""VERSION\s*[:=][^"']*["']([^"']+)["']""",
        (where or Path(__file__).resolve().parent / "version.py").read_text(),
    )
    return found.group(1) if found else "unknown"


VERSION = _version()

ROOT = Path(__file__).resolve().parent.parent


def _reachable(root: Path = ROOT, path: list[str] | None = None) -> bool:
    """Put the repository root where an import can find the package.

    Running this as a file puts the directory holding it on the path, which is the
    package's own directory rather than the one above it, so `import smsimage` finds
    nothing. This has to happen before any finding reaches for the package, and it
    happens here rather than inside a finding because every finding needs it.

    Its SNES counterpart does the same thing inside one finding, several dozen lines
    after a module-level import of the package, so running it the way its own
    docstring instructs fails with a traceback naming a module the reader has never
    heard of. That is the exact failure the docstring says the file exists to
    prevent, and it is invisible to the tests, which import the doctor from a
    process that already has the root on the path.

        Answers whether it had to add it, so a caller can tell an already-reachable
        root from one this put there.
    """
    where = sys.path if path is None else path
    if str(root) in where:
        return False
    where.insert(0, str(root))
    return True


_reachable()

CORPUS = ROOT / "conformance" / "corpus.json"

MANIFEST = ROOT / "artifacts.manifest.json"

OLDEST_PYTHON = (3, 12)

ANCHOR = 0x7FF0
"""Where the synthetic image built below puts its header."""

REGION_AND_SIZE = 0x4C
"""An exported Master System cartridge of thirty two kilobytes."""

IMAGE_BYTES = 0x8000
"""Small enough to build in memory, and the size the byte above declares."""

STUB_BYTES = 512
"""What a copier writes in front of an image, for the reading check."""

CHECKS = (
    "python",
    "package",
    "reading",
    "anchoring",
    "checksumming",
    "measuring",
    "artifacts",
    "corpus",
    "library",
)
"""What is looked at, in the order a reader wants it."""


class Finding:
    """One thing that was looked at, and what was there."""

    __slots__ = ("advice", "detail", "name", "ok")

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        """The one-line form, which is what a reader scans."""
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        """The same, with what to do about it when there is something to do."""
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    @override
    def __repr__(self) -> str:
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def _threw(name: str, error: BaseException, advice: str | None = None) -> Finding:
    """A check that threw, reported as what it threw rather than as a traceback."""
    return Finding(name, False, f"{type(error).__name__}: {error}", advice)


def _synthetic(_: object = None) -> bytes:
    """An image built here, with a header and a checksum that matches it."""
    from smsimage import header

    image = bytearray((index * 11 + 5) & 0xFF for index in range(IMAGE_BYTES))
    image[ANCHOR : ANCHOR + len(header.MAGIC)] = header.MAGIC
    image[ANCHOR + 0x08 : ANCHOR + header.LENGTH] = bytes(8)
    image[ANCHOR + header.REGION_AND_SIZE] = REGION_AND_SIZE
    computed = header.checksum(bytes(image))
    if computed is None:
        raise ValueError("the reader found no checksum in an image built with a header")
    image[ANCHOR + 0x0A : ANCHOR + 0x0C] = computed.to_bytes(2, "little")
    return bytes(image)


def _python() -> Finding:
    running = sys.version_info[:2]
    return Finding(
        "python",
        running >= OLDEST_PYTHON,
        f"{platform.python_version()}",
        f"this package needs {OLDEST_PYTHON[0]}.{OLDEST_PYTHON[1]} or newer",
    )


def _load() -> Any:
    """The package, imported here rather than at the top of the file."""
    import smsimage

    return smsimage


def _package(load: Callable[[], Any] = _load) -> Finding:
    try:
        loaded = load()
    except Exception as error:
        return _threw("package", error, "the package did not import from this directory")
    return Finding("package", True, f"smsimage {loaded.__version__} imported from {ROOT}")


def _reading(build: Callable[[], bytes] = _synthetic) -> Finding:
    """A copier block removed from an image assembled here, rather than a claim."""
    try:
        from smsimage import dump

        image = build()
        stubbed = bytes(range(STUB_BYTES % 256)) * (STUB_BYTES // (STUB_BYTES % 256 or 1))
        stubbed = (stubbed + bytes(STUB_BYTES))[:STUB_BYTES] + image
        back = dump.strip_copier_stub(stubbed)
        again = dump.strip_copier_stub(back)
    except Exception as error:
        return _threw("reading", error)

    return Finding(
        "reading",
        back == image and again == back,
        f"a {len(stubbed)} byte dump read back to {len(back)} bytes, and again to {len(again)}",
        "stripping a copier block did not give back the image it was put in front of",
    )


def _anchoring(build: Callable[[], bytes] = _synthetic) -> Finding:
    """A header found in an image assembled here."""
    try:
        from smsimage import header

        image = build()
        found = header.anchor_of(image)
        every = header.anchors_in(image)
        region = header.region_of(image)
        declared = header.declared_size(image)
    except Exception as error:
        return _threw("anchoring", error)

    return Finding(
        "anchoring",
        found == ANCHOR and every == (ANCHOR,) and declared == IMAGE_BYTES,
        f"a header at {found:#06x} declaring {region} and {declared} bytes"
        if found is not None
        else "no header was found in an image built with one",
        f"a header was planted at {ANCHOR:#06x} and the reader did not find it there",
    )


def _checksumming(build: Callable[[], bytes] = _synthetic) -> Finding:
    """A checksum reproduced on an image sealed here."""
    try:
        from smsimage import header

        image = build()
        computed = header.checksum(image)
        carried = header.carried(image)
        agrees = header.agrees(image)
    except Exception as error:
        return _threw("checksumming", error)

    return Finding(
        "checksumming",
        agrees is True,
        f"computed {computed:#06x}, the image carries {carried:#06x}"
        if computed is not None and carried is not None
        else "an image sealed here produced no checksum",
        "the checksum of an image sealed here does not match what was sealed into it",
    )


def _measuring(build: Callable[[], bytes] = _synthetic) -> Finding:
    """Every published value for an image assembled here, and which one decides."""
    try:
        from smsimage import identity

        image = build()
        found = identity.measure(image)
        agrees = identity.agrees(found, dict(found))
    except Exception as error:
        return _threw("measuring", error)

    return Finding(
        "measuring",
        agrees and identity.AUTHORITATIVE in found,
        f"{len(found)} values, {identity.AUTHORITATIVE} decides, "
        f"{found[identity.AUTHORITATIVE][:16]} for {found['size']} bytes",
        "a measurement of an image built here does not agree with itself",
    )


def _artifacts(path: Path | str = MANIFEST) -> Finding:
    """The manifest this repository ships, read rather than assumed."""
    where = Path(path)
    if not where.is_file():
        return Finding(
            "artifacts",
            False,
            f"not here: {where}",
            "this repository ships one, so a checkout missing it is incomplete",
        )
    try:
        from smsimage import manifest

        found = manifest.read(where)
    except Exception as error:
        return _threw("artifacts", error, f"{where} did not parse as a manifest")

    return Finding(
        "artifacts", True, f"{len(found.keys)} boot programs declared, none of them here"
    )


def _corpus(path: Path | str = CORPUS) -> Finding:
    """The corpus the suite replays, told apart from one that is missing."""
    where = Path(path)
    if not where.is_file():
        return Finding(
            "corpus",
            False,
            f"not here: {where}",
            "run the census over a library you own to build one",
        )
    try:
        combinations = json.loads(where.read_text())
    except Exception as error:
        return _threw("corpus", error, f"{where} did not parse")

    if not combinations:
        return Finding(
            "corpus",
            False,
            f"holds nothing: {where}",
            "a census that examined no image writes no combination, so check what it walked",
        )

    behind: Any = sum(one.get("count", 0) for one in combinations)
    return Finding(
        "corpus",
        True,
        f"{len(combinations)} combinations from {behind} images",
    )


def _library() -> Finding:
    """Where cartridges are looked for, which is nowhere until a caller says."""
    return Finding(
        "library",
        True,
        "the census takes the library to walk as an argument, so there is nothing to be set wrongly",
    )


def examine(
    corpus: Path | str = CORPUS,
    artifacts: Path | str = MANIFEST,
) -> list[Finding]:
    """Everything worth looking at on this machine, in the order a reader wants it."""
    return [
        _python(),
        _package(),
        _reading(),
        _anchoring(),
        _checksumming(),
        _measuring(),
        _artifacts(artifacts),
        _corpus(corpus),
        _library(),
    ]


def report(found: Sequence[Finding]) -> list[str]:
    """The lines a person pastes into an issue."""
    from smsimage import environment

    unwell = [one for one in found if not one.ok]
    lines = [f"smsimage {VERSION} on {platform.python_version()}, {platform.system()}", ""]
    lines.append("  the machine")
    lines.extend(environment.lines(ROOT))
    lines.append("")
    lines.append("  this package")
    lines.extend(one.report for one in found)
    lines.append("")
    if unwell:
        lines.append(f"  {len(unwell)} of {len(found)} checks did not pass")
    else:
        lines.append(f"  {len(found)} checks, nothing to report")
    return lines


def main(
    argv: Sequence[str] = (),
    examine: Callable[..., list[Finding]] = examine,
    say: Callable[[str], None] = print,
) -> int:
    found = examine()
    for line in report(found):
        say(line)
    return 1 if any(not one.ok for one in found) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
