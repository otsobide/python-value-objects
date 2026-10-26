from __future__ import annotations

from typing import TypeVar

from pyvalueobjects.abstract.valueobject import ValueObject
from pyvalueobjects.errors.ValueObjectError import ValueObjectError

T = TypeVar('T')

_array_list_classes = {}


def ArrayList(cls):
    """
    Dynamically creates a value object class for a list of values of a specific type.
    This function returns a class that validates and encapsulates a list of values, ensuring each value is of the specified type.
    Generated classes are cached per element type, so ArrayList(cls) always returns the same class for the same cls
    and its instances can be compared with isinstance() and type().

    :param cls: The class type for the elements in the list.
    :return: A class _ArrayList that inherits from ValueObject and validates a list of values of type cls.
    """
    if cls in _array_list_classes:
        return _array_list_classes[cls]

    class _ArrayList(ValueObject):
        """
        A value object representing a list of values of a specific type. Inherits from ValueObject and validates that the input is a list of the specified type.
        """

        def __init__(self, values: list[cls]):
            """
            Initialize the _ArrayList object with the given list of values.
            :param values: A list of values of type cls.
            """
            super().__init__(values)
            self._sub_value_objects = [cls(value) for value in values]

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

    _array_list_classes[cls] = _ArrayList
    return _ArrayList
