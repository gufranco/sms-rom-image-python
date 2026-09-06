import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import hashlib  # noqa: E402
import unittest  # noqa: E402
import zlib  # noqa: E402

from smsimage import errors, identity  # noqa: E402

IMAGE = bytes((index * 31 + 7) & 0xFF for index in range(32768))


class MeasureTest(unittest.TestCase):
    def test_it_reports_the_length_in_bytes(self) -> None:
        found = identity.measure(IMAGE)

        self.assertEqual(found["size"], 32768)

    def test_it_reports_the_checksum_the_databases_key_on(self) -> None:
        found = identity.measure(IMAGE)

        self.assertEqual(found["crc32"], f"{zlib.crc32(IMAGE):08x}")

    def test_it_reports_the_two_digests_the_databases_still_carry(self) -> None:
        found = identity.measure(IMAGE)

        self.assertEqual(found["md5"], hashlib.md5(IMAGE).hexdigest())
        self.assertEqual(found["sha1"], hashlib.sha1(IMAGE).hexdigest())

    def test_it_reports_the_digest_that_decides(self) -> None:
        found = identity.measure(IMAGE)

        self.assertEqual(found["sha256"], hashlib.sha256(IMAGE).hexdigest())

    def test_it_reports_every_value_and_no_others(self) -> None:
        found = identity.measure(IMAGE)

        self.assertEqual(sorted(found), ["crc32", "md5", "sha1", "sha256", "size"])

    def test_an_empty_image_is_measured_rather_than_refused(self) -> None:
        found = identity.measure(b"")

        self.assertEqual(found["size"], 0)
        self.assertEqual(found["sha256"], hashlib.sha256(b"").hexdigest())

    def test_two_images_of_one_length_are_told_apart(self) -> None:
        other = bytes(32768)

        self.assertNotEqual(identity.measure(IMAGE), identity.measure(other))


class AuthorityTest(unittest.TestCase):
    def test_one_value_decides_and_it_is_named(self) -> None:
        self.assertEqual(identity.AUTHORITATIVE, "sha256")

    def test_the_deciding_value_is_one_of_the_values_measured(self) -> None:
        self.assertIn(identity.AUTHORITATIVE, identity.measure(IMAGE))

    def test_the_weaker_values_are_named_as_what_they_are_for(self) -> None:
        self.assertEqual(sorted(identity.CROSS_REFERENCE), ["crc32", "md5", "sha1", "size"])


class AgreesTest(unittest.TestCase):
    def test_a_matching_deciding_value_agrees(self) -> None:
        found = identity.measure(IMAGE)

        self.assertTrue(identity.agrees(found, {"sha256": found["sha256"]}))

    def test_a_different_deciding_value_disagrees(self) -> None:
        found = identity.measure(IMAGE)

        self.assertFalse(identity.agrees(found, {"sha256": "0" * 64}))

    def test_it_decides_on_that_value_alone_even_when_the_others_match(self) -> None:
        found = identity.measure(IMAGE)
        expected = dict(found)
        expected["sha256"] = "0" * 64

        self.assertFalse(identity.agrees(found, expected))

    def test_it_decides_on_that_value_alone_even_when_the_others_differ(self) -> None:
        found = identity.measure(IMAGE)
        expected = {"sha256": found["sha256"], "crc32": "deadbeef", "size": 1}

        self.assertTrue(identity.agrees(found, expected))

    def test_it_compares_the_value_without_regard_to_case(self) -> None:
        found = identity.measure(IMAGE)

        self.assertTrue(identity.agrees(found, {"sha256": found["sha256"].upper()}))

    def test_a_record_carrying_no_deciding_value_is_refused(self) -> None:
        found = identity.measure(IMAGE)

        with self.assertRaises(errors.NoAuthority):
            identity.agrees(found, {"crc32": found["crc32"], "size": found["size"]})

    def test_the_refusal_names_what_was_missing(self) -> None:
        found = identity.measure(IMAGE)

        with self.assertRaises(errors.NoAuthority) as caught:
            identity.agrees(found, {"crc32": found["crc32"]})

        self.assertIn("sha256", str(caught.exception))

    def test_a_measurement_carrying_no_deciding_value_is_refused_too(self) -> None:
        with self.assertRaises(errors.NoAuthority):
            identity.agrees({"crc32": "deadbeef"}, {"sha256": "0" * 64})


if __name__ == "__main__":
    unittest.main()
