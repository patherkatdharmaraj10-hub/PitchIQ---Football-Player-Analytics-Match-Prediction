import { useEffect, useState } from 'react'
import api from '../api/client'

function StatCard({ label, value, color }) {
  return (
    <div className="bg-gray-800 rounded-xl p-5">
      <p className="text-gray-400 text-sm mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
    </div>
  )
}

export default function Dashboard() {
  const [scorers, setScorers] = useState([])
  const [matches, setMatches] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get('/top-scorers?limit=10'),
      api.get('/matches?limit=8'),
    ]).then(([s, m]) => {
      setScorers(s.data)
      setMatches(m.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <p className="text-gray-400 text-lg animate-pulse">Loading...</p>
    </div>
  )

  const totalGoals = scorers.reduce((a, b) => a + b.goals, 0)

  return (
    <div>
      <h1 className="text-3xl font-bold mb-1">Dashboard</h1>
      <p className="text-gray-400 mb-8">
        Football Player Analytics & Match Prediction
      </p>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <StatCard label="Top Scorers"   value={scorers.length} color="text-green-400" />
        <StatCard label="Total Goals"   value={totalGoals}     color="text-yellow-400" />
        <StatCard label="Matches"       value={matches.length} color="text-blue-400" />
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-bold mb-4">Top Scorers</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-700">
                <th className="text-left py-2">#</th>
                <th className="text-left py-2">Player</th>
                <th className="text-center py-2">G</th>
                <th className="text-center py-2">A</th>
                <th className="text-center py-2">xG</th>
              </tr>
            </thead>
            <tbody>
              {scorers.map((p, i) => (
                <tr key={i}
                    className="border-b border-gray-700 hover:bg-gray-750">
                  <td className="py-2 text-gray-500">{i+1}</td>
                  <td className="py-2">
                    <div className="font-medium">{p.player_name}</div>
                    <div className="text-xs text-gray-500">{p.team_name}</div>
                  </td>
                  <td className="py-2 text-center text-green-400 font-bold">
                    {p.goals}
                  </td>
                  <td className="py-2 text-center text-blue-400">{p.assists}</td>
                  <td className="py-2 text-center text-yellow-400">{p.xg}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="bg-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-bold mb-4">Recent Matches</h2>
          <div className="space-y-2">
            {matches.map((m, i) => (
              <div key={i}
                   className="bg-gray-900 rounded-lg px-4 py-3
                              flex items-center justify-between">
                <span className="text-sm text-right w-2/5 truncate">
                  {m.home_team_name}
                </span>
                <span className="text-green-400 font-bold px-3 text-lg">
                  {m.home_goals} - {m.away_goals}
                </span>
                <span className="text-sm w-2/5 truncate">
                  {m.away_team_name}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
