from typing import Optional
from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    name: str
    max_attempts: int = 3


class JoinRequest(BaseModel):
    session_code: str
    student_name: str


class DraftRequest(BaseModel):
    draft_text: str


class FinalizeRequest(BaseModel):
    attempt_number: int
