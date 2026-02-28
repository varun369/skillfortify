# Getting Started with SkillFortify

Install SkillFortify, run your first security scan, and generate a visual dashboard.

---

## Installation

```bash
pip install skillfortify
skillfortify --version
```

**From source:**

```bash
git clone https://github.com/varun369/skillfortify.git
cd skillfortify
pip install -e ".[dev]"
```

**Optional extras:**

```bash
pip install skillfortify[sat]        # SAT-based dependency resolution
pip install skillfortify[registry]   # Remote registry scanning (MCP, PyPI, npm)
```

**Requirements:** Python 3.11+ | macOS, Linux, Windows | Fully offline | No API keys needed

---

## Scan Your Entire System (Recommended First Step)

Run SkillFortify with no arguments to auto-discover every AI tool on your machine:

```bash
skillfortify scan
```

SkillFortify checks 23 known IDE and AI tool locations -- Claude Code, Cursor, VS Code, Windsurf, Gemini CLI, Cline, Continue, GitHub Copilot, and more. Every skill and MCP configuration found is analyzed automatically.

### Example Output

```
SkillFortify System Scan
========================================

Discovered AI Tools:
  + Claude Code        ~/.claude           2 skill dir(s), 1 MCP config(s)
  + Cursor             ~/.cursor           1 MCP config(s)
  o Windsurf           ~/.codeium          (no skills detected)

Scanning 6 skills across 2 active IDE(s)...

+----------------------+--------+--------+----------+-------------+
|                      SkillFortify Scan Results                  |
+----------------------+--------+--------+----------+-------------+
| Skill                | Format | Status | Findings | Max Severity|
+----------------------+--------+--------+----------+-------------+
| deploy-automation    | Claude | SAFE   |        0 | -           |
| data-export          | MCP    | UNSAFE |        2 | HIGH        |
+----------------------+--------+--------+----------+-------------+
```

---

## Scan a Specific Project

```bash
skillfortify scan ./my-agent-project
```

Auto-detects skills across all 22 supported frameworks within the directory.

---

## Generate an HTML Dashboard

```bash
skillfortify dashboard                                    # System-wide
skillfortify dashboard ./my-agent-project                 # Project-specific
skillfortify dashboard --title "Q1 Security Audit" --open # Custom title, auto-open
```

Generates a standalone HTML file with charts, severity breakdown, and per-skill details. No server needed.

---

## List Supported Frameworks

```bash
skillfortify frameworks
```

Prints all 22 agent frameworks with format identifiers and detection patterns.

---

## Understanding Findings

| Severity | What It Means | Action |
|----------|---------------|--------|
| **CRITICAL** | Immediate threat: data exfiltration, RCE, credential theft | Remove immediately |
| **HIGH** | Capabilities beyond declaration: undeclared network, excessive permissions | Investigate before using |
| **MEDIUM** | Potentially concerning but may be legitimate | Review the skill's purpose |
| **LOW** | Minor declarations that could be tightened | Security hygiene |

---

## Next Steps

### Generate a Lockfile

```bash
skillfortify lock .
```

Creates `skill-lock.json` for reproducible configurations. See [Skill Lock JSON](Skill-Lock-JSON).

### Compute Trust Scores

```bash
skillfortify trust .claude/skills/deploy.md
```

See [Trust Levels](Trust-Levels).

### Generate an ASBOM

```bash
skillfortify sbom . --project-name "my-agent" --project-version "1.0.0"
```

See [ASBOM Guide](ASBOM-Guide).

### Scan Remote Registries

```bash
pip install skillfortify[registry]
skillfortify registry-scan mcp --limit 20
skillfortify registry-scan pypi --keyword "mcp-server"
```

### Integrate into CI/CD

```yaml
- name: Scan agent skills
  run: skillfortify scan . --format json --severity-threshold high
```

See [CLI Reference](CLI-Reference) for full details.

---

## Getting Help

- **[CLI Reference](CLI-Reference)** -- All nine commands documented
- **[FAQ](FAQ)** -- Common questions
- **[Supported Formats](Supported-Formats)** -- All 22 frameworks
- **[GitHub Issues](https://github.com/varun369/skillfortify/issues)** -- Report bugs

---

*SkillFortify is part of the [AgentAssert](https://agentassert.com) research suite.*
