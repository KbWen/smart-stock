from fastapi import APIRouter
from datetime import datetime
from core import config
from core.data import get_db_connection
from core.ai import get_model_version

router = APIRouter(prefix="/api")

@router.get("/health")
def health_check():
    """System Health Check Endpoint"""
    health_status = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "db": "disconnected",
        "model_version": get_model_version(),
        "concurrency_workers": config.CONCURRENCY_WORKERS
    }
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        health_status["db"] = "connected"
    except Exception as e:
        health_status["status"] = "error"
        health_status["db"] = "disconnected"
        
    return health_status
