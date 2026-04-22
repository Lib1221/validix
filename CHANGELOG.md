# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `BaseModel.model_copy(*, update=None, deep=False)` for cloning models
  with optional re-validated overrides.

### Changed

- Field-alias semantics now match Pydantic: with `populate_by_name=False`
  (the default), only the alias is accepted as an input key. Attribute-name
  input is treated as an unknown key (and therefore rejected by
  `extra='forbid'` instead of silently overriding the alias).

### Fixed

- `populate_by_name=True` no longer raises `extra_forbidden` when both the
  alias and the canonical field name are supplied in the same input.

## [0.1.0] - 2026-05-04

### Added

- Initial release of `validix`.
- `BaseModel` with metaclass-based field collection.
- `Field()` constraints: `min_length`, `max_length`, `gt`, `ge`, `lt`, `le`, `pattern`, `multiple_of`.
- Type coercion with opt-in `strict` mode.
- Nested model validation, `list[Model]`, `dict[str, Model]`, `Optional[T]`, `Union[A, B]`.
- `@field_validator` and `@model_validator` decorators.
- `model_dump()` / `model_dump_json()` serialization.
- Field aliases and `populate_by_name` configuration.
- Comprehensive test suite and 100% type-checked code base.

[Unreleased]: https://github.com/Lib1221/validix/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Lib1221/validix/releases/tag/v0.1.0
