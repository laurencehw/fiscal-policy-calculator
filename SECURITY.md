# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Email:** Open a [GitHub Security Advisory](https://github.com/laurencehw/fiscal-policy-calculator/security/advisories/new) on this repository (preferred), or contact the maintainer directly via the email listed on their GitHub profile.

**Please do not** open a public issue for security vulnerabilities.

## Scope

This project processes publicly available fiscal data (IRS SOI, CBO baselines, FRED). It does not handle personal taxpayer data or authentication credentials in production.

Areas of concern include:
- API key handling (FRED, congress.gov, Anthropic) in environment variables
- SQL injection in the bill tracker SQLite database
- Dependency vulnerabilities in third-party packages

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.x     | Yes       |

## Response timeline

We aim to acknowledge reports within 72 hours and provide a fix or mitigation plan within 30 days.
