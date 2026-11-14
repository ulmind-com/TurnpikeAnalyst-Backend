"""Schemas for the internship programme.

Three things are modelled here:

* a **track** — a project brief an admin publishes, e.g. "Build a document
  ingestion dashboard";
* an **enrollment** — one intern's attempt at one track, carrying the
  submission, the automated review, the follow-up questions and the final
  human decision;
* the **settings** that govern deadlines, which are configuration rather
  than constants so the programme can be re-timed without a deploy.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import Field, HttpUrl, field_validator, model_validator

from app.models.enums import CourseLevel, EnrollmentMode, InternshipStatus, TrackCategory
from app.schemas.common import BaseSchema, PyObjectId


# --------------------------------------------------------------------------
# Tracks
# --------------------------------------------------------------------------

class TrackBase(BaseSchema):
    title: str = Field(..., min_length=3, max_length=150)
    slug: str = Field(..., min_length=3, max_length=150)
    category: TrackCategory
    level: CourseLevel = CourseLevel.BEGINNER
    summary: str = Field(..., max_length=500)
    brief: str = Field(..., description="Full project brief, Markdown.")

    # What the intern has to produce, and what they are free to choose.
    requirements: List[str] = Field(default_factory=list)
    deliverables: List[str] = Field(default_factory=list)
    suggested_stack: List[str] = Field(default_factory=list)

    # Days the intern gets from enrolling to submitting. Per-track because a
    # backend service and a landing page are not the same amount of work.
    build_days: int = Field(default=30, ge=1, le=365)

    cover_image_url: Optional[str] = None
    is_published: bool = True


class TrackCreate(TrackBase):
    pass


class TrackUpdate(BaseSchema):
    title: Optional[str] = None
    slug: Optional[str] = None
    category: Optional[TrackCategory] = None
    level: Optional[CourseLevel] = None
    summary: Optional[str] = None
    brief: Optional[str] = None
    requirements: Optional[List[str]] = None
    deliverables: Optional[List[str]] = None
    suggested_stack: Optional[List[str]] = None
    build_days: Optional[int] = Field(None, ge=1, le=365)
    cover_image_url: Optional[str] = None
    is_published: Optional[bool] = None


class TrackResponse(TrackBase):
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------
# Submission
# --------------------------------------------------------------------------

class Diagram(BaseSchema):
    """An architecture or data-flow diagram.

    Mermaid is offered alongside image upload because it is the only form the
    reviewer model can actually read — a PNG is opaque to it, so a diagram
    supplied that way can only be judged by a human.
    """

    kind: str = Field(..., description="mermaid | image")
    mermaid: Optional[str] = Field(None, max_length=20_000)
    asset_id: Optional[str] = None

    @model_validator(mode="after")
    def exactly_one_source(self) -> "Diagram":
        if self.kind == "mermaid":
            if not (self.mermaid or "").strip():
                raise ValueError("A Mermaid diagram needs its source text.")
            self.asset_id = None
        elif self.kind == "image":
            if not self.asset_id:
                raise ValueError("An image diagram needs an uploaded attachment.")
            self.mermaid = None
        else:
            raise ValueError("Diagram kind must be 'mermaid' or 'image'.")
        return self


class RepoEntry(BaseSchema):
    """One GitHub repository belonging to the intern's project."""

    url: HttpUrl
    role: str = Field(
        default="monorepo",
        description="monorepo | frontend | backend | admin | mobile | api | other",
    )
    label: Optional[str] = Field(None, max_length=60)

    @field_validator("url")
    @classmethod
    def must_be_github(cls, value: HttpUrl) -> HttpUrl:
        host = (value.host or "").lower()
        if host not in {"github.com", "www.github.com"}:
            raise ValueError("Repository URL must point at github.com")
        if len([part for part in value.path.strip("/").split("/") if part]) < 2:
            raise ValueError("Repository URL must be of the form https://github.com/owner/repo")
        return value


