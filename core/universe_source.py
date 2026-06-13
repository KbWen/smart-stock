"""Authoritative live sourcing of the Taiwan tradable universe (上市 + 上櫃).

Replaces reliance on the static, package-release-cadence ``twstock`` bundled list
with fresh data pulled from the official TWSE / TPEX open endpoints — the same
public endpoints already proven in ``fetch_stocks.py`` — and normalizes every
entry to ``{code, name, market, kind}`` so ETFs are included and classified
instead of being silently dropped.

Network failures are the caller's concern: ``build_universe`` raises on a hard
failure so ``core.data.get_all_tw_stocks`` can fall back to twstock / file cache.
All functions are pure given their inputs (HTTP is injectable via ``requests``)
so tests never hit the network.
"""
import io
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import urllib3

from core.logger import setup_logger

logger = setup_logger(__name__)

# The TWSE/TPEX open endpoints serve over TLS with certs that occasionally fail
# strict verification from CI hosts; fetch_stocks.py already disables the warning.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TWSE_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"
TPEX_URL = (
    "https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/"
    "stk_quote_result.php"
)

# Sentinel so an explicit ``twstock_module=None`` ("no twstock") is distinct from
# "caller did not specify, resolve the real module".
_UNSET = object()


def _resolve_twstock(twstock_module: Any):
    """Resolve the twstock module unless the caller explicitly passed one (incl. None)."""
    if twstock_module is not _UNSET:
        return twstock_module
    try:
        import twstock  # optional dependency

        return twstock
    except Exception:
        return None


def _is_universe_code(code: str) -> bool:
    """True for 4-digit equities and ``00``-prefixed ETFs (4–6 digits).

    Excludes warrants / rights (6-digit numeric not starting with ``00``) and any
    non-numeric instrument codes.
    """
    if not code or not code.isdigit():
        return False
    if len(code) == 4:
        return True
    return code.startswith("00") and 4 <= len(code) <= 6


def classify_kind(code: str, name: Optional[str] = None, twstock_module: Any = _UNSET) -> str:
    """Classify a code as ``'ETF'`` or ``'股票'``.

    Authoritative when twstock knows the code (its ``type`` field); otherwise a
    Taiwan-specific heuristic: ETF codes are ``00``-prefixed.
    """
    tw = _resolve_twstock(twstock_module)
    if tw is not None:
        try:
            info = tw.codes.get(code)
            if info is not None and getattr(info, "type", None):
                return "ETF" if info.type == "ETF" else "股票"
        except Exception:
            pass
    return "ETF" if code.startswith("00") else "股票"


def _col(df: pd.DataFrame, names: List[str], pos: int) -> pd.Series:
    """Return a column by the first matching header name, else by position."""
    for n in names:
        if n in df.columns:
            return df[n]
    return df.iloc[:, pos]


def _to_int(value: Any) -> int:
    s = str(value).replace(",", "").strip()
    return int(s) if s.isdigit() else 0


def fetch_twse_listed(timeout: int = 30) -> List[Dict[str, Any]]:
    """Fetch all TWSE-listed (上市) securities from STOCK_DAY_ALL open data."""
    resp = requests.get(TWSE_URL, timeout=timeout, verify=False)
    df = pd.read_csv(io.StringIO(resp.text), dtype=str)
    codes = _col(df, ["證券代號"], 1)
    names = _col(df, ["證券名稱"], 2)
    vols = _col(df, ["成交股數"], 3)

    rows: List[Dict[str, Any]] = []
    for code, name, vol in zip(codes, names, vols):
        code = str(code).strip()
        if not _is_universe_code(code):
            continue
        rows.append(
            {"code": code, "name": str(name).strip(), "market": "上市", "volume": _to_int(vol)}
        )
    return rows


def fetch_tpex_otc(timeout: int = 30, roc_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch all TPEX-listed (上櫃/OTC) securities from the daily close quotes."""
    if roc_date is None:
        today = datetime.now()
        roc_date = f"{today.year - 1911}/{today.month:02d}/{today.day:02d}"
    resp = requests.get(f"{TPEX_URL}?d={roc_date}&o=csv", timeout=timeout, verify=False)
    content = resp.content.decode("cp950", errors="ignore")
    # First 3 lines are titles; line 4 (skiprows=3) is the header row.
    df = pd.read_csv(io.StringIO(content), skiprows=3, header=0, dtype=str)
    codes = _col(df, ["代號", "證券代號"], 0)
    names = _col(df, ["名稱", "證券名稱"], 1)
    # Volume by NAME only: the positional column 2 is 收盤 (close) in the TPEX
    # daily-close layout, so a positional fallback would silently store close as
    # volume. Volume is non-critical for the universe; default 0 when absent.
    vols = df["成交股數"] if "成交股數" in df.columns else [0] * len(df)

    rows: List[Dict[str, Any]] = []
    for code, name, vol in zip(codes, names, vols):
        if pd.isna(code):
            continue
        code = str(code).strip()
        if not _is_universe_code(code):
            continue
        rows.append(
            {"code": code, "name": str(name).strip(), "market": "上櫃", "volume": _to_int(vol)}
        )
    return rows


def _normalize_entry(raw: Dict[str, Any], twstock_module: Any) -> Dict[str, Any]:
    raw_code = raw.get("code")
    # Guard None/NaN: str(None) -> "None" is truthy and would leak a phantom ticker.
    if raw_code is None or (isinstance(raw_code, float) and pd.isna(raw_code)):
        code = ""
    else:
        code = str(raw_code).strip()
    return {
        "code": code,
        "name": str(raw.get("name", "") or code).strip(),
        "market": raw.get("market") or "unknown",
        "kind": raw.get("kind") or classify_kind(code, raw.get("name"), twstock_module),
    }


def build_universe(
    twse: Optional[List[Dict[str, Any]]] = None,
    tpex: Optional[List[Dict[str, Any]]] = None,
    twstock_module: Any = _UNSET,
) -> List[Dict[str, Any]]:
    """Build the normalized, de-duplicated universe.

    When ``twse`` / ``tpex`` are not injected they are fetched live. Each entry is
    normalized to ``{code, name, market, kind}``. On a code collision the first
    occurrence wins (TWSE is appended before TPEX), so a listed equity is never
    shadowed by an OTC row of the same code.
    """
    if twse is None:
        twse = fetch_twse_listed()
    if tpex is None:
        tpex = fetch_tpex_otc()

    tw = _resolve_twstock(twstock_module)
    universe: List[Dict[str, Any]] = []
    seen = set()
    for raw in list(twse) + list(tpex):
        entry = _normalize_entry(raw, tw)
        code = entry["code"]
        if not code or code in seen:
            continue
        seen.add(code)
        universe.append(entry)
    return universe
