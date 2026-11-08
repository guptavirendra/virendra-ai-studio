# Virendra AI Studio Docs

यह folder Virendra AI Studio के लिए project documentation को organize करने के लिए बनाया गया है।

## Public website

The static project website lives in this folder and is separate from the
private FastAPI dashboard and backend. To publish it manually on GitHub Pages:

1. Open the repository's **Settings → Pages**.
2. Under **Build and deployment**, choose **Deploy from a branch**.
3. Select branch **main** and folder **/docs**, then save.
4. After the Pages deployment completes, review
   `https://guptavirendra.github.io/virendra-ai-studio/`.

The site uses repository-relative links and does not require the backend,
environment variables, OAuth credentials, or a build step. The Pages Jekyll
configuration excludes the existing Markdown project notes from the generated
site, so they are not published as website pages.

## Documents

- [Project Status](./PROJECT_STATUS.md)
- [ChatGPT Handoff](./CHATGPT_HANDOFF.md)
- [Development Strategy](./DEVELOPMENT_STRATEGY.md)
- [Master Roadmap](./ROADMAP.md)
- [Architecture](./ARCHITECTURE.md)
- [Architecture and Product Decisions](./DECISIONS.md)

- [Public website](./index.html)
- [Privacy Policy](./privacy.html)
- [YouTube API Disclosure](./youtube-api-disclosure.html)
- [Terms of Use](./terms.html)
- [Backup retention runbook](./backup-retention.md)
- [Automation and scheduler](./automation-scheduler.md)
- [Contact](./contact.html)
- [Product Overview](./vision-and-product-overview.md)
- [Agent Workflow](./agent-workflow.md)
- [Implementation Roadmap](./implementation-roadmap.md)
- [Creator AI Studio Roadmap](../Creator_AI_Studio_Roadmap.md)
- [Government Alert Automation Use Case](./government-alert-automation.md)

## Summary

Virendra AI Studio ek AI-powered content automation system hai jisme:

- AI content generation
- script, voice, video, thumbnail aur SEO automation
- multi-platform publishing
- analytics aur self-learning

Isse ek single-click system banaya ja sakta hai jahan user sirf review aur final approval kare.
