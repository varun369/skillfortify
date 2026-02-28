# Skill Lock JSON -- Reproducible Agent Configurations

`skill-lock.json` is SkillFortify's lockfile format for agent skill configurations. It serves the same purpose as `package-lock.json` in npm or `poetry.lock` in Python -- pinning every skill to its exact version and content hash so that the same verified configuration can be reproduced across development, staging, and production environments.

Before `skill-lock.json`, there was no way to guarantee that the agent skills deployed to production were the exact same skills that were verified during development. SkillFortify introduces lockfile semantics to the agent skill ecosystem.

---

## Why Reproducibility Matters

### The Problem Without a Lockfile

Without a lockfile, agent skill configurations are non-deterministic:

- A skill might be updated between your development session and production deployment
- An attacker could replace a legitimate skill with a malicious version between verification and deployment
- Different team members may have different skill versions, leading to inconsistent behavior
- There is no audit trail of what was actually deployed

### The Solution

`skill-lock.json` captures the exact state of every skill at the time of verification:

- **Content hash**: SHA-256 hash of each skill's contents, detecting any modification
- **Capabilities at lock time**: The capabilities inferred during formal analysis
- **Trust score at lock time**: The trust level when the lockfile was generated
- **Timestamp**: When the lockfile was created

If any skill changes after locking, the hash mismatch is detected immediately.

---

## Generating a Lockfile

### Basic Generation

```bash
skillfortify lock .
```

This scans the project directory, analyzes all detected skills, and generates `skill-lock.json` in the current directory.

### Custom Output Path

```bash
skillfortify lock ./my-agent-project -o ./config/skill-lock.json
```

### Workflow

```bash
# 1. Develop your agent project
# 2. Scan for security issues
skillfortify scan .

# 3. Fix any findings
# 4. Generate the lockfile
skillfortify lock .

# 5. Commit the lockfile to version control
git add skill-lock.json
git commit -m "Lock agent skill configuration"

# 6. In CI/CD, verify the lockfile is current
skillfortify lock . --output /tmp/fresh-lock.json
diff skill-lock.json /tmp/fresh-lock.json
```

---

## Schema

The `skill-lock.json` file has the following structure:

```json
{
  "lockfile_version": "1.0",
  "generated_at": "2026-02-26T14:30:00Z",
  "generated_by": "skillfortify 0.1.0",
  "project_path": "./my-agent-project",
  "skills": [
    {
      "name": "deploy-automation",
      "format": "claude",
      "path": ".claude/skills/deploy.md",
      "hash": "sha256:a1b2c3d4e5f6...",
      "capabilities": [
        {"resource": "filesystem", "access": "READ"},
        {"resource": "network", "access": "READ"}
      ],
      "trust_score": 0.85,
      "trust_level": "FORMALLY_VERIFIED",
      "findings_count": 0,
      "status": "SAFE"
    },
    {
      "name": "weather-lookup",
      "format": "mcp",
      "path": "mcp.json#weather-lookup",
      "hash": "sha256:f6e5d4c3b2a1...",
      "capabilities": [
        {"resource": "network", "access": "READ"}
      ],
      "trust_score": 0.60,
      "trust_level": "COMMUNITY_VERIFIED",
      "findings_count": 0,
      "status": "SAFE"
    }
  ],
  "summary": {
    "total_skills": 2,
    "safe": 2,
    "unsafe": 0,
    "average_trust_score": 0.725
  }
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `lockfile_version` | string | Schema version for the lockfile format |
| `generated_at` | ISO 8601 | When the lockfile was generated |
| `generated_by` | string | SkillFortify version that generated the lockfile |
| `project_path` | string | Path that was scanned |
| `skills` | array | List of all locked skills |
| `skills[].name` | string | Skill name |
| `skills[].format` | string | Detected format (claude, mcp, claw) |
| `skills[].path` | string | Relative path to the skill file |
| `skills[].hash` | string | SHA-256 content hash |
| `skills[].capabilities` | array | Inferred capabilities at lock time |
| `skills[].trust_score` | number | Trust score at lock time (0.0 to 1.0) |
| `skills[].trust_level` | string | Trust level at lock time |
| `skills[].findings_count` | integer | Number of findings at lock time |
| `skills[].status` | string | SAFE or UNSAFE at lock time |
| `summary` | object | Aggregate statistics |

---

## Integrity Verification

### Detecting Modifications

The content hash in the lockfile enables tamper detection. If a skill file changes after locking -- whether through legitimate update or malicious modification -- regenerating the lockfile will produce different hashes.

```bash
# Generate a fresh lockfile
skillfortify lock . --output /tmp/fresh-lock.json

# Compare with committed lockfile
diff skill-lock.json /tmp/fresh-lock.json
```

If the files differ, one or more skills have changed since the lockfile was generated. Investigate the changes before proceeding.

### CI/CD Verification

```yaml
- name: Verify lockfile integrity
  run: |
    skillfortify lock . --output /tmp/fresh-lock.json
    if ! diff -q skill-lock.json /tmp/fresh-lock.json > /dev/null 2>&1; then
      echo "ERROR: Lockfile is stale. Skills have changed since last lock."
      echo "Run 'skillfortify lock .' locally and commit the updated lockfile."
      exit 1
    fi
```

---

## Best Practices

### 1. Commit the Lockfile

Always commit `skill-lock.json` to version control. It is part of your project's security configuration, just like `package-lock.json` or `Cargo.lock`.

### 2. Regenerate After Skill Changes

Whenever you add, remove, or update a skill, regenerate the lockfile:

```bash
skillfortify lock .
git add skill-lock.json
git commit -m "Update skill lockfile"
```

### 3. Verify in CI/CD

Add lockfile verification to your CI/CD pipeline to catch situations where skills have changed but the lockfile was not updated.

### 4. Review Lockfile Diffs in PRs

When a pull request modifies `skill-lock.json`, review the changes carefully:

- New skills: Were they scanned and verified?
- Changed hashes: What changed in the skill content?
- Trust score changes: Did any skill's trust level change?
- New findings: Did any previously safe skill become unsafe?

### 5. Keep Lockfiles Per Environment

If your staging and production environments use different skill configurations, maintain separate lockfiles:

```bash
skillfortify lock ./staging-config -o staging-skill-lock.json
skillfortify lock ./production-config -o production-skill-lock.json
```

---

## Further Reading

- **[ASBOM Guide](ASBOM-Guide)** -- Compliance documentation using CycloneDX SBOM
- **[Trust Levels](Trust-Levels)** -- How trust scores in the lockfile are computed
- **[CLI Reference](CLI-Reference)** -- Full `skillfortify lock` command options
- **[Getting Started](Getting-Started)** -- First scan and lockfile generation walkthrough

---

*SkillFortify is part of the [AgentAssert](https://agentassert.com) research suite -- building formal foundations for trustworthy AI agents.*
