"""The BaseModel class — the heart of validix."""

from __future__ import annotations

import copy
import json
from typing import Any, ClassVar, Mapping, get_type_hints

from validix.coercion import parse_bool, parse_float, parse_int, parse_str
from validix.errors import ConfigError, ErrorDetail, ValidationError
from validix.fields import Field, FieldInfo
from validix.types import (
    UNSET,
    get_type_args,
    get_type_origin,
    is_literal,
    is_optional,
    is_union,
    type_name,
    unwrap_optional,
)
from validix.validators import (
    FieldValidator,
    ModelValidator,
    get_field_validator,
    get_model_validator,
)


__all__ = ["BaseModel", "ModelConfig"]


class ModelConfig:
    """Per-model configuration (override on a subclass).

    Attributes:
        strict: if True, no lenient coercion happens.
        extra: 'ignore' (default), 'forbid', or 'allow'.
        frozen: if True, the model is immutable.
        populate_by_name: if True, fields with an alias also accept
            the original attribute name.
    """

    strict: bool = False
    extra: str = "ignore"
    frozen: bool = False
    populate_by_name: bool = False


class _ModelMeta(type):
    """Collect FieldInfo objects and validators at class creation."""

    def __new__(  # noqa: D401 - standard metaclass signature
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        if name == "BaseModel" and not any(isinstance(b, _ModelMeta) for b in bases):
            return cls

        # ---- Merge config from bases + this class ------------------------------
        config_attrs = ("strict", "extra", "frozen", "populate_by_name")
        cfg = type("ModelConfig", (ModelConfig,), {})
        for base in bases:
            base_cfg = getattr(base, "model_config", None)
            if base_cfg is not None:
                for a in config_attrs:
                    if hasattr(base_cfg, a):
                        setattr(cfg, a, getattr(base_cfg, a))
        own_cfg = namespace.get("model_config")
        if own_cfg is not None:
            for a in config_attrs:
                if hasattr(own_cfg, a):
                    setattr(cfg, a, getattr(own_cfg, a))
        cls.model_config = cfg  # type: ignore[attr-defined]

        # ---- Inherit fields from bases -----------------------------------------
        fields: dict[str, FieldInfo] = {}
        for base in bases:
            base_fields = getattr(base, "model_fields", None)
            if base_fields:
                for fname, finfo in base_fields.items():
                    fields[fname] = copy.copy(finfo)

        # ---- Resolve annotations on this class ---------------------------------
        try:
            hints = get_type_hints(cls, include_extras=True)
        except Exception:
            hints = dict(getattr(cls, "__annotations__", {}))

        own_annotations = dict(getattr(cls, "__annotations__", {}))

        for fname, annotation in own_annotations.items():
            if fname.startswith("_") or fname == "model_config":
                continue
            resolved = hints.get(fname, annotation)
            attr_value = namespace.get(fname, UNSET)

            if isinstance(attr_value, FieldInfo):
                finfo = attr_value
            elif attr_value is UNSET:
                finfo = Field()  # type: ignore[assignment]
            else:
                finfo = Field(default=attr_value)  # type: ignore[assignment]

            finfo.name = fname
            finfo.annotation = resolved
            finfo.required = not finfo.has_default and not is_optional(resolved)
            if not finfo.required and finfo.default is UNSET and finfo.default_factory is None:
                # Optional[X] with no explicit default → default to None
                finfo.default = None
            fields[fname] = finfo

            # Don't leak Field()/FieldInfo onto the class itself
            if hasattr(cls, fname) and isinstance(getattr(cls, fname), FieldInfo):
                try:
                    delattr(cls, fname)
                except AttributeError:  # pragma: no cover
                    pass

        # ---- Discover validators ------------------------------------------------
        field_validators: dict[str, list[FieldValidator]] = {}
        model_validators: list[ModelValidator] = []
        for attr_name, attr in namespace.items():
            fv = get_field_validator(attr)
            if fv is not None:
                for target in fv.fields:
                    if target not in fields:
                        raise ConfigError(
                            f"@field_validator on {name}.{attr_name} references unknown field {target!r}"
                        )
                    field_validators.setdefault(target, []).append(fv)
            mv = get_model_validator(attr)
            if mv is not None:
                model_validators.append(mv)

        # Inherit validators from bases
        for base in bases:
            for fname, vlist in getattr(base, "__validix_field_validators__", {}).items():
                field_validators.setdefault(fname, []).extend(vlist)
            model_validators[:0] = list(getattr(base, "__validix_model_validators__", []))

        cls.model_fields = fields  # type: ignore[attr-defined]
        cls.__validix_field_validators__ = field_validators  # type: ignore[attr-defined]
        cls.__validix_model_validators__ = model_validators  # type: ignore[attr-defined]

        # Build alias lookup
        alias_map: dict[str, str] = {}
        for fname, finfo in fields.items():
            if finfo.alias is not None:
                alias_map[finfo.alias] = fname
        cls.__validix_alias_map__ = alias_map  # type: ignore[attr-defined]

        return cls


class BaseModel(metaclass=_ModelMeta):
    """Base class for every validated model."""

    model_fields: ClassVar[dict[str, FieldInfo]] = {}
    model_config: ClassVar[type[ModelConfig]] = ModelConfig
    __validix_field_validators__: ClassVar[dict[str, list[FieldValidator]]] = {}
    __validix_model_validators__: ClassVar[list[ModelValidator]] = []
    __validix_alias_map__: ClassVar[dict[str, str]] = {}

    __slots__ = ("__dict__",)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def __init__(self, **data: Any) -> None:
        validated, errors = self._validate_data(data)
        if errors:
            raise ValidationError(self.__class__.__name__, errors)
        # bypass __setattr__ for frozen models
        object.__setattr__(self, "__dict__", validated)
        # Run after-mode model validators
        for mv in type(self).__validix_model_validators__:
            if mv.mode == "after":
                try:
                    result = mv.func(self)
                except (ValueError, TypeError, AssertionError) as exc:
                    raise ValidationError(
                        self.__class__.__name__,
                        [ErrorDetail(loc=(), msg=str(exc), type="model_validator", input=data)],
                    ) from exc
                if isinstance(result, BaseModel):
                    object.__setattr__(self, "__dict__", dict(result.__dict__))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @classmethod
    def model_validate(cls, data: Any) -> "BaseModel":
        if isinstance(data, cls):
            return data
        if not isinstance(data, Mapping):
            raise ValidationError(
                cls.__name__,
                [ErrorDetail(loc=(), msg="input must be a mapping", type="model_type", input=data)],
            )
        return cls(**dict(data))

    @classmethod
    def model_validate_json(cls, data: str | bytes) -> "BaseModel":
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                cls.__name__,
                [ErrorDetail(loc=(), msg=f"invalid JSON: {exc.msg}", type="json_invalid", input=data)],
            ) from exc
        return cls.model_validate(parsed)

    def model_dump(self, *, by_alias: bool = False, exclude_none: bool = False) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for fname, finfo in type(self).model_fields.items():
            value = getattr(self, fname)
            if exclude_none and value is None:
                continue
            key = finfo.alias if (by_alias and finfo.alias is not None) else fname
            out[key] = _to_python(value, by_alias=by_alias, exclude_none=exclude_none)
        return out

    def model_dump_json(
        self,
        *,
        by_alias: bool = False,
        exclude_none: bool = False,
        indent: int | None = None,
    ) -> str:
        return json.dumps(
            self.model_dump(by_alias=by_alias, exclude_none=exclude_none),
            indent=indent,
            default=str,
        )

    # ------------------------------------------------------------------
    # Mutability
    # ------------------------------------------------------------------
    def __setattr__(self, name: str, value: Any) -> None:
        cfg = type(self).model_config
        if cfg.frozen and name in type(self).model_fields:
            raise ConfigError(f"{self.__class__.__name__} is frozen; cannot assign to {name!r}")
        super().__setattr__(name, value)

    # ------------------------------------------------------------------
    # repr / equality
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        parts = [f"{n}={getattr(self, n)!r}" for n in type(self).model_fields]
        return f"{self.__class__.__name__}({', '.join(parts)})"

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__  # type: ignore[union-attr]

    def __hash__(self) -> int:
        cfg = type(self).model_config
        if not cfg.frozen:
            raise TypeError(f"{self.__class__.__name__} is not hashable (frozen=False)")
        return hash(tuple(sorted(self.__dict__.items())))

    # ------------------------------------------------------------------
    # Internal: full validation pipeline
    # ------------------------------------------------------------------
    def _validate_data(self, data: Mapping[str, Any]) -> tuple[dict[str, Any], list[ErrorDetail]]:
        cls = type(self)
        cfg = cls.model_config
        errors: list[ErrorDetail] = []
        validated: dict[str, Any] = {}

        # before-mode model validators get the raw dict
        mutable_data: dict[str, Any] = dict(data)
        for mv in cls.__validix_model_validators__:
            if mv.mode == "before":
                try:
                    result = mv.func(cls, mutable_data)
                except (ValueError, TypeError, AssertionError) as exc:
                    errors.append(
                        ErrorDetail(loc=(), msg=str(exc), type="model_validator", input=mutable_data)
                    )
                    return validated, errors
                if isinstance(result, Mapping):
                    mutable_data = dict(result)

        # Resolve aliases
        if cls.__validix_alias_map__:
            for alias, fname in cls.__validix_alias_map__.items():
                if alias in mutable_data and fname not in mutable_data:
                    mutable_data[fname] = mutable_data.pop(alias)
                elif alias in mutable_data and not cfg.populate_by_name:
                    mutable_data[fname] = mutable_data.pop(alias)

        # Extra-key handling
        known = set(cls.model_fields)
        extras = [k for k in mutable_data if k not in known]
        if cfg.extra == "forbid" and extras:
            for k in extras:
                errors.append(
                    ErrorDetail(loc=(k,), msg="extra fields are not permitted", type="extra_forbidden", input=mutable_data[k])
                )

        # Validate each known field
        for fname, finfo in cls.model_fields.items():
            if fname in mutable_data:
                raw = mutable_data[fname]
            elif finfo.has_default:
                validated[fname] = finfo.get_default()
                continue
            else:
                if finfo.required:
                    errors.append(
                        ErrorDetail(loc=(fname,), msg="field required", type="missing", input=None)
                    )
                continue

            # before-mode field validators
            for fv in cls.__validix_field_validators__.get(fname, []):
                if fv.mode == "before":
                    try:
                        raw = fv.func(cls, raw)
                    except (ValueError, TypeError, AssertionError) as exc:
                        errors.append(
                            ErrorDetail(loc=(fname,), msg=str(exc), type="value_error", input=raw)
                        )
                        raw = UNSET
                        break

            if raw is UNSET:
                continue

            # type coercion / validation
            value, type_errors = _validate_value(
                value=raw,
                annotation=finfo.annotation,
                loc=(fname,),
                strict=cfg.strict if finfo.strict is None else finfo.strict,
            )
            if type_errors:
                errors.extend(type_errors)
                continue

            # constraints
            constraint_errors = finfo.check_constraints(value, (fname,))
            if constraint_errors:
                errors.extend(constraint_errors)
                continue

            # after-mode field validators
            for fv in cls.__validix_field_validators__.get(fname, []):
                if fv.mode == "after":
                    try:
                        value = fv.func(cls, value)
                    except (ValueError, TypeError, AssertionError) as exc:
                        errors.append(
                            ErrorDetail(loc=(fname,), msg=str(exc), type="value_error", input=value)
                        )
                        break

            validated[fname] = value

        # Pass through extra keys when extra=allow
        if cfg.extra == "allow":
            for k in extras:
                validated[k] = mutable_data[k]

        return validated, errors


