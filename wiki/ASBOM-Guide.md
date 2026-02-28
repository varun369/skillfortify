# ASBOM Guide -- Agent Skill Bill of Materials

An Agent Skill Bill of Materials (ASBOM) is a structured inventory of every agent skill used in your project, including its version, capabilities, trust level, and security findings. SkillFortify generates ASBOMs in CycloneDX 1.6 format -- the industry standard for software bill of materials, extended to cover the unique attributes of agent skills.

If your organization deploys AI agents in production, compliance and security teams need to know exactly what skills those agents use and whether those skills are safe. The ASBOM provides that documentation in a machine-readable, auditable format.

---

## What Is an ASBOM and Why You Need One

### The Concept

A Software Bill of Materials (SBOM) lists every component in a software system -- libraries, frameworks, packages -- with version numbers, licenses, and known vulnerabilities. SBOMs have become standard practice after executive orders, regulatory frameworks, and high-profile supply chain attacks (SolarWinds, Log4j) made software transparency a requirement.

An **Agent Skill Bill of Materials (ASBOM)** extends this concept to AI agent skills. It documents:

- Every skill installed in your agent configuration
- The format and source of each skill (Claude Code, MCP, OpenClaw)
- Capabilities each skill requires and accesses
- Trust levels and trust scores for each skill
- Security findings from formal analysis
- Dependency relationships between skills

### Why It Matters

1. **Compliance**: Regulatory frameworks increasingly require documentation of AI components
2. **Audit trails**: Security teams need to know what changed and when
3. **Incident response**: When a vulnerability is disclosed, you need to know immediately which agents are affected
4. **Vendor management**: Enterprise procurement needs to evaluate the security posture of agent configurations
5. **Reproducibility**: ASBOMs document the exact skill inventory at a point in time

---

## Regulatory Context

### EU AI Act

The EU AI Act requires providers of high-risk AI systems to document third-party components and their risk profiles. Agent skills are third-party components. An ASBOM provides the documentation required to demonstrate compliance with:

- Article 15: Accuracy, robustness and cybersecurity
- Article 17: Quality management system
- Annex IV: Technical documentation requirements

### NIST AI Risk Management Framework (AI RMF)

NIST AI RMF mandates supply chain risk assessment for AI systems. The ASBOM directly addresses:

- MAP 3.4: AI risks from third-party components
- MEASURE 2.6: Assessment of system dependencies
- MANAGE 3.1: Supply chain risk mitigation

### Executive Order 14028 (US)

Executive Order 14028 establishes SBOM requirements for software sold to the US government. As AI agents enter government deployments, ASBOM requirements will follow. SkillFortify's CycloneDX output is compatible with existing SBOM tooling required by the executive order.

---

## Generating an ASBOM

### Basic Generation

```bash
skillfortify sbom ./my-agent-project
```

This outputs the CycloneDX 1.6 ASBOM to stdout.

### With Project Metadata

```bash
skillfortify sbom ./my-agent-project \
  --project-name "production-agent" \
  --project-version "2.1.0"
```

### Save to File

```bash
skillfortify sbom ./my-agent-project \
  --project-name "production-agent" \
  --project-version "2.1.0" \
  -o agent-sbom.json
```

---

## Output Format: CycloneDX 1.6

SkillFortify generates ASBOMs in CycloneDX 1.6 JSON format. CycloneDX is an OWASP standard supported by hundreds of tools in the SBOM ecosystem.

### Structure

