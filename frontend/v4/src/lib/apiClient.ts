interface CacheRecord<T> {
    data: T
    timestamp: number
}

const responseCache = new Map<string, CacheRecord<unknown>>()
const inFlightRequests = new Map<string, Promise<unknown>>()
const requestTimestamps = new Map<string, number>()
// Tracks invalidation generation per endpoint — prevents in-flight responses
// from writing to the cache after a caller has invalidated that key.
const invalidationGen = new Map<string, number>()

const DEFAULT_TTL_MS = 60_000
const DEFAULT_THROTTLE_MS = 500

/**
 * Fetch JSON with lightweight in-memory cache and throttle control.
 *
 * Args:
 *   endpoint: API endpoint string.
 *   ttlMs: Cache TTL in milliseconds.
 *   throttleMs: Minimum time gap between identical network requests.
 *
 * Returns:
 *   Parsed JSON object with generic type.
 */
export async function fetchJsonWithCache<T>(
    endpoint: string,
    ttlMs: number = DEFAULT_TTL_MS,
    throttleMs: number = DEFAULT_THROTTLE_MS,
    signal?: AbortSignal,
): Promise<T> {
    const now = Date.now()
    const cacheHit = responseCache.get(endpoint) as CacheRecord<T> | undefined

    if (cacheHit && now - cacheHit.timestamp < ttlMs) {
        return cacheHit.data
    }

    const bypassSharedInFlight = signal !== undefined
    const lastRequestAt = requestTimestamps.get(endpoint) ?? 0
    if (!bypassSharedInFlight && inFlightRequests.has(endpoint)) {
        return inFlightRequests.get(endpoint) as Promise<T>
    }

    if (cacheHit && now - lastRequestAt < throttleMs) {
        return cacheHit.data
    }

    const requestGen = invalidationGen.get(endpoint) ?? 0
    const request = fetch(endpoint, { signal }).then(async (response) => {
        if (!response.ok) {
            throw new Error(`Request failed: ${endpoint}`)
        }

        const data = (await response.json()) as T
        // Only write to cache if endpoint hasn't been invalidated since this request started.
        if ((invalidationGen.get(endpoint) ?? 0) === requestGen) {
            responseCache.set(endpoint, { data, timestamp: Date.now() })
            requestTimestamps.set(endpoint, Date.now())
            // Generation is fulfilled — remove it so the Map doesn't grow unboundedly.
            invalidationGen.delete(endpoint)
        }
        return data
    }).finally(() => {
        if (!bypassSharedInFlight) {
            inFlightRequests.delete(endpoint)
        }
    })

    if (!bypassSharedInFlight) {
        inFlightRequests.set(endpoint, request)
    }
    return request
}

export function invalidateApiCache(endpointPrefix: string): void {
    for (const key of responseCache.keys()) {
        if (key.startsWith(endpointPrefix)) {
            responseCache.delete(key)
        }
    }
    // Bump generation and evict in-flight entries: the generation check inside
    // the .then() handler will skip the cache write, fully closing the race.
    for (const key of inFlightRequests.keys()) {
        if (key.startsWith(endpointPrefix)) {
            inFlightRequests.delete(key)
            invalidationGen.set(key, (invalidationGen.get(key) ?? 0) + 1)
        }
    }
}

export function getCachedData<T>(endpoint: string): T | undefined {
    return (responseCache.get(endpoint) as CacheRecord<T> | undefined)?.data
}
