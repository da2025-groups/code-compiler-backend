from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, SessionLocal
from app.seed import seed_admin
from app.routers import auth, playground, questions, submissions, rankings, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create all tables then seed the admin account
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_admin(db)
    finally:
        db.close()
    yield
    # Shutdown: nothing needed for MVP


app = FastAPI(title="Code Compiler Platform", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(playground.router, prefix="/playground", tags=["playground"])
app.include_router(questions.router, prefix="/questions", tags=["questions"])
app.include_router(submissions.router, prefix="/submissions", tags=["submissions"])
app.include_router(rankings.router, prefix="/rankings", tags=["rankings"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
