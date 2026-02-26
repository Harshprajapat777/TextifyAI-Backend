from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.llm_service import get_predictions, ROLE_SYSTEM_PROMPTS


router = APIRouter(tags=["Predictions"])

VALID_ROLES = list(ROLE_SYSTEM_PROMPTS.keys())


class PredictRequest(BaseModel):
    text: str
    role: str = "student"
    count: int = Field(default=5, ge=1, le=10)


class PredictResponse(BaseModel):
    predictions: list[str]


@router.post("/predict", response_model=PredictResponse)
async def predict(body: PredictRequest):
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{body.role}'. Must be one of: {VALID_ROLES}",
        )

    predictions = await get_predictions(body.text, body.role, body.count)
    return PredictResponse(predictions=predictions)
