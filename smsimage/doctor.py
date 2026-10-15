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
    found = re.search(
        r"""VERSION\s*[:=][^"']*["']([^"']+)["']""",
        (where or Path(__file__).resolve().parent / "version.py").read_text(),
    )
    return found.group(1) if found else "unknown"


VERSION = _version()

ROOT = Path(__file__).resolve().parent.parent


def _reachable(root: Path = ROOT, path: list[str] | None = None) -> bool:
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

REGION_AND_SIZE = 0x4C

IMAGE_BYTES = 0x8000

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


class Finding:
    __slots__ = ("advice", "detail", "name", "ok")

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    @override
    def __repr__(self) -> str:
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def _threw(name: str, error: BaseException, advice: str | None = None) -> Finding:
    return Finding(name, False, f"{type(error).__name__}: {error}", advice)


def _synthetic(_: object = None) -> bytes:
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
    import smsimage

    return smsimage


def _package(load: Callable[[], Any] = _load) -> Finding:
    try:
        loaded = load()
    except Exception as error:
        return _threw("package", error, "the package did not import from this directory")
    return Finding("package", True, f"smsimage {loaded.__version__} imported from {ROOT}")


def _reading(build: Callable[[], bytes] = _synthetic) -> Finding:
    try:
        from smsimage import dump

        image = build()
        stubbed = bytes(dump.COPIER_BLOCK) + image
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
    return Finding(
        "library",
        True,
        "the census takes the library to walk as an argument, so there is nothing to be set wrongly",
    )


def examine(
    corpus: Path | str = CORPUS,
    artifacts: Path | str = MANIFEST,
) -> list[Finding]:
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
