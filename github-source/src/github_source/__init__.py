"""Standalone public GitHub source acquisition. No Git dependency."""

from .client import Client
from .errors import GitHubError
from .types import Comparison, FileEntry, ResolvedSource, Snapshot, SourceTree

__version__ = "0.1.0b0"
__all__ = [
    "Client",
    "GitHubError",
    "Comparison",
    "FileEntry",
    "ResolvedSource",
    "Snapshot",
    "SourceTree",
    "__version__",
]
