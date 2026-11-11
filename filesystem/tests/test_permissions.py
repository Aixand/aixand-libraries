"""Verify private permissions and handle-based protection on real files."""

import os
from pathlib import Path
import tempfile
import unittest

from aixand_filesystem import (
    private_directory,
    private_path,
    secure_file,
    verify_private,
)


class PermissionTests(unittest.TestCase):
    def test_private_file_and_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = private_directory(Path(temporary) / "private")
            path = directory / "state"
            path.write_bytes(b"private state")
            private_path(path)
            verify_private(directory)
            verify_private(path)
            if os.name != "nt":
                self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_open_file_is_protected_without_changing_contents(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state"
            with path.open("w+b") as stream:
                stream.write(b"original bytes")
                stream.flush()
                secure_file(stream)
                verify_private(path)
            self.assertEqual(path.read_bytes(), b"original bytes")

    @unittest.skipIf(os.name == "nt", "POSIX directory rename and modes")
    def test_handle_protection_follows_original_file_after_parent_rename(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "original"
            original.mkdir()
            with (original / "state").open("w+b") as stream:
                os.fchmod(stream.fileno(), 0o644)
                original.rename(root / "moved")
                original.mkdir()
                replacement = original / "state"
                replacement.write_bytes(b"replacement")
                replacement.chmod(0o644)
                secure_file(stream)
                self.assertEqual((root / "moved/state").stat().st_mode & 0o777, 0o600)
                self.assertEqual(replacement.stat().st_mode & 0o777, 0o644)

    @unittest.skipIf(os.name == "nt", "POSIX access bits")
    def test_verification_rejects_public_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "public"
            path.write_bytes(b"")
            path.chmod(0o644)
            with self.assertRaises(PermissionError):
                verify_private(path)
