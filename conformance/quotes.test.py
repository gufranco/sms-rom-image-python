import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import quotes  # noqa: E402


def run_main(text: str) -> tuple[int, str]:
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        code = quotes.main(text)
    return code, said.getvalue()


class CollectedTest(unittest.TestCase):
    def test_a_single_quote_is_collected_with_where_it_sits(self) -> None:
        # Arrange
        record = {"facts": {"revision": {"quote": "A software revision number byte."}}}

        # Act
        found = quotes.passages(record, "hardware.json")

        # Assert
        self.assertEqual(
            found, [("hardware.json.facts.revision", "A software revision number byte.")]
        )

    def test_a_numbered_set_is_collected_one_by_one(self) -> None:
        # Arrange
        record = {"sizeCodes": {"quotes": ["$4C 32K", "$4D 48K"]}}

        # Act
        found = quotes.passages(record, "hardware.json")

        # Assert
        self.assertEqual(
            found,
            [("hardware.json.sizeCodes[0]", "$4C 32K"), ("hardware.json.sizeCodes[1]", "$4D 48K")],
        )

    def test_a_quote_inside_a_list_is_found(self) -> None:
        # Arrange
        record = {"divergences": [{"documentSays": {"quote": "$40 256K (2M)"}}]}

        # Act
        found = quotes.passages(record, "divergences.json")

        # Assert
        self.assertEqual(found, [("divergences.json.divergences[0].documentSays", "$40 256K (2M)")])

    def test_every_record_this_member_keeps_is_read(self) -> None:
        # Arrange
        expected = {"hardware.json", "divergences.json"}

        # Act
        found = {where.split(".json")[0] + ".json" for where, _ in quotes.collected()}

        # Assert
        self.assertEqual(found, expected)


class VerifyTest(unittest.TestCase):
    def test_a_quote_laid_out_across_spaces_is_still_found(self) -> None:
        # Arrange
        held = [("here", "$4A 8K (header at $1FF0)")]

        # Act
        absent = quotes.absent(held, "$4A         8K      (header at $1FF0)")

        # Assert
        self.assertEqual(absent, [])

    def test_a_quote_the_document_does_not_hold_is_named(self) -> None:
        # Arrange
        held = [("here", "A software revision number word.")]

        # Act
        absent = quotes.absent(held, "A software revision number byte.")

        # Assert
        self.assertEqual(absent, [("here", "A software revision number word.")])


class MainTest(unittest.TestCase):
    def test_without_the_manual_nothing_is_checked_and_the_run_says_so(self) -> None:
        # Arrange
        text = ""

        # Act
        code, said = run_main(text)

        # Assert
        self.assertEqual((code, "none was checked" in said), (0, True))

    def test_a_manual_holding_every_quote_passes(self) -> None:
        # Arrange
        text = " ".join(quote for _, quote in quotes.collected())

        # Act
        code, said = run_main(text)

        # Assert
        self.assertEqual((code, "0 not" in said), (0, True))

    def test_a_manual_missing_one_fails_and_names_it(self) -> None:
        # Arrange
        held = quotes.collected()
        text = " ".join(quote for _, quote in held[1:])

        # Act
        code, said = run_main(text)

        # Assert
        self.assertEqual((code, held[0][0] in said), (1, True))


if __name__ == "__main__":
    unittest.main()
