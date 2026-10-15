import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ast  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402

from smsimage import doctor  # noqa: E402

SOURCE = ROOT / "smsimage" / "doctor.py"


def broken(_: object = None) -> bytes:
    raise ValueError("this build refuses")


class VersionTest(unittest.TestCase):
    def test_it_reads_the_version_out_of_the_file_beside_it(self) -> None:
        self.assertEqual(doctor.VERSION, doctor._version())

    def test_it_reads_a_version_from_a_file_it_is_handed(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            path = Path(where) / "version.py"
            path.write_text('VERSION = "9.9.9"\n')

            self.assertEqual(doctor._version(path), "9.9.9")

    def test_a_file_with_no_version_in_it_reads_as_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            path = Path(where) / "version.py"
            path.write_text("RELEASE = 1\n")

            self.assertEqual(doctor._version(path), "unknown")


class ImportsTest(unittest.TestCase):
    def imported_at_the_top(self) -> list[str]:
        tree = ast.parse(SOURCE.read_text())
        return [node.module or "" for node in tree.body if isinstance(node, ast.ImportFrom)] + [
            alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names
        ]

    def test_nothing_from_its_own_package_is_imported_at_the_top(self) -> None:
        reached = [one for one in self.imported_at_the_top() if one.startswith("smsimage")]

        self.assertEqual(reached, [])

    def test_nothing_relative_is_imported_at_the_top(self) -> None:
        tree = ast.parse(SOURCE.read_text())
        relative = [
            node.module for node in tree.body if isinstance(node, ast.ImportFrom) and node.level
        ]

        self.assertEqual(relative, [])


class ReachableTest(unittest.TestCase):
    def test_a_root_that_is_not_on_the_path_is_put_there(self) -> None:
        path: list[str] = []

        added = doctor._reachable(Path("/somewhere"), path)

        self.assertTrue(added)
        self.assertEqual(path, ["/somewhere"])

    def test_a_root_already_on_the_path_is_left_alone(self) -> None:
        path = ["/somewhere"]

        added = doctor._reachable(Path("/somewhere"), path)

        self.assertFalse(added)
        self.assertEqual(path, ["/somewhere"])

    def test_the_repository_root_is_reachable_by_the_time_this_runs(self) -> None:
        self.assertFalse(doctor._reachable())


class FindingTest(unittest.TestCase):
    def test_a_finding_that_passed_reads_as_one(self) -> None:
        found = doctor.Finding("a name", True, "what was there")

        self.assertIn("ok", found.line)
        self.assertIn("a name", found.line)

    def test_a_finding_that_did_not_carries_its_advice(self) -> None:
        found = doctor.Finding("a name", False, "what was there", "what to do")

        self.assertIn("what to do", found.report)

    def test_a_finding_that_passed_carries_no_advice_into_the_report(self) -> None:
        found = doctor.Finding("a name", True, "what was there", "what to do")

        self.assertNotIn("what to do", found.report)

    def test_a_failing_finding_with_no_advice_is_still_one_line(self) -> None:
        found = doctor.Finding("a name", False, "what was there")

        self.assertEqual(found.report, found.line)

    def test_a_finding_reads_as_what_it_is(self) -> None:
        self.assertIn("not ok", repr(doctor.Finding("a name", False, "detail")))
        self.assertIn("ok", repr(doctor.Finding("a name", True, "detail")))


class PackageTest(unittest.TestCase):
    def test_the_package_this_repository_ships_imports(self) -> None:
        found = doctor._package()

        self.assertTrue(found.ok)
        self.assertIn("smsimage", found.detail)

    def test_a_package_that_will_not_import_is_reported_by_what_it_threw(self) -> None:
        found = doctor._package(broken)

        self.assertFalse(found.ok)
        self.assertIn("ValueError", found.detail)


class DrivingTest(unittest.TestCase):
    def test_it_reads_a_dump_it_built_here(self) -> None:
        self.assertTrue(doctor._reading().ok)

    def test_the_dump_it_reads_carries_a_whole_copier_block(self) -> None:
        # Arrange
        image = doctor._synthetic()

        # Act
        found = doctor._reading()

        # Assert
        self.assertIn(
            f"a {len(image) + 512} byte dump read back to {len(image)} bytes", found.detail
        )

    def test_a_reader_that_refuses_is_reported_by_what_it_threw(self) -> None:
        found = doctor._reading(broken)

        self.assertFalse(found.ok)
        self.assertIn("ValueError", found.detail)

    def test_it_finds_a_header_in_an_image_it_built_here(self) -> None:
        self.assertTrue(doctor._anchoring().ok)

    def test_an_anchor_that_refuses_is_reported_by_what_it_threw(self) -> None:
        found = doctor._anchoring(broken)

        self.assertFalse(found.ok)
        self.assertIn("ValueError", found.detail)

    def test_it_reproduces_a_checksum_on_an_image_it_sealed_here(self) -> None:
        self.assertTrue(doctor._checksumming().ok)

    def test_a_checksum_that_refuses_is_reported_by_what_it_threw(self) -> None:
        found = doctor._checksumming(broken)

        self.assertFalse(found.ok)
        self.assertIn("ValueError", found.detail)

    def test_it_measures_an_image_it_built_here(self) -> None:
        self.assertTrue(doctor._measuring().ok)

    def test_a_measurement_that_refuses_is_reported_by_what_it_threw(self) -> None:
        found = doctor._measuring(broken)

        self.assertFalse(found.ok)
        self.assertIn("ValueError", found.detail)

    def test_an_image_it_built_that_yields_no_checksum_is_a_fault(self) -> None:
        from smsimage import header

        original = header.checksum
        header.checksum = lambda _: None  # type: ignore[assignment]
        try:
            with self.assertRaises(ValueError):
                doctor._synthetic()
        finally:
            header.checksum = original


class ArtifactTest(unittest.TestCase):
    def test_it_reads_the_manifest_this_repository_ships(self) -> None:
        found = doctor._artifacts()

        self.assertTrue(found.ok)
        self.assertIn("14", found.detail)

    def test_a_manifest_that_is_not_there_is_reported_as_absent(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            found = doctor._artifacts(Path(where) / "artifacts.manifest.json")

        self.assertFalse(found.ok)
        self.assertIn("not here", found.detail)

    def test_a_manifest_that_is_not_one_is_reported_by_what_it_threw(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            path = Path(where) / "artifacts.manifest.json"
            path.write_text('{"note": "nothing here yet"}')

            found = doctor._artifacts(path)

        self.assertFalse(found.ok)
        self.assertIn("Malformed", found.detail)


class CorpusTest(unittest.TestCase):
    def test_it_reads_the_corpus_this_repository_ships(self) -> None:
        found = doctor._corpus()

        self.assertTrue(found.ok)
        self.assertIn("combinations", found.detail)

    def test_a_corpus_that_is_not_there_is_reported_as_absent(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            found = doctor._corpus(Path(where) / "corpus.json")

        self.assertFalse(found.ok)
        self.assertIn("not here", found.detail)

    def test_a_corpus_holding_nothing_is_told_apart_from_one_that_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            path = Path(where) / "corpus.json"
            path.write_text("[]")

            found = doctor._corpus(path)

        self.assertFalse(found.ok)
        self.assertIn("holds nothing", found.detail)

    def test_a_corpus_that_will_not_parse_is_reported_by_what_it_threw(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            path = Path(where) / "corpus.json"
            path.write_text("{not json")

            found = doctor._corpus(path)

        self.assertFalse(found.ok)
        self.assertIn("JSONDecodeError", found.detail)


class LibraryTest(unittest.TestCase):
    def test_it_says_the_census_takes_its_library_as_an_argument(self) -> None:
        found = doctor._library()

        self.assertTrue(found.ok)
        self.assertIn("argument", found.detail)


class ReportTest(unittest.TestCase):
    def test_it_looks_at_everything_it_declares(self) -> None:
        found = doctor.examine()

        self.assertEqual(len(found), len(doctor.CHECKS))

    def test_the_report_names_the_package_and_the_version(self) -> None:
        lines = doctor.report(doctor.examine())

        self.assertIn("smsimage", lines[0])
        self.assertIn(doctor.VERSION, lines[0])

    def test_a_clean_run_says_how_many_it_looked_at(self) -> None:
        lines = doctor.report([doctor.Finding("a", True, "d")])

        self.assertIn("1 checks, nothing to report", lines[-1])

    def test_a_run_with_a_fault_says_how_many_did_not_pass(self) -> None:
        lines = doctor.report([doctor.Finding("a", True, "d"), doctor.Finding("b", False, "d")])

        self.assertIn("1 of 2", lines[-1])

    def test_it_reports_what_the_machine_is_as_well_as_what_the_package_is(self) -> None:
        lines = doctor.report(doctor.examine())

        self.assertIn("  the machine", lines)
        self.assertIn("  this package", lines)


class MainTest(unittest.TestCase):
    def test_a_clean_run_exits_zero_and_prints_its_report(self) -> None:
        said: list[str] = []

        code = doctor.main([], lambda: [doctor.Finding("a", True, "d")], said.append)

        self.assertEqual(code, 0)
        self.assertTrue(any("a" in one for one in said))

    def test_a_run_with_a_fault_exits_non_zero(self) -> None:
        code = doctor.main([], lambda: [doctor.Finding("a", False, "d")], lambda _: None)

        self.assertEqual(code, 1)

    def test_the_real_run_on_this_machine_reports_nothing_wrong(self) -> None:
        said: list[str] = []

        code = doctor.main([], say=said.append)

        self.assertEqual(code, 0, "\n".join(said))


class ShippedTest(unittest.TestCase):
    def test_the_manifest_it_reads_declares_what_the_file_declares(self) -> None:
        declared = json.loads((ROOT / "artifacts.manifest.json").read_text())["artifacts"]

        self.assertIn(str(len(declared)), doctor._artifacts().detail)

    def test_the_corpus_it_reads_counts_what_the_file_counts(self) -> None:
        combinations = json.loads((ROOT / "conformance" / "corpus.json").read_text())

        self.assertIn(str(len(combinations)), doctor._corpus().detail)


class AsDocumentedTest(unittest.TestCase):
    def test_running_it_as_a_file_prints_a_report(self) -> None:
        with tempfile.TemporaryDirectory() as elsewhere:
            finished = subprocess.run(
                [sys.executable, str(ROOT / "smsimage" / "doctor.py")],
                capture_output=True,
                text=True,
                cwd=elsewhere,
                check=False,
            )

        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        self.assertIn("checks, nothing to report", finished.stdout)

    def test_it_prints_a_report_rather_than_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as elsewhere:
            finished = subprocess.run(
                [sys.executable, str(ROOT / "smsimage" / "doctor.py")],
                capture_output=True,
                text=True,
                cwd=elsewhere,
                check=False,
            )

        self.assertNotIn("Traceback", finished.stdout + finished.stderr)

    def test_the_readme_names_the_invocation_that_works(self) -> None:
        # Arrange
        readme = ROOT / "README.md"

        # Act
        said = readme.read_text()

        # Assert
        self.assertIn("python3 smsimage/doctor.py", said)


if __name__ == "__main__":
    unittest.main()
