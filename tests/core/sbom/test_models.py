"""Tests for ASBOM data models: SkillComponent, purl, and CycloneDX component dicts."""

from __future__ import annotations

from skillfortify.core.sbom import SkillComponent


# =========================================================================
# 1. SkillComponent creation and purl generation
# =========================================================================


class TestSkillComponent:
    """SkillComponent dataclass and purl property."""

    def test_purl_basic(self) -> None:
        """purl follows pkg:agent-skill/<name>@<version> format."""
        comp = SkillComponent(name="weather-api", version="2.1.0", format="mcp")
        assert comp.purl == "pkg:agent-skill/weather-api@2.1.0"

    def test_purl_unknown_version(self) -> None:
        """purl works when version is 'unknown'."""
        comp = SkillComponent(name="my-skill", version="unknown", format="claude")
        assert comp.purl == "pkg:agent-skill/my-skill@unknown"

    def test_defaults(self) -> None:
        """Default values for optional fields."""
        comp = SkillComponent(name="s", version="0.1", format="openclaw")
        assert comp.is_safe is True
        assert comp.findings_count == 0
        assert comp.trust_score is None
        assert comp.trust_level is None
        assert comp.capabilities == []
        assert comp.dependencies == []
        assert comp.source_path == ""

    def test_cyclonedx_component_dict_structure(self) -> None:
        """to_cyclonedx_component produces required CycloneDX fields."""
        comp = SkillComponent(
            name="fs-tool",
            version="3.0.0",
            format="mcp",
            capabilities=["filesystem:READ", "network:WRITE"],
            is_safe=False,
            findings_count=2,
            trust_score=0.75,
            trust_level="COMMUNITY_VERIFIED",
            source_path="/tmp/skill",
        )
        d = comp.to_cyclonedx_component()

        assert d["type"] == "library"
        assert d["name"] == "fs-tool"
        assert d["version"] == "3.0.0"
        assert d["purl"] == "pkg:agent-skill/fs-tool@3.0.0"

        # Check properties list contains all expected keys
        prop_names = {p["name"] for p in d["properties"]}
        assert "skillfortify:format" in prop_names
        assert "skillfortify:is-safe" in prop_names
        assert "skillfortify:findings-count" in prop_names
        assert "skillfortify:capabilities" in prop_names
        assert "skillfortify:trust-score" in prop_names
        assert "skillfortify:trust-level" in prop_names
        assert "skillfortify:source-path" in prop_names


# =========================================================================
# 2. Edge cases for SkillComponent
# =========================================================================


class TestSkillComponentEdgeCases:
    """Edge cases: optional properties, dependency serialisation."""

    def test_optional_properties_omitted_when_none(self) -> None:
        """Properties for trust_score, trust_level, capabilities, source_path
        are omitted when not set."""
        comp = SkillComponent(name="minimal", version="0.1", format="mcp")
        d = comp.to_cyclonedx_component()
        prop_names = {p["name"] for p in d["properties"]}
        # Required: format, is-safe, findings-count
        assert "skillfortify:format" in prop_names
        assert "skillfortify:is-safe" in prop_names
        assert "skillfortify:findings-count" in prop_names
        # Optional should be absent
        assert "skillfortify:trust-score" not in prop_names
        assert "skillfortify:trust-level" not in prop_names
        assert "skillfortify:capabilities" not in prop_names
        assert "skillfortify:source-path" not in prop_names

    def test_dependency_with_deps(self) -> None:
        """Component with dependencies produces dependsOn array."""
        comp = SkillComponent(
            name="orchestrator",
            version="1.0.0",
            format="claude",
            dependencies=["helper-a", "helper-b"],
        )
        dep = comp.to_cyclonedx_dependency()
        assert dep["ref"] == "pkg:agent-skill/orchestrator@1.0.0"
        assert "pkg:agent-skill/helper-a@unknown" in dep["dependsOn"]
        assert "pkg:agent-skill/helper-b@unknown" in dep["dependsOn"]

    def test_dependency_without_deps(self) -> None:
        """Component without dependencies omits dependsOn key."""
        comp = SkillComponent(name="standalone", version="1.0.0", format="mcp")
        dep = comp.to_cyclonedx_dependency()
        assert dep["ref"] == "pkg:agent-skill/standalone@1.0.0"
        assert "dependsOn" not in dep
