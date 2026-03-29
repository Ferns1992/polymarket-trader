from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.database import engine, Base
import app.api.routes as routes_module
from app.init_db import init_db

app = FastAPI(
    title="Polymarket AI Trader", description="AI-powered trading bot for Polymarket"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

try:
    init_db()
except:
    pass

app.include_router(router)

templates = Jinja2Templates(directory="app/static")

from pathlib import Path

static_path = Path("app/static")
if not static_path.exists():
    static_path.mkdir(parents=True)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/markets", response_class=HTMLResponse)
async def markets_page(request: Request):
    return templates.TemplateResponse("markets.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})


@app.get("/trades", response_class=HTMLResponse)
async def trades_page(request: Request):
    return templates.TemplateResponse("trades.html", {"request": request})
