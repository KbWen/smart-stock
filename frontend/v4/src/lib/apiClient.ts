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

export interface MutationError extends Error {
    status?: number
}

/**
 * POST/PUT/DELETE JSON helper for mutations (no caching).
 *
 * Sends `X-Requested-With: XMLHttpRequest` to stay consistent with the app's
 * lightweight CSRF defense on mutating endpoints. On a non-2xx response it
 * throws a `MutationError` carrying the HTTP `status` and the server's generic
 * `detail` message (never a raw stack — the backend already scrubs those).
 */
export async function mutateJson<T>(
    endpoint: string,
    method: 'POST' | 'PUT' | 'DELETE',
    body?: unknown,
): Promise<T> {
    const response = await fetch(endpoint, {
        method,
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
        },
        body: body === undefined ? undefined : JSON.stringify(body),
    })

    if (!response.ok) {
        let detail = `Request failed: ${endpoint}`
        try {
            // Backend error shapes: HTTPException -> {message}; body-validation
            // 422 -> {detail: [{msg}]}. Handle both so the user sees a real message.
            const errBody = (await response.json()) as {
                message?: unknown
                detail?: unknown
            }
            if (typeof errBody?.message === 'string') {
                detail = errBody.message
            } else if (typeof errBody?.detail === 'string') {
                detail = errBody.detail
            } else if (Array.isArray(errBody?.detail)) {
                const msgs = (errBody.detail as Array<{ msg?: unknown }>)
                    .map((e) => (typeof e?.msg === 'string' ? e.msg : null))
                    .filter((m): m is string => m !== null)
                if (msgs.length > 0) detail = msgs.join('; ')
            }
        } catch {
            /* non-JSON error body — keep the generic message */
        }
        const err = new Error(detail) as MutationError
        err.status = response.status
        throw err
    }

    const text = await response.text()
    return (text ? (JSON.parse(text) as T) : ({} as T))
}
