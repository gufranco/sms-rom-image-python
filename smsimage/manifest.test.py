import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402
from typing import Any  # noqa: E402

import smsimage  # noqa: E402
from smsimage import identity, manifest  # noqa: E402

IMAGE = bytes((index * 17 + 3) & 0xFF for index in range(8192))
OTHER = bytes((index * 19 + 5) & 0xFF for index in range(8192))
SHORTER = bytes((index * 17 + 3) & 0xFF for index in range(4096))

VERDICTS = (
    "accepted",
    "a known bad dump",
    "the right length, the wrong content",
    "a length nothing declares",
    "undeclared",
)


def declared(data: bytes) -> dict[str, object]:
    measured = identity.measure(data)
    return {key: measured[key] for key in ("size", "crc32", "sha1", "sha256")}


def artifact(**fields: object) -> dict[str, object]:
    base: dict[str, object] = {
        "name": "a boot program",
        "accepted": [declared(IMAGE)],
        "badDumps": [{**declared(OTHER), "why": "half a dump"}],
    }
    return {key: value for key, value in {**base, **fields}.items() if value is not None}


def document(**fields: object) -> dict[str, object]:
    return {"artifacts": {"bios": artifact(**fields)}}


def refusal(raw: object) -> Any:
    def attempt() -> Any:
        return smsimage.Manifest(raw)

    return attempt


class ReadingTest(unittest.TestCase):
    def test_it_names_every_artifact_the_document_declares(self) -> None:
        # Arrange
        raw = document()

        # Act
        found = smsimage.Manifest(raw)

        # Assert
        self.assertEqual(found.keys, ("bios",))

    def test_it_carries_the_name_a_reader_recognises(self) -> None:
        # Arrange
        found = smsimage.Manifest(document())

        # Act
        named = found.name("bios")

        # Assert
        self.assertEqual(named, "a boot program")

    def test_an_artifact_with_no_name_is_named_by_its_key(self) -> None:
        # Arrange
        found = smsimage.Manifest(document(name=None))

        # Act
        named = found.name("bios")

        # Assert
        self.assertEqual(named, "bios")

    def test_an_artifact_it_does_not_declare_is_named_by_its_key(self) -> None:
        # Arrange
        found = smsimage.Manifest(document())

        # Act
        named = found.name("cartridge")

        # Assert
        self.assertEqual(named, "cartridge")

    def test_it_reads_a_document_from_a_file(self) -> None:
        # Arrange
        held = tempfile.TemporaryDirectory()
        self.addCleanup(held.cleanup)
        path = Path(held.name) / "artifacts.manifest.json"
        path.write_text(json.dumps(document()))

        # Act
        found = manifest.read(path)

        # Assert
        self.assertEqual((found.keys, found.name("bios")), (("bios",), "a boot program"))

    def test_a_document_that_is_not_a_mapping_is_refused(self) -> None:
        # Arrange
        attempt = refusal(["not a manifest"])

        # Act
        with self.assertRaises(smsimage.Malformed) as caught:
            attempt()

        # Assert
        self.assertEqual(str(caught.exception), "a manifest is a mapping, and this is not one")

    def test_a_document_with_no_artifacts_block_is_refused(self) -> None:
        # Arrange
        attempt = refusal({"note": "nothing here yet"})

        # Act
        with self.assertRaises(smsimage.Malformed) as caught:
            attempt()

        # Assert
        self.assertEqual(
            str(caught.exception), "a manifest declares artifacts, and this declares none"
        )

    def test_an_artifact_that_is_not_a_mapping_is_refused(self) -> None:
        # Arrange
        attempt = refusal({"artifacts": {"bios": "not a mapping"}})

        # Act
        with self.assertRaises(smsimage.Malformed) as caught:
            attempt()

        # Assert
        self.assertEqual(
            str(caught.exception), "bios: an artifact is a mapping, and this is not one"
        )

    def test_an_artifact_accepting_nothing_is_refused(self) -> None:
        # Arrange
        attempt = refusal({"artifacts": {"bios": {"accepted": []}}})

        # Act
        with self.assertRaises(smsimage.Malformed) as caught:
            attempt()

        # Assert
        self.assertEqual(
            str(caught.exception), "bios: an artifact accepts something, and this accepts nothing"
        )

    def test_an_accepted_entry_with_no_deciding_digest_is_refused_by_name(self) -> None:
        # Arrange
        attempt = refusal(document(accepted=[{"size": 8192, "crc32": "00000000"}]))

        # Act
        with self.assertRaises(smsimage.NoAuthority) as caught:
            attempt()

        # Assert
        self.assertEqual(
            str(caught.exception), "bios: an accepted file with no sha256 to decide on"
        )

    def test_an_accepted_entry_that_is_not_a_mapping_is_refused(self) -> None:
        # Arrange
        attempt = refusal(document(accepted=["not a record"]))

        # Act
        with self.assertRaises(smsimage.NoAuthority) as caught:
            attempt()

        # Assert
        self.assertEqual(
            str(caught.exception), "bios: an accepted file with no sha256 to decide on"
        )

    def test_an_artifact_declaring_no_bad_dump_is_read(self) -> None:
        # Arrange
        raw = document(badDumps=None)

        # Act
        found = smsimage.Manifest(raw)

        # Assert
        self.assertEqual(found.match("bios", OTHER).verdict, "the right length, the wrong content")


