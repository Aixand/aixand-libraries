# Use GitHub source acquisition

Install `aixand-lib-github-source` into a Python 3.11+ environment. No Git executable
or credentials are needed. Only public GitHub repositories are supported.

```sh
python -m pip install aixand-lib-github-source
python examples/fetch_snapshot.py https://github.com/Aixand/undercurrent --ref main --path README.md
```

Run from the package directory. This makes network requests and prints a commit,
content digest, and file count; it writes no downloaded files. GitHub availability
and anonymous rate limits apply. You can pass any supported public repository,
`tree`, or `blob` URL instead. Use explicit `--ref` and `--path` for ambiguous URLs.

## Resolve, then fetch

`Client.resolve(url, ref=..., path=...)` resolves the selection to an exact commit.
Pass that mapping to `fetch` to obtain an in-memory snapshot. Files in
`snapshot["tree"]["files"]` retain repository-relative paths, base64-encoded original
bytes, and executable flags. Directory selection does not flatten paths.
Decode only the files your application needs:

```python
import base64

from github_source import Client

client = Client()
source = client.resolve("https://github.com/Aixand/undercurrent", ref="main", path="README.md")
snapshot = client.fetch(source)
raw = base64.b64decode(snapshot["tree"]["files"]["README.md"]["content_b64"])
```

The library does not install, execute, or persist downloaded content. Applications
own format validation, storage containment, permissions, and activation policy.
A content digest establishes equality/integrity, not publisher trust.

## Track a reference

Resolve the same repository/reference/path again, then call
`client.compare(before, after)`. The result describes commit ancestry (`ahead`,
`identical`, `behind`, or `diverged`); it does not recommend installation or merging.
Two different commits can have equal snapshot content digests.

## Handle errors and bounded work

Catch `GitHubError` and inspect `.code`, `.status`, and `.retry_after`; `.to_dict()`
provides a structured error. Rate limiting is returned to the caller rather than
waiting for the reset. Choose whether and when to reschedule in your application.
Client timeouts bound socket operations, not the total acquisition duration.
Cancellation callbacks run between bounded work steps; they do not interrupt a
blocked socket immediately. Progress callbacks may run on download threads and
must be thread-safe; callback exceptions propagate.

Selections containing links, submodules, unsupported file kinds, or unsafe paths
are rejected. See [bounds and transport](../README.md#bounds-and-transport) for
size, entry, and path limits. Narrow a selection rather than assuming arbitrary
repository contents can be downloaded.

[API reference](api.md) · [Runnable starter](../examples/README.md)
