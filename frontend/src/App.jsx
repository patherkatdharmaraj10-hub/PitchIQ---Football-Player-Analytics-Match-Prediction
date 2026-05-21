import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Players from './pages/PlayerProfile'
import MatchPredictor from './pages/MatchPredictor'
import Standings from './pages/Standings'

function Navbar() {
  const location = useLocation()
  const links = [
    { to: '/',          label: 'Dashboard' },
    { to: '/players',   label: 'Players'   },
    { to: '/matches',   label: 'Predictor' },
    { to: '/standings', label: 'Standings' },
  ]
  return (
    <nav className="bg-gray-900 border-b border-gray-800 px-6 py-4
                    flex items-center gap-8">
      <span className="text-xl font-bold text-green-400">⚽ PitchIQ</span>
      {links.map(l => (
        <Link
          key={l.to}
          to={l.to}
          className={`text-sm transition ${
            location.pathname === l.to
              ? 'text-green-400 font-semibold'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          {l.label}
        </Link>
      ))}
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-white">
        <Navbar />
        <div className="max-w-7xl mx-auto px-6 py-8">
          <Routes>
            <Route path="/"          element={<Dashboard />}      />
            <Route path="/players"   element={<Players />}        />
            <Route path="/matches"   element={<MatchPredictor />} />
            <Route path="/standings" element={<Standings />}      />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}
