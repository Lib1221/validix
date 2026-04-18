# Custom validators

`validix` exposes two decorators for adding custom logic.

## `@field_validator`

```python
from validix import BaseModel, field_validator

class User(BaseModel):
    name: str

    @field_validator("name")
    def _strip_and_title(cls, value: str) -> str:
        return value.strip().title()
```

`mode="before"` runs *before* type coercion (so the value is whatever the user
passed in); `mode="after"` (the default) runs after coercion and constraints.

## `@model_validator`

```python
from validix import BaseModel, model_validator

class Range(BaseModel):
    lo: int
    hi: int

    @model_validator(mode="after")
    def _check_order(self):
        if self.lo > self.hi:
            raise ValueError("lo must be <= hi")
        return self
```

`mode="before"` receives the raw input dict and may mutate or replace it;
`mode="after"` receives the constructed model instance.

## Raising errors

Inside a validator, raise `ValueError` (or `TypeError` / `AssertionError`) to
record a failure. The framework attaches the appropriate `loc` automatically.
