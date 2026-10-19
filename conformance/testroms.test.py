import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import testroms  # noqa: E402

WITH_A_HEADER = bytearray(0x8000)
WITH_A_HEADER[0x7FF0:0x7FF8] = b"TMR SEGA"
WITH_A_HEADER[0x7FFA:0x7FFC] = (0x1234).to_bytes(2, "little")
WITH_A_HEADER[0x7FFF] = 0x4C

AN_IMAGE = bytes(WITH_A_HEADER)

ITS_READING = {
    "form": "bare",
    "size": 0x8000,
    "anchor": 0x7FF0,
    "region": "sms-export",
    "declared": 0x8000,
    "carried": False,
    "stored": 0x1234,
    "computed": sum(AN_IMAGE[:0x7FF0]) & 0xFFFF,
}


def a_record(folder: Path, *images: bytes, read: dict[str, Any] | None = None) -> Path:
    listed: list[dict[str, Any]] = [
        {
            "id": f"probe-{index}",
            "sha256": hashlib.sha256(image).hexdigest(),
            "outcome": "read",
            "read": read,
        }
        for index, image in enumerate(images)
    ]
    listed.append({"id": "waits", "sha256": "ab" * 32, "outcome": "hosted", "needs": "x"})
    path = folder / "testroms.json"
    path.write_text(json.dumps({"cartridges": listed}))
    return path


def held_in(folder: Path, image: bytes, name: str = "probe.sms") -> Path:
    path = folder / name
    path.write_bytes(image)
    return path


class RecordedReadingTest(unittest.TestCase):
    def test_every_image_reads_as_recorded(self) -> None:
        # Arrange
        expected = {
            "64-color-palette-test": (0x7FF0, None, 262144, False),
            "bios-alex-kidd-in-miracle-world-bios-version-world-sega-ages": (
                0x7FF0,
                "sms-export",
                131072,
                False,
            ),
            "bios-alex-kidd-in-miracle-world-korea-unl": (0x7FF0, "sms-export", 131072, False),
            "bios-alex-kidd-in-miracle-world-usa-europe": (0x7FF0, "sms-export", 131072, True),
            "bios-hang-on-safari-hunt-usa-europe-brazil-en-v2-4": (
                0x7FF0,
                "sms-export",
                131072,
                False,
            ),
            "bios-hang-on-usa-europe-v3-4": (None, None, None, None),
            "bios-missile-defense-3-d-usa-europe-v4-4": (None, None, None, None),
            "bios-sega-master-system-europe-v2-0": (None, None, None, None),
            "bios-sega-master-system-japan-v2-1": (None, None, None, None),
            "bios-sega-master-system-usa-m404-proto": (None, None, None, None),
            "bios-sega-master-system-usa-store-display-unit": (None, None, None, None),
            "bios-sega-master-system-usa-v1-0-proto": (None, None, None, None),
            "bios-sega-master-system-usa-europe-v1-3": (None, None, None, None),
            "bios-sonic-the-hedgehog-europe": (0x7FF0, "sms-export", 262144, False),
            "color-switch-test-japan-en-proto": (0x7FF0, "sms-export", 32768, True),
            "controllers-test-sms-genesis-v1-sverx-2018-01-30": (None, None, None, None),
            "empty-slot-to-test-sms-bios-splash-screen": (None, None, None, None),
            "interrupt-test": (0x7FF0, None, 262144, False),
            "line-interrupt-test-1-charles-macdonald": (0x7FF0, "sms-export", 32768, True),
            "sega-graphic-board-usa-v2-0-proto": (0x7FF0, "sms-export", 32768, True),
            "sega-mark-iii-bg-test-v0-01": (None, None, None, None),
            "sega-mark-iii-port-test-v0-1": (None, None, None, None),
            "sms-boot-loader-0-9": (0x7FF0, "sms-export", 32768, True),
            "sms-fm-tool-ym2413-v1-chris-covell": (0x7FF0, "sms-export", 32768, True),
            "sms-genesis-6-button-controller-test-by-charles-macdonald": (
                0x7FF0,
                None,
                262144,
                False,
            ),
            "sms-paging-pfr-detect-v2-eric-r-quinn": (0x7FF0, None, 1048576, True),
            "sms-palette-tool-v1-0": (0x7FF0, None, None, None),
            "sms-sound-test-v1-1-nicolas-warren": (0x7FF0, "sms-export", 32768, True),
            "sms-sprite-test": (0x7FF0, None, 262144, False),
            "sms-test-suite-v0-32-sverx": (0x7FF0, "sms-export", 32768, True),
            "sms-v-counter-test-program-charles-macdonald": (0x7FF0, None, 262144, False),
            "sms-vgm-player-v0-45-maxim": (0x7FF0, "sms-export", 32768, True),
            "zexall-sdsc": (0x7FF0, "sms-export", 32768, True),
            "zexall-svpd": (0x7FF0, "sms-export", 32768, True),
            "sg-1000-m2-check": (None, None, None, None),
        }

        # Act
        found = {
            one["id"]: (
                one["read"]["anchor"],
                one["read"]["region"],
                one["read"]["declared"],
                one["read"]["carried"],
            )
            for one in testroms.record()["cartridges"]
            if one["outcome"] == "read"
        }

        # Assert
        self.assertEqual(found, expected)

    def test_a_record_that_is_not_an_object_is_refused(self) -> None:
        # Arrange
        path = Path(tempfile.mkdtemp()) / "testroms.json"
        path.write_text("[]")

        # Act
        attempt = lambda: testroms.record(path)  # noqa: E731

        # Assert
        self.assertRaises(AssertionError, attempt)


