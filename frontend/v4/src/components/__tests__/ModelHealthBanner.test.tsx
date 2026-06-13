/**
 * ModelHealthBanner — honest model-state disclosure.
 * Spec: .agentcortex/specs/ui-model-state-disclosure.md — AC3
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ModelHealthBanner from '../ModelHealthBanner'

describe('ModelHealthBanner', () => {
    it('renders the disclosure message when the model is degraded', () => {
        render(
            <ModelHealthBanner
                health={{ status: 'degraded', version: 'v4.x', message: '模型對買訊的辨識力不足，僅供參考。' }}
            />,
        )
        expect(screen.getByRole('alert')).toBeInTheDocument()
        expect(screen.getByText(/辨識力不足/)).toBeInTheDocument()
    })

    it('renders nothing when the model is ok', () => {
        const { container } = render(<ModelHealthBanner health={{ status: 'ok', message: '' }} />)
        expect(container).toBeEmptyDOMElement()
        expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })

    it('renders nothing when health is null/absent', () => {
        const { container } = render(<ModelHealthBanner health={null} />)
        expect(container).toBeEmptyDOMElement()
    })
})
