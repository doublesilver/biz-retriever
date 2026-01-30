from typing import Any, Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """
    Standard Error Response Schema
    """

    code: str
    message: str
    details: Optional[Any] = None
