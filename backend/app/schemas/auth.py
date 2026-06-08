import uuid
from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    email_verified: bool
    has_workspace: bool


class PasswordResetRequestBody(BaseModel):
    email: EmailStr


class PasswordResetConfirmBody(BaseModel):
    token: str = Field(max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class ChangePasswordBody(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class VerifyEmailBody(BaseModel):
    token: str = Field(max_length=128)


class ResendVerificationBody(BaseModel):
    pass
