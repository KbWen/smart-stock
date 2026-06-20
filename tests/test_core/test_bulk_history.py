"""Tests for core/bulk_history.py — TWSE/TPEX per-day bulk backfill (v1 #4).

Parsers are pure; HTTP is injected so tests never touch the network. Column
indices below were validated against live TWSE MI_INDEX / TPEX daily-close data.
"""
from datetime import datetime

from core import bulk_history as bh

TWSE_FIELDS = ["證券代號", "證券名稱", "成交股數", "成交筆數", "成交金額",
               "開盤價", "最高價", "最低價", "收盤價", "漲跌(+/-)"]


def _twse_payload(rows, stat="OK"):
    return {"stat": stat, "tables": [
        {"title": "indices", "fields": ["指數", "收盤指數"], "data": [["加權", "1"]]},
        {"title": "stocks", "fields": TWSE_FIELDS, "data": rows},
    ]}


def test_parse_twse_extracts_ohlcv_and_filters_universe():
    rows = [
        ["2330", "台積電", "30,059,393", "1", "1", "2,355.00", "2,385.00", "2,350.00", "2,385.00", "+"],
        ["0050", "元大台灣50", "1,000", "1", "1", "105.00", "106.00", "104.50", "106.00", "+"],
        ["881A", "warrant", "1", "1", "1", "1.00", "1.00", "1.00", "1.00", ""],   # non-universe -> dropped
        ["2317", "鴻海", "--", "--", "--", "--", "--", "--", "--", ""],            # suspended (no OHLC) -> dropped
    ]
    out = bh.parse_twse_mi_index(_twse_payload(rows), "2026-06-17")
    assert {r["code"] for r in out} == {"2330", "0050"}
    tsmc = next(r for r in out if r["code"] == "2330")
    assert tsmc == {"code": "2330", "date": "2026-06-17", "open": 2355.0,
                    "high": 2385.0, "low": 2350.0, "close": 2385.0, "volume": 30059393}


def test_parse_twse_holiday_or_empty_returns_empty():
    assert bh.parse_twse_mi_index({"stat": "very sorry, no data"}, "2026-01-01") == []
    assert bh.parse_twse_mi_index({}, "2026-01-01") == []


def test_parse_tpex_handles_quoted_comma_volume():
    csv_text = "\r\n".join([
        "title line", "subtitle line",
        "代號,名稱,收盤,漲跌,開盤,最高,最低,均價,成交股數",
        '6488,環球晶,"1,110.00",+5.00,"1,110.00","1,145.00","1,065.00","1,100.00","12,271,700"',
        '00679B,元大美債20年,27.04,+0.23,26.95,27.04,26.93,26.98,256157',  # B-suffix -> non-universe
    ])
    out = bh.parse_tpex_daily(csv_text, "2026-06-17")
    assert {r["code"] for r in out} == {"6488"}
    r = out[0]
    assert (r["open"], r["high"], r["low"], r["close"]) == (1110.0, 1145.0, 1065.0, 1110.0)
    assert r["volume"] == 12271700  # quoted "12,271,700" parsed correctly (not split on the comma)


def test_weekdays_back_skips_weekends_and_is_descending():
    days = bh.weekdays_back(10, end=datetime(2026, 6, 17))
    assert len(days) == 10
    assert all(d.weekday() < 5 for d in days)
    assert days[0] == datetime(2026, 6, 17)  # a trading weekday -> included
    assert all(days[i] > days[i + 1] for i in range(len(days) - 1))


class _Resp:
    def __init__(self, payload=None, content=b""):
        self._payload = payload
        self.content = content

    def json(self):
        return self._payload


def test_backfill_bulk_assembles_per_ticker_and_saves():
    twse = _twse_payload([["2330", "台積電", "100", "1", "1", "10.0", "11.0", "9.0", "10.5", "+"]])
    empty_tpex = "代號,名稱,收盤,漲跌,開盤,最高,最低,均價,成交股數\n".encode("cp950")

    class _Http:
        def get(self, url, **kw):
            return _Resp(payload=twse) if "MI_INDEX" in url else _Resp(content=empty_tpex)

    saved = {}

    def _save(code, df):
        saved[code] = df

    res = bh.backfill_bulk(days=3, save_fn=_save, http=_Http(), end=datetime(2026, 6, 17))
    assert res["tickers"] == 1
    assert res["days_with_data"] == 3
    assert "2330" in saved
    df = saved["2330"]
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert len(df) == 3  # 3 weekdays, one row each, distinct dates
