# Code Compiler Platform — Backend

A FastAPI backend for a competitive programming platform. Supports user auth, question management, code execution via Piston, submission judging, and global/per-question rankings.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI (Python 3.11) |
| Database | SQLite + SQLAlchemy 2.x |
| Auth | JWT (HS256) via python-jose |
| Code execution | Piston (self-hosted) |
| Container | Docker Compose |

---

## Getting Started

### Prerequisites

- Docker Desktop (macOS, Linux, Windows)
- `git`

### 1. Clone and configure

```bash
git clone <repo-url>
cd code-compiler-backend
cp .env.example .env   # or create .env manually (see below)
```

### 2. Create `.env`

```env
SECRET_KEY=change-me-in-production
ADMIN_EMAIL=admin@platform.com
ADMIN_PASSWORD=admin123
PISTON_URL=http://localhost:2000
DATABASE_URL=sqlite:///./app.db
```

### 3. Start services

```bash
docker compose up -d
```

This starts two services:

- **piston** — code execution engine (port 2000)
- **fastapi** — REST API with hot-reload (port 8000)

**On first run**, the Piston container automatically installs the required language runtimes (Python, JavaScript, Java, C++, Go, Rust). This takes **2–5 minutes** depending on your connection. Monitor progress:

```bash
docker logs piston -f
```

You'll see:
```
Piston API ready
  [ok] python already installed
  [+]  Installing gcc-10.2.0 ...
  ...
All runtimes ready.
```

On subsequent starts the runtimes are cached in a Docker volume and load instantly.

### 4. Verify

```bash
# API health
curl http://localhost:8000/docs         # Swagger UI

# Quick smoke test
curl -s -X POST http://localhost:8000/playground/run \
  -H "Content-Type: application/json" \
  -d '{"language":"python","code":"print(42)","stdin":""}' 
# -> {"stdout":"42\n","status":"accepted",...}
```

---

## Supported Languages

| Frontend alias | Piston runtime | Notes |
|---|---|---|
| `python`, `python3`, `py` | `python 3.12.0` | |
| `javascript`, `js`, `node` | `javascript 18.15.0` | Node.js |
| `java` | `java 15.0.2` | JVM startup adds ~3s |
| `cpp`, `c++`, `c` | `gcc 10.2.0` | Compiles with g++ |
| `go` | `go 1.16.2` | |
| `rust` | `rust 1.68.2` | |

---

## API Reference

All authenticated endpoints require:
```
Authorization: Bearer <token>
```

### Auth

#### `POST /auth/register`
Register a new student account.

```json
// Request
{ "name": "Alice", "email": "alice@example.com", "password": "secret" }

// Response 201
{ "id": 1, "name": "Alice", "email": "alice@example.com", "role": "student" }
```

#### `POST /auth/login`
Obtain a JWT token.

```json
// Request
{ "email": "alice@example.com", "password": "secret" }

// Response 200
{ "access_token": "<jwt>", "token_type": "bearer" }
```

---

### Playground

#### `POST /playground/run`
Execute code without authentication. No submission is recorded.

```json
// Request
{
  "language": "python",   // see supported languages table
  "code": "print('hi')",
  "stdin": ""             // optional
}

// Response 200
{
  "stdout": "hi\n",
  "stderr": "",
  "execution_time_ms": 730,
  "status": "accepted"    // accepted | runtime_error | time_limit_exceeded
}
```

---

### Questions

#### `GET /questions`
List all published questions. If authenticated, includes `is_solved` per question.

```json
// Response 200
[
  {
    "id": 1,
    "title": "Two Sum",
    "difficulty": "easy",      // easy | medium | hard
    "description": "...",
    "constraints": "...",
    "sample_input": "...",
    "sample_output": "...",
    "is_solved": false          // only when authenticated
  }
]
```

#### `GET /questions/{question_id}`
Get a single published question. Test cases are not exposed.

---

### Submissions — requires auth

#### `POST /submissions/run`
Run code against the question's **sample input** only. Does not record a submission.

```json
// Request
{ "question_id": 1, "language": "python", "code": "..." }

// Response 200  (same shape as playground/run)
{ "stdout": "...", "stderr": "", "execution_time_ms": 450, "status": "accepted" }
```

