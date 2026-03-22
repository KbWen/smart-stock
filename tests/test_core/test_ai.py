import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, mock_open
from core.ai import predict_prob, prepare_features
from core.features import compute_all_indicators

def test_prepare_features(sample_stock_data):
    """Verify that features are correctly prepared for the AI model."""
    df = compute_all_indicators(sample_stock_data)
    X, y = prepare_features(df)
    
    # Feature columns should match config
    from core.ai import FEATURE_COLS
    for col in FEATURE_COLS:
        assert col in X.columns
    
    assert len(X) == len(y)
    assert not X.isna().any().any()

@patch('core.ai.predictor._read_sidecar', return_value=None)
@patch('builtins.open', new=mock_open(read_data=b''))
@patch('joblib.load')
@patch('os.path.exists')
def test_predict_prob_mocked(mock_exists, mock_load, _mock_sidecar, sample_stock_data):
    """Test prediction logic with a mocked model."""
    mock_exists.return_value = True
    
    # Clear cache to ensure mock is used
    from core.ai.predictor import _model_cache
    _model_cache.clear()
    
    # Mock model breakdown
    mock_model_gb = MagicMock()
    mock_model_gb.predict_proba.return_value = [[0.8, 0.1, 0.1]] # 20% win
    
    mock_model_rf = MagicMock()
    mock_model_rf.predict_proba.return_value = [[0.7, 0.2, 0.1]] # 30% win
    
    mock_model_mlp = MagicMock()
    mock_model_mlp.predict_proba.return_value = [[0.6, 0.3, 0.1]] # 40% win
    
    mock_load.return_value = {
        'version': 'v4.0-test',
        'ensemble': {
            'gb': mock_model_gb,
            'rf': mock_model_rf,
            'mlp': mock_model_mlp
        }
    }
    
    df = compute_all_indicators(sample_stock_data)
    result = predict_prob(df)
    
    assert result is not None
    assert 'prob' in result
    assert 'details' in result
    # Ave: (0.2 + 0.3 + 0.4) / 3 = 0.3
    assert pytest.approx(result['prob'], 0.01) == 0.3

@patch('core.ai.predictor._read_sidecar', return_value=None)
@patch('builtins.open', new=mock_open(read_data=b''))
@patch('core.ai.trainer.prepare_features')
@patch('joblib.load')
@patch('os.path.exists')
def test_predict_prob_legacy_model_handles_missing_features(mock_exists, mock_load, mock_prepare, _mock_sidecar):
    """Legacy model path should reindex missing features to zero instead of KeyError."""
    import numpy as np
    from core.ai.predictor import _model_cache

    _model_cache.clear()
    mock_exists.return_value = True

    class LegacyModel:
        feature_names_in_ = np.array(['f1', 'f2'])

        def predict_proba(self, X):
            assert list(X.columns) == ['f1', 'f2']
            assert float(X.iloc[0]['f2']) == 0.0
            return [[0.2, 0.3, 0.5]]

    mock_load.return_value = LegacyModel()
    mock_prepare.return_value = (pd.DataFrame([{'f1': 1.0}]), pd.Series([0]))

    df = pd.DataFrame({'close': [1] * 80, 'high': [1] * 80, 'low': [1] * 80, 'volume': [1] * 80})
    result = predict_prob(df)

    assert result['prob'] == pytest.approx(0.8)


def test_prepare_features_target_labeling_buy_before_stop():
    """Class 1 should be assigned when +10% is hit before stop-loss (without +15%)."""
    from core.ai.common import FEATURE_COLS

    n = 320
    close = np.full(n, 100.0)
    high = np.full(n, 101.0)
    low = np.full(n, 99.0)
    volume = np.full(n, 1000.0)

    # Entry at idx 280: +10% hit at day +2, +15% never hit, stop at day +5 (after buy target)
    high[282] = 111.0
    low[285] = 94.0

    df = pd.DataFrame({
        'close': close, 'high': high, 'low': low, 'volume': volume,
        'open': close
    })
    df = compute_all_indicators(df)

    X, y = prepare_features(df)
    target_index = 280
    assert target_index in y.index
    assert y.loc[target_index] == 1
    assert list(X.columns) == FEATURE_COLS


def test_prepare_features_fills_missing_and_matches_feature_cols(sample_stock_data):
    """Feature matrix should be fully numeric, aligned to FEATURE_COLS, and have no NaN after sanitization."""
    from core.ai.common import FEATURE_COLS

    df = compute_all_indicators(sample_stock_data)
    # inject NaN/inf edge cases
    df.loc[df.index[50:55], 'rsi'] = np.nan
    df.loc[df.index[60], 'macd'] = np.inf
    df.loc[df.index[61], 'macd_signal'] = -np.inf

    X, y = prepare_features(df)

    assert list(X.columns) == FEATURE_COLS
    assert len(X) == len(y)
    assert np.isfinite(X.to_numpy()).all()


def test_prepare_features_does_not_backfill_training_from_future_values():
    """Training rows with initial indicator NaNs should be dropped, not backfilled from future rows."""
    from core.ai.common import FEATURE_COLS

    n = 320
    close = np.linspace(100, 130, n)
    high = close + 1
    low = close - 1
    volume = np.full(n, 1000.0)

    df = pd.DataFrame({
        'open': close,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    })
    df = compute_all_indicators(df)

    # Simulate warm-up NaNs at the beginning for an actual feature column.
    df.loc[df.index[:3], 'rsi'] = np.nan
    df.loc[df.index[3], 'rsi'] = 77.0

    X, y = prepare_features(df, is_training=True)

    # Leading NaNs should not be backfilled from row 3's value.
    assert X.loc[0, 'rsi'] == 0
    assert X.loc[1, 'rsi'] == 0
    assert X.loc[2, 'rsi'] == 0
    assert np.isfinite(X.to_numpy()).all()
    assert list(X.columns) == FEATURE_COLS
    assert len(X) == len(y)
