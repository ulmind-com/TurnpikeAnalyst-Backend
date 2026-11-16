# Turnpike Backend — FastAPI Enterprise & Internship API

> **Async FastAPI + MongoDB Motor backend** powering **Turnpike Frontend**, **Turnpike Admin**, the **dual-source AI internship verification pipeline**, **grounded support assistant**, and **automated PDF certificate engine**. Deployed to **Render**.

> **Full System Design (All Actors, Frontend, Admin & Data Flows):** [ARCHITECTURE.md](./ARCHITECTURE.md)  
> **Deployment Runbook:** [DEPLOYMENT.md](./DEPLOYMENT.md)

---

## Repository Layout

```text
app/
├── main.py                         # FastAPI app, lifespan, 12 index builders, 15 routers, /uploads
├── core/
│   ├── config.py                   # Pydantic v2 settings (env knobs, AI chains, Cloudinary, Firebase)
│   └── security.py                 # Passlib bcrypt hashing, HS256 access/refresh JWT encode/decode
├── api/
│   ├── deps.py                     # get_current_user, _active_user, _admin, require_roles
│   └── v1/                         # 15 domain FastAPI routers
├── schemas/                        # Pydantic v2 request/response contracts (outbound field filter)
├── crud/                           # Exclusive MongoDB Motor async access layer & index builders
├── services/                       # Pure HTTP-free domain services:
│   ├── llm.py                      # Multi-provider fallback chain (OpenRouter, Groq, OpenAI, Gemini, Anthropic)
│   ├── ai_review.py                # Dual-source prompts, claim checks & project-specific questions
│   ├── github_repo.py              # Bounded public GitHub repo snapshot fetcher
│   ├── source_archive.py           # In-memory .zip archive validator & digest (zip-slip/zip-bomb guards)
│   ├── certificate_render.py       # Dynamic Pillow PDF renderer + TA-YYYY-XXXXXXXXXX IDs
│   └── storage.py                  # Cloudinary (public + authenticated) / local dev storage
├── models/enums.py                 # UserRole, InternshipStatus, EnrollmentMode, etc.
└── db/mongodb.py                   # AsyncIOMotorClient lifecycle
scripts/                            # Seeders (seed_data, seed_internship, seed_chatbot) & cluster migration
render.yaml                         # Render deployment blueprint
```

---

## 4-Layer Backend Architecture

Each layer calls **only** the layer directly beneath it. Services never import FastAPI `Request` or raise `HTTPException` — they raise domain errors so the same review pipeline works inside both HTTP requests and detached `BackgroundTasks`.

```mermaid
graph TB
    subgraph L1["Layer 1 — Routers (app/api/v1/)"]
        R["HTTP routing · FastAPI Depends() auth · Status codes"]
    end
    subgraph L2["Layer 2 — Schemas (app/schemas/)"]
        S["Pydantic v2 validation at the edge & field filtering on output"]
    end
    subgraph L3["Layer 3 — Services (app/services/)"]
        SV["llm · ai_review · github_repo · source_archive · certificate_render · storage"]
    end
    subgraph L4["Layer 4 — CRUD (app/crud/)"]
        C["Exclusive Motor async MongoDB queries & 12 isolated index builders"]
    end
    DB[("MongoDB Atlas")]

    R --> S
    R --> SV
    R --> C
    SV --> C
    C --> DB
```

---

## Request Lifecycle, Auth & Super Admin Security

```mermaid
sequenceDiagram
    participant C as Client (Frontend / Admin)
    participant CORS as CORSMiddleware
    participant DEP as deps.py (JWT + Role Check)
    participant SVC as Service Layer
    participant CRUD as CRUD Layer
    participant DB as MongoDB Atlas

    C->>CORS: HTTP Request + Bearer JWT
    CORS->>CORS: Explicit origin check (CORS_ORIGINS)
    CORS->>DEP: Decode HS256 JWT (type == "access")
    DEP->>CRUD: Load user by ID / email
    CRUD->>DB: users.find_one()
    DEP->>DEP: Verify is_active & role (ADMIN / CONSULTANT / CLIENT)
    DEP->>SVC: Execute validated domain operation
    SVC->>CRUD: Read / Write collections
    CRUD->>DB: Async Motor operation
    SVC-->>C: Response shaped by Pydantic response_model
```

