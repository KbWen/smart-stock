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

interface BacktestPoint {
    date: string
    equity: number
}

interface BacktestEquityChartProps {
    history: BacktestPoint[]
}

const BacktestEquityChart: React.FC<BacktestEquityChartProps> = ({ history }) => {
    return (
        <div className="mt-6 rounded-xl border border-dark-border bg-dark-card p-6 shadow-lg">
            <h3 className="mb-6 text-lg font-semibold text-white">資產曲線 (Equity Curve)</h3>
            <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={history} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                        <XAxis dataKey="date" stroke="#666" tick={{ fill: '#888', fontSize: 12 }} tickMargin={10} />
                        <YAxis
                            stroke="#666"
                            tick={{ fill: '#888', fontSize: 12 }}
                            domain={['auto', 'auto']}
                            tickFormatter={(value: number) => value.toLocaleString()}
                        />
                        <RechartsTooltip
                            contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333', borderRadius: '8px' }}
                            itemStyle={{ fontWeight: 'bold' }}
                            formatter={(value: number | string | undefined) => Number(value || 0).toLocaleString()}
                        />
                        <Legend wrapperStyle={{ paddingTop: '20px' }} />
                        <Line
                            type="monotone"
                            dataKey="equity"
                            name="模擬資產 (Equity)"
                            stroke="#f59e0b"
                            strokeWidth={3}
                            dot={false}
                            activeDot={{ r: 6 }}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    )
}

export default memo(BacktestEquityChart)
