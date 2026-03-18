import React, { memo, useEffect, useMemo } from 'react'
import { MOCK_CANDIDATES } from '../mockData'
import { useCachedApi } from '../hooks/useCachedApi'
import CandidateTable from './dashboard/CandidateTable'
import type { StockCandidate } from '../hooks/useDashboardData'

interface StockListProps {
    onSelect: (ticker: string) => void
    selectedTicker?: string | null
}

interface BulkMetaSignals {
    squeeze?: boolean
    golden_cross?: boolean
    volume_spike?: boolean
}

interface BulkMetaItem {
    signals?: BulkMetaSignals
    trend_score?: number
    momentum_score?: number
    volatility_score?: number
}

interface BulkMetaResponse {
    data: Record<string, BulkMetaItem>
}

const buildSignalTags = (signals?: BulkMetaSignals): string[] => {
    if (!signals) {
        return []
    }
    const tags: string[] = []
    if (signals.squeeze) tags.push('Squeeze')
    if (signals.golden_cross) tags.push('Golden Cross')
    if (signals.volume_spike) tags.push('Volume Spike')
    return tags
}

const sameSignalArray = (left?: string[], right?: string[]): boolean => {
    const leftArr = left ?? []
    const rightArr = right ?? []
    if (leftArr.length !== rightArr.length) return false
    for (let i = 0; i < leftArr.length; i += 1) {
        if (leftArr[i] !== rightArr[i]) return false
    }
    return true
}

const sameV4Signals = (
    left?: StockCandidate['v4_signals'],
    right?: BulkMetaSignals,
): boolean => {
    if (!left && !right) return true
    if (!left || !right) return false
    return (
        left.squeeze === !!right.squeeze &&
        left.golden_cross === !!right.golden_cross &&
        left.volume_spike === !!right.volume_spike
    )
}

const StockList: React.FC<StockListProps> = ({ onSelect, selectedTicker }) => {
    // 1. Fetch initial candidates
    const { data: rawStocks, loading: loadingCandidates, isPlaceholder: isListPlaceholder } = useCachedApi<StockCandidate[]>('/api/v4/sniper/candidates?limit=50', {
        fallbackData: MOCK_CANDIDATES,
        ttlMs: 30_000,
        throttleMs: 1000,
    })

    const tickersStr = useMemo(() => {
        // Use whatever tickers are available (mock or real) so bulk-meta fetch
        // starts immediately instead of waiting for candidates to resolve first.
        return rawStocks.map(s => s.ticker).join(',')
    }, [rawStocks])

    // 2. Fetch bulk meta indicators for those tickers
    const { data: bulkMeta, loading: loadingMeta } = useCachedApi<BulkMetaResponse>(
        tickersStr ? `/api/v4/meta?tickers=${tickersStr}` : '',
        {
            fallbackData: { data: {} },
            ttlMs: 30_000,
            throttleMs: 1000,
            enabled: !!tickersStr
        }
    )

    const metaByTicker = bulkMeta.data

    // 3. Merge meta into stocks
    const enrichedStocks = useMemo(() => {
        if (isListPlaceholder || Object.keys(metaByTicker).length === 0) {
            return rawStocks
        }

        let hasChanges = false
        const next = rawStocks.map((stock) => {
            const meta = metaByTicker[stock.ticker]
            if (!meta) {
                return stock
            }

            const mappedSignals = buildSignalTags(meta.signals)
            const nextSignals = mappedSignals.length > 0 ? mappedSignals : stock.signals
            const unchanged =
                sameV4Signals(stock.v4_signals, meta.signals) &&
                sameSignalArray(stock.signals, nextSignals) &&
                stock.trend === meta.trend_score &&
                stock.momentum === meta.momentum_score &&
                stock.volatility === meta.volatility_score

            if (unchanged) {
                return stock
            }

            hasChanges = true
            return {
                ...stock,
                v4_signals: meta.signals as StockCandidate['v4_signals'],
                signals: nextSignals,
                trend: meta.trend_score,
                momentum: meta.momentum_score,
                volatility: meta.volatility_score
            }
        })
        return hasChanges ? next : rawStocks
    }, [rawStocks, metaByTicker, isListPlaceholder])

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
