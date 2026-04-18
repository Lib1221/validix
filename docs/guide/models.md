# Models

A model is any subclass of `validix.BaseModel`. Annotated class attributes
become validated fields; un-annotated attributes are ignored.

## Inheritance

Subclasses inherit fields and validators from their bases:

```python
class Animal(BaseModel):
    name: str

class Dog(Animal):
    breed: str

Dog(name="Rex", breed="Labrador")
```

## Configuration

Override `model_config` to change behaviour:

```python
class Strict(BaseModel):
    class model_config:
        strict = True
        extra = "forbid"
        frozen = True
```

| Option              | Default    | Effect                                                 |
| ------------------- | ---------- | ------------------------------------------------------ |
| `strict`            | `False`    | Disable lenient `str → int / bool / …` coercion.       |
| `extra`             | `"ignore"` | `"ignore"`, `"allow"`, or `"forbid"` extra input keys. |
| `frozen`            | `False`    | Make instances immutable; enables `__hash__`.          |
| `populate_by_name`  | `False`    | When using aliases, also accept the original name.     |
