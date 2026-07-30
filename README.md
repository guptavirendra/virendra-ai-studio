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

Create a `.env` file in the project root with the following values:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/youtube_ai
OPENAI_API_KEY=your-openai-api-key
YOUTUBE_CLIENT_SECRETS=client_secrets.json
YOUTUBE_TOKEN_JSON=youtube_token.json
YOUTUBE_CATEGORY_ID=25
YOUTUBE_PRIVACY_STATUS=private
```

Copy `.env.example` to `.env` and update the values.

## OpenAI integration

The backend can generate Hindi scripts and SEO metadata using OpenAI. Use the endpoint:

- `POST /content/{item_id}/generate-ai`

This populates `script`, `seo_title`, `seo_description`, and `hashtags` for the content item.

## YouTube integration

You need a Google OAuth client secrets file in the project root named by `YOUTUBE_CLIENT_SECRETS`.

To generate credentials, run:

```bash
python -m app.youtube_auth
```

Then upload a video with:

- `POST /content/{item_id}/upload-youtube`

Payload example:

```json
{
  "file_path": "/path/to/video.mp4",
  "privacy_status": "private",
  "tags": ["government update", "Aadhaar", "EPFO"]
}
```

The YouTube client will upload the file and return YouTube's upload response.
