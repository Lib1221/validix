"""The BaseModel class — the heart of validix."""

from __future__ import annotations

import contextlib
import copy
import json
import sys
from collections.abc import Mapping
from typing import (
    Annotated,
    Any,
    ClassVar,
    ForwardRef,
    Literal,
    Optional,
    get_args,
    get_origin,
    get_type_hints,
)

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
)
from validix.validators import (
    FieldValidator,
    ModelValidator,
    get_field_validator,
    get_model_validator,
)

__all__ = ["BaseModel", "ModelConfig"]

# With aliases and populate_by_name=False, an input that uses a field's
# attribute name instead of its alias is parked under this prefix so it can
# go through the extra-key handling without clashing with the field itself.
_DISALLOWED_PREFIX = "_disallowed:"


def _is_parked(key: Any) -> bool:
    return isinstance(key, str) and key.startswith(_DISALLOWED_PREFIX)


def _input_key(key: Any) -> Any:
    """The key as the caller wrote it, without the internal parking prefix."""

    return key[len(_DISALLOWED_PREFIX) :] if _is_parked(key) else key


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


def _defining_namespace(depth: int = 1) -> dict[str, Any] | None:
    """Snapshot the local names of the scope that is creating a model.

    *depth* counts frames above the caller of this helper. Module-level code
    returns ``None``: ``get_type_hints`` reads module globals live, so names
    defined later in the module still resolve when the model is first used.
    """

    try:
        frame = sys._getframe(depth + 1)
    except ValueError:  # pragma: no cover - not enough frames
        return None
    if frame.f_locals is frame.f_globals:
        return None
    return dict(frame.f_locals)


def _resolve_type_hints(cls: type, localns: dict[str, Any] | None) -> dict[str, Any]:
    """``get_type_hints`` that also sees the defining scope and the class itself."""

    namespace: dict[str, Any] = dict(localns or {})
    namespace.update(vars(cls))
    namespace[cls.__name__] = cls  # self-references always mean this class
    return get_type_hints(cls, localns=namespace, include_extras=True)


def _has_forward_ref(tp: Any) -> bool:
    """True if *tp* is, or contains, a string annotation or ``ForwardRef``."""

    if isinstance(tp, (str, ForwardRef)):
        return True
    origin = get_origin(tp)
    if origin is Literal:
        return False  # Literal["cat"] holds values, not annotations
    args = get_args(tp)
    if origin is Annotated:
        args = args[:1]  # skip the metadata
    return any(_has_forward_ref(arg) for arg in args)


