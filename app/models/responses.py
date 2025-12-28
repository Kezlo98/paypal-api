"""Response models for type safety."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Error response model for consistent error formatting."""

    error: str
    message: str
