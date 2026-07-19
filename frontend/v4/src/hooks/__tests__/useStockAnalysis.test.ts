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

// Use local date (not UTC ISO) to match the hook's toDateString() comparison.
// toLocaleDateString('en-CA') returns YYYY-MM-DD in local timezone — no manual padding needed.
const _now = new Date()
const TODAY = _now.toLocaleDateString('en-CA')
const _yest = new Date(_now.getFullYear(), _now.getMonth(), _now.getDate() - 1)
const YESTERDAY = _yest.toLocaleDateString('en-CA')

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

    it('returns AI 機率偏高 when ai_probability >= 70', () => {
        setupMock({ ai_probability: 75 })
        const { result } = renderHook(() => useStockAnalysis('2330.TW'))
        expect(result.current.recommendationBadge!.text).toBe('AI 機率偏高')
        expect(result.current.recommendationBadge!.color).toContain('sniper-green')
    })

    it('returns AI 機率中等 when ai_probability is 50–69', () => {
        setupMock({ ai_probability: 60 })
        const { result } = renderHook(() => useStockAnalysis('2330.TW'))
        expect(result.current.recommendationBadge!.text).toBe('AI 機率中等')
        expect(result.current.recommendationBadge!.color).toContain('yellow')
    })

    it('returns AI 機率偏低 when ai_probability < 50', () => {
        setupMock({ ai_probability: 30 })
        const { result } = renderHook(() => useStockAnalysis('2330.TW'))
        expect(result.current.recommendationBadge!.text).toBe('AI 機率偏低')
        expect(result.current.recommendationBadge!.color).toContain('red')
    })

    it('returns 資料不足 (not AI 機率偏低) when ai_probability is unavailable (null)', () => {
        setupMock({ ai_probability: null })
        const { result } = renderHook(() => useStockAnalysis('2330.TW'))
        expect(result.current.recommendationBadge!.text).toBe('資料不足')
    })

    it('shows the grade WITH a caption when model_health is degraded (never hide a true number)', () => {
        setupMock({ ai_probability: 75, model_health: { status: 'degraded' } })
        const { result } = renderHook(() => useStockAnalysis('2330.TW'))
        expect(result.current.recommendationBadge!.text).toBe('AI 機率偏高')
        expect(result.current.recommendationBadge!.caption).toBeTruthy()
    })

    it('suppresses the grade (資料不足) when model_health is unavailable, even with a probability', () => {
        setupMock({ ai_probability: 75, model_health: { status: 'unavailable' } })
        const { result } = renderHook(() => useStockAnalysis('2330.TW'))
        expect(result.current.recommendationBadge!.text).toBe('資料不足')
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
