---
name: pydantic
description: |
  Use when implementing data validation, API schemas, or settings management with Pydantic v2.
  Provides model patterns, validators, serialization, and configuration options.
  Do NOT use for simple dataclasses without validation needs or when Pydantic overhead isn't justified.
keywords:
  - pydantic-v2
  - data-validation
  - type-hints
  - json-parsing
  - api-schemas
  - settings-management
triggers:
  - "create data model"
  - "validate input data"
  - "parse JSON"
  - "serialize objects"
  - "define API schema"
  - "handle configuration"
code-triggers:
  - "BaseModel"
  - "Field"
  - "field_validator"
  - "model_validator"
  - "model_validate"
  - "model_dump"
  - "TypeAdapter"
  - "ConfigDict"
---

# Pydantic v2

## Field Constraints

```python
from pydantic import BaseModel, Field

class Product(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0, description="Price in USD")
    quantity: int = Field(ge=0, default=0)
    tags: list[str] = Field(default_factory=list)
```

| Type | Constraints |
|------|-------------|
| Numeric | `gt`, `ge`, `lt`, `le`, `multiple_of` |
| String | `min_length`, `max_length`, `pattern` |
| Collections | `min_length`, `max_length` |

## Validation

```python
from pydantic import BaseModel, field_validator, model_validator

class User(BaseModel):
    name: str
    password: str
    password_confirm: str

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.title()

    @model_validator(mode='after')
    def passwords_match(self) -> 'User':
        if self.password != self.password_confirm:
            raise ValueError('Passwords do not match')
        return self
```

## Serialization & Parsing

```python
# To dict/JSON
user.model_dump()
user.model_dump(exclude={'password'}, by_alias=True, exclude_unset=True)
user.model_dump_json(indent=2)

# From dict/JSON
User.model_validate({'id': 1, 'name': 'John'})
User.model_validate_json('{"id": 1, "name": "John"}')

# Skip validation (trusted data)
User.model_construct(id=1, name='John')

# Validate arbitrary types
from pydantic import TypeAdapter
adapter = TypeAdapter(list[int])
result = adapter.validate_python(['1', '2', '3'])  # [1, 2, 3]
```

## Aliases

```python
class User(BaseModel):
    user_id: int = Field(alias='userId')           # For both input/output
    full_name: str = Field(validation_alias='fullName')  # Input only
    email: str = Field(serialization_alias='email_addr') # Output only

user = User.model_validate({'userId': 1, 'fullName': 'John', 'email': 'j@e.com'})
user.model_dump(by_alias=True)
```

## Configuration

```python
from pydantic import BaseModel, ConfigDict

class StrictUser(BaseModel):
    model_config = ConfigDict(
        strict=True,              # No type coercion
        frozen=True,              # Immutable
        extra='forbid',           # No extra fields allowed
        str_strip_whitespace=True,
        validate_assignment=True, # Validate on attribute assignment
        from_attributes=True,     # Enable ORM mode
    )
```

## Common Patterns

### API Request/Response

```python
class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1)
    email: str
    password: str = Field(min_length=8)

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
```

### Settings with Environment Variables

```python
# pip install pydantic-settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    api_key: str
    debug: bool = False
    model_config = ConfigDict(env_file='.env')

settings = Settings()  # Reads from environment/.env
```

## Quick Reference

| Task | Method |
|------|--------|
| Create from dict | `Model.model_validate(data)` |
| Create from JSON | `Model.model_validate_json(json_str)` |
| Skip validation | `Model.model_construct(**data)` |
| To dict | `instance.model_dump()` |
| To JSON | `instance.model_dump_json()` |
| Get JSON Schema | `Model.model_json_schema()` |
| Copy with changes | `instance.model_copy(update={'field': value})` |

## Advanced Topics

- **Custom Types & Validators**: [references/validators.md](references/validators.md)
- **JSON Schema Generation**: [references/serialization.md](references/serialization.md)
- **Model Inheritance & Generics**: [references/models.md](references/models.md)
- **Special Types (EmailStr, HttpUrl)**: [references/types.md](references/types.md)
