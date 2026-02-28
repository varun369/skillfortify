# CLI Reference -- SkillFortify Commands

SkillFortify provides nine commands. All local commands run entirely offline with no API keys required.

**Global options:** `--version` (show version) | `--help` (show help)

---

## `skillfortify scan` -- Discover and Analyze Skills

Scan a project directory or your entire system for skills across all 22 supported frameworks. **When called with no arguments**, auto-discovers all AI tools on your system (23 IDE profiles) and scans every skill found.

```bash
skillfortify scan                              # System-wide auto-discovery
skillfortify scan ./my-agent-project           # Specific directory
skillfortify scan . --format json              # JSON for CI/CD
skillfortify scan . --severity-threshold high  # HIGH and CRITICAL only
skillfortify scan . --format html              # HTML report output
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `[path]` | argument | (none) | Directory to scan. Omit for system scan |
| `--system` | flag | off | Explicitly request system-wide scan |
| `--format` | `text`/`json`/`html` | `text` | Output format |
| `--severity-threshold` | `low`/`medium`/`high`/`critical` | `low` | Minimum severity to report |

---

## `skillfortify verify` -- Formally Verify a Single Skill

Deep formal analysis of one skill file with full capability inference and POLA compliance checks.

```bash
skillfortify verify .claude/skills/deploy.md
skillfortify verify mcp.json --format json
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `<skill-path>` | argument | (required) | Path to the skill file |
| `--format` | `text`/`json` | `text` | Output format |

---

## `skillfortify lock` -- Generate Skill Lockfile

Create `skill-lock.json` pinning every skill to its exact content hash, capabilities, and trust score.

```bash
skillfortify lock .
skillfortify lock ./my-agent-project -o ./config/skill-lock.json
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `<path>` | argument | (required) | Project directory to lock |
| `-o`, `--output` | string | `skill-lock.json` | Output file path |

See [Skill Lock JSON](Skill-Lock-JSON) for the full schema.

---

## `skillfortify trust` -- Compute Trust Score

Multi-signal trust score based on provenance, behavioral analysis, community signals, and historical record.

```bash
skillfortify trust .claude/skills/deploy.md
skillfortify trust mcp.json --format json
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `<skill-path>` | argument | (required) | Path to the skill file |
| `--format` | `text`/`json` | `text` | Output format |

See [Trust Levels](Trust-Levels) for what each level means.

---

## `skillfortify sbom` -- Generate CycloneDX ASBOM

Agent Skill Bill of Materials in CycloneDX 1.6 format for compliance and audit.

```bash
skillfortify sbom .
skillfortify sbom . --project-name "prod-agent" --project-version "2.1.0" -o sbom.json
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `<path>` | argument | (required) | Project directory |
| `--project-name` | string | directory name | SBOM project name |
| `--project-version` | string | `0.0.0` | SBOM project version |
| `-o`, `--output` | string | stdout | Output file path |

See [ASBOM Guide](ASBOM-Guide) for details.

---

## `skillfortify frameworks` -- List Supported Frameworks

Display all 22 supported agent frameworks with format identifiers and detection patterns. Always exits with code 0.

```bash
skillfortify frameworks
```

---

## `skillfortify dashboard` -- Generate HTML Security Report

Standalone HTML dashboard with charts and per-skill analysis. Supports project-level and system-wide scans.

```bash
skillfortify dashboard                                    # System-wide
skillfortify dashboard ./my-agent-project                 # Project-specific
skillfortify dashboard --title "Q1 Audit" --open          # Custom title, auto-open
skillfortify dashboard -o ./reports/security.html         # Custom output path
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `[path]` | argument | (none) | Directory to scan. Omit for system scan |
| `--system` | flag | off | Explicitly request system-wide scan |
| `-o`, `--output` | string | `skillfortify-report.html` | Output HTML file path |
| `-t`, `--title` | string | `SkillFortify Security Report` | Report title |
| `--open` | flag | off | Open report in default browser |

---

## `skillfortify registry-scan` -- Scan Remote Registries

Scan remote agent skill registries for supply chain risks. Requires: `pip install skillfortify[registry]`.

```bash
skillfortify registry-scan mcp --limit 20
skillfortify registry-scan pypi --keyword "mcp-server"
skillfortify registry-scan npm --format json
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `<registry>` | `mcp`/`pypi`/`npm` | (required) | Registry to scan |
| `--limit` | integer | `50` | Max entries to scan |
| `--keyword` | string | (none) | Filter keyword |
| `--format` | `text`/`json` | `text` | Output format |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All checks passed |
| `1` | Findings detected |
| `2` | No skills found or parse error |

---

## GitHub Actions Integration

```yaml
name: Skill Security
on: [push, pull_request]
jobs:
  skillfortify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install skillfortify
      - run: skillfortify scan . --severity-threshold high --format json
      - run: skillfortify sbom . --project-name "${{ github.repository }}" -o sbom.json
      - uses: actions/upload-artifact@v4
        with:
          name: agent-sbom
          path: sbom.json
```

---

## Further Reading

- **[Getting Started](Getting-Started)** -- First scan walkthrough
- **[Supported Formats](Supported-Formats)** -- All 22 frameworks
- **[FAQ](FAQ)** -- Common questions

---

*SkillFortify is part of the [AgentAssert](https://agentassert.com) research suite.*
