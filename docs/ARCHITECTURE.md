# Virendra AI Studio — Architecture

## System Overview

The application is organized around a React dashboard, FastAPI backend,
workflow/orchestration services, persistence, AI providers, media processing,
and external publishing integrations.

```text
Creator / Reviewer
       |
       v
React Dashboard
       |
       v
FastAPI Application
       |
       +---- Authentication and Authorization
       |
       +---- Content APIs and Approval Workflow
       |
       +---- AI Orchestrator
       |        |
       |        +---- Topic Agent
       |        +---- Script Agent
       |        +---- SEO Agent
       |        +---- Thumbnail Agent
       |        +---- Quality Agent
       |
       +---- Media Factory
       |        |
       |        +---- Voice / Audio
       |        +---- Images
       |        +---- Subtitles
       |        +---- Video Rendering
       |
       +---- Publishing Integrations
       |        |
       |        +---- YouTube
       |        +---- Instagram
       |        +---- Facebook Page
       |        +---- Telegram
       |
       +---- Analytics and Recommendations
       |
       v
SQLAlchemy / Database / Alembic
