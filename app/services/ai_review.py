"""Automated review of an intern's repository, source archive, and live site.

Two separate calls are made rather than one, on purpose:

1. **Review** — judge the repository, archive and live site to produce a
   structured report with claim checks and findings.
2. **Questions** — derive 5 to 7 project-specific follow-up questions from
   the actual code, files, architecture, and live deployment.
3. **Authenticity Assessment** — analyze submitted answers against typing
   telemetry and stylistic AI markers to flag AI-generated or copy-pasted text.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.schemas.internship import (
    AiReview,
    AnswerAuthenticityReport,
    ClaimCheck,
    FollowUpQuestion,
    QuestionAnswerAssessment,
    ReviewFinding,
)
from app.services.github_repo import RepoSnapshot
from app.services.live_site import LiveSiteSnapshot
from app.services.llm import (
    AllProvidersFailed,
    Provider,
    build_chain,
    complete,
    extract_json,
)
from app.services.source_archive import ArchiveSnapshot

logger = logging.getLogger("uvicorn.error")


class ReviewUnavailable(RuntimeError):
    """The review could not be produced. The attempt is parked for a human."""


# --------------------------------------------------------------------------
# Prompt construction
# --------------------------------------------------------------------------

def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "\n…[truncated]"


def _diagram_text(diagram: Optional[Dict[str, Any]], label: str) -> str:
    if not diagram:
        return f"{label}: (not supplied)"
    if diagram.get("kind") == "mermaid" and diagram.get("mermaid"):
        return f"{label} (Mermaid source):\n{_truncate(diagram['mermaid'], 6000)}"
    return (
        f"{label}: supplied as an image, which you cannot see. "
        "Judge it only from the written description above, and do not comment "
        "on the drawing itself."
    )


def _dossier_section(submission: Optional[Dict[str, Any]]) -> str:
    if not submission:
        return ""

    technologies = submission.get("technologies") or []
    use_cases = submission.get("use_cases") or []
    repos = submission.get("repositories") or []

    repos_str = ""
    if repos:
        repos_str = "\n### Repositories declared\n" + "\n".join(
            f"- [{r.get('role', 'repo').upper()}] {r.get('url')} ({r.get('label') or ''})"
            for r in repos
        )

    return f"""
## The intern's own account of the project
These are CLAIMS. Your job includes deciding whether the code actually supports them.
{repos_str}

### Purpose
{submission.get("purpose") or "(not supplied)"}

### Technologies the intern says they used
{chr(10).join(f"- {item}" for item in technologies) or "- (none listed)"}

### Architecture, in the intern's words
{submission.get("architecture_text") or "(not supplied)"}

{_diagram_text(submission.get("architecture_diagram"), "Architecture diagram")}

### Data flow, in the intern's words
{submission.get("data_flow_text") or "(not supplied)"}

{_diagram_text(submission.get("data_flow_diagram"), "Data flow diagram")}

### Use cases
{chr(10).join(f"- {item}" for item in use_cases) or "- (none listed)"}

### Claimed benefit
{submission.get("benefits") or "(not supplied)"}

### Notes to the reviewer
{submission.get("notes") or "(none)"}
"""


def _archive_section(archive: Optional[ArchiveSnapshot]) -> str:
    if archive is None:
        return (
            "\n## Uploaded source archive (.zip)\n"
            "The intern did not upload a source archive, or it could not be read."
        )
    manifests = "\n\n".join(
        f"--- {path} ---\n{_truncate(content, 4000)}"
        for path, content in archive.manifests.items()
    )
    sources = "\n\n".join(
        f"--- {path} ---\n{_truncate(content, 4000)}"
        for path, content in archive.source_samples.items()
    )
    return f"""
## Uploaded source archive (.zip)
Compare the zip archive against the GitHub repository/repositories. Genuine work
has high consistency between the uploaded zip and GitHub code.
Archive name: {archive.filename}
Files: {archive.entry_count}   Uncompressed: {archive.total_uncompressed} bytes
Top-level folders: {", ".join(archive.top_level) or "none"}
Tests present: {archive.has_tests}   README: {archive.has_readme}   Dockerfile: {archive.has_dockerfile}

### Archive file tree
{chr(10).join(archive.tree[:160]) or "(empty)"}

### Archive manifests
{manifests or "(none found)"}

### Archive sampled source files
{sources or "(none sampled)"}
"""


def _live_site_section(live_site: Optional[LiveSiteSnapshot]) -> str:
    if not live_site:
        return "\n## Live deployed site\n(No live deployment URL provided)"
    return f"""
