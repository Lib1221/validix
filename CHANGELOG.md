# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
