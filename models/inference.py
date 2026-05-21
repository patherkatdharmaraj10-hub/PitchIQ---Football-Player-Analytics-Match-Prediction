"""
models/inference.py - Load saved models and serve predictions.
"""
import os, joblib, pandas as pd
from functools import lru_cache

MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved")
RESULT_LABELS = {0: "home_win", 1: "draw", 2: "away_win"}


@lru_cache(maxsize=1)
def _load(name):
    path = os.path.join(MODELS_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Model not found: {path}. Run: python models/train.py")
    return joblib.load(path)


def predict_match_outcome(feature_row: dict) -> dict:
    art = _load("match_predictor.pkl")
    model, features = art["model"], art["features"]
    row = {f: 0.0 for f in features}
    row.update({k: v for k, v in feature_row.items() if k in features})
    X = pd.DataFrame([row])[features].astype(float)
    proba = model.predict_proba(X)[0]
    probs = {RESULT_LABELS[c]: round(float(p), 4)
             for c, p in zip(model.classes_, proba)}
    probs["predicted"] = max(
        (k for k in probs if k != "predicted"),
        key=lambda k: probs[k]
    )
    return probs


def model_status() -> dict:
    return {
        name: os.path.exists(os.path.join(MODELS_DIR, fname))
        for name, fname in [
            ("match_predictor", "match_predictor.pkl"),
            ("player_scorer",   "player_scorer.pkl"),
        ]
    }
