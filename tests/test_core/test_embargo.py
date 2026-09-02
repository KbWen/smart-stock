"""Date-based train/test embargo (docs/specs/date-based-train-test-embargo.md).

The defect these tests pin: the embargo used to be `X_all.iloc[:split_idx - PRED_DAYS]` on a
cross-sectionally stacked panel. One calendar day contributes N rows (N = tickers), so removing
PRED_DAYS ROWS removes PRED_DAYS/N trading days — at 92 tickers, about 0.2 of a day against a
20-trading-day label horizon. Rows and days are only equivalent when N == 1, which is why the bug
survived: on a single-ticker frame the row arithmetic was accidentally correct.

Every assertion here is about DISTINCT DATES, never row counts. A row-count assertion cannot
distinguish a correct embargo from the bug.
"""
import numpy as np
import pandas as pd
import pytest

from core.ai.common import FEATURE_COLS, PRED_DAYS
from core.ai.trainer import InsufficientPanelHistory, chronological_split


def _panel(n_tickers, n_dates, rows_per_date=None):
    """Build a stacked panel: every ticker contributes one row per date, date-sorted.

    `rows_per_date` optionally overrides the width of specific dates (by index) so an UNEVEN
    panel can be exercised — the case that makes mean-based gap scaling unsafe.
    """
    dates = pd.bdate_range("2020-01-01", periods=n_dates)
    records = []
    for i, d in enumerate(dates):
        width = (rows_per_date or {}).get(i, n_tickers)
        for t in range(width):
            row = {col: float(t + i) for col in FEATURE_COLS}
            row["target"] = t % 3
            row["date"] = d
            records.append(row)
    return pd.DataFrame(records).sort_values("date").reset_index(drop=True)


def _old_row_based_masks(df_all, pred_days=PRED_DAYS):
    """The pre-fix split, reproduced verbatim so its failure can be demonstrated, not asserted."""
    split_idx = int(len(df_all) * 0.8)
    train = np.zeros(len(df_all), dtype=bool)
    test = np.zeros(len(df_all), dtype=bool)
    train[: max(0, split_idx - pred_days)] = True
    test[split_idx:] = True
    return train, test


def _distinct_date_gap(df_all, train_mask, test_mask):
    """Distinct panel dates separating the last training date from the first test date."""
    dates = pd.to_datetime(df_all["date"])
    unique = np.sort(dates.unique())
    last_train = np.datetime64(dates[train_mask].max())
    first_test = np.datetime64(dates[test_mask].min())
    return int(np.searchsorted(unique, first_test) - np.searchsorted(unique, last_train))


def test_embargo_spans_pred_days_of_trading_days_on_a_wide_panel():
    df = _panel(n_tickers=92, n_dates=400)
    train_mask, test_mask, meta = chronological_split(df, PRED_DAYS)

    assert _distinct_date_gap(df, train_mask, test_mask) >= PRED_DAYS
    assert meta["gap_dates"] >= PRED_DAYS
    assert meta["n_train"] > 0 and meta["n_test"] > 0
    # No training row may share a date with, or post-date, any test row.
    dates = pd.to_datetime(df["date"])
    assert dates[train_mask].max() < dates[test_mask].min()


def test_old_row_based_embargo_fails_the_same_invariant():
    """Demonstrates the defect rather than trusting the audit: at 92 tickers the row-based
    embargo separates the splits by well under PRED_DAYS trading days."""
    df = _panel(n_tickers=92, n_dates=400)
    train_mask, test_mask = _old_row_based_masks(df)

    gap = _distinct_date_gap(df, train_mask, test_mask)
    assert gap < PRED_DAYS, f"expected the buggy split to under-embargo, got {gap} days"
    # 20 rows out of 92-per-date is a fraction of a single day.
    assert gap <= 1


def test_cv_gap_is_scaled_to_span_pred_days_of_dates():
    df = _panel(n_tickers=92, n_dates=400)
    _, _, meta = chronological_split(df, PRED_DAYS)

    assert meta["max_rows_per_date"] == 92
    assert meta["cv_gap"] == PRED_DAYS * 92
    # The unscaled gap the old code passed to TimeSeriesSplit could not span a single date.
    assert meta["cv_gap"] > PRED_DAYS


