from fastapi import APIRouter

from core.ai import get_model_version, get_model_health
from core.market import get_market_status

router = APIRouter()


@router.get("/api/market_status")
def market_status():
    from core.market import get_market_history

    status = get_market_status()
    status["model_version"] = get_model_version()
    status["model_health"] = get_model_health()
    status["history"] = get_market_history()
    return status
