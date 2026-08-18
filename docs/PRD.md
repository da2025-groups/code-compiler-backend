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
- JWT-based sessions (email + password)
- Role-based route protection (admin vs student)

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
GET    /questions           List all published questions
GET    /questions/:id       Question detail + sample I/O
POST   /questions           [Admin] Create question with test cases
PUT    /questions/:id       [Admin] Edit question
DELETE /questions/:id       [Admin] Delete question
```

### Submissions
```
POST  /submissions/run      Run against sample input (no score saved)
POST  /submissions/submit   Judge against all test cases (score saved)
GET   /submissions/my       Student's own submission history
GET   /admin/submissions    [Admin] All submissions across all users
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

## 13. Non-functional Requirements
- Code execution isolated per submission (no cross-contamination)
- Execution timeout: 5 seconds
- Memory limit: 64MB per execution
- API response time (non-execution): < 200ms
- JWT tokens expire after 24 hours
