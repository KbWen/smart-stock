import React, { memo } from 'react'
import { TrendingUp, TrendingDown, Target, ShieldAlert } from 'lucide-react'

export interface BacktestPick {
    ticker: string
    name: string
    entry_date: string
    entry_price: number
    current_price: number
    ai_prob_at_entry: number
    actual_return: number
    sniper_result: 'HIT' | 'STOP' | 'HOLD'
    max_gain: number
    max_drawdown: number
    holding_days?: number
    exit_date?: string
}

interface BacktestTableProps {
    picks: BacktestPick[]
}

const BacktestTable: React.FC<BacktestTableProps> = ({ picks }) => {
    if (!picks || picks.length === 0) return null

    return (
        <div className="rounded-xl border border-dark-border bg-dark-card overflow-hidden shadow-xl animate-slide-up">
            <div className="border-b border-dark-border bg-dark-card/50 px-4 py-3">
                <h3 className="text-sm font-bold uppercase tracking-widest text-white flex items-center gap-2">
                    <Target size={16} className="text-sniper-green" />
                    回測持股明細 (Backtest Details)
                </h3>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                    <thead>
                        <tr className="border-b border-dark-border text-[11px] font-bold uppercase tracking-wider text-dark-muted">
                            <th className="px-4 py-3">標的 (Stock)</th>
                            <th className="px-4 py-3 text-center">結果 (Result)</th>
                            <th className="px-4 py-3">進場日期/價</th>
                            <th className="px-4 py-3">出場日/現價</th>
                            <th className="px-4 py-3 text-right">區間回報</th>
                            <th className="px-4 py-3 text-right text-sniper-gold">AI 機率</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-dark-border/50">
                        {picks.map((pick, idx) => (
                            <tr key={`${pick.ticker}-${idx}`} className="hover:bg-white/5 transition-colors">
                                <td className="px-4 py-4">
                                    <div className="font-bold text-white">{pick.name}</div>
                                    <div className="text-[10px] text-dark-muted">{pick.ticker}</div>
                                </td>
                                <td className="px-4 py-4 text-center">
                                    {pick.sniper_result === 'HIT' ? (
                                        <span className="inline-flex items-center gap-1 rounded-full bg-red-500/10 px-2 py-0.5 text-[10px] font-bold text-red-500 ring-1 ring-inset ring-red-500/20 uppercase">
                                            <TrendingUp size={10} /> HIT
                                        </span>
                                    ) : pick.sniper_result === 'STOP' ? (
                                        <span className="inline-flex items-center gap-1 rounded-full bg-sniper-green/10 px-2 py-0.5 text-[10px] font-bold text-sniper-green ring-1 ring-inset ring-sniper-green/20 uppercase">
                                            <TrendingDown size={10} /> STOP
                                        </span>
                                    ) : (
                                        <span className="inline-flex items-center gap-1 rounded-full bg-dark-border px-2 py-0.5 text-[10px] font-bold text-dark-muted uppercase">
                                            HOLD
                                        </span>
                                    )}
                                </td>
                                <td className="px-4 py-4">
                                    <div className="text-white">{pick.entry_price.toFixed(2)}</div>
                                    <div className="text-[10px] text-dark-muted">{pick.entry_date}</div>
                                </td>
                                <td className="px-4 py-4">
                                    <div className="text-white">{pick.current_price.toFixed(2)}</div>
                                    <div className="text-[10px] text-dark-muted">{pick.exit_date || '—'}</div>
                                </td>
                                <td className={`px-4 py-4 text-right font-mono font-bold ${pick.actual_return >= 0 ? 'text-red-500' : 'text-sniper-green'}`}>
                                    {(pick.actual_return * 100).toFixed(2)}%
                                </td>
                                <td className="px-4 py-4 text-right font-mono text-sniper-gold">
                                    {(pick.ai_prob_at_entry * 100).toFixed(1)}%
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="bg-dark-border/10 p-3 flex items-center gap-2 text-[10px] text-dark-muted">
                <ShieldAlert size={12} className="opacity-50" />
                <span>註：回測結果為歷史模擬，不代表未來獲利保證。 sniper_result 代表是否觸發 +15% 目標 (HIT) 或 -5% 停損 (STOP)。</span>
            </div>
        </div>
    )
}

export default memo(BacktestTable)
