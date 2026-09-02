#!/usr/bin/env python3
"""Reproducible OOS comparison of ATR vs fixed labeling (no model is saved).

Trains the production ensemble (GB + RF + MLP) under each ``LABEL_MODE`` on whatever
tickers are present in storage.db, with a chronological 80/20 split and a PRED_DAYS
embargo measured in TRADING DAYS (shared with core.ai.trainer.chronological_split, so this
tool and production cannot drift apart), and reports per-class precision/recall for
Buy / StrongBuy.

This is the evidence tool behind docs/specs/ml-label-oos-evaluation.md. Results scale
with the data: on the bundled 6-ticker demo it is only indicative; populate a broader
universe (see core.data.backfill_history / fetch_stock_data) for a credible read.

Usage: python scripts/eval_label_modes.py
"""
import logging
import os
import sys
import warnings

warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from core.ai import common, trainer
from core.ai.common import FEATURE_COLS, PRED_DAYS
from core.data import get_db_connection, load_from_db


def _db_tickers():
    conn = get_db_connection()
    try:
        return [r[0] for r in conn.execute("SELECT DISTINCT ticker FROM stock_history").fetchall()]
    finally:
        conn.close()


def _build(tickers, mode):
    common.LABEL_MODE = mode
    frames = []
    for t in tickers:
        df = load_from_db(t, days=1100)
        if len(df) < 300:
            continue
        X, y = trainer.prepare_features(df)
        if not X.empty:
            d = X.copy()
            d["target"] = y
            if "date" in df.columns:
                d["date"] = df.loc[d.index, "date"]
            frames.append(d)
    alld = pd.concat(frames).sort_values("date") if frames else pd.DataFrame()
    X = alld[FEATURE_COLS].replace([np.inf, -np.inf], np.nan).fillna(0)
    return X, alld["target"].astype(int), alld


def evaluate(tickers, mode):
    X, y, panel = _build(tickers, mode)
    dist = {int(k): round(float(v), 3) for k, v in y.value_counts(normalize=True).items()}
    # Date-based embargo, shared with the trainer so this evidence tool and production cannot
    # drift apart. The old `iloc[: split - PRED_DAYS]` removed PRED_DAYS ROWS from a stacked
    # panel, i.e. PRED_DAYS/N trading days -- the numbers it produced were not out-of-sample.
    try:
        train_mask, test_mask, split_meta = trainer.chronological_split(panel, PRED_DAYS)
    except trainer.InsufficientPanelHistory as exc:
        return {"mode": mode, "samples": len(X), "error": f"insufficient panel history: {exc}"}
    Xtr, ytr = X[train_mask], y[train_mask]
    Xte, yte = X[test_mask], y[test_mask]

    w = {c: (1.0 / (m if (m := (ytr == c).mean()) > 0 else 1)) for c in (0, 1, 2)}
    w[2] *= 2
    tot = sum(w.values())
    w = {k: v / tot * 3 for k, v in w.items()}
    sw = ytr.map(w)

    gb = HistGradientBoostingClassifier(max_iter=100, max_depth=4, learning_rate=0.05, random_state=42)
    gb.fit(Xtr, ytr, sample_weight=sw)
    rf = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, class_weight=w, n_jobs=-1)
    rf.fit(Xtr, ytr)
    rng = np.random.default_rng(42)
    idx = rng.choice(len(Xtr), len(Xtr), replace=True, p=sw.to_numpy() / sw.sum())
    mlp = make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=300,
                                                        early_stopping=True, random_state=42))
    mlp.fit(Xtr.iloc[idx], ytr.iloc[idx])
    pred = np.argmax((gb.predict_proba(Xte) + rf.predict_proba(Xte) + mlp.predict_proba(Xte)) / 3, axis=1)

    out = {"mode": mode, "samples": len(X), "test_n": len(Xte), "dist": dist,
           "embargo_days": split_meta["gap_dates"],
           "cut_date": str(split_meta["cut_date"].date()),
           "accuracy": round(accuracy_score(yte, pred), 3)}
    for c, name in ((1, "Buy"), (2, "StrongBuy")):
        out[name] = {
            "precision": round(precision_score(yte, pred, labels=[c], average="macro", zero_division=0), 3),
            "recall": round(recall_score(yte, pred, labels=[c], average="macro", zero_division=0), 3),
        }
    return out


def main():
    tickers = _db_tickers()
    print(f"[eval] {len(tickers)} tickers in storage.db")
    if len(tickers) < 10:
        print("[eval] WARNING: very few tickers - results are indicative only, not a credible OOS read.")
    for mode in ("fixed", "atr"):
        print(evaluate(tickers, mode), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
