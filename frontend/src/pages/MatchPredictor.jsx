import { useEffect, useState } from 'react'
import api from '../api/client'

export default function MatchPredictor() {
  const [teams,    setTeams]    = useState([])
  const [homeTeam, setHomeTeam] = useState('')
  const [awayTeam, setAwayTeam] = useState('')
  const [result,   setResult]   = useState(null)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState(null)

  useEffect(() => {
    api.get('/teams').then(r => setTeams(r.data))
  }, [])

  const predict = async () => {
    if (!homeTeam || !awayTeam) return
    if (homeTeam === awayTeam) {
      setError('Home and away teams must be different')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const r = await api.post('/predict/match', {
        home_team_id: parseInt(homeTeam),
        away_team_id: parseInt(awayTeam),
      })
      setResult(r.data)
    } catch {
      setError('Prediction failed. Make sure the model is trained.')
    }
    setLoading(false)
  }

  const homeName = teams.find(t => t.id === parseInt(homeTeam))?.name || ''
  const awayName = teams.find(t => t.id === parseInt(awayTeam))?.name || ''

  const colors = {
    home_win: 'bg-green-500',
    draw:     'bg-yellow-500',
    away_win: 'bg-blue-500',
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-1">Match Predictor</h1>
      <p className="text-gray-400 mb-8">
        Predict match outcome using AI
      </p>

      <div className="bg-gray-800 rounded-xl p-6 mb-6 max-w-md">
        <div className="mb-4">
          <label className="text-gray-400 text-sm block mb-1">
            Home Team
          </label>
          <select
            className="w-full bg-gray-900 border border-gray-700
                       rounded-lg px-3 py-2 text-white"
            value={homeTeam}
            onChange={e => setHomeTeam(e.target.value)}
          >
            <option value="">Select home team</option>
            {teams.map(t => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </div>

        <div className="mb-6">
          <label className="text-gray-400 text-sm block mb-1">
            Away Team
          </label>
          <select
            className="w-full bg-gray-900 border border-gray-700
                       rounded-lg px-3 py-2 text-white"
            value={awayTeam}
            onChange={e => setAwayTeam(e.target.value)}
          >
            <option value="">Select away team</option>
            {teams.map(t => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </div>

        {error && (
          <p className="text-red-400 text-sm mb-4">{error}</p>
        )}

        <button
          onClick={predict}
          disabled={loading || !homeTeam || !awayTeam}
          className="w-full bg-green-500 hover:bg-green-600
                     disabled:bg-gray-600 disabled:cursor-not-allowed
                     text-white font-bold py-3 rounded-lg transition"
        >
          {loading ? 'Predicting...' : 'Predict Match ⚡'}
        </button>
      </div>

      {result && (
        <div className="bg-gray-800 rounded-xl p-6 max-w-md">
          <h2 className="text-xl font-bold mb-1">
            {homeName} vs {awayName}
          </h2>
          <p className="text-gray-400 text-sm mb-6">
            Predicted:
            <span className="text-green-400 font-bold ml-2 uppercase">
              {result.predicted_outcome.replace(/_/g, ' ')}
            </span>
          </p>
          <div className="space-y-4">
            {Object.entries(result.probabilities).map(([key, val]) => (
              <div key={key}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-300 capitalize">
                    {key.replace(/_/g, ' ')}
                  </span>
                  <span className="font-bold">
                    {(val * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-4">
                  <div
                    className={`${colors[key] || 'bg-green-500'}
                                h-4 rounded-full transition-all duration-500`}
                    style={{ width: `${(val * 100).toFixed(1)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
