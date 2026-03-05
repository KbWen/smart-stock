import time
from datetime import datetime
from typing import Any, Optional, List

from fastapi import HTTPException

from backend.repositories.indicator_repo import IndicatorRepository
from backend.repositories.score_repo import ScoreRepository
from backend.repositories.stock_repo import StockRepository
from backend.repositories.system_repo import SystemRepository
from core.ai import predict_prob, get_model_version
from core.analysis import generate_analysis_report
from core.alerts import check_smart_conditions
from core.features import compute_all_indicators
from core.utils import safe_float
from core import config

class LegacyStockDetailService:
    def __init__(self, score_repo: ScoreRepository, stock_repo: StockRepository):
        self.score_repo = score_repo
        self.stock_repo = stock_repo
        from core.ai import predict_prob
        from core.analysis import generate_analysis_report
        self.predict_prob = predict_prob
        self.generate_analysis_report = generate_analysis_report

    def get_stock_detail(self, ticker: str) -> dict:
        df = self.stock_repo.load_price_history(ticker)
        if df.empty:
            df = self.stock_repo.fetch_price_history(ticker)
        if df.empty:
            raise HTTPException(status_code=404, detail="Stock not found")

        from core.indicators_v2 import compute_v4_indicators
        from core.rise_score_v2 import calculate_rise_score_v2

        df = compute_v4_indicators(df)
        df = calculate_rise_score_v2(df)
        df = df.fillna(0)
        last_row = df.iloc[-1]
        
        score = {
            "total_score": safe_float(last_row.get("total_score_v2", 0)),
            "trend_score": safe_float(last_row.get("trend_score_v2", 0)),
            "momentum_score": safe_float(last_row.get("momentum_score_v2", 0)),
            "volatility_score": safe_float(last_row.get("volatility_score_v2", 0)),
        }

        prev_row = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
        analysis_report = self.generate_analysis_report(
            df.iloc[-1],
            prev_row,
            score["trend_score"],
            score["momentum_score"],
            score["volatility_score"],
        )
        score["analysis"] = analysis_report

        ai_result = self.predict_prob(df)
        ai_prob = 0.0
        ai_details = {}

        if isinstance(ai_result, dict):
            ai_prob = ai_result.get("prob", 0.0)
            ai_details = ai_result.get("details", {})
        elif isinstance(ai_result, float):
            ai_prob = ai_result

        score["ai_details"] = ai_details

        last_price = float(last_row.get("close", 0) or 0)
        history = df.tail(30)[["date", "close", "volume"]].to_dict("records")
        for h in history:
            if hasattr(h["date"], "strftime"):
                h["date"] = h["date"].strftime("%Y-%m-%d")

        change_percent = 0.0
        if len(df) > 1 and float(df.iloc[-2].get("close", 0) or 0) != 0:
            prev_close = float(df.iloc[-2]["close"])
            change_percent = ((last_price - prev_close) / prev_close) * 100

        score["last_price"] = round(last_price, 4)
        score["change_percent"] = round(change_percent, 4)

        db_score = self.score_repo.get_latest_score(ticker)
        db_updated_at = db_score.get("updated_at") if db_score else None

        return {
            "ticker": ticker,
            "last_price": round(last_price, 4),
            "change_percent": round(change_percent, 4),
            "updated_at": db_updated_at,
            "score": score,
            "ai_probability": ai_prob,
            "ai_target_price": round(last_price * 1.15, 2) if last_price else 0,
            "ai_stop_price": round(last_price * 0.95, 2) if last_price else 0,
            "history": history,
        }

    def verify_stock_detail(self, ticker: str, refresh_db: bool = False) -> dict:
        db_score = self.score_repo.get_latest_score(ticker)
        if not db_score:
            raise HTTPException(status_code=404, detail="Stock score not found in DB")

        realtime_df = self.stock_repo.fetch_price_history(ticker, days=30, force_download=True)
        if realtime_df.empty:
            raise HTTPException(status_code=404, detail="Unable to fetch realtime stock data")

        realtime_last = float(realtime_df.iloc[-1].get("close", 0) or 0)
        realtime_change = 0.0
        if len(realtime_df) > 1 and float(realtime_df.iloc[-2].get("close", 0) or 0) != 0:
            prev_close = float(realtime_df.iloc[-2].get("close", 0) or 0)
            realtime_change = ((realtime_last - prev_close) / prev_close) * 100

        db_last = float(db_score.get("last_price", 0) or 0)
        db_change = float(db_score.get("change_percent", 0) or 0)

        last_price_diff_pct = abs((db_last - realtime_last) / realtime_last * 100) if realtime_last else 0
        change_diff_abs = abs(db_change - realtime_change)

        tolerance_percent = 0.5
        within_tolerance = (
            last_price_diff_pct <= tolerance_percent and change_diff_abs <= tolerance_percent
        )

        if refresh_db:
            model_version = db_score.get("model_version")
            refresh_score_payload = {
                "total_score": db_score.get("total_score", 0),
                "trend_score": db_score.get("trend_score", 0),
                "momentum_score": db_score.get("momentum_score", 0),
                "volatility_score": db_score.get("volatility_score", 0),
                "last_price": realtime_last,
                "change_percent": realtime_change,
            }
            self.score_repo.save_score(
                ticker,
                refresh_score_payload,
                ai_prob=db_score.get("ai_probability", 0),
                model_version=model_version,
            )
            db_score = self.score_repo.get_latest_score(ticker, model_version=model_version)

        return {
            "ticker": ticker,
            "within_tolerance": within_tolerance,
            "tolerance_percent": tolerance_percent,
            "database": {
                "last_price": db_last,
                "change_percent": db_change,
                "updated_at": db_score.get("updated_at") if db_score else None,
                "model_version": db_score.get("model_version") if db_score else None,
            },
            "realtime": {
                "last_price": round(realtime_last, 4),
                "change_percent": round(realtime_change, 4),
            },
            "diff": {
                "last_price_pct": round(last_price_diff_pct, 4),
                "change_percent_abs": round(change_diff_abs, 4),
            },
        }

