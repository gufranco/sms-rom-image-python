import contextlib
import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import smsimage  # noqa: E402
from conformance import boot  # noqa: E402

FIRST_SPAN = {
    0xA: 0x1FF0,
    0xB: 0x3FF0,
    0xC: 0x7FF0,
    0xD: 0xBFF0,
    0xE: 0x7FF0,
    0xF: 0x7FF0,
    0x0: 0x7FF0,
    0x1: 0x7FF0,
    0x2: 0x7FF0,
}

BANKS_FROM_THE_THIRD = {0xE: 2, 0xF: 6, 0x0: 14, 0x1: 30, 0x2: 62}

COMPARED = 8


def a_boot_program(**changed: bytes) -> bytes:
    held = bytearray(0x2000)
    held[boot.FIRST_SPAN_AT : boot.FIRST_SPAN_AT + len(boot.CODES)] = bytes(
        FIRST_SPAN[code] >> 8 for code in boot.CODES
    )
    held[boot.BANKS_AT : boot.BANKS_AT + len(boot.BANKED_CODES)] = bytes(
        BANKS_FROM_THE_THIRD[code] for code in boot.BANKED_CODES
    )
    held[boot.COMPARED_AT] = COMPARED
    held[boot.REGION_GATE_AT] = boot.EXPORT_REGION << 4
    for name, value in changed.items():
        at = getattr(boot, name)
        held[at : at + len(value)] = value
    return bytes(held)


def run_main(argv: list[str]) -> tuple[int, str]:
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        code = boot.main(argv)
    return code, said.getvalue()


class ReadingTest(unittest.TestCase):
    def test_a_boot_program_holding_the_package_s_tables_agrees_with_it(self) -> None:
        # Arrange
        program = a_boot_program()

        # Act
        found = boot.disagreements(program)

        # Assert
        self.assertEqual(found, [])

    def test_a_span_table_that_differs_is_named(self) -> None:
        # Arrange
        program = a_boot_program(FIRST_SPAN_AT=b"\x1e")

        # Act
        found = boot.disagreements(program)

        # Assert
        self.assertEqual(found, ["the first span for size code 0xa is 0x1ef0, not 0x1ff0"])

    def test_a_bank_table_that_differs_is_named(self) -> None:
        # Arrange
        program = a_boot_program(BANKS_AT=b"\x03")

        # Act
        found = boot.disagreements(program)

        # Assert
        self.assertEqual(found, ["size code 0xe adds 3 banks, not 2"])

    def test_a_compare_of_another_length_is_named(self) -> None:
        # Arrange
        program = a_boot_program(COMPARED_AT=b"\x0a")

        # Act
        found = boot.disagreements(program)

        # Assert
        self.assertEqual(found, ["it compares 10 bytes, not 8"])

    def test_a_gate_on_another_region_is_named(self) -> None:
        # Arrange
        program = a_boot_program(REGION_GATE_AT=b"\x30")

        # Act
        found = boot.disagreements(program)

        # Assert
        self.assertEqual(found, ["it checks the sum only for region 0x3, not 0x4"])

    def test_every_code_the_reading_names_is_read_from_the_program(self) -> None:
        # Arrange
        named = set(smsimage.SIZES)

        # Act
        read = set(boot.CODES)

        # Assert
        self.assertEqual(read, named)


class MainTest(unittest.TestCase):
    def test_naming_no_file_explains_how_to_call_it(self) -> None:
        # Arrange
        argv: list[str] = []

        # Act
        code, said = run_main(argv)

        # Assert
        self.assertEqual((code, "usage" in said), (2, True))

    def test_a_file_that_is_not_the_declared_boot_program_is_refused(self) -> None:
        # Arrange
        path = Path(tempfile.mkdtemp()) / "other.sms"
        path.write_bytes(a_boot_program())

        # Act
        code, said = run_main([str(path)])

        # Assert
        self.assertEqual((code, "not the boot program" in said), (1, True))

    def test_the_declared_boot_program_agreeing_reports_what_it_read(self) -> None:
        # Arrange
        path = Path(tempfile.mkdtemp()) / "v13.sms"
        program = a_boot_program()
        path.write_bytes(program)
        held = boot.DECLARED
        boot.DECLARED = hashlib.sha256(program).hexdigest()
        self.addCleanup(setattr, boot, "DECLARED", held)

        # Act
        code, said = run_main([str(path)])

        # Assert
        self.assertEqual((code, "agrees with the package" in said), (0, True))

    def test_the_declared_boot_program_disagreeing_names_each_difference(self) -> None:
        # Arrange
        path = Path(tempfile.mkdtemp()) / "v13.sms"
        program = a_boot_program(COMPARED_AT=b"\x0a")
        path.write_bytes(program)
        held = boot.DECLARED
        boot.DECLARED = hashlib.sha256(program).hexdigest()
        self.addCleanup(setattr, boot, "DECLARED", held)

        # Act
        code, said = run_main([str(path)])

        # Assert
        self.assertEqual((code, "it compares 10 bytes, not 8" in said), (1, True))

    def test_the_declared_digest_is_the_manifest_s(self) -> None:
        # Arrange
        expected = "477617917a12a30f9f43844909dc2de6e6a617430f5c9a36306c86414a670d50"

        # Act
        declared = boot.DECLARED

        # Assert
        self.assertEqual(declared, expected)


if __name__ == "__main__":
    unittest.main()
