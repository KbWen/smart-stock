import threading
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException

from backend.repositories.indicator_repo import IndicatorRepository
from backend.repositories.score_repo import ScoreRepository
from backend.repositories.stock_repo import StockRepository
from backend.repositories.system_repo import SystemRepository
from core.ai import predict_prob
from core.utils import safe_float


class V4StockDetailService:
    def __init__(
        self,
        score_repo: Optional[ScoreRepository] = None,
        indicator_repo: Optional[IndicatorRepository] = None,
        stock_repo: Optional[StockRepository] = None,
        system_repo: Optional[SystemRepository] = None,
        cache_ttl_seconds: int = 300,  # 5 min: reduces redundant DB reads for repeat ticker lookups
    ) -> None:
        self.score_repo = score_repo or ScoreRepository()
        self.indicator_repo = indicator_repo or IndicatorRepository()
        self.stock_repo = stock_repo or StockRepository()
        self.system_repo = system_repo or SystemRepository()
        self.predict_prob = predict_prob
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_lock = threading.Lock()

    @staticmethod
    def _to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y"}
        return False

    @staticmethod
    def _parse_db_datetime(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str) or not value.strip():
            return None

        raw = value.strip()
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None

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

    _HISTORY_CACHE_TTL_SECONDS: int = 60  # spec: visual-upgrade-phase1 AC2

    def _write_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._cache_lock:
            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + (ttl if ttl is not None else self.cache_ttl_seconds),
            }

    def get_stock_history(self, ticker: str, days: int = 90) -> list[dict[str, Any]]:
        cache_key = f"history:{ticker}"
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        from core.indicators_v2 import compute_v4_indicators
        from core.rise_score_v2 import calculate_rise_score_v2

        df = self.stock_repo.load_price_history(ticker)
        if df.empty:
            df = self.stock_repo.fetch_price_history(ticker)
        if df.empty:
            raise HTTPException(status_code=404, detail="Stock not found")

        df = compute_v4_indicators(df)
        df = calculate_rise_score_v2(df)
        df = df.tail(days)

        result = []
        for _, row in df.iterrows():
            date_val = row.get("date")
            if hasattr(date_val, "strftime"):
                date_str = date_val.strftime("%Y-%m-%d")
            else:
                date_str = str(date_val)[:10]
            result.append({
                "date": date_str,
                "close": round(safe_float(row.get("close", 0)), 2),
                "is_squeeze": self._to_bool(row.get("is_squeeze", False)),
                "golden_cross": self._to_bool(row.get("kd_cross_flag", False)),
                "volume_spike": bool(safe_float(row.get("rel_vol", 1.0)) > 1.5),
            })

        self._write_cache(cache_key, result, ttl=self._HISTORY_CACHE_TTL_SECONDS)
        return result

    def get_stock_detail(self, ticker: str) -> dict[str, Any]:
        cache_version = self.system_repo.get_sync_epoch()
        cache_key = f"v4_stock_detail:{ticker}:sync={cache_version}"
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        db_score = self.score_repo.get_latest_score(ticker)
        cached_indicators = self.indicator_repo.load_for_ticker(ticker)

        db_updated_at = self._parse_db_datetime(db_score.get("updated_at")) if db_score else None
        if db_score and db_updated_at and datetime.now() - db_updated_at < timedelta(hours=6):
            price = safe_float(db_score.get("last_price", 0))
            ai_prob = safe_float(db_score.get("ai_probability", 0))
            squeeze_flag = self._to_bool(cached_indicators.get("is_squeeze"))
            golden_cross_flag = self._to_bool(cached_indicators.get("kd_cross_flag"))
            rel_vol = safe_float(cached_indicators.get("rel_vol", 1.0))
            volume_spike_flag = bool(rel_vol > 1.5)

            analyst_text = []
            if squeeze_flag:
                analyst_text.append("Squeeze Alert: Low volatility detected, expecting a major move.")
            if volume_spike_flag:
                analyst_text.append("Volume Spike: Heavy trading activity detected.")

            response = {
                "ticker": ticker,
                "name": self.stock_repo.get_stock_name(ticker),
                "price": price,
                "updated_at": db_score.get("updated_at"),
                "rise_score_breakdown": {
                    "total": round(safe_float(db_score.get("total_score", 0)), 1),
                    "trend": round(safe_float(db_score.get("trend_score", 0)), 1),
                    "momentum": round(safe_float(db_score.get("momentum_score", 0)), 1),
                    "volatility": round(safe_float(db_score.get("volatility_score", 0)), 1),
                },
                "ai_probability": round(safe_float(ai_prob) * 100, 1),
                "analyst_summary": " ".join(analyst_text) if analyst_text else "Market is neutral. Watch for setup signals.",
                "signals": {
                    "squeeze": squeeze_flag,
                    "golden_cross": golden_cross_flag,
                    "volume_spike": volume_spike_flag,
                },
            }
            self._write_cache(cache_key, response)
            return response

        from core.indicators_v2 import compute_v4_indicators
        from core.rise_score_v2 import calculate_rise_score_v2

        df = self.stock_repo.load_price_history(ticker)
        if df.empty:
            df = self.stock_repo.fetch_price_history(ticker)
        if df.empty:
            raise HTTPException(status_code=404, detail="Stock not found")

        df = compute_v4_indicators(df)
        df = calculate_rise_score_v2(df)
        latest = df.iloc[-1]

        ai_result = self.predict_prob(df)
        ai_prob = 0.0
        if isinstance(ai_result, dict):
            ai_prob = ai_result.get("prob", 0)
        elif isinstance(ai_result, float):
            ai_prob = ai_result

        squeeze_flag = self._to_bool(cached_indicators.get("is_squeeze")) if cached_indicators else self._to_bool(latest.get("is_squeeze", False))
        golden_cross_flag = (
            self._to_bool(cached_indicators.get("kd_cross_flag"))
            if cached_indicators
            else self._to_bool(latest.get("kd_cross_flag", False))
        )
        rel_vol = safe_float(cached_indicators.get("rel_vol")) if cached_indicators else safe_float(latest.get("rel_vol", 1.0))
        volume_spike_flag = bool(rel_vol > 1.5)

        analyst_text = []
        if latest["trend_alignment"] == 1:
            analyst_text.append("Strong Uptrend: Price is consistently above SMA20 & SMA60.")
        elif latest["sma20_slope"] > 0:
            analyst_text.append("Recovering: Price is building momentum above SMA20.")

        if 40 <= latest["rsi"] <= 70:
            analyst_text.append("Momentum: RSI is in the bullish zone (40-70).")
        elif latest["rsi"] > 80:
            analyst_text.append("Overheated: RSI indicates overbought territory.")

        if squeeze_flag:
            analyst_text.append("Squeeze Alert: Low volatility detected, expecting a major move.")
        elif volume_spike_flag:
            analyst_text.append("Volume Spike: Heavy trading activity detected.")

        response = {
            "ticker": ticker,
            "name": self.stock_repo.get_stock_name(ticker),
            "price": safe_float(latest["close"]),
            "updated_at": db_score.get("updated_at") if db_score else None,
            "rise_score_breakdown": {
                "total": round(safe_float(latest["total_score_v2"]), 1),
                "trend": round(safe_float(latest["trend_score_v2"]), 1),
                "momentum": round(safe_float(latest["momentum_score_v2"]), 1),
                "volatility": round(safe_float(latest["volatility_score_v2"]), 1),
            },
            "ai_probability": round(safe_float(ai_prob) * 100, 1),
            "analyst_summary": " ".join(analyst_text) if analyst_text else "Market is neutral. Watch for setup signals.",
            "signals": {
                "squeeze": squeeze_flag,
                "golden_cross": golden_cross_flag,
                "volume_spike": volume_spike_flag,
            },
        }
        self._write_cache(cache_key, response)
        return response
