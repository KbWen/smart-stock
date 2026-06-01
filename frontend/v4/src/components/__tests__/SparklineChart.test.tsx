/**
 * SparklineChart — unit tests.
 * Verifies SVG-based rendering, color encoding, and robustness.
 */
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import SparklineChart from '../charts/SparklineChart'
import type { SparklinePoint } from '../../hooks/useSparkline'

const makeData = (n: number): SparklinePoint[] =>
    Array.from({ length: n }, (_, i) => ({ date: `2026-01-${String(i + 1).padStart(2, '0')}`, close: 100 + i }))

describe('SparklineChart', () => {
    it('renders placeholder when data is empty', () => {
        const { container } = render(<SparklineChart data={[]} />)
        expect(container.querySelector('svg')).toBeNull()
        expect(container.querySelector('div')).toBeTruthy()
    })

    it('renders placeholder for single-point data', () => {
        const { container } = render(<SparklineChart data={makeData(1)} />)
        expect(container.querySelector('svg')).toBeNull()
    })

    it('renders svg when data has 2+ points', () => {
        const { container } = render(<SparklineChart data={makeData(10)} changePercent={1.5} />)
        expect(container.querySelector('svg')).toBeTruthy()
        expect(container.querySelectorAll('path')).toHaveLength(2) // one for area fill, one for line stroke
    })

    it('renders with positive color (red) for positive change_percent', () => {
        const { container } = render(<SparklineChart data={makeData(10)} changePercent={2.0} />)
        const paths = container.querySelectorAll('path')
        const strokePath = Array.from(paths).find(p => p.getAttribute('stroke') === '#ef4444')
        expect(strokePath).toBeTruthy()
    })

    it('renders with negative color (green) for negative change_percent', () => {
        const { container } = render(<SparklineChart data={makeData(10)} changePercent={-2.0} />)
        const paths = container.querySelectorAll('path')
        const strokePath = Array.from(paths).find(p => p.getAttribute('stroke') === '#22c55e')
        expect(strokePath).toBeTruthy()
    })

    it('renders with default positive color (red) when changePercent is omitted', () => {
        const { container } = render(<SparklineChart data={makeData(5)} />)
        const paths = container.querySelectorAll('path')
        const strokePath = Array.from(paths).find(p => p.getAttribute('stroke') === '#ef4444')
        expect(strokePath).toBeTruthy()
    })
})
