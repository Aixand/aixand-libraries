# GitHub source public API

Import from `github_source`. Python 3.11+ is required.

| API | Result and contract |
| --- | --- |
| `Client(*, timeout=30, retries=2, cancelled=None, progress=None)` | Client with positive socket timeout up to 60 seconds and 0–3 retries. Cancellation callback returns bool; progress callback receives an event and must be thread-safe. |
| `client.resolve(url, *, ref=None, path=None)` | Returns `ResolvedSource` pinned to an exact commit. Accepts public repository/tree/blob URLs; optional selection overrides. |
| `client.fetch(source)` | Returns an in-memory `Snapshot` for the resolved selection; performs no file writes. |
| `client.compare(before, after)` | Returns `Comparison` for the same repository identity and path. |
| `client.get(url, *, limit=67108864, json=True)` | Restricted HTTPS transport for supported GitHub hosts; returns parsed JSON or raw bytes when `json=False`. Limit must be between zero and 64 MiB. Prefer the selection methods for acquisition. |
| `GitHubError` | Exception with `.code`, optional HTTP `.status`, integer/absent `.retry_after`, and `.to_dict()`. |

Error codes: `validation`, `integrity`, `size`, `not_found`, `unsupported`, `network`,
`rate_limited`, `access_denied`, `conflict`, `cancelled`. Callback exceptions propagate.

## Exported TypedDict contracts

| Type | Fields |
| --- | --- |
| `ResolvedSource` | `schema`, `kind`, `repository_id`, `repository`, `url`, `ref`, `path`, `commit`, `reference_kind`; optional `tree_sha`. Schema `github-source/source-1`. |
| `FileEntry` | `content_b64` (original bytes), `executable` (bool). |
| `SourceTree` | `schema`, `files` (repository-relative path to `FileEntry`), `directories` (paths). Schema `github-source/tree-1`. |
| `Snapshot` | `schema`, `source`, `tree`, `digest` (SHA-256 content identity). Schema `github-source/snapshot-1`. |
| `Comparison` | `before`, `after` (commits), `relationship` (`ahead`, `identical`, `behind`, `diverged`). |

These mappings are JSON contracts, not runtime model objects. File selections
contain only the selected file; directories retain repository-relative paths.
The [overview](../README.md#contracts) explains canonical hashing and identity.

[Usage](usage.md) · [Type definitions](../src/github_source/types.py)
