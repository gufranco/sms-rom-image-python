import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ast  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402

from smsimage import doctor  # noqa: E402

SOURCE = ROOT / "smsimage" / "doctor.py"


class Scratch(unittest.TestCase):
    def folder(self) -> Path:
        held = tempfile.TemporaryDirectory()
        self.addCleanup(held.cleanup)
        return Path(held.name)

    def file_holding(self, name: str, text: str) -> Path:
        path = self.folder() / name
        path.write_text(text)
        return path


class VersionTest(Scratch):
    def test_it_reads_the_version_out_of_the_file_beside_it(self) -> None:
        # Arrange
        beside = ROOT / "smsimage" / "version.py"

        # Act
        found = doctor.installed_version(beside)

        # Assert
        self.assertEqual(found, doctor.VERSION)

    def test_with_nothing_handed_it_reads_the_file_beside_it(self) -> None:
        # Arrange
        expected = doctor.installed_version(ROOT / "smsimage" / "version.py")

        # Act
        found = doctor.installed_version()

        # Assert
        self.assertEqual(found, expected)

    def test_it_reads_a_version_from_a_file_it_is_handed(self) -> None:
        # Arrange
        path = self.file_holding("version.py", 'VERSION = "9.9.9"\n')

        # Act
        found = doctor.installed_version(path)

        # Assert
        self.assertEqual(found, "9.9.9")

    def test_a_file_with_no_version_in_it_reads_as_unknown(self) -> None:
        # Arrange
        path = self.file_holding("version.py", "RELEASE = 1\n")

        # Act
        found = doctor.installed_version(path)

        # Assert
        self.assertEqual(found, "unknown")


class ImportsTest(unittest.TestCase):
    def test_nothing_from_its_own_package_is_imported_at_the_top(self) -> None:
        # Arrange
        tree = ast.parse(SOURCE.read_text())

        # Act
        reached = [
            name
            for name in [
                node.module or "" for node in tree.body if isinstance(node, ast.ImportFrom)
            ]
            + [
                alias.name
                for node in tree.body
                if isinstance(node, ast.Import)
                for alias in node.names
            ]
            if name.startswith("smsimage")
        ]

        # Assert
        self.assertEqual(reached, [])

    def test_nothing_relative_is_imported_at_the_top(self) -> None:
        # Arrange
        tree = ast.parse(SOURCE.read_text())

        # Act
        relative = [
            node.module for node in tree.body if isinstance(node, ast.ImportFrom) and node.level
        ]

        # Assert
        self.assertEqual(relative, [])


class ReachableTest(unittest.TestCase):
    def test_a_root_that_is_not_on_the_path_is_put_there(self) -> None:
        # Arrange
        path: list[str] = []

        # Act
        added = doctor.reachable(Path("/somewhere"), path)

        # Assert
        self.assertEqual((added, path), (True, ["/somewhere"]))

    def test_a_root_already_on_the_path_is_left_alone(self) -> None:
        # Arrange
        path = ["/somewhere"]

        # Act
        added = doctor.reachable(Path("/somewhere"), path)

        # Assert
        self.assertEqual((added, path), (False, ["/somewhere"]))

    def test_the_repository_root_is_reachable_by_the_time_this_runs(self) -> None:
        # Arrange
        root = doctor.ROOT

        # Act
        added = doctor.reachable(root)

        # Assert
        self.assertFalse(added)


class FindingTest(unittest.TestCase):
    def test_a_finding_that_passed_reads_as_one(self) -> None:
        # Arrange
        found = doctor.Finding("a name", True, "what was there")

        # Act
        line = found.line

        # Assert
        self.assertEqual(line, "  ok    a name: what was there")

    def test_a_finding_that_did_not_carries_its_advice(self) -> None:
        # Arrange
        found = doctor.Finding("a name", False, "what was there", "what to do")

        # Act
        report = found.report

        # Assert
        self.assertEqual(report, "     !  a name: what was there\n         what to do")

    def test_a_finding_that_passed_carries_no_advice_into_the_report(self) -> None:
        # Arrange
        found = doctor.Finding("a name", True, "what was there", "what to do")

        # Act
        report = found.report

        # Assert
        self.assertNotIn("what to do", report)

    def test_a_failing_finding_with_no_advice_is_still_one_line(self) -> None:
        # Arrange
        found = doctor.Finding("a name", False, "what was there")

        # Act
        report = found.report

        # Assert
        self.assertEqual(report, found.line)

    def test_a_finding_reads_as_what_it_is(self) -> None:
        # Arrange
        findings = (doctor.Finding("a name", False, "d"), doctor.Finding("a name", True, "d"))

        # Act
        shown = [repr(one) for one in findings]

        # Assert
        self.assertEqual(shown, ["<Finding a name not ok>", "<Finding a name ok>"])


