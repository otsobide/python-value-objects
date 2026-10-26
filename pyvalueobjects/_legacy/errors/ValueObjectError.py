class ValueObjectError(Exception):
    """
    Custom exception raised when a value object validation fails or when an invalid operation is performed on a value object.
    """

    def __init__(self, message: str):
        """
        Initialize the ValueObjectError with a specific error message.
        :param message: A string describing the error that occurred.
        """
        self.message = message
