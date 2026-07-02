/**
 * StrategyCompare — honesty UX tests (docs/specs/strategy-lab.md AC6).
 *
 * Ensures the side-by-side comparison: (1) shows the "past ≠ future / noise"
 * disclaimer, (2) surfaces data-sufficiency context (sample size + date range),
 * (3) renders inline plain-language metric interpretations (not hover-only),
 * (4) shows an honest failure slot instead of a fabricated number, and
 * (5) never applies comparative green/red coloring across strategy columns.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import StrategyCompare from '../StrategyCompare'
import type { CompareResult, CompareContext } from '../../../hooks/useStrategies'

const CONTEXT: CompareContext = {
    sample_size: 92,
    date_range: { start: '2024-06-01', end: '2026-06-01' },
}

const RESULTS: CompareResult[] = [
    {
        id: 1,
        name: 'Balanced',
        summary: {
            avg_net_return: 0.08,
            net_win_rate: 0.61,
            sharpe_ratio: 1.2,
            net_profit_factor: 1.7,
            worst_drawdown: -12.3,
        },
    },
    { id: 2, name: 'Wide', error: 'backtest failed for this strategy' },
]

describe('StrategyCompare — honesty UX', () => {
    it('renders the past-performance disclaimer', () => {
        render(<StrategyCompare results={RESULTS} context={CONTEXT} onClose={vi.fn()} />)
        const disclaimer = screen.getByTestId('compare-disclaimer')
        expect(disclaimer.textContent).toMatch(/過去回測表現不代表未來/)
        expect(disclaimer.textContent).toMatch(/雜訊/)
    })

    it('surfaces data-sufficiency context (sample size + date range)', () => {
        render(<StrategyCompare results={RESULTS} context={CONTEXT} onClose={vi.fn()} />)
        expect(screen.getByText('92')).toBeTruthy()
        expect(screen.getByText(/2024-06-01 ~ 2026-06-01/)).toBeTruthy()
    })

    it('honestly notes when context is unavailable instead of fabricating it', () => {
        render(<StrategyCompare results={RESULTS} context={null} onClose={vi.fn()} />)
        expect(screen.getByText(/無足夠歷史資料/)).toBeTruthy()
    })

    it('shows inline plain-language interpretation for a metric', () => {
        render(<StrategyCompare results={RESULTS} context={CONTEXT} onClose={vi.fn()} />)
        expect(screen.getByText(/扣掉手續費與稅之後/)).toBeTruthy()
    })

    it('renders an honest failure slot for a failed strategy (no fabricated number)', () => {
        render(<StrategyCompare results={RESULTS} context={CONTEXT} onClose={vi.fn()} />)
        expect(screen.getAllByText('回測失敗').length).toBeGreaterThan(0)
    })

    it('does not apply comparative green/red coloring across strategy value cells', () => {
        const { container } = render(
            <StrategyCompare results={RESULTS} context={CONTEXT} onClose={vi.fn()} />,
        )
        // Metric value cells are neutral (font-mono text-white); a comparative
        // win/lose color would defeat AC6's no-winner honesty guard.
        const valueCells = container.querySelectorAll('td.font-mono')
        expect(valueCells.length).toBeGreaterThan(0)
        valueCells.forEach((cell) => {
            expect(cell.className).not.toMatch(/text-(red|green|sniper-green)/)
        })
    })
})
