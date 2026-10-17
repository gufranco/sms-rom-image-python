import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from smsimage import header  # noqa: E402

HELD: dict[str, Any] = json.loads((ROOT / "conformance" / "hardware.json").read_text())

FACTS: dict[str, Any] = HELD["facts"]

LARGEST_ANCHOR: int = FACTS["headerAddress"]["value"]

PRINTED_STRING = bytes(FACTS["openingString"]["value"])

COMPARED = 8

IMAGE_BYTES = 0x8000

FILLED = 0xFF

NIBBLES = range(0x10)


def stamped(address: int, data: bytes) -> dict[int, int]:
    return {address + offset: byte for offset, byte in enumerate(data)}


def an_image(writes: dict[int, int]) -> bytes:
    image = bytearray(IMAGE_BYTES)
    for where, byte in writes.items():
        image[where] = byte
    return bytes(image)


def a_header() -> dict[int, int]:
    return stamped(LARGEST_ANCHOR, PRINTED_STRING)


def with_code(code: int) -> bytes:
    return an_image({**a_header(), FACTS["sizeCodeAddress"]["value"]: code})


def read_as(image: bytes) -> tuple[int | None, int | None]:
    return header.carried(image), header.declared_size(image)


class DocumentTest(unittest.TestCase):
    def test_every_fact_names_a_document_the_record_declares(self) -> None:
        # Arrange
        declared = set(HELD["documents"])

        # Act
        unnamed = [name for name, fact in FACTS.items() if fact["document"] not in declared]

        # Assert
        self.assertEqual(unnamed, [])

    def test_every_fact_names_the_page_it_was_read_from(self) -> None:
        # Arrange
        pages = set(HELD["documents"]["referenceManual"]["headerPages"])

        # Act
        elsewhere = [name for name, fact in FACTS.items() if fact["manualPage"] not in pages]

        # Assert
        self.assertEqual(elsewhere, [])

    def test_every_fact_names_the_parts_it_governs(self) -> None:
        # Arrange
        facts = FACTS

        # Act
        silent = [name for name, fact in facts.items() if not fact.get("governs")]

        # Assert
        self.assertEqual(silent, [])

    def test_the_manual_carries_a_digest_so_the_reading_can_be_repeated(self) -> None:
        # Arrange
        manual = HELD["documents"]["referenceManual"]

        # Act
        width = len(manual["sha256"])

        # Assert
        self.assertEqual(width, 64)

    def test_the_record_and_the_document_list_name_the_same_file(self) -> None:
        # Arrange
        listed = json.loads((ROOT / "conformance" / "documents.json").read_text())

        # Act
        digests = {entry["sha256"] for entry in listed["documents"]}

        # Assert
        self.assertIn(HELD["documents"]["referenceManual"]["sha256"], digests)


