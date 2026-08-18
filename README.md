# Multi-language Code Compiler & Evaluation Platform — Backend

> **Project #10** — Dr. Dhawaleswar Rao, SoET/CSE  
> A HackerRank-style competitive coding platform for academic and competitive programming contexts.

---

## Problem Statement

Manual code evaluation in academic settings is time-consuming and prone to bias. There is a lack of platforms that can handle multiple programming languages securely and efficiently. This project builds an automated, secure, and scalable system where admins post coding challenges and students solve them in a browser-based editor — with real-time output, hidden test case judging, and a live leaderboard.

---

## What This Repo Is

This is the **backend API** for the platform. It handles:

- User authentication (JWT, role-based: admin vs student)
- Question management (create, publish, hide test cases)
- Code execution via a self-hosted Piston engine (Python, C++, Java, JavaScript)
- Submission judging against hidden test cases with scoring
- Global and per-question leaderboards

The companion frontend repo (`code-compiler-frontend`) is a React + Vite + Monaco Editor app that consumes this API.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        FRONTEND                          │
│   ┌──────────────────┐       ┌────────────────────────┐  │
│   │  Admin Dashboard  │       │     Student Portal     │  │
│   │  - Add questions  │       │  - Playground          │  │
│   │  - Edit questions │       │  - Question list       │  │
│   │  - View all subs  │       │  - Code editor         │  │
│   └──────────────────┘       │  - Run / Submit        │  │
│                               │  - Leaderboard         │  │
│                               └────────────────────────┘  │
└───────────────────────────┬─────────────────────────────┘
                            │ REST API + JWT
┌───────────────────────────▼─────────────────────────────┐
│                     FASTAPI BACKEND                      │
│   /auth  /playground  /questions  /submissions  /rankings │
└──────┬───────────────────────────────────────┬──────────┘
       │                                       │
  ┌────▼──────┐                       ┌────────▼────────┐
  │  SQLite DB │                       │  Piston Engine  │
  │  users     │                       │  (Docker)       │
  │  questions │                       │  Python / C++   │
  │  submissions│                      │  Java / Node.js │
  └────────────┘                       └─────────────────┘
```

---

## Two Modes

```
PLAYGROUND MODE                   CONTEST MODE
────────────────────────          ──────────────────────────────
Route: /playground                Route: /questions/:id
Free editor, any code             Problem statement shown
Custom stdin input                Sample I/O provided
Run only — no score               Run (sample) + Submit (all tests)
Nothing saved to DB               Submission saved + scored
No test cases                     Hidden test cases judged
No ranking impact                 Affects leaderboard
```

Both modes share the same Piston execution engine.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI (Python 3.11) |
| Database | SQLite via SQLAlchemy 2.x |
| Auth | JWT HS256 via python-jose |
| Password hashing | bcrypt |
| Code execution | Piston (self-hosted via Docker) |
| HTTP client | httpx (async) |
| Config | pydantic-settings (reads `.env`) |
| Container | Docker Compose |
| Tests | pytest (94 tests) |

---

## User Roles

| Role | Capabilities |
|---|---|
| **Admin** | Login, use playground, create/edit questions with hidden test cases, view all submissions |
| **Student** | Register/login, use playground, view published questions, run and submit solutions, view leaderboard |

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS, Linux, or Windows)
- `git`

### 1. Clone the repo

```bash
git clone <repo-url>
cd code-compiler-backend
```

### 2. Create `.env`

```env
SECRET_KEY=change-me-in-production
ADMIN_EMAIL=admin@platform.com
ADMIN_PASSWORD=admin123
PISTON_URL=http://localhost:2000
DATABASE_URL=sqlite:///./app.db
```

> The admin account is automatically seeded from `ADMIN_EMAIL` and `ADMIN_PASSWORD` on first startup.

### 3. Start all services

```bash
docker compose up -d
```

This starts two containers:

| Container | Port | Role |
|---|---|---|
| `piston` | 2000 | Code execution engine |
| `fastapi` | 8000 | REST API (hot-reload enabled) |

### 4. Wait for runtimes (first run only)

On first run, the Piston container automatically downloads and installs the required language runtimes. This takes **2–5 minutes**. Watch progress:

```bash
docker logs piston -f
```

You will see:
```
Piston API ready
  [ok] python already installed
  [+]  Installing gcc-10.2.0 ...
  [+]  Installing java-15.0.2 ...
  ...
All runtimes ready.
```

On every subsequent `docker compose up`, runtimes are already cached in the `piston_data` Docker volume and load instantly.

### 5. Verify

```bash
# Interactive API docs
open http://localhost:8000/docs

