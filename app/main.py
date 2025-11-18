from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api import plans_router
from app.db.session import init_db
from app.core.scheduler import scheduler
import os

app = FastAPI()

# Allow CORS for frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plans_router, prefix="/api")

@app.on_event("startup")
def on_startup():
    init_db()
    scheduler.start()

# Serve static frontend (Vite build)
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend_dist")
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    # SPA fallback: serve index.html for any non-API, non-static route
    @app.middleware("http")
    async def spa_fallback(request: Request, call_next):
        if request.url.path.startswith("/api") or "." in request.url.path.split("/")[-1]:
            return await call_next(request)
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return await call_next(request)

@app.get("/api/health")
def health():
    return {"status": "ok"}
