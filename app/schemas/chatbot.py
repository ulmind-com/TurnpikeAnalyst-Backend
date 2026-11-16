"""Support chatbot: knowledge entries, conversations and messages.

The bot answers from a knowledge base an admin curates, not from whatever
the model happens to believe about Turnpike Analyst. That is what makes it
trainable: adding an entry changes the answers, with no deploy and no
prompt engineering by the person doing it.
"""

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import Field

from app.schemas.common import BaseSchema


class KnowledgeEntryBase(BaseSchema):
    question: str = Field(..., min_length=5, max_length=400)
    answer: str = Field(..., min_length=5, max_length=4000)
    # Free-form grouping, e.g. "internship", "certificates", "services".
    topic: str = Field(default="general", max_length=60)
    # Extra phrasings people use for the same question. These are matched
    # against, so they widen recall without duplicating the answer.
    keywords: List[str] = Field(default_factory=list)
    is_published: bool = True


class KnowledgeEntryCreate(KnowledgeEntryBase):
    pass


class KnowledgeEntryUpdate(BaseSchema):
    question: Optional[str] = None
    answer: Optional[str] = None
    topic: Optional[str] = None
    keywords: Optional[List[str]] = None
    is_published: Optional[bool] = None


class KnowledgeEntryResponse(KnowledgeEntryBase):
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime


class ChatTurn(BaseSchema):
    role: str = Field(..., description="user | assistant")
    content: str = Field(..., max_length=4000)


class ChatRequest(BaseSchema):
    message: str = Field(..., min_length=1, max_length=2000)
    # The last few turns, sent by the client. The server does not hold a
    # session for anonymous visitors.
    history: List[ChatTurn] = Field(default_factory=list, max_length=20)
    conversation_id: Optional[str] = None


class ChatResponse(BaseSchema):
    reply: str
    conversation_id: str
    # Which provider answered, so a slow or odd reply can be traced.
    answered_by: str
    # Knowledge entries used, so an admin can see what the bot drew on.
    sources: List[str] = Field(default_factory=list)
    # Up to 3 follow-up questions the visitor is likely to ask next, shown as
    # clickable chips — like a support agent anticipating the next question.
    suggestions: List[str] = Field(default_factory=list)
    # True when nothing in the knowledge base matched and a human should
    # probably follow up.
    needs_human: bool = False


class ConversationResponse(BaseSchema):
    id: str = Field(alias="_id")
    started_at: datetime
    last_message_at: datetime
    message_count: int
    needs_human: bool
    user_id: Optional[str] = None
    turns: List[ChatTurn] = Field(default_factory=list)


class ChatbotSettings(BaseSchema):
    """Admin-editable behaviour, so tone and scope change without a deploy."""

    enabled: bool = True
    greeting: str = Field(
        default="Hi — ask me anything about the internship programme, our services or your submission.",
        max_length=500,
    )
    # Prepended to the system prompt. For voice and hard rules.
    persona: str = Field(
        default=(
            "You are the support assistant for Turnpike Analyst, an enterprise content "
            "and automation consultancy that also runs a free internship programme."
        ),
        max_length=2000,
    )
    # Shown when the knowledge base has nothing relevant.
    fallback_message: str = Field(
        default="I don't have an answer for that one. Email hello@turnpikeanalyst.com and a person will pick it up.",
        max_length=500,
    )
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatbotSettingsUpdate(BaseSchema):
    enabled: Optional[bool] = None
    greeting: Optional[str] = None
    persona: Optional[str] = None
    fallback_message: Optional[str] = None
