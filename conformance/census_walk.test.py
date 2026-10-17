import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import contextlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import tempfile  # noqa: E402
import types  # noqa: E402
import unittest  # noqa: E402
import zipfile  # noqa: E402
from typing import Any  # noqa: E402

import smsimage  # noqa: E402
from conformance import census  # noqa: E402
from smsimage import header  # noqa: E402

MAGIC = b"TMR SEGA"

REGION_AND_SIZE = 0x0F

CHECKSUM = 0x0A


def synthetic(length: int, seed: int = 0) -> bytearray:
    return bytearray((seed + index * 13) & 0xFF for index in range(length))


def always_agrees(image: bytes) -> bool | None:
    return True


def replaced(module: str, name: str, instead: Any) -> Any:
    modules = {one: getattr(smsimage, one) for one in ("dump", "header", "identity")}
    swapped = types.SimpleNamespace(**{**vars(modules[module]), name: instead})
    return types.SimpleNamespace(**{**modules, module: swapped})


def with_header(length: int, at: int, region_and_size: int = 0x4C) -> bytes:
    image = synthetic(length)
    image[at : at + len(MAGIC)] = MAGIC
    image[at + 0x08 : at + 0x10] = bytes(8)
    image[at + REGION_AND_SIZE] = region_and_size
    computed = header.checksum(bytes(image))
    assert computed is not None
    image[at + CHECKSUM : at + CHECKSUM + 2] = computed.to_bytes(2, "little")
    return bytes(image)


class Scratch(unittest.TestCase):
    def folder(self) -> Path:
        held = tempfile.TemporaryDirectory()
        self.addCleanup(held.cleanup)
        return Path(held.name)

    def holding(self, files: dict[str, bytes]) -> Path:
        where = self.folder()
        for name, body in files.items():
            (where / name).write_bytes(body)
        return where

    def archive(self, entries: dict[str, bytes]) -> Path:
        bundle = self.folder() / "pack.zip"
        with zipfile.ZipFile(bundle, "w") as written:
            for name, body in entries.items():
                written.writestr(name, body)
        return bundle


class WalkTest(Scratch):
    def test_it_reads_images_out_of_a_directory(self) -> None:
        # Arrange
        where = self.holding(
            {"one.sms": with_header(32768, 0x7FF0), "two.gg": bytes(synthetic(16384))}
        )

        # Act
        found = list(census.images_in(where))

        # Assert
        self.assertEqual(len(found), 2)

    def test_it_reads_images_out_of_an_archive(self) -> None:
        # Arrange
        bundle = self.archive(
            {"a/one.sms": with_header(32768, 0x7FF0), "a/two.gg": bytes(synthetic(16384))}
        )

        # Act
        found = list(census.images_in(bundle))

        # Assert
        self.assertEqual(len(found), 2)

    def test_it_ignores_a_file_that_is_not_a_cartridge_image(self) -> None:
        # Arrange
        where = self.holding({"notes.txt": b"not an image", "one.sms": with_header(32768, 0x7FF0)})

        # Act
        found = list(census.images_in(where))

        # Assert
        self.assertEqual(len(found), 1)

    def test_it_reads_an_image_named_directly(self) -> None:
        # Arrange
        path = self.holding({"one.sms": with_header(32768, 0x7FF0)}) / "one.sms"

        # Act
        found = list(census.images_in(path))

        # Assert
        self.assertEqual(len(found), 1)

    def test_a_directory_entry_inside_an_archive_is_not_an_image(self) -> None:
        # Arrange
        bundle = self.archive(
            {
                "a/": b"",
                "a/one.sms": with_header(32768, 0x7FF0),
                "a/notes.txt": b"not an image",
            }
        )

        # Act
        found = list(census.images_in(bundle))

        # Assert
        self.assertEqual(len(found), 1)

    def test_a_file_that_is_neither_an_archive_nor_an_image_reads_as_nothing(self) -> None:
        # Arrange
        path = self.holding({"notes.txt": b"not an image"}) / "notes.txt"

        # Act
        found = list(census.images_in(path))

        # Assert
        self.assertEqual(found, [])

    def test_a_path_that_is_neither_reads_as_nothing(self) -> None:
        # Arrange
        path = self.folder() / "absent"

        # Act
        found = list(census.images_in(path))

        # Assert
        self.assertEqual(found, [])


