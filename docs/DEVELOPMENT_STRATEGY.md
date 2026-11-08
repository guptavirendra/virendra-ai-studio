# Virendra AI Studio — Development Strategy

## Product Vision

Virendra AI Studio is an AI-powered content operating system for creating,
reviewing, producing, and publishing digital content.

The product vision includes:

- AI content generation and research.
- Script, voice, video, thumbnail, and SEO automation.
- Multi-platform publishing.
- Analytics and a self-learning feedback loop.
- A single-click workflow in which the user reviews content and gives final approval.

## Primary Use Case

The initial creator workflow includes the SarkariKam YouTube channel,
focused on government services and informational tutorials in Hindi.

Government-related content must be accurate, source-grounded, and reviewed
before publication. The existing Bollywood-news scheduler is a separate
workflow and must not be treated as a SarkariKam content source.

## Development Principles

1. Local-first development on the developer's Mac.
2. Preserve existing application data and uncommitted work.
3. Prefer small, testable changes over large rewrites.
4. Review security-sensitive changes before committing.
5. Never expose API keys, OAuth credentials, tokens, or passwords.
6. Never publish content without explicit user approval.
7. Do not describe integrations as production-verified without live evidence.
8. Update project documentation after meaningful milestones.

## Technology Direction

- Backend: Python and FastAPI.
- Frontend: React.
- Database: PostgreSQL, with SQLite for supported local/test workflows.
- Persistence and migrations: SQLAlchemy and Alembic.
- AI: existing OpenAI integration and agent orchestration.
- Media: local development rendering and storage; private cloud storage for a future deployment.
- Local environment: Docker Compose.
- Future deployment: Azure artifacts are retained, but deployment is deferred.

## Content Workflow

1. User provides a topic or content requirement.
2. System researches or receives trusted source material.
3. AI generates a draft script and supporting metadata.
4. Specialized agents perform SEO and quality checks.
5. Media factory prepares voice, images, subtitles, and video.
6. User reviews the complete draft.
7. User explicitly approves publication.
8. Publishing integration executes the approved action.
9. Analytics are collected and used for future recommendations.

## Publishing Safety

- YouTube manual upload defaults to private.
- Expected channel identity must be verified before upload.
- Approval must correspond to the current content version.
- The daily Bollywood scheduler remains disabled by default and draft-only.
- No automatic public publishing is permitted.
- SarkariKam government-services content must use a separate, reviewed workflow.

## Infrastructure and Budget

Development remains local-first. Do not create Azure resources, deploy services,
push container images, or run cloud migrations until the owner has an account,
budget, and explicitly authorizes deployment.

Keep Azure Bicep and deployment documentation for future use.

## Working with ChatGPT

At the beginning of a development session:

1. Inspect `git status`.
2. Read `docs/PROJECT_STATUS.md`.
3. Read `docs/CHATGPT_HANDOFF.md`.
4. Read the relevant architecture, decision, and roadmap documents.
5. Inspect current code before proposing modifications.

Do not assume old snapshots describe the current workspace.
Do not overwrite user changes or commit without explicit authorization.
