import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402

from smsimage import header  # noqa: E402

MAGIC = b"TMR SEGA"

REGION_AND_SIZE = 0x0F

CHECKSUM = 0x0A

SPANS = {
    0x4A: (0x1FEF, 0x1FF0, 0x8000),
    0x4B: (0x3FEF, 0x3FF0, 0x8000),
    0x4C: (0x7FEF, 0x7FFC, 0x8000),
    0x4D: (0xBFEF, 0xBFF0, 0x10000),
    0x4E: (0xFFFF, 0x10000, 0x20000),
    0x4F: (0x1FFFF, 0x20000, 0x40000),
    0x40: (0x3FFFF, 0x40000, 0x80000),
    0x41: (0x7FFFF, 0x80000, 0x100000),
    0x42: (0xFFFFF, 0x100000, 0x200000),
}


def blank(length: int) -> bytearray:
    return bytearray((index * 11 + 5) & 0xFF for index in range(length))


def planted(length: int, at: int, region_and_size: int = 0x4C) -> bytearray:
    image = blank(length)
    image[at : at + len(MAGIC)] = MAGIC
    image[at + 0x08 : at + REGION_AND_SIZE] = bytes(REGION_AND_SIZE - 0x08)
    image[at + REGION_AND_SIZE] = region_and_size
    return image


def sealed(length: int, at: int, region_and_size: int = 0x4C) -> bytes:
    image = planted(length, at, region_and_size)
    computed = header.checksum(bytes(image))
    assert computed is not None
    image[at + CHECKSUM : at + CHECKSUM + 2] = computed.to_bytes(2, "little")
    return bytes(image)


def flipped(image: bytes, where: int) -> bytes:
    return image[:where] + bytes([image[where] ^ 0xFF]) + image[where + 1 :]


def counts(region_and_size: int, length: int, where: int) -> bool:
    image = sealed(length, 0x7FF0, region_and_size)
    return header.checksum(flipped(image, where)) != header.checksum(image)


class ChecksumTest(unittest.TestCase):
    def test_it_reproduces_the_value_on_an_image_that_was_sealed(self) -> None:
        # Arrange
        image = sealed(32768, 0x7FF0)

        # Act
        found = header.checksum(image)

        # Assert
        self.assertEqual(found, header.carried(image))

    def test_the_readme_example_sums_to_what_it_prints(self) -> None:
        # Arrange
        image = bytearray(0x8000)
        image[0x7FF0:0x7FF8] = MAGIC
        image[0x7FFF] = 0x6C

        # Act
        found = header.checksum(bytes(image))

        # Assert
        self.assertEqual(found, 0)

    def test_it_ignores_the_header_itself(self) -> None:
        # Arrange
        image = flipped(sealed(32768, 0x7FF0), 0x7FFC)

        # Act
        found = header.checksum(image)

        # Assert
        self.assertEqual(found, header.carried(image))

    def test_a_byte_changed_outside_the_header_changes_it(self) -> None:
        # Arrange
        image = sealed(32768, 0x7FF0)

        # Act
        found = header.checksum(flipped(image, 0x0100))

        # Assert
        self.assertNotEqual(found, header.checksum(image))

    def test_every_size_code_counts_its_last_byte_and_not_the_next(self) -> None:
        # Arrange
        spans = SPANS

        # Act
        found = {
            code: (counts(code, length, last), counts(code, length, past))
            for code, (last, past, length) in spans.items()
        }

        # Assert
        self.assertEqual(found, dict.fromkeys(spans, (True, False)))

    def test_a_banked_size_skips_the_header_between_its_spans(self) -> None:
        # Arrange
        banked = (0x4E, 0x4F, 0x40)

        # Act
        found = [counts(code, SPANS[code][2], 0x7FFC) for code in banked]

        # Assert
        self.assertEqual(found, [False, False, False])

    def test_and_counts_the_first_byte_of_the_third_bank(self) -> None:
        # Arrange
        banked = (0x4E, 0x4F, 0x40)

        # Act
        found = [counts(code, SPANS[code][2], 0x8000) for code in banked]

        # Assert
        self.assertEqual(found, [True, True, True])

    def test_a_forty_eight_kilobyte_declaration_sums_through_the_header(self) -> None:
        # Arrange
        where = 0x7FFC

        # Act
        found = counts(0x4D, 0x10000, where)

        # Assert
        self.assertTrue(found)

    def test_it_covers_only_as_far_as_the_declared_size(self) -> None:
        # Arrange
        where = 0xC000

        # Act
        found = counts(0x4C, 65536, where)

        # Assert
        self.assertFalse(found)

    def test_it_stops_at_the_end_of_a_file_shorter_than_it_declares(self) -> None:
        # Arrange
        image = sealed(32768, 0x7FF0, 0x4F)

        # Act
        found = header.agrees(image)

        # Assert
        self.assertTrue(found)

    def test_it_stays_inside_sixteen_bits(self) -> None:
        # Arrange
        image = bytes([0xFF] * 0x7FF0) + bytes(planted(0x8000, 0x7FF0))[0x7FF0:]

        # Act
        found = header.checksum(image)

        # Assert
        self.assertEqual(found, 0x7010)

    def test_an_image_with_no_header_has_no_checksum(self) -> None:
        # Arrange
        image = bytes(blank(32768))

        # Act
        found = header.checksum(image)

        # Assert
        self.assertIsNone(found)

    def test_an_image_declaring_a_size_outside_the_reading_has_none(self) -> None:
        # Arrange
        image = bytes(planted(32768, 0x7FF0, 0x43))

        # Act
        found = header.checksum(image)

        # Assert
        self.assertIsNone(found)


if __name__ == "__main__":
    unittest.main()
