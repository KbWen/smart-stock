import { useCachedApi } from './useCachedApi'

export interface SparklinePoint {
    date: string
    close: number
}

export function useSparkline(ticker: string | null) {
    const endpoint = ticker ? `/api/v4/stock/${ticker}/sparkline` : ''
    const { data, loading } = useCachedApi<SparklinePoint[]>(endpoint, {
        fallbackData: [],
        ttlMs: 60_000,
        throttleMs: 200,
        enabled: Boolean(ticker),
    })
    return { data, loading }
}
