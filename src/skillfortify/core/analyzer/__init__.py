"""Static Analyzer with Formal Guarantees for Agent Skill Supply Chain Security.

This package implements the primary detection engine of SkillShield. Given a
``ParsedSkill`` (the universal intermediate representation from any parser),
the ``StaticAnalyzer`` performs three analysis phases and returns an
``AnalysisResult`` containing all findings.

Three-Phase Analysis
--------------------

**Phase 1 -- Capability Inference (Abstract Interpretation):**
    From the parsed skill's extracted patterns (URLs, shell commands, env vars,
    file operations in instructions), the analyzer *infers* what capabilities
    the skill actually requires.

**Phase 2 -- Dangerous Pattern Detection:**
    A catalog of known-dangerous patterns (derived from the ClawHavoc campaign,
    MalTool benchmark, and "Agent Skills in the Wild" survey) is matched against
    the skill's shell commands, code blocks, URLs, and environment variable
    references.

**Phase 3 -- Capability Violation Check:**
    If the skill declares capabilities, the analyzer compares inferred
    capabilities against declared capabilities. Any inferred capability that
    *exceeds* the declared set is a violation.

Submodules
----------
- ``models``: Data types (Severity, Finding, AnalysisResult).
- ``patterns``: Compiled regex catalogs and helper functions.
- ``engine``: The StaticAnalyzer class.

All public names are re-exported here for backward compatibility::

    from skillfortify.core.analyzer import StaticAnalyzer, AnalysisResult, Finding, Severity
"""

from skillfortify.core.analyzer.models import AnalysisResult, Finding, Severity
from skillfortify.core.analyzer.engine import StaticAnalyzer

__all__ = [
    "AnalysisResult",
    "Finding",
    "Severity",
    "StaticAnalyzer",
]
