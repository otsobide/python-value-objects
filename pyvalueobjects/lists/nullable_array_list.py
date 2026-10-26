from __future__ import annotations

from pyvalueobjects.abstract.nullablevalueobject import build_nullable
from pyvalueobjects.errors.ValueObjectError import ValueObjectError
from pyvalueobjects.lists.array_list import ArrayList

_nullable_array_list_classes = {}


def NullableArrayList(cls):
    """
    Dynamically creates a nullable value object class for a list of values of a specific type.
    This function returns a class that validates and encapsulates a list of values, allowing the list to be None.
    Generated classes are cached per element type, so NullableArrayList(cls) always returns the same class for the
    same cls and its instances can be compared with isinstance() and type().

    :param cls: The class type for the elements in the list.
    :return: A class _NullableArrayList that inherits from a nullable version of ArrayList and validates a list of values of type cls.
    """
    if cls in _nullable_array_list_classes:
        return _nullable_array_list_classes[cls]

    _nullable_cls = build_nullable(ArrayList(cls))
    class _NullableArrayList(_nullable_cls):
        """
        A nullable value object representing a list of values of a specific type. Inherits from a nullable version of ArrayList and validates that the input is a list of the specified type or None.
        """

        def __init__(self, values: list[cls] | None):
            """
            Initialize the _NullableArrayList object with the given list of values or None.
            :param values: A list of values of type cls, or None.
            """
            super().__init__(values)

        def _validate(self, value):
            """
            Validate that the given value is a list.
            :param value: The value to validate.
            :raises: ValueObjectError if the value is not a list.
            """
            super()._validate(value)
            input_type = type(value)
            if input_type != list:
                raise ValueObjectError(f'Input type should be: list.')

    _nullable_array_list_classes[cls] = _NullableArrayList
    return _NullableArrayList
