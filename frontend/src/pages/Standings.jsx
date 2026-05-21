import { useEffect, useState } from 'react'
import api from '../api/client'

export default function Standings() {
  const [leagues,   setLeagues]   = useState([])
  const [standings, setStandings] = useState([])
  const [leagueId,  setLeagueId]  = useState(null)
  const [loading,   setLoading]   = useState(true)

  useEffect(() => {
    api.get('/leagues').then(r => {
      setLeagues(r.data)
      if (r.data.length > 0) setLeagueId(r.data[0].id)
    })
  }, [])

  useEffect(() => {
    if (!leagueId) return
    setLoading(true)
    api.get(`/standings/${leagueId}`)
      .then(r => { setStandings(r.data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [leagueId])

  return (
    <div>
      <h1 className="text-3xl font-bold mb-1">Standings</h1>
      <p className="text-gray-400 mb-6">League table</p>

      <select
        className="bg-gray-800 border border-gray-700 rounded-lg
                   px-3 py-2 text-white mb-6"
        value={leagueId || ''}
        onChange={e => setLeagueId(parseInt(e.target.value))}
      >
        {leagues.map(l => (
          <option key={l.id} value={l.id}>
            {l.name} — {l.season}
          </option>
        ))}
      </select>

      {loading ? (
        <p className="text-gray-400 animate-pulse">Loading...</p>
      ) : standings.length === 0 ? (
        <div className="bg-gray-800 rounded-xl p-6">
          <p className="text-gray-400">
            No standings data available yet.
            Team match stats need to be loaded first.
          </p>
        </div>
      ) : (
        <div className="bg-gray-800 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-700
                             bg-gray-900 text-left">
                <th className="px-4 py-3">#</th>
                <th className="px-4 py-3">Team</th>
                <th className="text-center px-3 py-3">P</th>
                <th className="text-center px-3 py-3 text-green-400">W</th>
                <th className="text-center px-3 py-3 text-yellow-400">D</th>
                <th className="text-center px-3 py-3 text-red-400">L</th>
                <th className="text-center px-3 py-3">GF</th>
                <th className="text-center px-3 py-3">GA</th>
                <th className="text-center px-3 py-3">GD</th>
                <th className="text-center px-3 py-3 text-green-400">
                  PTS
                </th>
              </tr>
            </thead>
            <tbody>
              {standings.map((s, i) => (
                <tr key={i}
                    className="border-b border-gray-700 hover:bg-gray-700
                               transition">
                  <td className="px-4 py-3 text-gray-500">{i + 1}</td>
                  <td className="px-4 py-3 font-medium">{s.team}</td>
                  <td className="text-center px-3 py-3">{s.played}</td>
                  <td className="text-center px-3 py-3 text-green-400">
                    {s.won}
                  </td>
                  <td className="text-center px-3 py-3 text-yellow-400">
                    {s.drawn}
                  </td>
                  <td className="text-center px-3 py-3 text-red-400">
                    {s.lost}
                  </td>
                  <td className="text-center px-3 py-3">{s.gf}</td>
                  <td className="text-center px-3 py-3">{s.ga}</td>
                  <td className="text-center px-3 py-3">{s.gd}</td>
                  <td className="text-center px-3 py-3 font-bold
                                 text-green-400">{s.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
