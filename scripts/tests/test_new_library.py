"""Verify scaffold boundaries and generated package metadata."""
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "new_library.py"


class ScaffoldTests(unittest.TestCase):
    def run_scaffold(self, destination, *extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "sample-tools", "--import-name",
             "aixand_sample_tools", "--description", 'Sample "tools"',
             "--destination", str(destination), *extra],
            capture_output=True, text=True,
        )

    def test_scaffold_metadata_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "sample-tools"
            result = self.run_scaffold(destination)
            self.assertEqual(result.returncode, 0, result.stderr)
            metadata = tomllib.loads((destination / "pyproject.toml").read_text())
            self.assertEqual(metadata["project"]["name"], "aixand-lib-sample-tools")
            self.assertEqual(metadata["project"]["description"], 'Sample "tools"')
            self.assertTrue((destination / "src/aixand_sample_tools/py.typed").exists())
            sentinel = destination / "README.md"
            sentinel.write_text("Keep this content")
            result = self.run_scaffold(destination)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(), "Keep this content")
            self.assertFalse((destination / "CONTRIBUTING.md").exists())

    def test_invalid_import_does_not_create_destination(self):
        for name in ("../escape", "class", "MixedCase", "bad-name"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary) / "scaffold"
                result = self.run_scaffold(destination, "--import-name", name)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
