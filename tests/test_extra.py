"""Tests for how extra input keys are kept, dumped and reported."""

from __future__ import annotations

import json
from typing import Optional

import pytest

from validix import BaseModel, Field, ValidationError


class _Allow(BaseModel):
    class model_config:
        extra = "allow"

    a: int
    b: Optional[str] = None


class _Inner(BaseModel):
    x: int


def test_model_dump_includes_extra_keys() -> None:
    m = _Allow(z=1, a=2, m=3)
    assert m.model_dump() == {"a": 2, "b": None, "z": 1, "m": 3}


def test_extra_keys_come_after_fields_in_input_order() -> None:
    # Same order as Pydantic: declared fields first, then extras as given.
    m = _Allow(z=1, a=2, m=3)
    assert list(m.model_dump()) == ["a", "b", "z", "m"]


def test_model_dump_json_includes_extra_keys() -> None:
    m = _Allow(a=1, tags=["x", "y"], meta={"k": 1})
    assert json.loads(m.model_dump_json()) == {
        "a": 1,
        "b": None,
        "tags": ["x", "y"],
        "meta": {"k": 1},
    }


def test_exclude_none_applies_to_extra_keys() -> None:
    m = _Allow(a=1, gone=None, kept=0)
    assert m.model_dump(exclude_none=True) == {"a": 1, "kept": 0}


def test_extra_model_instances_are_dumped_recursively() -> None:
    m = _Allow(a=1, inner=_Inner(x=5), items=[_Inner(x=6)])
    dumped = m.model_dump()
    assert dumped["inner"] == {"x": 5}
    assert dumped["items"] == [{"x": 6}]


def test_repr_shows_extra_keys() -> None:
    assert repr(_Allow(a=1, z=2)) == "_Allow(a=1, b=None, z=2)"


def test_ignore_mode_does_not_dump_attributes_set_later() -> None:
    class M(BaseModel):
        n: int

    m = M(n=1)
    m.note = "set after construction"  # type: ignore[attr-defined]
    assert m.model_dump() == {"n": 1}


def test_forbid_reports_attribute_name_of_aliased_field_as_given() -> None:
    class M(BaseModel):
        class model_config:
            extra = "forbid"

        name: str = Field(alias="full_name")

    with pytest.raises(ValidationError) as ctx:
        M(name="Ada")
    extra = [e for e in ctx.value.errors() if e["type"] == "extra_forbidden"]
    assert [e["loc"] for e in extra] == [["name"]]


def test_allow_does_not_keep_attribute_name_of_aliased_field() -> None:
    class M(BaseModel):
        class model_config:
            extra = "allow"

        name: str = Field(alias="full_name")

    m = M(full_name="Ada", name="ignored", other=1)
    assert m.name == "Ada"
    assert m.model_dump() == {"name": "Ada", "other": 1}
    assert not any(key.startswith("_disallowed") for key in vars(m))
