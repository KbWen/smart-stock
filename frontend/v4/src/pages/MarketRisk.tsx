import React, { Suspense, lazy, useMemo } from 'react'
import ErrorBoundary from '../components/ErrorBoundary'
import { Activity, Cpu, Database, Info, ShieldAlert, Thermometer } from 'lucide-react'
import Tooltip from '../components/Tooltip'
import { useCachedApi } from '../hooks/useCachedApi'
import { MOCK_MARKET_STATUS } from '../mockData'
import type { MarketStatus } from '../hooks/useDashboardData'

const MarketRiskHistoryChart = lazy(() => import('../components/charts/MarketRiskHistoryChart'))

const MarketRisk: React.FC = () => {
    const { data, loading } = useCachedApi<MarketStatus>('/api/market_status', {
        fallbackData: MOCK_MARKET_STATUS as MarketStatus,
        ttlMs: 30_000,
        throttleMs: 600,
    })

    const riskColorClass = useMemo(() => {
        if (data.risk_level.includes('HIGH')) {
            return 'text-red-500'
        }
        if (data.risk_level.includes('LOW')) {
            return 'text-sniper-green'
        }
        return 'text-yellow-500'
    }, [data.risk_level])

    if (loading && !data) {
        return <div className="p-6 text-dark-muted">Scanning Market Risk...</div>
    }

    return (
        <div className="space-y-6">
            <h2 className="mb-4 flex items-center gap-2 text-2xl font-bold text-white">
                <Activity className="text-sniper-green" />
                Market Radar
            </h2>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <div className="flex flex-col justify-between rounded-xl border border-dark-border bg-dark-card p-6 shadow-lg">
                    <div className="mb-6 flex items-center gap-2">
                        <h3 className="text-lg font-semibold tracking-wide text-white">大盤多空比 (Bull Ratio)</h3>
                        <Tooltip content="反映市場廣度。當比例 > 50% 代表多數股票處於多頭。">
                            <Info size={14} className="text-dark-muted opacity-50" />
                        </Tooltip>
                    </div>
                    <div className="flex flex-1 flex-col items-center justify-center">
                        <div className="mb-4 text-6xl font-black">
                            <span className="text-sniper-green">{data.bull_ratio.toFixed(1)}</span>
                            <span className="text-3xl text-dark-muted">%</span>
                        </div>
                        <div className="mt-6 flex h-4 w-full overflow-hidden rounded-full bg-red-500/20">
                            <div className="h-full bg-sniper-green transition-all duration-1000" style={{ width: `${data.bull_ratio}%` }} />
                        </div>
                    </div>
                </div>

                <div className="flex flex-col justify-between rounded-xl border border-dark-border bg-dark-card p-6 shadow-lg">
                    <div className="mb-4 flex items-center gap-2">
                        <h3 className="text-lg font-semibold tracking-wide text-white">市場狀態 (Market Status)</h3>
                        <Tooltip content="根據動量均值與系統風險評估當前市場過熱或過冷。">
                            <Info size={14} className="text-dark-muted opacity-50" />
                        </Tooltip>
                    </div>
                    <div className="grid grid-cols-2 gap-6">
                        <div className="rounded-lg border border-dark-border bg-dark-bg/30 p-4">
                            <Thermometer className="mb-2 text-sniper-green" size={20} />
                            <div className="text-sm text-dark-muted">Market Temp</div>
                            <div className="text-2xl font-bold text-white">{data.market_temp.toFixed(1)}</div>
                        </div>
                        <div className="rounded-lg border border-dark-border bg-dark-bg/30 p-4">
                            <ShieldAlert className={`mb-2 ${riskColorClass}`} size={20} />
                            <div className="text-sm text-dark-muted">Risk Level</div>
                            <div className={`text-2xl font-bold ${riskColorClass}`}>{data.risk_level}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div className="rounded-xl border border-dark-border bg-dark-card p-4">
                    <div className="mb-1 flex items-center gap-2 text-dark-muted"><Cpu size={16} /> AI Sentiment</div>
                    <p className="text-2xl font-bold text-sniper-gold">{data.ai_sentiment.toFixed(1)}%</p>
                </div>
                <div className="rounded-xl border border-dark-border bg-dark-card p-4">
                    <div className="mb-1 flex items-center gap-2 text-dark-muted"><Database size={16} /> Total Stocks</div>
                    <p className="text-2xl font-bold text-white">{data.total_stocks}</p>
                </div>
                <div className="rounded-xl border border-dark-border bg-dark-card p-4">
                    <div className="mb-1 text-dark-muted">Model Version</div>
                    <p className="text-2xl font-bold text-white">{data.model_version}</p>
                </div>
            </div>

            <ErrorBoundary>
            <Suspense fallback={<div className="rounded-xl border border-dark-border bg-dark-card p-6 text-dark-muted">Loading risk history chart...</div>}>
                {data.history && data.history.length > 0 ? <MarketRiskHistoryChart history={data.history} /> : null}
            </Suspense>
            </ErrorBoundary>
        </div>
    )
}

export default MarketRisk
