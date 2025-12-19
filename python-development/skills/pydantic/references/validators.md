# Validators Reference

## Table of Contents
- [Field Validators](#field-validators)
- [Model Validators](#model-validators)
- [Validation Modes](#validation-modes)
- [Custom Types](#custom-types)
- [Annotated Validators](#annotated-validators)

## Field Validators

Use `@field_validator` to validate individual fields:

```python
from pydantic import BaseModel, field_validator, ValidationInfo

class User(BaseModel):
    name: str
    age: int
    email: str

    @field_validator('name')
    @classmethod
    def name_must_be_alpha(cls, v: str) -> str:
        if not v.replace(' ', '').isalpha():
            raise ValueError('Name must contain only letters')
        return v.title()

    @field_validator('age')
    @classmethod
    def age_must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError('Age must be positive')
        return v

    # Multiple fields with same validator
    @field_validator('name', 'email')
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Field cannot be empty')
        return v
```

### Validator Modes

```python
@field_validator('field', mode='before')  # Run before Pydantic's validation
@field_validator('field', mode='after')   # Run after Pydantic's validation (default)
@field_validator('field', mode='wrap')    # Full control over validation
@field_validator('field', mode='plain')   # Replace Pydantic's validation entirely
```

### Wrap Validator

```python
from pydantic import field_validator, ValidatorFunctionWrapHandler

class Model(BaseModel):
    value: int

    @field_validator('value', mode='wrap')
    @classmethod
    def validate_value(cls, v, handler: ValidatorFunctionWrapHandler) -> int:
        # Pre-processing
        if isinstance(v, str):
            v = int(v.strip())
        # Call next validator
        result = handler(v)
        # Post-processing
        return result * 2
```

### Access Other Fields

```python
from pydantic import field_validator, ValidationInfo

class User(BaseModel):
    password: str
    confirm_password: str

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info: ValidationInfo) -> str:
        if info.data.get('password') != v:
            raise ValueError('Passwords do not match')
        return v
```

## Model Validators

Use `@model_validator` for cross-field validation:

```python
from pydantic import BaseModel, model_validator
from typing_extensions import Self

class Order(BaseModel):
    items: list[str]
    discount_percent: float
    total: float

    @model_validator(mode='before')
    @classmethod
    def check_data(cls, data: dict) -> dict:
        # Modify raw input data
        if 'items' not in data:
            data['items'] = []
        return data

    @model_validator(mode='after')
    def validate_total(self) -> Self:
        expected = len(self.items) * 10 * (1 - self.discount_percent / 100)
        if abs(self.total - expected) > 0.01:
            raise ValueError('Total does not match calculated value')
        return self
```

### Model Validator Modes

```python
@model_validator(mode='before')  # Receives raw input (dict), returns dict
@model_validator(mode='after')   # Receives model instance, returns instance
@model_validator(mode='wrap')    # Full control, receives handler
```

## Validation Modes

### Strict Mode

```python
from pydantic import BaseModel, ConfigDict

class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True)
    
    value: int  # Won't coerce "123" to 123

# Or per-field
from pydantic import Field

class Model(BaseModel):
    strict_int: int = Field(strict=True)
    lax_int: int  # Will coerce strings
```

### Coercion Behavior

| Type | Lax Mode Accepts |
|------|------------------|
| `int` | int, float (no decimals), str (numeric) |
| `float` | int, float, str (numeric) |
| `str` | str, bytes |
| `bool` | bool, int (0/1), str ('true'/'false') |
| `datetime` | datetime, str (ISO), int (timestamp) |

## Custom Types

### Using `Annotated`

```python
from typing import Annotated
from pydantic import BaseModel, AfterValidator

def validate_even(v: int) -> int:
    if v % 2 != 0:
        raise ValueError('Must be even')
    return v

EvenInt = Annotated[int, AfterValidator(validate_even)]

class Model(BaseModel):
    value: EvenInt
```

### Using `__get_pydantic_core_schema__`

```python
from typing import Any
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

class CustomType:
    def __init__(self, value: str):
        self.value = value

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def _validate(cls, v: str) -> 'CustomType':
        return cls(v.upper())
```

## Annotated Validators

```python
from typing import Annotated
from pydantic import BaseModel, BeforeValidator, AfterValidator, PlainValidator

def strip_whitespace(v: str) -> str:
    return v.strip()

def to_uppercase(v: str) -> str:
    return v.upper()

CleanString = Annotated[str, BeforeValidator(strip_whitespace), AfterValidator(to_uppercase)]

class Model(BaseModel):
    name: CleanString  # " hello " -> "HELLO"
```

### Available Validator Types

```python
from pydantic import (
    BeforeValidator,   # Before Pydantic validation
    AfterValidator,    # After Pydantic validation
    PlainValidator,    # Replace Pydantic validation
    WrapValidator,     # Wrap Pydantic validation
)
```

## Handling Validation Errors

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
    print(e.json())         # JSON representation
    
    for error in e.errors():
        print(f"Field: {error['loc']}")
        print(f"Message: {error['msg']}")
        print(f"Type: {error['type']}")
```
