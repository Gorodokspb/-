# Agent guidance for CRM_OLD_BAD

## Code style

- Python style is enforced by [ruff](https://docs.astral.sh/ruff/).
- Config: `pyproject.toml` (`[tool.ruff]`).
- Run before committing:
  ```bash
  python -m ruff check .
  python -m ruff format --check .
  ```
- Auto-fix safe issues:
  ```bash
  python -m ruff check --fix .
  python -m ruff format .
  ```
- Pre-commit hook: `pip install pre-commit && pre-commit install`.

## Existing rules

- God-files (CRM.py, webapp/main.py, webapp/db.py) are intentionally not
  refactored (D-002). Adding new helpers inside them is fine; splitting is
  not.
- Tests require live `.env.web` (real secrets) for webapp tests that touch
  `get_settings()`. The `TestConfigSecrets` and `TestCsrfFunctional` classes
  in `tests/test_security_regressions.py` are the exception: they mock env
  and use `TestClient` without DB.