def _set_annotation(finfo: FieldInfo, annotation: Any) -> None:
    finfo.annotation = annotation
    finfo.required = not finfo.has_default and not is_optional(annotation)
    if not finfo.required and finfo.default is UNSET and finfo.default_factory is None:
        # Optional[X] with no explicit default → default to None
        finfo.default = None


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
        # Annotations that can't be resolved yet (self-references, models
        # defined later, names local to a function) stay unresolved here and
        # are resolved on first use; see BaseModel._resolve_forward_refs().
        localns = _defining_namespace()
        try:
            hints = get_type_hints(cls, include_extras=True)
        except Exception:
            try:
                hints = _resolve_type_hints(cls, localns)
            except Exception:
                hints = {}

        for fname, finfo in fields.items():
            if _has_forward_ref(finfo.annotation) and fname in hints:
                _set_annotation(finfo, hints[fname])

        own_annotations = dict(getattr(cls, "__annotations__", {}))

        for fname, annotation in own_annotations.items():
            if fname.startswith("_") or fname == "model_config":
                continue
            resolved = hints.get(fname, annotation)
            attr_value = namespace.get(fname, UNSET)

            if isinstance(attr_value, FieldInfo):
                finfo = attr_value
            elif attr_value is UNSET:
                finfo = Field()
            else:
                finfo = Field(default=attr_value)

            finfo.name = fname
            _set_annotation(finfo, resolved)
            fields[fname] = finfo

            # Don't leak Field()/FieldInfo onto the class itself
            if hasattr(cls, fname) and isinstance(getattr(cls, fname), FieldInfo):
                with contextlib.suppress(AttributeError):
                    delattr(cls, fname)

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
        unresolved = any(_has_forward_ref(finfo.annotation) for finfo in fields.values())
        cls.__validix_unresolved__ = unresolved  # type: ignore[attr-defined]
        # Keep the defining scope only while it's still needed for resolution.
        cls.__validix_localns__ = localns if unresolved else None  # type: ignore[attr-defined]
        cls.__validix_field_validators__ = field_validators  # type: ignore[attr-defined]
        cls.__validix_model_validators__ = model_validators  # type: ignore[attr-defined]
        # Pre-compute the iteration views used in the hot path.
        cls.__validix_fields_items__ = tuple(fields.items())  # type: ignore[attr-defined]
        cls.__validix_known_keys__ = frozenset(fields)  # type: ignore[attr-defined]

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
    __validix_fields_items__: ClassVar[tuple] = ()  # type: ignore[type-arg]
    __validix_known_keys__: ClassVar[frozenset[str]] = frozenset()
    # Optional[...] rather than `| None`: get_type_hints() evaluates these
    # class annotations at runtime, and Python 3.9 doesn't support `X | None`.
    __validix_localns__: ClassVar[Optional[dict[str, Any]]] = None
    __validix_unresolved__: ClassVar[bool] = False

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
    def model_rebuild(cls) -> None:
        """Resolve forward references using the names visible to the caller.

        Self-references and models defined later in the same module are
        resolved automatically the first time the model is used. Call this
        after defining the referenced models when they live inside a function,
        where the model can't see names created after it.

        Raises:
            ConfigError: if an annotation still can't be resolved.
        """

        cls._resolve_forward_refs(_defining_namespace())

    @classmethod
    def _resolve_forward_refs(cls, extra_namespace: dict[str, Any] | None = None) -> None:
        localns = dict(cls.__validix_localns__ or {})
        if extra_namespace:
            localns.update(extra_namespace)
        pending = [f for f in cls.model_fields.values() if _has_forward_ref(f.annotation)]
        if not pending:
            cls.__validix_unresolved__ = False
            return
        try:
            hints = _resolve_type_hints(cls, localns)
        except Exception as exc:
            names = ", ".join(repr(f.name) for f in pending)
            raise ConfigError(
                f"{cls.__name__} has field annotations that could not be resolved "
                f"({names}): {exc}. Define the referenced types before using the model, "
                f"or call {cls.__name__}.model_rebuild() once they exist."
            ) from exc
        for finfo in pending:
            if finfo.name in hints:
                _set_annotation(finfo, hints[finfo.name])
        cls.__validix_unresolved__ = any(_has_forward_ref(f.annotation) for f in pending)
        cls.__validix_localns__ = localns if cls.__validix_unresolved__ else None

    @classmethod
    def model_validate(cls, data: Any) -> BaseModel:
        if isinstance(data, cls):
            return data
        if not isinstance(data, Mapping):
            raise ValidationError(
                cls.__name__,
                [ErrorDetail(loc=(), msg="input must be a mapping", type="model_type", input=data)],
            )
        return cls(**dict(data))

    @classmethod
    def model_validate_json(cls, data: str | bytes) -> BaseModel:
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                cls.__name__,
                [
                    ErrorDetail(
                        loc=(), msg=f"invalid JSON: {exc.msg}", type="json_invalid", input=data
                    )
                ],
            ) from exc
        return cls.model_validate(parsed)

    def model_copy(
        self,
        *,
        update: Mapping[str, Any] | None = None,
        deep: bool = False,
    ) -> BaseModel:
        """Return a copy of this model, optionally overriding some fields.

        When ``update`` is supplied the new values are *re-validated* by
        going through :class:`BaseModel`-construction, so this is also a
        convenient way to coerce a partial patch.

        Set ``deep=True`` to recursively copy nested models / containers.
        """

        cls = type(self)
        if update is None:
            data: dict[str, Any] = copy.deepcopy(self.__dict__) if deep else dict(self.__dict__)
            new = cls.__new__(cls)
            object.__setattr__(new, "__dict__", data)
            return new
        merged = dict(self.__dict__)
        merged.update(update)
        if deep:
            merged = copy.deepcopy(merged)
        return cls(**merged)

    def model_dump(self, *, by_alias: bool = False, exclude_none: bool = False) -> dict[str, Any]:
        out: dict[str, Any] = {}
        fields = type(self).model_fields
        for fname, finfo in fields.items():
            value = getattr(self, fname)
            if exclude_none and value is None:
                continue
            key = finfo.alias if (by_alias and finfo.alias is not None) else fname
            out[key] = _to_python(value, by_alias=by_alias, exclude_none=exclude_none)
        for key, value in self._extras().items():
            if exclude_none and value is None:
                continue
            out[key] = _to_python(value, by_alias=by_alias, exclude_none=exclude_none)
        return out

    def _extras(self) -> dict[str, Any]:
        """Keys kept by ``extra='allow'``, in the order they were given."""

        cls = type(self)
        if cls.model_config.extra != "allow":
            return {}
        fields = cls.model_fields
        return {k: v for k, v in self.__dict__.items() if k not in fields}

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
        parts += [f"{k}={v!r}" for k, v in self._extras().items()]
        return f"{self.__class__.__name__}({', '.join(parts)})"

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__

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
        if cls.__validix_unresolved__:
            cls._resolve_forward_refs()
        cfg = cls.model_config
        # Fast paths cached on the class by the metaclass:
        fields_items = cls.__validix_fields_items__
        field_validators = cls.__validix_field_validators__
        alias_map = cls.__validix_alias_map__
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
                        ErrorDetail(
                            loc=(), msg=str(exc), type="model_validator", input=mutable_data
                        )
                    )
                    return validated, errors
                if isinstance(result, Mapping):
                    mutable_data = dict(result)

        # Resolve aliases. Pydantic-style semantics:
        #   populate_by_name=False (default): only the alias is accepted;
        #     supplying the canonical attribute name is treated as an
        #     unknown input key (silently dropped under extra='ignore',
        #     rejected under extra='forbid').
        #   populate_by_name=True: both names are accepted. If both are
        #     supplied, the canonical name wins and the alias is dropped.
        if alias_map:
            if not cfg.populate_by_name:
                # First, evict canonical-name input for any aliased field —
                # it's not an accepted key in this mode.
                for fname in alias_map.values():
                    if fname in mutable_data:
                        # Move the value to a synthetic key so it surfaces
                        # via the extras pipeline below if extra='forbid'.
                        mutable_data[_DISALLOWED_PREFIX + fname] = mutable_data.pop(fname)
            for alias, fname in alias_map.items():
                if alias in mutable_data and fname not in mutable_data:
                    mutable_data[fname] = mutable_data.pop(alias)
                elif alias in mutable_data and fname in mutable_data:
                    # populate_by_name=True path; canonical name wins
                    mutable_data.pop(alias)

        # Extra-key handling
        known = cls.__validix_known_keys__
        extras = [k for k in mutable_data if k not in known]
        if cfg.extra == "forbid" and extras:
            for k in extras:
                errors.append(
                    ErrorDetail(
                        loc=(_input_key(k),),
                        msg="extra fields are not permitted",
                        type="extra_forbidden",
                        input=mutable_data[k],
                    )
                )

        # Validate each known field
        for fname, finfo in fields_items:
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
            for fv in field_validators.get(fname, ()):
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
            for fv in field_validators.get(fname, ()):
                if fv.mode == "after":
                    try:
                        value = fv.func(cls, value)
                    except (ValueError, TypeError, AssertionError) as exc:
                        errors.append(
                            ErrorDetail(loc=(fname,), msg=str(exc), type="value_error", input=value)
                        )
                        break

            validated[fname] = value

        # Pass through extra keys when extra=allow. A field's attribute name
        # supplied where only its alias is accepted isn't kept: storing it would
        # shadow the field itself.
        if cfg.extra == "allow":
            for k in extras:
                if not _is_parked(k):
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


def _coerce_err(
    loc: tuple[str | int, ...], expected: str, value: Any, exc: Exception
) -> ErrorDetail:
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
        return {
            k: _to_python(v, by_alias=by_alias, exclude_none=exclude_none) for k, v in value.items()
        }
    return value
