"""Support chatbot.

The bot is grounded: it answers from knowledge entries an admin writes, and
is told plainly to say it does not know rather than invent. For a support
widget that is the right trade — a confident wrong answer about whether a
certificate costs money is worse than no answer.

Anyone can use it, signed in or not, so the public endpoint is rate limited
per client and never echoes anything but the reply.
"""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_admin
from app.core.config import settings
from app.crud import chatbot as crud
from app.db.mongodb import get_db
from app.schemas.chatbot import (
    ChatRequest,
    ChatResponse,
    ChatbotSettings,
    ChatbotSettingsUpdate,
    ConversationResponse,
    KnowledgeEntryCreate,
    KnowledgeEntryResponse,
    KnowledgeEntryUpdate,
)
from app.services.llm import AllProvidersFailed, build_chain, complete, extract_json

logger = logging.getLogger("uvicorn.error")
router = APIRouter()

# A visitor is allowed this many messages per window. Generous for a person
# typing, restrictive for a script burning the account's model credits.
RATE_LIMIT = 20
RATE_WINDOW_SECONDS = 300
_recent: Dict[str, Deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    # Behind Render's proxy the real address is in X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(request: Request) -> None:
    key = _client_key(request)
    now = time.monotonic()
    bucket = _recent[key]
    while bucket and now - bucket[0] > RATE_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="That's a lot of questions at once. Give it a minute and try again.",
        )
    bucket.append(now)
    # Keep the table from growing without bound on a long-lived process.
    if len(_recent) > 5000:
        for stale_key in [k for k, v in _recent.items() if not v][:1000]:
            _recent.pop(stale_key, None)


SYSTEM_TEMPLATE = """{persona}

You are the Turnpike Analyst website support assistant — warm, concise and genuinely
helpful, the way a great support agent is. You help visitors understand Turnpike
Analyst: its services, industries served, training & internship programme, and blog.

You answer ONLY from the reference material below, which is drawn live from the
Turnpike Analyst website and the team's notes.

Rules, in order of importance:
1. If the reference answers the question, answer from it in two to four sentences.
   You may mention the page path shown in the reference (e.g. /services/...).
2. If the reference does NOT cover it, say you are not certain and offer to connect
   them to the team on WhatsApp or the contact page. Never invent prices, dates,
   eligibility, policy, URLs, emails, phone numbers or names.
3. If the question is off-topic or nonsense — not about Turnpike Analyst or what it
   offers — gently steer back: say what you can help with (services, training,
   internship) and ask what they would like to know. Do not answer unrelated trivia.
4. Always propose up to three short, relevant follow-up questions the visitor is
   likely to ask next, grounded in the reference material.
5. Plain, friendly language. No sales fluff.

Respond as STRICT JSON only, with no text outside it:
{{"reply": "<your answer>", "suggestions": ["<follow-up 1>", "<follow-up 2>", "<follow-up 3>"]}}

Reference material:
{knowledge}"""

NO_KNOWLEDGE = "(nothing on the website matched this question)"


# Stop-words kept out of the keyword query so "what are your services" still
# retrieves on "services" rather than matching every page that says "your".
_STOPWORDS = {
    "the", "and", "for", "are", "you", "your", "what", "how", "can", "does", "with",
    "about", "this", "that", "from", "have", "has", "will", "should", "would", "when",
    "where", "which", "who", "why", "tell", "want", "need", "please", "here", "there",
    "turnpike", "analyst", "website", "site",
}


def _keywords(text: str) -> List[str]:
    tokens = re.findall(r"[A-Za-z0-9]{3,}", (text or "").lower())
    seen: List[str] = []
    for t in tokens:
        if t not in _STOPWORDS and t not in seen:
            seen.append(t)
    return seen[:8]


def _trim(value: Any, length: int = 220) -> str:
    s = str(value or "").strip().replace("\n", " ")
    return s[: length - 1] + "…" if len(s) > length else s


async def _site_knowledge(db: AsyncIOMotorDatabase, query: str, per_source: int = 3) -> List[str]:
    """Retrieve snippets from the live site content so the bot can research the
    whole website, not just hand-written FAQ entries. A keyword regex over the
    existing content collections — no extra index or paid service."""
    kws = _keywords(query)
    if not kws:
        return []
    regex = "|".join(re.escape(k) for k in kws)
    snippets: List[str] = []

    async def pull(collection: str, fields: List[str], render) -> None:
        clause = {"$or": [{f: {"$regex": regex, "$options": "i"}} for f in fields]}
        async for doc in db[collection].find(clause).limit(per_source):
            snippets.append(render(doc))

    await pull(
        "services",
        ["title", "short_description", "full_description"],
        lambda d: f"Service — {d.get('title')}: {_trim(d.get('short_description') or d.get('full_description'))} (page: /services/{d.get('slug')})",
    )
    await pull(
        "industries",
        ["title", "short_description", "full_description"],
        lambda d: f"Industry — {d.get('title')}: {_trim(d.get('short_description') or d.get('full_description'))} (page: /industries/{d.get('slug')})",
    )
    await pull(
        "courses_and_training",
        ["title", "short_description", "description", "summary"],
        lambda d: f"Training — {d.get('title')}: {_trim(d.get('short_description') or d.get('description') or d.get('summary'))} (page: /training)",
    )
    await pull(
        "blogs_and_articles",
        ["title", "summary"],
        lambda d: f"Blog — {d.get('title')}: {_trim(d.get('summary'))} (page: /blog/{d.get('slug')})",
    )
    await pull(
        "faqs",
        ["question", "answer"],
        lambda d: f"FAQ — Q: {_trim(d.get('question'), 160)} A: {_trim(d.get('answer'))}",
    )
    return snippets[:12]


