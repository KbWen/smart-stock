/**
 * Market BREADTH, not risk. `breadth_level` is the share of tracked tickers whose trend score
 * exceeds 20 — no volatility, no index level, no drawdown, no correlation. The backend sends a
 * stable machine token and the label lives here, so re-wording the UI can no longer silently
 * break the colour logic the way substring matching on "HIGH"/"LOW" did.
 */
export type BreadthLevel = 'BULLISH' | 'NEUTRAL' | 'BEARISH' | 'UNKNOWN'

export const BREADTH_LABEL: Record<BreadthLevel, string> = {
    BULLISH: '偏多 (廣度高)',
    NEUTRAL: '中性',
    BEARISH: '偏空 (廣度低)',
    UNKNOWN: '—',
}

export const BREADTH_COLOR: Record<BreadthLevel, string> = {
    BULLISH: 'text-sniper-green',
    NEUTRAL: 'text-yellow-500',
    BEARISH: 'text-red-500',
    UNKNOWN: 'text-dark-muted',
}

export const BREADTH_TOOLTIP =
    '多頭廣度：追蹤標的中趨勢分數 > 20 的比例。這是市場「有多少檔在走多」的廣度讀數，' +
    '不是風險評估 — 不含波動率、指數水位、回撤或相關性。'

export function breadthOf(value: string | null | undefined): BreadthLevel {
    return value === 'BULLISH' || value === 'NEUTRAL' || value === 'BEARISH' ? value : 'UNKNOWN'
}
