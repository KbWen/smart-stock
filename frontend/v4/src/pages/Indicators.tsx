import React, { useMemo, useState } from 'react'
import { MOCK_CANDIDATES } from '../mockData'
import { Info } from 'lucide-react'
import Tooltip from '../components/Tooltip'
import { useCachedApi } from '../hooks/useCachedApi'

interface StockTechnical {
    ticker: string
    name: string
    price: number
    change_pct: number
    rise_score: number
    ai_prob: number
    trend: number
    momentum: number
    volatility: number
    signals: string[]
}

interface ApiCandidate {
    ticker: string
    name: string
    price: number
    change_percent?: number
    rise_score?: number
    ai_prob?: number
    trend?: number
    momentum?: number
    volatility?: number
    signals?: string[]
}

const INDICATORS_SCORE_THRESHOLD = 80
const INDICATORS_AI_THRESHOLD = 60

const Indicators: React.FC = () => {
    const [filter, setFilter] = useState<'ALL' | 'HIGH SCORE' | 'HIGH AI'>('ALL')

    const { data: rawData, loading, isPlaceholder } = useCachedApi<ApiCandidate[]>(
        '/api/v4/sniper/candidates?limit=100',
        { fallbackData: MOCK_CANDIDATES as ApiCandidate[], ttlMs: 30_000, throttleMs: 1_000 },
    )

    const stocks = useMemo<StockTechnical[]>(() =>
        rawData.map((s) => ({
            ticker: s.ticker,
            name: s.name,
            price: s.price,
            change_pct: s.change_percent ?? 0,
            rise_score: s.rise_score ?? 0,
            ai_prob: s.ai_prob ?? 0,
            trend: s.trend ?? 0,
            momentum: s.momentum ?? 0,
            volatility: s.volatility ?? 0,
            signals: s.signals ?? [],
        })),
        [rawData],
    )

    const filteredStocks = useMemo(() =>
        stocks
            .filter(s => {
                if (filter === 'HIGH SCORE') return s.rise_score > INDICATORS_SCORE_THRESHOLD
                if (filter === 'HIGH AI') return s.ai_prob >= INDICATORS_AI_THRESHOLD
                return true
            })
            .sort((a, b) => {
                if (filter === 'HIGH AI') return b.ai_prob - a.ai_prob
                return b.rise_score - a.rise_score
            }),
        [stocks, filter],
    )

    if (loading && isPlaceholder) return <div className="p-6 text-dark-muted">Loading Technical Scanner...</div>

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold text-white">
                    Technical Scanner
                    <span className="text-sm text-dark-muted font-normal ml-2">
                        ({filteredStocks.length} 檔)
                    </span>
                </h2>
                <div className="flex bg-dark-card rounded-lg p-1 border border-dark-border">
                    {(['ALL', 'HIGH SCORE', 'HIGH AI'] as const).map(f => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${filter === f ? 'bg-sniper-green text-dark-bg' : 'text-dark-muted hover:text-white'
                                }`}
                        >
                            {f}
                        </button>
                    ))}
                </div>
            </div>

            <div className="bg-dark-card rounded-xl border border-dark-border shadow-lg overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-dark-border/30 text-dark-muted uppercase text-xs">
                            <tr>
                                <th className="p-4">Ticker</th>
                                <th className="p-4 text-right">Price</th>
                                <th className="p-4 text-right">Change</th>
                                <th className="p-4 text-right">
                                    <div className="flex items-center justify-end gap-1">
                                        Rise Score
                                        <Tooltip content="技術評分 (0-100)。">
                                            <Info size={12} className="opacity-50" />
                                        </Tooltip>
                                    </div>
                                </th>
                                <th className="p-4 text-right">
                                    <div className="flex items-center justify-end gap-1">
                                        AI Prob
                                        <Tooltip content="AI 預測達成 15% 漲幅的機率。">
                                            <Info size={12} className="opacity-50" />
                                        </Tooltip>
                                    </div>
                                </th>
                                <th className="p-4 text-right">
                                    <div className="flex items-center justify-end gap-1">
                                        Trend · Mom · Vol
                                        <Tooltip content="Trend (趨勢/40), Momentum (動能/30), Volatility (波動率/30)。">
                                            <Info size={12} className="opacity-50" />
                                        </Tooltip>
                                    </div>
                                </th>
                                <th className="p-4">Signals</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-dark-border">
                            {filteredStocks.map((stock) => (
                                <tr key={stock.ticker} className="hover:bg-dark-border/30 transition-colors group">
                                    <td className="p-4 font-medium text-white">
                                        {stock.ticker} <span className="text-dark-muted font-normal ml-1">{stock.name}</span>
                                    </td>
                                    <td className="p-4 text-right text-white">{stock.price.toFixed(2)}</td>
                                    <td className={`p-4 text-right font-bold ${stock.change_pct >= 0 ? 'text-red-500' : 'text-sniper-green'}`}>
                                        {stock.change_pct >= 0 ? '+' : ''}{stock.change_pct.toFixed(2)}%
                                    </td>
                                    <td className="p-4 text-right">
                                        <span className={`px-2 py-1 rounded font-bold ${stock.rise_score > INDICATORS_SCORE_THRESHOLD ? 'bg-sniper-green/10 text-sniper-green' : 'text-dark-muted'}`}>
                                            {stock.rise_score.toFixed(1)}
                                        </span>
                                    </td>
                                    <td className="p-4 text-right">
                                        <span className={`px-2 py-1 rounded font-bold ${stock.ai_prob >= 70 ? 'bg-sniper-gold/10 text-sniper-gold' : 'text-dark-muted'}`}>
                                            {stock.ai_prob.toFixed(1)}%
                                        </span>
                                    </td>
                                    <td className="p-4 text-right text-dark-muted">
                                        <span className="text-blue-400">{stock.trend.toFixed(1)}</span>
                                        <span className="mx-1">/</span>
                                        <span className="text-purple-400">{stock.momentum.toFixed(1)}</span>
                                        <span className="mx-1">/</span>
                                        <span className="text-yellow-500">{stock.volatility.toFixed(1)}</span>
                                    </td>
                                    <td className="p-4">
                                        <div className="flex gap-1 flex-wrap">
                                            {stock.signals.slice(0, 2).map((sig, i) => {
                                                const bullish = ['黃金交叉', '多頭', '超賣', '低檔', '收斂']
                                                const bearish = ['死亡交叉', '空頭', '過熱', '高檔', '擴張']
                                                let colorClass = 'bg-dark-border text-dark-muted border-dark-border'
                                                if (bullish.some(k => sig.includes(k))) colorClass = 'bg-sniper-green/10 text-sniper-green border-sniper-green/30'
                                                else if (bearish.some(k => sig.includes(k))) colorClass = 'bg-red-500/10 text-red-400 border-red-500/30'

                                                return (
                                                    <span key={i} className={`px-2 py-0.5 rounded text-[10px] border group-hover:border-opacity-100 transition-colors ${colorClass}`}>
                                                        {sig}
                                                    </span>
                                                )
                                            })}
                                            {stock.signals.length === 0 && <span className="text-dark-muted text-[10px]">-</span>}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}

export default Indicators