### Authentication & Privilege Safeguards
- **Staff & Admin (`/api/v1/auth/login`):** Email + bcrypt password hash (`OAuth2PasswordRequestForm`), issuing 30-minute access JWTs and 7-day refresh JWTs.
- **Intern Google Sign-In (`/api/v1/auth/google`):** Verifies Firebase ID token (`email_verified == true`), auto-provisions `CLIENT` role only.
- **Public Registration (`/api/v1/auth/register`):** Hardcodes `role = CLIENT` regardless of request body to prevent privilege escalation.
- **Super Administrator Bootstrap (`app/main.py`):** Seeds `SUPER_ADMIN_EMAIL` / `SUPER_ADMIN_PASSWORD` **only** when zero `ADMIN` users exist in MongoDB. Once created, live credentials are managed via `POST /api/v1/account/credentials` (which requires `current_password`).

---

## Dual-Source Internship Verification & AI Pipeline

```mermaid
sequenceDiagram
    actor I as Intern
    participant API as /api/v1/internship
    participant ZIP as source_archive.py
    participant CL as Cloudinary
    participant BG as BackgroundTask
    participant GH as GitHub REST API
    participant LLM as Multi-LLM Chain
    participant DB as MongoDB

    I->>API: POST .../source-archive (.zip upload, max 60 MB)
    API->>ZIP: digest_archive() in-memory ONLY
    Note over ZIP: Rejects traversal (../, absolute paths)<br/>Rejects zip bombs (>400 MB, >12k entries, >200:1 ratio)
    ZIP-->>API: ArchiveSnapshot verified
    API->>CL: store(private=True, resource_type="raw")
    API-->>I: 201 SourceArchiveMeta

    I->>API: POST .../submit (dossier + repo_url + demo_video_url)
    API->>DB: Store dossier, status = AI_REVIEWING
    API-->>I: 200 OK immediately

    BG->>GH: Fetch tree, manifests, 12 sampled files, commits, contributors
    BG->>CL: Fetch & digest uploaded .zip in memory
    BG->>LLM: Compare GitHub Snapshot + .zip Archive + Dossier Claims
    LLM-->>BG: Score, findings, claim_checks (supported/partial/unsupported)
    BG->>LLM: Generate N follow-up questions grounded in actual project files
    LLM-->>BG: FollowUpQuestion[]
    BG->>DB: Save ai_review (admin-only) + questions, status = QUESTIONS_PENDING
```

### Multi-Provider LLM Chain (`app/services/llm.py`)

```mermaid
flowchart LR
    REQ["Prompt + Optional JSON Schema"] --> P1{"OpenRouter<br/>(openrouter/free)"}
    P1 -->|OK| OUT["JSON Response + Provider"]
    P1 -->|"429 / 5xx / Timeout"| P2{"Groq"}
    P2 -->|OK| OUT
    P2 -->|Fail| P3{"OpenAI"}
    P3 -->|OK| OUT
    P3 -->|Fail| P4{"Gemini<br/>(generateContent)"}
    P4 -->|OK| OUT
    P4 -->|Fail| P5{"Anthropic<br/>(Messages)"}
    P5 -->|OK| OUT
    P5 -->|Fail| FAIL["AllProvidersFailed -> REVIEW_FAILED (queued for human admin)"]
```

---

## Grounded Support Assistant & Certificate Engine

