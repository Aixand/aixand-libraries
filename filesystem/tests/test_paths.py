import errno
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from aixand_filesystem import PinnedPath
from aixand_filesystem._windows import native_path


class PathContractTests(unittest.TestCase):
    def test_rejects_absolute_or_escaping_components_before_io(self):
        for parts in ([".."], ["a/b"], ["a\\b"], ["C:"], ["."], ["name "], "filename"):
            with self.subTest(parts=parts), self.assertRaises(PermissionError):
                PinnedPath("root", parts)

    def test_native_path_supports_drives_unc_and_existing_prefix(self):
        self.assertEqual("\\\\?\\C:\\long", native_path("C:\\long"))
        self.assertEqual("\\\\?\\UNC\\server\\share", native_path("\\\\server\\share"))
        self.assertEqual("\\\\?\\C:\\long", native_path("\\\\?\\C:\\long"))

    @unittest.skipIf(os.name == "nt", "POSIX unsupported contract")
    def test_posix_import_is_safe_and_pinning_reports_unsupported(self):
        with self.assertRaises(OSError) as error:
            with PinnedPath(Path.cwd(), directory=True):
                pass
        self.assertEqual(errno.ENOTSUP, error.exception.errno)


@unittest.skipUnless(os.name == "nt", "Requires real Windows kernel handles")
class WindowsPinnedPathTests(unittest.TestCase):
    def test_reads_bytes_pins_ancestors_and_releases_on_exit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "nested"
            parent.mkdir()
            (parent / "file.txt").write_bytes(b"original\r\n")
            with PinnedPath(root, ["nested", "file.txt"]) as selected:
                self.assertEqual(b"original\r\n", selected.file.read())
                with self.assertRaises(OSError):
                    parent.rename(root / "moved")
            self.assertTrue(selected.file.closed)
            parent.rename(root / "moved")

    def test_rejects_junction_and_releases_handles_after_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.mkdir()
            (target / "file.txt").write_bytes(b"outside")
            junction = root / "junction"
            result = subprocess.run(
                ["cmd", "/d", "/c", "mklink", "/J", str(junction), str(target)],
                capture_output=True,
                timeout=10,
            )
            if result.returncode:
                self.skipTest("Junction creation is unavailable")
            with self.assertRaises(PermissionError):
                with PinnedPath(root, ["junction", "file.txt"]):
                    pass
            target.rename(root / "renamed")

    def test_context_exception_releases_directory_handles(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "folder"
            root.mkdir()
            with self.assertRaises(RuntimeError):
                with PinnedPath(root, directory=True):
                    raise RuntimeError("abort")
            root.rename(root.with_name("renamed"))
