# Changelog

All notable changes to this project will be documented in this file.

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
