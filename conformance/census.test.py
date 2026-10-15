import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import contextlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402
import zipfile  # noqa: E402
from typing import Any  # noqa: E402

from conformance import census  # noqa: E402
from smsimage import dump, header, identity  # noqa: E402


def synthetic(length: int, seed: int = 0) -> bytearray:
    return bytearray((seed + index * 13) & 0xFF for index in range(length))


def always_agrees(image: bytes) -> bool | None:
    return True


def never_strips_completely(data: bytes) -> bytes:
    return data[1:]


def anchor_outside_the_candidates(image: bytes) -> int | None:
    return 0x0100


def anchor_with_nothing_under_it(image: bytes) -> int | None:
    return header.CANDIDATES[2]


def checksum_too_wide(image: bytes) -> int | None:
    return 0x1_0000


def with_header(length: int, at: int, region_and_size: int = 0x4C) -> bytes:
    image = synthetic(length)
    image[at : at + len(header.MAGIC)] = header.MAGIC
    image[at + 0x08 : at + 0x10] = bytes(8)
    image[at + header.REGION_AND_SIZE] = region_and_size
    computed = header.checksum(bytes(image))
    assert computed is not None
    image[at + 0x0A : at + 0x0C] = computed.to_bytes(2, "little")
    return bytes(image)


class PropertyTest(unittest.TestCase):
    def test_a_sealed_image_holds_every_property(self) -> None:
        broken = census.broken_properties(with_header(32768, 0x7FF0))

        self.assertEqual(broken, [])

    def test_a_headerless_image_holds_every_property(self) -> None:
        broken = census.broken_properties(bytes(synthetic(32768)))

        self.assertEqual(broken, [])

    def test_a_stubbed_image_holds_every_property(self) -> None:
        stubbed = bytes(synthetic(512, seed=9)) + with_header(32768, 0x7FF0)

        broken = census.broken_properties(stubbed)

        self.assertEqual(broken, [])

    def fires(self, module: Any, name: str, instead: Any, image: bytes) -> list[str]:
        original = getattr(module, name)
        setattr(module, name, instead)
        try:
            return census.broken_properties(image)
        finally:
            setattr(module, name, original)

    def test_a_strip_that_removes_more_each_time_is_reported(self) -> None:
        broken = self.fires(
            dump, "strip_copier_stub", never_strips_completely, with_header(32768, 0x7FF0)
        )

        self.assertIn(census.IDEMPOTENT_STRIP, broken)

    def test_an_anchor_that_is_not_a_candidate_is_reported(self) -> None:
        broken = self.fires(
            header, "anchor_of", anchor_outside_the_candidates, with_header(32768, 0x7FF0)
        )

        self.assertIn(census.ANCHOR_IS_A_CANDIDATE, broken)

    def test_an_anchor_with_no_magic_under_it_is_reported(self) -> None:
        broken = self.fires(
            header, "anchor_of", anchor_with_nothing_under_it, bytes(synthetic(32768))
        )

        self.assertIn(census.MAGIC_AT_THE_ANCHOR, broken)

    def test_a_checksum_outside_sixteen_bits_is_reported(self) -> None:
        broken = self.fires(header, "checksum", checksum_too_wide, with_header(32768, 0x7FF0))

        self.assertIn(census.CHECKSUM_IN_RANGE, broken)

    def test_agreement_answered_without_a_checksum_is_reported(self) -> None:
        broken = self.fires(header, "agrees", always_agrees, bytes(synthetic(32768)))

        self.assertIn(census.AGREEMENT_FOLLOWS_A_CHECKSUM, broken)

    def test_a_measurement_that_changes_between_calls_is_reported(self) -> None:
        counter = iter(range(2))

        def measures_differently(image: bytes) -> dict[str, int]:
            return {"n": next(counter)}

        broken = self.fires(identity, "measure", measures_differently, with_header(32768, 0x7FF0))

        self.assertIn(census.MEASUREMENT_IS_STABLE, broken)

    def test_every_property_it_declares_is_named_once(self) -> None:
        self.assertEqual(sorted(set(census.PROPERTIES)), sorted(census.PROPERTIES))

    def test_every_property_it_declares_can_be_reported(self) -> None:
        reported = {
            census.IDEMPOTENT_STRIP,
            census.ANCHOR_IS_A_CANDIDATE,
            census.MAGIC_AT_THE_ANCHOR,
            census.CHECKSUM_IN_RANGE,
            census.AGREEMENT_FOLLOWS_A_CHECKSUM,
            census.MEASUREMENT_IS_STABLE,
        }

        self.assertEqual(reported, set(census.PROPERTIES))


