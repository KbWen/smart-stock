import React from 'react'
import { AlertTriangle, X } from 'lucide-react'
import { isCompareError } from '../../hooks/useStrategies'
import type { CompareContext, CompareResult, CompareSummary } from '../../hooks/useStrategies'

interface MetricDef {
    key: keyof CompareSummary
    fallbackKey?: keyof CompareSummary
    label: string
    /** Plain-language interpretation shown inline (novices won't hover). */
    plain: string
    format: (value: number) => string
}

// Deliberately neutral: NO comparative green/red across columns (see spec AC6 —
// color-coding a "winner" would imply a buy signal on small, backtested data).
const COMPARE_METRICS: MetricDef[] = [
    {
        key: 'avg_net_return',
        fallbackKey: 'avg_return',
        label: '平均淨報酬',
        plain: '扣掉手續費與稅之後，這組規則過去平均每次的報酬（越高越好，但不代表未來）。',
        format: (v) => `${(v * 100).toFixed(2)}%`,
    },
    {
        key: 'net_win_rate',
        fallbackKey: 'win_rate',
        label: '淨勝率',
        plain: '扣掉成本後，賺錢的次數佔比。',
        format: (v) => `${(v * 100).toFixed(1)}%`,
    },
    {
        key: 'sharpe_ratio',
        label: '報酬穩定度（單期）',
        plain: '報酬相對於波動的穩定度，越高代表越穩——不是獲利保證。',
        format: (v) => v.toFixed(2),
    },
    {
        key: 'net_profit_factor',
        fallbackKey: 'profit_factor',
        label: '淨獲利因子',
        plain: '賺的總額 ÷ 賠的總額，大於 1 代表整體有賺。',
        format: (v) => v.toFixed(2),
    },
    {
        key: 'worst_drawdown',
        label: '最差單股回撤',
        plain: '這段期間最慘的一次下跌，越接近 0 越好。',
        format: (v) => `${v.toFixed(1)}%`,
    },
]

function readMetric(summary: CompareSummary | null, def: MetricDef): string {
    if (!summary) return '—'
    let value = summary[def.key]
    if ((value === null || value === undefined) && def.fallbackKey) {
        value = summary[def.fallbackKey]
    }
    if (value === null || value === undefined || Number.isNaN(value)) return '—'
    return def.format(value as number)
}

interface StrategyCompareProps {
    results: CompareResult[]
    context: CompareContext | null
    onClose: () => void
}

const StrategyCompare: React.FC<StrategyCompareProps> = ({ results, context, onClose }) => {
    // The compare table was the one user-facing surface with no temporal marker: the backtest
    // page warns that its numbers are hindsight, and this showed the same numbers silently.
    const anyInSample = results.some(
        (r) => !isCompareError(r) && r.model_temporal_scope === 'in_sample',
    )
    return (
        <div className="rounded-xl border border-dark-border bg-dark-card p-4 md:p-6 space-y-4 animate-fade-in">
            <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-white">策略並排比較</h3>
            </div>
            {anyInSample && (
                <div className="rounded-lg border border-slate-500/40 bg-slate-500/10 p-3 text-[11px] leading-relaxed text-slate-300">
                    <strong className="text-slate-100">以下數字是事後回顧。</strong>
                    評分用的 AI 模型，其訓練資料涵蓋了被回測的期間，所以這些是「對看過的資料的辨識力」，
                    不是對未來的預測力 —— 用它來比較策略參數的相對高下，不要當成任一策略的實際期望報酬。
                </div>
            )}
            <div className="flex items-center justify-between">
                <button
                    type="button"
                    onClick={onClose}
                    aria-label="關閉比較"
                    className="text-dark-muted hover:text-white transition-colors"
                >
                    <X size={18} />
                </button>
            </div>

            {/* Honesty: data sufficiency context — is there even enough data to compare? */}
            <div className="rounded-lg border border-dark-border/60 bg-dark-bg/40 p-3 text-xs text-dark-muted">
                {context ? (
                    <span>
                        此比較基於 <span className="text-white font-semibold">{context.sample_size}</span> 檔股票、
                        <span className="text-white font-semibold">
                            {' '}{context.date_range.start} ~ {context.date_range.end}
                        </span>{' '}
                        的歷史資料。
                    </span>
                ) : (
                    <span>目前無足夠歷史資料可標示樣本範圍（結果僅供參考）。</span>
                )}
            </div>

            {/* Honesty: past performance is not a promise; small diffs are noise. */}
            <div
                data-testid="compare-disclaimer"
                className="flex items-start gap-2 rounded-lg border border-sniper-gold/30 bg-sniper-gold/5 p-3 text-xs text-sniper-gold/90"
            >
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                <span>
                    過去回測表現不代表未來結果；小幅差異可能落在雜訊範圍內。這是規則的歷史模擬，不是選股建議。
                </span>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full min-w-[480px] border-collapse text-sm">
                    <thead>
                        <tr>
                            <th className="p-2 text-left text-xs font-semibold uppercase tracking-wider text-dark-muted">
                                指標
                            </th>
                            {results.map((r) => (
                                <th
                                    key={r.id}
                                    className="p-2 text-right text-xs font-semibold text-white"
                                >
                                    {r.name}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {COMPARE_METRICS.map((def) => (
                            <tr key={def.key} className="border-t border-dark-border/40">
                                <td className="p-2 align-top">
                                    <div className="text-white">{def.label}</div>
                                    {/* Inline plain-language interpretation (not hover-only). */}
                                    <div className="mt-0.5 text-[10px] leading-tight text-dark-muted">
                                        {def.plain}
                                    </div>
                                </td>
                                {results.map((r) => (
                                    <td
                                        key={r.id}
                                        // Neutral color only — never comparative green/red across columns.
                                        className="p-2 text-right align-top font-mono text-white"
                                    >
                                        {isCompareError(r) ? (
                                            <span className="text-dark-muted">回測失敗</span>
                                        ) : (
                                            readMetric(r.summary, def)
                                        )}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}

export default StrategyCompare
