# CLI Reference

Complete documentation for every SkillFortify command, option, and exit code.

---

## Global Options

```bash
skillfortify --version    # Print version and exit
skillfortify --help       # Show top-level help
```

---

## `skillfortify scan`

Discover and analyze all agent skills in a directory.

### Usage

```bash
skillfortify scan <path> [OPTIONS]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `path` | Yes | Directory to scan. Must exist and contain agent skills |

### Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--format` | `text`, `json` | `text` | Output format |
| `--severity-threshold` | `low`, `medium`, `high`, `critical` | `low` | Minimum severity to report |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All skills passed (no findings above threshold) |
| `1` | One or more skills have findings at or above threshold |
| `2` | No skills found in the target path |

### Examples

```bash
# Scan current directory
skillfortify scan .

# Scan with JSON output for CI/CD
skillfortify scan ./my-project --format json

# Only report HIGH and CRITICAL findings
skillfortify scan . --severity-threshold high

# Combine options
skillfortify scan ./agent-app --format json --severity-threshold medium
```

### JSON Output Schema

```json
[
  {
    "skill_name": "deploy-automation",
    "is_safe": false,
    "findings_count": 2,
    "max_severity": "HIGH",
    "inferred_capabilities": [
      {"resource": "filesystem", "access": "WRITE"},
      {"resource": "network", "access": "READ"}
    ],
    "findings": [
      {
        "severity": "HIGH",
        "message": "Skill requests write access to filesystem beyond declared scope",
        "attack_class": "privilege_escalation",
        "finding_type": "capability_violation",
        "evidence": "..."
      }
    ]
  }
]
```

---

## `skillfortify verify`

Formally verify a single agent skill file with full capability inference.

### Usage

```bash
skillfortify verify <skill-path> [OPTIONS]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `skill-path` | Yes | Path to a specific skill file |

### Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--format` | `text`, `json` | `text` | Output format |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Skill passed all verification checks |
| `1` | Skill has one or more security findings |
| `2` | Skill file could not be parsed |

### Examples

```bash
# Verify a Claude Code skill
skillfortify verify .claude/skills/deploy.md

# Verify with JSON output
skillfortify verify .claude/skills/deploy.md --format json

# Verify an MCP server config
skillfortify verify mcp.json
```

### What Verify Reports

1. **Verdict** -- SAFE or UNSAFE
2. **Inferred Capabilities** -- what the skill can actually access (filesystem, network, environment variables, etc.) and at what access level (READ, WRITE, EXECUTE)
3. **Findings** -- each security issue with severity, type, message, and evidence
4. **POLA Compliance** -- whether the skill adheres to the Principle of Least Authority

---

## `skillfortify lock`

Generate a `skill-lock.json` lockfile for reproducible agent configurations.

### Usage

```bash
skillfortify lock <path> [OPTIONS]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `path` | Yes | Project directory containing agent skills |

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--output` | `-o` | `<path>/skill-lock.json` | Custom output path for the lockfile |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Lockfile generated successfully |
| `1` | Dependency resolution failed (conflicts detected) |
| `2` | No skills found in the target path |

### Examples

```bash
# Generate lockfile in project root
skillfortify lock .

# Custom output path
skillfortify lock ./my-project -o ./config/skill-lock.json
```

### What the Lockfile Captures

- Exact resolved version of every skill
- SHA-256 content integrity hash
- Declared and inferred capabilities
- Resolved dependency mappings
- Trust score and trust level (when computed)
- Source path for auditing

See [Lockfile Format](skill-lock-json.md) for the complete specification.

---

## `skillfortify trust`

Compute and display a multi-signal trust score for an agent skill.

### Usage

```bash
skillfortify trust <skill-path> [OPTIONS]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `skill-path` | Yes | Path to a specific skill file |

### Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--format` | `text`, `json` | `text` | Output format |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Trust score computed and displayed |
| `2` | Skill file could not be parsed |

### Examples

```bash
# Compute trust score
skillfortify trust .claude/skills/deploy.md

# JSON output for programmatic use
skillfortify trust .claude/skills/deploy.md --format json
```

### JSON Output Schema

```json
{
  "skill_name": "deploy-automation",
  "version": "1.0.0",
  "intrinsic_score": 0.75,
  "effective_score": 0.75,
  "level": "FORMALLY_VERIFIED",
  "signals": {
    "provenance": 0.5,
    "behavioral": 1.0,
    "community": 0.5,
    "historical": 0.5
  }
}
```

### Trust Score Components

| Field | Description |
|-------|-------------|
| **Intrinsic Score** | Weighted combination of four signals. Range: [0, 1] |
| **Effective Score** | After propagation through dependencies. Always <= intrinsic score |
| **Trust Level** | Graduated level: UNSIGNED, SIGNED, COMMUNITY_VERIFIED, or FORMALLY_VERIFIED |

---

## `skillfortify sbom`

Generate a CycloneDX 1.6 Agent Skill Bill of Materials (ASBOM).

### Usage

```bash
skillfortify sbom <path> [OPTIONS]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `path` | Yes | Project directory containing agent skills |

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--output` | `-o` | `<path>/asbom.cdx.json` | Custom output path |
| `--project-name` | | `agent-project` | Name of the agent project |
| `--project-version` | | `0.0.0` | Version of the agent project |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | ASBOM generated successfully |
| `2` | No skills found in the target path |

### Examples

```bash
# Generate ASBOM with defaults
skillfortify sbom .

# Full options
skillfortify sbom ./my-project \
  --project-name "prod-agent" \
  --project-version "2.1.0" \
  -o ./compliance/asbom.cdx.json
```

See [ASBOM Output](asbom.md) for format details and compliance guidance.