class ObservationTest(unittest.TestCase):
    def test_a_sealed_image_reproduces_its_carried_value(self) -> None:
        found = census.observe(with_header(32768, 0x7FF0))

        self.assertTrue(found["carried"])

    def test_an_image_whose_content_moved_does_not(self) -> None:
        image = bytearray(with_header(32768, 0x7FF0))
        image[0x0100] ^= 0xFF

        found = census.observe(bytes(image))

        self.assertFalse(found["carried"])

    def test_a_headerless_image_carries_nothing_to_compare(self) -> None:
        found = census.observe(bytes(synthetic(32768)))

        self.assertIsNone(found["carried"])
        self.assertIsNone(found["anchor"])

    def test_it_records_where_the_header_sat_and_what_it_declared(self) -> None:
        found = census.observe(with_header(32768, 0x7FF0, 0x4C))

        self.assertEqual(found["anchor"], 0x7FF0)
        self.assertEqual(found["region"], header.SMS_EXPORT)
        self.assertEqual(found["declared"], 32768)

    def test_it_records_the_length_after_any_stub_is_removed(self) -> None:
        stubbed = bytes(synthetic(512)) + with_header(32768, 0x7FF0)

        found = census.observe(stubbed)

        self.assertEqual(found["size"], 32768)
        self.assertEqual(found["form"], "stubbed")

    def test_it_records_no_title_and_nothing_of_the_content(self) -> None:
        found = census.observe(with_header(32768, 0x7FF0))

        self.assertEqual(
            sorted(found),
            ["anchor", "carried", "declared", "form", "region", "size"],
        )


