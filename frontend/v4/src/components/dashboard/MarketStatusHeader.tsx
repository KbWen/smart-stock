import React from 'react'
import { Activity, Zap, ShieldAlert } from 'lucide-react'
import StatCard from './StatCard'
import type { MarketStatus } from '../../hooks/useDashboardData'

interface MarketStatusHeaderProps {
    market: MarketStatus
    isLoading: boolean
    riskColorClass: string
}

const MarketStatusHeader: React.FC<MarketStatusHeaderProps> = ({
    market,
    isLoading,
    riskColorClass
}) => {
    return (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            <StatCard
                title="大盤多空比"
                value={market.bull_ratio.toFixed(1)}
                unit="%"
                subtitle={`市場溫度: ${market.market_temp.toFixed(1)}`}
                icon={Activity}
                tooltip="目前全台股站上 20 日均線的個股比例。"
                isLoading={isLoading}
            />

            <StatCard
                title="AI 情緒指數"
                value={market.ai_sentiment.toFixed(1)}
                unit="%"
                subtitle={`Model ${market.model_version}`}
                icon={Zap}
                tooltip="由 AI 模型綜合技術指標、成交量與市場氛圍算出的多頭信心指數。"
                isLoading={isLoading}
                valueColorClass="text-sniper-gold"
            />

            <StatCard
                title="風險等級"
                value={market.risk_level}
                subtitle={`掃描數量: ${market.total_stocks}`}
                icon={ShieldAlert}
                tooltip="綜合市場溫度與風險情緒，建議當前的操作模式（積極/中性/減碼）。"
                isLoading={isLoading}
                valueColorClass={riskColorClass}
            />
        </div>
    )
}

export default React.memo(MarketStatusHeader)
