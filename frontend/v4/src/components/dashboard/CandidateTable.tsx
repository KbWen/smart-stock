import React, { useCallback, useMemo, useState, memo } from 'react'
import { ArrowDown, ArrowUp, Info, Minus } from 'lucide-react'
import Tooltip from '../Tooltip'
import CandidateRow from './CandidateRow'
import type { StockCandidate } from '../../hooks/useDashboardData'

interface CandidateTableProps {
    stocks: StockCandidate[]
    selectedTicker?: string | null
    onSelect: (ticker: string) => void
    height?: number
}

type SortKey = 'price' | 'change_percent' | 'rise_score' | 'ai_prob'
type SortDir = 'asc' | 'desc'

const ROW_HEIGHT = 76
const OVERSCAN_COUNT = 4

const CandidateTable: React.FC<CandidateTableProps> = ({
    stocks,
    selectedTicker,
    onSelect,
    height = 460
}) => {
    const [sortConfig, setSortConfig] = useState<{ key: SortKey; dir: SortDir }>({
        key: 'rise_score',
        dir: 'desc',
    })
    const [scrollTop, setScrollTop] = useState<number>(0)

    const handleSort = useCallback((key: SortKey) => {
        setSortConfig((prev) => ({
            key,
            dir: prev.key === key && prev.dir === 'desc' ? 'asc' : 'desc'
        }))
    }, [])

    const sortedStocks = useMemo(() => {
        const sortable = [...stocks]
        sortable.sort((a, b) => {
            const aVal = a[sortConfig.key] ?? 0
            const bVal = b[sortConfig.key] ?? 0
            if (aVal < bVal) return sortConfig.dir === 'asc' ? -1 : 1
            if (aVal > bVal) return sortConfig.dir === 'asc' ? 1 : -1
            return 0
        })
        return sortable
    }, [stocks, sortConfig])

    // Virtualization logic
    const visibleRange = useMemo(() => {
        const start = Math.max(Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN_COUNT, 0)
        const visibleCount = Math.ceil(height / ROW_HEIGHT) + OVERSCAN_COUNT * 2
        const end = Math.min(start + visibleCount, sortedStocks.length)
        return { start, end }
    }, [scrollTop, height, sortedStocks.length])

    const visibleRows = sortedStocks.slice(visibleRange.start, visibleRange.end)
    const paddingTop = visibleRange.start * ROW_HEIGHT
    const paddingBottom = Math.max((sortedStocks.length - visibleRange.end) * ROW_HEIGHT, 0)

    const renderSortIcon = (columnKey: SortKey) => {
        if (sortConfig.key !== columnKey) return <Minus size={14} className="inline opacity-20" />
        return sortConfig.dir === 'asc'
            ? <ArrowUp size={14} className="inline tracking-tight text-white" />
            : <ArrowDown size={14} className="inline text-white" />
    }

    return (
        <div className="flex flex-col">
            <div className="grid grid-cols-5 border-b border-dark-border p-3 text-left text-sm text-dark-muted select-none">
                <div className="font-normal">Ticker</div>
                {(['price', 'change_percent', 'rise_score', 'ai_prob'] as SortKey[]).map(key => (
                    <button
                        key={key}
                        type="button"
                        className="text-left font-normal hover:text-white transition-colors"
                        onClick={() => handleSort(key)}
                    >
                        <span className="flex items-center gap-1 uppercase tracking-wider text-[11px] font-bold">
                            {key.replace('_', ' ')} {renderSortIcon(key)}
                            {(key === 'rise_score' || key === 'ai_prob') && (
                                <Tooltip content={key === 'rise_score' ? "技術評分" : "AI 預測機率"}>
                                    <Info size={12} className="opacity-50" />
                                </Tooltip>
                            )}
                        </span>
                    </button>
                ))}
            </div>

            <div
                className="overflow-y-auto scrollbar-thin scrollbar-thumb-dark-border"
                style={{ height: `${height}px` }}
                onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
            >
                <div style={{ paddingTop, paddingBottom }}>
                    {visibleRows.map((stock) => (
                        <CandidateRow
                            key={stock.ticker}
                            stock={stock}
                            isSelected={selectedTicker === stock.ticker}
                            onSelect={onSelect}
                            rowHeight={ROW_HEIGHT}
                        />
                    ))}
                </div>
            </div>
        </div>
    )
}

export default memo(CandidateTable)
