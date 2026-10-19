import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402
from functools import partial  # noqa: E402

from smsimage import doctor  # noqa: E402

COPIER_BLOCK = 512

DECLARED_BOOT_PROGRAMS = 14


def broken(_: object = None) -> bytes:
    raise ValueError("this build refuses")


class Scratch(unittest.TestCase):
    def folder(self) -> Path:
        held = tempfile.TemporaryDirectory()
        self.addCleanup(held.cleanup)
        return Path(held.name)

    def file_holding(self, name: str, text: str) -> Path:
        path = self.folder() / name
        path.write_text(text)
        return path


class PythonTest(unittest.TestCase):
    def test_the_interpreter_running_this_is_new_enough(self) -> None:
        # Arrange
        oldest = doctor.OLDEST_PYTHON

        # Act
        found = doctor.check_python()

        # Assert
        self.assertEqual((found.ok, oldest), (True, (3, 12)))


class PackageTest(unittest.TestCase):
    def test_the_package_this_repository_ships_imports(self) -> None:
        # Arrange
        expected = f"smsimage {doctor.VERSION} imported from {doctor.ROOT}"

        # Act
        found = doctor.check_package()

        # Assert
        self.assertEqual((found.ok, found.detail), (True, expected))

    def test_a_package_that_will_not_import_is_reported_by_what_it_threw(self) -> None:
        # Arrange
        load = broken

        # Act
        found = doctor.check_package(load)

        # Assert
        self.assertEqual((found.ok, found.detail), (False, "ValueError: this build refuses"))


class SealedImageTest(unittest.TestCase):
    def test_the_image_it_builds_is_a_whole_32k_cartridge(self) -> None:
        # Arrange
        expected = 0x8000

        # Act
        image = doctor.sealed_image()

        # Assert
        self.assertEqual(len(image), expected)

    def test_a_sum_that_finds_no_checksum_is_a_fault(self) -> None:
        # Arrange
        def nothing(_: bytes) -> int | None:
            return None

        # Act
        building = partial(doctor.sealed_image, nothing)

        # Assert
        with self.assertRaises(ValueError):
            building()


class DrivingTest(unittest.TestCase):
    def test_it_reads_a_dump_it_built_here(self) -> None:
        # Arrange
        build = doctor.sealed_image

        # Act
        found = doctor.check_reading(build)

        # Assert
        self.assertTrue(found.ok)

    def test_the_dump_it_reads_carries_a_whole_copier_block(self) -> None:
        # Arrange
        image = doctor.sealed_image()

        # Act
        found = doctor.check_reading()

        # Assert
        self.assertEqual(
            found.detail,
            f"a {len(image) + COPIER_BLOCK} byte dump read back to {len(image)} bytes, "
            f"and again to {len(image)}",
        )

    def test_a_reader_that_refuses_is_reported_by_what_it_threw(self) -> None:
        # Arrange
        build = broken

        # Act
        found = doctor.check_reading(build)

        # Assert
        self.assertEqual((found.ok, found.detail), (False, "ValueError: this build refuses"))

    def test_it_finds_a_header_in_an_image_it_built_here(self) -> None:
        # Arrange
        build = doctor.sealed_image

        # Act
        found = doctor.check_anchoring(build)

        # Assert
        self.assertEqual(
            (found.ok, found.detail),
            (True, "a header at 0x7ff0 declaring sms-export and 32768 bytes"),
        )

    def test_an_image_with_no_header_is_reported_as_one(self) -> None:
        # Arrange
        def bare() -> bytes:
            return bytes(0x8000)

        # Act
        found = doctor.check_anchoring(bare)

        # Assert
        self.assertEqual(
            (found.ok, found.detail), (False, "no header was found in an image built with one")
        )

    def test_an_anchor_that_refuses_is_reported_by_what_it_threw(self) -> None:
        # Arrange
        build = broken

        # Act
        found = doctor.check_anchoring(build)

        # Assert
        self.assertEqual((found.ok, found.detail), (False, "ValueError: this build refuses"))

    def test_it_reproduces_a_checksum_on_an_image_it_sealed_here(self) -> None:
        # Arrange
        build = doctor.sealed_image

        # Act
        found = doctor.check_checksumming(build)

        # Assert
        self.assertTrue(found.ok)

    def test_an_image_with_no_checksum_is_reported_as_one(self) -> None:
        # Arrange
        def bare() -> bytes:
            return bytes(0x8000)

        # Act
        found = doctor.check_checksumming(bare)

        # Assert
        self.assertEqual(
            (found.ok, found.detail), (False, "an image sealed here produced no checksum")
        )

    def test_a_checksum_that_refuses_is_reported_by_what_it_threw(self) -> None:
        # Arrange
        build = broken

        # Act
        found = doctor.check_checksumming(build)

        # Assert
        self.assertEqual((found.ok, found.detail), (False, "ValueError: this build refuses"))

    def test_it_measures_an_image_it_built_here(self) -> None:
        # Arrange
        build = doctor.sealed_image

        # Act
        found = doctor.check_measuring(build)

        # Assert
        self.assertEqual((found.ok, found.detail.endswith(" for 32768 bytes")), (True, True))

    def test_a_measurement_that_refuses_is_reported_by_what_it_threw(self) -> None:
        # Arrange
        build = broken

        # Act
        found = doctor.check_measuring(build)

        # Assert
        self.assertEqual((found.ok, found.detail), (False, "ValueError: this build refuses"))