## Live deployed site inspection
URL submitted: {live_site.url}
Final resolved URL: {live_site.final_url}
Reachable: {live_site.reachable} (HTTP {live_site.status_code or 'error'})
Page Title: {live_site.title or 'none'}
Meta Description: {live_site.meta_description or 'none'}
Detected Technologies / Hosting: {", ".join(live_site.detected_tech) or "none"}
Is Parked / Placeholder: {live_site.is_placeholder_or_parked}
Error (if any): {live_site.error or "none"}
Headings found: {", ".join(live_site.headings) or "none"}

### Page text excerpt
{_truncate(live_site.text_excerpt, 1000) or "(no visible text extracted)"}
"""


def _single_repo_section(snapshot: RepoSnapshot, role_label: str = "primary") -> str:
    manifests = "\n\n".join(
        f"--- {path} ---\n{_truncate(content, 4500)}"
        for path, content in snapshot.manifests.items()
    )
    sources = "\n\n".join(
        f"--- {path} ---\n{_truncate(content, 4500)}"
        for path, content in snapshot.source_samples.items()
    )
    return f"""
### Repository [{role_label.upper()}]: {snapshot.owner}/{snapshot.name}
URL: {snapshot.html_url} — {snapshot.description or "no description"}
Default branch: {snapshot.default_branch}
Languages: {json.dumps(snapshot.languages)}
Topics: {", ".join(snapshot.topics) or "none"}
Created: {snapshot.created_at}  Last push: {snapshot.pushed_at}
Fork of another repository: {snapshot.is_fork}
Commits: {snapshot.commit_count} across {snapshot.distinct_commit_days} distinct days
Contributors: {", ".join(snapshot.contributors) or "unknown"}
Tests: {snapshot.has_tests}   CI: {snapshot.has_ci}   Dockerfile: {snapshot.has_dockerfile}   README: {snapshot.has_readme}

#### Recent commit messages
{chr(10).join(f"- {message}" for message in snapshot.commit_messages[:25]) or "- (none)"}

#### File tree
{chr(10).join(snapshot.tree[:250])}

#### Manifests
{manifests or "(none found)"}

#### Sampled source files
{sources or "(none sampled)"}
"""


def _full_project_digest(
    snapshots: List[Tuple[RepoSnapshot, str]],
    brief: str,
    requirements: List[str],
    submission: Optional[Dict[str, Any]] = None,
    archive: Optional[ArchiveSnapshot] = None,
    live_site: Optional[LiveSiteSnapshot] = None,
) -> str:
    repos_digest = "\n".join(
        _single_repo_section(snap, role) for snap, role in snapshots
    )
    return f"""## Project brief the intern was given
{brief}

## Stated requirements
{chr(10).join(f"- {item}" for item in requirements) or "- (none recorded)"}

{_dossier_section(submission)}

## GitHub Repositories
{repos_digest}

{_archive_section(archive)}

{_live_site_section(live_site)}
"""


REVIEW_SYSTEM = """You review internship submissions for Turnpike Analyst, an enterprise content and automation consultancy.

You are given:
1. The project brief and stated requirements.
2. The intern's dossier (claimed purpose, technologies, architecture, diagrams, use cases).
3. The snapshot(s) of the GitHub repository/repositories (which may be a single monorepo or split across frontend, backend, admin, etc.).
4. The uploaded project .zip source archive.
5. The live deployed site inspection results (if provided).

Judge the work on what the code and facts actually show, not on claims.

Your most important job is the CLAIM CHECK:
- Produce one claim_checks row for EVERY technology the intern listed.
- Produce claim_checks rows for key architectural components they claimed.
- Produce a claim_check for "Live Deployment" if a live URL was submitted: does the live site match the repo and actually run?
- Produce a claim_check for "Source Archive Match": does the uploaded .zip archive match the GitHub repository?

Verdicts:
- "supported" — you can point at a file, dependency or live response that proves it.
- "partial" — present but trivial, stubbed, or far smaller than described.
- "unsupported" — you looked and found nothing backing it.
Always name the evidence ("found in app/api/...", "live URL title matches and shows React app", or "absence of any Postgres client").

Then weigh:
- Stated requirements fulfillment.
- Multi-repo or project structure coherence.
- Commit history realism.
- Code quality, typing, and error handling in sampled files.
- Consistency between GitHub repos, the .zip archive, and live URL.

