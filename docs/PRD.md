# Product Requirements Document
## Multi-language Code Compiler & Evaluation Platform

**Version:** 1.4  
**Date:** 2026-08-18  
**Project:** #10 — Dr. Dhawaleswar Rao, SoET/CSE  

---

## 1. Overview

A HackerRank-style competitive coding platform where admins post coding challenges and students solve them in a browser-based code editor. Code runs securely in a sandboxed execution engine with real-time output and a live leaderboard. Students can also use a free playground compiler independently of any contest.

---

## 2. Repositories

| Repo | Tech Stack | Purpose |
|------|-----------|---------|
| `code-compiler-backend` | FastAPI, SQLite, SQLAlchemy, Piston | API, auth, execution engine, judging, rankings |
| `code-compiler-frontend` | React, Vite, Monaco Editor | Admin dashboard + Student portal |

---

## 3. User Roles

| Role | Capabilities |
|------|-------------|
| **Admin** | Login, use playground, create/edit/delete questions, view all submissions |
| **Student** | Register/login, use playground, view published questions, run & submit solutions, view rankings |

---

## 4. Core Features

### 4.1 Authentication
- Student self-registration (name, email, password)
- Admin account seeded at application startup
- JWT-based sessions (email + password) — no OAuth, no third-party providers
- Access token returned on login, stored in `localStorage` on the frontend
- Role-based route protection (admin vs student)
- All protected routes require `Authorization: Bearer <token>` header

### 4.2 Playground (Free Compiler)
A standalone code editor with no relation to questions, scoring, or leaderboard.

- Monaco Editor with language selector
- Custom stdin input field
- Run code → see stdout, stderr, and execution time
- Stateless — nothing saved to database
- Available to all logged-in users (both students and admins)

### 4.3 Question Management (Admin)
- Create question with: title, description, difficulty (Easy / Medium / Hard), constraints, sample input/output
- Add hidden test cases used for judging only (not visible to students)
- Publish / unpublish questions
- Edit or delete existing questions

### 4.4 Code Editor — Contest Mode (Student)
- Monaco Editor (VS Code-grade editor in browser)
- Language selector: Python, C++, Java, JavaScript
- **Run** — executes against sample input, shows output instantly, no score saved
- **Submit** — judges against all hidden test cases, score saved to database

### 4.5 Execution Engine
- **Piston** (self-hosted via Docker) handles all language runtimes
- Execution limits: 5s timeout, 64MB memory per submission
- Same engine used for both Playground and Contest modes

### 4.6 Judging & Scoring

| Verdict | Condition | Score |
|---------|-----------|-------|
| Accepted | All test cases pass | 100 |
| Partial | Some test cases pass | (passed / total) × 100 |
| Wrong Answer | Output mismatch | 0 |
| Time Limit Exceeded | Execution > 5s | 0 |
| Compile / Runtime Error | Error in code | 0 |

- Output comparison uses **trimmed whitespace matching**: `actual.strip() == expected.strip()` — prevents false Wrong Answers from trailing newlines or spaces
- Only the best submission per question per student counts toward ranking
- Full submission history is always visible to the student

### 4.7 Leaderboard / Rankings
- **Per question:** ranked by score DESC, then execution time ASC
- **Global:** ranked by problems fully solved DESC, then total score DESC
- Updates after every submission

---

## 5. API Design

### Auth
```
POST  /auth/register        Student signup
                            Body: { name, email, password }
                            Response: { message: "registered successfully" }

POST  /auth/login           Get JWT token (admin + student)
                            Body: { email, password }
                            Response: { access_token, token_type: "bearer", role }
```

### Playground
```
POST  /playground/run       Run code with custom stdin — stateless, no score
                            Body: { language, code, stdin }
                            Response: { stdout, stderr, execution_time_ms, status }
```

