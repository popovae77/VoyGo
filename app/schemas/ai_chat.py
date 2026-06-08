from typing import Literal

from pydantic import BaseModel, Field


class AiChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class AiChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[AiChatMessage] = Field(default_factory=list, max_length=20)
    trip_context: str | None = None


class AiChatResponse(BaseModel):
    reply: str
