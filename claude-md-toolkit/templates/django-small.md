# CLAUDE.md

<project_context>
This is a Django web application with approximately {LOC} lines of code. The project follows Django best practices and conventions.
</project_context>

<architecture>

## Django Project Structure

```
{DIRECTORY_TREE}
```

**Key patterns**:
- Apps follow Django app structure (models, views, urls, templates)
- Settings split by environment (if applicable)
- Static files managed through Django's static files system

</architecture>

<critical_rules>

<rule id="migrations" priority="blocking" authority="django-standard">

## Database Migrations

When modifying models, YOU MUST:

1. **Create migrations**: `python manage.py makemigrations`
2. **Review migration files**: Ensure migrations are correct before committing
3. **Test migrations**: Run `python manage.py migrate` in development
4. **Commit migrations**: Include migration files in the same commit as model changes

NEVER commit model changes without corresponding migrations. NEVER edit migration files manually unless absolutely necessary.

</rule>

<rule id="django-security" priority="critical">

## Django Security Standards

YOU MUST follow Django security best practices:

- Use Django's built-in protection against SQL injection, XSS, CSRF
- Never disable CSRF protection without explicit justification
- Keep SECRET_KEY secure (never commit to repository)
- Use Django's authentication system properly
- Validate and sanitize user input

</rule>

<rule id="django-orm" priority="recommended">

## Django ORM Best Practices

- Use `select_related()` and `prefetch_related()` to avoid N+1 queries
- Create database indexes for frequently queried fields
- Use Django's query optimization tools for performance
- Write efficient querysets; avoid loading unnecessary data

</rule>

</critical_rules>

<standards>

## Django Development Standards

- **Models**: Use verbose_name, help_text, and proper field types
- **Views**: Prefer class-based views for CRUD operations
- **URLs**: Use meaningful URL patterns with proper namespacing
- **Templates**: Follow Django template best practices
- **Testing**: Write tests for models, views, and critical business logic

</standards>

<common_commands>

## Common Django Commands

```bash
# Run development server
python manage.py runserver

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Run tests
python manage.py test

# Create superuser
python manage.py createsuperuser

# Collect static files (production)
python manage.py collectstatic

# Django shell
python manage.py shell
```

</common_commands>
