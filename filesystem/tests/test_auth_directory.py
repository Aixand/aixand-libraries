"""Check the Windows authentication directory boundary."""

import errno
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from aixand_filesystem import current_user_sid, private_directory, verify_private
from aixand_filesystem import auth_directory


class AuthenticationDirectoryTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "Other operating systems only")
    def test_account_identity_rejects_other_operating_systems(self):
        with self.assertRaises(OSError) as caught:
            current_user_sid()
        self.assertEqual(caught.exception.errno, errno.ENOTSUP)

    @unittest.skipIf(os.name == "nt", "Other operating systems only")
    def test_cli_rejects_unsupported_system_without_creating_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "auth"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "aixand_filesystem.auth_directory",
                    "create",
                    str(target),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("require Windows", result.stderr)
            self.assertFalse(target.exists())

    @unittest.skipUnless(os.name == "nt", "Native Windows ACL checks")
    def test_private_creation_checks_and_file_protection(self):
        self.assertTrue(current_user_sid().startswith("S-1-"))
        with tempfile.TemporaryDirectory() as temporary:
            root = private_directory(temporary)
            target = root / "auth" / "nested"
            auth_directory.create(target)
            auth_directory.create(target)
            auth_directory.check(target)
            verify_private(target)
            token = target / "token.json"
            token.write_text("{}")
            auth_directory.secure_file(token)
            verify_private(token)
            with self.assertRaises(OSError):
                auth_directory.secure_file(target)
