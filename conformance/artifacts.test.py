import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json  # noqa: E402
import unittest  # noqa: E402

from smsimage import identity, manifest  # noqa: E402

MANIFEST = ROOT / "artifacts.manifest.json"

DIGESTS = {"crc32": 8, "sha1": 40, "sha256": 64}


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


class ShapeTest(unittest.TestCase):
    def test_the_file_this_repository_ships_parses(self) -> None:
        found = manifest.read(MANIFEST)

        self.assertEqual(len(found.keys), len(entries()))

    def test_it_declares_at_least_one_artifact(self) -> None:
        self.assertGreater(len(entries()), 0)

    def test_it_names_the_value_that_decides(self) -> None:
        self.assertEqual(document()["decidedBy"], identity.AUTHORITATIVE)

    def test_it_says_why_the_others_do_not_decide(self) -> None:
        why = document()["why"]

        assert isinstance(why, str)
        self.assertIn(identity.AUTHORITATIVE, why.lower().replace("-", ""))
        for weaker in identity.CROSS_REFERENCE:
            self.assertIn(weaker, why.lower().replace("-", ""))

    def test_it_records_when_and_from_what_the_digests_were_read(self) -> None:
        provenance = document()["provenance"]

        assert isinstance(provenance, dict)
        self.assertEqual(sorted(provenance), ["caveat", "from", "read"])


class LadderTest(unittest.TestCase):
    def test_every_accepted_file_publishes_the_whole_ladder(self) -> None:
        missing = [
            (key, name)
            for key, entry in entries().items()
            for one in accepted(entry)
            for name in ("size", *DIGESTS)
            if name not in one
        ]

        self.assertEqual(missing, [])

    def test_every_digest_is_the_width_its_algorithm_produces(self) -> None:
        wrong = [
            (key, name, one[name])
            for key, entry in entries().items()
            for one in accepted(entry)
            for name, width in DIGESTS.items()
            if len(str(one[name])) != width
        ]

        self.assertEqual(wrong, [])

    def test_every_digest_is_lowercase_hexadecimal(self) -> None:
        wrong = [
            (key, name)
            for key, entry in entries().items()
            for one in accepted(entry)
            for name in DIGESTS
            if str(one[name]) != str(one[name]).lower()
            or not all(digit in "0123456789abcdef" for digit in str(one[name]))
        ]

        self.assertEqual(wrong, [])

    def test_every_declared_length_is_a_positive_whole_number(self) -> None:
        wrong = [
            (key, one["size"])
            for key, entry in entries().items()
            for one in accepted(entry)
            if not isinstance(one["size"], int) or one["size"] <= 0
        ]

        self.assertEqual(wrong, [])

    def test_no_deciding_digest_is_declared_twice_under_two_keys(self) -> None:
        deciding = [
            str(one[identity.AUTHORITATIVE])
            for entry in entries().values()
            for one in accepted(entry)
        ]

        self.assertEqual(sorted(deciding), sorted(set(deciding)))


class DeclarationTest(unittest.TestCase):
    def test_every_artifact_carries_a_name_a_reader_would_recognise(self) -> None:
        unnamed = [key for key, entry in entries().items() if not entry.get("name")]

        self.assertEqual(unnamed, [])

    def test_every_artifact_names_the_machine_it_boots(self) -> None:
        known = {"master-system", "game-gear"}
        wrong = [
            (key, entry.get("machine"))
            for key, entry in entries().items()
            if entry.get("machine") not in known
        ]

        self.assertEqual(wrong, [])

    def test_bad_dumps_are_declared_as_their_own_list(self) -> None:
        missing = [
            key for key, entry in entries().items() if not isinstance(entry.get("badDumps"), list)
        ]

        self.assertEqual(missing, [])

    def test_an_empty_bad_dump_list_is_accounted_for_rather_than_left_unsaid(self) -> None:
        note = document()["badDumpsNote"]

        assert isinstance(note, str)
        self.assertGreater(len(note), 0)


class DistributionTest(unittest.TestCase):
    def test_it_carries_no_path_to_any_of_these_files(self) -> None:
        raw = MANIFEST.read_text().lower()

        for pointer in ("http://", "https://", "ftp://", "magnet:", "torrent"):
            self.assertNotIn(pointer, raw)

    def test_it_carries_nothing_that_could_rebuild_one(self) -> None:
        for entry in entries().values():
            for one in accepted(entry):
                self.assertEqual(sorted(one), ["crc32", "sha1", "sha256", "size"])


if __name__ == "__main__":
    unittest.main()
