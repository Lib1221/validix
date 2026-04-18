# Fields and constraints

`Field()` lets you attach metadata and constraints to a model attribute.

## Numeric

```python
from validix import BaseModel, Field

class Item(BaseModel):
    price: float = Field(gt=0, le=10_000, multiple_of=0.01)
```

| Argument      | Meaning                                     |
| ------------- | ------------------------------------------- |
| `gt`          | strictly greater than                       |
| `ge`          | greater than or equal                       |
| `lt`          | strictly less than                          |
| `le`          | less than or equal                          |
| `multiple_of` | value must be an exact multiple of this     |

## Strings and collections

```python
class User(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-z0-9_]+$")
    tags: list[str] = Field(default_factory=list, max_length=10)
```

`min_length` and `max_length` apply to anything that has a `len()`.

## Defaults

- `default=...`         — a literal default
- `default_factory=...` — called every time a default is needed (use this for
  mutable defaults like `[]` or `{}`)

The two are mutually exclusive; passing both raises `ConfigError`.

## Aliases

```python
class M(BaseModel):
    full_name: str = Field(alias="fullName")

M(fullName="Ada")          # accepts the alias
M(fullName="Ada").model_dump(by_alias=True)
# {'fullName': 'Ada'}
```
