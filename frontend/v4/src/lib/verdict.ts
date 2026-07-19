/**
 * verdict.ts — single source of truth for the non-directive, model-health-gated
 * grade shown on stock detail views, plus the canonical Traditional-Chinese
 * signal labels shared across dashboard components.
 *
 * Honesty invariant (adversarially reviewed):
 *   - status === 'unavailable' ⇒ suppress the directive grade (資料不足) —
 *     no model has ever run, so there is nothing to grade.
 *   - status === 'degraded'    ⇒ SHOW the grade + a qualifier caption —
 *     never hide a true number just because the model is weak.
 *   - status === 'ok' (or unset) ⇒ grade, no caption.
 *
 * Wording below is PROVISIONAL — copy will be tuned on review.
 */

export const SIGNAL_LABELS: Record<
    'squeeze' | 'golden_cross' | 'volume_spike',
    { label: string; plain: string }
> = {
    golden_cross: { label: 'KD 黃金交叉', plain: '短線 KD 指標向上交叉，偏多訊號。' },
    volume_spike: { label: '爆量', plain: '成交量明顯放大（>1.5×），資金開始關注。' },
    squeeze: { label: '低波壓縮', plain: '波動收斂，常醞釀較大行情（方向未定）。' },
}

export type ModelHealthStatus = 'unavailable' | 'degraded' | 'ok'

export interface Grade {
    text: string
    color: string
    caption?: string
}

export function deriveGrade(
    aiProbability: number | null,
    status?: ModelHealthStatus,
): Grade | null {
    if (aiProbability == null || status === 'unavailable') {
        return { text: '資料不足', color: 'bg-dark-border text-dark-muted border-dark-border' }
    }

    let grade: Grade
    if (aiProbability >= 70) {
        grade = { text: 'AI 機率偏高', color: 'bg-sniper-green/10 text-sniper-green border-sniper-green/20' }
    } else if (aiProbability >= 50) {
        grade = { text: 'AI 機率中等', color: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20' }
    } else {
        grade = { text: 'AI 機率偏低', color: 'bg-red-500/10 text-red-500 border-red-500/20' }
    }

    if (status === 'degraded') {
        grade = { ...grade, caption: '模型辨識力不足，僅供參考' }
    }

    return grade
}
