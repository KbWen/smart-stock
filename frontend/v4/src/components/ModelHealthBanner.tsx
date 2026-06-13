import React from 'react'
import { AlertTriangle } from 'lucide-react'
import type { ModelHealth } from '../hooks/useDashboardData'

/**
 * Honest disclosure banner: shown when the active AI model is degraded
 * (cannot identify buy signals) or unavailable. Informational only — it does
 * not block the rest of the UI. Hidden when the model is healthy.
 */
const ModelHealthBanner: React.FC<{ health?: ModelHealth | null }> = ({ health }) => {
    if (!health || health.status === 'ok') return null

    const tone =
        health.status === 'unavailable'
            ? 'border-yellow-500/30 bg-yellow-500/10 text-yellow-300'
            : 'border-orange-500/40 bg-orange-500/10 text-orange-300'

    return (
        <div className={`flex items-start gap-2 rounded-lg border px-4 py-2 text-sm ${tone}`} role="alert">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" />
            <span>{health.message}</span>
        </div>
    )
}

export default React.memo(ModelHealthBanner)
