---
name: pydantic
description: Data validation and settings management using Python type hints with Pydantic v2. Use when creating data models, validating input data, parsing JSON, serializing objects, defining API schemas, handling configuration, or working with structured data. Triggers on BaseModel, Field, validators, model_validate, model_dump, TypeAdapter.
---

# Pydantic v2

## Basic Model

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str
    age: int | None = None  # Optional with default

user = User(id=1, name="John", email="john@example.com")
print(user.model_dump())  # {'id': 1, 'name': 'John', 'email': 'john@example.com', 'age': None}
```

## Field Constraints

```python
from pydantic import BaseModel, Field

class Product(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0, description="Price in USD")
    quantity: int = Field(ge=0, default=0)
    tags: list[str] = Field(default_factory=list)
```

Common Field constraints:
- Numeric: `gt`, `ge`, `lt`, `le`, `multiple_of`
- String: `min_length`, `max_length`, `pattern`
- Collections: `min_length`, `max_length`

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

## Error Handling

```python
from pydantic import BaseModel, ValidationError

class User(BaseModel):
    name: str
    age: int

try:
    User(name=123, age='invalid')
except ValidationError as e:
    print(e.error_count())  # Number of errors
    print(e.errors())       # List of error dicts

    for error in e.errors():
        print(f"Field: {error['loc']}, Message: {error['msg']}")
```

## Serialization

```python
user = User(name="john", email="john@example.com")

# To dict
user.model_dump()
user.model_dump(exclude={'password'})
user.model_dump(include={'name', 'email'})
user.model_dump(by_alias=True)
user.model_dump(exclude_unset=True)  # Only explicitly set fields

# To JSON
user.model_dump_json()
user.model_dump_json(indent=2)
```

## Parsing/Validation

```python
# From dict
user = User.model_validate({'id': 1, 'name': 'John', 'email': 'j@e.com'})

# From JSON
user = User.model_validate_json('{"id": 1, "name": "John", "email": "j@e.com"}')

# Skip validation (for trusted data, better performance)
user = User.model_construct(id=1, name='John', email='j@e.com')

# Validate arbitrary types with TypeAdapter
from pydantic import TypeAdapter

adapter = TypeAdapter(list[int])
result = adapter.validate_python(['1', '2', '3'])  # [1, 2, 3]
```

## Nested Models

```python
class Address(BaseModel):
    street: str
    city: str
    country: str = "USA"

class User(BaseModel):
    name: str
    address: Address
    addresses: list[Address] = []

user = User(
    name="John",
    address={"street": "123 Main", "city": "NYC"}
)
```

## Computed Fields

```python
from pydantic import BaseModel, computed_field

class Rectangle(BaseModel):
    width: float
    height: float

    @computed_field
    @property
    def area(self) -> float:
        return self.width * self.height

rect = Rectangle(width=3, height=4)
rect.model_dump()  # {'width': 3.0, 'height': 4.0, 'area': 12.0}
```

## Private Attributes

```python
from pydantic import BaseModel, PrivateAttr

class Model(BaseModel):
    name: str
    _internal_cache: dict = PrivateAttr(default_factory=dict)
    _created_at: float = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self._created_at = time.time()
```

## Aliases

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    user_id: int = Field(alias='userId')  # For both validation/serialization
    full_name: str = Field(validation_alias='fullName')  # Only for input
    email_address: str = Field(serialization_alias='emailAddress')  # Only for output

# Input uses alias
user = User.model_validate({'userId': 1, 'fullName': 'John', 'email_address': 'j@e.com'})
# Output with by_alias=True
user.model_dump(by_alias=True)  # {'userId': 1, 'full_name': 'John', 'emailAddress': 'j@e.com'}
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
    name: str
    age: int
```

## Common Patterns

### API Request/Response Models

```python
class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1)
    email: str
    password: str = Field(min_length=8)

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # Enable ORM mode

    id: int
    name: str
    email: str
```

### Settings with Environment Variables

```python
# Requires: pip install pydantic-settings
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    database_url: str
    api_key: str
    debug: bool = False

    model_config = ConfigDict(env_file='.env')

settings = Settings()  # Reads from environment/`.env`
```

### Discriminated Unions

```python
from typing import Literal
from pydantic import BaseModel, Field

class Cat(BaseModel):
    pet_type: Literal['cat']
    meows: int

class Dog(BaseModel):
    pet_type: Literal['dog']
    barks: int

class Pet(BaseModel):
    pet: Cat | Dog = Field(discriminator='pet_type')
```

## Advanced Topics

- **Custom Types & Validators**: See [references/validators.md](references/validators.md)
- **JSON Schema Generation**: See [references/serialization.md](references/serialization.md)
- **Model Inheritance & Generics**: See [references/models.md](references/models.md)
- **Special Types (EmailStr, HttpUrl, etc.)**: See [references/types.md](references/types.md)

## Quick Reference

| Task | Method |
|------|--------|
| Create from dict | `Model.model_validate(data)` |
| Create from JSON | `Model.model_validate_json(json_str)` |
| Create without validation | `Model.model_construct(**data)` |
| To dict | `instance.model_dump()` |
| To JSON | `instance.model_dump_json()` |
| Get JSON Schema | `Model.model_json_schema()` |
| Copy with changes | `instance.model_copy(update={'field': value})` |
| Rebuild schema | `Model.model_rebuild()` |
