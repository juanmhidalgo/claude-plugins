# CLAUDE.md

<project_context>
This is a FastAPI application with approximately {LOC} lines of code. The project follows FastAPI and modern Python async best practices.
</project_context>

<architecture>

## FastAPI Project Structure

```
{DIRECTORY_TREE}
```

**Key patterns**:
- API routes organized by domain/resource
- Pydantic models for request/response validation
- Dependency injection for shared logic
- Async/await for I/O operations

</architecture>

<critical_rules>

<rule id="pydantic-validation" priority="blocking" authority="fastapi-standard">

## Request/Response Validation

When creating API endpoints, YOU MUST:

1. **Define Pydantic models** for all request bodies and responses
2. **Use proper types** (str, int, List, Optional, etc.) with validators
3. **Add descriptions** using Field() for API documentation
4. **Validate data** - let Pydantic handle validation, never bypass it

NEVER accept unvalidated input. NEVER return unstructured responses. This ensures API contract safety.

</rule>

<rule id="async-patterns" priority="critical">

## Async/Await Best Practices

YOU MUST follow async patterns correctly:

- Use `async def` for endpoints making I/O calls (database, HTTP, file operations)
- Use `def` (sync) for CPU-bound operations or when no I/O is involved
- Never mix blocking I/O in async functions without `asyncio.to_thread()`
- Use async database libraries (asyncpg, motor, etc.) with async ORMs

Incorrect async usage causes performance degradation and blocking.

</rule>

<rule id="dependency-injection" priority="recommended">

## Dependency Injection

Use FastAPI's dependency injection system:
- Database sessions via dependencies
- Authentication/authorization via dependencies
- Shared logic as reusable dependencies
- Avoid global state; prefer dependency injection

</rule>

</critical_rules>

<standards>

## FastAPI Development Standards

- **Endpoints**: Use proper HTTP methods (GET, POST, PUT, DELETE, PATCH)
- **Status codes**: Return appropriate HTTP status codes (200, 201, 400, 404, 500)
- **Documentation**: Auto-generated docs via Pydantic models and docstrings
- **Error handling**: Use HTTPException for API errors with clear messages
- **Testing**: Write tests using TestClient from fastapi.testclient

</standards>

<common_commands>

## Common FastAPI Commands

```bash
# Run development server (with auto-reload)
uvicorn main:app --reload

# Run development server on specific host/port
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
pytest

# Run tests with coverage
pytest --cov=app tests/

# Type checking
mypy .

# Linting
ruff check .

# Format code
ruff format .
```

</common_commands>
