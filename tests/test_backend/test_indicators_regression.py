"""
Regression tests for indicator edge-case bug fixes (eng-audit-r4).

Covered fixes:
  FIX-A  core/analysis.py:42    KD stochastic div-by-zero on flat price window
  FIX-B  core/analysis.py:60    bb_percent div-by-zero when std=0
  FIX-C  core/indicators_v2.py  MACD/ATR normalised by close with no zero-guard
  FIX-D  system_repo health-check connection always closed on exception
  FIX-E  score_repo deterministic row when updated_at ties
"""
import math
import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flat_ohlcv(n: int = 20, price: float = 100.0) -> pd.DataFrame:
    """OHLCV DataFrame where every bar has identical OHLC (zero range)."""
    return pd.DataFrame({
        "open":   [price] * n,
        "high":   [price] * n,
        "low":    [price] * n,
        "close":  [price] * n,
        "volume": [1_000_000] * n,
    })


def _normal_ohlcv(n: int = 120) -> pd.DataFrame:
    """OHLCV DataFrame with realistic varying prices."""
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    close = np.clip(close, 10, None)
    return pd.DataFrame({
        "open":   close * 0.999,
        "high":   close * 1.005,
        "low":    close * 0.995,
        "close":  close,
        "volume": rng.integers(500_000, 2_000_000, n).astype(float),
    })


def _ohlcv_with_zero_close(n: int = 30) -> pd.DataFrame:
    """Normal OHLCV with one row where close=0 (data-quality edge case)."""
    df = _normal_ohlcv(n)
    df.loc[15, "close"] = 0.0
    df.loc[15, "open"]  = 0.0
    df.loc[15, "high"]  = 0.0
    df.loc[15, "low"]   = 0.0
    return df


def _has_no_inf(series: pd.Series) -> bool:
    return not np.isinf(series.dropna()).any()


# ---------------------------------------------------------------------------
# FIX-A: KD stochastic — flat price window must not produce NaN/inf
# ---------------------------------------------------------------------------

class TestKDFlatPriceRegression:
    """calculate_kd must be numerically stable when high == low over the window."""

    def test_flat_prices_k_no_nan(self):
        from core.analysis import calculate_kd
        df = _flat_ohlcv(20)
        result = calculate_kd(df)
        finite_k = result["k"].dropna()
        assert len(finite_k) > 0, "Expected some finite K values after warmup"
        assert _has_no_inf(result["k"]), "K contains inf on flat prices"

    def test_flat_prices_d_no_nan(self):
        from core.analysis import calculate_kd
        df = _flat_ohlcv(20)
        result = calculate_kd(df)
        finite_d = result["d"].dropna()
        assert len(finite_d) > 0, "Expected some finite D values after warmup"
        assert _has_no_inf(result["d"]), "D contains inf on flat prices"

    def test_flat_prices_k_bounded(self):
        """RSV on flat prices should yield 50 (midpoint), K/D should stay in [0, 100]."""
        from core.analysis import calculate_kd
        df = _flat_ohlcv(30)
        result = calculate_kd(df)
        k_finite = result["k"].dropna()
        assert (k_finite >= 0).all() and (k_finite <= 100).all(), \
            f"K out of [0,100] range: {k_finite.describe()}"

    def test_normal_prices_unchanged(self):
        """Regression guard: normal prices still produce valid K/D."""
        from core.analysis import calculate_kd
        df = _normal_ohlcv(60)
        result = calculate_kd(df)
        assert _has_no_inf(result["k"])
        assert _has_no_inf(result["d"])


# ---------------------------------------------------------------------------
# FIX-B: Bollinger Band bb_percent — zero std must not produce inf
# ---------------------------------------------------------------------------

