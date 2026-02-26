# Contributing to SkillFortify

Thank you for your interest in contributing to SkillFortify. This document covers the process for setting up a development environment, running tests, and submitting changes.

---

## Development Setup

### Prerequisites

- Python 3.11 or later
- Git

### Clone and Install

```bash
git clone https://github.com/varun369/skillfortify.git
cd skillfortify
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

The `[dev]` extra installs testing and linting tools required for development.

### Optional: SAT Solver

For full dependency resolution features:

```bash
pip install -e ".[dev,sat]"
```

---

## Running Tests

### Full Test Suite

```bash
pytest -v
```

### Quick Check (No Verbose Output)

```bash
pytest -q
```

### Specific Test File

```bash
pytest tests/test_analyzer.py -v
```

### With Coverage Report

```bash
pytest --cov=skillfortify --cov-report=term-missing
```

### Property-Based Tests

SkillFortify uses [Hypothesis](https://hypothesis.readthedocs.io/) for property-based testing. These run automatically as part of the standard test suite. If you need to reproduce a specific failure, Hypothesis stores its database in `.hypothesis/`.

---

## Linting

SkillFortify uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for lint errors
ruff check src/ tests/

# Auto-fix where possible
ruff check src/ tests/ --fix

# Format code
ruff format src/ tests/
```

The CI pipeline enforces lint checks on every pull request.

---

## Code Standards

- **Target Python version:** 3.11+ (use modern syntax: `X | Y` unions, `match` statements where appropriate)
- **Line length:** 100 characters maximum
- **Type annotations:** Required on all public functions and methods
- **Docstrings:** Required on all public classes, functions, and methods. Use Google-style format
- **Test coverage:** Every new feature or bug fix must include tests. Aim for comprehensive coverage of edge cases
- **No print statements:** Use `click.echo()` in CLI code and `logging` elsewhere

---

## Submitting Changes

### Before You Start

1. **Check existing issues** to see if someone is already working on the same area
2. **Open an issue first** for significant changes to discuss the approach
3. **Keep PRs focused** -- one logical change per pull request

### Pull Request Process

1. Fork the repository and create a feature branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. Make your changes. Ensure:
   - All existing tests still pass: `pytest -v`
   - Lint passes: `ruff check src/ tests/`
   - New code has tests

3. Write a clear commit message describing WHAT changed (not why -- that goes in the PR description)

4. Push and open a pull request against `main`

5. The CI pipeline will run tests across Python 3.11, 3.12, and 3.13. All checks must pass before merge

### What Makes a Good PR

- Clear title (under 70 characters)
- Description explaining the motivation and approach
- Tests for new behavior
- No unrelated changes mixed in

---

## Reporting Security Issues

If you discover a security vulnerability in SkillFortify, **do not open a public issue.** Instead, email the maintainer directly. Responsible disclosure is appreciated and will be acknowledged.

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this standard. Report unacceptable behavior to the project maintainer.

### Summary

- Be respectful and constructive
- Focus on technical merit
- Welcome newcomers
- No harassment, discrimination, or personal attacks

---

## Questions?

Open a GitHub Discussion or an issue tagged `question`. We are happy to help contributors get oriented.
