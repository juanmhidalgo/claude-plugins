---
name: security-hardening
description: |
  Use when writing code that handles user input, auth, sessions, or external data. Covers OWASP prevention patterns.
  Do NOT use for general code quality or performance — see dedicated skills.
keywords:
  - security
  - owasp
  - authentication
  - authorization
  - xss
  - injection
triggers:
  - "secure this code"
  - "check for vulnerabilities"
  - "add input validation"
  - "harden authentication"
code-triggers:
  - "eval("
  - "innerHTML"
  - "dangerouslySetInnerHTML"
  - "exec("
  - "password"
  - "authenticate"
  - "authorize"
  - "session"
  - "cookie"
  - "cors"
allowed-tools:
  - Read
  - Grep
  - Glob
agent: security:security-auditor
---

# Security and Hardening

Security is a constraint on every line of code that touches user data, authentication, or external systems. Treat every external input as hostile, every secret as sacred, and every authorization check as mandatory.

## The Three-Tier Boundary System

### Always Do (No Exceptions)

- **Validate all external input** at the system boundary (API routes, form handlers)
- **Parameterize all database queries** — never concatenate user input into SQL
- **Encode output** to prevent XSS (use framework auto-escaping, don't bypass it)
- **Hash passwords** with bcrypt/scrypt/argon2 (salt rounds ≥ 12)
- **Set security headers** (CSP, HSTS, X-Frame-Options, X-Content-Type-Options)
- **Use httpOnly, secure, sameSite cookies** for sessions
- **Audit dependencies** before every release (`npm audit` / `pip audit`)
- **Use HTTPS** for all external communication

### Ask First (Requires Human Approval)

- Adding new authentication flows or changing auth logic
- Storing new categories of sensitive data (PII, payment info)
- Adding new external service integrations
- Changing CORS configuration
- Adding file upload handlers
- Modifying rate limiting or throttling
- Granting elevated permissions or roles

### Never Do

- **Never commit secrets** to version control (API keys, passwords, tokens)
- **Never log sensitive data** (passwords, tokens, full credit card numbers)
- **Never trust client-side validation** as a security boundary
- **Never disable security headers** for convenience
- **Never use `eval()` or `innerHTML`** with user-provided data
- **Never store auth tokens in localStorage** (use httpOnly cookies)
- **Never expose stack traces** or internal error details to users

## OWASP Top 10 Quick Reference

| # | Vulnerability | Prevention |
|---|---------------|------------|
| 1 | Injection | Parameterized queries, ORM, no string concatenation |
| 2 | Broken Auth | Strong hashing, secure sessions, rate limiting |
| 3 | XSS | Framework auto-escaping, DOMPurify for raw HTML |
| 4 | Broken Access Control | Ownership checks on every endpoint, IDOR prevention |
| 5 | Misconfiguration | Helmet/security headers, restrictive CORS, no defaults |
| 6 | Sensitive Data Exposure | Sanitize responses, env vars for secrets, encrypt PII |

For code examples of each, see [owasp-patterns.md](references/owasp-patterns.md).

## Input Validation Pattern

Validate at system boundaries. Trust internal code after validation.

```typescript
import { z } from 'zod';

const CreateUserSchema = z.object({
  email: z.string().email().max(254),
  name: z.string().min(1).max(100).trim(),
});

// Validate at the route handler — internal code trusts the types after this
app.post('/api/users', async (req, res) => {
  const result = CreateUserSchema.safeParse(req.body);
  if (!result.success) {
    return res.status(422).json({
      error: { code: 'VALIDATION_ERROR', message: 'Invalid input', details: result.error.flatten() }
    });
  }
  const user = await userService.create(result.data);
  return res.status(201).json(user);
});
```

## Anti-Rationalizations

| Excuse | Reality |
|--------|---------|
| "This is an internal tool, security doesn't matter" | Internal tools get compromised. Attackers target the weakest link. |
| "We'll add security later" | Retrofitting is 10x harder than building it in. Add it now. |
| "No one would try to exploit this" | Automated scanners will find it. Security by obscurity is not security. |
| "The framework handles security" | Frameworks provide tools, not guarantees. You still need to use them correctly. |
| "It's just a prototype" | Prototypes become production. Security habits from day one. |

## Red Flags

- User input passed directly to queries, shell commands, or HTML rendering
- Secrets in source code or commit history
- API endpoints without authentication or authorization checks
- Wildcard CORS origins in production
- No rate limiting on auth endpoints
- Stack traces exposed to users
- Dependencies with known critical CVEs

## Verification

- [ ] `npm audit` / `pip audit` shows no critical or high vulnerabilities
- [ ] No secrets in source code or git history
- [ ] All user input validated at system boundaries
- [ ] Auth and authorization checked on every protected endpoint
- [ ] Security headers present in responses
- [ ] Error responses don't expose internal details
- [ ] Rate limiting active on auth endpoints
- [ ] `.gitignore` covers .env, *.pem, *.key

For the full security checklist, see [security-checklist.md](references/security-checklist.md).
