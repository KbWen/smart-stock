/**
 * Dashboard — tests the two net-new first-run behaviors (v1 #3):
 *   AC1: the 示範模式 demo badge appears iff the AI model is unavailable.
 *   AC4: the full-market sync is gated behind a window.confirm.
 *
 * useDashboardData and the lazy/heavy children are mocked so the test isolates
 * Dashboard's own badge + sync-confirm logic.
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

const mockTriggerSync = vi.fn()
const mockUseDashboardData = vi.hoisted(() => vi.fn())

vi.mock('../../hooks/useDashboardData', () => ({ useDashboardData: mockUseDashboardData }))
vi.mock('../../components/dashboard/MarketStatusHeader', () => ({ default: () => <div>market-header</div> }))
vi.mock('../../components/StockList', () => ({ default: () => <div>stock-list</div> }))
vi.mock('../../components/SniperCard', () => ({ default: () => <div>sniper-card</div> }))

import Dashboard from '../Dashboard'

const baseState = (overrides: Record<string, unknown> = {}) => ({
    market: null,
    modelHealth: null,
    isLoading: false,
    marketError: null,
    riskColorClass: '',
    lastUpdated: '10:00',
    dbUpdatedAt: '2026-06-20 10:00',
    isDbStale: false,
    syncStatus: { isSyncing: false, total: 0, current: 0, failedCount: 0, currentTicker: '' },
    triggerSync: mockTriggerSync,
    ...overrides,
})

describe('Dashboard — demo-mode badge (AC1)', () => {
    beforeEach(() => { mockUseDashboardData.mockReset(); mockTriggerSync.mockReset() })

    it('shows the 示範模式 badge when the AI model is unavailable', async () => {
        mockUseDashboardData.mockReturnValue(baseState({ modelHealth: { status: 'unavailable', message: '模型尚未訓練' } }))
        render(<Dashboard />)
        expect(await screen.findByText(/示範模式/)).toBeInTheDocument()
    })

    it('hides the 示範模式 badge when the model is ok', async () => {
        mockUseDashboardData.mockReturnValue(baseState({ modelHealth: { status: 'ok', message: '' } }))
        render(<Dashboard />)
        await screen.findByText('同步資料庫')
        expect(screen.queryByText(/示範模式/)).not.toBeInTheDocument()
    })
})

describe('Dashboard — sync confirm gate (AC4)', () => {
    beforeEach(() => { mockUseDashboardData.mockReset(); mockTriggerSync.mockReset() })

    it('triggers a full-market sync only after the user confirms', async () => {
        mockUseDashboardData.mockReturnValue(baseState())
        const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
        render(<Dashboard />)
        fireEvent.click(await screen.findByText('同步資料庫'))
        expect(confirmSpy).toHaveBeenCalledTimes(1)
        expect(mockTriggerSync).toHaveBeenCalledTimes(1)
        confirmSpy.mockRestore()
    })

    it('does not sync when the user cancels the confirm', async () => {
        mockUseDashboardData.mockReturnValue(baseState())
        const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
        render(<Dashboard />)
        fireEvent.click(await screen.findByText('同步資料庫'))
        expect(mockTriggerSync).not.toHaveBeenCalled()
        confirmSpy.mockRestore()
    })
})
