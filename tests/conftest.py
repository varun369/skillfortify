"""Shared fixtures for skillfortify tests."""

import pathlib

import pytest


@pytest.fixture
def sample_skill_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create a temporary directory simulating a skill project."""
    skill_dir = tmp_path / "sample-skill"
    skill_dir.mkdir()
    return skill_dir


@pytest.fixture
def empty_manifest(sample_skill_dir: pathlib.Path) -> pathlib.Path:
    """Create a minimal skill manifest file."""
    manifest = sample_skill_dir / "manifest.yaml"
    manifest.write_text("name: test-skill\nversion: 0.1.0\n")
    return manifest
