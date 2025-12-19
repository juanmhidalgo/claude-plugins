# Schemas Reference

## Table of Contents
- [Computed Fields](#computed-fields)
- [Resolvers](#resolvers)
- [Nested Schemas](#nested-schemas)
- [Aliases](#aliases)
- [create_schema](#create_schema)

## Computed Fields

```python
from ninja import Schema

class UserSchema(Schema):
    id: int
    first_name: str
    last_name: str
    full_name: str  # Computed via resolver

    @staticmethod
    def resolve_full_name(obj):
        return f"{obj.first_name} {obj.last_name}"
```

## Resolvers

```python
class TaskSchema(Schema):
    id: int
    title: str
    owner_name: str = None
    lower_title: str

    @staticmethod
    def resolve_owner_name(obj):
        if obj.owner:
            return f"{obj.owner.first_name} {obj.owner.last_name}"
        return None

    # Instance method - access to self (other validated fields)
    def resolve_lower_title(self, obj):
        return self.title.lower()
```

### Context in Resolvers

```python
class DataSchema(Schema):
    id: int
    request_path: str = ""

    @staticmethod
    def resolve_request_path(obj, context):
        request = context["request"]
        return request.get_full_path()
```

## Nested Schemas

```python
class AddressSchema(Schema):
    street: str
    city: str

class UserSchema(Schema):
    id: int
    name: str
    address: AddressSchema = None
    addresses: list[AddressSchema] = []
```

### Self-referential

```python
class CategorySchema(Schema):
    id: int
    name: str
    parent: 'CategorySchema' = None

CategorySchema.model_rebuild()  # Required for forward refs
```

## Aliases

### Field Aliases

```python
from ninja import Schema, Field

class ItemSchema(Schema):
    item_id: int = Field(..., alias="id")
    item_name: str = Field(..., alias="name")
```

### Alias Generator (camelCase)

```python
from pydantic import ConfigDict

def to_camel(string: str) -> str:
    words = string.split('_')
    return words[0] + ''.join(w.capitalize() for w in words[1:])

class CamelSchema(Schema):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

class UserSchema(CamelSchema):
    user_name: str   # -> "userName" in JSON
    first_name: str  # -> "firstName" in JSON

# Use by_alias in response
@api.get("/users", response=list[UserSchema], by_alias=True)
def get_users(request):
    return User.objects.all()
```

## create_schema

Dynamic schema generation from Django models:

```python
from ninja.orm import create_schema
from django.contrib.auth.models import User

# Basic
UserSchema = create_schema(User, fields=['id', 'username', 'email'])

# With exclude
UserSchema = create_schema(User, exclude=['password', 'last_login'])

# With depth (nested relations)
UserSchema = create_schema(User, depth=1, fields=['username', 'groups'])
# groups becomes List[GroupSchema]

# Optional fields
UserSchema = create_schema(
    User,
    fields=['id', 'username', 'email'],
    optional_fields=['email'],  # or '__all__'
)

# Custom fields
UserSchema = create_schema(
    User,
    fields=['id', 'username'],
    custom_fields=[
        ('full_name', str, None),
        ('is_premium', bool, False),
    ],
)
```

## Schema Inheritance

```python
class BaseSchema(Schema):
    id: int
    created_at: datetime

class UserSchema(BaseSchema):
    username: str
    email: str

class AdminSchema(UserSchema):
    permissions: list[str]
```

## Optional vs Required

```python
class ItemSchema(Schema):
    # Required
    name: str
    
    # Optional with None default
    description: str | None = None
    
    # Optional with value default
    quantity: int = 0
    
    # Required but can be None
    category: str | None
```
