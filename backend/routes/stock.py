import re
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from backend.limiter import limiter

# Ticker validation: 1-15 chars, uppercase alphanumeric + . ^ -
# Covers TW (e.g. 2330.TW), US (AAPL), index (^TWII), crypto (BTC-USD)
_TICKER_RE = re.compile(r'^[A-Z0-9.\^\-]{1,15}$')

# Rate limit tiers (per-IP, per-minute)
_RATE_CANDIDATES = "60/minute"
_RATE_META = "30/minute"
_RATE_BACKTEST = "20/minute"

from backend.backtest import run_time_machine
from backend.repositories.indicator_repo import IndicatorRepository
from backend.repositories.score_repo import ScoreRepository
from backend.repositories.stock_repo import StockRepository
from backend.repositories.system_repo import SystemRepository
from backend.routes.sync import register_cache_clearer
from backend.services.top_picks_service import TopPicksService
from backend.services.v4_candidates_service import V4CandidatesService
from backend.services.v4_meta_service import V4MetaService
from backend.services.v4_stock_detail_service import V4StockDetailService
from backend.services.legacy_service import LegacyStockDetailService, SmartScanService, HealthService
from core import config
from core.ai import get_model_version, predict_prob
from core.alerts import check_smart_conditions
from core.analysis import generate_analysis_report
from core.data import standardize_ticker
from core.features import compute_all_indicators
from core.logger import setup_logger
from core.utils import safe_float

router = APIRouter()
logger = setup_logger("backend.stock")

score_repo = ScoreRepository()
indicator_repo = IndicatorRepository()
stock_repo = StockRepository()
system_repo = SystemRepository()
top_picks_service = TopPicksService(score_repo=score_repo, stock_repo=stock_repo)
v4_candidates_service = V4CandidatesService(
    score_repo=score_repo,
    indicator_repo=indicator_repo,
    stock_repo=stock_repo,
    system_repo=system_repo,
)
v4_stock_detail_service = V4StockDetailService(
    score_repo=score_repo,
    indicator_repo=indicator_repo,
    stock_repo=stock_repo,
    system_repo=system_repo,
)
v4_meta_service = V4MetaService(
    score_repo=score_repo,
    indicator_repo=indicator_repo,
    stock_repo=stock_repo,
)
legacy_stock_detail_service = LegacyStockDetailService(score_repo=score_repo, stock_repo=stock_repo)
smart_scan_service = SmartScanService(score_repo=score_repo, stock_repo=stock_repo, indicator_repo=indicator_repo)
health_service = HealthService(system_repo=system_repo)


def clear_api_caches() -> None:
    v4_candidates_service.clear_cache()
    v4_stock_detail_service.clear_cache()


register_cache_clearer(clear_api_caches)


@router.get("/api/stocks")
def search_stocks(q: Optional[str] = None):
    all_stocks = stock_repo.get_all_tw_stocks()
    if not q:
        return all_stocks[:50]

    q = q.lower()
    filtered = [s for s in all_stocks if q in s["code"].lower() or q in s["name"].lower()]
    return filtered[:20]


@router.get("/api/models")
def get_model_history_list():
    from core.ai import list_available_models

    return list_available_models()


@router.get("/api/search")
def search_stocks_global_api(q: str = Query(..., min_length=1)):
    from core.data import search_stocks_global

    return search_stocks_global(q)


@router.get("/api/init")
def get_init_data():
    t0 = time.time()

    from core.market import get_market_status
    from core.ai import list_available_models

    market = get_market_status()
    picks = get_top_picks(sort="score")
    models = list_available_models()
    curr_sync = system_repo.get_sync_status()

    total_time = time.time() - t0
    logger.info("Consolidated Init took %.4fs", total_time)

    return {
        "market": market,
        "top_picks": picks,
        "models": models,
        "sync": curr_sync,
        "perf_ms": int(total_time * 1000),
    }


@router.get("/api/top_picks")
def get_top_picks(sort: str = "score", version: Optional[str] = None):
    return top_picks_service.get_top_picks(sort=sort, version=version, limit=50)


@router.get("/api/stock/{ticker}")
def get_stock_detail(ticker: str):
    if not _TICKER_RE.match(ticker.upper()):
        raise HTTPException(status_code=422, detail=f"Invalid ticker format: {ticker!r}")
    return legacy_stock_detail_service.get_stock_detail(ticker=ticker)


@router.get("/api/stock/{ticker}/verify")
def verify_stock_detail(ticker: str, refresh_db: bool = False):
    return legacy_stock_detail_service.verify_stock_detail(ticker=ticker, refresh_db=refresh_db)


@router.get("/api/backtest")
@limiter.limit(_RATE_BACKTEST)
def run_backtest_simulation(request: Request, days: int = 30, version: Optional[str] = None):
    try:
        return run_time_machine(days_ago=days, limit=100, version=version)
    except Exception as e:
        logger.error("Backtest API Error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/smart_scan")
def smart_scan(request: Request, criteria: list[str] = []):
    # Lightweight CSRF defense: require XMLHttpRequest header on POST (M5).
    # The app has no cookie auth, so full CSRF tokens are not needed, but this
    # header blocks naive cross-site form submissions and direct browser POSTs.
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        raise HTTPException(status_code=403, detail="Missing X-Requested-With header")
    return smart_scan_service.smart_scan(criteria=criteria)


@router.get("/api/health")
def health_check():
    return health_service.get_health()


@router.get("/api/v4/sniper/candidates")
@limiter.limit(_RATE_CANDIDATES)
def get_v4_candidates(request: Request, limit: int = 50, sort: str = "score", version: Optional[str] = None):
    try:
        if sort not in {"score", "ai"}:
            raise HTTPException(status_code=422, detail="sort must be one of: score, ai")
        return v4_candidates_service.get_candidates(limit=limit, sort=sort, version=version)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("API ERROR: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/v4/stock/{ticker}")
def get_v4_stock_detail(ticker: str):
    if not _TICKER_RE.match(ticker.upper()):
        raise HTTPException(status_code=422, detail=f"Invalid ticker format: {ticker!r}")
    return v4_stock_detail_service.get_stock_detail(ticker=ticker)


@router.get("/api/v4/meta")
@limiter.limit(_RATE_META)
def get_v4_meta(request: Request, tickers: str = Query(..., min_length=1, description="Comma-separated ticker list")):
    raw = [item.strip() for item in tickers.split(",")]
    requested_pairs: list[tuple[str, str]] = []
    normalized: list[str] = []
    seen: set[str] = set()
    for ticker in raw:
        if not ticker:
            continue
        upper = ticker.upper()
        if not _TICKER_RE.match(upper):
            raise HTTPException(status_code=422, detail=f"Invalid ticker format: {ticker!r}")
        normalized_ticker = standardize_ticker(upper)
        requested_pairs.append((ticker, normalized_ticker))
        if normalized_ticker in seen:
            continue
        seen.add(normalized_ticker)
        normalized.append(normalized_ticker)

    if not requested_pairs:
        raise HTTPException(status_code=422, detail="At least one ticker is required")
    if len(normalized) > 100:
        raise HTTPException(status_code=422, detail="Maximum 100 tickers per request")
    # Pass pre-normalized pairs — service no longer re-normalizes (B1: single-pass)
    return v4_meta_service.get_meta(requested_pairs=requested_pairs)
