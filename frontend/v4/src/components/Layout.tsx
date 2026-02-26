import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, LineChart, Activity, Scan, Settings, Menu, X } from 'lucide-react'

interface LayoutProps {
    children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
    const location = useLocation()
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
    const appVersion = import.meta.env.VITE_APP_VERSION || '2026.02.14'

    const navItems = [
        { path: '/', label: 'Dashboard', icon: LayoutDashboard },
        { path: '/backtest', label: 'AI Backtest', icon: LineChart },
        { path: '/risk', label: 'Market Risk', icon: Activity },
        { path: '/indicators', label: 'Scanner', icon: Scan },
    ]

    return (
        <div className="min-h-screen bg-dark-bg text-dark-text font-sans selection:bg-sniper-green selection:text-white flex">
            {/* Mobile Top Navbar */}
            <div className="md:hidden fixed top-0 inset-x-0 h-16 bg-dark-card border-b border-dark-border flex items-center justify-between px-4 z-40">
                <div className="flex items-center">
                    <span className="text-2xl mr-2">🎯</span>
                    <h1 className="text-lg font-bold tracking-tight text-white">
                        Smart Stock
                    </h1>
                </div>
                <button
                    onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                    className="p-2 text-dark-muted hover:text-white focus:outline-none"
                    aria-label="Toggle Menu"
                >
                    {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
                </button>
            </div>

            {/* Mobile Overlay */}
            {isMobileMenuOpen && (
                <div
                    className="fixed inset-0 bg-black/50 z-40 md:hidden"
                    onClick={() => setIsMobileMenuOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside className={`fixed inset-y-0 left-0 bg-dark-card border-r border-dark-border flex flex-col z-50 w-64 transform transition-transform duration-200 ease-in-out md:translate-x-0 ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}`}>
                <div className="h-16 flex items-center px-6 border-b border-dark-border justify-between md:justify-start">
                    <div className="flex items-center">
                        <span className="text-2xl mr-2">🎯</span>
                        <h1 className="text-lg font-bold tracking-tight text-white">
                            Smart Stock
                        </h1>
                    </div>
                    <button
                        className="md:hidden text-dark-muted hover:text-white"
                        onClick={() => setIsMobileMenuOpen(false)}
                    >
                        <X size={20} />
                    </button>
                </div>

                <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
                    {navItems.map((item) => {
                        const isActive = location.pathname === item.path
                        const Icon = item.icon
                        return (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${isActive
                                    ? 'bg-sniper-green/10 text-sniper-green'
                                    : 'text-dark-muted hover:bg-dark-border/50 hover:text-white'
                                    }`}
                                onClick={() => setIsMobileMenuOpen(false)}
                            >
                                <Icon size={18} />
                                {item.label}
                            </Link>
                        )
                    })}
                </nav>

                <div className="p-4 border-t border-dark-border">
                    <div className="flex items-center gap-3 px-4 py-3 text-dark-muted text-xs">
                        <Settings size={16} />
                        <span>Build: {appVersion}</span>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 w-full md:ml-64 p-4 pt-20 md:p-8 md:pt-8 min-h-screen">
                <div className="max-w-7xl mx-auto">
                    {children}
                </div>
            </main>
        </div>
    )
}

export default Layout
