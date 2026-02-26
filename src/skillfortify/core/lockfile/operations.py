"""Lockfile operations --- deserialization, validation, and diffing.

This module extends the ``Lockfile`` class (defined in ``lockfile.py``) with
classmethods and instance methods for:

- **Deserialization:** ``from_dict``, ``from_json``, ``read`` (disk).
- **Validation:** internal consistency checks (dependencies, hashes, DAG).
- **Diffing:** structured comparison of two lockfiles.

These are attached to the ``Lockfile`` class at import time (in
``__init__.py``) to keep each source file focused and under 300 lines
while presenting a single unified API to callers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skillfortify.core.lockfile.models import (
    LockedSkill,
    LockfileMetadata,
    _INTEGRITY_RE,
)


def _from_dict(cls: type, data: dict[str, Any]) -> Any:
    """Deserialize a lockfile from a dict (parsed JSON).

    Accepts the dict format produced by ``to_dict()``. Fields not
    present in the dict use default values, enabling forward
    compatibility with older lockfile versions.

    Args:
        data: Dictionary matching the lockfile schema.

    Returns:
        A new ``Lockfile`` instance populated from the dict.
    """
    lf = cls()

    skills_data = data.get("skills", {})
    for name, entry in skills_data.items():
        skill = LockedSkill(
            name=name,
            version=entry.get("version", ""),
            integrity=entry.get("integrity", ""),
            format=entry.get("format", ""),
            capabilities=list(entry.get("capabilities", [])),
            dependencies=dict(entry.get("dependencies", {})),
            trust_score=entry.get("trust_score"),
            trust_level=entry.get("trust_level"),
            source_path=entry.get("source_path", ""),
        )
        lf._skills[name] = skill

    meta = data.get("metadata", {})
    lf._metadata = LockfileMetadata(
        total_skills=meta.get("total_skills", len(lf._skills)),
        resolution_strategy=meta.get("resolution_strategy", "sat"),
        allowed_capabilities=meta.get("allowed_capabilities"),
    )

    return lf


def _from_json(cls: type, json_str: str) -> Any:
    """Deserialize from a JSON string.

    Args:
        json_str: JSON string matching the lockfile schema.

    Returns:
        A new ``Lockfile`` instance.

    Raises:
        json.JSONDecodeError: If the string is not valid JSON.
    """
    data = json.loads(json_str)
    return cls.from_dict(data)


def _read(cls: type, path: Path) -> Any:
    """Read a lockfile from disk.

    Args:
        path: Filesystem path to the lockfile.

    Returns:
        A new ``Lockfile`` instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    text = path.read_text(encoding="utf-8")
    return cls.from_json(text)


def _validate(self: Any) -> list[str]:
    """Validate the lockfile for internal consistency.

    Performs the following checks:

    1. **Dependency completeness:** Every dependency name referenced by
       a skill must itself exist as an entry in the lockfile.
    2. **No circular dependencies:** The dependency graph among locked
       skills must be a DAG (directed acyclic graph).
    3. **Integrity format:** Every integrity hash must match the
       pattern ``sha256:<64-hex-chars>``.
    4. **Metadata consistency:** The ``total_skills`` in metadata must
       match the actual number of skill entries.
    5. **Version non-empty:** Every skill must have a non-empty version.

    Returns:
        List of validation error messages. Empty means the lockfile is
        valid.
    """
    errors: list[str] = []

    # 1. Dependency completeness
    for name, skill in self._skills.items():
        for dep_name in skill.dependencies:
            if dep_name not in self._skills:
                errors.append(
                    f"Skill {name!r} depends on {dep_name!r} which is "
                    f"not in the lockfile"
                )

    # 2. Circular dependency detection (DFS-based cycle detection)
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {name: WHITE for name in self._skills}

    def _dfs(u: str) -> bool:
        """Return True if a cycle is found starting from u."""
        color[u] = GRAY
        skill = self._skills[u]
        for dep_name in skill.dependencies:
            if dep_name not in color:
                continue  # Already reported as missing dependency
            if color[dep_name] == GRAY:
                errors.append(
                    f"Circular dependency detected involving "
                    f"{u!r} and {dep_name!r}"
                )
                return True
            if color[dep_name] == WHITE:
                if _dfs(dep_name):
                    return True
        color[u] = BLACK
        return False

    for skill_name in self._skills:
        if color[skill_name] == WHITE:
            _dfs(skill_name)

    # 3. Integrity format
    for name, skill in self._skills.items():
        if skill.integrity and not _INTEGRITY_RE.match(skill.integrity):
            errors.append(
                f"Skill {name!r} has invalid integrity hash format: "
                f"{skill.integrity!r}"
            )

    # 4. Metadata consistency
    if self._metadata.total_skills != len(self._skills):
        errors.append(
            f"Metadata total_skills ({self._metadata.total_skills}) "
            f"does not match actual count ({len(self._skills)})"
        )

    # 5. Version non-empty
    for name, skill in self._skills.items():
        if not skill.version:
            errors.append(f"Skill {name!r} has empty version string")

    return errors


def _diff(self: Any, other: Any) -> dict[str, Any]:
    """Compare two lockfiles and return differences.

    Useful for security review workflows where lockfile changes must
    be approved before deployment.

    - **added**: Skills present in ``other`` but not in ``self``.
    - **removed**: Skills present in ``self`` but not in ``other``.
    - **changed**: Skills present in both but with different version,
      integrity, or capabilities.

    Args:
        other: The lockfile to compare against (typically the newer one).

    Returns:
        Dict with keys 'added', 'removed', 'changed'.
    """
    self_names = set(self._skills.keys())
    other_names = set(other._skills.keys())

    added = sorted(other_names - self_names)
    removed = sorted(self_names - other_names)

    changes: list[dict[str, Any]] = []
    for name in sorted(self_names & other_names):
        old = self._skills[name]
        new = other._skills[name]

        if old.version != new.version:
            changes.append({
                "name": name,
                "field": "version",
                "old": old.version,
                "new": new.version,
            })
        if old.integrity != new.integrity:
            changes.append({
                "name": name,
                "field": "integrity",
                "old": old.integrity,
                "new": new.integrity,
            })
        if sorted(old.capabilities) != sorted(new.capabilities):
            changes.append({
                "name": name,
                "field": "capabilities",
                "old": sorted(old.capabilities),
                "new": sorted(new.capabilities),
            })
        if old.trust_score != new.trust_score:
            changes.append({
                "name": name,
                "field": "trust_score",
                "old": old.trust_score,
                "new": new.trust_score,
            })

    return {
        "added": added,
        "removed": removed,
        "changed": changes,
    }
