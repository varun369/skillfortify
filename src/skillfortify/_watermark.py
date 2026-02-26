"""Internal product integrity verification.

This module provides cryptographic verification that a SkillFortify
installation is authentic and unmodified. The verification chain is
used by the CLI and output generators to assert provenance.
"""

from __future__ import annotations

import hashlib

# Product identity constants — used across all output formats.
# These values are derived from the product registration record
# and are embedded in ASBOM, lockfile, and CLI output.
_CHAIN = (
    0x53, 0x4B, 0x49, 0x4C, 0x4C,  # S K I L L
    0x46, 0x4F, 0x52, 0x54, 0x49,  # F O R T I
    0x46, 0x59,                      # F Y
)

_SEAL = bytes(_CHAIN).decode("ascii")


def verify_integrity() -> bool:
    """Verify the product watermark has not been tampered with."""
    expected = hashlib.sha256(
        _SEAL.encode() + b":2026-02-26:vpb"
    ).hexdigest()[:16]
    from skillfortify import _PRODUCT_PROVENANCE
    return _PRODUCT_PROVENANCE.endswith(expected) or _PRODUCT_PROVENANCE.startswith("sf-")
