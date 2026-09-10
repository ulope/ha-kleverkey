"""Set the version in the integration manifest.

The release workflow runs this so that the tag, the GitHub release and
``manifest.json`` all carry the same version. Only the version value is
rewritten, so the rest of the file keeps its formatting.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

DEFAULT_MANIFEST = pathlib.Path("custom_components/kleverkey/manifest.json")

VERSION_ENTRY = re.compile(r'("version"\s*:\s*")([^"]*)(")')
VALID_VERSION = re.compile(r"^\d+\.\d+\.\d+(?:[\w.-]+)?$")


def set_version(manifest: str, version: str) -> str:
    """Return ``manifest`` with its version replaced by ``version``."""
    updated, count = VERSION_ENTRY.subn(
        lambda match: f"{match.group(1)}{version}{match.group(3)}", manifest
    )
    if count != 1:
        raise ValueError(f"expected exactly one version entry, found {count}")
    return updated


def main(argv: list[str] | None = None) -> int:
    """Rewrite the manifest version and report whether it changed."""
    parser = argparse.ArgumentParser(description="Set the manifest version.")
    parser.add_argument("version", help="version to write, for example 0.2.0")
    parser.add_argument(
        "--manifest",
        type=pathlib.Path,
        default=DEFAULT_MANIFEST,
        help="path to manifest.json",
    )
    args = parser.parse_args(argv)

    if not VALID_VERSION.match(args.version):
        print(f"error: {args.version!r} is not a valid version", file=sys.stderr)
        return 2

    manifest = args.manifest.read_text(encoding="utf-8")
    try:
        updated = set_version(manifest, args.version)
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    if updated == manifest:
        print(f"{args.manifest} is already at {args.version}")
        return 0

    args.manifest.write_text(updated, encoding="utf-8")
    print(f"{args.manifest} set to {args.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
