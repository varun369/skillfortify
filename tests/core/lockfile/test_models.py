"""Tests for lockfile data models: LockedSkill, LockfileMetadata, trust levels.

Validates dataclass instantiation, default field isolation, and the
``_score_to_level_str`` helper that maps trust scores to SLSA-inspired
trust level strings.
"""

from __future__ import annotations

from skillfortify.core.lockfile import (
    Lockfile,
    LockedSkill,
    LockfileMetadata,
    _score_to_level_str,
)

from .conftest import make_locked_skill, make_lockfile_with_skills


# ===========================================================================
# LockedSkill creation
# ===========================================================================


class TestLockedSkillCreation:
    """Validate LockedSkill dataclass instantiation and defaults."""

    def test_minimal_locked_skill(self) -> None:
        """A LockedSkill with only required fields uses correct defaults."""
        skill = LockedSkill(
            name="alpha",
            version="0.1.0",
            integrity="sha256:" + "a" * 64,
            format="claude",
        )
        assert skill.name == "alpha"
        assert skill.version == "0.1.0"
        assert skill.format == "claude"
        assert skill.capabilities == []
        assert skill.dependencies == {}
        assert skill.trust_score is None
        assert skill.trust_level is None
        assert skill.source_path == ""

    def test_full_locked_skill(self) -> None:
        """A LockedSkill with all fields populated retains every value."""
        skill = LockedSkill(
            name="weather-api",
            version="2.1.0",
            integrity="sha256:" + "b" * 64,
            format="mcp",
            capabilities=["network:READ", "filesystem:READ"],
            dependencies={"http-client": "1.0.0"},
            trust_score=0.85,
            trust_level="FORMALLY_VERIFIED",
            source_path="/skills/weather-api/main.py",
        )
        assert skill.trust_score == 0.85
        assert skill.trust_level == "FORMALLY_VERIFIED"
        assert skill.dependencies == {"http-client": "1.0.0"}
        assert len(skill.capabilities) == 2

    def test_locked_skill_mutable_defaults_isolation(self) -> None:
        """Mutable default fields are independent across instances."""
        a = LockedSkill(name="a", version="1.0.0", integrity="sha256:" + "0" * 64, format="mcp")
        b = LockedSkill(name="b", version="1.0.0", integrity="sha256:" + "0" * 64, format="mcp")
        a.capabilities.append("network:WRITE")
        assert b.capabilities == []  # Must not be shared


# ===========================================================================
# Trust score to level mapping
# ===========================================================================


class TestScoreToLevel:
    """Validate _score_to_level_str boundary conditions."""

    def test_score_to_level_boundaries(self) -> None:
        """Trust score to level string mapping respects exact thresholds."""
        assert _score_to_level_str(0.0) == "UNSIGNED"
        assert _score_to_level_str(0.24) == "UNSIGNED"
        assert _score_to_level_str(0.25) == "SIGNED"
        assert _score_to_level_str(0.49) == "SIGNED"
        assert _score_to_level_str(0.50) == "COMMUNITY_VERIFIED"
        assert _score_to_level_str(0.74) == "COMMUNITY_VERIFIED"
        assert _score_to_level_str(0.75) == "FORMALLY_VERIFIED"
        assert _score_to_level_str(1.0) == "FORMALLY_VERIFIED"


# ===========================================================================
# Metadata edge cases
# ===========================================================================


class TestMetadataEdgeCases:
    """Validate LockfileMetadata serialization edge cases."""

    def test_lockfile_metadata_allowed_capabilities_none(self) -> None:
        """When allowed_capabilities is None, it is omitted from serialization."""
        lf = Lockfile()
        lf.add_skill(make_locked_skill(name="s1"))
        d = lf.to_dict()
        assert "allowed_capabilities" not in d["metadata"]

    def test_lockfile_metadata_allowed_capabilities_set(self) -> None:
        """When allowed_capabilities is set, it appears sorted in serialization."""
        lf = Lockfile()
        lf.add_skill(make_locked_skill(name="s1"))
        lf.metadata = LockfileMetadata(
            total_skills=1,
            allowed_capabilities=["network:READ", "filesystem:READ"],
        )
        d = lf.to_dict()
        assert d["metadata"]["allowed_capabilities"] == [
            "filesystem:READ",
            "network:READ",
        ]

    def test_optional_fields_omitted_in_serialization(self) -> None:
        """trust_score, trust_level, source_path are omitted when None/empty."""
        skill = LockedSkill(
            name="minimal",
            version="1.0.0",
            integrity=Lockfile.compute_integrity("x"),
            format="mcp",
        )
        lf = make_lockfile_with_skills(skill)
        entry = lf.to_dict()["skills"]["minimal"]
        assert "trust_score" not in entry
        assert "trust_level" not in entry
        assert "source_path" not in entry
