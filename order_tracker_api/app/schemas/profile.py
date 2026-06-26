from typing import Optional

from pydantic import BaseModel


class ProfileResponse(BaseModel):
    id: int
    username: str
    full_name: str
    email: Optional[str] = None
    party_code: str
