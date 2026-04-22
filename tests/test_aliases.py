"""Tests for field aliases and populate_by_name."""

from __future__ import annotations

import pytest

from validix import BaseModel, Field, ValidationError


class _Aliased(BaseModel):
    full_name: str = Field(alias="fullName")
    user_id: int = Field(alias="userId")


def test_alias_only_input_is_promoted_to_attribute_name() -> None:
    m = _Aliased(fullName="Ada", userId=7)
    assert m.full_name == "Ada"
    assert m.user_id == 7


def test_attribute_name_input_rejected_when_populate_by_name_false() -> None:
    with pytest.raises(ValidationError) as ctx:
        _Aliased(full_name="Ada", user_id=7)
    assert {tuple(e["loc"]) for e in ctx.value.errors()} == {("full_name",), ("user_id",)}


def test_dump_uses_attribute_names_by_default() -> None:
    m = _Aliased(fullName="Ada", userId=7)
    assert m.model_dump() == {"full_name": "Ada", "user_id": 7}


def test_dump_with_by_alias() -> None:
    m = _Aliased(fullName="Ada", userId=7)
    assert m.model_dump(by_alias=True) == {"fullName": "Ada", "userId": 7}


class _PopulateByName(BaseModel):
    class model_config:
        populate_by_name = True

    full_name: str = Field(alias="fullName")


def test_populate_by_name_accepts_alias() -> None:
    assert _PopulateByName(fullName="Ada").full_name == "Ada"


def test_populate_by_name_accepts_attribute_name() -> None:
    assert _PopulateByName(full_name="Ada").full_name == "Ada"


def test_populate_by_name_dump_uses_attribute_name_by_default() -> None:
    m = _PopulateByName(full_name="Ada")
    assert m.model_dump() == {"full_name": "Ada"}
    assert m.model_dump(by_alias=True) == {"fullName": "Ada"}
