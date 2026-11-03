# Automation and Scheduler

## Implemented: daily Bollywood news

The FastAPI backend starts an APScheduler job when
`DAILY_NEWS_AUTOPUBLISH_ENABLED=true`. It runs once per day at
`DAILY_NEWS_PUBLISH_TIME` in `DAILY_NEWS_TIMEZONE` (defaults: `20:00`,
`Asia/Kolkata`). The job:

1. Reads fresh items from the direct publisher feeds configured in
   `app/daily_news.py`.
2. Requires three recent Bollywood-related stories from at least two sources.
3. Uses OpenAI to produce an original Hindi summary from the feed headlines and
   excerpts, then puts source links in the video description.
4. Renders the narrated MP4/SRT locally and uploads the video with public
   visibility.
5. Records the date-keyed run in `content_items` to prevent duplicate uploads.

The feature is off by default. Enabling it requires `OPENAI_API_KEY` and a
valid local YouTube OAuth token (`YOUTUBE_TOKEN_JSON`). Missing prerequisites
stop application startup with an actionable error. Keep one backend instance
running; the scheduler is process-local, not a distributed job queue. If the
machine is offline or stopped at the scheduled time, the job does not catch up.
Google OAuth consent-screen testing mode can expire refresh tokens after seven
days; review Google's publication and verification requirements for
long-running unattended uploads.

If a run fails or the upload result is ambiguous, the date is recorded and is
not retried automatically. Check logs, the content record, and YouTube Studio
before manually resolving the run; blindly retrying could publish a duplicate.
The manual dashboard upload remains private by default and is independent of
this scheduler.

Publisher RSS feeds may impose reuse or commercial-use terms. Review each
publisher's terms before running this feature on a monetized channel. The
automation paraphrases reporting and links original articles; it does not
republish full article text. Generated scripts can still contain errors, so
review the output and channel before enabling unattended public publishing.

## Future work

Analytics reports, broader trend detection, publication notifications, and
learning from channel performance are not implemented. Celery or a distributed
scheduler may be appropriate if the app later moves to multiple backend
instances; do not run this process-local scheduler in multiple workers.
