import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.llm_service import (
    get_chat_reply,
    stream_chat_reply,
    ROLE_SYSTEM_PROMPTS,
)


router = APIRouter(tags=["Chat"])

VALID_ROLES = list(ROLE_SYSTEM_PROMPTS.keys())


class Message(BaseModel):
    sender: str  # "user" or "assistant"
    text: str


class ChatRequest(BaseModel):
    role: str = "student"
    messages: list[Message]


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{body.role}'. Must be one of: {VALID_ROLES}",
        )

    reply = await get_chat_reply(body.role, [m.model_dump() for m in body.messages])
    return ChatResponse(reply=reply)


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest):
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{body.role}'. Must be one of: {VALID_ROLES}",
        )

    async def event_generator():
        async for token in stream_chat_reply(
            body.role, [m.model_dump() for m in body.messages]
        ):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
