import ast
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import aixand_filesystem


class StandaloneTests(unittest.TestCase):
    def test_only_standard_library_imports_and_isolated_package(self):
        package = Path(aixand_filesystem.__file__).parent
        for path in package.glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                names = (
                    [a.name for a in node.names]
                    if isinstance(node, ast.Import)
                    else (
                        [node.module]
                        if isinstance(node, ast.ImportFrom)
                        and node.level == 0
                        and node.module
                        else []
                    )
                )
                for name in names:
                    self.assertIn(
                        name.split(".")[0],
                        sys.stdlib_module_names | {"aixand_filesystem"},
                    )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(
                package,
                root / "aixand_filesystem",
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            script = r"""
import sys
sys.path.insert(0, sys.argv[1])
from pathlib import Path
from aixand_filesystem import file_lock, PinnedPath
with (Path(sys.argv[1])/'state.lock').open('a+b') as stream:
    with file_lock(stream):
        assert not stream.closed
assert all(n.split('.')[0] in sys.stdlib_module_names | {'__main__', 'aixand_filesystem'} for n in sys.modules)
"""
            result = subprocess.run(
                [sys.executable, "-I", "-S", "-c", script, str(root)],
                cwd=root,
                text=True,
                capture_output=True,
                timeout=10,
            )
            self.assertEqual(0, result.returncode, result.stderr)
