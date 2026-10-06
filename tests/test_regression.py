"""Regression tests for previously-broken edge cases."""

from __future__ import annotations

from typing import Optional

import pytest

from validix import BaseModel, Field, ValidationError


def test_optional_with_default_factory_preserves_none() -> None:
    class M(BaseModel):
        n: Optional[int] = Field(default_factory=lambda: None)

    assert M().n is None


def test_optional_field_with_no_default_uses_none_default() -> None:
    class M(BaseModel):
        n: Optional[int]

    instance = M()  # type: ignore[call-arg]
    assert instance.n is None


def test_inheritance_does_not_share_mutable_default() -> None:
    class Parent(BaseModel):
        items: list[int] = Field(default_factory=list)

    class Child(Parent):
        extra: int = 0

    a = Child()
    b = Child()
    a.items.append(1)
    assert b.items == []


def test_populate_by_name_accepts_either_input_name() -> None:
    class M(BaseModel):
        class model_config:
            populate_by_name = True
            extra = "forbid"

        full_name: str = Field(alias="fullName")

    assert M(full_name="Ada").full_name == "Ada"
    assert M(fullName="Ada").full_name == "Ada"


def test_populate_by_name_accepts_both_alias_and_attribute_name() -> None:
    """Regression: with populate_by_name=True and extra='forbid', supplying both
    the alias and the attribute name used to raise 'extra_forbidden' for the
    alias because it survived alias resolution."""

    class M(BaseModel):
        class model_config:
            populate_by_name = True
            extra = "forbid"

        full_name: str = Field(alias="fullName")

    instance = M(fullName="Ada", full_name="Ada")
    assert instance.full_name == "Ada"


def test_subclass_without_own_fields_keeps_inherited_ones() -> None:
    """Regression: on Python 3.9 a subclass that declares no fields of its own
    read its parent's annotations as its own and rebuilt every field, dropping
    the parent's Field() constraints, defaults and aliases."""

    class Parent(BaseModel):
        n: int = Field(gt=0)
        label: str = Field(default="x", alias="lbl")

    class Child(Parent):
        def describe(self) -> str:
            return f"{self.label}:{self.n}"

    with pytest.raises(ValidationError):
        Child(n=-1)
    assert Child(n=1).label == "x"
    assert Child(n=1, lbl="y").describe() == "y:1"
    assert Child.model_fields["n"].gt == 0
