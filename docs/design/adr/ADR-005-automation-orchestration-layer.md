# Why use an external orchestration layer and why n8n owns orchestration rather than RAG logic

(draft only)

## Decision
- n8n orchestrates schedules, webhooks, evaluation triggers, notifications, and issue creation.
- The Python RAG service retains all indexing, retrieval, evaluation, and generation logic.
- n8n is optional infrastructure, not a core runtime dependency.

## Alternatives considered
- Put scheduling/orchestration directly into the Python service.
- Use cron/GitHub Actions/cloud-native scheduling only.
- Let n8n own parts of ingestion or evaluation logic.

## Rationale
- Preserves platform-agnostic core architecture.
- Keeps operational workflow logic separate from RAG logic.
- Makes the orchestration layer replaceable.
- Better reflects how the service could participate in a larger DocOps environment.

## Consequences
- Another deployable/manageable component exists.
- A secure administrative trigger mechanism is needed.
- Workflow definitions and operational docs must be maintained separately.

