"""Tests for Field() constraints."""

from __future__ import annotations

import pytest

from validix import BaseModel, ConfigError, Field, ValidationError


def test_field_disallows_default_and_default_factory() -> None:
    with pytest.raises(ConfigError):
        Field(default=1, default_factory=lambda: 2)


def test_field_default_factory_is_called_each_time() -> None:
    counter = {"n": 0}

    def make_list() -> list[int]:
        counter["n"] += 1
        return [counter["n"]]

    class Bag(BaseModel):
        items: list[int] = Field(default_factory=make_list)

    a = Bag()
    b = Bag()
    assert a.items != b.items
    assert a.items == [1]
    assert b.items == [2]


def test_min_length_string() -> None:
    class M(BaseModel):
        name: str = Field(min_length=3)

    M(name="abc")
    with pytest.raises(ValidationError) as ctx:
        M(name="ab")
    assert ctx.value.errors()[0]["type"] == "too_short"


def test_max_length_list() -> None:
    class M(BaseModel):
        items: list[int] = Field(max_length=2)

    M(items=[1, 2])
    with pytest.raises(ValidationError) as ctx:
        M(items=[1, 2, 3])
    assert ctx.value.errors()[0]["type"] == "too_long"


def test_numeric_constraints() -> None:
    class M(BaseModel):
        n: int = Field(gt=0, le=10, multiple_of=2)

    M(n=2)
    M(n=10)
    with pytest.raises(ValidationError):
        M(n=0)
    with pytest.raises(ValidationError):
        M(n=11)
    with pytest.raises(ValidationError):
        M(n=3)


def test_pattern_matching() -> None:
    class M(BaseModel):
        sku: str = Field(pattern=r"^[A-Z]{3}-\d{4}$")

    M(sku="ABC-1234")
    with pytest.raises(ValidationError) as ctx:
        M(sku="abc-1234")
    assert ctx.value.errors()[0]["type"] == "string_pattern_mismatch"
