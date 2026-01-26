"""
Custom exception classes for better error handling
"""


class BizRetrieverException(Exception):
    """Base exception for all application errors"""
    pass


class InsufficientDataError(BizRetrieverException):
    """Raised when ML training data is insufficient"""
    
    def __init__(self, required: int, actual: int):
        self.required = required
        self.actual = actual
        super().__init__(
            f"Insufficient training data: required {required}, got {actual}"
        )


class CrawlerError(BizRetrieverException):
    """Raised when crawler fails"""
    
    def __init__(self, source: str, message: str):
        self.source = source
        super().__init__(f"Crawler error from {source}: {message}")


class APIKeyError(BizRetrieverException):
    """Raised when API key is invalid or missing"""
    
    def __init__(self, key_name: str):
        self.key_name = key_name
        super().__init__(f"Invalid or missing API key: {key_name}")


class ModelNotTrainedError(BizRetrieverException):
    """Raised when trying to predict without trained model"""
    
    def __init__(self):
        super().__init__(
            "ML model not trained. Please train the model first."
        )


class FileProcessingError(BizRetrieverException):
    """Raised when file processing fails"""

    def __init__(self, filename: str, reason: str):
        self.filename = filename
        super().__init__(f"Failed to process file '{filename}': {reason}")


class WeakPasswordError(BizRetrieverException):
    """Raised when password does not meet security requirements"""

    def __init__(self, reason: str = "Password does not meet security requirements"):
        self.reason = reason
        super().__init__(reason)


class ValidationError(BizRetrieverException):
    """Raised when input validation fails"""

    def __init__(self, field: str, reason: str):
        self.field = field
        self.reason = reason
        super().__init__(f"Validation error for '{field}': {reason}")


class DatabaseError(BizRetrieverException):
    """Raised when database operation fails"""

    def __init__(self, operation: str, reason: str):
        self.operation = operation
        super().__init__(f"Database error during {operation}: {reason}")


class ExternalAPIError(BizRetrieverException):
    """Raised when external API call fails"""

    def __init__(self, api_name: str, status_code: int = None, message: str = None):
        self.api_name = api_name
        self.status_code = status_code
        error_msg = f"External API error from {api_name}"
        if status_code:
            error_msg += f" (status: {status_code})"
        if message:
            error_msg += f": {message}"
        super().__init__(error_msg)
