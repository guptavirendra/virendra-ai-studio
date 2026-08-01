# System Architecture

## Components

### Backend
- Python + FastAPI
- REST API endpoints for content workflow
- PostgreSQL database for content, analytics, and learning data
- OpenAI / Gemini integration for script and SEO generation
- Google YouTube API integration for uploads

### Automation
- Celery: background jobs for video generation, uploads, and analytics processing
- APScheduler: scheduled tasks for nightly reporting and trend checks
- n8n: external workflow automation, multi-platform publishing, and notification triggers

### Frontend
- React dashboard
- Preview status, review queue, and content controls

### Data Flow
1. Topic input creates a content draft
2. AI generates Hindi script and SEO metadata
3. Voice + video creator builds media
4. Thumbnail generator produces creative assets
5. Publisher agent uploads drafts across platforms
6. Analytics agent gathers performance metrics nightly
7. Learning agent updates future content strategy

## Deployment
- Docker for backend, frontend, and worker services
- PostgreSQL container for persistence
- Optional separate containers for Celery workers and scheduler

## Integration Patterns
- API-first backend with reusable AI workflow services
- Event-driven publishing pipeline
- Data-driven learning loop for daily improvement
