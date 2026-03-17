/**
 * apiClient — unit tests for cache, throttle, and deduplication logic.
 *
 * These tests also serve as the "standard mock pattern" reference for the
 * project (spec: frontend-testing.md AC#4: Data Mocking).
 *
 * Pattern: Use vi.spyOn(global, 'fetch') to intercept requests, then restore
 * with vi.restoreAllMocks() in afterEach.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
    fetchJsonWithCache,
    getCachedData,
    invalidateApiCache,
} from '../apiClient'

// ─── Helpers ────────────────────────────────────────────────────────────────

const mockFetch = (payload: unknown, status = 200) => {
    return vi.spyOn(global, 'fetch').mockResolvedValue({
        ok: status >= 200 && status < 300,
        status,
        json: async () => payload,
    } as Response)
}

// ─── Tests ──────────────────────────────────────────────────────────────────

describe('fetchJsonWithCache', () => {
    afterEach(() => {
        vi.restoreAllMocks()
        // Invalidate all cache entries between tests
        invalidateApiCache('/api')
        invalidateApiCache('/test')
    })

    it('fetches and returns data on first call', async () => {
        const spy = mockFetch({ value: 42 })
        const result = await fetchJsonWithCache<{ value: number }>('/test/resource', 10_000)
        expect(result).toEqual({ value: 42 })
        expect(spy).toHaveBeenCalledTimes(1)
    })

    it('returns cached data on second call within TTL', async () => {
        const spy = mockFetch({ value: 99 })
        await fetchJsonWithCache('/test/cached', 60_000)
        const result2 = await fetchJsonWithCache('/test/cached', 60_000)
        expect(result2).toEqual({ value: 99 })
        // Only one network call
        expect(spy).toHaveBeenCalledTimes(1)
    })

    it('bypasses cache when TTL is 0', async () => {
        const spy = mockFetch({ version: 2 })
        await fetchJsonWithCache('/test/noCache', 60_000)
        await fetchJsonWithCache('/test/noCache', 0, 0)
        // Should re-fetch
        expect(spy).toHaveBeenCalledTimes(2)
    })

    it('throws when response is not ok', async () => {
        mockFetch(null, 500)
        await expect(
            fetchJsonWithCache('/test/error', 0, 0),
        ).rejects.toThrow('Request failed')
    })
})

describe('invalidateApiCache', () => {
    afterEach(() => {
        vi.restoreAllMocks()
        invalidateApiCache('/api')
        invalidateApiCache('/test')
    })

    it('clears entries by prefix', async () => {
        mockFetch({ ok: true })
        await fetchJsonWithCache('/api/stocks', 60_000)
        await fetchJsonWithCache('/api/market', 60_000)

        invalidateApiCache('/api/stocks')

        // /api/stocks should be gone; /api/market still cached
        expect(getCachedData('/api/stocks')).toBeUndefined()
        expect(getCachedData<unknown>('/api/market')).toEqual({ ok: true })
    })
})

describe('getCachedData', () => {
    afterEach(() => {
        vi.restoreAllMocks()
        invalidateApiCache('/api')
        invalidateApiCache('/test')
    })

    it('returns undefined for uncached endpoints', () => {
        expect(getCachedData('/api/nonexistent')).toBeUndefined()
    })

    it('returns cached value after fetch', async () => {
        mockFetch({ ticker: '2330.TW' })
        await fetchJsonWithCache('/test/ticker', 60_000)
        expect(getCachedData('/test/ticker')).toEqual({ ticker: '2330.TW' })
    })
})
