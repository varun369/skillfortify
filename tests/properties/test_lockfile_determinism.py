"""Property-based tests for lockfile determinism and round-trip fidelity.

Verifies that lockfile serialization is:
- Deterministic: same skills -> same JSON (modulo timestamp)
- Round-trip safe: to_json -> from_json preserves all data
- Integrity consistent: compute_integrity is deterministic
"""
from __future__ import annotations

import re

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from skillfortify.core.lockfile import Lockfile, LockedSkill


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

skill_names = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz-"),
    min_size=3,
    max_size=20,
).filter(lambda s: not s.startswith("-") and not s.endswith("-"))

versions = st.from_regex(r"[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2}", fullmatch=True)

formats = st.sampled_from(["claude", "mcp", "openclaw"])

capabilities = st.lists(
    st.sampled_from([
        "filesystem:READ", "filesystem:WRITE",
        "network:READ", "network:WRITE",
        "shell:WRITE", "environment:READ",
    ]),
    min_size=0,
    max_size=4,
    unique=True,
)


@st.composite
def locked_skill_strategy(draw: st.DrawFn) -> LockedSkill:
    """Generate a valid LockedSkill with realistic field values."""
    name = draw(skill_names)
    version = draw(versions)
    content = draw(st.text(min_size=10, max_size=200))
    integrity = Lockfile.compute_integrity(content)
    fmt = draw(formats)
    caps = draw(capabilities)
    score = draw(st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0, allow_nan=False)))

    return LockedSkill(
        name=name,
        version=version,
        integrity=integrity,
        format=fmt,
        capabilities=caps,
        trust_score=score,
    )


# ---------------------------------------------------------------------------
# Determinism: same skills -> same JSON (except timestamp)
# ---------------------------------------------------------------------------

_TIMESTAMP_RE = re.compile(r'"generated_at":\s*"[^"]*"')


def _strip_timestamp(json_str: str) -> str:
    """Remove the generated_at timestamp for comparison."""
    return _TIMESTAMP_RE.sub('"generated_at": "STRIPPED"', json_str)


class TestLockfileDeterminism:
    """Same lockfile contents produce byte-identical JSON output."""

    def test_same_skills_same_json(self) -> None:
        """Two lockfiles with identical skills produce identical JSON."""
        skills = [
            LockedSkill(
                name=f"skill-{i}", version="1.0.0",
                integrity=Lockfile.compute_integrity(f"content-{i}"),
                format="claude",
            )
            for i in range(5)
        ]

        lf1 = Lockfile()
        lf2 = Lockfile()
        for s in skills:
            lf1.add_skill(s)
            lf2.add_skill(s)

        json1 = _strip_timestamp(lf1.to_json())
        json2 = _strip_timestamp(lf2.to_json())
        assert json1 == json2

    def test_insertion_order_does_not_matter(self) -> None:
        """Skills added in different order produce the same JSON."""
        skills = [
            LockedSkill(
                name=name, version="1.0.0",
                integrity=Lockfile.compute_integrity(name),
                format="mcp",
            )
            for name in ["zulu", "alpha", "mike", "bravo"]
        ]

        lf_forward = Lockfile()
        for s in skills:
            lf_forward.add_skill(s)

        lf_reverse = Lockfile()
        for s in reversed(skills):
            lf_reverse.add_skill(s)

        json_fwd = _strip_timestamp(lf_forward.to_json())
        json_rev = _strip_timestamp(lf_reverse.to_json())
        assert json_fwd == json_rev

    @given(skill=locked_skill_strategy())
    @settings(max_examples=50)
    def test_single_skill_deterministic(self, skill: LockedSkill) -> None:
        """A single generated skill always produces deterministic output."""
        lf1 = Lockfile()
        lf1.add_skill(skill)

        lf2 = Lockfile()
        lf2.add_skill(skill)

        assert _strip_timestamp(lf1.to_json()) == _strip_timestamp(lf2.to_json())


# ---------------------------------------------------------------------------
# Round-trip: to_json -> from_json preserves data
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Serialization -> deserialization preserves all lockfile data."""

    def test_round_trip_preserves_skills(self) -> None:
        """Skill data survives a JSON round-trip."""
        lf = Lockfile()
        lf.add_skill(LockedSkill(
            name="round-trip",
            version="2.5.0",
            integrity=Lockfile.compute_integrity("content"),
            format="openclaw",
            capabilities=["network:READ", "filesystem:WRITE"],
            dependencies={"dep-a": "1.0.0"},
            trust_score=0.85,
            trust_level="FORMALLY_VERIFIED",
            source_path="/some/path",
        ))

        json_str = lf.to_json()
        restored = Lockfile.from_json(json_str)

        skill = restored.get_skill("round-trip")
        assert skill is not None
        assert skill.version == "2.5.0"
        assert skill.format == "openclaw"
        assert sorted(skill.capabilities) == ["filesystem:WRITE", "network:READ"]
        assert skill.dependencies == {"dep-a": "1.0.0"}
        assert skill.trust_score == 0.85
        assert skill.trust_level == "FORMALLY_VERIFIED"

    @given(skill=locked_skill_strategy())
    @settings(max_examples=50)
    def test_round_trip_preserves_generated_skills(
        self, skill: LockedSkill
    ) -> None:
        """Generated skills survive round-trip serialization."""
        lf = Lockfile()
        lf.add_skill(skill)

        json_str = lf.to_json()
        restored = Lockfile.from_json(json_str)

        restored_skill = restored.get_skill(skill.name)
        assert restored_skill is not None
        assert restored_skill.version == skill.version
        assert restored_skill.integrity == skill.integrity
        assert restored_skill.format == skill.format
        assert sorted(restored_skill.capabilities) == sorted(skill.capabilities)

    def test_round_trip_preserves_metadata(self) -> None:
        """Lockfile metadata survives round-trip."""
        lf = Lockfile()
        lf.add_skill(LockedSkill(
            name="meta-test", version="1.0.0",
            integrity="sha256:" + "a" * 64, format="claude",
        ))

        json_str = lf.to_json()
        restored = Lockfile.from_json(json_str)
        assert restored.skill_count == 1
        assert restored.metadata.total_skills == 1


# ---------------------------------------------------------------------------
# Integrity hash determinism
# ---------------------------------------------------------------------------


class TestIntegrityDeterminism:
    """compute_integrity is deterministic and consistent."""

    @given(content=st.text(min_size=1, max_size=1000))
    def test_same_content_same_hash(self, content: str) -> None:
        """Identical content always produces identical hash."""
        h1 = Lockfile.compute_integrity(content)
        h2 = Lockfile.compute_integrity(content)
        assert h1 == h2

    @given(content=st.text(min_size=1, max_size=1000))
    def test_hash_format(self, content: str) -> None:
        """Integrity hash matches sha256:<64 hex chars> format."""
        h = Lockfile.compute_integrity(content)
        assert re.match(r"^sha256:[0-9a-f]{64}$", h)

    @given(
        c1=st.text(min_size=1, max_size=500),
        c2=st.text(min_size=1, max_size=500),
    )
    def test_different_content_different_hash(
        self, c1: str, c2: str
    ) -> None:
        """Different content produces different hashes (collision resistance)."""
        assume(c1 != c2)
        h1 = Lockfile.compute_integrity(c1)
        h2 = Lockfile.compute_integrity(c2)
        assert h1 != h2