class ReportTest(unittest.TestCase):
    def test_it_looks_at_everything_it_declares(self) -> None:
        # Arrange
        declared = list(doctor.CHECKS)

        # Act
        found = doctor.examine()

        # Assert
        self.assertEqual([one.name for one in found], declared)

    def test_the_report_names_the_package_and_the_version(self) -> None:
        # Arrange
        found = [doctor.Finding("a", True, "d")]

        # Act
        lines = doctor.report(found)

        # Assert
        self.assertTrue(lines[0].startswith(f"smsimage {doctor.VERSION} on "))

    def test_a_clean_run_says_how_many_it_looked_at(self) -> None:
        # Arrange
        found = [doctor.Finding("a", True, "d")]

        # Act
        lines = doctor.report(found)

        # Assert
        self.assertEqual(lines[-1], "  1 checks, nothing to report")

    def test_a_run_with_a_fault_says_how_many_did_not_pass(self) -> None:
        # Arrange
        found = [doctor.Finding("a", True, "d"), doctor.Finding("b", False, "d")]

        # Act
        lines = doctor.report(found)

        # Assert
        self.assertEqual(lines[-1], "  1 of 2 checks did not pass")

    def test_it_reports_what_the_machine_is_as_well_as_what_the_package_is(self) -> None:
        # Arrange
        found = [doctor.Finding("a", True, "d")]

        # Act
        lines = doctor.report(found)

        # Assert
        self.assertEqual(
            ("  the machine" in lines, "  this package" in lines),
            (True, True),
        )


class MainTest(unittest.TestCase):
    def test_a_clean_run_exits_zero_and_prints_its_report(self) -> None:
        # Arrange
        said: list[str] = []

        # Act
        code = doctor.main([], lambda: [doctor.Finding("a", True, "d")], said.append)

        # Assert
        self.assertEqual((code, said[-1]), (0, "  1 checks, nothing to report"))

    def test_a_run_with_a_fault_exits_non_zero(self) -> None:
        # Arrange
        said: list[str] = []

        # Act
        code = doctor.main([], lambda: [doctor.Finding("a", False, "d")], said.append)

        # Assert
        self.assertEqual(code, 1)

    def test_the_real_run_on_this_machine_reports_nothing_wrong(self) -> None:
        # Arrange
        said: list[str] = []

        # Act
        code = doctor.main([], say=said.append)

        # Assert
        self.assertEqual(code, 0, "\n".join(said))


class AsDocumentedTest(unittest.TestCase):
    def run_as_a_file(self) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as elsewhere:
            return subprocess.run(
                [sys.executable, str(ROOT / "smsimage" / "doctor.py")],
                capture_output=True,
                text=True,
                cwd=elsewhere,
                check=False,
            )

    def test_running_it_as_a_file_prints_a_report(self) -> None:
        # Arrange
        expected = f"  {len(doctor.CHECKS)} checks, nothing to report"

        # Act
        finished = self.run_as_a_file()

        # Assert
        self.assertEqual(
            (finished.returncode, finished.stdout.splitlines()[-1]),
            (0, expected),
            finished.stdout + finished.stderr,
        )

    def test_it_prints_a_report_rather_than_a_traceback(self) -> None:
        # Arrange
        marker = "Traceback"

        # Act
        finished = self.run_as_a_file()

        # Assert
        self.assertNotIn(marker, finished.stdout + finished.stderr)

    def test_the_readme_names_the_invocation_that_works(self) -> None:
        # Arrange
        readme = ROOT / "README.md"

        # Act
        said = readme.read_text()

        # Assert
        self.assertIn("python3 smsimage/doctor.py", said)


if __name__ == "__main__":
    unittest.main()
