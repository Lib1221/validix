"""validix — a lightweight data validation and parsing library."""

from __future__ import annotations

from validix.errors import (
    ConfigError,
    ErrorDetail,
    ValidationError,
    ValidatorError,
)
from validix.fields import Field, FieldInfo

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "ConfigError",
    "ErrorDetail",
    "Field",
    "FieldInfo",
    "ValidationError",
    "ValidatorError",
]