Reply with JSON only, matching exactly:
{
  "score": <integer 0-100>,
  "verdict": "strong" | "acceptable" | "weak",
  "summary": "<2-4 sentences for the reviewing admin>",
  "strengths": ["<specific, referencing files, commits or architecture>"],
  "concerns": ["<specific>"],
  "detected_stack": ["<technology actually found>"],
  "claim_checks": [
    {"claim": "<what the intern claimed>", "verdict": "supported|partial|unsupported", "evidence": "<the file or fact that settles it>"}
  ],
  "findings": [
    {"area": "structure|workflow|quality|testing|docs|security", "severity": "info|minor|major", "detail": "<one sentence>"}
  ]
}"""


QUESTIONS_SYSTEM = """You write follow-up questions for an internship submission at Turnpike Analyst.

The intern submitted their project code (GitHub repos, .zip archive, and live site). Write between 5 and 7 deeply technical, project-specific questions that ONLY someone who actually built THIS project could answer well.

Rules:
- Generate between 5 and 7 questions (default 6).
- Never ask something answerable from the README alone.
- Never ask generic textbook questions ("what is REST?", "what is Vite?", "what did you learn?").
- Anchor every question to an EXACT named file, route, component, schema, or configuration from the provided code (e.g. "In `src/api/auth.ts` you handled refresh tokens by...", "In `app/models/order.py`...").
- Ask about trade-offs, edge-case handling, and reasoning.
- At least one question must quote the intern's OWN written architecture or data flow text.
- If multiple repositories or a live site are present, ask about the contract between them or deployment quirks.
- For each question, provide "expects": what a strong, genuine developer answer must demonstrate (for admin review).

Reply with JSON only, matching exactly:
{
  "questions": [
    {"question": "<the question, addressed to the intern>", "expects": "<what a strong answer demonstrates — for the admin's eyes only>"}
  ]
}"""


AUTHENTICITY_SYSTEM = """You are a technical reviewer and AI-detection evaluator for Turnpike Analyst.
You assess whether an intern's follow-up question answers were genuinely typed by the intern in their own words, or generated by an AI (ChatGPT/Claude/Gemini) or copy-pasted.

You are given:
- The questions and the intern's answers.
- Typing telemetry (time spent typing in seconds, keystrokes, paste attempts, and tab switch/blur count).
- The project context.

Evaluation criteria:
1. Telemetry flags:
   - High paste attempts (> 0) or 0 typing time with large text = severe copy-paste flag.
   - Keystroke count much lower than character count = clipboard insertion.
   - Extremely short duration (< 15 seconds) for a long response = pasted.
2. AI generation markers:
   - Overly diplomatic, robotic AI tone ("Certainly! Here is an explanation...", "In conclusion, it is important to note...").
   - Generic boilerplate bullet lists without mentioning concrete bugs or implementation quirks.
   - Generic non-committal answers that sound like a textbook.
3. Authentic human markers:
   - Personal developer voice ("I decided to...", "I hit an issue where...").
   - Mentioning specific struggles, bugs, or practical trade-offs from their repository.

