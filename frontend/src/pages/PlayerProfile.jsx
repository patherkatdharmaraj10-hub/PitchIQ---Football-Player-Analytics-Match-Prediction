import { useEffect, useState } from 'react'
import api from '../api/client'

export default function PlayerProfile() {
  const [players, setPlayers] = useState([])
  const [search,  setSearch]  = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/players?limit=200').then(r => {
      setPlayers(r.data)
      setLoading(false)
    })
  }, [])

  const filtered = players.filter(p => {
    const name = (p.player_name || p.name || '').toLowerCase()
    const team = (p.team_name || '').toLowerCase()
    const q    = search.toLowerCase()
    return name.includes(q) || team.includes(q)
  })

  return (
    <div>
      <h1 className="text-3xl font-bold mb-1">Players</h1>
      <p className="text-gray-400 mb-6">
        Browse all {players.length} players in the database
      </p>

      <input
        type="text"
        placeholder="Search by name or team..."
        className="w-full max-w-sm bg-gray-800 border border-gray-700
                   rounded-lg px-4 py-2 text-white mb-6 outline-none
                   focus:border-green-500"
        value={search}
        onChange={e => setSearch(e.target.value)}
      />

      {loading ? (
        <p className="text-gray-400 animate-pulse">Loading players...</p>
      ) : (
        <div className="bg-gray-800 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-700
                             bg-gray-900 text-left">
                <th className="px-4 py-3">#</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Team</th>
                <th className="px-4 py-3">Position</th>
                <th className="px-4 py-3">Nationality</th>
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 100).map((p, i) => (
                <tr key={i}
                    className="border-b border-gray-700 hover:bg-gray-700
                               transition">
                  <td className="px-4 py-3 text-gray-500">{i + 1}</td>
                  <td className="px-4 py-3 font-medium">
                    {p.player_name || p.name}
                  </td>
                  <td className="px-4 py-3 text-gray-400">{p.team_name}</td>
                  <td className="px-4 py-3 text-gray-400">
                    {p.position || '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {p.nationality || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-gray-500 text-xs px-4 py-3">
            Showing {Math.min(100, filtered.length)} of {filtered.length} players
          </p>
        </div>
      )}
    </div>
  )
}
