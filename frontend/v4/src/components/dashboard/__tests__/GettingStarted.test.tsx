/**
 * GettingStarted — novice entry tests (docs/specs/novice-entry.md).
 * Honest positioning + guided links + dismissible/remembered + demo-mode note.
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, beforeEach } from 'vitest'
import GettingStarted from '../GettingStarted'

function renderGuide(props: { modelHealth?: { status?: string } | null } = {}) {
    return render(
        <MemoryRouter>
            <GettingStarted {...props} />
        </MemoryRouter>,
    )
}

describe('GettingStarted — novice entry', () => {
    beforeEach(() => {
        try {
            localStorage.clear()
        } catch {
            /* ignore */
        }
    })

    it('renders honest positioning (not investment advice) + guided links', () => {
        renderGuide()
        expect(screen.getByText(/不是投顧/)).toBeTruthy()
        // '系統透明度' appears twice by design: an inline link + a guided card.
        expect(screen.getAllByText('系統透明度').length).toBeGreaterThan(0)
        expect(screen.getByText('選股雷達')).toBeTruthy()
    })

    it('dismiss hides the panel and remembers the choice', () => {
        renderGuide()
        fireEvent.click(screen.getByLabelText('關閉新手導引'))
        expect(screen.queryByText(/不是投顧/)).toBeNull()
        expect(screen.getByText(/顯示新手導引/)).toBeTruthy()
        expect(localStorage.getItem('novice_guide_dismissed')).toBe('1')
    })

    it('stays hidden when already dismissed, with a working re-open toggle', () => {
        localStorage.setItem('novice_guide_dismissed', '1')
        renderGuide()
        expect(screen.queryByText(/不是投顧/)).toBeNull()
        fireEvent.click(screen.getByText(/顯示新手導引/))
        expect(screen.getByText(/不是投顧/)).toBeTruthy()
    })

    it('shows the demo-mode note only when the model is unavailable', () => {
        const { unmount } = renderGuide({ modelHealth: { status: 'unavailable' } })
        expect(screen.getByText(/示範模式 · AI 未訓練/)).toBeTruthy()
        unmount()
        renderGuide({ modelHealth: { status: 'ok' } })
        expect(screen.queryByText(/示範模式 · AI 未訓練/)).toBeNull()
    })
})
