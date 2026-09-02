import { useCallback, useEffect, useMemo, useState } from 'react'
import { useCachedApi } from './useCachedApi'
import { invalidateApiCache } from '../lib/apiClient'
import { BREADTH_COLOR, BREADTH_LABEL, breadthOf } from '../lib/breadth'

export interface MarketHistory {
    timestamp: string
    bull_ratio: number
    market_temp: number
    ai_sentiment: number
}

export interface ModelHealth {
    status: 'ok' | 'degraded' | 'unavailable'
    version?: string
    message: string
}

export interface MarketStatus {
    bull_ratio: number
    market_temp: number
    ai_sentiment: number
    breadth_level: string
    total_stocks: number
    model_version: string
    model_health?: ModelHealth
    history?: MarketHistory[]
}

export interface StockCandidate {
    ticker: string
    name: string
    price: number
    change_percent?: number
    rise_score: number
    ai_prob: number | null  // null = prediction unavailable (honest, not a fake 0)
    signals?: string[]      // Legacy support for string tags
    v4_signals?: {          // New structured signals
        squeeze: boolean
        golden_cross: boolean
        volume_spike: boolean
        rsi: number
        macd_diff: number
        rel_vol: number
    }
    updated_at?: string
    // Simplified breakdown if merged
    trend?: number
    momentum?: number
    volatility?: number
    sparkline?: { date: string; close: number }[]
}

export interface CandidateMeta {
    updated_at?: string
}

export const useDashboardData = () => {
    const { data: market, loading: marketLoading, isPlaceholder, error: marketError } = useCachedApi<MarketStatus>('/api/market_status', {
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

    const [syncStatus, setSyncStatus] = useState({
        isSyncing: false,
        total: 0,
        current: 0,
        failedCount: 0,
        currentTicker: '',
    })

    const breadth = useMemo(() => breadthOf(market?.breadth_level), [market])
    const riskColorClass = useMemo(() => BREADTH_COLOR[breadth], [breadth])
    const breadthLabel = useMemo(() => BREADTH_LABEL[breadth], [breadth])

    const lastUpdated = useMemo(() => {
        return market?.history?.[market.history.length - 1]?.timestamp || '未知'
    }, [market])

    const dbUpdatedAt = candidateMeta?.[0]?.updated_at || '未知'

    const isDbStale = useMemo(() => {
        const updatedAt = candidateMeta?.[0]?.updated_at
        if (!updatedAt) return false
        const updated = new Date(updatedAt)
        return updated.toDateString() !== new Date().toDateString()
    }, [candidateMeta])

    const refreshCandidates = useCallback(async () => {
        invalidateApiCache('/api/market_status')
        invalidateApiCache('/api/v4/sniper/candidates')
        invalidateApiCache('/api/v4/meta')
        await refetchCandidates()
    }, [refetchCandidates])

    const triggerSync = useCallback(async () => {
        try {
            setSyncStatus((prev) => ({ ...prev, isSyncing: true }))
            await fetch('/api/sync', { method: 'POST' })
        } catch (err) {
            console.error('Failed to trigger sync', err)
            setSyncStatus((prev) => ({ ...prev, isSyncing: false }))
        }
    }, [])

    useEffect(() => {
        let intervalId: any = null

        const checkStatus = async () => {
            try {
                const res = await fetch('/api/sync/status')
                if (res.ok) {
                    const data = await res.json()
                    const isNowSyncing = data.is_syncing

                    setSyncStatus({
                        isSyncing: isNowSyncing,
                        total: data.total || 0,
                        current: data.current || 0,
                        failedCount: data.failed_count || 0,
                        currentTicker: data.current_ticker || '',
                    })

                    if (isNowSyncing) {
                        if (!intervalId) {
                            intervalId = setInterval(checkStatus, 2000)
                        }
                    } else if (intervalId) {
                        clearInterval(intervalId)
                        intervalId = null
                        // Refresh all views when sync finishes
                        await refreshCandidates()
                    }
                }
            } catch (err) {
                console.error('Failed to fetch sync status', err)
            }
        }

        // Check immediately on mount
        void checkStatus()

        // Also check if triggerSync has updated isSyncing to true
        if (syncStatus.isSyncing && !intervalId) {
            intervalId = setInterval(checkStatus, 2000)
        }

        return () => {
            if (intervalId) {
                clearInterval(intervalId)
            }
        }
    }, [syncStatus.isSyncing, refreshCandidates])

    return {
        market,
        modelHealth: market?.model_health ?? null,
        // On a persistent fetch error, isPlaceholder stays true forever; gate on
        // marketError so the UI breaks out of the skeleton into an honest error state.
        isLoading: (marketLoading || isPlaceholder) && !marketError,
        isPlaceholder,
        marketError,
        riskColorClass,
        breadthLabel,
        lastUpdated,
        dbUpdatedAt,
        isDbStale,
        refreshCandidates,
        syncStatus,
        triggerSync,
    }
}
