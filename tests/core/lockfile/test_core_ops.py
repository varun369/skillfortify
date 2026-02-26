"""Tests for Lockfile core operations: add/get, integrity, determinism.

Validates basic skill management (add, get, count, names), SHA-256
integrity hashing and verification, deterministic serialization ordering,
and empty-lockfile edge cases.
"""

from __future__ import annotations

import hashlib
import json

from skillfortify.core.lockfile import Lockfile

from .conftest import make_locked_skill, make_lockfile_with_skills


# ===========================================================================
# Integrity hash computation and verification
# ===========================================================================


class TestIntegrity:
    """Validate SHA-256 integrity hashing and verification."""

    def test_compute_integrity_string(self) -> None:
        """Integrity hash of a string matches manual SHA-256 computation."""
        content = "Hello, SkillShield!"
        expected = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert Lockfile.compute_integrity(content) == expected

    def test_compute_integrity_bytes(self) -> None:
        """Integrity hash of bytes matches manual SHA-256 computation."""
        content = b"\x00\x01\x02\xff"
        expected = "sha256:" + hashlib.sha256(content).hexdigest()
        assert Lockfile.compute_integrity(content) == expected

    def test_compute_integrity_empty_content(self) -> None:
        """Integrity hash of empty string produces a valid hash."""
        result = Lockfile.compute_integrity("")
        assert result.startswith("sha256:")
        assert len(result) == len("sha256:") + 64

    def test_verify_integrity_matching(self) -> None:
        """verify_integrity returns True when content matches the lockfile hash."""
        content = "exact skill content"
        skill = make_locked_skill(name="s1", content=content)
        lf = make_lockfile_with_skills(skill)
        assert lf.verify_integrity("s1", content) is True

    def test_verify_integrity_tampered(self) -> None:
        """verify_integrity returns False when content has been modified."""
        original = "original content"
        skill = make_locked_skill(name="s1", content=original)
        lf = make_lockfile_with_skills(skill)
        assert lf.verify_integrity("s1", "tampered content") is False

    def test_verify_integrity_unknown_skill(self) -> None:
        """verify_integrity returns False for a skill not in the lockfile."""
        lf = Lockfile()
        assert lf.verify_integrity("nonexistent", "anything") is False


# ===========================================================================
# Lockfile add/get/count operations
# ===========================================================================


class TestLockfileOperations:
    """Validate basic lockfile skill management."""

    def test_add_and_get_skill(self) -> None:
        """Adding a skill makes it retrievable by name."""
        skill = make_locked_skill(name="alpha")
        lf = Lockfile()
        lf.add_skill(skill)
        assert lf.get_skill("alpha") is skill

    def test_get_nonexistent_skill_returns_none(self) -> None:
        """Getting a skill that was never added returns None."""
        lf = Lockfile()
        assert lf.get_skill("missing") is None

    def test_skill_count_and_names(self) -> None:
        """skill_count and skill_names reflect all added skills."""
        lf = Lockfile()
        lf.add_skill(make_locked_skill(name="charlie"))
        lf.add_skill(make_locked_skill(name="alpha"))
        lf.add_skill(make_locked_skill(name="bravo"))
        assert lf.skill_count == 3
        assert lf.skill_names == ["alpha", "bravo", "charlie"]  # Sorted

    def test_add_skill_replaces_existing(self) -> None:
        """Adding a skill with a duplicate name replaces the previous entry."""
        lf = Lockfile()
        lf.add_skill(make_locked_skill(name="s1", version="1.0.0"))
        lf.add_skill(make_locked_skill(name="s1", version="2.0.0"))
        assert lf.skill_count == 1
        assert lf.get_skill("s1").version == "2.0.0"


# ===========================================================================
# Determinism
# ===========================================================================


class TestDeterminism:
    """Validate that lockfile serialization is deterministic."""

    def test_same_input_same_json_structure(self) -> None:
        """Two lockfiles with the same skills produce structurally identical JSON.

        We strip the generated_at timestamp since it naturally differs
        between calls, and verify the remaining structure is identical.
        """
        skills = [
            make_locked_skill(name="z-skill", version="3.0.0"),
            make_locked_skill(name="a-skill", version="1.0.0"),
            make_locked_skill(name="m-skill", version="2.0.0"),
        ]

        lf1 = Lockfile()
        lf2 = Lockfile()
        for s in skills:
            lf1.add_skill(s)
            lf2.add_skill(s)

        d1 = lf1.to_dict()
        d2 = lf2.to_dict()

        # Remove timestamp for comparison
        del d1["generated_at"]
        del d2["generated_at"]

        # Serialize to JSON for byte-level comparison
        json1 = json.dumps(d1, sort_keys=True)
        json2 = json.dumps(d2, sort_keys=True)
        assert json1 == json2

    def test_skill_ordering_is_alphabetical(self) -> None:
        """Skills in serialized output are ordered alphabetically by name."""
        lf = make_lockfile_with_skills(
            make_locked_skill(name="zebra"),
            make_locked_skill(name="alpha"),
            make_locked_skill(name="middle"),
        )
        d = lf.to_dict()
        skill_names = list(d["skills"].keys())
        assert skill_names == ["alpha", "middle", "zebra"]


# ===========================================================================
# Empty lockfile edge cases
# ===========================================================================


class TestEmptyLockfile:
    """Edge cases for empty lockfiles."""

    def test_empty_lockfile_to_dict(self) -> None:
        """An empty lockfile serializes without error."""
        lf = Lockfile()
        d = lf.to_dict()
        assert d["skills"] == {}
        assert d["metadata"]["total_skills"] == 0

    def test_empty_lockfile_validation(self) -> None:
        """An empty lockfile passes validation."""
        lf = Lockfile()
        assert lf.validate() == []
