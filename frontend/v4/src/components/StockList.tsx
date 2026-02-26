import React, { memo, useEffect } from 'react'
import { MOCK_CANDIDATES } from '../mockData'
import { useCachedApi } from '../hooks/useCachedApi'
import CandidateTable from './dashboard/CandidateTable'
import type { StockCandidate } from '../hooks/useDashboardData'

interface StockListProps {
    onSelect: (ticker: string) => void
    selectedTicker?: string | null
}

const StockList: React.FC<StockListProps> = ({ onSelect, selectedTicker }) => {
    const { data: stocks, loading, isPlaceholder } = useCachedApi<StockCandidate[]>('/api/v4/sniper/candidates?limit=50', {
        fallbackData: MOCK_CANDIDATES,
        ttlMs: 30_000,
        throttleMs: 700,
    })

    useEffect(() => {
        if (!isPlaceholder && stocks.length > 0 && !selectedTicker) {
            onSelect(stocks[0].ticker)
        }
    }, [stocks, selectedTicker, onSelect, isPlaceholder])

    if (loading && isPlaceholder) {
        return <div className="p-6 text-center text-dark-muted animate-pulse">Scanning AI Models...</div>
    }

    if (stocks.length === 0) {
        return <div className="p-6 text-center text-dark-muted">No candidates found. Try running sync.</div>
    }

    return (
        <CandidateTable
            stocks={stocks}
            selectedTicker={selectedTicker}
            onSelect={onSelect}
        />
    )
}

export default memo(StockList)
