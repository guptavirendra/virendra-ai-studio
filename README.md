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

Create the PostgreSQL database, then apply the schema:

```bash
alembic upgrade head
```

For local development, rendered media is stored under
`app/generated/videos/`. Azure deployments can instead configure
`AZURE_STORAGE_ACCOUNT_URL` and `AZURE_STORAGE_CONTAINER`; the backend then
stores MP4/SRT artifacts in a private Blob container using its managed identity.
Leave both settings unset to use local disk.

Before starting for the first time, copy `.env.example` to `.env`, generate a
session key, and set the bootstrap admin username/password. The app refuses to
start without a valid session key or when the database has no users and no
bootstrap admin credentials. See the authentication configuration below.

Start the app:

```bash
uvicorn app.main:app --reload
```

Run with Docker (local development):

```bash
cp .env.example .env
# edit .env and set SESSION_SECRET_KEY, BOOTSTRAP_ADMIN_USERNAME, and BOOTSTRAP_ADMIN_PASSWORD
docker compose run --rm backend alembic upgrade head
docker compose up --build
# then visit http://localhost:4173 and sign in with the bootstrap admin
```

Existing installations can run the same migration command against their current `DATABASE_URL`;
the baseline migration creates only missing tables and preserves existing rows.
After upgrading an existing database, run `alembic check` to detect schema drift
between that database and the SQLAlchemy models. The baseline intentionally
does not rewrite pre-existing tables or columns; review reported differences
and add an explicit migration before relying on the application against a
drifted legacy schema.

Continuous integration:

- A GitHub Actions workflow is configured at `.github/workflows/python-tests.yml`
- It installs dependencies and runs `DATABASE_URL=sqlite:///./test.db pytest -q`

New API endpoints:

- `POST /content/generate` — create a draft content item
- `POST /content/create-with-ai` — create a draft item and generate AI script + SEO metadata immediately
- `POST /content/orchestrate` — generate an orchestration payload without persisting it

## Local video workflow

Create a content draft in the dashboard, then choose **Render MP4** from Recent Content. The local renderer creates a narrated Hindi slide video, an SRT subtitle file, and saves both under `app/generated/videos/`. Use **Download MP4** and **Download SRT** to retrieve them.

The default script generator uses a built-in local template when `OPENAI_API_KEY` is unset. To upload the rendered file to YouTube, configure the Google OAuth client secrets and token described below; the dashboard's upload action submits videos privately.

## Daily Bollywood news auto-publishing

The backend can collect fresh reports from RSS feeds published by Hindustan
Times, The Times of India, and The Indian Express, create an
original Hindi digest, render it locally, and upload it publicly once a day.
The scheduler is **off by default** and does not change the dashboard's private
manual-upload behavior.

To enable it on your own computer:

1. Install the app's Python dependencies in a local virtual environment and
   configure Google Cloud OAuth. Enable **YouTube Data API v3**, create an
   OAuth **Desktop app** client, and save its downloaded JSON in the project
   root as `client_secrets.json`. If Google's consent screen is in testing mode,
   add the Google account that owns the channel as a test user.
2. With the virtual environment active, run `python -m app.youtube_auth` from
   the project root and sign in to the Google account/channel you intend to
   publish to. The OAuth token is saved locally as `youtube_token.json`; do not
   send or commit either credentials file. Check the printed channel name and
   ID before enabling the scheduler. Google's OAuth testing-mode refresh tokens
   can expire after seven days; review the consent-screen publication and
   verification requirements for a long-running setup.
3. Set `OPENAI_API_KEY` in `.env`, then set:

   ```dotenv
   DAILY_NEWS_AUTOPUBLISH_ENABLED=true
   DAILY_NEWS_PUBLISH_TIME=20:00
   DAILY_NEWS_TIMEZONE=Asia/Kolkata
   ```

4. Apply migrations with `docker compose run --rm backend alembic upgrade head`,
   then start the stack with `docker compose up --build`. On macOS, you can keep
   the computer awake while running the stack with
   `caffeinate -dimsu docker compose up --build`.

The app must be running with internet access at the scheduled time. It checks
for at least three fresh Bollywood-related items from at least two publisher
feeds; if the reporting is insufficient, it skips publication for that date.
Each date is recorded before rendering/uploading to prevent accidental
duplicate uploads. Failed or ambiguous uploads are not retried automatically;
check the YouTube Studio channel and the backend logs before taking action.
Use one backend instance only; running multiple backend processes can cause
competing schedules. Existing public-upload API quota and Google OAuth app
verification restrictions still apply, so verify the Google Cloud project
before relying on the schedule.

