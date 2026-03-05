from typing import Any, Optional

from core.data import (
    get_db_connection,
    get_latest_score_for_ticker,
    get_top_scores_from_db,
    save_score_to_db,
)


class ScoreRepository:
    def get_top_scores(self, limit: int, sort_by: str, version: Optional[str] = None) -> list[dict[str, Any]]:
        return get_top_scores_from_db(limit=limit, sort_by=sort_by, version=version)

    def get_latest_score(self, ticker: str, model_version: Optional[str] = None) -> Optional[dict[str, Any]]:
        return get_latest_score_for_ticker(ticker, model_version=model_version)

    def save_score(
        self,
        ticker: str,
        score_payload: dict[str, Any],
        ai_prob: float = 0.0,
        model_version: Optional[str] = None,
    ) -> None:
        save_score_to_db(ticker, score_payload, ai_prob=ai_prob, model_version=model_version)

    def load_latest_scores_for_tickers(self, tickers: list[str]) -> dict[str, dict[str, Any]]:
        if not tickers:
            return {}

        conn = get_db_connection()
        try:
            placeholders = ",".join(["?"] * len(tickers))
            query = f"""
            SELECT s.*
            FROM stock_scores s
            WHERE s.ticker IN ({placeholders})
              AND s.updated_at = (
                SELECT MAX(s2.updated_at)
                FROM stock_scores s2
                WHERE s2.ticker = s.ticker
              )
        """
            rows = conn.execute(query, tickers).fetchall()
            result: dict[str, dict[str, Any]] = {}
            for row in rows:
                row_dict = dict(row)
                ticker = row_dict.get("ticker")
                if ticker and ticker not in result:
                    result[ticker] = row_dict
            return result
        finally:
            conn.close()
