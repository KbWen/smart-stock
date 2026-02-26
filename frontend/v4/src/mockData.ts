export const MOCK_MARKET_STATUS = {
    bull_ratio: 62.5,        // 百分比
    market_temp: 18.3,       // 動量均值
    ai_sentiment: 45.2,      // AI 情緒
    risk_level: "LOW RISK (BULL)",
    total_stocks: 980,
    model_version: "v4.1_sniper_20260213_2240",
    history: [
        { timestamp: "2026-02-20", bull_ratio: 58.1, market_temp: 17.5, ai_sentiment: 43.0 },
        { timestamp: "2026-02-21", bull_ratio: 60.2, market_temp: 18.0, ai_sentiment: 44.1 },
        { timestamp: "2026-02-22", bull_ratio: 62.5, market_temp: 18.3, ai_sentiment: 45.2 }
    ]
};

export const MOCK_CANDIDATES = [
    {
        ticker: "2330.TW", name: "台積電",
        price: 580.0, change_percent: 1.52,
        rise_score: 85.5, ai_prob: 72.1,
        trend: 38.0, momentum: 25.5, volatility: 22.0,
        rsi_14: 62.3, macd_diff: 2.15, volume_ratio: 1.8, signals: []
    },
    {
        ticker: "2317.TW", name: "鴻海",
        price: 114.5, change_percent: -0.87,
        rise_score: 72.0, ai_prob: 55.3,
        trend: 28.0, momentum: 22.0, volatility: 22.0,
        rsi_14: 48.7, macd_diff: -0.51, volume_ratio: 1.2, signals: []
    },
    {
        ticker: "2603.TW", name: "長榮",
        price: 165.0, change_percent: 3.2,
        rise_score: 91.0, ai_prob: 88.5,
        trend: 42.0, momentum: 29.0, volatility: 20.0,
        rsi_14: 71.2, macd_diff: 3.4, volume_ratio: 2.5, signals: ["golden_cross"]
    }
];

export const MOCK_BACKTEST = {
    days_ago: 30,
    model_version: "v4.1_sniper_20260213_2240",
    simulated_date: "2026-01-23",
    candidate_pool_size: 156,
    top_picks: [
        {
            ticker: "2330.TW", name: "台積電",
            entry_date: "2026-01-23",
            entry_price: 560.0, current_price: 580.0,
            actual_return: 0.0357, ai_prob_at_entry: 0.72,
            sniper_result: "HIT" as const,
            max_gain: 0.08,
            max_drawdown: -0.02
        },
        {
            ticker: "2603.TW", name: "長榮",
            entry_date: "2026-01-23",
            entry_price: 180.0, current_price: 165.0,
            actual_return: -0.0833, ai_prob_at_entry: 0.65,
            sniper_result: "STOP" as const,
            max_gain: 0.02,
            max_drawdown: -0.09
        }
    ],
    summary: {
        avg_return: 0.025,
        win_rate: 0.5,
        sniper_hit_rate: 0.5,
        sniper_hits: 1,
        sniper_stops: 1,
        profit_factor: 1.5,
        avg_max_drawdown: -0.055,
        best_stock: "2330.TW",
        best_return: 0.0357
    }
};

export const MOCK_STOCK_DETAIL = {
    ticker: "2330.TW", name: "台積電", price: 580.0,
    rise_score_breakdown: { total: 85.5, trend: 38.0, momentum: 25.5, volatility: 22.0 },
    ai_probability: 72.1,
    analyst_summary: "✅ **Strong Uptrend**: The stock is showing strong bullish momentum...",
    signals: { squeeze: false, golden_cross: true, volume_spike: false }
};
