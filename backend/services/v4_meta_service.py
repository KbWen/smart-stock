from typing import Any, Optional

from backend.repositories.indicator_repo import IndicatorRepository
from backend.repositories.score_repo import ScoreRepository
from backend.repositories.stock_repo import StockRepository
from core.ai import get_model_version
from core.utils import safe_float


class V4MetaService:
    def __init__(
        self,
        score_repo: Optional[ScoreRepository] = None,
        indicator_repo: Optional[IndicatorRepository] = None,
        stock_repo: Optional[StockRepository] = None,
    ) -> None:
        self.score_repo = score_repo or ScoreRepository()
        self.indicator_repo = indicator_repo or IndicatorRepository()
        self.stock_repo = stock_repo or StockRepository()

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

    def get_meta(
        self,
        requested_pairs: list[tuple[str, str]],
    ) -> dict[str, dict[str, dict[str, Any]]]:
        """
        Build enriched meta payload for a list of tickers.

        Args:
            requested_pairs: Pre-normalized list of (original_ticker, normalized_ticker)
                             tuples produced by the route handler. Caller is responsible
                             for normalization and deduplication (B1 — single-pass).
        """
        # Unique normalized tickers (preserve insertion order for deterministic queries)
        seen: set[str] = set()
        normalized: list[str] = []
        for _, norm in requested_pairs:
            if norm not in seen:
                seen.add(norm)
                normalized.append(norm)

        indicators_map = self.indicator_repo.load_for_tickers(normalized)
        latest_scores = self.score_repo.load_latest_scores_for_tickers(normalized)

        data: dict[str, dict[str, Any]] = {}
        for requested_ticker, normalized_ticker in requested_pairs:
            score = latest_scores.get(normalized_ticker, {})
            indicators = indicators_map.get(normalized_ticker, {})

            macd = safe_float(indicators.get("macd", 0))
            macd_signal = safe_float(indicators.get("macd_signal", 0))
            rel_vol = safe_float(indicators.get("rel_vol", 1.0))
            ai_prob = safe_float(score.get("ai_probability", 0))

            data[requested_ticker] = {
                "total_score": safe_float(score.get("total_score", 0)),
                "trend_score": safe_float(score.get("trend_score", 0)),
                "momentum_score": safe_float(score.get("momentum_score", 0)),
                "volatility_score": safe_float(score.get("volatility_score", 0)),
                "last_price": safe_float(score.get("last_price", 0)),
                "change_percent": safe_float(score.get("change_percent", 0)),
                "ai_prob": ai_prob,
                "signals": {
                    "squeeze": self._to_bool(indicators.get("is_squeeze")),
                    "golden_cross": self._to_bool(indicators.get("kd_cross_flag")),
                    "volume_spike": bool(rel_vol > 1.5),
                    "rsi": safe_float(indicators.get("rsi", 50)),
                    "macd_diff": safe_float(macd - macd_signal),
                    "rel_vol": rel_vol,
                },
                "updated_at": score.get("updated_at") or indicators.get("updated_at"),
                "model_version": (
                    score.get("model_version")
                    or indicators.get("model_version")
                    or get_model_version()
                ),
                "name": self.stock_repo.get_stock_name(normalized_ticker),
            }

        return {"data": data}
