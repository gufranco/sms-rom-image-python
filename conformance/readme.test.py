"""That every worked example in the readme still does what it says.

A readme example is a promise a reader tests by pasting it, so an example that
has stopped working is worse than an absent one: it is the first thing a new
reader runs and the first impression they get. Nothing else in the suite touches
these lines, because they live in prose rather than in a module, which is exactly
why they rot quietly.

Each example runs in a fresh interpreter rather than in this one. An example that
only works because a test already imported something is not an example a reader
can paste, and running it here in-process would hide that.

An example that cannot run at all here is reported as skipped rather than as
broken, and only when the member itself says why. Two members model a part that
runs a program their repository is not allowed to carry, so on a machine without
one every example that builds a part refuses. That refusal is the package working
correctly, and counting it as a broken example would make a bare checkout look
like a defect while hiding real ones behind it.

What decides is the member's own `why_not`, which is the same sentence its doctor
prints. A member that publishes none skips nothing, and on a machine that has the
files nothing is skipped either, so the check keeps its teeth exactly where it
had them.
"""

from __future__ import annotations

import contextlib
import importlib
import re
import subprocess
import sys
import unittest
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent

README = ROOT / "README.md"


def packages() -> list[str]:
    """The importable package in this repository, which is the member itself.

    The conformance directory is one too and is not the member, so it is left
    out by name rather than by position.
    """
    return sorted(
        found.name
        for found in ROOT.iterdir()
        if (found / "__init__.py").is_file() and found.name != "conformance"
    )


