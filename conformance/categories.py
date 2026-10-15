import hashlib
import sys
import zipfile
from collections.abc import Iterable, Mapping
from pathlib import Path

from smsimage import dump, header

SUFFIXES = (".sms", ".gg", ".sg")

RETAIL = ("1 US - A-Z", "2 Europe - A-Z", "2 Japan - A-Z", "2 Other Regions A-Z")

Groups = Mapping[str, Mapping[str, bytes]]


def grouped(path: Path) -> dict[str, dict[str, bytes]]:
    found: dict[str, dict[str, bytes]] = {}
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(SUFFIXES):
                continue
            raw = archive.read(info)
            folder = found.setdefault(info.filename.split("/")[0], {})
            folder.setdefault(hashlib.sha256(raw).hexdigest(), dump.strip_copier_stub(raw))
    return found


def tally(images: Iterable[bytes]) -> tuple[int, int, int]:
    verdicts = [header.agrees(one) for one in images]
    return (
        len(verdicts),
        sum(one is not None for one in verdicts),
        sum(one is True for one in verdicts),
    )


def retail(groups: Groups) -> dict[str, bytes]:
    return {digest: image for name in RETAIL for digest, image in groups.get(name, {}).items()}


def line(label: str, images: Iterable[bytes]) -> str:
    distinct, judged, agree = tally(images)
    return f"{label}: {distinct} distinct, {judged} judged, {agree} agree"


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python3 -m conformance.categories <archive>")
        return 2
    groups = grouped(Path(argv[0]))
    if not groups:
        print("nothing was examined, so nothing was measured")
        return 1
    for name in sorted(groups):
        print(line(name, groups[name].values()))
    print(line("retail Master System", retail(groups).values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
