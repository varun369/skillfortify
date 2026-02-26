"""Tests for lockfile validation, diffing, and from_resolution factory.

Validates internal consistency checks (missing dependencies, cycles, hash
format, metadata count, empty versions), structured lockfile comparison
(diff), and the ``from_resolution`` factory method that constructs a
lockfile from SAT-based dependency resolution results.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from skillfortify.core.lockfile import Lockfile, LockedSkill

from .conftest import make_locked_skill, make_lockfile_with_skills


# ===========================================================================
# Validation
# ===========================================================================


class TestValidation:
    """Validate internal consistency checking."""

    def test_valid_lockfile_has_no_errors(self) -> None:
        """A correctly constructed lockfile passes validation."""
        dep_skill = make_locked_skill(name="dep-a", version="1.0.0")
        main_skill = make_locked_skill(
            name="main",
            version="2.0.0",
            dependencies={"dep-a": "1.0.0"},
        )
        lf = make_lockfile_with_skills(dep_skill, main_skill)
        errors = lf.validate()
        assert errors == []

    def test_missing_dependency_detected(self) -> None:
        """A skill referencing a dependency not in the lockfile produces an error."""
        skill = make_locked_skill(
            name="broken",
            version="1.0.0",
            dependencies={"ghost": "1.0.0"},
        )
        lf = make_lockfile_with_skills(skill)
        errors = lf.validate()
        assert any("ghost" in e and "not in the lockfile" in e for e in errors)

    def test_circular_dependency_detected(self) -> None:
        """Circular dependencies are detected and reported."""
        a = make_locked_skill(name="a", dependencies={"b": "1.0.0"})
        b = make_locked_skill(name="b", dependencies={"a": "1.0.0"})
        lf = make_lockfile_with_skills(a, b)
        errors = lf.validate()
        assert any("Circular dependency" in e for e in errors)

    def test_invalid_integrity_hash_format(self) -> None:
        """An integrity hash with wrong format is flagged."""
        skill = LockedSkill(
            name="bad-hash",
            version="1.0.0",
            integrity="md5:notagoodhash",
            format="mcp",
        )
        lf = make_lockfile_with_skills(skill)
        errors = lf.validate()
        assert any("invalid integrity hash" in e for e in errors)

    def test_metadata_count_mismatch(self) -> None:
        """A mismatch between metadata.total_skills and actual count is flagged."""
        skill = make_locked_skill(name="only-one")
        lf = make_lockfile_with_skills(skill)
        # Manually corrupt the metadata count
        lf._metadata.total_skills = 99
        errors = lf.validate()
        assert any("total_skills" in e for e in errors)

    def test_empty_version_detected(self) -> None:
        """A skill with an empty version string is flagged."""
        skill = LockedSkill(
            name="no-version",
            version="",
            integrity=Lockfile.compute_integrity("content"),
            format="mcp",
        )
        lf = make_lockfile_with_skills(skill)
        errors = lf.validate()
        assert any("empty version" in e for e in errors)


# ===========================================================================
# Diff between two lockfiles
# ===========================================================================


class TestDiff:
    """Validate lockfile comparison/diffing."""

    def test_diff_identical_lockfiles(self) -> None:
        """Diffing identical lockfiles produces no differences."""
        skill = make_locked_skill(name="same")
        lf1 = make_lockfile_with_skills(skill)
        lf2 = make_lockfile_with_skills(skill)
        result = lf1.diff(lf2)
        assert result["added"] == []
        assert result["removed"] == []
        assert result["changed"] == []

    def test_diff_detects_added_skill(self) -> None:
        """Diff detects skills present in other but not in self."""
        lf1 = make_lockfile_with_skills(make_locked_skill(name="a"))
        lf2 = make_lockfile_with_skills(
            make_locked_skill(name="a"),
            make_locked_skill(name="b"),
        )
        result = lf1.diff(lf2)
        assert result["added"] == ["b"]
        assert result["removed"] == []

    def test_diff_detects_removed_skill(self) -> None:
        """Diff detects skills present in self but not in other."""
        lf1 = make_lockfile_with_skills(
            make_locked_skill(name="a"),
            make_locked_skill(name="b"),
        )
        lf2 = make_lockfile_with_skills(make_locked_skill(name="a"))
        result = lf1.diff(lf2)
        assert result["removed"] == ["b"]
        assert result["added"] == []

    def test_diff_detects_version_change(self) -> None:
        """Diff detects when a skill's version changes between lockfiles."""
        lf1 = make_lockfile_with_skills(
            make_locked_skill(name="s1", version="1.0.0"),
        )
        lf2 = make_lockfile_with_skills(
            make_locked_skill(name="s1", version="2.0.0"),
        )
        result = lf1.diff(lf2)
        assert len(result["changed"]) >= 1
        version_changes = [c for c in result["changed"] if c["field"] == "version"]
        assert len(version_changes) == 1
        assert version_changes[0]["old"] == "1.0.0"
        assert version_changes[0]["new"] == "2.0.0"

    def test_diff_detects_capability_change(self) -> None:
        """Diff detects capability changes (security-critical)."""
        lf1 = make_lockfile_with_skills(
            make_locked_skill(name="s1", capabilities=["network:READ"]),
        )
        lf2 = make_lockfile_with_skills(
            make_locked_skill(name="s1", capabilities=["network:READ", "filesystem:WRITE"]),
        )
        result = lf1.diff(lf2)
        cap_changes = [c for c in result["changed"] if c["field"] == "capabilities"]
        assert len(cap_changes) == 1


