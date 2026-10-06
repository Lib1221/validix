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

## Forward references

A field can refer to a model that doesn't exist yet when the class is created,
such as the model itself or one defined further down the module:

```python
from typing import Optional

class Node(BaseModel):
    value: int
    next: Optional["Node"] = None

Node(value=1, next={"value": 2})  # next is parsed into a Node
```

These annotations are resolved the first time the model is used. If a model
defined inside a function refers to a model defined *after* it in the same
function, call `model_rebuild()` once both exist:

```python
def build():
    class Order(BaseModel):
        item: Optional["Item"] = None

    class Item(BaseModel):
        sku: str

    Order.model_rebuild()
    return Order
```

An annotation that still can't be resolved raises `ConfigError` the first time
the model is used, rather than leaving that field unvalidated.

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
