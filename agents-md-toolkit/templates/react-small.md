# CLAUDE.md

<project_context>
This is a React application with approximately {LOC} lines of code. The project follows modern React best practices with hooks and functional components.
</project_context>

<architecture>

## React Project Structure

```
{DIRECTORY_TREE}
```

**Key patterns**:
- Functional components with hooks
- Component organization by feature or domain
- Shared components in common directory
- State management using {STATE_MANAGEMENT}

</architecture>

<critical_rules>

<rule id="component-patterns" priority="blocking" authority="react-standard">

## React Component Standards

When creating or modifying components, YOU MUST:

1. **Use functional components** with hooks (avoid class components)
2. **Follow hooks rules**: Only call hooks at the top level, only in React functions
3. **Extract custom hooks** for reusable stateful logic
4. **Memoize expensive computations** using useMemo, useCallback when needed
5. **Handle cleanup** properly in useEffect (return cleanup functions)

NEVER violate hooks rules. NEVER create side effects without proper cleanup.

</rule>

<rule id="state-management" priority="critical">

## State Management Best Practices

YOU MUST manage state correctly:

- Keep state as local as possible; lift only when necessary
- Use proper state management for global state (Context, Redux, Zustand, etc.)
- Avoid prop drilling; use context or state management for deep trees
- Never mutate state directly; always use setState/dispatch
- Handle loading, error, and success states for async operations

</rule>

<rule id="accessibility" priority="recommended">

## Accessibility Standards

Follow accessibility best practices:
- Use semantic HTML elements
- Include proper ARIA attributes when needed
- Ensure keyboard navigation works
- Provide alt text for images
- Test with screen readers when possible

</rule>

</critical_rules>

<standards>

## React Development Standards

- **TypeScript**: Use TypeScript for type safety (if applicable)
- **Props**: Define PropTypes or TypeScript interfaces for all components
- **Naming**: PascalCase for components, camelCase for functions/variables
- **File structure**: One component per file
- **Testing**: Write tests for components using React Testing Library
- **Performance**: Profile and optimize only when necessary

</standards>

<common_commands>

## Common React Commands

```bash
# Start development server
npm start
# or
yarn start

# Run tests
npm test
# or
yarn test

# Build for production
npm run build
# or
yarn build

# Run linter
npm run lint
# or
yarn lint

# Type checking (if using TypeScript)
npm run type-check
# or
yarn type-check
```

</common_commands>
