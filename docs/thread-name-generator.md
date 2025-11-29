# Thread Name Generator Guide

This guide covers creating custom thread name generators for your AgentFlow application.

## Overview

Thread name generators create meaningful names for AI conversation threads. You can implement custom logic to generate names based on conversation content.

## ThreadNameGenerator Interface

### Import

```python
from agentflow_cli import ThreadNameGenerator
```

### Interface Definition

```python
from abc import ABC, abstractmethod

class ThreadNameGenerator(ABC):
    @abstractmethod
    async def generate_name(self, messages: list[str]) -> str:
        """Generate a thread name from conversation messages.
        
        Args:
            messages: List of message content strings
            
        Returns:
            str: A meaningful thread name
        """
        pass
```

## Basic Implementation

### Simple Static Name

```python
from agentflow_cli import ThreadNameGenerator

class MyNameGenerator(ThreadNameGenerator):
    async def generate_name(self, messages: list[str]) -> str:
        return "MyCustomThreadName"
```

### AI-Powered Name Generation

```python
from agentflow_cli import ThreadNameGenerator
from litellm import acompletion

class MyNameGenerator(ThreadNameGenerator):
    async def generate_name(self, messages: list[str]) -> str:
        """Generate thread name using AI."""
        if not messages:
            return "new-conversation"
        
        # Call AI to generate a meaningful name
        response = await acompletion(
            model="gemini/gemini-2.0-flash-exp",
            messages=[{
                "role": "user",
                "content": f"""Please generate a short thread name (2-3 words, hyphen-separated) 
for this conversation:

```
{chr(10).join(messages)}
```

Reply only with the thread name, nothing else."""
            }],
            max_tokens=20
        )
        
        return response.choices[0].message.content.strip()
```

## Configuration in agentflow.json

Register your generator in the agentflow.json configuration:

```json
{
  "agent": "graph.react:app",
  "thread_name_generator": "graph.thread_name_generator:MyNameGenerator",
  "env": ".env",
  "auth": null
}
```

The path format is: `"module.path:ClassName"`

### Example Directory Structure

```
project/
├── graph/
│   ├── __init__.py
│   ├── react.py
│   └── thread_name_generator.py
├── agentflow.json
└── .env
```

### Example Implementation File

**graph/thread_name_generator.py:**
```python
from agentflow_cli import ThreadNameGenerator
from litellm import acompletion

class MyNameGenerator(ThreadNameGenerator):
    async def generate_name(self, messages: list[str]) -> str:
        """Generate thread names using AI."""
        if not messages:
            return "new-conversation"
        
        response = await acompletion(
            model="gemini/gemini-2.0-flash-exp",
            messages=[{
                "role": "user",
                "content": f"""Generate a thread name for: {chr(10).join(messages[:2])}"""
            }],
            max_tokens=20
        )
        
        return response.choices[0].message.content.strip()
```

## Best Practices

1. **Handle empty messages** - Return a default name when no messages are provided
2. **Include error handling** - Add try-except blocks for external API calls
3. **Keep names reasonable** - Use 2-4 words, hyphen-separated for consistency
4. **Be asynchronous** - Use `async` functions to avoid blocking
5. **Return strings** - Always return a valid string from `generate_name()`

---

## Additional Resources

- [Configuration Guide](./configuration.md) - Complete configuration reference
- [CLI Guide](./cli-guide.md) - Command-line interface documentation
