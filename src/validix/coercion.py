"""Lenient parsers used when ``strict=False`` (the default).

Each parser raises :class:`ValueError` when the input cannot be reasonably
interpreted as the target type. The model layer turns these into
``ErrorDetail`` records.
"""

from __future__ import annotations

from typing import Any


__all__ = [
    "parse_bool",
    "parse_int",
    "parse_float",
    "parse_str",
]


_TRUE = {"true", "1", "yes", "y", "on", "t"}
_FALSE = {"false", "0", "no", "n", "off", "f"}


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value == 0:
            return False
        if value == 1:
            return True
        raise ValueError(f"cannot coerce {value!r} to bool")
    if isinstance(value, str):
        v = value.strip().lower()
        if v in _TRUE:
            return True
        if v in _FALSE:
            return False
    raise ValueError(f"cannot coerce {value!r} to bool")


def parse_int(value: Any) -> int:
    if isinstance(value, bool):
        # bool is a subclass of int, but we treat them as different here
        raise ValueError(f"cannot coerce {value!r} to int")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise ValueError(f"cannot coerce non-integer float {value!r} to int")
    if isinstance(value, str):
        s = value.strip()
        try:
            return int(s)
        except ValueError:
            try:
                f = float(s)
            except ValueError:
                raise ValueError(f"cannot coerce {value!r} to int") from None
            if f.is_integer():
                return int(f)
            raise ValueError(f"cannot coerce non-integer string {value!r} to int")
    raise ValueError(f"cannot coerce {value!r} to int")


def parse_float(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError(f"cannot coerce {value!r} to float")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError as exc:
            raise ValueError(f"cannot coerce {value!r} to float") from exc
    raise ValueError(f"cannot coerce {value!r} to float")


def parse_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"cannot decode bytes as utf-8: {exc}") from exc
    raise ValueError(f"cannot coerce {value!r} to str")
