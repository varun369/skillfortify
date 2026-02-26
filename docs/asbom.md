# ASBOM Output (Agent Skill Bill of Materials)

SkillFortify generates Agent Skill Bills of Materials (ASBOMs) in CycloneDX 1.6 JSON format. An ASBOM is a complete, machine-readable inventory of every agent skill in your project -- including security findings, capability declarations, and trust metadata.

---

## Why ASBOMs?

Software Bill of Materials (SBOMs) are already required by US Executive Order 14028 and the EU Cyber Resilience Act for traditional software. As AI agents become production infrastructure, the same compliance requirements extend to agent components.

An ASBOM answers the questions auditors and compliance teams ask:

- **What skills does this agent use?**
- **What can each skill access?**
- **Are any skills flagged as security risks?**
- **What is the trust level of each component?**
- **Who authored each skill, and has it been verified?**

---

## Generating an ASBOM

```bash
skillfortify sbom ./my-project
```

This produces `./my-project/asbom.cdx.json`. To customize:

```bash
skillfortify sbom ./my-project \
  --project-name "production-agent" \
  --project-version "2.1.0" \
  -o ./compliance/asbom.cdx.json
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--output`, `-o` | `<path>/asbom.cdx.json` | Custom output path |
| `--project-name` | `agent-project` | Name of the agent project |
| `--project-version` | `0.0.0` | Version of the agent project |

---

## Output Format

The ASBOM follows the [CycloneDX 1.6 specification](https://cyclonedx.org/specification/overview/) with extensions for agent skill metadata. The output is a JSON file that can be consumed by any CycloneDX-compatible tool.

### Terminal Summary

When generating an ASBOM, SkillFortify prints a summary to the terminal:

```
┌───────────────────────────────────────────┐
│   Agent Skill Bill of Materials (ASBOM)   │
├───────────────────────────────────────────┤
│   Total skills:   5                       │
│   Safe:           3                       │
│   Unsafe:         2                       │
│   Total findings: 4                       │
├───────────────────────────────────────────┤
│           Format Distribution             │
├──────────────────┬────────────────────────┤
│ Format           │ Count                  │
├──────────────────┼────────────────────────┤
│ claude           │ 3                      │
│ mcp              │ 1                      │
│ openclaw         │ 1                      │
├──────────────────┴────────────────────────┤
│           Trust Distribution              │
├──────────────────┬────────────────────────┤
│ Level            │ Count                  │
├──────────────────┼────────────────────────┤
│ FORMALLY_VERIFIED│ 2                      │
│ COMMUNITY_VERIFIED│ 1                     │
│ SIGNED           │ 1                      │
│ UNSIGNED         │ 1                      │
└──────────────────┴────────────────────────┘

ASBOM written to: ./my-project/asbom.cdx.json
```

---

## What the ASBOM Includes

Each skill entry in the ASBOM contains:

| Field | Description |
|-------|-------------|
| **Name** | Skill identifier |
| **Version** | Resolved version string |
| **Format** | Skill ecosystem (Claude, MCP, OpenClaw) |
| **Integrity hash** | SHA-256 content hash for tamper detection |
| **Capabilities** | What the skill can access (filesystem, network, etc.) |
| **Security findings** | Any issues detected during analysis, with severity |
| **Trust score** | Multi-signal trust score [0, 1] |
| **Trust level** | Graduated trust level (UNSIGNED through FORMALLY_VERIFIED) |
| **Source path** | Where the skill was found on disk |

---

## Compliance Use Cases

### Audit Trails

The ASBOM serves as a point-in-time snapshot of your agent's skill inventory. By generating ASBOMs as part of your release process and archiving them, you create an audit trail of exactly which skills were deployed in each version.

```bash
# Generate ASBOM as part of release
skillfortify sbom . \
  --project-name "prod-agent" \
  --project-version "$(git describe --tags)" \
  -o "./releases/asbom-$(date +%Y%m%d).cdx.json"
```

### Regulatory Compliance

ASBOMs help demonstrate compliance with:

- **US Executive Order 14028** -- SBOM requirements for software sold to the federal government
- **EU Cyber Resilience Act** -- Component transparency requirements
- **NIST AI Risk Management Framework** -- Third-party AI component documentation
- **ISO/IEC 27001** -- Information security management system controls

### Third-Party Risk Assessment

When evaluating an agent project from a vendor or open-source contributor, generate an ASBOM to understand its skill dependencies:

```bash
git clone <vendor-agent-repo>
skillfortify sbom ./vendor-agent --project-name "vendor-evaluation"
```

The ASBOM tells you exactly what skills the agent uses, what they can access, and whether any have security concerns -- before you deploy anything.

---

## Integration with SBOM Tools

The CycloneDX JSON output is compatible with the broader SBOM tooling ecosystem:

- **Dependency-Track** (OWASP) -- import the ASBOM for continuous monitoring
- **Grype** -- scan the ASBOM for known vulnerabilities
- **CycloneDX CLI** -- validate, merge, and transform ASBOMs
- **GUAC** (Google) -- ingest into supply chain knowledge graph

### Example: Import into Dependency-Track

```bash
# Generate ASBOM
skillfortify sbom . --project-name "my-agent" --project-version "1.0.0"

# Upload to Dependency-Track API
curl -X POST https://dtrack.example.com/api/v1/bom \
  -H "X-Api-Key: $DTRACK_API_KEY" \
  -F "project=my-agent" \
  -F "bom=@asbom.cdx.json"
```

---

## Combining with Lockfiles

For maximum security, use both the lockfile and ASBOM together:

1. **`skill-lock.json`** -- enforces reproducibility and tamper detection at install time
2. **`asbom.cdx.json`** -- provides inventory and compliance documentation for auditors

```bash
# Generate both
skillfortify lock .
skillfortify sbom . --project-name "prod-agent" --project-version "1.0.0"

# Commit both to version control
git add skill-lock.json asbom.cdx.json
git commit -m "Update skill lockfile and ASBOM"
```

The lockfile is for machines (reproducible installs). The ASBOM is for humans and compliance systems (understanding what is installed and whether it is safe).