Reply with JSON only, matching exactly:
{
  "overall_authenticity_score": <integer 0-100, 100 = completely genuine human, 0 = pure AI/pasted>,
  "ai_generated_likelihood": "low" | "medium" | "high",
  "summary": "<2-3 sentences summarizing the authenticity findings>",
  "flags": ["<specific warning flag if any>"],
  "per_question": [
    {
      "question_id": "<id>",
      "ai_likelihood": "low" | "medium" | "high",
      "reason": "<one sentence assessment>"
    }
  ]
}"""


# --------------------------------------------------------------------------
# Provider interface
# --------------------------------------------------------------------------

def _build_review(
    data: Dict[str, Any],
    snapshots: List[Tuple[RepoSnapshot, str]],
    model: str,
    archive: Optional[ArchiveSnapshot] = None,
    live_site: Optional[LiveSiteSnapshot] = None,
) -> AiReview:
    findings = [
        ReviewFinding(
            area=str(item.get("area", "quality")),
            severity=str(item.get("severity", "info")),
            detail=str(item.get("detail", "")).strip(),
        )
        for item in data.get("findings", [])
        if str(item.get("detail", "")).strip()
    ]

    try:
        score = max(0, min(100, int(data.get("score", 0))))
    except (TypeError, ValueError):
        score = 0

    claim_checks = [
        ClaimCheck(
            claim=str(item.get("claim", "")).strip(),
            verdict=str(item.get("verdict", "unsupported")),
            evidence=str(item.get("evidence", "")).strip() or "No evidence recorded.",
        )
        for item in data.get("claim_checks", [])
        if str(item.get("claim", "")).strip()
    ]

    primary_snapshot = snapshots[0][0] if snapshots else None
    repos_facts = [
        {**snap.as_facts(), "role": role} for snap, role in snapshots
    ]

    return AiReview(
        score=score,
        verdict=str(data.get("verdict", "weak")),
        summary=str(data.get("summary", "")).strip() or "No summary returned.",
        strengths=[str(item) for item in data.get("strengths", []) if str(item).strip()],
        concerns=[str(item) for item in data.get("concerns", []) if str(item).strip()],
        detected_stack=[
            str(item) for item in data.get("detected_stack", []) if str(item).strip()
        ],
        findings=findings,
        claim_checks=claim_checks,
        repo_facts=primary_snapshot.as_facts() if primary_snapshot else {},
        repos_facts=repos_facts,
        archive_facts=archive.as_facts() if archive else None,
        live_site_facts=live_site.as_facts() if live_site else None,
        model=model,
        reviewed_at=datetime.now(timezone.utc),
    )


def _build_questions(data: Dict[str, Any], count: int) -> List[FollowUpQuestion]:
    questions: List[FollowUpQuestion] = []
    target_count = max(5, min(7, count))
    for item in data.get("questions", [])[:target_count]:
        text = str(item.get("question", "")).strip()
        if not text:
            continue
        questions.append(
            FollowUpQuestion(
                id=uuid.uuid4().hex[:12],
                question=text,
                expects=str(item.get("expects", "")).strip() or None,
            )
        )
    if not questions:
        raise ReviewUnavailable("The review service returned no usable questions.")
    return questions


REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "verdict": {"type": "string", "enum": ["strong", "acceptable", "weak"]},
        "summary": {"type": "string"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "concerns": {"type": "array", "items": {"type": "string"}},
        "detected_stack": {"type": "array", "items": {"type": "string"}},
        "claim_checks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "verdict": {
                        "type": "string",
                        "enum": ["supported", "partial", "unsupported"],
                    },
                    "evidence": {"type": "string"},
                },
                "required": ["claim", "verdict", "evidence"],
            },
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "area": {"type": "string"},
                    "severity": {"type": "string", "enum": ["info", "minor", "major"]},
                    "detail": {"type": "string"},
                },
                "required": ["area", "severity", "detail"],
            },
        },
    },
    "required": [
        "score", "verdict", "summary", "strengths", "concerns",
        "detected_stack", "claim_checks", "findings",
    ],
}

QUESTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "expects": {"type": "string"},
                },
                "required": ["question", "expects"],
            },
        }
    },
    "required": ["questions"],
}

AUTHENTICITY_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_authenticity_score": {"type": "integer"},
        "ai_generated_likelihood": {"type": "string", "enum": ["low", "medium", "high"]},
        "summary": {"type": "string"},
        "flags": {"type": "array", "items": {"type": "string"}},
        "per_question": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_id": {"type": "string"},
                    "ai_likelihood": {"type": "string", "enum": ["low", "medium", "high"]},
                    "reason": {"type": "string"},
                },
                "required": ["question_id", "ai_likelihood", "reason"],
            },
        },
    },
    "required": [
        "overall_authenticity_score", "ai_generated_likelihood",
        "summary", "flags", "per_question",
    ],
}


# --------------------------------------------------------------------------
# Review Service
# --------------------------------------------------------------------------

class ReviewService:
    def __init__(self, chain: List[Provider]) -> None:
        if not chain:
            raise ReviewUnavailable(
                "No AI provider is configured. Set GEMINI_API_KEY, OPENROUTER_API_KEY, "
                "OPENAI_API_KEY, GROQ_API_KEY or ANTHROPIC_API_KEY."
            )
        self._chain = chain

    async def review(
        self,
        snapshots: List[Tuple[RepoSnapshot, str]],
        brief: str,
        requirements: List[str],
        submission: Optional[Dict[str, Any]] = None,
        archive: Optional[ArchiveSnapshot] = None,
        live_site: Optional[LiveSiteSnapshot] = None,
    ) -> AiReview:
        digest = _full_project_digest(snapshots, brief, requirements, submission, archive, live_site)
        try:
            raw, provider = await complete(
                self._chain,
                system=REVIEW_SYSTEM,
                user=digest,
                max_tokens=6000,
                json_schema=REVIEW_SCHEMA,
            )
        except AllProvidersFailed as exc:
            raise ReviewUnavailable(str(exc)) from exc

        model = next((p.model for p in self._chain if p.name == provider), "")
        return _build_review(
            extract_json(raw), snapshots, f"{provider}/{model}", archive, live_site
        )

    async def follow_up_questions(
        self,
        snapshots: List[Tuple[RepoSnapshot, str]],
        brief: str,
        count: int,
        submission: Optional[Dict[str, Any]] = None,
        archive: Optional[ArchiveSnapshot] = None,
        live_site: Optional[LiveSiteSnapshot] = None,
    ) -> List[FollowUpQuestion]:
        target_count = max(5, min(7, count or 6))
        digest = _full_project_digest(snapshots, brief, [], submission, archive, live_site)
        try:
            raw, _ = await complete(
                self._chain,
                system=QUESTIONS_SYSTEM,
                user=f"{digest}\n\nWrite between 5 and 7 deeply technical questions (target {target_count}).",
                max_tokens=3000,
                json_schema=QUESTIONS_SCHEMA,
            )
        except AllProvidersFailed as exc:
            raise ReviewUnavailable(str(exc)) from exc
        return _build_questions(extract_json(raw), target_count)

    async def assess_authenticity(
        self,
        questions: List[Dict[str, Any]],
        answers_with_telemetry: List[Dict[str, Any]],
        submission_summary: str,
    ) -> AnswerAuthenticityReport:
        qa_lines: List[str] = []
        q_map = {q["id"]: q["question"] for q in questions}

        heuristic_flags: List[str] = []
        total_paste_attempts = 0

        for item in answers_with_telemetry:
            qid = str(item.get("id"))
            text = str(item.get("answer", "")).strip()
            telemetry = item.get("telemetry") or {}
            time_spent = float(telemetry.get("time_spent_seconds", 0.0))
            keystrokes = int(telemetry.get("keystrokes", 0))
            pastes = int(telemetry.get("paste_attempts", 0))
            blurs = int(telemetry.get("blur_count", 0))

            total_paste_attempts += pastes
            if pastes > 0:
                heuristic_flags.append(f"Question '{qid[:6]}': {pastes} blocked paste attempt(s).")
            if len(text) > 200 and time_spent < 10.0:
                heuristic_flags.append(
                    f"Question '{qid[:6]}': Answer length {len(text)} chars with only {time_spent:.1f}s typing time."
                )
            if len(text) > 150 and keystrokes < (len(text) * 0.25):
                heuristic_flags.append(
                    f"Question '{qid[:6]}': Low keystroke count ({keystrokes}) for {len(text)} characters."
                )

            qa_lines.append(
                f"### Question: {q_map.get(qid, qid)}\n"
                f"ID: {qid}\n"
                f"Answer: {text}\n"
                f"Typing telemetry: time_spent={time_spent:.1f}s, keystrokes={keystrokes}, "
                f"paste_attempts={pastes}, tab_switches={blurs}\n"
            )

        prompt = f"""Project summary:
{submission_summary}

