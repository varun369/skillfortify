# Formal Foundations -- The Mathematics Behind SkillFortify

SkillFortify is grounded in formal methods research -- the same discipline used to verify cryptographic protocols, flight control software, and hardware designs. This page explains the five theorems that form SkillFortify's theoretical foundation, the formal models they use, and what they guarantee in practice. The goal is accessibility: you do not need a mathematics background to understand what these theorems mean for your agent skill security. For the full proofs, see the [research paper](https://doi.org/10.5281/zenodo.18787663).

---

## Why Formal Methods for Agent Skills

Every security tool makes implicit assumptions about what attacks are possible and what detection can catch. Most agent skill scanners make these assumptions informally -- the tool author writes rules based on attacks they have seen or can imagine. This approach has two problems:

1. **Completeness**: There is no way to know if you have covered all possible attacks. Novel attack techniques bypass rules that were never written.
2. **Soundness**: When the tool reports "no issues found," there is no mathematical basis for concluding the skill is safe.

Formal methods address both problems by constructing mathematical models of the system (skills, attackers, trust relationships) and proving properties about those models. The properties are then guaranteed to hold for any input that falls within the model's scope -- not just the inputs the developer tested against.

---

## The Five Theorems

### Theorem 1: Attacker Completeness

**What it says:** The DY-Skill threat model captures all possible symbolic attacks on the agent skill supply chain. Any real-world attack on the skill lifecycle maps to a sequence of operations in the formal model.

**What it means in practice:** When SkillFortify analyzes a skill, it considers the full space of possible attacks -- not just a list of known attack patterns. The threat model covers every stage of the skill lifecycle: installation, loading, configuration, execution, and persistence. If an attack is possible at any stage, the model represents it.

**Why it matters:** Heuristic scanners detect attacks they have seen before. SkillFortify's threat model covers attacks that have not been seen yet, because the model is defined over the structure of the skill supply chain, not over a database of known incidents.

### Theorem 2: Analysis Soundness

**What it says:** If SkillFortify's static analysis reports no capability violations, the skill provably does not exceed its declared capabilities within the formal model. There are no false negatives for capability-level threats.

**What it means in practice:** When SkillFortify says a skill is SAFE, that statement is backed by a formal proof. The skill has been verified to only access the resources and perform the actions it declares. If the skill secretly accesses the network while claiming to only read local files, SkillFortify will detect it.

**Why it matters:** This is the soundness guarantee. Other tools say "no findings does not mean no risk." SkillFortify says: no findings means the formal capability bounds are assured. This is the fundamental difference between heuristic scanning and formal verification.

### Theorem 3: Non-Amplification

**What it says:** A skill executing within SkillFortify's capability model cannot acquire capabilities beyond those explicitly granted. Authority cannot be amplified through indirect means.

**What it means in practice:** If a skill is granted read-only access to the file system, it cannot escalate to write access, network access, or command execution -- even through clever indirect techniques like manipulating other skills, exploiting shared resources, or chaining legitimate capabilities together.

**Why it matters:** Privilege escalation is one of the most common attack patterns in security. Non-amplification guarantees that the capabilities you grant are the maximum capabilities the skill can exercise. There is no path from limited access to unlimited access within the model.

### Theorem 4: Resolution Soundness

**What it says:** If the dependency resolver finds a valid configuration, all version constraints, conflict constraints, and security bounds are satisfied simultaneously.

**What it means in practice:** When `skillfortify lock` generates a lockfile, every skill in that lockfile has been verified to be mutually compatible -- no version conflicts, no capability conflicts, and no security constraint violations. The configuration is guaranteed to be internally consistent.

**Why it matters:** In complex agent configurations with many skills, dependency conflicts can create subtle security gaps. A skill that is safe in isolation may create a vulnerability when combined with another skill. The SAT-based resolver considers all constraints simultaneously, not sequentially.

### Theorem 5: Trust Monotonicity

**What it says:** Adding positive evidence to a skill's trust assessment never decreases its trust score. Trust propagation through dependency chains preserves ordering.

**What it means in practice:** The trust scoring system behaves predictably. Getting a code review, adding a signature, or receiving community endorsement can only increase (or maintain) a skill's trust level -- never decrease it. And if skill A trusts skill B, and skill B's trust score increases, skill A's effective trust score also increases (or stays the same).

**Why it matters:** Trust scoring systems that behave non-monotonically are confusing and unreliable. If adding positive evidence could lower a trust score, developers would not trust the scoring system itself. Monotonicity is a basic sanity property that ensures the trust model behaves as expected.

---

## The DY-Skill Model

