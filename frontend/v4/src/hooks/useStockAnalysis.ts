import { useMemo, useCallback } from 'react'
import { useCachedApi } from './useCachedApi'
import { invalidateApiCache } from '../lib/apiClient'
import { MOCK_STOCK_DETAIL } from '../mockData'

export interface StockDetail {
    ticker: string
    name: string
    price: number
    rise_score_breakdown: {
        total: number
        trend: number
        momentum: number
        volatility: number
    }
    ai_probability: number
    analyst_summary: string
    updated_at?: string
    signals: {
        squeeze: boolean
        golden_cross: boolean
        volume_spike: boolean
    }
}

export const useStockAnalysis = (ticker: string | null) => {
    const endpoint = ticker ? `/api/v4/stock/${ticker}` : ''

    const {
        data,
        loading,
        error,
        refetch,
    } = useCachedApi<StockDetail>(endpoint, {
        fallbackData: MOCK_STOCK_DETAIL,
        ttlMs: 20_000,
        throttleMs: 500,
        enabled: Boolean(ticker),
    })

    const recommendationBadge = useMemo(() => {
        if (data.ai_probability >= 70) {
            return { text: 'STRONG BUY', color: 'bg-sniper-green/10 text-sniper-green border-sniper-green/20' }
        }
        if (data.ai_probability >= 50) {
            return { text: 'HOLD', color: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20' }
        }
        return { text: 'HIGH RISK', color: 'bg-red-500/10 text-red-500 border-red-500/20' }
    }, [data.ai_probability])

    const isDbStale = useMemo(() => {
        if (!data.updated_at) return false
        const updated = new Date(data.updated_at)
        return updated.toDateString() !== new Date().toDateString()
    }, [data.updated_at])

    const handleRefetch = useCallback(async () => {
        if (ticker) {
            invalidateApiCache(`/api/v4/stock/${ticker}`)
            await refetch()
        }
    }, [ticker, refetch])

    return {
        data,
        loading,
        error,
        recommendationBadge,
        isDbStale,
        handleRefetch
    }
}
