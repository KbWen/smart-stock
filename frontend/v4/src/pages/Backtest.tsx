import React, { Suspense, useMemo, useState } from 'react'
import ErrorBoundary from '../components/ErrorBoundary'
import { Info } from 'lucide-react'
import Tooltip from '../components/Tooltip'
import { useCachedApi } from '../hooks/useCachedApi'

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
    avg_net_return?: number
    net_win_rate?: number
    sharpe_ratio?: number
    worst_drawdown?: number
    net_profit_factor?: number
    avg_max_drawdown?: number
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
    const [commissionRate, setCommissionRate] = useState<number>(0.001425)
    const [taxRate, setTaxRate] = useState<number>(0.003)
    const [slippageRate, setSlippageRate] = useState<number>(0.001)
    const [targetGain, setTargetGain] = useState<number>(0.15)
    const [stopLoss, setStopLoss] = useState<number>(0.05)
    const [holdingDays, setHoldingDays] = useState<number>(20)
    const [showSettings, setShowSettings] = useState<boolean>(false)

    const { data: versions } = useCachedApi<ModelVersion[]>('/api/models', {
        fallbackData: fallbackVersion,
        ttlMs: 60_000,
        throttleMs: 1_000,
    })

    const endpoint = `/api/backtest?days=${days}&version=${selectedVersion}&commission_rate=${commissionRate}&tax_rate=${taxRate}&slippage_rate=${slippageRate}&target_gain=${targetGain}&stop_loss=${stopLoss}&holding_days=${holdingDays}`
    const { data, loading, isPlaceholder, refetch } = useCachedApi<BacktestResponse>(endpoint, {
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

            {/* Transaction Cost Settings Control Panel */}
            <div className="rounded-xl border border-dark-border bg-dark-card/50 backdrop-blur-md p-4">
                <div className="flex items-center justify-between cursor-pointer" onClick={() => setShowSettings(!showSettings)}>
                    <h3 className="font-semibold text-white flex items-center gap-2 text-sm">
                        ⚙️ 交易成本與策略參數設定
                        <span className="text-xs text-dark-muted font-normal">
                            (成本: {((commissionRate + taxRate + slippageRate) * 100).toFixed(2)}% | 策略: +{(targetGain * 100).toFixed(0)}% / -{(stopLoss * 100).toFixed(0)}%, {holdingDays}天)
                        </span>
                    </h3>
                    <button type="button" className="text-xs text-sniper-gold font-semibold hover:underline">
                        {showSettings ? '收合' : '展開變更'}
                    </button>
                </div>
                {showSettings && (
                    <div className="mt-4 border-t border-dark-border/40 pt-4 space-y-6 animate-fade-in">
                        {/* Section A: Transaction Friction */}
                        <div>
                            <h4 className="text-xs font-bold uppercase tracking-wider text-sniper-gold mb-3">💰 交易摩擦成本</h4>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <div className="space-y-2">
                                    <label className="flex justify-between text-xs text-dark-muted font-medium">
                                        <span>買賣單邊手續費 (Commission)</span>
                                        <span className="text-white font-semibold">{(commissionRate * 100).toFixed(4)}%</span>
                                    </label>
                                    <input
                                        type="range"
                                        min={0}
                                        max={0.01}
                                        step={0.0001}
                                        value={commissionRate}
                                        onChange={(e) => setCommissionRate(Number(e.target.value))}
                                        className="w-full h-1.5 bg-dark-border rounded-lg appearance-none cursor-pointer accent-sniper-green"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="flex justify-between text-xs text-dark-muted font-medium">
                                        <span>證券交易稅率 (Transaction Tax)</span>
                                        <span className="text-white font-semibold">{(taxRate * 100).toFixed(2)}%</span>
                                    </label>
                                    <input
                                        type="range"
                                        min={0}
                                        max={0.01}
                                        step={0.0005}
                                        value={taxRate}
                                        onChange={(e) => setTaxRate(Number(e.target.value))}
                                        className="w-full h-1.5 bg-dark-border rounded-lg appearance-none cursor-pointer accent-sniper-green"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="flex justify-between text-xs text-dark-muted font-medium">
                                        <span>滑價成本設定 (Slippage)</span>
                                        <span className="text-white font-semibold">{(slippageRate * 100).toFixed(2)}%</span>
                                    </label>
                                    <input
                                        type="range"
                                        min={0}
                                        max={0.01}
                                        step={0.0005}
                                        value={slippageRate}
                                        onChange={(e) => setSlippageRate(Number(e.target.value))}
                                        className="w-full h-1.5 bg-dark-border rounded-lg appearance-none cursor-pointer accent-sniper-green"
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Section B: Sniper Strategy Parameters */}
                        <div className="border-t border-dark-border/20 pt-4">
                            <h4 className="text-xs font-bold uppercase tracking-wider text-sniper-gold mb-3">🎯 狙擊策略參數</h4>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <div className="space-y-2">
                                    <label className="flex justify-between text-xs text-dark-muted font-medium">
                                        <span>停利目標 (Target Gain)</span>
                                        <span className="text-white font-semibold">{(targetGain * 100).toFixed(0)}%</span>
                                    </label>
                                    <input
                                        type="range"
                                        min={0.01}
                                        max={0.50}
                                        step={0.01}
                                        value={targetGain}
                                        onChange={(e) => setTargetGain(Number(e.target.value))}
                                        className="w-full h-1.5 bg-dark-border rounded-lg appearance-none cursor-pointer accent-sniper-green"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="flex justify-between text-xs text-dark-muted font-medium">
                                        <span>停損閥值 (Stop Loss)</span>
                                        <span className="text-white font-semibold">{(stopLoss * 100).toFixed(0)}%</span>
                                    </label>
                                    <input
                                        type="range"
                                        min={0.01}
                                        max={0.50}
                                        step={0.01}
                                        value={stopLoss}
                                        onChange={(e) => setStopLoss(Number(e.target.value))}
                                        className="w-full h-1.5 bg-dark-border rounded-lg appearance-none cursor-pointer accent-sniper-green"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="flex justify-between text-xs text-dark-muted font-medium">
                                        <span>最大持股天數 (Holding Days)</span>
                                        <span className="text-white font-semibold">{holdingDays} 天</span>
                                    </label>
                                    <input
                                        type="range"
                                        min={1}
                                        max={90}
                                        step={1}
                                        value={holdingDays}
                                        onChange={(e) => setHoldingDays(Number(e.target.value))}
                                        className="w-full h-1.5 bg-dark-border rounded-lg appearance-none cursor-pointer accent-sniper-green"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {!data ? (
                <div className="rounded-xl border border-dark-border bg-dark-card p-8 text-center text-dark-muted">
                    {loading ? '回測執行中...' : '無法載入回測資料，請點擊 Run Backtest 或確認後端運作後重試。'}
                </div>
            ) : data.error ? (
                <div className="rounded-lg border border-red-500/50 bg-red-900/20 p-4 text-red-200">{data.error}</div>
            ) : (
                <>
                    <div className={`grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6 transition-opacity duration-300 ${showLoadingOverlay ? 'opacity-20 pointer-events-none' : 'opacity-100'}`}>
                        {/* 1. Avg Net Return */}
                        <div className="rounded-xl border border-dark-border bg-dark-card p-4 shadow-lg relative overflow-hidden">
                            {showLoadingOverlay && <div className="absolute inset-0 bg-dark-card/50 flex items-center justify-center animate-pulse" />}
                            <div className="mb-1 flex items-center gap-1">
                                <p className="text-[10px] font-semibold uppercase tracking-wider text-dark-muted">平均淨報酬 (Net ROI)</p>
                                <Tooltip content="扣除交易手續費與稅金後的平均報酬率。"><Info size={12} className="text-dark-muted opacity-50" /></Tooltip>
                            </div>
                            <p className={`text-2xl font-bold ${(data.summary?.avg_net_return ?? data.summary?.avg_return ?? 0) >= 0 ? 'text-red-500' : 'text-sniper-green'}`}>{(((data.summary?.avg_net_return ?? data.summary?.avg_return ?? 0) * 100)).toFixed(2)}%</p>
                            <p className="mt-1 text-[10px] text-dark-muted">原始報酬: {((data.summary?.avg_return || 0) * 100).toFixed(2)}%</p>
                        </div>

                        {/* 2. Net Win Rate */}
                        <div className="rounded-xl border border-dark-border bg-dark-card p-4 shadow-lg relative overflow-hidden">
                            {showLoadingOverlay && <div className="absolute inset-0 bg-dark-card/50 flex items-center justify-center animate-pulse" />}
                            <div className="mb-1 flex items-center gap-1">
                                <p className="text-[10px] font-semibold uppercase tracking-wider text-dark-muted">淨勝率 (Net Win Rate)</p>
                                <Tooltip content="扣除交易摩擦後報酬大於 0 的標的佔比。"><Info size={12} className="text-dark-muted opacity-50" /></Tooltip>
                            </div>
                            <p className="text-2xl font-bold text-blue-400">{((data.summary?.net_win_rate ?? data.summary?.win_rate ?? 0) * 100).toFixed(1)}%</p>
                            <p className="mt-1 text-[10px] text-dark-muted">原始勝率: {((data.summary?.win_rate || 0) * 100).toFixed(1)}% ({winCount}/{data.top_picks?.length || 10})</p>
                        </div>

                        {/* 3. Sniper Hit Rate */}
                        <div className="rounded-xl border border-dark-border bg-dark-card p-4 shadow-lg relative overflow-hidden">
                            {showLoadingOverlay && <div className="absolute inset-0 bg-dark-card/50 flex items-center justify-center animate-pulse" />}
                            <div className="mb-1 flex items-center gap-1">
                                <p className="text-[10px] font-semibold uppercase tracking-wider text-dark-muted">🎯 狙擊命中率</p>
                                <Tooltip content={`進場後先觸發 +${(targetGain * 100).toFixed(0)}% 停利目標 vs 先觸發 -${(stopLoss * 100).toFixed(0)}% 停損的比例。`}><Info size={12} className="text-dark-muted opacity-50" /></Tooltip>
                            </div>
                            <p className={`text-2xl font-bold ${(data.summary?.sniper_hit_rate || 0) >= 0.5 ? 'text-sniper-gold' : 'text-dark-muted'}`}>{((data.summary?.sniper_hit_rate || 0) * 100).toFixed(1)}%</p>
                            <p className="mt-1 text-[10px] text-dark-muted">HIT {data.summary?.sniper_hits || 0} / STOP {data.summary?.sniper_stops || 0}</p>
                        </div>

                        {/* 4. Sharpe Ratio */}
                        <div className="rounded-xl border border-dark-border bg-dark-card p-4 shadow-lg relative overflow-hidden">
                            {showLoadingOverlay && <div className="absolute inset-0 bg-dark-card/50 flex items-center justify-center animate-pulse" />}
                            <div className="mb-1 flex items-center gap-1">
                                <p className="text-[10px] font-semibold uppercase tracking-wider text-dark-muted">報酬風險比 (單期)</p>
                                <Tooltip content="本期 Top picks 淨報酬的平均 ÷ 標準差（單期、未年化、未扣無風險利率）。數值越高代表報酬相對其波動越穩定；與年化夏普值不可直接比較。"><Info size={12} className="text-dark-muted opacity-50" /></Tooltip>
                            </div>
                            <p className={`text-2xl font-bold ${(data.summary?.sharpe_ratio || 0) >= 1.0 ? 'text-purple-400' : 'text-dark-muted'}`}>{data.summary?.sharpe_ratio != null ? data.summary.sharpe_ratio.toFixed(2) : '—'}</p>
                            <p className="mt-1 text-[10px] text-dark-muted">平均淨報酬 / 標準差（單期）</p>
                        </div>

                        {/* 5. Net Profit Factor */}
                        <div className="rounded-xl border border-dark-border bg-dark-card p-4 shadow-lg relative overflow-hidden">
                            {showLoadingOverlay && <div className="absolute inset-0 bg-dark-card/50 flex items-center justify-center animate-pulse" />}
                            <div className="mb-1 flex items-center gap-1">
                                <p className="text-[10px] font-semibold uppercase tracking-wider text-dark-muted">淨獲利因子</p>
                                <Tooltip content="淨總獲利 ÷ 淨總虧損。大於 1.5 代表策略具備明顯交易優勢。"><Info size={12} className="text-dark-muted opacity-50" /></Tooltip>
                            </div>
                            <p className={`text-2xl font-bold ${(data.summary?.net_profit_factor ?? data.summary?.profit_factor ?? 0) >= 1.5 ? 'text-sniper-green' : 'text-dark-muted'}`}>{data.summary?.net_profit_factor ?? data.summary?.profit_factor ?? '—'}</p>
                            <p className="mt-1 text-[10px] text-dark-muted">原始因子: {data.summary?.profit_factor || '—'}</p>
                        </div>

                        {/* 6. Worst Drawdown */}
                        <div className="rounded-xl border border-dark-border bg-dark-card p-4 shadow-lg relative overflow-hidden">
                            {showLoadingOverlay && <div className="absolute inset-0 bg-dark-card/50 flex items-center justify-center animate-pulse" />}
                            <div className="mb-1 flex items-center gap-1">
                                <p className="text-[10px] font-semibold uppercase tracking-wider text-dark-muted">最差單股回撤</p>
                                <Tooltip content="所有 Top Picks 中，表現最差的個股在持股期間的最大下跌百分比。"><Info size={12} className="text-dark-muted opacity-50" /></Tooltip>
                            </div>
                            <p className="text-2xl font-bold text-red-400">{data.summary?.worst_drawdown != null ? `${data.summary.worst_drawdown.toFixed(1)}%` : '—'}</p>
                            <p className="mt-1 text-[10px] text-dark-muted">平均回撤: {data.summary?.avg_max_drawdown != null ? `${data.summary.avg_max_drawdown.toFixed(1)}%` : '—'}</p>
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
