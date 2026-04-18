# Errors

When validation fails, `validix` raises a `ValidationError` containing one or
more `ErrorDetail` records. Each record has:

| Field   | Type                        | Meaning                                |
| ------- | --------------------------- | -------------------------------------- |
| `loc`   | `tuple[str | int, ...]`     | path to the offending input            |
| `msg`   | `str`                       | human-readable message                 |
| `type`  | `str`                       | machine-readable failure code          |
| `input` | `Any`                       | the value that was rejected            |
| `ctx`   | `dict[str, Any]`            | extra context (e.g. `{'gt': 0}`)       |

```python
from validix import BaseModel, Field, ValidationError

class M(BaseModel):
    n: int = Field(gt=0)

try:
    M(n=-1)
except ValidationError as exc:
    print(exc.errors())
    # [{'loc': ['n'], 'msg': 'must be > 0', 'type': 'greater_than',
    #   'input': -1, 'ctx': {'gt': 0}}]
```

## Common error types

| `type`                    | Raised when                                   |
| ------------------------- | --------------------------------------------- |
| `missing`                 | a required field wasn't supplied              |
| `type_error`              | strict-mode type mismatch                     |
| `coercion_error`          | lenient coercion couldn't convert the value   |
| `too_short` / `too_long`  | length constraint violated                    |
| `greater_than`, `less_than`, … | numeric constraint violated              |
| `string_pattern_mismatch` | regex didn't match                            |
| `union_error`             | no member of a `Union[...]` matched           |
| `literal_error`           | value not in the `Literal[...]` choices       |
| `extra_forbidden`         | unknown key with `extra="forbid"`             |
| `model_validator`         | `@model_validator` raised                     |
| `value_error`             | `@field_validator` raised                     |
| `json_invalid`            | `model_validate_json` got malformed JSON      |
