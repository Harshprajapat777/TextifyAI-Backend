from fastapi import APIRouter
from pydantic import BaseModel

from app.services.nlp_service import nlp_service


router = APIRouter(tags=["Spell Check"])


class SpellCheckRequest(BaseModel):
    text: str


class Correction(BaseModel):
    word: str
    correction: str
    offset: int
    length: int


class SpellCheckResponse(BaseModel):
    corrections: list[Correction]


@router.post("/spellcheck", response_model=SpellCheckResponse)
async def spellcheck(body: SpellCheckRequest):
    corrections = nlp_service.check_text(body.text)
    return SpellCheckResponse(corrections=corrections)
