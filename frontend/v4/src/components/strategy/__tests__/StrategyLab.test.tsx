/**
 * StrategyLab — manage (rename/delete) + suggested-default tests
 * (docs/specs/strategy-lab.md AC5 / §2).
 *
 * Mocks the useStrategies hook so we test the UI wiring (rename calls PUT via
 * updateStrategy, delete calls DELETE, the "Balanced" preset is highlighted).
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import StrategyLab from '../StrategyLab'
import type { Strategy, StrategyParams } from '../../../hooks/useStrategies'

const updateStrategy = vi.fn(() => Promise.resolve())
const deleteStrategy = vi.fn(() => Promise.resolve())
const createStrategy = vi.fn(() => Promise.resolve())
const reload = vi.fn(() => Promise.resolve())

const PARAMS: StrategyParams = {
    target_gain: 0.15,
    stop_loss: 0.05,
    holding_days: 20,
    commission_rate: 0.001425,
    tax_rate: 0.003,
    slippage_rate: 0.001,
    days_ago: 30,
}

const STRATEGIES: Strategy[] = [
    { id: 1, name: 'Balanced', params: PARAMS, notes: null, created_at: '', updated_at: '' },
    { id: 2, name: 'Tight', params: PARAMS, notes: null, created_at: '', updated_at: '' },
]

vi.mock('../../../hooks/useStrategies', async (importActual) => {
    const actual = await importActual<typeof import('../../../hooks/useStrategies')>()
    return {
        ...actual,
        useStrategies: () => ({
            strategies: STRATEGIES,
            loading: false,
            error: null,
            reload,
            createStrategy,
            updateStrategy,
            deleteStrategy,
        }),
        compareStrategies: vi.fn(() => Promise.resolve({ context: null, results: [] })),
    }
})

describe('StrategyLab — manage (rename/delete)', () => {
    beforeEach(() => {
        updateStrategy.mockClear()
        deleteStrategy.mockClear()
    })

    it('highlights the suggested "Balanced" starting point', () => {
        render(<StrategyLab currentParams={PARAMS} />)
        expect(screen.getByText('建議起點')).toBeTruthy()
    })

    it('renames a strategy via the inline editor (wires PUT through updateStrategy)', () => {
        render(<StrategyLab currentParams={PARAMS} />)
        fireEvent.click(screen.getByLabelText('重新命名 Tight'))
        const input = screen.getByLabelText('Tight 新名稱')
        fireEvent.change(input, { target: { value: 'My Tight' } })
        fireEvent.click(screen.getByLabelText('確認改名'))
        expect(updateStrategy).toHaveBeenCalledWith(2, { name: 'My Tight' })
    })

    it('deletes a strategy', () => {
        render(<StrategyLab currentParams={PARAMS} />)
        fireEvent.click(screen.getByLabelText('刪除 Tight'))
        expect(deleteStrategy).toHaveBeenCalledWith(2)
    })
})
