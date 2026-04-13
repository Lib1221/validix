"""Helpers for introspecting type hints.

This module abstracts away the differences between :mod:`typing`,
:pep:`585` generics (``list[int]``) and :pep:`604` unions (``int | str``)
across the supported Python versions.
"""

from __future__ import annotations

import sys
import types
import typing
from typing import Any, Union, get_args, get_origin


__all__ = [
    "UNSET",
    "is_union",
    "is_optional",
    "is_literal",
    "unwrap_optional",
    "get_type_args",
    "get_type_origin",
    "type_name",
]


class _UnsetType:
    """Sentinel for "no value given" — distinct from ``None``."""

    _instance: "_UnsetType | None" = None

    def __new__(cls) -> "_UnsetType":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET: Any = _UnsetType()


_UNION_TYPES: tuple[type, ...]
if sys.version_info >= (3, 10):
    _UNION_TYPES = (typing.Union, types.UnionType)  # type: ignore[attr-defined]
else:  # pragma: no cover
    _UNION_TYPES = (typing.Union,)


def is_union(tp: Any) -> bool:
    """True if *tp* is ``Union[...]`` or ``X | Y``."""

    origin = get_origin(tp)
    if origin is Union:
        return True
    if sys.version_info >= (3, 10) and origin is types.UnionType:  # type: ignore[attr-defined]
        return True
    return False


def is_optional(tp: Any) -> bool:
    """True if *tp* allows ``None`` (``Optional[X]`` or ``X | None``)."""

    if not is_union(tp):
        return tp is type(None)
    return type(None) in get_args(tp)


def is_literal(tp: Any) -> bool:
    return get_origin(tp) is typing.Literal


def unwrap_optional(tp: Any) -> Any:
    """Strip a single ``None`` arm from ``Optional[X]``.

    ``Optional[int]`` → ``int``;  ``int | str | None`` → ``int | str``;
    everything else is returned unchanged.
    """

    if not is_union(tp):
        return tp
    args = tuple(a for a in get_args(tp) if a is not type(None))
    if len(args) == len(get_args(tp)):
        return tp
    if len(args) == 1:
        return args[0]
    return Union[args]  # type: ignore[return-value]


def get_type_args(tp: Any) -> tuple[Any, ...]:
    return get_args(tp)


def get_type_origin(tp: Any) -> Any:
    return get_origin(tp)


def type_name(tp: Any) -> str:
    """Pretty name for a type, used in error messages."""

    if tp is type(None):
        return "NoneType"
    name = getattr(tp, "__name__", None)
    if name:
        return name
    return repr(tp).replace("typing.", "")
