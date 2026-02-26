import React from 'react'

interface DetailHeaderProps {
    ticker: string
    name: string
    price: number
    recommendation: {
        text: string
        color: string
    }
    updatedAt?: string
}

const DetailHeader: React.FC<DetailHeaderProps> = ({
    ticker,
    name,
    price,
    recommendation,
    updatedAt
}) => {
    return (
        <div className="mb-6 flex items-start justify-between border-b border-dark-border pb-4">
            <div>
                <h2 className="text-3xl font-bold tracking-tight text-white">{ticker}</h2>
                <p className="text-sm text-dark-muted">{name}</p>
            </div>
            <div className="flex flex-col items-end">
                <div className="text-2xl font-bold font-mono text-white">{price.toFixed(2)}</div>
                <div className={`mt-1 rounded-full border px-3 py-1 text-xs font-bold ${recommendation.color}`}>
                    {recommendation.text}
                </div>
                <div className="mt-2 text-xs text-dark-muted whitespace-nowrap">DB 更新: {updatedAt || 'Unknown'}</div>
            </div>
        </div>
    )
}

export default React.memo(DetailHeader)
