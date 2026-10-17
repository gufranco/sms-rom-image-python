import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402

import smsimage  # noqa: E402
from smsimage import header  # noqa: E402

MAGIC = b"TMR SEGA"

REGION_AND_SIZE = 0x0F

CHECKSUM = 0x0A


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


def with_magic_at(image: bytearray, where: int) -> bytes:
    image[where : where + len(MAGIC)] = MAGIC
    return bytes(image)


class AnchorTest(unittest.TestCase):
    def test_it_finds_a_header_at_the_usual_offset(self) -> None:
        # Arrange
        image = bytes(planted(32768, 0x7FF0))

        # Act
        found = header.anchor_of(image)

        # Assert
        self.assertEqual(found, 0x7FF0)

    def test_it_finds_a_header_at_the_middle_offset(self) -> None:
        # Arrange
        image = bytes(planted(16384, 0x3FF0))

        # Act
        found = header.anchor_of(image)

        # Assert
        self.assertEqual(found, 0x3FF0)

    def test_it_finds_a_header_at_the_smallest_offset(self) -> None:
        # Arrange
        image = bytes(planted(8192, 0x1FF0))

        # Act
        found = header.anchor_of(image)

        # Assert
        self.assertEqual(found, 0x1FF0)

    def test_an_image_with_no_header_anywhere_has_no_anchor(self) -> None:
        # Arrange
        image = bytes(blank(32768))

        # Act
        found = header.anchor_of(image)

        # Assert
        self.assertIsNone(found)

    def test_an_image_too_short_to_hold_one_has_no_anchor(self) -> None:
        # Arrange
        image = bytes(blank(50))

        # Act
        found = header.anchor_of(image)

        # Assert
        self.assertIsNone(found)

    def test_the_magic_elsewhere_in_the_image_is_not_a_header(self) -> None:
        # Arrange
        image = with_magic_at(blank(65536), 0x81F0)

        # Act
        found = header.anchor_of(image)

        # Assert
        self.assertIsNone(found)

    def test_the_largest_candidate_wins_when_two_match(self) -> None:
        # Arrange
        image = with_magic_at(planted(262144, 0x7FF0), 0x3FF0)

        # Act
        found = header.anchor_of(image)

        # Assert
        self.assertEqual(found, 0x7FF0)

    def test_every_candidate_that_matches_is_reported_as_well(self) -> None:
        # Arrange
        image = with_magic_at(planted(262144, 0x7FF0), 0x3FF0)

        # Act
        found = header.anchors_in(image)

        # Assert
        self.assertEqual(found, (0x7FF0, 0x3FF0))

    def test_all_three_candidates_are_reported_largest_first(self) -> None:
        # Arrange
        image = with_magic_at(bytearray(with_magic_at(planted(32768, 0x1FF0), 0x7FF0)), 0x3FF0)

        # Act
        found = header.anchors_in(image)

        # Assert
        self.assertEqual(found, (0x7FF0, 0x3FF0, 0x1FF0))

    def test_an_image_with_no_header_reports_no_candidates(self) -> None:
        # Arrange
        image = bytes(blank(32768))

        # Act
        found = header.anchors_in(image)

        # Assert
        self.assertEqual(found, ())

    def test_eight_bytes_decide_and_the_two_after_them_do_not(self) -> None:
        # Arrange
        image = planted(32768, 0x7FF0)
        image[0x7FF8:0x7FFA] = b"\xff\xff"

        # Act
        found = header.anchor_of(bytes(image))

        # Assert
        self.assertEqual(found, 0x7FF0)

    def test_a_magic_short_of_its_last_byte_is_not_a_header(self) -> None:
        # Arrange
        image = planted(32768, 0x7FF0)
        image[0x7FF7] = 0x00

        # Act
        found = header.anchor_of(bytes(image))

        # Assert
        self.assertIsNone(found)


