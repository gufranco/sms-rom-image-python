from __future__ import annotations

import ast
import importlib
import inspect
import json
import posixpath
import re
import subprocess
import sys
import tempfile
import tokenize
import tomllib
import types
import unittest
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any, ClassVar, Protocol

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import smsimage  # noqa: E402

FAMILY = (ROOT / "FAMILY.md").read_text()

KIND = "Format"

CLOCKED = KIND == "Clocked part"

PACKAGE: Any = smsimage

TOOL_MODULES = {"doctor", "environment"}

TESTED_DIRECTORIES = ("smsimage", "conformance")

A_MODEL = sorted(PACKAGE.MODELS)[0] if hasattr(PACKAGE, "MODELS") else ""


def why_it_cannot_build_here() -> str | None:
    asked = getattr(PACKAGE, "why_not", None)
    return asked() if callable(asked) else None


BUILDABLE = why_it_cannot_build_here() is None


A_PART = KIND == "Part"


SOLD_AS_A_COMPONENT = False

INTERFACE = (
    "step",
    "run_for",
    "run_until",
    "reset",
    "held",
)

INTERRUPT_LINES = ("irq", "nmi")

COUNTERS = ("cycles", "steps")


class Part(Protocol):
    cycles: int
    steps: int

    def step(self) -> int: ...

    def run_for(self, cycles: int) -> int: ...

    def run_until(self, predicate: Any, limit: int | None = None) -> Any: ...

    def reset(self) -> Any: ...

    def held(self) -> bool: ...


def a_part() -> Part:  # pragma: no cover
    part: Part = PACKAGE.Cpu(A_MODEL)
    return part


def store_attribute() -> str:  # pragma: no cover
    part = PACKAGE.Cpu(A_MODEL)
    found = [name for name in ("memory", "stores") if getattr(part, name, None) is not None]
    assert found, "a clocked part keeps its store on `memory` or on `stores`"
    return found[0]


def accounts_for_one_interrupt(node: Any) -> bool:  # pragma: no cover
    if isinstance(node, dict):
        if any("interrupt" in str(key).lower() for key in node):
            return True
        return any(accounts_for_one_interrupt(one) for one in node.values())
    if isinstance(node, list):
        return any(accounts_for_one_interrupt(one) for one in node)
    return "interrupt" in str(node).lower()


def at_the_start(part: Any) -> None:  # pragma: no cover
    held = getattr(part, "registers", part)
    held.pc = 0x0000


def a_running_part() -> Part:  # pragma: no cover
    part = PACKAGE.Cpu(A_MODEL, fill=0)
    at_the_start(part)
    checked: Part = part
    return checked


class ModelsAClockedPartTest(unittest.TestCase):
    def row(self) -> str:
        pattern = rf"^\|\s*\[{re.escape(ROOT.name)}\]\([^)]*\)\s*\|(.+)\|(.+)\|\s*$"
        found = re.search(pattern, FAMILY, re.M)

        assert found is not None, f"{ROOT.name} is not in the membership table"
        return found.group(2).strip()

    def test_this_member_is_in_the_membership_table(self) -> None:
        # Arrange
        member = ROOT.name

        # Act
        listed = member in FAMILY

        # Assert
        self.assertTrue(listed, member)

    def test_and_the_kind_it_declares_is_the_kind_the_table_gives_it(self) -> None:
        # Arrange
        declared = KIND

        # Act
        given = self.row()

        # Assert
        self.assertEqual(declared, given)

    def test_the_table_only_uses_kinds_the_standard_explains(self) -> None:
        # Arrange
        explained = {"Clocked part", "Part", "Board", "Format", "Tool"}

        # Act
        kinds = set(re.findall(r"\|\s*(Clocked part|Part|Board|Format|Tool)\s*\|", FAMILY))

        # Assert
        self.assertTrue(kinds <= explained)
        self.assertIn(KIND, kinds)

    def test_the_standard_says_what_a_kind_that_is_not_clocked_skips(self) -> None:
        # Arrange
        sentence = "skips the section about a clock"

        # Act
        said = sentence in FAMILY

        # Assert
        self.assertTrue(said)


@unittest.skipUnless(CLOCKED, "not a clocked part")  # pragma: no cover
class PromisedInterfaceTest(unittest.TestCase):
    def test_every_call_the_standard_names_exists_here(self) -> None:
        # Arrange
        part = a_part()

        # Act
        absent = [name for name in INTERFACE if not hasattr(part, name)]

        # Assert
        self.assertEqual(absent, [])

    def test_and_every_interrupt_line_the_part_has(self) -> None:
        # Arrange
        part = a_part()

        # Act
        absent = [name for name in INTERRUPT_LINES if not hasattr(part, name)]

        # Assert
        self.assertEqual(absent, [])

    def test_and_the_record_accounts_for_what_lines_it_names(self) -> None:
        # Arrange
        record = json.loads(RECORD.read_text())

        # Act
        accounted = accounts_for_one_interrupt(record)

        # Assert
        self.assertTrue(accounted)

    def test_a_record_naming_an_interrupt_as_a_key_is_read(self) -> None:
        # Arrange
        record = {"facts": {"interruptVector": 4}}

        # Act
        accounted = accounts_for_one_interrupt(record)

        # Assert
        self.assertTrue(accounted)

    def test_and_one_naming_it_only_in_a_sentence(self) -> None:
        # Arrange
        record = {"notStated": ["what the interrupt pin does"]}

        # Act
        accounted = accounts_for_one_interrupt(record)

        # Assert
        self.assertTrue(accounted)

    def test_and_one_naming_it_inside_a_list(self) -> None:
        # Arrange
        record = [{"note": "one interrupt line"}]

        # Act
        accounted = accounts_for_one_interrupt(record)

        # Assert
        self.assertTrue(accounted)

    def test_and_a_record_that_never_mentions_one_is_reported(self) -> None:
        # Arrange
        record = {"facts": {"window": [1, 2]}, "note": "a part"}

        # Act
        accounted = accounts_for_one_interrupt(record)

        # Assert
        self.assertFalse(accounted)

    def test_and_every_counter(self) -> None:
        # Arrange
        part = a_part()

        # Act
        absent = [name for name in COUNTERS if not hasattr(part, name)]

        # Assert
        self.assertEqual(absent, [])

    def test_the_standard_names_each_of_them(self) -> None:
        # Arrange
        names = INTERFACE + COUNTERS

        # Act
        unnamed = [name for name in names if name not in FAMILY]

        # Assert
        self.assertEqual(unnamed, [])


@unittest.skipUnless(CLOCKED, "not a clocked part")  # pragma: no cover
class PromisedBehaviourTest(unittest.TestCase):
    def test_a_step_reports_what_it_cost(self) -> None:
        # Arrange
        part = a_running_part()

        # Act
        cost = part.step()

        # Assert
        self.assertIsInstance(cost, int)

    def test_a_budget_reports_what_it_spent(self) -> None:
        # Arrange
        part = a_running_part()

        # Act
        spent = part.run_for(64)

        # Assert
        self.assertGreaterEqual(spent, 64)

    def test_the_budget_parameter_is_named_for_the_family(self) -> None:
        # Arrange
        part = a_part()

        # Act
        named = list(inspect.signature(part.run_for).parameters)

        # Assert
        self.assertEqual(named, ["cycles"])

    def test_a_reset_hands_the_part_back(self) -> None:
        # Arrange
        part = a_part()

        # Act
        handed = part.reset()

        # Assert
        self.assertIs(handed, part)

    def test_the_tally_survives_a_reset(self) -> None:
        # Arrange
        part = a_running_part()
        part.run_for(64)
        before = part.cycles

        # Act
        part.reset()

        # Assert
        self.assertGreaterEqual(part.cycles, before)

    def test_a_bounded_run_gives_up_rather_than_hanging(self) -> None:
        # Arrange
        part = a_running_part()

        # Act
        attempt = lambda: part.run_until(lambda _: False, limit=32)  # noqa: E731

        # Assert
        self.assertRaises(PACKAGE.RunLimit, attempt)

    def test_a_running_part_is_not_held(self) -> None:
        # Arrange
        part = a_part()

        # Act
        held = part.held()

        # Assert
        self.assertFalse(held)


SURFACE = (
    "Cpu",
    "MODELS",
    "UNSET_SEED",
    "Clock",
    "ClockClosed",
    "RunLimit",
    "UnknownModelError",
)


PART_SURFACE = (
    "Chip",
    "MODELS",
    "Model",
    "UnknownModelError",
)


def buildable_variants(package: Any = None, variants: Any = None) -> list[str]:
    known = VARIANTS if variants is None else variants
    asked = getattr(PACKAGE if package is None else package, "available", None)
    if not callable(asked):
        return sorted(known)
    held = asked()
    if not isinstance(held, Mapping):
        return sorted(known)
    return sorted(name for name in known if name in held)


class BuildableVariantTest(unittest.TestCase):
    NAMED: ClassVar[dict[str, object]] = {"one": object(), "two": object()}

    class Silent:
        pass

    class Odd:
        @staticmethod
        def available() -> int:
            return 7

    class Partial:
        @staticmethod
        def available() -> dict[str, int]:
            return {"two": 1}

    def test_a_member_that_publishes_no_catalogue_can_build_everything_it_names(self) -> None:
        # Arrange
        member = self.Silent()

        # Act
        found = buildable_variants(member, self.NAMED)

        # Assert
        self.assertEqual(found, ["one", "two"])

    def test_and_so_can_one_whose_catalogue_is_not_a_mapping(self) -> None:
        # Arrange
        member = self.Odd()

        # Act
        found = buildable_variants(member, self.NAMED)

        # Assert
        self.assertEqual(found, ["one", "two"])

    def test_a_member_holding_one_file_can_build_that_one(self) -> None:
        # Arrange
        member = self.Partial()

        # Act
        found = buildable_variants(member, self.NAMED)

        # Assert
        self.assertEqual(found, ["two"])


def public_exceptions() -> list[str]:
    errors = importlib.import_module(f"{PACKAGE.__name__}.errors")
    return [
        name
        for name, held in vars(errors).items()
        if isinstance(held, type)
        and issubclass(held, Exception)
        and not name.startswith("_")
        and held.__module__ == errors.__name__
    ]


class PublishedSurfaceTest(unittest.TestCase):
    @unittest.skipUnless(CLOCKED, "not a clocked part")  # pragma: no cover
    def test_every_name_the_standard_promises_is_published(self) -> None:
        # Arrange
        published = PACKAGE.__all__

        # Act
        absent = [name for name in SURFACE if name not in published]

        # Assert
        self.assertEqual(absent, [])

    @unittest.skipUnless(CLOCKED, "not a clocked part")  # pragma: no cover
    def test_and_each_one_is_actually_reachable(self) -> None:
        # Arrange
        names = SURFACE

        # Act
        absent = [name for name in names if not hasattr(PACKAGE, name)]

        # Assert
        self.assertEqual(absent, [])

    @unittest.skipUnless(CLOCKED, "not a clocked part")  # pragma: no cover
    def test_the_part_a_caller_gets_back_is_called_Cpu(self) -> None:  # noqa: N802
        # Arrange
        model = A_MODEL

        # Act
        built = PACKAGE.Cpu(model)

        # Assert
        self.assertEqual(type(built).__name__, "Cpu")

    @unittest.skipUnless(A_PART and BUILDABLE, "no part can be built here")  # pragma: no cover
    def test_a_part_is_built_by_Chip_taking_the_model_first(self) -> None:  # noqa: N802
        # Arrange
        model = A_MODEL

        # Act
        built = PACKAGE.Chip(model)

        # Assert
        self.assertEqual(type(built).__name__, "Chip")

    @unittest.skipUnless(A_PART and BUILDABLE, "no part can be built here")  # pragma: no cover
    def test_and_it_takes_a_model_by_name(self) -> None:
        # Arrange
        names = buildable_variants()

        # Act
        built = {name: PACKAGE.Chip(name).model for name in names}

        # Assert
        self.assertEqual(built, {name: name for name in names})

    @unittest.skipUnless(A_PART, "not a part in the sense this checks")  # pragma: no cover
    def test_and_refuses_a_name_no_model_goes_by(self) -> None:
        # Arrange
        name = "no model goes by this name"

        # Act
        attempt = lambda: PACKAGE.Chip(name)  # noqa: E731

        # Assert
        self.assertRaises(PACKAGE.UnknownModelError, attempt)

    @unittest.skipUnless(A_PART and BUILDABLE, "no part can be built here")  # pragma: no cover
    def test_a_part_that_holds_what_it_held_offers_a_reset(self) -> None:
        # Arrange
        built = PACKAGE.Chip(A_MODEL)

        # Act
        offered = callable(getattr(built, "reset", None))

        # Assert
        self.assertTrue(offered)

    @unittest.skipUnless(A_PART and BUILDABLE, "no part can be built here")  # pragma: no cover
    def test_and_that_reset_hands_the_part_back(self) -> None:
        # Arrange
        built = PACKAGE.Chip(A_MODEL)

        # Act
        handed = built.reset()

        # Assert
        self.assertIs(handed, built)

    @unittest.skipUnless(A_PART, "not a part in the sense this checks")  # pragma: no cover
    def test_and_what_that_reset_does_is_accounted_for(self) -> None:
        # Arrange
        record = json.loads(RECORD.read_text())

        # Act
        accounted = accounts_for_a_reset(record)

        # Assert
        self.assertTrue(accounted)

    @unittest.skipUnless(A_PART, "not a part in the sense this checks")  # pragma: no cover
    def test_the_reader_of_that_finds_a_reset_named_as_a_key(self) -> None:
        # Arrange
        record = {"facts": {"resetPulseCycles": {"value": 4}}}

        # Act
        accounted = accounts_for_a_reset(record)

        # Assert
        self.assertTrue(accounted)

    @unittest.skipUnless(A_PART, "not a part in the sense this checks")  # pragma: no cover
    def test_and_one_named_only_in_a_sentence(self) -> None:
        # Arrange
        record = {"notStated": ["what the RESET line does"]}

        # Act
        accounted = accounts_for_a_reset(record)

        # Assert
        self.assertTrue(accounted)

    @unittest.skipUnless(A_PART, "not a part in the sense this checks")  # pragma: no cover
    def test_and_reports_a_record_that_never_mentions_one(self) -> None:
        # Arrange
        record = {"facts": {"window": [1, 2]}, "note": "a chip"}

        # Act
        accounted = accounts_for_a_reset(record)

        # Assert
        self.assertFalse(accounted)

    @unittest.skipUnless(A_PART, "not a part in the sense this checks")  # pragma: no cover
    def test_every_name_a_part_promises_is_published(self) -> None:
        # Arrange
        published = PACKAGE.__all__

        # Act
        absent = [name for name in PART_SURFACE if name not in published]

        # Assert
        self.assertEqual(absent, [])

    @unittest.skipUnless(CLOCKED, "not a clocked part")  # pragma: no cover
    def test_the_store_type_is_reachable_without_a_private_import(self) -> None:
        # Arrange
        built = PACKAGE.Cpu(A_MODEL)

        # Act
        held = getattr(built, store_attribute())

        # Assert
        self.assertIn(type(held).__name__, PACKAGE.__all__)

    def test_and_so_is_everything_it_can_raise(self) -> None:
        # Arrange
        published = PACKAGE.__all__

        # Act
        public = public_exceptions()

        # Assert
        self.assertTrue(public, "the errors module defines no exception")
        self.assertEqual([name for name in public if name not in published], [])

    def test_nothing_is_promised_that_is_not_there(self) -> None:
        # Arrange
        promised = PACKAGE.__all__

        # Act
        absent = [name for name in promised if not hasattr(PACKAGE, name)]

        # Assert
        self.assertEqual(absent, [])


