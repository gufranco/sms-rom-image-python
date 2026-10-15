import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from smsimage import dump, header

CORPUS = Path(__file__).resolve().parent / "corpus.json"

Combination = Mapping[str, Any]


def load(path: Path = CORPUS) -> list[Combination]:
    loaded = json.loads(path.read_text())
    return [dict(one) for one in loaded]


def _anchor_fault(recorded: Combination) -> str | None:
    anchor = recorded["anchor"]
    if anchor is None or anchor in header.CANDIDATES:
        return None
    return f"anchor {anchor:#x} is not a candidate"


def _region_fault(recorded: Combination) -> str | None:
    region = recorded["region"]
    if region is None or region in header.REGIONS.values():
        return None
    return f"region {region!r} is not one the reading knows"


def _declared_fault(recorded: Combination) -> str | None:
    declared = recorded["declared"]
    if declared is None or declared in header.SIZES.values():
        return None
    return f"declared size {declared} is not one the reading knows"


def _carried_fault(recorded: Combination) -> str | None:
    comparable = recorded["anchor"] is not None and recorded["declared"] is not None
    carried = recorded["carried"]
    if comparable and carried is None:
        return "carried None recorded where a checksum exists"
    if not comparable and carried is not None:
        return f"carried {carried} recorded where nothing can be compared"
    return None


def _form_fault(recorded: Combination) -> str | None:
    if recorded["form"] in (dump.BARE, dump.STUBBED):
        return None
    return f"form {recorded['form']!r} is not one the reader names"


CHECKS = (_anchor_fault, _region_fault, _declared_fault, _carried_fault, _form_fault)


def inconsistencies(recorded: Sequence[Combination]) -> list[str]:
    return [fault for one in recorded for check in CHECKS if (fault := check(one)) is not None]


def figures(recorded: Sequence[Combination]) -> dict[str, int]:
    weighted = [(one, int(one["count"])) for one in recorded]
    return {
        "images": sum(count for _, count in weighted),
        "at_7ff0": sum(count for one, count in weighted if one["anchor"] == header.CANDIDATES[0]),
        "agreed": sum(count for one, count in weighted if one["carried"] is True),
        "judged": sum(count for one, count in weighted if one["carried"] is not None),
    }


def report(recorded: Sequence[Combination]) -> int:
    faults = inconsistencies(recorded)
    for fault in faults:
        print(fault)
    if faults:
        return 1
    print(f"{len(recorded)} combinations replayed, every one consistent with the package")
    return 0


def main() -> int:
    return report(load())


if __name__ == "__main__":
    sys.exit(main())
