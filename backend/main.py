import argparse
import os
import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from backend.limiter import limiter

# Add parent directory to path - MUST BE FIRST for core imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.routes.market import router as market_router
from backend.routes.stock import router as stock_router
from backend.routes.sync import run_sync_task, router as sync_router
from backend.routes.system import router as system_router
from core.data import get_all_tw_stocks, init_db
from core.logger import setup_logger

logger = setup_logger("backend")

app = FastAPI(title="Smart Stock Selector")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Global Error Catch: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "path": request.url.path,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail},
    )


# CORS allowed origins: configure via env var CORS_ORIGINS (comma-separated).
# Wildcard ("*") + allow_credentials=True is intentionally avoided — browsers
# reject this combination and it is an OWASP A05 Security Misconfiguration.
def _get_allowed_origins() -> list[str]:
    env_val = os.environ.get("CORS_ORIGINS", "").strip()
    if env_val:
        return [o.strip() for o in env_val.split(",") if o.strip()]
    return [
        "http://localhost:5174",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
)

frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if not os.path.exists(frontend_path):
    os.makedirs(frontend_path)


@app.get("/")
async def read_index():
    candidates = [
        os.path.join(frontend_path, "index.html"),
        os.path.join(frontend_path, "index_legacy.html"),
        os.path.join(frontend_path, "v4", "dist", "index.html"),
        os.path.join(frontend_path, "v4", "index.html"),
    ]
    for entry in candidates:
        if os.path.exists(entry):
            return FileResponse(entry)
    raise HTTPException(status_code=404, detail="Frontend entry file not found")


app.mount("/static", StaticFiles(directory=frontend_path, html=True), name="static")

app.include_router(sync_router)
app.include_router(market_router)
app.include_router(stock_router)
app.include_router(system_router)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sync", action="store_true", help="Run sync and exit")
    args = parser.parse_args()

    if args.sync:
        print("Starting Sync-Only Mode...")
        run_sync_task()
        print("Sync Complete.")
    else:
        try:
            init_db()
            get_all_tw_stocks()
            logger.info("Stock list cached successfully.")
        except Exception as e:
            logger.error("Failed to cache stock list: %s", e)

        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=8000)
