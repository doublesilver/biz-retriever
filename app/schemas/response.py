from pydantic import BaseModel
from typing import Optional, Any

class ErrorResponse(BaseModel):
    """
    Standard Error Response Schema
    """
    code: str
    message: str
    details: Optional[Any] = None