class TestBollingerFlatPriceRegression:
    """calculate_bollinger must not emit inf/NaN when std=0 over the window."""

    def test_flat_prices_bb_percent_no_inf(self):
        from core.analysis import calculate_bollinger
        df = _flat_ohlcv(30)
        result = calculate_bollinger(df)
        assert _has_no_inf(result["bb_percent"]), \
            "bb_percent contains inf on flat prices (div-by-zero regression)"

    def test_flat_prices_bb_width_no_inf(self):
        """bb_width was already guarded; ensure it stays safe."""
        from core.analysis import calculate_bollinger
        df = _flat_ohlcv(30)
        result = calculate_bollinger(df)
        assert _has_no_inf(result["bb_width"]), "bb_width contains inf on flat prices"

    def test_flat_prices_bb_percent_bounded_or_nan(self):
        """With zero-width bands the result should be NaN (0/0+eps ≈ 0) or finite."""
        from core.analysis import calculate_bollinger
        df = _flat_ohlcv(30)
        result = calculate_bollinger(df)
        valid = result["bb_percent"].dropna()
        assert _has_no_inf(valid), "bb_percent must not be inf"
        # When upper == lower == close, (close - lower) / epsilon ≈ 0
        assert (valid.abs() < 1e6).all(), "bb_percent values unreasonably large"

    def test_normal_prices_bb_percent_range(self):
        """Regression guard: bb_percent on normal data stays roughly in [0, 1]."""
        from core.analysis import calculate_bollinger
        df = _normal_ohlcv(60)
        result = calculate_bollinger(df)
        valid = result["bb_percent"].dropna()
        assert _has_no_inf(valid)
        # Reasonable range — can exceed [0,1] during extreme moves, but not by much
        assert valid.abs().max() < 5, "bb_percent suspiciously large on normal data"


# ---------------------------------------------------------------------------
# FIX-C: indicators_v2 — MACD/ATR no inf when close contains zero
# ---------------------------------------------------------------------------

class TestIndicatorsV2ZeroCloseRegression:
    """compute_v4_indicators must not produce inf in normalized columns when close=0."""

    def test_zero_close_no_inf_in_norm_macd_hist(self):
        from core.indicators_v2 import compute_v4_indicators
        df = _ohlcv_with_zero_close(60)
        result = compute_v4_indicators(df)
        assert _has_no_inf(result["norm_macd_hist"]), \
            "norm_macd_hist contains inf when close=0 (div regression)"

    def test_zero_close_no_inf_in_atr_percent(self):
        from core.indicators_v2 import compute_v4_indicators
        df = _ohlcv_with_zero_close(60)
        result = compute_v4_indicators(df)
        assert _has_no_inf(result["atr_percent"]), \
            "atr_percent contains inf when close=0 (div regression)"

    def test_normal_data_no_inf_any_column(self):
        """Regression guard: no inf in any computed column on normal data."""
        from core.indicators_v2 import compute_v4_indicators
        df = _normal_ohlcv(120)
        result = compute_v4_indicators(df)
        numeric_cols = result.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            assert _has_no_inf(result[col]), \
                f"Column '{col}' contains inf on normal data"


# ---------------------------------------------------------------------------
# FIX-D: system_repo — check_db_health does not leak on exception
# ---------------------------------------------------------------------------

class TestSystemRepoHealthCheckRegression:
    """check_db_health must close the connection even when execute() raises."""

    def test_health_check_returns_error_tuple_on_exception(self, monkeypatch):
        """When get_db_connection().execute() raises, return ('error', msg)."""
        import backend.repositories.system_repo as sr_module
        from backend.repositories.system_repo import SystemRepository

        closed_calls = []

        class _FakeConn:
            def execute(self, _sql):
                raise RuntimeError("DB locked")
            def close(self):
                closed_calls.append(True)

        monkeypatch.setattr(sr_module, "get_db_connection", lambda: _FakeConn())

        repo = SystemRepository()
        status, msg = repo.check_db_health()
        assert status == "error"
        assert "DB locked" in msg

    def test_health_check_closes_connection_on_exception(self, monkeypatch):
        """Connection.close() must be called even when execute() raises (no leak)."""
        import backend.repositories.system_repo as sr_module
        from backend.repositories.system_repo import SystemRepository

        closed_calls = []

        class _FakeConn:
            def execute(self, _sql):
                raise RuntimeError("DB locked")
            def close(self):
                closed_calls.append(True)

        monkeypatch.setattr(sr_module, "get_db_connection", lambda: _FakeConn())

        repo = SystemRepository()
        repo.check_db_health()
        assert len(closed_calls) == 1, \
            "Connection was not closed after exception (leak regression)"

    def test_health_check_ok_path(self, monkeypatch):
        """Happy path still returns ('ok', 'connected')."""
        import backend.repositories.system_repo as sr_module
        from backend.repositories.system_repo import SystemRepository

        closed_calls = []

        class _FakeConn:
            def execute(self, _sql):
                return self
            def close(self):
                closed_calls.append(True)

        monkeypatch.setattr(sr_module, "get_db_connection", lambda: _FakeConn())

        repo = SystemRepository()
        status, msg = repo.check_db_health()
        assert status == "ok"
        assert len(closed_calls) == 1


