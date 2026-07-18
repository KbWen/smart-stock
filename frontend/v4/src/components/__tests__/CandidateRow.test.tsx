import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import CandidateRow from '../dashboard/CandidateRow'
import type { StockCandidate } from '../../hooks/useDashboardData'

const createStock = (overrides: Partial<StockCandidate> = {}): StockCandidate => ({
    ticker: '2330.TW',
    name: 'TSMC',
    price: 1000,
    change_percent: 1.5,
    rise_score: 85,
    ai_prob: 75,
    signals: [],
    v4_signals: {
        squeeze: false,
        golden_cross: false,
        volume_spike: false,
        rsi: 0,
        macd_diff: 0,
        rel_vol: 0,
    },
    ...overrides,
})

describe('CandidateRow', () => {
    it('renders enriched squeeze signal from v4 meta', () => {
        render(
            <CandidateRow
                stock={createStock({
                    v4_signals: {
                        squeeze: true,
                        golden_cross: false,
                        volume_spike: false,
                        rsi: 51,
                        macd_diff: 1.2,
                        rel_vol: 1.1,
                    },
                })}
                isSelected={false}
                onSelect={() => {}}
                rowHeight={50}
            />,
        )

        expect(screen.getByText('2330.TW')).toBeInTheDocument()
        expect(screen.getByText('TSMC')).toBeInTheDocument()
        expect(screen.getByText('低波壓縮')).toBeInTheDocument()
    })

    it('renders enriched golden cross signal from v4 meta', () => {
        render(
            <CandidateRow
                stock={createStock({
                    v4_signals: {
                        squeeze: false,
                        golden_cross: true,
                        volume_spike: false,
                        rsi: 49,
                        macd_diff: 0.8,
                        rel_vol: 1.0,
                    },
                })}
                isSelected={false}
                onSelect={() => {}}
                rowHeight={50}
            />,
        )

        expect(screen.getByText('KD 黃金交叉')).toBeInTheDocument()
    })

    it('deduplicates legacy and enriched signals while keeping hidden count', () => {
        render(
            <CandidateRow
                stock={createStock({
                    signals: ['低波壓縮'],
                    v4_signals: {
                        squeeze: true,
                        golden_cross: true,
                        volume_spike: false,
                        rsi: 55,
                        macd_diff: 1.7,
                        rel_vol: 1.3,
                    },
                })}
                isSelected={false}
                onSelect={() => {}}
                rowHeight={50}
            />,
        )

        expect(screen.getByText('低波壓縮')).toBeInTheDocument()
        expect(screen.getByText('+1')).toBeInTheDocument()
    })

    it('renders N/A for an unavailable (null) AI probability instead of 0.0%', () => {
        render(
            <CandidateRow
                stock={createStock({ ai_prob: null })}
                isSelected={false}
                onSelect={() => {}}
                rowHeight={50}
            />,
        )

        expect(screen.getByText('N/A')).toBeInTheDocument()
        expect(screen.queryByText('0.0%')).not.toBeInTheDocument()
    })
})