# ===========================================================================
# from_resolution factory method
# ===========================================================================


class TestFromResolution:
    """Validate lockfile construction from Resolution results."""

    def test_from_resolution_basic(self) -> None:
        """from_resolution creates a lockfile from a simple resolution."""
        @dataclass
        class FakeResolution:
            success: bool = True
            installed: dict = field(default_factory=dict)
            conflicts: list = field(default_factory=list)

        resolution = FakeResolution(
            success=True,
            installed={"alpha": "1.0.0", "bravo": "2.1.0"},
        )
        lf = Lockfile.from_resolution(resolution)
        assert lf.skill_count == 2
        assert lf.get_skill("alpha").version == "1.0.0"
        assert lf.get_skill("bravo").version == "2.1.0"

    def test_from_resolution_failed_raises(self) -> None:
        """from_resolution raises ValueError for a failed resolution."""
        @dataclass
        class FakeResolution:
            success: bool = False
            installed: dict = field(default_factory=dict)
            conflicts: list = field(default_factory=list)

        resolution = FakeResolution(
            success=False,
            conflicts=["skill-x@1.0.0 conflicts with skill-y@2.0.0"],
        )
        with pytest.raises(ValueError, match="Cannot create lockfile from failed"):
            Lockfile.from_resolution(resolution)

    def test_from_resolution_with_trust_scores(self) -> None:
        """from_resolution populates trust_score and trust_level when provided."""
        @dataclass
        class FakeResolution:
            success: bool = True
            installed: dict = field(default_factory=dict)
            conflicts: list = field(default_factory=list)

        resolution = FakeResolution(
            success=True,
            installed={"s1": "1.0.0"},
        )
        trust_scores = {"s1": 0.85}
        lf = Lockfile.from_resolution(resolution, trust_scores=trust_scores)
        skill = lf.get_skill("s1")
        assert skill.trust_score == 0.85
        assert skill.trust_level == "FORMALLY_VERIFIED"

    def test_from_resolution_with_graph(self) -> None:
        """from_resolution extracts capabilities and dependencies from graph."""
        from skillfortify.core.dependency import (
            AgentDependencyGraph,
            SkillDependency,
            SkillNode,
            VersionConstraint,
        )

        graph = AgentDependencyGraph()
        graph.add_skill(SkillNode(
            name="main-skill",
            version="1.0.0",
            dependencies=[
                SkillDependency("helper", VersionConstraint(">=1.0.0")),
            ],
            capabilities={"network:READ", "filesystem:READ"},
        ))
        graph.add_skill(SkillNode(
            name="helper",
            version="1.2.0",
            capabilities={"network:READ"},
        ))

        @dataclass
        class FakeResolution:
            success: bool = True
            installed: dict = field(default_factory=dict)
            conflicts: list = field(default_factory=list)

        resolution = FakeResolution(
            success=True,
            installed={"main-skill": "1.0.0", "helper": "1.2.0"},
        )

        lf = Lockfile.from_resolution(resolution, graph=graph)
        main = lf.get_skill("main-skill")
        assert sorted(main.capabilities) == ["filesystem:READ", "network:READ"]
        assert main.dependencies == {"helper": "1.2.0"}

        helper = lf.get_skill("helper")
        assert helper.capabilities == ["network:READ"]
        assert helper.dependencies == {}