class MatchTest(unittest.TestCase):
    def matched(self, key: str, data: bytes) -> Any:
        return smsimage.Manifest(document()).match(key, data)

    def test_the_file_it_expects_is_accepted(self) -> None:
        # Arrange
        data = IMAGE

        # Act
        found = self.matched("bios", data)

        # Assert
        self.assertEqual((found.key, found.verdict, found.why), ("bios", "accepted", None))

    def test_a_declared_bad_dump_is_named_as_one_with_its_reason(self) -> None:
        # Arrange
        data = OTHER

        # Act
        found = self.matched("bios", data)

        # Assert
        self.assertEqual((found.verdict, found.why), ("a known bad dump", "half a dump"))

    def test_the_right_length_with_the_wrong_content_says_so(self) -> None:
        # Arrange
        data = bytes([IMAGE[0] ^ 0xFF]) + IMAGE[1:]

        # Act
        found = self.matched("bios", data)

        # Assert
        self.assertEqual(found.verdict, "the right length, the wrong content")

    def test_a_length_no_accepted_entry_has_says_so(self) -> None:
        # Arrange
        data = SHORTER

        # Act
        found = self.matched("bios", data)

        # Assert
        self.assertEqual(found.verdict, "a length nothing declares")

    def test_an_artifact_the_document_never_declared_says_so(self) -> None:
        # Arrange
        data = IMAGE

        # Act
        found = self.matched("absent", data)

        # Assert
        self.assertEqual((found.key, found.verdict), ("absent", "undeclared"))

    def test_a_digest_in_capitals_is_still_the_file(self) -> None:
        # Arrange
        upper = {**declared(IMAGE), "sha256": str(declared(IMAGE)["sha256"]).upper()}
        found = smsimage.Manifest(document(accepted=[upper]))

        # Act
        verdict = found.match("bios", IMAGE).verdict

        # Assert
        self.assertEqual(verdict, "accepted")

    def test_a_match_carries_what_was_measured(self) -> None:
        # Arrange
        measured = identity.measure(IMAGE)

        # Act
        found = self.matched("bios", IMAGE)

        # Assert
        self.assertEqual(dict(found.found), dict(measured))

    def test_a_match_reads_as_the_verdict_it_carries(self) -> None:
        # Arrange
        found = self.matched("bios", IMAGE)

        # Act
        shown = repr(found)

        # Assert
        self.assertEqual(shown, "<Match bios: accepted>")

    def test_only_an_accepted_file_reads_as_true(self) -> None:
        # Arrange
        asked = (("bios", IMAGE), ("bios", OTHER), ("bios", SHORTER), ("absent", IMAGE))

        # Act
        found = [bool(self.matched(key, data)) for key, data in asked]

        # Assert
        self.assertEqual(found, [True, False, False, False])

    def test_every_verdict_is_published_in_the_order_match_tries_them(self) -> None:
        # Arrange
        expected = VERDICTS

        # Act
        published = tuple(smsimage.VERDICTS)

        # Assert
        self.assertEqual(published, expected)


class StateTest(unittest.TestCase):
    def test_a_match_holds_no_state_a_caller_can_add_to(self) -> None:
        # Arrange
        found = smsimage.Manifest(document()).match("bios", IMAGE)

        # Act
        with self.assertRaises(AttributeError) as caught:
            found.invented = 1  # type: ignore[attr-defined]

        # Assert
        self.assertIn("invented", str(caught.exception))

    def test_a_manifest_holds_no_state_a_caller_can_add_to(self) -> None:
        # Arrange
        found = smsimage.Manifest(document())

        # Act
        with self.assertRaises(AttributeError) as caught:
            found.invented = 1  # type: ignore[attr-defined]

        # Assert
        self.assertIn("invented", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