# ---------------------------------------------------------------------------
# FIX-E: score_repo — deterministic tie-breaking when updated_at is identical
# ---------------------------------------------------------------------------

class TestScoreRepoDeterministicTieBreaking:
    """load_latest_scores_for_tickers must return a deterministic row when multiple
    rows share the same updated_at (ORDER BY rowid DESC picks most-recently inserted)."""

    def _make_db_with_ties(self, conn, ticker: str):
        """Insert two rows for the same ticker with identical updated_at."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_scores (
                ticker TEXT,
                updated_at TEXT,
                ai_probability REAL,
                total_score REAL,
                trend_score REAL,
                momentum_score REAL,
                volatility_score REAL,
                last_price REAL,
                change_percent REAL,
                model_version TEXT,
                ai_details TEXT
            )
        """)
        ts = "2026-03-28 10:00:00"
        conn.execute(
            "INSERT INTO stock_scores (ticker, updated_at, ai_probability, model_version) VALUES (?,?,?,?)",
            (ticker, ts, 0.1, "v1"),
        )
        conn.execute(
            "INSERT INTO stock_scores (ticker, updated_at, ai_probability, model_version) VALUES (?,?,?,?)",
            (ticker, ts, 0.9, "v1"),  # higher rowid — should win
        )
        conn.commit()

    def test_tie_returns_highest_rowid(self, tmp_path, monkeypatch):
        """When two rows share updated_at, the one with higher rowid is returned."""
        import sqlite3
        import backend.repositories.score_repo as sr_module
        from backend.repositories.score_repo import ScoreRepository

        db_path = str(tmp_path / "test.db")
        conn_main = sqlite3.connect(db_path)
        conn_main.row_factory = sqlite3.Row
        self._make_db_with_ties(conn_main, "2330")
        conn_main.close()

        def _fake_conn():
            c = sqlite3.connect(db_path)
            c.row_factory = sqlite3.Row
            return c

        monkeypatch.setattr(sr_module, "get_db_connection", _fake_conn)

        repo = ScoreRepository()
        result = repo.load_latest_scores_for_tickers(["2330"])
        assert "2330" in result
        # rowid DESC means the second insert (ai_probability=0.9) wins
        assert abs(result["2330"]["ai_probability"] - 0.9) < 1e-6, \
            "Expected highest-rowid row (ai_prob=0.9) but got different row"

    def test_tie_result_is_stable_across_calls(self, tmp_path, monkeypatch):
        """Multiple calls must return the same row (determinism check)."""
        import sqlite3
        import backend.repositories.score_repo as sr_module
        from backend.repositories.score_repo import ScoreRepository

        db_path = str(tmp_path / "test.db")
        conn_main = sqlite3.connect(db_path)
        conn_main.row_factory = sqlite3.Row
        self._make_db_with_ties(conn_main, "2330")
        conn_main.close()

        def _fake_conn():
            c = sqlite3.connect(db_path)
            c.row_factory = sqlite3.Row
            return c

        monkeypatch.setattr(sr_module, "get_db_connection", _fake_conn)

        repo = ScoreRepository()
        results = [repo.load_latest_scores_for_tickers(["2330"])["2330"]["ai_probability"]
                   for _ in range(5)]
        assert len(set(results)) == 1, \
            f"Non-deterministic results across calls: {results}"
