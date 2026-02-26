"""Tests for lockfile serialization and deserialization.

Validates ``to_dict``, ``to_json``, ``write`` (serialization),
``from_dict``, ``from_json``, ``read`` (deserialization), and full
round-trip fidelity through JSON and disk I/O.
"""

from __future__ import annotations

import json
from pathlib import Path

from skillfortify.core.lockfile import Lockfile, LockfileMetadata

from .conftest import make_locked_skill, make_lockfile_with_skills


# ===========================================================================
# Serialization: to_dict, to_json, write
# ===========================================================================


class TestSerialization:
    """Validate lockfile serialization to dict, JSON, and file."""

    def test_to_dict_structure(self) -> None:
        """to_dict produces a dict with all required top-level keys."""
        skill = make_locked_skill(name="alpha", version="1.0.0")
        lf = make_lockfile_with_skills(skill)
        d = lf.to_dict()

        assert d["lockfile_version"] == "1.0"
        assert d["generated_by"] == "skillfortify"
        assert "generated_at" in d
        assert d["integrity_algorithm"] == "sha256"
        assert "alpha" in d["skills"]
        assert d["metadata"]["total_skills"] == 1
        assert d["metadata"]["resolution_strategy"] == "sat"

    def test_to_dict_skill_entry_fields(self) -> None:
        """Serialized skill entry contains all expected fields."""
        skill = make_locked_skill(
            name="bravo",
            version="2.0.0",
            capabilities=["network:WRITE"],
            dependencies={"dep-a": "1.0.0"},
            trust_score=0.9,
            trust_level="FORMALLY_VERIFIED",
            source_path="/tmp/bravo",
        )
        lf = make_lockfile_with_skills(skill)
        entry = lf.to_dict()["skills"]["bravo"]

        assert entry["version"] == "2.0.0"
        assert entry["integrity"].startswith("sha256:")
        assert entry["capabilities"] == ["network:WRITE"]
        assert entry["dependencies"] == {"dep-a": "1.0.0"}
        assert entry["trust_score"] == 0.9
        assert entry["trust_level"] == "FORMALLY_VERIFIED"
        assert entry["source_path"] == "/tmp/bravo"

    def test_to_json_is_valid_json(self) -> None:
        """to_json produces valid JSON that can be parsed back."""
        lf = make_lockfile_with_skills(make_locked_skill(name="x"))
        json_str = lf.to_json()
        parsed = json.loads(json_str)
        assert parsed["lockfile_version"] == "1.0"
        assert "x" in parsed["skills"]

    def test_write_creates_file(self, tmp_path: Path) -> None:
        """write() creates a valid JSON file on disk."""
        lf = make_lockfile_with_skills(make_locked_skill(name="disk-skill"))
        lockfile_path = tmp_path / "skill-lock.json"
        lf.write(lockfile_path)

        assert lockfile_path.exists()
        data = json.loads(lockfile_path.read_text())
        assert "disk-skill" in data["skills"]


# ===========================================================================
# Deserialization: from_dict, from_json, read
# ===========================================================================


