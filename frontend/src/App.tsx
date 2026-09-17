import { HashRouter, Routes, Route, NavLink } from 'react-router-dom'
import SimulationPage from './pages/SimulationPage'
import ComparisonPage from './pages/ComparisonPage'
import ExperimentsPage from './pages/ExperimentsPage'
import AboutPage from './pages/AboutPage'

const tabs = [
  { to: '/', label: 'Simulation' },
  { to: '/compare', label: 'Comparison' },
  { to: '/experiments', label: 'Experiments' },
  { to: '/about', label: 'About the Algorithm' },
]

export default function App() {
  return (
    <HashRouter>
      <div className="min-h-screen flex flex-col">
        <header className="border-b hairline sticky top-0 bg-ink-950/95 backdrop-blur z-10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-8">
            <div>
              <div className="text-[15px] font-semibold tracking-tight">Adaptive Hybrid Disk Scheduler</div>
              <div className="text-[12px] text-slate-500 font-data">discrete-event simulator · mixed multimedia + database workloads</div>
            </div>
            <nav className="flex gap-1 sm:ml-auto flex-wrap">
              {tabs.map((t) => (
                <NavLink
                  key={t.to}
                  to={t.to}
                  end={t.to === '/'}
                  className={({ isActive }) =>
                    `px-3 py-1.5 text-[13px] border ${isActive ? 'border-amber-500 text-amber-400' : 'hairline text-slate-400 hover:text-slate-200'}`
                  }
                >
                  {t.label}
                </NavLink>
              ))}
            </nav>
          </div>
        </header>
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
          <Routes>
            <Route path="/" element={<SimulationPage />} />
            <Route path="/compare" element={<ComparisonPage />} />
            <Route path="/experiments" element={<ExperimentsPage />} />
            <Route path="/about" element={<AboutPage />} />
          </Routes>
        </main>
        <footer className="border-t hairline text-center text-[11px] text-slate-600 py-4 font-data">
          simulation only — no real hardware, no on-disk cache, no NCQ, no filesystem layer
        </footer>
      </div>
    </HashRouter>
  )
}
