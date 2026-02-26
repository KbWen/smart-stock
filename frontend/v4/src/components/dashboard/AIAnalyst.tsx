import React from 'react'

interface AIAnalystProps {
    summary: string
    signals: {
        squeeze: boolean
        golden_cross: boolean
        volume_spike: boolean
    }
}

const AIAnalyst: React.FC<AIAnalystProps> = ({ summary, signals }) => {
    return (
        <div className="space-y-4">
            <div className="border-t border-dark-border pt-4">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-white">
                    <span role="img" aria-label="robot">🤖</span> AI Analyst Insight
                </h3>
                <div className="rounded-lg border-l-2 border-sniper-gold bg-dark-bg/30 p-3 text-sm leading-relaxed text-dark-muted whitespace-pre-line shadow-inner">
                    {summary}
                </div>
            </div>

            <div className="flex flex-wrap gap-2 pt-2">
                {signals.squeeze && (
                    <span className="rounded border border-yellow-500/20 bg-yellow-500/10 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-yellow-500">
                        🔥 Squeeze
                    </span>
                )}
                {signals.golden_cross && (
                    <span className="rounded border border-blue-500/20 bg-blue-500/10 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-blue-500">
                        ✨ Golden Cross
                    </span>
                )}
                {signals.volume_spike && (
                    <span className="rounded border border-purple-500/20 bg-purple-500/10 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-purple-500">
                        📢 Volume Spike
                    </span>
                )}
            </div>
        </div>
    )
}

export default React.memo(AIAnalyst)
