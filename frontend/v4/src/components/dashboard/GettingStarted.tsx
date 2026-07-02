import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Compass, LineChart, Scan, ShieldCheck, Target, X } from 'lucide-react'

const STORAGE_KEY = 'novice_guide_dismissed'

// localStorage may be blocked/absent (private mode / SSR) — guard so it degrades
// to "always show", never crashes.
function readDismissed(): boolean {
    try {
        return localStorage.getItem(STORAGE_KEY) === '1'
    } catch {
        return false
    }
}
function writeDismissed(dismissed: boolean): void {
    try {
        if (dismissed) localStorage.setItem(STORAGE_KEY, '1')
        else localStorage.removeItem(STORAGE_KEY)
    } catch {
        /* storage blocked — best-effort only */
    }
}

interface GuideLink {
    to: string
    icon: React.ComponentType<{ size?: number; className?: string }>
    title: string
    desc: string
}

const LINKS: GuideLink[] = [
    { to: '/', icon: Target, title: '精選候選', desc: '看今日技術面較強的標的（分數是技術面評估，不是保證）。' },
    { to: '/indicators', icon: Scan, title: '選股雷達', desc: '用技術條件篩選，並看每檔「為什麼」入選。' },
    { to: '/backtest', icon: LineChart, title: 'AI 回測 · 策略實驗室', desc: '用歷史資料誠實回測你的策略（已扣台股交易成本）。' },
    { to: '/transparency', icon: ShieldCheck, title: '系統透明度', desc: '系統到底知道多少：資料涵蓋與 AI 模型的真實狀態。' },
]

interface GettingStartedProps {
    modelHealth?: { status?: string } | null
}

const GettingStarted: React.FC<GettingStartedProps> = ({ modelHealth }) => {
    const [dismissed, setDismissed] = useState<boolean>(() => readDismissed())

    const dismiss = (): void => {
        setDismissed(true)
        writeDismissed(true)
    }
    const reopen = (): void => {
        setDismissed(false)
        writeDismissed(false)
    }

    if (dismissed) {
        return (
            <button
                type="button"
                onClick={reopen}
                className="inline-flex items-center gap-1.5 rounded-lg border border-dark-border bg-dark-card/60 px-3 py-1.5 text-xs text-dark-muted transition-colors hover:text-white"
            >
                <Compass size={13} /> 顯示新手導引
            </button>
        )
    }

    return (
        <div className="rounded-xl border border-sniper-green/20 bg-dark-card/60 backdrop-blur-md p-5 animate-fade-in">
            <div className="mb-2 flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                    <Compass className="text-sniper-green" size={20} />
                    <h3 className="text-lg font-bold text-white">新手指南</h3>
                </div>
                <button
                    type="button"
                    onClick={dismiss}
                    aria-label="關閉新手導引"
                    className="text-dark-muted transition-colors hover:text-white"
                >
                    <X size={18} />
                </button>
            </div>

            {/* Honest positioning — set expectations before a novice misreads a score. */}
            <p className="text-sm text-dark-text">
                這是一個<strong className="text-sniper-green">誠實的台股研究工作台</strong>——
                <strong className="text-white">不是投顧、不提供買賣建議</strong>，也不會告訴你「買什麼會賺」。
            </p>
            <p className="mt-1 text-xs text-dark-muted">
                技術分數是量化評估、<strong className="text-dark-text">不是獲利保證</strong>；AI 機率可能顯示 N/A 或「示範模式」，
                那是<strong className="text-dark-text">誠實地表示模型尚未訓練或辨識力不足</strong>，並非故障。想了解可看{' '}
                <Link to="/transparency" className="text-sniper-green underline-offset-2 hover:underline">系統透明度</Link>。
            </p>

            {modelHealth?.status === 'unavailable' && (
                <div className="mt-3 inline-flex rounded border border-yellow-500/30 bg-yellow-500/10 px-2 py-0.5 text-[11px] font-semibold text-yellow-400">
                    目前為示範模式 · AI 未訓練
                </div>
            )}

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                {LINKS.map((l) => {
                    const Icon = l.icon
                    return (
                        <Link
                            key={l.to}
                            to={l.to}
                            className="group flex items-start gap-3 rounded-lg border border-dark-border bg-dark-bg/40 p-3 transition-colors hover:border-sniper-green/40 hover:bg-sniper-green/5"
                        >
                            <Icon size={18} className="mt-0.5 shrink-0 text-sniper-green" />
                            <div className="min-w-0">
                                <div className="text-sm font-semibold text-white group-hover:text-sniper-green">{l.title}</div>
                                <div className="mt-0.5 text-[11px] leading-tight text-dark-muted">{l.desc}</div>
                            </div>
                        </Link>
                    )
                })}
            </div>
        </div>
    )
}

export default GettingStarted
