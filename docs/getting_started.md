# Getting started

## Install

```bash
pip install validix
```

`validix` requires Python 3.9 or newer and has no required runtime dependencies.

## Define your first model

```python
from validix import BaseModel


class Movie(BaseModel):
    title: str
    year: int
    rating: float = 0.0


m = Movie(title="Solaris", year=1972)
print(m)
# Movie(title='Solaris', year=1972, rating=0.0)
```

Type-coercion is on by default, so this also works:

```python
m = Movie(title="Solaris", year="1972", rating="8.1")
print(m.year, m.rating)  # 1972 8.1
```

Turn it off per-model with `model_config`:

```python
class Movie(BaseModel):
    class model_config:
        strict = True

    title: str
    year: int
```

## Constraints with `Field()`

```python
from validix import BaseModel, Field


class Account(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-z0-9_]+$")
    age: int = Field(ge=13, lt=130)
```

See the [Fields and constraints](guide/fields.md) page for the full list.

## Catch errors

```python
from validix import ValidationError

try:
    Account(username="x", age=200)
except ValidationError as exc:
    for err in exc.errors():
        print(err["loc"], err["msg"])
```

## Serialize back

```python
account = Account(username="ada", age=37)
account.model_dump()        # plain dict
account.model_dump_json()   # JSON string
```

## Where next?

- [User guide → Models](guide/models.md)
- [User guide → Validators](guide/validators.md)
- [API reference → BaseModel](api/basemodel.md)
