"""Tests for lockfile edge cases.

Verifies:
    - Lockfile with skill referencing non-existent dependency (validation).
    - Lockfile with circular A->B->A dependencies (validation).
    - Very large lockfile (100 skills) serialization/deserialization.
    - Lockfile with all optional fields None (clean serialization).
    - from_resolution with failed resolution raises ValueError.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from skillfortify.core.lockfile import Lockfile, LockedSkill


class TestNonExistentDependencyValidation:
    """Validation catches skills referencing non-existent dependencies."""

    def test_missing_dependency_detected(self) -> None:
        """A skill depending on a non-existent skill produces a validation error."""
        lf = Lockfile()
        lf.add_skill(LockedSkill(
            name="consumer",
            version="1.0.0",
            integrity=Lockfile.compute_integrity("consumer content"),
            format="mcp",
            dependencies={"nonexistent-lib": "2.0.0"},
        ))
        errors = lf.validate()
        assert len(errors) >= 1
        assert any("nonexistent-lib" in e for e in errors)


class TestCircularDependencyValidation:
    """Validation catches circular dependency chains."""

    def test_direct_circular_a_b_a(self) -> None:
        """A->B->A circular dependency is detected by validation."""
        lf = Lockfile()
        lf.add_skill(LockedSkill(
            name="skill-a",
            version="1.0.0",
            integrity=Lockfile.compute_integrity("a"),
            format="mcp",
            dependencies={"skill-b": "1.0.0"},
        ))
        lf.add_skill(LockedSkill(
            name="skill-b",
            version="1.0.0",
            integrity=Lockfile.compute_integrity("b"),
            format="mcp",
            dependencies={"skill-a": "1.0.0"},
        ))
        errors = lf.validate()
        circular_errors = [e for e in errors if "ircular" in e]
        assert len(circular_errors) >= 1


class TestLargeLockfile:
    """Serialization/deserialization of large lockfiles."""

    def test_100_skills_round_trip(self) -> None:
        """A lockfile with 100 skills serializes and deserializes correctly."""
        lf = Lockfile()
        for i in range(100):
            name = f"skill-{i:03d}"
            lf.add_skill(LockedSkill(
                name=name,
                version=f"{i}.0.0",
                integrity=Lockfile.compute_integrity(f"content-{i}"),
                format="mcp",
                capabilities=["network:READ"],
                source_path=f"/tmp/skills/{name}",
            ))
        assert lf.skill_count == 100

        # Serialize to JSON.
        json_str = lf.to_json()
        assert len(json_str) > 0

        # Deserialize back.
        restored = Lockfile.from_json(json_str)
        assert restored.skill_count == 100

        # Validate restored lockfile.
        errors = restored.validate()
        assert len(errors) == 0

        # Spot-check a few skills.
        s0 = restored.get_skill("skill-000")
        assert s0 is not None
        assert s0.version == "0.0.0"

        s99 = restored.get_skill("skill-099")
        assert s99 is not None
        assert s99.version == "99.0.0"


class TestOptionalFieldsNone:
    """Serialization when all optional fields are None/empty."""

    def test_minimal_skill_serializes_cleanly(self) -> None:
        """A LockedSkill with None trust and empty capabilities serializes."""
        lf = Lockfile()
        lf.add_skill(LockedSkill(
            name="bare-skill",
            version="0.1.0",
            integrity=Lockfile.compute_integrity("bare"),
            format="claude",
            capabilities=[],
            dependencies={},
            trust_score=None,
            trust_level=None,
            source_path="",
        ))
        d = lf.to_dict()
        skill_entry = d["skills"]["bare-skill"]
        # Optional fields omitted when None/empty.
        assert "trust_score" not in skill_entry
        assert "trust_level" not in skill_entry
        assert "source_path" not in skill_entry


class TestFromResolutionFailure:
    """from_resolution raises ValueError on failed resolution."""

    def test_failed_resolution_raises(self) -> None:
        """Calling from_resolution with success=False raises ValueError."""

        @dataclass
        class FakeResolution:
            success: bool
            installed: dict = field(default_factory=dict)
            conflicts: list = field(default_factory=list)

        failed = FakeResolution(
            success=False,
            installed={},
            conflicts=["skill-a 1.0.0 conflicts with skill-b 2.0.0"],
        )
        with pytest.raises(ValueError, match="failed resolution"):
            Lockfile.from_resolution(failed)
