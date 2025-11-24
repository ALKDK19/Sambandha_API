# ...existing code...
from pydantic import BaseModel
from datetime import datetime

class RecommendationInDB(BaseModel):
    id: int
    user_id: int
    recommended_user_id: int
    status: str
    created_at: datetime
    class Config:
        orm_mode = True
# ...existing code...

