"""Decorators for declaring custom validators on a model.

Two flavours are provided:

* :func:`field_validator` runs **after** a single field has been parsed and
  type-coerced. It receives the field value and must return the (possibly
  transformed) value, or raise :class:`ValueError`/:class:`TypeError`.
* :func:`model_validator` runs **after** the whole model has been built and
  has access to the entire model instance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal


__all__ = [
    "FieldValidator",
    "ModelValidator",
    "field_validator",
    "model_validator",
]

_FIELD_VALIDATOR_ATTR = "__validix_field_validator__"
_MODEL_VALIDATOR_ATTR = "__validix_model_validator__"


@dataclass(frozen=True)
class FieldValidator:
    """A user-declared validator bound to one or more fields."""

    fields: tuple[str, ...]
    func: Callable[..., Any]
    mode: Literal["before", "after"] = "after"


@dataclass(frozen=True)
class ModelValidator:
    """A user-declared whole-model validator."""

    func: Callable[..., Any]
    mode: Literal["before", "after"] = "after"


def field_validator(
    *fields: str,
    mode: Literal["before", "after"] = "after",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a method as a field-level validator.

    Example::

        class User(BaseModel):
            name: str

            @field_validator("name")
            def _strip(cls, value: str) -> str:
                return value.strip()
    """

    if not fields:
        raise ValueError("field_validator requires at least one field name")
    if mode not in ("before", "after"):
        raise ValueError("mode must be 'before' or 'after'")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, _FIELD_VALIDATOR_ATTR, FieldValidator(fields=fields, func=func, mode=mode))
        return func

    return decorator


def model_validator(
    *,
    mode: Literal["before", "after"] = "after",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a method as a model-level validator.

    In ``mode="before"`` the function receives the raw input dict; in
    ``mode="after"`` it receives the constructed model instance.
    """

    if mode not in ("before", "after"):
        raise ValueError("mode must be 'before' or 'after'")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, _MODEL_VALIDATOR_ATTR, ModelValidator(func=func, mode=mode))
        return func

    return decorator


def get_field_validator(obj: Any) -> FieldValidator | None:
    return getattr(obj, _FIELD_VALIDATOR_ATTR, None)


def get_model_validator(obj: Any) -> ModelValidator | None:
    return getattr(obj, _MODEL_VALIDATOR_ATTR, None)
