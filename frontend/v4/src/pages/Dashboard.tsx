import React, { Suspense, lazy, useCallback, useState } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import MarketStatusHeader from '../components/dashboard/MarketStatusHeader'
import { useDashboardData } from '../hooks/useDashboardData'

const StockList = lazy(() => import('../components/StockList'))
const SniperCard = lazy(() => import('../components/SniperCard'))



const Dashboard: React.FC = () => {
    const [selectedTicker, setSelectedTicker] = useState<string | null>(null)
    const {
        market,
        isLoading,
        riskColorClass,
        lastUpdated,
        dbUpdatedAt,
        isDbStale,
        refreshCandidates
    } = useDashboardData()

    const handleSelectTicker = useCallback((ticker: string) => {
        setSelectedTicker(ticker)
    }, [])

    return (
        <div className="space-y-6">
            <MarketStatusHeader
                market={market}
                isLoading={isLoading}
                riskColorClass={riskColorClass}
            />

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <div className="overflow-hidden glass-card lg:col-span-2">
                    <div className="flex items-center justify-between border-b border-white/10 p-4 bg-white/5">
                        <h3 className="premium-text">Top Candidates</h3>
                        <span className="text-xs text-dark-muted">Updated: {isLoading ? '...' : lastUpdated}</span>
                    </div>
                    <div className="flex items-center justify-between border-b border-dark-border/60 px-4 py-2 text-xs text-dark-muted">
                        <span>資料庫更新時間: {dbUpdatedAt}</span>
                        {isDbStale && (
                            <button
                                type="button"
                                onClick={() => { void refreshCandidates() }}
                                className="inline-flex items-center gap-1 rounded border border-yellow-500/30 bg-yellow-500/10 px-2 py-1 text-yellow-400 hover:bg-yellow-500/20"
                            >
                                <RefreshCw size={12} /> 手動刷新
                            </button>
                        )}
                    </div>
                    {isDbStale && (
                        <div className="flex items-center gap-2 bg-yellow-500/10 px-4 py-2 text-xs text-yellow-400">
                            <AlertTriangle size={14} />
                            偵測到資料非當日，顯示內容可能有延遲。
                        </div>
                    )}
                    <Suspense fallback={<div className="p-6 text-center text-dark-muted">Loading candidates...</div>}>
                        <StockList onSelect={handleSelectTicker} selectedTicker={selectedTicker} />
                    </Suspense>
                </div>

                <div className="lg:col-span-1">
                    <Suspense fallback={<div className="p-6 text-center text-dark-muted">Loading detail card...</div>}>
                        <SniperCard ticker={selectedTicker} />
                    </Suspense>
                </div>
            </div>
        </div>
    )
}

export default Dashboard
