# SkillFortifyBench -- The Agent Skill Security Benchmark

SkillFortifyBench is a curated dataset of 540 agent skills designed to evaluate the accuracy of agent skill security tools. It contains both malicious and benign samples across all three major agent skill formats, covering 13 attack types derived from real-world incidents. SkillFortifyBench is the first public benchmark for agent skill security analysis with ground-truth labels, standardized evaluation metrics, and reproducible methodology.

---

## Overview

| Property | Value |
|----------|-------|
| **Total skills** | 540 |
| **Malicious skills** | 270 |
| **Benign skills** | 270 |
| **Attack types covered** | 13 |
| **Formats** | Claude Code, MCP, OpenClaw |
| **Ground truth** | All skills labeled with verified classifications |
| **Source** | Derived from ClawHavoc, MalTool, and documented incidents |

---

## Why a Benchmark Is Needed

Before SkillFortifyBench, there was no standardized way to evaluate agent skill security tools. Each tool claimed effectiveness based on its own test cases, making meaningful comparison impossible. The absence of a shared benchmark meant:

- No way to measure false positive rates across tools
- No way to compare recall on the same malicious samples
- No ground truth for what "malicious" means in the context of agent skills
- No reproducible evaluation methodology

SkillFortifyBench addresses all of these gaps.

---

## Construction Methodology

### Malicious Samples (270 skills)

Malicious samples were derived from three verified sources:

1. **ClawHavoc campaign samples**: Skills based on the attack patterns documented in the ClawHavoc investigation (1,200+ malicious skills that infiltrated the OpenClaw marketplace in January-February 2026)

2. **MalTool dataset patterns**: Attack techniques from the MalTool research paper (6,487 malicious agent tools catalogued in February 2026), adapted to the three supported skill formats

3. **CVE-2026-25253 variants**: Remote code execution patterns derived from the first agent-software CVE, including variations that exploit installation, loading, and execution phases

### The 13 Attack Types

| # | Attack Type | Description |
|---|-------------|-------------|
| 1 | **Data exfiltration** | Skill reads sensitive files or environment variables and sends them to an external endpoint |
| 2 | **Credential theft** | Skill specifically targets API keys, tokens, and authentication credentials |
| 3 | **Remote code execution** | Skill executes arbitrary commands on the host system |
| 4 | **Privilege escalation** | Skill attempts to gain capabilities beyond its declaration |
| 5 | **Prompt injection** | Skill injects instructions into the agent's prompt or context |
| 6 | **Configuration tampering** | Skill modifies agent or system configuration files |
| 7 | **Persistence installation** | Skill installs backdoors or persistent access mechanisms |
| 8 | **Supply chain redirect** | Skill redirects dependency resolution to malicious sources |
| 9 | **Information disclosure** | Skill leaks system information (OS, paths, installed software) |
| 10 | **Denial of service** | Skill consumes excessive resources or causes agent crashes |
| 11 | **Capability masking** | Skill declares minimal capabilities but requires more at runtime |
| 12 | **Dependency exploitation** | Skill exploits transitive dependencies for malicious purposes |
| 13 | **Environment manipulation** | Skill modifies environment variables or system state |

### Benign Samples (270 skills)

Benign samples represent legitimate agent skills across common use cases:

- File management and organization
- Web search and information retrieval
- Code analysis and development assistance
- Data formatting and transformation
- Communication and notification
- Deployment and DevOps automation
- Documentation and reporting

Each benign sample has been verified to require only the capabilities it declares -- no hidden behaviors, no excessive permissions, no undeclared resource access.

### Format Distribution

Skills are distributed across all three supported formats to ensure format-agnostic evaluation:

| Format | Malicious | Benign | Total |
|--------|-----------|--------|-------|
| Claude Code | 90 | 90 | 180 |
| MCP | 90 | 90 | 180 |
| OpenClaw | 90 | 90 | 180 |

---

## Results: SkillFortify on SkillFortifyBench

| Metric | Value |
|--------|-------|
| **Precision** | 100% (zero false positives) |
| **Recall** | 94.12% |
| **F1 Score** | 96.95% |
| **Average analysis time** | 2.55 ms per skill |

### What the Numbers Mean

- **100% precision**: SkillFortify did not flag any benign skill as malicious across all 540 test cases. When it reports a finding, it is backed by formal analysis -- not a heuristic guess that might be wrong.