The ASBOM contains these sections:

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.6",
  "version": 1,
  "metadata": {
    "timestamp": "2026-02-26T14:30:00Z",
    "tools": [
      {
        "name": "skillfortify",
        "version": "0.1.0"
      }
    ],
    "component": {
      "name": "production-agent",
      "version": "2.1.0",
      "type": "application"
    }
  },
  "components": [
    {
      "type": "library",
      "name": "deploy-automation",
      "version": "1.0.0",
      "properties": [
        {"name": "skillfortify:format", "value": "claude"},
        {"name": "skillfortify:trust_level", "value": "FORMALLY_VERIFIED"},
        {"name": "skillfortify:trust_score", "value": "0.85"},
        {"name": "skillfortify:status", "value": "SAFE"},
        {"name": "skillfortify:findings_count", "value": "0"}
      ]
    }
  ],
  "dependencies": [
    {
      "ref": "production-agent",
      "dependsOn": ["deploy-automation", "data-export", "weather-lookup"]
    }
  ]
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `components` | List of all skills with metadata |
| `properties` | SkillFortify-specific attributes (format, trust, findings) |
| `dependencies` | Skill dependency relationships |
| `metadata.tools` | Documents that SkillFortify generated the ASBOM |
| `metadata.timestamp` | When the ASBOM was generated |

---

## Integration with SBOM Management Tools

CycloneDX 1.6 is supported by a wide ecosystem of SBOM management tools. SkillFortify's output is compatible with:

### Dependency-Track

[OWASP Dependency-Track](https://dependencytrack.org/) is an open-source platform for SBOM management and vulnerability tracking.

```bash
# Generate ASBOM
skillfortify sbom . --project-name "my-agent" -o agent-sbom.json

# Upload to Dependency-Track (API example)
curl -X POST https://your-dtrack-instance/api/v1/bom \
  -H "X-Api-Key: YOUR_API_KEY" \
  -F "project=PROJECT_UUID" \
  -F "bom=@agent-sbom.json"
```

### Grype

[Grype](https://github.com/anchore/grype) is a vulnerability scanner for container images and SBOMs.

```bash
# Generate ASBOM
skillfortify sbom . -o agent-sbom.json

# Scan with Grype (for any known CVEs in skill dependencies)
grype sbom:agent-sbom.json
```

### Other Compatible Tools

Any tool that accepts CycloneDX 1.6 JSON can consume SkillFortify's ASBOM output, including:

- Sonatype Lifecycle
- Snyk Container
- JFrog Xray
- IBM Concert
- FOSSA

---

## CI/CD Integration

### Generate ASBOM on Every Build

```yaml
name: Agent Supply Chain Security
on: [push, pull_request]

jobs:
  sbom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install SkillFortify
        run: pip install skillfortify

      - name: Generate ASBOM
        run: |
          skillfortify sbom . \
            --project-name "${{ github.repository }}" \
            --project-version "${{ github.sha }}" \
            -o agent-sbom.json

      - name: Upload ASBOM artifact
        uses: actions/upload-artifact@v4
        with:
          name: agent-sbom
          path: agent-sbom.json
```

### Archive ASBOMs for Audit Trail

Store ASBOMs for every release to maintain a complete audit trail of your agent's skill inventory over time. When a vulnerability is disclosed in a skill, you can immediately identify which releases are affected.

---

## ASBOM Best Practices

1. **Generate on every release**: Include ASBOM generation in your release pipeline
2. **Version control the output**: Commit ASBOMs alongside your code for traceability
3. **Automate monitoring**: Feed ASBOMs into Dependency-Track or similar tools for continuous monitoring
4. **Include in vendor documentation**: When providing agent solutions to clients, include the ASBOM as part of security documentation
5. **Combine with lockfiles**: Use `skillfortify lock` alongside `skillfortify sbom` -- the lockfile ensures reproducibility, the ASBOM provides compliance documentation

---

## Further Reading

- **[Skill Lock JSON](Skill-Lock-JSON)** -- Lockfile format for reproducible configurations
- **[Trust Levels](Trust-Levels)** -- How trust levels in the ASBOM are computed
- **[CLI Reference](CLI-Reference)** -- Full `skillfortify sbom` command options
- **[Getting Started](Getting-Started)** -- First scan and ASBOM generation walkthrough

---

*SkillFortify is part of the [AgentAssert](https://agentassert.com) research suite -- building formal foundations for trustworthy AI agents.*
