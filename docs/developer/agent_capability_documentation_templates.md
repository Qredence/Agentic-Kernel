# Agent Capability Documentation Templates

## Introduction

This document provides templates and guidelines for documenting agent capabilities and interfaces in the Agentic Kernel
system. Standardized documentation helps developers understand what each agent can do, how to interact with it, and how
to extend or customize its functionality.

## Table of Contents

1. [Agent Capability Overview](#agent-capability-overview)
2. [Agent Card Template](#agent-card-template)
3. [Capability Documentation Template](#capability-documentation-template)
4. [Interface Documentation Template](#interface-documentation-template)
5. [Input/Output Format Documentation](#inputoutput-format-documentation)
6. [Example Usage Documentation](#example-usage-documentation)
7. [Integration Guide Template](#integration-guide-template)
8. [Customization Guide Template](#customization-guide-template)
9. [Best Practices](#best-practices)
10. [Examples](#examples)

## Agent Capability Overview

Agent capabilities should be documented in a clear, consistent manner that helps users understand what the agent can do
and how to use it effectively. The documentation should cover:

1. **Core Capabilities**: What tasks the agent can perform
2. **Interfaces**: How to interact with the agent
3. **Input/Output Formats**: What data formats the agent accepts and produces
4. **Limitations**: What the agent cannot do or constraints on its operation
5. **Performance Characteristics**: Expected performance for different types of tasks
6. **Integration Points**: How the agent can be integrated with other agents or systems

## Agent Card Template

The Agent Card is a standardized way to describe an agent's capabilities in the A2A protocol. Use this template to
create an Agent Card for your agent:

```markdown
# Agent Card: [Agent Name]

## Basic Information

- **Name**: [Agent name]
- **Version**: [Version number]
- **Description**: [Brief description of the agent's purpose and capabilities]
- **Provider**: [Organization or individual that created the agent]
- **Documentation URL**: [Link to full documentation]

## Capabilities

- **Streaming**: [Yes/No] - [Brief explanation of streaming capabilities]
- **Push Notifications**: [Yes/No] - [Brief explanation of push notification support]
- **State Transition History**: [Yes/No] - [Brief explanation of state history tracking]

## Input/Output Modes

### Input Modes

- **Text**: [Yes/No] - [Supported text formats, e.g., plain text, markdown]
- **Files**: [Yes/No] - [Supported file types and size limits]
- **Structured Data**: [Yes/No] - [Supported data formats, e.g., JSON, YAML]

### Output Modes

- **Text**: [Yes/No] - [Output text formats]
- **Files**: [Yes/No] - [Output file types]
- **Structured Data**: [Yes/No] - [Output data formats]

## Skills

### Skill 1: [Skill Name]

- **ID**: [Unique identifier for the skill]
- **Description**: [Detailed description of what the skill does]
- **Tags**: [List of relevant tags]
- **Examples**: [Brief examples of using this skill]
- **Input Modes**: [Specific input modes for this skill]
- **Output Modes**: [Specific output modes for this skill]

### Skill 2: [Skill Name]

[Same structure as Skill 1]

## Authentication

- **Type**: [Authentication type, e.g., API key, OAuth]
- **Required**: [Yes/No]
- **Description**: [How to authenticate with the agent]
```

## Capability Documentation Template

Use this template to document each capability of your agent in detail:

```markdown
# Capability: [Capability Name]

## Overview

[Brief description of the capability]

## Functionality

[Detailed explanation of what this capability does and how it works]

## Use Cases

[List of common use cases for this capability]

## Requirements

[Prerequisites or requirements for using this capability]

## Limitations

[Known limitations or constraints]

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| [param1]  | [type] | [Yes/No] | [default value] | [description] |
| [param2]  | [type] | [Yes/No] | [default value] | [description] |

## Return Value

[Description of what the capability returns]

## Examples

### Example 1: [Brief description]

```python
# Code example showing how to use this capability
```

### Example 2: [Brief description]

```python
# Another code example
```

## Error Handling

[Description of possible errors and how to handle them]

## Performance Considerations

[Notes on performance characteristics and optimization]

## Related Capabilities

[List of related capabilities with links]

```

## Interface Documentation Template

Use this template to document the interfaces that your agent exposes:

```markdown
# Interface: [Interface Name]

## Overview

[Brief description of the interface]

## Methods

### Method 1: [Method Name]

**Signature**: `[return_type] method_name([param_type] param_name, ...)`

**Description**: [Detailed description of what the method does]

**Parameters**:
- `param_name` ([param_type]): [Parameter description]
- ...

**Returns**: [Description of return value]

**Exceptions**:
- `ExceptionType`: [Condition when this exception is raised]
- ...

**Example**:
```python
# Example code showing how to call this method
```

### Method 2: [Method Name]

[Same structure as Method 1]

## Events

### Event 1: [Event Name]

**Type**: [Event type]

**Description**: [Detailed description of the event]

**Properties**:

- `property_name` ([property_type]): [Property description]
- ...

**Example**:

```python
# Example code showing how to subscribe to this event
```

### Event 2: [Event Name]

[Same structure as Event 1]

## Usage Patterns

[Common patterns for using this interface]

## Thread Safety

[Notes on thread safety and concurrency]

## Versioning

[Information about interface versioning and backward compatibility]

```

## Input/Output Format Documentation

Use this template to document the input and output formats that your agent supports:

```markdown
# Input/Output Format: [Format Name]

## Overview

[Brief description of the format]

## Schema

[Detailed description of the format schema]

```json
{
  "example": "JSON schema or example"
}
```

## Validation Rules

[Rules for validating input/output in this format]

## Examples

### Valid Example 1

```json
{
  "example": "valid data"
}
```

### Invalid Example 1

```json
{
  "example": "invalid data"
}
```

**Reason**: [Explanation of why this example is invalid]

## Conversion

[Information about converting to/from other formats]

## Size Limitations

[Any size limitations for this format]

## Versioning

[Information about format versioning and backward compatibility]

```

## Example Usage Documentation

Use this template to provide comprehensive examples of using your agent:

```markdown
# Example: [Example Name]

## Overview

[Brief description of what this example demonstrates]

## Prerequisites

[List of prerequisites for running this example]

## Setup

```python
# Code for setting up the example
```

## Step 1: [First Step]

```python
# Code for the first step
```

[Explanation of what this step does]

## Step 2: [Second Step]

```python
# Code for the second step
```

[Explanation of what this step does]

## Complete Example

```python
# Complete code example
```

## Expected Output

```
Example output
```

## Common Issues

[List of common issues and how to resolve them]

## Variations

[Variations of this example for different use cases]

```

## Integration Guide Template

Use this template to document how to integrate your agent with other agents or systems:

```markdown
# Integration Guide: [Integration Name]

## Overview

[Brief description of the integration]

## Architecture

[Diagram or description of the integration architecture]

## Prerequisites

[List of prerequisites for this integration]

## Configuration

[Configuration steps for both systems]

### Agent Configuration

```python
# Configuration code for the agent
```

### External System Configuration

```
Configuration for the external system
```

## Authentication

[Authentication requirements and setup]

## Data Flow

[Description of how data flows between systems]

## Error Handling

[How to handle errors in the integration]

## Monitoring

[How to monitor the integration]

## Limitations

[Known limitations of the integration]

## Troubleshooting

[Common issues and solutions]

```

## Customization Guide Template

Use this template to document how to customize or extend your agent:

```markdown
# Customization Guide: [Customization Type]

## Overview

[Brief description of what can be customized]

## Extension Points

[List and description of extension points]

## Creating a Custom [Component]

```python
# Example code for creating a custom component
```

[Explanation of the code]

## Configuration Options

[List of configuration options for customization]

## Best Practices

[Best practices for customization]

## Testing Custom Components

[How to test custom components]

## Deployment Considerations

[Considerations for deploying custom components]

## Examples

### Example 1: [Brief description]

```python
# Example code
```

### Example 2: [Brief description]

```python
# Example code
```

```

## Best Practices

When documenting agent capabilities and interfaces, follow these best practices:

1. **Be Comprehensive**: Document all capabilities, interfaces, and parameters
2. **Use Consistent Terminology**: Use the same terms throughout your documentation
3. **Provide Examples**: Include examples for all capabilities and interfaces
4. **Document Limitations**: Clearly state what the agent cannot do
5. **Keep Documentation Updated**: Update documentation when the agent changes
6. **Use Markdown Formatting**: Use headings, lists, tables, and code blocks for clarity
7. **Include Error Handling**: Document possible errors and how to handle them
8. **Consider Different Audiences**: Provide both high-level overviews and detailed technical information
9. **Link Related Documentation**: Cross-reference related documentation
10. **Include Version Information**: Specify which version of the agent the documentation applies to

## Examples

### Example Agent Card

```markdown
# Agent Card: CodeAssistant

## Basic Information

- **Name**: CodeAssistant
- **Version**: 1.0.0
- **Description**: An agent that assists with coding tasks, including code generation, analysis, and refactoring.
- **Provider**: Agentic Kernel Team
- **Documentation URL**: https://example.com/docs/codeassistant

## Capabilities

- **Streaming**: Yes - Provides incremental code generation results
- **Push Notifications**: No
- **State Transition History**: Yes - Tracks the history of code changes

## Input/Output Modes

### Input Modes

- **Text**: Yes - Plain text, markdown, and code snippets
- **Files**: Yes - Source code files up to 10MB
- **Structured Data**: Yes - JSON specifications and requirements

### Output Modes

- **Text**: Yes - Generated code and explanations
- **Files**: Yes - Complete source code files
- **Structured Data**: Yes - Code analysis results in JSON format

## Skills

### Skill 1: Code Generation

- **ID**: code_generation
- **Description**: Generates code based on natural language descriptions or requirements
- **Tags**: ["code", "generation", "programming"]
- **Examples**: ["Generate a Python function to sort a list", "Create a React component for a login form"]
- **Input Modes**: ["text", "structured_data"]
- **Output Modes**: ["text", "file"]

### Skill 2: Code Analysis

- **ID**: code_analysis
- **Description**: Analyzes code for bugs, performance issues, and style violations
- **Tags**: ["code", "analysis", "debugging"]
- **Examples**: ["Find bugs in this function", "Analyze the time complexity of this algorithm"]
- **Input Modes**: ["text", "file"]
- **Output Modes**: ["text", "structured_data"]

## Authentication

- **Type**: API Key
- **Required**: Yes
- **Description**: Provide an API key in the X-API-Key header for all requests
```

### Example Capability Documentation

```markdown
# Capability: Code Generation

## Overview

The Code Generation capability allows the CodeAssistant agent to generate code based on natural language descriptions or requirements.

## Functionality

This capability uses advanced language models to translate natural language descriptions into executable code. It supports multiple programming languages and can generate various types of code, from simple functions to complex classes and modules.

## Use Cases

- Generating boilerplate code
- Implementing algorithms based on descriptions
- Creating functions based on specifications
- Translating code between programming languages
- Implementing design patterns

## Requirements

- Clear description of the desired code functionality
- Specification of the target programming language
- Any constraints or requirements (e.g., performance, compatibility)

## Limitations

- May require refinement for complex algorithms
- Cannot guarantee optimal performance for all generated code
- Limited to supported programming languages
- Maximum input size of 4000 tokens

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| description | string | Yes | - | Natural language description of the code to generate |
| language | string | Yes | - | Target programming language (e.g., "python", "javascript") |
| include_comments | boolean | No | true | Whether to include comments in the generated code |
| style | string | No | "standard" | Code style to use (e.g., "standard", "google", "pep8") |
| max_tokens | integer | No | 1000 | Maximum number of tokens in the generated code |

## Return Value

Returns a string containing the generated code, or a file object if the code is large.

## Examples

### Example 1: Generate a simple Python function

```python
from agentic_kernel.agents import CodeAssistant

agent = CodeAssistant()
code = await agent.generate_code(
    description="A function that calculates the factorial of a number",
    language="python",
    include_comments=True
)
print(code)
```

Output:

```python
def factorial(n):
    """
    Calculate the factorial of a number.
    
    Args:
        n: A non-negative integer
        
    Returns:
        The factorial of n
    """
    if n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n - 1)
```

## Error Handling

- If the description is unclear, the agent will request clarification
- If the language is unsupported, a UnsupportedLanguageError will be raised
- If the generated code exceeds the token limit, a TokenLimitExceededError will be raised

## Performance Considerations

- Complex code generation may take longer to process
- Consider using streaming for large code generation tasks
- Providing more detailed descriptions generally results in better code

## Related Capabilities

- [Code Analysis](code_analysis.md)
- [Code Refactoring](code_refactoring.md)
- [Test Generation](test_generation.md)

```

By using these templates and following the best practices, you can create comprehensive, consistent documentation for your agents' capabilities and interfaces, making it easier for developers to understand and use your agents effectively.