import { useCallback, useMemo } from 'react'
import { useCachedApi } from './useCachedApi'
import { invalidateApiCache } from '../lib/apiClient'
import { MOCK_MARKET_STATUS } from '../mockData'

export interface MarketStatus {
    bull_ratio: number
    market_temp: number
    ai_sentiment: number
    risk_level: string
    total_stocks: number
    model_version: string
    history?: { timestamp: string }[]
}

export interface StockCandidate {
    ticker: string
    name: string
    price: number
    change_percent?: number
    rise_score: number
    ai_prob: number
    signals?: string[]
    updated_at?: string
}

export interface CandidateMeta {
    updated_at?: string
}

export const useDashboardData = () => {
    const { data: market, loading: isLoading, isPlaceholder } = useCachedApi<MarketStatus>('/api/market_status', {
        fallbackData: MOCK_MARKET_STATUS,
        ttlMs: 30_000,
        throttleMs: 600,
    })

    const { data: candidateMeta, refetch: refetchCandidates } = useCachedApi<CandidateMeta[]>(
        '/api/v4/sniper/candidates?limit=1',
        {
            fallbackData: [],
            ttlMs: 30_000,
            throttleMs: 700,
        },
    )

    const riskColorClass = useMemo(() => {
        if (market.risk_level.includes('HIGH')) return 'text-red-500'
        if (market.risk_level.includes('LOW')) return 'text-sniper-green'
        return 'text-yellow-500'
    }, [market.risk_level])

    const lastUpdated = useMemo(() => {
        return market.history?.[market.history.length - 1]?.timestamp || 'Unknown'
    }, [market.history])

    const dbUpdatedAt = candidateMeta[0]?.updated_at || 'Unknown'

    const isDbStale = useMemo(() => {
        if (!candidateMeta[0]?.updated_at) return false
        const updated = new Date(candidateMeta[0].updated_at)
        return updated.toDateString() !== new Date().toDateString()
    }, [candidateMeta])

    const refreshCandidates = useCallback(async () => {
        invalidateApiCache('/api/v4/sniper/candidates')
        await refetchCandidates()
    }, [refetchCandidates])

    return {
        market,
        isLoading: isLoading || isPlaceholder,
        isPlaceholder,
        riskColorClass,
        lastUpdated,
        dbUpdatedAt,
        isDbStale,
        refreshCandidates
    }
}