# ---------------------------------------------------------------------------
# Type-driven validation
# ---------------------------------------------------------------------------
def _validate_value(
    *,
    value: Any,
    annotation: Any,
    loc: tuple[str | int, ...],
    strict: bool,
) -> tuple[Any, list[ErrorDetail]]:
    """Recursively validate / coerce *value* against *annotation*."""

    if annotation is Any or annotation is None:
        return value, []

    # Optional / Union
    if is_union(annotation):
        if is_optional(annotation) and value is None:
            return None, []
        last_errors: list[ErrorDetail] = []
        for arm in get_type_args(annotation):
            if arm is type(None):
                continue
            v, errs = _validate_value(value=value, annotation=arm, loc=loc, strict=strict)
            if not errs:
                return v, []
            last_errors = errs
        return value, [
            ErrorDetail(
                loc=loc,
                msg=f"value did not match any union member ({type_name(annotation)})",
                type="union_error",
                input=value,
                ctx={"errors": [e.to_dict() for e in last_errors]},
            )
        ]

    # Literal
    if is_literal(annotation):
        choices = get_type_args(annotation)
        if value in choices:
            return value, []
        return value, [
            ErrorDetail(
                loc=loc,
                msg=f"input must be one of {list(choices)!r}",
                type="literal_error",
                input=value,
                ctx={"expected": list(choices)},
            )
        ]

    origin = get_type_origin(annotation)
    args = get_type_args(annotation)

    # Generic containers
    if origin in (list, tuple, set, frozenset):
        if not isinstance(value, (list, tuple, set, frozenset)):
            return value, [
                ErrorDetail(
                    loc=loc,
                    msg=f"expected {type_name(origin)}, got {type_name(type(value))}",
                    type="type_error",
                    input=value,
                )
            ]
        item_type = args[0] if args else Any
        out: list[Any] = []
        errors: list[ErrorDetail] = []
        for i, item in enumerate(value):
            v, errs = _validate_value(
                value=item, annotation=item_type, loc=loc + (i,), strict=strict
            )
            if errs:
                errors.extend(errs)
            else:
                out.append(v)
        if errors:
            return value, errors
        if origin is tuple:
            return tuple(out), []
        if origin is set:
            return set(out), []
        if origin is frozenset:
            return frozenset(out), []
        return out, []

    if origin is dict:
        if not isinstance(value, dict):
            return value, [
                ErrorDetail(
                    loc=loc,
                    msg=f"expected dict, got {type_name(type(value))}",
                    type="type_error",
                    input=value,
                )
            ]
        key_type = args[0] if args else Any
        val_type = args[1] if len(args) > 1 else Any
        out_d: dict[Any, Any] = {}
        errors = []
        for k, v in value.items():
            kv, kerrs = _validate_value(value=k, annotation=key_type, loc=loc + (k,), strict=strict)
            vv, verrs = _validate_value(value=v, annotation=val_type, loc=loc + (k,), strict=strict)
            errors.extend(kerrs)
            errors.extend(verrs)
            if not kerrs and not verrs:
                out_d[kv] = vv
        if errors:
            return value, errors
        return out_d, []

    # Nested BaseModel
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if isinstance(value, annotation):
            return value, []
        if isinstance(value, Mapping):
            try:
                return annotation(**dict(value)), []
            except ValidationError as exc:
                # Re-prefix nested locs with our location
                nested = [
                    ErrorDetail(
                        loc=loc + tuple(e["loc"]),
                        msg=e["msg"],
                        type=e["type"],
                        input=e.get("input"),
                        ctx=e.get("ctx", {}),
                    )
                    for e in exc.errors()
                ]
                return value, nested
        return value, [
            ErrorDetail(
                loc=loc,
                msg=f"expected {annotation.__name__} or mapping, got {type_name(type(value))}",
                type="model_type",
                input=value,
            )
        ]

    # Bare scalar types
    if annotation is bool:
        if isinstance(value, bool):
            return value, []
        if strict:
            return value, [_type_err(loc, "bool", value)]
        try:
            return parse_bool(value), []
        except ValueError as exc:
            return value, [_coerce_err(loc, "bool", value, exc)]

    if annotation is int:
        if isinstance(value, int) and not isinstance(value, bool):
            return value, []
        if strict:
            return value, [_type_err(loc, "int", value)]
        try:
            return parse_int(value), []
        except ValueError as exc:
            return value, [_coerce_err(loc, "int", value, exc)]

    if annotation is float:
        if isinstance(value, float):
            return value, []
        if isinstance(value, int) and not isinstance(value, bool):
            return float(value), []
        if strict:
            return value, [_type_err(loc, "float", value)]
        try:
            return parse_float(value), []
        except ValueError as exc:
            return value, [_coerce_err(loc, "float", value, exc)]

    if annotation is str:
        if isinstance(value, str):
            return value, []
        if strict:
            return value, [_type_err(loc, "str", value)]
        try:
            return parse_str(value), []
        except ValueError as exc:
            return value, [_coerce_err(loc, "str", value, exc)]

    if annotation is bytes:
        if isinstance(value, bytes):
            return value, []
        if isinstance(value, str) and not strict:
            return value.encode("utf-8"), []
        return value, [_type_err(loc, "bytes", value)]

    # Plain isinstance check for everything else (e.g. user-defined classes)
    if isinstance(annotation, type):
        if isinstance(value, annotation):
            return value, []
        return value, [_type_err(loc, type_name(annotation), value)]

    return value, []