### Questions
```
GET    /questions                List published questions — includes is_solved flag per authenticated student
                                 Response: [{ id, title, difficulty, is_solved, created_at }]

GET    /questions/:id            Question detail + sample I/O
                                 Response: { id, title, description, difficulty, constraints,
                                             sample_input, sample_output, created_at }
                                 Note: test_cases field is NEVER returned — hidden from students

POST   /questions                [Admin] Create question with test cases
                                 Body: { title, description, difficulty, constraints,
                                         sample_input, sample_output, test_cases, is_published }

PUT    /questions/:id            [Admin] Edit question
                                 Body: { title, description, difficulty, constraints,
                                         sample_input, sample_output, test_cases, is_published }

DELETE /questions/:id            [Admin] Delete question
                                 Response: { message: "deleted" }

GET    /admin/questions          [Admin] List ALL questions including unpublished drafts
                                 Response: [{ id, title, difficulty, is_published, created_at, updated_at }]
```

### Submissions
```
POST  /submissions/run                        Run against question's sample_input (no score saved)
                                              Body: { question_id, language, code }
                                              Backend fetches sample_input from DB and executes
                                              Response: { stdout, stderr, execution_time_ms, status }

POST  /submissions/submit                     Judge against all hidden test cases (score saved)
                                              Body: { question_id, language, code }
                                              Response: { status, score, passed_cases, total_cases, results: [{input, expected, actual, verdict}] }

GET   /submissions/my                         Student's own full submission history
                                              Response: [{ id, question_id, question_title, language, status, score, submitted_at }]
GET   /submissions/my?question_id=:id         Student's submissions for a specific question (same shape)
GET   /admin/submissions                      [Admin] All submissions across all users
                                              Response: [{ id, user_name, question_title, language, status, score, submitted_at }]
```

### Rankings
```
GET  /rankings                  Global leaderboard
                                Response: [{ rank, user_id, name, solved_count, total_score }]
                                sorted by solved_count DESC, total_score DESC

GET  /rankings/:question_id     Per-question leaderboard
                                Response: [{ rank, user_id, name, best_score, execution_time_ms }]
                                sorted by best_score DESC, execution_time_ms ASC
```

---

## 6. Database Schema (SQLite)

### users
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| name | TEXT | Display name |
| email | TEXT UNIQUE | Login email |
| password_hash | TEXT | bcrypt hash |
| role | TEXT | `admin` or `student` |
| created_at | DATETIME | Registration time |

### questions
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| title | TEXT | Question title |
| description | TEXT | Full problem statement |
| difficulty | TEXT | `easy`, `medium`, `hard` |
| constraints | TEXT | Input constraints |
| sample_input | TEXT | Visible sample input |
| sample_output | TEXT | Visible sample output |
| test_cases | JSON | Hidden test cases array `[{input, expected_output}]` |
| is_published | BOOLEAN | Visible to students only if true |
| created_by | INTEGER FK | Admin user id |
| created_at | DATETIME | Creation time |
| updated_at | DATETIME | Last edit time (auto-updated on PUT) |

### submissions
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| user_id | INTEGER FK | Student who submitted |
| question_id | INTEGER FK | Question attempted |
| language | TEXT | `python`, `cpp`, `java`, `javascript` |
| code | TEXT | Submitted source code |
| status | TEXT | `accepted`, `partial`, `wrong_answer`, `tle`, `error` |
| passed_cases | INTEGER | Number of test cases passed |
| total_cases | INTEGER | Total test cases |
| score | FLOAT | (passed / total) × 100 |
| execution_time_ms | INTEGER | Sum of execution time across all test cases (ms) |
| submitted_at | DATETIME | Submission timestamp |

---

## 7. Frontend Pages

