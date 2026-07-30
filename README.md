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
