"""Reproducible label-distribution analysis — the evidence tool for the ATR label
redesign (docs/specs/ml-label-volatility-scaling.md AC4).

Computes the 3-class (Hold / Buy / StrongBuy) distribution that a labeling mode
produces on a set of OHLCV frames, WITHOUT training a model. Used to demonstrate
that ATR-scaled barriers rebalance the otherwise-degenerate fixed-percentage labels.

Honesty note: this measures the *label* distribution only. It does NOT claim
model precision/recall improvement — that requires a full-universe retrain (the dev
DB holds only a handful of tickers).
"""
from typing import Any, Dict, Iterable, Optional

from core.ai import common, trainer


def label_distribution(dfs: Iterable[Any], mode: Optional[str] = None) -> Dict[str, Any]:
    """Return the 3-class label distribution for ``dfs`` under ``mode``.

    Args:
        dfs: iterable of OHLCV DataFrames (as fed to ``trainer.prepare_features``).
        mode: ``'atr'`` | ``'fixed'`` | ``None`` (use the current ``common.LABEL_MODE``).

    Returns ``{hold, buy, strong, n}`` where the first three are fractions in [0,1].
    Restores the previous ``LABEL_MODE`` even on error (no global leakage).
    """
    previous = common.LABEL_MODE
    counts = {0: 0, 1: 0, 2: 0}
    try:
        if mode is not None:
            common.LABEL_MODE = mode
        for df in dfs:
            _, y = trainer.prepare_features(df)
            if y is None or len(y) == 0:
                continue
            for cls in (0, 1, 2):
                counts[cls] += int((y == cls).sum())
    finally:
        common.LABEL_MODE = previous

    n = counts[0] + counts[1] + counts[2]
    frac = (lambda c: (c / n) if n else 0.0)
    return {"hold": frac(counts[0]), "buy": frac(counts[1]), "strong": frac(counts[2]), "n": n}


def compare_modes(dfs: Iterable[Any]) -> Dict[str, Dict[str, Any]]:
    """Convenience: return both fixed and atr distributions over the same frames.

    ``dfs`` is materialized to a list so it can be iterated twice.
    """
    frames = list(dfs)
    return {"fixed": label_distribution(frames, "fixed"), "atr": label_distribution(frames, "atr")}
