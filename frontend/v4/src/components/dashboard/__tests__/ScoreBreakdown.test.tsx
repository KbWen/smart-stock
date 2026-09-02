/**
 * ScoreBreakdown — explainable screening tests (docs/specs/explainable-screening.md).
 * The AI number must be qualified by model_health; fired signals get plain-language
 * chips; nothing is fabricated.
 */
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ScoreBreakdown from '../ScoreBreakdown'

const SCORES = { total: 72.5, trend: 30, momentum: 20, volatility: 15 }

describe('ScoreBreakdown — explainable screening', () => {
    it('qualifies the AI number when the model is degraded', () => {
        render(
            <ScoreBreakdown
                scores={SCORES}
                aiProbability={41}
                modelHealth={{ status: 'degraded', message: 'AI 模型辨識力不足（買/強買為 0）。' }}
            />,
        )
        expect(screen.getByText(/辨識力不足/)).toBeTruthy()
    })

    it('shows the demo-mode qualifier when the model is unavailable (no message)', () => {
        render(<ScoreBreakdown scores={SCORES} aiProbability={null} modelHealth={{ status: 'unavailable' }} />)
        expect(screen.getByText(/示範模式/)).toBeTruthy()
    })

    it('shows NO qualifier when the model is healthy', () => {
        render(<ScoreBreakdown scores={SCORES} aiProbability={62} modelHealth={{ status: 'ok' }} />)
        expect(screen.queryByText(/辨識力不足/)).toBeNull()
        expect(screen.queryByText(/示範模式/)).toBeNull()
    })

    it('renders plain-language chips for fired signals only', () => {
        render(
            <ScoreBreakdown
                scores={SCORES}
                aiProbability={50}
                signals={{ squeeze: false, golden_cross: true, volume_spike: true }}
            />,
        )
        expect(screen.getByText('KD 黃金交叉')).toBeTruthy()
        expect(screen.getByText('爆量')).toBeTruthy()
        expect(screen.queryByText('低波壓縮')).toBeNull() // not fired
        expect(screen.getByText(/非經驗證的個別勝率/)).toBeTruthy()
    })

    it('renders N/A honestly when AI probability is null', () => {
        render(<ScoreBreakdown scores={SCORES} aiProbability={null} />)
        expect(screen.getByText('N/A')).toBeTruthy()
    })

    /*
     * docs/specs/unknown-is-not-zero-ml-features.md AC7. The N/A tooltip used to assert one
     * cause ("no model trained yet") for every missing number — the same mistake the model-health
     * chip made before it was keyed on a machine reason. A stock whose history is too short would
     * have been told to run train_ai.py, which would not have helped.
     */
    it('explains a short-history refusal instead of blaming the model', () => {
        render(
            <ScoreBreakdown scores={SCORES} aiProbability={null} aiUnavailableReason="insufficient_history" />,
        )
        fireEvent.mouseEnter(screen.getByText('N/A').parentElement!)
        expect(screen.getByText(/歷史資料不足/)).toBeTruthy()
        expect(screen.queryByText(/尚未訓練 AI 模型/)).toBeNull()
    })

    it('falls back to the untrained-model wording when no reason is given', () => {
        render(<ScoreBreakdown scores={SCORES} aiProbability={null} />)
        fireEvent.mouseEnter(screen.getByText('N/A').parentElement!)
        expect(screen.getByText(/尚未訓練 AI 模型/)).toBeTruthy()
        expect(screen.queryByText(/歷史資料不足/)).toBeNull()
    })
})
