# Security Policy

ANNEX handles media content and generates credibility assessments for people
learning about information online. Security is a priority: user media, analysis
results, and access control are all sensitive.

## Supported versions

| Version | Status        |
| ------- | ------------- |
| 0.1.x   | Supported     |
| < 0.1   | Not supported |

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities. Instead,
report them privately so the issue can be fixed before it is disclosed.

How to report:

- Open a private advisory via the repository's *Security* tab
  (if available).
- Otherwise, email the maintainers directly (see the project contact in
  `GOVERNANCE.md`).

Please include:

- A description of the vulnerability and its impact.
- Steps to reproduce, or a minimal proof of concept.
- Affected component(s) and versions.

You should receive an acknowledgement within 48 hours. We will work with you to
confirm the issue and coordinate a fix, and we will credit you in the advisory
unless you prefer to remain anonymous.

## Scope

In scope:

- Authentication and authorization bypass (Supabase Auth / JWT handling).
- Unauthorized access to user media or analysis data (RLS rules).
- Prompt injection or data exfiltration via media/text submitted for analysis.
- Secrets management and deployment configuration.

Out of scope:

- Issues in upstream dependencies without a workaround in this codebase.
- Social engineering or phishing.
- Any attack requiring physical access to a machine running the service.

## Security practices

- Secrets are injected from Secret Manager at deploy time; never commit them.
- Access control is enforced with PostgreSQL Row Level Security; keep it intact
  when adding queries or tables.
- Core (domain + application) code stays free of framework imports; validate and
  sanitize all input at the interface layer.
- Pin and review dependencies (`pyproject.toml`), and keep them updated.