Answers submitted by the intern:
{"".join(qa_lines)}
"""
        try:
            raw, provider = await complete(
                self._chain,
                system=AUTHENTICITY_SYSTEM,
                user=prompt,
                max_tokens=2500,
                json_schema=AUTHENTICITY_SCHEMA,
            )
            parsed = extract_json(raw)
            all_flags = sorted(list(set(heuristic_flags + [str(f) for f in parsed.get("flags", [])])))
            score = int(parsed.get("overall_authenticity_score", 85))
            if total_paste_attempts > 1:
                score = min(score, 45)
            likelihood = parsed.get("ai_generated_likelihood", "low")
            if total_paste_attempts > 2 and likelihood == "low":
                likelihood = "medium"

            per_q = [
                QuestionAnswerAssessment(
                    question_id=str(pq.get("question_id", "")),
                    ai_likelihood=str(pq.get("ai_likelihood", "low")),
                    reason=str(pq.get("reason", "")),
                )
                for pq in parsed.get("per_question", [])
            ]
            model = next((p.model for p in self._chain if p.name == provider), "")
            return AnswerAuthenticityReport(
                overall_authenticity_score=max(0, min(100, score)),
                ai_generated_likelihood=likelihood,
                summary=str(parsed.get("summary", "")).strip(),
                flags=all_flags,
                per_question=per_q,
                analyzed_at=datetime.now(timezone.utc),
                model=f"{provider}/{model}",
            )
        except Exception as exc:
            logger.warning("Authenticity assessment fallback: %s", exc)
            return AnswerAuthenticityReport(
                overall_authenticity_score=75 if not heuristic_flags else 45,
                ai_generated_likelihood="medium" if heuristic_flags else "low",
                summary="Heuristic-based assessment (LLM analyzer unavailable).",
                flags=heuristic_flags,
                per_question=[],
                analyzed_at=datetime.now(timezone.utc),
                model="heuristic-fallback",
            )


def get_review_provider() -> ReviewService:
    return ReviewService(
        build_chain(settings.review_provider_chain, model_override=settings.AI_REVIEW_MODEL)
    )
