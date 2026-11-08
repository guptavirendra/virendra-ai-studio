# Creator AI Studio Roadmap

## Vision

Build an AI-powered content operating system for YouTube and Instagram.

## Status snapshot (reviewed 2026-11-07)

This file is now the working project plan for the repository. It should be updated whenever a milestone is completed so the next session can resume from the latest state.

### Completed or in progress

- [x] Project scaffolding for a FastAPI backend and React frontend exists.
- [x] Content workflow endpoints and backend services are in place.
- [x] OpenAI-based script and SEO generation logic is available.
- [x] YouTube upload integration is wired through the backend.
- [x] PostgreSQL schema and data models are defined.
- [x] A starter frontend dashboard is present.
- [x] Local Docker Compose setup is available for backend, frontend, and PostgreSQL.
- [x] Prompt manager and multi-agent orchestration components are implemented.
- [x] Basic orchestration layer and endpoint implemented (app/orchestrator.py, POST /content/orchestrate)
- [x] Prompt manager added for reusable AI prompts (app/prompt_manager.py)
- [x] Content creation route with AI generation added (POST /content/create-with-ai)
- [x] Regression and API tests added for orchestrator and AI content creation
- [x] Tests configured to run with SQLite during CI/local runs
- [x] YouTube upload uses the OAuth API and requires approved content with a rendered video.
- [x] Instagram Reels publishing is wired through Meta Graph API and uses approved rendered videos.
- [x] Facebook Page video publishing is wired through Meta Graph API and uses approved rendered videos.
- [x] Telegram bot video publishing is wired through the Bot API and uses approved rendered videos.
- [x] Video factory scaffold added for voiceover planning, SRT subtitle generation, and render metadata.
- [x] AI image generation prompt pipeline is now in place.
- [x] Analytics data/model groundwork and basic suggestion capabilities are reported in the project status.
- [ ] Complete CTR, watch-time, RPM reporting and a validated self-learning feedback loop.
- [x] Dashboard content list, summary, and creation flow are live for local use.
- [x] Local DB startup now falls back to SQLite when no DATABASE_URL is configured.
- [x] Local full-stack Docker workflow now includes the frontend dashboard and backend API.
- [x] Multi-user authentication with admin/member roles, signed sessions, and CSRF protection is in place.
- [x] Alembic baseline migration creates missing tables and adopts existing databases without dropping data.

### Current implementation references

- Backend API and content flow: [app/main.py](app/main.py)
- OpenAI and SEO generation: [app/openai_client.py](app/openai_client.py)
- YouTube integration: [app/youtube_client.py](app/youtube_client.py)
- Database schema: [schema.sql](schema.sql)
- Frontend starter: [frontend/src/App.tsx](frontend/src/App.tsx)

## Phase plan

### Phase 1 -- AI Script + Thumbnail + SEO

- [x] Topic input
- [x] Script generation
- [x] SEO title & description
- [x] Tags & hashtags
- [x] Thumbnail prompt

### Phase 1.1 -- MVP

- [x] FastAPI
- [x] React
- [x] PostgreSQL
- [x] Docker (local development stack)
- [x] Prompt Manager

### Phase 1.2 -- AI Orchestrator

- [x] Topic Agent
- [x] Script Agent
- [x] SEO Agent
- [x] Thumbnail Agent
- [x] Quality Agent

### Phase 2 -- Video Factory

- [x] AI Voice planning scaffold
- [x] AI Images
- [x] Subtitle Generator
- [ ] End-to-end MP4 output validation with a real content draft

### Phase 3 -- Publishing

- [x] YouTube upload workflow (OAuth; real account upload still requires credentials)
- [x] Instagram Reels publishing workflow (requires Meta credentials and public HTTPS media URL)
- [x] Facebook Page video publishing workflow (requires Page credentials and public HTTPS media URL)
- [x] Telegram video publishing workflow (requires bot credentials and public HTTPS media URL)

### Phase 4 -- Analytics

### Phase 5 -- Local deployment

- [x] Docker stack for backend and frontend is available for local development

- [ ] CTR
- [ ] Watch Time
- [ ] RPM
- [ ] AI Suggestions

## Architecture

```text
Frontend
   |
FastAPI
   |
Workflow Engine
   |
Agents
```

## Future

- [ ] MCP
- [ ] LangGraph
- [ ] Plugin System
- [ ] SaaS Billing

## Next actions for the next session

1. [x] Harden production secrets and deployment configuration for Azure Container Apps, including secure frontend serving (`docs/azure-container-apps.md`, `infra/azure/container-apps.bicep`).
2. [x] Add persistent login rate limiting (10 attempts per username per 15 minutes; successful login resets the counter).
3. [x] Add account lifecycle controls (admin password reset, account disable/reactivate, and session revocation).
4. [x] Add migration checks for schema drift on existing database installations (`alembic check` after adoption; tested drift reporting).
5. [x] Store rendered media in private Azure Blob Storage for multi-replica deployments; retain local disk for development.
6. Validate Azure deployment end to end, including media permissions, backup/restore, monitoring, and rollback.
7. Update this file after each completed milestone.
