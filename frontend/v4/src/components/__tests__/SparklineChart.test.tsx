/**
 * SparklineChart — unit tests.
 * Mock strategy: mock recharts (avoids ResizeObserver/canvas jsdom issues).
 */
import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import SparklineChart from '../charts/SparklineChart'
import type { SparklinePoint } from '../../hooks/useSparkline'

// ─── Mock recharts ────────────────────────────────────────────────────────────
vi.mock('recharts', () => {
    const MockResponsiveContainer = ({ children }: { children: React.ReactNode }) =>
        <div data-testid="sparkline-container">{children}</div>
    const MockLineChart = ({ children }: { children: React.ReactNode }) =>
        <div data-testid="sparkline-chart">{children}</div>
    const noop = () => null
    return {
        ResponsiveContainer: MockResponsiveContainer,
        LineChart: MockLineChart,
        Line: noop,
    }
})

import React from 'react'

const makeData = (n: number): SparklinePoint[] =>
    Array.from({ length: n }, (_, i) => ({ date: `2026-01-${String(i + 1).padStart(2, '0')}`, close: 100 + i }))

describe('SparklineChart', () => {
    it('renders placeholder when data is empty', () => {
        const { container } = render(<SparklineChart data={[]} />)
        expect(container.querySelector('[data-testid="sparkline-container"]')).toBeNull()
        expect(container.querySelector('div')).toBeTruthy()
    })

    it('renders placeholder for single-point data', () => {
        const { container } = render(<SparklineChart data={makeData(1)} />)
        expect(container.querySelector('[data-testid="sparkline-container"]')).toBeNull()
    })

    it('renders recharts container when data has 2+ points', () => {
        const { container } = render(<SparklineChart data={makeData(10)} changePercent={1.5} />)
        expect(container.querySelector('[data-testid="sparkline-container"]')).toBeTruthy()
        expect(container.querySelector('[data-testid="sparkline-chart"]')).toBeTruthy()
    })

    it('renders for negative change_percent', () => {
        const { container } = render(<SparklineChart data={makeData(10)} changePercent={-2.0} />)
        expect(container.querySelector('[data-testid="sparkline-container"]')).toBeTruthy()
    })

    it('renders with default positive color when changePercent is omitted', () => {
        const { container } = render(<SparklineChart data={makeData(5)} />)
        expect(container.querySelector('[data-testid="sparkline-container"]')).toBeTruthy()
    })
})
