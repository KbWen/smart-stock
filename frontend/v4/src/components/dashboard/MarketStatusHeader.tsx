import React from 'react'
import { Activity, Zap, ShieldAlert } from 'lucide-react'
import StatCard from './StatCard'
import type { MarketStatus } from '../../hooks/useDashboardData'
import { BREADTH_LABEL, BREADTH_TOOLTIP, breadthOf } from '../../lib/breadth'

interface MarketStatusHeaderProps {
    market: MarketStatus | null
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
                value={market ? market.bull_ratio.toFixed(1) : '—'}
                unit="%"
                subtitle={`市場溫度: ${market ? market.market_temp.toFixed(1) : '—'}`}
                icon={Activity}
                tooltip="趨勢分數（均線排列＋斜率綜合）大於 20 的個股占比。"
                isLoading={isLoading}
            />

            <StatCard
                title="AI 情緒指數"
                value={market ? market.ai_sentiment.toFixed(1) : '—'}
                unit="%"
                subtitle={`Model ${market?.model_version ?? '—'}`}
                icon={Zap}
                tooltip="前 50 檔（依 AI 機率排序）的 AI 買點機率平均值。"
                isLoading={isLoading}
                valueColorClass="text-sniper-gold"
            />

            <StatCard
                title="多頭廣度"
                value={BREADTH_LABEL[breadthOf(market?.breadth_level)]}
                subtitle={`掃描數量: ${market?.total_stocks ?? '—'}`}
                icon={ShieldAlert}
                tooltip={BREADTH_TOOLTIP}
                isLoading={isLoading}
                valueColorClass={riskColorClass}
            />
        </div>
    )
}

export default React.memo(MarketStatusHeader)