class ReadingTest(unittest.TestCase):
    def test_a_header_is_read_with_both_checksums(self) -> None:
        # Arrange
        image = AN_IMAGE

        # Act
        found = testroms.reading(image)

        # Assert
        self.assertEqual(found, ITS_READING)

    def test_an_image_inside_a_zip_is_found_by_digest_and_any_other_left_out(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(folder / "held.zip", "w") as archive:
            archive.writestr("inner.sms", AN_IMAGE)
        held_in(folder, b"something else", "other.sms")
        digest = hashlib.sha256(AN_IMAGE).hexdigest()

        # Act
        found = testroms.images([folder / "held.zip", folder], {digest})

        # Assert
        self.assertEqual(list(found), [digest])


class MainTest(unittest.TestCase):
    def test_an_image_read_as_recorded_exits_zero(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        record = a_record(folder, AN_IMAGE, read=ITS_READING)

        # Act
        code = testroms.main([str(held_in(folder, AN_IMAGE))], record)

        # Assert
        self.assertEqual(code, 0)

    def test_an_image_read_otherwise_exits_one(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        record = a_record(folder, AN_IMAGE, read={**ITS_READING, "stored": 0})

        # Act
        code = testroms.main([str(held_in(folder, AN_IMAGE))], record)

        # Assert
        self.assertEqual(code, 1)

    def test_writing_keeps_what_was_read(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        record = a_record(folder, AN_IMAGE)

        # Act
        testroms.main(["--write", str(held_in(folder, AN_IMAGE))], record)

        # Assert
        self.assertEqual(testroms.record(record)["cartridges"][0]["read"], ITS_READING)

    def test_an_image_absent_while_another_is_held_is_skipped_not_failed(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        record = a_record(folder, AN_IMAGE, AN_IMAGE[:-1] + b"\x01", read=ITS_READING)

        # Act
        code = testroms.main([str(held_in(folder, AN_IMAGE))], record)

        # Assert
        self.assertEqual(code, 0)

    def test_the_places_can_come_from_the_environment(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        record = a_record(folder, AN_IMAGE, read=ITS_READING)
        held_in(folder, AN_IMAGE)

        # Act
        with mock.patch.dict(os.environ, {testroms.PLACES: str(folder)}):
            code = testroms.main([], record)

        # Assert
        self.assertEqual(code, 0)

    def test_with_no_image_anywhere_it_exits_two(self) -> None:
        # Arrange
        environment = {k: v for k, v in os.environ.items() if k != testroms.PLACES}

        # Act
        with mock.patch.dict(os.environ, environment, clear=True):
            code = testroms.main([])

        # Assert
        self.assertEqual(code, testroms.NOTHING_TO_READ)

    def test_an_option_it_does_not_know_is_a_usage_error(self) -> None:
        # Arrange
        argv = ["--jobs"]

        # Act
        code = testroms.main(argv)

        # Assert
        self.assertEqual(code, testroms.USAGE_ERROR)


if __name__ == "__main__":
    unittest.main()
