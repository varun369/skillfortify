# Why SkillFortify -- Formal Analysis for Agent Skill Security

Agent skills are the new software dependencies. Developers install them into AI agent projects the same way they installed npm packages in 2015: quickly, without auditing what the code actually does. The difference is that agent skills can read your files, execute shell commands, make network requests, and inject prompts into your AI -- all with a single install. The attack surface is larger, the consequences are worse, and the security tooling is years behind.

SkillFortify exists because every other defense tool on the market today relies on heuristic pattern matching -- and heuristics have a fundamental ceiling that formal analysis does not.

---

## The Problem: Agent Skill Supply Chains Are Under Active Attack

### The Incidents

The agent skill ecosystem reached a tipping point in early 2026. Three events in rapid succession exposed how vulnerable the supply chain is:

**ClawHavoc Campaign (January-February 2026)**

Over 1,200 malicious skills were planted in the largest AI agent marketplace. The campaign deployed credential stealers, data exfiltration payloads, and remote access tools disguised as legitimate agent capabilities. Developers installing popular-sounding skill names unknowingly gave attackers access to their file systems, environment variables, and API keys.

This was not a proof-of-concept. It was a sustained, organized attack campaign that compromised real developer environments.

**CVE-2026-25253 (January 27, 2026)**

The first Common Vulnerabilities and Exposures identifier assigned to agent skill software. A remote code execution vulnerability in the OpenClaw agent framework allowed a crafted skill manifest to execute arbitrary commands on the host system during installation -- before the developer ever ran the skill. A proof-of-concept exploit was published with 75 stars on GitHub.

This CVE established that agent skill installation is itself an attack vector, not just skill execution.

**MalTool Dataset (February 12, 2026)**

Researchers catalogued **6,487 malicious agent tools** in a systematic study. The critical finding: conventional security scanners, including VirusTotal, fail to detect the majority of these malicious tools. Agent-specific malware uses techniques that traditional signature-based detection was never designed to catch -- prompt injection payloads, capability escalation through legitimate-looking API calls, and data exfiltration disguised as normal skill behavior.

### The Pattern

These incidents are not isolated. They follow the exact pattern that played out in the traditional software supply chain:

| Software Supply Chain | Agent Skill Supply Chain |
|----------------------|------------------------|
| **event-stream** (2018): Malicious code injected into popular npm package | **ClawHavoc** (2026): 1,200+ malicious skills in agent marketplace |
| **ua-parser-js** (2021): Crypto-miner injected via compromised maintainer | **CVE-2026-25253**: RCE through crafted skill manifest |
| **SolarWinds** (2020): State-sponsored supply chain compromise | **MalTool**: 6,487 malicious tools evading conventional detection |
| **Log4Shell** (2021): Ubiquitous library with critical vulnerability | Next incident: ? |

The software industry took years to build defenses -- npm audit (2018), Snyk (2015), Socket.dev (2022), SLSA framework (2021), Sigstore (2021). The agent skill ecosystem has none of these defenses today.

---

## Why Heuristic Scanning Is Not Enough

After ClawHavoc, over a dozen scanning tools appeared in February 2026 alone. All of them use some form of heuristic detection:

- **Pattern matching**: Regular expressions and YARA rules that flag known malicious code patterns
- **LLM-as-judge**: Sending skill code to a language model and asking "is this malicious?"
- **Signature databases**: Maintaining lists of known-bad hashes and indicators of compromise
- **Behavioral heuristics**: Flagging suspicious behaviors like network calls or file system access

These approaches are better than nothing. But they share three fundamental limitations:

### Limitation 1: Reactive, Not Proactive

Heuristic scanners can only detect what they have already seen. A novel attack that does not match any existing pattern, rule, or signature passes through undetected. Every new attack technique requires a new rule to be written and deployed. The attacker is always one step ahead.

### Limitation 2: No Formal Guarantees

One of the most widely-used agent skill scanners states explicitly in its documentation:

> "No findings does not mean no risk."

This is the honest truth about heuristic scanning. When the tool reports zero findings, you cannot conclude that the skill is safe. You can only conclude that the tool did not find anything it was looking for. The distinction matters enormously for security-critical deployments.

