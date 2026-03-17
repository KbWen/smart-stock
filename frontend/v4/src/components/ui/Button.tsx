import React from 'react'

type Variant = 'primary' | 'ghost' | 'warning' | 'danger'
type Size = 'sm' | 'md'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: Variant
    size?: Size
    loading?: boolean
    leftIcon?: React.ReactNode
}

const VARIANT_CLASSES: Record<Variant, string> = {
    primary:
        'border border-sniper-green/30 bg-sniper-green/10 text-sniper-green hover:bg-sniper-green/20 focus-visible:ring-sniper-green/40',
    ghost:
        'border border-dark-border bg-transparent text-dark-muted hover:bg-dark-border/30 focus-visible:ring-dark-border',
    warning:
        'border border-yellow-500/30 bg-yellow-500/10 text-yellow-400 hover:bg-yellow-500/20 focus-visible:ring-yellow-500/40',
    danger:
        'border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 focus-visible:ring-red-500/40',
}

const SIZE_CLASSES: Record<Size, string> = {
    sm: 'px-2 py-1 text-xs gap-1',
    md: 'px-3 py-1.5 text-sm gap-1.5',
}

/**
 * Button — standard action button with variant theming.
 *
 * Centralises all interactive button styling so visual and a11y updates
 * propagate from one location.
 *
 * Spec: docs/specs/smart-stock-cache.md — AC#5 "Common UI patterns extracted
 * to src/components/ui/"
 */
const Button: React.FC<ButtonProps> = ({
    variant = 'ghost',
    size = 'sm',
    loading = false,
    leftIcon,
    children,
    className = '',
    disabled,
    ...rest
}) => {
    const isDisabled = disabled || loading

    return (
        <button
            type="button"
            disabled={isDisabled}
            className={[
                'inline-flex items-center rounded transition-colors',
                'focus-visible:outline-none focus-visible:ring-2',
                'disabled:pointer-events-none disabled:opacity-50',
                VARIANT_CLASSES[variant],
                SIZE_CLASSES[size],
                className,
            ].join(' ')}
            {...rest}
        >
            {loading ? (
                <span className="h-3 w-3 animate-spin rounded-full border border-current border-t-transparent" />
            ) : (
                leftIcon
            )}
            {children}
        </button>
    )
}

export default Button