| Route | Role | Description |
|-------|------|-------------|
| `/` | Both | Redirect — students → `/questions`, admins → `/admin/questions`, unauthenticated → `/login` |
| `/login` | Both | Login form |
| `/register` | Student | Signup form |
| `/playground` | Both | Free compiler — write, run, see output. No question context. |
| `/questions` | Student | Contest question list with difficulty badges |
| `/questions/:id` | Student | Problem statement + Monaco editor + Run / Submit + verdict |
| `/leaderboard` | Both | Global rankings table |
| `/admin/questions` | Admin | Manage all questions (list, edit, delete) |
| `/admin/questions/new` | Admin | Create question form with test case editor |
| `/admin/questions/:id/edit` | Admin | Edit existing question and test cases |
| `/admin/submissions` | Admin | All submissions across all students |

---

## 8. Two Modes — Clear Separation

```
PLAYGROUND MODE                   CONTEST MODE
────────────────────────          ──────────────────────────────
Route: /playground                Route: /questions/:id
Free editor                       Problem statement shown
Custom stdin                      Sample I/O provided
Run only                          Run (sample) + Submit (judge)
Nothing saved to DB               Submission saved + scored
No test cases                     Hidden test cases judged
No ranking impact                 Affects leaderboard
```

Both modes share the same Piston execution engine and Monaco editor component.

---

## 9. Supported Languages (MVP)

| Language | Runtime | File Extension |
|----------|---------|----------------|
| Python | Python 3.11 | `.py` |
| C++ | GCC g++ | `.cpp` |
| Java | OpenJDK 17 | `.java` |
| JavaScript | Node.js 18 | `.js` |

---

## 10. Architecture Diagram

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
  │ SQLite DB  │                       │  Piston Engine  │
  │  users     │                       │  (Docker)       │
  │  questions │                       │  Python / C++   │
  │  submissions│                      │  Java / Node.js │
  └────────────┘                       └─────────────────┘
