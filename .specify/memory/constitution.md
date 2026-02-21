<!--
SYNC IMPACT REPORT
==================
Version change: (unversioned template) → 1.0.0
Ratification: 2026-02-21 (initial adoption)
Last Amended: 2026-02-21

Modified principles:
  - [PRINCIPLE_1_NAME] → I. Code Quality (new — replaces placeholder)
  - [PRINCIPLE_2_NAME] → II. Testing Standards (new — replaces placeholder)
  - [PRINCIPLE_3_NAME] → III. User Experience Consistency (new — replaces placeholder)
  - [PRINCIPLE_4_NAME] → IV. Performance Requirements (new — replaces placeholder)
  - [PRINCIPLE_5_NAME] → removed (user requested exactly four principles; template slot retired)

Added sections:
  - "Technology & Stack Constraints" (was [SECTION_2_NAME] placeholder)
  - "Development Workflow & Quality Gates" (was [SECTION_3_NAME] placeholder)

Removed sections: none (all were placeholders)

Templates reviewed:
  ✅ .specify/templates/plan-template.md — Constitution Check section updated; no structural changes required
  ✅ .specify/templates/spec-template.md — Requirements and Success Criteria sections align with principles; no changes required
  ✅ .specify/templates/tasks-template.md — Task phases align with principles; no changes required
  ✅ .specify/templates/agent-file-template.md — Generic template; no principle-specific references to update
  ✅ .specify/templates/checklist-template.md — Generic template; no principle-specific references to update

Deferred TODOs: none
-->

# homebank-to-hledger Constitution

## Core Principles

### I. Code Quality

All code contributed to this project MUST meet the following non-negotiable standards:

- **Type safety is mandatory.** Every function and method MUST carry complete type annotations.
  `Any` is forbidden unless accompanied by an inline comment explaining why it cannot be avoided.
- **`float` MUST NOT be used for monetary values.** Use `decimal.Decimal` exclusively.
- **Paths MUST be represented as `pathlib.Path`.** String-based `os.path` manipulation is forbidden.
- **Linting and formatting MUST pass without errors** (`ruff format` + `ruff check`) before any
  change is considered complete.
- **Static type checking MUST pass** (`mypy` in strict mode) before any change is considered complete.
- **No bare `except:` blocks.** Exceptions MUST be caught by their specific type.
- **No `print()` for diagnostic output.** Use the `logging` module or raise a domain exception.
- **Custom exception classes** MUST be used for domain errors (e.g., `HomebankParseError`,
  `ConversionError`).

**Rationale:** Financial data conversion is a correctness-critical domain. Imprecise types, silent
swallowed errors, and untyped code are the primary sources of data-integrity bugs in this class of
tooling.

### II. Testing Standards

All functional logic MUST be covered by automated tests. The following rules are non-negotiable:

- **Tests MUST be written before or alongside implementation** (test-first preferred, co-located
  acceptable for bug fixes when a reproduction test is written first).
- **A failing reproduction test MUST exist before any bug fix is merged.**
- **Pure conversion logic MUST live in `src/` and be independently testable** without file I/O.
  I/O concerns are isolated to the CLI layer.
- **`uv run pytest` MUST pass with zero failures and zero errors** before a change is considered done.
- **Test files MUST mirror the `src/` structure** under `tests/` (e.g., `src/converter.py` →
  `tests/test_converter.py`).
- Integration tests covering end-to-end file conversion MUST be present for every supported
  Homebank version or schema variation introduced.

**Rationale:** Conversion correctness cannot be verified manually for every edge case. Automated
tests are the only reliable safety net for regressions when the Homebank XML schema or hledger
journal format evolves.

### III. User Experience Consistency

The CLI interface MUST behave predictably and uniformly across all invocations:

- **Errors MUST be written to `stderr`**; normal output MUST go to `stdout`. These streams MUST
  NOT be mixed.
- **Exit codes MUST be meaningful:** `0` for success, non-zero for any failure. The specific
  non-zero code MUST be documented in the CLI help text.
