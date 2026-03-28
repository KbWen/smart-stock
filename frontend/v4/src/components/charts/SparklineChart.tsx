import React, { memo } from 'react'
import { LineChart, Line, ResponsiveContainer } from 'recharts'
import type { SparklinePoint } from '../../hooks/useSparkline'

interface SparklineChartProps {
    data: SparklinePoint[]
    changePercent?: number
}

// Taiwan market: red = up/gain, green = down/loss
const SparklineChart: React.FC<SparklineChartProps> = ({ data, changePercent }) => {
    if (!data || data.length < 2) {
        return <div className="h-6 w-full rounded bg-dark-border/30" />
    }

    const isPositive = (changePercent ?? 0) >= 0
    const color = isPositive ? '#ef4444' : '#22c55e'

    return (
        <ResponsiveContainer width="100%" height={24}>
            <LineChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 2 }}>
                <Line
                    type="monotone"
                    dataKey="close"
                    stroke={color}
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                />
            </LineChart>
        </ResponsiveContainer>
    )
}

export default memo(SparklineChart)
