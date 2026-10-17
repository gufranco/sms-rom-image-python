import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json  # noqa: E402
import types  # noqa: E402
import unittest  # noqa: E402
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


def never_strips_completely(data: bytes) -> bytes:
    return data[1:]


def anchor_outside_the_candidates(image: bytes) -> int | None:
    return 0x0100


def anchor_with_nothing_under_it(image: bytes) -> int | None:
    return 0x1FF0


def checksum_too_wide(image: bytes) -> int | None:
    return 0x1_0000


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


class PropertyTest(unittest.TestCase):
    def test_a_sealed_image_holds_every_property(self) -> None:
        # Arrange
        image = with_header(32768, 0x7FF0)

        # Act
        broken = census.broken_properties(image)

        # Assert
        self.assertEqual(broken, [])

    def test_a_headerless_image_holds_every_property(self) -> None:
        # Arrange
        image = bytes(synthetic(32768))

        # Act
        broken = census.broken_properties(image)

        # Assert
        self.assertEqual(broken, [])

    def test_a_stubbed_image_holds_every_property(self) -> None:
        # Arrange
        stubbed = bytes(synthetic(512, seed=9)) + with_header(32768, 0x7FF0)

        # Act
        broken = census.broken_properties(stubbed)

        # Assert
        self.assertEqual(broken, [])

    def test_a_strip_that_removes_more_each_time_is_reported(self) -> None:
        # Arrange
        package = replaced("dump", "strip_copier_stub", never_strips_completely)

        # Act
        broken = census.broken_properties(with_header(32768, 0x7FF0), package)

        # Assert
        self.assertIn(census.IDEMPOTENT_STRIP, broken)

    def test_an_anchor_that_is_not_a_candidate_is_reported(self) -> None:
        # Arrange
        package = replaced("header", "anchor_of", anchor_outside_the_candidates)

        # Act
        broken = census.broken_properties(with_header(32768, 0x7FF0), package)

        # Assert
        self.assertIn(census.ANCHOR_IS_A_CANDIDATE, broken)

    def test_an_anchor_with_no_magic_under_it_is_reported(self) -> None:
        # Arrange
        package = replaced("header", "anchor_of", anchor_with_nothing_under_it)

        # Act
        broken = census.broken_properties(bytes(synthetic(32768)), package)

        # Assert
        self.assertEqual(broken, [census.MAGIC_AT_THE_ANCHOR])

    def test_a_checksum_outside_sixteen_bits_is_reported(self) -> None:
        # Arrange
        package = replaced("header", "checksum", checksum_too_wide)

        # Act
        broken = census.broken_properties(with_header(32768, 0x7FF0), package)

        # Assert
        self.assertEqual(broken, [census.CHECKSUM_IN_RANGE])

    def test_agreement_answered_without_a_checksum_is_reported(self) -> None:
        # Arrange
        package = replaced("header", "agrees", always_agrees)

        # Act
        broken = census.broken_properties(bytes(synthetic(32768)), package)

        # Assert
        self.assertEqual(broken, [census.AGREEMENT_FOLLOWS_A_CHECKSUM])

    def test_a_measurement_that_changes_between_calls_is_reported(self) -> None:
        # Arrange
        counter = iter(range(2))

        def measures_differently(image: bytes) -> dict[str, int]:
            return {"n": next(counter)}

        package = replaced("identity", "measure", measures_differently)

        # Act
        broken = census.broken_properties(with_header(32768, 0x7FF0), package)

        # Assert
        self.assertEqual(broken, [census.MEASUREMENT_IS_STABLE])

    def test_every_property_it_declares_is_named_once(self) -> None:
        # Arrange
        declared = census.PROPERTIES

        # Act
        distinct = sorted(set(declared))

        # Assert
        self.assertEqual(sorted(declared), distinct)

    def test_every_property_it_declares_can_be_reported(self) -> None:
        # Arrange
        reported = {
            census.IDEMPOTENT_STRIP,
            census.ANCHOR_IS_A_CANDIDATE,
            census.MAGIC_AT_THE_ANCHOR,
            census.CHECKSUM_IN_RANGE,
            census.AGREEMENT_FOLLOWS_A_CHECKSUM,
            census.MEASUREMENT_IS_STABLE,
        }

        # Act
        declared = set(census.PROPERTIES)

        # Assert
        self.assertEqual(declared, reported)


class ObservationTest(unittest.TestCase):
    def test_a_sealed_image_reproduces_its_carried_value(self) -> None:
        # Arrange
        image = with_header(32768, 0x7FF0)

        # Act
        found = census.observe(image)

        # Assert
        self.assertIs(found["carried"], True)

    def test_an_image_whose_content_moved_does_not(self) -> None:
        # Arrange
        image = bytearray(with_header(32768, 0x7FF0))
        image[0x0100] ^= 0xFF

        # Act
        found = census.observe(bytes(image))

        # Assert
        self.assertIs(found["carried"], False)

    def test_a_headerless_image_carries_nothing_to_compare(self) -> None:
        # Arrange
        image = bytes(synthetic(32768))

        # Act
        found = census.observe(image)

        # Assert
        self.assertEqual((found["carried"], found["anchor"]), (None, None))

    def test_it_records_where_the_header_sat_and_what_it_declared(self) -> None:
        # Arrange
        image = with_header(32768, 0x7FF0, 0x4C)

        # Act
        found = census.observe(image)

        # Assert
        self.assertEqual(
            (found["anchor"], found["region"], found["declared"]), (0x7FF0, "sms-export", 32768)
        )

    def test_it_records_the_length_after_any_stub_is_removed(self) -> None:
        # Arrange
        stubbed = bytes(synthetic(512)) + with_header(32768, 0x7FF0)

        # Act
        found = census.observe(stubbed)

        # Assert
        self.assertEqual((found["size"], found["form"]), (32768, "stubbed"))

    def test_it_records_no_title_and_nothing_of_the_content(self) -> None:
        # Arrange
        image = with_header(32768, 0x7FF0)

        # Act
        found = census.observe(image)

        # Assert
        self.assertEqual(sorted(found), ["anchor", "carried", "declared", "form", "region", "size"])


class RenderTest(unittest.TestCase):
    def test_the_committed_corpus_is_written_back_byte_for_byte(self) -> None:
        # Arrange
        committed = census.CORPUS.read_text()

        # Act
        written = census.rendered(json.loads(committed))

        # Assert
        self.assertEqual(written, committed)


if __name__ == "__main__":
    unittest.main()
