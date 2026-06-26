# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 1.x | ✅ |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Email: security@example.com

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fix

You will receive a response within 48 hours. If confirmed, a patch will be released within 7 days and you will be credited in the CHANGELOG.

## Scope

In scope:
- Logic errors in rate limiting or blacklist evaluation that allow bypass
- Race conditions in the storage layer
- Incorrect `Retry-After` header values that could mislead clients

Out of scope:
- Denial of service against ChainShield itself (it is a protection layer, not a protected service)
- Issues in third-party dependencies — report those upstream
