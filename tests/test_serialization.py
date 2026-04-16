"""Tests for model_dump / model_dump_json / model_validate_json."""

from __future__ import annotations

import json

import pytest

from validix import BaseModel, Field, ValidationError


class _M(BaseModel):
    id: int
    name: str = Field(alias="full_name")
    age: int | None = None


def test_model_dump_uses_attribute_names_by_default() -> None:
    m = _M(full_name="Ada", id=1)
    assert m.model_dump() == {"id": 1, "name": "Ada", "age": None}


def test_model_dump_with_by_alias() -> None:
    m = _M(full_name="Ada", id=1)
    assert m.model_dump(by_alias=True) == {"id": 1, "full_name": "Ada", "age": None}


def test_model_dump_with_exclude_none() -> None:
    m = _M(full_name="Ada", id=1)
    assert "age" not in m.model_dump(exclude_none=True)


def test_model_dump_json_round_trips() -> None:
    m = _M(full_name="Ada", id=1)
    payload = m.model_dump_json()
    assert json.loads(payload) == {"id": 1, "name": "Ada", "age": None}


def test_model_validate_json_parses_string() -> None:
    m = _M.model_validate_json('{"id": 1, "full_name": "Ada"}')
    assert m.id == 1
    assert m.name == "Ada"


def test_model_validate_json_rejects_invalid_json() -> None:
    with pytest.raises(ValidationError) as ctx:
        _M.model_validate_json("not json")
    assert ctx.value.errors()[0]["type"] == "json_invalid"


def test_model_validate_rejects_non_mapping() -> None:
    with pytest.raises(ValidationError) as ctx:
        _M.model_validate(123)
    assert ctx.value.errors()[0]["type"] == "model_type"
