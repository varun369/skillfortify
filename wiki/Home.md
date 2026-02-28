# SkillFortify -- Formal Verification for Agent Skill Supply Chains

**SkillFortify** is the first security tool that formally verifies what your AI agent skills can actually do -- instead of guessing with heuristic pattern matching. Grounded in five mathematical theorems with full proofs, SkillFortify provides soundness-guaranteed analysis across **22 agent frameworks** and **23 IDE configurations**. One command scans every AI tool on your system. Zero false positives on the benchmark suite. Open source under MIT License.

---

## Why SkillFortify Exists

In January 2026, the **ClawHavoc** campaign infiltrated 1,200+ malicious skills into the largest AI agent marketplace. Researchers catalogued **6,487 malicious agent tools** that conventional scanners cannot detect. **CVE-2026-25253** demonstrated remote code execution through a single compromised skill.

The industry responded with heuristic scanning tools -- YARA rules, LLM-as-judge scoring, regex patterns. Every one shares the same limitation: **absence of findings does not mean absence of risk.**

SkillFortify solves this with formal verification. It constructs a mathematical model of what each skill can and cannot do -- and verifies that model against declared capabilities. The same category of guarantee used to verify cryptographic protocols and flight control software, applied to agent skills for the first time.

---

## Quick Start

```bash
# Install
pip install skillfortify

# Scan your entire system -- auto-discovers ALL AI tools
skillfortify scan

# Scan a specific project
skillfortify scan ./my-agent-project

# Generate an interactive HTML security dashboard
skillfortify dashboard

# List all 22 supported frameworks
skillfortify frameworks
```

**Requirements:** Python 3.11+ | Works on macOS, Linux, Windows | Runs entirely offline | MIT License

---

## 22 Supported Agent Frameworks

SkillFortify analyzes skills, tools, and configurations across the entire agent ecosystem:

| Tier | Frameworks |
|------|-----------|
| **Major Platforms** | Claude Code, MCP, OpenClaw, OpenAI Agents SDK, Google ADK, Anthropic Agent SDK |
| **Orchestration** | LangChain, CrewAI, AutoGen, Semantic Kernel, LlamaIndex, PydanticAI, Haystack |
| **Agent Frameworks** | Agno (Phidata), CAMEL-AI, MetaGPT, Composio, Mastra |
| **Workflow Builders** | n8n, Flowise, Dify Plugins |

Run `skillfortify frameworks` for the full list with detection patterns.

---

## Nine Commands, One Tool

| Command | Purpose |
|---------|---------|
| `skillfortify scan` | Auto-discover all AI tools on your system and analyze every skill found |
| `skillfortify scan <path>` | Scan a specific project directory |
| `skillfortify verify <skill>` | Formally verify a single skill file |
| `skillfortify lock <path>` | Generate `skill-lock.json` for reproducible configurations |
| `skillfortify trust <skill>` | Compute multi-signal trust score for a skill |
| `skillfortify sbom <path>` | Generate CycloneDX 1.6 Agent Skill Bill of Materials |
| `skillfortify frameworks` | List all 22 supported frameworks with detection patterns |
| `skillfortify dashboard` | Generate a standalone HTML security report |
| `skillfortify registry-scan` | Scan remote registries (MCP, PyPI, npm) for supply chain risks |

---

## Key Numbers

| Metric | Value |
|--------|-------|
| **Tests** | 1,818 passing |
| **Supported Frameworks** | 22 |
| **IDE Profiles** | 23 (auto-discovery) |
| **Benchmark Size** | 540 skills (270 malicious, 270 benign) |
| **F1 Score** | 96.95% |
| **Precision** | 100% (zero false positives) |
| **Recall** | 94.12% |
| **Analysis Speed** | ~2.5 ms per skill |
| **Paper** | 31 pages, 5 theorems with proofs |

---

## Wiki Pages

### Understanding SkillFortify

- **[Why SkillFortify](Why-SkillFortify)** -- The problem, the gap in current tools, and what formal analysis provides that heuristics cannot
- **[Formal Foundations](Formal-Foundations)** -- The five theorems, DY-Skill model, capability lattice, trust algebra, and SAT-based resolution
- **[Trust Levels](Trust-Levels)** -- L0 through L3 trust levels, how trust scores are computed, and trust propagation

### Using SkillFortify

- **[Getting Started](Getting-Started)** -- Installation, system scan walkthrough, dashboard generation
- **[CLI Reference](CLI-Reference)** -- All nine commands with full options, examples, and exit codes
- **[Supported Formats](Supported-Formats)** -- All 22 agent frameworks with detection patterns

### Supply Chain Security

- **[Skill Lock JSON](Skill-Lock-JSON)** -- The lockfile format for reproducible agent configurations
- **[ASBOM Guide](ASBOM-Guide)** -- Agent Skill Bill of Materials, CycloneDX 1.6, compliance
- **[SkillFortifyBench](SkillFortifyBench)** -- The 540-skill benchmark: construction, results, reproduction

### Reference

- **[FAQ](FAQ)** -- Frequently asked questions
- **[Roadmap](Roadmap)** -- What is coming next

---

## Links

| Resource | URL |
|----------|-----|
| **GitHub Repository** | [github.com/varun369/skillfortify](https://github.com/varun369/skillfortify) |
| **PyPI Package** | [pypi.org/project/skillfortify](https://pypi.org/project/skillfortify/) |
| **Research Paper** | [Zenodo](https://doi.org/10.5281/zenodo.18787663) (DOI: 10.5281/zenodo.18787663) |
| **AgentAssert Paper** | [arXiv:2602.22302](https://arxiv.org/abs/2602.22302) |
| **AgentAssert Suite** | [agentassert.com](https://agentassert.com) |

---

## Citation

If you use SkillFortify in your research, please cite:

```bibtex
@software{bhardwaj2026skillfortify,
  author    = {Bhardwaj, Varun Pratap},
  title     = {SkillFortify: Formal Analysis and Supply Chain Security
               for Agentic AI Skills},
  year      = {2026},
  publisher = {GitHub},
  url       = {https://github.com/varun369/skillfortify}
}
```

---

## Part of the AgentAssert Research Suite

SkillFortify is the second product in a research program building formal foundations for trustworthy AI agents:

| Product | What It Establishes | Status |
|---------|---------------------|--------|
| **[AgentAssert](https://arxiv.org/abs/2602.22302)** ([Zenodo](https://zenodo.org/records/18775393)) | How to SPECIFY and ENFORCE agent behavior | Published |
| **SkillFortify** | How to VERIFY and SECURE the agent supply chain | Current |
| More coming | Formal methods for agent testing, communication, and memory | Planned |

Together, AgentAssert specifies what agents SHOULD do. SkillFortify ensures the skills they USE are safe.

---

## Author

**Varun Pratap Bhardwaj** -- Solution Architect with 15+ years in enterprise technology. Dual qualifications in technology and law (LL.B.), with a focus on formal methods for AI safety and regulatory compliance for autonomous systems.

- ORCID: [0009-0002-8726-4289](https://orcid.org/0009-0002-8726-4289)
- Email: varun.pratap.bhardwaj@gmail.com

---

## License

MIT License. See [LICENSE](https://github.com/varun369/skillfortify/blob/main/LICENSE) for details.
