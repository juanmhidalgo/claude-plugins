# Pagination & Filtering Reference

## Table of Contents
- [Built-in Pagination](#built-in-pagination)
- [Custom Pagination](#custom-pagination)
- [Filtering](#filtering)
- [Ordering](#ordering)

## Built-in Pagination

```python
from ninja.pagination import paginate, LimitOffsetPagination, PageNumberPagination

# LimitOffset: ?limit=10&offset=20
@api.get("/items", response=list[ItemSchema])
@paginate(LimitOffsetPagination)
def list_items(request):
    return Item.objects.all()

# PageNumber: ?page=2
@api.get("/items", response=list[ItemSchema])
@paginate(PageNumberPagination)
def list_items(request):
    return Item.objects.all()
```

### Response Format

```json
{
  "items": [...],
  "count": 100
}
```

## Custom Pagination

```python
from ninja.pagination import PaginationBase
from ninja import Schema

class CustomPagination(PaginationBase):
    class Input(Schema):
        page: int = 1
        per_page: int = 10

    class Output(Schema):
        items: list
        total: int
        page: int
        pages: int

    def paginate_queryset(self, queryset, pagination: Input, **params):
        total = queryset.count()
        offset = (pagination.page - 1) * pagination.per_page
        
        return {
            "items": queryset[offset : offset + pagination.per_page],
            "total": total,
            "page": pagination.page,
            "pages": (total + pagination.per_page - 1) // pagination.per_page,
        }

@api.get("/items", response=list[ItemSchema])
@paginate(CustomPagination)
def list_items(request):
    return Item.objects.all()
```

### API-level Default

```python
from ninja.pagination import LimitOffsetPagination

api = NinjaAPI()
api.default_pagination = LimitOffsetPagination

@api.get("/items", response=list[ItemSchema])
@paginate  # Uses default
def list_items(request):
    return Item.objects.all()
```

## Filtering

### Query Parameters

```python
from typing import Optional

@api.get("/items", response=list[ItemSchema])
def list_items(
    request,
    category: str = None,
    min_price: float = None,
    max_price: float = None,
    in_stock: bool = None,
):
    qs = Item.objects.all()
    
    if category:
        qs = qs.filter(category=category)
    if min_price is not None:
        qs = qs.filter(price__gte=min_price)
    if max_price is not None:
        qs = qs.filter(price__lte=max_price)
    if in_stock is not None:
        qs = qs.filter(quantity__gt=0) if in_stock else qs.filter(quantity=0)
    
    return qs
```

### Filter Schema

```python
from ninja import FilterSchema, Field
from typing import Optional

class ItemFilter(FilterSchema):
    category: Optional[str] = None
    min_price: Optional[float] = Field(None, q='price__gte')
    max_price: Optional[float] = Field(None, q='price__lte')
    search: Optional[str] = Field(None, q='name__icontains')

@api.get("/items", response=list[ItemSchema])
def list_items(request, filters: ItemFilter = Query(...)):
    qs = Item.objects.all()
    return filters.filter(qs)
```

### Custom Filter Logic

```python
class ItemFilter(FilterSchema):
    search: Optional[str] = None
    
    def filter_search(self, value):
        # Custom Q object
        from django.db.models import Q
        return Q(name__icontains=value) | Q(description__icontains=value)
```

## Ordering

```python
from typing import Literal

@api.get("/items", response=list[ItemSchema])
def list_items(
    request,
    order_by: Literal['name', '-name', 'price', '-price', 'created'] = '-created',
):
    return Item.objects.order_by(order_by)

# Multiple ordering
@api.get("/items", response=list[ItemSchema])
def list_items(request, order_by: list[str] = Query(['-created'])):
    # Validate allowed fields
    allowed = {'name', '-name', 'price', '-price', 'created', '-created'}
    order_fields = [f for f in order_by if f in allowed]
    return Item.objects.order_by(*order_fields)
```

## Combined Example

```python
from ninja import Query
from ninja.pagination import paginate, LimitOffsetPagination

class ItemFilter(FilterSchema):
    category: str = None
    min_price: float = Field(None, q='price__gte')
    search: str = Field(None, q='name__icontains')

@api.get("/items", response=list[ItemSchema])
@paginate(LimitOffsetPagination)
def list_items(
    request,
    filters: ItemFilter = Query(...),
    order_by: str = '-created',
):
    qs = Item.objects.all()
    qs = filters.filter(qs)
    return qs.order_by(order_by)
```