```

---

## 11. Build Order

### Backend
1. Project scaffold (FastAPI + SQLAlchemy + SQLite + config.py + .env)
2. Docker Compose — spin up Piston engine, verify it responds
3. Database models (users, questions, submissions)
4. Auth routes (register, login, JWT middleware)
5. Piston integration (piston_service.py — execution wrapper)
6. Playground run endpoint
7. Questions CRUD (admin routes)
8. Submissions — run + submit + judge logic (trimmed whitespace comparison)
9. Rankings endpoint

### Frontend
1. React + Vite scaffold + MUI theme + Axios instance + Zustand stores
2. Router setup — ProtectedRoute, AdminRoute, root `/` redirect
3. Login + Register pages
4. Playground page (Monaco editor + run)
5. Question list page (with difficulty badges + is_solved indicator)
6. Question detail + Monaco editor + Run / Submit + verdict + submission history
7. Leaderboard page
8. Admin — question list + create + edit pages
9. Admin submissions view

---

## 12. Out of Scope (MVP)
- Email verification / password reset
- Google OAuth
- Real-time updates via WebSockets
- Plagiarism detection
- Code templates per language
- Discussion / comments on questions
- Contest scheduling / time-limited rounds
- Problem difficulty ratings by users

---

## 13. Frontend Folder Structure

### Tech Stack
| Concern | Choice | Reason |
|---------|--------|--------|
| Framework | React 18 + Vite | Fast builds, industry standard |
| Styling | Material UI (MUI v5) | Rich pre-built components, fast for hackathon |
| State | Zustand | Lightweight global state, no boilerplate |
| HTTP | Axios | Interceptors for JWT injection + error handling |
| Routing | React Router v6 | Declarative, nested routes |
| Code Editor | Monaco Editor (`@monaco-editor/react`) | VS Code engine in browser |

### Folder Structure

```
code-compiler-frontend/
├── public/
├── src/
│   │
│   ├── assets/                        # Static assets (images, icons, fonts)
│   │
│   ├── components/                    # REUSABLE COMPONENTS (shared across features)
│   │   │                              # NOTE: No ui/ folder — use MUI primitives directly
│   │   │                              # (Button, Input, Chip, Modal, Tabs, etc. all from MUI)
│   │   │
│   │   ├── layout/                    # App-wide layout components
│   │   │   ├── Navbar.jsx             # Top nav with role-aware links (student + admin in one)
│   │   │   ├── PageWrapper.jsx        # Consistent page padding/max-width
│   │   │   └── ProtectedLayout.jsx    # Wraps auth-required pages
│   │   │
│   │   └── common/                    # Shared composite components
│   │       ├── CodeEditor.jsx         # Monaco Editor wrapper (reused in Playground + Contest)
│   │       ├── LanguageSelector.jsx   # Dropdown for Python/C++/Java/JS
│   │       ├── OutputPanel.jsx        # stdout/stderr display panel
│   │       ├── VerdictBadge.jsx       # Accepted / WA / TLE status chip
│   │       └── EmptyState.jsx         # Empty list placeholder
│   │
│   ├── features/                      # FEATURE MODULES (co-located logic)
│   │   │
│   │   ├── auth/
│   │   │   ├── components/
│   │   │   │   ├── LoginForm.jsx
│   │   │   │   └── RegisterForm.jsx
│   │   │   ├── hooks/
│   │   │   │   └── useAuth.js         # login, logout, register actions
│   │   │   └── services/
│   │   │       └── authApi.js         # POST /auth/login, /auth/register
│   │   │
│   │   ├── playground/
│   │   │   ├── components/
│   │   │   │   ├── PlaygroundEditor.jsx   # CodeEditor + LanguageSelector + StdinInput
│   │   │   │   └── StdinInput.jsx         # Textarea for custom input
│   │   │   ├── hooks/
│   │   │   │   └── usePlayground.js       # run code, manage state
│   │   │   └── services/
│   │   │       └── playgroundApi.js       # POST /playground/run
│   │   │
│   │   ├── questions/
│   │   │   ├── components/
│   │   │   │   ├── QuestionList.jsx       # Grid/list of published questions
│   │   │   │   ├── QuestionCard.jsx       # Title, difficulty badge, solved status
│   │   │   │   ├── QuestionDetail.jsx     # Full problem statement + constraints
│   │   │   │   └── SampleIO.jsx           # Sample input/output display block
│   │   │   ├── hooks/
│   │   │   │   ├── useQuestions.js        # fetch question list
│   │   │   │   └── useQuestion.js         # fetch single question by id
│   │   │   └── services/
│   │   │       └── questionsApi.js        # GET /questions, GET /questions/:id
│   │   │
│   │   ├── editor/                        # Contest code editor + submission logic
│   │   │   ├── components/
│   │   │   │   ├── ContestEditor.jsx      # CodeEditor + Run + Submit buttons
│   │   │   │   ├── RunResult.jsx          # Output after Run (stdout/stderr)
│   │   │   │   ├── VerdictPanel.jsx       # Submit result: score, per-case breakdown
│   │   │   │   ├── TestCaseRow.jsx        # Single test case result row
│   │   │   │   └── SubmissionHistory.jsx  # Student's past submissions for this question
│   │   │   ├── hooks/
│   │   │   │   ├── useRun.js              # POST /submissions/run
│   │   │   │   └── useSubmit.js           # POST /submissions/submit
│   │   │   └── services/
│   │   │       └── submissionsApi.js      # run + submit API calls
│   │   │
│   │   ├── leaderboard/
│   │   │   ├── components/
│   │   │   │   ├── LeaderboardTable.jsx   # Full rankings table
│   │   │   │   ├── RankCell.jsx           # Rank number with medal for top 3
│   │   │   │   └── ScoreCell.jsx          # Score with progress bar
│   │   │   ├── hooks/
│   │   │   │   └── useLeaderboard.js      # GET /rankings
│   │   │   └── services/
│   │   │       └── rankingsApi.js
│   │   │
│   │   └── admin/
│   │       ├── components/
│   │       │   ├── QuestionForm.jsx        # Create/edit question form
│   │       │   ├── TestCaseEditor.jsx      # Add/remove hidden test cases
│   │       │   ├── AdminQuestionRow.jsx    # Single row in admin question table
│   │       │   └── AdminSubmissionsTable.jsx  # All submissions view
│   │       ├── hooks/
│   │       │   ├── useAdminQuestions.js
│   │       │   └── useAdminSubmissions.js
│   │       └── services/
│   │           └── adminApi.js            # GET/POST/PUT/DELETE /questions, GET /admin/questions, GET /admin/submissions
│   │
│   ├── pages/                             # ROUTE-LEVEL PAGES (thin wrappers only)
│   │   ├── LoginPage.jsx
│   │   ├── RegisterPage.jsx
│   │   ├── PlaygroundPage.jsx
│   │   ├── QuestionsPage.jsx
│   │   ├── QuestionDetailPage.jsx         # Composes QuestionDetail + ContestEditor
│   │   ├── LeaderboardPage.jsx
│   │   └── admin/
│   │       ├── AdminQuestionsPage.jsx
│   │       ├── AdminQuestionNewPage.jsx
│   │       ├── AdminQuestionEditPage.jsx   # Reuses QuestionForm with prefilled data
│   │       └── AdminSubmissionsPage.jsx
│   │
│   ├── store/                             # GLOBAL STATE (Zustand)
│   │   ├── authStore.js                   # user, token, role, login/logout — persisted to localStorage
│   │   └── editorStore.js                 # language + code per question — sessionStorage only (resets on tab close)
│   │
│   ├── router/                            # ROUTING
│   │   ├── index.jsx                      # All route definitions
│   │   ├── ProtectedRoute.jsx             # Redirect to /login if not authed
│   │   └── AdminRoute.jsx                 # Redirect if not admin role
│   │
│   ├── services/                          # HTTP CLIENT
│   │   └── api.js                         # Axios instance — baseURL + JWT interceptor
│   │
│   ├── hooks/                             # GLOBAL HOOKS
│   │   └── useToast.js                    # App-wide toast notifications
│   │
│   ├── utils/                             # PURE UTILITIES
│   │   ├── formatters.js                  # formatDate, formatScore, formatDuration
│   │   └── validators.js                  # Form validation helpers
│   │
│   ├── constants/                         # APP CONSTANTS
│   │   ├── languages.js                   # { id, label, monacoLang, pistonRuntime }
│   │   └── routes.js                      # Route path constants
│   │
│   ├── theme/
│   │   └── index.js                       # MUI theme (palette, typography, component overrides)
│   │
│   ├── App.jsx
│   └── main.jsx
│
├── .env                                   # VITE_API_BASE_URL
├── .env.example
├── index.html
├── vite.config.js
└── package.json
```

### Component Hierarchy (key pages)

```
QuestionDetailPage
├── PageWrapper
│   ├── QuestionDetail          (left panel)
│   │   ├── SampleIO
│   │   └── Badge (difficulty)
│   └── ContestEditor           (right panel)
│       ├── LanguageSelector    (reusable/common)
│       ├── CodeEditor          (reusable/common)
│       ├── RunResult
│       ├── VerdictPanel
│       │   └── TestCaseRow[]
│       └── SubmissionHistory