- **94.12% recall**: SkillFortify detected 254 of 270 malicious skills. The 16 undetected samples fall into two categories:
  - Install-time attacks (typosquatting, dependency confusion) that require registry-level analysis outside the scope of local static analysis
  - Heavily obfuscated payloads that resist static capability inference

- **96.95% F1**: The harmonic mean of precision and recall, representing the overall balance between catching threats and avoiding false alarms.

### The Recall Gap

The 6% recall gap is documented transparently in the paper as a known limitation. The undetected attacks require information that is not available during local analysis:

- **Typosquatting** requires comparing skill names against a registry of legitimate packages -- the attack is in the name, not the code
- **Dependency confusion** requires knowledge of internal vs external package namespaces -- the attack is in the resolution order, not the skill content

These attack types are addressed in v0.3.0 with registry scanning capabilities.

---

## Framework Coverage

The benchmark was originally constructed for three core skill formats (Claude Code, MCP, OpenClaw). As of v0.3.0, SkillFortify supports 22 agent frameworks. The formal analysis engine and detection methodology validated on SkillFortifyBench applies uniformly across all supported frameworks -- the capability lattice and threat model are format-agnostic by design. Skills from any supported framework are analyzed against the same formal model and theorems.

---

## Running the Benchmark Yourself

### Prerequisites

```bash
pip install skillfortify[dev]
```

### Run the Full Benchmark

```bash
# Clone the repository
git clone https://github.com/varun369/skillfortify.git
cd skillfortify

# Run benchmark tests
pytest tests/benchmark/ -v
```

### Run by Format

```bash
# Claude Code skills only
pytest tests/benchmark/ -v -k "claude"

# MCP configurations only
pytest tests/benchmark/ -v -k "mcp"

# OpenClaw manifests only
pytest tests/benchmark/ -v -k "claw"
```

### Run by Attack Type

```bash
# Data exfiltration samples
pytest tests/benchmark/ -v -k "exfiltration"

# Privilege escalation samples
pytest tests/benchmark/ -v -k "escalation"
```

---

## Contributing New Test Skills

The benchmark is open for community contributions. To add new test skills:

### Adding Malicious Samples

1. Create the skill file in the appropriate format (Claude, MCP, or OpenClaw)
2. Document the attack type and expected behavior
3. Classify the attack into one of the 13 types (or propose a new type)
4. Verify that the sample is detectable by SkillFortify (or document it as a gap)
5. Submit a pull request to the [benchmark directory](https://github.com/varun369/skillfortify/tree/main/tests/benchmark)

### Adding Benign Samples

1. Create a legitimate skill that performs a useful function
2. Verify that it only uses declared capabilities
3. Confirm SkillFortify reports it as SAFE (zero false positives is a hard requirement)
4. Submit a pull request

### Contribution Guidelines

- Every sample must have a ground-truth label (malicious or benign)
- Malicious samples must specify which attack type(s) they represent
- Benign samples must be verified to have no undeclared capabilities
- All samples must be in valid format for their declared type
- Include a brief description of what the skill does (or claims to do)

---

## Comparison with Other Benchmarks

SkillFortifyBench is the first benchmark specifically designed for agent skill security. The closest related work:

| Benchmark | Focus | Size | Agent Skills? | Ground Truth? |
|-----------|-------|------|---------------|---------------|
| **SkillFortifyBench** | Agent skill security | 540 | Yes (3 formats) | Yes |
| MalTool dataset | Malicious tool cataloguing | 6,487 | Partial | Partial |
| ToolShield eval set | Tool safety | ~100 | Partial | Yes |
| OWASP Benchmark | Web application security | 2,740 | No | Yes |

SkillFortifyBench differs from MalTool in that it includes verified benign samples for false positive measurement, covers all three major skill formats, and provides standardized evaluation metrics. MalTool is an excellent attack catalogue but was not designed as an evaluation benchmark.

---

## Further Reading

- **[Research Paper](https://doi.org/10.5281/zenodo.18787663)** -- Full benchmark methodology, statistical analysis, and comparison tables
- **[Formal Foundations](Formal-Foundations)** -- The theorems that guarantee SkillFortify's analysis properties
- **[Why SkillFortify](Why-SkillFortify)** -- The threat landscape that motivated the benchmark

---

*SkillFortify is part of the [AgentAssert](https://agentassert.com) research suite -- building formal foundations for trustworthy AI agents.*
