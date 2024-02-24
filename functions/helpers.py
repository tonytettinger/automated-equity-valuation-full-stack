class CustomException(Exception):
    def __init__(self, message, exception_variable):
        super().__init__(message)
        self.exception_variable = exception_variable