@router.get("/settings", response_model=ChatbotSettings)
async def public_settings(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Greeting and enabled flag, so the widget can render before any chat."""
    chatbot = await crud.get_settings(db)
    # The persona and fallback wording are operator configuration, not
    # something a visitor needs; only what the widget renders is returned.
    return ChatbotSettings(
        enabled=chatbot.enabled,
        greeting=chatbot.greeting,
        persona="",
        fallback_message="",
        updated_at=chatbot.updated_at,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    _check_rate_limit(request)

    chatbot = await crud.get_settings(db)
    if not chatbot.enabled:
        raise HTTPException(status_code=503, detail="The assistant is currently switched off.")

    # Research the whole site: hand-written FAQ entries first, then live
    # content pulled from the website's own collections.
    entries = await crud.search_knowledge(db, payload.message)
    site_snippets = await _site_knowledge(db, payload.message)

    knowledge_parts = [f"Q: {entry['question']}\nA: {entry['answer']}" for entry in entries]
    knowledge_parts.extend(site_snippets)
    needs_human = not knowledge_parts

    knowledge = "\n\n".join(knowledge_parts) or NO_KNOWLEDGE
    system = SYSTEM_TEMPLATE.format(persona=chatbot.persona, knowledge=knowledge)

    # Only the last few turns: enough for "and what about X?" to make sense,
    # short enough that a long session does not grow the prompt without end.
    history = "\n".join(
        f"{turn.role}: {turn.content}" for turn in payload.history[-6:]
    )
    user = f"{history}\nuser: {payload.message}" if history else payload.message

    chain = build_chain(settings.chatbot_provider_chain, model_override=settings.CHATBOT_MODEL)
    suggestions: List[str] = []
    try:
        raw, answered_by = await complete(
            chain, system=system, user=user, max_tokens=800, json_schema={"type": "object"}
        )
        try:
            parsed = extract_json(raw)
            reply = str(parsed.get("reply") or "").strip() or raw.strip()
            suggestions = [
                str(s).strip() for s in (parsed.get("suggestions") or []) if str(s).strip()
            ][:3]
        except Exception:
            # Model ignored the JSON instruction — use its text as the reply.
            reply = raw.strip()
    except AllProvidersFailed as exc:
        logger.error("Chatbot providers all failed: %s", exc)
        # The visitor gets the configured fallback, not a stack trace.
        reply, answered_by, needs_human = chatbot.fallback_message, "fallback", True

    conversation_id = await crud.append_turn(
        db,
        payload.conversation_id,
        user_message=payload.message,
        reply=reply,
        needs_human=needs_human,
        user_id=None,
    )

    return ChatResponse(
        reply=reply.strip(),
        conversation_id=conversation_id,
        answered_by=answered_by,
        sources=[entry["question"] for entry in entries],
        suggestions=suggestions,
        needs_human=needs_human,
    )


# --------------------------------------------------------------------------
# Admin
# --------------------------------------------------------------------------

@router.get("/admin/settings", response_model=ChatbotSettings)
async def admin_settings(
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    return await crud.get_settings(db)


@router.patch("/admin/settings", response_model=ChatbotSettings)
async def admin_update_settings(
    payload: ChatbotSettingsUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    return await crud.update_settings(db, payload.model_dump(exclude_unset=True))


@router.get("/admin/knowledge", response_model=List[KnowledgeEntryResponse])
async def admin_list_knowledge(
    topic: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    return await crud.list_knowledge(db, topic=topic)


@router.post(
    "/admin/knowledge",
    response_model=KnowledgeEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_create_knowledge(
    payload: KnowledgeEntryCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    return await crud.create_knowledge(db, payload)


@router.put("/admin/knowledge/{entry_id}", response_model=KnowledgeEntryResponse)
async def admin_update_knowledge(
    entry_id: str,
    payload: KnowledgeEntryUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    entry = await crud.update_knowledge(db, entry_id, payload)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.delete("/admin/knowledge/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_knowledge(
    entry_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    if not await crud.delete_knowledge(db, entry_id):
        raise HTTPException(status_code=404, detail="Entry not found")


@router.get("/admin/conversations", response_model=List[ConversationResponse])
async def admin_conversations(
    unanswered_only: bool = Query(False),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: Dict[str, Any] = Depends(get_current_admin),
):
    """What people actually asked.

    Filtering to the unanswered ones gives the knowledge base its backlog:
    every conversation here is a question the bot could not ground.
    """
    return await crud.list_conversations(db, needs_human=True if unanswered_only else None)
