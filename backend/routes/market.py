from fastapi import APIRouter

from core.ai import get_model_version
from core.market import get_market_status

router = APIRouter()


@router.get("/api/market_status")
def market_status():
    from core.market import get_market_history, save_market_history

    status = get_market_status()
    status["model_version"] = get_model_version()

    if status.get("bull_ratio") is not None:
        save_market_history(status)

    status["history"] = get_market_history()
    return status