class WalkTest(unittest.TestCase):
    def test_it_reads_images_out_of_a_directory(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "one.sms").write_bytes(with_header(32768, 0x7FF0))
            (Path(where) / "two.gg").write_bytes(bytes(synthetic(16384)))

            found = list(census.images_in(Path(where)))

        self.assertEqual(len(found), 2)

    def test_it_reads_images_out_of_an_archive(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            bundle = Path(where) / "pack.zip"
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("a/one.sms", with_header(32768, 0x7FF0))
                archive.writestr("a/two.gg", bytes(synthetic(16384)))

            found = list(census.images_in(bundle))

        self.assertEqual(len(found), 2)

    def test_it_ignores_a_file_that_is_not_a_cartridge_image(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "notes.txt").write_text("not an image")
            (Path(where) / "one.sms").write_bytes(with_header(32768, 0x7FF0))

            found = list(census.images_in(Path(where)))

        self.assertEqual(len(found), 1)

    def test_it_reads_an_image_named_directly(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            path = Path(where) / "one.sms"
            path.write_bytes(with_header(32768, 0x7FF0))

            found = list(census.images_in(path))

        self.assertEqual(len(found), 1)

    def test_a_directory_entry_inside_an_archive_is_not_an_image(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            bundle = Path(where) / "pack.zip"
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("a/", b"")
                archive.writestr("a/one.sms", with_header(32768, 0x7FF0))
                archive.writestr("a/notes.txt", b"not an image")

            found = list(census.images_in(bundle))

        self.assertEqual(len(found), 1)

    def test_a_file_that_is_neither_an_archive_nor_an_image_reads_as_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            path = Path(where) / "notes.txt"
            path.write_text("not an image")

            found = list(census.images_in(path))

        self.assertEqual(found, [])

    def test_a_path_that_is_neither_reads_as_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            found = list(census.images_in(Path(where) / "absent"))

        self.assertEqual(found, [])


class TakeTest(unittest.TestCase):
    def test_it_counts_distinct_images_rather_than_filenames(self) -> None:
        image = with_header(32768, 0x7FF0)
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "one.sms").write_bytes(image)
            (Path(where) / "again.sms").write_bytes(image)

            taken = census.take([Path(where)])

        self.assertEqual(taken["distinct"], 1)
        self.assertEqual(taken["listings"], 2)

    def test_it_reports_zero_explicitly_when_it_examined_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            taken = census.take([Path(where)])

        self.assertEqual(taken["distinct"], 0)
        self.assertEqual(taken["broken"], {})

    def test_it_names_every_image_that_broke_a_property(self) -> None:
        original: Any = header.agrees
        header.agrees = always_agrees
        try:
            with tempfile.TemporaryDirectory() as where:
                (Path(where) / "bad.sms").write_bytes(bytes(synthetic(8192)))

                taken = census.take([Path(where)])
        finally:
            header.agrees = original

        self.assertEqual(taken["broken"], {census.AGREEMENT_FOLLOWS_A_CHECKSUM: 1})

    def test_the_corpus_it_builds_holds_combinations_and_no_content(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "one.sms").write_bytes(with_header(32768, 0x7FF0))

            taken = census.take([Path(where)])

        combination = taken["corpus"][0]
        self.assertEqual(
            sorted(combination),
            ["anchor", "carried", "count", "declared", "form", "region", "size"],
        )

    def test_two_images_sharing_a_combination_are_counted_together(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "one.sms").write_bytes(with_header(32768, 0x7FF0))
            (Path(where) / "two.sms").write_bytes(with_header(32768, 0x7FF0, 0x4C))
            (Path(where) / "three.sms").write_bytes(bytes(synthetic(8192)))

            taken = census.take([Path(where)])

        self.assertEqual(len(taken["corpus"]), 2)


class RenderTest(unittest.TestCase):
    def test_the_committed_corpus_is_written_back_byte_for_byte(self) -> None:
        # Arrange
        committed = census.CORPUS.read_text()

        # Act
        written = census.rendered(json.loads(committed))

        # Assert
        self.assertEqual(written, committed)


class ReportTest(unittest.TestCase):
    def run_over(self, *paths: Path) -> tuple[int, str, Path]:
        into = Path(tempfile.mkdtemp()) / "corpus.json"
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            code = census.main([str(one) for one in paths], into=into)
        return code, captured.getvalue(), into

    def test_naming_no_path_explains_how_to_call_it(self) -> None:
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            code = census.main([])

        self.assertEqual(code, 2)
        self.assertIn("usage", captured.getvalue())

    def test_a_path_that_is_not_there_is_named_rather_than_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            code, said, _ = self.run_over(Path(where) / "absent")

        self.assertEqual(code, 1)
        self.assertIn("absent", said)

    def test_examining_nothing_says_so_rather_than_reporting_a_pass(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            code, said, _ = self.run_over(Path(where))

        self.assertEqual(code, 0)
        self.assertIn("nothing was examined", said)

    def test_a_library_it_can_read_is_reported_with_its_counts(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "one.sms").write_bytes(with_header(32768, 0x7FF0))
            (Path(where) / "two.sms").write_bytes(bytes(synthetic(8192)))

            code, said, into = self.run_over(Path(where))

        self.assertEqual(code, 0)
        self.assertIn("distinct images:                2", said)
        self.assertIn("properties held on 2 of 2", said)
        self.assertIn("carried    true of 1 of 1", said)
        self.assertEqual(len(json.loads(into.read_text())), 2)

    def test_a_broken_property_is_named_and_fails_the_run(self) -> None:
        original: Any = header.agrees
        header.agrees = always_agrees
        try:
            with tempfile.TemporaryDirectory() as where:
                (Path(where) / "bad.sms").write_bytes(bytes(synthetic(8192)))

                code, said, _ = self.run_over(Path(where))
        finally:
            header.agrees = original

        self.assertEqual(code, 1)
        self.assertIn("broken", said)
        self.assertIn(census.AGREEMENT_FOLLOWS_A_CHECKSUM, said)


if __name__ == "__main__":
    unittest.main()