PlaygroundPage
└── PageWrapper
    └── PlaygroundEditor
        ├── LanguageSelector    (same reusable component)
        ├── CodeEditor          (same reusable component)
        ├── StdinInput
        └── OutputPanel         (same reusable component)
```

### MUI Component Mapping
| UI Need | MUI Component |
|---------|--------------|
| Difficulty badge | `<Chip color="success/warning/error">` |
| Rankings table | `<DataGrid>` |
| Admin submissions | `<DataGrid>` |
| Question tabs (Problem / Submissions) | `<Tabs> + <Tab>` |
| Create question modal | `<Dialog>` |
| Test case add/remove | `<IconButton>` + `<TextField>` |
| Loading states | `<CircularProgress>` |
| Notifications | `<Snackbar> + <Alert>` |
| Verdict status | `<Alert severity="success/error/warning">` |
| Navbar | `<AppBar> + <Toolbar>` |

### Key Design Principles
- **Pages are thin** — they compose features, never contain business logic
- **Features are self-contained** — each has its own components, hooks, and API service
- **`components/`** holds only truly reusable pieces used across 2+ features
- **Zustand stores** are minimal — only what must be globally shared (auth, editor state)
- **Axios interceptor** in `services/api.js` auto-attaches JWT to every request and redirects to `/login` on 401 (token expired)
- **MUI theme** defined once in `src/theme/index.js` — all pages inherit it

---

## 14. Backend Folder Structure

```
code-compiler-backend/
├── app/
│   ├── main.py                  # FastAPI app init, CORS middleware, router registration
│   ├── database.py              # SQLAlchemy engine, session, Base
│   ├── config.py                # Pydantic BaseSettings — loads SECRET_KEY, ADMIN_EMAIL, PISTON_URL from .env
│   ├── seed.py                  # Admin account seeding on startup
│   │
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── user.py              # User model
│   │   ├── question.py          # Question model
│   │   └── submission.py        # Submission model
│   │
│   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── auth.py              # RegisterRequest, LoginRequest, TokenResponse
│   │   ├── question.py          # QuestionCreate, QuestionUpdate, QuestionResponse
│   │   ├── submission.py        # RunRequest, SubmitRequest, SubmissionResponse
│   │   └── ranking.py           # RankingResponse
│   │
│   ├── routers/                 # Route handlers (one file per domain)
│   │   ├── auth.py              # POST /auth/register, /auth/login
│   │   ├── playground.py        # POST /playground/run
│   │   ├── questions.py         # GET/POST/PUT/DELETE /questions
│   │   ├── submissions.py       # POST /submissions/run, /submit, GET /submissions/my
│   │   ├── rankings.py          # GET /rankings, /rankings/:question_id
│   │   └── admin.py             # GET /admin/questions (all incl. drafts), GET /admin/submissions
│   │
│   ├── services/                # Business logic (decoupled from HTTP layer)
│   │   ├── auth_service.py      # password hashing, JWT create/verify
│   │   ├── piston_service.py    # Piston API calls, execution wrapper
│   │   ├── judge_service.py     # Test case evaluation logic
│   │   └── ranking_service.py   # Leaderboard computation
│   │
│   └── dependencies.py          # get_db, get_current_user, require_admin
│
├── docker-compose.yml           # Piston engine + backend service
├── requirements.txt             # fastapi, uvicorn, sqlalchemy, python-jose[cryptography],
│                                # passlib[bcrypt], httpx, pydantic-settings, python-multipart
└── .env                         # SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD, PISTON_URL
```

### CORS Configuration
```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Admin Account Seeding
- Admin credentials stored in `.env` as `ADMIN_EMAIL` and `ADMIN_PASSWORD`
- `seed.py` runs once on app startup — checks if admin exists, creates if not
- Prevents duplicate seeding on restart

```python
# .env
ADMIN_EMAIL=admin@platform.com
ADMIN_PASSWORD=admin123
SECRET_KEY=your-secret-key
PISTON_URL=http://localhost:2000
```

---

## 15. Non-functional Requirements
- Code execution isolated per submission (no cross-contamination)
- Execution timeout: 5 seconds
- Memory limit: 64MB per execution
- API response time (non-execution): < 200ms
- JWT tokens expire after 24 hours
- Backend runs on port **8000** (`uvicorn app.main:app --port 8000`)
- Frontend dev server runs on port **5173** (Vite default)
- CORS allows `http://localhost:5173` in development
