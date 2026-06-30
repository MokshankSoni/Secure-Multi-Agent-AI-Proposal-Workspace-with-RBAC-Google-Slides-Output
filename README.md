# Secure Multi-Agent AI Proposal Workspace

> **Backend system combining a LangGraph multi-agent pipeline with a multi-tenant RBAC layer using Supabase. The Drafting Agent produces a real Google Slides presentation via the Google Slides API. The shareable link is stored in the session record and returned in the API response.**

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Setup Steps](#2-setup-steps)
3. [Environment Variables](#3-environment-variables)
4. [Google Credentials Setup](#4-google-credentials-setup)
5. [How to Run](#5-how-to-run)
6. [Database Setup](#6-database-setup)
7. [Schema Design Decisions](#7-schema-design-decisions)
8. [Intake Agent — Structured Output Fields & Justification](#8-intake-agent--structured-output-fields--justification)
9. [API Reference — Curl Examples for All 5 Endpoints](#9-api-reference--curl-examples-for-all-5-endpoints)
10. [Terminal Output — Full Pipeline Run with Retry](#10-terminal-output--full-pipeline-run-with-retry)
11. [Known Gaps & Partial Items](#11-known-gaps--partial-items)

---

## 1. Architecture Overview

```
POST /api/sessions/{id}/generate
          |
          v
  AuthMiddleware (JWT -> request.state.auth)
          |
          v
  SessionService.generate_session()
          |
          +-> Supabase: Load session, verify ownership
          |
          +-> Build LangGraph initial_state
          |     { tenant_id, user_id, user_role, raw_input, ... }
          |
          v
  LangGraph Pipeline (GRAPH.invoke)
    |
    +-- intake_node        <- Raw text -> ProposalData (structured)
    +-- drafting_node      <- ProposalData -> SlideData[] + Google Slides
    +-- review_node        <- Score presentation quality
    +-- route_after_review <- Conditional edge (pass / retry / fail)
    |
    +-- [RETRY PATH]
    |     retry_node       <- Delete failed slide from Drive, increment counter
    |     +-> drafting_node (loops with failure_reason in prompt)
    |
    +-- [PASS PATH] finalize_node -> status = 'approved'
    +-- [FAIL PATH]  fail_node   -> status = 'failed'
          |
          v
  SessionService: Write slides_url, slides_file_id, status -> Supabase
          |
          v
  GenerateResponse { session_id, status, slides_url, final_response }
```

### Tech Stack

| Layer | Technology |
|---|---|
| Web Framework | FastAPI |
| Pipeline Orchestration | LangGraph |
| LLM Provider | Groq (configurable via env) |
| Presentation Generation | Google Slides API + Drive API |
| Auth & Storage | Supabase (PostgreSQL + GoTrue Auth) |
| Auth Strategy | Supabase JWT validated in middleware |

---

## 2. Setup Steps

### Prerequisites
- Python 3.12+
- A Supabase project (free tier works)
- A Google Cloud project with Slides and Drive APIs enabled
- A Groq API key (or any supported LLM provider)

### Step 1 — Clone the Repository
```bash
git clone <your-repo-url>
cd "Smart AI Proposal"
```

### Step 2 — Create a Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Configure Environment Variables
```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Then fill in every value in `.env`. See Section 3 for a full description of each variable.

---

## 3. Environment Variables

Copy `.env.example` to `.env` and populate every field before starting the server.

| Variable | Required | Description | Where to Get It |
|---|---|---|---|
| `SUPABASE_URL` | YES | Your Supabase project REST URL | Supabase Dashboard -> Project Settings -> API -> Project URL |
| `SUPABASE_ANON_KEY` | YES | Supabase anonymous/public key. Used for Auth calls (sign-up, login). | Supabase Dashboard -> Project Settings -> API -> anon public |
| `SUPABASE_SERVICE_ROLE_KEY` | YES | Supabase service role key. Bypasses RLS for server-side operations. Never expose to client. | Supabase Dashboard -> Project Settings -> API -> service_role |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | NOT USED | Not used in the current implementation. OAuth 2.0 credentials are used instead (see Section 4 and Section 11). Would be required if switching to Service Account auth in future. | Google Cloud Console -> IAM -> Service Accounts |
| `LLM_API_KEY` | YES | API key for your LLM provider. The project uses Groq by default -- set GROQ_API_KEY or LLM_API_KEY. | console.groq.com |
| `LLM_MODEL` | YES | The model identifier to use. | Groq: llama-3.3-70b-versatile recommended |
| `LLM_PROVIDER` | NO | Optional label for the LLM provider. | e.g. groq |
| `LOG_LEVEL` | NO | Python logging level. Defaults to INFO. | DEBUG, INFO, WARNING, ERROR |

### Example `.env`
```
SUPABASE_URL=https://xyzxyzxyz.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...

# GOOGLE_SERVICE_ACCOUNT_JSON is not used in the current implementation.
# The project uses OAuth 2.0 credentials stored in credentials/token.json instead.
# See Section 4 (Google Credentials Setup) and Section 11 (Known Gaps) for full details.
# GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"my-project",...}

GROQ_API_KEY=gsk_...
LLM_MODEL=llama-3.3-70b-versatile

LOG_LEVEL=INFO
```

> **Security Note:** The `.env` file is listed in `.gitignore` and will never be committed to the repository.

---

## 4. Google Credentials Setup

The project authenticates with the Google Slides and Drive APIs using **OAuth 2.0 (Installed App / Desktop flow)** with credentials cached in `credentials/token.json`.

### Step 1 — Create a Google Cloud Project
1. Go to https://console.cloud.google.com
2. Click **Select a project** -> **New Project**
3. Give it a name (e.g. `ai-proposal-workspace`) and click **Create**

### Step 2 — Enable the Required APIs
1. In the left sidebar, go to **APIs & Services -> Library**
2. Search for and enable:
   - **Google Slides API**
   - **Google Drive API**

### Step 3 — Create OAuth 2.0 Credentials
1. Go to **APIs & Services -> Credentials**
2. Click **+ Create Credentials -> OAuth client ID**
3. If prompted, configure the OAuth consent screen first:
   - User type: **External**
   - Fill in app name, support email, developer email
   - Add scopes: `../auth/presentations` and `../auth/drive`
   - Add your own email as a **test user**
4. Back in Create credentials -> Application type: **Desktop app**
5. Click **Create** and download the JSON file
6. Rename it to `client_secret.json` and place it at `credentials/client_secret.json`

### Step 4 — Generate the Token (First Run)
On first run, the `GoogleSlidesService` will detect that no `credentials/token.json` exists and open a browser window for you to authorize access.

```bash
uvicorn main:app --reload
```

After you authorize in the browser, the token is saved to `credentials/token.json` and all future runs use it automatically without a browser prompt.

> **Note:** The `credentials/` directory is listed in `.gitignore` and is never committed to the repository.

---

## 5. How to Run

### Start the Development Server
```bash
uvicorn main:app --reload --port 8000
```

### Expected Startup Logs
```
INFO:     Started server process [XXXXX]
INFO:     Waiting for application startup.
INFO:app.database.supabase:Supabase clients initialized successfully.
INFO:app.graph.builder:LangGraph pipeline compiled successfully.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Verify the Server is Running
```bash
curl http://localhost:8000/health
```
Expected: `{"status": "healthy", "service": "Smart AI Proposal API", "version": "0.1.0"}`

### Swagger UI
Interactive API documentation is available at:
```
http://localhost:8000/docs
```
This endpoint is public and requires no authentication token.

---

## 6. Database Setup

### Step 1 — Apply the Schema
1. Open your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Paste the entire contents of `schema.sql` and click **Run**
4. Verify no errors appear in the output

The schema creates:
- `organizations` table
- `users` table (application profile, linked to `auth.users`)
- `sessions` table (pipeline state and results)
- All indexes, the `updated_at` trigger, and all RLS policies

### Step 2 — Disable Email Confirmation (Recommended for Testing)
By default, Supabase requires email confirmation before a user can log in. For local development:
1. Go to **Authentication -> Providers -> Email**
2. Turn **OFF** "Confirm email"

### Step 3 — Seed Test Organizations
Organizations must be created before any user can sign up. Run this in the Supabase SQL Editor:
```sql
INSERT INTO organizations (name) VALUES ('Org Alpha') RETURNING id, name;
INSERT INTO organizations (name) VALUES ('Org Beta')  RETURNING id, name;
```
**Copy the UUIDs returned** — you will need them in signup requests.

### Step 4 — Increase Rate Limits (Recommended for Testing)
Supabase free tier limits signups to ~3 per hour from the same IP. For testing:
1. Go to **Authentication -> Rate Limits**
2. Increase the email/signup rate limits for your development session.

---

## 7. Schema Design Decisions

### `sessions.owner_id` vs `user_id`
We use `owner_id` (not `user_id`) to make the semantic ownership intent explicit. A session is "owned" by the user who created it; `owner_id` communicates this at a glance without ambiguity.

### `sessions.status` — Enum via CHECK Constraint
The valid status values are: `pending -> drafting -> reviewing -> approved | failed`

We chose a `CHECK` constraint over a PostgreSQL `ENUM` type because:
- `CHECK` constraints can be modified without a table rewrite
- Values are self-documenting in the `schema.sql` file
- No migration step needed to add a new status

### `sessions.final_response` Column
Stores the human-readable final output from the pipeline (Review Agent's feedback text or the failure reason). This gives the API a rich response payload without requiring a separate table join. Nullable because it is only populated after the pipeline completes.

### Service Role Key for Pipeline Write-back
All pipeline write-backs (setting `slides_url`, `slides_file_id`, `status`) use the **service role key**, which bypasses RLS. This is intentional: the write-back is a system operation initiated by the server, not by the end user. Using the service role key prevents RLS from blocking the update while maintaining the guarantee that user-scoped clients cannot write arbitrary data.

### No `email` Column in `public.users`
The application profile table (`public.users`) does not store email. Email is owned by Supabase Auth (`auth.users`) and is always authoritative there. Duplicating it would create a consistency risk. The middleware retrieves email directly from the JWT claim.

### `organizations_select_authenticated` Policy
Any authenticated user can read from the `organizations` table. This is required for the signup flow to validate that the `organization_id` in the request actually exists. No `INSERT` or `DELETE` policies exist for authenticated users — org management is a privileged service-role operation only.

---

## 8. Intake Agent — Structured Output Fields & Justification

The Intake Agent converts raw user text into a `ProposalData` Pydantic model. This structured output is what the Drafting Agent receives to generate slides.

### Field Decisions

| Field | Type | Required | Justification |
|---|---|---|---|
| `client_name` | `str` | YES | The client name is the most important anchor of a proposal. All slides reference it. |
| `project_title` | `str` | YES | Used as the presentation title and first slide heading. Extracted separately from `client_name` because many users specify both. |
| `problem_statement` | `str` | YES | The core of any proposal deck. The Review Agent explicitly scores it. Without it, the LLM cannot generate a coherent Problem slide. |
| `objectives` | `list[str]` | YES | Structured as a list (not a prose block) so it maps directly to bullet points on an Objectives slide without further parsing. |
| `proposed_solution` | `str` | YES | Distinct from objectives — this is the *what we will build*, not the *why*. Separation produces cleaner slide content. |
| `deliverables` | `list[str]` | YES | Also a list for the same reason as objectives — maps cleanly to a Deliverables slide. |
| `timeline` | `str` | YES | Essential for any proposal. Kept as a string because users express it in many formats ("4 months", "Q3 2026") and structured date parsing would introduce fragility. |
| `budget_range` | `Optional[str]` | NO | Optional because some RFP inputs genuinely do not specify a budget. Nullable avoids forcing the LLM to hallucinate a number. |
| `target_industry` | `Optional[str]` | NO | Used to inform slide tone and vocabulary. Optional because it can be inferred from `client_name` in the drafting prompt when absent. |
| `tone` | `Optional[str]` | NO | Allows the client to specify "formal", "friendly", "executive", etc. If absent, the Drafting Agent defaults to professional. |
| `team_members` | `Optional[list[str]]` | NO | Some proposals include a Team slide. If the input mentions no team, the slide is simply omitted. |
| `unique_value_prop` | `Optional[str]` | NO | Powers the "Why Us" or closing slide. Optional because not all inputs contain this information explicitly. |

### Why Not a Free-Form String?
The Drafting Agent needs to populate **individual slides** (Problem slide, Objectives slide, Budget slide). If the intake output were a single prose block, the drafting LLM would need to re-parse prose, introducing a second point of LLM failure. The structured `ProposalData` model ensures each slide has exactly the input it needs.

---

## 9. API Reference — Curl Examples for All 5 Endpoints

All protected endpoints require:
```
Authorization: Bearer <access_token>
```
Replace `<access_token>` with the token returned by `POST /api/auth/login`.

---

### POST /api/auth/signup

Creates a new user account and attaches them to an existing organization.

```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "securepassword123",
    "organization_id": "f0872910-45c7-4a83-81c9-382244c0f67e",
    "role": "admin"
  }'
```

**201 Created**
```json
{"message": "User created successfully."}
```

| Error Code | Detail |
|---|---|
| 400 | "Organization does not exist." |
| 400 | "Email already exists." |
| 422 | Validation error (invalid role, password too short, bad email) |

---

### POST /api/auth/login

Authenticates a user and returns JWT tokens.

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "securepassword123"
  }'
```

**200 OK**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "v1.XXXX...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user_id": "41fa3ebd-5770-48fa-a521-9c7bfc47b68a"
}
```

| Error Code | Detail |
|---|---|
| 400 | "Invalid credentials." |

---

### POST /api/sessions

Creates a new proposal session (does not run the pipeline).

```bash
curl -X POST http://localhost:8000/api/sessions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "title": "Hospital AI Chatbot Proposal",
    "raw_input": "We are ABC Hospital. We want an AI chatbot to help patients book appointments and answer FAQs. Budget $50,000. Timeline 4 months."
  }'
```

**201 Created**
```json
{
  "session_id": "295869d4-998a-46ff-a102-d3e566cee530",
  "status": "pending"
}
```

---

### GET /api/sessions

Returns all sessions the caller is authorized to see.
- **Members** see only sessions they own
- **Admins** see all sessions within their organization (cross-org access blocked by RLS)

```bash
curl http://localhost:8000/api/sessions/ \
  -H "Authorization: Bearer <access_token>"
```

**200 OK**
```json
[
  {
    "session_id": "295869d4-998a-46ff-a102-d3e566cee530",
    "title": "Hospital AI Chatbot Proposal",
    "status": "approved",
    "slides_url": "https://docs.google.com/presentation/d/1BxiMVs.../edit?usp=sharing",
    "created_at": "2026-06-30T18:25:14Z"
  },
  {
    "session_id": "01238156-d1d6-43e1-917b-cfca058fee8c",
    "title": "EdTech Platform Proposal",
    "status": "pending",
    "slides_url": null,
    "created_at": "2026-06-30T19:00:00Z"
  }
]
```

> `slides_url` is `null` for sessions that have not yet been generated.

---

### POST /api/sessions/{id}/generate

Runs the full LangGraph pipeline for the given session and returns the Google Slides URL.

> This endpoint is synchronous and will take 30-120 seconds.

**Access Rules:**
- A `member` can only generate their own sessions
- An `admin` can generate any session within their organization
- Neither can generate sessions from a different organization

```bash
curl -X POST http://localhost:8000/api/sessions/295869d4-998a-46ff-a102-d3e566cee530/generate \
  -H "Authorization: Bearer <access_token>"
```

**200 OK**
```json
{
  "session_id": "295869d4-998a-46ff-a102-d3e566cee530",
  "status": "approved",
  "slides_url": "https://docs.google.com/presentation/d/1BxiMVs.../edit?usp=sharing",
  "final_response": "Proposal approved successfully. Google Slides available at: https://docs.google.com/..."
}
```

| Error Code | Detail |
|---|---|
| 401 | Missing or invalid Authorization header |
| 403 | "Access denied: you do not own this session." |
| 403 | "Access denied: session belongs to a different organization." |
| 404 | "Session not found." |
| 500 | "Pipeline failed: ..." |

---

## 10. Terminal Output — Full Pipeline Run with Retry

The following is **real captured output** from a complete pipeline run (passed on first attempt).

> **Live Slides URL:** https://docs.google.com/presentation/d/1jbqDDgColdnSXFKlgl13sZl5M0tR0wmsBYX5V0EVSCE/edit?usp=sharing

```
INFO:     127.0.0.1:54028 - "POST /api/sessions/ HTTP/1.1" 201 Created
INFO:httpx:HTTP Request: GET https://uuwgsoyvqwokxuiegece.supabase.co/auth/v1/user "HTTP/2 200 OK"
INFO:httpx:HTTP Request: GET https://uuwgsoyvqwokxuiegece.supabase.co/rest/v1/users?select=organization_id%2Crole&id=eq.b9ec6578-a1fc-4f3d-8f65-de919aa7f028 "HTTP/2 200 OK"
INFO:app.middleware.auth_middleware:Authentication successful for user_id=b9ec6578-a1fc-4f3d-8f65-de919aa7f028 role=admin org=aef36c60-72c9-465b-99f5-70cc169f8eb3.
INFO:httpx:HTTP Request: GET https://uuwgsoyvqwokxuiegece.supabase.co/rest/v1/sessions?select=%2A&id=eq.9fbe76d5-b332-4077-a97f-8f8314236f52 "HTTP/2 200 OK"
INFO:httpx:HTTP Request: PATCH https://uuwgsoyvqwokxuiegece.supabase.co/rest/v1/sessions?id=eq.9fbe76d5-b332-4077-a97f-8f8314236f52 "HTTP/2 200 OK"
INFO:app.services.session_service:Session generation started: id=9fbe76d5-b332-4077-a97f-8f8314236f52 user=b9ec6578-a1fc-4f3d-8f65-de919aa7f028 role=admin

INFO:app.agents.intake_agent:Intake node started.
INFO:app.agents.intake_agent:Intake prompt generated.
INFO:app.services.llm_service:LLMService initialized with Groq model: llama-3.3-70b-versatile
INFO:app.services.llm_service:Generating structured output using model 'llama-3.3-70b-versatile' for schema 'ProposalData'.
INFO:httpx:HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
INFO:app.services.llm_service:Successfully generated structured output for schema 'ProposalData'.
INFO:app.agents.intake_agent:Proposal extracted successfully.

INFO:app.agents.drafting_agent:Drafting node started.
INFO:app.agents.drafting_agent:Drafting prompt generated.
INFO:app.services.llm_service:LLMService initialized with Groq model: llama-3.3-70b-versatile
INFO:app.services.llm_service:Generating structured output using model 'llama-3.3-70b-versatile' for schema 'SlidesResponse'.
INFO:httpx:HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
INFO:app.services.llm_service:Successfully generated structured output for schema 'SlidesResponse'.
INFO:app.agents.drafting_agent:Slides generated successfully. Total slides: 9
INFO:app.services.google_service:Loaded cached OAuth token from credentials/token.json.
INFO:app.services.google_service:GoogleSlidesService authenticated successfully.
INFO:app.services.google_service:Presentation created. ID: 1jbqDDgColdnSXFKlgl13sZl5M0tR0wmsBYX5V0EVSCE
INFO:app.services.google_service:Slide 1/9 populated: title_id=None body_id=SLIDES_API1675776793_1
INFO:app.services.google_service:Slide 2/9 populated: title_id=SLIDES_API248604643_0 body_id=SLIDES_API248604643_1
INFO:app.services.google_service:Slide 3/9 populated: title_id=SLIDES_API1593047385_0 body_id=SLIDES_API1593047385_1
INFO:app.services.google_service:Slide 4/9 populated: title_id=SLIDES_API1108573446_0 body_id=SLIDES_API1108573446_1
INFO:app.services.google_service:Slide 5/9 populated: title_id=SLIDES_API331291476_0 body_id=SLIDES_API331291476_1
INFO:app.services.google_service:Slide 6/9 populated: title_id=SLIDES_API249452718_0 body_id=SLIDES_API249452718_1
INFO:app.services.google_service:Slide 7/9 populated: title_id=SLIDES_API293054177_0 body_id=SLIDES_API293054177_1
INFO:app.services.google_service:Slide 8/9 populated: title_id=SLIDES_API1580454388_0 body_id=SLIDES_API1580454388_1
INFO:app.services.google_service:Slide 9/9 populated: title_id=SLIDES_API100138251_0 body_id=SLIDES_API100138251_1
INFO:app.services.google_service:Deleted 1 default slide(s).
INFO:app.services.google_service:Populated presentation '1jbqDDgColdnSXFKlgl13sZl5M0tR0wmsBYX5V0EVSCE' with 9 slides.
INFO:app.services.google_service:Presentation '1jbqDDgColdnSXFKlgl13sZl5M0tR0wmsBYX5V0EVSCE' shared publicly. URL: https://docs.google.com/presentation/d/1jbqDDgColdnSXFKlgl13sZl5M0tR0wmsBYX5V0EVSCE/edit?usp=sharing
INFO:app.agents.drafting_agent:Presentation created and shared. URL: https://docs.google.com/presentation/d/1jbqDDgColdnSXFKlgl13sZl5M0tR0wmsBYX5V0EVSCE/edit?usp=sharing

INFO:app.agents.review_agent:Review node started.
INFO:app.agents.review_agent:Review prompt generated.
INFO:app.services.llm_service:LLMService initialized with Groq model: llama-3.3-70b-versatile
INFO:app.services.llm_service:Generating structured output using model 'llama-3.3-70b-versatile' for schema 'ReviewResult'.
INFO:httpx:HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
INFO:app.services.llm_service:Successfully generated structured output for schema 'ReviewResult'.
INFO:app.agents.review_agent:Review completed successfully. Passed: True, Composite Avg: 8.50

INFO:app.graph.terminal_nodes:Finalization successful. Presentation URL: https://docs.google.com/presentation/d/1jbqDDgColdnSXFKlgl13sZl5M0tR0wmsBYX5V0EVSCE/edit?usp=sharing

INFO:app.services.session_service:Pipeline completed for session 9fbe76d5-b332-4077-a97f-8f8314236f52: final_status=approved slides_url=https://docs.google.com/presentation/d/1jbqDDgColdnSXFKlgl13sZl5M0tR0wmsBYX5V0EVSCE/edit?usp=sharing
INFO:httpx:HTTP Request: PATCH https://uuwgsoyvqwokxuiegece.supabase.co/rest/v1/sessions?id=eq.9fbe76d5-b332-4077-a97f-8f8314236f52 "HTTP/2 200 OK"
INFO:app.services.session_service:Database update completed for session 9fbe76d5-b332-4077-a97f-8f8314236f52.
INFO:     127.0.0.1:54043 - "POST /api/sessions/9fbe76d5-b332-4077-a97f-8f8314236f52/generate HTTP/1.1" 200 OK
```

> **Note on retry demonstration:** To observe the retry loop, uncomment lines 57-62 in `app/agents/review_agent.py` (the forced failure block), trigger a generate call, then re-comment it. The logs will show: review `Passed: False` -> retry node deletes the first presentation -> drafting node runs again -> review `Passed: True` -> finalize.

---

## 11. Known Gaps & Partial Items

### Google Slides Authentication

The Google Slides integration is currently implemented using **OAuth 2.0 Installed Application credentials**, with access tokens cached locally in `credentials/token.json` after the initial browser-based authorization.

#### Current Functionality

- Create Google Slides presentations
- Populate presentation content
- Share presentations publicly
- Delete presentations during retry/failure handling

The complete Google Slides workflow is **fully functional** and has been tested end-to-end.

#### Design Decision

The original implementation was developed using Google Service Account authentication, as recommended in the assessment specification. During implementation, multiple attempts were made to use Service Accounts across different Google Cloud projects, service accounts, and credential configurations.

Despite enabling the required Google Slides and Google Drive APIs and verifying IAM permissions, the Google Slides API consistently returned **HTTP 403 - Permission Denied** when attempting to create presentations. The issue appeared to be related to Google Workspace/Drive permission restrictions rather than the application logic itself.

To ensure a fully functional submission, the authentication mechanism was migrated to **OAuth 2.0 Installed Application credentials** (Client ID & Client Secret), which is also permitted by the assessment specification:

> "Client ID and secrets can also be used if not using a Service Account."

This change resolved the authentication issue while leaving the remainder of the Google Slides integration unchanged.

#### Future Improvement

For a production deployment where Service Account permissions are fully configured, the authentication layer can be switched to:

```python
google.oauth2.service_account.Credentials.from_service_account_info(...)
```

loading credentials from the `GOOGLE_SERVICE_ACCOUNT_JSON` environment variable.

This change affects **only** the authentication mechanism. The presentation creation, population, sharing, retry, and deletion logic would remain exactly the same.

---

### Pipeline is Synchronous
`POST /sessions/{id}/generate` runs the full pipeline synchronously. The HTTP request will block for 30-120 seconds. For production this should be moved to a background task queue. This is acceptable for an assessment submission.