class PlacementTest(unittest.TestCase):
    def test_the_header_is_looked_for_first_where_the_manual_puts_it(self) -> None:
        # Arrange
        printed = FACTS["headerAddress"]["value"]
        smaller = [one["header"] for one in FACTS["sizeCodes"]["value"].values() if "header" in one]
        writes = {
            key: value
            for where in (*smaller, printed)
            for key, value in stamped(where, PRINTED_STRING).items()
        }

        # Act
        first = header.anchor_of(an_image(writes))

        # Assert
        self.assertEqual(first, printed)

    def test_and_at_every_smaller_address_the_size_codes_name(self) -> None:
        # Arrange
        smaller = {one["header"] for one in FACTS["sizeCodes"]["value"].values() if "header" in one}
        writes = {
            key: value for where in smaller for key, value in stamped(where, PRINTED_STRING).items()
        }

        # Act
        looked_at = set(header.anchors_in(an_image(writes)))

        # Assert
        self.assertEqual(looked_at, smaller)

    def test_the_checksum_sits_at_the_two_bytes_the_manual_names(self) -> None:
        # Arrange
        printed = FACTS["checksum"]["value"]
        serial = FACTS["serialNumber"]["value"]
        image = an_image(
            {**a_header(), printed["first"]: 0x34, printed["last"]: 0x12, serial["first"]: FILLED}
        )

        # Act
        carried = header.carried(image)

        # Assert
        self.assertEqual(carried, 0x1234)

    def test_and_is_read_low_byte_first(self) -> None:
        # Arrange
        printed = FACTS["checksum"]["value"]
        image = an_image({**a_header(), printed["first"]: 0x34, printed["last"]: 0x12})

        # Act
        carried = header.carried(image)

        # Assert
        self.assertEqual((printed["order"], carried), ("little", 0x1234))

    def test_the_size_code_is_read_from_the_byte_the_manual_names(self) -> None:
        # Arrange
        printed = FACTS["sizeCodeAddress"]["value"]
        image = an_image({**a_header(), printed - 1: 76, printed: 77})

        # Act
        held = header.declared_size(image)

        # Assert
        self.assertEqual(held, FACTS["sizeCodes"]["value"]["77"]["bytes"])

    def test_the_serial_and_revision_sit_between_the_checksum_and_the_size_code(self) -> None:
        # Arrange
        serial = FACTS["serialNumber"]["value"]

        # Act
        order = [
            FACTS["checksum"]["value"]["last"],
            serial["first"],
            serial["last"],
            FACTS["revision"]["value"],
            FACTS["sizeCodeAddress"]["value"],
        ]

        # Assert
        self.assertEqual(order, list(range(order[0], order[0] + len(order))))

    def test_the_header_is_as_long_as_the_fields_the_manual_lists(self) -> None:
        # Arrange
        span = FACTS["sizeCodeAddress"]["value"] - FACTS["headerAddress"]["value"] + 1
        image = an_image({**a_header(), LARGEST_ANCHOR + span - 1: 77})

        # Act
        held = header.declared_size(image)

        # Assert
        self.assertEqual((span, held), (0x10, FACTS["sizeCodes"]["value"]["77"]["bytes"]))


class OpeningStringTest(unittest.TestCase):
    def test_the_string_looked_for_is_how_the_printed_one_begins(self) -> None:
        # Arrange
        printed = bytes(FACTS["openingString"]["value"])
        begun = an_image(stamped(LARGEST_ANCHOR, printed[:COMPARED]))
        short = an_image(stamped(LARGEST_ANCHOR, printed[: COMPARED - 1]))

        # Act
        found = (header.anchor_of(begun), header.anchor_of(short))

        # Assert
        self.assertEqual(found, (LARGEST_ANCHOR, None))

    def test_and_stops_short_of_the_two_spaces_the_library_mostly_lacks(self) -> None:
        # Arrange
        lacking = PRINTED_STRING[:COMPARED] + bytes([FILLED, FILLED])
        image = an_image(stamped(LARGEST_ANCHOR, lacking))

        # Act
        found = header.anchor_of(image)

        # Assert
        self.assertEqual((PRINTED_STRING[COMPARED:], found), (b"  ", LARGEST_ANCHOR))


class SizeCodeTest(unittest.TestCase):
    def test_every_printed_code_carries_the_region_this_package_calls_export(self) -> None:
        # Arrange
        codes = [int(code) for code in FACTS["sizeCodes"]["value"]]

        # Act
        regions = {header.region_of(with_code(code)) for code in codes}

        # Assert
        self.assertEqual(regions, {"sms-export"})

    def test_every_printed_code_reads_as_the_size_the_manual_gives_it(self) -> None:
        # Arrange
        printed = FACTS["sizeCodes"]["value"]

        # Act
        read = {code: header.declared_size(with_code(int(code))) for code in printed}

        # Assert
        self.assertEqual(read, {code: one["bytes"] for code, one in printed.items()})

    def test_there_is_one_printed_line_per_code(self) -> None:
        # Arrange
        sizes = FACTS["sizeCodes"]

        # Act
        counts = (len(sizes["quotes"]), len(sizes["value"]))

        # Assert
        self.assertEqual(counts[0], counts[1])

    def test_every_printed_line_names_its_code_in_the_manual_s_notation(self) -> None:
        # Arrange
        sizes = FACTS["sizeCodes"]

        # Act
        named = sorted(int(line.split()[0].lstrip("$"), 16) for line in sizes["quotes"])

        # Assert
        self.assertEqual(named, sorted(int(code) for code in sizes["value"]))


