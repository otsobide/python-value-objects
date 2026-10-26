def build_nullable(cls):
    """
    Dynamically creates a nullable version of the given value object class.
    This allows the value to be either the specified type or None.

    :param cls: The class to create a nullable version of (typically a subclass of ValueObject).
    :return: A new class Nullable that wraps the input class, allowing None as a valid value.
    """
    class Nullable(cls):

        def __init__(self, value):
            if value is None:
                self._value = None
            else:
                super().__init__(value)

    return Nullable
