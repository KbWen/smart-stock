from typing import Any

from core.data import fetch_stock_data, get_all_tw_stocks, get_stock_name, load_from_db


class StockRepository:
    def get_all_tw_stocks(self) -> list[dict[str, Any]]:
        return get_all_tw_stocks()

    def get_stock_name(self, ticker: str) -> str:
        return get_stock_name(ticker)

    def load_price_history(self, ticker: str):
        return load_from_db(ticker)

    def fetch_price_history(self, ticker: str, days: int = 180, force_download: bool = False):
        return fetch_stock_data(ticker, days=days, force_download=force_download)
