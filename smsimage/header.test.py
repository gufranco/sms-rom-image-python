import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402

from smsimage import header  # noqa: E402


def blank(length: int) -> bytearray:
    return bytearray((index * 11 + 5) & 0xFF for index in range(length))


def planted(length: int, at: int, region_and_size: int = 0x4C) -> bytearray:
    image = blank(length)
    image[at : at + len(header.MAGIC)] = header.MAGIC
    image[at + 0x08 : at + 0x0A] = b"\x00\x00"
    image[at + 0x0A : at + 0x0C] = b"\x00\x00"
    image[at + 0x0C : at + 0x0F] = b"\x00\x00\x00"
    image[at + header.REGION_AND_SIZE] = region_and_size
    return image


def sealed(length: int, at: int, region_and_size: int = 0x4C) -> bytes:
    image = planted(length, at, region_and_size)
    computed = header.checksum(bytes(image))
    assert computed is not None
    image[at + 0x0A : at + 0x0C] = computed.to_bytes(2, "little")
    return bytes(image)


class AnchorTest(unittest.TestCase):
    def test_it_finds_a_header_at_the_usual_offset(self) -> None:
        found = header.anchor_of(bytes(planted(32768, 0x7FF0)))

        self.assertEqual(found, 0x7FF0)

    def test_it_finds_a_header_at_the_middle_offset(self) -> None:
        found = header.anchor_of(bytes(planted(16384, 0x3FF0)))

        self.assertEqual(found, 0x3FF0)

    def test_it_finds_a_header_at_the_smallest_offset(self) -> None:
        found = header.anchor_of(bytes(planted(8192, 0x1FF0)))

        self.assertEqual(found, 0x1FF0)

    def test_an_image_with_no_header_anywhere_has_no_anchor(self) -> None:
        found = header.anchor_of(bytes(blank(32768)))

        self.assertIsNone(found)

    def test_an_image_too_short_to_hold_one_has_no_anchor(self) -> None:
        found = header.anchor_of(bytes(blank(50)))

        self.assertIsNone(found)

    def test_the_magic_elsewhere_in_the_image_is_not_a_header(self) -> None:
        image = blank(65536)
        image[0x81F0 : 0x81F0 + len(header.MAGIC)] = header.MAGIC

        found = header.anchor_of(bytes(image))

        self.assertIsNone(found)

    def test_the_largest_candidate_wins_when_two_match(self) -> None:
        image = planted(262144, 0x7FF0)
        image[0x3FF0 : 0x3FF0 + len(header.MAGIC)] = header.MAGIC

        found = header.anchor_of(bytes(image))

        self.assertEqual(found, 0x7FF0)

    def test_every_candidate_that_matches_is_reported_as_well(self) -> None:
        image = planted(262144, 0x7FF0)
        image[0x3FF0 : 0x3FF0 + len(header.MAGIC)] = header.MAGIC

        found = header.anchors_in(bytes(image))

        self.assertEqual(found, (0x7FF0, 0x3FF0))

    def test_an_image_with_no_header_reports_no_candidates(self) -> None:
        found = header.anchors_in(bytes(blank(32768)))

        self.assertEqual(found, ())

    def test_the_candidates_are_searched_largest_first(self) -> None:
        self.assertEqual(header.CANDIDATES, (0x7FF0, 0x3FF0, 0x1FF0))


class DeclaredTest(unittest.TestCase):
    def test_it_reads_the_size_the_header_declares(self) -> None:
        found = header.declared_size(bytes(planted(32768, 0x7FF0, 0x4C)))

        self.assertEqual(found, 32768)

    def test_a_size_nibble_outside_the_reading_declares_nothing(self) -> None:
        found = header.declared_size(bytes(planted(32768, 0x7FF0, 0x43)))

        self.assertIsNone(found)

    def test_an_image_with_no_header_declares_nothing(self) -> None:
        found = header.declared_size(bytes(blank(32768)))

        self.assertIsNone(found)

    def test_it_reads_the_region_the_header_declares(self) -> None:
        found = header.region_of(bytes(planted(32768, 0x7FF0, 0x4C)))

        self.assertEqual(found, header.SMS_EXPORT)

    def test_a_region_nibble_outside_the_reading_names_nothing(self) -> None:
        found = header.region_of(bytes(planted(32768, 0x7FF0, 0x0C)))

        self.assertIsNone(found)

    def test_an_image_with_no_header_names_no_region(self) -> None:
        found = header.region_of(bytes(blank(32768)))

        self.assertIsNone(found)


