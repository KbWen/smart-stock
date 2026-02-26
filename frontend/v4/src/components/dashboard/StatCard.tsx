import React from 'react'
import { Info } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import Tooltip from '../Tooltip'

interface StatCardProps {
    title: string
    value: string | number
    unit?: string
    subtitle?: string
    icon: LucideIcon
    tooltip: string
    isLoading?: boolean
    valueColorClass?: string
}

const StatCard: React.FC<StatCardProps> = ({
    title,
    value,
    unit,
    subtitle,
    icon: Icon,
    tooltip,
    isLoading,
    valueColorClass = 'text-white'
}) => {
    return (
        <div className="premium-card rounded-xl border border-dark-border bg-dark-card/60 p-6 shadow-lg backdrop-blur-md">
            <div className="mb-2 flex items-center gap-2">
                <Icon className="text-dark-muted" size={20} />
                <h2 className="text-lg font-semibold text-dark-muted">{title}</h2>
                <Tooltip content={tooltip}>
                    <Info size={14} className="text-dark-muted opacity-50 transition-opacity hover:opacity-100 cursor-help" />
                </Tooltip>
            </div>
            {isLoading ? (
                <div className="h-10 w-1/2 animate-pulse rounded bg-dark-border" />
            ) : (
                <>
                    <div className={`text-3xl font-bold ${valueColorClass}`}>
                        {value}
                        {unit && <span className="text-xl text-dark-muted ml-0.5">{unit}</span>}
                    </div>
                    {subtitle && (
                        <div className="mt-1 text-sm text-dark-muted">
                            {subtitle}
                        </div>
                    )}
                </>
            )}
        </div>
    )
}

export default React.memo(StatCard)