class TakeTest(Scratch):
    def test_it_counts_distinct_images_rather_than_filenames(self) -> None:
        # Arrange
        image = with_header(32768, 0x7FF0)
        where = self.holding({"one.sms": image, "again.sms": image})

        # Act
        taken = census.take([where])

        # Assert
        self.assertEqual((taken["distinct"], taken["listings"]), (1, 2))

    def test_it_reports_zero_explicitly_when_it_examined_nothing(self) -> None:
        # Arrange
        where = self.folder()

        # Act
        taken = census.take([where])

        # Assert
        self.assertEqual((taken["distinct"], taken["broken"]), (0, {}))

    def test_it_names_every_image_that_broke_a_property(self) -> None:
        # Arrange
        where = self.holding({"bad.sms": bytes(synthetic(8192))})
        package = replaced("header", "agrees", always_agrees)

        # Act
        taken = census.take([where], package)

        # Assert
        self.assertEqual(taken["broken"], {census.AGREEMENT_FOLLOWS_A_CHECKSUM: 1})

    def test_the_corpus_it_builds_holds_combinations_and_no_content(self) -> None:
        # Arrange
        where = self.holding({"one.sms": with_header(32768, 0x7FF0)})

        # Act
        taken = census.take([where])

        # Assert
        self.assertEqual(
            taken["corpus"],
            [
                {
                    "anchor": 0x7FF0,
                    "carried": True,
                    "declared": 32768,
                    "form": "bare",
                    "region": "sms-export",
                    "size": 32768,
                    "count": 1,
                }
            ],
        )

    def test_two_images_sharing_a_combination_are_counted_together(self) -> None:
        # Arrange
        where = self.holding(
            {
                "one.sms": with_header(32768, 0x7FF0),
                "two.sms": with_header(32768, 0x7FF0, 0x4C),
                "three.sms": bytes(synthetic(8192)),
            }
        )

        # Act
        taken = census.take([where])

        # Assert
        self.assertEqual(len(taken["corpus"]), 2)


class ReportTest(Scratch):
    def run_over(self, *paths: Path, package: Any = smsimage) -> tuple[int, str, Path]:
        into = self.folder() / "corpus.json"
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            code = census.main([str(one) for one in paths], into=into, package=package)
        return code, captured.getvalue(), into

    def test_naming_no_path_explains_how_to_call_it(self) -> None:
        # Arrange
        captured = io.StringIO()

        # Act
        with contextlib.redirect_stdout(captured):
            code = census.main([])

        # Assert
        self.assertEqual(
            (code, captured.getvalue()),
            (2, "usage: python3 -m conformance.census <path> [path ...]\n"),
        )

    def test_a_path_that_is_not_there_is_named_rather_than_ignored(self) -> None:
        # Arrange
        absent = self.folder() / "absent"

        # Act
        code, said, _ = self.run_over(absent)

        # Assert
        self.assertEqual((code, said.splitlines()[0]), (1, f"absent: {absent}"))

    def test_examining_nothing_says_so_rather_than_reporting_a_pass(self) -> None:
        # Arrange
        where = self.folder()

        # Act
        code, said, _ = self.run_over(where)

        # Assert
        self.assertEqual(
            (code, said.splitlines()[-1]), (0, "nothing was examined, so nothing was checked")
        )

    def test_a_library_it_can_read_is_reported_with_its_counts(self) -> None:
        # Arrange
        where = self.holding(
            {"one.sms": with_header(32768, 0x7FF0), "two.sms": bytes(synthetic(8192))}
        )

        # Act
        code, said, into = self.run_over(where)

        # Assert
        self.assertEqual(
            (
                code,
                "distinct images:                2" in said,
                "properties held on 2 of 2" in said,
                "carried    true of 1 of 1" in said,
                len(json.loads(into.read_text())),
            ),
            (0, True, True, True, 2),
        )

    def test_a_broken_property_is_named_and_fails_the_run(self) -> None:
        # Arrange
        where = self.holding({"bad.sms": bytes(synthetic(8192))})
        package = replaced("header", "agrees", always_agrees)

        # Act
        code, said, _ = self.run_over(where, package=package)

        # Assert
        self.assertEqual(
            (code, f"  broken  {census.AGREEMENT_FOLLOWS_A_CHECKSUM}  on 1" in said.splitlines()),
            (1, True),
        )


if __name__ == "__main__":
    unittest.main()
