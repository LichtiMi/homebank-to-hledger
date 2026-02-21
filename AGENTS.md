# AGENTS.md

This file serves as the primary source of truth for all AI agents and developers working on the `homebank-to-hledger` repository.
Strictly adhere to these guidelines to maintain code quality, consistency, and stability.

## 1. Project Overview & Tech Stack

**Goal:** robust CLI tool to convert Homebank (`.xhb`) XML exports into strictly formatted hledger journal files.

**Core Stack:**
- **Language:** Python 3.12+
- **Package Manager:** `uv` (Fast, modern replacement for pip/poetry)
- **Testing:** `pytest`
- **Linting & Formatting:** `ruff` (Replaces Flake8, Black, isort)
- **Static Typing:** `mypy` (Strict mode)

---

## 2. Operational Commands

Agents must use `uv` for all environment interactions. Do not use global `pip` or `python` commands.

### Setup & Dependencies
```bash
# Install dependencies and sync environment (creates .venv automatically)
uv sync

# Add a new production dependency
uv add <package_name>

# Add a dev dependency
uv add --dev <package_name>
```

### Testing
**Crucial:** Always run tests before and after making changes.

```bash
# Run all tests
uv run pytest

# Run a SINGLE test file
uv run pytest tests/test_converter.py

# Run a SINGLE test case (essential for TDD/bug fixing)
uv run pytest tests/test_converter.py::test_specific_transaction_parse -v

# Run tests matching a keyword expression
uv run pytest -k "parsing or validation"
```

### Code Quality (Linting, Formatting, Typing)
**Crucial:** Code must pass all checks before being considered "done".

```bash
# Format code (fixes layout, imports, quotes automatically)
uv run ruff format .

# Lint code (fixes trivial issues automatically)
uv run ruff check . --fix

# Static Type Checking (Strict)
uv run mypy .
```

---

## 3. Code Style & Conventions

### General Philosophy
- **Modern Python:** Use features from Python 3.10+ (e.g., match/case, union types `X | Y`).
- **Functional Core, Imperative Shell:** Keep conversion logic pure and testable. Isolate I/O (file reading/writing) to the CLI layer.
- **Type Safety:** The codebase must be fully typed. `Any` is forbidden unless absolutely necessary and documented.

### Specific Guidelines

#### 1. Formatting & Structure
- **Line Length:** 88 characters (Ruff default).
- **Quotes:** Double quotes `"` for strings.
- **Imports:** Absolute imports only (e.g., `from src.converter import parse`).
  - Organized automatically by `ruff` (Standard Lib > Third Party > Local).
- **File Structure:**
  - `src/`: Source code.
  - `tests/`: Tests, mirroring the structure of `src/`.

#### 2. Naming Conventions
- **Variables/Functions:** `snake_case` (e.g., `parse_transaction`, `account_name`)
- **Classes/Types:** `PascalCase` (e.g., `TransactionConverter`, `HomebankParser`)
- **Constants:** `UPPER_CASE` (e.g., `DEFAULT_CURRENCY`, `DATE_FORMAT`)
- **Files:** `snake_case` (e.g., `xml_parser.py`)

#### 3. Typing & Annotations
- **Mandatory:** All function signatures must be typed.
  ```python
  # CORRECT
  def convert_amount(value: str) -> Decimal: ...
  
  # INCORRECT
  def convert_amount(value): ...
  ```
- **Unions:** Use `|` syntax (e.g., `int | None` instead of `Optional[int]`).
- **Collections:** Use standard generic types (e.g., `list[str]`, `dict[str, int]`).

#### 4. Critical Data Types
- **Currency:** ALWAYS use `decimal.Decimal`. **NEVER** use `float` for money.
- **Dates:** Use `datetime.date` (not `datetime.datetime` unless time is strictly required).
- **Paths:** ALWAYS use `pathlib.Path`. **NEVER** use `os.path` strings.
  ```python
  # CORRECT
  from pathlib import Path
  def read_file(path: Path) -> str: ...
  
  # INCORRECT
  def read_file(path: str) -> str: ...
  ```

#### 5. Error Handling
- Use custom exception classes for domain errors (e.g., `HomebankParseError`, `ConversionError`).
- **Never** use bare `except:` blocks.
- **Never** use `print()` for errors; use the `logging` module or raise exceptions.

---

## 4. Agent Workflow Rules

1.  **Read First:** Before editing, read related files to understand context and existing patterns.
2.  **Test First:**
    - If fixing a bug, create a reproduction test case that fails first.
    - If adding a feature, add a basic test case to verify the implementation.
3.  **Atomic Changes:** Keep changes focused. Do not refactor unrelated code unless requested.
4.  **Verify:**
    - Run `uv run ruff format .`
    - Run `uv run ruff check . --fix`
    - Run `uv run mypy .`
    - Run `uv run pytest`
    - Only report "Task Completed" if all checks pass.
5.  **Clean Up:** Remove any temporary files or debug print statements before finishing.

---

## 5. Directory Structure (Expected)

```
.
├── src/
│   ├── __init__.py
│   ├── main.py          # Entry point
│   ├── converter.py     # Core logic
│   └── models.py        # Data classes / Types
├── tests/
│   ├── __init__.py
│   └── test_converter.py
├── pyproject.toml       # Dependencies & Tool Config
├── uv.lock
├── README.md
└── AGENTS.md
```

## Active Technologies
- Python 3.12+ + Nur stdlib — `xml.etree.ElementTree`, `decimal`, `pathlib`, `datetime`, `argparse`, `logging` (001-homebank-to-hledger-konverter)
- Eingabe: `.xhb`-Datei; Ausgabe: `.journal`-Dateien im Zielverzeichnis (001-homebank-to-hledger-konverter)

## Recent Changes
- 001-homebank-to-hledger-konverter: Added Python 3.12+ + Nur stdlib — `xml.etree.ElementTree`, `decimal`, `pathlib`, `datetime`, `argparse`, `logging`
