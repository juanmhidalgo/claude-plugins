# Technical Decision Examples

## Example 1: N+1 Query Fix

```
Review feedback: "Fix N+1 query in get_user_posts()"

❌ WRONG: Just add select_related() and move on

✅ RIGHT:
"This fix requires a decision:

**Issue:** N+1 query in get_user_posts()

**Options:**
1. select_related('author') - Eager load in single query
   - Pros: Simple, handles this case
   - Cons: Always loads author even when not needed

2. Prefetch at view level - Load in batch where needed
   - Pros: More control, only when needed
   - Cons: More code, need to update multiple views

3. Cached property - Cache author on first access
   - Pros: Lazy loading, no query changes
   - Cons: Cache invalidation complexity

**Recommendation:** Option 1 (select_related) - this view always displays author info, so eager loading makes sense here.

Which approach?"
```

## Example 2: Error Handling

```
Review feedback: "Add proper error handling to API endpoint"

❌ WRONG: Add try/catch with generic error response

✅ RIGHT:
"This fix requires a decision:

**Issue:** Missing error handling in /api/users endpoint

**Options:**
1. Generic exception handler - Catch all, return 500
   - Pros: Quick, covers everything
   - Cons: Hides specific errors, poor debugging

2. Specific exception types - Custom exceptions for each case
   - Pros: Clear error messages, better client handling
   - Cons: More code, need to define exception hierarchy

3. Result pattern - Return Result<T, Error> types
   - Pros: Type-safe, explicit error handling
   - Cons: Different from rest of codebase, learning curve

**Recommendation:** Option 2 - matches existing patterns in other endpoints.

Which approach?"
```

## Example 3: Simple Fix (No Decision Needed)

```
Review feedback: "Missing null check before accessing user.email"

✅ Just implement:
"Added null check at line 45. Returns early if user is None."

No decision needed - single correct solution.
```

## Example 4: Related Decisions

```
"These 3 fixes are related and should be decided together:

1. Error handling approach (affects #2 and #3)
2. Logging format (depends on #1)
3. Response structure (depends on #1)

[Present options for each, showing dependencies]"
```
