"""Exception hierarchy and error reporting for validix.

A `ValidationError` carries a list of `ErrorDetail` records, each describing
*where* in the input the failure happened (`loc`), *what* went wrong (`msg`),
*which* check failed (`type`), and *what* value was rejected (`input`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


__all__ = [
    "ValidatorError",
    "ConfigError",
    "ErrorDetail",
    "ValidationError",
]


class ValidatorError(Exception):
    """Base class for every error raised by validix."""


class ConfigError(ValidatorError):
    """Raised when a model is *defined* incorrectly (not a runtime data error)."""


@dataclass(frozen=True)
class ErrorDetail:
    """A single validation failure."""

    loc: tuple[str | int, ...]
    msg: str
    type: str
    input: Any = None
    ctx: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "loc": list(self.loc),
            "msg": self.msg,
            "type": self.type,
            "input": self.input,
        }
        if self.ctx:
            out["ctx"] = dict(self.ctx)
        return out


class ValidationError(ValidatorError):
    """Raised when one or more fields fail validation.

    Use :meth:`errors` to introspect the individual failures programmatically,
    or :meth:`json` to get a JSON-serialisable summary.
    """

    def __init__(self, model: str, errors: list[ErrorDetail]) -> None:
        if not errors:
            raise ValueError("ValidationError requires at least one error")
        self._model = model
        self._errors: list[ErrorDetail] = list(errors)
        super().__init__(self._format_message())

    @property
    def model(self) -> str:
        return self._model

    def errors(self) -> list[dict[str, Any]]:
        """Return the failures as plain dicts (JSON friendly)."""

        return [e.to_dict() for e in self._errors]

    def error_count(self) -> int:
        return len(self._errors)

    def json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.errors(), indent=indent, default=str)

    def _format_message(self) -> str:
        n = len(self._errors)
        plural = "" if n == 1 else "s"
        lines = [f"{n} validation error{plural} for {self._model}"]
        for err in self._errors:
            loc = ".".join(str(p) for p in err.loc) or "<root>"
            lines.append(f"  {loc}")
            lines.append(f"    {err.msg} [type={err.type}]")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"ValidationError(model={self._model!r}, errors={self._errors!r})"
