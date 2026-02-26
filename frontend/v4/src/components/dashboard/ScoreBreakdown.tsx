import React from 'react'

interface ScoreBreakdownProps {
    scores: {
        total: number
        trend: number
        momentum: number
        volatility: number
    }
    aiProbability: number
}

const ScoreBreakdown: React.FC<ScoreBreakdownProps> = ({ scores, aiProbability }) => {
    const renderProgressBar = (label: string, value: number, max: number, colorClass: string) => {
        const percentage = Math.min(100, Math.max(0, (value / max) * 100))
        return (
            <div className="mb-1">
                <div className="mb-1 flex justify-between text-[11px] uppercase tracking-wider font-bold">
                    <span className="text-dark-muted">{label}</span>
                    <span className="text-white">
                        {value.toFixed(1)} <span className="font-normal text-dark-muted">/ {max}</span>
                    </span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-dark-bg/50 border border-white/5">
                    <div className={`h-full rounded-full transition-all duration-500 ${colorClass}`} style={{ width: `${percentage}%` }} />
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4 rounded-lg border border-dark-border bg-dark-bg/50 p-4 shadow-inner">
                <div>
                    <div className="mb-1 text-[10px] uppercase tracking-wider font-bold text-dark-muted">Total Rise Score</div>
                    <div className="text-3xl font-bold font-mono text-sniper-green">{scores.total.toFixed(1)}</div>
                </div>
                <div>
                    <div className="mb-1 text-[10px] uppercase tracking-wider font-bold text-dark-muted">AI Probability</div>
                    <div className="text-3xl font-bold font-mono text-sniper-gold">{aiProbability.toFixed(1)}%</div>
                </div>
            </div>

            <div className="rounded-lg bg-dark-border/10 p-4 space-y-4">
                {renderProgressBar('Trend', scores.trend, 40, 'bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]')}
                {renderProgressBar('Momentum', scores.momentum, 30, 'bg-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.5)]')}
                {renderProgressBar('Volatility', scores.volatility, 30, 'bg-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.5)]')}
            </div>
        </div>
    )
}

export default React.memo(ScoreBreakdown)
