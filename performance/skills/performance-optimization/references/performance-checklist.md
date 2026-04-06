# Performance Checklist

## Frontend

### Images
- [ ] Use modern formats (WebP/AVIF) with fallbacks
- [ ] Responsive `srcset` and `sizes` attributes
- [ ] Explicit `width` and `height` attributes (prevents CLS)
- [ ] Lazy loading for below-the-fold images (`loading="lazy"`)
- [ ] Images optimized and compressed (< 200KB above the fold)

### JavaScript
- [ ] Initial bundle < 200KB gzipped
- [ ] Code splitting with dynamic `import()` for routes/features
- [ ] Tree shaking enabled (no importing entire libraries)
- [ ] No render-blocking scripts in `<head>` (use `defer` or `async`)
- [ ] Web Workers for heavy computation (if applicable)
- [ ] Memoization applied where measured impact exists (not preemptively)

### CSS
- [ ] Critical CSS inlined for above-the-fold content
- [ ] No render-blocking stylesheets for non-critical CSS
- [ ] `font-display: swap` for web fonts
- [ ] System font stack as fallback

### Network
- [ ] Cache-Control headers set for static assets (long max-age + immutable)
- [ ] `preconnect` to critical third-party origins
- [ ] Minimize redirect chains
- [ ] Compression enabled (gzip/brotli)

### Rendering
- [ ] No layout thrashing (read then write, not interleaved)
- [ ] GPU-accelerated animations (`transform`, `opacity` only)
- [ ] Virtualized long lists (> 100 items)
- [ ] Unnecessary re-renders identified and fixed (stable refs, memo where needed)

## Backend

### Database
- [ ] No N+1 query patterns (use `include`/`select_related`/JOINs)
- [ ] Proper indexes on frequently queried columns
- [ ] Pagination on all list endpoints (cursor or offset)
- [ ] Connection pooling configured
- [ ] Slow query logging enabled in development

### API
- [ ] Response times < 200ms (p95)
- [ ] No synchronous heavy computation in request handlers
- [ ] Bulk operations for batch processing
- [ ] Response compression enabled
- [ ] Appropriate caching for hot data (in-memory or HTTP)

### Infrastructure
- [ ] CDN for static assets
- [ ] Health check endpoints
- [ ] Horizontal scaling path defined (if needed)
- [ ] Monitoring and alerting on response times

## Common Anti-Patterns and Fixes

### N+1 Queries
```typescript
// BAD: One query per item
const tasks = await db.tasks.findMany();
for (const task of tasks) {
  task.owner = await db.users.findUnique({ where: { id: task.ownerId } });
}

// GOOD: Single query with join
const tasks = await db.tasks.findMany({ include: { owner: true } });
```

### Unbounded Data Fetching
```typescript
// BAD: Fetch all records
const allTasks = await db.tasks.findMany();

// GOOD: Paginated
const tasks = await db.tasks.findMany({
  take: 20,
  skip: (page - 1) * 20,
  orderBy: { createdAt: 'desc' },
});
```

### Large Bundle from Full Library Import
```typescript
// BAD: Imports everything
import { format } from 'date-fns';

// GOOD: Tree-shakable import
import { format } from 'date-fns/format';

// GOOD: Dynamic import for heavy, rare features
const ChartLib = lazy(() => import('./ChartLibrary'));
```

### Unnecessary Re-renders
```tsx
// BAD: New object every render, children always re-render
function TaskList() {
  return <Filters options={{ sortBy: 'date', order: 'desc' }} />;
}

// GOOD: Stable reference
const DEFAULT_OPTIONS = { sortBy: 'date', order: 'desc' } as const;
function TaskList() {
  return <Filters options={DEFAULT_OPTIONS} />;
}
```

### Missing HTTP Caching
```typescript
// Static assets: cache for 1 year with content hashing
app.use('/static', express.static('public', {
  maxAge: '1y',
  immutable: true,
}));

// API responses: cache for 5 minutes
res.set('Cache-Control', 'public, max-age=300');
```

## Measurement Commands

```bash
# Bundle analysis
npx webpack-bundle-analyzer stats.json
npx source-map-explorer dist/main.js

# Lighthouse
npx lighthouse https://localhost:3000 --output json --output html

# Python profiling
python -m cProfile -s cumulative app.py
python -m timeit -s "from module import func" "func()"

# Database query timing (enable in your ORM)
# Prisma: set LOG_LEVEL=query
# Django: django.db.connection.queries
```
