# CLAUDE.md

<project_context>
This project contains approximately {LOC} lines of code. The codebase is organized following standard development practices.
</project_context>

<architecture>

## Project Structure

```
{DIRECTORY_TREE}
```

**Key patterns**: Follow established patterns in the codebase for consistency.

</architecture>

<critical_rules>

<rule id="code-quality" priority="blocking" authority="repository-standard">

## Code Quality Standards

When making changes, YOU MUST:

1. **Test before committing**: Run test suite and verify all tests pass
2. **Follow existing patterns**: Match the coding style and architecture of the codebase
3. **Handle errors properly**: Include appropriate error handling and validation

NEVER commit code that breaks existing functionality or tests. This is a MANDATORY requirement.

</rule>

<rule id="documentation" priority="recommended">

## Documentation Standards

Keep documentation up to date:
- Update README.md for user-facing changes
- Add code comments for complex logic
- Document new dependencies and their purpose

</rule>

</critical_rules>

<standards>

## Development Standards

- **Testing**: Write tests for new features and bug fixes
- **Dependencies**: Minimize dependencies; justify new additions
- **Commits**: Write clear, descriptive commit messages

</standards>

<common_commands>

## Common Development Commands

```bash
# Run tests
{TEST_COMMAND}

# Build project
{BUILD_COMMAND}

# Start development server
{DEV_COMMAND}
```

</common_commands>
