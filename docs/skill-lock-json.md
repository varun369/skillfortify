# skill-lock.json Format

The `skill-lock.json` file is SkillFortify's lockfile format for agent skill configurations. It serves the same purpose as `package-lock.json` in the npm ecosystem: guaranteeing that agent skill installations are **reproducible**, **auditable**, and **tamper-resistant**.

---

## Why a Lockfile?

Agent skills evolve. Authors push updates. Registries change. Without a lockfile, installing "the same skills" on two different machines -- or at two different times -- can produce different results. This is a security risk: a skill that was safe last week may have been updated with malicious behavior.

The lockfile pins every skill to:

1. **An exact version** -- no floating ranges
2. **A content hash** -- SHA-256 integrity verification
3. **Declared capabilities** -- what the skill is allowed to do
4. **Trust metadata** -- scored and leveled at lock time

If any skill's content changes (even by one byte), the integrity hash will not match, and SkillFortify will flag the discrepancy.

---

## Generating a Lockfile

```bash
skillfortify lock ./my-project
```

This creates `./my-project/skill-lock.json`. To specify a custom path:

```bash
skillfortify lock ./my-project -o ./config/skill-lock.json
```

---

## File Structure

```json
{
  "generated_at": "2026-02-26T10:30:00+00:00",
  "generated_by": "skillfortify",
  "integrity_algorithm": "sha256",
  "lockfile_version": "1.0",
  "metadata": {
    "resolution_strategy": "sat",
    "total_skills": 3
  },
  "skills": {
    "code-review": {
      "capabilities": [
        "filesystem:READ"
      ],
      "dependencies": {},
      "format": "claude",
      "integrity": "sha256:a1b2c3d4e5f6...64 hex characters",
      "source_path": ".claude/skills/code-review.md",
      "trust_level": "FORMALLY_VERIFIED",
      "trust_score": 0.85,
      "version": "1.0.0"
    },
    "data-export": {
      "capabilities": [
        "filesystem:READ",
        "filesystem:WRITE",
        "network:WRITE"
      ],
      "dependencies": {},
      "format": "claude",
      "integrity": "sha256:f6e5d4c3b2a1...64 hex characters",
      "source_path": ".claude/skills/data-export.md",
      "trust_level": "SIGNED",
      "trust_score": 0.35,
      "version": "1.0.0"
    }
  }
}
```

---

## Field Reference

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `lockfile_version` | string | Lockfile format version. Currently `"1.0"` |
| `generated_by` | string | Tool that generated the lockfile. Always `"skillfortify"` |
| `generated_at` | string | ISO 8601 timestamp (UTC) of when the lockfile was generated |
| `integrity_algorithm` | string | Hash algorithm used for content verification. Currently `"sha256"` |
| `skills` | object | Map of skill name to skill entry |
| `metadata` | object | Resolution metadata |

### Skill Entry Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Resolved semantic version |
| `integrity` | string | Content hash in `sha256:<64-hex-chars>` format |
| `format` | string | Skill format: `"claude"`, `"mcp"`, or `"openclaw"` |
| `capabilities` | array | List of capability strings (e.g., `"filesystem:READ"`) |
| `dependencies` | object | Map of dependency name to resolved version |
| `trust_score` | number | Computed trust score in [0, 1]. Optional |
| `trust_level` | string | Trust level: `UNSIGNED`, `SIGNED`, `COMMUNITY_VERIFIED`, or `FORMALLY_VERIFIED`. Optional |
| `source_path` | string | Filesystem path where the skill was found |

### Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `total_skills` | integer | Number of skill entries in the lockfile |
| `resolution_strategy` | string | Algorithm used for resolution: `"sat"` or `"manual"` |
| `allowed_capabilities` | array | Capability bounds applied during resolution. Optional |

---

## Integrity Verification

Each skill entry includes a `sha256:<hex>` integrity hash computed over the skill's complete file content. This provides:

- **Tamper detection** -- any modification to a skill file (including subtle prompt injection additions) invalidates the hash
- **Reproducibility** -- the exact content that was analyzed is recorded
- **Auditability** -- compliance teams can verify that deployed skills match the approved lockfile

### Verification Workflow

1. Generate the lockfile: `skillfortify lock .`
2. Commit `skill-lock.json` to version control
3. In CI/CD, re-generate and compare:
   ```bash
   skillfortify lock . -o /tmp/fresh-lock.json
   diff skill-lock.json /tmp/fresh-lock.json
   ```
4. If the diff is non-empty, a skill changed since the lockfile was created

---

## Determinism Guarantee

SkillFortify lockfiles are **deterministic**: given the same set of skills with the same content, `skillfortify lock` always produces byte-identical JSON output. This is achieved by:

- Sorting all skill entries alphabetically by name
- Sorting all capability lists alphabetically
- Sorting all dependency mappings alphabetically
- Sorting all JSON keys

This means lockfile diffs are clean and meaningful -- no spurious ordering changes.

---

## Capability Strings

Capabilities follow the `resource:access` format:

| Resource | Description |
|----------|-------------|
| `filesystem` | Local file system access |
| `network` | Network/HTTP access |
| `environment` | Environment variable access |
| `process` | Process execution |
| `database` | Database access |

| Access Level | Description |
|-------------|-------------|
| `READ` | Read-only access |
| `WRITE` | Write access (includes read) |
| `EXECUTE` | Execution access (highest level) |

Example capability strings:
- `filesystem:READ` -- can read files
- `network:WRITE` -- can make outbound network requests
- `process:EXECUTE` -- can spawn processes

---

## Best Practices

1. **Commit the lockfile to version control.** It is the source of truth for which skills are approved
2. **Regenerate after adding or updating skills.** Run `skillfortify lock .` whenever skill files change
3. **Verify in CI/CD.** Compare the committed lockfile against a freshly generated one to detect unauthorized changes
4. **Review capability changes.** When a lockfile diff shows new capabilities, investigate why a skill needs them
5. **Do not edit the lockfile by hand.** Always regenerate it with `skillfortify lock`
