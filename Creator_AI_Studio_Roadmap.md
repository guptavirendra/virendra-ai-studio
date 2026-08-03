# Creator AI Studio Roadmap

## Vision

Build an AI-powered content operating system for YouTube and Instagram.

## Status snapshot (updated 2026-08-03)

This file is now the working project plan for the repository. It should be updated whenever a milestone is completed so the next session can resume from the latest state.

### Completed or in progress

- [x] Project scaffolding for a FastAPI backend and React frontend exists.
- [x] Content workflow endpoints and backend services are in place.
- [x] OpenAI-based script and SEO generation logic is available.
- [x] YouTube upload integration is wired through the backend.
- [x] PostgreSQL schema and data models are defined.
- [x] A starter frontend dashboard is present.
- [ ] Docker container setup is not yet finalized.
- [ ] A full prompt manager and multi-agent orchestrator are not yet implemented.
- [x] Basic orchestration layer and endpoint implemented (app/orchestrator.py, POST /content/orchestrate)
- [x] Regression and API tests added for orchestrator (tests/test_orchestrator.py, tests/test_orchestrator_api.py)
- [x] Tests configured to run with in-memory SQLite during CI/local runs
- [ ] Video factory features such as voice, images, subtitles, and MP4 generation are still pending.
- [ ] Publishing to Instagram, Facebook, and Telegram is still pending.
- [ ] Analytics and AI suggestions are still pending.

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
- [ ] Docker
- [ ] Prompt Manager

### Phase 1.2 -- AI Orchestrator

- [ ] Topic Agent
- [ ] Script Agent
- [ ] SEO Agent
- [ ] Thumbnail Agent
- [ ] Quality Agent

### Phase 2 -- Video Factory

- [ ] AI Voice
- [ ] AI Images
- [ ] Subtitle Generator
- [ ] MP4 Output

### Phase 3 -- Publishing

- [x] YouTube
- [ ] Instagram
- [ ] Facebook
- [ ] Telegram

### Phase 4 -- Analytics

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

1. Implement the orchestrator layer and separate agents.
2. Add Docker support for local and deployment workflows. (DONE)
3. Expand publishing support beyond YouTube.
4. Update this file after each completed milestone.