class OneDefinitionTest(unittest.TestCase):
    def modules(self) -> list[Any]:
        found = []
        for path in sorted(Path(PACKAGE.__file__ or "").resolve().parent.glob("*.py")):
            if path.name.endswith(".test.py") or path.name == "__init__.py":
                continue
            found.append(importlib.import_module(f"{PACKAGE.__name__}.{path.stem}"))
        return found

    def defined(self, package: Any = None) -> dict[str, list[str]]:
        held = self.modules() if package is None else [getattr(package, n) for n in dir(package)]
        found: dict[str, list[str]] = {}
        for module in held:
            if not isinstance(module, types.ModuleType):
                continue
            for one in vars(module).values():
                if not isinstance(one, type) or not issubclass(one, BaseException):
                    continue
                if one.__module__ != module.__name__:
                    continue
                found.setdefault(one.__qualname__, []).append(module.__name__)
        return {name: sorted(set(where)) for name, where in found.items()}

    def test_no_exception_name_is_defined_twice(self) -> None:
        # Arrange
        defined = self.defined()

        # Act
        twice = {name: where for name, where in defined.items() if len(where) > 1}

        # Assert
        self.assertEqual(twice, {})

    def test_every_exception_a_caller_can_meet_is_published(self) -> None:
        # Arrange
        defined = self.defined()

        # Act
        hidden = [
            name for name in defined if not name.startswith("_") and name not in PACKAGE.__all__
        ]

        # Assert
        self.assertEqual(hidden, [])

    def test_there_are_exceptions_to_check(self) -> None:
        # Arrange
        modules = self.modules()

        # Act
        defined = self.defined()

        # Assert
        self.assertGreater(len(modules), 0)
        self.assertGreater(len(defined), 0)

    def test_an_exception_imported_into_a_module_is_not_counted_as_defined_there(
        self,
    ) -> None:
        # Arrange
        home: Any = types.ModuleType("home")
        borrower: Any = types.ModuleType("borrower")
        held = type("Borrowed", (Exception,), {"__module__": "home"})
        home.Borrowed = held
        borrower.Borrowed = held
        package: Any = types.ModuleType("package")
        package.home = home
        package.borrower = borrower

        # Act
        found = self.defined(package)

        # Assert
        self.assertEqual(found, {"Borrowed": ["home"]})


RECORD = ROOT / "conformance" / "hardware.json"


def declared(node: Any) -> dict[str, Any]:
    found: dict[str, Any] = {}
    if isinstance(node, dict):
        held = node.get("documents")
        if isinstance(held, dict):
            found.update(held)
        for value in node.values():
            found.update(declared(value))
    elif isinstance(node, list):
        for one in node:
            found.update(declared(one))
    return found


