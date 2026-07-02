import React, { Suspense, lazy, useCallback, useState } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import MarketStatusHeader from '../components/dashboard/MarketStatusHeader'
import GettingStarted from '../components/dashboard/GettingStarted'
import ModelHealthBanner from '../components/ModelHealthBanner'
import { useDashboardData } from '../hooks/useDashboardData'
import ErrorBoundary from '../components/ErrorBoundary'

const StockList = lazy(() => import('../components/StockList'))
const SniperCard = lazy(() => import('../components/SniperCard'))



const Dashboard: React.FC = () => {
    const [selectedTicker, setSelectedTicker] = useState<string | null>(null)
    const {
        market,
        modelHealth,
        isLoading,
        marketError,
        riskColorClass,
        lastUpdated,
        dbUpdatedAt,
        isDbStale,
        syncStatus,
        triggerSync,
    } = useDashboardData()

    const handleSelectTicker = useCallback((ticker: string) => {
        setSelectedTicker(ticker)
    }, [])

    const handleSyncClick = useCallback(() => {
        if (syncStatus.isSyncing) return
        const ok = window.confirm('這會從網路同步全市場（約 1,800 檔，需約 10–15 分鐘）。要開始嗎？')
        if (ok) void triggerSync()
    }, [syncStatus.isSyncing, triggerSync])

    return (
        <div className="space-y-6">
            <GettingStarted modelHealth={modelHealth} />
            <ModelHealthBanner health={modelHealth} />
            {marketError && !market && (
                <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-900/20 px-4 py-2 text-sm text-red-300">
                    <AlertTriangle size={16} />
                    市場狀態載入失敗，請確認後端運作後重試。
                </div>
            )}
            <MarketStatusHeader
                market={market}
                isLoading={isLoading}
                riskColorClass={riskColorClass}
            />

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <div className="overflow-hidden glass-card lg:col-span-2 transition-all duration-300 hover:shadow-[0_0_25px_rgba(16,185,129,0.15)] hover:border-sniper-green/30 hover:scale-[1.002]">
                    <div className="flex items-center justify-between border-b border-white/10 p-4 bg-white/5">
                        <div className="flex items-center gap-2">
                            <h3 className="premium-text">精選候選</h3>
                            {modelHealth?.status === 'unavailable' && (
                                <span className="rounded border border-yellow-500/30 bg-yellow-500/10 px-2 py-0.5 text-[10px] font-semibold text-yellow-400">
                                    示範模式 · AI 未訓練
                                </span>
                            )}
                        </div>
                        <span className="text-xs text-dark-muted">更新: {isLoading ? '...' : lastUpdated}</span>
                    </div>
                    <div className="flex items-center justify-between border-b border-dark-border/60 px-4 py-2 text-xs text-dark-muted">
                        <span>資料庫更新時間: {dbUpdatedAt}</span>
                        <button
                            type="button"
                            onClick={handleSyncClick}
                            disabled={syncStatus.isSyncing}
                            className={`inline-flex items-center gap-1.5 rounded border px-2 py-1 transition-all duration-200 ${
                                syncStatus.isSyncing
                                    ? 'border-sniper-green/30 bg-sniper-green/10 text-sniper-green cursor-not-allowed'
                                    : isDbStale
                                    ? 'border-yellow-500/30 bg-yellow-500/10 text-yellow-400 hover:bg-yellow-500/20'
                                    : 'border-white/10 bg-white/5 text-dark-muted hover:bg-white/10 hover:text-white'
                            }`}
                        >
                            <RefreshCw size={12} className={syncStatus.isSyncing ? 'animate-spin' : ''} />
                            {syncStatus.isSyncing ? '背景同步中...' : '同步資料庫'}
                        </button>
                    </div>
                    {syncStatus.isSyncing && (
                        <div className="border-b border-dark-border/60 px-4 py-3 bg-white/5 space-y-2">
                            <div className="flex items-center justify-between text-xs text-sniper-green">
                                <span className="flex items-center gap-1.5 font-medium animate-pulse">
                                    <RefreshCw className="animate-spin" size={12} />
                                    正在同步資料: {syncStatus.currentTicker || '準備中...'}
                                </span>
                                <span className="font-semibold">
                                    {syncStatus.current} / {syncStatus.total} ({Math.round((syncStatus.current / (syncStatus.total || 1)) * 100)}%)
                                </span>
                            </div>
                            <div className="w-full bg-white/10 rounded-full h-1.5 overflow-hidden">
                                <div
                                    className="bg-sniper-green h-1.5 rounded-full transition-all duration-300 ease-out"
                                    style={{ width: `${(syncStatus.current / (syncStatus.total || 1)) * 100}%` }}
                                />
                            </div>
                            {syncStatus.failedCount > 0 && (
                                <div className="text-[10px] text-red-400">
                                    已跳過/失敗標的: {syncStatus.failedCount} 檔
                                </div>
                            )}
                        </div>
                    )}
                    {isDbStale && !syncStatus.isSyncing && (
                        <div className="flex items-center gap-2 bg-yellow-500/10 px-4 py-2 text-xs text-yellow-400">
                            <AlertTriangle size={14} />
                            偵測到資料非當日，顯示內容可能有延遲。
                        </div>
                    )}
                    <ErrorBoundary>
                    <Suspense fallback={<div className="p-6 text-center text-dark-muted">載入候選清單…</div>}>
                        <StockList onSelect={handleSelectTicker} selectedTicker={selectedTicker} />
                    </Suspense>
                    </ErrorBoundary>
                </div>

                <div className="lg:col-span-1">
                    <ErrorBoundary>
                    <Suspense fallback={<div className="p-6 text-center text-dark-muted">載入詳細卡片…</div>}>
                        <SniperCard ticker={selectedTicker} />
                    </Suspense>
                    </ErrorBoundary>
                </div>
            </div>
        </div>
    )
}

export default Dashboard
