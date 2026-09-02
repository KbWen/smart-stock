import React, { useState } from 'react'
import { AlertTriangle, ChevronDown, ChevronUp, Database, ShieldCheck } from 'lucide-react'
import { useCachedApi } from '../hooks/useCachedApi'

type ModelStatus = 'unavailable' | 'degraded' | 'ok'

interface OosMetrics {
    accuracy?: number | null
    precision_strong?: number | null
    recall_strong?: number | null
    f1_strong?: number | null
    precision_buy?: number | null
    recall_buy?: number | null
    // precision / test-split prevalence. 1.0 = no better than guessing at the base rate.
    // null when the class is absent from the test split — there is no base rate to divide by.
    lift_strong?: number | null
    lift_buy?: number | null
}

interface TransparencyData {
    data: {
        universe_size: number
        tickers_with_history: number | null
        date_range: { start: string; end: string } | null
        coverage: {
            with_predict_rows: number
            with_train_rows: number
            short_count: number
            min_predict_rows: number
            min_train_rows: number
        }
    }
    model: {
        status: ModelStatus
        // Machine token for WHY the status is what it is. Display surfaces key off this rather
        // than hardcoding one cause for a status that has several.
        reason?: string | null
        version: string
        message: string
        trained_at?: string | null
        samples?: number | null
        test_samples?: number | null
        train_class_distribution?: { hold: number; buy: number; strong: number } | null
        test_class_distribution?: { hold: number; buy: number; strong: number } | null
        oos_metrics?: OosMetrics | null
        // "split_model" => the metrics describe the 80%-split ensemble, not the full-data refit
        // that ships. Absent => the entry predates 2026-09-02.
        oos_metrics_scope?: string | null
        // Absent => metrics produced under the old row-based split, which separated train from
        // test by 0 trading days. Contaminated by construction.
        embargo?: { days?: number | null; cut_date?: string | null } | null
    }
}

// Plain-language captions — novices won't hover (spec AC4).
const OOS_LABELS: { key: keyof OosMetrics; label: string; plain: string }[] = [
    { key: 'accuracy', label: '整體正確率', plain: '含大量「持有」樣本，容易被灌高，別單看它。' },
    { key: 'precision_strong', label: '強買精確率', plain: '模型喊「強力買進」時真的對的比例。' },
    { key: 'recall_strong', label: '強買召回率', plain: '實際的強買機會裡被模型抓到的比例。' },
    { key: 'precision_buy', label: '買進精確率', plain: '模型喊「買進」時真的對的比例。' },
    { key: 'recall_buy', label: '買進召回率', plain: '實際的買進機會裡被模型抓到的比例。' },
]

// `degraded` covers several different facts, and the chip used to assert only one of them —
// so an upgrading user whose metrics are merely UNTRUSTWORTHY read 「AI 辨識力不足」 sitting
// directly above a precision of 0.55. The backend now sends a machine `reason`; the label follows
// it rather than guessing.
const DEGRADED_CHIP: Record<string, string> = {
    zero_power: 'AI 辨識力不足',
    below_baseline: 'AI 未優於基準比例',
    contaminated_metrics: '指標不可信 · 需重新訓練',
    no_baseline: '缺少基準對照',
    metrics_not_for_this_version: '找不到此版本的指標',
}

