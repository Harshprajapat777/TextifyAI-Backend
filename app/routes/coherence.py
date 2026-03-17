import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.llm_service import _get_client, ROLE_SYSTEM_PROMPTS
from app.config import settings

router = APIRouter(tags=["Coherence"])

VALID_ROLES = list(ROLE_SYSTEM_PROMPTS.keys())
COHERENCE_LEVELS = ("low", "medium", "high")


class CoherenceRequest(BaseModel):
    sentence_a: str
    sentence_b: str
    role: str = "student"


class CoherenceResponse(BaseModel):
    coherence: str   # "low" | "medium" | "high"
    score: int       # 0–100
    reason: str      # one-line explanation
    suggestion: str  # how to improve sentence_b (empty string if high)


@router.post("/coherence", response_model=CoherenceResponse)
async def detect_coherence(body: CoherenceRequest):
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{body.role}'. Must be one of: {VALID_ROLES}",
        )

    if not body.sentence_a.strip() or not body.sentence_b.strip():
        raise HTTPException(
            status_code=400,
            detail="Both sentence_a and sentence_b are required and cannot be empty.",
        )

    role_context = ROLE_SYSTEM_PROMPTS[body.role]

    prompt = (
        f"{role_context}\n\n"
        "You are a coherence analysis expert. Analyze how logically and contextually "
        "sentence B follows from sentence A.\n\n"
        f'Sentence A: "{body.sentence_a}"\n'
        f'Sentence B: "{body.sentence_b}"\n\n'
        "Respond ONLY with valid json in this exact format:\n"
        '{"coherence": "<low|medium|high>", "score": <0-100>, '
        '"reason": "<one concise sentence explaining the coherence level>", '
        '"suggestion": "<one concise sentence on how to improve B, or empty string if coherence is high>"}'
    )

    client = _get_client()
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=200,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()
    try:
        result = json.loads(raw)
        coherence = result.get("coherence", "").lower()
        if coherence not in COHERENCE_LEVELS:
            coherence = "medium"

        return CoherenceResponse(
            coherence=coherence,
            score=int(result.get("score", 50)),
            reason=result.get("reason", ""),
            suggestion=result.get("suggestion", ""),
        )
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=500, detail="Failed to parse coherence result.")
