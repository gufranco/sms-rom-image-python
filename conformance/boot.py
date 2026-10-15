import hashlib
import json
import sys
from pathlib import Path

from smsimage import header

MANIFEST = Path(__file__).resolve().parent.parent / "artifacts.manifest.json"

READ_FROM = "sega-master-system-usa-europe-v1-3"

DECLARED = json.loads(MANIFEST.read_text())["artifacts"][READ_FROM]["accepted"][0]["sha256"]

CODES = (0xA, 0xB, 0xC, 0xD, 0xE, 0xF, 0x0, 0x1, 0x2)

BANKED_CODES = (0xE, 0xF, 0x0, 0x1, 0x2)

FIRST_SPAN_AT = 0x034D

BANKS_AT = 0x0356

COMPARED_AT = 0x02D1

REGION_GATE_AT = 0x02F4

SPAN_TAIL = 0xF0

EXPORT_REGION = 0x4


def span_disagreements(program: bytes) -> list[str]:
    found = []
    for index, code in enumerate(CODES):
        read = program[FIRST_SPAN_AT + index] << 8 | SPAN_TAIL
        if read != header.FIRST_SPAN[code]:
            found.append(
                f"the first span for size code {code:#x} is {read:#x}, "
                f"not {header.FIRST_SPAN[code]:#x}"
            )
    return found


def bank_disagreements(program: bytes) -> list[str]:
    found = []
    for index, code in enumerate(BANKED_CODES):
        read = program[BANKS_AT + index]
        if read != header.BANKS_FROM_THE_THIRD[code]:
            found.append(
                f"size code {code:#x} adds {read} banks, not {header.BANKS_FROM_THE_THIRD[code]}"
            )
    return found


def gate_disagreements(program: bytes) -> list[str]:
    found = []
    if program[COMPARED_AT] != len(header.MAGIC):
        found.append(f"it compares {program[COMPARED_AT]} bytes, not {len(header.MAGIC)}")
    gated = program[REGION_GATE_AT] >> 4
    if gated != EXPORT_REGION:
        found.append(f"it checks the sum only for region {gated:#x}, not {EXPORT_REGION:#x}")
    return found


def disagreements(program: bytes) -> list[str]:
    return span_disagreements(program) + bank_disagreements(program) + gate_disagreements(program)


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python3 -m conformance.boot <the v1.3 export boot program>")
        return 2
    program = Path(argv[0]).read_bytes()
    if hashlib.sha256(program).hexdigest() != DECLARED:
        print(f"{argv[0]} is not the boot program the manifest declares as {READ_FROM}")
        return 1
    found = disagreements(program)
    for one in found:
        print(one)
    if found:
        return 1
    print(
        f"{READ_FROM} agrees with the package: {len(CODES)} spans, "
        f"{len(BANKED_CODES)} bank counts, an {len(header.MAGIC)}-byte compare, "
        "the sum checked only for region 4"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
