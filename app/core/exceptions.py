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
