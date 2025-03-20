# Coding Conventions

## Core Principles

- Prefer simple, procedural code over complex object-oriented patterns
- Avoid unnecessary abstractions and complexity
- Functions should do one thing and do it well
- State should be explicit, not hidden in objects

## Structure and Organization

- Use plain functions over classes when possible
- When classes are needed, prefer simple data classes or structs
- Keep function signatures clear and explicit
- Group related functions together
- Place utility functions in separate modules

## Code Style

- Use type hints for function parameters and return values
- Write clear, descriptive function and variable names
- Include docstrings for public functions
- Keep functions focused and relatively short (under 50 lines preferred)
- Use immutable data structures when possible

## Dependencies and Libraries

- Minimize external dependencies
- Prefer standard library solutions when available
- Use established, well-maintained libraries when needed
- Avoid complex frameworks unless absolutely necessary

## Error Handling

- Use explicit error handling with try/except
- Return errors as values when appropriate
- Avoid swallowing exceptions
- Log errors with context for debugging

## Testing

- Write unit tests for core functionality
- Keep tests simple and focused
- Use table-driven tests when appropriate
- Test error cases explicitly

## Documentation

- Document function contracts clearly
- Include usage examples for complex functions
- Document any non-obvious design decisions
- Keep documentation close to the code it describes
