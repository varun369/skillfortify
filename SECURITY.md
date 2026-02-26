# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

Only the latest minor release receives security updates.

## Reporting a Vulnerability

If you discover a security vulnerability in SkillFortify, please report it responsibly.

**Email:** varun.pratap.bhardwaj@gmail.com

**Subject line format:** `[SECURITY] SkillFortify — Brief description`

**What to include:**
- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested fix (if any)

**Response commitment:**
- Acknowledgment within **48 hours** of receipt
- Initial assessment within **5 business days**
- Fix timeline communicated once assessment is complete

## Responsible Disclosure

We follow a coordinated disclosure process:

1. Report the vulnerability privately via email (not via public GitHub issues).
2. We will acknowledge receipt and work with you on a fix.
3. Once a fix is released, we will publicly credit you (unless you prefer anonymity).
4. Please allow a reasonable window for us to address the issue before any public disclosure.

## Scope

The following are in scope for security reports:

- Vulnerabilities in SkillFortify's analysis engine that could produce incorrect safety verdicts
- Bypasses of capability inference or threat detection
- Lockfile integrity issues (e.g., hash collisions, tamper-undetected modifications)
- Dependency confusion or supply chain issues in SkillFortify itself
- Any issue where SkillFortify reports a malicious skill as safe

The following are **out of scope:**

- Vulnerabilities in third-party dependencies (report those upstream)
- Denial-of-service through pathologically large inputs (known limitation)
- Issues requiring physical access to the machine running SkillFortify

## Security Advisories

Security advisories will be published via GitHub Security Advisories once the repository is public.
