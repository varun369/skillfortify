# SkillFortify

> Supply chain security scanner for AI agent skills -- supports 22 frameworks.

[![PyPI version](https://img.shields.io/pypi/v/skillfortify.svg)](https://pypi.org/project/skillfortify/)
[![Tests](https://img.shields.io/github/actions/workflow/status/varun369/skillfortify/ci.yml?label=tests)](https://github.com/varun369/skillfortify/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

---

## One Command. Every Framework.

```bash
pip install skillfortify
skillfortify scan                # Auto-discovers all AI tools on your system
skillfortify scan ./my-project   # Scan a specific project
skillfortify dashboard           # Generate HTML security report
```

SkillFortify formally analyzes agent skill safety using sound static analysis. If SkillFortify reports no violations, the capability bounds in the formal model are assured. Unlike heuristic scanners where absence of findings does not mean absence of risk, SkillFortify provides mathematically grounded security guarantees.

---

## Supported Frameworks (22)

| # | Framework | Detection |
|---|-----------|-----------|
| 1 | **Claude Code Skills** | `.claude/` directory |
| 2 | **MCP Servers** | `mcp.json`, `mcp_config.json`, deep server scan |
| 3 | **OpenClaw Skills** | `.claw/` directory |
| 4 | **LangChain Tools** | `langchain` imports, `BaseTool`, `@tool` |
| 5 | **CrewAI Tools** | `crew.yaml`, `crewai` imports |
| 6 | **AutoGen Tools** | `autogen` imports, `register_for_llm` |
| 7 | **OpenAI Agents SDK** | `openai-agents` configurations |
| 8 | **Google ADK** | `google-adk` configurations |
| 9 | **Dify** | Dify workflow and plugin definitions |
| 10 | **Composio** | Composio tool integrations |
| 11 | **Semantic Kernel** | Microsoft Semantic Kernel plugins |
| 12 | **LlamaIndex** | LlamaIndex tool abstractions |
| 13 | **n8n** | n8n workflow node definitions |
| 14 | **Flowise** | Flowise chatflow configurations |
| 15 | **Mastra** | Mastra agent tool definitions |
| 16 | **PydanticAI** | PydanticAI tool decorators |
| 17 | **Agno** | Agno agent configurations |
| 18 | **CAMEL-AI** | CAMEL-AI tool integrations |
| 19 | **MetaGPT** | MetaGPT action and tool definitions |
| 20 | **Haystack** | Haystack component definitions |
| 21 | **Anthropic Agent SDK** | Anthropic agent tool configurations |
| 22 | **Custom Skills** | User-defined skill manifests (YAML/JSON) |

All frameworks are parsed into a unified representation for consistent analysis, trust scoring, and SBOM generation.

---

## Quick Start

### Install

```bash
pip install skillfortify                 # Core scanner
pip install skillfortify[registry]       # + marketplace scanning
pip install skillfortify[all]            # Everything
```

### System-Wide Scan

Run `skillfortify scan` with no arguments to automatically discover every AI agent tool installed on your system -- Claude Code, Cursor, VS Code extensions, Windsurf, and more:

```bash
skillfortify scan
```

```
Discovering AI tools on this system...
  Found: Claude Code skills       (12 skills in ~/.claude/skills/)
  Found: MCP servers              (8 servers in ~/.cursor/mcp.json)
  Found: VS Code MCP configs      (3 servers in ~/.vscode/mcp.json)
  Found: Windsurf MCP configs     (2 servers)

Scanning 25 skills across 4 locations...

+----------------------+--------+-----------+----------+--------------+
|       Skill          | Source |  Status   | Findings | Max Severity |
+----------------------+--------+-----------+----------+--------------+
| deploy-automation    | Claude |   SAFE    |        0 | -            |
| data-export          | Claude |  UNSAFE   |        2 | HIGH         |
| postgres-server      | MCP    |   SAFE    |        0 | -            |
| file-manager         | MCP    |  WARNING  |        1 | MEDIUM       |
+----------------------+--------+-----------+----------+--------------+
25 skills scanned | 22 safe | 2 unsafe | 1 warning | 5 total findings
```

### Project Scan

```bash
skillfortify scan ./my-agent-project
skillfortify scan ./my-agent-project --format json
skillfortify scan ./my-agent-project --severity-threshold high
```

### HTML Dashboard

Generate a standalone HTML security report with interactive filtering, a capabilities matrix, and severity breakdown:

```bash
skillfortify dashboard
skillfortify dashboard --output security-report.html
```

Open the generated file in any browser -- no server or dependencies required.

---

## Features

- **Formal threat model (DY-Skill)** -- mathematically grounded attack taxonomy for the agent skill supply chain
- **Sound static analysis** -- formal capability verification, not heuristic pattern matching
- **Capability-based access control** -- POLA compliance checks for every skill
- **Agent Dependency Graph** -- constraint-based resolution with conflict detection
- **Lockfile generation** -- deterministic `skill-lock.json` for reproducible agent configurations
- **Trust score algebra** -- multi-signal trust with propagation through dependency chains
- **ASBOM generation** -- CycloneDX 1.6 Agent Skill Bill of Materials for compliance reporting
- **Registry scanning** -- scan MCP registries, PyPI, and npm for known vulnerabilities
- **HTML dashboard** -- standalone interactive security report
- **System auto-discovery** -- finds every AI tool on your machine automatically
- **22 framework support** -- broadest coverage of any agent security scanner

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `skillfortify scan [path]` | Discover and analyze skills. No path = system-wide scan |
| `skillfortify verify <skill>` | Deep formal verification of a single skill file |
| `skillfortify lock <path>` | Generate deterministic `skill-lock.json` lockfile |
| `skillfortify trust <skill>` | Compute multi-signal trust score with graduated levels |
| `skillfortify sbom <path>` | Generate CycloneDX 1.6 ASBOM for compliance |
| `skillfortify frameworks` | List all 22 supported frameworks and detection methods |
| `skillfortify dashboard` | Generate standalone HTML security report |
| `skillfortify registry-scan <source>` | Scan MCP, PyPI, or npm registries for threats |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All checks passed |
| `1` | Security findings detected |
| `2` | No skills found or parse error |

---

## Benchmark Results

Evaluated on SkillFortifyBench -- 540 agent skills (clean and malicious samples from documented real-world incidents):

| Metric | Value |
|--------|-------|
| Precision | **100%** (zero false positives) |
| Recall | 94.12% |
| F1 Score | **96.95%** |
| Average scan time | 2.55 ms per skill |

---

## Trust Levels

Graduated trust levels inspired by the SLSA framework:

| Level | Threshold | Meaning |
|-------|-----------|---------|
| **FORMALLY_VERIFIED** | >= 0.75 | Highest assurance. Formal analysis passed, strong provenance |
| **COMMUNITY_VERIFIED** | >= 0.50 | Community reviewed, usage history, behavioral checks passed |
| **SIGNED** | >= 0.25 | Basic provenance. Author signed, limited verification |
| **UNSIGNED** | < 0.25 | No verification. Treat with extreme caution |

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Skill Security Scan
on: [push, pull_request]

jobs:
  skillfortify-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install skillfortify
      - run: skillfortify scan . --format json
      - run: skillfortify lock . --output /tmp/fresh-lock.json
```

---

## Requirements

- Python 3.11 or later
- No external services required -- runs entirely offline
- Works on Linux, macOS, and Windows

---

## Academic Paper

**"Formal Analysis and Supply Chain Security for Agentic AI Skills"**

Backed by peer-reviewed research with five formal theorems and full proofs, formalizing the agent skill supply chain threat model, capability verification, trust algebra, and dependency resolution.

**[Read the paper on Zenodo](https://doi.org/10.5281/zenodo.18787663)** | DOI: 10.5281/zenodo.18787663

Part of the **AgentAssert** suite ([arXiv:2602.22302](https://arxiv.org/abs/2602.22302)) -- formal foundations for trustworthy AI agents.

---

## Contributing

Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, coding standards, and submission guidelines.

---

## Author

**Varun Pratap Bhardwaj** -- Solution Architect with 15+ years in enterprise technology. Dual qualifications in technology and law (LL.B.), with a focus on formal methods for AI safety.

- **ORCID:** [0009-0002-8726-4289](https://orcid.org/0009-0002-8726-4289)
- **Contact:** varun.pratap.bhardwaj@gmail.com

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Citation

```bibtex
@software{bhardwaj2026skillfortify,
  author    = {Bhardwaj, Varun Pratap},
  title     = {SkillFortify: Formal Analysis and Supply Chain Security
               for Agentic AI Skills},
  year      = {2026},
  doi       = {10.5281/zenodo.18787663},
  publisher = {Zenodo},
  url       = {https://doi.org/10.5281/zenodo.18787663}
}
```
