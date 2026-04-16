"""Tests for nested-model and generic-container validation."""

from __future__ import annotations

from typing import Optional

import pytest

from validix import BaseModel, ValidationError


class _Address(BaseModel):
    street: str
    city: str
    zip: str


class _User(BaseModel):
    name: str
    address: _Address
    secondary_addresses: list[_Address] = []


def test_nested_model_built_from_dict() -> None:
    u = _User(
        name="Ada",
        address={"street": "1 Babbage Way", "city": "London", "zip": "EC1"},
    )
    assert isinstance(u.address, _Address)
    assert u.address.city == "London"


def test_nested_model_accepts_existing_instance() -> None:
    addr = _Address(street="1", city="L", zip="A")
    u = _User(name="Ada", address=addr)
    assert u.address is addr


def test_nested_validation_errors_have_prefixed_loc() -> None:
    with pytest.raises(ValidationError) as ctx:
        _User(name="Ada", address={"street": "1", "city": "L"})  # missing zip
    errs = ctx.value.errors()
    assert any(e["loc"] == ["address", "zip"] and e["type"] == "missing" for e in errs)


def test_list_of_models() -> None:
    u = _User(
        name="Ada",
        address={"street": "1", "city": "L", "zip": "A"},
        secondary_addresses=[
            {"street": "2", "city": "P", "zip": "B"},
            {"street": "3", "city": "Q", "zip": "C"},
        ],
    )
    assert len(u.secondary_addresses) == 2
    assert all(isinstance(a, _Address) for a in u.secondary_addresses)


def test_list_of_models_reports_index_in_loc() -> None:
    with pytest.raises(ValidationError) as ctx:
        _User(
            name="Ada",
            address={"street": "1", "city": "L", "zip": "A"},
            secondary_addresses=[
                {"street": "ok", "city": "ok", "zip": "ok"},
                {"street": "bad"},  # missing city + zip
            ],
        )
    errs = ctx.value.errors()
    locs = {tuple(e["loc"]) for e in errs}
    assert ("secondary_addresses", 1, "city") in locs
    assert ("secondary_addresses", 1, "zip") in locs


class _Profile(BaseModel):
    age: Optional[int] = None
    bio: Optional[str] = None


def test_optional_fields_default_to_none() -> None:
    p = _Profile()
    assert p.age is None
    assert p.bio is None


def test_optional_field_accepts_none_explicitly() -> None:
    p = _Profile(age=None, bio=None)
    assert p.age is None


def test_optional_field_accepts_value() -> None:
    p = _Profile(age=21)
    assert p.age == 21


class _UnionModel(BaseModel):
    value: int | str


def test_union_picks_first_match() -> None:
    assert _UnionModel(value=42).value == 42
    assert _UnionModel(value="hello").value == "hello"


def test_dump_recurses_into_nested_models() -> None:
    u = _User(name="Ada", address={"street": "1", "city": "L", "zip": "A"})
    dumped = u.model_dump()
    assert dumped["address"] == {"street": "1", "city": "L", "zip": "A"}
