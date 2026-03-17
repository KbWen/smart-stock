import React from 'react'

interface GlassCardProps {
    children: React.ReactNode
    className?: string
    /** If true, suppresses the hover lift transform */
    static?: boolean
    /** Pass-through onClick for interactive card wrappers */
    onClick?: () => void
}

/**
 * GlassCard — standard glassmorphism card shell.
 *
 * Applies the shared `.glass-card` CSS layer (backdrop-blur-xl, bg-white/5,
 * border-white/10) defined in index.css.  All Dashboard-level card surfaces
 * should use this component so visual updates propagate from one place.
 *
 * Spec: docs/specs/smart-stock-cache.md — AC#5 "Common UI patterns extracted
 * to src/components/ui/"
 */
const GlassCard: React.FC<GlassCardProps> = ({
    children,
    className = '',
    static: isStatic = false,
    onClick,
}) => {
    return (
        <div
            className={`glass-card ${isStatic ? '[transform:none!important]' : ''} ${className}`.trim()}
            onClick={onClick}
            role={onClick ? 'button' : undefined}
            tabIndex={onClick ? 0 : undefined}
        >
            {children}
        </div>
    )
}

export default GlassCard
