# SkillFortify

> Formal analysis and supply chain security for agentic AI skills.

[![PyPI version](https://img.shields.io/pypi/v/skillfortify.svg)](https://pypi.org/project/skillfortify/)
[![Tests](https://img.shields.io/github/actions/workflow/status/varun369/skillfortify/ci.yml?label=tests)](https://github.com/varun369/skillfortify/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

---

## The Problem

In January 2026, the ClawHavoc campaign infiltrated 1,200+ malicious skills into agent marketplaces. A month later, researchers catalogued 6,487 malicious agent tools -- and showed that conventional virus scanners miss the vast majority of them. CVE-2026-25253 demonstrated remote code execution through a single compromised skill.

Every existing defense tool relies on heuristic pattern matching: YARA rules, LLM-as-judge scoring, or regex-based scanning. They are better than nothing, but they share a fundamental limitation: **absence of findings does not mean absence of risk.** A sophisticated attacker can evade every heuristic scanner on the market today.

SkillFortify takes a different approach. Instead of guessing whether a skill is safe, SkillFortify formally analyzes skill safety using sound static analysis -- if SkillFortify reports no violations, the capability bounds in the formal model are assured. Using formal verification techniques adapted from supply chain security research, SkillFortify constructs a mathematical model of what each skill can and cannot do -- and verifies that model against declared capabilities. Zero false positives on the benchmark suite. The same rigor that protects critical infrastructure, applied to the agent skill ecosystem.

---

## Quick Start

```bash
pip install skillfortify
```

Scan your agent project for security issues:

```bash
skillfortify scan ./my-agent-project
```

```
┌─────────────────────────────────────────────────────────────────┐
│                      SkillFortify Scan Results                        │
├──────────────────────┬────────┬────────┬──────────┬─────────────┤
│ Skill                │ Format │ Status │ Findings │ Max Severity│
├──────────────────────┼────────┼────────┼──────────┼─────────────┤
│ deploy-automation    │ -      │  SAFE  │        0 │ -           │
│ data-export          │ -      │ UNSAFE │        2 │ HIGH        │
│ weather-lookup       │ -      │  SAFE  │        0 │ -           │
└──────────────────────┴────────┴────────┴──────────┴─────────────┘
3 skills scanned | 2 safe | 1 unsafe | 2 total findings
```

---

## What SkillFortify Does

### `skillfortify scan <path>` -- Discover and analyze skills

Auto-detects all agent skills in your project directory across supported formats. Runs formal static analysis and reports security findings ranked by severity.

```bash
skillfortify scan . --format json              # Machine-readable output
skillfortify scan . --severity-threshold high  # Only show HIGH and CRITICAL
```

### `skillfortify verify <skill>` -- Formal verification of a single skill

Deep analysis of one skill file with full capability inference, including POLA (Principle of Least Authority) compliance checks.

```bash
skillfortify verify .claude/skills/deploy.md
```

```
┌───────────────────────────────────────────────────────┐
│ Skill: deploy-automation   Status: SAFE               │
├───────────────────────────────────────────────────────┤
│                  Inferred Capabilities                 │
├───────────────────────┬───────────────────────────────┤
│ Resource              │ Access Level                  │
├───────────────────────┼───────────────────────────────┤
│ filesystem            │ READ                          │
│ network               │ READ                          │
└───────────────────────┴───────────────────────────────┘
No findings. Skill passed all checks.
```

### `skillfortify lock <path>` -- Generate skill-lock.json

Creates a deterministic lockfile pinning every skill to its exact version and content hash. Guarantees reproducible agent configurations across environments -- the same way package lockfiles work for traditional dependencies.

```bash
skillfortify lock ./my-agent-project
skillfortify lock ./my-agent-project -o custom-lock.json
```

### `skillfortify trust <skill>` -- Trust score computation

Computes a multi-signal trust score combining provenance, behavioral analysis, community signals, and historical record. Maps to graduated trust levels inspired by the SLSA framework.

```bash
skillfortify trust .claude/skills/deploy.md
```

```
┌───────────────────────────────────────────────────────┐
│ Skill: deploy-automation   Version: 1.0.0             │
├───────────────────────────────────────────────────────┤
│   Intrinsic Score: 0.750                              │
│   Effective Score: 0.750                              │
│   Trust Level:     FORMALLY_VERIFIED                  │
├───────────────────────────────────────────────────────┤
│                   Signal Breakdown                     │
├───────────────────────┬───────────────────────────────┤
│ Provenance            │ 0.500                         │
│ Behavioral            │ 1.000                         │
│ Community             │ 0.500                         │
│ Historical            │ 0.500                         │
└───────────────────────┴───────────────────────────────┘
```

### `skillfortify sbom <path>` -- CycloneDX ASBOM generation

Generates a CycloneDX 1.6 Agent Skill Bill of Materials (ASBOM) for compliance reporting and audit trails. Includes skill inventory, capability declarations, trust scores, and security findings.

```bash
skillfortify sbom ./my-agent-project
skillfortify sbom ./my-agent-project --project-name "prod-agent" --project-version "2.1.0"
```

---

## How It's Different

| Feature | SkillFortify | Heuristic Scanners |
|---------|--------|--------------------|
| **Verification approach** | Formal static analysis with sound capability model | Pattern matching, YARA rules, LLM judges |
| **False positive rate** | 0% on benchmark suite | Variable, often high |
| **Guarantee semantics** | Formal bounds on skill capabilities | "No findings" != "no risk" |
| **Dependency resolution** | Constraint-based resolution | Not available |
| **Lockfile generation** | Deterministic `skill-lock.json` | Not available |
| **Trust scoring** | Multi-signal algebraic model | Not available |
| **SBOM generation** | CycloneDX 1.6 ASBOM | Not available |
| **Capability inference** | Formal capability model | Ad-hoc |
| **Reproducible configs** | Integrity-verified lockfiles | Not available |

---

## Supported Formats

SkillFortify auto-detects and analyzes skills across six major agent frameworks:

| Format | Detected From | Skill Location |
|--------|---------------|----------------|
| **Claude Code Skills** | `.claude/` directory | `.claude/skills/*.md` |
| **MCP Servers** | `mcp.json` or `mcp_config.json` | Server configurations |
| **OpenClaw Skills** | `.claw/` directory | `.claw/**/*` |
| **LangChain Tools** | `langchain` imports in `.py` | `BaseTool` subclasses, `@tool` decorators |
| **CrewAI Tools** | `crew.yaml` or `crewai` imports | Crew definitions + tool classes |
| **AutoGen Tools** | `autogen` imports in `.py` | `register_for_llm` decorators, function schemas |

All formats are parsed into a unified representation for consistent analysis, trust scoring, and SBOM generation.

---

## Benchmark Results

Evaluated on SkillFortifyBench -- a curated dataset of 540 agent skills (clean and malicious samples sourced from documented real-world incidents):

| Metric | Value |
|--------|-------|
| Precision | **100%** (zero false positives) |
| Recall | 94.12% |
| F1 Score | **96.95%** |
| Average scan time | 2.55 ms per skill |

Zero false positives on the benchmark suite means SkillFortify did not flag any safe skill as malicious across 540 test cases. When it reports a skill as unsafe, that finding is backed by formal analysis of the skill's capability bounds, not a heuristic guess.

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

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install SkillFortify
        run: pip install skillfortify

      - name: Scan agent skills
        run: skillfortify scan . --format json

      - name: Verify lockfile integrity
        run: skillfortify lock . --output /tmp/fresh-lock.json
```

### Exit Codes

All SkillFortify commands use consistent exit codes for CI/CD integration:

| Code | Meaning |
|------|---------|
| `0` | Success -- all checks passed |
| `1` | Findings detected -- one or more skills have security issues |
| `2` | No skills found or parse error |

---

## Trust Levels

SkillFortify assigns graduated trust levels to every skill, inspired by the SLSA framework for software supply chain integrity:

| Level | Threshold | Meaning |
|-------|-----------|---------|
| **FORMALLY_VERIFIED** | >= 0.75 | Highest assurance. Formal analysis passed, strong provenance, active community trust |
| **COMMUNITY_VERIFIED** | >= 0.50 | Multiple positive signals. Community reviewed, usage history, basic behavioral checks |
| **SIGNED** | >= 0.25 | Basic provenance established. Author signed, but limited community verification |
| **UNSIGNED** | < 0.25 | No verification. Treat with extreme caution |

---

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Installation, first scan, and walkthrough |
| [CLI Reference](docs/commands.md) | Complete command documentation |
| [Lockfile Format](docs/skill-lock-json.md) | `skill-lock.json` specification |
| [ASBOM Output](docs/asbom.md) | CycloneDX ASBOM format and compliance |

---

## Requirements

- Python 3.11 or later
- No external services required -- SkillFortify runs entirely offline
- Works on Linux, macOS, and Windows

---

## Academic Paper

**"Formal Analysis and Supply Chain Security for Agentic AI Skills"**

SkillFortify is backed by peer-reviewed research with five formal theorems and full proofs, formalizing the agent skill supply chain threat model, capability verification, trust algebra, and dependency resolution.

**[Read the paper on Zenodo →](https://doi.org/10.5281/zenodo.18787663)** | DOI: 10.5281/zenodo.18787663

Part of the **AgentAssert** suite — building the formal foundations for trustworthy AI agents.

---

## Author

**Varun Pratap Bhardwaj** — Solution Architect with 15+ years in enterprise technology. Dual qualifications in technology and law (LL.B.), with a focus on formal methods for AI safety and regulatory compliance for autonomous systems.

- **Research:** Formal methods for AI agent safety, behavioral contracts, supply chain security
- **Prior work:** [AgentAssert](https://zenodo.org/records/18775393) (design-by-contract for AI agents), SuperLocalMemory (privacy-preserving agent memory)
- **Contact:** varun.pratap.bhardwaj@gmail.com
- **ORCID:** [0009-0002-8726-4289](https://orcid.org/0009-0002-8726-4289)

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Citation

If you use SkillFortify in your research, please cite:

```bibtex
@software{bhardwaj2026skillfortify,
  author    = {Bhardwaj, Varun Pratap},
  title     = {SkillFortify: Formal Analysis and Supply Chain Security for Agentic AI Skills},
  year      = {2026},
  doi       = {10.5281/zenodo.18787663},
  publisher = {Zenodo},
  url       = {https://doi.org/10.5281/zenodo.18787663}
}
```
