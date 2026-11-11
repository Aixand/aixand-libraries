"""Fetch a public selection; writes no downloaded files and executes no content."""
import argparse
from github_source import Client, GitHubError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Public GitHub repository, tree, or blob URL")
    parser.add_argument("--ref", default=None)
    parser.add_argument("--path", default=None)
    args = parser.parse_args()
    client = Client(timeout=30, retries=2)
    try:
        source = client.resolve(args.url, ref=args.ref, path=args.path)
        snapshot = client.fetch(source)
    except GitHubError as error:
        parser.exit(1, f"{error.code}: {error}\n")
    print(f"Commit: {source['commit']}")
    print(f"Digest: {snapshot['digest']}")
    print(f"Files: {len(snapshot['tree']['files'])}")


if __name__ == "__main__":
    main()
