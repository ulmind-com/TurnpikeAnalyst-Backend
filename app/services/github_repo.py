"""Read a public GitHub repository well enough to review it.

What this collects is deliberately bounded. A review does not need every
byte of the project; it needs the shape of the tree, what the project says
about itself, how it was built over time, and a sample of real source files.
Pulling more than that costs tokens without improving the judgement.

Only public repositories are supported. A server-side token is used purely
to raise the rate limit (60/hour unauthenticated, 5000/hour with a token)
and never to reach anything the intern has not made public.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

GITHUB_API = "https://api.github.com"

# Files worth reading in full: they say what the project is and how it runs.
MANIFEST_FILES = {
    "readme.md", "readme.rst", "readme.txt", "readme",
    "package.json", "requirements.txt", "pyproject.toml", "pipfile",
    "go.mod", "cargo.toml", "pom.xml", "build.gradle", "composer.json",
    "gemfile", "dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "makefile", ".env.example", "vercel.json", "netlify.toml",
}

SOURCE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".kt",
    ".rb", ".php", ".cs", ".swift", ".vue", ".svelte", ".sql",
}

# Directories whose contents say nothing about the author's work.
IGNORED_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".output", "vendor",
    "__pycache__", ".venv", "venv", "target", "coverage", ".turbo", "out",
}

MAX_SOURCE_FILES = 12
MAX_FILE_BYTES = 24_000
REQUEST_TIMEOUT = 30.0


class RepoAccessError(RuntimeError):
    """The repository could not be read — missing, private, or renamed."""


@dataclass
class RepoSnapshot:
    """Everything the review service is given about a repository."""

    owner: str
    name: str
    html_url: str
    description: Optional[str]
    default_branch: str
    languages: Dict[str, int]
    topics: List[str]
    created_at: str
    pushed_at: str
    size_kb: int
    stargazers: int
    is_fork: bool
    license_name: Optional[str]

    commit_count: int
    commit_messages: List[str]
    distinct_commit_days: int
    contributors: List[str]

    tree: List[str]
    has_tests: bool
    has_ci: bool
    has_dockerfile: bool
    has_readme: bool

    manifests: Dict[str, str] = field(default_factory=dict)
    source_samples: Dict[str, str] = field(default_factory=dict)

    def as_facts(self) -> Dict[str, Any]:
        """The subset stored on the enrollment, so an admin can see what the
        review was based on without re-fetching the repository."""
        return {
            "repo": f"{self.owner}/{self.name}",
            "default_branch": self.default_branch,
            "languages": self.languages,
            "commit_count": self.commit_count,
            "distinct_commit_days": self.distinct_commit_days,
            "contributors": self.contributors,
            "file_count": len(self.tree),
            "has_tests": self.has_tests,
            "has_ci": self.has_ci,
            "has_dockerfile": self.has_dockerfile,
            "has_readme": self.has_readme,
            "is_fork": self.is_fork,
            "created_at": self.created_at,
            "pushed_at": self.pushed_at,
            "license": self.license_name,
        }


def parse_repo_url(url: str) -> tuple[str, str]:
    """Pull owner and repo out of a GitHub URL.

    Accepts the forms people actually paste: with or without .git, with or
    without a trailing slash, and with extra path segments such as /tree/main.
    """
    match = re.match(
        r"^https?://(?:www\.)?github\.com/([^/\s]+)/([^/\s?#]+)",
        url.strip(),
        flags=re.IGNORECASE,
    )
    if not match:
        raise RepoAccessError("That does not look like a GitHub repository URL.")
    owner, name = match.group(1), match.group(2)
    if name.endswith(".git"):
        name = name[:-4]
    return owner, name


def _headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        # GitHub asks automated clients to identify themselves.
        "User-Agent": "turnpike-internship-reviewer",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    return headers


async def _get(client: httpx.AsyncClient, path: str, **params: Any) -> Any:
    response = await client.get(f"{GITHUB_API}{path}", params=params or None)
    if response.status_code == 404:
        raise RepoAccessError(
            "Repository not found. It must exist and be public for the review to read it."
        )
    if response.status_code == 403 and "rate limit" in response.text.lower():
        raise RepoAccessError("GitHub rate limit reached. Try again shortly.")
    response.raise_for_status()
    return response.json()


def _should_sample(path: str) -> bool:
    parts = path.split("/")
    if any(part in IGNORED_DIRS for part in parts):
        return False
    lowered = parts[-1].lower()
    if lowered in MANIFEST_FILES:
        return False
    return any(lowered.endswith(ext) for ext in SOURCE_EXTENSIONS)


async def _fetch_file(client: httpx.AsyncClient, owner: str, name: str, path: str) -> Optional[str]:
    try:
        payload = await _get(client, f"/repos/{owner}/{name}/contents/{path}")
    except (RepoAccessError, httpx.HTTPError):
        return None
    if isinstance(payload, list) or payload.get("encoding") != "base64":
        return None
    try:
        raw = base64.b64decode(payload["content"])
    except Exception:
        return None
    return raw[:MAX_FILE_BYTES].decode("utf-8", errors="replace")


async def fetch_repo_snapshot(repo_url: str) -> RepoSnapshot:
    """Collect the facts a review needs. Raises RepoAccessError on anything
    the intern can fix themselves (wrong URL, private repo)."""
    owner, name = parse_repo_url(repo_url)

    # Redirects must be followed: GitHub answers 301 for any repository that
    # has been renamed or transferred between owners, and interns paste the
    # URL they remember rather than the current one.
    async with httpx.AsyncClient(
        headers=_headers(), timeout=REQUEST_TIMEOUT, follow_redirects=True
    ) as client:
        repo = await _get(client, f"/repos/{owner}/{name}")
        if repo.get("private"):
            raise RepoAccessError("That repository is private. Make it public to submit it.")

        default_branch = repo.get("default_branch") or "main"

        languages, commits, tree_payload = await asyncio.gather(
            _get(client, f"/repos/{owner}/{name}/languages"),
            _get(client, f"/repos/{owner}/{name}/commits", per_page=100),
            _get(client, f"/repos/{owner}/{name}/git/trees/{default_branch}", recursive="1"),
            return_exceptions=True,
        )
        languages = languages if isinstance(languages, dict) else {}
        commits = commits if isinstance(commits, list) else []
        tree_entries = (
            tree_payload.get("tree", []) if isinstance(tree_payload, dict) else []
        )

        paths = [
            entry["path"]
            for entry in tree_entries
            if entry.get("type") == "blob"
            and not any(part in IGNORED_DIRS for part in entry["path"].split("/"))
        ]

        commit_messages: List[str] = []
        commit_days: set[str] = set()
        contributors: set[str] = set()
        for commit in commits:
            detail = commit.get("commit", {})
            message = (detail.get("message") or "").splitlines()[0][:160]
            if message:
                commit_messages.append(message)
            date = (detail.get("author") or {}).get("date") or ""
            if date:
                commit_days.add(date[:10])
            login = (commit.get("author") or {}).get("login")
            if login:
                contributors.add(login)

        lowered_paths = [path.lower() for path in paths]
        snapshot = RepoSnapshot(
            owner=owner,
            name=name,
            html_url=repo.get("html_url", repo_url),
            description=repo.get("description"),
            default_branch=default_branch,
            languages=languages,
            topics=repo.get("topics", []) or [],
            created_at=repo.get("created_at", ""),
            pushed_at=repo.get("pushed_at", ""),
            size_kb=repo.get("size", 0),
            stargazers=repo.get("stargazers_count", 0),
            is_fork=bool(repo.get("fork")),
            license_name=(repo.get("license") or {}).get("name"),
            commit_count=len(commits),
            commit_messages=commit_messages[:40],
            distinct_commit_days=len(commit_days),
            contributors=sorted(contributors),
            tree=paths[:600],
            has_tests=any(
                "test" in path or "spec" in path for path in lowered_paths
            ),
            has_ci=any(path.startswith(".github/workflows/") for path in lowered_paths),
            has_dockerfile=any(
                path.split("/")[-1] in {"dockerfile", "docker-compose.yml", "docker-compose.yaml"}
                for path in lowered_paths
            ),
            has_readme=any(
                path.split("/")[-1].startswith("readme") for path in lowered_paths
            ),
        )

        manifest_paths = [
            path for path in paths if path.split("/")[-1].lower() in MANIFEST_FILES
        ][:8]
        sample_paths = [path for path in paths if _should_sample(path)][:MAX_SOURCE_FILES]

        fetched = await asyncio.gather(
            *(_fetch_file(client, owner, name, path) for path in manifest_paths + sample_paths),
            return_exceptions=True,
        )

        for path, content in zip(manifest_paths + sample_paths, fetched):
            if not isinstance(content, str):
                continue
            if path in manifest_paths:
                snapshot.manifests[path] = content
            else:
                snapshot.source_samples[path] = content

    logger.info(
        "Read %s/%s for review: %d files, %d commits, %d sampled sources",
        owner,
        name,
        len(snapshot.tree),
        snapshot.commit_count,
        len(snapshot.source_samples),
    )
    return snapshot