### Limitation 3: High False Positive Rates Under Adversarial Pressure

Heuristic rules are tuned to balance precision and recall on known datasets. An attacker who knows the rules can craft payloads that fall just outside the detection boundary. Tightening the rules increases false positives. Loosening them increases false negatives. There is no principled way to resolve this trade-off within the heuristic framework.

### The Analogy

The difference between heuristic scanning and formal analysis is the difference between a spell checker and a type system:

- **Spell checkers** catch known typos. They are useful but cannot guarantee that your text is error-free. A spell checker will not catch "their" when you meant "there."
- **Type systems** prevent entire categories of errors by construction. If the code compiles, certain classes of bugs are impossible. The guarantee is structural, not pattern-based.

SkillFortify is the type system for agent skills.

---

## What Formal Analysis Provides That Heuristics Cannot

### Soundness Guarantees

SkillFortify's static analysis is **sound**: if the analysis reports no capability violations, the skill provably cannot exceed its declared capabilities within the formal model. This is not a statistical claim -- it is a mathematical property proven as Theorem 2 in the paper.

When SkillFortify says a skill is safe, that statement is backed by a formal proof, not a pattern match.

### Capability-Level Reasoning

Instead of asking "does this skill contain known malicious patterns?", SkillFortify asks "what capabilities does this skill actually require, and do they exceed what it declares?" This is a fundamentally different question. It catches novel attacks that no heuristic scanner has ever seen, because it reasons about what a skill *can do*, not what it *looks like*.

### Mathematical Threat Model

SkillFortify's threat model is formalized and complete. Based on the Dolev-Yao framework (a foundational model in cryptographic protocol analysis), the DY-Skill model captures all possible symbolic attacks on the skill supply chain. Any real-world attack maps to a sequence of operations in the model. This means the analysis is not ad-hoc -- it covers the full attack space systematically.

### Composition Analysis

When skill A and skill B are installed together, new security properties (and risks) can emerge from their interaction. Heuristic scanners analyze skills in isolation. SkillFortify analyzes the composition of skills -- what happens when they share resources, exchange data, or interact through the agent runtime.

---

## Comparison: SkillFortify vs Current Tools

| Capability | SkillFortify | Snyk Agent Scan | Cisco skill-scanner | SkillShield.io | ToolShield | MCPShield |
|-----------|:------------:|:---------------:|:-------------------:|:--------------:|:----------:|:---------:|
| **Formal verification** | Yes | No | No | No | No | No |
| **Soundness guarantee** | 5 theorems | None | None | None | None | None |
| **False positive rate** | 0% (benchmark) | Not published | Not published | Not published | Not published | Not published |
| **"No findings = safe" caveat** | No caveat needed | N/A | "No findings != no risk" | N/A | N/A | N/A |
| **Capability-level analysis** | Formal model | No | No | No | No | No |
| **Dependency graph analysis** | SAT-based | Partial | No | No | No | No |
| **Lockfile generation** | skill-lock.json | No | No | No | No | No |
| **Trust score algebra** | Formal | No | No | No | No | No |
| **ASBOM (CycloneDX)** | 1.6 | No | No | No | No | No |
| **Agent frameworks** | 22 | Limited | 2-3 | Limited | 1-2 | 1 |
| **System auto-discovery** | 23 IDE profiles | No | No | No | No | No |
| **HTML dashboard** | Yes | No | No | No | No | No |
| **Registry scanning** | Yes | No | No | No | No | No |
| **Peer-reviewed paper** | 31 pages, 5 theorems | No | No | No | 1 paper | No |
| **Runs offline** | Yes | No (cloud) | Yes | Unknown | Yes | Yes |
| **License** | MIT (free) | Freemium | Free | Unknown | Free | Free |

### Key Differentiators

1. **Formal verification vs heuristic detection**: SkillFortify is the only tool grounded in a formal threat model with proven soundness properties. Every other tool uses pattern matching, rules, or LLM-based detection.

2. **Zero false positives**: On the 540-skill SkillFortifyBench benchmark, SkillFortify achieved 100% precision. This is a direct consequence of the sound formal model.

3. **Full supply chain coverage**: Lockfile generation, dependency resolution, formal trust scoring, CycloneDX ASBOM generation, registry scanning, system-wide auto-discovery, and enterprise dashboards. Other tools scan for threats but do not address the broader supply chain workflow.

