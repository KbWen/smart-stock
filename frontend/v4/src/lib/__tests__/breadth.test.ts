import { describe, expect, it } from 'vitest'

import { BREADTH_COLOR, BREADTH_LABEL, breadthOf } from '../breadth'

describe('breadthOf', () => {
    it('passes through the three real machine tokens', () => {
        expect(breadthOf('BULLISH')).toBe('BULLISH')
        expect(breadthOf('NEUTRAL')).toBe('NEUTRAL')
        expect(breadthOf('BEARISH')).toBe('BEARISH')
    })

    it('maps missing or unexpected values to UNKNOWN rather than throwing', () => {
        expect(breadthOf(undefined)).toBe('UNKNOWN')
        expect(breadthOf(null)).toBe('UNKNOWN')
        expect(breadthOf('')).toBe('UNKNOWN')
        expect(breadthOf('UNKNOWN')).toBe('UNKNOWN')
        // The pre-2026-09-02 display strings. A backend that had not been upgraded would send
        // these; they must degrade to UNKNOWN, not be half-matched the way the old
        // `.includes('HIGH')` colour logic did.
        expect(breadthOf('LOW RISK (BULL)')).toBe('UNKNOWN')
        expect(breadthOf('HIGH RISK (BEAR)')).toBe('UNKNOWN')
    })
})

describe('breadth label and colour maps', () => {
    it('covers every level, so a new token cannot render blank', () => {
        for (const level of ['BULLISH', 'NEUTRAL', 'BEARISH', 'UNKNOWN'] as const) {
            expect(BREADTH_LABEL[level]).toBeTruthy()
            expect(BREADTH_COLOR[level]).toMatch(/^text-/)
        }
    })

    it('keeps the three real states visually distinct', () => {
        expect(BREADTH_COLOR.BULLISH).toBe('text-sniper-green')
        expect(BREADTH_COLOR.NEUTRAL).toBe('text-yellow-500')
        expect(BREADTH_COLOR.BEARISH).toBe('text-red-500')
    })

    it('labels breadth as breadth — no label may imply a risk assessment', () => {
        // The whole point of the rename: this value is the share of tracked tickers with
        // trend_score > 20. It carries no volatility, index level, drawdown or correlation.
        for (const label of Object.values(BREADTH_LABEL)) {
            expect(label).not.toMatch(/風險|RISK/i)
        }
    })
})