class DeclaredTest(unittest.TestCase):
    def test_it_reads_the_size_the_header_declares(self) -> None:
        # Arrange
        image = bytes(planted(32768, 0x7FF0, 0x4C))

        # Act
        found = header.declared_size(image)

        # Assert
        self.assertEqual(found, 32768)

    def test_every_size_nibble_reads_as_the_size_the_readme_gives_it(self) -> None:
        # Arrange
        nibbles = (0xA, 0xB, 0xC, 0xD, 0xE, 0xF, 0x0, 0x1, 0x2)

        # Act
        found = [header.declared_size(bytes(planted(32768, 0x7FF0, 0x40 | one))) for one in nibbles]

        # Assert
        self.assertEqual(
            found,
            [8192, 16384, 32768, 49152, 65536, 131072, 262144, 524288, 1048576],
        )

    def test_a_size_nibble_outside_the_reading_declares_nothing(self) -> None:
        # Arrange
        image = bytes(planted(32768, 0x7FF0, 0x43))

        # Act
        found = header.declared_size(image)

        # Assert
        self.assertIsNone(found)

    def test_an_image_with_no_header_declares_nothing(self) -> None:
        # Arrange
        image = bytes(blank(32768))

        # Act
        found = header.declared_size(image)

        # Assert
        self.assertIsNone(found)

    def test_it_reads_the_region_the_header_declares(self) -> None:
        # Arrange
        image = bytes(planted(32768, 0x7FF0, 0x4C))

        # Act
        found = header.region_of(image)

        # Assert
        self.assertEqual(found, "sms-export")

    def test_every_region_nibble_reads_as_the_name_the_readme_gives_it(self) -> None:
        # Arrange
        nibbles = (0x3, 0x4, 0x5, 0x6, 0x7)

        # Act
        found = [header.region_of(bytes(planted(32768, 0x7FF0, one << 4 | 0xC))) for one in nibbles]

        # Assert
        self.assertEqual(
            found, ["sms-japan", "sms-export", "gg-japan", "gg-export", "gg-international"]
        )

    def test_a_region_nibble_outside_the_reading_names_nothing(self) -> None:
        # Arrange
        image = bytes(planted(32768, 0x7FF0, 0x0C))

        # Act
        found = header.region_of(image)

        # Assert
        self.assertIsNone(found)

    def test_an_image_with_no_header_names_no_region(self) -> None:
        # Arrange
        image = bytes(blank(32768))

        # Act
        found = header.region_of(image)

        # Assert
        self.assertIsNone(found)

    def test_the_byte_read_is_the_last_of_sixteen_from_the_anchor(self) -> None:
        # Arrange
        image = planted(32768, 0x7FF0, 0x4C)
        image[0x7FFE] = 0x6B

        # Act
        found = (header.region_of(bytes(image)), header.declared_size(bytes(image)))

        # Assert
        self.assertEqual(found, ("sms-export", 32768))


class CarriedTest(unittest.TestCase):
    def test_it_reads_the_value_the_cartridge_stored(self) -> None:
        # Arrange
        image = planted(32768, 0x7FF0)
        image[0x7FFA:0x7FFC] = b"\x34\x12"

        # Act
        found = header.carried(bytes(image))

        # Assert
        self.assertEqual(found, 0x1234)

    def test_an_image_with_no_header_carries_nothing(self) -> None:
        # Arrange
        image = bytes(blank(32768))

        # Act
        found = header.carried(image)

        # Assert
        self.assertIsNone(found)


class AgreesTest(unittest.TestCase):
    def test_a_sealed_image_agrees_with_itself(self) -> None:
        # Arrange
        image = sealed(32768, 0x7FF0)

        # Act
        found = header.agrees(image)

        # Assert
        self.assertTrue(found)

    def test_an_image_whose_content_moved_does_not(self) -> None:
        # Arrange
        image = flipped(sealed(32768, 0x7FF0), 0x0200)

        # Act
        found = header.agrees(image)

        # Assert
        self.assertFalse(found)

    def test_an_image_with_no_header_does_not_agree_or_disagree(self) -> None:
        # Arrange
        image = bytes(blank(32768))

        # Act
        found = header.agrees(image)

        # Assert
        self.assertIsNone(found)

    def test_an_image_declaring_an_unknown_size_does_not_either(self) -> None:
        # Arrange
        image = bytes(planted(32768, 0x7FF0, 0x43))

        # Act
        found = header.agrees(image)

        # Assert
        self.assertIsNone(found)


class PublishedTablesTest(unittest.TestCase):
    def test_the_candidates_are_searched_largest_first(self) -> None:
        # Arrange
        published = smsimage.CANDIDATES

        # Act
        found = tuple(published)

        # Assert
        self.assertEqual(found, (0x7FF0, 0x3FF0, 0x1FF0))

    def test_the_magic_is_the_eight_bytes_the_readme_prints(self) -> None:
        # Arrange
        published = smsimage.MAGIC

        # Act
        found = bytes(published)

        # Assert
        self.assertEqual(found, MAGIC)

    def test_the_region_table_is_the_one_the_readme_prints(self) -> None:
        # Arrange
        published = smsimage.REGIONS

        # Act
        found = dict(published)

        # Assert
        self.assertEqual(
            found,
            {
                0x3: "sms-japan",
                0x4: "sms-export",
                0x5: "gg-japan",
                0x6: "gg-export",
                0x7: "gg-international",
            },
        )

    def test_the_size_table_is_the_one_the_readme_prints(self) -> None:
        # Arrange
        published = smsimage.SIZES

        # Act
        found = {code: size // 1024 for code, size in published.items()}

        # Assert
        self.assertEqual(
            found,
            {0xA: 8, 0xB: 16, 0xC: 32, 0xD: 48, 0xE: 64, 0xF: 128, 0x0: 256, 0x1: 512, 0x2: 1024},
        )


if __name__ == "__main__":
    unittest.main()
