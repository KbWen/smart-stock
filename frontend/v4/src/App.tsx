import { Suspense, lazy } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import GlobalLayout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Backtest = lazy(() => import('./pages/Backtest'))
const MarketRisk = lazy(() => import('./pages/MarketRisk'))
const Indicators = lazy(() => import('./pages/Indicators'))

function PageFallback() {
    return <div className="p-6 text-dark-muted">Loading page...</div>
}

function App() {
    return (
        <BrowserRouter>
            <GlobalLayout>
                <ErrorBoundary>
                <Suspense fallback={<PageFallback />}>
                    <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/backtest" element={<Backtest />} />
                        <Route path="/risk" element={<MarketRisk />} />
                        <Route path="/indicators" element={<Indicators />} />
                    </Routes>
                </Suspense>
                </ErrorBoundary>
            </GlobalLayout>
        </BrowserRouter>
    )
}

export default App