- **Error messages MUST be actionable:** they MUST state what went wrong and, where possible,
  what the user can do to fix it.
- **Output format MUST be deterministic** for a given input: running the same conversion twice
  MUST produce byte-identical output (excluding timestamps the user explicitly opts into).
- **CLI flags and argument names MUST follow POSIX conventions** (kebab-case long options,
  single-character short options where provided).
- **Behaviour MUST NOT change silently** between versions. Any change to output format or flag
  semantics is a breaking change and requires a version bump.

**Rationale:** Financial journal files are frequently diff'd, version-controlled, and piped into
downstream tooling. Non-determinism or inconsistent stderr/stdout usage silently corrupts
automated pipelines.

### IV. Performance Requirements

The converter MUST remain efficient for realistic Homebank data sizes:

- **Full conversion of a file containing up to 50,000 transactions MUST complete in under 10 seconds**
  on commodity hardware (single core, 2 GHz equivalent, 512 MB available RAM).
- **Peak memory usage MUST NOT exceed 256 MB** for files up to 50,000 transactions.
- **Streaming or incremental parsing MUST be preferred** over loading the entire XML DOM into memory
  when processing large files.
- **No external network calls are permitted** at runtime. The tool MUST be fully offline-capable.
- Performance regressions (conversion time increases >20% on the reference dataset) MUST be
  flagged in PR review and justified before merge.

**Rationale:** Users run this tool as part of automated scripts and pre-commit hooks on full
transaction histories. Slow or memory-hungry conversions break those workflows and erode trust
in the tooling.

## Technology & Stack Constraints

- **Language:** Python 3.12+ exclusively. No backports to earlier versions.
- **Package management:** `uv` only. Do not use `pip`, `poetry`, or `pipenv` directly.
- **Testing framework:** `pytest` only.
- **Linting/formatting:** `ruff` (replaces Flake8, Black, and isort). Configuration lives in
  `pyproject.toml`.
- **Type checking:** `mypy` in strict mode. Configuration lives in `pyproject.toml`.
- **Forbidden at runtime:** `float` for money, `os.path`, bare `except`, `print()` for diagnostics,
  any network I/O.
- **Dependencies MUST be minimal.** Every new production dependency requires justification in the
  PR description. Prefer the Python standard library.

## Development Workflow & Quality Gates

Every change MUST pass all four gates, in order, before being considered complete:

1. **Format:** `uv run ruff format .` — zero diff produced.
2. **Lint:** `uv run ruff check . --fix` — zero remaining violations.
3. **Types:** `uv run mypy .` — zero errors.
4. **Tests:** `uv run pytest` — zero failures, zero errors.

No change may skip or defer any gate. Failing gates MUST be fixed, not suppressed with inline
ignore comments unless the suppression is accompanied by a tracked issue explaining the root cause.

## Governance

This constitution supersedes all other development practices for the `homebank-to-hledger` project.
Where any other document (README, inline comments, PR descriptions) conflicts with this constitution,
this constitution takes precedence.

**Amendment procedure:**
1. Propose the change as a PR modifying this file.
2. State the version bump type (MAJOR/MINOR/PATCH) and rationale in the PR description.
3. Update `LAST_AMENDED_DATE` and `CONSTITUTION_VERSION` in the footer.
4. Propagate changes to affected templates per the Sync Impact Report format (HTML comment at top).

**Versioning policy:**
- MAJOR: Removal or redefinition of a principle that breaks existing compliant code.
- MINOR: New principle or section added, or existing guidance materially expanded.
- PATCH: Clarifications, wording improvements, or typo fixes with no semantic change.

**Compliance review:** All PRs and code reviews MUST verify compliance with this constitution.
Complexity violations (e.g., deviations from the tech stack) MUST be justified in the PR with a
documented reason why the simpler compliant approach was insufficient. Use `AGENTS.md` for
runtime development guidance (commands, conventions, directory structure).

**Version**: 1.0.0 | **Ratified**: 2026-02-21 | **Last Amended**: 2026-02-21
