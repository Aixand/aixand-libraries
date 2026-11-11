"""Public GitHub snapshots; immutable commits, no Git checkout or hooks."""

from __future__ import annotations

import base64
import hashlib
import re
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, build_opener

from .contracts import (
    MAX_DOWNLOAD,
    MAX_ENTRIES,
    MAX_FILE,
    MAX_TOTAL,
    GitHubError,
    digest,
    loads,
    relative,
    require,
    validate_tree,
)
from .snapshots import archive_tree
from .types import Comparison, ResolvedSource, Snapshot
from .urls import COMMIT, REPO_PART, Redirects, parse_url


class Client:
    def __init__(self, *, timeout=30, retries=2, cancelled=None, progress=None):
        require(
            type(timeout) in (int, float) and 0 < timeout <= 60,
            "Timeout must be 0–60 seconds",
        )
        require(type(retries) is int and 0 <= retries <= 3, "Retries must be 0–3")
        require(
            cancelled is None or callable(cancelled),
            "Cancellation callback must be callable",
        )
        require(
            progress is None or callable(progress), "Progress callback must be callable"
        )
        self.timeout, self.retries = timeout, retries
        self.cancelled, self.progress = cancelled, progress

    def _check_cancelled(self):
        if self.cancelled is not None and self.cancelled():
            raise GitHubError("cancelled", "GitHub acquisition was cancelled")

    def get(self, url, *, limit=MAX_DOWNLOAD, json=True):
        self._check_cancelled()
        require(
            type(limit) is int and 0 <= limit <= MAX_DOWNLOAD,
            "Invalid response size limit",
        )
        parts = urlsplit(url)
        require(
            parts.scheme == "https"
            and parts.hostname
            in {"api.github.com", "codeload.github.com", "raw.githubusercontent.com"}
            and parts.port in (None, 443)
            and not parts.username
            and not parts.password
            and not parts.fragment,
            "Unsupported GitHub transport URL",
        )
        for attempt in range(self.retries + 1):
            try:
                return self._request(url, limit=limit, json=json)
            except GitHubError as error:
                if attempt == self.retries or error.code != "network":
                    raise
                for _ in range(2**attempt * 5):
                    self._check_cancelled()
                    time.sleep(0.1)

    def _request(self, url, *, limit, json):
        headers = {
            "User-Agent": "aixand-github-source/0.1",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
            with build_opener(Redirects()).open(
                Request(url, headers=headers), timeout=self.timeout
            ) as response:
                length = response.headers.get("Content-Length")
                require(
                    length is None or length.isdecimal(),
                    "Invalid GitHub Content-Length",
                    "integrity",
                )
                require(
                    length is None or int(length) <= limit,
                    "GitHub response exceeds size limit",
                    "size",
                )
                chunks, received = [], 0
                while True:
                    self._check_cancelled()
                    chunk = response.read(min(65536, limit + 1 - received))
                    if not chunk:
                        break
                    received += len(chunk)
                    require(
                        received <= limit, "GitHub response exceeds size limit", "size"
                    )
                    chunks.append(chunk)
                    if self.progress is not None:
                        self.progress({"event": "download", "bytes_received": received})
                data = b"".join(chunks)
                require(
                    len(data) <= limit, "GitHub response exceeds size limit", "size"
                )
                return loads(data) if json else data
        except HTTPError as error:
            # GitHub uses 422 as well as 404 for an unresolved commit expression.
            code = (
                "not_found"
                if error.code in (404, 422)
                else "rate_limited"
                if error.code == 429
                or (
                    error.code == 403
                    and error.headers.get("X-RateLimit-Remaining") == "0"
                )
                else "access_denied"
                if error.code in (401, 403)
                else "network"
            )
            retry = error.headers.get("Retry-After")
            error.close()
            raise GitHubError(
                code,
                f"GitHub returned HTTP {error.code}",
                status=error.code,
                retry_after=int(retry) if retry and retry.isdecimal() else None,
            ) from None
        except (URLError, TimeoutError, OSError) as error:
            raise GitHubError(
                "network", "Could not retrieve the GitHub source"
            ) from error

    def commit(self, repository, ref):
        require(
            isinstance(ref, str)
            and 0 < len(ref) <= 255
            and not any(c in ref for c in "\0\r\n"),
            "Invalid GitHub reference",
        )
        value = self.get(
            f"https://api.github.com/repos/{repository}/commits/{quote(ref, safe='')}",
            limit=2 * 1024 * 1024,
        )
        require(
            isinstance(value, dict)
            and isinstance(value.get("sha"), str)
            and COMMIT.fullmatch(value["sha"]),
            "GitHub returned an invalid commit",
            "integrity",
        )
        details = value.get("commit")
        require(
            isinstance(details, dict) and isinstance(details.get("tree"), dict),
            "GitHub returned an invalid commit tree",
            "integrity",
        )
        tree = details["tree"].get("sha")
        if isinstance(tree, str) and COMMIT.fullmatch(tree):
            if not hasattr(self, "_trees"):
                self._trees = {}
            self._trees[value["sha"]] = tree
        return value["sha"]

    def resolve(
        self, url: str, *, ref: str | None = None, path: str | None = None
    ) -> ResolvedSource:
        self._check_cancelled()
        owner, repo, tail = parse_url(url)
        metadata = self.get(
            f"https://api.github.com/repos/{owner}/{repo}", limit=1024 * 1024
        )
        require(
            isinstance(metadata, dict)
            and type(metadata.get("id")) is int
            and metadata["id"] > 0
            and isinstance(metadata.get("full_name"), str),
            "Invalid GitHub repository response",
            "integrity",
        )
        canonical = metadata["full_name"]
        require(
            len(canonical.split("/")) == 2
            and all(REPO_PART.fullmatch(p) for p in canonical.split("/")),
            "Invalid canonical repository",
            "integrity",
        )
        if tail and ref is None:
            require(len(tail) <= 32, "GitHub URL has too many path components")
            for count in range(len(tail), 0, -1):
                try:
                    ref = "/".join(tail[:count])
                    commit = self.commit(canonical, ref)
                    path = "/".join(tail[count:]) if path is None else path
                    break
                except GitHubError as error:
                    if error.code != "not_found":
                        raise
            else:
                raise GitHubError(
                    "not_found", "GitHub URL reference could not be resolved"
                )
        else:
            if tail and path is None:
                joined = "/".join(tail)
                require(
                    joined == ref or joined.startswith(ref + "/"),
                    "Specify the package path when overriding the URL reference",
                )
                path = joined[len(ref) :].lstrip("/")
            ref = ref or metadata.get("default_branch")
            commit = self.commit(canonical, ref)
        path = relative(path or "", empty=True)
        reference_kind = "commit" if COMMIT.fullmatch(ref) else "tag"
        if reference_kind != "commit":
            try:
                branch = self.get(
                    f"https://api.github.com/repos/{canonical}/branches/{quote(ref, safe='')}",
                    limit=1024 * 1024,
                )
                if isinstance(branch, dict) and branch.get("name") == ref:
                    reference_kind = "branch"
            except GitHubError as error:
                if error.code != "not_found":
                    raise
        result = {
            "schema": "github-source/source-1",
            "kind": "github",
            "repository_id": str(metadata["id"]),
            "repository": canonical,
            "url": f"https://github.com/{canonical}",
            "ref": ref,
            "path": path,
            "commit": commit,
            "reference_kind": reference_kind,
            **(
                {"tree_sha": self._trees[commit]}
                if commit in getattr(self, "_trees", {})
                else {}
            ),
        }
        self._validate_source(result)
        return result

    def snapshot(self, source):
        self._check_cancelled()
        self._validate_source(source)
        require(COMMIT.fullmatch(source["commit"]), "Source commit must be immutable")
        if source.get("path") and source.get("tree_sha"):
            tree = self.scoped_snapshot(source)
            return tree, digest(tree)
        data = self.get(
            f"https://codeload.github.com/{source['repository']}/tar.gz/{source['commit']}",
            json=False,
        )
        tree = archive_tree(data, check=self._check_cancelled)
        require(
            not any(path.rsplit("/", 1)[-1] == ".gitmodules" for path in tree["files"]),
            "Repository archives with submodules need a narrower package directory without gitlinks",
            "unsupported",
        )
        selected = source["path"]
        if selected:
            prefix = selected + "/"
            tree = {
                **tree,
                "files": {
                    p: value
                    for p, value in tree["files"].items()
                    if p == selected or p.startswith(prefix)
                },
                "directories": [
                    p
                    for p in tree["directories"]
                    if p == selected or p.startswith(prefix)
                ],
            }
            require(
                tree["files"] or tree["directories"],
                "Selected path is missing",
                "not_found",
            )
        return tree, digest(tree)

    def _validate_source(self, source):
        fields = {
            "schema",
            "kind",
            "repository_id",
            "repository",
            "url",
            "ref",
            "path",
            "commit",
            "reference_kind",
        }
        require(
            isinstance(source, dict)
            and fields <= set(source) <= fields | {"tree_sha"}
            and source.get("schema") == "github-source/source-1"
            and source.get("kind") == "github",
            "Expected a resolved GitHub source",
        )
        owner, repository, tail = parse_url(source.get("url"))
        require(
            not tail and source.get("repository") == owner + "/" + repository,
            "Source repository identity mismatch",
            "integrity",
        )
        require(
            isinstance(source.get("repository_id"), str)
            and re.fullmatch(r"[1-9][0-9]{0,31}", source["repository_id"])
            and isinstance(source.get("commit"), str)
            and COMMIT.fullmatch(source["commit"]),
            "Invalid resolved source identity",
            "integrity",
        )
        relative(source.get("path"), empty=True)
        require(
            isinstance(source["ref"], str)
            and 0 < len(source["ref"]) <= 255
            and not any(ord(c) < 32 or ord(c) == 127 for c in source["ref"])
            and source["reference_kind"] in ("branch", "tag", "commit"),
            "Invalid resolved reference",
            "integrity",
        )
        if "tree_sha" in source:
            require(
                isinstance(source["tree_sha"], str)
                and COMMIT.fullmatch(source["tree_sha"]),
                "Invalid resolved tree identity",
                "integrity",
            )

    def fetch(self, source: ResolvedSource) -> Snapshot:
        """Fetch one immutable selection; paths remain relative to the repository."""
        source = deepcopy(source)
        tree, identity = self.snapshot(source)
        return {
            "schema": "github-source/snapshot-1",
            "source": deepcopy(source),
            "tree": tree,
            "digest": identity,
        }

    def compare(self, before: ResolvedSource, after: ResolvedSource) -> Comparison:
        before, after = deepcopy(before), deepcopy(after)
        self._validate_source(before)
        self._validate_source(after)
        require(
            before["repository_id"] == after["repository_id"]
            and before["repository"] == after["repository"]
            and before["path"] == after["path"],
            "Compare the same repository and selection",
            "conflict",
        )
        return {
            "before": before["commit"],
            "after": after["commit"],
            "relationship": self.relation(before, after["commit"]),
        }

    def scoped_snapshot(self, source):
        """A directory link downloads its package, rather than every repo asset."""
        repository, requested = source["repository"], relative(source["path"])
        root = source["tree_sha"]
        require(COMMIT.fullmatch(root), "Invalid GitHub tree identity", "integrity")
        parts = requested.split("/")
        parent = ""
        node = None
        for index, component in enumerate(parts):
            self._check_cancelled()
            listing = self.get(
                f"https://api.github.com/repos/{repository}/git/trees/{root}",
                limit=8 * 1024 * 1024,
            )
            rows = self._listing(listing)
            node = next((row for row in rows if row.get("path") == component), None)
            require(
                node is not None, "Selected GitHub package path is missing", "not_found"
            )
            require(
                node.get("type") in ("tree", "blob") and node.get("mode") != "120000",
                "Source contains a link or submodule",
            )
            require(
                isinstance(node.get("sha"), str) and COMMIT.fullmatch(node["sha"]),
                "Invalid GitHub tree identity",
                "integrity",
            )
            if index < len(parts) - 1:
                require(node["type"] == "tree", "Source path crosses a regular file")
                root = node["sha"]
                parent = "/".join(parts[: index + 1])
        if node["type"] == "blob":
            entries = [{**node, "path": parts[-1]}]
            prefix = parent
        else:
            if node["type"] == "tree":
                root, prefix = node["sha"], requested
            else:
                prefix = parent
            listing = self.get(
                f"https://api.github.com/repos/{repository}/git/trees/{root}?recursive=1",
                limit=8 * 1024 * 1024,
            )
            entries = self._listing(listing)
        require(len(entries) <= MAX_ENTRIES, "Source has too many files", "size")
        blobs, directories, total = [], ([prefix] if node["type"] == "tree" else []), 0
        for entry in entries:
            self._check_cancelled()
            path = relative((prefix + "/" if prefix else "") + entry["path"])
            require(
                (entry.get("type"), entry.get("mode"))
                in {("tree", "040000"), ("blob", "100644"), ("blob", "100755")},
                "Source contains a link, submodule, or unsupported mode",
                "unsupported",
            )
            require(
                COMMIT.fullmatch(entry.get("sha", "")),
                "Invalid GitHub object identity",
                "integrity",
            )
            if entry["type"] == "tree":
                directories.append(path)
            else:
                size = entry.get("size", 0)
                require(
                    type(size) is int and 0 <= size <= MAX_FILE,
                    "Source file exceeds size limit",
                    "size",
                )
                total += size
                require(total <= MAX_TOTAL, "Source package exceeds size limit", "size")
                blobs.append((path, entry))
        validate_tree(
            {
                "schema": "github-source/tree-1",
                "directories": directories,
                "files": {
                    path: {"content_b64": "", "executable": False} for path, _ in blobs
                },
            }
        )

        def download(item):
            path, entry = item
            content = self.get(
                f"https://raw.githubusercontent.com/{repository}/{source['commit']}/{quote(path, safe='/')}",
                json=False,
                limit=MAX_FILE,
            )
            require(
                len(content) == entry.get("size"),
                "GitHub file size differs from its captured tree",
                "integrity",
            )
            require(
                not content.startswith(b"version https://git-lfs.github.com/spec/v1\n"),
                "Git LFS assets require a complete local checkout; import that local package",
                "unsupported",
            )
            header = f"blob {len(content)}\0".encode()
            actual = (
                hashlib.sha1(header + content).hexdigest()
                if len(entry["sha"]) == 40
                else hashlib.sha256(header + content).hexdigest()
            )
            require(
                actual == entry["sha"],
                "GitHub file does not match its captured tree",
                "integrity",
            )
            return path, {
                "content_b64": base64.b64encode(content).decode(),
                "executable": entry.get("mode") == "100755",
            }

        with ThreadPoolExecutor(max_workers=4) as pool:
            files = dict(pool.map(download, blobs))
        return validate_tree(
            {
                "schema": "github-source/tree-1",
                "files": files,
                "directories": directories,
            }
        )

    def _listing(self, value):
        require(
            isinstance(value, dict)
            and isinstance(value.get("tree"), list)
            and all(
                isinstance(row, dict)
                and isinstance(row.get("path"), str)
                and isinstance(row.get("sha"), str)
                and COMMIT.fullmatch(row["sha"])
                for row in value["tree"]
            ),
            "Invalid GitHub tree response",
            "integrity",
        )
        require(
            not value.get("truncated"),
            "GitHub tree is truncated; select a narrower directory",
            "size",
        )
        require(len(value["tree"]) <= MAX_ENTRIES, "Too many source entries", "size")
        paths = [row["path"] for row in value["tree"]]
        require(
            len(paths) == len(set(paths)),
            "GitHub tree contains duplicate paths",
            "integrity",
        )
        return value["tree"]

    def relation(self, source, commit):
        self._check_cancelled()
        self._validate_source(source)
        require(
            isinstance(commit, str) and COMMIT.fullmatch(commit),
            "Invalid comparison commit",
        )
        before = source["commit"]
        if before == commit:
            return "identical"
        value = self.get(
            f"https://api.github.com/repos/{source['repository']}/compare/{before}...{commit}",
            limit=8 * 1024 * 1024,
        )
        require(
            isinstance(value, dict), "Invalid GitHub comparison response", "integrity"
        )
        status = value.get("status")
        require(
            status in ("ahead", "identical", "behind", "diverged"),
            "Cannot establish GitHub update relationship",
            "integrity",
        )
        return status