class SmartScanService:
    def __init__(self, score_repo: ScoreRepository, stock_repo: StockRepository, indicator_repo: IndicatorRepository):
        self.score_repo = score_repo
        self.stock_repo = stock_repo
        self.indicator_repo = indicator_repo

    def smart_scan(self, criteria: List[str]) -> List[dict]:
        candidates = self.score_repo.get_top_scores(limit=100, sort_by="score")
        all_stocks = self.stock_repo.get_all_tw_stocks()
        name_map = {s["code"]: s["name"] for s in all_stocks}

        results = []
        for c in candidates:
            ticker = c["ticker"]
            try:
                cached_indicators = self.indicator_repo.load_for_ticker(ticker)
                if cached_indicators:
                    df = self.stock_repo.load_price_history(ticker)
                    if df.empty or len(df) < 60:
                        continue
                    if len(df) > 300:
                        df = df.tail(300).copy()

                    df = compute_all_indicators(df)
                    ai_prob = c.get("ai_probability", 0)
                    if check_smart_conditions(df, ai_prob, criteria):
                        results.append({
                            "ticker": ticker,
                            "name": name_map.get(ticker, ticker),
                            "ai_probability": ai_prob,
                            "model_version": c.get("model_version", "legacy"),
                            "last_sync": c.get("last_sync"),
                            "score": c,
                            "price": c.get("last_price", 0),
                            "ai_target_price": round(c.get("last_price", 0) * 1.15, 2),
                            "ai_stop_price": round(c.get("last_price", 0) * 0.95, 2),
                            "matches": criteria,
                        })
            except Exception:
                continue
        return results

class HealthService:
    def __init__(self, system_repo: SystemRepository):
        self.system_repo = system_repo

    def get_health(self) -> dict:
        health_status = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "db": "disconnected",
            "model_version": get_model_version(),
            "concurrency_workers": config.CONCURRENCY_WORKERS,
        }
        status, db_value = self.system_repo.check_db_health()
        health_status["status"] = status
        health_status["db"] = db_value
        return health_status
