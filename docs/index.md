# validix

A lightweight, fast data validation and parsing library for Python — inspired by Pydantic.

## At a glance

```python
from validix import BaseModel, Field, ValidationError


class User(BaseModel):
    id: int
    name: str = Field(min_length=1, max_length=64)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    is_active: bool = True


user = User(id="42", name="Ada Lovelace", email="ada@example.com")
print(user.model_dump_json(indent=2))
```

## Why validix?

- **Familiar.** Define models the way you write `dataclass` — with type hints.
- **Fast.** Field metadata is compiled once at class-creation time.
- **Helpful errors.** Every `ValidationError` carries a list of `ErrorDetail`s with `loc`, `msg`, `type`, `input` and optional `ctx`.
- **Zero required dependencies.** Pure Python, no C-extension build step.
- **Typed.** Ships with `py.typed` and works great with mypy/pyright.

Continue to [Getting started](getting_started.md) for a hands-on tour.
