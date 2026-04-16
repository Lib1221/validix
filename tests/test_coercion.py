"""Tests for the lenient parsers in :mod:`validix.coercion`."""

from __future__ import annotations

import pytest

from validix.coercion import parse_bool, parse_float, parse_int, parse_str


@pytest.mark.parametrize(
    "value,expected",
    [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        ("true", True),
        ("FALSE", False),
        ("Yes", True),
        ("no", False),
        ("on", True),
        ("off", False),
    ],
)
def test_parse_bool_accepts_common_values(value: object, expected: bool) -> None:
    assert parse_bool(value) is expected


@pytest.mark.parametrize("value", ["maybe", 2, -1, "tru", None, [], {}])
def test_parse_bool_rejects_garbage(value: object) -> None:
    with pytest.raises(ValueError):
        parse_bool(value)


@pytest.mark.parametrize(
    "value,expected",
    [
        (42, 42),
        (-3, -3),
        ("17", 17),
        (" 5 ", 5),
        (3.0, 3),
        ("3.0", 3),
    ],
)
def test_parse_int_accepts(value: object, expected: int) -> None:
    assert parse_int(value) == expected


@pytest.mark.parametrize("value", [True, False, "1.5", 1.5, "abc", None])
def test_parse_int_rejects(value: object) -> None:
    with pytest.raises(ValueError):
        parse_int(value)


@pytest.mark.parametrize(
    "value,expected",
    [(1, 1.0), (1.5, 1.5), ("3.14", 3.14), (" -2.5 ", -2.5)],
)
def test_parse_float_accepts(value: object, expected: float) -> None:
    assert parse_float(value) == expected


@pytest.mark.parametrize("value", [True, "abc", None, []])
def test_parse_float_rejects(value: object) -> None:
    with pytest.raises(ValueError):
        parse_float(value)


@pytest.mark.parametrize(
    "value,expected",
    [("hi", "hi"), (42, "42"), (1.5, "1.5"), (b"hello", "hello")],
)
def test_parse_str_accepts(value: object, expected: str) -> None:
    assert parse_str(value) == expected


@pytest.mark.parametrize("value", [True, None, [], {}])
def test_parse_str_rejects(value: object) -> None:
    with pytest.raises(ValueError):
        parse_str(value)
