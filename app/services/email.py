"""Transactional email service powered by Resend.

Sends branded, responsive notifications for the internship & account lifecycle:
1. Welcome / Account Registered (manual, Google, or Apple sign-up).
2. Project Enrolled / Clock Started.
3. Automated Review Finished & Follow-Up Questions Waiting.
4. Certificate Issued / Submission Approved (includes certificate number & links).

The markup is assembled with the :mod:`app.services.html_builder` element
builder — there is no literal HTML in this module; every element is a Python
call and user-supplied text is escaped automatically.

If RESEND_API_KEY is not configured, the service logs the email payload and
returns cleanly rather than crashing the caller.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.html_builder import Node, document, el, raw

logger = logging.getLogger("uvicorn.error")

RESEND_ENDPOINT = "https://api.resend.com/emails"
TIMEOUT = httpx.Timeout(15.0)

# Reused inline styles (email clients require inline CSS; these are data, not markup).
_CARD_PANEL = (
    "background-color: #162032; border: 1px solid #1E293B; border-radius: 14px;"
    " padding: 18px; margin: 20px 0;"
)
_HEAD_CSS = (
    "body, table, td, a { -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }"
    " table, td { mso-table-lspace: 0pt; mso-table-rspace: 0pt; }"
    " img { -ms-interpolation-mode: bicubic; border: 0; outline: none; text-decoration: none; }"
)


def _base_email_template(
    *,
    preheader: str,
    headline: str,
    content: List[Node],
    action_text: Optional[str] = None,
    action_url: Optional[str] = None,
    footer_note: Optional[str] = None,
) -> str:
    """Ultra-premium dark/slate email shell, built as Python elements."""
    site_url = settings.SITE_PUBLIC_URL.rstrip("/")
    btn_url = action_url or site_url

    action_block: Node = None
    if action_text and action_url:
        action_block = el(
            "table",
            el(
                "tr",
                el(
                    "td",
                    el(
                        "a",
                        f"{action_text} →",
                        href=btn_url,
                        target="_blank",
                        style=(
                            "display: inline-block; background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);"
                            " color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;"
                            " font-size: 14px; font-weight: 600; text-decoration: none; padding: 13px 28px;"
                            " border-radius: 9999px; box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35);"
                        ),
                    ),
                    align="left",
                ),
            ),
            role="presentation",
            border="0",
            cellpadding="0",
            cellspacing="0",
            style="margin: 28px 0 20px 0;",
        )

    footer_content = footer_note or "Turnpike Analyst Enterprise Content & Automation Platform."

    header_row = el(
        "tr",
        el(
            "td",
            el(
                "table",
                el(
                    "tr",
                    el(
                        "td",
                        el("span", "Turnpike", style="font-size: 20px; font-weight: 800; letter-spacing: -0.02em; color: #38BDF8;"),
                        el("span", "Analyst", style="font-size: 20px; font-weight: 700; color: #F8FAFC;"),
                    ),
                    el(
                        "td",
                        el(
                            "span",
                            "Official Notice",
                            style=(
                                "display: inline-block; background-color: rgba(56, 189, 248, 0.1);"
                                " border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 9999px; padding: 4px 12px;"
                                " font-size: 11px; font-weight: 600; color: #38BDF8; text-transform: uppercase; letter-spacing: 0.08em;"
                            ),
                        ),
                        align="right",
                    ),
                ),
                role="presentation",
                border="0",
                cellpadding="0",
                cellspacing="0",
                width="100%",
            ),
            style="padding: 32px 36px; border-bottom: 1px solid #1F2937; background: linear-gradient(180deg, #162032 0%, #111827 100%);",
        ),
    )

    body_row = el(
        "tr",
        el(
            "td",
            el("h1", headline, style="margin: 0 0 16px 0; font-size: 22px; font-weight: 700; line-height: 1.3; color: #F8FAFC;"),
            el("div", *content, style="font-size: 14px; line-height: 1.65; color: #94A3B8;"),
            action_block,
            style="padding: 36px 36px 28px 36px;",
        ),
    )

    footer_row = el(
        "tr",
        el(
            "td",
            el("p", footer_content, style="margin: 0 0 8px 0; font-size: 12px; color: #64748B;"),
            el(
                "p",
                f"© {datetime.now().year} Turnpike Analyst. All rights reserved. Do not reply directly to this automated email.",
                style="margin: 0; font-size: 11px; color: #475569;",
            ),
            style="padding: 24px 36px; background-color: #0D131F; border-top: 1px solid #1F2937; text-align: center;",
        ),
    )

    card = el(
        "table",
        header_row,
        body_row,
        footer_row,
        role="presentation",
        border="0",
        cellpadding="0",
        cellspacing="0",
        width="100%",
        style="max-width: 600px; background-color: #111827; border: 1px solid #1F2937; border-radius: 24px; overflow: hidden; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.45);",
    )

    outer = el(
        "table",
        el("tr", el("td", card, align="center", style="padding: 40px 16px;")),
        role="presentation",
        border="0",
        cellpadding="0",
        cellspacing="0",
        width="100%",
        style="background-color: #0B0F19;",
    )

    head = el(
        "head",
        el("meta", charset="UTF-8"),
        el("meta", name="viewport", content="width=device-width, initial-scale=1.0"),
        el("title", headline),
        el("style", raw(_HEAD_CSS)),
    )

    preheader_span = el(
        "span",
        preheader,
        style="display: none; font-size: 1px; color: #0B0F19; line-height: 1px; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden;",
    )

    body = el(
        "body",
        preheader_span,
        outer,
        style="margin: 0; padding: 0; background-color: #0B0F19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #F1F5F9;",
    )

    return document(el("html", head, body, lang="en"))


async def send_resend_email(
    *,
    to_email: str,
    subject: str,
    html: str,
) -> bool:
    """Send an email using Resend API, with graceful fallback logging."""
    if not settings.RESEND_API_KEY:
        logger.info(
            "RESEND_API_KEY not configured. Simulated email to %s: '%s'",
            to_email,
            subject,
        )
        return True

    payload: Dict[str, Any] = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }

    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(RESEND_ENDPOINT, json=payload, headers=headers)
        if response.status_code in {200, 201}:
            logger.info("Resend email sent successfully to %s: %s", to_email, subject)
            return True
        logger.warning(
            "Resend returned %d for email to %s: %s",
            response.status_code,
            to_email,
            response.text[:200],
        )
        return False
    except Exception as exc:
        logger.error("Failed to deliver Resend email to %s: %s", to_email, exc)
        return False


# --------------------------------------------------------------------------
# Branded Notification Templates
# --------------------------------------------------------------------------

async def send_welcome_email(user_email: str, user_name: str) -> bool:
    name = (user_name or "Intern").strip()
    content: List[Node] = [
        el(
            "p",
            "Your Turnpike Analyst account has been successfully created. You now have full access to our"
            " project catalogue, internship programme, automated code reviewer, and verified certification platform.",
        ),
        el(
            "div",
            el("p", "Next steps to earn your verified credential:", style="margin: 0 0 8px 0; font-size: 13px; font-weight: 600; color: #38BDF8;"),
            el(
                "ul",
                el("li", "Browse published internship project briefs or propose your own architecture."),
                el("li", "Enrol to start your build clock and receive requirements."),
                el("li", "Connect your GitHub repository, submit your .zip code archive, and answer AI follow-up questions."),
                style="margin: 0; padding-left: 20px; font-size: 13px; color: #CBD5E1; line-height: 1.6;",
            ),
            style=_CARD_PANEL,
        ),
        el("p", "We are excited to see what you build."),
    ]
    html = _base_email_template(
        preheader="Welcome to Turnpike Analyst — your account is ready.",
        headline=f"Welcome aboard, {name}!",
        content=content,
        action_text="Explore Projects & Dashboard",
        action_url=f"{settings.SITE_PUBLIC_URL.rstrip('/')}/internship",
    )
    return await send_resend_email(
        to_email=user_email,
        subject="Welcome to Turnpike Analyst — Your Account is Ready",
        html=html,
    )


async def send_verification_code_email(user_email: str, code: str, user_name: str = "") -> bool:
    """One-time 6-digit code for email-verified manual sign-up."""
    name = (user_name or "").strip()
    greeting = f"Hi {name}," if name else "Hi there,"
    content: List[Node] = [
        el("p", greeting),
        el(
            "p",
            "Use the verification code below to confirm your email and finish creating your"
            " Turnpike Analyst account. The code expires in 10 minutes.",
        ),
        el(
            "div",
            el(
                "span",
                code,
                style=(
                    "font-family: 'SF Mono', ui-monospace, 'Roboto Mono', Menlo, monospace;"
                    " font-size: 34px; font-weight: 700; letter-spacing: 0.4em; color: #F8FAFC;"
                    " padding-left: 0.4em;"
                ),
            ),
            style=(
                _CARD_PANEL
                + " text-align: center; padding: 26px 18px;"
            ),
        ),
        el(
            "p",
            "If you did not request this, you can safely ignore this email — no account will be created.",
            style="font-size: 12px; color: #94A3B8;",
        ),
    ]
    html = _base_email_template(
        preheader="Your Turnpike Analyst verification code.",
        headline="Verify your email",
        content=content,
        footer_note="This code is valid for 10 minutes and can be used once.",
    )
    return await send_resend_email(
        to_email=user_email,
        subject=f"{code} is your Turnpike Analyst verification code",
        html=html,
    )


async def send_enrollment_email(
    user_email: str,
    user_name: str,
    project_title: str,
    duration_months: int,
    deadline_at: datetime,
) -> bool:
    name = (user_name or "Intern").strip()
    deadline_str = deadline_at.strftime("%d %B %Y")
    duration_label = f"{duration_months} month" + ("s" if duration_months > 1 else "")

    def row(label: str, value: str, value_style: str) -> Node:
        return el(
            "tr",
            el("td", label, style="color: #64748B; padding: 4px 0;"),
            el("td", value, style=value_style),
        )

    content: List[Node] = [
        el("p", f"Hi {name},"),
        el(
            "p",
            "You have officially enrolled in ",
            el("strong", project_title),
            ". Your build window is active and the requirements are ready for implementation.",
        ),
        el(
            "div",
            el(
                "table",
                row("Project:", project_title, "color: #F8FAFC; font-weight: 600; padding: 4px 0;"),
                row("Duration:", duration_label, "color: #F8FAFC; padding: 4px 0;"),
                row("Deadline:", deadline_str, "color: #F59E0B; font-weight: 600; padding: 4px 0;"),
                role="presentation",
                border="0",
                cellpadding="0",
                cellspacing="0",
                width="100%",
                style="font-size: 13px;",
            ),
            style=_CARD_PANEL,
        ),
        el(
            "p",
            "Build your solution cleanly with good commit hygiene. When you are ready, submit your GitHub"
            " repositories, uploaded source .zip archive, and a brief screen recording of the project running.",
        ),
    ]
    html = _base_email_template(
        preheader=f"Enrolled in {project_title}. Build clock started.",
        headline="Project Enrolled & Build Clock Started",
        content=content,
        action_text="Open Your Project Workspace",
        action_url=f"{settings.SITE_PUBLIC_URL.rstrip('/')}/internship/dashboard",
    )
    return await send_resend_email(
        to_email=user_email,
        subject=f"Build Clock Started: {project_title}",
        html=html,
    )


async def send_questions_ready_email(
    user_email: str,
    user_name: str,
    project_title: str,
    enrollment_id: str,
    question_count: int,
) -> bool:
    name = (user_name or "Intern").strip()
    content: List[Node] = [
        el("p", f"Hi {name},"),
        el(
            "p",
            "Our automated engineering review has completed analyzing your code across your GitHub"
            " repository/repositories, your source archive, and your live deployment for ",
            el("strong", project_title),
            ".",
        ),
        el(
            "p",
            "Based on your exact architecture and implementation, ",
            el("strong", f"{question_count} project-specific follow-up questions"),
            " have been generated.",
        ),
        el(
            "div",
            el("p", "Anti-Cheat & Authenticity Notice:", style="margin: 0; font-size: 13px; color: #10B981; font-weight: 600;"),
            el(
                "p",
                "Please answer these questions in your own words. Copy-pasting is disabled in the dashboard to"
                " ensure genuine technical reflections. Explain your real design choices and debugging trade-offs.",
                style="margin: 6px 0 0 0; font-size: 13px; color: #CBD5E1;",
            ),
            style="background-color: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 14px; padding: 18px; margin: 20px 0;",
        ),
    ]
    html = _base_email_template(
        preheader="Automated review complete: follow-up technical questions are waiting.",
        headline="AI Code Review Complete — Questions Waiting",
        content=content,
        action_text="Answer Technical Questions",
        action_url=f"{settings.SITE_PUBLIC_URL.rstrip('/')}/internship/dashboard/{enrollment_id}",
    )
    return await send_resend_email(
        to_email=user_email,
        subject=f"Follow-Up Technical Questions Ready: {project_title}",
        html=html,
    )


async def send_certificate_email(
    user_email: str,
    user_name: str,
    project_title: str,
    certificate_number: str,
    pdf_url: str,
) -> bool:
    name = (user_name or "Intern").strip()
    site_url = settings.SITE_PUBLIC_URL.rstrip("/")
    verification_url = f"{site_url}/verify/{certificate_number}"

    content: List[Node] = [
        el("p", f"Hi {name},"),
        el(
            "p",
            "We are delighted to inform you that your internship submission for ",
            el("strong", project_title),
            " has been thoroughly reviewed and ",
            el("strong", "approved"),
            " by our engineering team!",
        ),
        el(
            "div",
            el("span", "Verified Credential Number", style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.15em; color: #F59E0B; font-weight: 700;"),
            el(
                "div",
                certificate_number,
                style="font-family: monospace; font-size: 20px; font-weight: 800; color: #F8FAFC; margin: 8px 0 12px 0; letter-spacing: 0.05em;",
            ),
            el("p", "Cryptographically verifiable by employers and clients worldwide.", style="margin: 0; font-size: 12px; color: #94A3B8;"),
            style="background: linear-gradient(135deg, rgba(217, 119, 6, 0.12) 0%, rgba(245, 158, 11, 0.04) 100%); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 16px; padding: 22px; margin: 24px 0; text-align: center;",
        ),
        el(
            "p",
            "You can download your high-resolution official PDF certificate directly or share your public"
            " verification link on LinkedIn and your resume.",
        ),
    ]
    html = _base_email_template(
        preheader=f"Congratulations! Your certificate {certificate_number} has been issued.",
        headline="Congratulations! Your Internship Certificate is Issued",
        content=content,
        action_text="View & Verify Certificate",
        action_url=verification_url,
    )
    return await send_resend_email(
        to_email=user_email,
        subject=f"Certificate Issued: {project_title} ({certificate_number})",
        html=html,
    )
