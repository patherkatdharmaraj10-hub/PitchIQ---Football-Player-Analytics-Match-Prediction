
"""
scripts/create_schema.py - Create all tables, indexes, and views.
Run once before loading any data.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db import engine
from sqlalchemy import text

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS leagues (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    country     VARCHAR(100),
    season      VARCHAR(10) NOT NULL,
    UNIQUE (name, season)
);

CREATE TABLE IF NOT EXISTS teams (
    id          SERIAL PRIMARY KEY,
    league_id   INT REFERENCES leagues(id) ON DELETE CASCADE,
    name        VARCHAR(100) NOT NULL,
    short_name  VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS players (
    id            SERIAL PRIMARY KEY,
    team_id       INT REFERENCES teams(id) ON DELETE SET NULL,
    name          VARCHAR(150) NOT NULL,
    position      VARCHAR(30),
    date_of_birth DATE,
    nationality   VARCHAR(80),
    market_value  NUMERIC(12,2)
);

CREATE TABLE IF NOT EXISTS matches (
    id           SERIAL PRIMARY KEY,
    league_id    INT REFERENCES leagues(id),
    home_team_id INT REFERENCES teams(id),
    away_team_id INT REFERENCES teams(id),
    match_date   DATE NOT NULL,
    kickoff_time TIME,
    home_goals   INT DEFAULT 0,
    away_goals   INT DEFAULT 0,
    status       VARCHAR(20) DEFAULT 'scheduled',
    matchweek    INT,
    venue        VARCHAR(150)
);

CREATE TABLE IF NOT EXISTS player_match_stats (
    id              SERIAL PRIMARY KEY,
    player_id       INT REFERENCES players(id) ON DELETE CASCADE,
    match_id        INT REFERENCES matches(id) ON DELETE CASCADE,
    team_id         INT REFERENCES teams(id),
    minutes_played  INT DEFAULT 0,
    goals           INT DEFAULT 0,
    assists         INT DEFAULT 0,
    xg              NUMERIC(5,3) DEFAULT 0,
    xa              NUMERIC(5,3) DEFAULT 0,
    shots           INT DEFAULT 0,
    shots_on_target INT DEFAULT 0,
    passes          INT DEFAULT 0,
    pass_accuracy   NUMERIC(5,2),
    key_passes      INT DEFAULT 0,
    dribbles        INT DEFAULT 0,
    tackles         INT DEFAULT 0,
    interceptions   INT DEFAULT 0,
    fouls           INT DEFAULT 0,
    yellow_cards    INT DEFAULT 0,
    red_cards       INT DEFAULT 0,
    rating          NUMERIC(4,2),
    UNIQUE (player_id, match_id)
);

CREATE TABLE IF NOT EXISTS team_match_stats (
    id               SERIAL PRIMARY KEY,
    team_id          INT REFERENCES teams(id) ON DELETE CASCADE,
    match_id         INT REFERENCES matches(id) ON DELETE CASCADE,
    is_home          BOOLEAN NOT NULL,
    xg_for           NUMERIC(5,3),
    xg_against       NUMERIC(5,3),
    possession_pct   NUMERIC(5,2),
    shots            INT DEFAULT 0,
    shots_on_target  INT DEFAULT 0,
    corners          INT DEFAULT 0,
    offsides         INT DEFAULT 0,
    fouls_committed  INT DEFAULT 0,
    UNIQUE (team_id, match_id)
);

CREATE TABLE IF NOT EXISTS match_events (
    id          SERIAL PRIMARY KEY,
    match_id    INT REFERENCES matches(id) ON DELETE CASCADE,
    player_id   INT REFERENCES players(id) ON DELETE SET NULL,
    team_id     INT REFERENCES teams(id),
    event_type  VARCHAR(30) NOT NULL,
    minute      INT NOT NULL,
    detail      VARCHAR(200)
);

CREATE INDEX IF NOT EXISTS idx_pms_player     ON player_match_stats(player_id);
CREATE INDEX IF NOT EXISTS idx_pms_match      ON player_match_stats(match_id);
CREATE INDEX IF NOT EXISTS idx_matches_date   ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_league ON matches(league_id);
CREATE INDEX IF NOT EXISTS idx_events_match   ON match_events(match_id);

CREATE OR REPLACE VIEW v_player_season_stats AS
SELECT
    p.id AS player_id, p.name AS player_name, p.position,
    t.name AS team_name, l.season,
    COUNT(*) AS matches_played,
    SUM(pms.goals) AS goals,
    SUM(pms.assists) AS assists,
    ROUND(SUM(pms.xg)::numeric,2) AS xg_total,
    ROUND(SUM(pms.xa)::numeric,2) AS xa_total,
    SUM(pms.shots) AS shots,
    ROUND(AVG(pms.pass_accuracy)::numeric,1) AS avg_pass_accuracy,
    ROUND(AVG(pms.rating)::numeric,2) AS avg_rating,
    ROUND((SUM(pms.goals)::numeric/NULLIF(SUM(pms.minutes_played),0)*90),2) AS goals_p90,
    ROUND((SUM(pms.xg)::numeric/NULLIF(SUM(pms.minutes_played),0)*90),3) AS xg_p90
FROM player_match_stats pms
JOIN players p ON p.id=pms.player_id
JOIN teams   t ON t.id=pms.team_id
JOIN matches m ON m.id=pms.match_id
JOIN leagues l ON l.id=m.league_id
GROUP BY p.id, p.name, p.position, t.name, l.season;

CREATE OR REPLACE VIEW v_team_form AS
WITH recent AS (
    SELECT tms.team_id, m.match_date,
        CASE
            WHEN (tms.is_home AND m.home_goals>m.away_goals) OR
                 (NOT tms.is_home AND m.away_goals>m.home_goals) THEN 'W'
            WHEN m.home_goals=m.away_goals THEN 'D'
            ELSE 'L'
        END AS result,
        ROW_NUMBER() OVER (PARTITION BY tms.team_id ORDER BY m.match_date DESC) AS rn
    FROM team_match_stats tms
    JOIN matches m ON m.id=tms.match_id
    WHERE m.status='finished'
)
SELECT team_id,
    SUM(CASE WHEN result='W' THEN 1 ELSE 0 END) AS wins_l5,
    SUM(CASE WHEN result='D' THEN 1 ELSE 0 END) AS draws_l5,
    SUM(CASE WHEN result='L' THEN 1 ELSE 0 END) AS losses_l5,
    ROUND(AVG(CASE WHEN result='W' THEN 1.0
                   WHEN result='D' THEN 0.5
                   ELSE 0 END)::numeric,3) AS form_score
FROM recent WHERE rn<=5
GROUP BY team_id;

CREATE OR REPLACE VIEW v_match_features AS
SELECT
    m.id AS match_id, m.match_date,
    m.home_goals, m.away_goals,
    CASE WHEN m.home_goals>m.away_goals THEN 'H'
         WHEN m.home_goals<m.away_goals THEN 'A'
         ELSE 'D' END AS result,
    ht.xg_for AS home_xg, ht.possession_pct AS home_possession,
    ht.shots_on_target AS home_shots_on_target,
    at_.xg_for AS away_xg, at_.possession_pct AS away_possession,
    at_.shots_on_target AS away_shots_on_target,
    COALESCE(ht.xg_for,0)-COALESCE(at_.xg_for,0) AS xg_diff,
    hf.wins_l5 AS home_wins_l5, hf.form_score AS home_form,
    af.wins_l5 AS away_wins_l5, af.form_score AS away_form
FROM matches m
LEFT JOIN team_match_stats ht  ON ht.match_id=m.id AND ht.is_home=TRUE
LEFT JOIN team_match_stats at_ ON at_.match_id=m.id AND at_.is_home=FALSE
LEFT JOIN v_team_form hf ON hf.team_id=m.home_team_id
LEFT JOIN v_team_form af ON af.team_id=m.away_team_id
WHERE m.status='finished';
"""

def create_schema():
    print("Creating PitchIQ schema...")
    with engine.begin() as conn:
        for stmt in SCHEMA_SQL.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
    print("Done — 7 tables + 3 views created successfully.")
    print("Tables : leagues, teams, players, matches,")
    print("         player_match_stats, team_match_stats, match_events")
    print("Views  : v_player_season_stats, v_team_form, v_match_features")

if __name__ == "__main__":
    create_schema()
