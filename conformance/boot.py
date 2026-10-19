import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from smsimage import header

MANIFEST = Path(__file__).resolve().parent.parent / "artifacts.manifest.json"

DECLARED = {
    accepted["sha256"]: name
    for name, artifact in json.loads(MANIFEST.read_text())["artifacts"].items()
    for accepted in artifact["accepted"]
}

CODES = (0xA, 0xB, 0xC, 0xD, 0xE, 0xF, 0x0, 0x1, 0x2)

BANKED_CODES = (0xE, 0xF, 0x0, 0x1, 0x2)

SPAN_TAIL = 0xF0

EXPORT_REGION = 0x4


@dataclass(frozen=True, slots=True)
class Layout:
    first_span_at: int
    banks_at: int
    compared_at: int
    region_gate_at: int
    passes_after_the_first: int


V1_3 = Layout(0x034D, 0x0356, 0x02D1, 0x02F4, 0)

ALEX_KIDD = Layout(0x17FE0, 0x17FE9, 0x17F64, 0x17F87, 1)

LAYOUTS = {
    "sega-master-system-usa-v1-0-proto": Layout(0x02C7, 0x02D0, 0x024E, 0x0271, 0),
    "sega-master-system-usa-europe-v1-3": V1_3,
    "sega-master-system-usa-store-display-unit": V1_3,
    "sonic-the-hedgehog-europe": Layout(0x16D25, 0x16D2E, 0x16CA9, 0x16CCC, 0),
    "alex-kidd-in-miracle-world-usa-europe": ALEX_KIDD,
    "alex-kidd-in-miracle-world-bios-version-world-sega-ages": ALEX_KIDD,
    "hang-on-usa-europe-v3-4": Layout(0x8378, 0x8381, 0x82FC, 0x831F, 1),
    "hang-on-safari-hunt-usa-europe-brazil-en-v2-4": Layout(0x1C378, 0x1C381, 0x1C2FC, 0x1C31F, 1),
    "missile-defense-3-d-usa-europe-v4-4": Layout(0x171F2, 0x171FB, 0x17176, 0x17199, 1),
}


def span_disagreements(program: bytes, layout: Layout = V1_3) -> list[str]:
    found = []
    for index, code in enumerate(CODES):
        passes = program[layout.first_span_at + index] - layout.passes_after_the_first
        read = passes << 8 | SPAN_TAIL
        if read != header.FIRST_SPAN[code]:
            found.append(
                f"the first span for size code {code:#x} is {read:#x}, "
                f"not {header.FIRST_SPAN[code]:#x}"
            )
    return found


def bank_disagreements(program: bytes, layout: Layout = V1_3) -> list[str]:
    found = []
    for index, code in enumerate(BANKED_CODES):
        read = program[layout.banks_at + index]
        if read != header.BANKS_FROM_THE_THIRD[code]:
            found.append(
                f"size code {code:#x} adds {read} banks, not {header.BANKS_FROM_THE_THIRD[code]}"
            )
    return found


def gate_disagreements(program: bytes, layout: Layout = V1_3) -> list[str]:
    found = []
    if program[layout.compared_at] != len(header.MAGIC):
        found.append(f"it compares {program[layout.compared_at]} bytes, not {len(header.MAGIC)}")
    gated = program[layout.region_gate_at] >> 4
    if gated != EXPORT_REGION:
        found.append(f"it checks the sum only for region {gated:#x}, not {EXPORT_REGION:#x}")
    return found


def disagreements(program: bytes, layout: Layout = V1_3) -> list[str]:
    return (
        span_disagreements(program, layout)
        + bank_disagreements(program, layout)
        + gate_disagreements(program, layout)
    )


def judged(path: str) -> int:
    program = Path(path).read_bytes()
    name = DECLARED.get(hashlib.sha256(program).hexdigest())
    if name is None:
        print(f"{path} is not a boot program the manifest declares")
        return 1
    if name not in LAYOUTS:
        print(f"{name} runs no checksum, so there is no table to read")
        return 1
    found = disagreements(program, LAYOUTS[name])
    for one in found:
        print(f"{name}: {one}")
    if found:
        return 1
    print(
        f"{name} agrees with the package: {len(CODES)} spans, "
        f"{len(BANKED_CODES)} bank counts, an {len(header.MAGIC)}-byte compare, "
        "the sum checked only for region 4"
    )
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python3 -m conformance.boot <export boot program> [program ...]")
        return 2
    return max(judged(one) for one in argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