The Dolev-Yao (DY) model is a foundational framework in cryptographic protocol analysis. Originally developed in 1983, it models an attacker who can intercept, modify, replay, and forge messages in a communication protocol. The DY model has been used to find vulnerabilities in SSL/TLS, Kerberos, and dozens of other security protocols.

SkillFortify adapts this model for the agent skill supply chain. The **DY-Skill model** defines:

- **Agents**: Developers, skill authors, registries, agent runtimes, and attackers
- **Messages**: Skill packages, manifests, capability declarations, configuration files
- **Operations**: Install, load, configure, execute, persist, compose
- **Attacker capabilities**: Intercept skill packages, modify manifests, forge capability declarations, squat on namespaces, compromise registries

The attacker in the DY-Skill model is powerful: they control the network between the developer and the registry, can publish skills under any name, and can modify skill content in transit. This is conservative by design -- if a defense works against this powerful attacker, it works against any less powerful attacker.

The completeness of this model (Theorem 1) means that any real-world attack on the skill supply chain -- including ClawHavoc, CVE-2026-25253, and the attacks catalogued in the MalTool dataset -- maps to a sequence of DY-Skill operations.

---

## The Capability Lattice

SkillFortify models skill permissions as a mathematical lattice -- a partially ordered set where every pair of elements has a unique least upper bound (join) and greatest lower bound (meet).

### What This Means

Every capability (file system access, network access, command execution, environment variable access) has defined access levels that form a hierarchy:

```
EXECUTE > WRITE > READ > NONE
```

The lattice structure enables precise reasoning about capability relationships:

- **Comparison**: Is capability A more powerful than capability B?
- **Combination**: What is the minimum capability that covers both A and B?
- **Restriction**: What is the maximum capability that is weaker than both A and B?

### Why a Lattice

The lattice structure guarantees that capability inference is well-defined and deterministic. Given any set of observed behaviors, there is exactly one minimal capability set that covers all of them. This is what enables Theorem 2 (soundness) -- the analysis can compute the exact capability requirements of a skill without over-approximation or under-approximation at the capability level.

### POLA Compliance

The Principle of Least Authority (POLA) states that a component should be granted only the minimum capabilities it needs. The capability lattice makes POLA checking formal: compare the inferred capabilities (what the skill needs) against the declared capabilities (what the skill claims to need). Any gap is a potential violation.

---

## The Trust Algebra

SkillFortify computes trust scores using a formal algebraic model with four signal categories:

| Signal | What It Measures |
|--------|-----------------|
| **Provenance** | Where did this skill come from? Is the author identifiable? Is there a cryptographic signature? |
| **Behavioral** | Does the skill's behavior match its capability declaration? Does it pass formal analysis? |
| **Community** | Has the skill been reviewed? How widely is it used? Are there reported issues? |
| **Historical** | How long has this skill existed? Has it been updated recently? Is the maintainer active? |

Each signal contributes a score between 0 and 1. The signals are combined using a weighted aggregation that produces an overall trust score, which maps to a trust level (L0 through L3).

### Key Properties

The trust algebra satisfies two critical properties:

1. **Monotonicity** (Theorem 5): Adding positive evidence never decreases the score
2. **Propagation soundness**: Trust scores propagate correctly through dependency chains -- a skill that depends on a highly-trusted skill receives appropriate trust credit, while a skill that depends on an untrusted skill is penalized

### Trust Decay

Skills that are not maintained become riskier over time. The trust algebra includes a decay function that gradually reduces the historical signal for skills that have not been updated. This ensures that abandoned skills do not retain high trust levels indefinitely.

See [Trust Levels](Trust-Levels) for the practical trust level thresholds and how to improve a skill's trust score.

---

## SAT-Based Dependency Resolution

When multiple agent skills are installed together, they may have dependencies, version constraints, and conflicting requirements. SkillFortify uses **Boolean satisfiability (SAT) solving** to find valid configurations.

### How It Works

1. **Encode constraints**: Each skill's version requirements, capability requirements, and conflict declarations are encoded as Boolean formulas
2. **Add security constraints**: Minimum trust levels, maximum capability bounds, and forbidden capability combinations are added as additional clauses
3. **Solve**: A SAT solver finds an assignment that satisfies all constraints simultaneously, or proves that no valid configuration exists
4. **Output**: The valid configuration becomes the lockfile

### Why SAT

Traditional dependency resolvers (like those in npm or pip) use heuristic backtracking algorithms. They work well for version constraints but cannot handle the additional security constraints that SkillFortify needs. SAT solving provides:

