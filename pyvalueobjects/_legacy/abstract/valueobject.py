from abc import ABC

from pyvalueobjects._legacy.errors.ValueObjectError import ValueObjectError


class ValueObject(ABC):
    """
    Abstract base class for all value objects. Ensures that values are validated and encapsulated.
    """

    def __init__(self, value):
        """
        Initialize the value object with the given value and validate it.
        :param value: The value to be stored and validated.
        """
        self._validate(value)
        self._value = value

    def value(self):
        """
        Return the raw value stored in this value object.
        :return: The stored value.
        """
        return self._value

    def str_value(self) -> str:
        """
        Return the string representation of the stored value.
        :return: A string representation of the value.
        """
        return str(self._value)

    def _validate(self, value):
        """
        Validate the given value. This method should be overridden by subclasses to enforce specific constraints.
        :param value: The value to validate.
        """
        pass

    def __hash__(self):
        """
        Return a hash of the stored value, allowing the object to be used in hash-based collections.
        :return: The hash of the value.
        """
        return hash(self._value)

    def __eq__(self, other):
        """
        Compare this value object with another. Raises a ValueObjectError if the other object is not a ValueObject.
        :param other: The other value object to compare with.
        :return: True if the values are equal, False otherwise.
        :raises: ValueObjectError if the other object is not a ValueObject.
        """
        if not isinstance(other, ValueObject):
            raise ValueObjectError('Comparing with a non value object.')
        return self._value == other.value()


