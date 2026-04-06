# Security Checklist

## Authentication

- [ ] Passwords hashed with bcrypt/scrypt/argon2 (salt rounds ≥ 12)
- [ ] Session tokens are httpOnly, secure, sameSite
- [ ] Login has rate limiting (≤ 10 attempts per 15 minutes)
- [ ] Password reset tokens are time-limited and single-use
- [ ] Failed login attempts are logged (without passwords)
- [ ] MFA available for sensitive accounts (if applicable)

## Authorization

- [ ] Every protected endpoint checks user permissions
- [ ] Users can only access their own resources (no IDOR)
- [ ] Admin actions require admin role verification
- [ ] Role checks happen server-side, not client-side
- [ ] API keys have minimal required scopes

## Input Validation

- [ ] All user input validated at the system boundary
- [ ] Input types, lengths, and formats are enforced
- [ ] SQL queries are parameterized (no string concatenation)
- [ ] HTML output is encoded/escaped by default
- [ ] File uploads restricted by type, size, and content
- [ ] URL redirects validated against an allowlist
- [ ] No `eval()`, `exec()`, or shell commands with user input

## Security Headers

- [ ] Content-Security-Policy (CSP) configured
- [ ] Strict-Transport-Security (HSTS) enabled
- [ ] X-Content-Type-Options: nosniff
- [ ] X-Frame-Options: DENY or SAMEORIGIN
- [ ] Referrer-Policy: strict-origin-when-cross-origin
- [ ] Permissions-Policy configured (camera, microphone, geolocation)

## CORS

- [ ] Origins restricted to known domains (no wildcard in production)
- [ ] Credentials only allowed for trusted origins
- [ ] Methods restricted to what's needed
- [ ] Preflight responses cached appropriately

## Data Protection

- [ ] Secrets in environment variables (not in code or version control)
- [ ] `.gitignore` covers .env, *.pem, *.key, credentials files
- [ ] Sensitive fields excluded from API responses (passwords, tokens, PII)
- [ ] Sensitive fields excluded from logs
- [ ] PII encrypted at rest (if applicable)
- [ ] Database backups encrypted (if applicable)
- [ ] `.env.example` uses placeholder values only

## Dependencies

- [ ] `npm audit` / `pip audit` shows no critical or high vulnerabilities
- [ ] Dependencies are pinned to specific versions
- [ ] No known CVEs in production dependencies
- [ ] Dev dependencies not bundled in production builds
- [ ] Lock file committed and up to date

## Error Handling

- [ ] Error messages are generic (no internal details exposed to users)
- [ ] No stack traces in production error responses
- [ ] Errors logged server-side with request context
- [ ] 500 errors return a safe, consistent response body
- [ ] Unhandled promise rejections / exceptions are caught globally
