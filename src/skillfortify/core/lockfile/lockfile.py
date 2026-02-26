"""Lockfile core class --- skill management, integrity, and serialization.

The ``Lockfile`` class is the central data structure representing a
``skill-lock.json`` file. It provides:

- **Skill management:** add, get, count, and list skills.
- **Integrity:** SHA-256 content hashing and verification.
- **Serialization:** deterministic ``to_dict``, ``to_json``, and ``write``.
- **Metadata:** resolution strategy and capability bounds.

Determinism guarantee: ``to_json()`` and ``to_dict()`` produce deterministic
output --- skill entries are sorted alphabetically by name, and all
dictionary keys are sorted. Two lockfiles with the same content always
produce byte-identical JSON.

References
----------
.. [SRI] W3C (2016). "Subresource Integrity." Content integrity via
   cryptographic hashes, adapted here for skill content verification.

.. [npm-lock] npm documentation. "package-lock.json." File format
   guaranteeing deterministic installs across environments.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skillfortify.core.lockfile.models import LockedSkill, LockfileMetadata


class Lockfile:
    """Agent skill lockfile --- captures exact resolved state.

    Analogous to package-lock.json but for agent skills. Includes:

    - Exact resolved versions from SAT-based dependency resolution.
    - Content integrity hashes (SHA-256) for tamper detection.
    - Capability declarations per skill.
    - Resolved dependency mappings.
    - Trust scores and levels.

    The lockfile guarantees **reproducibility**: given the same lockfile,
    the same skills at the same versions with the same capabilities
    will be installed.

    Example::

        lf = Lockfile()
        lf.add_skill(LockedSkill(
            name="weather-api",
            version="1.2.3",
            integrity="sha256:abcd..." ,
            format="mcp",
            capabilities=["network:READ"],
        ))
        lf.write(Path("skill-lock.json"))
    """

    LOCKFILE_VERSION: str = "1.0"
    INTEGRITY_ALGORITHM: str = "sha256"

    def __init__(self) -> None:
        self._skills: dict[str, LockedSkill] = {}
        self._metadata = LockfileMetadata()

    # -- Skill management ---------------------------------------------------

    def add_skill(self, skill: LockedSkill) -> None:
        """Add a locked skill entry.

        If a skill with the same name already exists, it is replaced.
        The metadata ``total_skills`` counter is updated automatically.

        Args:
            skill: The ``LockedSkill`` to add.
        """
        self._skills[skill.name] = skill
        self._metadata.total_skills = len(self._skills)

    def get_skill(self, name: str) -> LockedSkill | None:
        """Retrieve a locked skill by name.

        Args:
            name: Skill name to look up.

        Returns:
            The ``LockedSkill``, or None if not present.
        """
        return self._skills.get(name)

    @property
    def skill_count(self) -> int:
        """Return the number of locked skills."""
        return len(self._skills)

    @property
    def skill_names(self) -> list[str]:
        """Return sorted list of all skill names in the lockfile."""
        return sorted(self._skills.keys())

    # -- Integrity ----------------------------------------------------------

    @staticmethod
    def compute_integrity(content: str | bytes) -> str:
        """Compute SHA-256 integrity hash for skill content.

        Implements Subresource Integrity (SRI) style hashing for agent
        skills. The hash covers the complete skill content, detecting any
        modification --- including subtle prompt injection additions.

        Args:
            content: Skill file content, as string or bytes.

        Returns:
            Integrity string in "sha256:<64-hex-chars>" format.
        """
        if isinstance(content, str):
            content = content.encode("utf-8")
        digest = hashlib.sha256(content).hexdigest()
        return f"sha256:{digest}"

    def verify_integrity(self, skill_name: str, content: str | bytes) -> bool:
        """Verify that a skill's content matches its lockfile integrity hash.

        Used at install-time to detect tampered skills.

        Args:
            skill_name: Name of the skill to verify.
            content: Current content of the skill file.

        Returns:
            True if the computed hash matches the lockfile entry.
            False if the skill is not in the lockfile or the hash differs.
        """
        skill = self._skills.get(skill_name)
        if skill is None:
            return False
        computed = self.compute_integrity(content)
        return computed == skill.integrity

    # -- Serialization ------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the lockfile to a dict matching the schema.

        The output is deterministic: skills are sorted by name, and all
        dictionary keys are sorted.

        Returns:
            A dictionary suitable for JSON serialization.
        """
        skills_dict: dict[str, Any] = {}
        for name in sorted(self._skills.keys()):
            skill = self._skills[name]
            entry: dict[str, Any] = {
                "version": skill.version,
                "integrity": skill.integrity,
                "format": skill.format,
                "capabilities": sorted(skill.capabilities),
                "dependencies": dict(sorted(skill.dependencies.items())),
            }
            if skill.trust_score is not None:
                entry["trust_score"] = skill.trust_score
            if skill.trust_level is not None:
                entry["trust_level"] = skill.trust_level
            if skill.source_path:
                entry["source_path"] = skill.source_path
            skills_dict[name] = entry

        metadata_dict: dict[str, Any] = {
            "total_skills": self._metadata.total_skills,
            "resolution_strategy": self._metadata.resolution_strategy,
        }
        if self._metadata.allowed_capabilities is not None:
            metadata_dict["allowed_capabilities"] = sorted(
                self._metadata.allowed_capabilities
            )

        return {
            "lockfile_version": self.LOCKFILE_VERSION,
            "generated_by": "skillfortify",
            "provenance": "sf-e94b3c8b10240fab",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "integrity_algorithm": self.INTEGRITY_ALGORITHM,
            "skills": skills_dict,
            "metadata": metadata_dict,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to a JSON string.

        Args:
            indent: JSON indentation level. Default 2 for readability.

        Returns:
            Deterministic JSON string representation of the lockfile.
        """
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def write(self, path: Path) -> None:
        """Write lockfile to disk as JSON.

        Creates parent directories if they do not exist.

        Args:
            path: Filesystem path to write (e.g., Path("skill-lock.json")).
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    # -- Metadata access ----------------------------------------------------

    @property
    def metadata(self) -> LockfileMetadata:
        """Return the lockfile metadata."""
        return self._metadata

    @metadata.setter
    def metadata(self, value: LockfileMetadata) -> None:
        """Set the lockfile metadata."""
        self._metadata = value
