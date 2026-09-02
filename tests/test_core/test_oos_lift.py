"""OOS metric attribution and baseline lift (docs/specs/oos-metric-attribution-and-lift.md).

Three defects this pins:
  F8 the stored metrics describe the 80%-split ensemble, while the shipped artifact is a
     full-data refit -- the attribution was implied, never stated;
  F9 precision was reported with no base rate, and the distribution that WAS stored is the
     TRAIN split, which is not the denominator;
  F10 get_model_health returned `ok` for anything with non-zero metrics, so a model at or below
     the base rate passed as healthy.

The through-line: get_model_health must fail TOWARD disclosure. Every test here that adds a
reason to doubt the numbers expects `degraded`, never `ok`.
"""
import core.ai.predictor as predictor


HEALTHY_METRICS = {
    "precision_buy": 0.4, "recall_buy": 0.3,
    "precision_strong": 0.35, "recall_strong": 0.25,
    "lift_strong": 2.5, "lift_buy": 1.8,
}


def _health(monkeypatch, entry):
    monkeypatch.setattr(predictor, "get_model_version", lambda: "v4.test")
    monkeypatch.setattr(predictor, "list_available_models", lambda: [dict(entry, version="v4.test")])
    return predictor.get_model_health()


def test_entry_without_embargo_is_degraded_however_good_it_looks(monkeypatch):
    """An entry with no `embargo` block predates 2026-09-02, when the split separated train from
    test by 0 trading days. Strong-looking numbers from a contaminated split are the most
    dangerous kind, so absence of the marker outranks the metrics."""
    h = _health(monkeypatch, {"oos_metrics": dict(HEALTHY_METRICS, lift_strong=9.0)})

    assert h["status"] == "degraded"
    assert "舊的切分" in h["message"]


def test_lift_at_or_below_one_is_degraded(monkeypatch):
    """1.0 means the model matches the base rate. The boundary is inclusive: matching a coin
    weighted to the class prevalence is not an edge."""
    for lift in (0.98, 1.0):
        h = _health(monkeypatch, {
            "embargo": {"days": 21, "basis": "trading_days"},
            "oos_metrics": dict(HEALTHY_METRICS, lift_strong=lift),
        })
        assert h["status"] == "degraded", lift
        assert "基準比例" in h["message"]


def test_lift_above_one_with_an_embargo_is_ok(monkeypatch):
    h = _health(monkeypatch, {
        "embargo": {"days": 21, "basis": "trading_days"},
        "oos_metrics": dict(HEALTHY_METRICS, lift_strong=1.01),
    })

    assert h["status"] == "ok"
    assert h["message"] == ""


def test_zero_power_still_degraded_even_with_a_clean_embargo(monkeypatch):
    """Regression guard. The shipped model's metrics are literally all zero, so it reports
    degraded today -- by accident of that rule, not by design. It must not become `ok` when a
    future entry carries an embargo block."""
    h = _health(monkeypatch, {
        "embargo": {"days": 21, "basis": "trading_days"},
        "oos_metrics": {
            "precision_buy": 0.0, "recall_buy": 0.0,
            "precision_strong": 0.0, "recall_strong": 0.0,
            "lift_strong": 0.0, "lift_buy": 0.0,
        },
    })

    assert h["status"] == "degraded"
    assert "辨識力不足" in h["message"]


def test_missing_lift_is_degraded_not_ok(monkeypatch):
    """The `[CONSTRAINT]` in the spec: anything this function cannot evaluate resolves to
    disclosure, never to `ok`. The trainer writes `embargo` and `lift_strong` together, so an
    entry with one and not the other is hand-edited or half-written — exactly the case where
    guessing `ok` would be worst."""
    h = _health(monkeypatch, {
        "embargo": {"days": 21, "basis": "trading_days"},
        "oos_metrics": {k: v for k, v in HEALTHY_METRICS.items() if not k.startswith("lift")},
    })

    assert h["status"] == "degraded"
    assert "提升倍數" in h["message"]


# --- The recorded base rate must come from the TEST split ------------------------------------

import pandas as pd  # noqa: E402

from core.ai.trainer import class_prevalence, lift_over_prevalence  # noqa: E402


