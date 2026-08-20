import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import db
from .routes import instructor, student

if not os.environ.get("ANTHROPIC_API_KEY"):
    raise RuntimeError(
        "ANTHROPIC_API_KEY is not set. Put it in backend/.env (see backend/.env.example)."
    )

db.init_db()

app = FastAPI(title="Mission Statement Studio")

app.include_router(instructor.router)
app.include_router(student.router)

FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
