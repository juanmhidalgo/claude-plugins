# OWASP Top 10 Prevention Patterns

## 1. Injection (SQL, NoSQL, OS Command)

```typescript
// BAD: SQL injection via string concatenation
const query = `SELECT * FROM users WHERE id = '${userId}'`;

// GOOD: Parameterized query
const user = await db.query('SELECT * FROM users WHERE id = $1', [userId]);

// GOOD: ORM with parameterized input
const user = await prisma.user.findUnique({ where: { id: userId } });
```

```python
# BAD: SQL injection
cursor.execute(f"SELECT * FROM users WHERE id = '{user_id}'")

# GOOD: Parameterized query
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# GOOD: ORM
user = User.objects.get(id=user_id)
```

## 2. Broken Authentication

```typescript
// Password hashing
import { hash, compare } from 'bcrypt';

const SALT_ROUNDS = 12;
const hashedPassword = await hash(plaintext, SALT_ROUNDS);
const isValid = await compare(plaintext, hashedPassword);

// Session configuration
app.use(session({
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    maxAge: 24 * 60 * 60 * 1000,  // 24 hours
  },
}));
```

## 3. Cross-Site Scripting (XSS)

```typescript
// BAD: Rendering user input as HTML
element.innerHTML = userInput;

// GOOD: Framework auto-escaping (React does this by default)
return <div>{userInput}</div>;

// If you MUST render HTML, sanitize first
import DOMPurify from 'dompurify';
const clean = DOMPurify.sanitize(userInput);
```

## 4. Broken Access Control

```typescript
// Always check authorization, not just authentication
app.patch('/api/tasks/:id', authenticate, async (req, res) => {
  const task = await taskService.findById(req.params.id);

  // Check that the authenticated user owns this resource
  if (task.ownerId !== req.user.id) {
    return res.status(403).json({
      error: { code: 'FORBIDDEN', message: 'Not authorized to modify this task' }
    });
  }

  const updated = await taskService.update(req.params.id, req.body);
  return res.json(updated);
});
```

## 5. Security Misconfiguration

```typescript
// Security headers with helmet
import helmet from 'helmet';
app.use(helmet());

// Content Security Policy
app.use(helmet.contentSecurityPolicy({
  directives: {
    defaultSrc: ["'self'"],
    scriptSrc: ["'self'"],
    styleSrc: ["'self'", "'unsafe-inline'"],
    imgSrc: ["'self'", 'data:', 'https:'],
    connectSrc: ["'self'"],
  },
}));

// CORS — restrict to known origins
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || 'http://localhost:3000',
  credentials: true,
}));
```

## 6. Sensitive Data Exposure

```typescript
// Never return sensitive fields in API responses
function sanitizeUser(user: UserRecord): PublicUser {
  const { passwordHash, resetToken, ...publicFields } = user;
  return publicFields;
}

// Use environment variables for secrets
const API_KEY = process.env.STRIPE_API_KEY;
if (!API_KEY) throw new Error('STRIPE_API_KEY not configured');
```

## Rate Limiting

```typescript
import rateLimit from 'express-rate-limit';

// General API rate limit
app.use('/api/', rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
}));

// Stricter limit for auth endpoints
app.use('/api/auth/', rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 10,
}));
```

## File Upload Safety

```typescript
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_SIZE = 5 * 1024 * 1024; // 5MB

function validateUpload(file: UploadedFile) {
  if (!ALLOWED_TYPES.includes(file.mimetype)) {
    throw new ValidationError('File type not allowed');
  }
  if (file.size > MAX_SIZE) {
    throw new ValidationError('File too large (max 5MB)');
  }
  // Don't trust the file extension — check magic bytes if critical
}
```

## Secrets Management

```
.env files:
  ├── .env.example  → Committed (template with placeholder values)
  ├─��� .env          → NOT committed (real secrets)
  └── .env.local    → NOT committed (local overrides)

.gitignore must include:
  .env
  .env.local
  .env.*.local
  *.pem
  *.key
```

Pre-commit check:
```bash
git diff --cached | grep -iE "password|secret|api_key|token|private_key"
```

## npm audit Triage Decision Tree

```
npm audit reports a vulnerability
├── Severity: critical or high
│   ├── Vulnerable code reachable in your app?
│   │   ├── YES → Fix immediately (update, patch, or replace)
│   │   └── NO (dev-only dep, unused code path) → Fix soon, not a blocker
│   └── Fix available?
│       ├── YES → Update to patched version
│       └── NO → Check workarounds, consider replacing, or allowlist with review date
├── Severity: moderate
│   ├── Reachable in production? → Fix in next release cycle
│   └── Dev-only? → Fix when convenient
└── Severity: low
    └── Track and fix during regular dependency updates
```

When deferring a fix, document the reason and set a review date.
