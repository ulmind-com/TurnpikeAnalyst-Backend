# Turnpike Analyst — Enterprise System Architecture & Design

> **Single source tree, three production repositories.**  
> `turnpike-frontend` (Public Website & Intern Portal) · `turnpike-admin` (Super Admin & Operations Console) · `turnpike-backend` (FastAPI + MongoDB API) · `packages/shared` (Shared Design System & API Client)

This document is the complete **A-to-Z system architecture** for the Turnpike Analyst platform. It maps every user-facing route on the public website, every role-gated screen in the admin and super-admin console, the internal 4-layer backend execution model, the dual-source (GitHub + `.zip` archive) AI verification pipeline, certificate rendering, security boundaries, data schemas, and technology stack choices.

---

## Table of Contents

1. [System Context](#1-system-context)
2. [Container & Deployment Topology](#2-container--deployment-topology)
3. [Monorepo & Multi-Repo Publishing Structure](#3-monorepo--multi-repo-publishing-structure)
4. [User Access — Public Website (`turnpike-frontend`)](#4-user-access--public-website-turnpike-frontend)
5. [Admin & Super Admin Access (`turnpike-admin`)](#5-admin--super-admin-access-turnpike-admin)
6. [Backend Architecture (`turnpike-backend`)](#6-backend-architecture-turnpike-backend)
7. [Request Lifecycle & Token Refresh](#7-request-lifecycle--token-refresh)
8. [Authentication & Authorisation](#8-authentication--authorisation)
9. [Super Administrator Lifecycle](#9-super-administrator-lifecycle)
10. [Internship Programme & Dual-Source Verification](#10-internship-programme--dual-source-verification)
11. [AI Provider Fallback Chain](#11-ai-provider-fallback-chain)
12. [Grounded Support Assistant](#12-grounded-support-assistant)
13. [Certificate Rendering & Public Verification](#13-certificate-rendering--public-verification)
14. [File Storage & Upload Security](#14-file-storage--upload-security)
15. [Data Model & MongoDB Collections](#15-data-model--mongodb-collections)
16. [Complete API Surface](#16-complete-api-surface)
17. [Frontend & Admin UI Architecture](#17-frontend--admin-ui-architecture)
18. [Security Model](#18-security-model)
19. [Failure Modes & Resilience](#19-failure-modes--resilience)
20. [Complete Technology Stack](#20-complete-technology-stack)
21. [Operations & Extending the System](#21-operations--extending-the-system)

---

## 1. System Context

```mermaid
graph TB
    subgraph Actors["Platform Actors"]
        VIS["Visitor<br/>Browses consultancy, blogs, training, submits enquiries"]
        INT["Intern (CLIENT)<br/>Google sign-in, builds project, submits repo + zip, earns certificate"]
        CON["Consultant / Instructor<br/>Views assigned revenue & training surfaces"]
        ADM["Administrator (ADMIN)<br/>Reviews dossiers, watches demo videos, approves certificates, trains assistant"]
        SUP["Super Administrator<br/>First ADMIN bootstrap owner; rotates credentials & manages admin roles"]
        EMP["Employer / Verifier<br/>Verifies certificate authenticity via public URL"]
    end

    SYS["<b>Turnpike Analyst Platform</b><br/>turnpike-frontend · turnpike-admin · turnpike-backend"]

    subgraph External["External & Managed Services"]
        ATLAS[("MongoDB Atlas<br/>28+ collections")]
        CLOUD[("Cloudinary<br/>Public PDFs + Authenticated archives")]
        FIRE["Firebase Auth<br/>Google OAuth ID tokens"]
        GITHUB["GitHub REST API<br/>Reads submitted public repos"]
        AI["LLM Provider Chain<br/>OpenRouter · Groq · OpenAI · Gemini · Anthropic"]
    end

    VIS --> SYS
    INT --> SYS
    CON --> SYS
    ADM --> SYS
    SUP --> SYS
    EMP -->|"GET /verify/{number}"| SYS

    SYS --> ATLAS
    SYS --> CLOUD
    SYS --> FIRE
    SYS --> GITHUB
    SYS --> AI
```

| Core Capability | Primary Users | Outcome |
|---|---|---|
| **Enterprise Consultancy Showcase** | Visitors, Prospects | Explore 15+ service domains, industries, JAMES WEBB & Agent P8 solutions, training courses, and capture leads/calls |
| **Free Verified Internship Programme** | Interns, Admins, Employers | End-to-end project enrollment (1–3 months), dossier + `.zip` + GitHub repo verification, AI claim checks, human demo audit, PDF certificate |
| **Grounded Support Assistant** | Visitors, Interns, Admins | Knowledge-base-grounded Q&A widget with unanswered question backlog for continuous admin training |

---

## 2. Container & Deployment Topology

```mermaid
graph TB
    subgraph Vercel["Vercel (Edge + Serverless SSR)"]
        FE["<b>Turnpike Frontend</b><br/>turnpike-frontend/<br/>TanStack Start · React 19 · Nitro<br/>SSR Marketing + Client Intern Dashboard"]
        AD["<b>Turnpike Admin</b><br/>turnpike-admin/<br/>TanStack Start · React 19 · Nitro<br/>Client-Rendered Role-Gated Console (noindex, DENY)"]
    end

    subgraph Render["Render (Managed Python Web Service)"]
        API["<b>Turnpike Backend</b><br/>turnpike-backend/<br/>FastAPI · Python 3.12 · Uvicorn<br/>Async REST API + Background AI Worker"]
    end

    subgraph Managed["Managed Infrastructure"]
        DB[("<b>MongoDB Atlas</b><br/>Motor Async Driver")]
        CL[("<b>Cloudinary</b><br/>CDN + Authenticated Raw/Image Storage")]
        FB["<b>Firebase Auth</b><br/>Project: turnpikeanalyst-ff936"]
        GH["<b>GitHub REST API</b><br/>Tree, Manifests, Commits, Source Samples"]
        LLM["<b>Multi-LLM Chain</b><br/>OpenRouter · Groq · OpenAI · Gemini · Anthropic"]
    end

    FE -->|"HTTPS · Bearer JWT"| API
    AD -->|"HTTPS · Bearer JWT"| API
    FE -.->|"Google Sign-In Popup"| FB
    API -->|"verify_id_token()"| FB
    API --> DB
    API --> CL
    API -->|"BackgroundTask"| GH
    API -->|"BackgroundTask / Chat"| LLM
```

### Architectural Rationale
- **One API service, not microservices:** The internship review pipeline, certificate renderer, CMS, and support assistant share MongoDB collections, auth guards, and the LLM provider chain. A single FastAPI service eliminates distributed deployment drift while staying async.
- **Two separate frontend apps (`turnpike-frontend` & `turnpike-admin`):** The public site requires crawlable SSR (`X-Frame-Options: SAMEORIGIN`), while the admin console requires strict client-only rendering (`ssr: false`), `X-Robots-Tag: noindex, nofollow`, and `X-Frame-Options: DENY`. Keeping them separate guarantees admin console code never ships in the public bundle.

---

## 3. Monorepo & Multi-Repo Publishing Structure

The monorepo is the **single source of truth**. `scripts/publish-repos.sh` stages each deployable into its dedicated public GitHub repository, attaches shared packages and architecture docs, scans every file for leaked credentials, and pushes cleanly.

```mermaid
graph LR
    MONO["<b>Monorepo: turnpike-analyst</b><br/>turnpike-frontend/ · turnpike-admin/<br/>turnpike-backend/ · packages/shared/"]
    SCRIPT["<b>scripts/publish-repos.sh</b><br/>1. Stage files & shared workspace<br/>2. Generate root package.json & README<br/>3. Secret scan (refuses keys/URIs)<br/>4. Push to GitHub main"]

    MONO --> SCRIPT
    SCRIPT --> R1["<b>TurnpikeAnalyst-Frontend</b><br/>turnpike-frontend/ + packages/shared/<br/>Vercel Root: turnpike-frontend"]
    SCRIPT --> R2["<b>TurnpikeAnalyst-Adminpanel</b><br/>turnpike-admin/ + packages/shared/<br/>Vercel Root: turnpike-admin"]
    SCRIPT --> R3["<b>TurnpikeAnalyst-Backend</b><br/>turnpike-backend/ flattened to root<br/>Render Root: ."]
```

```
turnpike-analyst/
├── turnpike-frontend/                  # Public website + Intern portal (Vercel)
│   ├── src/
│   │   ├── routes/
│   │   │   ├── __root.tsx              # Document shell, theme, query provider
│   │   │   ├── _site.tsx               # SiteHeader, SiteFooter, FloatingActions, SupportChat
│   │   │   └── _site/                  # 22 public & intern routes
│   │   ├── components/
│   │   │   ├── site/                   # Navigation, Hero, Services, SupportChat, WaveDivider
│   │   │   ├── internship/             # DossierForm (4 steps + .zip), SubmissionSummary, GoogleButton
│   │   │   └── shared/                 # BookCallDialog
│   │   ├── content/                    # Static service/product/training marketing data
│   │   ├── server.ts · start.ts · router.tsx
│   │   ├── styles.css                  # Tailwind v4 entry (@source self + shared)
│   │   └── vercel.json                 # Nitro Vercel preset build & headers
│   └── README.md
│
├── turnpike-admin/                     # Super Admin & Operations Console (Vercel)
│   ├── src/
│   │   ├── routes/
│   │   │   ├── __root.tsx              # Admin HTML shell
│   │   │   ├── index.tsx               # Redirects / -> /admin
│   │   │   ├── login.tsx               # Staff email/password login
│   │   │   ├── admin.tsx               # Role gate (ADMIN check) + DashboardLayout
│   │   │   └── admin/                  # 27 console pages
│   │   ├── components/layout/          # AppSidebar, AppTopbar, DashboardLayout
│   │   ├── features/                   # Domain CRUD modal dialogs
│   │   ├── constants/navigation.ts     # Role-filtered sidebar & route titles
│   │   ├── server.ts · start.ts · router.tsx
│   │   ├── styles.css
│   │   └── vercel.json                 # X-Frame-Options: DENY, noindex
│   └── README.md
│
├── packages/shared/                    # Workspace package: @turnpike/shared
│   └── src/
│       ├── components/ui/              # 47 Radix-based UI primitives
│       ├── components/premium/         # PageHeader, DataTable, MermaidDiagram, States
│       ├── components/effects/         # AuroraBackground, CustomCursor, ScrollEffects
│       ├── api/
│       │   ├── client.ts               # Axios instance, Bearer injection, 401 refresh interceptor
│       │   └── services/               # 14 domain API clients
│       ├── hooks/                      # use-auth · use-api · use-internship · use-public-api · use-prefs
│       ├── lib/                        # firebase.ts · security-headers.ts · error-capture.ts
│       ├── store/auth-store.ts         # Zustand persisted session (turnpike.auth.v1)
│       ├── types/                      # TypeScript mirrors of backend Pydantic schemas
│       └── styles/tokens.css           # Light/dark oklch design system
│
├── turnpike-backend/                   # Enterprise FastAPI + MongoDB API (Render)
│   ├── app/
│   │   ├── main.py                     # App, lifespan, 12 index builders, 15 routers, /uploads
│   │   ├── core/                       # config.py (Pydantic Settings), security.py (JWT/bcrypt)
│   │   ├── api/
│   │   │   ├── deps.py                 # get_current_user, _active_user, _admin, require_roles
│   │   │   └── v1/                     # 15 FastAPI domain routers
│   │   ├── schemas/                    # Pydantic v2 request/response contracts
│   │   ├── crud/                       # Pure Motor async MongoDB operations
│   │   ├── services/                   # llm.py, ai_review.py, github_repo.py, source_archive.py,
│   │   │                               # certificate_render.py, storage.py
│   │   ├── models/enums.py             # UserRole, InternshipStatus, EnrollmentMode, etc.
│   │   └── db/mongodb.py               # AsyncIOMotorClient lifecycle
│   ├── scripts/                        # seed_data, seed_internship, seed_chatbot, migrate_database
│   ├── requirements.txt
│   └── README.md
│
├── scripts/publish-repos.sh            # Monorepo -> 3 GitHub deployment repos
├── render.yaml                         # Render blueprint
├── ARCHITECTURE.md                     # This system design document
├── DEPLOYMENT.md                       # Production deployment runbook
└── README.md                           # Monorepo overview
```

---

## 4. User Access — Public Website (`turnpike-frontend`)

### What Visitors & Interns See (22 Routes under `_site/`)

```mermaid
flowchart TB
    ROOT["Public Site (_site Layout)<br/>Sticky SiteHeader · AuroraBackground · SiteFooter · SupportChat Widget"]

    subgraph Public["Unauthenticated Visitor Access"]
        HOME["/ — Home<br/>Hero, Stats, Services Explorer, Tech Stack, Featured Blogs"]
        SRV["/services & /services/:slug<br/>15+ Enterprise Service Categories & Sub-Services"]
        IND["/industries/:slug<br/>Banking, Healthcare, Insurance, Govt, Manufacturing"]
        SW["/software-support<br/>Managed Support & SLAs"]
        TRN["/training & /training/:slug<br/>ECM, OpenShift, Cloud DevOps & AI/ML Courses"]
        BLG["/blog, /blog/:slug, /blog-posts, /blog-posts/:slug<br/>Articles & Technical Insights"]
        CMP["/about · /our-clients · /career · /faq · /contact<br/>Company Info, Client Showcase, Enquiries, Book Call"]
        VER["/verify/:certificateNumber<br/>Public Third-Party Certificate Verification"]
        BOT["Floating Support Assistant<br/>Grounded AI Chat (20 msgs / 5 min / IP)"]
    end

    subgraph Intern["Authenticated Intern Access (Google Sign-In -> CLIENT Role)"]
        INT["/internship<br/>Programme Overview & Published Project Briefs"]
        TRK["/internship/:slug<br/>Brief Details, Requirements & 1 / 2 / 3 Month Selector"]
        PRP["/internship/propose<br/>Propose Custom Project (Title, Summary, Duration)"]
        DSH["/internship/dashboard<br/>Active Enrollments, Deadlines, Status Badges & Certificates"]
        WRK["/internship/dashboard/:enrollmentId<br/>4-Step Dossier Form, .zip Archive Upload, AI Q&A & PDF Download"]
    end

    ROOT --> Public
    ROOT --> Intern
```

### Complete Website Route Inventory (`turnpike-frontend/src/routes/_site/`)

| Route | Access | Purpose |
|---|---|---|
| `/` | Public | Landing page, services explorer, proprietary tools, stats, blogs |
| `/services` & `/services/$slug` | Public | Enterprise service catalogue & individual service details |
| `/industries/$slug` | Public | Industry-specific solutions & client groupings |
| `/software-support` | Public | Managed enterprise software support offerings |
| `/training` & `/training/$slug` | Public | Training courses & curriculum details |
| `/blog`, `/blog/$slug`, `/blog-posts`, `/blog-posts/$slug` | Public | Blog catalogue & article reader |
| `/about`, `/our-clients`, `/career`, `/faq`, `/contact` | Public | Company profile, global partners, careers, FAQs, contact & call booking |
| `/verify/$certificateNumber` | Public | Instant certificate validity check for employers (no login required) |
| `/internship` | Public | Internship programme landing & available project tracks |
| `/internship/$slug` | Public / Google Auth | Project brief detail + duration selection (`1`, `2`, `3` months) + enroll |
| `/internship/propose` | Google Auth (`CLIENT`) | Custom project proposal + duration selection + enroll |
| `/internship/dashboard` | Google Auth (`CLIENT`) | Intern personal dashboard listing enrollments & issued certificates |
| `/internship/dashboard/$enrollmentId` | Google Auth (Owner) | 4-step dossier submission, `.zip` upload, follow-up Q&A, status polling, PDF download |

---

## 5. Admin & Super Admin Access (`turnpike-admin`)

### Role Gate & Console Architecture (27 Routes under `/admin`)

Every `/admin/*` page sits behind `admin.tsx` (`ssr: false`). Unauthenticated visitors redirect to `/login`; authenticated non-admin accounts (`CLIENT`) see an explicit access explanation and sign-out button before any admin API call is made; `ADMIN` (including Super Admin), `CONSULTANT`, and `INSTRUCTOR` see only the sidebar sections matching their role.

```mermaid
flowchart TB
    LOGIN["/login<br/>Email + Password (POST /api/v1/auth/login)"] --> HYD{"Session Hydrated<br/>& Authenticated?"}
    HYD -->|No| LOGIN
    HYD -->|Yes| ROLE{"user.role == ADMIN?"}
    ROLE -->|"No (e.g. CLIENT)"| DENY["Access Denied Screen<br/>'This console is for administrators' + Sign Out"]
    ROLE -->|Yes| SHELL["DashboardLayout<br/>AppSidebar + AppTopbar + Role-Filtered Nav"]

    subgraph Console["27 Admin & Super Admin Pages"]
        OV["Overview<br/>/admin (Dashboard) · /admin/system-health"]
        RV["Revenue (ADMIN, CONSULTANT)<br/>/admin/leads · /admin/book-calls · /admin/demo-requests"]
        CT["Catalog<br/>/admin/services · /admin/digital-content · /admin/industries<br/>/admin/courses · /admin/instructor-applications"]
        IN["Internship & AI (ADMIN only)<br/>/admin/internship-tracks · /admin/internship-submissions<br/>/admin/certificate-templates · /admin/chatbot"]
        CN["Content & CMS<br/>/admin/blogs · /admin/faqs · /admin/careers · /admin/clients<br/>/admin/clients/:industryName · /admin/newsletter · /admin/cms"]
        AD["Administration (Super Admin / ADMIN)<br/>/admin/users · /admin/activity · /admin/security<br/>/admin/profile · /admin/settings · /admin/notifications"]
    end

    SHELL --> Console
```

### Role & Permission Matrix

| Console Section / Surface | Super Admin / `ADMIN` | `CONSULTANT` | `INSTRUCTOR` | `CLIENT` (Intern) |
|---|---|---|---|---|
| **Dashboard & Profile / Settings** | Full Access | Read / Own | Read / Own | Blocked at Gate |
| **System Health (`/admin/system-health`)** | Full Access | Hidden | Hidden | Blocked |
| **Leads, Book Calls, Demo Requests** | Full CRUD | View & Update | Hidden | Blocked |
| **Services, Digital Content, Industries, Courses** | Full CRUD | Full CRUD | Full CRUD | Blocked |
| **Instructor Applications** | Full Access | Full Access | Full Access | Blocked |
| **Internship Tracks, Submissions, Decisions & Certificates** | Full Access | Hidden | Hidden | Blocked |
| **Support Assistant Knowledge, Unanswered & Behaviour** | Full Access | Hidden | Hidden | Blocked |
| **User Management & Role Elevation (`/admin/users`)** | Full CRUD | Hidden | Hidden | Blocked |
| **Activity Logs (`/admin/activity`)** | Full Audit | Hidden | Hidden | Blocked |
| **Sign-in & Security (`/admin/security`)** | Own Credentials | Hidden | Hidden | Blocked |

---

## 6. Backend Architecture (`turnpike-backend`)

### Four-Layer Dependency Rule

```mermaid
graph TB
    subgraph L1["Layer 1 — Routers (app/api/v1/)"]
        R["HTTP Concerns Only<br/>Route matching · Status codes · FastAPI Depends() · Response shaping"]
    end
    subgraph L2["Layer 2 — Schemas (app/schemas/)"]
        S["The API Contract (Pydantic v2)<br/>Edge validation · Field constraints · Outbound field filtering"]
    end
    subgraph L3["Layer 3 — Services (app/services/)"]
        SV["Pure Domain Logic (No HTTPException / Request)<br/>llm · ai_review · github_repo · source_archive<br/>certificate_render · storage"]
    end
    subgraph L4["Layer 4 — CRUD (app/crud/)"]
        C["Exclusive MongoDB Access Layer<br/>12+ modules · Index builders · Async Motor queries"]
    end
    DB[("MongoDB Atlas")]

    R --> S
    R --> SV
    R --> C
    SV --> C
    C --> DB
```

- **Strict Database Boundary:** Only `app/crud/` imports or executes Motor queries, guaranteeing collection names and indexes stay centralized.
- **HTTP-Free Services:** `app/services/*` raise domain exceptions (`ReviewUnavailable`, `RepoAccessError`, `ArchiveError`, `StorageError`, `CertificateRenderError`), allowing identical execution inside HTTP requests and detached `BackgroundTasks`.

### Startup Lifespan Sequence (`app/main.py`)

```mermaid
sequenceDiagram
    participant P as Uvicorn Process
    participant CFG as Settings (config.py)
    participant DB as MongoDB Atlas
    participant FS as Filesystem / Firebase
    participant ADM as Users Collection

    P->>CFG: Load env / .env settings
    P->>CFG: Warn if SECRET_KEY is default dev key
    P->>DB: db_client.connect_db()
    loop 12 Isolated Index Builders
        P->>DB: ensure_*_indexes(db)
        Note over P,DB: Failures log warning without blocking boot
    end
    P->>FS: Write FIREBASE_CREDENTIALS_JSON to disk if set
    P->>FS: Initialize firebase_admin (optional)
    P->>ADM: _seed_super_admin(db) — ONLY if zero ADMIN exists
    P->>DB: expire_overdue_enrollments(db)
    P-->>P: Ready — Serving traffic on /api/v1/*
```

---

## 7. Request Lifecycle & Token Refresh

### Authenticated Admin Request Lifecycle

```mermaid
sequenceDiagram
    participant B as Admin Browser
    participant CORS as CORSMiddleware
    participant R as FastAPI Router
    participant D as deps.get_current_admin
    participant P as Pydantic v2
    participant S as Service Layer
    participant C as CRUD Layer
    participant DB as MongoDB Atlas

    B->>CORS: POST /api/v1/internship/admin/... + Bearer JWT
    CORS->>CORS: Validate Origin against CORS_ORIGINS
    CORS-->>B: 400/CORS block if unlisted
    CORS->>R: Dispatch route
    R->>D: Decode HS256 JWT (type == "access")
    D->>C: get_user_by_id / get_user_by_email
    C->>DB: users.find_one()
    D->>D: Verify is_active == True & role == "ADMIN"
    D-->>R: Current Admin or 401/403
    R->>P: Validate request JSON / multipart payload
    P-->>B: 422 Validation Error if invalid
    R->>S: Execute domain logic
    S->>C: Persist / read domain records
    C->>DB: Async Motor operation
    S-->>R: Domain result or domain error
    R->>P: Filter output via response_model
    P-->>B: 200 OK (only declared schema fields)
```

### Shared Axios Silent JWT Refresh Loop (`packages/shared/src/api/client.ts`)

```mermaid
sequenceDiagram
    participant UI as React Component
    participant AX as apiClient (Axios)
    participant API as Turnpike Backend
    participant ST as Zustand auth-store

    UI->>AX: API call
    AX->>AX: Inject Authorization: Bearer access_token
    AX->>API: Send request
    API-->>AX: 401 Unauthorized
    AX->>AX: Check _retry flag
    AX->>API: POST /api/v1/auth/refresh-token
    alt Refresh succeeds
        API-->>AX: New access_token + refresh_token
        AX->>ST: Persist new tokens (turnpike.auth.v1)
        AX->>API: Retry original request once
        API-->>UI: 200 OK
    else Refresh fails
        AX->>ST: Clear auth-store
        AX->>UI: Redirect via setUnauthorizedRedirect() (/login in admin, / in site)
    end
```

---

## 8. Authentication & Authorisation

```mermaid
graph TB
    subgraph Staff["Staff & Admin Sign-In (Password)"]
        L1["POST /api/v1/auth/login<br/>OAuth2PasswordRequestForm"] --> L2["Verify bcrypt password hash"]
    end

    subgraph Intern["Intern Sign-In (Google via Firebase)"]
        G1["Browser: Firebase signInWithPopup()"] --> G2["Firebase ID Token"]
        G2 --> G3["POST /api/v1/auth/google"]
        G3 --> G4["firebase_admin.auth.verify_id_token()"]
        G4 --> G5{"email_verified == true?"}
        G5 -->|No| G6["403 Forbidden"]
        G5 -->|Yes| G7["Find or auto-create User (role = CLIENT)"]
    end

    subgraph Reg["Public Registration"]
        R1["POST /api/v1/auth/register"] --> R2["Forces role = CLIENT (ignores caller role)"]
    end

    L2 --> JWT["Issue HS256 Access JWT (30 min)<br/>+ Refresh JWT (7 days)"]
    G7 --> JWT
    JWT --> STORE["Persisted Zustand Store (turnpike.auth.v1)"]
```

---

## 9. Super Administrator Lifecycle

```mermaid
flowchart TB
    BOOT["Backend Startup"] --> ENV{"SUPER_ADMIN_EMAIL &<br/>SUPER_ADMIN_PASSWORD set?"}
    ENV -->|No| SKIP["Skip bootstrap"]
    ENV -->|Yes| CHECK{"Does ANY user in DB<br/>have role == ADMIN?"}
    CHECK -->|Yes| IGNORE["Log ignored — never overwrites<br/>live admin credentials"]
    CHECK -->|No| CREATE["Create initial Super Admin (role = ADMIN)<br/>Log warning to change password"]
```

### Changing Super Admin Credentials (`/admin/security` -> `POST /api/v1/account/credentials`)

```mermaid
sequenceDiagram
    actor SA as Super Administrator
    participant UI as /admin/security
    participant API as POST /api/v1/account/credentials
    participant DB as MongoDB users

    SA->>UI: Enter current_password + new_email / new_password (min 10 chars) / full_name
    UI->>API: Send authenticated request (get_current_admin)
    API->>API: verify_password(current_password, stored_hash)
    alt Incorrect current password
        API-->>UI: 403 "Current password is incorrect."
    else Verified
        API->>DB: Check new_email uniqueness (409 if taken)
        API->>DB: Update email / bcrypt hash / full_name
        API-->>UI: 200 Updated UserResponse
        UI->>UI: Sign out immediately to force re-login with new credentials
    end
```

---

## 10. Internship Programme & Dual-Source Verification

### Enrollment Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> ENROLLED: Enroll in Track or Own Project<br/>(1, 2, or 3 calendar months)
    ENROLLED --> EXPIRED: Build deadline passes with no submission
    ENROLLED --> AI_REVIEWING: 4-step dossier + .zip archive submitted
    AI_REVIEWING --> QUESTIONS_PENDING: Repo + .zip analyzed, claim checks & questions saved
    AI_REVIEWING --> REVIEW_FAILED: Repo unreachable or all LLM providers failed
    REVIEW_FAILED --> AI_REVIEWING: Intern updates dossier / resubmits
    REVIEW_FAILED --> UNDER_REVIEW: Admin picks up manually
    QUESTIONS_PENDING --> UNDER_REVIEW: Intern submits follow-up answers (SLA clock starts)
    UNDER_REVIEW --> APPROVED: Admin verifies demo video + approves
    UNDER_REVIEW --> REJECTED: Admin declines with feedback
    APPROVED --> [*]: Certificate PDF rendered & issued
    REJECTED --> [*]
```

### 4-Step Dossier + Mandatory `.zip` Archive & Dual-Source AI Review

Every intern submission combines **public GitHub code** with a **direct `.zip` source archive upload** (`source_archive.py`), preventing empty-repo fraud or bait-and-switch links:

```mermaid
sequenceDiagram
    actor I as Intern
    participant FE as DossierForm (4 Steps)
    participant API as /api/v1/internship
    participant ZIP as source_archive.py
    participant CL as Cloudinary (Private Raw)
    participant BG as BackgroundTask
    participant GH as GitHub REST API
    participant LLM as AI Provider Chain
    participant DB as MongoDB

    Note over FE: Step 1: Links & Demo Video · Step 2: Write-up · Step 3: Mermaid/Image Diagrams
    I->>FE: Step 4 — Upload project .zip (max 60 MB)
    FE->>API: POST .../source-archive
    API->>ZIP: digest_archive() in-memory ONLY
    Note over ZIP: Zip-slip check (no .. / absolute paths)<br/>Zip-bomb check (<=400MB, <=12k files, <=200:1 ratio)
    ZIP-->>API: Validated ArchiveSnapshot
    API->>CL: store(private=True, resource_type="raw")
    API-->>FE: SourceArchiveMeta + download_url

    I->>FE: Submit full dossier
    FE->>API: POST .../submit (verifies source_archive exists)
    API->>DB: Save submission, status = AI_REVIEWING
    API-->>I: 200 OK immediately (UI polls every few seconds)

    BG->>GH: Fetch repo tree, manifests, 12 source files, commits, contributors
    BG->>CL: Fetch & digest uploaded .zip in memory
    BG->>LLM: Prompt 1 — Compare GitHub Snapshot + .zip Archive + Dossier -> REVIEW_SCHEMA
    LLM-->>BG: score · strengths · concerns · claim_checks (supported/partial/unsupported)
    BG->>LLM: Prompt 2 — Generate project-specific questions -> QUESTIONS_SCHEMA
    LLM-->>BG: N follow-up questions anchored in real files
    BG->>DB: Save ai_review + questions, status = QUESTIONS_PENDING
```

### Admin Review & Human Demo Verification (`turnpike-admin`)

```mermaid
flowchart LR
    Q["Submissions Queue<br/>Default: 'Needs a decision' (UNDER_REVIEW)"] --> INSP["Inspect Submission<br/>Dossier · Mermaid/Images · GitHub Repo"]
    INSP --> ARCH["Download .zip Source Archive<br/>GET .../source-archive"]
    INSP --> AI["Inspect Admin-Only AI Report<br/>Score · Findings · Claim Checks"]
    INSP --> QA["Read Intern's Follow-Up Answers"]
    ARCH & AI & QA --> VID["Watch Intern's Local Demo Recording"]
    VID --> CHK["Tick 'I watched the demo recording'<br/>(demo_verified = true required by API)"]
    CHK --> DEC{"Decision"}
    DEC -->|Approve| CERT["Render Certificate PDF -> Upload to Cloudinary -> Issue TA-YYYY-XXXXXXXXXX"]
    DEC -->|Decline| REJ["Store rejection notes -> Visible to intern"]
```

---

## 11. AI Provider Fallback Chain

```mermaid
flowchart LR
    REQ["LLM Request + Optional JSON Schema"] --> P1{"1. OpenRouter<br/>(openrouter/free)"}
    P1 -->|Success| OK["Parsed JSON + Provider Name"]
    P1 -->|"429 / 5xx / Timeout"| P2{"2. Groq"}
    P2 -->|Success| OK
    P2 -->|Fails| P3{"3. OpenAI"}
    P3 -->|Success| OK
    P3 -->|Fails| P4{"4. Gemini<br/>(generateContent)"}
    P4 -->|Success| OK
    P4 -->|Fails| P5{"5. Anthropic<br/>(Messages API)"}
    P5 -->|Success| OK
    P5 -->|Fails| ERR["AllProvidersFailed<br/>-> Status: REVIEW_FAILED (never lost)"]
```

- **Configured Chains:**
  - `AI_REVIEW_PROVIDERS=openrouter,groq,openai,gemini,anthropic`
  - `CHATBOT_PROVIDERS=groq,openrouter,openai` (Gemini omitted from live chat due to 230–290s free-tier latency)
- **Reasoning Model Token Floor:** Responses apply a minimum 1024-token budget so reasoning models do not exhaust tokens before producing JSON.
- **Silent Key Pruning:** Any provider without an API key configured is skipped automatically.

---

## 12. Grounded Support Assistant

```mermaid
flowchart TB
    MSG["Visitor / Intern Question"] --> RL{"Rate Limiter<br/>20 msgs / 5 min / client IP"}
    RL -->|Exceeded| R429["429 Too Many Requests"]
    RL -->|Allowed| SEARCH["MongoDB Weighted Text Search<br/>question ×10 · keywords ×6 · answer ×2"]
    SEARCH --> SCORE{"Score >= Relevance Threshold?"}
    SCORE -->|Yes| CTX["Attach Matching Knowledge Entries"]
    SCORE -->|No| NH["needs_human = true<br/>(Queued in Admin -> Unanswered)"]
    CTX & NH --> PROMPT["Strict Server System Prompt<br/>'Answer ONLY from reference material; never invent prices/URLs/policies'"]
    PROMPT --> CHAIN["Groq -> OpenRouter -> OpenAI"]
    CHAIN -->|All Fail| FALL["Return Configured Fallback Message"]
    CHAIN -->|Success| LOG["Save Turn to chatbot_conversations"]
    LOG --> REPLY["Return Assistant Reply"]
```

---

## 13. Certificate Rendering & Public Verification

```mermaid
sequenceDiagram
    actor A as Administrator
    participant AD as /admin/certificate-templates
    participant API as Turnpike Backend
    participant PIL as Pillow Renderer
    participant CL as Cloudinary
    participant DB as MongoDB

    rect rgb(38, 46, 56)
        Note over A,DB: Template Setup (Once per Design)
        A->>AD: Upload background artwork (PNG/JPEG/WebP)
        AD->>API: POST /api/v1/internship/admin/templates
        API->>CL: Store public artwork + measure width/height
        A->>AD: Drag fields (recipient_name, project_title, duration, issued_on, certificate_number)
        API->>DB: Save field coordinates, fonts, colors & max_width
    end

    rect rgb(38, 46, 56)
        Note over A,DB: Certificate Issuance (Per Approval)
        A->>API: POST .../decide (decision=APPROVED, demo_verified=true)
        API->>DB: Load active certificate template
        API->>CL: Fetch background artwork
        API->>PIL: Stamp dynamic fields (auto-shrink long names to fit max_width)
        API->>PIL: Generate PDF bytes + ID TA-YYYY-10CHARS (no O/0/I/1)
        API->>CL: Store public PDF (raw)
        API->>DB: Insert certificates record + link enrollment
    end
```

Employers verify any certificate without signing in at `/verify/<certificateNumber>` -> `GET /api/v1/internship/certificates/verify/{certificate_number}`.

---

## 14. File Storage & Upload Security

```mermaid
graph TB
    subgraph Public["Public Assets (CDN URLs)"]
        C1["Issued Certificate PDFs"]
        C2["Certificate Template Backgrounds"]
    end
    subgraph Private["Private Authenticated Assets (Ownership Checked)"]
        P1["Intern Architecture / Data-Flow Images<br/>Decoded & re-encoded via Pillow (strips payloads)"]
        P2["Intern .zip Source Archives<br/>Validated in-memory for zip-slip & zip-bombs"]
    end

    SVC["services/storage.py<br/>store() · fetch()"]
    C1 & C2 --> SVC
    P1 & P2 --> SVC
    SVC -->|"Production"| CL[("Cloudinary<br/>Public + Authenticated Types")]
    SVC -.->|"Local Dev Fallback"| FS[("uploads/ & private_uploads/")]
```

---

## 15. Data Model & MongoDB Collections

```mermaid
erDiagram
    users ||--o{ internship_enrollments : enrolls
    users ||--o{ certificates : earns
    users ||--o{ internship_attachments : uploads
    internship_tracks ||--o{ internship_enrollments : optional_brief
    internship_enrollments ||--o| certificates : issues
    internship_enrollments ||--o{ internship_attachments : diagrams
    certificate_templates ||--o{ certificates : renders
    chatbot_knowledge ||--o{ chatbot_conversations : grounds

    users {
        ObjectId _id PK
        string email UK
        string hashed_password
        string role "ADMIN | CONSULTANT | INSTRUCTOR | CLIENT"
        bool is_active
        string theme
    }
    internship_tracks {
        string slug UK
        string category
        string level
        string brief
        array requirements
        int build_days
        bool is_published
    }
    internship_enrollments {
        string user_id
        string mode "TRACK | OWN"
        int duration_months
        string project_title
        string status
        date deadline_at
        object source_archive "zip metadata"
        object submission "dossier"
        object ai_review "admin only"
        array questions
        object decision
        string certificate_id
    }
    certificates {
        string certificate_number UK
        string enrollment_id UK
        string recipient_name
        string track_title
        string pdf_url
        bool revoked
    }
    chatbot_knowledge {
        string question
        string answer
        string topic
        array keywords
    }
```

### Key Collections & Indexes

| Domain | Collections | Critical Indexes |
|---|---|---|
| **Identity & Audit** | `users`, `activity_logs` | Unique `users.email` |
| **Consultancy & Content** | `services`, `industries`, `products`, `blogs`, `blogs_and_articles`, `faqs`, `courses_and_training`, `consultants`, `cms_assets`, `stats`, `awards`, `testimonials` | Unique slugs & category keys |
| **Revenue Capture** | `leads`, `appointments_and_leads`, `newsletters` | Status & created_at sorting |
| **Internship & Certificates** | `internship_tracks`, `internship_enrollments`, `internship_attachments`, `internship_settings`, `certificate_templates`, `certificates` | Partial unique `(user_id, track_id)` where `track_id` is string; unique `certificate_number`; unique `enrollment_id` |
| **Support Assistant** | `chatbot_knowledge`, `chatbot_conversations`, `chatbot_settings` | Weighted text index (`question: 10`, `keywords: 6`, `answer: 2`) |

---

## 16. Complete API Surface

Interactive OpenAPI & ReDoc documentation is served at `/docs` and `/redoc`.

| Router Prefix | Auth Guard | Responsibilities |
|---|---|---|
| `/api/v1/auth` | Public / Refresh | `POST /register` (forces `CLIENT`), `/login`, `/google`, `/refresh-token` |
| `/api/v1/account` | `get_current_admin` | `GET /me`, `POST /credentials` (current-password verified rotation) |
| `/api/v1/services` | Public / Admin | 15+ enterprise service categories, sub-services & proprietary tools |
| `/api/v1/content` | Public / Admin | Industries, products, stats, awards, testimonials, FAQs |
| `/api/v1/blogs` | Public / Admin | Blog posts & technical articles |
| `/api/v1/training` | Public / Admin | Training courses & instructor applications |
| `/api/v1/leads` | Public / Staff | Contact enquiries, book-a-call, demo requests |
| `/api/v1/newsletter` | Public / Admin | Newsletter subscriptions |
| `/api/v1/consultants` | Public / Admin | Consultant profiles & scheduling |
| `/api/v1/cms` | Public / Admin | CMS media assets & digital content |
| `/api/v1/users` | `ADMIN` | User listing, creation, role grants/revokes, deletion |
| `/api/v1/activity-logs` | `ADMIN` | Administrative audit trail |
| `/api/v1/internship` | Public / `CLIENT` | Public tracks, enroll, dossier submit, `.zip` upload/download, diagram attachments, Q&A, `/certificates/verify/{n}` |
| `/api/v1/internship/admin` | `ADMIN` | Settings, track CRUD, submission queue, AI reports, approve/decline, certificate templates & preview |
| `/api/v1/chatbot` | Public / `ADMIN` | Public `/chat` & `/settings`, admin knowledge CRUD, unanswered backlog, persona settings |

---

## 17. Frontend & Admin UI Architecture

```mermaid
graph TB
    subgraph FE["turnpike-frontend (SSR + Client)"]
        F_ROOT["__root.tsx — Head, Fonts, QueryClient, Toaster"]
        F_SITE["_site.tsx — Header, Footer, SupportChat, FloatingActions"]
        F_PAGES["22 Routes (Marketing SSR + Intern Dashboard ssr:false)"]
        F_ROOT --> F_SITE --> F_PAGES
    end

    subgraph AD["turnpike-admin (Client-Rendered Console)"]
        A_ROOT["__root.tsx — noindex, frame-denied"]
        A_GATE["admin.tsx — Role Gate (ADMIN check)"]
        A_SHELL["DashboardLayout — Sidebar, Topbar"]
        A_PAGES["27 Console Routes (ssr: false)"]
        A_ROOT --> A_GATE --> A_SHELL --> A_PAGES
    end

    SH["packages/shared (@turnpike/shared)<br/>47 Radix UI Primitives · Axios Client · Zustand Auth<br/>TanStack Query Hooks · oklch Design Tokens"]

    SH -.-> F_SITE
    SH -.-> A_SHELL
```

---

## 18. Security Model

| Threat / Vector | Implemented Control |
|---|---|
| **Privilege Escalation on Register** | `/auth/register` and `/auth/google` hardcode `role = CLIENT` regardless of payload |
| **Unverified Google Email** | `firebase_admin.auth.verify_id_token` enforces `email_verified == true` |
| **Admin Console Access by Non-Admin** | `admin.tsx` blocks non-`ADMIN` before rendering; backend enforces `get_current_admin` on all admin endpoints |
| **Bootstrap Backdoor** | `SUPER_ADMIN_*` seeding runs only when zero `ADMIN` accounts exist in MongoDB |
| **Unattended Console Hijack** | `/account/credentials` requires `current_password` verification |
| **Zip-Bomb / Zip-Slip Uploads** | `source_archive.py` validates paths (`..`, absolute, drive letters) and metadata limits (60 MB / 400 MB / 12k files / 200:1 ratio) purely in memory without writing to disk |
| **Stored XSS via Diagrams** | Only PNG/JPEG/WebP allowed (SVG rejected); Pillow decodes & re-encodes pixels; served only via auth-checked route with `nosniff` + CSP |
| **ID Enumeration** | Non-owned intern records & attachments return `404` instead of `403` |
| **Certificate Enumeration** | 10-char look-alike-free random token (`TA-YYYY-XXXXXXXXXX`) |
| **Secret Leakage in Repos** | `.env` & service accounts gitignored; `publish-repos.sh` aborts on credential patterns |

---

## 19. Failure Modes & Resilience

| Failure Scenario | System Behaviour |
|---|---|
| **Single LLM provider fails / 429s** | Automatically falls through to next provider in chain |
| **All LLM providers fail** | Enrollment parks safely in `REVIEW_FAILED` with stored diagnostic; admin can review manually or intern can resubmit |
| **Private / broken GitHub repo** | Marked `REVIEW_FAILED` with actionable message to intern |
| **Cloudinary outage** | Upload fails fast with `502`; no dangling MongoDB metadata written |
| **Firebase credentials absent** | Only `/auth/google` returns `503`; staff login, CMS, and public site remain online |
| **MongoDB unreachable at boot** | Index builders log warnings individually; server still boots |
| **Approval without active template** | API returns `409 Conflict` explaining an active template is required |

---

## 20. Complete Technology Stack

| Layer | `turnpike-frontend` & `turnpike-admin` | `packages/shared` | `turnpike-backend` |
|---|---|---|---|
| **Core Runtime & Language** | TypeScript 5.8 · React 19.2 · Bun 1.4+ | TypeScript 5.8 · React 19.2 | Python 3.12 · FastAPI 0.110+ · Uvicorn |
| **Routing & SSR** | TanStack Start · TanStack Router · Nitro (`vercel` preset) | TanStack Router types | FastAPI APIRouter (`/api/v1`) |
| **Build Tooling** | Vite 8 · `vite-tsconfig-paths` · ESLint · Prettier | Workspace source alias (`@turnpike/shared`) | `pip` + `requirements.txt` |
| **Styling & Design System** | Tailwind CSS v4 · `@tailwindcss/typography` · `tw-animate-css` | `oklch` CSS variables (light & dark) · `tailwind-merge` · `class-variance-authority` | — |
| **UI, Icons & Animation** | Lucide React · Motion (`motion`) · Recharts (Admin analytics) | 47 Radix UI primitives (`shadcn`) · GSAP · Lenis · `cmdk` · `vaul` · `embla-carousel-react` · `sonner` | — |
| **Diagrams & Rich Content** | `mermaid` 12.3 · `react-markdown` · `rehype-raw` | `MermaidDiagram` renderer | Mermaid source validation & AI parsing |
| **State & Validation** | TanStack React Query v5 · React Hook Form · Zod 3.24 | Axios (`apiClient`) · Zustand v5 (persisted auth) | Pydantic v2 · `pydantic-settings` · `email-validator` |
| **Database & Storage** | — | — | MongoDB Atlas · Motor (async) · Cloudinary · Pillow (image/PDF) |
| **Auth & Security** | Firebase Web SDK v12 (`signInWithPopup`) | Shared `firebase.ts` & `security-headers.ts` | `python-jose` (JWT HS256) · `passlib[bcrypt]` · `firebase-admin` |
| **AI & External APIs** | — | — | `httpx` async client -> OpenRouter, Groq, OpenAI, Gemini, Anthropic, GitHub REST |

---

## 21. Operations & Extending the System

### Local Development

```bash
# 1. Start Turnpike Backend (port 8000)
cd turnpike-backend
python -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env
./.venv/bin/uvicorn app.main:app --reload --port 8000

# 2. Start Turnpike Frontend (:3000) and Turnpike Admin (:3001) from monorepo root
bun install
bun run dev:frontend
bun run dev:admin
```

### Publishing to the Three GitHub Repositories

```bash
./scripts/publish-repos.sh --dry-run          # Stage & secret-scan locally
./scripts/publish-repos.sh                    # Push all 3 repos
./scripts/publish-repos.sh turnpike-backend   # Push a single target
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for Vercel, Render, MongoDB Atlas, Cloudinary, and Firebase production setup.
