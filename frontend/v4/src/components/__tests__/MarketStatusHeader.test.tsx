import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import MarketStatusHeader from '../dashboard/MarketStatusHeader'
import type { MarketStatus } from '../../hooks/useDashboardData'

const createMarketStatus = (overrides: Partial<MarketStatus> = {}): MarketStatus => ({
    bull_ratio: 58.5,
    market_temp: 62.3,
    ai_sentiment: 71.2,
    risk_level: '中性',
    total_stocks: 1200,
    model_version: 'v4.2',
    history: [],
    ...overrides,
})

describe('MarketStatusHeader', () => {
    it('renders all three StatCards with correct values', () => {
        render(
            <MarketStatusHeader
                market={createMarketStatus()}
                isLoading={false}
                riskColorClass="text-white"
            />,
        )
        // Bull ratio card
        expect(screen.getByText('大盤多空比')).toBeInTheDocument()
        expect(screen.getByText('58.5')).toBeInTheDocument()

        // AI sentiment card
        expect(screen.getByText('AI 情緒指數')).toBeInTheDocument()
        expect(screen.getByText('71.2')).toBeInTheDocument()

        // Risk level card
        expect(screen.getByText('風險等級')).toBeInTheDocument()
        expect(screen.getByText('中性')).toBeInTheDocument()
    })

    it('shows model version in AI sentiment subtitle', () => {
        render(
            <MarketStatusHeader
                market={createMarketStatus({ model_version: 'v4.3' })}
                isLoading={false}
                riskColorClass="text-white"
            />,
        )
        expect(screen.getByText('Model v4.3')).toBeInTheDocument()
    })

    it('shows market temp in bull ratio subtitle', () => {
        render(
            <MarketStatusHeader
                market={createMarketStatus({ market_temp: 55.1 })}
                isLoading={false}
                riskColorClass="text-white"
            />,
        )
        expect(screen.getByText('市場溫度: 55.1')).toBeInTheDocument()
    })

    it('shows total_stocks in risk level subtitle', () => {
        render(
            <MarketStatusHeader
                market={createMarketStatus({ total_stocks: 980 })}
                isLoading={false}
                riskColorClass="text-white"
            />,
        )
        expect(screen.getByText('掃描數量: 980')).toBeInTheDocument()
    })

    it('applies riskColorClass to risk level value', () => {
        render(
            <MarketStatusHeader
                market={createMarketStatus({ risk_level: '積極' })}
                isLoading={false}
                riskColorClass="text-sniper-green"
            />,
        )
        const riskValue = screen.getByText('積極')
        expect(riskValue.className).toContain('text-sniper-green')
    })

    it('passes isLoading to all three StatCards', () => {
        const { container } = render(
            <MarketStatusHeader
                market={createMarketStatus()}
                isLoading={true}
                riskColorClass="text-white"
            />,
        )
        const skeletons = container.querySelectorAll('.animate-pulse')
        expect(skeletons.length).toBe(3)
    })
})
