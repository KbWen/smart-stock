import React, { memo } from 'react'
import { AlertTriangle, Crosshair, Loader2, RefreshCw } from 'lucide-react'
import { useStockAnalysis } from '../hooks/useStockAnalysis'
import DetailHeader from './dashboard/DetailHeader'
import ScoreBreakdown from './dashboard/ScoreBreakdown'
import AIAnalyst from './dashboard/AIAnalyst'
import PriceSignalChart from './charts/PriceSignalChart'

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
            <div className="sticky top-24 flex min-h-[400px] flex-col items-center justify-center gap-4 glass-card p-8 text-dark-muted transition-all duration-300 hover:shadow-[0_0_25px_rgba(245,158,11,0.1)] hover:border-sniper-gold/20 hover:scale-[1.002]">
                <Crosshair size={48} className="opacity-20" />
                <div className="text-center">
                    <p className="mb-1 text-lg font-semibold text-white">尚未選擇標的</p>
                    <p className="text-sm">點選左側清單中的標的，查看 AI 狙擊分析、走勢與進場訊號。</p>
                </div>
            </div>
        )
    }

    if (loading) {
        return (
            <div className="sticky top-24 flex min-h-[400px] flex-col items-center justify-center gap-4 glass-card p-8 text-dark-muted transition-all duration-300 hover:shadow-[0_0_25px_rgba(16,185,129,0.1)] hover:border-sniper-green/20 hover:scale-[1.002]">
                <Loader2 size={40} className="animate-spin text-sniper-green" />
                <p className="animate-pulse text-sm font-medium">正在掃描 {ticker} 的 AI 模型…</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="sticky top-24 flex min-h-[400px] flex-col items-center justify-center gap-3 glass-card p-8 text-red-500 transition-all duration-300 hover:shadow-[0_0_25px_rgba(239,68,68,0.15)] hover:border-red-500/20 hover:scale-[1.002]">
                <AlertTriangle size={48} className="opacity-80" />
                <p className="text-lg font-semibold">資料載入失敗</p>
                <p className="text-center text-sm text-red-400 opacity-80">無法載入 {ticker} 的詳細資料，請確認後端運作後重試。</p>
            </div>
        )
    }

    if (!data) {
        return (
            <div className="sticky top-24 flex min-h-[400px] flex-col items-center justify-center gap-3 glass-card p-8 text-dark-muted">
                <Crosshair size={48} className="opacity-20" />
                <p className="text-sm">{ticker} 目前無可用資料。</p>
            </div>
        )
    }

    return (
        <div className="sticky top-24 glass-card p-6 overflow-hidden ring-1 ring-white/5 transition-all duration-300 hover:shadow-[0_0_25px_rgba(245,158,11,0.15)] hover:border-sniper-gold/30 hover:scale-[1.005]">
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
                    signals={data.signals}
                    modelHealth={data.model_health}
                />

                <PriceSignalChart ticker={ticker} />

                <AIAnalyst
                    summary={data.analyst_summary}
                    signals={data.signals}
                />
            </div>
        </div>
    )
}

export default memo(SniperCard)