def test_class_prevalence_reads_the_series_it_is_given():
    y = pd.Series([0, 0, 0, 0, 0, 0, 1, 1, 2, 2])
    assert class_prevalence(y) == {"hold": 0.6, "buy": 0.2, "strong": 0.2}
    assert class_prevalence(pd.Series([], dtype=int)) == {"hold": 0.0, "buy": 0.0, "strong": 0.0}


def test_lift_is_precision_over_the_base_rate():
    assert lift_over_prevalence(0.50, 0.25) == 2.0
    assert lift_over_prevalence(0.25, 0.25) == 1.0   # exactly the base rate: no edge
    assert lift_over_prevalence(0.20, 0.25) == 0.8   # worse than guessing


def test_zero_prevalence_yields_none_not_a_sentinel():
    """The class is absent from the split being scored, so there is no base rate to divide by.
    A sentinel here would be the `profit_factor=9999` mistake in a new place."""
    assert lift_over_prevalence(0.5, 0.0) is None
    assert lift_over_prevalence(0.0, 0.0) is None
    assert lift_over_prevalence(0.5, None) is None


def test_train_and_test_prevalence_differ_so_the_wrong_one_is_detectable():
    """The stored `class_distribution` is the TRAIN split. The whole F9 defect was that nothing
    said so, and the UI showed it as the denominator for the OOS precision beside it. A fixture
    whose two splits differ is what makes 'which one did you use?' answerable at all."""
    y_train = pd.Series([0] * 90 + [1] * 5 + [2] * 5)      # 90/5/5
    y_test = pd.Series([0] * 50 + [1] * 25 + [2] * 25)     # 50/25/25

    train_dist = class_prevalence(y_train)
    test_dist = class_prevalence(y_test)
    assert train_dist != test_dist

    # Same precision, read against the two different base rates, gives opposite verdicts:
    # a real edge against the train rate, no edge at all against the true test rate.
    precision = 0.25
    assert lift_over_prevalence(precision, train_dist["strong"]) == 5.0
    assert lift_over_prevalence(precision, test_dist["strong"]) == 1.0


def test_trainer_records_the_test_split_prevalence_not_the_train_one(tmp_path, monkeypatch):
    """Pins the CALL SITE, which the helper tests above cannot: rewriting
    `class_prevalence(y_test)` to `class_prevalence(y_train_full)` in trainer.py breaks nothing
    unless something actually runs the trainer and reads what it wrote. AC6 bullet 1 asks for
    exactly that proof, so this runs a real (small) train_and_save into a temp MODEL_PATH.

    The panel is built so the two splits have visibly different class balances -- late dates are
    mostly StrongBuy, early dates mostly Hold -- so reading the wrong one is detectable rather
    than a coincidental match.
    """
    import json

    from core.ai import trainer as t
    from core.ai.common import FEATURE_COLS

    # Patch the module constant rather than the env var: reloading core/* mid-suite would leave
    # other tests importing modules that had baked in this temp path.
    monkeypatch.setattr(t, "MODEL_PATH", str(tmp_path / "m.pkl"))

    dates = pd.bdate_range("2021-01-01", periods=400)
    rows = []
    for i, d in enumerate(dates):
        late = i > len(dates) * 0.8
        for k in range(12):
            rows.append({
                **{c: float(i + k) for c in FEATURE_COLS},
                "target": (2 if k % 4 else 0) if late else (0 if k % 4 else 1),
                "date": d,
            })
    panel = pd.DataFrame(rows)
    monkeypatch.setattr(t, "prepare_features", lambda df: (df[FEATURE_COLS], df["target"]))

    assert t.train_and_save([panel]) is True

    entry = json.loads((tmp_path / "models_history.json").read_text())[-1]
    train_mask, test_mask, _ = t.chronological_split(panel, t.PRED_DAYS)
    expected = t.class_prevalence(panel["target"][test_mask])

    assert entry["test_class_distribution"]["strong"] == round(expected["strong"], 3)
    # The train split is genuinely different, so the assertion above could not have passed by
    # reading the wrong series.
    train_dist = t.class_prevalence(panel["target"][train_mask])
    assert entry["test_class_distribution"]["strong"] != round(train_dist["strong"], 3)
    assert entry["class_distribution"]["strong"] == round(train_dist["strong"], 3)
    assert entry["oos_metrics_scope"] == "split_model"
    assert "lift_strong" in entry["oos_metrics"]
