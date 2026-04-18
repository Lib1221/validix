# Configuration

Configure a model by adding a nested `model_config` class:

```python
from validix import BaseModel

class Strict(BaseModel):
    class model_config:
        strict = True
        extra = "forbid"
        frozen = True
        populate_by_name = True
```

| Option              | Default    | Description                                            |
| ------------------- | ---------- | ------------------------------------------------------ |
| `strict`            | `False`    | Disable lenient coercion (`"42"` → `42`, etc.).        |
| `extra`             | `"ignore"` | What to do with unknown keys: `"ignore"`, `"allow"` (keep them on the instance), `"forbid"` (raise `extra_forbidden`). |
| `frozen`            | `False`    | Make instances immutable; assignment raises `ConfigError`, instances become hashable. |
| `populate_by_name`  | `False`    | Allow input by both alias and original attribute name. |

Per-field overrides:

- `Field(strict=True)` — strict mode for that field only.