class CarriedTest(unittest.TestCase):
    def test_it_reads_the_value_the_cartridge_stored(self) -> None:
        image = planted(32768, 0x7FF0)
        image[0x7FF0 + 0x0A : 0x7FF0 + 0x0C] = b"\x34\x12"

        found = header.carried(bytes(image))

        self.assertEqual(found, 0x1234)

    def test_an_image_with_no_header_carries_nothing(self) -> None:
        found = header.carried(bytes(blank(32768)))

        self.assertIsNone(found)


class ChecksumTest(unittest.TestCase):
    def test_it_reproduces_the_value_on_an_image_that_was_sealed(self) -> None:
        image = sealed(32768, 0x7FF0)

        self.assertEqual(header.checksum(image), header.carried(image))

    def test_it_ignores_the_header_itself(self) -> None:
        image = bytearray(sealed(32768, 0x7FF0))
        image[0x7FF0 + 0x0C] ^= 0xFF

        self.assertEqual(header.checksum(bytes(image)), header.carried(bytes(image)))

    def test_a_byte_changed_outside_the_header_changes_it(self) -> None:
        image = bytearray(sealed(32768, 0x7FF0))
        before = header.checksum(bytes(image))
        image[0x0100] ^= 0xFF

        self.assertNotEqual(header.checksum(bytes(image)), before)

    def test_it_covers_only_as_far_as_the_declared_size(self) -> None:
        image = bytearray(sealed(65536, 0x7FF0, 0x4C))
        before = header.checksum(bytes(image))
        image[0xC000] ^= 0xFF

        self.assertEqual(header.checksum(bytes(image)), before)

    def test_it_covers_the_bytes_past_the_header_up_to_that_size(self) -> None:
        image = bytearray(sealed(65536, 0x7FF0, 0x4E))
        before = header.checksum(bytes(image))
        image[0xC000] ^= 0xFF

        self.assertNotEqual(header.checksum(bytes(image)), before)

    def test_it_stops_at_the_end_of_a_file_shorter_than_it_declares(self) -> None:
        image = sealed(32768, 0x7FF0, 0x4F)

        self.assertIsNotNone(header.checksum(image))

    def test_it_stays_inside_sixteen_bits(self) -> None:
        image = bytes([0xFF] * 0x7FF0) + bytes(planted(0x8000, 0x7FF0))[0x7FF0:]

        found = header.checksum(image)

        assert found is not None
        self.assertLessEqual(found, 0xFFFF)

    def test_an_image_with_no_header_has_no_checksum(self) -> None:
        found = header.checksum(bytes(blank(32768)))

        self.assertIsNone(found)

    def test_an_image_declaring_a_size_outside_the_reading_has_none(self) -> None:
        found = header.checksum(bytes(planted(32768, 0x7FF0, 0x43)))

        self.assertIsNone(found)


class AgreesTest(unittest.TestCase):
    def test_a_sealed_image_agrees_with_itself(self) -> None:
        self.assertTrue(header.agrees(sealed(32768, 0x7FF0)))

    def test_an_image_whose_content_moved_does_not(self) -> None:
        image = bytearray(sealed(32768, 0x7FF0))
        image[0x0200] ^= 0xFF

        self.assertFalse(header.agrees(bytes(image)))

    def test_an_image_with_no_header_does_not_agree_or_disagree(self) -> None:
        self.assertIsNone(header.agrees(bytes(blank(32768))))


class SurfaceTest(unittest.TestCase):
    def test_the_header_is_sixteen_bytes(self) -> None:
        self.assertEqual(header.LENGTH, 0x10)

    def test_every_size_the_reading_names_is_a_whole_kilobyte(self) -> None:
        odd = [one for one in header.SIZES.values() if one % 1024]

        self.assertEqual(odd, [])

    def test_every_size_nibble_fits_in_a_nibble(self) -> None:
        wide = [one for one in header.SIZES if one > 0x0F]

        self.assertEqual(wide, [])

    def test_every_region_nibble_fits_in_a_nibble(self) -> None:
        wide = [one for one in header.REGIONS if one > 0x0F]

        self.assertEqual(wide, [])

    def test_each_region_is_named_once(self) -> None:
        named = list(header.REGIONS.values())

        self.assertEqual(sorted(named), sorted(set(named)))


if __name__ == "__main__":
    unittest.main()
