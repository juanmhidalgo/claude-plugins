# Models Reference

## Table of Contents
- [Model Configuration](#model-configuration)
- [Inheritance](#inheritance)
- [Generic Models](#generic-models)
- [Dynamic Models](#dynamic-models)
- [Dataclasses](#dataclasses)
- [TypedDict](#typeddict)

## Model Configuration

All configuration options via `ConfigDict`:

```python
from pydantic import BaseModel, ConfigDict

class Model(BaseModel):
    model_config = ConfigDict(
        # Validation
        strict=False,                  # Strict type checking
        validate_default=False,        # Validate default values
        validate_assignment=False,     # Validate on attribute assignment
        revalidate_instances='never',  # 'always', 'never', 'subclass-instances'
        
        # Extra fields
        extra='ignore',                # 'allow', 'forbid', 'ignore'
        
        # Immutability
        frozen=False,                  # Make instances immutable
        
        # String handling
        str_strip_whitespace=False,    # Strip whitespace from strings
        str_to_lower=False,            # Convert strings to lowercase
        str_to_upper=False,            # Convert strings to uppercase
        str_min_length=None,           # Min length for all strings
        str_max_length=None,           # Max length for all strings
        
        # Aliases
        populate_by_name=False,        # Allow field name in addition to alias
        alias_generator=None,          # Function to generate aliases
        
        # ORM/attributes
        from_attributes=False,         # Enable ORM mode
        
        # Serialization
        ser_json_timedelta='iso8601',  # 'iso8601', 'float'
        ser_json_bytes='utf8',         # 'utf8', 'base64', 'hex'
        ser_json_inf_nan='null',       # 'null', 'constants'
        
        # Schema
        title=None,                    # JSON schema title
        json_schema_extra=None,        # Extra JSON schema properties
    )
```

## Inheritance

### Basic Inheritance

```python
from pydantic import BaseModel

class Animal(BaseModel):
    name: str
    species: str

class Dog(Animal):
    breed: str
    species: str = "Canis familiaris"

dog = Dog(name="Buddy", breed="Labrador")
```

### Override Validators

```python
class Parent(BaseModel):
    value: int

    @field_validator('value')
    @classmethod
    def validate_value(cls, v: int) -> int:
        return v * 2

class Child(Parent):
    @field_validator('value', mode='after')
    @classmethod
    def validate_value(cls, v: int) -> int:
        return v + 1  # Runs after parent's validator
```

### Merge Config

```python
class Parent(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')

class Child(Parent):
    model_config = ConfigDict(extra='allow')  # Overrides only 'extra'
    # strict=True is inherited
```

## Generic Models

### Basic Generic

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T')

class Response(BaseModel, Generic[T]):
    data: T
    status: str

# Use with concrete types
IntResponse = Response[int]
response = IntResponse(data=42, status="ok")

ListResponse = Response[list[str]]
response = ListResponse(data=["a", "b"], status="ok")
```

### Multiple Type Parameters

```python
K = TypeVar('K')
V = TypeVar('V')

class KeyValue(BaseModel, Generic[K, V]):
    key: K
    value: V

item = KeyValue[str, int](key="count", value=42)
```

### Nested Generics

```python
class Paginated(BaseModel, Generic[T]):
    items: list[T]
    page: int
    total: int

class User(BaseModel):
    name: str

paginated_users = Paginated[User](
    items=[User(name="Alice"), User(name="Bob")],
    page=1,
    total=2
)
```

## Dynamic Models

### create_model

```python
from pydantic import create_model, Field

# Simple dynamic model
DynamicUser = create_model(
    'DynamicUser',
    name=(str, ...),              # Required
    age=(int, 25),                # With default
    email=(str, Field(pattern=r'.*@.*')),
)

user = DynamicUser(name="John", email="j@e.com")
```

### Dynamic from Schema

```python
from pydantic import create_model

fields = {
    'name': (str, ...),
    'value': (int, 0),
}

Model = create_model('Model', **fields)
```

### Extend Existing Model

```python
class BaseUser(BaseModel):
    id: int

ExtendedUser = create_model(
    'ExtendedUser',
    __base__=BaseUser,
    email=(str, ...),
)
```

## Dataclasses

### Pydantic Dataclass

```python
from pydantic.dataclasses import dataclass

@dataclass
class User:
    id: int
    name: str
    age: int = 0

user = User(id='1', name='John')  # id coerced to int
```

### With Configuration

```python
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

@dataclass(config=ConfigDict(strict=True))
class StrictUser:
    name: str
    age: int
```

### Convert to/from Dict

```python
from pydantic import TypeAdapter

adapter = TypeAdapter(User)

# From dict
user = adapter.validate_python({'id': 1, 'name': 'John'})

# To dict
data = adapter.dump_python(user)
```

## TypedDict

### With Pydantic Validation

```python
from typing import TypedDict
from pydantic import TypeAdapter

class UserDict(TypedDict):
    name: str
    age: int

adapter = TypeAdapter(UserDict)
user = adapter.validate_python({'name': 'John', 'age': '25'})
# {'name': 'John', 'age': 25}
```

### Optional Fields

```python
from typing import TypedDict, NotRequired

class UserDict(TypedDict):
    name: str
    age: NotRequired[int]

# Or use total=False
class PartialUser(TypedDict, total=False):
    name: str
    age: int
```

## RootModel

For models that wrap a single value:

```python
from pydantic import RootModel

class Tags(RootModel[list[str]]):
    pass

tags = Tags(['python', 'pydantic'])
print(tags.root)  # ['python', 'pydantic']
print(tags.model_dump())  # ['python', 'pydantic']

# With validation
class PositiveInt(RootModel[int]):
    @model_validator(mode='after')
    def validate_positive(self) -> 'PositiveInt':
        if self.root <= 0:
            raise ValueError('Must be positive')
        return self
```

## Model Methods

```python
class User(BaseModel):
    name: str
    age: int

# Copy with updates
user = User(name="John", age=25)
updated = user.model_copy(update={'age': 26})
updated = user.model_copy(deep=True)  # Deep copy

# Rebuild schema (for forward refs)
User.model_rebuild()

# Get fields info
User.model_fields  # Dict[str, FieldInfo]
User.model_computed_fields  # Dict[str, ComputedFieldInfo]

# JSON schema
User.model_json_schema()

# Validate
User.model_validate({'name': 'John', 'age': 25})
User.model_validate_json('{"name": "John", "age": 25}')
User.model_validate_strings({'name': 'John', 'age': '25'})
```
