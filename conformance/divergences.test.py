import contextlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import corpus, divergences  # noqa: E402
from smsimage import header  # noqa: E402

HELD: dict[str, Any] = json.loads((ROOT / "conformance" / "divergences.json").read_text())

ENTRIES: dict[str, Any] = {entry["id"]: entry for entry in HELD["divergences"]}


ANCHOR = header.CANDIDATES[0]

THIRTY_TWO_K = 0x8000


def image(tail: bytes = b"  ", stored: int | None = None) -> bytes:
    held = bytearray(THIRTY_TWO_K)
    held[0] = 0x11
    held[ANCHOR : ANCHOR + len(header.MAGIC)] = header.MAGIC
    held[ANCHOR + len(header.MAGIC) : ANCHOR + len(header.MAGIC) + len(tail)] = tail
    held[ANCHOR + header.REGION_AND_SIZE] = 0x4C
    if stored is not None:
        held[ANCHOR + header.CHECKSUM.start : ANCHOR + header.CHECKSUM.stop] = stored.to_bytes(
            2, "little"
        )
    return bytes(held)


def manual_sum(held: bytes) -> int:
    checksum_bytes = held[ANCHOR + header.CHECKSUM.start : ANCHOR + header.CHECKSUM.stop]
    return (sum(held) - sum(checksum_bytes)) & 0xFFFF


def library(where: Path, images: list[bytes]) -> Path:
    path = where / "library.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for number, one in enumerate(images):
            archive.writestr(f"image-{number}.sms", one)
    return path


def run_main(argv: list[str]) -> tuple[int, str]:
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        code = divergences.main(argv)
    return code, said.getvalue()


def counted(text: str) -> int:
    return int(text.split(maxsplit=1)[0])


class RecordTest(unittest.TestCase):
    def test_every_entry_says_which_way_this_package_went(self) -> None:
        # Arrange
        allowed = {"document", "cartridges", "microcode"}

        # Act
        ways = {entry["packageFollows"] for entry in ENTRIES.values()}

        # Assert
        self.assertLessEqual(ways, allowed)

    def test_every_entry_is_open_narrowed_or_closed(self) -> None:
        # Arrange
        allowed = {"open", "narrowed", "closed"}

        # Act
        statuses = {entry["status"] for entry in ENTRIES.values()}

        # Assert
        self.assertLessEqual(statuses, allowed)

    def test_an_open_entry_says_what_would_close_it(self) -> None:
        # Arrange
        entries = ENTRIES.values()

        # Act
        silent = [
            entry["id"]
            for entry in entries
            if entry["status"] in ("open", "narrowed") and not entry.get("wouldCloseIt")
        ]

        # Assert
        self.assertEqual(silent, [])

    def test_a_closed_entry_says_what_would_reopen_it(self) -> None:
        # Arrange
        entries = ENTRIES.values()

        # Act
        silent = [
            entry["id"]
            for entry in entries
            if entry["status"] == "closed" and not entry.get("wouldReopenIt")
        ]

        # Assert
        self.assertEqual(silent, [])

    def test_every_entry_quotes_the_manual_and_names_the_page(self) -> None:
        # Arrange
        entries = ENTRIES.values()

        # Act
        unsourced = [
            entry["id"]
            for entry in entries
            if not entry["documentSays"]["quote"]
            or "page 22" not in entry["documentSays"]["source"]
        ]

        # Assert
        self.assertEqual(unsourced, [])


class MeasuredOnlyTest(unittest.TestCase):
    def test_a_figure_the_corpus_cannot_hold_names_the_command_that_measures_it(self) -> None:
        # Arrange
        measured_only = [
            ENTRIES["checksum-coverage"]["measured"],
            ENTRIES["opening-string-length"]["measured"],
        ]

        # Act
        commands = [one.get("measuredBy", "") for one in measured_only]

        # Assert
        self.assertEqual(
            [command.startswith("python3 -m conformance.divergences") for command in commands],
            [True, True],
        )


class CorpusFigureTest(unittest.TestCase):
    def test_the_package_rule_figure_is_the_one_the_corpus_counts(self) -> None:
        # Arrange
        figures = corpus.figures(corpus.load())

        # Act
        claimed = ENTRIES["checksum-coverage"]["measured"]["packageRule"]

        # Assert
        self.assertEqual(claimed, f"{figures['agreed']} of {figures['judged']} agree")

    def test_and_the_subjects_it_was_taken_over(self) -> None:
        # Arrange
        figures = corpus.figures(corpus.load())

        # Act
        claimed = ENTRIES["checksum-coverage"]["measured"]["subjects"]

        # Assert
        self.assertEqual(claimed, figures["judged"])

    def test_every_region_count_is_the_corpus_count(self) -> None:
        # Arrange
        measured = ENTRIES["unprinted-region-codes"]["measured"]
        names = {
            "smsJapan": header.SMS_JAPAN,
            "ggJapan": header.GG_JAPAN,
            "ggExport": header.GG_EXPORT,
            "ggInternational": header.GG_INTERNATIONAL,
        }

        # Act
        found = {
            key: sum(one["count"] for one in corpus.load() if one["region"] == region)
            for key, region in names.items()
        }

        # Assert
        self.assertEqual(found, {key: counted(measured[key]) for key in names})

    def test_every_size_count_is_the_corpus_count(self) -> None:
        # Arrange
        measured = ENTRIES["unprinted-size-codes"]["measured"]
        sizes = {"declared512K": header.SIZES[0x1], "declared1M": header.SIZES[0x2]}

        # Act
        found = {
            key: sum(one["count"] for one in corpus.load() if one["declared"] == size)
            for key, size in sizes.items()
        }

        # Assert
        self.assertEqual(found, {key: counted(measured[key]) for key in sizes})


