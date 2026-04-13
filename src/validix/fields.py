"""Field descriptors and constraint metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from typing import Any, Callable, Iterable, Pattern

from validix.errors import ConfigError, ErrorDetail
from validix.types import UNSET


__all__ = ["FieldInfo", "Field"]


@dataclass
class FieldInfo:
    """The compiled metadata that backs every model attribute.

    Users construct one of these via :func:`Field`. The model metaclass
    fills ``annotation``, ``name`` and ``required`` after introspection.
    """

    default: Any = UNSET
    default_factory: Callable[[], Any] | None = None
    alias: str | None = None
    description: str | None = None
    examples: list[Any] | None = None

    # Numeric constraints
    gt: float | None = None
    ge: float | None = None
    lt: float | None = None
    le: float | None = None
    multiple_of: float | None = None

    # String / collection constraints
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | Pattern[str] | None = None

    # Misc
    frozen: bool = False
    strict: bool | None = None

    # Filled in by the metaclass
    name: str = ""
    annotation: Any = None
    required: bool = True

    _compiled_pattern: Pattern[str] | None = dc_field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.default is not UNSET and self.default_factory is not None:
            raise ConfigError("cannot specify both default and default_factory")
        if self.pattern is not None:
            self._compiled_pattern = (
                self.pattern if isinstance(self.pattern, re.Pattern) else re.compile(self.pattern)
            )

    @property
    def has_default(self) -> bool:
        return self.default is not UNSET or self.default_factory is not None

    def get_default(self) -> Any:
        if self.default_factory is not None:
            return self.default_factory()
        if self.default is UNSET:
            raise ConfigError(f"field {self.name!r} has no default")
        return self.default

    # ------------------------------------------------------------------
    # Constraint checking
    # ------------------------------------------------------------------
    def check_constraints(self, value: Any, loc: tuple[str | int, ...]) -> list[ErrorDetail]:
        """Return a list of ErrorDetail (empty if everything passes)."""

        errors: list[ErrorDetail] = []

        if isinstance(value, bool):
            numeric: float | None = None  # bool inherits from int but we don't compare it
        elif isinstance(value, (int, float)):
            numeric = float(value)
        else:
            numeric = None

        if numeric is not None:
            if self.gt is not None and not numeric > self.gt:
                errors.append(self._err(loc, value, "greater_than", f"must be > {self.gt}", {"gt": self.gt}))
            if self.ge is not None and not numeric >= self.ge:
                errors.append(self._err(loc, value, "greater_than_equal", f"must be >= {self.ge}", {"ge": self.ge}))
            if self.lt is not None and not numeric < self.lt:
                errors.append(self._err(loc, value, "less_than", f"must be < {self.lt}", {"lt": self.lt}))
            if self.le is not None and not numeric <= self.le:
                errors.append(self._err(loc, value, "less_than_equal", f"must be <= {self.le}", {"le": self.le}))
            if self.multiple_of is not None and self.multiple_of != 0:
                if (numeric % self.multiple_of) != 0:
                    errors.append(
                        self._err(
                            loc,
                            value,
                            "multiple_of",
                            f"must be a multiple of {self.multiple_of}",
                            {"multiple_of": self.multiple_of},
                        )
                    )

        if isinstance(value, (str, bytes, list, tuple, set, frozenset, dict)):
            length = len(value)
            if self.min_length is not None and length < self.min_length:
                errors.append(
                    self._err(
                        loc,
                        value,
                        "too_short",
                        f"length must be >= {self.min_length}",
                        {"min_length": self.min_length, "actual_length": length},
                    )
                )
            if self.max_length is not None and length > self.max_length:
                errors.append(
                    self._err(
                        loc,
                        value,
                        "too_long",
                        f"length must be <= {self.max_length}",
                        {"max_length": self.max_length, "actual_length": length},
                    )
                )

        if self._compiled_pattern is not None and isinstance(value, str):
            if not self._compiled_pattern.search(value):
                errors.append(
                    self._err(
                        loc,
                        value,
                        "string_pattern_mismatch",
                        f"does not match pattern {self._compiled_pattern.pattern!r}",
                        {"pattern": self._compiled_pattern.pattern},
                    )
                )

        return errors

    @staticmethod
    def _err(
        loc: tuple[str | int, ...],
        value: Any,
        type_: str,
        msg: str,
        ctx: dict[str, Any] | None = None,
    ) -> ErrorDetail:
        return ErrorDetail(loc=loc, msg=msg, type=type_, input=value, ctx=ctx or {})


def Field(  # noqa: N802 - matches the pydantic-style public name
    default: Any = UNSET,
    *,
    default_factory: Callable[[], Any] | None = None,
    alias: str | None = None,
    description: str | None = None,
    examples: Iterable[Any] | None = None,
    gt: float | None = None,
    ge: float | None = None,
    lt: float | None = None,
    le: float | None = None,
    multiple_of: float | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    pattern: str | Pattern[str] | None = None,
    frozen: bool = False,
    strict: bool | None = None,
) -> Any:
    """Declare metadata for a model field.

    The return type is annotated as ``Any`` so that ``name: str = Field(...)``
    type-checks with mypy and pyright (mirroring the pydantic API).
    """

    return FieldInfo(
        default=default,
        default_factory=default_factory,
        alias=alias,
        description=description,
        examples=list(examples) if examples is not None else None,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        multiple_of=multiple_of,
        min_length=min_length,
        max_length=max_length,
        pattern=pattern,
        frozen=frozen,
        strict=strict,
    )
