import React, { memo, useEffect, useMemo } from 'react'
import { MOCK_CANDIDATES } from '../mockData'
import { useCachedApi } from '../hooks/useCachedApi'
import CandidateTable from './dashboard/CandidateTable'
import type { StockCandidate } from '../hooks/useDashboardData'

interface StockListProps {
    onSelect: (ticker: string) => void
    selectedTicker?: string | null
}

const StockList: React.FC<StockListProps> = ({ onSelect, selectedTicker }) => {
    // 1. Fetch initial candidates
    const { data: rawStocks, loading: loadingCandidates, isPlaceholder: isListPlaceholder } = useCachedApi<StockCandidate[]>('/api/v4/sniper/candidates?limit=50', {
        fallbackData: MOCK_CANDIDATES,
        ttlMs: 30_000,
        throttleMs: 1000,
    })

    const tickersStr = useMemo(() => {
        if (isListPlaceholder) return ''
        return rawStocks.map(s => s.ticker).join(',')
    }, [rawStocks, isListPlaceholder])

    // 2. Fetch bulk meta indicators for those tickers
    const { data: bulkMeta, loading: loadingMeta } = useCachedApi<{ data: Record<string, any> }>(
        tickersStr ? `/api/v4/meta?tickers=${tickersStr}` : '',
        {
            fallbackData: { data: {} },
            ttlMs: 30_000,
            throttleMs: 1000,
            enabled: !!tickersStr
        }
    )

    // 3. Merge meta into stocks
    const enrichedStocks = useMemo(() => {
        if (!bulkMeta?.data || Object.keys(bulkMeta.data).length === 0) return rawStocks

        return rawStocks.map(s => {
            const meta = bulkMeta.data[s.ticker]
            if (!meta) return s

            const signals: string[] = []
            if (meta.signals.squeeze) signals.push('Squeeze')
            if (meta.signals.golden_cross) signals.push('Golden Cross')
            if (meta.signals.volume_spike) signals.push('Volume Spike')

            return {
                ...s,
                v4_signals: meta.signals,
                signals: signals.length > 0 ? signals : s.signals,
                trend: meta.trend_score,
                momentum: meta.momentum_score,
                volatility: meta.volatility_score
            }
        })
    }, [rawStocks, bulkMeta])

    useEffect(() => {
        if (!isListPlaceholder && enrichedStocks.length > 0 && !selectedTicker) {
            onSelect(enrichedStocks[0].ticker)
        }
    }, [enrichedStocks, selectedTicker, onSelect, isListPlaceholder])

    const loading = loadingCandidates || loadingMeta

    if (loading && isListPlaceholder) {
        return <div className="p-6 text-center text-dark-muted animate-pulse">Scanning AI Models...</div>
    }

    if (enrichedStocks.length === 0) {
        return <div className="p-6 text-center text-dark-muted">No candidates found. Try running sync.</div>
    }

    return (
        <CandidateTable
            stocks={enrichedStocks}
            selectedTicker={selectedTicker}
            onSelect={onSelect}
        />
    )
}

export default memo(StockList)
