# Roadmap -- SkillFortify Development Plan

This page tracks completed milestones and planned development.

---

## Completed Releases

### v0.1.0 -- Foundation (February 2026)

Established the formal foundations for agent skill supply chain security.

- Formal threat model (DY-Skill attacker model, 5 supply chain phases)
- Static analysis with capability inference
- Trust scoring with 4-signal algebra (L0 through L3)
- Lockfile generation (`skill-lock.json`)
- CycloneDX 1.6 ASBOM output
- 540-skill benchmark (96.95% F1, 100% precision)
- 5 CLI commands: scan, verify, lock, trust, sbom
- Support for 3 formats: Claude Code, MCP, OpenClaw
- 31-page research paper with 5 theorems

### v0.2.0 -- Expanded Coverage (February 2026)

Broadened format support and improved detection.

- 3 additional agent framework parsers
- Expanded benchmark with community samples
- CI/CD integration improvements
- Refactored codebase to enterprise-grade modularity

### v0.3.0 -- System Discovery and Dashboard (March 2026)

Transformed SkillFortify from a project scanner into a system-wide security tool.

- **22 agent frameworks supported** (up from 6)
- **System auto-discovery**: `skillfortify scan` with no arguments scans all AI tools
- **23 IDE profiles**: Claude Code, Cursor, VS Code, Windsurf, Gemini CLI, Cline, Continue, GitHub Copilot, n8n, Roo Code, Trae, Kiro, Kode, Jules, Junie, Codex CLI, and more
- **HTML Dashboard**: `skillfortify dashboard` generates standalone visual security reports
- **Framework listing**: `skillfortify frameworks` displays all supported frameworks
- **Registry scanning**: `skillfortify registry-scan` for MCP, PyPI, and npm marketplaces
- **1,818 tests** (up from 675)
- 9 CLI commands (up from 5)

---

## Planned

### v0.4 -- Advanced Detection

- **Install-time attack detection**: Typosquatting, dependency confusion, namespace squatting
- **Enhanced registry scanning**: Deeper analysis of remote marketplace entries
- **Policy engine**: Define organizational rules for skill approval (minimum trust levels, required capabilities, blocked patterns)

### v0.5 -- Runtime and IDE Integration

- **Runtime monitoring**: Capability enforcement during skill execution, not just at scan time
- **VS Code extension**: Inline verification as you edit skill files
- **Official GitHub Action**: `skillfortify/scan@v1` with pull request annotations

### v1.0 -- Enterprise Features (Vision)

- **Fleet dashboard**: Centralized visibility across all agent projects in an organization
- **Cryptographic skill signing**: Keyless signing protocol for skill authors
- **Advanced composition analysis**: Cross-skill interaction rules and policy enforcement
- **Integration with AgentAssert behavioral contracts**: Skills verified against agent-level specifications

---

## How to Contribute

SkillFortify is open source (MIT License). Contributions are welcome:

- **New framework parsers**: Add detection for frameworks not yet covered
- **Benchmark skills**: Contribute samples to SkillFortifyBench
- **Bug reports**: [github.com/varun369/skillfortify/issues](https://github.com/varun369/skillfortify/issues)
- **Documentation**: Improve wiki pages, add tutorials
- **Research**: Extend the formal model, propose new theorems

See [CONTRIBUTING.md](https://github.com/varun369/skillfortify/blob/main/CONTRIBUTING.md) for guidelines.

---

## Feature Requests

Open a discussion on [GitHub Discussions](https://github.com/varun369/skillfortify/discussions) or file a feature request as an issue. The roadmap is shaped by real developer needs.

---

*SkillFortify is part of the [AgentAssert](https://agentassert.com) research suite -- building formal foundations for trustworthy AI agents.*
