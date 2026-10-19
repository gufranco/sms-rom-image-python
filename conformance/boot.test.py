import contextlib
import dataclasses
import hashlib
import io
import json
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

V1_3 = "sega-master-system-usa-europe-v1-3"

HANG_ON = "hang-on-usa-europe-v3-4"

JAPAN = "sega-master-system-japan-v2-1"

SIZE = 0x20000


def planted(layout: boot.Layout, **changed: bytes) -> bytes:
    held = bytearray(SIZE)
    held[layout.first_span_at : layout.first_span_at + len(boot.CODES)] = bytes(
        (FIRST_SPAN[code] >> 8) + layout.passes_after_the_first for code in boot.CODES
    )
    held[layout.banks_at : layout.banks_at + len(boot.BANKED_CODES)] = bytes(
        BANKS_FROM_THE_THIRD[code] for code in boot.BANKED_CODES
    )
    held[layout.compared_at] = COMPARED
    held[layout.region_gate_at] = boot.EXPORT_REGION << 4
    for name, value in changed.items():
        at = getattr(layout, name)
        held[at : at + len(value)] = value
    return bytes(held)


def a_boot_program(**changed: bytes) -> bytes:
    return planted(boot.LAYOUTS[V1_3], **changed)


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
        program = a_boot_program(first_span_at=b"\x1e")

        # Act
        found = boot.disagreements(program)

        # Assert
        self.assertEqual(found, ["the first span for size code 0xa is 0x1ef0, not 0x1ff0"])

    def test_a_bank_table_that_differs_is_named(self) -> None:
        # Arrange
        program = a_boot_program(banks_at=b"\x03")

        # Act
        found = boot.disagreements(program)

        # Assert
        self.assertEqual(found, ["size code 0xe adds 3 banks, not 2"])

    def test_a_compare_of_another_length_is_named(self) -> None:
        # Arrange
        program = a_boot_program(compared_at=b"\x0a")

        # Act
        found = boot.disagreements(program)

        # Assert
        self.assertEqual(found, ["it compares 10 bytes, not 8"])

    def test_a_gate_on_another_region_is_named(self) -> None:
        # Arrange
        program = a_boot_program(region_gate_at=b"\x30")

        # Act
        found = boot.disagreements(program)

        # Assert
        self.assertEqual(found, ["it checks the sum only for region 0x3, not 0x4"])

    def test_a_table_counting_its_first_pass_is_read_one_pass_short(self) -> None:
        # Arrange
        layout = boot.LAYOUTS[HANG_ON]
        program = planted(layout, first_span_at=b"\x20")

        # Act
        found = boot.span_disagreements(program, layout)

        # Assert
        self.assertEqual(found, [])

    def test_a_table_counting_its_first_pass_names_a_span_that_differs(self) -> None:
        # Arrange
        layout = boot.LAYOUTS[HANG_ON]
        program = planted(layout, first_span_at=b"\x1f")

        # Act
        found = boot.span_disagreements(program, layout)

        # Assert
        self.assertEqual(found, ["the first span for size code 0xa is 0x1ef0, not 0x1ff0"])

    def test_every_code_the_reading_names_is_read_from_the_program(self) -> None:
        # Arrange
        named = set(smsimage.SIZES)

        # Act
        read = set(boot.CODES)

        # Assert
        self.assertEqual(read, named)


class MainTest(unittest.TestCase):
    def a_declared_file(self, program: bytes, name: str) -> Path:
        path = Path(tempfile.mkdtemp()) / "boot.sms"
        path.write_bytes(program)
        held = boot.DECLARED
        boot.DECLARED = {**held, hashlib.sha256(program).hexdigest(): name}
        self.addCleanup(setattr, boot, "DECLARED", held)
        return path

    def test_naming_no_file_explains_how_to_call_it(self) -> None:
        # Arrange
        argv: list[str] = []

        # Act
        code, said = run_main(argv)

        # Assert
        self.assertEqual((code, "usage" in said), (2, True))

    def test_a_file_the_manifest_does_not_declare_is_refused(self) -> None:
        # Arrange
        path = Path(tempfile.mkdtemp()) / "other.sms"
        path.write_bytes(a_boot_program())

        # Act
        code, said = run_main([str(path)])

        # Assert
        self.assertEqual((code, "not a boot program the manifest declares" in said), (1, True))

    def test_a_declared_program_that_runs_no_checksum_is_refused(self) -> None:
        # Arrange
        path = self.a_declared_file(bytes(SIZE), JAPAN)

        # Act
        code, said = run_main([str(path)])

        # Assert
        self.assertEqual(
            (code, said), (1, f"{JAPAN} runs no checksum, so there is no table to read\n")
        )

    def test_a_declared_program_agreeing_reports_what_it_read(self) -> None:
        # Arrange
        path = self.a_declared_file(a_boot_program(), V1_3)

        # Act
        code, said = run_main([str(path)])

        # Assert
        self.assertEqual((code, f"{V1_3} agrees with the package" in said), (0, True))

    def test_a_declared_program_disagreeing_names_each_difference(self) -> None:
        # Arrange
        layout = boot.LAYOUTS[HANG_ON]
        program = planted(layout, banks_at=bytes([2, 6, 14, 30, 33]))
        path = self.a_declared_file(program, HANG_ON)

        # Act
        code, said = run_main([str(path)])

        # Assert
        self.assertEqual(
            (code, f"{HANG_ON}: size code 0x2 adds 33 banks, not 62" in said), (1, True)
        )

    def test_one_program_disagreeing_fails_a_run_over_several(self) -> None:
        # Arrange
        agreeing = self.a_declared_file(a_boot_program(), V1_3)
        refused = Path(tempfile.mkdtemp()) / "other.sms"
        refused.write_bytes(bytes(SIZE))

        # Act
        code, said = run_main([str(agreeing), str(refused)])

        # Assert
        self.assertEqual((code, said.count("\n")), (1, 2))


class DeclarationTest(unittest.TestCase):
    def test_every_program_read_is_declared_in_the_manifest(self) -> None:
        # Arrange
        declared = set(json.loads(boot.MANIFEST.read_text())["artifacts"])

        # Act
        read = set(boot.LAYOUTS)

        # Assert
        self.assertEqual(read - declared, set())

    def test_the_v1_3_program_is_declared_by_the_manifest_s_digest(self) -> None:
        # Arrange
        expected = "477617917a12a30f9f43844909dc2de6e6a617430f5c9a36306c86414a670d50"

        # Act
        declared = boot.DECLARED[expected]

        # Assert
        self.assertEqual(declared, V1_3)

    def test_the_v1_3_layout_is_the_one_its_tables_were_first_read_at(self) -> None:
        # Arrange
        expected = boot.Layout(0x034D, 0x0356, 0x02D1, 0x02F4, 0)

        # Act
        layout = boot.LAYOUTS[V1_3]

        # Assert
        self.assertEqual(dataclasses.astuple(layout), dataclasses.astuple(expected))


if __name__ == "__main__":
    unittest.main()
