import argparse, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqlalchemy import text
from statsbombpy import sb
from db import engine
import pandas as pd

def get_or_create(conn, table, where_params, insert_params={}):
    where_sql = " AND ".join(f"{k}=:{k}" for k in where_params)
    row = conn.execute(text(f"SELECT id FROM {table} WHERE {where_sql}"),
                       where_params).fetchone()
    if row:
        return row[0]
    all_params = {**where_params, **insert_params}
    cols = ", ".join(all_params.keys())
    vals = ", ".join(f":{k}" for k in all_params.keys())
    r = conn.execute(
        text(f"INSERT INTO {table} ({cols}) VALUES ({vals}) RETURNING id"),
        all_params)
    return r.fetchone()[0]

def safe_str(val):
    if val is None: return None
    try:
        if pd.isna(val): return None
    except Exception: pass
    return str(val).strip() if isinstance(val, str) else None

def safe_float(val, default=0.0):
    try:
        f = float(val)
        return 0.0 if pd.isna(f) else f
    except Exception:
        return default

def get_outcome_name(val):
    """Safely extract outcome name from StatsBomb dict or string."""
    if val is None: return ""
    if isinstance(val, dict): return val.get("name", "")
    try:
        if pd.isna(val): return ""
    except Exception: pass
    return str(val)

def process_events(conn, sb_match_id, db_match_id, league_id):
    try:
        events = sb.events(match_id=sb_match_id)
    except Exception as e:
        print(f"    Warning: {e}")
        return

    player_stats = {}

    def get_ps(player_name, team_name):
        key = f"{player_name}|{team_name}"
        if key not in player_stats:
            team_id = get_or_create(conn, "teams",
                {"name": team_name, "league_id": league_id})
            player_id = get_or_create(conn, "players",
                {"name": player_name, "team_id": team_id})
            player_stats[key] = dict(
                player_id=player_id, team_id=team_id,
                match_id=db_match_id,
                minutes_played=0, goals=0, assists=0,
                xg=0.0, xa=0.0, shots=0, shots_on_target=0,
                passes=0, pass_accuracy=None, key_passes=0,
                dribbles=0, tackles=0, interceptions=0,
                fouls=0, yellow_cards=0, red_cards=0,
                _pass_total=0, _pass_success=0,
            )
        return player_stats[key]

    for _, ev in events.iterrows():
        pname = safe_str(ev.get("player"))
        tname = safe_str(ev.get("team"))
        if not pname or not tname:
            continue

        p   = get_ps(pname, tname)
        etype = safe_str(ev.get("type")) or ""

        if etype == "Shot":
            p["shots"] += 1
            oname = get_outcome_name(ev.get("shot_outcome"))
            # StatsBomb goal detection — outcome name is exactly "Goal"
            if oname == "Goal":
                p["goals"] += 1
            if oname in ("Goal", "Saved", "Saved To Post"):
                p["shots_on_target"] += 1
            p["xg"] += safe_float(ev.get("shot_statsbomb_xg"))

        elif etype == "Pass":
            p["passes"]      += 1
            p["_pass_total"] += 1
            oname = get_outcome_name(ev.get("pass_outcome"))
            # Successful pass = no outcome recorded (outcome only set on failure)
            if oname == "":
                p["_pass_success"] += 1
            # Goal assist — must be exactly True boolean
            if ev.get("pass_goal_assist") is True:
                p["assists"] += 1
            # Key pass — shot assist
            if ev.get("pass_shot_assist") is True:
                p["key_passes"] += 1
            p["xa"] += safe_float(ev.get("pass_xa"))

        elif etype == "Dribble":
            p["dribbles"] += 1
        elif etype == "Pressure":
            pass
        elif etype == "Tackle":
            p["tackles"] += 1
        elif etype == "Interception":
            p["interceptions"] += 1
        elif etype == "Foul Committed":
            p["fouls"] += 1
        elif etype == "Bad Behaviour":
            card = get_outcome_name(ev.get("bad_behaviour_card"))
            if "Yellow" in card:
                p["yellow_cards"] += 1
            elif "Red" in card:
                p["red_cards"] += 1

    for p in player_stats.values():
        if p["_pass_total"] > 0:
            p["pass_accuracy"] = round(
                p["_pass_success"] / p["_pass_total"] * 100, 1)
        del p["_pass_total"]
        del p["_pass_success"]
        conn.execute(text("""
            INSERT INTO player_match_stats
              (player_id,match_id,team_id,minutes_played,goals,assists,
               xg,xa,shots,shots_on_target,passes,pass_accuracy,
               key_passes,dribbles,tackles,interceptions,
               fouls,yellow_cards,red_cards)
            VALUES
              (:player_id,:match_id,:team_id,:minutes_played,:goals,:assists,
               :xg,:xa,:shots,:shots_on_target,:passes,:pass_accuracy,
               :key_passes,:dribbles,:tackles,:interceptions,
               :fouls,:yellow_cards,:red_cards)
            ON CONFLICT (player_id, match_id) DO NOTHING
        """), p)

def load(competition_id, season_id):
    comps = sb.competitions()
    row = comps[
        (comps["competition_id"] == competition_id) &
        (comps["season_id"]      == season_id)
    ]
    if row.empty:
        print("Competition not found.")
        return
    comp_name    = row.iloc[0]["competition_name"]
    country_name = row.iloc[0]["country_name"]
    season_name  = row.iloc[0]["season_name"]
    print(f"Loading: {comp_name} - {season_name}")
    matches = sb.matches(competition_id=competition_id, season_id=season_id)
    print(f"Found {len(matches)} matches.")
    with engine.begin() as conn:
        league_id = get_or_create(
            conn, "leagues",
            {"name": comp_name, "season": season_name},
            {"country": country_name}
        )
        for i, (_, match) in enumerate(matches.iterrows(), 1):
            home_id = get_or_create(conn, "teams",
                {"name": match["home_team"], "league_id": league_id})
            away_id = get_or_create(conn, "teams",
                {"name": match["away_team"], "league_id": league_id})
            existing = conn.execute(text("""
                SELECT id FROM matches
                WHERE league_id=:l AND home_team_id=:h
                  AND away_team_id=:a AND match_date=:d
            """), {"l": league_id, "h": home_id,
                   "a": away_id,   "d": match["match_date"]}).fetchone()
            if existing:
                db_match_id = existing[0]
            else:
                r = conn.execute(text("""
                    INSERT INTO matches
                      (league_id,home_team_id,away_team_id,match_date,
                       home_goals,away_goals,status,matchweek)
                    VALUES (:l,:h,:a,:d,:hg,:ag,'finished',:mw)
                    RETURNING id
                """), {
                    "l":  league_id,
                    "h":  home_id,
                    "a":  away_id,
                    "d":  match["match_date"],
                    "hg": int(match.get("home_score", 0)),
                    "ag": int(match.get("away_score", 0)),
                    "mw": match.get("match_week"),
                })
                db_match_id = r.fetchone()[0]
            print(f"  [{i}/{len(matches)}] "
                  f"{match['home_team']} vs {match['away_team']}",
                  end=" ... ")
            process_events(conn, int(match["match_id"]),
                           db_match_id, league_id)
            print("done")
    print(f"Finished loading {len(matches)} matches.")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--competition", type=int, default=53)
    p.add_argument("--season",      type=int, default=106)
    args = p.parse_args()
    load(args.competition, args.season)
