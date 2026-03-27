import React, { memo } from 'react'
import {
    CartesianGrid,
    ComposedChart,
    Line,
    ReferenceDot,
    ResponsiveContainer,
    Tooltip as RechartsTooltip,
    XAxis,
    YAxis,
} from 'recharts'
import { useCachedApi } from '../../hooks/useCachedApi'

interface HistoryPoint {
    date: string
    close: number
    is_squeeze: boolean
    golden_cross: boolean
    volume_spike: boolean
}

interface PriceSignalChartProps {
    ticker: string | null
}

const EMPTY_HISTORY: HistoryPoint[] = []

const PriceSignalChart: React.FC<PriceSignalChartProps> = ({ ticker }) => {
    const endpoint = ticker ? `/api/v4/stock/${ticker}/history` : ''

    const { data, loading, isPlaceholder, error } = useCachedApi<HistoryPoint[]>(endpoint, {
        fallbackData: EMPTY_HISTORY,
        ttlMs: 60_000,
        enabled: Boolean(ticker),
    })

    if (!ticker) return null

    // Show skeleton only during first fetch (not when refreshing stale data)
    if (loading && isPlaceholder) {
        return (
            <div className="h-[220px] w-full animate-pulse rounded-lg bg-dark-border/20" />
        )
    }

    // First fetch failed (backend down / 404) — isPlaceholder stays true on error
    if (data.length === 0 || (error && isPlaceholder)) {
        return (
            <div className="flex h-[220px] items-center justify-center rounded-lg border border-dark-border bg-dark-bg/30 text-xs text-dark-muted">
                No history data
            </div>
        )
    }

    const squeezePoints = data.filter(d => d.is_squeeze)
    const goldenCrossPoints = data.filter(d => d.golden_cross)
    const volumeSpikePoints = data.filter(d => d.volume_spike)

    const closes = data.map(d => d.close)
    const minClose = Math.min(...closes)
    const maxClose = Math.max(...closes)
    const padding = (maxClose - minClose) * 0.05 || 1

    return (
        <div>
            <div className="mb-2 flex items-center justify-between">
                <span className="text-[10px] uppercase tracking-wider font-bold text-dark-muted">
                    Price History (90d)
                </span>
                <div className="flex gap-3 text-[9px] font-bold uppercase tracking-wider">
                    <span className="text-yellow-400">⚡ Squeeze</span>
                    <span className="text-blue-400">✦ Golden Cross</span>
                    <span className="text-purple-400">▲ Vol Spike</span>
                </div>
            </div>
            <div className="h-[200px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                        <XAxis
                            dataKey="date"
                            stroke="#444"
                            tick={{ fill: '#555', fontSize: 10 }}
                            tickFormatter={(v: string) => v.slice(5)}
                            interval={Math.floor(data.length / 5)}
                        />
                        <YAxis
                            stroke="#444"
                            tick={{ fill: '#555', fontSize: 10 }}
                            domain={[minClose - padding, maxClose + padding]}
                            tickFormatter={(v: number) => v.toFixed(0)}
                            width={45}
                        />
                        <RechartsTooltip
                            contentStyle={{ backgroundColor: '#111', border: '1px solid #333', borderRadius: '6px', fontSize: 11 }}
                            formatter={(value: number | string | undefined) => [Number(value ?? 0).toFixed(2), 'Close']}
                            labelStyle={{ color: '#888' }}
                        />
                        <Line
                            type="monotone"
                            dataKey="close"
                            stroke="#4ade80"
                            strokeWidth={1.5}
                            dot={false}
                            activeDot={{ r: 4, fill: '#4ade80' }}
                        />
                        {squeezePoints.map(d => (
                            <ReferenceDot
                                key={`sq-${d.date}`}
                                x={d.date}
                                y={d.close}
                                r={4}
                                fill="#facc15"
                                stroke="none"
                                label={{ value: '⚡', position: 'top', fontSize: 10 }}
                            />
                        ))}
                        {goldenCrossPoints.map(d => (
                            <ReferenceDot
                                key={`gc-${d.date}`}
                                x={d.date}
                                y={d.close}
                                r={4}
                                fill="#60a5fa"
                                stroke="none"
                                label={{ value: '✦', position: 'top', fontSize: 10 }}
                            />
                        ))}
                        {volumeSpikePoints.map(d => (
                            <ReferenceDot
                                key={`vs-${d.date}`}
                                x={d.date}
                                y={d.close}
                                r={4}
                                fill="#c084fc"
                                stroke="none"
                                label={{ value: '▲', position: 'top', fontSize: 10 }}
                            />
                        ))}
                    </ComposedChart>
                </ResponsiveContainer>
            </div>
        </div>
    )
}

export default memo(PriceSignalChart)