class ReadingTest(unittest.TestCase):
    def test_a_header_opened_at_the_printed_address_is_found_there(self) -> None:
        # Arrange
        printed = FACTS["headerAddress"]["value"]
        image = an_image(stamped(printed, PRINTED_STRING[:COMPARED]))

        # Act
        found = header.anchor_of(image)

        # Assert
        self.assertEqual(found, printed)

    def test_an_image_carrying_the_printed_string_has_a_header(self) -> None:
        # Arrange
        printed = bytes(FACTS["openingString"]["value"])
        image = an_image(stamped(LARGEST_ANCHOR, printed))

        # Act
        found = header.anchor_of(image)

        # Assert
        self.assertEqual(found, LARGEST_ANCHOR)

    def test_the_carried_checksum_is_the_two_printed_bytes_low_byte_first(self) -> None:
        # Arrange
        printed = FACTS["checksum"]["value"]
        image = an_image({**a_header(), printed["first"]: 0x34, printed["last"]: 0x12})

        # Act
        carried = header.carried(image)

        # Assert
        self.assertEqual(carried, int.from_bytes(bytes([0x34, 0x12]), printed["order"]))

    def test_the_size_is_read_from_the_printed_byte(self) -> None:
        # Arrange
        printed = FACTS["sizeCodeAddress"]["value"]
        image = an_image({**a_header(), printed: 77})

        # Act
        size = header.declared_size(image)

        # Assert
        self.assertEqual(size, FACTS["sizeCodes"]["value"]["77"]["bytes"])

    def test_every_printed_size_code_declares_the_printed_size(self) -> None:
        # Arrange
        printed = FACTS["sizeCodes"]["value"]

        # Act
        read = {code: header.declared_size(with_code(int(code))) for code in printed}

        # Assert
        self.assertEqual(read, {code: one["bytes"] for code, one in printed.items()})

    def test_a_small_cartridge_header_is_found_where_its_size_code_puts_it(self) -> None:
        # Arrange
        printed = [one["header"] for one in FACTS["sizeCodes"]["value"].values() if "header" in one]

        # Act
        found = [
            header.anchor_of(an_image(stamped(where, PRINTED_STRING[:COMPARED])))
            for where in printed
        ]

        # Assert
        self.assertEqual(found, printed)

    def test_a_serial_number_moves_nothing_the_header_is_read_as(self) -> None:
        # Arrange
        printed = FACTS["serialNumber"]["value"]
        code = {FACTS["sizeCodeAddress"]["value"]: 76}
        image = an_image({**a_header(), **code, printed["first"]: FILLED, printed["last"]: FILLED})

        # Act
        read = read_as(image)

        # Assert
        self.assertEqual(read, (0, FACTS["sizeCodes"]["value"]["76"]["bytes"]))

    def test_a_revision_moves_nothing_the_header_is_read_as(self) -> None:
        # Arrange
        printed = FACTS["revision"]["value"]
        code = {FACTS["sizeCodeAddress"]["value"]: 76}
        image = an_image({**a_header(), **code, printed: FILLED})

        # Act
        read = read_as(image)

        # Assert
        self.assertEqual(read, (0, FACTS["sizeCodes"]["value"]["76"]["bytes"]))


class NotStatedTest(unittest.TestCase):
    def test_every_reading_the_manual_does_not_cover_is_said_out_loud(self) -> None:
        # Arrange
        expected = {
            "otherRegions",
            "largerSizes",
            "whichBytesTheChecksumCovers",
            "copierBlocks",
            "gameGear",
        }

        # Act
        said = set(HELD["notStated"])

        # Assert
        self.assertEqual(said, expected)

    def test_the_package_reads_regions_the_manual_never_prints(self) -> None:
        # Arrange
        printed = {int(code) >> 4 for code in FACTS["sizeCodes"]["value"]}

        # Act
        named = {one for one in NIBBLES if header.region_of(with_code(one << 4 | 0xC))}

        # Assert
        self.assertEqual(named - printed, {0x3, 0x5, 0x6, 0x7})

    def test_and_sizes_larger_than_any_it_prints(self) -> None:
        # Arrange
        printed = {int(code) & 0x0F for code in FACTS["sizeCodes"]["value"]}

        # Act
        named = {one for one in NIBBLES if header.declared_size(with_code(0x40 | one))}

        # Assert
        self.assertEqual(named - printed, {0x1, 0x2})


if __name__ == "__main__":
    unittest.main()
