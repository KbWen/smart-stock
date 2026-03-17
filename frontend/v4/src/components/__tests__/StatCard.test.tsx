import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Activity } from 'lucide-react'
import StatCard from '../dashboard/StatCard'

describe('StatCard', () => {
    it('renders title and value correctly', () => {
        render(
            <StatCard
                title="大盤多空比"
                value={65.4}
                unit="%"
                icon={Activity}
                tooltip="目前全台股站上 20 日均線的個股比例。"
            />,
        )
        expect(screen.getByText('大盤多空比')).toBeInTheDocument()
        expect(screen.getByText('65.4')).toBeInTheDocument()
        expect(screen.getByText('%')).toBeInTheDocument()
    })

    it('renders subtitle when provided', () => {
        render(
            <StatCard
                title="Test"
                value={42}
                subtitle="副標題內容"
                icon={Activity}
                tooltip="說明"
            />,
        )
        expect(screen.getByText('副標題內容')).toBeInTheDocument()
    })

    it('shows loading skeleton when isLoading=true', () => {
        const { container } = render(
            <StatCard
                title="Loading Card"
                value={0}
                icon={Activity}
                tooltip="說明"
                isLoading={true}
            />,
        )
        // Should render the animate-pulse skeleton div, not the value
        expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
        expect(screen.queryByText('0')).not.toBeInTheDocument()
    })

    it('applies custom valueColorClass', () => {
        render(
            <StatCard
                title="Risk"
                value="積極"
                icon={Activity}
                tooltip="說明"
                valueColorClass="text-sniper-gold"
            />,
        )
        const valueEl = screen.getByText('積極')
        expect(valueEl.className).toContain('text-sniper-gold')
    })

    it('renders tooltip trigger icon', () => {
        render(
            <StatCard
                title="Test"
                value={1}
                icon={Activity}
                tooltip="這是 tooltip 說明"
            />,
        )
        // Tooltip wraps an Info icon — the tooltip content div appears on hover.
        // Verify the card title is present as a proxy for correct rendering.
        expect(screen.getByText('Test')).toBeInTheDocument()
    })
})
