"""Accelerated full-universe history backfill via authoritative TWSE/TPEX
per-day bulk endpoints.

One HTTP call returns ALL stocks' OHLCV for a single trading day, instead of one
call per stock (the yfinance path in ``core/data.py``). This is the user-chosen
"option C": each user fetches their own data from the official source (no
redistribution) with far fewer calls than the per-stock crawl.

Prices are RAW (not split/dividend-adjusted) — a bulk-backfilled DB is internally
consistent (all raw), but differs from yfinance ``auto_adjust=True``. Parsers are
pure and HTTP is injectable so tests never touch the network.
"""
import csv
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import requests
import urllib3

from core.logger import setup_logger
from core.universe_source import _is_universe_code

logger = setup_logger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TWSE_MI_INDEX = (
    "https://www.twse.com.tw/exchangeReport/MI_INDEX"
    "?response=json&date={date}&type=ALLBUT0999"
)
TPEX_DAILY = (
    "https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/"
    "stk_quote_result.php?d={roc}&o=csv"
)


def _num(value: Any) -> Optional[float]:
    """Parse a TWSE/TPEX numeric cell (commas, blanks, '--' for suspended)."""
    if value is None:
        return None
    s = str(value).replace(",", "").strip()
    if not s or s in ("--", "---", "—", "N/A"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _row(code: Any, date: str, o: Any, h: Any, l: Any, c: Any, v: Any) -> Optional[Dict[str, Any]]:
    code = str(code).strip()
    if not _is_universe_code(code):
        return None
    op, hi, lo, cl = _num(o), _num(h), _num(l), _num(c)
    if op is None or hi is None or lo is None or cl is None:
        return None  # suspended / no trade for this stock on this day
    vol = _num(v)
    return {
        "code": code,
        "date": date,
        "open": op,
        "high": hi,
        "low": lo,
        "close": cl,
        "volume": int(vol) if vol is not None else 0,
    }


def parse_twse_mi_index(payload: Dict[str, Any], date: str) -> List[Dict[str, Any]]:
    """Extract per-stock OHLCV from a TWSE MI_INDEX JSON payload for ``date`` (YYYY-MM-DD).

    The per-stock table is identified by its fields (證券代號 + 開盤價), not a fixed
    index, so it survives endpoint table-order changes. Column idx in that table:
    0=code, 2=volume, 5=open, 6=high, 7=low, 8=close.
    """
    if not payload or payload.get("stat") != "OK":
        return []
    rows: List[Dict[str, Any]] = []
    for table in payload.get("tables", []) or []:
        fields = [str(f) for f in (table.get("fields") or [])]
        if not (any("證券代號" in f for f in fields) and any("開盤" in f for f in fields)):
            continue
        table_rows: List[Dict[str, Any]] = []
        for r in table.get("data") or []:
            if len(r) < 9:
                continue
            row = _row(r[0], date, r[5], r[6], r[7], r[8], r[2])
            if row:
                table_rows.append(row)
        if table_rows:  # only accept a matching table that actually yielded stock rows
            rows.extend(table_rows)
            break
    return rows


def parse_tpex_daily(csv_text: str, date: str) -> List[Dict[str, Any]]:
    """Extract per-stock OHLCV from a TPEX daily-close CSV for ``date`` (YYYY-MM-DD).

    Parsed positionally (robust to title/header row count): col idx 0=code,
    2=close, 4=open, 5=high, 6=low, 8=volume. Non-universe codes are filtered out.
    """
    rows: List[Dict[str, Any]] = []
    # Use a real CSV reader: TPEX quotes numeric fields that contain commas
    # (e.g. volume "256,157"), so a naive split(',') would shift columns.
    for cells in csv.reader(csv_text.splitlines()):
        if len(cells) < 9:
            continue
        cells = [c.strip() for c in cells]
        row = _row(cells[0], date, cells[4], cells[5], cells[6], cells[2], cells[8])
        if row:
            rows.append(row)
    return rows


def _roc(date: datetime) -> str:
    return f"{date.year - 1911}/{date.month:02d}/{date.day:02d}"


def fetch_twse_day(date: datetime, http: Any = requests, timeout: int = 30) -> List[Dict[str, Any]]:
    url = TWSE_MI_INDEX.format(date=date.strftime("%Y%m%d"))
    try:
        resp = http.get(url, timeout=timeout, verify=False)
        return parse_twse_mi_index(resp.json(), date.strftime("%Y-%m-%d"))
    except Exception as exc:  # holiday/network/parse — caller continues with other days
        logger.warning("TWSE bulk fetch failed for %s: %s", date.date(), exc)
        return []


def fetch_tpex_day(date: datetime, http: Any = requests, timeout: int = 30) -> List[Dict[str, Any]]:
    url = TPEX_DAILY.format(roc=_roc(date))
    try:
        resp = http.get(url, timeout=timeout, verify=False)
        text = resp.content.decode("cp950", errors="ignore")
        return parse_tpex_daily(text, date.strftime("%Y-%m-%d"))
    except Exception as exc:
        logger.warning("TPEX bulk fetch failed for %s: %s", date.date(), exc)
        return []


def weekdays_back(days: int, end: Optional[datetime] = None) -> List[datetime]:
    """The last ``days`` weekday dates (Mon–Fri), most-recent first. Holidays are
    handled downstream — the endpoint returns empty for a non-trading day."""
    end = end or datetime.now()
    out: List[datetime] = []
    d = end
    while len(out) < days:
        if d.weekday() < 5:
            out.append(d)
        d = d - timedelta(days=1)
    return out


def backfill_bulk(
    days: int = 180,
    listed_only: bool = False,
    save_fn: Optional[Callable[[str, pd.DataFrame], None]] = None,
    http: Any = requests,
    end: Optional[datetime] = None,
    sleep_fn: Optional[Callable[[], None]] = None,
) -> Dict[str, Any]:
    """Backfill the universe's history from per-day bulk endpoints.

    For each of the last ``days`` weekdays, fetch all TWSE (+TPEX unless
    ``listed_only``) OHLCV, accumulate per-ticker, then persist via ``save_fn``
    (defaults to ``core.data.save_to_db``). Returns
    ``{tickers, rows, days_with_data}``.
    """
    if save_fn is None:
        from core.data import save_to_db as save_fn  # lazy: avoid import cycle

    by_ticker: Dict[str, List[Dict[str, Any]]] = {}
    days_with_data = 0
    for d in weekdays_back(days, end):
        day_rows = list(fetch_twse_day(d, http))
        if not listed_only:
            day_rows += list(fetch_tpex_day(d, http))
        if day_rows:
            days_with_data += 1
        for row in day_rows:
            by_ticker.setdefault(row["code"], []).append(row)
        if sleep_fn:
            sleep_fn()

    total_rows = 0
    tickers_saved = 0
    save_failures = 0
    for code, recs in by_ticker.items():
        df = pd.DataFrame(recs).sort_values("date").drop_duplicates("date", keep="last")
        cols = df[["date", "open", "high", "low", "close", "volume"]]
        written = save_fn(code, cols)
        # Honest accounting: core.data.save_to_db returns rows actually written
        # (0 on a swallowed DB error). A saver that returns None (e.g. a test
        # stub) is trusted. Count only CONFIRMED saves so the report can never
        # over-state persistence.
        n = len(cols) if written is None else int(written)
        if n > 0:
            total_rows += n
            tickers_saved += 1
        elif len(cols) > 0:
            save_failures += 1

    logger.info(
        "bulk backfill complete: %d tickers saved, %d rows, %d trading days, %d save failures",
        tickers_saved, total_rows, days_with_data, save_failures,
    )
    return {
        "tickers": tickers_saved,
        "rows": total_rows,
        "days_with_data": days_with_data,
        "save_failures": save_failures,
    }
