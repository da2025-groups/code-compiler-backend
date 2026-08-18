# Product Requirements Document
## Multi-language Code Compiler & Evaluation Platform

**Version:** 1.0  
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
| **Admin** | Login, create/edit/delete questions, view all submissions, manage users |
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
- Available to all logged-in students

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
POST  /auth/login           Get JWT token (admin + student)
```

### Playground
```
POST  /playground/run       Run code with custom stdin — stateless, no score
```

### Questions
```
GET    /questions           List published questions — includes is_solved flag per authenticated student
GET    /questions/:id       Question detail + sample I/O
POST   /questions           [Admin] Create question with test cases
PUT    /questions/:id       [Admin] Edit question
DELETE /questions/:id       [Admin] Delete question
```

### Submissions
```
POST  /submissions/run                        Run against sample input (no score saved)
POST  /submissions/submit                     Judge against all test cases (score saved)
GET   /submissions/my                         Student's own full submission history
GET   /submissions/my?question_id=:id         Student's submissions for a specific question
GET   /admin/submissions                      [Admin] All submissions across all users
```

### Rankings
```
GET  /rankings                  Global leaderboard
GET  /rankings/:question_id     Per-question leaderboard
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
| execution_time_ms | INTEGER | Total execution time |
| submitted_at | DATETIME | Submission timestamp |

---

## 7. Frontend Pages

| Route | Role | Description |
|-------|------|-------------|
| `/login` | Both | Login form |
| `/register` | Student | Signup form |
| `/playground` | Student | Free compiler — write, run, see output. No question context. |
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
│   │  - View all subs  │       │  - Question list       │  │
│   │  - Manage users   │       │  - Code editor         │  │
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
1. Project scaffold (FastAPI + SQLAlchemy + SQLite)
2. Database models (users, questions, submissions)
3. Auth routes (register, login, JWT middleware)
4. Piston integration (execution service)
5. Playground run endpoint
6. Questions CRUD (admin routes)
7. Submissions — run + submit + judge logic
8. Rankings endpoint

### Frontend
1. React + Vite scaffold
2. Login + Register pages
3. Playground page (Monaco editor + run)
4. Question list page
5. Question detail + Monaco editor + run/submit + verdict
6. Leaderboard page
7. Admin dashboard (question management)
8. Admin submissions view

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
│   │   │   ├── Navbar.jsx             # Top nav with role-aware links
│   │   │   ├── Sidebar.jsx            # Admin sidebar
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
│   │           └── adminApi.js            # POST/PUT/DELETE /questions, GET /admin/submissions
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
│   │   ├── authStore.js                   # user, token, role, login/logout
│   │   └── editorStore.js                 # language, code per question (persisted)
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
- **Axios interceptor** in `services/api.js` auto-attaches JWT to every request
- **MUI theme** defined once in `src/theme/index.js` — all pages inherit it

---

## 14. Backend Folder Structure

```
code-compiler-backend/
├── app/
│   ├── main.py                  # FastAPI app init, CORS middleware, router registration
│   ├── database.py              # SQLAlchemy engine, session, Base
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
│   │   └── admin.py             # GET /admin/submissions
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
├── requirements.txt
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
