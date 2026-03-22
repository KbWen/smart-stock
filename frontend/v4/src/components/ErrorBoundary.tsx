import React from 'react'

interface Props {
    children: React.ReactNode
    fallback?: React.ReactNode
}

interface State {
    hasError: boolean
    error: Error | null
}

class ErrorBoundary extends React.Component<Props, State> {
    constructor(props: Props) {
        super(props)
        this.state = { hasError: false, error: null }
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error }
    }

    componentDidCatch(error: Error, info: React.ErrorInfo): void {
        console.error('[ErrorBoundary] Caught render error:', error, info.componentStack)
    }

    reset = () => {
        this.setState({ hasError: false, error: null })
    }

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) return this.props.fallback
            return (
                <div className="rounded-xl border border-red-500/40 bg-red-900/20 p-6 text-red-300">
                    <p className="mb-2 font-semibold">Something went wrong rendering this component.</p>
                    <p className="mb-4 font-mono text-xs text-red-400/70">{this.state.error?.message}</p>
                    <button
                        type="button"
                        onClick={this.reset}
                        className="rounded bg-red-500/20 px-3 py-1 text-sm text-red-300 hover:bg-red-500/30"
                    >
                        Retry
                    </button>
                </div>
            )
        }
        return this.props.children
    }
}

export default ErrorBoundary
