---
name: django-ninja
description: Build APIs with Django using type hints.
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

## Basic Setup

```python
# api.py
from ninja import NinjaAPI

api = NinjaAPI()

@api.get("/hello")
def hello(request, name: str = "world"):
    return {"message": f"Hello {name}"}

# urls.py
from django.urls import path
from .api import api

urlpatterns = [
    path("api/", api.urls),
]
```

## Path and Query Parameters

```python
# Query params: /items?skip=0&limit=10
@api.get("/items")
def list_items(request, skip: int = 0, limit: int = 10):
    return items[skip : skip + limit]

# Path params: /items/123
@api.get("/items/{item_id}")
def get_item(request, item_id: int):
    return get_object_or_404(Item, id=item_id)

# Combined: /users/42/items?category=books
@api.get("/users/{user_id}/items")
def user_items(request, user_id: int, category: str = None):
    qs = Item.objects.filter(user_id=user_id)
    if category:
        qs = qs.filter(category=category)
    return qs
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
    item = Item.objects.create(**payload.dict())
    return item

@api.get("/items", response=list[ItemOut])
def list_items(request):
    return Item.objects.all()
```

## ModelSchema (from Django models)

```python
from ninja import ModelSchema
from .models import User

class UserSchema(ModelSchema):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        # or: exclude = ['password']
        # or: fields = '__all__'  # Not recommended

class UserCreateSchema(ModelSchema):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
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

# 204 No Content
@api.delete("/items/{id}", response={204: None})
def delete_item(request, id: int):
    Item.objects.filter(id=id).delete()
    return 204, None
```

## File Upload

```python
from ninja import File, UploadedFile

@api.post("/upload")
def upload(request, file: UploadedFile = File(...)):
    data = file.read()
    return {"name": file.name, "size": len(data)}

# Multiple files
@api.post("/upload-many")
def upload_many(request, files: list[UploadedFile] = File(...)):
    return [{"name": f.name} for f in files]
```

## Form Data

```python
from ninja import Form

@api.post("/login")
def login(request, username: Form[str], password: Form[str]):
    # ...
    return {"token": "..."}
```

## Routers (modular APIs)

```python
# events/api.py
from ninja import Router

router = Router()

@router.get("/")
def list_events(request):
    return Event.objects.all()

@router.get("/{event_id}")
def get_event(request, event_id: int):
    return get_object_or_404(Event, id=event_id)

# main api.py
from ninja import NinjaAPI
from events.api import router as events_router
from users.api import router as users_router

api = NinjaAPI()
api.add_router("/events/", events_router, tags=["events"])
api.add_router("/users/", users_router, tags=["users"])
```

## Authentication

```python
from ninja.security import HttpBearer, APIKeyHeader, django_auth

# Token auth
class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        if token == "supersecret":
            return token  # or return user object

@api.get("/protected", auth=AuthBearer())
def protected(request):
    return {"token": request.auth}

# Django session auth
@api.get("/me", auth=django_auth)
def me(request):
    return {"username": request.user.username}

# API-level auth (all endpoints)
api = NinjaAPI(auth=AuthBearer())

# Router-level auth
api.add_router("/admin/", admin_router, auth=django_auth)
```

## Async Support

```python
@api.get("/async")
async def async_operation(request):
    await asyncio.sleep(1)
    return {"status": "done"}
```

## Advanced Topics

- **Custom validators & resolvers**: See [references/schemas.md](references/schemas.md)
- **Error handling & exceptions**: See [references/errors.md](references/errors.md)
- **Pagination & filtering**: See [references/pagination.md](references/pagination.md)

## Quick Reference

| Decorator | Usage |
|-----------|-------|
| `@api.get` | GET request |
| `@api.post` | POST request |
| `@api.put` | PUT request |
| `@api.patch` | PATCH request |
| `@api.delete` | DELETE request |
| `response=Schema` | Response validation |
| `response={200: A, 404: B}` | Multiple responses |
| `tags=["name"]` | OpenAPI grouping |
| `auth=AuthClass()` | Authentication |
