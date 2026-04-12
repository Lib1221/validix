# validix

[![CI](https://github.com/Lib1221/validix/actions/workflows/ci.yml/badge.svg)](https://github.com/Lib1221/validix/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linter: ruff](https://img.shields.io/badge/linter-ruff-red.svg)](https://github.com/astral-sh/ruff)
[![Type checker: mypy](https://img.shields.io/badge/type%20checker-mypy-blue.svg)](https://github.com/python/mypy)

> A lightweight, fast, and friendly data validation and parsing library for Python — inspired by Pydantic.

`validix` lets you define data schemas using regular Python type hints, then parse, validate, and serialize untrusted data (JSON, dicts, query strings, env vars, …) with helpful error messages.

```python
from validix import BaseModel, Field, ValidationError


class User(BaseModel):
    id: int
    name: str = Field(min_length=1, max_length=64)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    is_active: bool = True


try:
    user = User(id="42", name="Ada Lovelace", email="ada@example.com")
    print(user.model_dump())
except ValidationError as exc:
    print(exc.errors())
```

## Why validix?

- **Familiar.** Define models the way you already write Python `dataclass`-style classes.
- **Fast.** Field metadata is compiled once at class-creation time.
- **Helpful errors.** Every validation failure includes a `loc` path, a `msg`, and a machine-readable `type`.
- **Zero required dependencies.** Pure Python, no C-extensions.
- **Typed.** Ships with a complete `py.typed` marker and works great with `mypy`/`pyright`.

## Installation

```bash
pip install validix
```

Requires **Python 3.9+**.

## Features

- ✅ Type-hint based schemas
- ✅ Built-in coercion (`"42"` → `42`, `"true"` → `True`, …) with an opt-in `strict` mode
- ✅ Constraint fields: `min_length`, `max_length`, `gt`, `ge`, `lt`, `le`, `pattern`, `multiple_of`
- ✅ Custom `@field_validator` and `@model_validator` decorators
- ✅ Recursive nested models, `list[Model]`, `dict[str, Model]`, `Optional[T]`, `Union[A, B]`
- ✅ JSON serialization: `model_dump()`, `model_dump_json()`
- ✅ Field aliases and `populate_by_name`
- ✅ Frozen / immutable models
- ✅ Friendly errors, fully introspectable

## Quick start

See [`docs/getting_started.md`](docs/getting_started.md) and the runnable examples in [`examples/`](examples/).

## Contributing

Contributions are very welcome! Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) and the [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) before opening a pull request.

## License

`validix` is released under the [MIT License](LICENSE).