#### `POST /submissions/submit`
Run code against **all hidden test cases**, score it, and record the result.

```json
// Request
{ "question_id": 1, "language": "python", "code": "..." }

// Response 201
{
  "id": 42,
  "question_id": 1,
  "language": "python",
  "status": "accepted",        // accepted | wrong_answer | runtime_error | time_limit_exceeded
  "score": 100.0,              // 0–100, (passed_cases / total_cases) * 100
  "passed_cases": 5,
  "total_cases": 5,
  "execution_time_ms": 450,
  "submitted_at": "2026-08-18T19:00:00"
}
```

#### `GET /submissions/my`
List the authenticated user's submission history.

---

### Rankings

#### `GET /rankings`
Global leaderboard. No auth required.

```json
[
  { "rank": 1, "user_id": 3, "name": "Alice", "total_score": 300.0, "solved_count": 3 },
  { "rank": 2, "user_id": 7, "name": "Bob",   "total_score": 150.0, "solved_count": 1 }
]
```

#### `GET /rankings/{question_id}`
Per-question leaderboard, sorted by best score then fastest time.

```json
[
  { "rank": 1, "user_id": 7, "name": "Bob",   "best_score": 100.0, "execution_time_ms": 120 },
  { "rank": 2, "user_id": 3, "name": "Alice", "best_score": 100.0, "execution_time_ms": 450 }
]
```

---

### Admin — requires admin role

The seeded admin credentials (from `.env`):
- Email: `ADMIN_EMAIL`
- Password: `ADMIN_PASSWORD`

#### `GET /admin/questions`
List all questions including unpublished.

#### `POST /admin/questions`
Create a question.

```json
{
  "title": "Two Sum",
  "description": "Given an array...",
  "difficulty": "easy",
  "constraints": "1 ≤ n ≤ 1000",
  "sample_input": "4\n2 7 11 15\n9",
  "sample_output": "0 1",
  "test_cases": [
    { "input": "4\n2 7 11 15\n9", "expected_output": "0 1" }
  ],
  "is_published": false
}
```

#### `PUT /admin/questions/{question_id}`
Replace a question (full update).

#### `GET /admin/submissions`
List all submissions across all users.

---

## Running Tests

```bash
# Inside the fastapi container
docker exec fastapi pytest

# Or locally (Python 3.11+ required)
pip install -r requirements.txt
pytest
```

94 tests covering auth, dependencies, playground, questions, submissions, rankings, and service-layer logic.

---

## Project Structure

```
app/
  main.py              # FastAPI app, router registration
  config.py            # pydantic-settings config (reads .env)
  database.py          # SQLAlchemy engine + session
  dependencies.py      # get_current_user, require_admin, get_optional_user
  seed.py              # seeds admin user on startup
  models/              # SQLAlchemy ORM models
    user.py
    question.py
    submission.py
  schemas/             # Pydantic request/response schemas
  routers/             # Route handlers
    auth.py
    playground.py
    questions.py
    submissions.py
    rankings.py
    admin.py
  services/            # Business logic
    auth_service.py    # JWT encode/decode, password hashing
    piston_service.py  # Piston API client, language aliases, timeouts
    question_service.py
    judge_service.py   # run_against_sample, judge_submission
    ranking_service.py

scripts/
  piston-entrypoint.sh # Auto-installs runtimes on docker compose up

Dockerfile             # FastAPI image
Dockerfile.piston      # Custom Piston image (isolate no-sandbox wrapper)
isolate-nosec.py       # Replaces isolate binary — dev only, no sandboxing
docker-compose.yml
tests/
```

---

## macOS ARM Notes

The upstream Piston image uses `isolate` for sandboxing which relies on Linux `clone()` namespaces. These fail under QEMU x86_64 emulation on Apple Silicon. This repo ships a no-sandbox wrapper (`isolate-nosec.py`) that executes code directly. It is **development-only** — do not use in production.

For production, use the upstream `ghcr.io/engineer-man/piston` on a native Linux host and remove the custom `Dockerfile.piston` build in `docker-compose.yml`.
