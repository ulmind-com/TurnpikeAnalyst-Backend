"""Seed the support chatbot's knowledge base.

These are the questions people actually ask about a free internship
programme, answered from the programme as built. Safe to re-run: entries
are matched on their question text and updated rather than duplicated.

An admin can edit every one of these in the console; this is a starting
set, not a fixed script.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

ENTRIES = [
    {
        "topic": "internship",
        "question": "Does the internship cost anything?",
        "answer": "No. The programme is free and there is no charge at any stage — not to enrol, not to submit, and not to receive the certificate.",
        "keywords": ["fee", "price", "cost", "payment", "charge", "free", "paid"],
    },
    {
        "topic": "internship",
        "question": "How long is the internship?",
        "answer": "You choose one, two or three months when you enrol. The certificate states the duration you picked, so choose the one that matches the scope of what you intend to build.",
        "keywords": ["duration", "months", "how long", "time", "deadline", "1 month", "3 months"],
    },
    {
        "topic": "internship",
        "question": "Can I build my own project instead of one of yours?",
        "answer": "Yes. You can take one of our published briefs, or propose your own project in any technology you like. Use the 'I have my own project idea' option on the internship page. The review and the certificate are the same either way.",
        "keywords": ["own project", "my project", "choose", "technology", "propose", "idea"],
    },
    {
        "topic": "internship",
        "question": "What do I have to submit?",
        "answer": "Eight things: the project in a public GitHub repository, its purpose, the technologies you used, the architecture, a data flow diagram, the use cases, the benefit of using it, and a recording of you running the project locally.",
        "keywords": ["submit", "deliverables", "requirements", "what do i need", "documents"],
    },
    {
        "topic": "internship",
        "question": "Why do I need to record myself running the project?",
        "answer": "It is how we know the project genuinely works and is genuinely yours. An unlisted YouTube, Loom or Drive link is fine — show the project starting up and doing what it is meant to do.",
        "keywords": ["video", "recording", "demo", "run locally", "screen recording", "loom"],
    },
    {
        "topic": "internship",
        "question": "Does my repository have to be public?",
        "answer": "Yes. The review reads your code, structure and commit history directly from GitHub, so a private repository cannot be assessed. Make it public before you submit.",
        "keywords": ["private repo", "public", "github", "repository", "visibility"],
    },
    {
        "topic": "internship",
        "question": "What are the follow-up questions?",
        "answer": "After you submit, your repository is read and questions are generated from your specific project — your architecture, your choices, your code. No two interns get the same questions. Answer them in your own words; a short honest answer beats a long vague one.",
        "keywords": ["questions", "follow up", "interview", "quiz", "after submit"],
    },
    {
        "topic": "certificates",
        "question": "How long until I get the certificate?",
        "answer": "Once you have answered the follow-up questions, a reviewer reads your submission, watches your demo and makes a decision. You will see the expected decision date on your dashboard — typically about a week.",
        "keywords": ["certificate", "how long", "when", "wait", "review time", "decision"],
    },
    {
        "topic": "certificates",
        "question": "Is the certificate verifiable?",
        "answer": "Yes. Every certificate carries a number in the form TA-YEAR-XXXXXXXXXX, and anyone can check it at /verify/<number> on our site without signing in. It shows the recipient, the project and the issue date.",
        "keywords": ["verify", "verification", "authentic", "real", "check certificate", "number"],
    },
    {
        "topic": "certificates",
        "question": "Who issues the certificate?",
        "answer": "Turnpike Analyst, a company registered in the USA and India. Certificates are issued only after a human reviewer has approved the submission — nothing is generated automatically.",
        "keywords": ["who issues", "company", "registered", "iso", "authority", "valid"],
    },
    {
        "topic": "internship",
        "question": "Can I work on more than one project at a time?",
        "answer": "No. The programme runs one project at a time so each submission gets a proper review. Finish or close your current project before starting another.",
        "keywords": ["multiple", "two projects", "parallel", "another project", "second"],
    },
    {
        "topic": "internship",
        "question": "What happens if I miss the deadline?",
        "answer": "The attempt expires and you can start a different project whenever you are ready. Nothing is lost permanently and there is no penalty.",
        "keywords": ["deadline", "miss", "late", "expired", "overdue", "too late"],
    },
    {
        "topic": "internship",
        "question": "How do I sign up?",
        "answer": "Sign in with Google on the internship page. Your profile is created automatically — there is no separate registration form and no payment step.",
        "keywords": ["sign up", "register", "login", "google", "account", "join"],
    },
    {
        "topic": "services",
        "question": "What does Turnpike Analyst do?",
        "answer": "We run enterprise content management, intelligent automation and AI programmes for organisations in regulated industries — ECM migration, document capture, workflow automation and related consulting.",
        "keywords": ["what do you do", "services", "company", "about", "business", "ecm"],
    },
    {
        "topic": "internship",
        "question": "My submission says the review failed. What does that mean?",
        "answer": "It means our automated read could not run — an outage or a rate limit on our side, not a problem with your work. Your submission is saved and a reviewer will pick it up directly. You do not need to do anything.",
        "keywords": ["review failed", "error", "problem", "stuck", "not working", "failed"],
    },
]


async def seed() -> None:
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    created = updated = 0

    for entry in ENTRIES:
        now = datetime.now(timezone.utc)
        existing = await db.chatbot_knowledge.find_one({"question": entry["question"]})
        if existing:
            await db.chatbot_knowledge.update_one(
                {"_id": existing["_id"]},
                {"$set": {**entry, "is_published": True, "updated_at": now}},
            )
            updated += 1
        else:
            await db.chatbot_knowledge.insert_one(
                {**entry, "is_published": True, "created_at": now, "updated_at": now}
            )
            created += 1

    total = await db.chatbot_knowledge.count_documents({})
    print(f"Created {created}, updated {updated}. Knowledge entries in database: {total}")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
