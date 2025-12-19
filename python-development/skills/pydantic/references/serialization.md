# Serialization Reference

## Table of Contents
- [Model Dump](#model-dump)
- [JSON Serialization](#json-serialization)
- [Custom Serializers](#custom-serializers)
- [JSON Schema](#json-schema)
- [Aliases](#aliases)

## Model Dump

### Basic Usage

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    password: str

user = User(id=1, name="John", password="secret")

# To dictionary
user.model_dump()
# {'id': 1, 'name': 'John', 'password': 'secret'}
```

### Dump Options

```python
# Include/exclude fields
user.model_dump(include={'id', 'name'})
user.model_dump(exclude={'password'})

# Nested include/exclude
class Address(BaseModel):
    street: str
    city: str
    zip: str

class User(BaseModel):
    name: str
    address: Address

user.model_dump(exclude={'address': {'zip'}})

# Exclude unset/none/defaults
user.model_dump(exclude_unset=True)   # Only fields explicitly set
user.model_dump(exclude_none=True)    # Exclude None values
user.model_dump(exclude_defaults=True) # Exclude default values

# Use aliases
user.model_dump(by_alias=True)

# Serialization mode
user.model_dump(mode='json')  # JSON-compatible output
user.model_dump(mode='python') # Python objects (default)
```

### Field-Level Exclusion

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    name: str
    password: str = Field(exclude=True)  # Always excluded
```

## JSON Serialization

```python
# To JSON string
user.model_dump_json()

# With options
user.model_dump_json(
    indent=2,
    exclude={'password'},
    by_alias=True,
)

# From JSON
User.model_validate_json('{"id": 1, "name": "John"}')
```

### Custom JSON Encoders

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class Event(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    timestamp: datetime
```

## Custom Serializers

### Field Serializer

```python
from pydantic import BaseModel, field_serializer
from datetime import datetime

class Event(BaseModel):
    name: str
    timestamp: datetime

    @field_serializer('timestamp')
    def serialize_timestamp(self, dt: datetime) -> str:
        return dt.strftime('%Y-%m-%d %H:%M')
```

### Serializer Modes

```python
@field_serializer('field', mode='plain')  # Replace default serialization
@field_serializer('field', mode='wrap')   # Wrap default serialization

# Wrap example
@field_serializer('value', mode='wrap')
def serialize_value(self, value: int, handler) -> str:
    # handler calls next serializer
    result = handler(value)
    return f"Value: {result}"
```

### Model Serializer

```python
from pydantic import BaseModel, model_serializer

class Point(BaseModel):
    x: float
    y: float

    @model_serializer
    def serialize_model(self) -> str:
        return f"({self.x}, {self.y})"
```

### Using Annotated

```python
from typing import Annotated
from pydantic import BaseModel, PlainSerializer

UpperStr = Annotated[str, PlainSerializer(lambda x: x.upper(), return_type=str)]

class Model(BaseModel):
    name: UpperStr  # Serializes to uppercase
```

## JSON Schema

### Generate Schema

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str

schema = User.model_json_schema()
# {
#     'properties': {
#         'id': {'title': 'Id', 'type': 'integer'},
#         'name': {'title': 'Name', 'type': 'string'}
#     },
#     'required': ['id', 'name'],
#     'title': 'User',
#     'type': 'object'
# }
```

### Customize Schema

```python
from pydantic import BaseModel, Field

class Product(BaseModel):
    name: str = Field(
        title="Product Name",
        description="The name of the product",
        examples=["Widget", "Gadget"],
        json_schema_extra={'category': 'consumer'}
    )
    price: float = Field(gt=0, description="Price in USD")
```

### Schema for Types

```python
from pydantic import TypeAdapter

adapter = TypeAdapter(list[int])
schema = adapter.json_schema()
```

## Aliases

### Validation vs Serialization Aliases

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    # alias: used for both validation and serialization
    user_id: int = Field(alias='userId')
    
    # validation_alias: only for input
    full_name: str = Field(validation_alias='fullName')
    
    # serialization_alias: only for output
    email: str = Field(serialization_alias='emailAddress')
```

### Alias Generator

```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class Model(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allow both alias and field name
    )
    
    user_name: str  # Alias: userName
    first_name: str  # Alias: firstName
```

### AliasPath and AliasChoices

```python
from pydantic import BaseModel, Field, AliasPath, AliasChoices

class User(BaseModel):
    # Extract from nested path
    name: str = Field(validation_alias=AliasPath('data', 'user', 'name'))
    
    # Accept multiple aliases
    email: str = Field(validation_alias=AliasChoices('email', 'e-mail', 'mail'))

# Works with:
# {'data': {'user': {'name': 'John'}}, 'email': 'j@e.com'}
# {'data': {'user': {'name': 'John'}}, 'e-mail': 'j@e.com'}
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
