---
name: django-ninja
description: |
  Use when building REST APIs with Django Ninja and type hints.
  Provides endpoint patterns, schemas, routers, authentication, and async support.
  Do NOT use for GraphQL APIs, Django REST Framework projects, or when raw Django views are simpler.
keywords:
  - django-ninja
  - django-api
  - rest-api
  - type-hints
  - openapi
triggers:
  - "create Django API"
  - "define API endpoint"
  - "build REST API with Django"
  - "Django API schema"
  - "Django authentication"
code-triggers:
  - "NinjaAPI"
  - "Schema"
  - "ModelSchema"
  - "Router"
  - "@api.get"
  - "@api.post"
  - "@api.put"
  - "@api.delete"
---

# Django Ninja

## Setup

```python
# api.py
from ninja import NinjaAPI
api = NinjaAPI()

@api.get("/hello")
def hello(request, name: str = "world"):
    return {"message": f"Hello {name}"}

# urls.py
urlpatterns = [path("api/", api.urls)]
```

## Path & Query Parameters

```python
# Query: /items?skip=0&limit=10
@api.get("/items")
def list_items(request, skip: int = 0, limit: int = 10):
    return items[skip : skip + limit]

# Path: /items/123
@api.get("/items/{item_id}")
def get_item(request, item_id: int):
    return get_object_or_404(Item, id=item_id)
```

## Schema (Request/Response)

```python
from ninja import Schema

class ItemIn(Schema):
    name: str
    price: float
    quantity: int = 1

class ItemOut(Schema):
    id: int
    name: str
    price: float

@api.post("/items", response=ItemOut)
def create_item(request, payload: ItemIn):
    return Item.objects.create(**payload.dict())

@api.get("/items", response=list[ItemOut])
def list_items(request):
    return Item.objects.all()
```

## ModelSchema

```python
from ninja import ModelSchema

class UserSchema(ModelSchema):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        # or: exclude = ['password']
```

## Multiple Response Codes

```python
class Error(Schema):
    message: str

@api.get("/items/{id}", response={200: ItemOut, 404: Error})
def get_item(request, id: int):
    try:
        return Item.objects.get(id=id)
    except Item.DoesNotExist:
        return 404, {"message": "Not found"}

@api.delete("/items/{id}", response={204: None})
def delete_item(request, id: int):
    Item.objects.filter(id=id).delete()
    return 204, None
```

## File Upload & Form

```python
from ninja import File, UploadedFile, Form

@api.post("/upload")
def upload(request, file: UploadedFile = File(...)):
    return {"name": file.name, "size": len(file.read())}

@api.post("/login")
def login(request, username: Form[str], password: Form[str]):
    return {"token": "..."}
```

## Routers (Modular APIs)

```python
# events/api.py
from ninja import Router
router = Router()

@router.get("/")
def list_events(request):
    return Event.objects.all()

# main api.py
api.add_router("/events/", events_router, tags=["events"])
api.add_router("/users/", users_router, tags=["users"])
```

## Authentication

```python
from ninja.security import HttpBearer, django_auth

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        if token == "supersecret":
            return token

@api.get("/protected", auth=AuthBearer())
def protected(request):
    return {"token": request.auth}

@api.get("/me", auth=django_auth)
def me(request):
    return {"username": request.user.username}

# API-level auth
api = NinjaAPI(auth=AuthBearer())
```

## Quick Reference

| Decorator | Usage |
|-----------|-------|
| `@api.get/post/put/patch/delete` | HTTP methods |
| `response=Schema` | Response validation |
| `response={200: A, 404: B}` | Multiple responses |
| `tags=["name"]` | OpenAPI grouping |
| `auth=AuthClass()` | Authentication |

## Advanced Topics

- **Computed fields, resolvers, aliases**: [references/schemas.md](references/schemas.md)
- **Error handling & exceptions**: [references/errors.md](references/errors.md)
- **Pagination & filtering**: [references/pagination.md](references/pagination.md)
