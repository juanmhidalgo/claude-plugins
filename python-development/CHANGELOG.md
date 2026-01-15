# Changelog

All notable changes to this project will be documented in this file.

## [1.3.0] - 2026-01-15

### Added
- Added `keywords`, `triggers`, and `code-triggers` fields to all skills for improved discoverability
- Skills now include semantic keywords for search, natural language triggers for intent matching, and code-triggers for pattern detection
- Plugin-level triggers added to plugin.json

### Changed
- Skill descriptions simplified (triggers moved to dedicated structured fields)
- Extracted code patterns (BaseModel, Field, etc.) from descriptions into `code-triggers` field

## [1.2.0] - 2025-12-30

### Added
- **tech-debt-finder** skill for analyzing Python codebases for technical debt
  - Debt markers scanning (TODO, FIXME, HACK, XXX)
  - Code smells detection (broad exceptions, hardcoded values, magic numbers)
  - Complexity indicators (long files, deep nesting)
  - Framework-specific anti-patterns for Django, Flask, FastAPI
  - Optional integration with radon, flake8, pylint
  - Prioritized markdown report generation (P1/P2/P3)
  - Reference documentation:
    - patterns.md - Complete scanning patterns by category

## [1.1.0] - 2025-12-19

### Added
- **django-ninja** skill for building APIs with Django using type hints
  - Basic setup and URL configuration
  - Path and query parameters
  - Schema and ModelSchema for request/response validation
  - Multiple response codes handling
  - File upload and form data
  - Routers for modular APIs
  - Authentication (Bearer, API Key, Django session)
  - Async support
  - Reference documentation:
    - schemas.md - Computed fields, resolvers, aliases, create_schema
    - errors.md - HTTP exceptions, validation errors, custom handlers
    - pagination.md - Built-in and custom pagination, filtering, ordering

## [1.0.0] - 2025-12-19

### Added
- Initial release of python-development plugin
- **pydantic** skill for Pydantic v2 data validation
  - Basic models and field constraints
  - Validators (field_validator, model_validator)
  - Serialization and parsing
  - Nested models and aliases
  - Configuration options
  - Common patterns (API models, settings, discriminated unions)
  - Reference documentation for advanced topics:
    - validators.md - Custom validators and validation modes
    - serialization.md - JSON schema and custom serializers
    - models.md - Inheritance, generics, dynamic models
    - types.md - Built-in types, network types, secret types
