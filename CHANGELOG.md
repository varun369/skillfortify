# Changelog

All notable changes to SkillFortify are documented here.

This project follows [Semantic Versioning](https://semver.org/).

## [0.3.0] - 2026-03-01

### Added
- Expanded framework support to cover all major agent ecosystems
- System-wide scan mode for comprehensive security assessment
- Interactive HTML security report with filtering and export
- New CLI commands for framework listing and report generation
- Marketplace security scanning capabilities

### Changed
- `skillfortify scan` now works without arguments for broader coverage

## [0.2.0] - 2026-02-26

### Added
- LangChain tools format support (BaseTool subclasses, @tool decorators)
- CrewAI tools format support (crew.yaml definitions, tool classes)
- AutoGen tools format support (register_for_llm, function schemas)
- Six agent frameworks now supported (up from three)
- 69 new parser tests (675 total)

## [0.1.0] - 2026-02-26

### Added
- Five CLI commands: scan, verify, lock, trust, sbom
- Formal threat model with capability-based analysis
- Constraint-based dependency resolution with lockfile generation
- Trust score computation with propagation through dependency chains
- CycloneDX 1.6 Agent Skill Bill of Materials (ASBOM) generation
- Support for Claude Code, MCP, and OpenClaw skill formats
- 562 automated tests with property-based verification
