# Why two public API endpoints?

(draft only)

Endpoints:
- `POST /v1/search`
- `POST /v1/answer`

The public API is limited to two endpoints because the system has two primary user-facing capabilities: retrieving relevant source content and generating a grounded answer from that content. 

Indexing and administrative operations remain internal so the public interface stays small, easier to secure, easier to document, and less tightly coupled to implementation details.
