import React, { Suspense, useMemo, useState } from 'react'
import ErrorBoundary from '../components/ErrorBoundary'
import { Info } from 'lucide-react'
import Tooltip from '../components/Tooltip'
import { useCachedApi } from '../hooks/useCachedApi'
import { MOCK_BACKTEST } from '../mockData'

import BacktestEquityChart from '../components/charts/BacktestEquityChart'
import BacktestTable from '../components/dashboard/BacktestTable'
import type { BacktestPick } from '../components/dashboard/BacktestTable'

interface ModelVersion {
    version: string
    timestamp: string
}

interface BacktestSummary {
    avg_return: number
    win_rate: number
    sniper_hit_rate: number
    sniper_hits: number
    sniper_stops: number
    profit_factor: number
}

interface BacktestHistoryPoint {
    date: string
    equity: number
}

interface BacktestResponse {
    error?: string
    summary: BacktestSummary
    history?: BacktestHistoryPoint[]
    top_picks?: BacktestPick[]
}

const fallbackVersion: ModelVersion[] = [{ version: 'v4.1.0-lite', timestamp: '2024-03-24' }]

const Backtest: React.FC = () => {
    const [selectedVersion, setSelectedVersion] = useState<string>('latest')
    const [days, setDays] = useState<number>(30)

    const { data: versions } = useCachedApi<ModelVersion[]>('/api/models', {
        fallbackData: fallbackVersion,
        ttlMs: 60_000,
        throttleMs: 1_000,
    })

    const endpoint = `/api/backtest?days=${days}&version=${selectedVersion}`
    const { data, loading, isPlaceholder, refetch } = useCachedApi<BacktestResponse>(endpoint, {
        fallbackData: MOCK_BACKTEST as BacktestResponse,
        ttlMs: 20_000,
        throttleMs: 600,
    })

    const winCount = useMemo(() => {
        const winRate = data?.summary?.win_rate || 0
        const picksCount = data?.top_picks?.length || 10
        return (winRate * picksCount).toFixed(0)
    }, [data?.summary?.win_rate, data?.top_picks?.length])

    const showLoadingOverlay = loading && isPlaceholder

    return (
        <div className="space-y-6 animate-fade-in">
            <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
                <h2 className="text-2xl font-bold uppercase tracking-widest text-white">AI 回測報告</h2>

                <div className="flex items-center gap-3">
                    <select value={selectedVersion} onChange={(event) => setSelectedVersion(event.target.value)} className="rounded-lg border border-dark-border bg-dark-card p-2 text-sm text-white outline-none focus:border-sniper-green focus:ring-sniper-green">
                        <option value="latest">Latest Model</option>
                        {versions?.map((model) => (
                            <option key={model.version} value={model.version}>{model.version}</option>
                        ))}
                    </select>

                    <select value={days} onChange={(event) => setDays(Number(event.target.value))} className="rounded-lg border border-dark-border bg-dark-card p-2 text-sm text-white outline-none focus:border-sniper-green focus:ring-sniper-green">
                        <option value={10}>10 個交易日前</option>
                        <option value={30}>30 個交易日前</option>
                        <option value={60}>60 個交易日前</option>
                        <option value={90}>90 個交易日前</option>
                    </select>

                    <button type="button" onClick={() => void refetch()} disabled={loading} className="rounded-lg bg-sniper-green px-4 py-2 text-sm uppercase tracking-wider text-black transition-colors disabled:opacity-50">
                        {loading ? 'Running...' : 'Run Backtest'}
                    </button>
                </div>
            </div>

            {data?.error ? (
                <div className="rounded-lg border border-red-500/50 bg-red-900/20 p-4 text-red-200">{data.error}</div>
            ) : (
                <>
                    <div className={`grid grid-cols-2 gap-4 md:grid-cols-4 transition-opacity duration-300 ${showLoadingOverlay ? 'opacity-20 pointer-events-none' : 'opacity-100'}`}>
                        <div className="rounded-xl border border-dark-border bg-dark-card p-4 shadow-lg relative overflow-hidden">
                            {showLoadingOverlay && <div className="absolute inset-0 bg-dark-card/50 flex items-center justify-center animate-pulse" />}
                            <div className="mb-1 flex items-center gap-1">
                                <p className="text-xs font-semibold uppercase tracking-wider text-dark-muted">平均報酬 (Avg Return)</p>
                                <Tooltip content="回測期間所有 Top Picks 的算術平均報酬率。"><Info size={12} className="text-dark-muted opacity-50" /></Tooltip>
                            </div>
                            <p className={`text-2xl font-bold ${(data.summary?.avg_return || 0) >= 0 ? 'text-red-500' : 'text-sniper-green'}`}>{((data.summary?.avg_return || 0) * 100).toFixed(2)}%</p>
                        </div>
                        <div className="rounded-xl border border-dark-border bg-dark-card p-4 shadow-lg relative overflow-hidden">
                            {showLoadingOverlay && <div className="absolute inset-0 bg-dark-card/50 flex items-center justify-center animate-pulse" />}
                            <div className="mb-1 flex items-center gap-1">
                                <p className="text-xs font-semibold uppercase tracking-wider text-dark-muted">勝率 (Win Rate)</p>
                                <Tooltip content="報酬率 > 0 的股票佔比。"><Info size={12} className="text-dark-muted opacity-50" /></Tooltip>
                            </div>
                            <p className="text-2xl font-bold text-blue-400">{((data.summary?.win_rate || 0) * 100).toFixed(1)}%</p>
                            <p className="mt-1 text-[10px] text-dark-muted">報酬 &gt; 0 的標的佔比 ({winCount}/{data.top_picks?.length || 10})</p>
                        </div>
                        <div className="rounded-xl border border-dark-border bg-dark-card p-4 shadow-lg relative overflow-hidden">
                            {showLoadingOverlay && <div className="absolute inset-0 bg-dark-card/50 flex items-center justify-center animate-pulse" />}
                            <div className="mb-1 flex items-center gap-1">
                                <p className="text-xs font-semibold uppercase tracking-wider text-dark-muted">🎯 狙擊命中率</p>
                                <Tooltip content="進場後先觸發 +15% 目標 vs 先觸發 -5% 停損的比例。"><Info size={12} className="text-dark-muted opacity-50" /></Tooltip>
                            </div>
                            <p className={`text-2xl font-bold ${(data.summary?.sniper_hit_rate || 0) >= 0.5 ? 'text-sniper-gold' : 'text-dark-muted'}`}>{((data.summary?.sniper_hit_rate || 0) * 100).toFixed(1)}%</p>
                            <p className="mt-1 text-[10px] text-dark-muted">HIT {data.summary?.sniper_hits || 0} / STOP {data.summary?.sniper_stops || 0}</p>
                        </div>
                        <div className="rounded-xl border border-dark-border bg-dark-card p-4 shadow-lg relative overflow-hidden">
                            {showLoadingOverlay && <div className="absolute inset-0 bg-dark-card/50 flex items-center justify-center animate-pulse" />}
                            <div className="mb-1 flex items-center gap-1">
                                <p className="text-xs font-semibold uppercase tracking-wider text-dark-muted">獲利因子</p>
                                <Tooltip content="總獲利金額 ÷ 總虧損金額，大於 1.5 代表具備優勢。"><Info size={12} className="text-dark-muted opacity-50" /></Tooltip>
                            </div>
                            <p className={`text-2xl font-bold ${(data.summary?.profit_factor || 0) >= 1.5 ? 'text-sniper-green' : 'text-dark-muted'}`}>{data.summary?.profit_factor || '—'}</p>
                        </div>
                    </div>

                    <div className={`transition-opacity duration-300 ${showLoadingOverlay ? 'opacity-20' : 'opacity-100'}`}>
                        <ErrorBoundary>
                        <Suspense fallback={<div className="rounded-xl border border-dark-border bg-dark-card p-6 text-dark-muted">Loading chart...</div>}>
                            {data.history && data.history.length > 0 ? <BacktestEquityChart history={data.history} /> : null}
                        </Suspense>
                        </ErrorBoundary>

                        {data.top_picks && data.top_picks.length > 0 && (
                            <BacktestTable picks={data.top_picks} />
                        )}
                    </div>
                </>
            )}
        </div>
    )
}

export default Backtest