def cannot_run_here(named: list[str] | None = None) -> str | None:
    """Why this member cannot build its part on this machine, or nothing.

    Read off the package rather than guessed from a traceback, so the sentence
    an example is excused by is the sentence the member itself publishes.

    The names are a parameter so this can be driven against a member that
    publishes a reason from a member that does not, and the other way round.
    Nine of the sixteen publish nothing, and a branch only two of them reach is
    a branch nobody has seen work.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    for name in packages() if named is None else named:
        asked = getattr(importlib.import_module(name), "why_not", None)
        if callable(asked):
            answer = asked()
            return str(answer) if answer else None
    return None


def excused(failure: str, reason: str | None = None) -> bool:
    """Whether that failure is the member saying it has no file to run.

    Matched on a run of the member's own sentence rather than on an exception
    name, because the name differs per member and the sentence is the thing the
    member publishes for exactly this purpose.
    """
    said = cannot_run_here() if reason is None else reason
    return bool(said) and str(said)[:40] in failure


BLOCK = re.compile(r"^```(\w*)\n(.*?)^```$", re.M | re.S)


def blocks(text: str | None = None) -> list[tuple[str, str]]:
    return [
        (lang, body)
        for lang, body in BLOCK.findall(text if text is not None else README.read_text())
    ]


def examples(text: str | None = None) -> list[tuple[str, str | None]]:
    """Each python block, paired with the output block that follows it.

    `text` is here so the collectors below can be driven against a readme that
    is deliberately wrong. A checker nothing has ever seen fail is a checker
    nobody knows the failure path of.
    """
    found = blocks(text)
    paired: list[tuple[str, str | None]] = []
    for index, (lang, body) in enumerate(found):
        if lang != "python":
            continue
        after = found[index + 1] if index + 1 < len(found) else None
        paired.append((body, after[1] if after and after[0] == "" else None))
    return paired


def ran(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", source],
        capture_output=True,
        check=False,
        text=True,
        cwd=ROOT,
        timeout=120,
    )


def broken(found: list[tuple[str, str | None]], reason: str | None = None) -> list[str]:
    """The last line of the traceback of every example that will not run.

    A process can exit non-zero and print nothing, so the reason falls back to
    the exit code rather than indexing an empty list. A checker that raises
    while collecting a fault reports neither that fault nor any after it.
    """
    failed = []
    reason = cannot_run_here() if reason is None else reason
    for source, _ in found:
        finished = ran(source)
        if finished.returncode == 0:
            continue
        if excused(finished.stderr, reason):
            continue
        said = finished.stderr.strip().splitlines()
        failed.append(said[-1] if said else f"exited {finished.returncode} in silence")
    return failed


def mismatched(
    found: list[tuple[str, str | None]], reason: str | None = None
) -> list[tuple[str, str]]:
    """What the readme claims each example prints, beside what it printed."""
    wrong = []
    reason = cannot_run_here() if reason is None else reason
    for source, expected in found:
        if expected is None:
            continue
        finished = ran(source)
        if finished.returncode != 0 and excused(finished.stderr, reason):
            continue
        if finished.stdout != expected:
            wrong.append((expected.strip(), finished.stdout.strip()))
    return wrong


@contextlib.contextmanager
def installed(name: str, module: ModuleType) -> Iterator[None]:
    sys.modules[name] = module
    try:
        yield
    finally:
        del sys.modules[name]


def publishing(name: str, answer: str | None) -> ModuleType:
    module = ModuleType(name)
    module.why_not = lambda: answer  # type: ignore[attr-defined]
    return module


FIRMWARE = "no firmware image was found: this backend runs the part's own microcode"


class WorkedExampleTest(unittest.TestCase):
    def test_there_are_examples_to_check(self) -> None:
        # Arrange
        readme = README.read_text()

        # Act
        found = examples(readme)

        # Assert
        self.assertGreaterEqual(len(found), 4)

    def test_every_example_that_can_run_here_runs(self) -> None:
        # Arrange
        found = examples()

        # Act
        failed = broken(found)

        # Assert
        self.assertEqual(failed, [])

    def test_every_example_prints_what_the_readme_says_it_prints(self) -> None:
        # Arrange
        found = examples()

        # Act
        wrong = mismatched(found)

        # Assert
        self.assertEqual(wrong, [])

    def test_every_example_is_run_and_none_is_skipped(self) -> None:
        # Arrange
        readme = README.read_text()

        # Act
        found = examples(readme)

        # Assert
        self.assertEqual(len([body for body, _ in found if body.strip()]), len(found))


class CheckerTest(unittest.TestCase):
    """That the collectors above report a fault rather than sailing past one.

    They are the only thing standing between a rotted example and a reader, so a
    run in which they have never been seen to fail says nothing about them. Each
    is driven against a readme crafted here rather than inherited from whichever
    readme this member has: on a member whose every example needs a file it may
    not ship, no example succeeds on a runner, and the arc that reports success
    would otherwise be covered on one machine and not on another.

    Two mismatching examples with the failure first is the only arrangement in
    which continuing after a failure is observable, so that case carries two. The
    excuse a member publishes is driven against stand-in modules, because most
    members publish none and a branch only two of them reach is a branch nobody
    has seen work.
    """

    def test_an_example_that_runs_is_not_reported(self) -> None:
        # Arrange
        readme = "```python\nprint(1)\n```\n"

        # Act
        failed = broken(examples(readme))

        # Assert
        self.assertEqual(failed, [])

    def test_an_example_that_raises_is_reported(self) -> None:
        # Arrange
        readme = '```python\nraise ValueError("nope")\n```\n'

        # Act
        failed = broken(examples(readme))

        # Assert
        self.assertEqual(failed, ["ValueError: nope"])

    def test_an_example_that_fails_in_silence_is_still_reported(self) -> None:
        # Arrange
        readme = "```python\nraise SystemExit(3)\n```\n"

        # Act
        failed = broken(examples(readme))

        # Assert
        self.assertEqual(failed, ["exited 3 in silence"])

    def test_an_example_that_prints_the_wrong_thing_is_reported(self) -> None:
        # Arrange
        readme = "```python\nprint(1)\n```\n\n```\n2\n```\n"

        # Act
        wrong = mismatched(examples(readme))

        # Assert
        self.assertEqual(wrong, [("2", "1")])

    def test_and_a_later_example_is_still_checked_after_an_earlier_one_failed(self) -> None:
        # Arrange
        readme = (
            "```python\nprint(1)\n```\n\n```\n2\n```\n\n```python\nprint(3)\n```\n\n```\n3\n```\n"
        )

        # Act
        wrong = mismatched(examples(readme))

        # Assert
        self.assertEqual(wrong, [("2", "1")])

    def test_an_example_with_no_stated_output_is_only_run(self) -> None:
        # Arrange
        readme = "```python\nprint(1)\n```\n"

        # Act
        wrong = mismatched(examples(readme))

        # Assert
        self.assertEqual(wrong, [])

    def test_a_member_that_can_run_everything_excuses_nothing(self) -> None:
        # Arrange
        reason = None if cannot_run_here() else "x" * 60

        # Act
        forgiven = excused("anything at all", reason)

        # Assert
        self.assertFalse(forgiven)

    def test_a_failure_the_member_says_it_expects_is_excused(self) -> None:
        # Arrange
        failure = f"Traceback\nNoFirmware: {FIRMWARE}"

        # Act
        forgiven = excused(failure, FIRMWARE)

        # Assert
        self.assertTrue(forgiven)

    def test_and_any_other_failure_is_not(self) -> None:
        # Arrange
        failure = "Traceback\nZeroDivisionError: division by zero"

        # Act
        forgiven = excused(failure, FIRMWARE)

        # Assert
        self.assertFalse(forgiven)

    def test_and_a_member_that_publishes_no_reason_excuses_nothing(self) -> None:
        # Arrange
        failure = "Traceback\nNoFirmware: anything"

        # Act
        forgiven = excused(failure, "")

        # Assert
        self.assertFalse(forgiven)

    def test_an_example_that_only_this_machine_can_run_is_reported_as_broken(self) -> None:
        # Arrange
        readme = "```python\nraise ValueError('nope')\n```\n"

        # Act
        failed = broken(examples(readme))

        # Assert
        self.assertEqual(failed, ["ValueError: nope"])

    def test_an_example_the_member_says_it_cannot_run_is_not_reported_as_broken(self) -> None:
        # Arrange
        readme = "```python\nraise SystemExit('no image is here')\n```\n"

        # Act
        failed = broken(examples(readme), "no image is here")

        # Assert
        self.assertEqual(failed, [])

    def test_and_its_stated_output_is_not_compared_either(self) -> None:
        # Arrange
        readme = "```python\nraise SystemExit('no image is here')\n```\n\n```\n7\n```\n"

        # Act
        wrong = mismatched(examples(readme), "no image is here")

        # Assert
        self.assertEqual(wrong, [])

    def test_a_member_that_publishes_a_reason_is_read(self) -> None:
        # Arrange
        speaking = publishing("speaking", "no image is here")

        # Act
        with installed("speaking", speaking):
            said = cannot_run_here(["speaking"])

        # Assert
        self.assertEqual(said, "no image is here")

    def test_and_one_that_publishes_nothing_to_say_says_nothing(self) -> None:
        # Arrange
        quiet = publishing("quiet", None)

        # Act
        with installed("quiet", quiet):
            said = cannot_run_here(["quiet"])

        # Assert
        self.assertIsNone(said)

    def test_and_one_that_publishes_no_such_call_is_passed_over(self) -> None:
        # Arrange
        silent = ModuleType("silent")

        # Act
        with installed("silent", silent):
            said = cannot_run_here(["silent"])

        # Assert
        self.assertIsNone(said)

    def test_the_member_this_repository_holds_is_found_by_name(self) -> None:
        # Arrange
        excluded = "conformance"

        # Act
        found = packages()

        # Assert
        self.assertNotIn(excluded, found)


if __name__ == "__main__":
    unittest.main(verbosity=2)
