"""Tests for the public ValidationError API."""

from __future__ import annotations

import json

import pytest

from validix import BaseModel, ErrorDetail, ValidationError


def test_error_detail_to_dict_round_trip() -> None:
    detail = ErrorDetail(loc=("a", 0), msg="bad", type="x", input=42, ctx={"k": 1})
    assert detail.to_dict() == {
        "loc": ["a", 0],
        "msg": "bad",
        "type": "x",
        "input": 42,
        "ctx": {"k": 1},
    }


def test_validation_error_requires_at_least_one_detail() -> None:
    with pytest.raises(ValueError):
        ValidationError("M", [])


def test_validation_error_message_contains_loc_and_type() -> None:
    class M(BaseModel):
        n: int

    with pytest.raises(ValidationError) as ctx:
        M(n="abc")
    msg = str(ctx.value)
    assert "n" in msg
    assert "type=coercion_error" in msg


def test_validation_error_json_is_parseable() -> None:
    class M(BaseModel):
        n: int

    with pytest.raises(ValidationError) as ctx:
        M(n="abc")
    parsed = json.loads(ctx.value.json())
    assert parsed[0]["loc"] == ["n"]


def test_error_count() -> None:
    class M(BaseModel):
        a: int
        b: int

    with pytest.raises(ValidationError) as ctx:
        M(a="x", b="y")
    assert ctx.value.error_count() == 2