class ArtifactTest(Scratch):
    def test_it_reads_the_manifest_this_repository_ships(self) -> None:
        # Arrange
        expected = f"{DECLARED_BOOT_PROGRAMS} boot programs declared, none of them here"

        # Act
        found = doctor.check_artifacts()

        # Assert
        self.assertEqual((found.ok, found.detail), (True, expected))

    def test_a_manifest_that_is_not_there_is_reported_as_absent(self) -> None:
        # Arrange
        path = self.folder() / "artifacts.manifest.json"

        # Act
        found = doctor.check_artifacts(path)

        # Assert
        self.assertEqual((found.ok, found.detail), (False, f"not here: {path}"))

    def test_a_manifest_that_is_not_one_is_reported_by_what_it_threw(self) -> None:
        # Arrange
        path = self.file_holding("artifacts.manifest.json", '{"note": "nothing here yet"}')

        # Act
        found = doctor.check_artifacts(path)

        # Assert
        self.assertEqual((found.ok, found.detail.split(":")[0]), (False, "Malformed"))


class CorpusTest(Scratch):
    def test_it_reads_the_corpus_this_repository_ships(self) -> None:
        # Arrange
        combinations = json.loads((ROOT / "conformance" / "corpus.json").read_text())
        images = 2922

        # Act
        found = doctor.check_corpus()

        # Assert
        self.assertEqual(
            (found.ok, found.detail),
            (True, f"{len(combinations)} combinations from {images} images"),
        )

    def test_a_corpus_that_is_not_there_is_reported_as_absent(self) -> None:
        # Arrange
        path = self.folder() / "corpus.json"

        # Act
        found = doctor.check_corpus(path)

        # Assert
        self.assertEqual((found.ok, found.detail), (False, f"not here: {path}"))

    def test_a_corpus_holding_nothing_is_told_apart_from_one_that_is_missing(self) -> None:
        # Arrange
        path = self.file_holding("corpus.json", "[]")

        # Act
        found = doctor.check_corpus(path)

        # Assert
        self.assertEqual((found.ok, found.detail), (False, f"holds nothing: {path}"))

    def test_a_corpus_that_will_not_parse_is_reported_by_what_it_threw(self) -> None:
        # Arrange
        path = self.file_holding("corpus.json", "{not json")

        # Act
        found = doctor.check_corpus(path)

        # Assert
        self.assertEqual((found.ok, found.detail.split(":")[0]), (False, "JSONDecodeError"))


class LibraryTest(unittest.TestCase):
    def test_it_says_the_census_takes_its_library_as_an_argument(self) -> None:
        # Arrange
        expected = (
            "the census takes the library to walk as an argument, "
            "so there is nothing to be set wrongly"
        )

        # Act
        found = doctor.check_library()

        # Assert
        self.assertEqual((found.ok, found.detail), (True, expected))


class ShippedTest(unittest.TestCase):
    def test_the_manifest_it_reads_declares_what_the_file_declares(self) -> None:
        # Arrange
        declared = json.loads((ROOT / "artifacts.manifest.json").read_text())["artifacts"]

        # Act
        found = doctor.check_artifacts()

        # Assert
        self.assertEqual(found.detail, f"{len(declared)} boot programs declared, none of them here")


if __name__ == "__main__":
    unittest.main()
