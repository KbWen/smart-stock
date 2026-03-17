/**
 * useStockAnalysis — unit tests for recommendation badge and stale detection.
 *
 * Spec: docs/specs/frontend-testing.md — AC#4 (Data Mocking), AC#6 (coverage)
 *
 * Mock strategy: vi.mock the useCachedApi module so tests run in jsdom without
 * a network or React component tree.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useStockAnalysis } from '../useStockAnalysis'

// ─── Mock useCachedApi ───────────────────────────────────────────────────────

const mockUseCachedApi = vi.fn()

vi.mock('../useCachedApi', () => ({
    useCachedApi: (...args: unknown[]) => mockUseCachedApi(...args),
}))

vi.mock('../../lib/apiClient', () => ({
    invalidateApiCache: vi.fn(),
}))

// ─── Helpers ─────────────────────────────────────────────────────────────────

const TODAY = new Date().toISOString().split('T')[0]
const YESTERDAY = new Date(Date.now() - 86_400_000).toISOString().split('T')[0]

const makeStockDetail = (overrides = {}) => ({
    ticker: '2330.TW',
    name: 'TSMC',
    price: 1000,
    rise_score_breakdown: { total: 85, trend: 0.9, momentum: 0.7, volatility: 0.5 },
    ai_probability: 75,
    analyst_summary: 'Bullish',
    updated_at: `${TODAY} 12:00:00`,
    signals: { squeeze: false, golden_cross: true, volume_spike: false },
    ...overrides,
})

const setupMock = (detailOverrides = {}, hookOverrides = {}) => {
    mockUseCachedApi.mockReturnValue({
        data: makeStockDetail(detailOverrides),
        loading: false,
        error: null,
        refetch: vi.fn(),
        ...hookOverrides,
    })
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('useStockAnalysis — recommendationBadge', () => {
    beforeEach(() => mockUseCachedApi.mockReset())

    it('returns STRONG BUY when ai_probability >= 70', () => {
        setupMock({ ai_probability: 75 })
        const { result } = renderHook(() => useStockAnalysis('2330.TW'))
        expect(result.current.recommendationBadge.text).toBe('STRONG BUY')
        expect(result.current.recommendationBadge.color).toContain('sniper-green')
    })

    it('returns HOLD when ai_probability is 50–69', () => {
        setupMock({ ai_probability: 60 })
        const { result } = renderHook(() => useStockAnalysis('2330.TW'))
        expect(result.current.recommendationBadge.text).toBe('HOLD')
        expect(result.current.recommendationBadge.color).toContain('yellow')
    })

    it('returns HIGH RISK when ai_probability < 50', () => {
        setupMock({ ai_probability: 30 })
        const { result } = renderHook(() => useStockAnalysis('2330.TW'))
        expect(result.current.recommendationBadge.text).toBe('HIGH RISK')
        expect(result.current.recommendationBadge.color).toContain('red')
    })
})

describe('useStockAnalysis — isDbStale', () => {
    beforeEach(() => mockUseCachedApi.mockReset())

    it('returns false when updated_at is today', () => {
        setupMock({ updated_at: `${TODAY} 09:30:00` })
        const { result } = renderHook(() => useStockAnalysis('2330.TW'))
        expect(result.current.isDbStale).toBe(false)
    })

    it('returns true when updated_at is yesterday', () => {
        setupMock({ updated_at: `${YESTERDAY} 09:30:00` })
        const { result } = renderHook(() => useStockAnalysis('2330.TW'))
        expect(result.current.isDbStale).toBe(true)
    })

    it('returns false when updated_at is missing', () => {
        setupMock({ updated_at: undefined })
        const { result } = renderHook(() => useStockAnalysis('2330.TW'))
        expect(result.current.isDbStale).toBe(false)
    })
})

describe('useStockAnalysis — disabled when ticker is null', () => {
    beforeEach(() => {
        mockUseCachedApi.mockReturnValue({
            data: makeStockDetail(),
            loading: false,
            error: null,
            refetch: vi.fn(),
        })
    })

    it('passes enabled=false to useCachedApi when ticker is null', () => {
        renderHook(() => useStockAnalysis(null))
        expect(mockUseCachedApi).toHaveBeenCalledWith(
            '',
            expect.objectContaining({ enabled: false }),
        )
    })
})
