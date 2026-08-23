# Security Policy

## Protect Secrets

- Keep `.env` at the project root and never commit it.
- Use Vercel environment variables for deployed secrets.
- Never place API keys in `index.html`, screenshots, logs, or issue reports.
- Rotate a credential immediately if it is exposed.

## Public Deployment Risks

The current Flask API has no user authentication, authorization, rate limiting, or quota enforcement. A public deployment can therefore be abused to consume AI provider quota or serverless resources. Add an authenticated gateway and request limits before production use.

The service accepts remote URLs and passes them to media tooling. Restrict allowed hosts and validate URLs if the endpoint is exposed to untrusted users. Avoid processing private or confidential media through third-party transcription and AI providers.

## Reporting a Vulnerability

Do not publish credentials or exploit details in a public issue. Contact the project owner privately with:

- affected endpoint or file
- reproducible steps
- impact assessment
- suggested mitigation, if known

No public security-support SLA has been established yet.