def cited(node: Any, where: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(node, dict):
        named = node.get("document")
        if isinstance(named, str):
            found.append((where or ".", named))
        for name, value in node.items():
            found += cited(value, f"{where}.{name}")
    elif isinstance(node, list):
        for index, one in enumerate(node):
            found += cited(one, f"{where}[{index}]")
    return found


def quoted_sentences(node: Any) -> int:
    if isinstance(node, dict):
        held = sum(1 for key in node if "quote" in str(key).lower())
        return held + sum(quoted_sentences(one) for one in node.values())
    if isinstance(node, list):
        return sum(quoted_sentences(one) for one in node)
    return 0


QUOTED = quoted_sentences(json.loads(RECORD.read_text())) if RECORD.is_file() else 0


def astray_citations(held: Any) -> list[str]:
    keys = set(declared(held))
    return sorted({named for _, named in cited(held) if named not in keys})


def nameless_sources(held: Any) -> list[str]:
    return sorted(key for key, one in declared(held).items() if not one.get("file"))


class OneVocabularyForADocumentTest(unittest.TestCase):
    def record(self) -> Any:
        return json.loads(RECORD.read_text())

    def test_the_standard_asks_for_a_documents_block(self) -> None:
        # Arrange
        phrase = "`documents` block"

        # Act
        asked = phrase in FAMILY

        # Assert
        self.assertTrue(asked)

    def test_the_record_declares_its_sources_in_one(self) -> None:
        # Arrange
        record = self.record()

        # Act
        block = record.get("documents")

        # Assert
        self.assertIsInstance(block, dict)

    def test_every_source_declared_anywhere_names_the_file_it_is(self) -> None:
        # Arrange
        record = self.record()

        # Act
        nameless = nameless_sources(record)

        # Assert
        self.assertEqual(nameless, [])

    def test_every_citation_names_one_of_them(self) -> None:
        # Arrange
        record = self.record()

        # Act
        astray = astray_citations(record)

        # Assert
        self.assertEqual(astray, [])

    def test_there_is_a_record_to_check(self) -> None:
        # Arrange
        record = self.record()

        # Act
        fields = [key for key in record if key != "documents"]

        # Assert
        self.assertGreater(len(fields), 0)

    def test_the_reader_of_that_finds_a_citation_wherever_it_sits(self) -> None:
        # Arrange
        held = {
            "facts": {"pin": {"document": "sheet", "page": 6}},
            "parts": [{"timing": [{"document": "book"}]}],
            "note": "not a citation",
        }

        # Act
        found = sorted(cited(held))

        # Assert
        self.assertEqual(found, [(".facts.pin", "sheet"), (".parts[0].timing[0]", "book")])

    def test_and_finds_a_block_declared_beside_a_part(self) -> None:
        # Arrange
        held = {
            "documents": {"a": {"file": "a.pdf"}},
            "parts": [{"documents": {"b": {"file": "b.pdf"}}}],
        }

        # Act
        found = sorted(declared(held))

        # Assert
        self.assertEqual(found, ["a", "b"])

    def test_a_block_declared_beside_a_part_is_read_as_well_as_a_top_level_one(
        self,
    ) -> None:
        # Arrange
        held = {
            "documents": {},
            "parts": [
                {"documents": {"sheet": {"file": "a.pdf"}}},
                {"documents": {"book": {"file": "b.pdf"}}},
            ],
        }

        # Act
        found = sorted(declared(held))

        # Assert
        self.assertEqual(found, ["book", "sheet"])

    def test_a_source_reached_through_a_sibling_still_has_to_name_the_sibling(
        self,
    ) -> None:
        # Arrange
        held = {"documents": {"manual": {"file": "book1.pdf", "through": "snes-graphics-python"}}}

        # Act
        borrowed = {key: one["through"] for key, one in declared(held).items() if "through" in one}

        # Assert
        self.assertEqual(borrowed, {"manual": "snes-graphics-python"})

    def test_an_empty_block_is_a_declaration_and_not_a_missing_one(self) -> None:
        # Arrange
        held = {"documents": {}, "facts": {"pin": 1}}

        # Act
        found = (held.get("documents"), declared(held), cited(held))

        # Assert
        self.assertEqual(found, ({}, {}, []))

    def test_a_record_citing_a_key_that_is_not_declared_is_reported(self) -> None:
        # Arrange
        held = {"documents": {"sheet": {"file": "a.pdf"}}, "facts": {"document": "elsewhere"}}

        # Act
        astray = astray_citations(held)

        # Assert
        self.assertEqual(astray, ["elsewhere"])

    def test_and_a_source_with_no_file_beside_it_is_reported(self) -> None:
        # Arrange
        held = {"documents": {"sheet": {"title": "a manual with no file named"}}}

        # Act
        nameless = nameless_sources(held)

        # Assert
        self.assertEqual(nameless, ["sheet"])


class EveryModuleIsReachedTest(unittest.TestCase):
    def an_entry_point(self, path: Path) -> bool:
        return any(
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
            for node in ast.walk(ast.parse(path.read_text()))
        )

    def entry_points(self) -> set[str]:
        return {
            path.stem
            for path in Path(PACKAGE.__file__ or "").resolve().parent.glob("*.py")
            if not path.name.endswith(".test.py") and self.an_entry_point(path)
        }

    def modules(self) -> set[str]:
        return {
            path.stem
            for path in Path(PACKAGE.__file__ or "").resolve().parent.glob("*.py")
            if not path.name.endswith(".test.py") and path.stem != "__init__"
        }

    def imported(self, where: Path | None = None) -> set[str]:
        held = ROOT if where is None else where
        name = PACKAGE.__name__
        found: set[str] = set()
        for path in sorted(held.glob("**/*.py")):
            if "node_modules" in path.parts or path.name.endswith(".test.py"):
                continue
            try:
                tree = ast.parse(path.read_text())
            except SyntaxError:  # pragma: no cover
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if not (node.level or (node.module or "").split(".")[0] == name):
                        continue
                    if node.module:
                        found.add(node.module.rsplit(".", 1)[-1])
                    found.update(one.name for one in node.names)
                elif isinstance(node, ast.Import):
                    for one in node.names:
                        if one.name.split(".")[0] == name:
                            found.add(one.name.rsplit(".", 1)[-1])
        return found

    def a_tree_holding(self, name: str, text: str) -> Path:
        where = Path(tempfile.mkdtemp())
        (where / name).write_text(text)
        return where

    def test_every_module_in_the_package_is_reached_by_something(self) -> None:
        # Arrange
        published = set(PACKAGE.__all__) | {
            name for name in dir(PACKAGE) if isinstance(getattr(PACKAGE, name), types.ModuleType)
        }

        # Act
        stranded = sorted(self.modules() - published - self.imported() - self.entry_points())

        # Assert
        self.assertEqual(stranded, [])

    def test_the_doctor_is_reached_by_being_run_rather_than_imported(self) -> None:
        # Arrange
        name = "doctor"

        # Act
        points = self.entry_points()

        # Assert
        self.assertIn(name, points)

    def test_a_module_with_no_main_guard_is_not_an_entry_point(self) -> None:
        # Arrange
        where = self.a_tree_holding("quiet.py", "VALUE = 1\n") / "quiet.py"

        # Act
        found = self.an_entry_point(where)

        # Assert
        self.assertFalse(found)

    def test_the_reader_of_that_counts_a_module_a_sibling_imports(self) -> None:
        # Arrange
        where = self.a_tree_holding("one.py", f"from {PACKAGE.__name__} import held\n")

        # Act
        found = self.imported(where)

        # Assert
        self.assertIn("held", found)

    def test_and_one_reached_only_by_a_relative_import(self) -> None:
        # Arrange
        where = self.a_tree_holding("one.py", "from . import sibling\n")

        # Act
        found = self.imported(where)

        # Assert
        self.assertIn("sibling", found)

    def test_and_does_not_count_a_module_reached_only_by_its_own_test(self) -> None:
        # Arrange
        where = self.a_tree_holding("stranded.test.py", "from . import stranded\n")

        # Act
        found = self.imported(where)

        # Assert
        self.assertNotIn("stranded", found)

    def test_and_a_module_reached_by_its_full_dotted_name(self) -> None:
        # Arrange
        where = self.a_tree_holding("one.py", f"import {PACKAGE.__name__}.reached\n")

        # Act
        found = self.imported(where)

        # Assert
        self.assertIn("reached", found)

    def test_and_ignores_a_module_from_somewhere_else_entirely(self) -> None:
        # Arrange
        where = self.a_tree_holding("one.py", "from json import loads\n")

        # Act
        found = self.imported(where)

        # Assert
        self.assertNotIn("loads", found)


class EveryLinkResolvesTest(unittest.TestCase):
    LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

    def documents(self) -> list[Path]:
        held = subprocess.run(
            ["git", "ls-files", "*.md"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return [ROOT / one for one in held.stdout.split()]

    def tracked(self) -> set[str]:
        held = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        )
        found: set[str] = set()
        for one in held.stdout.split():
            found.add(one)
            for parent in PurePosixPath(one).parents:
                if str(parent) != ".":
                    found.add(str(parent))
        return found

    def targets(self, where: Path) -> list[str]:
        found = []
        for target in self.LINK.findall(where.read_text()):
            held = target.split("#", 1)[0].split(" ", 1)[0]
            if not held or "://" in held or held.startswith(("mailto:", "#")):
                continue
            found.append(held)
        return found

    def said_from_the_root(self, inside: PurePosixPath, target: str) -> str:
        return posixpath.normpath(str(inside / target)).rstrip("/")

    def unresolved(self, where: Path, known: set[str]) -> list[str]:
        inside = PurePosixPath(where.parent.relative_to(ROOT))
        return [
            f"{where.relative_to(ROOT)} -> {one}"
            for one in self.targets(where)
            if self.said_from_the_root(inside, one) not in known
        ]

    def a_page(self, text: str) -> Path:
        where = Path(tempfile.mkdtemp()) / "one.md"
        where.write_text(text)
        return where

    def test_every_markdown_file_here_is_checked(self) -> None:
        # Arrange
        expected = {"README.md", "AGENTS.md", "FAMILY.md"}

        # Act
        named = {one.name for one in self.documents()}

        # Assert
        self.assertTrue(expected <= named, named)

    def test_and_every_link_into_this_repository_resolves(self) -> None:
        # Arrange
        known = self.tracked()

        # Act
        missing = sorted(one for held in self.documents() for one in self.unresolved(held, known))

        # Assert
        self.assertEqual(missing, [])

    def test_a_link_to_something_the_repository_does_not_track_is_reported(self) -> None:
        # Arrange
        held = ROOT / "README.md"

        # Act
        unresolved = self.unresolved(held, set())

        # Assert
        self.assertEqual(len(unresolved), len(self.targets(held)))

    def test_a_link_to_something_it_does_track_is_not(self) -> None:
        # Arrange
        held = ROOT / "README.md"

        # Act
        unresolved = self.unresolved(held, self.tracked())

        # Assert
        self.assertEqual(unresolved, [])

    def test_a_link_out_of_a_subdirectory_resolves_to_what_it_names(self) -> None:
        # Arrange
        inside = PurePosixPath("cartridges")

        # Act
        held = self.said_from_the_root(inside, "../manifest.json")

        # Assert
        self.assertEqual(held, "manifest.json")

    def test_and_one_that_climbs_past_the_root_still_resolves_to_nothing(self) -> None:
        # Arrange
        inside = PurePosixPath(".")

        # Act
        held = self.said_from_the_root(inside, "../outside.json")

        # Assert
        self.assertEqual(held, "../outside.json")

    def test_an_anchor_is_dropped_before_the_file_is_looked_for(self) -> None:
        # Arrange
        where = self.a_page("see [a section](FAMILY.md#somewhere)\n")

        # Act
        found = self.targets(where)

        # Assert
        self.assertEqual(found, ["FAMILY.md"])

    def test_and_a_link_within_one_document_is_left_alone(self) -> None:
        # Arrange
        where = self.a_page("see [above](#somewhere)\n")

        # Act
        found = self.targets(where)

        # Assert
        self.assertEqual(found, [])

    def test_an_address_on_the_network_is_not_this_check_s_business(self) -> None:
        # Arrange
        where = self.a_page("see [a site](https://example.com/page)\n")

        # Act
        found = self.targets(where)

        # Assert
        self.assertEqual(found, [])

    def test_a_path_this_repository_ignores_does_not_count_as_resolved(self) -> None:
        # Arrange
        ignored = "docs/PROMPT.md"

        # Act
        known = self.tracked()

        # Assert
        self.assertNotIn(ignored, known)


class NothingOutsideTheStandardLibraryTest(unittest.TestCase):
    def declared_submodules(self, root: Path | None = None) -> set[str]:
        where = ROOT if root is None else root
        held = where / ".gitmodules"
        if not held.is_file():
            return set()
        found = set()
        for line in held.read_text().splitlines():
            if not line.strip().startswith("path = "):
                continue
            name = line.strip().removeprefix("path = ").strip()
            for path in sorted((where / name).glob("*/__init__.py")):
                found.add(path.parent.name)
        return found

    def imports(self, where: Path) -> set[str]:
        found: set[str] = set()
        for node in ast.walk(ast.parse(where.read_text())):
            if isinstance(node, ast.Import):
                found.update(one.name.split(".")[0] for one in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                found.add(node.module.split(".")[0])
        return found

    def a_file(self, text: str) -> Path:
        where = Path(tempfile.mkdtemp()) / "one.py"
        where.write_text(text)
        return where

    def test_the_package_imports_nothing_it_does_not_ship(self) -> None:
        # Arrange
        allowed = (
            set(sys.stdlib_module_names)
            | {PACKAGE.__name__, "conformance"}
            | self.declared_submodules()
        )

        # Act
        outside = sorted(
            f"{path.name}: {name}"
            for path in Path(PACKAGE.__file__ or "").resolve().parent.glob("*.py")
            if not path.name.endswith(".test.py")
            for name in self.imports(path)
            if name not in allowed
        )

        # Assert
        self.assertEqual(outside, [])

    def test_and_the_readme_says_so(self) -> None:
        # Arrange
        readme = (ROOT / "README.md").read_text()

        # Act
        said = "no dependencies" in readme

        # Assert
        self.assertTrue(said)

    def test_a_submodule_is_allowed_because_it_is_carried_rather_than_fetched(
        self,
    ) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp())
        (where / ".gitmodules").write_text(
            '[submodule "sibling-python"]\n\tpath = sibling-python\n'
            "\turl = https://example.invalid/sibling.git\n"
        )
        (where / "sibling-python" / "sibling").mkdir(parents=True)
        (where / "sibling-python" / "sibling" / "__init__.py").write_text("")

        # Act
        found = self.declared_submodules(where)

        # Assert
        self.assertEqual(found, {"sibling"})

    def test_and_a_repository_with_none_declares_none(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp())

        # Act
        found = self.declared_submodules(where)

        # Assert
        self.assertEqual(found, set())

    def test_the_reader_of_that_sees_an_import_from_outside(self) -> None:
        # Arrange
        where = self.a_file("import json\nimport numpy\nfrom yaml import safe_load\n")

        # Act
        held = self.imports(where)

        # Assert
        self.assertEqual(sorted(held - set(sys.stdlib_module_names)), ["numpy", "yaml"])

    def test_and_reads_a_relative_import_as_the_package_itself(self) -> None:
        # Arrange
        where = self.a_file("from . import sibling\nfrom .errors import Refused\n")

        # Act
        found = self.imports(where)

        # Assert
        self.assertEqual(found, set())


class EveryQuoteIsCheckableTest(unittest.TestCase):
    @unittest.skipUnless(QUOTED, "this record quotes nothing")
    def test_a_record_that_quotes_ships_a_checker_for_it(self) -> None:
        # Arrange
        checker = ROOT / "conformance" / "quotes.py"

        # Act
        shipped = checker.is_file()

        # Assert
        self.assertTrue(shipped)

    @unittest.skipUnless(QUOTED, "this record quotes nothing")
    def test_and_the_pipeline_runs_it(self) -> None:
        # Arrange
        held = (ROOT / ".github" / "workflows" / "ci.yml").read_text()

        # Act
        run = "conformance.quotes" in held

        # Assert
        self.assertTrue(run)

    def test_the_reader_of_that_counts_a_quote_however_its_key_is_spelled(self) -> None:
        # Arrange
        record = {"a": {"quote": "x"}, "b": {"countRangeQuote": "y"}}

        # Act
        counted = quoted_sentences(record)

        # Assert
        self.assertEqual(counted, 2)

    def test_and_counts_none_in_a_record_that_quotes_nothing(self) -> None:
        # Arrange
        record = {"facts": {"window": [1, 2]}, "note": "a chip"}

        # Act
        counted = quoted_sentences(record)

        # Assert
        self.assertEqual(counted, 0)


class EveryRecordStatesItsAuthorityTest(unittest.TestCase):
    def record(self) -> Any:
        return json.loads(RECORD.read_text())

    def authority(self) -> Any:
        held = self.record().get("authority")
        return held if isinstance(held, dict) else {}

    def compared_against(self) -> dict[str, Any]:
        held = self.authority().get("comparedAgainst")
        assert isinstance(held, dict)
        return held

    def test_the_record_states_the_order_it_answers_in(self) -> None:
        # Arrange
        authority = self.authority()

        # Act
        order = authority.get("order")

        # Assert
        self.assertTrue(order)

    def test_and_the_order_is_a_list_of_rungs_rather_than_a_sentence(self) -> None:
        # Arrange
        authority = self.authority()

        # Act
        order = authority.get("order")

        # Assert
        self.assertIsInstance(order, list)

    def test_and_says_why_it_is_that_order(self) -> None:
        # Arrange
        authority = self.authority()

        # Act
        why = str(authority.get("why", "")).strip()

        # Assert
        self.assertTrue(why)

    def test_the_record_names_what_this_member_is_held_to(self) -> None:
        # Arrange
        held = self.compared_against()

        # Act
        what = str(held.get("what", "")).strip()

        # Assert
        self.assertTrue(what)

    def test_and_the_runner_that_does_the_comparing_is_here(self) -> None:
        # Arrange
        held = self.compared_against()

        # Act
        present = (ROOT / str(held.get("runner"))).is_file()

        # Assert
        self.assertTrue(present, held.get("runner"))

    def test_the_standard_carries_the_ladder_this_is_measured_against(self) -> None:
        # Arrange
        heading = "The authority ladder"

        # Act
        carried = heading in FAMILY

        # Assert
        self.assertTrue(carried)

    def test_a_record_with_no_ladder_at_all_is_reported(self) -> None:
        # Arrange
        held = {"note": "layouts, pinned to the figures", "documents": {}}

        # Act
        found = held.get("authority")

        # Assert
        self.assertIsNone(found)


class SharedFileTest(unittest.TestCase):
    NAMED = re.compile(r"^\| `([^`]+)` \|", re.M)

    FILE = re.compile(r"[./]")

    def promised(self) -> list[str]:
        return [row for row in self.NAMED.findall(FAMILY) if self.FILE.search(row)]

    def test_the_standard_names_every_file_this_repository_must_carry(self) -> None:
        # Arrange
        promised = self.promised()

        # Act
        missing = [row for row in promised if not (ROOT / row).exists()]

        # Assert
        self.assertEqual(missing, [])

    def test_and_there_is_something_to_check(self) -> None:
        # Arrange
        smallest = 6

        # Act
        promised = self.promised()

        # Assert
        self.assertGreater(len(promised), smallest)

    def test_a_file_named_with_no_directory_in_it_is_still_required(self) -> None:
        # Arrange
        citation = "CITATION.cff"

        # Act
        promised = self.promised()

        # Assert
        self.assertIn(citation, promised)


def accounts_for_a_reset(node: Any) -> bool:  # pragma: no cover
    if isinstance(node, dict):
        if any("reset" in str(key).lower() for key in node):
            return True
        return any(accounts_for_a_reset(one) for one in node.values())
    if isinstance(node, list):
        return any(accounts_for_a_reset(one) for one in node)
    return "reset" in str(node).lower()


def catalogue(package: Any = None) -> dict[str, Any]:
    held = PACKAGE if package is None else package
    for name in sorted(getattr(held, "__all__", ())):
        found = getattr(held, name, None)
        if not isinstance(found, dict) or not found:
            continue
        if all(hasattr(one, "name") and hasattr(one, "aliases") for one in found.values()):
            return dict(found)
    return {}


VARIANTS: dict[str, Any] = catalogue()


def built(name: str, readme: str) -> bool:  # pragma: no cover
    return re.search(rf"""\w\(\s*["']{re.escape(name)}["']""", readme) is not None


@unittest.skipUnless(VARIANTS, "this package names no variants")  # pragma: no cover
class DocumentedModelTest(unittest.TestCase):
    def test_every_model_has_a_worked_construction(self) -> None:
        # Arrange
        readme = (ROOT / "README.md").read_text()

        # Act
        undocumented = [name for name in VARIANTS if not built(name, readme)]

        # Assert
        self.assertEqual(undocumented, [])

    def test_and_every_alias_is_named_beside_it(self) -> None:
        # Arrange
        readme = (ROOT / "README.md").read_text()

        # Act
        unnamed = [
            alias for model in VARIANTS.values() for alias in model.aliases if alias not in readme
        ]

        # Assert
        self.assertEqual(unnamed, [])

    def test_the_reader_of_that_tells_a_call_from_a_mention(self) -> None:
        # Arrange
        lines = ('Chip("a-part")', "Cpu('a-part')", "the a-part is covered here", "`a-part`")

        # Act
        found = [built("a-part", line) for line in lines]

        # Assert
        self.assertEqual(found, [True, True, False, False])


class CatalogueReaderTest(unittest.TestCase):
    def package(self, **published: Any) -> Any:
        held: Any = types.ModuleType("published")
        held.__all__ = sorted(published)
        for name, one in published.items():
            setattr(held, name, one)
        return held

    def variant(self, name: str) -> Any:
        return type("Variant", (), {"name": name, "aliases": ()})()

    def test_it_finds_a_catalogue_whatever_the_package_calls_it(self) -> None:
        # Arrange
        held = self.package(FORMATS={"4bpp": self.variant("4bpp")})

        # Act
        found = sorted(catalogue(held))

        # Assert
        self.assertEqual(found, ["4bpp"])

    def test_and_finds_it_under_any_other_name(self) -> None:
        # Arrange
        held = self.package(MODELS={"z80": self.variant("z80")})

        # Act
        found = sorted(catalogue(held))

        # Assert
        self.assertEqual(found, ["z80"])

    def test_it_steps_over_a_published_name_that_is_not_a_mapping(self) -> None:
        # Arrange
        held = self.package(LIMIT=3, MODELS={"z80": self.variant("z80")})

        # Act
        found = sorted(catalogue(held))

        # Assert
        self.assertEqual(found, ["z80"])

    def test_and_over_a_mapping_with_nothing_in_it(self) -> None:
        # Arrange
        held = self.package(EMPTY={}, MODELS={"z80": self.variant("z80")})

        # Act
        found = sorted(catalogue(held))

        # Assert
        self.assertEqual(found, ["z80"])

    def test_and_over_a_mapping_whose_entries_are_not_variants(self) -> None:
        # Arrange
        held = self.package(SIZES={"small": 8, "large": 64})

        # Act
        found = catalogue(held)

        # Assert
        self.assertEqual(found, {})

    def test_a_package_publishing_no_catalogue_answers_with_nothing(self) -> None:
        # Arrange
        held = self.package(decode=len)

        # Act
        found = catalogue(held)

        # Assert
        self.assertEqual(found, {})

    def test_and_so_does_one_publishing_nothing_at_all(self) -> None:
        # Arrange
        held = types.ModuleType("bare")

        # Act
        found = catalogue(held)

        # Assert
        self.assertEqual(found, {})


def counted_tests() -> int:
    return sum(
        len(re.findall(r"^\s+def test_", found.read_text(), re.M))
        for directory in TESTED_DIRECTORIES
        for found in sorted((ROOT / directory).glob("**/*.test.py"))
    )


class ClaimedCountTest(unittest.TestCase):
    def test_the_readme_advertises_the_number_of_tests_there_are(self) -> None:
        # Arrange
        readme = (ROOT / "README.md").read_text()

        # Act
        claimed = re.search(r"\*\*([\d,]+)\*\* tests", readme)

        # Assert
        assert claimed is not None
        self.assertEqual(int(claimed.group(1).replace(",", "")), counted_tests())


def as_a_script(text: str) -> list[int]:
    return [
        number
        for number, line in enumerate(text.splitlines(), start=1)
        if re.search(r"python3? conformance/[a-z_]+\.py", line)
    ]


class StandardIsKeptTest(unittest.TestCase):
    def test_the_standard_names_the_errors_module_as_the_one_home(self) -> None:
        # Arrange
        name = "errors.py"

        # Act
        named = name in FAMILY

        # Assert
        self.assertTrue(named)

    def test_and_this_repository_has_one(self) -> None:
        # Arrange
        package = Path(PACKAGE.__file__ or "").resolve().parent

        # Act
        present = (package / "errors.py").exists()

        # Assert
        self.assertTrue(present)

    def test_the_standard_says_a_tool_runs_as_a_module(self) -> None:
        # Arrange
        phrase = "python3 -m conformance.name"

        # Act
        said = phrase in FAMILY

        # Assert
        self.assertTrue(said)

    def test_and_no_workflow_runs_one_as_a_script(self) -> None:
        # Arrange
        workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))

        # Act
        astray = [
            f"{path.name}:{number}"
            for path in workflows
            for number in as_a_script(path.read_text())
        ]

        # Assert
        self.assertEqual(astray, [])

    def test_and_no_document_tells_a_reader_to(self) -> None:
        # Arrange
        names = ("README.md", "AGENTS.md", "CONTRIBUTING.md")

        # Act
        astray = [
            name
            for name in names
            if (ROOT / name).exists() and as_a_script((ROOT / name).read_text())
        ]

        # Assert
        self.assertEqual(astray, [])

    def test_the_reader_of_those_two_finds_a_script_invocation(self) -> None:
        # Arrange
        texts = (
            "run: python conformance/speed.py\n",
            "run: python3 -m conformance.speed\n",
            "a\nb\npython conformance/links.py\n",
        )

        # Act
        found = [as_a_script(text) for text in texts]

        # Assert
        self.assertEqual(found, [[1], [], [3]])

    def test_the_standard_promises_a_throughput_floor(self) -> None:
        # Arrange
        phrase = "throughput floor"

        # Act
        promised = phrase in FAMILY

        # Assert
        self.assertTrue(promised)

    def test_and_this_repository_has_one_with_a_floor_to_beat(self) -> None:
        # Arrange
        speed = importlib.import_module("conformance.speed")

        # Act
        floor = speed.FLOOR

        # Assert
        self.assertGreater(floor, 0)

    def test_and_it_is_this_repository_s_floor(self) -> None:
        # Arrange
        speed = importlib.import_module("conformance.speed")

        # Act
        held = Path(speed.__file__ or "").resolve()

        # Assert
        self.assertEqual(held, ROOT / "conformance" / "speed.py", held)

    def test_the_floor_is_checked_outside_the_coverage_step(self) -> None:
        # Arrange
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()

        # Act
        found = (
            "python -m conformance.speed" in workflow,
            "coverage run -a conformance/speed.py" in workflow,
        )

        # Assert
        self.assertEqual(found, (True, False))


