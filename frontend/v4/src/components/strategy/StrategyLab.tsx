import React, { useMemo, useState } from 'react'
import { Star, Trash2 } from 'lucide-react'
import { SUGGESTED_DEFAULT_NAME, compareStrategies, useStrategies } from '../../hooks/useStrategies'
import type { CompareResponse, StrategyParams } from '../../hooks/useStrategies'
import StrategyCompare from './StrategyCompare'

const MAX_COMPARE = 4

interface StrategyLabProps {
    /** The current backtest slider values, savable as a named strategy. */
    currentParams: StrategyParams
}

function summarize(params: StrategyParams): string {
    return `+${(params.target_gain * 100).toFixed(0)}% / -${(params.stop_loss * 100).toFixed(0)}% · ${params.holding_days}天 · 回溯${params.days_ago}日`
}

const StrategyLab: React.FC<StrategyLabProps> = ({ currentParams }) => {
    const { strategies, loading, error, createStrategy, deleteStrategy } = useStrategies()

    const [name, setName] = useState<string>('')
    const [saving, setSaving] = useState<boolean>(false)
    const [saveError, setSaveError] = useState<string | null>(null)
    const [selected, setSelected] = useState<number[]>([])
    const [comparing, setComparing] = useState<boolean>(false)
    const [compareData, setCompareData] = useState<CompareResponse | null>(null)
    const [compareError, setCompareError] = useState<string | null>(null)

    const nameHint = useMemo(() => {
        const lowered = name.toLowerCase()
        // Non-blocking honesty nudge — user's own local data, but keep the spirit of AC6.
        const flagged = ['必勝', '穩賺', '飆股', '保證', 'guaranteed', 'sure win']
        return flagged.some((w) => name.includes(w) || lowered.includes(w))
            ? '提醒：策略名稱避免「必勝／保證」等字眼——這是歷史回測，不是獲利保證。'
            : null
    }, [name])

    const toggleSelect = (id: number): void => {
        setSelected((prev) => {
            if (prev.includes(id)) return prev.filter((x) => x !== id)
            if (prev.length >= MAX_COMPARE) return prev
            return [...prev, id]
        })
    }

    const handleSave = async (): Promise<void> => {
        const trimmed = name.trim()
        if (!trimmed) {
            setSaveError('請輸入策略名稱')
            return
        }
        setSaving(true)
        setSaveError(null)
        try {
            await createStrategy(trimmed, currentParams)
            setName('')
        } catch (e) {
            setSaveError(e instanceof Error ? e.message : '儲存失敗')
        } finally {
            setSaving(false)
        }
    }

    const handleCompare = async (): Promise<void> => {
        if (selected.length < 2) return
        setComparing(true)
        setCompareError(null)
        setCompareData(null)
        try {
            const data = await compareStrategies(selected)
            setCompareData(data)
        } catch (e) {
            setCompareError(e instanceof Error ? e.message : '比較失敗，請稍後再試')
        } finally {
            setComparing(false)
        }
    }

    return (
        <div className="rounded-xl border border-dark-border bg-dark-card/50 backdrop-blur-md p-4 space-y-4">
            <div className="flex flex-col gap-1">
                <h3 className="font-semibold text-white text-sm">🧪 策略實驗室（Strategy Lab）</h3>
                <p className="text-xs text-dark-muted">
                    把目前參數存成具名策略，並排比較它們扣成本後的歷史表現。純本地儲存，不上傳。
                </p>
            </div>

            {/* Save current params */}
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="為目前參數命名（例如：我的保守策略）"
                    className="flex-1 rounded-lg border border-dark-border bg-dark-bg/60 p-2 text-sm text-white outline-none focus:border-sniper-green"
                />
                <button
                    type="button"
                    onClick={() => void handleSave()}
                    disabled={saving}
                    className="rounded-lg bg-sniper-green px-4 py-2 text-sm font-semibold text-black transition-colors disabled:opacity-50"
                >
                    {saving ? '儲存中…' : '儲存目前參數'}
                </button>
            </div>
            {nameHint && <p className="text-xs text-sniper-gold/90">{nameHint}</p>}
            {saveError && <p className="text-xs text-red-400">{saveError}</p>}

            {/* Strategy list */}
            {loading ? (
                <p className="text-xs text-dark-muted">載入策略中…</p>
            ) : error ? (
                <p className="text-xs text-red-400">{error}</p>
            ) : strategies.length === 0 ? (
                <p className="text-xs text-dark-muted">尚無策略。先儲存一組參數，或稍候載入預設策略。</p>
            ) : (
                <div className="space-y-2">
                    {strategies.map((s) => {
                        const isSuggested = s.name === SUGGESTED_DEFAULT_NAME
                        const isSelected = selected.includes(s.id)
                        const selectDisabled = !isSelected && selected.length >= MAX_COMPARE
                        return (
                            <div
                                key={s.id}
                                className={`flex items-center gap-3 rounded-lg border p-3 transition-colors ${
                                    isSuggested
                                        ? 'border-sniper-gold/50 bg-sniper-gold/5'
                                        : 'border-dark-border bg-dark-bg/40'
                                }`}
                            >
                                <input
                                    type="checkbox"
                                    checked={isSelected}
                                    disabled={selectDisabled}
                                    onChange={() => toggleSelect(s.id)}
                                    aria-label={`選取 ${s.name} 進行比較`}
                                    className="h-4 w-4 accent-sniper-green disabled:opacity-40"
                                />
                                <div className="min-w-0 flex-1">
                                    <div className="flex items-center gap-2">
                                        <span className="truncate text-sm font-semibold text-white">{s.name}</span>
                                        {isSuggested && (
                                            <span className="inline-flex items-center gap-1 rounded-full bg-sniper-gold/20 px-2 py-0.5 text-[10px] font-semibold text-sniper-gold">
                                                <Star size={10} /> 建議起點
                                            </span>
                                        )}
                                    </div>
                                    <div className="mt-0.5 truncate text-[11px] text-dark-muted">{summarize(s.params)}</div>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => void deleteStrategy(s.id)}
                                    aria-label={`刪除 ${s.name}`}
                                    className="text-dark-muted transition-colors hover:text-red-400"
                                >
                                    <Trash2 size={15} />
                                </button>
                            </div>
                        )
                    })}
                </div>
            )}

            {/* Compare action */}
            <div className="flex items-center gap-3">
                <button
                    type="button"
                    onClick={() => void handleCompare()}
                    disabled={selected.length < 2 || comparing}
                    className="rounded-lg border border-sniper-green/60 px-4 py-2 text-sm font-semibold text-sniper-green transition-colors hover:bg-sniper-green/10 disabled:opacity-40"
                >
                    {comparing ? '比較執行中…' : `比較所選（${selected.length}/${MAX_COMPARE}）`}
                </button>
                {selected.length < 2 && (
                    <span className="text-[11px] text-dark-muted">勾選 2–4 個策略以並排比較</span>
                )}
            </div>
            {compareError && <p className="text-xs text-red-400">{compareError}</p>}

            {compareData && (
                <StrategyCompare
                    results={compareData.results}
                    context={compareData.context}
                    onClose={() => setCompareData(null)}
                />
            )}
        </div>
    )
}

export default StrategyLab
