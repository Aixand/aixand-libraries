import ast
import base64
import io
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

from github_source import Client, GitHubError
from github_source.client import Redirects, archive_tree, parse_url
from github_source.contracts import digest, validate_tree


def archive(entries):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for path, body, mode, kind in entries:
            entry = tarfile.TarInfo(path)
            entry.mode, entry.type = mode, kind
            if kind == tarfile.REGTYPE:
                entry.size = len(body)
                tar.addfile(entry, io.BytesIO(body))
            else:
                entry.linkname = "../../escape"
                tar.addfile(entry)
    return buffer.getvalue()


class ContractTests(unittest.TestCase):
    def test_archive_preserves_binary_executable_hidden_and_empty_directory(self):
        data = archive(
            [
                ("repo/skill/binary", b"\x00\xff", 0o755, tarfile.REGTYPE),
                ("repo/skill/.hidden", b"original\r\n", 0o644, tarfile.REGTYPE),
                ("repo/skill/empty/", b"", 0o755, tarfile.DIRTYPE),
            ]
        )
        tree = archive_tree(data)
        self.assertEqual(
            b"\x00\xff", base64.b64decode(tree["files"]["skill/binary"]["content_b64"])
        )
        self.assertTrue(tree["files"]["skill/binary"]["executable"])
        self.assertEqual(["skill", "skill/empty"], tree["directories"])
        self.assertEqual(digest(tree), digest(archive_tree(data)))

    def test_archive_rejects_escape_links_duplicates_collisions_and_lfs(self):
        cases = [
            [("repo/../escape", b"", 0o644, tarfile.REGTYPE)],
            [("repo/link", b"", 0o644, tarfile.SYMTYPE)],
            [("repo/file", b"", 0o644, tarfile.LNKTYPE)],
            [
                ("repo/a", b"", 0o644, tarfile.REGTYPE),
                ("repo/A", b"", 0o644, tarfile.REGTYPE),
            ],
            [
                ("repo/a", b"", 0o644, tarfile.REGTYPE),
                ("other/b", b"", 0o644, tarfile.REGTYPE),
            ],
            [
                (
                    "repo/a",
                    b"version https://git-lfs.github.com/spec/v1\n",
                    0o644,
                    tarfile.REGTYPE,
                )
            ],
            [("repo/NUL.txt", b"", 0o644, tarfile.REGTYPE)],
        ]
        for entries in cases:
            with self.subTest(entries=entries), self.assertRaises(GitHubError):
                archive_tree(archive(entries))
        for raw in (b"invalid", b"\x1f\x8b\x08"):
            with self.assertRaises(GitHubError):
                archive_tree(raw)

    def test_expanded_file_and_metadata_limits(self):
        with patch("github_source.snapshots.MAX_FILE", 3):
            with self.assertRaises(GitHubError):
                archive_tree(archive([("repo/file", b"1234", 0o644, tarfile.REGTYPE)]))
        with (
            patch("github_source.snapshots.MAX_TOTAL", 1),
            patch("github_source.snapshots.MAX_ENTRIES", 0),
        ):
            with self.assertRaises(GitHubError):
                archive_tree(archive([("repo/file", b"1234", 0o644, tarfile.REGTYPE)]))

    def test_portable_tree_collisions_and_invalid_payloads(self):
        base = {"schema": "github-source/tree-1", "directories": [], "files": {}}
        for names in (("a", "a/b"), ("é", "e\u0301"), ("a.",), ("a\\b",), ("C:/x",)):
            tree = {
                **base,
                "files": {
                    name: {"content_b64": "", "executable": False} for name in names
                },
            }
            with self.subTest(names=names), self.assertRaises(GitHubError):
                validate_tree(tree)

    def test_urls_and_redirects_restrict_hosts_and_credentials(self):
        for url in (
            "https://evil.test/a/b",
            "https://u:p@github.com/a/b",
            "https://github.com:bad/a/b",
            "https://github.com/a/b?token=x",
            "https://github.com/a/b#fragment",
            "https://github.com/a/.git",
        ):
            with self.subTest(url=url), self.assertRaises(GitHubError):
                parse_url(url)
        with self.assertRaises(GitHubError):
            Redirects().redirect_request(
                Request("https://api.github.com/test"),
                None,
                302,
                "",
                {},
                "https://evil.test/archive",
            )

    def test_archive_cancellation(self):
        def cancelled():
            raise GitHubError("cancelled", "Cancelled")

        with self.assertRaises(GitHubError) as error:
            archive_tree(
                archive([("repo/file", b"x", 0o644, tarfile.REGTYPE)]), check=cancelled
            )
        self.assertEqual("cancelled", error.exception.code)

    def test_independent_package_uses_only_standard_library(self):
        import github_source

        root = Path(github_source.__file__).parent
        for path in root.glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                names = (
                    [alias.name for alias in node.names]
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
                        name.split(".")[0], sys.stdlib_module_names | {"github_source"}
                    )
        with tempfile.TemporaryDirectory() as directory:
            shutil.copytree(
                root,
                Path(directory) / "github_source",
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            script = "import sys; sys.path.insert(0,sys.argv[1]); from github_source import Client; Client(); print('isolated')"
            result = subprocess.run(
                [sys.executable, "-I", "-S", "-c", script, directory],
                cwd=directory,
                text=True,
                capture_output=True,
                timeout=15,
            )
            self.assertEqual(0, result.returncode, result.stderr)


class TransportTests(unittest.TestCase):
    def response(self, content=b"{}", headers=None):
        response = io.BytesIO(content)
        response.headers = headers or {}
        return response

    def test_network_retry_is_bounded_and_response_is_closed(self):
        response = self.response()
        with (
            patch("github_source.client.build_opener") as opener,
            patch("github_source.client.time.sleep"),
        ):
            opener.return_value.open.side_effect = [URLError("temporary"), response]
            self.assertEqual({}, Client(retries=1).get("https://api.github.com/test"))
            self.assertEqual(2, opener.return_value.open.call_count)
        self.assertTrue(response.closed)

    def test_rate_limit_exposes_retry_without_retrying(self):
        with patch("github_source.client.build_opener") as opener:
            opener.return_value.open.side_effect = HTTPError(
                "url", 429, "limited", {"Retry-After": "60"}, None
            )
            with self.assertRaises(GitHubError) as error:
                Client().get("https://api.github.com/test")
            self.assertEqual("rate_limited", error.exception.code)
            self.assertEqual(60, error.exception.retry_after)
            self.assertEqual(1, opener.return_value.open.call_count)

    def test_response_limit_and_cancelled_download(self):
        with patch("github_source.client.build_opener") as opener:
            opener.return_value.open.return_value = self.response(b"12345")
            with self.assertRaises(GitHubError) as error:
                Client().get("https://api.github.com/test", limit=4)
            self.assertEqual("size", error.exception.code)
        events = []
        with patch("github_source.client.build_opener") as opener:
            response = self.response(b"12345")
            opener.return_value.open.return_value = response
            with self.assertRaises(GitHubError) as error:
                Client(cancelled=lambda: bool(events), progress=events.append).get(
                    "https://api.github.com/test"
                )
            self.assertEqual("cancelled", error.exception.code)
            self.assertTrue(response.closed)

    def test_missing_reference_is_not_retried(self):
        with patch("github_source.client.build_opener") as opener:
            opener.return_value.open.side_effect = HTTPError(
                "url", 404, "missing", {}, None
            )
            with self.assertRaises(GitHubError) as error:
                Client().get("https://api.github.com/test")
            self.assertEqual("not_found", error.exception.code)
            self.assertEqual(1, opener.return_value.open.call_count)