The video paraphrases reporting and links the publisher articles in its
description. RSS availability and reuse terms are controlled by each publisher;
check those terms for your channel and its monetization status. OpenAI usage
may incur charges. The scheduler does not publish old reports to catch up if
the computer was off at 20:00.

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
SESSION_SECRET_KEY=
BOOTSTRAP_ADMIN_USERNAME=
BOOTSTRAP_ADMIN_PASSWORD=
SESSION_COOKIE_SECURE=false
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/youtube_ai
OPENAI_API_KEY=your-openai-api-key
YOUTUBE_CLIENT_SECRETS=client_secrets.json
YOUTUBE_TOKEN_JSON=youtube_token.json
YOUTUBE_CATEGORY_ID=25
YOUTUBE_PRIVACY_STATUS=private
DAILY_NEWS_AUTOPUBLISH_ENABLED=false
DAILY_NEWS_PUBLISH_TIME=20:00
DAILY_NEWS_TIMEZONE=Asia/Kolkata
INSTAGRAM_ACCESS_TOKEN=your-meta-access-token
INSTAGRAM_USER_ID=your-instagram-professional-account-id
INSTAGRAM_GRAPH_API_VERSION=v22.0
FACEBOOK_PAGE_ACCESS_TOKEN=
FACEBOOK_PAGE_ID=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
AZURE_STORAGE_ACCOUNT_URL=
AZURE_STORAGE_CONTAINER=
PUBLIC_MEDIA_BASE_URL=https://your-public-api-domain.example
```

Copy `.env.example` to `.env` and update the values.

Authentication is enabled for the dashboard and all content APIs. Generate a
unique `SESSION_SECRET_KEY` (at least 32 characters; generate one with
`python -c "import secrets; print(secrets.token_urlsafe(48))"`) and set
`BOOTSTRAP_ADMIN_USERNAME` and `BOOTSTRAP_ADMIN_PASSWORD` before first startup.
The first admin is created only when the users table is empty; subsequent
accounts are provisioned by an admin in the dashboard or through
`POST /auth/users`. Passwords must be at least 12 characters. In TLS-terminated
deployments set `SESSION_COOKIE_SECURE=true`; keep it `false` only for local HTTP
development. Sessions are HTTP-only, SameSite=Strict, and expire after eight
hours. Unsafe requests require the CSRF token returned by login (the dashboard
sends it automatically). Login allows ten attempts per normalized username in
a 15-minute window; excess requests receive HTTP 429 with a `Retry-After`
header, and a successful login resets the counter.

Content is shared across authenticated team users. Admins can create other
admins or members; members can use the content and publishing workflows but
cannot provision accounts. Admins can disable or reactivate users and reset
their passwords from Manage accounts; each operation revokes existing sessions,
and disabled accounts cannot sign in. The final active administrator cannot be
disabled. Social platform fetches use short-lived signed URLs for rendered
media, while dashboard downloads still require login.

Generate the session key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Instagram publishing requires an Instagram Professional account connected to a
Facebook Page, a Meta access token with Instagram publishing permissions, and a
public HTTPS backend URL that Meta can use to fetch rendered MP4 files. Once the
values above are configured, approve and render a video, then call
`POST /content/{item_id}/publish/instagram`. Localhost URLs cannot be used for
live Instagram publishing.

Facebook Page video publishing requires `FACEBOOK_PAGE_ACCESS_TOKEN` with Page
publishing permissions, `FACEBOOK_PAGE_ID`, and the same public HTTPS media URL.
After approving and rendering a video, call
`POST /content/{item_id}/publish/facebook` or select **Publish Facebook video**
in the dashboard.

Telegram video publishing requires a bot token (`TELEGRAM_BOT_TOKEN`), a target
chat or channel ID (`TELEGRAM_CHAT_ID`), and the same public HTTPS media URL so
Telegram can fetch the rendered MP4. Add the bot to the target channel/chat with
permission to post, then approve and render a video and call
`POST /content/{item_id}/publish/telegram` or select **Publish on Telegram**.

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

## Project Documentation

Additional documentation is available in the `docs/` folder:

- `docs/README.md`
- `docs/vision-and-product-overview.md`
- `docs/agent-workflow.md`
- `docs/implementation-roadmap.md`
- `docs/system-architecture.md`
- `docs/api-spec.md`
- `docs/automation-scheduler.md`
- `docs/government-alert-automation.md`
