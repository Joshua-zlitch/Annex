# Contributing to ANNEX

Thanks for your interest in contributing to ANNEX — "Learn Before You Believe".
Every contribution, whether a bug report, a typo fix, or a feature, helps more
people evaluate what they see online before they believe it.

## Code of Conduct

This project and everyone participating in it is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to
uphold this code.

## Getting started

1. Fork the repository and create a branch: `git checkout -b your-feature`.
2. Set up the environment:
   ```bash
   cp .env.example .env   # fill in Supabase + OpenAI keys as needed
   pip install -e ".[dev]"
   ```
3. Apply the database migrations: `supabase db push` (or run the SQL in
   `supabase/migrations/` in the SQL editor).
4. Run the server locally: `uvicorn app.main:app --reload`.

## Development workflow

The codebase follows Clean Architecture (see `README.md`). Please respect the
dependency rule: the **core** layer (domain + application) must never import
from FastAPI, Supabase, or OpenAI. Adapters live in `infrastructure`, delivery
in `interface`.

### Style and tooling

- **Formatting / linting:** [ruff](https://docs.astral.sh/ruff/), configured in
  `pyproject.toml`.
- **Line length:** 100 characters.
- **Python:** 3.12+.

Before submitting, run:

```bash
ruff format .
ruff check .
pytest
```

All checks must pass and the test suite must be green. Tests live in `tests/`
and use fakes for external services, so no network access is required.

### Commits

- Write clear, conventional commit messages (e.g. `feat: add ...`,
  `fix: handle ...`, `refactor: ...`).
- Keep changes focused; one logical change per commit.

## Pull request process

1. Update or add tests for your change.
2. Update `README.md` if the public interface or setup changes.
3. Run `ruff format .`, `ruff check .`, and `pytest` locally.
4. Open a pull request describing what you changed and why.

## Reporting issues

- Search open and closed issues first to avoid duplicates.
- Include steps to reproduce, expected vs. actual behavior, and the environment
  (OS, Python version) for bugs.
- For security vulnerabilities, do **not** open an issue — follow the process in
  [SECURITY.md](SECURITY.md).

## Questions

If you are unsure about anything, open a discussion or ask in an issue before
writing a large amount of code. Early feedback saves everyone time.