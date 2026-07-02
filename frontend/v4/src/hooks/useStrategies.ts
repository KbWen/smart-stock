import { useCallback, useEffect, useState } from 'react'
import { fetchJsonWithCache, mutateJson } from '../lib/apiClient'

/** The name of the seeded preset the UI highlights as a novice starting point. */
export const SUGGESTED_DEFAULT_NAME = 'Balanced'

export interface StrategyParams {
    target_gain: number
    stop_loss: number
    holding_days: number
    commission_rate: number
    tax_rate: number
    slippage_rate: number
    days_ago: number
}

export interface Strategy {
    id: number
    name: string
    params: StrategyParams
    notes: string | null
    created_at: string
    updated_at: string
}

/** Subset of the backtest summary returned per strategy in a comparison. */
export interface CompareSummary {
    avg_net_return?: number | null
    avg_return?: number | null
    net_win_rate?: number | null
    win_rate?: number | null
    sharpe_ratio?: number | null
    net_profit_factor?: number | null
    profit_factor?: number | null
    worst_drawdown?: number | null
}

export interface CompareContext {
    sample_size: number
    date_range: { start: string; end: string }
}

export interface CompareResultOk {
    id: number
    name: string
    summary: CompareSummary | null
}

export interface CompareResultError {
    id: number
    name: string
    error: string
}

export type CompareResult = CompareResultOk | CompareResultError

export interface CompareResponse {
    context: CompareContext | null
    results: CompareResult[]
}

export function isCompareError(r: CompareResult): r is CompareResultError {
    return typeof (r as CompareResultError).error === 'string'
}

interface UseStrategiesResult {
    strategies: Strategy[]
    loading: boolean
    error: string | null
    reload: () => Promise<void>
    createStrategy: (name: string, params: StrategyParams, notes?: string) => Promise<void>
    deleteStrategy: (id: number) => Promise<void>
}

/**
 * Loads and mutates saved backtest strategies. Local-only; no promise of returns.
 */
export function useStrategies(): UseStrategiesResult {
    const [strategies, setStrategies] = useState<Strategy[]>([])
    const [loading, setLoading] = useState<boolean>(true)
    const [error, setError] = useState<string | null>(null)

    const reload = useCallback(async (): Promise<void> => {
        setLoading(true)
        setError(null)
        try {
            // Short TTL: strategies change via mutations in this same UI.
            const data = await fetchJsonWithCache<Strategy[]>('/api/strategies', 0, 0)
            setStrategies(Array.isArray(data) ? data : [])
        } catch (e) {
            setError(e instanceof Error ? e.message : '無法載入策略')
            setStrategies([])
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        void reload()
    }, [reload])

    const createStrategy = useCallback(
        async (name: string, params: StrategyParams, notes?: string): Promise<void> => {
            await mutateJson<Strategy>('/api/strategies', 'POST', { name, params, notes })
            await reload()
        },
        [reload],
    )

    const deleteStrategy = useCallback(
        async (id: number): Promise<void> => {
            await mutateJson<{ ok: boolean }>(`/api/strategies/${id}`, 'DELETE')
            await reload()
        },
        [reload],
    )

    return { strategies, loading, error, reload, createStrategy, deleteStrategy }
}

/**
 * Runs a side-by-side comparison of up to 4 strategies. Reuses the backtest
 * engine server-side; returns honest error slots for strategies that fail.
 */
export async function compareStrategies(ids: number[]): Promise<CompareResponse> {
    const query = ids.join(',')
    return fetchJsonWithCache<CompareResponse>(`/api/strategies/compare?ids=${query}`, 0, 0)
}
