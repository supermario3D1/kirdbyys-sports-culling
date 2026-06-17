"""Kirdbyys Sports Culling Tool — FastAPI application entry point."""
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import uvicorn

from kirdbyys.config import settings
from kirdbyys.core.database import init_db
from kirdbyys.api import routes

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_TAGLINE,
    version=settings.APP_VERSION
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Templates
templates = Jinja2Templates(directory=str(settings.UI_TEMPLATES_DIR))

# Static files
app.mount("/static", StaticFiles(directory=str(settings.UI_STATIC_DIR)), name="static")

# Include API routes
app.include_router(routes.router, prefix="/api")

@app.on_event("startup")
async def startup():
    await init_db()
    print(f"[Kirdbyys] {settings.APP_NAME} v{settings.APP_VERSION} started")
    print(f"[Kirdbyys] Data directory: {settings.DATA_DIR}")
    print(f"[Kirdbyys] Models directory: {settings.MODELS_DIR}")
    print(f"[Kirdbyys] Open UI at http://{settings.HOST}:{settings.PORT}")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/favicon.ico")
async def favicon():
    icon_path = settings.UI_STATIC_DIR / "icon.svg"
    if icon_path.exists():
        return FileResponse(str(icon_path))
    return None

def run():
    uvicorn.run(
        "kirdbyys.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    run()