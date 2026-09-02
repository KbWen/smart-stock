/**
 * MarketRisk — honest data state tests.
 *
 * Spec: .agentcortex/specs/frontend-honest-data-states.md — AC#2, AC#3
 * Ensures the page never renders fabricated mock numbers; on fetch failure /
 * empty result it shows an honest error / empty state instead.
 *
 * Mock strategy: vi.hoisted + vi.mock useCachedApi.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import MarketRisk from '../../pages/MarketRisk'

const mockUseCachedApi = vi.hoisted(() => vi.fn())

vi.mock('../../hooks/useCachedApi', () => ({
    useCachedApi: mockUseCachedApi,
}))

const REAL_MARKET = {
    bull_ratio: 58.5,
    market_temp: 62.3,
    ai_sentiment: 71.2,
    breadth_level: 'NEUTRAL',
    total_stocks: 1200,
    model_version: 'v4.2',
    history: [],
}

describe('MarketRisk — honest data states', () => {
    beforeEach(() => mockUseCachedApi.mockReset())

    it('shows an honest error state on fetch failure (no fabricated numbers)', () => {
        mockUseCachedApi.mockReturnValue({
            data: null,
            loading: false,
            error: new Error('network'),
            isPlaceholder: true,
            refetch: vi.fn(),
        })
        render(<MarketRisk />)
        expect(screen.getByText('市場資料載入失敗')).toBeInTheDocument()
        // Must NOT render the old hardcoded mock value.
        expect(screen.queryByText('62.5')).not.toBeInTheDocument()
    })

    it('shows an honest empty state when there is no data', () => {
        mockUseCachedApi.mockReturnValue({
            data: null,
            loading: false,
            error: null,
            isPlaceholder: true,
            refetch: vi.fn(),
        })
        render(<MarketRisk />)
        expect(screen.getByText(/目前無市場資料/)).toBeInTheDocument()
    })

    it('renders real market data on success', () => {
        mockUseCachedApi.mockReturnValue({
            data: REAL_MARKET,
            loading: false,
            error: null,
            isPlaceholder: false,
            refetch: vi.fn(),
        })
        render(<MarketRisk />)
        expect(screen.getByText('58.5')).toBeInTheDocument()
    })
})
