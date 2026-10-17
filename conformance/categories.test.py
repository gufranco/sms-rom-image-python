import contextlib
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import categories  # noqa: E402
from smsimage import header  # noqa: E402

ANCHOR = 0x7FF0

MAGIC = b"TMR SEGA"

REGION_AND_SIZE = 0x0F

CHECKSUM = 0x0A

THIRTY_TWO_K = 0x8000


def image(first: int, sealed: bool) -> bytes:
    held = bytearray(THIRTY_TWO_K)
    held[0] = first
    held[ANCHOR : ANCHOR + len(MAGIC)] = MAGIC
    held[ANCHOR + REGION_AND_SIZE] = 0x4C
    if sealed:
        stored = header.checksum(bytes(held)) or 0
        held[ANCHOR + CHECKSUM : ANCHOR + CHECKSUM + 2] = stored.to_bytes(2, "little")
    return bytes(held)


def library(entries: dict[str, bytes]) -> Path:
    path = Path(tempfile.mkdtemp()) / "set.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for name, body in entries.items():
            archive.writestr(name, body)
    return path


def run_main(argv: list[str]) -> tuple[int, str]:
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        code = categories.main(argv)
    return code, said.getvalue()


class GroupTest(unittest.TestCase):
    def test_an_entry_is_filed_under_the_folder_it_opens_with(self) -> None:
        # Arrange
        path = library({"1 US - A-Z/a.sms": image(1, True), "4 Hacks/b.sms": image(2, False)})

        # Act
        found = categories.grouped(path)

        # Assert
        self.assertEqual(sorted(found), ["1 US - A-Z", "4 Hacks"])

    def test_the_same_image_twice_in_one_folder_is_counted_once(self) -> None:
        # Arrange
        path = library({"1 US - A-Z/a.sms": image(1, True), "1 US - A-Z/c.sms": image(1, True)})

        # Act
        found = categories.grouped(path)

        # Assert
        self.assertEqual(len(found["1 US - A-Z"]), 1)

    def test_a_file_that_is_not_an_image_is_stepped_over(self) -> None:
        # Arrange
        path = library({"1 US - A-Z/notes.txt": b"text", "1 US - A-Z/a.sms": image(1, True)})

        # Act
        found = categories.grouped(path)

        # Assert
        self.assertEqual(len(found["1 US - A-Z"]), 1)


class TallyTest(unittest.TestCase):
    def test_agreement_is_counted_over_the_images_that_can_be_judged(self) -> None:
        # Arrange
        images = [image(1, True), image(2, False), bytes(THIRTY_TWO_K)]

        # Act
        found = categories.tally(images)

        # Assert
        self.assertEqual(found, (3, 2, 1))


class RetailTest(unittest.TestCase):
    def test_the_retail_set_is_the_four_region_folders_taken_together(self) -> None:
        # Arrange
        groups = {
            "1 US - A-Z": {"a": image(1, True)},
            "2 Europe - A-Z": {"a": image(1, True), "b": image(2, True)},
            "4 Hacks": {"c": image(3, False)},
        }

        # Act
        found = categories.retail(groups)

        # Assert
        self.assertEqual(sorted(found), ["a", "b"])


class MainTest(unittest.TestCase):
    def test_naming_no_library_explains_how_to_call_it(self) -> None:
        # Arrange
        argv: list[str] = []

        # Act
        code, said = run_main(argv)

        # Assert
        self.assertEqual((code, "usage" in said), (2, True))

    def test_a_library_with_no_image_measures_nothing_and_fails(self) -> None:
        # Arrange
        path = library({"1 US - A-Z/notes.txt": b"text"})

        # Act
        code, said = run_main([str(path)])

        # Assert
        self.assertEqual((code, "nothing was examined" in said), (1, True))

    def test_a_library_reports_every_folder_and_the_retail_set(self) -> None:
        # Arrange
        path = library(
            {
                "1 US - A-Z/a.sms": image(1, True),
                "2 Europe - A-Z/b.sms": image(2, False),
                "4 Hacks/c.sms": image(3, False),
            }
        )

        # Act
        code, said = run_main([str(path)])

        # Assert
        self.assertEqual(code, 0)
        self.assertIn("4 Hacks: 1 distinct, 1 judged, 0 agree", said)
        self.assertIn("retail Master System: 2 distinct, 2 judged, 1 agree", said)


if __name__ == "__main__":
    unittest.main()
