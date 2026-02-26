import React, { memo } from 'react'
import type { StockCandidate } from '../../hooks/useDashboardData'

interface CandidateRowProps {
    stock: StockCandidate
    isSelected: boolean
    onSelect: (ticker: string) => void
    rowHeight: number
}

const CandidateRow: React.FC<CandidateRowProps> = ({ stock, isSelected, onSelect, rowHeight }) => {
    const getChangeColor = (change?: number) => {
        if (change === undefined || change === 0) return 'text-dark-muted'
        return change > 0 ? 'text-red-500' : 'text-sniper-green'
    }

    const visibleSignals = stock.signals?.slice(0, 1) ?? []
    const hiddenSignalCount = Math.max((stock.signals?.length ?? 0) - visibleSignals.length, 0)

    return (
        <div
            onClick={() => onSelect(stock.ticker)}
            className={`grid cursor-pointer grid-cols-5 items-center border-b border-dark-border px-3 text-sm transition-colors ${isSelected ? 'bg-sniper-green/10' : 'hover:bg-dark-border/30'
                }`}
            style={{ height: `${rowHeight}px` }}
        >
            <div className="min-w-0 py-2">
                <span className="block truncate font-medium text-white">{stock.ticker}</span>
                <span className="block truncate text-xs text-dark-muted" title={stock.name}>{stock.name}</span>
                {visibleSignals.length > 0 && (
                    <div className="mt-1 flex items-center gap-1 overflow-hidden">
                        {visibleSignals.map((sig: string) => (
                            <span
                                key={sig}
                                className="truncate rounded-sm border border-sniper-gold/20 bg-sniper-gold/10 px-1 py-0.5 text-[10px] font-semibold text-sniper-gold"
                                title={sig}
                            >
                                {sig}
                            </span>
                        ))}
                        {hiddenSignalCount > 0 && (
                            <span className="rounded-sm border border-dark-border px-1 py-0.5 text-[10px] text-dark-muted" title={`另外 ${hiddenSignalCount} 個訊號`}>
                                +{hiddenSignalCount}
                            </span>
                        )}
                    </div>
                )}
            </div>
            <div className="whitespace-nowrap font-mono text-dark-text">
                {stock.price.toFixed(2)}
            </div>
            <div className={`whitespace-nowrap font-medium ${getChangeColor(stock.change_percent)}`}>
                {stock.change_percent != null
                    ? `${stock.change_percent > 0 ? '+' : ''}${stock.change_percent.toFixed(2)}%`
                    : '-'}
            </div>
            <div>
                <span className={`font-bold ${stock.rise_score >= 80 ? 'text-sniper-green' : 'text-white'}`}>
                    {stock.rise_score.toFixed(1)}
                </span>
            </div>
            <div>
                <span className={`font-bold ${stock.ai_prob >= 70 ? 'text-sniper-gold' : 'text-dark-muted'}`}>
                    {stock.ai_prob.toFixed(1)}%
                </span>
            </div>
        </div>
    )
}

export default memo(CandidateRow)
