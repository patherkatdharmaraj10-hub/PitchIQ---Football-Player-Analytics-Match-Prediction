"""
api/main.py - PitchIQ FastAPI backend.
Usage: uvicorn api.main:app --reload --port 8000
Docs:  http://localhost:8000/docs
"""
import sys, os, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from db import run_query
from models.inference import model_status

app = FastAPI(
    title="PitchIQ API",
    version="1.0.0",
    description="Football Player Analytics and Match Prediction"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class MatchPredictRequest(BaseModel):
    home_team_id: int
    away_team_id: int
    home_xg: Optional[float] = 0
    away_xg: Optional[float] = 0
    home_possession: Optional[float] = 50
    away_possession: Optional[float] = 50


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0", "models": model_status()}


@app.get("/leagues")
def get_leagues():
    return run_query("SELECT * FROM leagues ORDER BY season DESC, name")


@app.get("/players")
def list_players(
    league_id: Optional[int] = None,
    position: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0
):
    where, params = ["1=1"], {}
    if league_id:
        where.append("l.id = :league_id")
        params["league_id"] = league_id
    if position:
        where.append("p.position ILIKE :pos")
        params["pos"] = f"%{position}%"
    params["limit"] = limit
    params["offset"] = offset
    return run_query(f"""
        SELECT DISTINCT p.id, p.name, p.position,
               p.nationality, t.name AS team_name, l.season
        FROM players p
        JOIN teams   t ON t.id = p.team_id
        JOIN leagues l ON l.id = t.league_id
        WHERE {' AND '.join(where)}
        ORDER BY p.name
        LIMIT :limit OFFSET :offset
    """, params)


@app.get("/players/{player_id}")
def get_player(player_id: int):
    rows = run_query("""
        SELECT p.*, t.name AS team_name
        FROM players p
        LEFT JOIN teams t ON t.id = p.team_id
        WHERE p.id = :id
    """, {"id": player_id})
    if not rows:
        raise HTTPException(404, "Player not found")
    return rows[0]


@app.get("/players/{player_id}/stats")
def player_stats(player_id: int):
    return run_query("""
        SELECT pms.*, m.match_date,
               ht.name AS home_team,
               at_.name AS away_team,
               l.season
        FROM player_match_stats pms
        JOIN matches m   ON m.id   = pms.match_id
        JOIN teams   ht  ON ht.id  = m.home_team_id
        JOIN teams   at_ ON at_.id = m.away_team_id
        JOIN leagues l   ON l.id   = m.league_id
        WHERE pms.player_id = :id
        ORDER BY m.match_date DESC
    """, {"id": player_id})


@app.get("/players/{player_id}/season-summary")
def player_season_summary(player_id: int):
    rows = run_query("""
        SELECT * FROM v_player_season_stats
        WHERE player_id = :id
        ORDER BY season DESC
    """, {"id": player_id})
    if not rows:
        raise HTTPException(404, "No stats found")
    return rows


@app.get("/teams")
def list_teams(league_id: Optional[int] = None):
    where, params = ["1=1"], {}
    if league_id:
        where.append("t.league_id = :league_id")
        params["league_id"] = league_id
    return run_query(f"""
        SELECT t.*, l.name AS league_name, l.season
        FROM teams t
        JOIN leagues l ON l.id = t.league_id
        WHERE {' AND '.join(where)}
        ORDER BY t.name
    """, params)


@app.get("/teams/{team_id}/form")
def team_form(team_id: int):
    rows = run_query(
        "SELECT * FROM v_team_form WHERE team_id = :id",
        {"id": team_id}
    )
    if not rows:
        raise HTTPException(404, "Team not found or no finished matches")
    return rows[0]


@app.get("/matches")
def list_matches(
    league_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(20, le=100),
    offset: int = 0
):
    where, params = ["1=1"], {}
    if league_id:
        where.append("m.league_id = :league_id")
        params["league_id"] = league_id
    if status:
        where.append("m.status = :status")
        params["status"] = status
    params["limit"] = limit
    params["offset"] = offset
    return run_query(f"""
        SELECT m.*,
               ht.name  AS home_team_name,
               at_.name AS away_team_name,
               l.name   AS league_name,
               l.season
        FROM matches m
        JOIN teams   ht  ON ht.id  = m.home_team_id
        JOIN teams   at_ ON at_.id = m.away_team_id
        JOIN leagues l   ON l.id   = m.league_id
        WHERE {' AND '.join(where)}
        ORDER BY m.match_date DESC
        LIMIT :limit OFFSET :offset
    """, params)


@app.get("/matches/{match_id}")
def get_match(match_id: int):
    rows = run_query("""
        SELECT m.*,
               ht.name  AS home_team_name,
               at_.name AS away_team_name,
               l.name   AS league_name, l.season
        FROM matches m
        JOIN teams   ht  ON ht.id  = m.home_team_id
        JOIN teams   at_ ON at_.id = m.away_team_id
        JOIN leagues l   ON l.id   = m.league_id
        WHERE m.id = :id
    """, {"id": match_id})
    if not rows:
        raise HTTPException(404, "Match not found")
    match = rows[0]
    match["player_stats"] = run_query("""
        SELECT pms.*, p.name AS player_name, p.position
        FROM player_match_stats pms
        JOIN players p ON p.id = pms.player_id
        WHERE pms.match_id = :id
        ORDER BY pms.goals DESC
    """, {"id": match_id})
    return match


@app.get("/standings/{league_id}")
def get_standings(league_id: int):
    return run_query("""
        WITH r AS (
            SELECT tms.team_id,
                COUNT(*) AS played,
                SUM(CASE
                    WHEN (tms.is_home AND m.home_goals>m.away_goals) OR
                         (NOT tms.is_home AND m.away_goals>m.home_goals)
                    THEN 1 ELSE 0 END) AS won,
                SUM(CASE WHEN m.home_goals=m.away_goals
                    THEN 1 ELSE 0 END) AS drawn,
                SUM(CASE
                    WHEN (tms.is_home AND m.home_goals<m.away_goals) OR
                         (NOT tms.is_home AND m.away_goals<m.home_goals)
                    THEN 1 ELSE 0 END) AS lost,
                SUM(CASE WHEN tms.is_home
                    THEN m.home_goals ELSE m.away_goals END) AS gf,
                SUM(CASE WHEN tms.is_home
                    THEN m.away_goals ELSE m.home_goals END) AS ga
            FROM team_match_stats tms
            JOIN matches m ON m.id = tms.match_id
            JOIN leagues l ON l.id = m.league_id
            WHERE m.status='finished' AND l.id = :league_id
            GROUP BY tms.team_id
        )
        SELECT t.name AS team,
               r.played, r.won, r.drawn, r.lost,
               r.gf, r.ga, (r.gf-r.ga) AS gd,
               (r.won*3+r.drawn) AS points
        FROM r JOIN teams t ON t.id = r.team_id
        ORDER BY points DESC, gd DESC
    """, {"league_id": league_id})


@app.get("/top-scorers")
def top_scorers(
    league_id: Optional[int] = None,
    limit: int = Query(10, le=50)
):
    where, params = ["1=1"], {}
    if league_id:
        where.append("l.id = :league_id")
        params["league_id"] = league_id
    params["limit"] = limit
    return run_query(f"""
        SELECT p.name AS player_name, p.position,
               t.name AS team_name,
               SUM(pms.goals)   AS goals,
               SUM(pms.assists) AS assists,
               ROUND(SUM(pms.xg)::numeric, 2) AS xg,
               COUNT(*) AS matches
        FROM player_match_stats pms
        JOIN players p ON p.id = pms.player_id
        JOIN teams   t ON t.id = pms.team_id
        JOIN matches m ON m.id = pms.match_id
        JOIN leagues l ON l.id = m.league_id
        WHERE {' AND '.join(where)}
        GROUP BY p.id, p.name, p.position, t.name
        ORDER BY goals DESC, xg DESC
        LIMIT :limit
    """, params)


@app.post("/predict/match")
def predict_match(req: MatchPredictRequest):
    try:
        from models.inference import predict_match_outcome
        home_form = run_query(
            "SELECT * FROM v_team_form WHERE team_id = :id",
            {"id": req.home_team_id}
        )
        away_form = run_query(
            "SELECT * FROM v_team_form WHERE team_id = :id",
            {"id": req.away_team_id}
        )
        hf = home_form[0] if home_form else {}
        af = away_form[0] if away_form else {}
        result = predict_match_outcome({
            "home_xg":          req.home_xg or 0,
            "away_xg":          req.away_xg or 0,
            "home_possession":  req.home_possession or 50,
            "away_possession":  req.away_possession or 50,
            "home_wins_l5":     hf.get("wins_l5", 0),
            "home_form":        hf.get("form_score", 0.5),
            "away_wins_l5":     af.get("wins_l5", 0),
            "away_form":        af.get("form_score", 0.5),
            "xg_diff":          (req.home_xg or 0) - (req.away_xg or 0),
            "home_shots_on_target": 0,
            "away_shots_on_target": 0,
        })
        return {
            "home_team_id":     req.home_team_id,
            "away_team_id":     req.away_team_id,
            "probabilities":    {k: v for k, v in result.items()
                                 if k != "predicted"},
            "predicted_outcome": result["predicted"],
        }
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))
    except Exception:
        raise HTTPException(500, f"Prediction error: {traceback.format_exc()}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=True
    )
