import { useEffect, useRef, useState } from 'react'
import { fetchJsonWithCache } from '../lib/apiClient'

interface UseCachedApiOptions<T> {
    fallbackData: T
    ttlMs?: number
    throttleMs?: number
    enabled?: boolean
}

interface UseCachedApiResult<T> {
    data: T
    loading: boolean
    error: Error | null
    isPlaceholder: boolean
    refetch: () => Promise<void>
}

/**
 * Reusable hook for cached API requests with fallback support.
 */
export function useCachedApi<T>(
    endpoint: string,
    options: UseCachedApiOptions<T>,
): UseCachedApiResult<T> {
    const {
        fallbackData,
        ttlMs = 30_000,
        throttleMs = 500,
        enabled = true,
    } = options

    const [data, setData] = useState<T>(fallbackData)
    const [loading, setLoading] = useState<boolean>(enabled)
    const [error, setError] = useState<Error | null>(null)
    const [isPlaceholder, setIsPlaceholder] = useState<boolean>(true)
    const requestIdRef = useRef(0)

    const fetchData = async (signal?: AbortSignal): Promise<void> => {
        if (!enabled) {
            return
        }
        const requestId = ++requestIdRef.current
        setLoading(true)
        setError(null)
        try {
            const response = await fetchJsonWithCache<T>(endpoint, ttlMs, throttleMs, signal)
            if (requestId !== requestIdRef.current || signal?.aborted) return
            setData(response)
            setIsPlaceholder(false)
        } catch (err) {
            if (signal?.aborted) {
                return
            }
            if (requestId !== requestIdRef.current) {
                return
            }
            setError(err as Error)
            // Only use fallback if we don't already have some data
            if (isPlaceholder) {
                setData(fallbackData)
            }
        } finally {
            if (requestId === requestIdRef.current && !signal?.aborted) {
                setLoading(false)
            }
        }
    }

    useEffect(() => {
        const controller = new AbortController()
        void fetchData(controller.signal)
        return () => controller.abort()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [endpoint, enabled])

    return {
        data,
        loading,
        error,
        isPlaceholder,
        refetch: fetchData,
    }
}
