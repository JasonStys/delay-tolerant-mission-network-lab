"""Frozen/source identity and owned-instance guards by Jason Stys.

Functions: fixtures and test_*; variables: isolated bundled metadata and nonce values.
Exact declarations: docs/CODE_INDEX.md. No user profiles, listeners or package downloads.
"""

import json
import sys

import pytest

from dtnlab import __version__
from dtnlab import package_info as identity
from dtnlab.server import make_server

METADATA = {
    "schema_version": 1,
    "name": "delay-tolerant-mission-network-lab",
    "version": __version__,
    "source_commit": "a" * 40,
    "source_dirty": False,
    "platform": "windows",
    "machine": "amd64",
}


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    """Model the packaged resource location without invoking source or real installed profiles."""
    module = tmp_path / "dtnlab/package_info.py"
    resource = module.parent / "resources/RELEASE.json"
    resource.parent.mkdir(parents=True)
    resource.write_text(json.dumps(METADATA))
    monkeypatch.setattr(identity, "__file__", str(module))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    return resource


def test_frozen_valid_identity_and_source_mode(frozen, monkeypatch):
    """Only frozen mode reads packaged metadata; ordinary source runs never borrow a release claim."""
    assert identity.package_info() == METADATA
    monkeypatch.setattr(sys, "frozen", False)
    assert identity.package_info() is None


@pytest.mark.parametrize(
    "key,value",
    [
        ("schema_version", 2),
        ("schema_version", True),
        ("name", "other"),
        ("version", "1.0.0"),
        ("source_commit", "short"),
        ("source_commit", None),
        ("source_dirty", 0),
        ("platform", "other"),
        ("machine", "../other"),
        ("machine", None),
    ],
)
def test_frozen_invalid_identity_never_falls_back_to_source(frozen, key, value):
    """Each wrong field remains a hard launch failure rather than silently labeling source mode."""
    data = {**METADATA, key: value}
    frozen.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="invalid"):
        identity.package_info()


def test_frozen_missing_oversized_and_wrong_shape_metadata(frozen):
    """Missing and corrupt bundle resources fail without reaching a local source tree."""
    frozen.unlink()
    with pytest.raises(ValueError, match="missing"):
        identity.package_info()
    frozen.write_text("x" * 4097)
    with pytest.raises(ValueError, match="missing"):
        identity.package_info()
    frozen.write_text("[]")
    with pytest.raises(ValueError, match="invalid"):
        identity.package_info()


def test_invalid_instance_marker_refused_before_binding(tmp_path, monkeypatch):
    """Owned native-smoke markers are bounded and do not cause listeners on invalid input."""
    monkeypatch.setenv("PORTABLE_SMOKE_NONCE", "invalid marker")
    with pytest.raises(ValueError, match="instance marker"):
        make_server(tmp_path)
