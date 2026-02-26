# Whitepaper: Smart Stock Selector AI Sniper

## Executive Summary

The **Smart Stock Selector** is a specialized quantitative tool designed for the Taiwan Stock Market. It bridges the gap between traditional technical analysis and modern machine learning by focusing on asymmetric risk-reward profiles rather than simple price forecasts.

## 1. Technical Indicators (Rule-Based Engine)

The system calculates a multi-factor "Rise Score" (0-100) based on three pillars:

### A. Trend (40%)

Utilizes Moving Average ribbons (SMA20, SMA60). Full points are awarded when the price exhibits a perfect bullish alignment (Price > SMA20 > SMA60).

### B. Momentum (30%)

* **RSI (14)**: 採用標準的 **Wilder's Smoothing (EWMA)** 方法計算，捕捉更穩健的強弱訊號。
* **KD (Stochastics)**: Uses momentum-zone KD condition where **K > D** and **K < 80** to confirm bullish pressure without overheating.
* **MACD**: Confirms directional strength via signal line divergence.

### C. Volatility & Setup (30%)

* **Bollinger Squeeze**: Detects periods of abnormally low volatility, often preceding explosive moves.
* **Volume Breakout**: Filters for price moves supported by heavy institutional-grade volume (>1.5x MA20).

## 2. The AI Sniper Model (Machine Learning V4 - Ensemble)

The V4 engine moves beyond a single classifier to an **Ensemble Voting** architecture, increasing stability and reducing prediction variance.

Unlike "black box" models, our Sniper Model is trained with a specific exit strategy: **3:1 Risk/Reward**. It also incorporates the heuristic **Rise Score** (Trend, Momentum, Volatility) as direct features to guide the ensemble with technical expertise.

### Target Labeling (3-Class System)

We label outcomes into three categories (within **20 trading days**):

1. **Strong Buy (Class 2)**: Price reaches **+15%** gain BEFORE hitting a **-5%** stop loss.
2. **Buy (Class 1)**: Price reaches **+10%** gain BEFORE hitting a **-5%** stop loss (but doesn't reach +15%).
3. **Hold/Loss (Class 0)**: Any other scenario (hits stop loss first, or fails to reach +10% within 20 days).

* **Ensemble Learning (V4)**: 結合三種異質模型，採 **等權重投票法 (Equal Weighting 1/3 each)**：
  * **GradientBoosting**: 專注於殘差學習，捕捉複雜的非線性趨勢。
  * **RandomForest**: 採用 200 棵決策樹，增加模型魯棒性。
  * **MLP (Multi-Layer Perceptron)**: (128, 64) 雙層神經網路，挖掘深層特徵關聯。
* **Expert Feature Engineering**: 加入並向量化「Rise Score」 heuristic 分數作為核心輸入。
* **Feature Normalization**: MACD、MACD Hist、ATR% 皆經過價格標準化 (`Indicator / Price`)。
* **Class Weighting**: 針對獲利樣本稀缺 (15.58%) 的特性優化。

### Model Version Control

To ensure strategy consistency and reproducibility, the system implements a strict versioning protocol:

* **Version Tagging**: Every trained model is saved with a timestamped tag (e.g., `v4.1.20231027`).
* **Database Partitioning**: The `stock_scores` table uses a composite primary key `(ticker, model_version)`, allowing multiple model versions to coexist.
* **User Selection**: The frontend includes a "Version Switcher" that allows traders to toggle between the "Latest" model and historical versions to verify performance stability over time.

### AI Sniper Strategy Visualization

```mermaid
graph LR
    subgraph "Sniper Conditions (20 Days)"
    Price[Current Price] --> Strong["Strong Buy: +15%"]
    Price --> Buy["Buy: +10%"]
    Price --> Stop["Stop: -5% (Loss/Hold)"]
    end
    
    subgraph "Ensemble V4 Consensus"
    GB[Gradient Boosting]
    RF[Random Forest]
    MLP[Neural Network]
    end
    
    GB & RF & MLP --> Vote{Voting & Averaging}
    Vote --> Result[Class 0, 1, 2]
```

## 3. AI 虛擬分析師 (Heuristic Explanation)

To solve the "black box" problem of AI, the system includes an explanation layer that maps technical scores to natural language insights:

* **Trend Analysis**: Interprets SMA slopes to detect "Strong Uptrends" or "Support Tests".
* **Momentum Logic**: Correlates RSI and KD to flag "Overheating" or "Fresh Bounce" scenarios.
* **Form Patterns**: Detects Bollinger Squeezes and Volume spikes to explain the AI's "Signal Strength".

## 4. Data Integrity & "No Look-ahead" Policy

To prevent overfitting and survivorship bias:

* **Time-Series Splitting**: We use strict historical splitting for training. The model never "sees" the future during its training phase.
* **Adjusted OHLC Data**: Market data is fetched with `auto_adjust=True` to reduce distortions from dividends/splits and keep return labeling consistent.
* **Chronological Sanitization**: Downloaded OHLCV is re-sorted by date and de-duplicated per trading day before persistence.
* **Normalized Features**: All price-based features are relative (percentages) to ensure the model generalizes across different stock price ranges (e.g., a $10 penny stock vs a $1000 blue chip).

### Backtest Result Semantics

* **Candidate Ranking**: Top picks are selected by AI probability at entry (`ai_prob_at_entry`).
* **Best Pick Reporting**: `best_stock` and `best_return` are computed from the **highest realized return** among selected picks, not merely the highest AI rank.

## 5. Conclusion

The Smart Stock Selector does not aim to trade often; it aims to trade **well**. By filtering for high-probability setups where the math of the "Sniper Strategy" is in the user's favor, it provides a disciplined framework for successful swing trading.