def test_cv_gap_uses_the_widest_date_so_an_uneven_panel_is_still_covered():
    """Mean-based scaling would under-cover a panel whose widest dates sit near the split.
    The max is the only choice that guarantees the gap spans >= PRED_DAYS distinct dates."""
    df = _panel(n_tickers=10, n_dates=400, rows_per_date={i: 40 for i in range(280, 300)})
    train_mask, _, meta = chronological_split(df, PRED_DAYS)

    dates = pd.to_datetime(df["date"])
    counts = dates[train_mask].value_counts()
    assert meta["max_rows_per_date"] == int(counts.max()) == 40
    # A gap of cv_gap samples, taken from the end of the train split, cannot span fewer than
    # PRED_DAYS distinct dates, because no single date is wider than max_rows_per_date.
    tail_dates = dates[train_mask].iloc[-meta["cv_gap"]:]
    assert tail_dates.nunique() >= PRED_DAYS


def test_single_ticker_panel_still_splits_correctly():
    """N == 1 is the degenerate case the old row arithmetic handled by accident. The fix must
    not regress it."""
    df = _panel(n_tickers=1, n_dates=200)
    train_mask, test_mask, meta = chronological_split(df, PRED_DAYS)

    assert _distinct_date_gap(df, train_mask, test_mask) >= PRED_DAYS
    assert meta["max_rows_per_date"] == 1
    assert meta["cv_gap"] == PRED_DAYS


def test_too_few_dates_aborts_instead_of_shrinking_the_embargo():
    df = _panel(n_tickers=50, n_dates=PRED_DAYS)
    with pytest.raises(InsufficientPanelHistory, match="distinct dates"):
        chronological_split(df, PRED_DAYS)


def test_panel_without_a_date_column_aborts():
    df = _panel(n_tickers=5, n_dates=100).drop(columns=["date"])
    with pytest.raises(InsufficientPanelHistory, match="no 'date' column"):
        chronological_split(df, PRED_DAYS)


def test_embargo_holds_when_tickers_do_not_all_trade_every_day():
    """The panel calendar is the union of dates actually present — no assumption that every
    ticker trades every day."""
    df = _panel(n_tickers=30, n_dates=300, rows_per_date={i: 1 for i in range(150, 200)})
    train_mask, test_mask, meta = chronological_split(df, PRED_DAYS)

    assert _distinct_date_gap(df, train_mask, test_mask) >= PRED_DAYS
    dates = pd.to_datetime(df["date"])
    assert dates[train_mask].max() < meta["cut_date"]


def _fold_date_gaps(panel, train_mask, cv_gap, n_splits=3):
    """Distinct-date gap between train and validation for each real TimeSeriesSplit fold."""
    from sklearn.model_selection import TimeSeriesSplit

    dates = pd.to_datetime(panel["date"])[train_mask].reset_index(drop=True)
    unique = np.sort(pd.to_datetime(panel["date"]).unique())
    gaps = []
    for t_idx, v_idx in TimeSeriesSplit(n_splits=n_splits, gap=cv_gap).split(np.zeros(len(dates))):
        last_train = np.datetime64(dates.iloc[t_idx].max())
        first_val = np.datetime64(dates.iloc[v_idx].min())
        gaps.append(int(np.searchsorted(unique, first_val) - np.searchsorted(unique, last_train)))
    return gaps


def test_every_cv_fold_is_separated_by_pred_days_of_dates():
    """AC6 bullet 2, asserted against a real TimeSeriesSplit rather than inferred from `meta`.

    The scaled gap is only meaningful if the FOLD BOUNDARIES it produces are actually
    PRED_DAYS apart in calendar terms — arithmetic on `cv_gap` alone cannot show that.
    """
    df = _panel(n_tickers=92, n_dates=400)
    train_mask, _, meta = chronological_split(df, PRED_DAYS)

    gaps = _fold_date_gaps(df, train_mask, meta["cv_gap"])
    assert len(gaps) == 3
    assert all(g >= PRED_DAYS for g in gaps), gaps


