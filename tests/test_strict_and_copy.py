"""Tests for strict mode, frozen models, extra-key handling, and model_copy."""

from __future__ import annotations

import pytest

from validix import BaseModel, ConfigError, Field, ValidationError


class _StrictUser(BaseModel):
    class model_config:
        strict = True

    id: int
    name: str


def test_strict_rejects_string_int() -> None:
    with pytest.raises(ValidationError) as ctx:
        _StrictUser(id="42", name="Ada")
    assert ctx.value.errors()[0]["type"] == "type_error"


def test_strict_accepts_proper_types() -> None:
    u = _StrictUser(id=42, name="Ada")
    assert u.id == 42


def test_per_field_strict_overrides_model_lenient() -> None:
    class M(BaseModel):
        n: int = Field(strict=True)
        s: str

    M(n=1, s="x")
    with pytest.raises(ValidationError):
        M(n="1", s="x")


class _Frozen(BaseModel):
    class model_config:
        frozen = True

    a: int
    b: int


def test_frozen_rejects_attribute_assignment() -> None:
    f = _Frozen(a=1, b=2)
    with pytest.raises(ConfigError):
        f.a = 5


def test_frozen_models_are_hashable() -> None:
    f1 = _Frozen(a=1, b=2)
    f2 = _Frozen(a=1, b=2)
    assert hash(f1) == hash(f2)
    assert {f1, f2} == {f1}


def test_unhashable_when_not_frozen() -> None:
    class M(BaseModel):
        n: int

    with pytest.raises(TypeError):
        hash(M(n=1))


def test_extra_forbid_raises() -> None:
    class M(BaseModel):
        class model_config:
            extra = "forbid"

        n: int

    with pytest.raises(ValidationError):
        M(n=1, mystery=2)


def test_extra_allow_keeps_value_on_instance() -> None:
    class M(BaseModel):
        class model_config:
            extra = "allow"

        n: int

    m = M(n=1, mystery=2)
    assert m.mystery == 2  # type: ignore[attr-defined]


def test_extra_ignore_silently_drops() -> None:
    class M(BaseModel):
        n: int

    m = M(n=1, mystery=2)
    assert not hasattr(m, "mystery")


# --------------------------------------------------------------------------
# model_copy
# --------------------------------------------------------------------------

class _Mutable(BaseModel):
    name: str
    tags: list[str] = Field(default_factory=list)


def test_model_copy_without_update_is_a_clone() -> None:
    a = _Mutable(name="Ada", tags=["a", "b"])
    b = a.model_copy()
    assert a == b
    assert a is not b


def test_model_copy_shallow_shares_lists() -> None:
    a = _Mutable(name="Ada", tags=["a"])
    b = a.model_copy()
    b.tags.append("b")
    assert a.tags == ["a", "b"]


def test_model_copy_deep_does_not_share_lists() -> None:
    a = _Mutable(name="Ada", tags=["a"])
    b = a.model_copy(deep=True)
    b.tags.append("b")
    assert a.tags == ["a"]


def test_model_copy_with_update_revalidates() -> None:
    class N(BaseModel):
        n: int = Field(gt=0)

    a = N(n=1)
    b = a.model_copy(update={"n": 5})
    assert b.n == 5
    with pytest.raises(ValidationError):
        a.model_copy(update={"n": -1})
