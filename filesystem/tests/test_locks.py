import errno
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import aixand_filesystem
from aixand_filesystem import file_lock, lock_file, locks, unlock_file


class LockTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / "state.lock"
        self.package_root = str(Path(aixand_filesystem.__file__).parent.parent)

    def probe(self):
        code = """
import sys
sys.path.insert(0, sys.argv[1])
from aixand_filesystem import lock_file
with open(sys.argv[2], 'a+b') as stream:
    try: lock_file(stream)
    except BlockingIOError: raise SystemExit(17)
"""
        return subprocess.run(
            [sys.executable, "-I", "-S", "-c", code, self.package_root, str(self.path)],
            capture_output=True,
            timeout=10,
        )

    def test_real_process_contention_explicit_unlock_and_close_release(self):
        with self.path.open("a+b") as stream:
            lock_file(stream)
            self.assertEqual(17, self.probe().returncode)
            unlock_file(stream)
            self.assertEqual(0, self.probe().returncode)
            lock_file(stream)
        self.assertEqual(0, self.probe().returncode)

    @unittest.skipIf(os.name == "nt", "POSIX shared locks")
    def test_shared_readers_coexist_and_exclude_an_exclusive_writer(self):
        with self.path.open("a+b") as first, self.path.open("a+b") as second:
            lock_file(first, shared=True)
            lock_file(second, shared=True)
            self.assertEqual(17, self.probe().returncode)
            unlock_file(first)
            self.assertEqual(17, self.probe().returncode)
            unlock_file(second)
            self.assertEqual(0, self.probe().returncode)

    def test_context_releases_after_exception_without_closing_stream(self):
        with self.path.open("a+b") as stream:
            with self.assertRaisesRegex(RuntimeError, "abort"):
                with file_lock(stream):
                    self.assertEqual(17, self.probe().returncode)
                    raise RuntimeError("abort")
            self.assertFalse(stream.closed)
            self.assertEqual(0, self.probe().returncode)

    def test_process_termination_releases_lock(self):
        code = """
import sys
sys.path.insert(0,sys.argv[1])
from aixand_filesystem import lock_file
with open(sys.argv[2], 'a+b') as stream:
    lock_file(stream)
    print('locked', flush=True)
    sys.stdin.read()
"""
        child = subprocess.Popen(
            [sys.executable, "-I", "-S", "-c", code, self.package_root, str(self.path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            import queue
            import threading

            ready = queue.Queue()
            threading.Thread(
                target=lambda: ready.put(child.stdout.readline()), daemon=True
            ).start()
            self.assertEqual(b"locked" + os.linesep.encode(), ready.get(timeout=10))
            self.assertEqual(17, self.probe().returncode)
        finally:
            child.terminate()
            child.communicate(timeout=10)
        self.assertEqual(0, self.probe().returncode)

    def test_windows_byte_zero_protocol_and_initialization_are_stable(self):
        calls = Mock()
        windows = SimpleNamespace(locking=calls, LK_NBLCK=2, LK_UNLCK=0)
        with (
            self.path.open("a+b") as stream,
            patch.object(locks, "os", SimpleNamespace(name="nt")),
            patch.dict(sys.modules, {"msvcrt": windows}),
        ):
            for _ in range(5):
                lock_file(stream)
                self.assertEqual(0, stream.tell())
                unlock_file(stream)
        self.assertEqual(b"\0", self.path.read_bytes())
        self.assertEqual(10, calls.call_count)
        self.assertTrue(all(call.args[2] == 1 for call in calls.call_args_list))

    def test_windows_blocking_retries_but_nonblocking_reports_contention(self):
        windows = SimpleNamespace(
            locking=Mock(side_effect=[OSError(errno.EACCES, "locked"), None]),
            LK_NBLCK=2,
        )
        with (
            self.path.open("a+b") as stream,
            patch.object(locks, "os", SimpleNamespace(name="nt")),
            patch.dict(sys.modules, {"msvcrt": windows}),
            patch.object(locks.time, "sleep") as sleep,
        ):
            lock_file(stream, blocking=True)
            sleep.assert_called_once_with(0.05)
            windows.locking.side_effect = OSError(errno.EACCES, "locked")
            with self.assertRaises(BlockingIOError):
                lock_file(stream)

    def test_windows_unexpected_errors_are_not_retried(self):
        windows = SimpleNamespace(
            locking=Mock(side_effect=OSError(errno.EBADF, "bad fd")), LK_NBLCK=2
        )
        with (
            self.path.open("a+b") as stream,
            patch.object(locks, "os", SimpleNamespace(name="nt")),
            patch.dict(sys.modules, {"msvcrt": windows}),
            patch.object(locks.time, "sleep") as sleep,
        ):
            with self.assertRaises(OSError):
                lock_file(stream, blocking=True)
            sleep.assert_not_called()
