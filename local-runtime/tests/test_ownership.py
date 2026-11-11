"""Exercise ownership with real processes rather than PID/lock mocks."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from aixand_filesystem import lock_file, private_directory
from aixand_local_runtime import process_start


class ProcessOwnership(unittest.TestCase):
    def test_live_identity_is_stable_and_exited_process_is_absent(self):
        own = process_start(os.getpid())
        self.assertIsNotNone(own)
        self.assertEqual(own, process_start(os.getpid()))
        child = subprocess.Popen(
            [sys.executable, "-I", "-c", "import sys;sys.stdin.read()"],
            stdin=subprocess.PIPE,
        )
        try:
            token = process_start(child.pid)
            self.assertIsNotNone(token)
            self.assertEqual(token, process_start(child.pid))
        finally:
            child.communicate(timeout=10)
        self.assertIsNone(process_start(child.pid))
        for pid in (0, -1, 4294967295, "invalid", None):
            self.assertIsNone(process_start(pid))

    def test_lock_excludes_another_process_and_releases(self):
        with tempfile.TemporaryDirectory(prefix="platform locks ") as directory:
            path = Path(directory) / "state.lock"
            code = """import sys
from aixand_filesystem import lock_file
with open(sys.argv[1], 'a+') as stream:
    try:
        lock_file(stream)
    except BlockingIOError:
        raise SystemExit(17)
"""
            with path.open("a+") as stream:
                lock_file(stream)
                result = subprocess.run(
                    [sys.executable, "-I", "-c", code, str(path)], timeout=10
                )
                self.assertEqual(result.returncode, 17)
            result = subprocess.run(
                [sys.executable, "-I", "-c", code, str(path)], timeout=10
            )
            self.assertEqual(result.returncode, 0)

    @unittest.skipIf(os.name == "nt", "POSIX file modes")
    def test_existing_directory_is_private_and_links_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "private"
            path.mkdir(mode=0o755)
            self.assertEqual(private_directory(path), path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o700)
            (root / "link").symlink_to(path, target_is_directory=True)
            with self.assertRaises(PermissionError):
                private_directory(root / "link")
