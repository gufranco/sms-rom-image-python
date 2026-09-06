import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ast  # noqa: E402
import unittest  # noqa: E402

import smsimage  # noqa: E402
from smsimage import errors  # noqa: E402

SOURCE = ROOT / "smsimage" / "errors.py"


def defined_errors() -> list[str]:
    return [
        name
        for name in dir(errors)
        if not name.startswith("_")
        and isinstance(getattr(errors, name), type)
        and issubclass(getattr(errors, name), Exception)
    ]


def imported_modules(tree: ast.Module) -> list[str]:
    from_imports = [
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    ]
    plain = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    ]
    return from_imports + plain


class SurfaceTest(unittest.TestCase):
    def test_it_defines_at_least_one_error(self) -> None:
        self.assertGreater(len(defined_errors()), 0)

    def test_every_error_it_defines_is_exported_from_the_package(self) -> None:
        missing = [name for name in defined_errors() if name not in smsimage.__all__]

        self.assertEqual(missing, [])

    def test_the_package_exports_the_class_and_not_a_name_that_shadows_it(self) -> None:
        rebound = [
            name
            for name in defined_errors()
            if getattr(smsimage, name, None) is not getattr(errors, name)
        ]

        self.assertEqual(rebound, [])

    def test_it_defines_each_name_exactly_once(self) -> None:
        tree = ast.parse(SOURCE.read_text())
        named = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]

        self.assertEqual(sorted(named), sorted(set(named)))

    def test_every_error_carries_a_docstring(self) -> None:
        tree = ast.parse(SOURCE.read_text())
        silent = [
            node.name
            for node in tree.body
            if isinstance(node, ast.ClassDef) and ast.get_docstring(node) is None
        ]

        self.assertEqual(silent, [])


class NoCycleTest(unittest.TestCase):
    def test_it_imports_nothing_from_its_own_package(self) -> None:
        reached = imported_modules(ast.parse(SOURCE.read_text()))

        self.assertEqual([one for one in reached if one.startswith("smsimage")], [])

    def test_it_reaches_for_nothing_relative_either(self) -> None:
        tree = ast.parse(SOURCE.read_text())
        relative = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.level
        ]

        self.assertEqual(relative, [])


class RaisingTest(unittest.TestCase):
    def test_a_caller_can_catch_a_dump_with_no_parts_by_name(self) -> None:
        with self.assertRaises(errors.NoParts):
            raise errors.NoParts("no numbered part here")

    def test_a_caller_can_catch_a_record_with_no_deciding_digest(self) -> None:
        with self.assertRaises(errors.NoAuthority):
            raise errors.NoAuthority("nothing decides")

    def test_a_caller_can_catch_a_document_that_is_not_one(self) -> None:
        with self.assertRaises(errors.Malformed):
            raise errors.Malformed("not a manifest")


if __name__ == "__main__":
    unittest.main()
