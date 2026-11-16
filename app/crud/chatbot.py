"""Persistence for the support chatbot."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.chatbot import (
    ChatbotSettings,
    KnowledgeEntryCreate,
    KnowledgeEntryUpdate,
)

SETTINGS_ID = "chatbot"

# Below this, a text hit is coincidence rather than relevance. Tuned against
# the seeded entries: a real question match scores well above 1.0.
MIN_TEXT_SCORE = 1.0


async def ensure_chatbot_indexes(db: AsyncIOMotorDatabase) -> None:
    # A text index is what lets the bot find relevant entries by wording
    # rather than by exact match. Weighted so a question beats a keyword
    # match, and a keyword match beats a hit buried in a long answer.
    await db.chatbot_knowledge.create_index(
        [("question", "text"), ("keywords", "text"), ("answer", "text")],
        weights={"question": 10, "keywords": 6, "answer": 2},
        name="knowledge_text",
    )
    await db.chatbot_knowledge.create_index("topic")
    await db.chatbot_conversations.create_index("last_message_at")
    await db.chatbot_conversations.create_index("needs_human")


def _public(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {**doc, "_id": str(doc["_id"])}


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------

async def get_settings(db: AsyncIOMotorDatabase) -> ChatbotSettings:
    doc = await db.chatbot_settings.find_one({"_id": SETTINGS_ID})
    if not doc:
        return ChatbotSettings()
    doc.pop("_id", None)
    return ChatbotSettings(**doc)


async def update_settings(db: AsyncIOMotorDatabase, changes: Dict[str, Any]) -> ChatbotSettings:
    changes = {k: v for k, v in changes.items() if v is not None}
    changes["updated_at"] = datetime.now(timezone.utc)
    await db.chatbot_settings.update_one({"_id": SETTINGS_ID}, {"$set": changes}, upsert=True)
    return await get_settings(db)


# --------------------------------------------------------------------------
# Knowledge base
# --------------------------------------------------------------------------

async def list_knowledge(
    db: AsyncIOMotorDatabase, *, published_only: bool = False, topic: Optional[str] = None
) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {}
    if published_only:
        query["is_published"] = True
    if topic:
        query["topic"] = topic
    cursor = db.chatbot_knowledge.find(query).sort("topic", 1)
    return [_public(doc) async for doc in cursor]


async def search_knowledge(
    db: AsyncIOMotorDatabase, query: str, limit: int = 6
) -> List[Dict[str, Any]]:
    """Find the entries most likely to answer a question.

    Mongo's text search first. If it finds nothing — which happens for very
    short questions and for words the index stems differently — fall back
    to a case-insensitive regex over the question field, so a visitor
    asking "certificate?" still gets the certificate entries.
    """
    cursor = (
        db.chatbot_knowledge.find(
            {"$text": {"$search": query}, "is_published": True},
            {"score": {"$meta": "textScore"}},
        )
        .sort([("score", {"$meta": "textScore"})])
        .limit(limit)
    )
    # A weak text score means one common word happened to line up, not that
    # the entry answers the question. Letting those through would mark
    # genuinely unanswered questions as answered and empty the admin's
    # backlog of the very questions worth adding.
    hits = [doc for doc in [_public(d) async for d in cursor] if doc.get("score", 0) >= MIN_TEXT_SCORE]
    if hits:
        return hits

    words = [w for w in re.findall(r"[a-zA-Z]{4,}", query)][:5]
    if not words:
        return []
    pattern = "|".join(re.escape(word) for word in words)
    cursor = db.chatbot_knowledge.find(
        {
            "is_published": True,
            "$or": [
                {"question": {"$regex": pattern, "$options": "i"}},
                {"keywords": {"$regex": pattern, "$options": "i"}},
            ],
        }
    ).limit(limit)
    return [_public(doc) async for doc in cursor]


async def create_knowledge(
    db: AsyncIOMotorDatabase, data: KnowledgeEntryCreate
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    doc = {**data.model_dump(), "created_at": now, "updated_at": now}
    result = await db.chatbot_knowledge.insert_one(doc)
    return {**doc, "_id": str(result.inserted_id)}


async def update_knowledge(
    db: AsyncIOMotorDatabase, entry_id: str, data: KnowledgeEntryUpdate
) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(entry_id):
        return None
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        doc = await db.chatbot_knowledge.find_one({"_id": ObjectId(entry_id)})
        return _public(doc) if doc else None
    changes["updated_at"] = datetime.now(timezone.utc)
    doc = await db.chatbot_knowledge.find_one_and_update(
        {"_id": ObjectId(entry_id)}, {"$set": changes}, return_document=True
    )
    return _public(doc) if doc else None


async def delete_knowledge(db: AsyncIOMotorDatabase, entry_id: str) -> bool:
    if not ObjectId.is_valid(entry_id):
        return False
    result = await db.chatbot_knowledge.delete_one({"_id": ObjectId(entry_id)})
    return result.deleted_count == 1


# --------------------------------------------------------------------------
# Conversations
# --------------------------------------------------------------------------

async def append_turn(
    db: AsyncIOMotorDatabase,
    conversation_id: Optional[str],
    *,
    user_message: str,
    reply: str,
    needs_human: bool,
    user_id: Optional[str],
) -> str:
    """Record a question and its answer.

    Conversations are stored so an admin can see what people actually ask —
    the unanswered ones are the backlog for the knowledge base.
    """
    now = datetime.now(timezone.utc)
    turns = [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": reply},
    ]

    if conversation_id and ObjectId.is_valid(conversation_id):
        updated = await db.chatbot_conversations.find_one_and_update(
            {"_id": ObjectId(conversation_id)},
            {
                "$push": {"turns": {"$each": turns}},
                "$set": {"last_message_at": now, "needs_human": needs_human},
                "$inc": {"message_count": 1},
            },
            return_document=True,
        )
        if updated:
            return str(updated["_id"])

    result = await db.chatbot_conversations.insert_one(
        {
            "started_at": now,
            "last_message_at": now,
            "message_count": 1,
            "needs_human": needs_human,
            "user_id": user_id,
            "turns": turns,
        }
    )
    return str(result.inserted_id)


async def list_conversations(
    db: AsyncIOMotorDatabase, *, needs_human: Optional[bool] = None, limit: int = 100
) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {}
    if needs_human is not None:
        query["needs_human"] = needs_human
    cursor = db.chatbot_conversations.find(query).sort("last_message_at", -1).limit(limit)
    return [_public(doc) async for doc in cursor]
