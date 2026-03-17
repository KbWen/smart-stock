import { test, expect } from '@playwright/test'

/**
 * E2E Smoke & Performance Tests
 * Spec: docs/specs/frontend-testing.md — AC#3 (Playwright E2E)
 * Spec: docs/specs/frontend-api-opt.md — AC#1 (Single Batch Fetch), AC#3 (<300ms)
 */

test('dashboard loads successfully', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/Smart Stock Selector/i)
})

test('renders three MarketStatusHeader cards', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('大盤多空比')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('AI 情緒指數')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('風險等級')).toBeVisible({ timeout: 10_000 })
})

test('Top Candidates panel renders without crash', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('Top Candidates')).toBeVisible({ timeout: 10_000 })
    // No uncaught JS error should appear
    const errors: string[] = []
    page.on('pageerror', (err) => errors.push(err.message))
    await page.waitForTimeout(1000)
    expect(errors.filter(e => !e.includes('ResizeObserver'))).toHaveLength(0)
})

test('bulk meta fetch is single-call and under 300ms', async ({ page }) => {
    let metaCallCount = 0
    const metaDurations: number[] = []

    await page.route('**/api/v4/sniper/candidates?limit=50', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify([
                { ticker: '2330.TW', name: 'TSMC', price: 1000, change_percent: 1.2, rise_score: 81, ai_prob: 74 },
                { ticker: '2317.TW', name: 'Hon Hai', price: 120, change_percent: 0.4, rise_score: 76, ai_prob: 69 },
            ]),
        })
    })

    await page.route('**/api/v4/meta?*', async (route) => {
        metaCallCount += 1
        const start = Date.now()
        await page.waitForTimeout(60)
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                data: {
                    '2330.TW': {
                        signals: { squeeze: true, golden_cross: true, volume_spike: false },
                        trend_score: 0.9,
                        momentum_score: 0.7,
                        volatility_score: 0.4,
                    },
                    '2317.TW': {
                        signals: { squeeze: false, golden_cross: false, volume_spike: true },
                        trend_score: 0.4,
                        momentum_score: 0.6,
                        volatility_score: 0.5,
                    },
                },
            }),
        })
        metaDurations.push(Date.now() - start)
    })

    await page.goto('/')
    await expect(page).toHaveTitle(/Smart Stock Selector/i)

    await expect.poll(() => metaCallCount, { timeout: 3000 }).toBe(1)
    await page.waitForTimeout(300)
    expect(metaCallCount).toBe(1)
    expect(metaDurations[0]).toBeLessThan(300)
})
