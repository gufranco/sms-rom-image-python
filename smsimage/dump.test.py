import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tempfile  # noqa: E402
import unittest  # noqa: E402

from smsimage import dump  # noqa: E402


def synthetic(length: int, seed: int = 0) -> bytes:
    return bytes((seed + index * 7) & 0xFF for index in range(length))


class FormTest(unittest.TestCase):
    def test_a_whole_number_of_kilobytes_is_bare(self) -> None:
        found = dump.form(synthetic(32768))

        self.assertEqual(found, dump.BARE)

    def test_a_whole_number_of_kilobytes_plus_the_stub_is_stubbed(self) -> None:
        found = dump.form(synthetic(32768 + dump.STUB))

        self.assertEqual(found, dump.STUBBED)

    def test_a_length_that_is_neither_is_bare(self) -> None:
        found = dump.form(synthetic(49149))

        self.assertEqual(found, dump.BARE)

    def test_an_empty_image_is_bare(self) -> None:
        found = dump.form(b"")

        self.assertEqual(found, dump.BARE)

    def test_a_file_shorter_than_the_stub_is_bare(self) -> None:
        found = dump.form(synthetic(50))

        self.assertEqual(found, dump.BARE)

    def test_a_lone_stub_with_no_image_behind_it_is_bare(self) -> None:
        found = dump.form(synthetic(dump.STUB))

        self.assertEqual(found, dump.BARE)


class StripTest(unittest.TestCase):
    def test_stripping_a_stubbed_image_leaves_the_bytes_behind_it(self) -> None:
        image = synthetic(32768, seed=3)
        stubbed = synthetic(dump.STUB, seed=200) + image

        found = dump.strip_copier_stub(stubbed)

        self.assertEqual(found, image)

    def test_stripping_a_bare_image_changes_nothing(self) -> None:
        image = synthetic(32768)

        found = dump.strip_copier_stub(image)

        self.assertEqual(found, image)

    def test_stripping_twice_changes_nothing_the_second_time(self) -> None:
        stubbed = synthetic(dump.STUB, seed=9) + synthetic(32768)

        once = dump.strip_copier_stub(stubbed)
        twice = dump.strip_copier_stub(once)

        self.assertEqual(once, twice)


class ReadTest(unittest.TestCase):
    def test_it_returns_the_bytes_of_a_bare_file(self) -> None:
        image = synthetic(16384)
        with tempfile.TemporaryDirectory() as where:
            path = Path(where) / "bare.sms"
            path.write_bytes(image)

            found = dump.read(path)

        self.assertEqual(found, image)

    def test_it_returns_the_image_behind_a_stub(self) -> None:
        image = synthetic(16384, seed=5)
        with tempfile.TemporaryDirectory() as where:
            path = Path(where) / "stubbed.sms"
            path.write_bytes(synthetic(dump.STUB, seed=77) + image)

            found = dump.read(path)

        self.assertEqual(found, image)

    def test_it_reads_a_file_named_by_a_string_as_well(self) -> None:
        image = synthetic(8192)
        with tempfile.TemporaryDirectory() as where:
            path = Path(where) / "bare.gg"
            path.write_bytes(image)

            found = dump.read(str(path))

        self.assertEqual(found, image)


class SurfaceTest(unittest.TestCase):
    def test_the_two_forms_are_different_names(self) -> None:
        self.assertNotEqual(dump.BARE, dump.STUBBED)

    def test_the_stub_is_the_size_the_copiers_wrote(self) -> None:
        self.assertEqual(dump.STUB, 512)

    def test_the_rule_is_stated_in_terms_of_a_kilobyte(self) -> None:
        self.assertEqual(dump.STUB * 2, dump.ALIGNMENT)


if __name__ == "__main__":
    unittest.main()
