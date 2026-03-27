/**
 * PriceSignalChart — unit tests for rendering, empty state, and loading state.
 * Spec: .agentcortex/specs/visual-upgrade-phase1.md — AC3, AC5
 *
 * Mock strategy: mock recharts (avoids ResizeObserver/canvas jsdom issues)
 *                + mock useCachedApi for controlled data.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import PriceSignalChart from '../charts/PriceSignalChart'

// ─── Mock recharts ────────────────────────────────────────────────────────────
vi.mock('recharts', () => {
    const MockResponsiveContainer = ({ children }: { children: React.ReactNode }) =>
        <div data-testid="responsive-container">{children}</div>
    const MockComposedChart = ({ children }: { children: React.ReactNode }) =>
        <div data-testid="composed-chart">{children}</div>
    const noop = () => null
    return {
        ResponsiveContainer: MockResponsiveContainer,
        ComposedChart: MockComposedChart,
        Line: noop,
        ReferenceDot: noop,
        XAxis: noop,
        YAxis: noop,
        CartesianGrid: noop,
        Tooltip: noop,
    }
})

// ─── Mock useCachedApi ───────────────────────────────────────────────────────
const mockUseCachedApi = vi.hoisted(() => vi.fn())
vi.mock('../../hooks/useCachedApi', () => ({
    useCachedApi: mockUseCachedApi,
}))

import React from 'react'

// ─── Fixtures ────────────────────────────────────────────────────────────────
const MOCK_HISTORY = [
    { date: '2026-01-01', close: 100.0, is_squeeze: false, golden_cross: false, volume_spike: false },
    { date: '2026-01-02', close: 101.0, is_squeeze: true,  golden_cross: false, volume_spike: false },
    { date: '2026-01-03', close: 102.0, is_squeeze: false, golden_cross: true,  volume_spike: false },
    { date: '2026-01-04', close: 103.0, is_squeeze: false, golden_cross: false, volume_spike: true  },
]

const DEFAULT_MOCK = {
    data: [] as typeof MOCK_HISTORY,
    loading: false,
    isPlaceholder: false,
    error: null,
}

describe('PriceSignalChart', () => {
    beforeEach(() => {
        mockUseCachedApi.mockReset()
        mockUseCachedApi.mockReturnValue(DEFAULT_MOCK)
    })

    it('renders chart with data', () => {
        mockUseCachedApi.mockReturnValue({ ...DEFAULT_MOCK, data: MOCK_HISTORY })

        render(<PriceSignalChart ticker="2330" />)
        expect(screen.getByText('Price History (90d)')).toBeDefined()
        expect(screen.getByText('⚡ Squeeze')).toBeDefined()
        expect(screen.getByText('✦ Golden Cross')).toBeDefined()
        expect(screen.getByText('▲ Vol Spike')).toBeDefined()
    })

    it('renders empty state when data is empty', () => {
        render(<PriceSignalChart ticker="2330" />)
        expect(screen.getByText('No history data')).toBeDefined()
    })

    it('renders skeleton when loading', () => {
        mockUseCachedApi.mockReturnValue({ ...DEFAULT_MOCK, loading: true, isPlaceholder: true })

        const { container } = render(<PriceSignalChart ticker="2330" />)
        const skeleton = container.querySelector('.animate-pulse')
        expect(skeleton).not.toBeNull()
    })

    it('renders nothing when ticker is null', () => {
        const { container } = render(<PriceSignalChart ticker={null} />)
        expect(container.firstChild).toBeNull()
    })
})
