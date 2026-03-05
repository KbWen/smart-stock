"""Tests for generate_signals() to validate technical indicator signal logic."""
import pytest
from unittest.mock import patch


def make_indicators(**overrides):
    """Helper to build a mock indicators dict with sensible defaults."""
    base = {
        'rsi': 50.0,
        'macd': 0.0,
        'macd_signal': 0.0,
        'k_val': 50.0,
        'd_val': 50.0,
        'sma_20': 100.0,
        'sma_60': 100.0,
        'bb_width': 0.10,
    }
    base.update(overrides)
    return base


# We use get_signals_from_indicators from core.signals
from core.signals import get_signals_from_indicators as generate_signals_core
import core.data

def generate_signals(ticker: str) -> list[str]:
    ind = core.data.load_indicators_from_db(ticker)
    if not ind:
        return []
    return generate_signals_core(ind)


class TestGenerateSignals:
    """Verify signal generation logic against known indicator states."""

    @patch('core.data.load_indicators_from_db', return_value=None)
    def test_no_indicators_returns_empty(self, mock_load):
        """When no cached indicators exist, return empty list."""
        result = generate_signals("9999")
        assert result == []

    @patch('core.data.load_indicators_from_db')
    def test_rsi_oversold(self, mock_load):
        """RSI < 30 should produce RSI 超賣 signal."""
        mock_load.return_value = make_indicators(rsi=25.0)
        result = generate_signals("2330")
        assert 'RSI 超賣' in result

    @patch('core.data.load_indicators_from_db')
    def test_rsi_overbought(self, mock_load):
        """RSI > 70 should produce RSI 過熱 signal."""
        mock_load.return_value = make_indicators(rsi=75.0)
        result = generate_signals("2330")
        assert 'RSI 過熱' in result

    @patch('core.data.load_indicators_from_db')
    def test_rsi_neutral_no_signal(self, mock_load):
        """RSI between 30-70 should NOT produce RSI signal."""
        mock_load.return_value = make_indicators(rsi=50.0)
        result = generate_signals("2330")
        assert not any('RSI' in s for s in result)

    @patch('core.data.load_indicators_from_db')
    def test_macd_golden_cross(self, mock_load):
        """MACD slightly above signal line should produce 黃金交叉."""
        mock_load.return_value = make_indicators(macd=0.3, macd_signal=0.1)
        result = generate_signals("2330")
        assert 'MACD 黃金交叉' in result

    @patch('core.data.load_indicators_from_db')
    def test_macd_death_cross(self, mock_load):
        """MACD slightly below signal line should produce 死亡交叉."""
        mock_load.return_value = make_indicators(macd=-0.1, macd_signal=0.1)
        result = generate_signals("2330")
        assert 'MACD 死亡交叉' in result

    @patch('core.data.load_indicators_from_db')
    def test_macd_strong_bull(self, mock_load):
        """MACD well above signal should produce MACD 多頭."""
        mock_load.return_value = make_indicators(macd=2.0, macd_signal=0.5)
        result = generate_signals("2330")
        assert 'MACD 多頭' in result

    @patch('core.data.load_indicators_from_db')
    def test_kd_low_golden_cross(self, mock_load):
        """K > D and K < 30 should produce KD 低檔黃金交叉."""
        mock_load.return_value = make_indicators(k_val=25.0, d_val=20.0)
        result = generate_signals("2330")
        assert 'KD 低檔黃金交叉' in result

    @patch('core.data.load_indicators_from_db')
    def test_kd_high_death(self, mock_load):
        """K < D and K > 70 should produce KD 高檔死叉."""
        mock_load.return_value = make_indicators(k_val=75.0, d_val=80.0)
        result = generate_signals("2330")
        assert 'KD 高檔死叉' in result

    @patch('core.data.load_indicators_from_db')
    def test_sma_bullish_alignment(self, mock_load):
        """SMA20 > SMA60 should produce 均線多頭排列."""
        mock_load.return_value = make_indicators(sma_20=110.0, sma_60=100.0)
        result = generate_signals("2330")
        assert '均線多頭排列' in result

    @patch('core.data.load_indicators_from_db')
    def test_sma_bearish_alignment(self, mock_load):
        """SMA20 < SMA60 should produce 均線空頭排列."""
        mock_load.return_value = make_indicators(sma_20=90.0, sma_60=100.0)
        result = generate_signals("2330")
        assert '均線空頭排列' in result

    @patch('core.data.load_indicators_from_db')
    def test_bollinger_squeeze(self, mock_load):
        """BB width < 0.05 should produce 布林收斂."""
        mock_load.return_value = make_indicators(bb_width=0.03)
        result = generate_signals("2330")
        assert '布林收斂' in result

    @patch('core.data.load_indicators_from_db')
    def test_bollinger_expansion(self, mock_load):
        """BB width > 0.15 should produce 布林擴張."""
        mock_load.return_value = make_indicators(bb_width=0.20)
        result = generate_signals("2330")
        assert '布林擴張' in result

    @patch('core.data.load_indicators_from_db')
    def test_max_three_signals(self, mock_load):
        """Should never return more than 3 signals."""
        # Trigger many signals: RSI oversold + MACD golden + KD low golden + SMA bull + BB squeeze
        mock_load.return_value = make_indicators(
            rsi=20.0, macd=0.3, macd_signal=0.1, k_val=25.0, d_val=20.0,
            sma_20=110.0, sma_60=100.0, bb_width=0.03
        )
        result = generate_signals("2330")
        assert len(result) <= 3