# Quick smoke test
curl -s -X POST http://localhost:8000/playground/run \
  -H "Content-Type: application/json" \
  -d '{"language":"python","code":"print(\"hello world\")","stdin":""}' 
# -> {"stdout":"hello world\n","status":"accepted","execution_time_ms":730,...}
```

---

## Supported Languages

| Input alias | Piston runtime | Notes |
|---|---|---|
| `python`, `python3`, `py` | python 3.12.0 | |
| `javascript`, `js`, `node` | javascript 18.15.0 | Node.js |
| `java` | java 15.0.2 | JVM startup adds ~3–4s per run |
| `cpp`, `c++`, `c` | gcc 10.2.0 | Compiled with g++ |
| `go` | go 1.16.2 | |
| `rust` | rust 1.68.2 | |

---

## API Reference

All protected endpoints require:
```
Authorization: Bearer <token>
```

---

### Auth

#### `POST /auth/register`
Register a new student account.

**Request**
```json
{ "name": "Alice", "email": "alice@example.com", "password": "secret123" }
```
**Response `201`**
```json
{ "id": 1, "name": "Alice", "email": "alice@example.com", "role": "student" }
```

---

#### `POST /auth/login`
Obtain a JWT access token. Works for both students and admins.

**Request**
```json
{ "email": "alice@example.com", "password": "secret123" }
```
**Response `200`**
```json
{ "access_token": "<jwt>", "token_type": "bearer", "role": "student" }
```

> Tokens expire after **24 hours**. Store in `localStorage` on the frontend and attach as `Authorization: Bearer <token>` on every request.

---

### Playground

#### `POST /playground/run`
Execute code freely. No authentication required. Nothing is saved.

**Request**
```json
{
  "language": "python",
  "code": "name = input()\nprint(f'Hello, {name}!')",
  "stdin": "Alice"
}
```
**Response `200`**
```json
{
  "stdout": "Hello, Alice!\n",
  "stderr": "",
  "execution_time_ms": 730,
  "status": "accepted"
}
```

**Status values:** `accepted` | `runtime_error` | `time_limit_exceeded`

---

### Questions

#### `GET /questions`
List all published questions. If authenticated, includes an `is_solved` flag per question.

**Response `200`**
```json
[
  {
    "id": 1,
    "title": "Two Sum",
    "difficulty": "easy",
    "description": "Given an array of integers...",
    "constraints": "1 ≤ n ≤ 1000",
    "sample_input": "4\n2 7 11 15\n9",
    "sample_output": "0 1",
    "created_at": "2026-08-18T10:00:00",
    "is_solved": false
  }
]
```

> `is_solved` only appears when the request includes a valid auth token.  
> `difficulty` is one of: `easy`, `medium`, `hard`.

---

#### `GET /questions/{question_id}`
Get full details of a single published question. **Test cases are never exposed** to students.

---

### Submissions — requires auth

#### `POST /submissions/run`
Run your code against the question's **sample input** only. Does not record a submission or affect the leaderboard.

**Request**
```json
{ "question_id": 1, "language": "python", "code": "print(input())" }
```
**Response `200`** — same shape as `/playground/run`

---

#### `POST /submissions/submit`
Judge code against **all hidden test cases**. Scores the result and records it to the database.

**Request**
```json
{ "question_id": 1, "language": "java", "code": "..." }
```
**Response `201`**
```json
{
  "id": 42,
  "question_id": 1,
  "language": "java",
  "status": "accepted",
  "score": 100.0,
  "passed_cases": 5,
  "total_cases": 5,
  "execution_time_ms": 3200,
  "submitted_at": "2026-08-18T19:00:00"
}
```

**Scoring**

| Verdict | Condition | Score |
|---|---|---|
| Accepted | All test cases pass | 100 |
| Partial | Some test cases pass | (passed / total) × 100 |
| Wrong Answer | Output mismatch | proportional |
| Time Limit Exceeded | Execution > timeout | 0 |
| Runtime Error | Crash or compile error | 0 |

Output comparison uses **trimmed whitespace matching** — `actual.strip() == expected.strip()` — so trailing newlines and spaces never cause false Wrong Answers.

---

#### `GET /submissions/my`
List the authenticated user's full submission history across all questions.

**Response `200`**
```json
[
  {
    "id": 42,
    "question_id": 1,
    "question_title": "Two Sum",
    "language": "java",
    "status": "accepted",
    "score": 100.0,
    "submitted_at": "2026-08-18T19:00:00"
  }
]
```

---

### Rankings — no auth required

#### `GET /rankings`
Global leaderboard. Ranked by `total_score` descending, then `solved_count` descending. Only the **best submission per question per student** counts.

**Response `200`**
```json
[
  { "rank": 1, "user_id": 3, "name": "Alice", "total_score": 300.0, "solved_count": 3 },
  { "rank": 2, "user_id": 7, "name": "Bob",   "total_score": 150.0, "solved_count": 1 }
]
```

---

#### `GET /rankings/{question_id}`
Per-question leaderboard. Ranked by `best_score` descending, then `execution_time_ms` ascending (faster wins on ties).

**Response `200`**
```json
[
  { "rank": 1, "user_id": 7, "name": "Bob",   "best_score": 100.0, "execution_time_ms": 120 },
  { "rank": 2, "user_id": 3, "name": "Alice", "best_score": 100.0, "execution_time_ms": 450 }
]
```

---

### Admin — requires admin role

Use the default admin credentials to log in (set in `.env`):

| Field | Default value |
|---|---|
| Email | `admin@platform.com` |
| Password | `admin123` |

> Change these in `.env` before deploying to production.

#### `GET /admin/questions`
List **all** questions including unpublished drafts.

#### `POST /admin/questions`
Create a new question with hidden test cases.

**Request**
```json
{
  "title": "Two Sum",
  "description": "Given an array of integers nums and an integer target...",
  "difficulty": "easy",
  "constraints": "2 ≤ n ≤ 10⁴, -10⁹ ≤ nums[i] ≤ 10⁹",
  "sample_input": "4\n2 7 11 15\n9",
  "sample_output": "0 1",
  "test_cases": [
    { "input": "4\n2 7 11 15\n9",  "expected_output": "0 1" },
    { "input": "3\n3 2 4\n6",       "expected_output": "1 2" }
  ],
  "is_published": false
}
```
**Response `201`** — created question object

#### `PUT /admin/questions/{question_id}`
Full update (replace) of an existing question.

#### `GET /admin/submissions`
List all submissions across all students.

**Response `200`**
```json
[
  {
    "id": 42,
    "user_name": "Alice",
    "question_title": "Two Sum",
    "language": "python",
    "status": "accepted",
    "score": 100.0,
    "submitted_at": "2026-08-18T19:00:00"
  }
]
```

---

## Database Schema

### `users`
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| name | TEXT | Display name |
| email | TEXT UNIQUE | Login email |
| password_hash | TEXT | bcrypt hash |
| role | TEXT | `admin` or `student` |
| created_at | DATETIME | Registration time |

### `questions`
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| title | TEXT | Question title |
| description | TEXT | Full problem statement |
| difficulty | TEXT | `easy`, `medium`, or `hard` |
| constraints | TEXT | Input constraints |
| sample_input | TEXT | Visible sample input |
| sample_output | TEXT | Visible sample output |
| test_cases | JSON | Hidden test cases — `[{input, expected_output}]` — never returned to students |
| is_published | BOOLEAN | Visible to students only if `true` |
| created_by | INTEGER FK | Admin user id |
| created_at | DATETIME | |
| updated_at | DATETIME | Auto-updated on every PUT |

### `submissions`
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| user_id | INTEGER FK | Student who submitted |
| question_id | INTEGER FK | Question attempted |
| language | TEXT | `python`, `gcc`, `java`, `javascript`, etc. |
| code | TEXT | Submitted source code |
| status | TEXT | `accepted`, `wrong_answer`, `runtime_error`, `time_limit_exceeded` |
| passed_cases | INTEGER | Number of test cases passed |
| total_cases | INTEGER | Total test cases |
| score | FLOAT | (passed / total) × 100 |
| execution_time_ms | INTEGER | Total wall-clock time across all test cases |
| submitted_at | DATETIME | |

---

## Project Structure

```
code-compiler-backend/
├── app/
│   ├── main.py              # FastAPI app init, CORS, router registration
│   ├── config.py            # pydantic-settings — loads .env (SECRET_KEY, ADMIN_EMAIL, PISTON_URL)
│   ├── database.py          # SQLAlchemy engine, SessionLocal, Base
│   ├── dependencies.py      # get_db, get_current_user, require_admin, get_optional_user
│   ├── seed.py              # Seeds admin account on startup (idempotent)
│   │
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── question.py
│   │   └── submission.py
│   │
│   ├── schemas/             # Pydantic request/response schemas
│   │   ├── auth.py          # RegisterRequest, LoginRequest, TokenResponse
│   │   ├── question.py      # QuestionCreate, QuestionUpdate, QuestionResponse
│   │   ├── submission.py    # RunRequest, SubmitRequest, ExecutionResult, SubmitResponse
│   │   └── ranking.py       # RankingEntry
│   │
│   ├── routers/             # HTTP route handlers (one file per domain)
│   │   ├── auth.py          # POST /auth/register, /auth/login
│   │   ├── playground.py    # POST /playground/run
│   │   ├── questions.py     # GET /questions, GET /questions/{id}
│   │   ├── submissions.py   # POST /submissions/run, /submit — GET /submissions/my
│   │   ├── rankings.py      # GET /rankings, /rankings/{id}
│   │   └── admin.py         # GET/POST/PUT /admin/questions — GET /admin/submissions
│   │
│   └── services/            # Business logic, decoupled from HTTP
│       ├── auth_service.py  # hash_password, verify_password, create_token, decode_token
│       ├── piston_service.py# execute_code, run_code, language aliases, per-language timeouts
│       ├── question_service.py  # list/get/create/update questions
│       ├── judge_service.py     # run_against_sample, judge_submission, get_my_submissions
│       └── ranking_service.py   # get_global_rankings, get_question_rankings
│
├── tests/                   # 94 pytest tests
│   ├── test_auth.py
│   ├── test_dependencies.py
│   ├── test_playground.py
│   ├── test_questions.py
│   ├── test_submissions.py
│   ├── test_rankings.py
│   ├── test_piston_service.py
│   ├── test_judge_service.py
│   └── test_ranking_service.py
│
├── scripts/
│   └── piston-entrypoint.sh # Starts Piston + auto-installs runtimes on docker compose up
│
├── docs/
│   └── PRD.md               # Full Product Requirements Document
│
├── Dockerfile               # FastAPI image (Python 3.11-slim)
├── Dockerfile.piston        # Custom Piston image with no-sandbox isolate wrapper
├── isolate-nosec.py         # Replaces isolate binary — dev-only, no namespace sandboxing
├── docker-compose.yml       # Orchestrates piston + fastapi services
├── requirements.txt
└── .env                     # Not committed — see .env section above
```

---

## Running Tests

```bash
# Inside the fastapi container (recommended)
docker exec fastapi pytest -v

