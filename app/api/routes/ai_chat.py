from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.ai_chat import AiChatRequest, AiChatResponse
from app.services.ai_advisor import chat_with_ai

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/chat", response_model=AiChatResponse)
def ai_chat(
    payload: AiChatRequest,
    current_user: User = Depends(get_current_user),
) -> AiChatResponse:
    del current_user
    history = [{"role": m.role, "content": m.content} for m in payload.history]
    reply = chat_with_ai(payload.message, history, trip_context=payload.trip_context)
    return AiChatResponse(reply=reply)
