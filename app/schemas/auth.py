"""Authentication schemas."""

from pydantic import BaseModel

class SignupRequest(BaseModel):
    pass

class SignupResponse(BaseModel):
    pass

class LoginRequest(BaseModel):
    pass

class LoginResponse(BaseModel):
    pass
