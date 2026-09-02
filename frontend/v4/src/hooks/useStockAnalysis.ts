import { useMemo, useCallback } from 'react'
import { useCachedApi } from './useCachedApi'
import { invalidateApiCache } from '../lib/apiClient'
import { deriveGrade } from '../lib/verdict'

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
    ai_probability: number | null  // null = prediction unavailable (honest, not a fake 0)
    // Machine token for WHY there is no number, when the backend can attribute it.
    // null when the cause is the model rather than the data -- model_health reports that.
    ai_unavailable_reason?: 'insufficient_history' | null
    analyst_summary: string
    updated_at?: string
    signals: {
        squeeze: boolean
        golden_cross: boolean
        volume_spike: boolean
    }
    model_health?: {
        status: 'unavailable' | 'degraded' | 'ok'
        message?: string
        version?: string
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
        ttlMs: 20_000,
        throttleMs: 500,
        enabled: Boolean(ticker),
    })

    const recommendationBadge = useMemo(() => {
        if (!data) return null
        return deriveGrade(data.ai_probability, data.model_health?.status)
    }, [data])

    const isDbStale = useMemo(() => {
        if (!data?.updated_at) return false
        const updated = new Date(data.updated_at)
        return updated.toDateString() !== new Date().toDateString()
    }, [data?.updated_at])

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
