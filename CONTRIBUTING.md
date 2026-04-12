# Contributing to validix

Thanks for your interest in contributing to `validix`! This document describes how to set up your environment, run the test suite, and propose changes.

## Development setup

```bash
git clone https://github.com/Lib1221/validix.git
cd validix
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,docs]"
pre-commit install
```

## Running the test suite

```bash
pytest                       # full test suite
pytest --cov=validix         # with coverage
pytest tests/test_core.py    # a single file
```

## Code style

We use [black](https://github.com/psf/black) for formatting, [ruff](https://github.com/astral-sh/ruff) for linting and import-sorting, and [mypy](https://github.com/python/mypy) in `strict` mode for type checking.

```bash
black .
ruff check . --fix
mypy src/validix
```

The pre-commit hook runs all three on every commit.

## Commit messages

We loosely follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(core): add support for frozen models
fix(fields): correct min_length check for empty strings
docs(readme): clarify installation instructions
```

Common types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `ci`.

## Pull requests

1. Fork the repository and create a feature branch.
2. Add tests for any new behaviour.
3. Make sure `pytest`, `ruff`, `mypy`, and `black --check` all pass.
4. Update `CHANGELOG.md` under the `[Unreleased]` section.
5. Open a PR with a clear description of the problem and the solution.

## Reporting issues

If you find a bug, please open an issue using the **Bug Report** template and include:

- A minimal reproducer
- The version of `validix` and Python you are using
- The full traceback / error output

For feature requests, use the **Feature Request** template and explain *why* the feature would be useful, not just *what* it should do.