```mermaid
flowchart TB
    Q["POST /api/v1/chatbot/chat"] --> RL{"Rate Limit<br/>20 req / 5 min / IP"}
    RL -->|Ok| TXT["Weighted Text Search on chatbot_knowledge<br/>question ×10 · keywords ×6 · answer ×2"]
    TXT --> TH{"Score >= Threshold?"}
    TH -->|Yes| LLM["Groq -> OpenRouter -> OpenAI<br/>Strict grounding prompt"]
    TH -->|No| NH["Mark needs_human = true -> Admin Unanswered Backlog"]
    NH --> LLM
    LLM --> SAVE["Save conversation -> Return reply"]
```

- **Certificate Rendering (`certificate_render.py`):** Admin approval requires `demo_verified: true`. Renders dynamic recipient name, project title, duration, issue date, and look-alike-free certificate ID (`TA-<year>-<10 chars>`) onto the active template via **Pillow**, stores the PDF on Cloudinary (`raw`, public), and exposes unauthenticated third-party verification at `GET /api/v1/internship/certificates/verify/{certificate_number}`.

---

## Complete API Surface (15 Routers)

Interactive docs: `/docs` (Swagger UI) and `/redoc` (ReDoc).

| Prefix | Auth | Purpose |
|---|---|---|
| `/api/v1/auth` | Public | Register (`CLIENT`), login, Google Firebase login, refresh token |
| `/api/v1/account` | `ADMIN` | Admin `/me` and password-verified `/credentials` rotation |
| `/api/v1/internship` | Public / `CLIENT` | Tracks, enroll, 4-step submit, `.zip` upload/download, diagram uploads, Q&A, verify |
| `/api/v1/internship/admin` | `ADMIN` | Settings, track CRUD, submission queue, AI reports, approve/decline, templates |
| `/api/v1/chatbot` | Public / `ADMIN` | Rate-limited grounded chat, knowledge CRUD, unanswered backlog, behaviour |
| `/api/v1/users` & `/activity-logs` | `ADMIN` | Staff/user role management & administrative audit trail |
| `/api/v1/services`, `/content`, `/blogs`, `/training`, `/cms`, `/consultants` | Public / Admin | Enterprise catalog, industries, JAMES WEBB & Agent P8, courses, CMS |
| `/api/v1/leads` & `/newsletter` | Public / Staff | Contact enquiries, book-a-call, demo requests, newsletter |

---

## Technologies Used in Turnpike Backend

| Category | Technologies & Libraries |
|---|---|
| **Web Framework & Server** | Python 3.12 · FastAPI `>=0.110` · Uvicorn `[standard]` · `python-multipart` |
| **Database & Validation** | MongoDB Atlas · Motor `>=3.3` (async driver) · Pydantic v2 `>=2.6` · `pydantic-settings` · `email-validator` |
| **Authentication & Security** | `python-jose[cryptography]` (HS256 JWT) · `passlib[bcrypt]` & `bcrypt` · `firebase-admin >=6.5` |
| **AI & External HTTP** | `httpx >=0.27` async HTTP client · OpenRouter · Groq · OpenAI · Google Gemini (`generateContent`) · Anthropic · GitHub REST API |
| **Storage, Archives & PDF** | Cloudinary SDK `>=1.40` · Pillow `>=10.3` (raster sanitization & PDF rendering) · Python `zipfile` (in-memory anti-tamper digest) |

---

## Local Development, Seeding & Cluster Migration

```bash
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env
./.venv/bin/uvicorn app.main:app --reload --port 8000
```

```bash
# Seed initial data
python -m scripts.seed_data          # users, services, courses, blogs
python scripts/seed_internship.py    # internship project briefs
python scripts/seed_chatbot.py       # support assistant knowledge base

# Non-destructive MongoDB cluster migration
MIGRATE_SOURCE_URL="mongodb+srv://..." python -m scripts.migrate_database --dry-run
MIGRATE_SOURCE_URL="mongodb+srv://..." python -m scripts.migrate_database
```

---

*Published from the Turnpike Analyst monorepo. See [ARCHITECTURE.md](./ARCHITECTURE.md) for the complete platform blueprint.*
