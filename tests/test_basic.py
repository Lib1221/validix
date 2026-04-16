"""Smoke tests for the simplest BaseModel use cases."""

from __future__ import annotations

import pytest

from validix import BaseModel, ValidationError


class _User(BaseModel):
    id: int
    name: str
    is_active: bool = True


def test_simple_construction() -> None:
    u = _User(id=1, name="Ada")
    assert u.id == 1
    assert u.name == "Ada"
    assert u.is_active is True


def test_default_value_used_when_field_missing() -> None:
    u = _User(id=1, name="Ada")
    assert u.is_active is True


def test_missing_required_field_raises() -> None:
    with pytest.raises(ValidationError) as ctx:
        _User(id=1)  # type: ignore[call-arg]
    errors = ctx.value.errors()
    assert any(e["loc"] == ["name"] and e["type"] == "missing" for e in errors)


def test_repr_contains_field_values() -> None:
    u = _User(id=1, name="Ada")
    text = repr(u)
    assert "id=1" in text
    assert "name='Ada'" in text


def test_equality_by_field_values() -> None:
    a = _User(id=1, name="Ada")
    b = _User(id=1, name="Ada")
    c = _User(id=2, name="Ada")
    assert a == b
    assert a != c


def test_equality_with_other_type_returns_not_implemented() -> None:
    u = _User(id=1, name="Ada")
    assert u != ("id", 1, "name", "Ada")