- **Completeness**: If a valid configuration exists, the solver will find it
- **Soundness** (Theorem 4): If the solver returns a configuration, all constraints are satisfied
- **Expressiveness**: Arbitrary Boolean constraints can be encoded, including complex security policies

---

## How the Pieces Fit Together

The five theorems and four models are not independent -- they form a coherent system:

```
DY-Skill Model (Threat Model)
    |
    | defines what attacks are possible
    v
Capability Lattice (Permission Model)
    |
    | defines what skills are allowed to do
    v
Static Analysis (Verification Engine)
    |
    | proves skills stay within capability bounds (Theorem 2)
    | proves capabilities cannot be amplified (Theorem 3)
    v
SAT Resolver (Dependency Manager)
    |
    | finds valid configurations satisfying all constraints (Theorem 4)
    v
Trust Algebra (Trust Assessment)
    |
    | scores skills based on evidence (Theorem 5)
    v
Output: Findings, Lockfile, Trust Levels, ASBOM
```

Theorem 1 (attacker completeness) underpins the entire system: because the threat model is complete, the analysis built on top of it covers the full attack space. Theorems 2 and 3 guarantee that the analysis engine correctly identifies capability violations. Theorem 4 ensures that the dependency resolver produces valid configurations. Theorem 5 ensures that trust scoring behaves predictably.

---

## Connection to AgentAssert

SkillFortify's formal foundations complement the AgentAssert framework:

| AgentAssert | SkillFortify |
|-------------|-------------|
| Behavioral contracts specify what agents SHOULD do | Capability model specifies what skills CAN do |
| Runtime enforcement catches behavioral drift | Static analysis catches capability violations before runtime |
| Composition conditions (C1-C4) for agent pipelines | Composition analysis for skill interactions |
| ContractSpec DSL for declaring agent behavior | Capability declarations for skill permissions |

The two systems address the same fundamental problem -- ensuring AI agents behave correctly -- from complementary angles. AgentAssert works at the agent level (behavior over time). SkillFortify works at the skill level (what individual components can access).

---

## Known Limitations of the Formal Model

Every formal model has scope boundaries. SkillFortify's formal guarantees apply within the model's assumptions. The paper documents these limitations explicitly:

1. **Install-time attacks**: Typosquatting and dependency confusion require registry-level analysis that is outside the scope of local static analysis. This accounts for the 6% recall gap in the benchmark.
2. **Runtime behavior**: Static analysis reasons about what a skill *can* do, not what it *will* do at runtime. A skill that is formally safe may still behave unexpectedly if the agent runtime has vulnerabilities.
3. **Semantic understanding**: The formal model analyzes capabilities at the resource level (file system, network, environment). It does not reason about the semantic content of data -- for example, whether a skill is exfiltrating *sensitive* files versus reading *benign* files.
4. **Obfuscation**: Heavily obfuscated skill code may resist static analysis. The formal guarantees assume the analysis can parse the skill's structure.

These limitations are inherent to the approach and are documented for transparency. Note that limitation 1 (install-time attacks) is partially addressed in v0.3.0 through registry scanning, which evaluates skills at the registry level before installation, extending the DY-Skill model's coverage to the pre-installation phase of the supply chain.

---

## Glossary of Formal Terms

| Term | Definition |
|------|------------|
| **Soundness** | If the analysis says "safe," it is correct (no false negatives for capability-level threats) |
| **Completeness** (of threat model) | Every possible attack is represented in the model |
| **Monotonicity** | Adding positive evidence never decreases the metric |
| **Lattice** | A mathematical structure with well-defined join and meet operations |
| **SAT solving** | Finding variable assignments that satisfy a Boolean formula |
| **Dolev-Yao** | A standard attacker model for protocol security analysis |
| **POLA** | Principle of Least Authority -- grant only the minimum needed |
| **Non-amplification** | Authority cannot grow beyond what was explicitly granted |
| **Abstract interpretation** | A theory for computing sound approximations of program behavior |

---

## Further Reading

- **[Research Paper](https://doi.org/10.5281/zenodo.18787663)** -- Full 31-page paper with all five proofs, benchmark methodology, and experimental results
- **[AgentAssert Paper](https://arxiv.org/abs/2602.22302)** -- The companion framework for agent behavioral contracts
- **[SkillFortifyBench](SkillFortifyBench)** -- The 540-skill benchmark used to evaluate the formal analysis
- **[Trust Levels](Trust-Levels)** -- Practical guide to trust scores and levels
- **[Why SkillFortify](Why-SkillFortify)** -- The problem and why formal analysis is the right approach

---

*SkillFortify is part of the [AgentAssert](https://agentassert.com) research suite -- building formal foundations for trustworthy AI agents.*
