from uuid import UUID

from pydantic import BaseModel, Field


class UserSchema(BaseModel):
    """
    Schema for user details including contact information and authentication.
    """

    user_id: UUID = Field(..., description="Unique identifier for the user")
    email: str = Field(..., description="Email address of the user")
    fullname: str = Field(..., min_length=1, max_length=100, description="Full name of the user")
    phone: str = Field(..., description="Phone number in international format (e.g., +1234567890)")
    token: str = Field(..., min_length=20, description="Authentication token for the user")
    type: int = Field(..., ge=0, description="Type of the user (e.g., admin = 0, regular user = 1)")
