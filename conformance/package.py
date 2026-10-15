"""Audit a built wheel for what it ships and what it leaves out.

The configuration says test files stay out of the wheel, and for as long as that
configuration was the only thing saying it, every wheel this family built carried
them: `exclude-package-data` filters data files, and a `.test.py` file sitting in
a package directory is collected as a module. Nothing failed, because nothing in
the pipeline built the package at all, which is also how this member once had a
`pyproject.toml` declaring a readme that did not exist.

So the pipeline builds the wheel and hands it to this, and this compares it with
the source tree: every module the package carries is in the wheel, and no test
file is.

It takes the wheel as an argument rather than building one, so its own tests can
hand it a wheel that is deliberately wrong.
"""

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PACKAGE = "smsimage"

TEST_SUFFIX = ".test.py"


def modules(root: Path = ROOT) -> list[str]:
    """Every module the package carries, by file name, tests left out."""
    return sorted(
        found.name
        for found in (root / PACKAGE).glob("*.py")
        if not found.name.endswith(TEST_SUFFIX)
    )


def audit(wheel: Path) -> list[str]:
    """Every way this wheel differs from what the package should ship."""
    shipped = set(zipfile.ZipFile(wheel).namelist())
    faults = [
        f"ships a test: {name}"
        for name in sorted(shipped)
        if name.startswith(f"{PACKAGE}/") and name.endswith(TEST_SUFFIX)
    ]
    faults.extend(
        f"missing a module: {PACKAGE}/{name}"
        for name in modules()
        if f"{PACKAGE}/{name}" not in shipped
    )
    return faults


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python3 -m conformance.package <wheel>")
        return 2

    wheel = Path(argv[0])
    if not wheel.is_file():
        print(f"absent: {wheel}")
        return 1

    faults = audit(wheel)
    for fault in faults:
        print(fault)
    if faults:
        return 1

    print(f"{wheel.name}: {len(modules())} modules present, no test shipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
