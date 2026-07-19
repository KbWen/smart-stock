import React, { useEffect, useRef, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import Tooltip from '../Tooltip'
import { SIGNAL_LABELS } from '../../lib/verdict'

export interface ScoreSignals {
    squeeze: boolean
    golden_cross: boolean
    volume_spike: boolean
}

export interface ScoreModelHealth {
    status: 'unavailable' | 'degraded' | 'ok'
    message?: string
    version?: string
}

interface ScoreBreakdownProps {
    scores: {
        total: number
        trend: number
        momentum: number
        volatility: number
    }
    aiProbability: number | null
    signals?: ScoreSignals | null
    modelHealth?: ScoreModelHealth | null
}

// Plain-language explanations — the point of epic #3 (novices won't hover).
// SSoT: src/lib/verdict.ts (shared with CandidateRow's signal chips).
const SIGNAL_META = SIGNAL_LABELS

const SUBSCORE_CAPTION: Record<'trend' | 'momentum' | 'volatility', string> = {
    trend: '均線多頭排列與斜率的強度',
    momentum: 'RSI／MACD 等動能指標的強度',
    volatility: '波動結構（壓縮或擴張）的評分',
}

function healthCaption(h: ScoreModelHealth): string {
    if (h.message) return h.message
    return h.status === 'unavailable' ? '示範模式 · AI 尚未訓練' : 'AI 模型辨識力不足，僅供參考'
}

function useCountUp(target: number, duration = 1000): number {
    const [display, setDisplay] = useState(0)
    const rafRef = useRef<number | null>(null)
    const startRef = useRef<number | null>(null)
    const fromRef = useRef(0)

    useEffect(() => {
        fromRef.current = display
        startRef.current = null
        if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
        const animate = (timestamp: number) => {
            if (startRef.current === null) startRef.current = timestamp
            const elapsed = timestamp - startRef.current
            const progress = Math.min(elapsed / duration, 1)
            const eased = 1 - Math.pow(1 - progress, 3)
            setDisplay(parseFloat((fromRef.current + (target - fromRef.current) * eased).toFixed(1)))
            if (progress < 1) rafRef.current = requestAnimationFrame(animate)
        }
        rafRef.current = requestAnimationFrame(animate)
        return () => {
            if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [target, duration])

    return display
}

const ScoreBreakdown: React.FC<ScoreBreakdownProps> = ({ scores, aiProbability, signals, modelHealth }) => {
    const displayProb = useCountUp(aiProbability ?? 0)
    const safeScores = scores || { total: 0, trend: 0, momentum: 0, volatility: 0 }
    const aiUnhealthy = !!modelHealth && modelHealth.status !== 'ok'

    const firedSignals = signals
        ? (Object.keys(SIGNAL_META) as (keyof ScoreSignals)[]).filter((k) => signals[k])
        : []

    const renderProgressBar = (
        key: 'trend' | 'momentum' | 'volatility',
        label: string,
        value: number,
        max: number,
        colorClass: string,
    ) => {
        const safeValue = value ?? 0
        const percentage = Math.min(100, Math.max(0, (safeValue / max) * 100))
        return (
            <div className="mb-1">
                <div className="mb-1 flex justify-between text-[11px] uppercase tracking-wider font-bold">
                    <span className="text-dark-muted">{label}</span>
                    <span className="text-white">
                        {safeValue.toFixed(1)} <span className="font-normal text-dark-muted">/ {max}</span>
                    </span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-dark-bg/50 border border-white/5">
                    <div className={`h-full rounded-full transition-all duration-500 ${colorClass}`} style={{ width: `${percentage}%` }} />
                </div>
                <div className="mt-1 text-[10px] leading-tight text-dark-muted">{SUBSCORE_CAPTION[key]}</div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4 rounded-lg border border-dark-border bg-dark-bg/50 p-4 shadow-inner">
                <div>
                    <div className="mb-1 text-[10px] uppercase tracking-wider font-bold text-dark-muted">技術總分</div>
                    <div className="text-3xl font-bold font-mono text-sniper-green">{(safeScores.total ?? 0).toFixed(1)}</div>
                </div>
                <div>
                    <div className="mb-1 text-[10px] uppercase tracking-wider font-bold text-dark-muted">AI 預測機率</div>
                    <div className="text-3xl font-bold font-mono text-sniper-gold">
                        {aiProbability == null ? (
                            <Tooltip content="尚未訓練 AI 模型，技術分數仍正常運作。執行 train_ai.py 即可啟用。">
                                <span className="cursor-help border-b border-dashed border-dark-muted/40">N/A</span>
                            </Tooltip>
                        ) : `${(displayProb ?? 0).toFixed(1)}%`}
                    </div>
                    {/* Honest qualifier: never show the AI number as reliable when the model isn't. */}
                    {aiUnhealthy && modelHealth && (
                        <div className="mt-1 flex items-start gap-1 text-[10px] leading-tight text-yellow-400/90">
                            <AlertTriangle size={11} className="mt-0.5 shrink-0" />
                            <span>{healthCaption(modelHealth)}</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Explainable signals — which technical factors fired, in plain language. */}
            {firedSignals.length > 0 && (
                <div className="rounded-lg border border-dark-border bg-dark-bg/40 p-3">
                    <div className="mb-2 text-[10px] uppercase tracking-wider font-bold text-dark-muted">觸發的技術訊號</div>
                    <div className="flex flex-wrap gap-2">
                        {firedSignals.map((k) => (
                            <Tooltip key={k} content={SIGNAL_META[k].plain}>
                                <span className="cursor-help rounded-full border border-sniper-green/30 bg-sniper-green/10 px-2.5 py-1 text-xs font-medium text-sniper-green">
                                    {SIGNAL_META[k].label}
                                </span>
                            </Tooltip>
                        ))}
                    </div>
                    <p className="mt-2 text-[10px] leading-tight text-dark-muted">
                        這些是構成分數的技術因子，<strong className="text-dark-text">非經驗證的個別勝率</strong>；僅供研究參考。
                    </p>
                </div>
            )}

            <div className="rounded-lg bg-dark-border/10 p-4 space-y-4">
                {renderProgressBar('trend', '趨勢', safeScores.trend, 40, 'bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]')}
                {renderProgressBar('momentum', '動能', safeScores.momentum, 30, 'bg-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.5)]')}
                {renderProgressBar('volatility', '波動', safeScores.volatility, 30, 'bg-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.5)]')}
            </div>
        </div>
    )
}

export default React.memo(ScoreBreakdown)
