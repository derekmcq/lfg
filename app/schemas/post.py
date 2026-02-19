from datetime import datetime
from typing import Optional
from pydantic import BaseModel

VALID_PLATFORMS = ["PC", "PlayStation", "Xbox", "Nintendo Switch", "Mobile", "Other"]


class PostCreate(BaseModel):
    game: str
    platform: str
    description: str
    max_players: int = 4
    scheduled_at: Optional[datetime] = None


class PostUpdate(BaseModel):
    game: str
    platform: str
    description: str
    max_players: int
    scheduled_at: Optional[datetime] = None
