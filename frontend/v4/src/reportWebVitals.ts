/**
 * Collect lightweight performance metrics using PerformanceObserver.
 */
export function initWebVitals(): void {
    if (typeof window === 'undefined' || !('PerformanceObserver' in window)) {
        return
    }

    const metricTypes: string[] = ['paint', 'largest-contentful-paint', 'navigation']

    metricTypes.forEach((type) => {
        try {
            const observer = new PerformanceObserver((entryList) => {
                entryList.getEntries().forEach((entry) => {
                    if (import.meta.env.DEV) {
                        console.info('[perf]', type, entry.name, Math.round(entry.startTime))
                    }
                })
            })
            observer.observe({ type, buffered: true })
        } catch (error) {
            if (import.meta.env.DEV) {
                console.debug('Performance observer unsupported:', type, error)
            }
        }
    })
}
