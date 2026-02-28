# FAQ -- Frequently Asked Questions

Answers to common questions about SkillFortify, agent skill security, and how SkillFortify fits into the broader agent development workflow.

---

## General

### What is SkillFortify?

SkillFortify is a security tool that formally verifies what your AI agent skills can actually do. Instead of scanning for known malicious patterns (heuristic detection), SkillFortify constructs a mathematical model of each skill's capabilities and verifies that model against declared permissions. It supports 22 agent frameworks and auto-discovers 23 IDE configurations.

### Is SkillFortify free?

Yes. SkillFortify is open source under the MIT License. No paid tiers, usage limits, or feature restrictions. Full source code at [github.com/varun369/skillfortify](https://github.com/varun369/skillfortify).

### Does SkillFortify work offline?

Yes, entirely. Local scanning and analysis require no external services, APIs, or cloud endpoints. No data leaves your machine. The only exception is `registry-scan`, which connects to remote registries (MCP, PyPI, npm) by design.

### Does SkillFortify send my code anywhere?

No. All local commands process everything on your machine. No telemetry, no phone-home, no data transmission.

---

## System Scan and Auto-Discovery

### How does the system scan work?

When you run `skillfortify scan` with no arguments, SkillFortify checks 23 known locations on your system where AI development tools store their configurations. For each location found, it looks for MCP configuration files and skill directories. Every skill discovered is then run through the full formal analysis pipeline. The entire process is local and takes seconds.

### What IDEs and AI tools are auto-detected?

SkillFortify has profiles for 23 tools: Claude Code, Cursor, VS Code (macOS and Linux), Windsurf/Codeium, Gemini CLI, OpenCode, Cline, Continue, GitHub Copilot, n8n, Roo Code, Trae, Kiro, Kode, Jules, Junie, Codex CLI, SuperVS, Zencoder, CommandCode, Factory, and Qoder. See [Supported Formats](Supported-Formats) for the full list.

### How do I scan a specific framework only?

Point `skillfortify scan` at the project directory containing that framework's files. SkillFortify will auto-detect which framework is present and analyze only those skills. For example, `skillfortify scan ./my-langchain-project` will detect and analyze LangChain tools in that directory.

### What if an AI tool is installed but has no skills?

It appears in the system scan discovery table with "(no skills detected)". SkillFortify still reports it so you have full visibility into which AI tools are present on the system.

---

## Dashboard

### What is the dashboard?

The `skillfortify dashboard` command generates a standalone HTML security report. It contains visual charts showing the security posture of your scanned skills, a detailed breakdown of findings by severity, and per-skill analysis results. The file is self-contained -- no server or internet connection needed to view it.

### How do I generate a dashboard?

```bash
# System-wide dashboard (all AI tools)
skillfortify dashboard

# Project-specific dashboard
skillfortify dashboard ./my-agent-project

# Custom title, auto-open in browser
skillfortify dashboard --title "March Audit" --open -o report.html
```

### Can I share the dashboard with my team?

Yes. The HTML file is fully self-contained. Email it, upload it to your internal wiki, or include it as a CI/CD artifact. No external dependencies are required to view it.

---

## How It Works

### How is SkillFortify different from npm audit?

`npm audit` checks against a database of known vulnerabilities. SkillFortify formally analyzes what a skill *can do* and verifies that against what it *claims to do*. This catches novel threats that no database contains, because the analysis is structural, not database-driven.

### How is SkillFortify different from other agent skill scanners?

All other agent skill security tools as of March 2026 use heuristic detection: pattern matching, YARA rules, LLM-as-judge scoring, or regex. SkillFortify is the only tool grounded in a formal threat model with proven soundness properties.

### Can SkillFortify catch zero-day attacks?

Yes, for capability-level attacks. Because SkillFortify analyzes what a skill *can do* rather than matching known signatures, it detects novel attacks that no scanner has seen before -- as long as the attack involves undeclared capabilities.

### What kinds of attacks does SkillFortify NOT catch?

Known limitations documented in the paper: install-time attacks (typosquatting, dependency confusion), heavily obfuscated code, and purely semantic attacks. These account for the 6% recall gap in the benchmark.

---

## Usage

### Can I use SkillFortify in CI/CD?

Yes. Use `--format json` for machine-readable output. Exit codes: `0` (all passed), `1` (findings detected), `2` (no skills found). See [CLI Reference](CLI-Reference#github-actions-integration) for GitHub Actions examples.

### What is skill-lock.json?

The equivalent of `package-lock.json` for agent skills. It pins every skill to its exact content hash, capabilities, and trust score. Commit it to version control for reproducible deployments. See [Skill Lock JSON](Skill-Lock-JSON).

### What is an ASBOM?

Agent Skill Bill of Materials -- a structured inventory of every agent skill in your project, generated in CycloneDX 1.6 format. For compliance and audit. See [ASBOM Guide](ASBOM-Guide).

### How do I scan remote registries?

Install the registry extra and use `registry-scan`:

```bash
pip install skillfortify[registry]
skillfortify registry-scan mcp --limit 20
skillfortify registry-scan pypi --keyword "agent-tool"
skillfortify registry-scan npm --keyword "@modelcontextprotocol"
```

---

## Compatibility

### Which agent frameworks are supported?

22 frameworks as of v0.3.0. See [Supported Formats](Supported-Formats) for the complete list covering Claude Code, MCP, OpenClaw, OpenAI Agents SDK, Google ADK, LangChain, CrewAI, AutoGen, and 14 more.

### What Python versions are supported?

Python 3.11 and later. Tested on Python 3.11, 3.12, and 3.13.

### Does it work on Windows?

Yes. SkillFortify is tested on macOS, Linux, and Windows.

---

## Trust and Security

### How are trust scores computed?

Four signals: provenance (who published), behavioral (formal analysis pass/fail), community (usage and review), and historical (maintenance record). Weighted aggregate maps to trust levels L0 through L3. See [Trust Levels](Trust-Levels).

### Is a SAFE result an absolute guarantee?

Within the scope of the formal model, yes. Outside documented boundaries, additional measures are recommended. See [Formal Foundations](Formal-Foundations#known-limitations-of-the-formal-model).

---

## Academic and Research

### Is there a research paper?

Yes. 31 pages, five theorems with full proofs, comprehensive evaluation. Available on [Zenodo](https://doi.org/10.5281/zenodo.18787663).

### How do I cite SkillFortify?

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

## Contributing

- **[GitHub Discussions](https://github.com/varun369/skillfortify/discussions)** -- Questions and community
- **[GitHub Issues](https://github.com/varun369/skillfortify/issues)** -- Bugs and feature requests
- **[SECURITY.md](https://github.com/varun369/skillfortify/blob/main/SECURITY.md)** -- Responsible disclosure for vulnerabilities

---

*SkillFortify is part of the [AgentAssert](https://agentassert.com) research suite -- building formal foundations for trustworthy AI agents.*
