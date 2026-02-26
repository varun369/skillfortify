# Getting Started with SkillFortify

This guide walks you through installing SkillFortify, running your first scan, and understanding the results.

---

## Installation

### From PyPI

```bash
pip install skillfortify
```

### From Source

```bash
git clone https://github.com/varun369/skillfortify.git
cd skillfortify
pip install -e .
```

### Verify Installation

```bash
skillfortify --version
```

You should see output like:

```
skillfortify, version 0.1.0
```

---

## Your First Scan

Navigate to any project directory that contains agent skills and run:

```bash
skillfortify scan .
```

SkillFortify automatically detects skills across all supported formats:

- **Claude Code Skills** in `.claude/skills/`
- **MCP Server configurations** in `mcp.json` or `mcp_config.json`
- **OpenClaw Skills** in `.claw/`

### Example Output

```
┌──────────────────────────────────────────────────────────────────┐
│                       SkillFortify Scan Results                        │
├─────────────────────┬────────┬────────┬──────────┬──────────────┤
│ Skill               │ Format │ Status │ Findings │ Max Severity │
├─────────────────────┼────────┼────────┼──────────┼──────────────┤
│ code-review         │ -      │  SAFE  │        0 │ -            │
│ deploy-prod         │ -      │ UNSAFE │        3 │ CRITICAL     │
│ fetch-weather       │ -      │  SAFE  │        0 │ -            │
└─────────────────────┴────────┴────────┴──────────┴──────────────┘
3 skills scanned | 2 safe | 1 unsafe | 3 total findings
```

**Exit code 0** means all skills passed. **Exit code 1** means at least one skill has security findings. This makes SkillFortify ideal for CI/CD pipelines -- a failing exit code blocks the build.

---

## Understanding Findings

Each finding includes:

| Field | Description |
|-------|-------------|
| **Severity** | CRITICAL, HIGH, MEDIUM, or LOW |
| **Type** | Category of the finding (e.g., data exfiltration, privilege escalation) |
| **Message** | Human-readable description of the security issue |
| **Evidence** | The specific content that triggered the finding |

### Severity Levels

| Level | Meaning | Action |
|-------|---------|--------|
| **CRITICAL** | Active exploitation risk. The skill exhibits behavior consistent with known attack patterns | Remove immediately |
| **HIGH** | Significant security concern. The skill requests capabilities or performs actions well beyond its stated purpose | Investigate before using |
| **MEDIUM** | Moderate concern. Potentially unnecessary capabilities or suspicious patterns | Review and assess |
| **LOW** | Minor observation. Informational findings that may warrant attention | Note for future review |

---

## Deep Verification

For detailed analysis of a specific skill, use `verify`:

```bash
skillfortify verify .claude/skills/deploy-prod.md
```

This produces a full report including:

- **Inferred capabilities** -- what the skill can actually do (filesystem access, network calls, etc.)
- **Findings** with evidence -- exactly what triggered each security flag
- **POLA compliance** -- whether the skill requests more permissions than it needs

---

## Generating a Lockfile

Lock your agent configuration for reproducibility and tamper detection:

```bash
skillfortify lock .
```

This creates a `skill-lock.json` file in your project directory containing:

- Exact version of every discovered skill
- SHA-256 content hash for integrity verification
- Declared and inferred capabilities
- Trust metadata

Commit `skill-lock.json` to version control. On subsequent installs or CI runs, you can verify that no skill has been tampered with by comparing against the lockfile.

See [Lockfile Format](skill-lock-json.md) for the full specification.

---

## Computing Trust Scores

Evaluate how trustworthy a skill is:

```bash
skillfortify trust .claude/skills/deploy-prod.md
```

Trust scores combine four signals into a single score between 0 and 1:

| Signal | What It Measures |
|--------|-----------------|
| **Provenance** | Author verification and signing status |
| **Behavioral** | Static analysis results (clean = higher score) |
| **Community** | Usage history, reviews, community reputation |
| **Historical** | Past vulnerability and incident record |

The score maps to a trust level: UNSIGNED, SIGNED, COMMUNITY_VERIFIED, or FORMALLY_VERIFIED.

---

## Generating an ASBOM

For compliance and audit requirements, generate a CycloneDX 1.6 Agent Skill Bill of Materials:

```bash
skillfortify sbom . --project-name "my-agent" --project-version "1.0.0"
```

This produces `asbom.cdx.json` -- a machine-readable inventory of every skill in your project, including security findings and trust metadata. See [ASBOM Output](asbom.md) for details on the format and compliance use cases.

---

## JSON Output

Every command supports `--format json` for machine-readable output:

```bash
skillfortify scan . --format json
skillfortify verify .claude/skills/deploy.md --format json
skillfortify trust .claude/skills/deploy.md --format json
```

This is useful for:

- CI/CD pipeline integration
- Custom dashboards and reporting
- Programmatic analysis of results

---

## Filtering by Severity

To reduce noise, filter scan results by minimum severity:

```bash
skillfortify scan . --severity-threshold high
```

This only reports findings at HIGH or CRITICAL severity, suppressing MEDIUM and LOW. Available thresholds: `low`, `medium`, `high`, `critical`.

---

## Next Steps

- **[CLI Reference](commands.md)** -- complete documentation for every command and option
- **[Lockfile Format](skill-lock-json.md)** -- understand the `skill-lock.json` specification
- **[ASBOM Output](asbom.md)** -- CycloneDX format for compliance reporting
