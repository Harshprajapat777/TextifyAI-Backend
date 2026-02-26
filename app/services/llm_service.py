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
        "You are a legal writing assistant. You help draft contracts, briefs, "
        "legal memos, and formal correspondence. Use precise legal terminology."
    ),
    "doctor": (
        "You are a medical writing assistant. You help with clinical notes, "
        "patient summaries, and medical documentation. Use accurate medical terms."
    ),
    "engineer": (
        "You are a technical writing assistant. You help with documentation, "
        "technical reports, and specifications. Be clear and precise."
    ),
    "faculty": (
        "You are an academic writing assistant. You help with research papers, "
        "syllabi, grant proposals, and academic correspondence."
    ),
    "writer": (
        "You are a creative writing assistant. You help with stories, essays, "
        "prose, and narrative content. Focus on style and flow."
    ),
    "student": (
        "You are a study assistant. You help with essays, assignments, "
        "research papers, and study notes. Keep language clear and structured."
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