@unittest.skipUnless(CLOCKED, "not a clocked part")  # pragma: no cover
class SuppliedMemoryTest(unittest.TestCase):
    def test_a_supplied_store_is_the_one_the_part_uses(self) -> None:
        # Arrange
        where = store_attribute()
        own = getattr(PACKAGE.Cpu(A_MODEL), where)

        # Act
        built = PACKAGE.Cpu(A_MODEL, own)

        # Assert
        self.assertIs(getattr(built, where), own)

    def test_and_one_is_built_when_the_argument_is_left_out(self) -> None:
        # Arrange
        model = A_MODEL

        # Act
        built = PACKAGE.Cpu(model)

        # Assert
        self.assertIsNotNone(getattr(built, store_attribute()))

    def test_the_standard_names_this_part_spelling(self) -> None:
        # Arrange
        spelling = f"cpu.{store_attribute()}"

        # Act
        named = spelling in FAMILY

        # Assert
        self.assertTrue(named)


def still_holding(classes: Any) -> list[str]:
    return [
        one.__qualname__
        for one in classes
        if any("__dict__" in vars(base) for base in one.__mro__[:-1])
    ]


class NoStrayAttributeTest(unittest.TestCase):
    def published(self) -> list[type]:
        found = []
        for name in dir(PACKAGE):
            held = getattr(PACKAGE, name)
            if (
                isinstance(held, type)
                and not issubclass(held, BaseException)
                and held.__module__.startswith(PACKAGE.__name__)
            ):
                found.append(held)
            elif isinstance(held, types.ModuleType) and held.__name__.startswith(PACKAGE.__name__):
                for attr, one in vars(held).items():
                    if attr.startswith("_"):
                        continue
                    if (
                        isinstance(one, type)
                        and one.__module__ == held.__name__
                        and not issubclass(one, BaseException)
                        and not getattr(one, "_is_protocol", False)
                    ):
                        found.append(one)
        return sorted(set(found), key=lambda one: one.__qualname__)

    def test_every_published_class_declares_what_it_holds(self) -> None:
        # Arrange
        published = self.published()

        # Act
        loose = [
            f"{one.__module__.split('.')[-1]}.{one.__qualname__}"
            for one in published
            if "__slots__" not in vars(one)
        ]

        # Assert
        self.assertEqual(loose, [])

    def test_and_none_of_them_kept_a_dict_anyway(self) -> None:
        # Arrange
        published = self.published()

        # Act
        holding = still_holding(published)

        # Assert
        self.assertEqual(holding, [])

    def test_and_one_that_did_would_be_named(self) -> None:
        # Arrange
        class Loose:
            pass

        class Slotted(Loose):
            __slots__ = ()

        # Act
        found = still_holding([Slotted])

        # Assert
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].endswith("Slotted"), found[0])

    def test_there_are_classes_to_check(self) -> None:
        # Arrange
        smallest = 0

        # Act
        published = self.published()

        # Assert
        self.assertGreater(len(published), smallest)


SECTIONS = (
    "Install",
    "The interface",
    "Is it right",
    "Working on it",
    "References",
    "Citing this",
    "License",
)

CLOCKED_SECTIONS = (
    "Running it at a real speed",
    "Models",
    "Nothing starts clean",
)

DIRECTIVE = ("noqa", "type:", "pragma", "ruff:", "mypy:", "isort:", "fmt:")

TEST_MARKERS = ("Arrange", "Act", "Assert")


def prose_comments(where: Path) -> list[str]:
    found = []
    for path in sorted(where.glob("**/*.py")):
        with path.open("rb") as opened:
            for token in tokenize.tokenize(opened.readline):
                if token.type != tokenize.COMMENT:
                    continue
                body = token.string.lstrip("#").strip()
                if body and not body.startswith(DIRECTIVE) and body not in TEST_MARKERS:
                    found.append(f"{path.name}:{token.start[0]}")
    return found


CONFIGURATION = ("pyproject.toml", "setup.cfg", ".gitignore")


def configuration_comments(where: Path) -> list[str]:
    found = []
    for name in CONFIGURATION:
        path = where / name
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if line.lstrip().startswith("#"):
                found.append(f"{name}:{number}")
    return found


def mute_names(where: Path) -> list[str]:
    found = []
    for path in sorted(where.glob("**/*.test.py")):
        for name in re.findall(r"^    def test_(\w+)", path.read_text(), re.M):
            if len(name.split("_")) < 2:
                found.append(f"{path.name}:test_{name}")
    return found


def a_folder_holding(name: str, text: str) -> Path:
    where = Path(tempfile.mkdtemp())
    (where / name).write_text(text)
    return where


TRANSLATIONS = ("README.ja.md", "README.zh-Hans.md", "README.zh-HK.md")

READMES = ("README.md", *TRANSLATIONS)

FENCE = re.compile(r"^```.*?^```$", re.M | re.S)

LINK = re.compile(r"\]\(([^)\s]+)\)")

UNDER_TAGLINE = re.compile(r"^# .+\n\n(?:.+\n)+\n(.+)$", re.M)


def fenced(text: str) -> list[str]:
    return FENCE.findall(text)


def heading_levels(text: str) -> list[int]:
    return [len(marks) for marks in re.findall(r"^(#{1,6}) ", FENCE.sub("", text), re.M)]


def switcher(text: str) -> str:
    found = UNDER_TAGLINE.search(FENCE.sub("", text))
    return found.group(1) if found else ""


def body_links(text: str) -> list[str]:
    unfenced = FENCE.sub("", text)
    return sorted(LINK.findall(unfenced.replace(switcher(text), "", 1)))


def switcher_gaps(name: str, text: str) -> list[str]:
    linked = set(LINK.findall(switcher(text)))
    others = [one for one in READMES if one != name]
    return [one for one in others if one not in linked] + [name] * (name in linked)


