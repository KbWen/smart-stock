/**
 * StockList — unit tests for bulk-meta merge logic and rendering.
 *
 * Spec: docs/specs/frontend-api-opt.md — AC#1 (single batch fetch),
 *       AC#2 (signal enrichment from bulk meta)
 * Spec: docs/specs/frontend-testing.md — AC#4 (Data Mocking standard)
 *
 * Mock strategy: vi.mock useCachedApi; return controlled fixtures per test.
 */
import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import StockList from '../StockList'

// ─── Mock useCachedApi ───────────────────────────────────────────────────────

const mockUseCachedApi = vi.fn()

vi.mock('../../hooks/useCachedApi', () => ({
    useCachedApi: (...args: unknown[]) => mockUseCachedApi(...args),
}))

// ─── Fixtures ────────────────────────────────────────────────────────────────

const RAW_CANDIDATES = [
    {
        ticker: '2330.TW',
        name: 'TSMC',
        price: 1000,
        change_percent: 1.2,
        rise_score: 85,
        ai_prob: 75,
        signals: [],
        v4_signals: { squeeze: false, golden_cross: false, volume_spike: false, rsi: 0, macd_diff: 0, rel_vol: 0 },
        trend: 0,
        momentum: 0,
        volatility: 0,
    },
    {
        ticker: '2317.TW',
        name: 'Hon Hai',
        price: 120,
        change_percent: 0.4,
        rise_score: 76,
        ai_prob: 68,
        signals: [],
        v4_signals: { squeeze: false, golden_cross: false, volume_spike: false, rsi: 0, macd_diff: 0, rel_vol: 0 },
        trend: 0,
        momentum: 0,
        volatility: 0,
    },
]

const BULK_META_RESPONSE = {
    data: {
        '2330.TW': {
            signals: { squeeze: true, golden_cross: false, volume_spike: false },
            trend_score: 0.9,
            momentum_score: 0.7,
            volatility_score: 0.4,
        },
        '2317.TW': {
            signals: { squeeze: false, golden_cross: true, volume_spike: false },
            trend_score: 0.5,
            momentum_score: 0.6,
            volatility_score: 0.5,
        },
    },
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Returns mock call results based on endpoint string */
const setupMock = ({
    candidates = RAW_CANDIDATES,
    meta = BULK_META_RESPONSE,
    loadingCandidates = false,
    loadingMeta = false,
}: {
    candidates?: typeof RAW_CANDIDATES
    meta?: typeof BULK_META_RESPONSE
    loadingCandidates?: boolean
    loadingMeta?: boolean
} = {}) => {
    mockUseCachedApi.mockImplementation((endpoint: string) => {
        if (endpoint.includes('/api/v4/sniper/candidates')) {
            return {
                data: candidates,
                loading: loadingCandidates,
                error: null,
                isPlaceholder: false,
                refetch: vi.fn(),
            }
        }
        // bulk meta
        return {
            data: meta,
            loading: loadingMeta,
            error: null,
            isPlaceholder: false,
            refetch: vi.fn(),
        }
    })
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('StockList — rendering', () => {
    beforeEach(() => mockUseCachedApi.mockReset())

    it('renders ticker and name from candidates', async () => {
        setupMock()
        render(<StockList onSelect={() => {}} selectedTicker={null} />)
        await waitFor(() => {
            expect(screen.getByText('2330.TW')).toBeInTheDocument()
            expect(screen.getByText('TSMC')).toBeInTheDocument()
        })
    })

    it('shows loading state when candidates are loading', () => {
        setupMock({ loadingCandidates: true })
        // Override isPlaceholder to true
        mockUseCachedApi.mockImplementation((endpoint: string) => {
            if (endpoint.includes('/api/v4/sniper/candidates')) {
                return { data: [], loading: true, error: null, isPlaceholder: true, refetch: vi.fn() }
            }
            return { data: { data: {} }, loading: false, error: null, isPlaceholder: false, refetch: vi.fn() }
        })
        render(<StockList onSelect={() => {}} selectedTicker={null} />)
        expect(screen.getByText(/Scanning AI Models/i)).toBeInTheDocument()
    })

    it('shows empty state when no candidates', () => {
        mockUseCachedApi.mockImplementation(() => ({
            data: endpoint?.includes?.('/api/v4/sniper') ? [] : { data: {} },
            loading: false,
            error: null,
            isPlaceholder: false,
            refetch: vi.fn(),
        }))
        // Both return empty for simplicity
        mockUseCachedApi.mockReturnValue({
            data: [],
            loading: false,
            error: null,
            isPlaceholder: false,
            refetch: vi.fn(),
        })
        render(<StockList onSelect={() => {}} selectedTicker={null} />)
        expect(screen.getByText(/No candidates found/i)).toBeInTheDocument()
    })
})

describe('StockList — bulk meta signal enrichment (AC#2)', () => {
    beforeEach(() => mockUseCachedApi.mockReset())

    it('enriches 2330.TW with Squeeze signal from bulk meta', async () => {
        setupMock()
        render(<StockList onSelect={() => {}} selectedTicker={null} />)
        await waitFor(() => {
            // TSMC should show Squeeze tag (from meta signals.squeeze = true)
            expect(screen.getByText('Squeeze')).toBeInTheDocument()
        })
    })

    it('makes exactly one meta API call per candidate batch (AC#1)', () => {
        setupMock()
        render(<StockList onSelect={() => {}} selectedTicker={null} />)
        // Count calls to /api/v4/meta
        const metaCalls = mockUseCachedApi.mock.calls.filter(
            (args) => typeof args[0] === 'string' && args[0].includes('/api/v4/meta'),
        )
        expect(metaCalls.length).toBe(1)
    })
})
