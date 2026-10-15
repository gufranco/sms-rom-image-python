from __future__ import annotations

from pathlib import Path

COPIER_BLOCK = 512

CARTRIDGE_UNIT = 1024

BARE = "bare"

STUBBED = "stubbed"


def _longer_than_a_copier_block(data: bytes) -> bool:
    return len(data) > COPIER_BLOCK


def _a_whole_cartridge_after_a_copier_block(data: bytes) -> bool:
    return len(data) % CARTRIDGE_UNIT == COPIER_BLOCK


def form(data: bytes) -> str:
    if _longer_than_a_copier_block(data) and _a_whole_cartridge_after_a_copier_block(data):
        return STUBBED
    return BARE


def strip_copier_stub(data: bytes) -> bytes:
    return data[COPIER_BLOCK:] if form(data) == STUBBED else data


def read(path: Path | str) -> bytes:
    return strip_copier_stub(Path(path).read_bytes())