class SubmissionCreate(BaseSchema):
    """The project dossier an intern submits.

    Everything the client asked a candidate to show: the project and its
    purpose, the technology, the architecture, the data flow, the use cases,
    the benefit, the Git link(s), and proof that it runs.
    """

    repo_url: Optional[HttpUrl] = Field(None, description="Primary public GitHub repository URL.")
    repositories: List[RepoEntry] = Field(
        default_factory=list,
        max_length=6,
        description="All GitHub repositories when the project spans multiple repos.",
    )
    project_architecture_type: str = Field(
        default="single",
        description="single | multiple",
    )
    live_url: Optional[HttpUrl] = Field(
        None, description="Optional deployed URL, if the project is hosted."
    )
    demo_video_url: HttpUrl = Field(
        ...,
        description="Screen recording of the project running locally — the proof it works.",
    )

    purpose: str = Field(..., min_length=40, max_length=4000)
    technologies: List[str] = Field(..., min_length=1, max_length=40)
    architecture_text: str = Field(..., min_length=40, max_length=8000)
    architecture_diagram: Diagram
    data_flow_text: str = Field(..., min_length=40, max_length=8000)
    data_flow_diagram: Diagram
    use_cases: List[str] = Field(..., min_length=1, max_length=20)
    benefits: str = Field(..., min_length=40, max_length=4000)

    notes: Optional[str] = Field(
        None, max_length=4000, description="Anything else the reviewer should know."
    )

    @field_validator("repo_url")
    @classmethod
    def must_be_github(cls, value: Optional[HttpUrl]) -> Optional[HttpUrl]:
        if value is None:
            return None
        host = (value.host or "").lower()
        if host not in {"github.com", "www.github.com"}:
            raise ValueError("Repository URL must point at github.com")
        if len([part for part in value.path.strip("/").split("/") if part]) < 2:
            raise ValueError("Repository URL must be of the form https://github.com/owner/repo")
        return value

    @field_validator("technologies", "use_cases")
    @classmethod
    def no_blank_entries(cls, value: List[str]) -> List[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned:
            raise ValueError("At least one entry is required.")
        return cleaned

    @model_validator(mode="after")
    def sync_repositories(self) -> "SubmissionCreate":
        if not self.repositories and self.repo_url is None:
            raise ValueError("At least one GitHub repository URL is required.")
        if not self.repositories and self.repo_url is not None:
            self.repositories = [RepoEntry(url=self.repo_url, role="monorepo")]
        elif self.repositories:
            # Deduplicate by normalized URL
            seen: set[str] = set()
            deduped: List[RepoEntry] = []
            for entry in self.repositories:
                norm = str(entry.url).rstrip("/").lower()
                if norm.endswith(".git"):
                    norm = norm[:-4]
                if norm not in seen:
                    seen.add(norm)
                    deduped.append(entry)
            self.repositories = deduped
            if self.repo_url is None:
                self.repo_url = self.repositories[0].url
        return self


class Submission(BaseSchema):
    """The stored dossier.

    Every field after `notes` is optional so enrollments submitted before the
    dossier existed still load; new submissions always populate them.
    """

    repo_url: str
    repositories: List[Dict[str, Any]] = Field(default_factory=list)
    project_architecture_type: str = "single"
    live_url: Optional[str] = None
    notes: Optional[str] = None
    submitted_at: datetime

    demo_video_url: Optional[str] = None
    purpose: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    architecture_text: Optional[str] = None
    architecture_diagram: Optional[Diagram] = None
    data_flow_text: Optional[str] = None
    data_flow_diagram: Optional[Diagram] = None
    use_cases: List[str] = Field(default_factory=list)
    benefits: Optional[str] = None


# --------------------------------------------------------------------------
# Pre-submission live source analysis
# --------------------------------------------------------------------------

class SourceAnalysisRequest(BaseSchema):
    repositories: List[RepoEntry] = Field(..., min_length=1, max_length=6)
    live_url: Optional[HttpUrl] = None


class RepoPrecheckResult(BaseSchema):
    url: str
    role: str
    label: Optional[str] = None
    accessible: bool
    owner: Optional[str] = None
    name: Optional[str] = None
    default_branch: Optional[str] = None
    languages: Dict[str, int] = Field(default_factory=dict)
    commit_count: int = 0
    distinct_commit_days: int = 0
    file_count: int = 0
    has_tests: bool = False
    has_readme: bool = False
    is_fork: bool = False
    error: Optional[str] = None


class LiveSitePrecheckResult(BaseSchema):
    url: str
    final_url: str
    reachable: bool
    status_code: Optional[int] = None
    title: Optional[str] = None
    detected_tech: List[str] = Field(default_factory=list)
    is_placeholder_or_parked: bool = False
    error: Optional[str] = None


class SourceAnalysisResponse(BaseSchema):
    repos: List[RepoPrecheckResult]
    live_site: Optional[LiveSitePrecheckResult] = None
    detected_technologies: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    all_accessible: bool = True


# --------------------------------------------------------------------------
# Automated review
# --------------------------------------------------------------------------

class ReviewFinding(BaseSchema):
    """One observation, so the admin reads a list rather than an essay."""

    area: str = Field(..., description="structure | workflow | quality | testing | docs | security")
    severity: str = Field(..., description="info | minor | major")
    detail: str


class ClaimCheck(BaseSchema):
    """Whether the repository backs up something the intern wrote down.

    This is the core anti-fraud signal. A dossier is easy to write; a
    repository that matches it is not. Each row names the evidence so an
    admin can confirm the judgement rather than trust it.
    """

    claim: str
    verdict: str = Field(..., description="supported | partial | unsupported")
    evidence: str = Field(..., description="The file or fact that settles it.")


class AiReview(BaseSchema):
    score: int = Field(..., ge=0, le=100)
    verdict: str = Field(..., description="strong | acceptable | weak")
    summary: str
    strengths: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    detected_stack: List[str] = Field(default_factory=list)
    findings: List[ReviewFinding] = Field(default_factory=list)
    # One row per technology and architecture component the intern claimed.
    claim_checks: List[ClaimCheck] = Field(default_factory=list)

    # Repository facts the review was based on, kept so an admin can see what
    # the model actually looked at rather than taking the prose on trust.
    repo_facts: Dict[str, Any] = Field(default_factory=dict)
    repos_facts: List[Dict[str, Any]] = Field(default_factory=list)
    # The same, for the uploaded source archive — present only when the intern
    # uploaded one and it could be read.
    archive_facts: Optional[Dict[str, Any]] = None
    # Inspected live deployed site facts (when live_url was provided).
    live_site_facts: Optional[Dict[str, Any]] = None

    model: str
    reviewed_at: datetime


class AnswerTelemetry(BaseSchema):
    """Client-recorded typing metrics per follow-up answer."""

    time_spent_seconds: float = Field(default=0.0, ge=0, le=86400)
    keystrokes: int = Field(default=0, ge=0, le=100_000)
    paste_attempts: int = Field(default=0, ge=0, le=1000)
    blur_count: int = Field(default=0, ge=0, le=1000)


class FollowUpQuestion(BaseSchema):
    """A question generated from this specific repository.

    `expects` records what a good answer should demonstrate; it is shown to
    the admin alongside the intern's answer, never to the intern.
    """

    id: str
    question: str
    expects: Optional[str] = None
    answer: Optional[str] = None
    answered_at: Optional[datetime] = None
    telemetry: Optional[AnswerTelemetry] = None


class AnswerItem(BaseSchema):
    id: str
    answer: str
    telemetry: Optional[AnswerTelemetry] = None


class AnswerSubmission(BaseSchema):
    answers: List[AnswerItem] = Field(
        ..., description="[{id, answer, telemetry}] — every generated question must be answered."
    )


class QuestionAnswerAssessment(BaseSchema):
    question_id: str
    ai_likelihood: str = Field(..., description="low | medium | high")
    reason: str


class AnswerAuthenticityReport(BaseSchema):
    overall_authenticity_score: int = Field(..., ge=0, le=100)
    ai_generated_likelihood: str = Field(..., description="low | medium | high")
    summary: str
    flags: List[str] = Field(default_factory=list)
    per_question: List[QuestionAnswerAssessment] = Field(default_factory=list)
    analyzed_at: datetime
    model: str


class AdminDecision(BaseSchema):
    approved: bool
    notes: Optional[str] = Field(None, max_length=4000)
    # The reviewer model cannot watch the demo recording, so approval must
    # carry a human's word that someone did. The route rejects an approval
    # without it.
    demo_verified: bool = False


class DecisionRecord(BaseSchema):
    approved: bool
    notes: Optional[str] = None
    demo_verified: bool = False
    decided_by: str
    decided_at: datetime


# --------------------------------------------------------------------------
# Enrollment
# --------------------------------------------------------------------------

class OwnProjectProposal(BaseSchema):
    """An intern's own project, when they are not taking one of our briefs."""

    title: str = Field(..., min_length=4, max_length=150)
    summary: str = Field(
        ..., min_length=40, max_length=1000, description="What it is and what it will do."
    )
    intended_stack: List[str] = Field(..., min_length=1, max_length=30)

    @field_validator("intended_stack")
    @classmethod
    def no_blank_entries(cls, value: List[str]) -> List[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned:
            raise ValueError("Name at least one technology you intend to use.")
        return cleaned


class EnrollmentCreate(BaseSchema):
    """Start an attempt, from our catalogue or the intern's own idea."""

    mode: EnrollmentMode = EnrollmentMode.TRACK
    track_id: Optional[str] = None
    own_project: Optional[OwnProjectProposal] = None
    # The certificate states this, so the intern picks it up front rather
    # than having it inferred from how long they happened to take.
    duration_months: int = Field(default=1, ge=1, le=3)

    @model_validator(mode="after")
    def one_project_source(self) -> "EnrollmentCreate":
        if self.mode == EnrollmentMode.TRACK:
            if not self.track_id:
                raise ValueError("Choose a project from the catalogue.")
            self.own_project = None
        else:
            if not self.own_project:
                raise ValueError("Describe the project you intend to build.")
            self.track_id = None
        return self


class SourceArchiveMeta(BaseSchema):
    """The intern's uploaded project source archive, as shown back to them
    and to an admin. Storage internals (keys, backend) are deliberately not
    exposed; the file is reached only through an ownership-checked route."""

    asset_id: str
    filename: str
    size_bytes: int
    uploaded_at: datetime
    download_url: Optional[str] = None


class EnrollmentResponse(BaseSchema):
    id: str = Field(alias="_id")
    user_id: str
    # Admin-only convenience: the intern's identity, joined from the users
    # collection so a reviewer sees who submitted without a second lookup.
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    status: InternshipStatus

    mode: EnrollmentMode = EnrollmentMode.TRACK
    duration_months: int = 1
    # Set for both modes, so nothing downstream — screens, certificate — has
    # to know where the project came from.
    project_title: str
    project_summary: Optional[str] = None

    # Null for an intern's own project.
    track_id: Optional[str] = None
    track_title: Optional[str] = None
    track_slug: Optional[str] = None

    enrolled_at: datetime
    # Build window. Past this with nothing submitted, the attempt expires.
    deadline_at: datetime

    submission: Optional[Submission] = None
    # The uploaded project source archive, when one has been uploaded.
    source_archive: Optional[SourceArchiveMeta] = None
    questions: List[FollowUpQuestion] = Field(default_factory=list)
    # When the intern can expect a decision; shown as a date, not a promise
    # of instant turnaround.
    review_due_at: Optional[datetime] = None

    decision: Optional[DecisionRecord] = None
    certificate_id: Optional[str] = None

    # Present only for admins — the full automated report.
    ai_review: Optional[AiReview] = None
    # Present only for admins — authenticity & AI detection on submitted answers.
    answer_analysis: Optional[AnswerAuthenticityReport] = None
    # Why the automated review could not run, when it could not. The admin
    # needs this to know whether to read the repository themselves.
    review_error: Optional[str] = None


class EnrollmentPublic(BaseSchema):
    """What the intern sees.

    The automated review is deliberately absent: interns answer the follow-up
    questions on their own merit, and a visible score would turn the exercise
    into a negotiation.
    """

    id: str = Field(alias="_id")
    status: InternshipStatus

    mode: EnrollmentMode = EnrollmentMode.TRACK
    duration_months: int = 1
    project_title: str
    project_summary: Optional[str] = None

    track_id: Optional[str] = None
    track_title: Optional[str] = None
    track_slug: Optional[str] = None

    enrolled_at: datetime
    deadline_at: datetime
    submission: Optional[Submission] = None
    source_archive: Optional[SourceArchiveMeta] = None
    questions: List[FollowUpQuestion] = Field(default_factory=list)
    review_due_at: Optional[datetime] = None
    certificate_id: Optional[str] = None
    decision_notes: Optional[str] = None
    # Interns see that something went wrong on our side, not the detail.
    review_failed: bool = False


# --------------------------------------------------------------------------
# Programme settings
# --------------------------------------------------------------------------

class AttachmentResponse(BaseSchema):
    """An intern-uploaded diagram image."""

    asset_id: str
    filename: str
    content_type: str
    size_bytes: int
    url: str


class InternshipSettings(BaseSchema):
    """Singleton document controlling programme timing."""

    # Durations the intern may pick, in months. The certificate states it.
    allowed_durations: List[int] = Field(default_factory=lambda: [1, 2, 3])
    # Whether a screen recording of the project running is mandatory.
    require_demo_video: bool = True

    default_build_days: int = Field(default=30, ge=1, le=365)
    # Working days the team allows itself between the intern answering and a
    # decision being published.
    review_sla_days: int = Field(default=7, ge=1, le=60)
    # How many follow-up questions the review service generates per project.
    questions_per_submission: int = Field(default=5, ge=1, le=15)
    # Whether an intern may hold more than one active attempt at a time.
    allow_parallel_enrollments: bool = False
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InternshipSettingsUpdate(BaseSchema):
    allowed_durations: Optional[List[int]] = None
    require_demo_video: Optional[bool] = None
    default_build_days: Optional[int] = Field(None, ge=1, le=365)
    review_sla_days: Optional[int] = Field(None, ge=1, le=60)
    questions_per_submission: Optional[int] = Field(None, ge=1, le=15)
    allow_parallel_enrollments: Optional[bool] = None
