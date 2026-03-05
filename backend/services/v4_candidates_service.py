import threading
import time
from typing import Any, Optional

from backend.repositories.indicator_repo import IndicatorRepository
from backend.repositories.score_repo import ScoreRepository
from backend.repositories.stock_repo import StockRepository
from backend.repositories.system_repo import SystemRepository
from core.ai import predict_prob
from core.logger import setup_logger
from core.utils import safe_float


class V4CandidatesService:
    def __init__(
        self,
        score_repo: Optional[ScoreRepository] = None,
        indicator_repo: Optional[IndicatorRepository] = None,
        stock_repo: Optional[StockRepository] = None,
        system_repo: Optional[SystemRepository] = None,
        cache_ttl_seconds: int = 60,
    ) -> None:
        self.score_repo = score_repo or ScoreRepository()
        self.indicator_repo = indicator_repo or IndicatorRepository()
        self.stock_repo = stock_repo or StockRepository()
        self.system_repo = system_repo or SystemRepository()
        self.cache_ttl_seconds = cache_ttl_seconds
        self.logger = setup_logger("backend.stock")
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_lock = threading.Lock()

    def clear_cache(self) -> None:
        with self._cache_lock:
            self._cache.clear()

    def _read_cache(self, key: str):
        now = time.time()
        with self._cache_lock:
            item = self._cache.get(key)
            if not item:
                return None
            if item["expires_at"] <= now:
                self._cache.pop(key, None)
                return None
            return item["value"]

    def _write_cache(self, key: str, value: Any) -> None:
        with self._cache_lock:
            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + self.cache_ttl_seconds,
            }

    def get_candidates(self, limit: int = 50, sort: str = "score", version: Optional[str] = None) -> list[dict[str, Any]]:
        cache_version = self.system_repo.get_sync_epoch()
        cache_key = f"v4_candidates:limit={limit}:sort={sort}:version={version or 'latest'}:sync={cache_version}"
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        start_ts = time.time()
        raw_candidates = self.score_repo.get_top_scores(limit=limit * 2, sort_by=sort, version=version)
        indicators_map = self.indicator_repo.load_for_tickers([c["ticker"] for c in raw_candidates])

        results: list[dict[str, Any]] = []
        fallback_errors = 0
        for c in raw_candidates:
            ticker = c["ticker"]

            if c.get("model_version", "").startswith("v4"):
                cached_ind = indicators_map.get(ticker) or {}
                results.append(
                    {
                        "ticker": ticker,
                        "name": self.stock_repo.get_stock_name(ticker),
                        "price": round(safe_float(c.get("last_price", 0)), 2),
                        "change_percent": round(safe_float(c.get("change_percent", 0)), 2),
                        "rise_score": round(safe_float(c["total_score"]), 1),
                        "ai_prob": round(safe_float(c.get("ai_probability", 0)) * 100, 1),
                        "trend": round(safe_float(c["trend_score"]), 1),
                        "momentum": round(safe_float(c["momentum_score"]), 1),
                        "volatility": round(safe_float(c["volatility_score"]), 1),
                        "rsi_14": round(safe_float(cached_ind.get("rsi", 50)), 1),
                        "macd_diff": round(
                            safe_float((cached_ind.get("macd") or 0) - (cached_ind.get("macd_signal") or 0)),
                            2,
                        ),
                        "volume_ratio": round(safe_float(cached_ind.get("rel_vol", 1.0)), 2),
                        "updated_at": c.get("updated_at"),
                    }
                )
                if len(results) >= limit:
                    break
                continue

            try:
                from core.indicators_v2 import compute_v4_indicators
                from core.rise_score_v2 import calculate_rise_score_v2

                df = self.stock_repo.load_price_history(ticker)
                if df.empty or len(df) < 60:
                    continue
                df = compute_v4_indicators(df)
                df = calculate_rise_score_v2(df)
                latest = df.iloc[-1]
                ai_result = predict_prob(df)
                ai_prob = ai_result.get("prob", 0) if isinstance(ai_result, dict) else ai_result

                results.append(
                    {
                        "ticker": ticker,
                        "name": self.stock_repo.get_stock_name(ticker),
                        "price": safe_float(latest["close"]),
                        "change_percent": safe_float(
                            (latest["close"] - df.iloc[-2]["close"]) / df.iloc[-2]["close"] * 100 if len(df) > 1 else 0
                        ),
                        "rise_score": round(safe_float(latest["total_score_v2"]), 1),
                        "ai_prob": round(safe_float(ai_prob) * 100, 1),
                        "trend": round(safe_float(latest["trend_score_v2"]), 1),
                        "momentum": round(safe_float(latest["momentum_score_v2"]), 1),
                        "volatility": round(safe_float(latest["volatility_score_v2"]), 1),
                        "rsi_14": round(safe_float(latest.get("rsi", 50)), 1),
                        "macd_diff": round(safe_float(latest.get("macd_hist", 0)), 2),
                        "volume_ratio": round(safe_float(latest.get("rel_vol", 1.0)), 2),
                        "updated_at": c.get("updated_at"),
                    }
                )
            except Exception as e:
                fallback_errors += 1
                if fallback_errors <= 10:
                    self.logger.warning("Fallback candidate recompute failed", extra={"ticker": ticker, "error": str(e)})
                continue
            if len(results) >= limit:
                break

        elapsed_ms = round((time.time() - start_ts) * 1000, 2)
        self.logger.info(
            "Built v4 candidates payload",
            extra={
                "requested_limit": limit,
                "selected": len(results),
                "raw_count": len(raw_candidates),
                "elapsed_ms": elapsed_ms,
            },
        )
        self._write_cache(cache_key, results)
        return results