def _type_err(loc: tuple[str | int, ...], expected: str, value: Any) -> ErrorDetail:
    return ErrorDetail(
        loc=loc,
        msg=f"expected {expected}, got {type_name(type(value))}",
        type="type_error",
        input=value,
        ctx={"expected_type": expected},
    )


def _coerce_err(loc: tuple[str | int, ...], expected: str, value: Any, exc: Exception) -> ErrorDetail:
    return ErrorDetail(
        loc=loc,
        msg=f"could not coerce to {expected}: {exc}",
        type="coercion_error",
        input=value,
        ctx={"expected_type": expected},
    )


def _to_python(value: Any, *, by_alias: bool, exclude_none: bool) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(by_alias=by_alias, exclude_none=exclude_none)
    if isinstance(value, list):
        return [_to_python(v, by_alias=by_alias, exclude_none=exclude_none) for v in value]
    if isinstance(value, tuple):
        return [_to_python(v, by_alias=by_alias, exclude_none=exclude_none) for v in value]
    if isinstance(value, set):
        return [_to_python(v, by_alias=by_alias, exclude_none=exclude_none) for v in value]
    if isinstance(value, dict):
        return {k: _to_python(v, by_alias=by_alias, exclude_none=exclude_none) for k, v in value.items()}
    return value
