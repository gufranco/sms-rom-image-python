import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import manual  # noqa: E402
from smsimage import header  # noqa: E402

HELD: dict[str, Any] = json.loads((ROOT / "conformance" / "hardware.json").read_text())

FACTS: dict[str, Any] = HELD["facts"]

LARGEST_ANCHOR = header.CANDIDATES[0]


def relative(address: int) -> int:
    return address - LARGEST_ANCHOR


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

        # Act
        first = header.CANDIDATES[0]

        # Assert
        self.assertEqual(first, printed)

    def test_and_at_every_smaller_address_the_size_codes_name(self) -> None:
        # Arrange
        smaller = {one["header"] for one in FACTS["sizeCodes"]["value"].values() if "header" in one}

        # Act
        looked_at = set(header.CANDIDATES)

        # Assert
        self.assertLessEqual(smaller, looked_at)

    def test_the_checksum_sits_at_the_two_bytes_the_manual_names(self) -> None:
        # Arrange
        printed = FACTS["checksum"]["value"]

        # Act
        held = (header.CHECKSUM.start, header.CHECKSUM.stop - 1)

        # Assert
        self.assertEqual(held, (relative(printed["first"]), relative(printed["last"])))

    def test_and_is_read_low_byte_first(self) -> None:
        # Arrange
        image = bytearray(0x8000)
        image[LARGEST_ANCHOR : LARGEST_ANCHOR + len(header.MAGIC)] = header.MAGIC
        image[LARGEST_ANCHOR + header.CHECKSUM.start] = 0x34
        image[LARGEST_ANCHOR + header.CHECKSUM.start + 1] = 0x12

        # Act
        carried = header.carried(bytes(image))

        # Assert
        self.assertEqual((FACTS["checksum"]["value"]["order"], carried), ("little", 0x1234))

    def test_the_size_code_is_read_from_the_byte_the_manual_names(self) -> None:
        # Arrange
        printed = FACTS["sizeCodeAddress"]["value"]

        # Act
        held = header.REGION_AND_SIZE

        # Assert
        self.assertEqual(held, relative(printed))

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

        # Act
        held = header.LENGTH

        # Assert
        self.assertEqual(held, span)


class OpeningStringTest(unittest.TestCase):
    def test_the_string_looked_for_is_how_the_printed_one_begins(self) -> None:
        # Arrange
        printed = bytes(FACTS["openingString"]["value"])

        # Act
        begins = printed.startswith(header.MAGIC)

        # Assert
        self.assertTrue(begins, printed)

    def test_and_stops_short_of_the_two_spaces_the_library_mostly_lacks(self) -> None:
        # Arrange
        printed = bytes(FACTS["openingString"]["value"])

        # Act
        left_out = printed[len(header.MAGIC) :]

        # Assert
        self.assertEqual(left_out, b"  ")


class SizeCodeTest(unittest.TestCase):
    def test_every_printed_code_carries_the_region_this_package_calls_export(self) -> None:
        # Arrange
        codes = [int(code) for code in FACTS["sizeCodes"]["value"]]

        # Act
        regions = {header.REGIONS[code >> 4] for code in codes}

        # Assert
        self.assertEqual(regions, {header.SMS_EXPORT})

    def test_every_printed_code_reads_as_the_size_the_manual_gives_it(self) -> None:
        # Arrange
        printed = FACTS["sizeCodes"]["value"]

        # Act
        read = {code: header.SIZES[int(code) & 0x0F] for code in printed}

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


def quotes_of(fact: dict[str, Any]) -> list[str]:
    return [fact["quote"]] if "quote" in fact else list(fact["quotes"])


class QuotesOfTest(unittest.TestCase):
    def test_a_fact_with_one_quote_gives_that_quote(self) -> None:
        # Arrange
        fact = {"quote": "A software revision number byte."}

        # Act
        found = quotes_of(fact)

        # Assert
        self.assertEqual(found, ["A software revision number byte."])

    def test_a_fact_with_a_numbered_set_gives_every_one(self) -> None:
        # Arrange
        fact = {"quotes": ["$4C 32K", "$4D 48K"]}

        # Act
        found = quotes_of(fact)

        # Assert
        self.assertEqual(found, ["$4C 32K", "$4D 48K"])


MANUAL = manual.text()


@unittest.skipUnless(MANUAL, "the manual or pdftotext is not on this machine")
class QuotedTest(unittest.TestCase):  # pragma: no cover
    def test_every_quote_is_in_the_manual_word_for_word(self) -> None:
        # Arrange
        quoted = [manual.flatten(one) for fact in FACTS.values() for one in quotes_of(fact)]

        # Act
        absent = [one for one in quoted if one not in MANUAL]

        # Assert
        self.assertEqual(absent, [])


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
        beyond = set(header.REGIONS) - printed

        # Assert
        self.assertEqual(beyond, {0x3, 0x5, 0x6, 0x7})

    def test_and_sizes_larger_than_any_it_prints(self) -> None:
        # Arrange
        printed = {int(code) & 0x0F for code in FACTS["sizeCodes"]["value"]}

        # Act
        beyond = set(header.SIZES) - printed

        # Assert
        self.assertEqual(beyond, {0x1, 0x2})


if __name__ == "__main__":
    unittest.main()
