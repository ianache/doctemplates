# Coding Conventions

**Analysis Date:** 2026-07-05

## Status

This codebase is in very early stage (pre-alpha). Only one Python file exists (`main.py` at 93 bytes), and no coding conventions, linting, or formatting tools have been configured. The patterns below are inferred from the single existing function.

## Naming Patterns

**Files:**
- All lowercase with hyphens (project name: `29-docmanagemet`)
- Python modules: lowercase with underscores (e.g., `main.py`)
- Not yet established for package/module organization

**Functions:**
- Snake case (e.g., `main()`)
- Following PEP 8 conventions (inferred from `main.py`)

**Variables:**
- Not yet established (minimal existing code)

**Types:**
- No type hints present in current code
- Python 3.12+ available but not yet utilized

## Code Style

**Formatting:**
- No formatter configured (black, ruff, or others not in dependencies)
- Default Python indentation (4 spaces, inferred from `main.py`)

**Linting:**
- No linter configured (flake8, pylint, ruff not in dependencies)
- No `.pylintrc`, `setup.cfg`, or similar files present

## Import Organization

**Order:**
- Not yet established
- Python 3.12 and later (with modern import features available)

**Path Aliases:**
- Not used in current code

## Error Handling

**Patterns:**
- Not yet established
- No error handling present in `main.py`

## Logging

**Framework:** 
- Not configured
- `print()` used in `main.py` (basic console output)

**Patterns:**
- None established yet

## Comments

**When to Comment:**
- Not yet established
- Current code has no comments

**JSDoc/TSDoc:**
- Not applicable (Python, not TypeScript)
- No docstrings present in current code

## Function Design

**Size:** 
- Not yet established

**Parameters:** 
- Single function `main()` takes no parameters

**Return Values:** 
- Single function `main()` returns `None` (implicit)

## Module Design

**Exports:** 
- Entry point: `main()` called via standard `if __name__ == "__main__":` pattern

**Barrel Files:** 
- Not applicable to current structure

## Dependencies

**Package Manager:** `uv` (from `uv.lock`)

**Configuration File:** `pyproject.toml`

**Current Dependencies:**
- `headroom-ai[all]>=0.30.0` (only production dependency)

No development dependencies (testing, linting, formatting) configured.

---

*Convention analysis: 2026-07-05*

**NOTE:** This project requires establishing coding standards, linting configuration, and development tool setup before conventions become actionable. The planned DocManagement system (per PRD.md) will likely require:
- Type hints (Python 3.12 supports modern type syntax)
- Error handling framework (for BFF API endpoints)
- API response serialization patterns
- Logging configuration (for PDF processing pipeline)
