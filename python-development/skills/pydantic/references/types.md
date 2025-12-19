# Types Reference

## Table of Contents
- [Built-in Constrained Types](#built-in-constrained-types)
- [Network Types](#network-types)
- [DateTime Types](#datetime-types)
- [File Types](#file-types)
- [Secret Types](#secret-types)
- [Extra Types](#extra-types)
- [Type Coercion](#type-coercion)

## Built-in Constrained Types

### String Types

```python
from pydantic import (
    BaseModel,
    constr,           # Constrained string
    StrictStr,        # No coercion
)

class Model(BaseModel):
    # Using constr
    name: constr(min_length=1, max_length=50)
    code: constr(pattern=r'^[A-Z]{3}$')
    
    # Strict (no coercion from other types)
    strict_name: StrictStr
```

### Numeric Types

```python
from pydantic import (
    BaseModel,
    conint,           # Constrained int
    confloat,         # Constrained float
    condecimal,       # Constrained Decimal
    PositiveInt,
    NegativeInt,
    PositiveFloat,
    NegativeFloat,
    NonNegativeInt,
    NonPositiveInt,
    StrictInt,
    StrictFloat,
)

class Model(BaseModel):
    count: conint(ge=0, le=100)
    price: confloat(gt=0, multiple_of=0.01)
    percentage: confloat(ge=0, le=100)
    
    positive: PositiveInt      # > 0
    non_negative: NonNegativeInt  # >= 0
    strict_int: StrictInt      # No coercion
```

### Collection Types

```python
from pydantic import conlist, conset, confrozenset

class Model(BaseModel):
    tags: conlist(str, min_length=1, max_length=10)
    unique_ids: conset(int, min_length=1)
```

## Network Types

```python
from pydantic import (
    BaseModel,
    EmailStr,
    NameEmail,
    AnyUrl,
    AnyHttpUrl,
    HttpUrl,
    FileUrl,
    PostgresDsn,
    RedisDsn,
    MongoDsn,
    KafkaDsn,
    IPvAnyAddress,
    IPvAnyInterface,
    IPvAnyNetwork,
)

class Config(BaseModel):
    email: EmailStr                    # user@example.com
    contact: NameEmail                 # "John Doe <john@example.com>"
    website: HttpUrl                   # https://example.com
    database: PostgresDsn              # postgresql://user:pass@host/db
    cache: RedisDsn                    # redis://localhost:6379
    ip: IPvAnyAddress                  # 192.168.1.1 or ::1
```

### URL Handling

```python
from pydantic import HttpUrl

class Model(BaseModel):
    url: HttpUrl

m = Model(url='https://example.com/path?query=1')
print(m.url.scheme)    # 'https'
print(m.url.host)      # 'example.com'
print(m.url.path)      # '/path'
```

## DateTime Types

```python
from datetime import datetime, date, time, timedelta
from pydantic import (
    BaseModel,
    PastDate,
    FutureDate,
    PastDatetime,
    FutureDatetime,
    AwareDatetime,
    NaiveDatetime,
)

class Event(BaseModel):
    # Standard types with coercion
    timestamp: datetime           # Accepts ISO strings, timestamps
    event_date: date              # Accepts ISO date strings
    event_time: time              # Accepts time strings
    duration: timedelta           # Accepts ISO duration, seconds
    
    # Constrained types
    birthday: PastDate            # Must be in the past
    deadline: FutureDate          # Must be in the future
    created_at: PastDatetime
    scheduled_for: FutureDatetime
    
    # Timezone constraints
    with_tz: AwareDatetime        # Must have timezone
    without_tz: NaiveDatetime     # Must not have timezone
```

### Date/Time Coercion

```python
# All of these work:
Event(
    timestamp='2024-01-15T10:30:00',       # ISO string
    timestamp=1705312200,                   # Unix timestamp
    timestamp='1705312200',                 # Timestamp as string
)
```

## File Types

```python
from pydantic import (
    BaseModel,
    FilePath,          # Must exist and be a file
    DirectoryPath,     # Must exist and be a directory
    NewPath,           # Must not exist
)
from pathlib import Path

class FileConfig(BaseModel):
    input_file: FilePath
    output_dir: DirectoryPath
    new_file: NewPath
```

## Secret Types

```python
from pydantic import BaseModel, SecretStr, SecretBytes

class Credentials(BaseModel):
    username: str
    password: SecretStr
    api_key: SecretBytes

creds = Credentials(
    username="admin",
    password="secret123",
    api_key=b"key123"
)

print(creds.password)                    # SecretStr('**********')
print(creds.password.get_secret_value()) # 'secret123'
print(creds.model_dump())                # password shown as '**********'
```

## Extra Types

Install with: `pip install pydantic-extra-types`

```python
from pydantic import BaseModel
from pydantic_extra_types.color import Color
from pydantic_extra_types.country import CountryAlpha2
from pydantic_extra_types.phone_numbers import PhoneNumber
from pydantic_extra_types.payment import PaymentCardNumber

class Profile(BaseModel):
    favorite_color: Color           # "red", "#ff0000", "rgb(255,0,0)"
    country: CountryAlpha2          # "US", "GB"
    phone: PhoneNumber              # "+1-555-555-5555"
    card_number: PaymentCardNumber  # Validates Luhn algorithm
```

### Color Type

```python
from pydantic_extra_types.color import Color

class Design(BaseModel):
    color: Color

d = Design(color='#ff5733')
print(d.color.as_hex())      # '#ff5733'
print(d.color.as_rgb())      # 'rgb(255, 87, 51)'
print(d.color.as_rgb_tuple())# (255, 87, 51)
```

## Type Coercion

### Coercion Table

| Target Type | Accepts (Lax Mode) |
|------------|-------------------|
| `int` | int, float (no decimals), str (numeric) |
| `float` | int, float, str (numeric) |
| `str` | str, bytes (UTF-8) |
| `bool` | bool, int (0/1), str ('true'/'false') |
| `bytes` | bytes, str, bytearray |
| `datetime` | datetime, str (ISO), int (timestamp) |
| `date` | date, datetime, str (ISO) |
| `list` | list, tuple, set, frozenset |
| `dict` | dict, Mapping |

### Strict Mode

```python
from pydantic import BaseModel, ConfigDict

class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True)
    
    value: int  # Only accepts int, not "123" or 123.0
```

## Unions and Optional

```python
from pydantic import BaseModel
from typing import Union, Optional

class Model(BaseModel):
    # Union types
    value: int | str                    # Python 3.10+
    value: Union[int, str]              # Any Python 3.x
    
    # Optional (None allowed)
    maybe: Optional[int]                # int | None
    maybe: int | None                   # Python 3.10+
    
    # With default
    optional_with_default: int | None = None
```

### Smart Union Mode

```python
from pydantic import BaseModel, ConfigDict

class Model(BaseModel):
    model_config = ConfigDict(smart_union=True)
    
    # Tries each type in order, picks first that validates without coercion
    value: int | str

Model(value=123)    # int
Model(value="abc")  # str
Model(value="123")  # str (not coerced to int in smart mode)
```

## Literal and Enums

```python
from typing import Literal
from enum import Enum
from pydantic import BaseModel

class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class Model(BaseModel):
    status: Status
    priority: Literal['low', 'medium', 'high']

m = Model(status='active', priority='high')
print(m.status)  # Status.ACTIVE
```

## Any and Arbitrary Types

```python
from typing import Any
from pydantic import BaseModel, ConfigDict

class Flexible(BaseModel):
    data: Any  # Accepts anything

class WithArbitrary(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    custom_obj: MyCustomClass  # Non-Pydantic class
```
