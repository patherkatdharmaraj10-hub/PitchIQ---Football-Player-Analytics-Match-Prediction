"""
models/train.py - Train XGBoost match predictor and player scorer.
Usage:
    python models/train.py
    python models/train.py --model match
    python models/train.py --model player
"""
import argparse, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, mean_absolute_error
from xgboost import XGBClassifier, XGBRegressor
from db import run_query

MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved")
os.makedirs(MODELS_DIR, exist_ok=True)

FEATURE_COLS_MATCH = [
    "home_xg", "home_possession", "home_shots_on_target",
    "away_xg", "away_possession", "away_shots_on_target",
    "xg_diff", "home_wins_l5", "home_form", "away_wins_l5", "away_form",
]

FEATURE_COLS_PLAYER = [
    "goals", "assists", "xg", "xa", "shots", "shots_on_target",
    "pass_accuracy", "key_passes", "tackles", "interceptions",
    "minutes_played", "shot_accuracy", "goal_contributions_p90",
]

MATCH_SQL = """
SELECT
    CASE WHEN home_goals>away_goals THEN 0
         WHEN home_goals=away_goals THEN 1
         ELSE 2 END AS result,
    (home_goals+away_goals) AS total_goals,
    COALESCE(home_xg,0) AS home_xg,
    COALESCE(home_possession,50) AS home_possession,
    COALESCE(home_shots_on_target,0) AS home_shots_on_target,
    COALESCE(away_xg,0) AS away_xg,
    COALESCE(away_possession,50) AS away_possession,
    COALESCE(away_shots_on_target,0) AS away_shots_on_target,
    COALESCE(home_xg,0)-COALESCE(away_xg,0) AS xg_diff,
    COALESCE(home_wins_l5,0) AS home_wins_l5,
    COALESCE(home_form,0.5) AS home_form,
    COALESCE(away_wins_l5,0) AS away_wins_l5,
    COALESCE(away_form,0.5) AS away_form
FROM v_match_features
"""

PLAYER_SQL = """
SELECT
    pms.goals, pms.assists, pms.xg, pms.xa,
    pms.shots, pms.shots_on_target,
    COALESCE(pms.pass_accuracy,75) AS pass_accuracy,
    pms.key_passes, pms.tackles, pms.interceptions,
    pms.minutes_played,
    CASE WHEN pms.shots>0
         THEN pms.shots_on_target::float/pms.shots
         ELSE 0 END AS shot_accuracy,
    CASE WHEN pms.minutes_played>0
         THEN (pms.goals+pms.assists)::float/pms.minutes_played*90
         ELSE 0 END AS goal_contributions_p90,
    pms.rating AS target_rating,
    p.position
FROM player_match_stats pms
JOIN players p ON p.id=pms.player_id
WHERE pms.minutes_played >= 45
"""


def to_float_df(df, cols):
    """Force all feature columns to float — fixes object dtype errors."""
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)
    return df


def train_match():
    print("\n── Match outcome predictor ──")
    df = pd.DataFrame(run_query(MATCH_SQL))
    if len(df) < 10:
        print(f"  Only {len(df)} matches — need more data.")
        return
    df = to_float_df(df, FEATURE_COLS_MATCH)
    X = df[FEATURE_COLS_MATCH]
    y = df["result"].astype(int)
    print(f"  Total matches: {len(df)}")
    print(f"  Class distribution: {y.value_counts().to_dict()} (0=H, 1=D, 2=A)")
    if len(df) < 30:
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.2, random_state=42)
    else:
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"  Train: {len(X_tr)}  Test: {len(X_te)}")
    clf = XGBClassifier(
        n_estimators=100, max_depth=3, learning_rate=0.1,
        eval_metric="mlogloss", random_state=42, verbosity=0
    )
    clf.fit(X_tr, y_tr)
    acc = accuracy_score(y_te, clf.predict(X_te))
    print(f"  Accuracy: {acc:.3f}")
    print(classification_report(
        y_te, clf.predict(X_te),
        target_names=["Home win", "Draw", "Away win"],
        zero_division=0
    ))
    path = os.path.join(MODELS_DIR, "match_predictor.pkl")
    joblib.dump({"model": clf, "features": FEATURE_COLS_MATCH}, path)
    print(f"  Saved → {path}")


def train_player():
    print("\n── Player performance scorer ──")
    df = pd.DataFrame(run_query(PLAYER_SQL))
    if df.empty:
        print("  No player data found.")
        return
    df = df.dropna(subset=["target_rating"])
    if len(df) < 20:
        print(f"  Only {len(df)} rows with ratings — need more data.")
        print("  Skipping player scorer.")
        return
    df = to_float_df(df, FEATURE_COLS_PLAYER)
    df = pd.get_dummies(df, columns=["position"], prefix="pos", dummy_na=True)
    pos_cols = [c for c in df.columns if c.startswith("pos_")]
    features = FEATURE_COLS_PLAYER + pos_cols
    X = df[features].fillna(0).astype(float)
    y = df["target_rating"].astype(float)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=42)
    reg = XGBRegressor(
        n_estimators=100, max_depth=3, learning_rate=0.1,
        random_state=42, verbosity=0
    )
    reg.fit(X_tr, y_tr)
    mae = mean_absolute_error(y_te, reg.predict(X_te))
    print(f"  MAE: {mae:.3f}")
    path = os.path.join(MODELS_DIR, "player_scorer.pkl")
    joblib.dump({"model": reg, "features": features}, path)
    print(f"  Saved → {path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", choices=["match", "player", "all"], default="all")
    args = p.parse_args()
    if args.model in ("match", "all"):
        train_match()
    if args.model in ("player", "all"):
        train_player()
    print("\nDone.")
