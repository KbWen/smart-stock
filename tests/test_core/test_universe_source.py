"""Tests for core.universe_source — authoritative live TWSE/TPEX universe sourcing.

Network is never hit: requests.get is monkeypatched with CSV fixtures that mirror
the real TWSE STOCK_DAY_ALL open-data and TPEX daily-close formats.
"""
import io
import types
import pytest

from core import universe_source as us


# --- Fixtures mirroring the real endpoint payloads -------------------------

# TWSE STOCK_DAY_ALL open_data: every field quoted, comma-separated.
# Columns: 日期,證券代號,證券名稱,成交股數,成交金額,開盤價,最高價,最低價,收盤價,漲跌價差,成交筆數
TWSE_CSV = (
    '"日期","證券代號","證券名稱","成交股數","成交金額","開盤價","最高價","最低價","收盤價","漲跌價差","成交筆數"\n'
    '"1130613","2330","台積電","30,000,000","...","900","910","895","905","+5","100000"\n'
    '"1130613","0050","元大台灣50","12,345,678","...","180","181","179","180","+1","50000"\n'
    '"1130613","00878","國泰永續高股息","8,000,000","...","22","22.5","21.9","22.1","+0.1","40000"\n'
    '"1130613","030123","某某認購權證","1,000","...","1","1","1","1","0","10"\n'  # warrant -> excluded
)

# TPEX daily_close_quotes: 3 junk header lines, then the real header row.
TPEX_CSV = (
    "上櫃股票每日收盤行情\n"
    "資料日期: 113/06/13\n"
    "說明: ...\n"
    "代號,名稱,收盤,漲跌,開盤,最高,最低,成交股數\n"
    "6488,環球晶,650,+5,648,655,645,2000000\n"
    "006201,元大富櫃50,18.5,+0.1,18.4,18.6,18.3,300000\n"
    ",,,,,,,\n"  # blank/NaN row -> skipped
)


class _FakeResp:
    def __init__(self, text="", content=b""):
        self.text = text
        self.content = content


def _patch_get(monkeypatch, twse_text=TWSE_CSV, tpex_bytes=None):
    if tpex_bytes is None:
        tpex_bytes = TPEX_CSV.encode("cp950", errors="ignore")

    def fake_get(url, *args, **kwargs):
        if "tpex" in url or "tpex.org" in url:
            return _FakeResp(content=tpex_bytes)
        return _FakeResp(text=twse_text)

    monkeypatch.setattr(us.requests, "get", fake_get)


# --- fetch_twse_listed ------------------------------------------------------

def test_fetch_twse_listed_parses_and_tags_market(monkeypatch):
    _patch_get(monkeypatch)
    rows = us.fetch_twse_listed()
    by_code = {r["code"]: r for r in rows}

    assert by_code["2330"]["name"] == "台積電"
    assert by_code["2330"]["market"] == "上市"
    assert by_code["2330"]["volume"] == 30_000_000
    # ETFs are included (no longer dropped)
    assert "0050" in by_code
    assert "00878" in by_code
    # Warrants (6-digit, not starting 00) are excluded
    assert "030123" not in by_code


# --- fetch_tpex_otc ---------------------------------------------------------

def test_fetch_tpex_otc_parses_and_tags_market(monkeypatch):
    _patch_get(monkeypatch)
    rows = us.fetch_tpex_otc()
    by_code = {r["code"]: r for r in rows}

    assert by_code["6488"]["market"] == "上櫃"
    assert by_code["6488"]["name"] == "環球晶"
    assert "006201" in by_code  # OTC ETF included
    assert "" not in by_code    # blank row skipped


# --- classify_kind ----------------------------------------------------------

def test_classify_kind_heuristic():
    assert us.classify_kind("2330") == "股票"
    assert us.classify_kind("0050") == "ETF"   # 4-digit ETF
    assert us.classify_kind("00878") == "ETF"  # 5-digit ETF
    assert us.classify_kind("006201") == "ETF"


def test_classify_kind_twstock_crossref_wins():
    fake_tw = types.SimpleNamespace(
        codes={"2330": types.SimpleNamespace(type="ETF", market="上市", name="x")}
    )
    # twstock says 2330 is ETF -> cross-ref overrides the '00' heuristic
    assert us.classify_kind("2330", twstock_module=fake_tw) == "ETF"


# --- build_universe ---------------------------------------------------------

def test_build_universe_normalizes_includes_etf_and_dedups(monkeypatch):
    twse = [
        {"code": "2330", "name": "台積電", "market": "上市", "volume": 1},
        {"code": "0050", "name": "元大台灣50", "market": "上市", "volume": 2},
        {"code": "2330", "name": "DUPLICATE", "market": "上市", "volume": 9},  # dup -> first wins
    ]
    tpex = [{"code": "6488", "name": "環球晶", "market": "上櫃", "volume": 3}]

    universe = us.build_universe(twse=twse, tpex=tpex, twstock_module=None)
    by_code = {r["code"]: r for r in universe}

    # Required normalized keys present on every entry
    for r in universe:
        assert set(["code", "name", "market", "kind"]).issubset(r.keys())

    assert by_code["2330"]["kind"] == "股票"
    assert by_code["2330"]["name"] == "台積電"  # dedup: TWSE first wins
    assert by_code["0050"]["kind"] == "ETF"
    assert by_code["6488"]["market"] == "上櫃"
    assert len(universe) == 3  # duplicate collapsed


def test_build_universe_drops_none_and_nan_codes():
    twse = [
        {"code": "2330", "name": "台積電", "market": "上市"},
        {"code": None, "name": "壞列", "market": "上市"},
        {"code": float("nan"), "name": "壞列2", "market": "上市"},
    ]
    universe = us.build_universe(twse=twse, tpex=[], twstock_module=None)
    codes = {r["code"] for r in universe}
    assert codes == {"2330"}  # phantom "None"/"nan" rows excluded


def test_build_universe_live_fetch_when_not_injected(monkeypatch):
    _patch_get(monkeypatch)
    universe = us.build_universe(twstock_module=None)
    codes = {r["code"] for r in universe}
    assert {"2330", "0050", "00878", "6488", "006201"}.issubset(codes)
    # every entry carries market + kind
    assert all(r["market"] in ("上市", "上櫃") for r in universe)
    assert all(r["kind"] in ("股票", "ETF") for r in universe)
