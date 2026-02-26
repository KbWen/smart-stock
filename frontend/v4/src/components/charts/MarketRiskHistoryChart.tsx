import React, { memo } from 'react'
import {
    CartesianGrid,
    Legend,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip as RechartsTooltip,
    XAxis,
    YAxis,
} from 'recharts'

interface MarketHistory {
    timestamp: string
    bull_ratio: number
    market_temp: number
    ai_sentiment: number
}

interface MarketRiskHistoryChartProps {
    history: MarketHistory[]
}

const MarketRiskHistoryChart: React.FC<MarketRiskHistoryChartProps> = ({ history }) => {
    return (
        <div className="rounded-xl border border-dark-border bg-dark-card p-6 shadow-lg">
            <h3 className="mb-6 text-lg font-semibold text-white">風險趨勢歷史 (History)</h3>
            <div className="h-[320px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={history} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                        <XAxis dataKey="timestamp" stroke="#666" tick={{ fill: '#888', fontSize: 12 }} />
                        <YAxis stroke="#666" tick={{ fill: '#888', fontSize: 12 }} />
                        <RechartsTooltip
                            contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333', borderRadius: '8px' }}
                        />
                        <Legend />
                        <Line type="monotone" dataKey="bull_ratio" stroke="#00ff9d" strokeWidth={2} dot={false} name="Bull Ratio" />
                        <Line type="monotone" dataKey="market_temp" stroke="#ef4444" strokeWidth={2} dot={false} name="Market Temp" />
                        <Line type="monotone" dataKey="ai_sentiment" stroke="#f59e0b" strokeWidth={2} dot={false} name="AI Sentiment" />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    )
}

export default memo(MarketRiskHistoryChart)
