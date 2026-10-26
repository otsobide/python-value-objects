<h1 align="center">💊 Python Value Objects</h1>

<div align="center">

![](https://img.shields.io/badge/PRs-welcome-green.svg)
[![GitHub](https://img.shields.io/github/license/n1nj4t4nuk1/python-value-objects)](https://github.com/n1nj4t4nuk1/python-value-objects/blob/main/LICENSE)
[![Pypi](https://img.shields.io/pypi/v/pyvalueobjects)](https://pypi.org/project/pyvalueobjects/)
[![Downloads](https://pepy.tech/badge/pyvalueobjects)](https://pepy.tech/project/pyvalueobjects)
[![GA](https://github.com/n1nj4t4nuk1/python-value-objects/workflows/Tests/badge.svg)](https://github.com/n1nj4t4nuk1/python-value-objects/actions/workflows/test.yml)
 
</div>
&nbsp;

A collection of Value Objects to save time by generalizing types and format validations.

* [Value-objects](#value-objects)
  * [Numeric value-objects](#numeric-value-objects)
    * [Int](#int)
    * [Nullable Int](#nullable-int)
    * [Positive Int](#positive-int)
    * [Nullable Positive Int](#positive-int)
    * [Positive or zero Int](#positive-or-zero-int)
    * [Nullable Positive or zero Int](#nullable-positive-or-zero-int)
    * [Negative Int](#negative-int)
    * [Nullable Negative Int](#nullable-negative-int)
    * [Negative or zero Int](#negative-or-zero-int)
    * [Nullable Negative or zero Int](#nullable-negative-or-zero-int)
    * [Float](#float)
    * [Positive Float](#positive-float)
    * [Negative Float](#negative-float)
  * [String value-objects](#string-value-objects)
    * [String](#string)
    * [Nullable String](#nullable-string)
    * [Uuid4](#uuid4)
    * [Nullable Uuid4](#nullable-uuid4)
  * [Date value-objects](#date-value-objects)
    * [ISO Date](#iso-date)
  * [Data Structures value-objects](#data-structures-value-objects)
    * [ArrayList](#arraylist)
    * [NullableArrayList](#nullable-arraylist)
  * [Security value-objects](#security-value-objects)
    * [CVE](#cve)
    * [Nullable CVE](#nullable-cve)
    * [CPE](#cpe)
    * [Nullable CPE](#nullable-cpe)

# Value-objects

## Numeric value-objects

### Int

A basic integer value object that ensures the value is a valid integer without decimal points. It provides type safety and validation for integer values.

```python
from pyvalueobjects import Int

# Creation
my_integer = Int(9)

# Getting raw value
my_integer.value() # returns -> 9
```

### Nullable Int

An integer value object that can also be None, useful for optional numeric fields. It provides the same validation as Int but allows for null values.

```python
from pyvalueobjects import NullableInt

# Creation
my_integer = NullableInt(9)

# Creating from None
my_nullable_integer = NullableInt(None)

# Getting raw value
my_integer.value() # returns -> 9
my_nullable_integer.value() # returns -> None
```

### Positive Int

An integer value object that ensures the value is strictly greater than zero. Useful for representing quantities, counts, or any value that must be positive.

```python
from pyvalueobjects import PositiveInt

# Creation
my_integer = PositiveInt(9)

# Getting raw value
my_integer.value() # returns -> 9
```

### Nullable Positive Int

A positive integer value object that can also be None. Combines the validation of PositiveInt with the flexibility of nullable values.

```python
from pyvalueobjects import NullablePositiveInt

# Creation
my_integer = NullablePositiveInt(9)

# Creating from None
my_nullable_integer = NullablePositiveInt(None)

# Getting raw value
my_integer.value() # returns -> 9
my_nullable_integer.value() # returns -> None
```

### Positive Or Zero Int

An integer value object that ensures the value is greater than or equal to zero. Useful for representing non-negative quantities or counts.

```python
from pyvalueobjects import PositiveOrZeroInt

# Creation
my_integer = PositiveOrZeroInt(9)

# Getting raw value
my_integer.value() # returns -> 9
```

### Nullable Positive Or Zero Int

A non-negative integer value object that can also be None. Combines the validation of PositiveOrZeroInt with the flexibility of nullable values.

```python
from pyvalueobjects import NullablePositiveOrZeroInt

# Creation
my_integer = NullablePositiveOrZeroInt(9)

# Creating from None
my_nullable_integer = NullablePositiveOrZeroInt(None)

# Getting raw value
my_integer.value() # returns -> 9
my_nullable_integer.value() # returns -> None
```

### Negative Int

An integer value object that ensures the value is strictly less than zero. Useful for representing negative quantities or values.

```python
from pyvalueobjects import NegativeInt

# Creation
my_integer = NegativeInt(-9)

# Getting raw value
my_integer.value() # returns -> -9
```

### Nullable Negative Int

A negative integer value object that can also be None. Combines the validation of NegativeInt with the flexibility of nullable values.

```python
from pyvalueobjects import NullableNegativeInt

# Creation
my_integer = NullableNegativeInt(-9)

# Creating from None
my_nullable_integer = NullableNegativeInt(None)

# Getting raw value
my_integer.value() # returns -> -9
my_nullable_integer.value() # returns -> None
```

### Negative Or Zero Int

An integer value object that ensures the value is less than or equal to zero. Useful for representing non-positive quantities or values.

```python
from pyvalueobjects import NegativeOrZeroInt

# Creation
my_integer = NegativeOrZeroInt(-9)

# Getting raw value
my_integer.value() # returns -> -9
```

### Nullable Negative Or Zero Int

A non-positive integer value object that can also be None. Combines the validation of NegativeOrZeroInt with the flexibility of nullable values.

```python
from pyvalueobjects import NullableNegativeOrZeroInt

# Creation
my_integer = NullableNegativeOrZeroInt(-9)

# Creating from None
my_nullable_integer = NullableNegativeOrZeroInt(None)

# Getting raw value
my_integer.value() # returns -> -9
my_nullable_integer.value() # returns -> None
```

### Float

A basic float value object that ensures the value is a finite float. NaN and infinite values are rejected.

```python
from pyvalueobjects import Float

# Creation
my_float = Float(9.5)

# Creating from int or str
my_float_from_int = Float.from_int(9)
my_float_from_str = Float.from_str('9.5')

# Getting raw value
my_float.value() # returns -> 9.5
my_float_from_int.value() # returns -> 9.0
```

### Positive Float

A float value object that ensures the value is strictly greater than zero. Useful for representing amounts, measures, or any decimal value that must be positive.

```python
from pyvalueobjects import PositiveFloat

# Creation
my_float = PositiveFloat(9.5)

# Getting raw value
my_float.value() # returns -> 9.5

# Creation
my_float2 = PositiveFloat(0.0) # raises error
```

### Negative Float

A float value object that ensures the value is strictly less than zero. Useful for representing debts, losses, or any decimal value that must be negative.

```python
from pyvalueobjects import NegativeFloat

# Creation
my_float = NegativeFloat(-9.5)

# Getting raw value
my_float.value() # returns -> -9.5

# Creation
my_float2 = NegativeFloat(0.0) # raises error
```

## String value-objects

### String

A basic string value object that ensures the value is a valid string. Provides type safety and validation for string values.

```python
from pyvalueobjects import String

# Creation
my_str = String('potato')

# Getting raw value
my_str.value() # returns -> 'potato'
```

### Nullable String

A string value object that can also be None. Useful for optional string fields.

```python
from pyvalueobjects import NullableString

# Creation
my_str = NullableString('potato')

# Getting raw value
my_str.value() # returns -> 'potato'

# Creation
my_nullable_str = NullableString(None)

# Getting raw value
my_nullable_str.value() # returns -> None
```

### Non Empty String

A string value object that ensures the value is not an empty string. Useful for required string fields that must contain content.

```python
from pyvalueobjects import NonEmptyString

# Creation
my_str = NonEmptyString('potato')

# Getting raw value
my_str.value() # returns -> 'potato'

# Creation
my_str2 = NonEmptyString('') # raises error
```

### Nullable non Empty String

A non-empty string value object that can also be None. Combines the validation of NonEmptyString with the flexibility of nullable values.

```python
from pyvalueobjects import NullableNonEmptyString

# Creation
my_str = NullableNonEmptyString('potato')

# Getting raw value
my_str.value() # returns -> 'potato'

# Creation
my_str2 = NullableNonEmptyString(None)

# Getting raw value
my_str2.value() # returns -> None

# Creation
my_str3 = NullableNonEmptyString('') # raises error
```

### Uuid4

A string value object that ensures the value is a valid UUID v4 format. Useful for representing unique identifiers.

```python
from pyvalueobjects import Uuid4

# Creation
my_uuid4 = Uuid4('6c7add12-bf35-459e-a6c5-3178a2a33011')

# Getting raw value
my_uuid4.value()  # returns -> '6c7add12-bf35-459e-a6c5-3178a2a33011'
```

### Nullable Uuid4

A UUID v4 value object that can also be None. Combines the validation of Uuid4 with the flexibility of nullable values.

```python
from pyvalueobjects import NullableUuid4

# Creation
my_uuid4 = NullableUuid4('6c7add12-bf35-459e-a6c5-3178a2a33011')
my_null_uuid4 = NullableUuid4(None)

# Getting raw value
my_uuid4.value()  # returns -> '6c7add12-bf35-459e-a6c5-3178a2a33011'
my_null_uuid4.value()  # returns -> 'None'
```

## Date value-objects

### ISO Date

A string value object that ensures the value is a valid ISO 8601 date format. Useful for representing dates and timestamps in a standardized format.

```python
from pyvalueobjects import IsoDate

# Creation
my_date = IsoDate('2023-08-15T04:55:12.076Z')

# Getting raw value
my_date.value()  # returns -> '2023-08-15T04:55:12.076Z'
```

## Data structures value-objects

### ArrayList

A value object that ensures all elements in a list are of a specific type. Provides type safety and validation for list contents.

```python
from pyvalueobjects import ArrayList
from pyvalueobjects import Int

# Creation
my_int_array = ArrayList(Int)([39])

# Getting raw value
my_int_array.value()  # returns -> [39]
```

### Nullable ArrayList

A list value object that can also be None, with type validation for its elements. Combines the validation of ArrayList with the flexibility of nullable values.

```python
from pyvalueobjects import NullableArrayList
from pyvalueobjects import Int

# Creation
my_int_array = NullableArrayList(Int)([39])
my_null_array = NullableArrayList(Int)(None)

# Getting raw value
my_int_array.value()  # returns -> [39]
my_null_array.value()  # returns -> None
```

## Security value-objects

### CVE

A string value object that ensures the value is a valid Common Vulnerabilities and Exposures (CVE) identifier format. Useful for representing security vulnerability identifiers.

```python
from pyvalueobjects import Cve

# Creation
my_cve = Cve('CVE-2014-9418')

# Getting raw value
my_cve.value()  # returns -> 'CVE-2014-9418'
```

### Nullable CVE

A CVE value object that can also be None. Combines the validation of CVE with the flexibility of nullable values.

```python
from pyvalueobjects import NullableCve

# Creation
my_cve = NullableCve('CVE-2014-9418')
my_null_cve = NullableCve(None)

# Getting raw value
my_cve.value()  # returns -> 'CVE-2014-9418'
my_null_cve.value()  # returns -> None
```

### CPE

A string value object that ensures the value is a valid Common Platform Enumeration (CPE) format. Useful for representing platform and software identifiers.

```python
from pyvalueobjects import Cpe

# Creation
my_cpe = Cpe('cpe:/a:openjdk:openjdk:8u282')

# Getting raw value
my_cpe.value()  # returns -> 'cpe:/a:openjdk:openjdk:8u282'
```

### Nullable CPE

A CPE value object that can also be None. Combines the validation of CPE with the flexibility of nullable values.

```python
from pyvalueobjects import NullableCpe

# Creation
my_cpe = NullableCpe('cpe:/a:openjdk:openjdk:8u282')
my_null_cpe = NullableCpe(None)

# Getting raw value
my_cpe.value()  # returns -> 'cpe:/a:openjdk:openjdk:8u282'
my_null_cpe.value()  # returns -> None
```


## Contributing

Contributions are welcome! Feel free to submit a Pull Request. But **Make sure you are not contributing to a mirror repository.** Check the following [Repository Status](#-repository-status) section to identify the primary repository.

### 🔄 Repository Status

This project **may be a *mirror*** of another primary repository. Below is a list of all related repositories, indicating whether they are mirrors and their approximate sync frequency:

| Service  | Repository URL                                              | Type      | Sync Frequency        |
|----------|-------------------------------------------------------------|-----------|-----------------------|
| Codeberg | `https://codeberg.org/n1nj4t4nuk1/python-value-objects`     | Primary   | N/A                   |
| Github   | `https://github.com/n1nj4t4nuk1/python-value-objects`       | Mirror    | Every commit          |

> ⚠️ Note: If you are viewing this repository on a platform like GitHub, GitLab, Gitea, Forgejo, etc., be aware that it **might not be the main repository**.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.