4. **22 agent frameworks, 23 IDE profiles**: The broadest coverage of any tool in this space, with automatic discovery of every agent skill configuration across your development environment.

---

## The Supply Chain Perspective

The agent skill problem is fundamentally a supply chain problem. Every piece of the traditional software supply chain has an agent skill equivalent -- but the agent skill ecosystem lacks the defenses that the software industry built over the last decade:

| Software Supply Chain Defense | Agent Skill Equivalent | Status |
|-------------------------------|----------------------|--------|
| `npm audit` / `pip-audit` (vulnerability database) | Agent skill vulnerability database | Does not exist |
| `package-lock.json` / `Cargo.lock` (lockfile) | `skill-lock.json` | **SkillFortify provides this** |
| SBOM (CycloneDX, SPDX) | Agent Skill BOM (ASBOM) | **SkillFortify provides this** |
| Sigstore / cosign (code signing) | Skill signing | Planned (SkillFortify v1.0) |
| SLSA framework (graduated trust) | Agent skill trust levels | **SkillFortify provides this** |
| Socket.dev (behavioral analysis) | Formal behavioral analysis | **SkillFortify provides this** |
| Snyk / Dependabot (automated scanning) | Automated skill scanning | **SkillFortify provides this** |

With v0.3.0, SkillFortify added registry scanning -- the ability to evaluate skills directly from package registries before they are installed. This closes the pre-installation gap and makes SkillFortify a complete supply chain security solution, from marketplace evaluation through runtime verification.

SkillFortify is not just a scanner -- it is the supply chain security infrastructure for the agent skill ecosystem.

---

## Who Needs SkillFortify

### Developers Building with Agent Skills

If you install agent skills from any source -- across any of the 22 supported agent frameworks -- those skills can access your files, environment, and network. SkillFortify auto-discovers every skill configuration across your development environment (23 IDE profiles supported) and tells you exactly what capabilities each skill requires and whether they exceed what the skill declares. You can also scan registry packages before installing them.

### Security Teams at Enterprises

After SolarWinds and Log4j, supply chain security is a board-level concern at every Fortune 500 company. As enterprises adopt AI agents, the skill supply chain becomes the next frontier. SkillFortify provides the compliance documentation (CycloneDX SBOM), audit trails (lockfiles), interactive HTML dashboards for reporting, and formal verification that enterprise security teams require.

### AI Agent Framework Authors

If you maintain an agent framework or skill marketplace, SkillFortify can verify skills before they are published. Preventing malicious skills from entering the registry is more effective than detecting them after installation.

### Researchers in AI Safety

The DY-Skill threat model, capability lattice, and trust algebra are contributions to the formal methods and AI safety literature. The full paper with proofs is available for extension and citation.

### DevOps and Platform Engineers

If you manage agent infrastructure or deployment pipelines, SkillFortify integrates into CI/CD workflows with JSON output, HTML dashboards, and consistent exit codes. Use system-wide discovery to audit every agent configuration across developer workstations, or add `skillfortify scan . --format json` to your pipeline to catch skill security issues before they reach production.

---

## The Bottom Line

Agent skills are powerful. They give AI agents the ability to read files, execute commands, access networks, and interact with external services. That power comes with risk -- and that risk needs to be managed with the same rigor applied to any other software supply chain.

Heuristic scanning is a good start but has a known ceiling. Formal verification raises that ceiling by providing mathematical guarantees about what skills can and cannot do. SkillFortify brings formal verification to the agent skill ecosystem for the first time -- with support for 22 agent frameworks, system-wide auto-discovery, interactive dashboards for enterprise reporting, and registry scanning to evaluate skills before installation.

---

## Next Steps

- **[Getting Started](Getting-Started)** -- Install SkillFortify and run your first scan
- **[Formal Foundations](Formal-Foundations)** -- Understand the five theorems and what they guarantee
- **[SkillFortifyBench](SkillFortifyBench)** -- Explore the benchmark and reproduce the results

---

*SkillFortify is part of the [AgentAssert](https://agentassert.com) research suite -- building formal foundations for trustworthy AI agents.*
