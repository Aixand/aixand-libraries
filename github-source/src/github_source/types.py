"""Versioned JSON contracts. Paths in a selection remain repository-relative."""

from typing import Literal, NotRequired, TypedDict


class ResolvedSource(TypedDict):
    schema: str
    kind: Literal["github"]
    repository_id: str
    repository: str
    url: str
    ref: str
    path: str
    commit: str
    reference_kind: Literal["branch", "tag", "commit"]
    tree_sha: NotRequired[str]


class FileEntry(TypedDict):
    content_b64: str
    executable: bool


class SourceTree(TypedDict):
    schema: str
    files: dict[str, FileEntry]
    directories: list[str]


class Snapshot(TypedDict):
    schema: str
    source: ResolvedSource
    tree: SourceTree
    digest: str


class Comparison(TypedDict):
    before: str
    after: str
    relationship: Literal["ahead", "identical", "behind", "diverged"]
