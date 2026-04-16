"""Tests for @field_validator and @model_validator."""

from __future__ import annotations

import pytest

from validix import BaseModel, ConfigError, ValidationError, field_validator, model_validator


def test_field_validator_after_mode_transforms_value() -> None:
    class M(BaseModel):
        name: str

        @field_validator("name")
        def _strip(cls, value: str) -> str:
            return value.strip().title()

    assert M(name="  ada lovelace  ").name == "Ada Lovelace"


def test_field_validator_can_raise() -> None:
    class M(BaseModel):
        name: str

        @field_validator("name")
        def _no_admin(cls, value: str) -> str:
            if value.lower() == "admin":
                raise ValueError("'admin' is reserved")
            return value

    with pytest.raises(ValidationError) as ctx:
        M(name="admin")
    assert ctx.value.errors()[0]["msg"] == "'admin' is reserved"


def test_field_validator_before_mode_runs_before_coercion() -> None:
    class M(BaseModel):
        n: int

        @field_validator("n", mode="before")
        def _drop_currency(cls, value: object) -> object:
            if isinstance(value, str) and value.startswith("$"):
                return value[1:]
            return value

    assert M(n="$42").n == 42


def test_model_validator_after_mode_can_inspect_full_model() -> None:
    class M(BaseModel):
        a: int
        b: int

        @model_validator(mode="after")
        def _check(self):  # type: ignore[no-untyped-def]
            if self.a + self.b != 10:
                raise ValueError("a + b must equal 10")
            return self

    M(a=4, b=6)
    with pytest.raises(ValidationError):
        M(a=1, b=2)


def test_model_validator_before_mode_can_mutate_input() -> None:
    class M(BaseModel):
        a: int

        @model_validator(mode="before")
        def _double(cls, data):  # type: ignore[no-untyped-def]
            return {"a": data["a"] * 2}

    assert M(a=3).a == 6


def test_field_validator_unknown_field_is_config_error() -> None:
    with pytest.raises(ConfigError):

        class _Bad(BaseModel):
            name: str

            @field_validator("does_not_exist")
            def _v(cls, value: str) -> str:  # pragma: no cover
                return value
