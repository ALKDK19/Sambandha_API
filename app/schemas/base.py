from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class BaseSchema(BaseModel):
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class MessageResponse(BaseModel):
    message: str
