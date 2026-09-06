import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402

import smsimage  # noqa: E402
from smsimage import version  # noqa: E402


class VersionTest(unittest.TestCase):
    def test_the_version_is_three_numbers(self) -> None:
        parts = version.VERSION.split(".")

        self.assertEqual(len(parts), 3)
        self.assertTrue(all(part.isdigit() for part in parts))

    def test_the_package_reports_the_same_version(self) -> None:
        self.assertEqual(smsimage.__version__, version.VERSION)


class SurfaceTest(unittest.TestCase):
    def test_everything_it_declares_is_reachable(self) -> None:
        missing = [name for name in smsimage.__all__ if not hasattr(smsimage, name)]

        self.assertEqual(missing, [])


class ReleaseWiringTest(unittest.TestCase):
    def test_the_release_job_rewrites_the_file_the_package_reads(self) -> None:
        assets = (ROOT / ".releaserc.json").read_text()

        self.assertIn("smsimage/version.py", assets)

    def test_the_release_job_commits_the_citation_it_stamps(self) -> None:
        assets = (ROOT / ".releaserc.json").read_text()

        self.assertIn("CITATION.cff", assets)

    def test_the_script_that_rewrites_it_points_at_the_same_file(self) -> None:
        script = (ROOT / "scripts" / "set-version.sh").read_text()

        self.assertIn("smsimage/version.py", script)

    def test_the_script_also_stamps_the_citation(self) -> None:
        script = (ROOT / "scripts" / "set-version.sh").read_text()

        self.assertIn("CITATION.cff", script)

    def test_the_citation_carries_the_version_the_package_reports(self) -> None:
        cited = [
            line.removeprefix("version: ").strip()
            for line in (ROOT / "CITATION.cff").read_text().splitlines()
            if line.startswith("version: ")
        ]

        self.assertEqual(cited, [version.VERSION])


if __name__ == "__main__":
    unittest.main()
