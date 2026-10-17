import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import contextlib  # noqa: E402
import io  # noqa: E402
import unittest  # noqa: E402

from conformance import corpus  # noqa: E402


def combination(**fields: object) -> dict[str, object]:
    base: dict[str, object] = {
        "form": "bare",
        "size": 32768,
        "anchor": 0x7FF0,
        "region": "sms-export",
        "declared": 32768,
        "carried": True,
        "count": 1,
    }
    return {**base, **fields}


class ConsistentTest(unittest.TestCase):
    def test_a_recorded_combination_the_tables_allow_is_consistent(self) -> None:
        # Arrange
        recorded = combination()

        # Act
        found = corpus.inconsistencies([recorded])

        # Assert
        self.assertEqual(found, [])

    def test_an_anchor_no_candidate_names_is_reported(self) -> None:
        # Arrange
        recorded = combination(anchor=0x0100)

        # Act
        found = corpus.inconsistencies([recorded])

        # Assert
        self.assertEqual(found, ["anchor 0x100 is not a candidate"])

    def test_a_region_no_reading_names_is_reported(self) -> None:
        # Arrange
        recorded = combination(region="mars")

        # Act
        found = corpus.inconsistencies([recorded])

        # Assert
        self.assertEqual(found, ["region 'mars' is not one the reading knows"])

    def test_a_declared_size_no_nibble_names_is_reported(self) -> None:
        # Arrange
        recorded = combination(declared=12345)

        # Act
        found = corpus.inconsistencies([recorded])

        # Assert
        self.assertEqual(found, ["declared size 12345 is not one the reading knows"])

    def test_an_answer_recorded_where_no_checksum_can_exist_is_reported(self) -> None:
        # Arrange
        recorded = combination(anchor=None, region=None, declared=None, carried=True)

        # Act
        found = corpus.inconsistencies([recorded])

        # Assert
        self.assertEqual(found, ["carried True recorded where nothing can be compared"])

    def test_no_answer_recorded_where_one_must_exist_is_reported(self) -> None:
        # Arrange
        recorded = combination(carried=None)

        # Act
        found = corpus.inconsistencies([recorded])

        # Assert
        self.assertEqual(found, ["carried None recorded where a checksum exists"])

    def test_a_form_the_reader_does_not_name_is_reported(self) -> None:
        # Arrange
        recorded = combination(form="folded")

        # Act
        found = corpus.inconsistencies([recorded])

        # Assert
        self.assertEqual(found, ["form 'folded' is not one the reader names"])


class ShippedTest(unittest.TestCase):
    def test_every_recorded_combination_is_consistent_with_the_package(self) -> None:
        # Arrange
        recorded = corpus.load()

        # Act
        found = corpus.inconsistencies(recorded)

        # Assert
        self.assertEqual(found, [])

    def test_and_there_are_combinations_to_check(self) -> None:
        # Arrange
        minimum = 100

        # Act
        recorded = corpus.load()

        # Assert
        self.assertGreater(len(recorded), minimum)

    def test_the_readme_headline_holds_the_number_of_images_the_corpus_counts(self) -> None:
        # Arrange
        readme = (ROOT / "README.md").read_text()

        # Act
        figures = corpus.figures(corpus.load())

        # Assert
        claim = f"**{figures['images']:,}** distinct images"
        self.assertTrue(claim in readme, claim)

    def test_and_the_number_whose_header_is_read_at_the_usual_offset(self) -> None:
        # Arrange
        readme = (ROOT / "README.md").read_text()

        # Act
        figures = corpus.figures(corpus.load())

        # Assert
        claim = f"header read at `0x7FF0` on **{figures['at_7ff0']:,}**"
        self.assertTrue(claim in readme, claim)

    def test_and_how_many_reproduce_their_checksum_of_how_many_can(self) -> None:
        # Arrange
        readme = (ROOT / "README.md").read_text()

        # Act
        figures = corpus.figures(corpus.load())

        # Assert
        claim = f"{figures['agreed']:,} of {figures['judged']:,}"
        self.assertTrue(claim in readme, claim)


class FiguresTest(unittest.TestCase):
    def test_counts_are_weighted_by_how_many_images_share_a_combination(self) -> None:
        # Arrange
        recorded = [
            combination(count=3),
            combination(anchor=None, region=None, declared=None, carried=None, count=2),
        ]

        # Act
        found = corpus.figures(recorded)

        # Assert
        self.assertEqual(found, {"images": 5, "at_7ff0": 3, "agreed": 3, "judged": 3})


class MainTest(unittest.TestCase):
    def test_a_consistent_corpus_reports_what_it_examined(self) -> None:
        # Arrange
        said = io.StringIO()

        # Act
        with contextlib.redirect_stdout(said):
            code = corpus.main()

        # Assert
        self.assertEqual(code, 0)
        self.assertIn(
            "combinations replayed, every one consistent with the package", said.getvalue()
        )

    def test_an_inconsistent_corpus_names_each_fault_and_fails(self) -> None:
        # Arrange
        said = io.StringIO()

        # Act
        with contextlib.redirect_stdout(said):
            code = corpus.report([combination(anchor=0x0100)])

        # Assert
        self.assertEqual(code, 1)
        self.assertIn("anchor 0x100 is not a candidate", said.getvalue())


if __name__ == "__main__":
    unittest.main()