# Locally (requires Python 3.11+)
pip install -r requirements.txt
pytest -v
```

Tests use an in-memory SQLite database with `StaticPool` so they are fully isolated and fast.

---

## CORS

The API allows requests from the frontend dev server:

```python
# app/main.py
CORSMiddleware(
    allow_origins=["http://localhost:5173"],   # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Update `allow_origins` for production deployments.

---

## Non-Functional Details

| Setting | Value |
|---|---|
| JWT expiry | 24 hours |
| Execution timeout (default) | 5 seconds |
| Execution timeout (Java/JVM) | 10 seconds (JVM startup overhead) |
| Execution timeout (C++/Rust) | 8 seconds (compile time) |
| Memory limit | 128 MB per execution |
| Output comparison | Trimmed whitespace (`actual.strip() == expected.strip()`) |
| API port | 8000 |
| Piston port | 2000 |
| Frontend expects | `http://localhost:5173` |

---

## macOS ARM (Apple Silicon) Notes

The upstream Piston image uses the `isolate` sandbox which calls Linux `clone()` with namespace flags. These fail under QEMU x86_64 emulation on Apple Silicon (M1/M2/M3).

This repo ships a drop-in replacement (`isolate-nosec.py`) that executes code directly without namespace isolation. It is **development-only** — safe for local use but provides no process isolation between submissions.

**For production** on a native Linux host:
1. Remove the `build:` block from the `piston` service in `docker-compose.yml`
2. Restore `image: ghcr.io/engineer-man/piston`
3. Remove `Dockerfile.piston` and `isolate-nosec.py`

---

## Frontend Repository

The companion frontend is a separate repo:

| Repo | Stack |
|---|---|
| `code-compiler-frontend` | React 18, Vite, Material UI, Zustand, Monaco Editor, React Router v6 |

Frontend pages:

| Route | Access | Description |
|---|---|---|
| `/login` | Public | Login form |
| `/register` | Public | Student registration |
| `/playground` | Auth | Free compiler — write, run, see output |
| `/questions` | Auth | Published question list with difficulty badges |
| `/questions/:id` | Auth | Problem statement + Monaco editor + Run / Submit |
| `/leaderboard` | Auth | Global rankings table |
| `/admin/questions` | Admin | Manage all questions |
| `/admin/questions/new` | Admin | Create question with test case editor |
| `/admin/questions/:id/edit` | Admin | Edit question and test cases |
| `/admin/submissions` | Admin | All submissions across all students |
