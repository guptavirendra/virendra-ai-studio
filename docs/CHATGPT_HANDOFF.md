# ChatGPT Handoff — Virendra AI Studio

Use this document to continue work on the existing repository. Treat it as a
snapshot; first inspect the current Git status and relevant files because local
changes may have advanced since it was written.

## User's goal

The user owns the YouTube channel `https://www.youtube.com/@sarkarikamm` and
wants a reviewed government-services information workflow suitable for that
channel. The existing Bollywood-news scheduler is unrelated to that use case,
must remain disabled for SarkariKam, and must never publish automatically.

Explain setup in Hindi/Devanagari when talking directly to the user. Never ask
the user to paste Google passwords, OAuth tokens, API keys, or the contents of
credential files into chat.

## Current repository state

- Branch: `main`.
- Last pushed commit at snapshot: `e4d3477` (`Add local daily Bollywood
  YouTube scheduler`).
- There are local, uncommitted changes related to a YouTube configuration fix
  and documentation. Check `git status` before editing, staging, or committing.
- Do not overwrite or delete the user's `.env` or credential files.
- The OAuth client secrets file was present at the project root at the last
  check; do not read or expose its contents.
- `.env` and `youtube_token.json` were absent at that check.
- Manual upload privacy default is `private`; preserve it.
- The daily Bollywood draft scheduler is disabled by default and creates drafts
  only if explicitly enabled. Keep it disabled for SarkariKam; do not enable
  automatic public publishing.

## Work already done

The application includes:

- FastAPI + SQLAlchemy content API and React/Vite dashboard.
- AI-assisted content/script/SEO workflows and local Hindi video rendering.
- YouTube OAuth/upload integration; Instagram, Facebook, and Telegram publishing
  integrations.
- Session-based multi-user authentication, CSRF protection, login throttling,
  account controls, Alembic migrations, and schema drift detection.
- Docker Compose local development support.
- Azure Container Apps and private Blob Storage deployment artifacts. They are
  not equivalent to a verified live Azure deployment.
- Opt-in local daily Bollywood news workflow, scheduled for 20:00
  `Asia/Kolkata`, sourcing fresh reporting from publisher RSS feeds and
  preparing original summaries with source links.

The project is not yet confirmed production-ready. No real YouTube account
authorization, channel upload, public scheduled upload, or end-to-end Azure
deployment has been verified.

## Current YouTube config fix (local, uncommitted at snapshot)

The reported error was:

```text
pydantic_core.ValidationError: SESSION_SECRET_KEY Field required
```

Observed cause: `app.youtube_auth` imported `app.config`, whose global
`Settings()` required the app's `SESSION_SECRET_KEY` before OAuth could start.
The repository-root `.env` was absent. `.env.example` is only a template.

Changes already made locally:

- Added `app/youtube_config.py` with YouTube-only Pydantic settings, root-anchored
  `.env` lookup, and project-root-relative OAuth file paths.
- Changed `app/youtube_auth.py` and `app/youtube_client.py` to use these settings
  without importing app-wide settings.
- Kept FastAPI `SESSION_SECRET_KEY` required.
- Kept the YouTube privacy default `private`.
- Updated README instructions and added `tests/test_youtube_config.py`.

Validation already observed:

- `env -u SESSION_SECRET_KEY pytest -q tests/test_youtube_config.py` — 3 passed.
- `SESSION_SECRET_KEY=<test-only-value> pytest -q tests/test_auth.py tests/test_media_storage.py`
  — 14 passed. The actual test value must never be treated as a production
  secret.
- No live Google OAuth flow or YouTube upload was run.
- Pylance syntax calls timed out; use focused pytest or Python compile checks
  instead if needed.

Review current `git diff` before continuing; do not assume the patch remains
unchanged.

## Safe next steps

1. Inspect current `git status`, then review the pending configuration diff.
2. Ensure normal FastAPI settings still load the root `.env` and environment
   variables, and OAuth-specific settings ignore unrelated environment keys.
3. Verify YouTube config path resolution and imports from a different working
   directory with `SESSION_SECRET_KEY` unset.
4. Run relevant auth/upload tests; do not make real YouTube calls in tests.
5. Explain to the user how to create a strong root `.env` without replacing any
   existing file. If `.env` is absent, give a safe command or instructions to
   create it; never put fake values in place of real secrets.
6. The user must run `python -m app.youtube_auth`, sign in to the Google account
   managing the channel, and confirm the channel name/ID printed by the tool.
7. Set `YOUTUBE_EXPECTED_CHANNEL_ID` to the intended channel ID before any
   upload. The daily Bollywood workflow now creates drafts only; each video
   must be reviewed, approved, and explicitly published by a user.
8. The daily Bollywood workflow is not a government-alert feed for the
   SarkariKam channel. Do not present it as aligned with that channel without
   the developer's confirmation.
9. Any commit/push requires an explicit user request. Do not include
   credentials, generated media, or unrelated untracked files.

## Product and operational caveats

- Local scheduler runs only while the host, app, and network are up; it is
  process-local and should run as one backend instance.
- Current scheduler does not automatically retry uncertain upload failures;
  inspect YouTube Studio and logs to avoid duplicate posts.
- Google OAuth testing-mode tokens and YouTube API project verification/quota
  can affect unattended uploads.
- RSS reuse terms vary by publisher; review them, especially for monetization.
- Existing roadmap follow-ups include analytics/learning features and full
  Azure operational validation.

## Handoff update — 2026-11-07

Before continuing, inspect the current Git status and diffs. Preserve all
existing changes and stage only files explicitly selected for a task.

Project direction:
- Local-first development; cloud deployment deferred.
- Product vision: AI content generation, script/voice/video/thumbnail/SEO
  automation, multi-platform publishing, analytics, and self-learning.
- The intended experience is a streamlined workflow with user review and
  explicit final approval.
- SarkariKam government-services content is a distinct workflow.
- The Bollywood-news scheduler remains disabled by default and draft-only.
- Never publish automatically or expose credentials.
- Do not claim live OAuth, publishing, analytics, or cloud deployment has
  been verified without fresh evidence.

Read DEVELOPMENT_STRATEGY.md, ROADMAP.md, ARCHITECTURE.md, and DECISIONS.md
alongside this handoff.
