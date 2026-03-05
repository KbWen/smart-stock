from typing import Any

from core.data import load_indicators_for_tickers, load_indicators_from_db


class IndicatorRepository:
    def load_for_tickers(self, tickers: list[str]) -> dict[str, dict[str, Any]]:
        return load_indicators_for_tickers(tickers)

    def load_for_ticker(self, ticker: str) -> dict[str, Any]:
        return load_indicators_from_db(ticker) or {}
