import React, { memo } from 'react'
import type { SparklinePoint } from '../../hooks/useSparkline'

interface SparklineChartProps {
    data: SparklinePoint[]
    changePercent?: number
}

// Taiwan market: red = up/gain, green = down/loss
const SparklineChart: React.FC<SparklineChartProps> = ({ data, changePercent }) => {
    if (!data || !Array.isArray(data) || data.length < 2) {
        return <div className="h-6 w-full rounded bg-dark-border/30" />
    }

    const points = data.map((d) => d.close)
    const min = Math.min(...points)
    const max = Math.max(...points)
    const range = max - min === 0 ? 1 : max - min

    const isPositive = (changePercent ?? 0) >= 0
    const color = isPositive ? '#ef4444' : '#22c55e'
    const gradientId = `sparkline-gradient-${isPositive ? 'up' : 'down'}-${Math.random().toString(36).substr(2, 9)}`

    // Map points to SVG coordinates (width=100, height=24)
    // Height: padding top=2, padding bottom=2. Range height = 20.
    const mappedPoints = data.map((d, i) => {
        const x = (i / (data.length - 1)) * 100
        const y = 22 - ((d.close - min) / range) * 20
        return { x, y }
    })

    // Construct SVG path string for line
    const linePath = mappedPoints.reduce(
        (path, p, i) => `${path}${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`,
        ''
    )

    // Construct SVG path string for area fill
    const areaPath = `${linePath} L 100 24 L 0 24 Z`

    return (
        <svg
            className="w-full h-6 block"
            viewBox="0 0 100 24"
            preserveAspectRatio="none"
        >
            <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={color} stopOpacity={0.25} />
                    <stop offset="100%" stopColor={color} stopOpacity={0.0} />
                </linearGradient>
            </defs>
            <path
                d={areaPath}
                fill={`url(#${gradientId})`}
                stroke="none"
            />
            <path
                d={linePath}
                fill="none"
                stroke={color}
                strokeWidth={1.5}
                strokeLinecap="round"
                strokeLinejoin="round"
            />
        </svg>
    )
}

export default memo(SparklineChart)
