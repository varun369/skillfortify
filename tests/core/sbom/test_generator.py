"""Tests for ASBOMGenerator: JSON structure, summary, integration, and edge cases."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from skillfortify.core.sbom import ASBOMGenerator, ASBOMMetadata, SkillComponent

from .conftest import make_analysis, make_finding, make_skill


# =========================================================================
# 1. ASBOMGenerator basic operations
# =========================================================================


class TestASBOMGeneratorBasic:
    """Basic add_component, component_count, and summary."""

    def test_empty_generator(self) -> None:
        gen = ASBOMGenerator()
        assert gen.component_count == 0

    def test_add_single_component(self) -> None:
        gen = ASBOMGenerator()
        gen.add_component(SkillComponent(name="a", version="1.0", format="claude"))
        assert gen.component_count == 1

    def test_add_multiple_components(self) -> None:
        gen = ASBOMGenerator()
        for i in range(5):
            gen.add_component(
                SkillComponent(name=f"skill-{i}", version="1.0", format="mcp")
            )
        assert gen.component_count == 5

    def test_summary_counts(self) -> None:
        gen = ASBOMGenerator()
        gen.add_component(
            SkillComponent(name="safe-1", version="1.0", format="claude", is_safe=True)
        )
        gen.add_component(
            SkillComponent(
                name="unsafe-1", version="1.0", format="mcp",
                is_safe=False, findings_count=3,
            )
        )
        gen.add_component(
            SkillComponent(
                name="unsafe-2", version="2.0", format="openclaw",
                is_safe=False, findings_count=1,
            )
        )
        s = gen.summary()
        assert s["total"] == 3
        assert s["safe"] == 1
        assert s["unsafe"] == 2
        assert s["total_findings"] == 4
        assert s["formats"] == {"claude": 1, "mcp": 1, "openclaw": 1}

    def test_summary_trust_distribution(self) -> None:
        gen = ASBOMGenerator()
        gen.add_component(
            SkillComponent(name="a", version="1", format="mcp", trust_level="COMMUNITY_VERIFIED")
        )
        gen.add_component(
            SkillComponent(name="b", version="1", format="mcp", trust_level="COMMUNITY_VERIFIED")
        )
        gen.add_component(
            SkillComponent(name="c", version="1", format="mcp", trust_level="ORG_SIGNED")
        )
        gen.add_component(SkillComponent(name="d", version="1", format="mcp"))
        dist = gen.summary()["trust_distribution"]
        assert dist["COMMUNITY_VERIFIED"] == 2
        assert dist["ORG_SIGNED"] == 1
        assert dist["UNSCORED"] == 1


# =========================================================================
# 2. CycloneDX JSON structure validation
# =========================================================================


class TestCycloneDXStructure:
    """Validate top-level CycloneDX 1.6 required fields."""

    def _gen_with_one(self) -> dict:
        gen = ASBOMGenerator(
            metadata=ASBOMMetadata(
                project_name="my-agent", project_version="1.2.3",
                skillfortify_version="0.1.0",
                timestamp=datetime(2026, 2, 26, 12, 0, 0, tzinfo=timezone.utc),
            )
        )
        gen.add_component(SkillComponent(name="weather", version="1.0.0", format="mcp"))
        return gen.generate()

    def test_bom_format(self) -> None:
        assert self._gen_with_one()["bomFormat"] == "CycloneDX"

    def test_spec_version(self) -> None:
        assert self._gen_with_one()["specVersion"] == "1.6"

    def test_version_integer(self) -> None:
        assert self._gen_with_one()["version"] == 1

    def test_serial_number_format(self) -> None:
        bom = self._gen_with_one()
        assert bom["serialNumber"].startswith("urn:uuid:")
        assert len(bom["serialNumber"][len("urn:uuid:"):]) == 36

    def test_metadata_timestamp(self) -> None:
        assert "2026-02-26" in self._gen_with_one()["metadata"]["timestamp"]

    def test_metadata_tool_name(self) -> None:
        tools = self._gen_with_one()["metadata"]["tools"]["components"]
        assert len(tools) == 1
        assert tools[0]["name"] == "skillfortify"
        assert tools[0]["version"] == "0.1.0"

    def test_metadata_project_component(self) -> None:
        comp = self._gen_with_one()["metadata"]["component"]
        assert comp["type"] == "application"
        assert comp["name"] == "my-agent"
        assert comp["version"] == "1.2.3"

    def test_components_array(self) -> None:
        bom = self._gen_with_one()
        assert isinstance(bom["components"], list)
        assert len(bom["components"]) == 1
        assert bom["components"][0]["name"] == "weather"

    def test_dependencies_array(self) -> None:
        bom = self._gen_with_one()
        assert isinstance(bom["dependencies"], list)
        assert len(bom["dependencies"]) == 1
        assert bom["dependencies"][0]["ref"] == "pkg:agent-skill/weather@1.0.0"


# =========================================================================
# 3. add_from_parsed_skill integration
# =========================================================================


class TestAddFromParsedSkill:
    """Integration with ParsedSkill and AnalysisResult."""

    def test_from_safe_skill(self) -> None:
        gen = ASBOMGenerator()
        skill = make_skill(name="safe-skill", version="2.0.0", format="mcp")
        gen.add_from_parsed_skill(skill)
        assert gen.component_count == 1
        comp = gen.components[0]
        assert comp.name == "safe-skill"
        assert comp.is_safe is True
        assert comp.findings_count == 0

    def test_from_unsafe_skill_with_analysis(self) -> None:
        gen = ASBOMGenerator()
        skill = make_skill(name="bad-skill", version="0.1.0", format="openclaw")
        result = make_analysis(
            skill_name="bad-skill", is_safe=False,
            findings=[make_finding("bad-skill"), make_finding("bad-skill")],
        )
        gen.add_from_parsed_skill(skill, analysis_result=result)
        comp = gen.components[0]
        assert comp.is_safe is False
        assert comp.findings_count == 2

    def test_capabilities_propagated(self) -> None:
        gen = ASBOMGenerator()
        skill = make_skill(name="fs-skill", declared_capabilities=["filesystem:READ", "network:WRITE"])
        gen.add_from_parsed_skill(skill)
        assert gen.components[0].capabilities == ["filesystem:READ", "network:WRITE"]

    def test_trust_score_and_level(self) -> None:
        gen = ASBOMGenerator()
        skill = make_skill(name="trusted")
        gen.add_from_parsed_skill(skill, trust_score=0.92, trust_level="ORG_SIGNED")
        comp = gen.components[0]
        assert comp.trust_score == pytest.approx(0.92)
        assert comp.trust_level == "ORG_SIGNED"

    def test_dependencies_propagated(self) -> None:
        gen = ASBOMGenerator()
        skill = make_skill(name="depends-skill", dependencies=["auth-lib", "http-client"])
        gen.add_from_parsed_skill(skill)
        assert gen.components[0].dependencies == ["auth-lib", "http-client"]


# =========================================================================
# 4. Dependency relationships in output
# =========================================================================


class TestDependencies:
    """Dependency serialisation in CycloneDX output."""

    def test_component_with_dependencies(self) -> None:
        gen = ASBOMGenerator()
        gen.add_component(SkillComponent(
            name="orchestrator", version="1.0.0", format="claude",
            dependencies=["helper-a", "helper-b"],
        ))
        dep = gen.generate()["dependencies"][0]
        assert dep["ref"] == "pkg:agent-skill/orchestrator@1.0.0"
        assert "pkg:agent-skill/helper-a@unknown" in dep["dependsOn"]
        assert "pkg:agent-skill/helper-b@unknown" in dep["dependsOn"]

    def test_component_without_dependencies(self) -> None:
        gen = ASBOMGenerator()
        gen.add_component(SkillComponent(name="standalone", version="1.0.0", format="mcp"))
        dep = gen.generate()["dependencies"][0]
        assert dep["ref"] == "pkg:agent-skill/standalone@1.0.0"
        assert "dependsOn" not in dep

    def test_multiple_dependency_entries(self) -> None:
        gen = ASBOMGenerator()
        gen.add_component(SkillComponent(name="a", version="1.0", format="mcp", dependencies=["common"]))
        gen.add_component(SkillComponent(name="b", version="2.0", format="mcp", dependencies=["common"]))
        bom = gen.generate()
        assert len(bom["dependencies"]) == 2
        refs = {d["ref"] for d in bom["dependencies"]}
        assert "pkg:agent-skill/a@1.0" in refs
        assert "pkg:agent-skill/b@2.0" in refs


# =========================================================================
# 5. JSON serialisation and file writing
# =========================================================================


class TestJsonOutput:
    """JSON string output and file persistence."""

    def test_to_json_is_valid_json(self) -> None:
        gen = ASBOMGenerator()
        gen.add_component(SkillComponent(name="x", version="1.0", format="claude"))
        parsed = json.loads(gen.to_json())
        assert parsed["bomFormat"] == "CycloneDX"

    def test_write_json_creates_file(self, tmp_path: Path) -> None:
        gen = ASBOMGenerator()
        gen.add_component(SkillComponent(name="y", version="2.0", format="mcp"))
        out = tmp_path / "asbom.cdx.json"
        gen.write_json(out)
        assert out.exists()
        content = json.loads(out.read_text(encoding="utf-8"))
        assert content["bomFormat"] == "CycloneDX"
        assert len(content["components"]) == 1

    def test_write_json_creates_parent_dirs(self, tmp_path: Path) -> None:
        gen = ASBOMGenerator()
        gen.add_component(SkillComponent(name="z", version="1.0", format="openclaw"))
        nested = tmp_path / "a" / "b" / "c" / "asbom.cdx.json"
        gen.write_json(nested)
        assert nested.exists()


# =========================================================================
# 6. Edge cases
# =========================================================================


class TestEdgeCases:
    """Edge cases: empty ASBOM, duplicates, unique serial numbers."""

    def test_empty_asbom_generates_valid_json(self) -> None:
        bom = ASBOMGenerator().generate()
        assert bom["bomFormat"] == "CycloneDX"
        assert bom["components"] == []
        assert bom["dependencies"] == []

    def test_empty_summary(self) -> None:
        s = ASBOMGenerator().summary()
        assert s["total"] == 0
        assert s["safe"] == 0
        assert s["unsafe"] == 0
        assert s["total_findings"] == 0
        assert s["formats"] == {}
        assert s["trust_distribution"] == {}

    def test_duplicate_components_allowed(self) -> None:
        gen = ASBOMGenerator()
        gen.add_component(SkillComponent(name="dup", version="1.0", format="claude"))
        gen.add_component(SkillComponent(name="dup", version="1.0", format="claude"))
        assert gen.component_count == 2
        assert len(gen.generate()["components"]) == 2

    def test_unique_serial_numbers(self) -> None:
        gen = ASBOMGenerator()
        assert gen.generate()["serialNumber"] != gen.generate()["serialNumber"]

    def test_default_timestamp_is_utc(self) -> None:
        ts_str = ASBOMGenerator().generate()["metadata"]["timestamp"]
        assert "T" in ts_str
        dt = datetime.fromisoformat(ts_str)
        assert dt.tzinfo is not None
