# Glossary - Sniper V4.1

## Core Concepts

### Sniper Strategy

A high-probability trading strategy targeting a **Risk/Reward Ratio of 3:1** or better. The goal is to identify stocks that have a high likelihood of rising +15% before falling -5%.

### Rise Score (Technical Launch Score)

A composite score (0-100) indicating the technical strength of a stock. It is composed of three sub-scores:

1. **Trend Score**: Moving Average alignment (SMA20 > SMA60) and slope.
2. **Momentum Score**: Strength of price movement (RSI, MACD, KD).
3. **Volatility Score**: Potential for explosive moves (Bollinger Band compression).

### V2 Indicators

The optimized set of technical indicators introduced in V4.1. Computed by `core/indicators_v2.py`.Key differences from V1 include 20-day look-ahead labeling for training and stricter "Golden Cross" definitions.

## Technical Terms

* **Golden Cross**: When a short-term moving average (e.g., SMA 20) crosses above a long-term moving average (e.g., SMA 60). In this system, it also applies to KD and MACD indicators.
* **Squeeze**: A period of low volatility where Bollinger Bands contract, often preceding a significant price breakout.
* **Regime**: The current market state (Bullish, Bearish, or Choppy). The AI model uses regime detection to adjust its confidence thresholds.
* **Ensemble V4**: The current AI architecture, combining Gradient Boosting, Random Forest, and MLP (Multi-Layer Perceptron) models to predict the probability of a "Win" outcome.

## System Terms

* **Time Machine**: The backtesting module that simulates historical performance by running the current strategy on past data.
* **Score Persistence**: The V4.1 architecture feature where scores are pre-calculated and stored in the database (`stock_scores` table) rather than computed on-the-fly, enabling millisecond-level API responses.
* **Recalculate**: A batch process (`backend/recalculate.py`) that updates the Rise Score and AI probabilities for all stocks after new market data is synced.

## Governance Terms

* **Engineering Constitution**: The set of fundamental engineering rules and guardrails (located in `.agent/rules/`) that govern AI behavior and ensure code quality.
* **Superpowers**: The methodology of structured, workflow-oriented prompting used for AI-human collaboration.
* **CORTEX/Agent**: The digital collaborator role assumed by the AI, acting as a technical partner rather than just an automation tool.
