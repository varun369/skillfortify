"""Agent Skill Lockfile --- Reproducible, Auditable Skill Installations.

This package implements the ``skill-lock.json`` lockfile format for agent
skill configurations. The lockfile captures the exact resolved state of an
agent's installed skills --- every skill at its resolved version, with
content integrity hashes, declared capabilities, resolved dependencies,
and trust metadata.

The package is split into focused submodules:

- ``models``: Data classes (``LockedSkill``, ``LockfileMetadata``) and the
  ``_score_to_level_str`` helper.
- ``lockfile``: The ``Lockfile`` class with skill management, integrity
  hashing, serialization, and metadata.
- ``operations``: Deserialization (``from_dict``, ``from_json``, ``read``),
  validation, and diffing.
- ``factory``: The ``from_resolution`` factory method for constructing
  lockfiles from SAT-based dependency resolution results.

All public names are re-exported here so that existing imports like
``from skillfortify.core.lockfile import Lockfile`` continue to work.
"""

# Re-export data models
from skillfortify.core.lockfile.models import (
    LockedSkill,
    LockfileMetadata,
    _INTEGRITY_RE,
    _score_to_level_str,
)

# Re-export the Lockfile class
from skillfortify.core.lockfile.lockfile import Lockfile

# Attach operations to Lockfile as methods/classmethods
from skillfortify.core.lockfile import operations as _ops
from skillfortify.core.lockfile import factory as _factory

Lockfile.from_dict = classmethod(_ops._from_dict)
Lockfile.from_json = classmethod(_ops._from_json)
Lockfile.read = classmethod(_ops._read)
Lockfile.validate = _ops._validate
Lockfile.diff = _ops._diff
Lockfile.from_resolution = classmethod(_factory._from_resolution)

__all__ = [
    "Lockfile",
    "LockedSkill",
    "LockfileMetadata",
    "_score_to_level_str",
    "_INTEGRITY_RE",
]
