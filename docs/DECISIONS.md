# Virendra AI Studio — Architecture and Product Decisions

This document records important decisions so future development sessions
do not silently reverse them.

## D-001: Local-first development

Decision: Develop and validate locally before cloud deployment.

Reason: Cloud deployment is deferred until budget and account access are available.

## D-002: Preserve existing work

Decision: Inspect Git status and diffs before modifying, staging, or committing.

Reason: The repository may contain valuable uncommitted code, migrations, and tests.

## D-003: Human approval before publication

Decision: AI-generated content remains a draft until reviewed and explicitly approved.

Reason: Content quality, factual accuracy, and publishing safety require human oversight.

## D-004: Private YouTube upload default

Decision: Preserve private as the default upload privacy setting.

Reason: A private test upload allows verification without unintended public release.

## D-005: Expected YouTube channel verification

Decision: Verify the authorized Google account against the configured expected
YouTube channel identity before upload.

Reason: Prevent accidental publishing to the wrong channel.

## D-006: Scheduler separation

Decision: The daily Bollywood-news scheduler is separate from SarkariKam and
must remain disabled by default and draft-only.

Reason: Bollywood news and government-services tutorials are different
content products and must not be mixed.

## D-007: No secrets in Git or chat

Decision: Never commit .env, OAuth client secrets, access tokens, or production
secrets. Never ask the user to paste them into chat.

Reason: Protect accounts and publishing infrastructure.

## D-008: Cloud deployment deferred

Decision: Retain Azure deployment artifacts but do not provision or deploy
cloud resources until explicitly authorized.

Reason: Current development is local-first and cloud spending is deferred.

## D-009: Roadmap status requires evidence

Decision: Distinguish implementation scaffolding, integration code, tested
behaviour, and live production verification.

Reason: A checkbox must not imply that an external integration or production
workflow has been validated when it has not.

## Updating decisions

Add a dated entry when a decision changes. Explain the previous decision,
the new decision, and the reason.
