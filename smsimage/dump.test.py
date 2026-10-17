import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tempfile  # noqa: E402
import unittest  # noqa: E402

import smsimage  # noqa: E402
from smsimage import dump  # noqa: E402

COPIER_BLOCK = 512


def synthetic(length: int, seed: int = 0) -> bytes:
    return bytes((seed + index * 7) & 0xFF for index in range(length))


class FormTest(unittest.TestCase):
    def test_a_whole_number_of_kilobytes_is_bare(self) -> None:
        # Arrange
        data = synthetic(32768)

        # Act
        found = dump.form(data)

        # Assert
        self.assertEqual(found, "bare")

    def test_a_whole_number_of_kilobytes_plus_the_stub_is_stubbed(self) -> None:
        # Arrange
        data = synthetic(32768 + COPIER_BLOCK)

        # Act
        found = dump.form(data)

        # Assert
        self.assertEqual(found, "stubbed")

    def test_a_length_that_is_neither_is_bare(self) -> None:
        # Arrange
        data = synthetic(49149)

        # Act
        found = dump.form(data)

        # Assert
        self.assertEqual(found, "bare")

    def test_an_empty_image_is_bare(self) -> None:
        # Arrange
        data = b""

        # Act
        found = dump.form(data)

        # Assert
        self.assertEqual(found, "bare")

    def test_a_file_shorter_than_the_stub_is_bare(self) -> None:
        # Arrange
        data = synthetic(50)

        # Act
        found = dump.form(data)

        # Assert
        self.assertEqual(found, "bare")

    def test_a_lone_stub_with_no_image_behind_it_is_bare(self) -> None:
        # Arrange
        data = synthetic(COPIER_BLOCK)

        # Act
        found = dump.form(data)

        # Assert
        self.assertEqual(found, "bare")

    def test_the_lengths_the_readme_works_through_read_as_it_prints(self) -> None:
        # Arrange
        lengths = (512, 1536, 32768, 33280)

        # Act
        found = [dump.form(bytes(length)) for length in lengths]

        # Assert
        self.assertEqual(found, ["bare", "stubbed", "bare", "stubbed"])

    def test_the_test_is_a_kilobyte_and_a_half_not_a_byte_either_side(self) -> None:
        # Arrange
        lengths = (1535, 1536, 1537, 2048, 2560)

        # Act
        found = [dump.form(bytes(length)) for length in lengths]

        # Assert
        self.assertEqual(found, ["bare", "stubbed", "bare", "bare", "stubbed"])

    def test_the_two_forms_are_published_under_the_names_it_returns(self) -> None:
        # Arrange
        published = (smsimage.BARE, smsimage.STUBBED)

        # Act
        found = (dump.form(bytes(32768)), dump.form(bytes(33280)))

        # Assert
        self.assertEqual(found, published)


class StripTest(unittest.TestCase):
    def test_stripping_a_stubbed_image_leaves_the_bytes_behind_it(self) -> None:
        # Arrange
        image = synthetic(32768, seed=3)
        stubbed = synthetic(COPIER_BLOCK, seed=200) + image

        # Act
        found = dump.strip_copier_stub(stubbed)

        # Assert
        self.assertEqual(found, image)

    def test_stripping_a_bare_image_changes_nothing(self) -> None:
        # Arrange
        image = synthetic(32768)

        # Act
        found = dump.strip_copier_stub(image)

        # Assert
        self.assertEqual(found, image)

    def test_stripping_twice_changes_nothing_the_second_time(self) -> None:
        # Arrange
        once = dump.strip_copier_stub(synthetic(COPIER_BLOCK, seed=9) + synthetic(32768))

        # Act
        twice = dump.strip_copier_stub(once)

        # Assert
        self.assertEqual(twice, once)

    def test_the_block_removed_is_512_bytes_long(self) -> None:
        # Arrange
        lengths = (1536, 33280)

        # Act
        found = [len(dump.strip_copier_stub(bytes(length))) for length in lengths]

        # Assert
        self.assertEqual(found, [1024, 32768])


class ReadTest(unittest.TestCase):
    def written(self, name: str, data: bytes) -> Path:
        held = tempfile.TemporaryDirectory()
        self.addCleanup(held.cleanup)
        path = Path(held.name) / name
        path.write_bytes(data)
        return path

    def test_it_returns_the_bytes_of_a_bare_file(self) -> None:
        # Arrange
        image = synthetic(16384)
        path = self.written("bare.sms", image)

        # Act
        found = dump.read(path)

        # Assert
        self.assertEqual(found, image)

    def test_it_returns_the_image_behind_a_stub(self) -> None:
        # Arrange
        image = synthetic(16384, seed=5)
        path = self.written("stubbed.sms", synthetic(COPIER_BLOCK, seed=77) + image)

        # Act
        found = dump.read(path)

        # Assert
        self.assertEqual(found, image)

    def test_it_reads_a_file_named_by_a_string_as_well(self) -> None:
        # Arrange
        image = synthetic(8192)
        path = self.written("bare.gg", image)

        # Act
        found = dump.read(str(path))

        # Assert
        self.assertEqual(found, image)


if __name__ == "__main__":
    unittest.main()