function statusChip(status: ModelStatus, version: string, reason?: string | null): { text: string; cls: string } {
    switch (status) {
        case 'ok':
            return { text: `AI 已訓練 · ${version}`, cls: 'border-sniper-green/40 bg-sniper-green/10 text-sniper-green' }
        case 'degraded':
            return {
                text: (reason && DEGRADED_CHIP[reason]) || '模型狀態：需注意',
                cls: 'border-orange-500/40 bg-orange-500/10 text-orange-300',
            }
        default:
            return { text: '示範模式 · AI 未訓練', cls: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-300' }
    }
}

function fmtPct(v: number | null | undefined): string {
    return v === null || v === undefined || Number.isNaN(v) ? '—' : `${(v * 100).toFixed(1)}%`
}
function fmtNum(v: number | null | undefined): string {
    return v === null || v === undefined || Number.isNaN(v) ? '—' : String(v)
}
// Handles both the model-history "YYYYMMDD_HHMM" timestamp and ISO strings.
function fmtDate(s: string | null | undefined): string {
    if (!s) return '—'
    const m = /^(\d{4})(\d{2})(\d{2})/.exec(s)
    return m ? `${m[1]}-${m[2]}-${m[3]}` : s.slice(0, 10)
}

const Transparency: React.FC = () => {
    const { data, loading, error } = useCachedApi<TransparencyData>('/api/transparency', {
        ttlMs: 60_000,
        throttleMs: 1_000,
    })
    const [expanded, setExpanded] = useState(false)

    return (
        <div className="space-y-6 animate-fade-in">
            <div className="flex items-center gap-3">
                <ShieldCheck className="text-sniper-green" size={24} />
                <div>
                    <h2 className="text-2xl font-bold uppercase tracking-widest text-white">系統透明度</h2>
                    <p className="text-xs text-dark-muted">這個系統到底知道多少——資料涵蓋與 AI 模型的真實狀態，不誇大、不隱藏。</p>
                </div>
            </div>

            {loading && !data ? (
                <div className="rounded-xl border border-dark-border bg-dark-card p-8 text-center text-dark-muted">
                    載入中…
                </div>
            ) : error || !data ? (
                <div className="rounded-lg border border-red-500/50 bg-red-900/20 p-4 text-red-200">
                    無法載入透明度資料，請確認後端運作後重試。
                </div>
            ) : (
                <>
                    {/* Simple headline (always visible) */}
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                        <div className="rounded-xl border border-dark-border bg-dark-card p-5">
                            <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-dark-muted">
                                <Database size={14} /> 資料涵蓋
                            </div>
                            <p className="text-2xl font-bold text-white">
                                {data.data.tickers_with_history ?? '—'} <span className="text-base font-normal text-dark-muted">檔股票</span>
                            </p>
                            <p className="mt-1 text-xs text-dark-muted">
                                {data.data.date_range
                                    ? `歷史區間 ${data.data.date_range.start} ~ ${data.data.date_range.end}`
                                    : '尚無足夠歷史資料'}
                            </p>
                        </div>

                        <div className="rounded-xl border border-dark-border bg-dark-card p-5">
                            <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-dark-muted">AI 模型狀態</div>
                            {(() => {
                                const chip = statusChip(data.model.status, data.model.version, data.model.reason)
                                return (
                                    <span className={`inline-flex rounded-full border px-3 py-1 text-sm font-semibold ${chip.cls}`}>
                                        {chip.text}
                                    </span>
                                )
                            })()}
                            {data.model.status !== 'ok' && data.model.message && (
                                <p className="mt-3 flex items-start gap-2 text-xs text-dark-muted">
                                    <AlertTriangle size={13} className="mt-0.5 shrink-0 text-yellow-400" />
                                    {data.model.message}
                                </p>
                            )}
                        </div>
                    </div>

                    {/* Expert depth (expandable) */}
                    <div className="rounded-xl border border-dark-border bg-dark-card/50 p-4">
                        <button
                            type="button"
                            onClick={() => setExpanded((v) => !v)}
                            className="flex w-full items-center justify-between text-sm font-semibold text-white"
                            aria-expanded={expanded}
                        >
                            <span>詳細數據（資料覆蓋與模型 OOS 指標）</span>
                            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>

                        {expanded && (
                            <div className="mt-4 space-y-6 border-t border-dark-border/40 pt-4 animate-fade-in">
                                {/* Data coverage */}
                                <div>
                                    <h4 className="mb-3 text-xs font-bold uppercase tracking-wider text-sniper-gold">資料覆蓋</h4>
                                    <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
                                        <Metric label="宇宙股票數" value={fmtNum(data.data.universe_size)} />
                                        <Metric label={`達預測門檻 (≥${data.data.coverage.min_predict_rows})`} value={fmtNum(data.data.coverage.with_predict_rows)} />
                                        <Metric label={`達訓練門檻 (≥${data.data.coverage.min_train_rows})`} value={fmtNum(data.data.coverage.with_train_rows)} />
                                        <Metric label="歷史不足" value={fmtNum(data.data.coverage.short_count)} />
                                    </div>
                                </div>

                                {/* Model metrics */}
                                <div>
                                    <h4 className="mb-1 text-xs font-bold uppercase tracking-wider text-sniper-gold">AI 模型評估</h4>
                                    <p className="mb-3 text-[11px] text-dark-muted">
                                        以下為訓練 universe 上的<strong className="text-dark-text">樣本外 (OOS)</strong> 評估，
                                        <strong className="text-dark-text">不是對未來的保證</strong>。
                                        {data.model.oos_metrics_scope === 'split_model' && (
                                            <>
                                                這些數字是在 <strong className="text-dark-text">80/20 切分</strong>的模型上量到的；
                                                實際出貨的模型是用全部資料重新訓練的另一個模型。
                                            </>
                                        )}
                                    </p>
                                    {data.model.oos_metrics && !data.model.embargo && (
                                        <p className="mb-3 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-[11px] leading-relaxed text-red-300">
                                            <strong>這批指標並非真正的樣本外結果。</strong>
                                            它們是在 2026-09-02 之前的舊切分方式下產生的 —— 當時訓練集與測試集的隔離以「列數」計算，
                                            在本專案的資料面板上實際隔離為 <strong>0 個交易日</strong>，
                                            也就是模型在被評分的那段期間上訓練過。重新訓練後才會有可信的數字。
                                        </p>
                                    )}
                                    {data.model.oos_metrics ? (
                                        <>
                                            <div className="mb-3 grid grid-cols-2 gap-3 text-xs md:grid-cols-4">
                                                <Metric label="訓練時間" value={fmtDate(data.model.trained_at)} />
                                                <Metric label="訓練樣本" value={fmtNum(data.model.samples)} />
                                                <Metric label="測試樣本" value={fmtNum(data.model.test_samples)} />
                                                <Metric label="版本" value={data.model.version} />
                                            </div>
                                            {data.model.train_class_distribution && (
                                                <div className="mb-3 rounded-lg border border-dark-border/40 bg-dark-bg/30 p-3">
                                                    <div className="mb-1 text-[10px] uppercase tracking-wider text-dark-muted">
                                                        <strong>訓練集</strong>標籤分布（類別越不平衡，上面的「整體正確率」越容易被灌高）
                                                    </div>
                                                    <div className="flex flex-wrap gap-4 text-sm text-white">
                                                        <span>持有 {fmtPct(data.model.train_class_distribution.hold)}</span>
                                                        <span>買進 {fmtPct(data.model.train_class_distribution.buy)}</span>
                                                        <span>強買 {fmtPct(data.model.train_class_distribution.strong)}</span>
                                                    </div>
                                                </div>
                                            )}
                                            {data.model.test_class_distribution && (
                                                <div className="mb-3 rounded-lg border border-sniper-gold/30 bg-dark-bg/30 p-3">
                                                    <div className="mb-1 text-[10px] uppercase tracking-wider text-dark-muted">
                                                        <strong>測試集</strong>標籤分布 —— 這才是下面精確率該比對的基準比例
                                                    </div>
                                                    <div className="flex flex-wrap gap-4 text-sm text-white">
                                                        <span>持有 {fmtPct(data.model.test_class_distribution.hold)}</span>
                                                        <span>買進 {fmtPct(data.model.test_class_distribution.buy)}</span>
                                                        <span>強買 {fmtPct(data.model.test_class_distribution.strong)}</span>
                                                    </div>
                                                </div>
                                            )}
                                            <LiftRow
                                                label="強買提升倍數"
                                                plain="強買精確率 ÷ 測試集強買比例。1.0 代表與「照基準比例亂猜」一樣好。"
                                                value={data.model.oos_metrics?.lift_strong}
                                            />
                                            <LiftRow
                                                label="買進提升倍數"
                                                plain="買進精確率 ÷ 測試集買進比例。低於 1.0 代表比亂猜還差。"
                                                value={data.model.oos_metrics?.lift_buy}
                                            />
                                            <div className="space-y-2">
                                                {OOS_LABELS.map((m) => (
                                                    <div key={m.key} className="flex items-start justify-between gap-3 border-t border-dark-border/30 pt-2">
                                                        <div>
                                                            <div className="text-sm text-white">{m.label}</div>
                                                            <div className="text-[10px] leading-tight text-dark-muted">{m.plain}</div>
                                                        </div>
                                                        <div className="shrink-0 font-mono text-sm text-white">{fmtPct(data.model.oos_metrics?.[m.key])}</div>
                                                    </div>
                                                ))}
                                            </div>
                                        </>
                                    ) : (
                                        <p className="text-sm text-dark-muted">
                                            尚無已訓練模型，因此沒有評估指標可顯示（AI 機率維持 N/A）。
                                        </p>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    )
}

/**
 * A lift is precision divided by the test-split base rate. It is the number that makes a raw
 * precision readable, so it is rendered as a verdict rather than as a neutral figure: at or below
 * 1.0 the model is not beating a coin weighted to the class prevalence, and saying so is the whole
 * point of this panel.
 */
const LiftRow: React.FC<{ label: string; plain: string; value?: number | null }> = ({ label, plain, value }) => {
    const hasValue = typeof value === 'number' && Number.isFinite(value)
    const noEdge = hasValue && (value as number) <= 1.0
    return (
        <div className="mb-3 flex items-start justify-between gap-3 rounded-lg border border-dark-border/40 bg-dark-bg/30 p-3">
            <div>
                <div className="text-sm text-white">{label}</div>
                <div className="text-[10px] leading-tight text-dark-muted">{plain}</div>
                {noEdge && (
                    <div className="mt-1 text-[10px] font-semibold text-red-400">
                        未優於基準比例 —— 這個類別上模型沒有可用的優勢。
                    </div>
                )}
                {!hasValue && (
                    <div className="mt-1 text-[10px] text-dark-muted">
                        這個模型是在開始記錄基準比例之前訓練的，無法計算提升倍數。
                    </div>
                )}
            </div>
            <div className={`shrink-0 font-mono text-sm ${noEdge ? 'text-red-400' : hasValue ? 'text-white' : 'text-dark-muted'}`}>
                {hasValue ? `${(value as number).toFixed(2)}×` : '—'}
            </div>
        </div>
    )
}

const Metric: React.FC<{ label: string; value: string }> = ({ label, value }) => (
    <div className="rounded-lg border border-dark-border bg-dark-bg/40 p-3">
        <div className="text-[10px] uppercase tracking-wider text-dark-muted">{label}</div>
        <div className="mt-1 font-mono text-base font-semibold text-white">{value}</div>
    </div>
)

export default Transparency
