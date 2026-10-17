import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json  # noqa: E402
import unittest  # noqa: E402

import smsimage  # noqa: E402
from smsimage import identity, manifest  # noqa: E402

MANIFEST = ROOT / "artifacts.manifest.json"

DIGESTS = {"crc32": 8, "sha1": 40, "sha256": 64}

CROSS_REFERENCE = ("size", "crc32", "md5", "sha1")

DECLARED = 14


def document() -> dict[str, object]:
    loaded = json.loads(MANIFEST.read_text())
    assert isinstance(loaded, dict)
    return loaded


def entries() -> dict[str, dict[str, object]]:
    found = document()["artifacts"]
    assert isinstance(found, dict)
    return found


def accepted(entry: dict[str, object]) -> list[dict[str, object]]:
    found = entry["accepted"]
    assert isinstance(found, list)
    return found


def every_accepted() -> list[tuple[str, dict[str, object]]]:
    return [(key, one) for key, entry in entries().items() for one in accepted(entry)]


class ShapeTest(unittest.TestCase):
    def test_the_file_this_repository_ships_parses(self) -> None:
        # Arrange
        path = MANIFEST

        # Act
        found = manifest.read(path)

        # Assert
        self.assertEqual(len(found.keys), DECLARED)

    def test_and_every_artifact_in_it_is_accepted_by_its_own_digest(self) -> None:
        # Arrange
        found = manifest.read(MANIFEST)

        # Act
        refused = [
            key
            for key, one in every_accepted()
            if not identity.agrees({"sha256": one["sha256"]}, one)
        ]

        # Assert
        self.assertEqual((refused, len(found.keys)), ([], DECLARED))

    def test_it_names_the_value_that_decides(self) -> None:
        # Arrange
        deciding = smsimage.AUTHORITATIVE

        # Act
        named = document()["decidedBy"]

        # Assert
        self.assertEqual(named, deciding)

    def test_it_says_why_the_others_do_not_decide(self) -> None:
        # Arrange
        named = (smsimage.AUTHORITATIVE, *CROSS_REFERENCE)

        # Act
        why = str(document()["why"]).lower().replace("-", "")

        # Assert
        self.assertEqual([one for one in named if one not in why], [])

    def test_it_records_when_and_from_what_the_digests_were_read(self) -> None:
        # Arrange
        expected = ["caveat", "from", "read"]

        # Act
        provenance = document()["provenance"]

        # Assert
        self.assertEqual(sorted(provenance) if isinstance(provenance, dict) else [], expected)


class LadderTest(unittest.TestCase):
    def test_every_accepted_file_publishes_the_whole_ladder(self) -> None:
        # Arrange
        names = ("size", *DIGESTS)

        # Act
        missing = [
            (key, name) for key, one in every_accepted() for name in names if name not in one
        ]

        # Assert
        self.assertEqual(missing, [])

    def test_every_digest_is_the_width_its_algorithm_produces(self) -> None:
        # Arrange
        widths = DIGESTS

        # Act
        wrong = [
            (key, name, one[name])
            for key, one in every_accepted()
            for name, width in widths.items()
            if len(str(one[name])) != width
        ]

        # Assert
        self.assertEqual(wrong, [])

    def test_every_digest_is_lowercase_hexadecimal(self) -> None:
        # Arrange
        hexadecimal = set("0123456789abcdef")

        # Act
        wrong = [
            (key, name)
            for key, one in every_accepted()
            for name in DIGESTS
            if not set(str(one[name])) <= hexadecimal
        ]

        # Assert
        self.assertEqual(wrong, [])

    def test_every_declared_length_is_a_positive_whole_number(self) -> None:
        # Arrange
        held = every_accepted()

        # Act
        wrong = [
            (key, one["size"])
            for key, one in held
            if not isinstance(one["size"], int) or one["size"] <= 0
        ]

        # Assert
        self.assertEqual(wrong, [])

    def test_no_deciding_digest_is_declared_twice_under_two_keys(self) -> None:
        # Arrange
        deciding = [str(one[smsimage.AUTHORITATIVE]) for _, one in every_accepted()]

        # Act
        distinct = sorted(set(deciding))

        # Assert
        self.assertEqual(sorted(deciding), distinct)


class DeclarationTest(unittest.TestCase):
    def test_every_artifact_carries_a_name_a_reader_would_recognise(self) -> None:
        # Arrange
        found = manifest.read(MANIFEST)

        # Act
        unnamed = [key for key in found.keys if found.name(key) == key]

        # Assert
        self.assertEqual(unnamed, [])

    def test_every_artifact_names_the_machine_it_boots(self) -> None:
        # Arrange
        known = {"master-system", "game-gear"}

        # Act
        wrong = [
            (key, entry.get("machine"))
            for key, entry in entries().items()
            if entry.get("machine") not in known
        ]

        # Assert
        self.assertEqual(wrong, [])

    def test_bad_dumps_are_declared_as_their_own_list(self) -> None:
        # Arrange
        held = entries()

        # Act
        missing = [
            key for key, entry in held.items() if not isinstance(entry.get("badDumps"), list)
        ]

        # Assert
        self.assertEqual(missing, [])

    def test_an_empty_bad_dump_list_is_accounted_for_rather_than_left_unsaid(self) -> None:
        # Arrange
        held = document()

        # Act
        note = str(held.get("badDumpsNote", ""))

        # Assert
        self.assertGreater(len(note), 0)


class DistributionTest(unittest.TestCase):
    def test_it_carries_no_path_to_any_of_these_files(self) -> None:
        # Arrange
        pointers = ("http://", "https://", "ftp://", "magnet:", "torrent")

        # Act
        raw = MANIFEST.read_text().lower()

        # Assert
        self.assertEqual([one for one in pointers if one in raw], [])

    def test_it_carries_nothing_that_could_rebuild_one(self) -> None:
        # Arrange
        expected = ["crc32", "sha1", "sha256", "size"]

        # Act
        shapes = [sorted(one) for _, one in every_accepted()]

        # Assert
        self.assertEqual([shape for shape in shapes if shape != expected], [])


if __name__ == "__main__":
    unittest.main()