def test_every_cv_fold_holds_on_an_uneven_panel():
    """The max-based scaling exists for exactly this shape: dates of wildly different widths.
    A mean-based gap would under-cover the folds that land near the wide stretch."""
    df = _panel(n_tickers=8, n_dates=1000, rows_per_date={i: 60 for i in range(300, 340)})
    train_mask, _, meta = chronological_split(df, PRED_DAYS)

    gaps = _fold_date_gaps(df, train_mask, meta["cv_gap"])
    assert all(g >= PRED_DAYS for g in gaps), gaps

    # A mean-scaled gap would have been far smaller, and is what the max protects against.
    dates = pd.to_datetime(df["date"])[train_mask]
    mean_gap = int(PRED_DAYS * (len(dates) / dates.nunique()))
    assert mean_gap < meta["cv_gap"]


def test_partially_dated_panel_aborts_instead_of_dropping_rows_silently():
    """A batch where only some frames carry a date yields NaT after concat. Those rows would
    vanish from BOTH splits while `gap_dates` still reported a healthy embargo."""
    df = _panel(n_tickers=10, n_dates=300)
    df.loc[df.index[:200], "date"] = pd.NaT

    with pytest.raises(InsufficientPanelHistory, match="no usable date"):
        chronological_split(df, PRED_DAYS)


def test_timezone_aware_dates_are_normalised_rather_than_raising():
    """A tz-aware `date` column used to raise TypeError, escaping this module's own exception
    type so the caller never saw the honest message."""
    df = _panel(n_tickers=6, n_dates=300)
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize("Asia/Taipei")

    train_mask, test_mask, meta = chronological_split(df, PRED_DAYS)
    assert meta["gap_dates"] >= PRED_DAYS
    assert int(train_mask.sum()) > 0 and int(test_mask.sum()) > 0


def test_cv_degrades_but_the_holdout_embargo_never_does(monkeypatch):
    """The scaled gap is deliberately large, so on a short panel `TimeSeriesSplit` cannot build
    3 folds. That must NOT abort training: the CV loop is diagnostic only — each fold's model is
    fit, its accuracy printed, and discarded — while the holdout embargo is the actual guarantee.
    Aborting would conflate the two and strand small panels (the shipped demo fixture among them)
    with no model at all.

    Pins the real cliff the tenth-man measured: feasibility is driven by distinct TRAINING DATES,
    roughly `> 4 x PRED_DAYS`, and is INDEPENDENT of ticker count — adding tickers scales the gap
    and the row count together.
    """
    from sklearn.model_selection import TimeSeriesSplit as _RealTSS

    for n_tickers in (8, 60):
        # ~60 training dates: comfortably above the 22-date InsufficientPanelHistory floor, but
        # below the CV feasibility cliff.
        df = _panel(n_tickers=n_tickers, n_dates=100)
        train_mask, test_mask, meta = chronological_split(df, PRED_DAYS)

        # The holdout guarantee still holds regardless.
        assert _distinct_date_gap(df, train_mask, test_mask) >= PRED_DAYS

        # The cliff is about dates, not tickers: same verdict at 8 and at 60 tickers.
        feasible = True
        try:
            list(_RealTSS(n_splits=2, gap=meta["cv_gap"]).split(np.zeros(meta["n_train"])))
        except ValueError:
            feasible = False
        assert feasible is False, (
            f"expected {meta['n_train_dates']} training dates to be below the CV cliff "
            f"at {n_tickers} tickers"
        )


def test_meta_records_test_window_in_dates_not_just_rows():
    """A row-position cut on a panel whose width grows over time yields "20% of rows" spanning
    far fewer than 20% of the dates. Without this the concentration is invisible."""
    df = _panel(n_tickers=4, n_dates=400, rows_per_date={i: 40 for i in range(360, 400)})
    _, _, meta = chronological_split(df, PRED_DAYS)

    assert meta["n_test_dates"] >= 1
    assert meta["n_train_dates"] + meta["n_test_dates"] < 400  # the embargo removed dates
    # The wide tail pulls the row-based cut late, so the test window covers a much smaller share
    # of DATES than of rows -- the distortion this field exists to expose.
    row_share = meta["n_test"] / (meta["n_train"] + meta["n_test"])
    date_share = meta["n_test_dates"] / (meta["n_train_dates"] + meta["n_test_dates"])
    assert date_share < row_share
