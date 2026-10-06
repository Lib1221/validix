"""Tests for forward references: self-referencing models and names defined later.

This module deliberately does *not* use ``from __future__ import annotations``
so it can cover both string annotations and ``ForwardRef`` objects inside
typing constructs such as ``Optional["Node"]``.
"""

import sys
from typing import Optional

import pytest

from validix import BaseModel, ConfigError, ValidationError


class _Node(BaseModel):
    value: int
    next: Optional["_Node"] = None


class _Tree(BaseModel):
    name: str
    children: "list[_Tree]" = []


class _Owner(BaseModel):
    pet: Optional["_Pet"] = None  # _Pet is defined below
    name: str


class _Pet(BaseModel):
    species: str


def _types(model: type) -> dict:
    return {name: f.annotation for name, f in model.model_fields.items()}


def test_self_reference_at_module_level() -> None:
    n = _Node(value=1, next={"value": 2, "next": {"value": 3}})
    assert isinstance(n.next, _Node)
    assert isinstance(n.next.next, _Node)
    assert n.next.next.value == 3


def test_self_reference_validates_nested_values() -> None:
    with pytest.raises(ValidationError) as ctx:
        _Node(value=1, next={"value": "not a number"})
    (err,) = ctx.value.errors()
    # Optional[...] reports a union_error that carries the nested model's errors.
    assert err["loc"] == ["next"]
    assert err["type"] == "union_error"
    assert [e["loc"] for e in err["ctx"]["errors"]] == [["next", "value"]]

    with pytest.raises(ValidationError):
        _Node(value=1, next=5)


def test_string_annotation_with_generic_self_reference() -> None:
    t = _Tree(name="root", children=[{"name": "a"}, {"name": "b", "children": [{"name": "c"}]}])
    assert all(isinstance(c, _Tree) for c in t.children)
    assert t.children[1].children[0].name == "c"


def test_reference_to_model_defined_later_in_module() -> None:
    o = _Owner(name="Ada", pet={"species": "cat"})
    assert isinstance(o.pet, _Pet)
    assert _types(_Owner)["pet"] == Optional[_Pet]

    with pytest.raises(ValidationError):
        _Owner(name="Ada", pet={"species": 3.5j})


def test_self_reference_inside_a_function() -> None:
    # The reproducer from issue #14.
    def make_models() -> type:
        class Node(BaseModel):
            next: Optional["Node"] = None
            value: int

        return Node

    node_cls = make_models()
    n = node_cls(next={"value": 2}, value=1)
    assert isinstance(n.next, node_cls)
    assert n.next.value == 2


def test_string_annotations_inside_a_function_see_local_models() -> None:
    class Address(BaseModel):
        city: str

    class User(BaseModel):
        address: "Address"
        age: "int"

    u = User(address={"city": "Adama"}, age="30")
    assert isinstance(u.address, Address)
    assert u.age == 30

    with pytest.raises(ValidationError):
        User(address={"city": "Adama"}, age="thirty")


def test_optional_forward_ref_without_default_is_not_required() -> None:
    class Link(BaseModel):
        value: int
        next: "Optional[Link]"

    assert Link(value=1).next is None


def test_unresolvable_annotation_raises_config_error() -> None:
    class Broken(BaseModel):
        value: int
        other: Optional["DoesNotExist"] = None  # noqa: F821

    with pytest.raises(ConfigError, match="DoesNotExist"):
        Broken(value=1)


def test_model_rebuild_picks_up_models_defined_later_in_a_function() -> None:
    class Order(BaseModel):
        item: Optional["Item"] = None
        qty: int

    with pytest.raises(ConfigError, match="model_rebuild"):
        Order(qty=1)

    class Item(BaseModel):
        sku: str

    Order.model_rebuild()
    order = Order(qty=1, item={"sku": "A-1"})
    assert isinstance(order.item, Item)


def test_subclass_resolves_inherited_forward_refs() -> None:
    class Base(BaseModel):
        child: Optional["Leaf"] = None

    class Leaf(BaseModel):
        x: int

    class Derived(Base):
        y: int

    d = Derived(y=1, child={"x": 2})
    assert isinstance(d.child, Leaf)


@pytest.mark.skipif(sys.version_info >= (3, 10), reason="X | Y is valid at runtime on 3.10+")
def test_pep604_union_on_python39_gives_a_clear_error() -> None:
    class M(BaseModel):
        value: "int | None" = None

    with pytest.raises(ConfigError):
        M(value=1)
