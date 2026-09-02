/**
 * Transparency Panel — honesty + progressive-disclosure tests
 * (docs/specs/transparency-panel.md AC3/AC4).
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import Transparency from '../Transparency'

const mockUseCachedApi = vi.hoisted(() => vi.fn())
vi.mock('../../hooks/useCachedApi', () => ({ useCachedApi: mockUseCachedApi }))

const BASE_DATA = {
    universe_size: 1800,
    tickers_with_history: 92,
    date_range: { start: '2021-11-26', end: '2026-06-12' },
    coverage: { with_predict_rows: 92, with_train_rows: 80, short_count: 1708, min_predict_rows: 60, min_train_rows: 250 },
}

function ret(data: unknown) {
    mockUseCachedApi.mockReturnValue({ data, loading: false, error: null, isPlaceholder: false, refetch: vi.fn() })
}

describe('Transparency Panel', () => {
    beforeEach(() => mockUseCachedApi.mockReset())

    it('shows the data-coverage headline', () => {
        ret({ data: BASE_DATA, model: { status: 'unavailable', version: 'unknown', message: 'AI 模型尚未訓練' } })
        render(<Transparency />)
        expect(screen.getByText('92')).toBeTruthy()
        expect(screen.getByText(/2021-11-26 ~ 2026-06-12/)).toBeTruthy()
    })

    it('shows the demo-mode chip + honest message when the model is unavailable', () => {
        ret({ data: BASE_DATA, model: { status: 'unavailable', version: 'unknown', message: 'AI 模型尚未訓練，AI 機率暫時不可用。' } })
        render(<Transparency />)
        expect(screen.getByText(/示範模式 · AI 未訓練/)).toBeTruthy()
        expect(screen.getByText(/AI 機率暫時不可用/)).toBeTruthy()
    })

    it('hides expert numbers until expanded, and shows honest N/A when no model metrics', () => {
        ret({ data: BASE_DATA, model: { status: 'unavailable', version: 'unknown', message: 'x', oos_metrics: null } })
        render(<Transparency />)
        // Collapsed: OOS disclaimer not shown yet.
        expect(screen.queryByText(/樣本外/)).toBeNull()
        fireEvent.click(screen.getByText(/詳細數據/))
        expect(screen.getByText(/尚無已訓練模型/)).toBeTruthy()
    })

    it('renders OOS metrics + the not-a-guarantee disclaimer for a trained model', () => {
        ret({
            data: BASE_DATA,
            model: {
                status: 'ok', reason: 'ok', version: 'v4.x', message: '',
                trained_at: '2026-06-01T20:31:00', samples: 5000, test_samples: 1000,
                // Deliberately DIFFERENT distributions: a test that supplies only one cannot
                // show which split the panel is labelling.
                train_class_distribution: { hold: 0.6, buy: 0.14, strong: 0.26 },
                test_class_distribution: { hold: 0.5, buy: 0.2, strong: 0.3 },
                oos_metrics_scope: 'split_model',
                embargo: { days: 21, cut_date: '2026-06-01' },
                oos_metrics: { accuracy: 0.35, precision_strong: 0.36, recall_strong: 0.52, f1_strong: 0.42, precision_buy: 0.12, recall_buy: 0.3, lift_strong: 1.2, lift_buy: 0.6 },
            },
        })
        render(<Transparency />)
        expect(screen.getByText(/AI 已訓練/)).toBeTruthy()
        fireEvent.click(screen.getByText(/詳細數據/))
        expect(screen.getByText(/不是對未來的保證/)).toBeTruthy()
        expect(screen.getByText('36.0%')).toBeTruthy() // precision_strong
        // Both distributions render, each named for the split it belongs to. The whole F9 defect
        // was that the TRAIN distribution sat unlabelled under an OOS heading.
        expect(screen.getAllByText(/訓練集/).length).toBeGreaterThan(0)
        expect(screen.getAllByText(/測試集/).length).toBeGreaterThan(0)
        expect(screen.getByText(/強買 26\.0%/)).toBeTruthy() // train strong
        expect(screen.getByText(/強買 30\.0%/)).toBeTruthy() // test strong — the real denominator
        // Lift is the number that makes precision readable, and a buy lift below 1.0 must be
        // called out rather than shown as a neutral figure.
        expect(screen.getByText('1.20×')).toBeTruthy()
        expect(screen.getByText('0.60×')).toBeTruthy()
        expect(screen.getAllByText(/未優於基準比例/).length).toBeGreaterThan(0)
        // Attribution is stated, not implied.
        expect(screen.getByText(/80\/20 切分/)).toBeTruthy()
    })

    it('names the actual degraded cause instead of asserting one for all of them', () => {
        // An upgrading user: good-looking metrics, but no embargo block, so they were never
        // out-of-sample. The chip used to read 「AI 辨識力不足」 above a precision of 55%.
        ret({
            data: BASE_DATA,
            model: {
                status: 'degraded', reason: 'contaminated_metrics', version: 'v4.old',
                message: '此模型的評估指標是在舊的切分方式下產生的（訓練集與測試集實際上沒有隔離）。',
                trained_at: '2026-06-01T20:31:00', samples: 5000, test_samples: 1000,
                train_class_distribution: { hold: 0.6, buy: 0.14, strong: 0.26 },
                oos_metrics: { accuracy: 0.72, precision_strong: 0.55, recall_strong: 0.4, f1_strong: 0.46, precision_buy: 0.5, recall_buy: 0.45 },
            },
        })
        render(<Transparency />)
        expect(screen.getByText(/指標不可信/)).toBeTruthy()
        expect(screen.queryByText('AI 辨識力不足')).toBeNull()
        fireEvent.click(screen.getByText(/詳細數據/))
        // The contamination banner, and no lift claim for a model that predates the measurement.
        expect(screen.getByText(/並非真正的樣本外結果/)).toBeTruthy()
        expect(screen.getAllByText(/開始記錄基準比例之前/).length).toBeGreaterThan(0)
    })

    it('shows an honest error state on fetch failure (no fabricated numbers)', () => {
        mockUseCachedApi.mockReturnValue({ data: null, loading: false, error: new Error('net'), isPlaceholder: true, refetch: vi.fn() })
        render(<Transparency />)
        expect(screen.getByText(/無法載入透明度資料/)).toBeTruthy()
    })
})
