import hashlib
import unittest
from urllib.parse import unquote

from github_source import Client as GitHub
from github_source import GitHubError as SourceError


class GithubTests(unittest.TestCase):
    def client(self, *, tamper=False):
        class Fixture(GitHub):
            def get(self, url, **options):
                if url == "https://api.github.com/repos/example/resources":
                    return {
                        "id": 123,
                        "full_name": "example/resources",
                        "default_branch": "main",
                    }
                if "/commits/" in url:
                    ref = unquote(url.split("/commits/")[1])
                    if ref not in ("main", "feature/docs", "v1"):
                        raise SourceError("not_found", "Unresolved commit expression")
                    return {"sha": "a" * 40, "commit": {"tree": {"sha": "b" * 40}}}
                if "/branches/" in url:
                    ref = unquote(url.split("/branches/")[1])
                    if ref == "v1":
                        raise SourceError("not_found", "Tag is not a branch")
                    return {"name": ref}
                if "/git/trees/" in url:
                    key = url.split("/git/trees/")[1]
                    if key == "b" * 40:
                        return {
                            "tree": [
                                {
                                    "path": "skills",
                                    "type": "tree",
                                    "mode": "040000",
                                    "sha": "c" * 40,
                                }
                            ]
                        }
                    if key == "c" * 40:
                        return {
                            "tree": [
                                {
                                    "path": "review",
                                    "type": "tree",
                                    "mode": "040000",
                                    "sha": "d" * 40,
                                }
                            ]
                        }
                    if key in ("d" * 40, "d" * 40 + "?recursive=1"):
                        data = b"Content"
                        sha = hashlib.sha1(b"blob 7\0" + data).hexdigest()
                        return {
                            "tree": [
                                {
                                    "path": "SKILL.md",
                                    "type": "blob",
                                    "size": 7,
                                    "mode": "100755",
                                    "sha": sha,
                                }
                            ]
                        }
                if url.startswith("https://raw.githubusercontent.com/"):
                    return b"Tampered" if tamper else b"Content"
                raise AssertionError(url)

        return Fixture()

    def test_directory_url_resolves_slash_branch_without_guessing_path(self):
        source = self.client().resolve(
            "https://github.com/example/resources/tree/feature/docs/skills/review"
        )
        self.assertEqual(source["ref"], "feature/docs")
        self.assertEqual(source["path"], "skills/review")
        self.assertEqual("branch", source["reference_kind"])

    def test_tags_are_pinned_and_explicit_tracking_is_supported(self):
        client = self.client()
        self.assertEqual(
            "tag",
            client.resolve("https://github.com/example/resources", ref="v1")[
                "reference_kind"
            ],
        )

    def test_scoped_package_fetch_verifies_blobs_and_executable_mode(self):
        client = self.client()
        source = client.resolve(
            "https://github.com/example/resources/tree/main/skills/review"
        )
        tree, identity = client.snapshot(source)
        self.assertEqual(list(tree["files"]), ["skills/review/SKILL.md"])
        self.assertTrue(tree["files"]["skills/review/SKILL.md"]["executable"])
        self.assertTrue(identity.startswith("sha256:"))

    def test_scoped_fetch_rejects_content_different_from_captured_commit(self):
        client = self.client(tamper=True)
        source = client.resolve(
            "https://github.com/example/resources/tree/main/skills/review"
        )
        with self.assertRaises(SourceError) as error:
            client.snapshot(source)
        self.assertEqual(error.exception.code, "integrity")

    def test_public_fetch_selects_single_file_without_format_knowledge(self):
        client = self.client()
        source = client.resolve(
            "https://github.com/example/resources/blob/main/skills/review/SKILL.md"
        )
        result = client.fetch(source)
        self.assertEqual("github-source/snapshot-1", result["schema"])
        self.assertEqual(["skills/review/SKILL.md"], list(result["tree"]["files"]))
        self.assertEqual(source, result["source"])

    def test_content_identity_is_independent_of_repository_commit(self):
        client = self.client()
        source = client.resolve(
            "https://github.com/example/resources/tree/main/skills/review"
        )
        before = client.fetch(source)
        after = client.fetch({**source, "commit": "e" * 40})
        self.assertEqual(before["digest"], after["digest"])
        self.assertNotEqual(before["source"]["commit"], after["source"]["commit"])

    def test_compare_reports_divergence_and_rejects_different_selections(self):
        client = self.client()
        source = client.resolve(
            "https://github.com/example/resources/tree/main/skills/review"
        )
        self.assertEqual("identical", client.compare(source, source)["relationship"])
        client.get = lambda *args, **kwargs: {"status": "diverged"}
        self.assertEqual(
            "diverged",
            client.compare(source, {**source, "commit": "f" * 40})["relationship"],
        )
        with self.assertRaises(SourceError):
            client.compare(source, {**source, "path": "other"})

    def test_truncated_listing_is_an_explicit_failure(self):
        client = self.client()
        source = client.resolve(
            "https://github.com/example/resources/tree/main/skills/review"
        )
        client.get = lambda *args, **kwargs: {"truncated": True, "tree": []}
        with self.assertRaises(SourceError) as error:
            client.fetch(source)
        self.assertEqual("size", error.exception.code)


if __name__ == "__main__":
    unittest.main()
