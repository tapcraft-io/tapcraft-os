# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly by emailing **security@tapcraft.io** instead of opening a public issue.

We will acknowledge your report within 48 hours and aim to provide a fix or mitigation within 7 days for critical issues.

## Security Model

Tapcraft OS is designed as a **self-hosted, single-tenant** platform. The security model assumes:

- **You control the deployment environment.** Tapcraft is not a multi-tenant SaaS — it runs on your infrastructure.
- **API key authentication** protects all API endpoints. A key is auto-generated on first startup if not configured. It can be set via the `TAPCRAFT_API_KEY` environment variable.
- **Secrets are encrypted at rest** using Fernet symmetric encryption (via the `cryptography` library). The encryption key is configured via `TAPCRAFT_SECRET_KEY`.
- **No built-in TLS** — Tapcraft expects a reverse proxy (nginx, Caddy, Traefik, etc.) or cloud load balancer to terminate TLS in production.

## Best Practices for Deployment

- Always run behind a TLS-terminating reverse proxy in production.
- Set `TAPCRAFT_API_KEY` and `TAPCRAFT_SECRET_KEY` explicitly — do not rely on auto-generation in production.
- Restrict network access to the Temporal UI port (8233) to trusted networks.
- Review activity code before deploying — activities run arbitrary Python and have access to the host network and secrets.
