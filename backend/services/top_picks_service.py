from typing import Any, Optional

from backend.repositories.score_repo import ScoreRepository
from backend.repositories.stock_repo import StockRepository


class TopPicksService:
    def __init__(
        self,
        score_repo: Optional[ScoreRepository] = None,
        stock_repo: Optional[StockRepository] = None,
    ) -> None:
        self.score_repo = score_repo or ScoreRepository()
        self.stock_repo = stock_repo or StockRepository()

    def get_top_picks(self, sort: str = "score", version: Optional[str] = None, limit: int = 50) -> list[dict[str, Any]]:
        picks = self.score_repo.get_top_scores(limit=limit, sort_by=sort, version=version)

        if not picks:
            return []

        result: list[dict[str, Any]] = []
        for p in picks:
            last_price = p.get("last_price", 0) or 0
            ai_prob = p.get("ai_probability") or 0
            result.append(
                {
                    "ticker": p["ticker"],
                    "name": self.stock_repo.get_stock_name(p["ticker"]),
                    "ai_probability": ai_prob,
                    "model_version": p.get("model_version", "legacy"),
                    "last_sync": p.get("last_sync"),
                    "ai_target_price": round(last_price * 1.15, 2) if last_price else 0,
                    "ai_stop_price": round(last_price * 0.95, 2) if last_price else 0,
                    "score": {
                        "total_score": p["total_score"],
                        "trend_score": p["trend_score"],
                        "momentum_score": p["momentum_score"],
                        "volatility_score": p["volatility_score"],
                        "last_price": last_price,
                        "change_percent": p.get("change_percent", 0) or 0,
                    },
                }
            )
        return result