class TailTest(unittest.TestCase):
    def test_a_header_carrying_the_two_printed_spaces_is_counted(self) -> None:
        # Arrange
        held = image(tail=b"  ")

        # Act
        found = divergences.carries_the_printed_tail(held)

        # Assert
        self.assertIs(found, True)

    def test_a_header_carrying_anything_else_there_is_not(self) -> None:
        # Arrange
        held = image(tail=b"\xff\xff")

        # Act
        found = divergences.carries_the_printed_tail(held)

        # Assert
        self.assertIs(found, False)

    def test_an_image_with_no_header_has_nothing_to_say(self) -> None:
        # Arrange
        held = bytes(THIRTY_TWO_K)

        # Act
        found = divergences.carries_the_printed_tail(held)

        # Assert
        self.assertIsNone(found)


class DocumentRuleTest(unittest.TestCase):
    def test_a_checksum_written_the_manual_s_way_agrees_with_it(self) -> None:
        # Arrange
        unsigned = image()
        held = image(stored=manual_sum(unsigned))

        # Act
        found = divergences.document_rule_agrees(held)

        # Assert
        self.assertIs(found, True)

    def test_a_checksum_written_the_package_s_way_does_not(self) -> None:
        # Arrange
        unsigned = image()
        held = image(stored=header.checksum(unsigned))

        # Act
        found = divergences.document_rule_agrees(held)

        # Assert
        self.assertIs(found, False)

    def test_a_declared_size_shorter_than_the_header_sums_without_leaving_bytes_out(self) -> None:
        # Arrange
        held = bytearray(image(stored=0x11))
        held[ANCHOR + header.REGION_AND_SIZE] = 0x4B

        # Act
        found = divergences.document_rule_agrees(bytes(held))

        # Assert
        self.assertIs(found, True)

    def test_an_image_with_no_header_has_nothing_to_say(self) -> None:
        # Arrange
        held = bytes(THIRTY_TWO_K)

        # Act
        found = divergences.document_rule_agrees(held)

        # Assert
        self.assertIsNone(found)


class TallyTest(unittest.TestCase):
    def test_counts_cover_every_image_and_only_the_ones_with_a_header(self) -> None:
        # Arrange
        images = [image(tail=b"  "), image(tail=b"\x00\x00"), bytes(THIRTY_TWO_K)]

        # Act
        found = divergences.tally(images)

        # Assert
        self.assertEqual(
            found,
            {
                "anchored": 2,
                "withTheTwoSpaces": 1,
                "judged": 2,
                "documentRuleAgrees": 0,
                "storesZero": 2,
                "packageRuleAgrees": 0,
            },
        )

    def test_a_stored_zero_and_an_agreeing_sum_are_counted_apart(self) -> None:
        # Arrange
        unsigned = image()
        images = [image(stored=header.checksum(unsigned)), image(stored=0)]

        # Act
        found = divergences.tally(images)

        # Assert
        self.assertEqual((found["storesZero"], found["packageRuleAgrees"]), (1, 1))

    def test_the_same_image_listed_twice_is_counted_once(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp())
        path = library(where, [image(), image()])

        # Act
        found = divergences.distinct_images([path])

        # Assert
        self.assertEqual(len(found), 1)


class TailsTest(unittest.TestCase):
    def test_the_bytes_after_the_magic_are_counted_most_common_first(self) -> None:
        # Arrange
        images = [image(tail=b"\x00\x00"), image(tail=b"\x00\x00"), image(tail=b"  ")]

        # Act
        found = divergences.tails(images)

        # Assert
        self.assertEqual(found, [("0000", 2), ("2020", 1)])

    def test_an_image_with_no_header_adds_nothing(self) -> None:
        # Arrange
        images = [bytes(THIRTY_TWO_K)]

        # Act
        found = divergences.tails(images)

        # Assert
        self.assertEqual(found, [])


class MainTest(unittest.TestCase):
    def test_naming_no_library_explains_how_to_call_it(self) -> None:
        # Arrange
        argv: list[str] = []

        # Act
        code, said = run_main(argv)

        # Assert
        self.assertEqual((code, "usage" in said), (2, True))

    def test_a_library_holding_no_header_measures_nothing_and_fails(self) -> None:
        # Arrange
        path = library(Path(tempfile.mkdtemp()), [bytes(THIRTY_TWO_K)])

        # Act
        code, said = run_main([str(path)])

        # Assert
        self.assertEqual((code, "nothing was examined" in said), (1, True))

    def test_a_library_reports_both_measurements(self) -> None:
        # Arrange
        path = library(Path(tempfile.mkdtemp()), [image(tail=b"  ")])

        # Act
        code, said = run_main([str(path)])

        # Assert
        self.assertEqual(code, 0)
        self.assertIn("the two printed spaces: 1 of 1", said)
        self.assertIn("the manual's checksum rule: 0 of 1", said)
        self.assertIn("after the magic: 2020 on 1", said)
        self.assertIn("storing zero: 1 of 1", said)
        self.assertIn("the package's checksum rule: 0 of 1", said)


if __name__ == "__main__":
    unittest.main()
