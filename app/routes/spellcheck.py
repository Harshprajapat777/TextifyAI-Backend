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
    auto_corrected_text: str


def _apply_corrections(text: str, corrections: list[dict]) -> str:
    """Apply all corrections to the text, working in reverse order to preserve offsets."""
    result = text
    for c in sorted(corrections, key=lambda x: x["offset"], reverse=True):
        result = result[: c["offset"]] + c["correction"] + result[c["offset"] + c["length"] :]
    return result


@router.post("/spellcheck", response_model=SpellCheckResponse)
async def spellcheck(body: SpellCheckRequest):
    corrections = nlp_service.check_text(body.text)
    auto_corrected_text = _apply_corrections(body.text, corrections)
    return SpellCheckResponse(corrections=corrections, auto_corrected_text=auto_corrected_text)