class TranslatedTest(unittest.TestCase):
    def english(self) -> str:
        return (ROOT / "README.md").read_text()

    def translated(self) -> dict[str, str]:
        return {name: (ROOT / name).read_text() for name in TRANSLATIONS if (ROOT / name).is_file()}

    def test_every_translation_is_there(self) -> None:
        # Arrange
        expected = list(TRANSLATIONS)

        # Act
        held = sorted(self.translated())

        # Assert
        self.assertEqual(held, sorted(expected))

    def test_every_readme_links_the_other_three_under_its_tagline(self) -> None:
        # Arrange
        held = {"README.md": self.english(), **self.translated()}

        # Act
        gaps = {name: switcher_gaps(name, text) for name, text in held.items()}

        # Assert
        self.assertEqual({name: gap for name, gap in gaps.items() if gap}, {})

    def test_every_translation_keeps_the_english_headings_level_by_level(self) -> None:
        # Arrange
        expected = heading_levels(self.english())

        # Act
        held = {name: heading_levels(text) for name, text in self.translated().items()}

        # Assert
        self.assertEqual({name: levels for name, levels in held.items() if levels != expected}, {})

    def test_every_translation_carries_the_english_code_byte_for_byte(self) -> None:
        # Arrange
        expected = fenced(self.english())

        # Act
        held = {name: fenced(text) for name, text in self.translated().items()}

        # Assert
        self.assertEqual([name for name, code in held.items() if code != expected], [])

    def test_every_translation_links_where_the_english_links(self) -> None:
        # Arrange
        expected = body_links(self.english())

        # Act
        held = {name: body_links(text) for name, text in self.translated().items()}

        # Assert
        self.assertEqual([name for name, links in held.items() if links != expected], [])

    def test_a_heading_inside_a_code_block_is_not_counted(self) -> None:
        # Arrange
        text = "# Title\n\n```bash\n# not a heading\n```\n\n## Part\n"

        # Act
        levels = heading_levels(text)

        # Assert
        self.assertEqual(levels, [1, 2])

    def test_a_switcher_that_links_to_itself_is_reported(self) -> None:
        # Arrange
        text = "# Title\n\nWhat it is.\n\n[English](README.md) | [日本語](README.ja.md) | 简体中文 | [HK](README.zh-HK.md)\n"

        # Act
        gaps = switcher_gaps("README.ja.md", text)

        # Assert
        self.assertEqual(gaps, ["README.zh-Hans.md", "README.ja.md"])

    def test_a_switcher_above_the_title_is_reported_missing(self) -> None:
        # Arrange
        text = "[日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | [HK](README.zh-HK.md)\n\n# Title\n\nWhat it is.\n\nBody.\n"

        # Act
        gaps = switcher_gaps("README.md", text)

        # Assert
        self.assertEqual(gaps, ["README.ja.md", "README.zh-Hans.md", "README.zh-HK.md"])

    def test_a_readme_with_no_title_carries_no_switcher(self) -> None:
        # Arrange
        text = "[日本語](README.ja.md)\n\nBody.\n"

        # Act
        found = switcher(text)

        # Assert
        self.assertEqual(found, "")

    def test_the_switcher_line_is_not_compared_as_a_body_link(self) -> None:
        # Arrange
        text = "# Title\n\nWhat it is.\n\n[日本語](README.ja.md)\n\nSee [LICENSE](LICENSE).\n"

        # Act
        links = body_links(text)

        # Assert
        self.assertEqual(links, ["LICENSE"])


ANCHOR = re.compile(r'<a id="([^"]+)"></a>')


def slug(title: str) -> str:
    lowered = re.sub(r"[`*_\[\]()]", "", title).strip().lower()
    return re.sub(r"[^\w\- ]", "", lowered).replace(" ", "-")


def landings(text: str) -> set[str]:
    unfenced = FENCE.sub("", text)
    titled = {slug(title) for title in re.findall(r"^#{1,6} (.+)$", unfenced, re.M)}
    return titled | set(ANCHOR.findall(unfenced))


def in_page_links(text: str) -> set[str]:
    return set(re.findall(r"\]\(#([^)\s]+)\)", FENCE.sub("", text)))


class InPageLinkTest(unittest.TestCase):
    def test_every_in_page_link_in_every_readme_lands(self) -> None:
        # Arrange
        held = {name: (ROOT / name).read_text() for name in READMES if (ROOT / name).is_file()}

        # Act
        stray = {name: sorted(in_page_links(text) - landings(text)) for name, text in held.items()}

        # Assert
        self.assertEqual({name: links for name, links in stray.items() if links}, {})

    def test_a_translated_heading_lands_through_an_anchor(self) -> None:
        # Arrange
        text = '<a id="models"></a>\n\n## モデル\n\nSee [the models](#models).\n'

        # Act
        stray = in_page_links(text) - landings(text)

        # Assert
        self.assertEqual(stray, set())


class WrittenTheSameWayTest(unittest.TestCase):
    def readme(self) -> str:
        return (ROOT / "README.md").read_text()

    def headings(self) -> list[str]:
        return re.findall(r"^## (.+)$", self.readme(), re.M)

    def opening(self) -> str:
        return self.readme().split("## ")[0]

    def tool(self) -> Any:
        return tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]

    def test_the_readme_carries_the_sections_the_family_carries(self) -> None:
        # Arrange
        headings = self.headings()

        # Act
        missing = [one for one in SECTIONS if one not in headings]

        # Assert
        self.assertEqual(missing, [])

    def test_and_in_the_order_the_family_carries_them(self) -> None:
        # Arrange
        headings = self.headings()

        # Act
        held = [one for one in headings if one in SECTIONS]

        # Assert
        self.assertEqual(held, list(SECTIONS))

    @unittest.skipUnless(CLOCKED, "not a clocked part")  # pragma: no cover
    def test_a_clocked_part_also_carries_the_three_a_clock_needs(self) -> None:
        # Arrange
        headings = self.headings()

        # Act
        missing = [one for one in CLOCKED_SECTIONS if one not in headings]

        # Assert
        self.assertEqual(missing, [])

    @unittest.skipUnless(CLOCKED, "not a clocked part")  # pragma: no cover
    def test_and_a_section_on_driving_it_a_cycle_at_a_time(self) -> None:
        # Arrange
        headings = self.headings()

        # Act
        found = any(one.startswith("Driving it one") for one in headings)

        # Assert
        self.assertTrue(found)

    @unittest.skipUnless(CLOCKED, "not a clocked part")  # pragma: no cover
    def test_and_one_on_reading_a_program_without_running_it(self) -> None:
        # Arrange
        heading = "Reading without running"

        # Act
        headings = self.headings()

        # Assert
        self.assertIn(heading, headings)

    def test_anything_it_adds_sits_between_the_interface_and_the_evidence(self) -> None:
        # Arrange
        held = self.headings()
        added = [one for one in held if one not in SECTIONS and one not in CLOCKED_SECTIONS]
        interface = held.index("The interface")
        evidence = held.index("Is it right")

        # Act
        stray = [one for one in added if not interface < held.index(one) < evidence]

        # Assert
        self.assertEqual(stray, [])

    def test_the_readme_opens_with_what_was_measured(self) -> None:
        # Arrange
        held = self.opening()

        # Act
        found = re.search(r"^\*\*[0-9,]+\*\* [a-z]", held, re.M)

        # Assert
        self.assertTrue(found, held[:400])

    def test_and_says_how_much_of_it_failed(self) -> None:
        # Arrange
        held = self.opening()

        # Act
        found = re.search(r"\*\*0\*\* (?:\w+ )?(?:failures|disagreements)", held)

        # Assert
        self.assertTrue(found, held[:400])

    def test_and_what_it_costs_to_install(self) -> None:
        # Arrange
        held = self.opening()

        # Act
        said = "no dependencies" in held

        # Assert
        self.assertTrue(said)

    def test_no_source_file_carries_a_comment_a_tool_does_not_read(self) -> None:
        # Arrange
        package = Path(PACKAGE.__file__ or "").resolve().parent

        # Act
        found = prose_comments(package)

        # Assert
        self.assertEqual(found, [])

    def test_a_bare_test_marker_is_not_prose(self) -> None:
        # Arrange
        where = a_folder_holding("sample.py", "# Arrange\nx = 1\n# Act now\n# Assert\n")

        # Act
        found = prose_comments(where)

        # Assert
        self.assertEqual(found, ["sample.py:3"])

    def test_nor_does_any_conformance_file(self) -> None:
        # Arrange
        where = ROOT / "conformance"

        # Act
        found = prose_comments(where)

        # Assert
        self.assertEqual(found, [])

    def test_no_configuration_file_carries_a_comment(self) -> None:
        # Arrange
        where = ROOT

        # Act
        found = configuration_comments(where)

        # Assert
        self.assertEqual(found, [])

    def test_the_reader_of_configuration_finds_a_comment_line(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp())
        (where / "pyproject.toml").write_text('[tool.x]\n# why\nname = "a#b"\n')

        # Act
        found = configuration_comments(where)

        # Assert
        self.assertEqual(found, ["pyproject.toml:2"])

    def test_the_reader_of_that_tells_a_directive_from_prose(self) -> None:
        # Arrange
        where = a_folder_holding(
            "sample.py",
            "# ruff: noqa: E501\n"
            "# noqa: E743 -- the register really is called l\n"
            "x = 1  # type: ignore[assignment]\n"
            "#\n"
            "# the accumulator is eight bits wide\n"
            "def f() -> None:\n"
            '    """One worked line, with the answer beside it.\n'
            "\n"
            "        resolve(address).region\n"
            "        # 'work-ram', not cartridge\n"
            '    """\n',
        )

        # Act
        found = prose_comments(where)

        # Assert
        self.assertEqual(found, ["sample.py:5"])

    def test_and_the_reader_of_names_tells_a_sentence_from_a_function(self) -> None:
        # Arrange
        where = a_folder_holding(
            "sample.test.py",
            "class T:\n"
            "    def test_step(self) -> None:\n"
            "        pass\n"
            "\n"
            "    def test_a_step_costs_what_the_sheet_says(self) -> None:\n"
            "        pass\n",
        )

        # Act
        found = mute_names(where)

        # Assert
        self.assertEqual(found, ["sample.test.py:test_step"])

    def test_every_test_is_named_as_a_sentence_about_behaviour(self) -> None:
        # Arrange
        where = ROOT

        # Act
        found = mute_names(where)

        # Assert
        self.assertEqual(found, [])

    def test_the_checker_is_strict_everywhere_the_family_is(self) -> None:
        # Arrange
        held = self.tool()

        # Act
        found = (
            held["mypy"]["strict"],
            held["coverage"]["report"]["fail_under"],
            held["ruff"]["line-length"],
        )

        # Assert
        self.assertEqual(found, (True, 100, 100))

    def test_a_protocol_stub_is_excluded_from_the_count_both_ways(self) -> None:
        # Arrange
        patterns = self.tool()["coverage"]["report"].get("exclude_also", [])

        # Act
        inline = [one for one in patterns if re.search(one, "    def step(self) -> int: ...")]
        alone = [one for one in patterns if re.search(one, "        ...")]

        # Assert
        self.assertTrue(inline, patterns)
        self.assertTrue(alone, patterns)

    def test_and_a_pattern_that_matches_neither_would_be_reported(self) -> None:
        # Arrange
        doubled = r"^\\s*\\.\\.\\.$"

        # Act
        found = re.search(doubled, "        ...")

        # Assert
        self.assertIsNone(found)


MACHINES: dict[str, tuple[str, ...]] = {}


NOT_THIS_PACKAGES_WORDS = ("conformance/family.test.py", "FAMILY.md")


def unquoted(text: str, suffix: str) -> str:
    if suffix != ".json":
        return text
    try:
        record = json.loads(text)
    except json.JSONDecodeError:
        return text
    blanked = text
    for passage in _passages(record):
        if len(passage) > 8:
            blanked = blanked.replace(
                json.dumps(passage)[1:-1], " " * len(json.dumps(passage)[1:-1])
            )
    return blanked


def _passages(node: Any) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key.endswith(("quote", "Quote")) and isinstance(value, str):
                found.append(value)
            elif key.endswith(("quotes", "Quotes")) and isinstance(value, list):
                found.extend(one for one in value if isinstance(one, str))
            elif key.endswith(("quotes", "Quotes")) and isinstance(value, dict):
                found.extend(one for one in value.values() if isinstance(one, str))
            else:
                found.extend(_passages(value))
    elif isinstance(node, list):
        for one in node:
            found.extend(_passages(one))
    return found


def machine_mentions(
    where: Path, names: tuple[str, ...], run: Any = None
) -> list[str]:  # pragma: no cover
    runner = subprocess.run if run is None else run
    listed = runner(
        ["git", "ls-files"], cwd=where, capture_output=True, text=True, check=False
    ).stdout.split()
    found = []
    for rel in listed:
        if rel in NOT_THIS_PACKAGES_WORDS:
            continue
        path = where / rel
        if path.suffix in {".png", ".jpg", ".ico", ".pdf"} or not path.is_file():
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        searched = unquoted(text, path.suffix)
        for name in names:
            for hit in re.finditer(rf"(?<![\w-]){re.escape(name)}(?![\w-])", searched):
                found.append(f"{rel}:{text[: hit.start()].count(chr(10)) + 1} names {name}")
    return found


