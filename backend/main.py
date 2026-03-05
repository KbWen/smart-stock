import argparse
import os
import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Global Error Catch: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": f"Server Side Error: {str(exc)}",
            "path": request.url.path,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
