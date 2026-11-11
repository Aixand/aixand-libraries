# GitHub Source

Standalone Python 3.11+ acquisition of public GitHub repository content. Install
`aixand-lib-github-source`, import `github_source`. Runtime dependencies: none. No Git,
curl, background worker, or service is required.

```python
from github_source import Client

client = Client(timeout=30, retries=2)
source = client.resolve(
    "https://github.com/example/repository",
    ref="main", path="skills/review",
)
snapshot = client.fetch(source)

latest = client.resolve(source["url"], ref=source["ref"], path=source["path"])
relationship = client.compare(source, latest)["relationship"]
```

Repository, `tree`, and `blob` URLs are supported. Slash-containing branch names
are resolved against GitHub. When overriding the reference in a directory/file
URL, supply an explicit `path` if it cannot be derived unambiguously.

## Contracts

`resolve` returns a `github-source/source-1` mapping with stable repository ID,
canonical repository name/URL, requested reference, selected path, exact commit,
reference kind (`branch`, `tag`, or `commit`), and the root Git tree identity when
provided by GitHub. Reference kind is descriptive; callers decide pinning/tracking.

`fetch` returns `github-source/snapshot-1` containing the resolved source, a
`github-source/tree-1` tree, and its SHA-256 content digest. Paths remain relative
to the repository root, including for scoped selections. Trees preserve original
file bytes as `content_b64`, executable flags, and directories (including empty
directories). A file selection returns that file only; the library has no special
knowledge of SKILL.md, pack.json, or server.json. Callers select a containing
directory when their package needs accompanying files.

Content identity hashes sorted canonical UTF-8 JSON with finite values. Directories
are normalized and sorted, including implicit parents. Commit/origin metadata is
outside the tree digest, so unrelated repository commits can have equal content
identities. Hashes establish equality and integrity, not publisher authenticity.

`compare` accepts two selections from the same repository identity/path and returns
their commits and GitHub's `ahead`, `identical`, `behind`, or `diverged` relationship.
It does not decide whether to activate, merge, install, or overwrite content.

The exported `ResolvedSource`, `SourceTree`, `FileEntry`, `Snapshot`, and
`Comparison` TypedDicts describe these JSON contracts. `GitHubError` exposes a
stable `code`, optional HTTP `status` and integer `retry_after`, and `to_dict()`.
Codes include `validation`, `integrity`, `size`, `not_found`, `unsupported`,
`network`, `rate_limited`, `access_denied`, `conflict`, and `cancelled`.

## Bounds and transport

Downloads use HTTPS with restricted redirect hosts. A selected directory is fetched
through Git trees and commit-pinned raw files; each file is checked against its
Git blob identity. Repository downloads use GitHub archives without a checkout.
No downloaded scripts or hooks execute, and the library does not write files.

Limits: 64 MiB per repository archive, 128 MiB total source bytes, 16 MiB per file,
10,000 entries including implicit directories, 32 path components, 1,024 path
characters, and 255 UTF-8 bytes per component. Tree/metadata response sizes are
bounded separately. Archive expansion, including tar metadata, is bounded before
unbounded allocation. Symlinks, hard links, submodules, special files, unsafe or
colliding portable paths, and unresolved Git LFS pointers are rejected. A repository
archive containing submodule declarations requires a narrower supported selection.

`Client(timeout=30, retries=2, cancelled=None, progress=None)` has a 0–60 second
positive socket timeout and at most three retries. Transient network/server failures
use bounded backoff. Rate limits are reported for the caller to reschedule; the
library does not wait for a rate-limit reset. No credentials or private repositories
are supported in this version.

`cancelled()` returns a boolean. Cancellation is checked between requests, read
chunks, backoff steps, tree entries, and archive entries; a blocked socket remains
bounded by its timeout. `progress(event)` receives download byte progress. Scoped
downloads use up to four threads, so callbacks must be thread-safe. Callback
exceptions propagate. Snapshots are captured in memory within the limits above.

## Ownership

This library owns URL/reference resolution, snapshot acquisition, and commit
comparison. Native format discovery, accepted storage, customization/reconciliation,
tracking schedules, persistent jobs, and dependency installation belong to callers.
The `aixand-libraries/` location is a repository organization choice, not a runtime path
dependency. Applications supply their own adapters and storage policies.

## Development

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
python -m pip wheel --no-deps .
```

Tests use local fixtures and mocked transport, including an isolated copied-package
check with site packages disabled. They require no GitHub credentials or network.

## Local developer commands

Inside the aixand-libraries source checkout, run from this directory with
Python 3.11+ and uv:

```sh
./dev.sh develop --local
./dev.sh check
./dev.sh test
./dev.sh build
```

Use `.\dev.ps1` on Windows. Each package owns its development environment and
helper. Commands run within this package. See the
[development guide](docs/development.md) for wheel-based setup without sibling
sources, lock updates, and build outputs.

## Documentation and support

See the [documentation index](docs/README.md) for usage, API reference, and runnable
starter examples. Report ordinary problems through the integrating product's
support channel or issue tracker. External contributions are not currently
accepted due to limited maintainer capacity; see [reporting guidance](../docs/reporting.md).
Report vulnerabilities [privately](../SECURITY.md).
