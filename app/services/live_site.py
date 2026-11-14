"""Safely inspect a submitted live deployment URL.

The internship review reads both the code (GitHub + uploaded zip) and any
live deployed URL the intern supplied. Checking the live site keeps an intern
from linking someone else's unrelated website or a dead placeholder.

Because the URL comes from an untrusted user, every hop (initial URL plus
redirects) is DNS-resolved and checked against private/loopback/metadata IP
ranges before any TCP connection is allowed (SSRF defense).
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import socket
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger("uvicorn.error")

MAX_LIVE_BYTES = 512 * 1024
LIVE_TIMEOUT = httpx.Timeout(connect=6.0, read=10.0, write=6.0, pool=6.0)
MAX_REDIRECTS = 4

PLACEHOLDER_PATTERNS = (
    "domain is for sale",
    "this site is parked",
    "deployment not found",
    "404: the page could not be found",
    "welcome to nginx!",
    "apache2 ubuntu default page",
    "placeholder page",
)


class LiveSiteError(RuntimeError):
    """Raised when a URL is invalid or unsafe to fetch."""


@dataclass
class LiveSiteSnapshot:
    url: str
    final_url: str
    reachable: bool
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    title: Optional[str] = None
    meta_description: Optional[str] = None
    headings: List[str] = field(default_factory=list)
    detected_tech: List[str] = field(default_factory=list)
    text_excerpt: str = ""
    is_placeholder_or_parked: bool = False
    error: Optional[str] = None

    def as_facts(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "final_url": self.final_url,
            "reachable": self.reachable,
            "status_code": self.status_code,
            "content_type": self.content_type,
            "title": self.title,
            "meta_description": self.meta_description,
            "headings": self.headings[:8],
            "detected_tech": self.detected_tech,
            "is_placeholder_or_parked": self.is_placeholder_or_parked,
            "error": self.error,
        }


def _is_forbidden_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


async def _validate_public_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise LiveSiteError("Live URL must be a valid http:// or https:// address.")
    host = parsed.hostname.lower()
    if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"} or host.endswith(".local"):
        raise LiveSiteError("Local or private network URLs cannot be inspected as live deployments.")

    try:
        infos = await asyncio.to_thread(
            socket.getaddrinfo, host, parsed.port or (443 if parsed.scheme == "https" else 80)
        )
    except socket.gaierror as exc:
        raise LiveSiteError(f"Could not resolve hostname '{host}'.") from exc

    ips = {info[4][0] for info in infos if info[4]}
    if not ips or any(_is_forbidden_ip(ip) for ip in ips):
        raise LiveSiteError("Target resolves to a restricted or private IP address.")
    return parsed.geturl()


class _SimpleHTMLInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.in_heading = False
        self.skip_depth = 0
        self.title_parts: List[str] = []
        self.meta_description: Optional[str] = None
        self.headings: List[str] = []
        self._current_heading: List[str] = []
        self.text_parts: List[str] = []
        self.raw_markers: List[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        t = tag.lower()
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        if t in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
        if t == "title":
            self.in_title = True
        elif t in {"h1", "h2"}:
            self.in_heading = True
            self._current_heading = []
        elif t == "meta":
            name = (attr_map.get("name") or attr_map.get("property") or "").lower()
            if name in {"description", "og:description"} and not self.meta_description:
                self.meta_description = attr_map.get("content", "").strip()[:300]
            elif name == "generator" and attr_map.get("content"):
                self.raw_markers.append(attr_map["content"])
        if t == "script" and attr_map.get("src"):
            self.raw_markers.append(attr_map["src"])
        if t == "link" and attr_map.get("href"):
            self.raw_markers.append(attr_map["href"])
        if attr_map.get("id") in {"__next", "root", "app", "__nuxt"}:
            self.raw_markers.append(f"id={attr_map['id']}")

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in {"script", "style", "noscript", "svg"} and self.skip_depth > 0:
            self.skip_depth -= 1
        if t == "title":
            self.in_title = False
        elif t in {"h1", "h2"} and self.in_heading:
            self.in_heading = False
            heading_text = " ".join("".join(self._current_heading).split())
            if heading_text and len(self.headings) < 12:
                self.headings.append(heading_text[:160])

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.in_heading:
            self._current_heading.append(data)
        if self.skip_depth == 0:
            cleaned = " ".join(data.split())
            if cleaned:
                self.text_parts.append(cleaned)


def _detect_technologies(
    html_lower: str, markers: List[str], headers: httpx.Headers, content_type: str
) -> List[str]:
    tech: List[str] = []
    joined_markers = " ".join(markers).lower()

    checks = [
        ("Next.js", "__next" in html_lower or "/_next/" in joined_markers),
        ("React", "id=root" in joined_markers or "react" in joined_markers),
        ("Vite", "/assets/index-" in joined_markers or "@vite" in joined_markers),
        ("Vue / Nuxt", "__nuxt" in html_lower or "vue" in joined_markers),
        ("Angular", "ng-version" in html_lower),
        ("Tailwind CSS", "tailwind" in html_lower),
        ("FastAPI / Swagger", "swagger-ui" in html_lower or "/openapi.json" in html_lower),
        ("JSON REST API", "application/json" in content_type.lower()),
    ]
    for label, hit in checks:
        if hit and label not in tech:
            tech.append(label)

    server = (headers.get("server") or "").lower()
    powered = (headers.get("x-powered-by") or "").lower()
    if "vercel" in server or headers.get("x-vercel-id"):
        tech.append("Hosted on Vercel")
    elif "render" in server or headers.get("x-render-origin-server"):
        tech.append("Hosted on Render")
    elif "netlify" in server or headers.get("x-nf-request-id"):
        tech.append("Hosted on Netlify")
    elif "cloudflare" in server:
        tech.append("Cloudflare")
    if "express" in powered:
        tech.append("Express.js")
    return tech


async def fetch_live_site_snapshot(url: str) -> LiveSiteSnapshot:
    """Safely fetch and inspect a deployed project URL.

    Never raises for network errors or HTTP 4xx/5xx — captures them cleanly
    into `LiveSiteSnapshot(reachable=False, error=...)` so callers and the AI
    reviewer can report exact diagnostics without crashing the submission.
    """
    current_url = url.strip()
    try:
        current_url = await _validate_public_url(current_url)
    except LiveSiteError as exc:
        return LiveSiteSnapshot(
            url=url,
            final_url=url,
            reachable=False,
            error=str(exc),
        )

    headers = {
        "User-Agent": "TurnpikeAnalyst-SubmissionInspector/1.0",
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    }

    try:
        async with httpx.AsyncClient(
            timeout=LIVE_TIMEOUT, follow_redirects=False, headers=headers
        ) as client:
            response: Optional[httpx.Response] = None
            for _ in range(MAX_REDIRECTS + 1):
                response = await client.get(current_url)
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        break
                    next_url = urljoin(current_url, location)
                    current_url = await _validate_public_url(next_url)
                    continue
                break

            assert response is not None
            raw = response.content[:MAX_LIVE_BYTES]
            content_type = response.headers.get("content-type", "")
            status = response.status_code
            reachable = 200 <= status < 400

            if "application/json" in content_type.lower():
                excerpt = raw.decode("utf-8", errors="replace")[:1200]
                return LiveSiteSnapshot(
                    url=url,
                    final_url=current_url,
                    reachable=reachable,
                    status_code=status,
                    content_type=content_type,
                    title="JSON API Endpoint",
                    detected_tech=_detect_technologies("", [], response.headers, content_type),
                    text_excerpt=excerpt,
                    error=None if reachable else f"HTTP {status}",
                )

            html_text = raw.decode("utf-8", errors="replace")
            parser = _SimpleHTMLInspector()
            parser.feed(html_text)
            title = " ".join("".join(parser.title_parts).split())[:180] or None
            excerpt = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()[:1400]
            lowered_all = f"{title or ''} {excerpt}".lower()
            is_placeholder = (not reachable) or any(
                pat in lowered_all for pat in PLACEHOLDER_PATTERNS
            )

            return LiveSiteSnapshot(
                url=url,
                final_url=current_url,
                reachable=reachable,
                status_code=status,
                content_type=content_type,
                title=title,
                meta_description=parser.meta_description,
                headings=parser.headings,
                detected_tech=_detect_technologies(
                    html_text.lower(), parser.raw_markers, response.headers, content_type
                ),
                text_excerpt=excerpt,
                is_placeholder_or_parked=is_placeholder,
                error=None if reachable else f"HTTP {status}",
            )
    except LiveSiteError as exc:
        return LiveSiteSnapshot(url=url, final_url=current_url, reachable=False, error=str(exc))
    except httpx.TimeoutException:
        return LiveSiteSnapshot(
            url=url,
            final_url=current_url,
            reachable=False,
            error="Live URL timed out after 10 seconds.",
        )
    except httpx.HTTPError as exc:
        return LiveSiteSnapshot(
            url=url,
            final_url=current_url,
            reachable=False,
            error=f"Could not connect to live URL: {exc}",
        )