def imported_by(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.add("." * node.level + (node.module or ""))
    return found


def reaching_inside(names: Iterable[str], package: str) -> list[str]:
    return sorted(
        name
        for name in names
        if name.startswith(".") or name == package or name.startswith(package + ".")
    )


class ErrorsCloseNoCycleTest(unittest.TestCase):
    def errors(self) -> Path:
        return Path(PACKAGE.__file__ or "").resolve().parent / "errors.py"

    def test_it_imports_nothing_from_this_package(self) -> None:
        # Arrange
        held = imported_by(self.errors())

        # Act
        inside = reaching_inside(held, PACKAGE.__name__)

        # Assert
        self.assertEqual(inside, [])

    def test_the_reader_of_that_tells_the_package_from_the_standard_library(self) -> None:
        # Arrange
        held = {"__future__", "re", "typing", PACKAGE.__name__, f"{PACKAGE.__name__}.core", "."}

        # Act
        inside = reaching_inside(held, PACKAGE.__name__)

        # Assert
        self.assertEqual(inside, [".", PACKAGE.__name__, f"{PACKAGE.__name__}.core"])

    def test_and_a_package_whose_name_merely_starts_the_same_is_not_inside(self) -> None:
        # Arrange
        held = {f"{PACKAGE.__name__}asm", f"{PACKAGE.__name__}_tools"}

        # Act
        inside = reaching_inside(held, PACKAGE.__name__)

        # Assert
        self.assertEqual(inside, [])

    def test_the_reader_of_that_sees_the_imports_that_are_there(self) -> None:
        # Arrange
        where = a_folder_holding(
            "sample.py", "from __future__ import annotations\nimport re\nfrom . import core\n"
        )

        # Act
        found = imported_by(where / "sample.py")

        # Assert
        self.assertEqual(found, {"__future__", "re", "."})

    def test_and_would_name_one_reaching_back_into_the_package(self) -> None:
        # Arrange
        where = a_folder_holding("sample.py", f"from {PACKAGE.__name__}.core import Cpu\n")

        # Act
        found = imported_by(where / "sample.py")

        # Assert
        self.assertIn(f"{PACKAGE.__name__}.core", found)


DOCUMENT_SUFFIXES = frozenset({".pdf", ".djvu", ".epub", ".rom", ".bin", ".img"})


def unignored(where: Path, run: Any = None) -> list[str]:
    runner = subprocess.run if run is None else run
    done = runner(
        ["git", "-c", "core.excludesFile=/dev/null", "status", "--porcelain", "-uall"],
        cwd=where,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise RuntimeError(
            f"git could not read the tree: {done.stderr.strip() or 'no reason given'}"
        )
    return sorted(line[3:] for line in done.stdout.splitlines() if line.startswith("??"))


AGENTS_SECTIONS = (
    "What this project is, in one paragraph",
    "The interface a caller drives",
    "The authority ladder",
    "What is settled and what is not",
    "Every gate, in the order to run them",
    "Conventions that are not negotiable",
    "Layout",
    "Things that will bite you",
    "Before calling anything finished",
    "What a change is expected to leave behind",
)


SETTLED_SECTIONS = ("What is not in question", "What is deliberately not modelled")


def open_questions(where: Path | None = None) -> list[str]:
    held = ((ROOT if where is None else where) / "OPEN-QUESTIONS.md").read_text()
    found: list[str] = []
    section = ""
    for line in held.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        elif line.startswith("### ") and section not in SETTLED_SECTIONS:
            found.append(line[4:].strip())
    return found


class BriefedTheSameWayTest(unittest.TestCase):
    def agents(self) -> str:
        return (ROOT / "AGENTS.md").read_text()

    def held(self) -> list[str]:
        return re.findall(r"^## (.+)$", self.agents(), re.M)

    def test_it_carries_the_sections_the_family_carries(self) -> None:
        # Arrange
        held = self.held()

        # Act
        missing = [one for one in AGENTS_SECTIONS if one not in held]

        # Assert
        self.assertEqual(missing, [])

    def test_and_in_the_order_the_family_carries_them(self) -> None:
        # Arrange
        held = self.held()

        # Act
        kept = [one for one in held if one in AGENTS_SECTIONS]

        # Assert
        self.assertEqual(kept, list(AGENTS_SECTIONS))

    def test_anything_it_adds_of_its_own_sits_in_one_place(self) -> None:
        # Arrange
        held = self.held()
        gates = held.index("Every gate, in the order to run them")
        settled = held.index("What is settled and what is not")

        # Act
        added = [one for one in held if one not in AGENTS_SECTIONS]

        # Assert
        self.assertTrue(all(settled < held.index(one) < gates for one in added), added)

    def test_the_count_of_open_questions_is_the_count_there_is(self) -> None:
        # Arrange
        listed = open_questions()

        # Act
        claimed = re.search(r"\*\*Not settled: (\d+) things\*\*", self.agents())

        # Assert
        assert claimed is not None
        self.assertEqual(int(claimed.group(1)), len(listed))

    def test_and_counts_questions_rather_than_headings(self) -> None:
        # Arrange
        held = (ROOT / "OPEN-QUESTIONS.md").read_text()

        # Act
        listed = open_questions()

        # Assert
        self.assertLessEqual(len(listed), len(re.findall(r"^### ", held, re.M)))


class PublishesNamesNotModulesTest(unittest.TestCase):
    def test_no_module_is_published_as_a_name(self) -> None:
        # Arrange
        names = PACKAGE.__all__

        # Act
        published = sorted(
            name for name in names if isinstance(getattr(PACKAGE, name, None), types.ModuleType)
        )

        # Assert
        self.assertEqual(published, [])

    def test_a_module_is_still_reachable_without_being_published(self) -> None:
        # Arrange
        name = "errors"

        # Act
        found = (hasattr(PACKAGE, name), name in PACKAGE.__all__)

        # Assert
        self.assertEqual(found, (True, False))

    def test_there_are_names_published(self) -> None:
        # Arrange
        smallest = 0

        # Act
        published = len(PACKAGE.__all__)

        # Assert
        self.assertGreater(published, smallest)


def tracked_files() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return listed.stdout.split()


def saying(text: str) -> Any:
    def run(*_: Any, **__: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 0, stdout=text, stderr="")

    return run


def refusing(code: int, said: str) -> Any:
    def run(*_: Any, **__: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], code, stdout="", stderr=said)

    return run


class CarriesNobodyElsesWorkTest(unittest.TestCase):
    def test_no_document_is_committed(self) -> None:
        # Arrange
        tracked = tracked_files()

        # Act
        carried = sorted(rel for rel in tracked if Path(rel).suffix.lower() in DOCUMENT_SUFFIXES)

        # Assert
        self.assertEqual(carried, [])

    def test_nor_is_anything_from_the_folder_they_live_in(self) -> None:
        # Arrange
        tracked = tracked_files()

        # Act
        carried = [rel for rel in tracked if rel.startswith("docs/")]

        # Assert
        self.assertEqual(carried, [])

    def test_there_are_tracked_files_to_look_through(self) -> None:
        # Arrange
        smallest = 20

        # Act
        tracked = tracked_files()

        # Assert
        self.assertGreater(len(tracked), smallest)

    def test_the_ignore_file_here_covers_everything_on_its_own(self) -> None:
        # Arrange
        where = ROOT

        # Act
        found = unignored(where)

        # Assert
        self.assertEqual(found, [])

    def test_the_reader_of_that_names_an_untracked_file(self) -> None:
        # Arrange
        run = saying("?? left/behind.txt\n M edited.py\n")

        # Act
        found = unignored(ROOT, run)

        # Assert
        self.assertEqual(found, ["left/behind.txt"])

    def test_and_steps_over_one_that_is_merely_edited(self) -> None:
        # Arrange
        run = saying(" M edited.py\nA  added.py\n")

        # Act
        found = unignored(ROOT, run)

        # Assert
        self.assertEqual(found, [])

    def test_a_run_that_failed_is_not_read_as_a_clean_tree(self) -> None:
        # Arrange
        run = refusing(128, "not a repository")

        # Act
        attempt = lambda: unignored(ROOT, run)  # noqa: E731

        # Assert
        self.assertRaisesRegex(RuntimeError, "not a repository", attempt)

    def test_and_a_failure_with_nothing_to_say_still_raises(self) -> None:
        # Arrange
        run = refusing(1, "")

        # Act
        attempt = lambda: unignored(ROOT, run)  # noqa: E731

        # Assert
        self.assertRaises(RuntimeError, attempt)


class QuotedPassageTest(unittest.TestCase):
    def test_a_quote_is_blanked_and_the_line_numbers_survive(self) -> None:
        # Arrange
        held = '{"quote": "the SNES is named here", "note": "and here too"}'

        # Act
        found = unquoted(held, ".json")

        # Assert
        self.assertEqual(len(found), len(held))
        self.assertNotIn("SNES", found[: found.index("note")])
        self.assertIn("and here too", found)

    def test_a_plural_key_holding_a_list_is_blanked_as_well(self) -> None:
        # Arrange
        held = '{"aboutQuotes": ["the SNES is named here", "and so it is here"]}'

        # Act
        found = unquoted(held, ".json")

        # Assert
        self.assertNotIn("SNES", found)

    def test_and_one_holding_a_map_of_numbered_notes(self) -> None:
        # Arrange
        held = '{"noteQuotes": {"1": "the SNES is named here"}}'

        # Act
        found = unquoted(held, ".json")

        # Assert
        self.assertNotIn("SNES", found)

    def test_a_short_passage_is_left_alone(self) -> None:
        # Arrange
        held = '{"quote": "SNES", "note": "SNES"}'

        # Act
        found = unquoted(held, ".json")

        # Assert
        self.assertEqual(found, held)

    def test_a_file_that_is_not_a_record_is_read_as_it_stands(self) -> None:
        # Arrange
        held = "the SNES is named here"

        # Act
        found = unquoted(held, ".md")

        # Assert
        self.assertEqual(found, held)

    def test_and_so_is_one_that_claims_to_be_and_is_not(self) -> None:
        # Arrange
        held = "{this is not json at all, and it names the SNES"

        # Act
        found = unquoted(held, ".json")

        # Assert
        self.assertEqual(found, held)

    def test_a_value_that_is_not_a_passage_is_stepped_over(self) -> None:
        # Arrange
        held = '{"quote": 5, "quotes": [1, 2], "noteQuotes": {"1": 3}, "cycles": [1]}'

        # Act
        found = _passages(json.loads(held))

        # Assert
        self.assertEqual(found, [])


def listing(*names: str) -> Any:  # pragma: no cover
    def run(*_: Any, **__: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 0, stdout="\n".join(names), stderr="")

    return run


@unittest.skipUnless(
    SOLD_AS_A_COMPONENT, "this part only existed inside one machine"
)  # pragma: no cover
class NamesNoMachineTest(unittest.TestCase):
    def names(self) -> tuple[str, ...]:
        return MACHINES[PACKAGE.__name__ if PACKAGE.__name__ in MACHINES else ROOT.name]

    def test_no_tracked_file_names_one(self) -> None:
        # Arrange
        names = self.names()

        # Act
        found = machine_mentions(ROOT, names)

        # Assert
        self.assertEqual(found, [])

    def test_the_sweep_would_report_one_if_it_were_there(self) -> None:
        # Arrange
        names = ("README",)

        # Act
        found = machine_mentions(ROOT, names)

        # Assert
        self.assertNotEqual(found, [])

    def test_a_name_inside_a_longer_word_is_not_a_mention(self) -> None:
        # Arrange
        folder = a_folder_holding("a.md", "SNESLIKE and pre-SNES-era are not mentions\n")

        # Act
        found = machine_mentions(folder, ("SNES",), listing("a.md"))

        # Assert
        self.assertEqual(found, [])

    def test_but_the_bare_name_is(self) -> None:
        # Arrange
        folder = a_folder_holding("a.md", "first\nthis one names the SNES outright\n")

        # Act
        found = machine_mentions(folder, ("SNES",), listing("a.md"))

        # Assert
        self.assertEqual(found, ["a.md:2 names SNES"])

    def test_a_file_that_is_not_text_is_stepped_over(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        (folder / "a.bin").write_bytes(b"\xff\xfe\x00SNES")

        # Act
        found = machine_mentions(folder, ("SNES",), listing("a.bin"))

        # Assert
        self.assertEqual(found, [])

    def test_and_so_is_one_git_lists_that_is_not_on_disk(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())

        # Act
        found = machine_mentions(folder, ("SNES",), listing("gone.md"))

        # Assert
        self.assertEqual(found, [])


DIVERGENCES = ROOT / "conformance" / "divergences.json"

DIVERGENCE_STATUS = (
    "open",
    "narrowed",
    "acknowledged",
    "closed",
    "notADisagreement",
    "notModelled",
)

DIVERGENCE_SEVERITY = (
    "contradiction",
    "high",
    "medium",
    "low",
    "unstated",
    "unchecked",
    "outOfScope",
)

DIVERGENCE_SOURCES = (
    "document",
    "reference",
    "recording",
    "corpus",
    "cartridges",
    "microcode",
    "neither",
)


def divergence_entries(where: Path) -> list[Any]:
    if not where.is_file():
        return []
    held = json.loads(where.read_text())
    for value in held.values():
        if isinstance(value, list):
            return list(value)
    return []


def outside_vocabulary(entries: Any, field: str, allowed: Any) -> list[str]:
    return sorted({str(one.get(field)) for one in entries if one.get(field) not in allowed})


class DivergenceRecordTest(unittest.TestCase):
    @property
    def entries(self) -> Any:
        return divergence_entries(DIVERGENCES)

    def test_there_is_a_record_to_check(self) -> None:
        # Arrange
        where = DIVERGENCES

        # Act
        entries = divergence_entries(where)

        # Assert
        self.assertTrue(entries)

    def test_every_entry_says_where_it_stands(self) -> None:
        # Arrange
        entries = self.entries

        # Act
        found = outside_vocabulary(entries, "status", DIVERGENCE_STATUS)

        # Assert
        self.assertEqual(found, [])

    def test_every_entry_says_how_much_it_costs(self) -> None:
        # Arrange
        entries = self.entries

        # Act
        found = outside_vocabulary(entries, "severity", DIVERGENCE_SEVERITY)

        # Assert
        self.assertEqual(found, [])

    def test_every_entry_says_what_this_package_followed(self) -> None:
        # Arrange
        entries = self.entries

        # Act
        found = outside_vocabulary(entries, "packageFollows", DIVERGENCE_SOURCES)

        # Assert
        self.assertEqual(found, [])

    def test_a_value_nobody_agreed_on_is_caught(self) -> None:
        # Arrange
        entries = [{"status": "mostly open"}]

        # Act
        found = outside_vocabulary(entries, "status", DIVERGENCE_STATUS)

        # Assert
        self.assertEqual(found, ["mostly open"])

    def test_a_field_left_out_entirely_is_caught(self) -> None:
        # Arrange
        entries: list[dict[str, Any]] = [{}]

        # Act
        found = outside_vocabulary(entries, "severity", DIVERGENCE_SEVERITY)

        # Assert
        self.assertEqual(found, ["None"])

    def test_a_record_that_is_not_here_reads_as_empty(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "divergences.json"

        # Act
        found = divergence_entries(where)

        # Assert
        self.assertEqual(found, [])

    def test_a_record_with_no_list_in_it_reads_as_empty(self) -> None:
        # Arrange
        where = a_folder_holding("divergences.json", '{"note": "nothing here yet"}')

        # Act
        found = divergence_entries(where / "divergences.json")

        # Assert
        self.assertEqual(found, [])


def stamped_paths(script: Path) -> list[str]:
    if not script.is_file():
        return []
    return sorted(set(re.findall(r"\$\{root\}/([^\"'\s]+)", script.read_text())))


def released_assets(config: Path) -> list[str]:
    if not config.is_file():
        return []
    document = json.loads(config.read_text())
    for plugin in document.get("plugins", []):
        if isinstance(plugin, list) and plugin and plugin[0] == "@semantic-release/git":
            return [str(asset) for asset in plugin[1].get("assets", [])]
    return []


def unreleased(stamped: Iterable[str], released: Iterable[str]) -> list[str]:
    committed = set(released)
    return [path for path in stamped if path not in committed]


class EveryStampedFileIsReleasedTest(unittest.TestCase):
    SCRIPT = "scripts/set-version.sh"

    CONFIG = ".releaserc.json"

    def test_the_release_commits_every_file_the_script_stamps(self) -> None:
        # Arrange
        stamped = stamped_paths(ROOT / self.SCRIPT)
        released = released_assets(ROOT / self.CONFIG)

        # Act
        left_out = unreleased(stamped, released)

        # Assert
        self.assertEqual(left_out, [])

    def test_and_there_is_something_to_check(self) -> None:
        # Arrange
        script = ROOT / self.SCRIPT

        # Act
        stamped = stamped_paths(script)

        # Assert
        self.assertGreaterEqual(len(stamped), 2)

    def test_a_path_the_release_leaves_out_is_reported(self) -> None:
        # Arrange
        stamped = ["pkg/version.py", "CITATION.cff"]

        # Act
        found = unreleased(stamped, ["pkg/version.py"])

        # Assert
        self.assertEqual(found, ["CITATION.cff"])

    def test_a_script_that_is_not_here_stamps_nothing(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "set-version.sh"

        # Act
        found = stamped_paths(where)

        # Assert
        self.assertEqual(found, [])

    def test_a_script_that_names_no_target_stamps_nothing(self) -> None:
        # Arrange
        where = a_folder_holding(
            "set-version.sh", "#!/usr/bin/env bash\nprintf 'nothing to do\\n'\n"
        )

        # Act
        found = stamped_paths(where / "set-version.sh")

        # Assert
        self.assertEqual(found, [])

    def test_a_release_config_that_is_not_here_releases_nothing(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / ".releaserc.json"

        # Act
        found = released_assets(where)

        # Assert
        self.assertEqual(found, [])

    def test_a_config_with_no_git_plugin_releases_nothing(self) -> None:
        # Arrange
        where = a_folder_holding(
            ".releaserc.json", '{"plugins": ["@semantic-release/github", [], ["@other", {}]]}'
        )

        # Act
        found = released_assets(where / ".releaserc.json")

        # Assert
        self.assertEqual(found, [])

    def test_a_git_plugin_naming_no_asset_releases_nothing(self) -> None:
        # Arrange
        where = a_folder_holding(".releaserc.json", '{"plugins": [["@semantic-release/git", {}]]}')

        # Act
        found = released_assets(where / ".releaserc.json")

        # Assert
        self.assertEqual(found, [])


def recorded_version(module: Path) -> str | None:
    if not module.is_file():
        return None
    found = re.search(r'^VERSION = "([^"]*)"$', module.read_text(), re.M)
    return found.group(1) if found else None


def cited_version(citation: Path) -> str | None:
    if not citation.is_file():
        return None
    found = re.search(r"^version: (.*)$", citation.read_text(), re.M)
    return found.group(1).strip() if found else None


class TheVersionAndTheCitationAgreeTest(unittest.TestCase):
    def stamped(self) -> list[str]:
        return stamped_paths(ROOT / "scripts" / "set-version.sh")

    def module(self) -> Path:
        named = [one for one in self.stamped() if one.endswith("version.py")]
        return ROOT / named[0] if named else ROOT / "version.py"

    def test_the_script_stamps_exactly_one_version_module(self) -> None:
        # Arrange
        stamped = self.stamped()

        # Act
        named = [one for one in stamped if one.endswith("version.py")]

        # Assert
        self.assertEqual(len(named), 1, named)

    def test_the_package_reports_a_version(self) -> None:
        # Arrange
        module = self.module()

        # Act
        found = recorded_version(module)

        # Assert
        self.assertIsNotNone(found)

    def test_the_citation_publishes_a_version(self) -> None:
        # Arrange
        citation = ROOT / "CITATION.cff"

        # Act
        found = cited_version(citation)

        # Assert
        self.assertIsNotNone(found)

    def test_the_two_say_the_same_thing(self) -> None:
        # Arrange
        module = self.module()

        # Act
        found = (recorded_version(module), cited_version(ROOT / "CITATION.cff"))

        # Assert
        self.assertEqual(found[0], found[1])

    def test_a_module_that_is_not_here_reports_no_version(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "version.py"

        # Act
        found = recorded_version(where)

        # Assert
        self.assertIsNone(found)

    def test_a_module_with_no_assignment_reports_no_version(self) -> None:
        # Arrange
        where = a_folder_holding("version.py", "RELEASE = '1.2.3'\n")

        # Act
        found = recorded_version(where / "version.py")

        # Assert
        self.assertIsNone(found)

    def test_a_citation_that_is_not_here_publishes_no_version(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "CITATION.cff"

        # Act
        found = cited_version(where)

        # Assert
        self.assertIsNone(found)

    def test_a_citation_with_no_version_line_publishes_none(self) -> None:
        # Arrange
        where = a_folder_holding("CITATION.cff", "cff-version: 1.2.0\ntitle: something\n")

        # Act
        found = cited_version(where / "CITATION.cff")

        # Assert
        self.assertIsNone(found)


DOCUMENTED = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def is_bare_string(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def documents_its_holder(body: list[ast.stmt], index: int) -> bool:
    opens_the_body = index == 0
    follows_an_assignment = index > 0 and isinstance(body[index - 1], (ast.Assign, ast.AnnAssign))
    return is_bare_string(body[index]) and (opens_the_body or follows_an_assignment)


def documentation_strings(text: str) -> list[int]:
    holders = [node for node in ast.walk(ast.parse(text)) if isinstance(node, DOCUMENTED)]
    return sorted(
        holder.body[index].lineno
        for holder in holders
        for index in range(len(holder.body))
        if documents_its_holder(holder.body, index)
    )


def tracked_python_files() -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    return [ROOT / one for one in listed]


class NoDocumentationStringTest(unittest.TestCase):
    def test_no_tracked_file_carries_a_documentation_string(self) -> None:
        # Arrange
        files = tracked_python_files()

        # Act
        found = [
            f"{path.relative_to(ROOT)}:{line}"
            for path in files
            for line in documentation_strings(path.read_text())
        ]

        # Assert
        self.assertEqual(found, [])

    def test_and_there_are_files_to_check(self) -> None:
        # Arrange
        minimum = 5

        # Act
        files = tracked_python_files()

        # Assert
        self.assertGreater(len(files), minimum)

    def test_a_module_class_and_function_string_are_each_found(self) -> None:
        # Arrange
        text = '"""M."""\n\n\nclass A:\n    """C."""\n\n\ndef f() -> None:\n    """F."""\n'

        # Act
        found = documentation_strings(text)

        # Assert
        self.assertEqual(found, [1, 5, 9])

    def test_a_string_after_an_assignment_is_found(self) -> None:
        # Arrange
        text = 'LIMIT = 3\n"""What the limit is."""\n'

        # Act
        found = documentation_strings(text)

        # Assert
        self.assertEqual(found, [2])

    def test_a_string_used_as_a_value_is_not_one(self) -> None:
        # Arrange
        text = 'NAME = "a value"\nprint("a call")\n'

        # Act
        found = documentation_strings(text)

        # Assert
        self.assertEqual(found, [])


HELD_BY = "heldBy"

UNREACHABLE = "unreachable"

SUPPORTING = "alsoSays"

NOT_PRINTED = frozenset({"notStated", "documents"})

Fact = tuple[tuple[str, ...], dict[str, Any]]


def is_a_sentence(value: Any) -> bool:
    return isinstance(value, str) or (
        isinstance(value, list) and any(isinstance(one, str) for one in value)
    )


def quotes_a_sentence(entry: dict[str, Any]) -> bool:
    return any(
        str(key).lower().endswith(("quote", "quotes")) and is_a_sentence(value)
        for key, value in entry.items()
    )


def printed_facts(node: Any, path: tuple[str, ...] = ()) -> list[Fact]:
    if NOT_PRINTED & set(path) or (path and path[-1] == SUPPORTING):
        return []
    if isinstance(node, list):
        return [fact for one in node for fact in printed_facts(one, path)]
    if not isinstance(node, dict):
        return []
    own: list[Fact] = [(path, node)] if quotes_a_sentence(node) else []
    return own + [
        fact for key, value in node.items() for fact in printed_facts(value, (*path, str(key)))
    ]


def named_test(source: str, dotted: str) -> str | None:
    owner, _, method = dotted.rpartition(".")
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.ClassDef) and node.name == owner):
            continue
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == method:
                return ast.get_source_segment(source, item) or ""
    return None


def holding_problem(root: Path, held: str, name: str | None) -> str | None:
    file, _, dotted = held.partition("::")
    path = root / file
    if not path.is_file():
        return f"{held} names a file that is not there"
    body = named_test(path.read_text(), dotted)
    if body is None:
        return f"{held} names a test that is not there"
    if name is not None and f'"{name}"' not in body and f"'{name}'" not in body:
        return f"{held} never reads {name} from the record"
    return None


def unheld(record: Any, root: Path) -> list[str]:
    problems = []
    for path, entry in printed_facts(record):
        where = "/".join(path) or "the record itself"
        reason = entry.get(UNREACHABLE)
        if isinstance(reason, str) and reason.strip():
            continue
        held = entry.get(HELD_BY)
        if not isinstance(held, list) or not held:
            problems.append(f"{where}: held by no test and not marked unreachable")
            continue
        name = path[-1] if path else None
        problems.extend(
            f"{where}: {problem}"
            for one in held
            if (problem := holding_problem(root, str(one), name)) is not None
        )
    return problems


A_HOLDING_TEST = (
    "class RecordTest:\n"
    "    def test_the_counter_has_the_printed_width(self):\n"
    '        printed = value("toneCounter")\n'
)


def a_folder_with_a_test(source: str = A_HOLDING_TEST) -> Path:
    folder = Path(tempfile.mkdtemp())
    (folder / "held.test.py").write_text(source)
    return folder


def a_printed_fact(**fields: Any) -> dict[str, Any]:
    return {"facts": {"toneCounter": {"value": 10, "quote": "a 10 stage counter", **fields}}}


HELD = ["held.test.py::RecordTest.test_the_counter_has_the_printed_width"]


class EveryPrintedFactIsHeldTest(unittest.TestCase):
    @unittest.skipUnless(RECORD.is_file(), "this repository keeps no record")
    def test_every_fact_the_manufacturer_printed_is_held_by_a_test_or_unreachable(self) -> None:
        # Arrange
        record = json.loads(RECORD.read_text())

        # Act
        problems = unheld(record, ROOT)

        # Assert
        self.assertEqual(problems, [])

    def test_a_fact_held_by_a_test_that_reads_it_passes(self) -> None:
        # Arrange
        record = a_printed_fact(heldBy=HELD)

        # Act
        problems = unheld(record, a_folder_with_a_test())

        # Assert
        self.assertEqual(problems, [])

    def test_a_fact_held_by_nothing_is_reported(self) -> None:
        # Arrange
        record = a_printed_fact()

        # Act
        problems = unheld(record, a_folder_with_a_test())

        # Assert
        self.assertEqual(
            problems, ["facts/toneCounter: held by no test and not marked unreachable"]
        )

    def test_a_fact_with_an_empty_reason_is_still_reported(self) -> None:
        # Arrange
        record = a_printed_fact(unreachable="  ")

        # Act
        problems = unheld(record, a_folder_with_a_test())

        # Assert
        self.assertEqual(
            problems, ["facts/toneCounter: held by no test and not marked unreachable"]
        )

    def test_a_fact_no_test_can_reach_passes_when_it_says_why(self) -> None:
        # Arrange
        record = a_printed_fact(unreachable="an electrical level on a pin the model does not have")

        # Act
        problems = unheld(record, a_folder_with_a_test())

        # Assert
        self.assertEqual(problems, [])

    def test_a_test_file_that_is_not_there_is_reported(self) -> None:
        # Arrange
        record = a_printed_fact(heldBy=["gone.test.py::RecordTest.test_x"])

        # Act
        problems = unheld(record, a_folder_with_a_test())

        # Assert
        self.assertEqual(
            problems,
            ["facts/toneCounter: gone.test.py::RecordTest.test_x names a file that is not there"],
        )

    def test_a_test_that_is_not_there_is_reported(self) -> None:
        # Arrange
        gone = "held.test.py::RecordTest.test_gone"

        # Act
        problems = unheld(a_printed_fact(heldBy=[gone]), a_folder_with_a_test())

        # Assert
        self.assertEqual(problems, [f"facts/toneCounter: {gone} names a test that is not there"])

    def test_a_method_of_another_class_is_not_the_named_test(self) -> None:
        # Arrange
        record = a_printed_fact(
            heldBy=["held.test.py::OtherTest.test_the_counter_has_the_printed_width"]
        )

        # Act
        problems = unheld(record, a_folder_with_a_test())

        # Assert
        self.assertEqual(len(problems), 1)

    def test_a_test_that_never_reads_the_fact_is_reported(self) -> None:
        # Arrange
        source = (
            "class RecordTest:\n"
            "    def test_the_counter_has_the_printed_width(self):\n"
            "        printed = 10\n"
        )

        # Act
        problems = unheld(a_printed_fact(heldBy=HELD), a_folder_with_a_test(source))

        # Assert
        self.assertEqual(
            problems, [f"facts/toneCounter: {HELD[0]} never reads toneCounter from the record"]
        )

    def test_a_test_that_reads_the_fact_in_single_quotes_passes(self) -> None:
        # Arrange
        source = A_HOLDING_TEST.replace('"toneCounter"', "'toneCounter'")

        # Act
        problems = unheld(a_printed_fact(heldBy=HELD), a_folder_with_a_test(source))

        # Assert
        self.assertEqual(problems, [])

    def test_a_fact_quoting_several_sentences_is_a_printed_fact(self) -> None:
        # Arrange
        record = {"facts": {"tableBases": {"quotes": ["the first", "the second"]}}}

        # Act
        found = [path for path, _ in printed_facts(record)]

        # Assert
        self.assertEqual(found, [("facts", "tableBases")])

    def test_a_list_holding_no_sentence_is_not_a_quote(self) -> None:
        # Arrange
        record = {"facts": {"x": {"quotes": [3]}, "y": {"quotes": []}}}

        # Act
        found = printed_facts(record)

        # Assert
        self.assertEqual(found, [])

    def test_a_quote_kept_outside_the_printed_facts_needs_no_test(self) -> None:
        # Arrange
        record = {
            "notStated": {"x": {"quote": "a"}},
            "documents": [{"quote": "b"}],
            "facts": {"y": {"value": 1}},
        }

        # Act
        found = printed_facts(record)

        # Assert
        self.assertEqual(found, [])

    def test_a_supporting_quote_belongs_to_the_fact_it_supports(self) -> None:
        # Arrange
        record = a_printed_fact(heldBy=HELD, alsoSays=[{"quote": "and again on page 3"}])

        # Act
        found = [path for path, _ in printed_facts(record)]

        # Assert
        self.assertEqual(found, [("facts", "toneCounter")])

    def test_a_fact_inside_a_list_is_named_by_the_list_it_sits_in(self) -> None:
        # Arrange
        record = {"fields": [{"quote": "bit 7 selects", "value": 7}, 3]}

        # Act
        found = [path for path, _ in printed_facts(record)]

        # Assert
        self.assertEqual(found, [("fields",)])

    def test_a_quote_on_the_record_itself_needs_only_a_test_that_exists(self) -> None:
        # Arrange
        source = (
            "class RecordTest:\n"
            "    def test_the_counter_has_the_printed_width(self):\n"
            "        pass\n"
        )

        # Act
        problems = unheld({"quote": "the part", "heldBy": HELD}, a_folder_with_a_test(source))

        # Assert
        self.assertEqual(problems, [])


def is_private(name: str) -> bool:
    return name.startswith("_") and not name.startswith("__")


def project_modules(tree: ast.Module, package: str) -> set[str]:
    roots = {package, "conformance"}
    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in roots:
            bound.update(alias.asname or alias.name for alias in node.names)
        if isinstance(node, ast.Import):
            bound.update(
                alias.asname or alias.name.split(".")[0]
                for alias in node.names
                if alias.name.split(".")[0] in roots
            )
    return bound


def import_problems(node: ast.AST, package: str, exported: set[str], tools: set[str]) -> list[str]:
    if isinstance(node, ast.Import):
        return [
            f"imports {alias.name}"
            for alias in node.names
            if alias.name.startswith(f"{package}.") and alias.name.split(".")[1] not in tools
        ]
    if not isinstance(node, ast.ImportFrom) or node.module is None:
        return []
    if node.module.startswith(f"{package}."):
        return [] if node.module.split(".")[1] in tools else [f"imports from {node.module}"]
    if node.module == package:
        allowed = exported | tools
        return [
            f"imports {alias.name} from {package}"
            for alias in node.names
            if alias.name not in allowed
        ]
    return []


LOADERS = frozenset(
    {"import_module", "spec_from_file_location", "SourceFileLoader", "run_path", "run_module"}
)


def loaded_inner(text: str, package: str) -> str | None:
    if text.startswith(f"{package}."):
        return text.split(".")[1]
    if f"{package}/" in text:
        return text.split(f"{package}/", 1)[1].split("/", maxsplit=1)[0].removesuffix(".py")
    return None


def load_problems(node: ast.AST, package: str, tools: set[str]) -> list[str]:
    if not isinstance(node, ast.Call):
        return []
    called = (
        node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
    )
    if called not in LOADERS:
        return []
    pieces = sorted(
        (one.lineno, one.col_offset, one.value)
        for argument in node.args
        for one in ast.walk(argument)
        if isinstance(one, ast.Constant) and isinstance(one.value, str)
    )
    words = [value for _, _, value in pieces]
    candidates = [*words, "/".join(words)]
    return sorted(
        {
            f"loads {inner} from {package}"
            for text in candidates
            if (inner := loaded_inner(text, package)) and inner not in tools | {"__init__"}
        }
    )


def reaches_inside(source: str, package: str, exported: set[str], tools: set[str]) -> list[str]:
    tree = ast.parse(source)
    roots = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name == package
    }
    modules = project_modules(tree, package)
    found: list[str] = []
    for node in ast.walk(tree):
        found.extend(import_problems(node, package, exported, tools))
        found.extend(load_problems(node, package, tools))
        if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)):
            continue
        owner, name = node.value.id, node.attr
        if owner in roots and name not in exported | tools and not name.startswith("__"):
            found.append(f"reaches {package}.{name}")
        elif owner in modules and is_private(name):
            found.append(f"reaches {owner}.{name}")
    return found


def realiased_modules(init_source: str) -> set[str]:
    return {
        alias.name
        for node in ast.walk(ast.parse(init_source))
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module is None
        for alias in node.names
        if alias.asname == alias.name
    }


def documented_modules(init_source: str, readme: str, package: str) -> set[str]:
    return {
        name
        for name in realiased_modules(init_source)
        if re.search(rf"\b{package}[./]{name}\b(?!\.test)", readme)
        or re.search(rf"from {package} import [^\n]*\b{name}\b", readme)
    }


def public_names() -> set[str]:
    init_source = (ROOT / PACKAGE.__name__ / "__init__.py").read_text()
    readme = (ROOT / "README.md").read_text()
    return set(PACKAGE.__all__) | documented_modules(init_source, readme, PACKAGE.__name__)


def repository_test_files() -> list[Path]:
    listed = subprocess.run(
        ["git", "-c", "submodule.recurse=false", "ls-files", "*.test.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split()
    homes = {PACKAGE.__name__, "conformance"}
    return [ROOT / one for one in listed if Path(one).parts[0] in homes]


class EveryTestUsesThePublicInterfaceTest(unittest.TestCase):
    def test_no_test_reaches_past_what_the_package_exports(self) -> None:
        # Arrange
        exported = public_names()

        # Act
        found = {
            str(path.relative_to(ROOT)): problems
            for path in repository_test_files()
            if (
                problems := reaches_inside(
                    path.read_text(), PACKAGE.__name__, exported, TOOL_MODULES
                )
            )
        }

        # Assert
        self.assertEqual(found, {})

    def test_there_are_package_tests_to_look_at(self) -> None:
        # Arrange
        package = PACKAGE.__name__

        # Act
        found = [path for path in repository_test_files() if path.parts[-2] == package]

        # Assert
        self.assertGreater(len(found), 0)

    def test_an_exported_name_passes(self) -> None:
        # Arrange
        source = "import part\n\nchip = part.Chip('a')\nnames = part.__all__\n"

        # Act
        found = reaches_inside(source, "part", {"Chip"}, set())

        # Assert
        self.assertEqual(found, [])

    def test_a_name_the_package_does_not_export_is_reported(self) -> None:
        # Arrange
        source = "import part as p\n\nwidth = p.tone\n"

        # Act
        found = reaches_inside(source, "part", {"Chip"}, set())

        # Assert
        self.assertEqual(found, ["reaches part.tone"])

    def test_importing_an_inner_module_is_reported(self) -> None:
        # Arrange
        source = "import part.tone\nfrom part.noise import shifted\nfrom part import tone, Chip\n"

        # Act
        found = reaches_inside(source, "part", {"Chip"}, set())

        # Assert
        self.assertEqual(
            found, ["imports part.tone", "imports from part.noise", "imports tone from part"]
        )

    def test_a_tool_module_may_be_imported_and_driven(self) -> None:
        # Arrange
        source = "import part.doctor\nfrom part.doctor import main\nfrom part import doctor\n"

        # Act
        found = reaches_inside(source, "part", {"Chip"}, {"doctor"})

        # Assert
        self.assertEqual(found, [])

    def test_a_private_name_of_any_project_module_is_reported(self) -> None:
        # Arrange
        source = (
            "from conformance import census\nfrom part import doctor\n\n"
            "census._tally\ndoctor._load\n"
        )

        # Act
        found = reaches_inside(source, "part", {"Chip"}, {"doctor"})

        # Assert
        self.assertEqual(found, ["reaches census._tally", "reaches doctor._load"])

    def test_a_private_name_of_something_else_is_left_alone(self) -> None:
        # Arrange
        source = "import json\n\nhandle = json._default_decoder\n"

        # Act
        found = reaches_inside(source, "part", {"Chip"}, set())

        # Assert
        self.assertEqual(found, [])

    def test_a_relative_import_is_left_to_the_other_checks(self) -> None:
        # Arrange
        source = "from . import helper\n"

        # Act
        found = reaches_inside(source, "part", {"Chip"}, set())

        # Assert
        self.assertEqual(found, [])

    def test_loading_an_inner_module_by_name_is_reported(self) -> None:
        # Arrange
        source = "import importlib\n\ntone = importlib.import_module('part.tone')\n"

        # Act
        found = reaches_inside(source, "part", {"Chip"}, set())

        # Assert
        self.assertEqual(found, ["loads tone from part"])

    def test_loading_an_inner_module_by_path_is_reported(self) -> None:
        # Arrange
        source = "spec = spec_from_file_location('t', ROOT / 'part' / 'tone.py')\n"

        # Act
        found = reaches_inside(source, "part", {"Chip"}, set())

        # Assert
        self.assertEqual(found, ["loads tone from part"])

    def test_loading_a_tool_or_something_outside_the_package_passes(self) -> None:
        # Arrange
        source = (
            "import runpy\n\nrunpy.run_path(str(ROOT / 'setup.py'))\n"
            "importlib.import_module('part.doctor')\nloader = make(ROOT / 'part.py')\n"
        )

        # Act
        found = reaches_inside(source, "part", {"Chip"}, {"doctor"})

        # Assert
        self.assertEqual(found, [])

    def test_a_module_reexported_and_documented_for_callers_is_public(self) -> None:
        # Arrange
        init_source = "from . import tiles as tiles\nfrom . import core as core\n"

        # Act
        found = documented_modules(init_source, "Call `from part import tiles` first.", "part")

        # Assert
        self.assertEqual(found, {"tiles"})

    def test_a_module_documented_by_its_path_is_public_too(self) -> None:
        # Arrange
        init_source = "from . import tiles as tiles\n"

        # Act
        found = documented_modules(init_source, "| [`part/tiles.py`](part/tiles.py) |", "part")

        # Assert
        self.assertEqual(found, {"tiles"})

    def test_a_command_running_a_modules_tests_is_not_documentation(self) -> None:
        # Arrange
        init_source = "from . import core as core\n"

        # Act
        found = documented_modules(init_source, "python3 part/core.test.py", "part")

        # Assert
        self.assertEqual(found, set())

    def test_a_module_imported_without_the_alias_stays_private(self) -> None:
        # Arrange
        init_source = "from . import tiles\nfrom .core import Chip\n"

        # Act
        found = realiased_modules(init_source)

        # Assert
        self.assertEqual(found, set())

    def test_this_package_publishes_its_names_and_its_documented_modules(self) -> None:
        # Arrange
        listed = set(PACKAGE.__all__)

        # Act
        found = public_names()

        # Assert
        self.assertGreaterEqual(found, listed)

    def test_an_import_of_another_library_is_left_alone(self) -> None:
        # Arrange
        source = "from json import loads\nimport conformance.census as census\n"

        # Act
        found = reaches_inside(source, "part", {"Chip"}, set())

        # Assert
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
