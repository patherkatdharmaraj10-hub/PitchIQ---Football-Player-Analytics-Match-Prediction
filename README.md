# PitchIQ ⚽
### Football Player Analytics & Match Prediction

A full-stack football analytics platform built with Python, FastAPI, React, and XGBoost.

![Dashboard](data/sample/README.md)

## Live Demo
- Frontend: Coming soon (Vercel)
- API Docs: Coming soon (Railway)

## Features
- Real football data from StatsBomb open data
- XGBoost match outcome prediction (Home/Draw/Away)
- Player performance analytics
- League standings table
- Interactive React dashboard

## Tech Stack
| Layer | Tech |
|-------|------|
| Database | PostgreSQL 15 |
| ETL | Python, StatsBombPy |
| ML | XGBoost, Scikit-learn, MLflow |
| API | FastAPI, Uvicorn, Pydantic |
| Frontend | React, Vite, Tailwind CSS |

## Quick Start
```bash
# 1. Install dependencies
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env

# 3. Create database
createdb pitchiq_db
python scripts/create_schema.py

# 4. Load data
python etl/load_statsbomb.py --competition 53 --season 106

# 5. Train models
python models/train.py

# 6. Start API
uvicorn api.main:app --reload --port 8000

# 7. Start frontend
cd frontend && npm install && npm run dev
```

## Project Structure


## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Status check |
| GET | /players | Player list |
| GET | /matches | Match list |
| GET | /top-scorers | Goals leaderboard |
| GET | /standings/{id} | League table |
| POST | /predict/match | Match prediction |

## Data Source
StatsBomb open data — UEFA Women's Euro 2022

## Author
patherkatdharmaraj10-hub
