from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import ai_chat, auth, favorites, notifications, refs, trips
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.migrations import ensure_trip_origin_column
from app.services.budget_calculator import seed_travel_type_coefficients
from app.tasks.scheduler import start_scheduler, stop_scheduler
import app.models  # noqa: F401


settings = get_settings()
templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_trip_origin_column()
    db = SessionLocal()
    try:
        seed_travel_type_coefficients(db)
    finally:
        db.close()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title=settings.app_name, version="1.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(trips.router, prefix=settings.api_v1_prefix)
app.include_router(favorites.router, prefix=settings.api_v1_prefix)
app.include_router(notifications.router, prefix=settings.api_v1_prefix)
app.include_router(refs.router, prefix=settings.api_v1_prefix)
app.include_router(ai_chat.router, prefix=settings.api_v1_prefix)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse("static/favicon.ico", media_type="image/x-icon")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="home.html")


@app.get("/auth", response_class=HTMLResponse, include_in_schema=False)
def auth_page(request: Request):
    return templates.TemplateResponse(request=request, name="auth.html")


@app.get(f"{settings.api_v1_prefix}/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
