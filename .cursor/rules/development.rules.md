# Development Rules

## Planning & Tasks

- Create plan before implementation
- Update `tasks.md` regularly
- Document design decisions

## Testing

- Write unit tests for core logic
- Write integration tests for agent interactions
- Test complex paths thoroughly
- Test streaming functionality explicitly

## Configuration

- Use environment variables for sensitive data
- Define configurations in `~/.cursor/mcp.json`
- Use central config modules
- Log configuration loading status

## Dependencies

- Keep `requirements.txt` updated
- Check for package conflicts
- Use specific version numbers
- Document version compatibility

## Code Style

- Follow PEP 8
- Use descriptive names
- Comment only non-trivial logic
- Use backticks for code in comments
- Use proper type hints for async generators

## Error Handling

- Use structured logging with levels
- Include stack traces for debugging
- Handle streaming errors gracefully
- Provide user-friendly error messages

## Version Control

- Commit frequently
- Write clear commit messages
- Use feature branches
- Follow Git flow

## Documentation

- Document agent interactions
- Keep API documentation updated
- Include usage examples
- Document streaming patterns

## Security

- Never commit credentials
- Validate user inputs
- Handle errors securely
- Log securely (no sensitive data)

## Streaming Implementation

- Use appropriate async patterns
- Handle partial responses correctly
- Maintain state during streaming
- Clean up resources properly
