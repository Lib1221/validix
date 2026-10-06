# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `Dockerfile` (multi-stage targets `test` and `docs`) plus `docker-compose.yml`
  for running pytest and serving MkDocs without a local virtualenv.
- `BaseModel.model_rebuild()` for models defined inside a function that refer
  to models defined later in the same function.

### Fixed

- The README and getting-started page no longer say `pip install validix`,
  since the package isn't on PyPI yet. They show how to install from GitHub
  ([#18](https://github.com/Lib1221/validix/issues/18)).
- Forward references are resolved: self-referencing models, references to
  models defined later in the module, and models defined inside functions.
  These annotations used to stay as strings and the fields weren't validated
  at all. Under `from __future__ import annotations`, one unresolved
  annotation switched off validation for every field of the model
  ([#14](https://github.com/Lib1221/validix/issues/14)).
- An annotation that can't be resolved now raises `ConfigError` when the model
  is first used, instead of silently skipping validation.
- With `extra='allow'`, the extra keys kept on the instance now appear in
  `model_dump()`, `model_dump_json()` and the repr, after the declared fields
  ([#11](https://github.com/Lib1221/validix/issues/11)).
- A field's attribute name passed where only its alias is accepted no longer
  surfaces as `_disallowed:<name>`. `extra='forbid'` reports it under the name
  that was passed, and `extra='allow'` doesn't keep it on the instance.
- On Python 3.9, a subclass that declares no fields of its own no longer resets
  the fields it inherits. Their `Field()` constraints, defaults and aliases
  used to be dropped.

## [0.1.0] - 2026-04-24

### Added

- Initial release of `validix`.
- `BaseModel` with metaclass-based field collection.
- `Field()` constraints: `min_length`, `max_length`, `gt`, `ge`, `lt`, `le`, `pattern`, `multiple_of`.
- Type coercion with opt-in `strict` mode.
- Nested model validation, `list[Model]`, `dict[str, Model]`, `Optional[T]`, `Union[A, B]`.
- `@field_validator` and `@model_validator` decorators.
- `model_dump()` / `model_dump_json()` / `model_validate_json()` serialization helpers.
- `model_copy(*, update=None, deep=False)` for cloning models with re-validated overrides.
- Field aliases plus Pydantic-style `populate_by_name` semantics.
- `frozen` models with hashing support.
- 110-test suite, mypy-strict source tree, mkdocs-material documentation site.

[Unreleased]: https://github.com/Lib1221/validix/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Lib1221/validix/releases/tag/v0.1.0