class TestDeserialization:
    """Validate lockfile deserialization from dict, JSON, and file."""

    def test_from_dict_basic(self) -> None:
        """from_dict reconstructs a lockfile from a minimal dict."""
        data = {
            "lockfile_version": "1.0",
            "skills": {
                "alpha": {
                    "version": "1.0.0",
                    "integrity": "sha256:" + "a" * 64,
                    "format": "mcp",
                    "capabilities": ["network:READ"],
                    "dependencies": {},
                }
            },
            "metadata": {
                "total_skills": 1,
                "resolution_strategy": "sat",
            },
        }
        lf = Lockfile.from_dict(data)
        assert lf.skill_count == 1
        skill = lf.get_skill("alpha")
        assert skill is not None
        assert skill.version == "1.0.0"
        assert skill.capabilities == ["network:READ"]

    def test_from_dict_with_trust(self) -> None:
        """from_dict correctly parses trust_score and trust_level fields."""
        data = {
            "skills": {
                "s1": {
                    "version": "1.0.0",
                    "integrity": "sha256:" + "b" * 64,
                    "format": "claude",
                    "capabilities": [],
                    "dependencies": {},
                    "trust_score": 0.65,
                    "trust_level": "COMMUNITY_VERIFIED",
                }
            },
            "metadata": {"total_skills": 1},
        }
        lf = Lockfile.from_dict(data)
        skill = lf.get_skill("s1")
        assert skill.trust_score == 0.65
        assert skill.trust_level == "COMMUNITY_VERIFIED"

    def test_from_json_parses_correctly(self) -> None:
        """from_json round-trips through JSON string correctly."""
        lf_orig = make_lockfile_with_skills(
            make_locked_skill(name="skill-a", version="3.0.0"),
        )
        json_str = lf_orig.to_json()
        lf_restored = Lockfile.from_json(json_str)
        assert lf_restored.skill_count == 1
        assert lf_restored.get_skill("skill-a").version == "3.0.0"

    def test_read_from_disk(self, tmp_path: Path) -> None:
        """read() loads a lockfile from a JSON file on disk."""
        lf_orig = make_lockfile_with_skills(
            make_locked_skill(name="file-skill", version="0.5.0"),
        )
        lockfile_path = tmp_path / "skill-lock.json"
        lf_orig.write(lockfile_path)

        lf_read = Lockfile.read(lockfile_path)
        assert lf_read.skill_count == 1
        assert lf_read.get_skill("file-skill").version == "0.5.0"


# ===========================================================================
# Round-trip: serialize -> deserialize -> compare
# ===========================================================================


class TestRoundTrip:
    """Validate that serialize -> deserialize preserves all data."""

    def test_round_trip_preserves_skills(self) -> None:
        """All skill fields survive a dict round-trip."""
        skill = make_locked_skill(
            name="round-trip-skill",
            version="4.2.1",
            fmt="openclaw",
            capabilities=["filesystem:WRITE", "network:READ"],
            dependencies={"lib-a": "1.0.0", "lib-b": "2.0.0"},
            trust_score=0.72,
            trust_level="COMMUNITY_VERIFIED",
            source_path="/skills/rt-skill",
        )
        lf_orig = make_lockfile_with_skills(skill)

        # Round-trip through JSON
        json_str = lf_orig.to_json()
        lf_restored = Lockfile.from_json(json_str)

        restored_skill = lf_restored.get_skill("round-trip-skill")
        assert restored_skill is not None
        assert restored_skill.version == "4.2.1"
        assert restored_skill.format == "openclaw"
        assert restored_skill.integrity == skill.integrity
        assert sorted(restored_skill.capabilities) == sorted(skill.capabilities)
        assert restored_skill.dependencies == skill.dependencies
        assert restored_skill.trust_score == 0.72
        assert restored_skill.trust_level == "COMMUNITY_VERIFIED"
        assert restored_skill.source_path == "/skills/rt-skill"

    def test_round_trip_via_disk(self, tmp_path: Path) -> None:
        """Write to disk and read back preserves all data."""
        lf_orig = make_lockfile_with_skills(
            make_locked_skill(name="a", version="1.0.0"),
            make_locked_skill(name="b", version="2.0.0"),
        )
        path = tmp_path / "skill-lock.json"
        lf_orig.write(path)
        lf_read = Lockfile.read(path)

        assert lf_read.skill_count == 2
        assert lf_read.skill_names == ["a", "b"]
        assert lf_read.get_skill("a").version == "1.0.0"
        assert lf_read.get_skill("b").version == "2.0.0"

    def test_round_trip_metadata(self) -> None:
        """Metadata fields survive round-trip."""
        lf_orig = make_lockfile_with_skills(
            make_locked_skill(name="s1"),
        )
        lf_orig.metadata = LockfileMetadata(
            total_skills=1,
            resolution_strategy="sat",
            allowed_capabilities=["filesystem:READ", "network:READ"],
        )
        json_str = lf_orig.to_json()
        lf_restored = Lockfile.from_json(json_str)

        assert lf_restored.metadata.resolution_strategy == "sat"
        assert sorted(lf_restored.metadata.allowed_capabilities) == [
            "filesystem:READ",
            "network:READ",
        ]
