import React, { memo } from 'react'
import { AlertTriangle, Crosshair, Loader2, RefreshCw } from 'lucide-react'
import { useStockAnalysis } from '../hooks/useStockAnalysis'
import DetailHeader from './dashboard/DetailHeader'
import ScoreBreakdown from './dashboard/ScoreBreakdown'
import AIAnalyst from './dashboard/AIAnalyst'

interface SniperCardProps {
    ticker: string | null
}

const SniperCard: React.FC<SniperCardProps> = ({ ticker }) => {
    const {
        data,
        loading,
        error,
        recommendationBadge,
        isDbStale,
        handleRefetch
    } = useStockAnalysis(ticker)

    if (!ticker) {
        return (
            <div className="sticky top-24 flex min-h-[400px] flex-col items-center justify-center gap-4 rounded-xl border border-dark-border bg-dark-card p-8 text-dark-muted shadow-xl">
                <Crosshair size={48} className="opacity-20" />
                <div className="text-center">
                    <p className="mb-1 text-lg font-semibold text-white">No Stock Selected</p>
                    <p className="text-sm">Click on a ticker from the list to view detailed AI analysis, trends, and entry signals.</p>
                </div>
            </div>
        )
    }

    if (loading) {
        return (
            <div className="sticky top-24 flex min-h-[400px] flex-col items-center justify-center gap-4 rounded-xl border border-dark-border bg-dark-card p-8 text-dark-muted shadow-xl">
                <Loader2 size={40} className="animate-spin text-sniper-green" />
                <p className="animate-pulse text-sm font-medium">Scanning AI Models for {ticker}...</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="sticky top-24 flex min-h-[400px] flex-col items-center justify-center gap-3 rounded-xl border border-dark-border bg-dark-card p-8 text-red-500 shadow-xl">
                <AlertTriangle size={48} className="opacity-80" />
                <p className="text-lg font-semibold">Error Loading Data</p>
                <p className="text-center text-sm text-red-400 opacity-80">Failed to load details for {ticker}. Ensure backend is running and try again.</p>
            </div>
        )
    }

    return (
        <div className="sticky top-24 rounded-xl border border-dark-border bg-dark-card p-6 shadow-xl overflow-hidden ring-1 ring-white/5">
            <DetailHeader
                ticker={data.ticker}
                name={data.name}
                price={data.price}
                recommendation={recommendationBadge}
                updatedAt={data.updated_at}
            />

            {isDbStale && (
                <div className="mb-4 flex items-center justify-between rounded border border-yellow-500/20 bg-yellow-500/10 px-3 py-2 text-xs text-yellow-400">
                    <span>資料非當日，可能存在延遲。</span>
                    <button
                        type="button"
                        onClick={() => { void handleRefetch() }}
                        className="inline-flex items-center gap-1 rounded border border-yellow-500/30 px-2 py-1 hover:bg-yellow-500/10 transition-colors"
                    >
                        <RefreshCw size={12} /> 重新抓取
                    </button>
                </div>
            )}

            <div className="space-y-6">
                <ScoreBreakdown
                    scores={data.rise_score_breakdown}
                    aiProbability={data.ai_probability}
                />

                <AIAnalyst
                    summary={data.analyst_summary}
                    signals={data.signals}
                />
            </div>
        </div>
    )
}

export default memo(SniperCard)
