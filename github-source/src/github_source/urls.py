"""Public GitHub URLs and restricted HTTPS redirects."""

import re
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler

from .contracts import require
from .errors import GitHubError

COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")

REPO_PART = re.compile(r"[A-Za-z0-9_.-]{1,100}")


class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parts = urlsplit(newurl)
        require(
            parts.scheme == "https"
            and parts.hostname
            in {
                "api.github.com",
                "codeload.github.com",
                "github.com",
                "raw.githubusercontent.com",
            }
            and parts.port in (None, 443)
            and not parts.username,
            "GitHub redirected outside the supported hosts",
            "network",
        )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def parse_url(url):
    require(isinstance(url, str) and len(url) <= 2048, "Invalid GitHub URL")
    require(not any(ord(c) < 32 or ord(c) == 127 for c in url), "Invalid GitHub URL")
    try:
        parts = urlsplit(url)
        parts.port
    except ValueError as error:
        raise GitHubError("validation", "Invalid GitHub URL") from error
    require(
        parts.scheme == "https"
        and parts.hostname == "github.com"
        and parts.port in (None, 443)
        and not parts.username
        and not parts.password
        and not parts.query
        and not parts.fragment,
        "Use an HTTPS github.com repository or file URL",
    )
    path = unquote(parts.path).strip("/").split("/")
    require(
        len(path) >= 2
        and all(REPO_PART.fullmatch(p) and p not in (".", "..") for p in path[:2]),
        "Invalid GitHub repository",
    )
    owner, repo = path[:2]
    repo = repo.removesuffix(".git")
    require(repo and repo not in (".", ".."), "Invalid GitHub repository")
    tail = path[2:]
    require(
        not tail or (tail[0] in ("tree", "blob") and len(tail) >= 2),
        "Use a repository, tree or blob URL",
    )
    return owner, repo, tail[1:] if tail else []
