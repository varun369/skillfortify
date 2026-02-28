# Trust Levels -- Graduated Trust for Agent Skills

SkillFortify assigns every agent skill a trust level based on a multi-signal trust score. The trust model is inspired by the SLSA (Supply-chain Levels for Software Artifacts) framework, adapted for the unique characteristics of agent skill ecosystems. Trust levels provide a clear, actionable assessment of how much confidence you should place in each skill -- and what it would take to increase that confidence.

---

## The Four Trust Levels

### L0: UNSIGNED (Score < 0.25)

**Risk Level: HIGH**

The skill has no verified provenance. Its origin is unknown or unverifiable. There is no cryptographic signature, no community review, and limited or no behavioral analysis.

**What this means:** Treat this skill as untrusted. Do not use it in production without thorough manual review. It may be legitimate, but there is no evidence to confirm it.

**Common for:** Newly created skills, skills from unknown authors, skills without any published metadata.

### L1: SIGNED (Score >= 0.25, < 0.50)

**Risk Level: MODERATE**

The skill has basic provenance established. The author is identifiable, and there may be a cryptographic signature or basic metadata. However, the skill has limited community verification and behavioral analysis may be incomplete.

**What this means:** The skill has some accountability -- you know who published it. But the content has not been independently verified. Suitable for development and testing environments. Requires additional verification for production use.

**Common for:** Skills from known authors with limited track record, newly published skills with signed manifests.

### L2: COMMUNITY_VERIFIED (Score >= 0.50, < 0.75)

**Risk Level: LOW**

The skill has been signed, has passed behavioral analysis, and has met a community review threshold. Multiple positive signals confirm its legitimacy: usage history, community feedback, and basic behavioral compliance.

**What this means:** Multiple independent signals agree that this skill is what it claims to be. Suitable for most production environments. Continue monitoring for changes.

**Common for:** Popular skills with active maintainers, skills from established authors with good track records, skills that have been in use for a meaningful period.

### L3: FORMALLY_VERIFIED (Score >= 0.75)

**Risk Level: MINIMAL**

The highest assurance level. The skill is signed, community-verified, and has passed formal capability analysis. SkillFortify has generated a mathematical proof that the skill cannot exceed its declared capabilities.

**What this means:** Maximum confidence. The skill has the strongest available evidence of safety: cryptographic identity, community validation, and formal verification. Suitable for security-critical and compliance-sensitive deployments.

**Common for:** Widely-used skills that have been thoroughly analyzed, skills from trusted organizations, core infrastructure skills.

---

## How Trust Scores Are Computed

The trust score is a weighted aggregation of four signal categories, each scoring between 0 and 1:

### Signal 1: Provenance (Source Identity)

| Factor | Score Contribution |
|--------|--------------------|
| Unknown author, no signature | 0.0 |
| Author identified but unsigned | 0.25 |
| Cryptographically signed by author | 0.50 |
| Signed + verified organizational affiliation | 0.75 |
| Signed + org-verified + reproducible build | 1.0 |

### Signal 2: Behavioral (Analysis Results)

| Factor | Score Contribution |
|--------|--------------------|
| Analysis failed or not performed | 0.0 |
| Analysis completed with CRITICAL findings | 0.25 |
| Analysis completed with HIGH/MEDIUM findings | 0.50 |
| Analysis completed with LOW findings only | 0.75 |
| Analysis completed with zero findings | 1.0 |

### Signal 3: Community (External Validation)

| Factor | Score Contribution |
|--------|--------------------|
| No community signals | 0.0 |
| Some usage detected | 0.25 |
| Multiple users, no reported issues | 0.50 |
| Active community, positive reviews | 0.75 |
| Widely adopted, audited by third parties | 1.0 |

### Signal 4: Historical (Track Record)

| Factor | Score Contribution |
|--------|--------------------|
| Brand new, no history | 0.0 |
| Less than 30 days old | 0.25 |
| 30-90 days, maintained | 0.50 |
| 90+ days, actively maintained | 0.75 |
| 1+ year, consistent maintenance, no incidents | 1.0 |

---

## Trust Propagation Through Dependencies

When a skill depends on other skills, trust propagates through the dependency chain. The effective trust score considers both the skill's intrinsic trust and the trust of its dependencies.

### The Rules

1. **A skill's effective trust cannot exceed its intrinsic trust.** A well-trusted skill that depends on an untrusted skill is limited by its weakest dependency.

2. **Trust propagation preserves ordering.** If skill A has a higher intrinsic trust than skill B, and they share the same dependencies, skill A's effective trust will be at least as high as skill B's.

3. **Adding trusted dependencies does not decrease trust** (Theorem 5: monotonicity). Introducing a highly-trusted dependency into a skill's chain can only maintain or improve the effective trust score.

### Example

```
Skill: deploy-automation (intrinsic: 0.85, L3)
  Depends on: config-reader (intrinsic: 0.70, L2)
  Depends on: network-utils (intrinsic: 0.45, L1)

Effective trust: limited by weakest dependency
  deploy-automation effective: 0.45 -> L1

Resolution: upgrade network-utils or replace with a higher-trust alternative
```

---

## Trust Decay for Unmaintained Skills

Skills that are not maintained become riskier over time. New vulnerabilities are discovered, attack techniques evolve, and unmaintained code accumulates unpatched exposure. The trust model accounts for this through **trust decay**:

- **Active maintenance** (updates within last 90 days): No decay
- **Aging** (90-180 days since last update): Historical signal reduced gradually
- **Stale** (180+ days since last update): Historical signal approaches minimum
- **Abandoned** (365+ days since last update): Historical signal at minimum; effective trust drops by one level threshold

Trust decay ensures that a skill's trust level reflects its current state, not its peak reputation.

---

## How to Improve Your Skill's Trust Level

### From L0 to L1 (UNSIGNED to SIGNED)

- Add author metadata to the skill manifest
- Sign the skill with a verifiable identity
- Publish the skill to a registry with identity verification

### From L1 to L2 (SIGNED to COMMUNITY_VERIFIED)

- Ensure the skill passes SkillFortify analysis with zero findings
- Build a usage track record (time and adoption)
- Respond to community feedback and reported issues
- Maintain the skill with regular updates

### From L2 to L3 (COMMUNITY_VERIFIED to FORMALLY_VERIFIED)

- Ensure all findings are resolved (zero findings from SkillFortify)
- Maintain strong provenance (signed + organizational affiliation)
- Sustain active maintenance for 90+ days
- Accumulate positive community signals (reviews, adoption, no incidents)

---

## Checking Trust Levels

```bash
# Check trust level for a single skill
skillfortify trust .claude/skills/deploy.md

# Check trust levels for all skills in a project (via scan)
skillfortify scan . --format json
# The JSON output includes trust information for each skill
```

---

## Further Reading

- **[Formal Foundations](Formal-Foundations)** -- Theorem 5 (Trust Monotonicity) and the trust algebra
- **[ASBOM Guide](ASBOM-Guide)** -- Trust levels in CycloneDX SBOM output
- **[Skill Lock JSON](Skill-Lock-JSON)** -- Trust scores captured in the lockfile
- **[Getting Started](Getting-Started)** -- First scan walkthrough

---

*SkillFortify is part of the [AgentAssert](https://agentassert.com) research suite -- building formal foundations for trustworthy AI agents.*
