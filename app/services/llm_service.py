import json

from openai import AsyncOpenAI

from app.config import settings

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client

ROLE_SYSTEM_PROMPTS = {
    "lawyer": (
        "You are a legal writing assistant. You ONLY answer questions related to "
        "law, legal documents, contracts, briefs, court proceedings, and legal advice. "
        "If the user asks about anything outside the legal domain (e.g. health, engineering, "
        "academics, creative writing), refuse strictly and say: "
        "'I am specialized in the Legal field only. Please go back and choose your field carefully.'"
    ),
    "doctor": (
        "You are a medical writing assistant. You ONLY answer questions related to "
        "medicine, health, clinical notes, diagnoses, patient care, and medical documentation. "
        "If the user asks about anything outside the medical domain (e.g. law, engineering, "
        "academics, creative writing), refuse strictly and say: "
        "'I am specialized in the Medical field only. Please go back and choose your field carefully.'"
    ),
    "engineer": (
        "You are a technical writing assistant. You ONLY answer questions related to "
        "engineering, technology, software, hardware, technical documentation, and specifications. "
        "If the user asks about anything outside the engineering/technical domain (e.g. law, health, "
        "creative writing), refuse strictly and say: "
        "'I am specialized in the Engineering field only. Please go back and choose your field carefully.'"
    ),
    "faculty": (
        "You are an academic writing assistant. You ONLY answer questions related to "
        "academia, research papers, syllabi, grant proposals, teaching, and scholarly work. "
        "If the user asks about anything outside the academic domain (e.g. law, health, creative writing), "
        "refuse strictly and say: "
        "'I am specialized in the Academic field only. Please go back and choose your field carefully.'"
    ),
    "writer": (
        "You are a creative writing assistant. You ONLY answer questions related to "
        "creative writing, storytelling, essays, prose, poetry, and narrative content. "
        "If the user asks about anything outside the creative writing domain (e.g. law, health, engineering), "
        "refuse strictly and say: "
        "'I am specialized in the Creative Writing field only. Please go back and choose your field carefully.'"
    ),
    "student": (
        "You are a student study assistant. You ONLY answer questions related to "
        "studying, assignments, essays, research papers, exam preparation, and academic learning. "
        "If the user asks about anything outside academics and student life (e.g. legal advice, medical diagnosis), "
        "refuse strictly and say: "
        "'I am specialized in the Student/Academic field only. Please go back and choose your field carefully.'"
    ),
}


async def get_predictions(text: str, role: str, count: int = 5) -> list[str]:
    """Generate next-sentence predictions using OpenAI."""
    system_prompt = ROLE_SYSTEM_PROMPTS.get(role, ROLE_SYSTEM_PROMPTS["student"])

    client = _get_client()
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": (
                f"{system_prompt}\n\n"
                f"The user is typing a sentence. Complete it in {count} different ways. "
                f"Return ONLY a JSON array of {count} strings, each being a full sentence "
                f"completion. No explanation, no markdown — just the JSON array."
            )},
            {"role": "user", "content": text},
        ],
        temperature=0.8,
        max_tokens=500,
    )

    raw = response.choices[0].message.content.strip()
    try:
        predictions = json.loads(raw)
        if isinstance(predictions, list):
            return [str(p) for p in predictions[:count]]
    except json.JSONDecodeError:
        pass

    # Fallback: split by newlines if JSON parsing fails
    lines = [line.strip().strip("-•").strip() for line in raw.split("\n") if line.strip()]
    return lines[:count]


def _build_chat_messages(role: str, messages: list[dict]) -> list[dict]:
    """Convert frontend messages to OpenAI format with role system prompt."""
    system_prompt = ROLE_SYSTEM_PROMPTS.get(role, ROLE_SYSTEM_PROMPTS["student"])
    openai_messages = [{"role": "system", "content": system_prompt}]

    for msg in messages:
        openai_role = "assistant" if msg["sender"] == "assistant" else "user"
        openai_messages.append({"role": openai_role, "content": msg["text"]})

    return openai_messages


async def get_chat_reply(role: str, messages: list[dict]) -> str:
    """Get a single chat reply from OpenAI."""
    client = _get_client()
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=_build_chat_messages(role, messages),
        temperature=0.7,
        max_tokens=1024,
    )
    return response.choices[0].message.content


async def stream_chat_reply(role: str, messages: list[dict]):
    """Yield chat tokens one by one from OpenAI streaming."""
    client = _get_client()
    stream = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=_build_chat_messages(role, messages),
        temperature=0.7,
        max_tokens=1024,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


async def get_structured_chat_reply(role: str, messages: list[dict]) -> dict:
    """
    Get a chat reply. For casual messages returns a simple reply; for
    informational queries returns a description + numbered points.

    Returns one of:
      {"type": "chat", "text": "..."}
      {"type": "structured", "description": "...", "points": ["...", ...]}
    """
    base_prompt = ROLE_SYSTEM_PROMPTS.get(role, ROLE_SYSTEM_PROMPTS["student"])
    structured_prompt = (
        f"{base_prompt}\n\n"
        "You must always respond with valid json. "
        "Decide the format based on the user's message:\n"
        "- Casual (greetings, thanks, small talk) → return json:\n"
        '  {"type": "chat", "text": "<your reply>"}\n'
        "- Informational question → return json:\n"
        '  {"type": "structured", "description": "<one sentence overview, max 20 words>", '
        '"points": ["<point 1, max 15 words>", "<point 2>", "<point 3>"]}\n'
        "Return 3 to 5 points for structured replies. No markdown, no extra keys."
    )

    chat_messages = [{"role": "system", "content": structured_prompt}]
    for msg in messages:
        openai_role = "assistant" if msg["sender"] == "assistant" else "user"
        chat_messages.append({"role": openai_role, "content": msg["text"]})

    client = _get_client()
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=chat_messages,
        temperature=0.7,
        max_tokens=512,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()
    try:
        result = json.loads(raw)
        if result.get("type") in ("chat", "structured"):
            return result
    except json.JSONDecodeError:
        pass

    # Fallback: treat as casual reply
    return {"type": "chat", "text": raw[:200]}
