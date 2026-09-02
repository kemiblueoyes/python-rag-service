# ADR-009: API Key Authentication

## Status

Accepted

## Date

2026-09-02

## Context

The RAG service exposes two public capability endpoints:

- `POST /v1/search`
- `POST /v1/answer`

Both endpoints can invoke external services and consume paid resources for embedding, vector retrieval, reranking, and answer generation. Leaving them unauthenticated would allow any caller who could reach the Python service to use those capabilities.

The initial reference client is a WordPress plugin. Its browser interface is intended to be publicly usable, but the browser should not receive a credential that grants direct access to the Python service. Any key included in JavaScript, HTML, or a browser request could be inspected and reused outside the application.

The authentication design therefore needed to:

- Reject unauthenticated requests to the Search and Answer endpoints
- Keep the credential out of browser-delivered code and requests
- Allow the WordPress server to authenticate when forwarding requests
- Support other trusted server-side clients without coupling authentication to WordPress
- Keep the health endpoint available to deployment platforms and monitoring systems without requiring a secret
- Represent the security requirement in the generated OpenAPI specification
- Fail closed when authentication is not configured
- Remain simple enough for the current single-service, portfolio-scale architecture

This boundary is service-to-service authentication. It identifies a trusted client application, not an individual end user, and does not provide user accounts, roles, or permissions.

## Decision

Require a shared API key for `POST /v1/search` and `POST /v1/answer`.

The Python service reads the expected key from the `RAG_API_KEY` environment setting. Clients provide the matching value in the `X-API-Key` request header.

The authentication dependency is applied to both versioned capability routers so authentication runs before retrieval or answer generation. The supplied value is compared with the configured key using a timing-safe comparison.

Authentication failures use the public API error format:

- A missing or incorrect key returns `401 Unauthorized` with the error code `authentication_failed`.
- A missing server-side `RAG_API_KEY` configuration returns `503 Service Unavailable` with the error code `authentication_unavailable`.

The service does not silently disable authentication when `RAG_API_KEY` is absent. Returning `503` makes the configuration problem visible while preventing the protected endpoints from becoming unintentionally public.

The `GET /health` endpoint remains unauthenticated so infrastructure can confirm that the application process is available without storing or sending an API key.

The OpenAPI specification defines an API-key security scheme in the request header and marks both `/v1/search` and `/v1/answer` as requiring it. `/health` has no authentication requirement.

For the WordPress reference client, browser requests terminate at WordPress REST endpoints. The WordPress server then forwards Search and Answer requests to the Python service and adds the API key:

```text
Browser
  → WordPress REST proxy
  → X-API-Key header
  → Python RAG API
```

The WordPress server reads the Python service URL and credential from `DL_RAG_API_BASE_URL` and `DL_RAG_API_KEY`, typically configured in `wp-config.php`. The API key is not included in browser JavaScript or browser-to-WordPress requests.

Other trusted server-side clients may call the Python API directly by supplying the same header. Authentication remains part of the Python API rather than being implemented only in the WordPress client.

## Options Considered

### Leave the Search and Answer endpoints unauthenticated

Rejected for the implemented service.

Advantages:

- Simplest client and server implementation
- No credential configuration or rotation
- Convenient during early local development

Disadvantages:

- Allows any caller who can reach the service to invoke retrieval and generation
- Exposes paid provider usage to unauthorized requests
- Provides no trust boundary between the Python service and its clients
- Is unsuitable once the service is reachable outside a local development environment

### Shared API key in the `X-API-Key` header

Selected.

Advantages:

- Simple to implement and document
- Works for WordPress and other server-side clients
- Protects both capability endpoints before cost-bearing work begins
- Can be described directly in OpenAPI
- Keeps authentication independent of retrieval and generation logic
- Fits the current single-service architecture without introducing user-management infrastructure

Disadvantages:

- A single shared key does not identify individual clients or users
- All configured clients must be updated when the key is rotated
- A compromised key provides access until it is replaced
- Does not provide roles, permissions, quotas, or per-client revocation

### Send the API key from browser JavaScript

Rejected.

Advantages:

- Allows the browser to call the Python service directly
- Removes the need for a server-side proxy

Disadvantages:

- Exposes the credential through browser developer tools and network requests
- Allows the key to be copied and reused outside the intended interface
- Cannot provide meaningful protection for a public browser application

### Put the API key in the query string or request body

Rejected.

Advantages:

- Easy for basic clients to construct
- Does not require a custom request header

Disadvantages:

- Query-string credentials may appear in URLs, logs, browser history, and monitoring systems
- A body field mixes authentication with the application request model
- Is less compatible with standard API security tooling and OpenAPI authentication schemes

### OAuth, signed tokens, or end-user authentication

Deferred.

Advantages:

- Can identify individual users or client applications
- Can support expiration, scopes, roles, and selective revocation
- Better suited to a multi-user or multi-tenant service

Disadvantages:

- Requires substantially more identity and authorization infrastructure
- Adds token issuance, validation, lifecycle, and client-integration work
- Exceeds the current requirement to authenticate a small number of trusted server-side clients

## Consequences

### Positive

- Search and Answer requests require authentication before retrieval or generation runs.
- The Python API owns and consistently enforces its security boundary regardless of the client.
- The WordPress reference client keeps the Python service credential on the server side.
- Missing authentication configuration fails closed instead of exposing the API.
- Authentication errors follow the same structured error contract as other API errors.
- The generated OpenAPI specification accurately describes the required header.
- Health checks remain simple for hosting and monitoring systems.
- The implementation does not require a full user or identity-management system.

### Negative

- The shared key authenticates the calling application, not the person using it.
- The public WordPress proxy can still be called by site visitors; the API key protects the Python service from direct unauthenticated access, not from all use through the intended public interface.
- One shared key does not provide per-client usage tracking or selective revocation.
- Key rotation requires coordinated configuration changes in the Python service and every trusted client.
- The design does not provide rate limiting, quotas, roles, or user-level authorization.
- Production requests must use HTTPS so the header is protected in transit.

### Future Considerations

Production-readiness work should address:

- Secure secret storage in the hosting environment
- A documented key-generation and rotation procedure
- Prevention of credential exposure in logs and error messages
- Rate limiting and abuse protection at the application or gateway layer
- Monitoring for repeated authentication failures

If the service gains multiple independent clients, replace or extend the single shared key with separately revocable client credentials.

If future use cases require user identity, roles, tenant isolation, or scoped access, evaluate OAuth, short-lived signed tokens, or another identity-aware authentication system rather than extending the shared-key design beyond its intended scope.

Future administrative, indexing, or management endpoints should receive their own explicit authentication and authorization review. They should not inherit the public health-check exception or rely automatically on the same access policy as Search and Answer.
