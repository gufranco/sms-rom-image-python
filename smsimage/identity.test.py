import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402
from typing import Any  # noqa: E402

import smsimage  # noqa: E402
from smsimage import identity  # noqa: E402

ABC = b"abc"

ABC_CRC32 = "352441c2"

ABC_MD5 = "900150983cd24fb0d6963f7d28e17f72"

ABC_SHA1 = "a9993e364706816aba3e25717850c26c9cd0d89d"

ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

IMAGE = bytes((index * 31 + 7) & 0xFF for index in range(32768))


class MeasureTest(unittest.TestCase):
    def test_it_reports_the_length_in_bytes(self) -> None:
        # Arrange
        data = IMAGE

        # Act
        found = identity.measure(data)

        # Assert
        self.assertEqual(found["size"], 32768)

    def test_it_reports_the_checksum_the_databases_key_on(self) -> None:
        # Arrange
        data = ABC

        # Act
        found = identity.measure(data)

        # Assert
        self.assertEqual(found["crc32"], ABC_CRC32)

    def test_it_reports_the_two_digests_the_databases_still_carry(self) -> None:
        # Arrange
        data = ABC

        # Act
        found = identity.measure(data)

        # Assert
        self.assertEqual((found["md5"], found["sha1"]), (ABC_MD5, ABC_SHA1))

    def test_it_reports_the_digest_that_decides(self) -> None:
        # Arrange
        data = ABC

        # Act
        found = identity.measure(data)

        # Assert
        self.assertEqual(found["sha256"], ABC_SHA256)

    def test_it_reports_every_value_and_no_others(self) -> None:
        # Arrange
        data = IMAGE

        # Act
        found = identity.measure(data)

        # Assert
        self.assertEqual(sorted(found), ["crc32", "md5", "sha1", "sha256", "size"])

    def test_an_empty_image_is_measured_rather_than_refused(self) -> None:
        # Arrange
        data = b""

        # Act
        found = identity.measure(data)

        # Assert
        self.assertEqual((found["size"], found["sha256"]), (0, EMPTY_SHA256))

    def test_two_images_of_one_length_are_told_apart(self) -> None:
        # Arrange
        other = identity.measure(bytes(32768))

        # Act
        found = identity.measure(IMAGE)

        # Assert
        self.assertNotEqual(found, other)


class AuthorityTest(unittest.TestCase):
    def test_one_value_decides_and_it_is_named(self) -> None:
        # Arrange
        published = smsimage.AUTHORITATIVE

        # Act
        named = str(published)

        # Assert
        self.assertEqual(named, "sha256")

    def test_the_deciding_value_is_one_of_the_values_measured(self) -> None:
        # Arrange
        deciding = smsimage.AUTHORITATIVE

        # Act
        found = identity.measure(IMAGE)

        # Assert
        self.assertIn(deciding, found)

    def test_the_weaker_values_never_decide(self) -> None:
        # Arrange
        found = identity.measure(IMAGE)
        weaker = [key for key in found if key != "sha256"]

        # Act
        verdicts = [
            identity.agrees(found, {**found, key: "something else", "sha256": "0" * 64})
            for key in weaker
        ]

        # Assert
        self.assertEqual(
            (sorted(weaker), verdicts), (["crc32", "md5", "sha1", "size"], [False] * 4)
        )


class AgreesTest(unittest.TestCase):
    def test_a_matching_deciding_value_agrees(self) -> None:
        # Arrange
        found = identity.measure(IMAGE)

        # Act
        agreed = identity.agrees(found, {"sha256": found["sha256"]})

        # Assert
        self.assertTrue(agreed)

    def test_a_different_deciding_value_disagrees(self) -> None:
        # Arrange
        found = identity.measure(IMAGE)

        # Act
        agreed = identity.agrees(found, {"sha256": "0" * 64})

        # Assert
        self.assertFalse(agreed)

    def test_it_decides_on_that_value_alone_even_when_the_others_match(self) -> None:
        # Arrange
        found = identity.measure(IMAGE)
        expected = {**found, "sha256": "0" * 64}

        # Act
        agreed = identity.agrees(found, expected)

        # Assert
        self.assertFalse(agreed)

    def test_it_decides_on_that_value_alone_even_when_the_others_differ(self) -> None:
        # Arrange
        found = identity.measure(IMAGE)
        expected = {"sha256": found["sha256"], "crc32": "deadbeef", "size": 1}

        # Act
        agreed = identity.agrees(found, expected)

        # Assert
        self.assertTrue(agreed)

    def test_it_compares_the_value_without_regard_to_case(self) -> None:
        # Arrange
        found = identity.measure(ABC)

        # Act
        agreed = identity.agrees(found, {"sha256": ABC_SHA256.upper()})

        # Assert
        self.assertTrue(agreed)

    def test_a_record_carrying_no_deciding_value_is_refused(self) -> None:
        # Arrange
        found = identity.measure(IMAGE)

        def attempt() -> Any:
            return identity.agrees(found, {"crc32": found["crc32"], "size": 32768})

        # Act
        with self.assertRaises(smsimage.NoAuthority) as caught:
            attempt()

        # Assert
        self.assertEqual(str(caught.exception), "nothing decides: no sha256 to compare")

    def test_a_measurement_carrying_no_deciding_value_is_refused_too(self) -> None:
        # Arrange
        def attempt() -> Any:
            return identity.agrees({"crc32": "deadbeef"}, {"sha256": "0" * 64})

        # Act
        with self.assertRaises(smsimage.NoAuthority) as caught:
            attempt()

        # Assert
        self.assertEqual(str(caught.exception), "nothing decides: no sha256 to compare")


if __name__ == "__main__":
    unittest.main()
