"""One batch release can contain independently versioned libraries."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "release", Path(__file__).parents[1] / "release.py"
)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class ReleaseSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for slug in release.PACKAGES:
            directory = self.root / slug
            directory.mkdir()
            (directory / "pyproject.toml").write_text(
                f'[project]\nname = "aixand-lib-{slug}"\nversion = "0.1.0b0"\n'
            )

    def test_branch_build_checks_all_packages(self):
        self.assertEqual(release.select("", self.root), list(release.PACKAGES))

    def test_repository_tag_releases_all_libraries(self):
        self.assertEqual(release.select("release-1", self.root), list(release.PACKAGES))

    def test_batch_preserves_independent_versions(self):
        versions = {
            "filesystem": "0.1.0",
            "local-runtime": "0.3.0",
            "github-source": "0.2.1",
        }
        for slug, version in versions.items():
            (self.root / slug / "pyproject.toml").write_text(
                f'[project]\nname = "aixand-lib-{slug}"\nversion = "{version}"\n'
            )
        self.assertEqual(release.select("release-2", self.root), list(release.PACKAGES))
        self.assertEqual(
            {slug: p["version"] for slug, p in release.manifest(self.root).items()},
            versions,
        )

    def test_invalid_batch_tags_are_rejected(self):
        for tag in [
            "filesystem-v0.2.0",
            "v0.2.0",
            "unknown-v0.1.0b0",
            "filesystem-v0.1.0b0-extra",
        ]:
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                release.select(tag, self.root)

    def test_distribution_identity_is_checked(self):
        (self.root / "filesystem/pyproject.toml").write_text(
            '[project]\nname = "aixand-filesystem"\nversion = "0.1.0b0"\n'
        )
        with self.assertRaises(ValueError):
            release.select("release-1", self.root)


if __name__ == "__main__":
    unittest.main()
