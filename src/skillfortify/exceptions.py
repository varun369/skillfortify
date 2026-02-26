"""SkillFortify exception hierarchy.

All public exceptions inherit from SkillFortifyError, giving callers a single
base class to catch when they want to handle any SkillFortify-specific failure
without swallowing unrelated errors.
"""


class SkillFortifyError(Exception):
    """Base exception for all SkillFortify errors."""


class ParseError(SkillFortifyError):
    """Raised when a skill file cannot be parsed.

    Covers malformed skill definitions, unsupported formats, and
    encoding issues encountered during skill discovery and parsing.
    """


class AnalysisError(SkillFortifyError):
    """Raised when static analysis of a skill fails.

    Covers capability inference failures, pattern matching errors,
    and any issue in the formal analysis pipeline.
    """


class ResolutionError(SkillFortifyError):
    """Raised when dependency resolution fails.

    Covers unsatisfiable version constraints, circular dependencies,
    and conflicts that the constraint solver cannot resolve.
    """


class LockfileError(SkillFortifyError):
    """Raised for lockfile generation or integrity failures.

    Covers hash mismatches, corrupted lockfiles, and failures
    during lockfile creation or verification.
    """


class TrustError(SkillFortifyError):
    """Raised when trust score computation fails.

    Covers missing provenance data, invalid trust signals,
    and propagation failures in the trust graph.
    """


class SBOMError(SkillFortifyError):
    """Raised when SBOM generation fails.

    Covers serialization errors, schema validation failures,
    and issues producing CycloneDX output.
    """
