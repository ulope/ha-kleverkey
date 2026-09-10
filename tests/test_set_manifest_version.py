"""Tests for the manifest version helper used by the release workflow."""

from __future__ import annotations

import json
import pathlib

import pytest

from scripts.set_manifest_version import main, set_version

MANIFEST = (
    "{\n"
    '  "domain": "kleverkey",\n'
    '  "codeowners": ["@ulope"],\n'
    '  "version": "0.1.0"\n'
    "}\n"
)


def test_replaces_only_the_version() -> None:
    """The version changes and the rest of the file is untouched."""
    updated = set_version(MANIFEST, "1.2.3")

    assert json.loads(updated)["version"] == "1.2.3"
    assert updated == MANIFEST.replace('"0.1.0"', '"1.2.3"')
    # Formatting, including the inline list, survives.
    assert '"codeowners": ["@ulope"]' in updated


def test_rejects_a_manifest_without_a_version() -> None:
    """A manifest with no version entry is an error, not a silent no-op."""
    with pytest.raises(ValueError, match="found 0"):
        set_version('{"domain": "kleverkey"}', "1.2.3")


@pytest.mark.parametrize("version", ["1.2.3", "0.1.0", "2.0.0b1", "1.2.3-rc.1"])
def test_accepts_valid_versions(tmp_path: pathlib.Path, version: str) -> None:
    """Release and pre-release versions are written."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(MANIFEST)

    assert main([version, "--manifest", str(manifest)]) == 0
    assert json.loads(manifest.read_text())["version"] == version


@pytest.mark.parametrize("version", ["v1.2.3", "1.2", "", "not-a-version"])
def test_rejects_invalid_versions(tmp_path: pathlib.Path, version: str) -> None:
    """A malformed version fails instead of writing nonsense to the manifest."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(MANIFEST)

    assert main([version, "--manifest", str(manifest)]) == 2
    assert manifest.read_text() == MANIFEST


def test_is_idempotent(tmp_path: pathlib.Path) -> None:
    """Re-running with the current version leaves the file alone."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(MANIFEST)

    assert main(["0.1.0", "--manifest", str(manifest)]) == 0
    assert manifest.read_text() == MANIFEST


def test_updates_the_real_manifest(tmp_path: pathlib.Path) -> None:
    """The helper works against the manifest actually shipped."""
    source = pathlib.Path("custom_components/kleverkey/manifest.json")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(source.read_text())

    assert main(["9.9.9", "--manifest", str(manifest)]) == 0

    updated = json.loads(manifest.read_text())
    original = json.loads(source.read_text())
    assert updated["version"] == "9.9.9"
    assert list(updated) == list(original)
    assert {k: v for k, v in updated.items() if k != "version"} == {
        k: v for k, v in original.items() if k != "version"
    }
