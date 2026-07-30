# Virendra AI Studio

A starter FastAPI project for an AI-powered YouTube content automation workflow.

## Features

- Generate draft content ideas
- Create scripts for videos
- Store content in PostgreSQL
- Approve and publish content through simple API endpoints

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a PostgreSQL database and run the SQL in `schema.sql`.

Start the app:

```bash
uvicorn app.main:app --reload
```

## Frontend dashboard

A starter React dashboard is available in `frontend/`.

Install dependencies:

```bash
cd frontend
npm install
```

Run the dashboard:

```bash
npm run dev
```

The frontend currently uses a health endpoint at `/api/health`. In production, proxy the frontend to the FastAPI backend or add a simple reverse proxy.

## Environment

Create a `.env` file in the project root with:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/youtube_ai
```

The backend reads `DATABASE_URL` from the environment and falls back to the default URL shown above.
