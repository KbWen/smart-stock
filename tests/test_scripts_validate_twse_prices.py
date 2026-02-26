import importlib
import sys

import pandas as pd

# test_backtest may inject a fake core.data module during collection.
if 'core.data' in sys.modules and not hasattr(sys.modules['core.data'], 'standardize_ticker'):
    del sys.modules['core.data']

v = importlib.import_module('scripts.validate_twse_prices')


def test_validate_prices_reports_mismatch(monkeypatch, capsys):
    monkeypatch.setattr(
        v,
        "_get_db_recent_closes",
        lambda ticker, n: pd.DataFrame({"date": ["20260220", "20260221"], "close": [100.0, 101.0]}),
    )

    def fake_fetch(d, stock):
        return 100.0 if d == "20260220" else 102.0

    monkeypatch.setattr(v, "_fetch_twse_close", fake_fetch)

    code = v.validate_prices("2330.TW", trading_days=2)
    out = capsys.readouterr().out

    assert code == 1
    assert "Mismatches found" in out
    assert "20260221" in out
