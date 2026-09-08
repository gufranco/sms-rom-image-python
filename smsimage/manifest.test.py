import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402
from typing import override  # noqa: E402

from smsimage import errors, identity, manifest  # noqa: E402

IMAGE = bytes((index * 17 + 3) & 0xFF for index in range(8192))
OTHER = bytes((index * 19 + 5) & 0xFF for index in range(8192))
SHORTER = bytes((index * 17 + 3) & 0xFF for index in range(4096))


def declared(data: bytes) -> dict[str, object]:
    measured = identity.measure(data)
    return {key: measured[key] for key in ("size", "crc32", "sha1", "sha256")}


def document() -> dict[str, object]:
    return {
        "artifacts": {
            "bios": {
                "name": "a boot program",
                "accepted": [declared(IMAGE)],
                "badDumps": [{**declared(OTHER), "why": "half a dump"}],
            }
        }
    }


class ReadingTest(unittest.TestCase):
    def test_it_names_every_artifact_the_document_declares(self) -> None:
        found = manifest.Manifest(document())

        self.assertEqual(found.keys, ("bios",))

    def test_it_carries_the_name_a_reader_recognises(self) -> None:
        found = manifest.Manifest(document())

        self.assertEqual(found.name("bios"), "a boot program")

    def test_an_artifact_with_no_name_is_named_by_its_key(self) -> None:
        raw = document()
        del raw["artifacts"]["bios"]["name"]  # type: ignore[index]

        self.assertEqual(manifest.Manifest(raw).name("bios"), "bios")

    def test_it_reads_a_document_from_a_file(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            path = Path(where) / "artifacts.manifest.json"
            path.write_text(json.dumps(document()))

            found = manifest.read(path)

        self.assertEqual(found.keys, ("bios",))

    def test_a_document_that_is_not_a_mapping_is_refused(self) -> None:
        with self.assertRaises(errors.Malformed):
            manifest.Manifest(["not a manifest"])

    def test_a_document_with_no_artifacts_block_is_refused(self) -> None:
        with self.assertRaises(errors.Malformed):
            manifest.Manifest({"note": "nothing here yet"})

    def test_an_artifact_that_is_not_a_mapping_is_refused(self) -> None:
        with self.assertRaises(errors.Malformed):
            manifest.Manifest({"artifacts": {"bios": "not a mapping"}})

    def test_an_artifact_accepting_nothing_is_refused(self) -> None:
        with self.assertRaises(errors.Malformed):
            manifest.Manifest({"artifacts": {"bios": {"accepted": []}}})

    def test_an_accepted_entry_with_no_deciding_digest_is_refused(self) -> None:
        raw = document()
        del raw["artifacts"]["bios"]["accepted"][0]["sha256"]  # type: ignore[index]

        with self.assertRaises(errors.NoAuthority):
            manifest.Manifest(raw)

    def test_the_refusal_names_the_artifact_it_could_not_read(self) -> None:
        raw = document()
        del raw["artifacts"]["bios"]["accepted"][0]["sha256"]  # type: ignore[index]

        with self.assertRaises(errors.NoAuthority) as caught:
            manifest.Manifest(raw)

        self.assertIn("bios", str(caught.exception))

    def test_a_declared_bad_dump_needs_no_deciding_digest_to_be_ignored(self) -> None:
        raw = document()
        raw["artifacts"]["bios"]["badDumps"] = []  # type: ignore[index]

        self.assertEqual(manifest.Manifest(raw).keys, ("bios",))


class MatchTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.manifest = manifest.Manifest(document())

    def test_the_file_it_expects_is_accepted(self) -> None:
        found = self.manifest.match("bios", IMAGE)

        self.assertEqual(found.verdict, manifest.ACCEPTED)

    def test_a_declared_bad_dump_is_named_as_one(self) -> None:
        found = self.manifest.match("bios", OTHER)

        self.assertEqual(found.verdict, manifest.BAD_DUMP)

    def test_a_bad_dump_carries_the_reason_it_was_declared(self) -> None:
        found = self.manifest.match("bios", OTHER)

        self.assertEqual(found.why, "half a dump")

    def test_the_right_length_with_the_wrong_content_says_so(self) -> None:
        changed = bytearray(IMAGE)
        changed[0] ^= 0xFF

        found = self.manifest.match("bios", bytes(changed))

        self.assertEqual(found.verdict, manifest.WRONG_CONTENT)

    def test_a_length_no_accepted_entry_has_says_so(self) -> None:
        found = self.manifest.match("bios", SHORTER)

        self.assertEqual(found.verdict, manifest.WRONG_SIZE)

    def test_an_artifact_the_document_never_declared_says_so(self) -> None:
        found = self.manifest.match("absent", IMAGE)

        self.assertEqual(found.verdict, manifest.UNDECLARED)

    def test_a_match_carries_what_was_measured(self) -> None:
        found = self.manifest.match("bios", IMAGE)

        self.assertEqual(found.found["sha256"], identity.measure(IMAGE)["sha256"])

    def test_a_match_reads_as_the_verdict_it_carries(self) -> None:
        found = self.manifest.match("bios", IMAGE)

        self.assertIn(manifest.ACCEPTED, repr(found))
        self.assertIn("bios", repr(found))

    def test_only_an_accepted_file_reads_as_true(self) -> None:
        self.assertTrue(self.manifest.match("bios", IMAGE))
        self.assertFalse(self.manifest.match("bios", OTHER))
        self.assertFalse(self.manifest.match("bios", SHORTER))
        self.assertFalse(self.manifest.match("absent", IMAGE))


class SurfaceTest(unittest.TestCase):
    def test_every_verdict_is_named_once(self) -> None:
        named = list(manifest.VERDICTS)

        self.assertEqual(sorted(named), sorted(set(named)))

    def test_a_match_holds_no_state_a_caller_can_add_to(self) -> None:
        found = manifest.Manifest(document()).match("bios", IMAGE)

        with self.assertRaises(AttributeError):
            found.invented = 1  # type: ignore[attr-defined]

    def test_a_manifest_holds_no_state_a_caller_can_add_to(self) -> None:
        found = manifest.Manifest(document())

        with self.assertRaises(AttributeError):
            found.invented = 1  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
