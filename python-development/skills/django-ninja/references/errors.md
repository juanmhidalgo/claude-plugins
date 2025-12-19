# Error Handling Reference

## Table of Contents
- [HTTP Exceptions](#http-exceptions)
- [Validation Errors](#validation-errors)
- [Custom Exception Handlers](#custom-exception-handlers)
- [Response Codes](#response-codes)

## HTTP Exceptions

```python
from ninja.errors import HttpError

@api.get("/items/{id}")
def get_item(request, id: int):
    item = Item.objects.filter(id=id).first()
    if not item:
        raise HttpError(404, "Item not found")
    return item

# With custom headers
from django.http import Http404

@api.get("/items/{id}")
def get_item(request, id: int):
    try:
        return Item.objects.get(id=id)
    except Item.DoesNotExist:
        raise Http404("Item not found")
```

## Validation Errors

Django Ninja automatically validates input and returns 422 errors:

```json
{
  "detail": [
    {
      "type": "int_parsing",
      "loc": ["query", "item_id"],
      "msg": "Input should be a valid integer"
    }
  ]
}
```

### Custom Validation in Schema

```python
from pydantic import field_validator
from ninja import Schema

class ItemSchema(Schema):
    name: str
    price: float

    @field_validator('price')
    @classmethod
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v
```

## Custom Exception Handlers

```python
from ninja import NinjaAPI

api = NinjaAPI()

class ServiceUnavailable(Exception):
    pass

@api.exception_handler(ServiceUnavailable)
def service_unavailable(request, exc):
    return api.create_response(
        request,
        {"message": "Service temporarily unavailable"},
        status=503,
    )

# Usage
@api.get("/external")
def call_external(request):
    if not external_service_available():
        raise ServiceUnavailable()
    return {"status": "ok"}
```

### Override Default Handlers

```python
from ninja.errors import ValidationError

@api.exception_handler(ValidationError)
def custom_validation_error(request, exc):
    return api.create_response(
        request,
        {"errors": exc.errors, "message": "Invalid input"},
        status=422,
    )
```

## Response Codes

### Multiple Response Types

```python
class Success(Schema):
    id: int

class Error(Schema):
    message: str

@api.post("/items", response={201: Success, 400: Error, 409: Error})
def create_item(request, payload: ItemIn):
    if not payload.name:
        return 400, {"message": "Name required"}
    
    if Item.objects.filter(name=payload.name).exists():
        return 409, {"message": "Already exists"}
    
    item = Item.objects.create(**payload.dict())
    return 201, {"id": item.id}
```

### Using Response Code Ranges

```python
from ninja.responses import codes_4xx, codes_5xx

@api.get("/resource", response={200: Data, codes_4xx: Error})
def get_resource(request):
    # Any 4xx error will use Error schema
    pass

# Custom range
my_errors = frozenset({400, 401, 403, 404})

@api.get("/item", response={200: Item, my_errors: Error})
def get_item(request):
    pass
```

### 204 No Content

```python
@api.delete("/items/{id}", response={204: None})
def delete_item(request, id: int):
    Item.objects.filter(id=id).delete()
    return 204, None
```

## Django Shortcuts

```python
from django.shortcuts import get_object_or_404

@api.get("/items/{id}", response=ItemSchema)
def get_item(request, id: int):
    # Automatically raises 404 if not found
    return get_object_or_404(Item, id=id)

@api.get("/items/{id}")
def get_item(request, id: int):
    # With custom filter
    return get_object_or_404(Item, id=id, is_active=True)
```
