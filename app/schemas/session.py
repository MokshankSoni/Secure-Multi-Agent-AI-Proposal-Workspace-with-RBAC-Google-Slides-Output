"""Session schemas."""

from pydantic import BaseModel

class CreateSessionRequest(BaseModel):
    pass

class CreateSessionResponse(BaseModel):
    pass

class SessionResponse(BaseModel):
    pass

class GenerateResponse(BaseModel):
    pass
