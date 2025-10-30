# Thread Name Generator Guide

This guide covers using the AI Thread Name Generator to create meaningful, human-friendly names for conversation threads in your AgentFlow application.

## Table of Contents

- [Overview](#overview)
- [AIThreadNameGenerator](#aithreadnamegenerator)
- [Custom Thread Name Generator](#custom-thread-name-generator)
- [Configuration](#configuration)
- [Best Practices](#best-practices)
- [Examples](#examples)

---

## Overview

Thread name generators create meaningful, memorable names for AI conversation threads. Instead of using UUIDs like `a1b2c3d4-e5f6-7890`, you get human-friendly names like `thoughtful-dialogue` or `exploring-ideas`.

### Features

- ✅ **Human-friendly** - Easy to remember and reference
- ✅ **Varied** - Multiple patterns prevent repetition
- ✅ **Professional** - Suitable for production use
- ✅ **Customizable** - Implement your own naming logic
- ✅ **No external dependencies** - Uses Python's built-in `secrets` module

---

## AIThreadNameGenerator

The default thread name generator included with AgentFlow.

### Import

```python
from agentflow_cli.src.app.utils.thread_name_generator import AIThreadNameGenerator
```

### Basic Usage

```python
# Create generator
generator = AIThreadNameGenerator()

# Generate a name
name = generator.generate_name()
print(name)
# Output: "thoughtful-dialogue"
```

### Name Patterns

The generator uses three patterns:

#### 1. Simple Pattern (Adjective + Noun)

```python
name = generator.generate_simple_name()
# Examples:
# - "thoughtful-dialogue"
# - "creative-exploration"
# - "analytical-discussion"
# - "innovative-conversation"
```

#### 2. Action Pattern (Verb + Noun)

```python
name = generator.generate_action_name()
# Examples:
# - "exploring-ideas"
# - "building-solutions"
# - "discovering-insights"
# - "crafting-responses"
```

#### 3. Compound Pattern (Adjective + Noun)

```python
name = generator.generate_compound_name()
# Examples:
# - "deep-dive"
# - "bright-spark"
# - "fresh-perspective"
# - "open-dialogue"
```

### Custom Separator

```python
# Default separator is hyphen
name = generator.generate_name("-")
# Output: "thoughtful-dialogue"

# Use underscore
name = generator.generate_name("_")
# Output: "thoughtful_dialogue"

# Use space
name = generator.generate_name(" ")
# Output: "thoughtful dialogue"

# No separator
name = generator.generate_name("")
# Output: "thoughtfuldialogue"
```

### Available Adjectives

The generator includes 50+ carefully selected adjectives:

**Intellectual:**
- thoughtful, insightful, analytical, logical, strategic
- methodical, systematic, comprehensive, detailed, precise

**Creative:**
- creative, imaginative, innovative, artistic, expressive
- original, inventive, inspired, visionary, whimsical

**Emotional/Social:**
- engaging, collaborative, meaningful, productive, harmonious
- enlightening, empathetic, supportive, encouraging, uplifting

**Dynamic:**
- dynamic, energetic, vibrant, lively, spirited
- active, flowing, adaptive, responsive, interactive

**Quality-focused:**
- focused, dedicated, thorough, meticulous, careful
- patient, persistent, resilient, determined, ambitious

### Available Nouns

The generator includes 60+ context-appropriate nouns:

**Conversation-related:**
- dialogue, conversation, discussion, exchange, chat
- consultation, session, meeting, interaction, communication

**Journey/Process:**
- journey, exploration, adventure, quest, voyage
- expedition, discovery, investigation, research, study

**Conceptual:**
- insight, vision, perspective, understanding, wisdom
- knowledge, learning, growth, development, progress

**Solution-oriented:**
- solution, approach, strategy, method, framework
- plan, blueprint, pathway, route, direction

**Creative/Abstract:**
- canvas, story, narrative, symphony, composition
- creation, masterpiece, design, pattern, concept

**Collaborative:**
- partnership, collaboration, alliance, connection, bond
- synergy, harmony, unity, cooperation, teamwork

### Action Patterns

The generator includes 8 action verbs with associated targets:

```python
{
    "exploring": ["ideas", "concepts", "possibilities", "mysteries", "frontiers"],
    "building": ["solutions", "understanding", "connections", "frameworks"],
    "discovering": ["insights", "patterns", "answers", "truths", "wisdom"],
    "crafting": ["responses", "solutions", "stories", "strategies"],
    "navigating": ["challenges", "questions", "complexities", "paths"],
    "unlocking": ["potential", "mysteries", "possibilities", "creativity"],
    "weaving": ["ideas", "stories", "connections", "patterns"],
    "illuminating": ["concepts", "mysteries", "paths", "truths"]
}
```

---

## Custom Thread Name Generator

Implement your own thread name generator for custom logic.

### Interface

```python
from abc import ABC, abstractmethod

class ThreadNameGenerator(ABC):
    @abstractmethod
    async def generate_name(self, messages: list[str]) -> str:
        """Generate a thread name using the list of message text.
        
        Args:
            messages: List of message content strings
            
        Returns:
            str: A meaningful thread name
        """
        pass
```

### Basic Custom Generator

```python
# generators/custom.py
from agentflow_cli import ThreadNameGenerator
import uuid

class UUIDGenerator(ThreadNameGenerator):
    async def generate_name(self, messages: list[str]) -> str:
        """Generate UUID-based thread names."""
        return f"thread-{uuid.uuid4().hex[:8]}"
```

### Message-Based Generator

```python
# generators/smart.py
from agentflow_cli import ThreadNameGenerator
import re

class SmartGenerator(ThreadNameGenerator):
    async def generate_name(self, messages: list[str]) -> str:
        """Generate names based on message content."""
        if not messages:
            return "new-conversation"
        
        # Get first message
        first_message = messages[0].lower()
        
        # Extract key topics
        if "weather" in first_message:
            return "weather-inquiry"
        elif "help" in first_message or "support" in first_message:
            return "help-request"
        elif "?" in first_message:
            return "question-thread"
        else:
            # Extract first noun
            words = re.findall(r'\b[a-z]{4,}\b', first_message)
            if words:
                return f"{words[0]}-discussion"
            return "general-chat"
```

### AI-Powered Generator

```python
# generators/ai_powered.py
from agentflow_cli import ThreadNameGenerator
from litellm import acompletion

class AINameGenerator(ThreadNameGenerator):
    async def generate_name(self, messages: list[str]) -> str:
        """Use AI to generate contextual thread names."""
        if not messages:
            return "new-conversation"
        
        # Create prompt
        prompt = f"""Generate a short, descriptive thread name (2-3 words, hyphen-separated)
for a conversation that starts with: "{messages[0][:100]}"

Examples: "weather-inquiry", "technical-support", "creative-brainstorm"

Thread name:"""
        
        try:
            response = await acompletion(
                model="gemini/gemini-2.0-flash-exp",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20
            )
            
            name = response.choices[0].message.content.strip()
            # Clean up the name
            name = name.lower().replace(" ", "-")
            name = re.sub(r'[^a-z0-9-]', '', name)
            
            return name if name else "ai-conversation"
        except Exception:
            # Fallback to default
            return "ai-conversation"
```

### Database-Based Generator

```python
# generators/database.py
from agentflow_cli import ThreadNameGenerator
from sqlalchemy.orm import Session

class DatabaseGenerator(ThreadNameGenerator):
    def __init__(self, db: Session):
        self.db = db
    
    async def generate_name(self, messages: list[str]) -> str:
        """Generate sequential names with database counter."""
        # Get user from messages (assuming it's available)
        user_id = self.extract_user_id(messages)
        
        # Get user's thread count
        count = self.db.query(Thread)\
            .filter(Thread.user_id == user_id)\
            .count()
        
        return f"conversation-{count + 1}"
```

---

## Configuration

### In agentflow.json

```json
{
  "agent": "graph.react:app",
  "thread_name_generator": "generators.custom:MyGenerator"
}
```

### Default (No Configuration)

If not specified, the system uses `AIThreadNameGenerator`:

```json
{
  "agent": "graph.react:app",
  "thread_name_generator": null
}
```

### Custom Generator Setup

**generators/custom.py:**
```python
from agentflow_cli import ThreadNameGenerator

class MyGenerator(ThreadNameGenerator):
    async def generate_name(self, messages: list[str]) -> str:
        # Your logic here
        return "custom-thread-name"

# Create instance
generator = MyGenerator()
```

**agentflow.json:**
```json
{
  "thread_name_generator": "generators.custom:generator"
}
```

---

## Best Practices

### 1. Keep Names Short

```python
# ✅ Good: Short and memorable
"thoughtful-dialogue"
"exploring-ideas"

# ❌ Bad: Too long
"very-thoughtful-and-detailed-dialogue-about-important-topics"
```

### 2. Use Lowercase with Hyphens

```python
# ✅ Good: Consistent format
"creative-exploration"

# ❌ Bad: Inconsistent
"CreativeExploration"
"creative_exploration"
"Creative-Exploration"
```

### 3. Make Names Meaningful

```python
# ✅ Good: Descriptive
"weather-inquiry"
"technical-support"

# ❌ Bad: Generic
"thread-1"
"conversation"
```

### 4. Handle Empty Messages

```python
async def generate_name(self, messages: list[str]) -> str:
    if not messages:
        return "new-conversation"  # Fallback
    
    # Process messages
    ...
```

### 5. Add Error Handling

```python
async def generate_name(self, messages: list[str]) -> str:
    try:
        # Your logic
        return self.process_messages(messages)
    except Exception as e:
        logger.error(f"Error generating thread name: {e}")
        return "conversation"  # Fallback
```

### 6. Consider Performance

```python
# ✅ Good: Fast generation
async def generate_name(self, messages: list[str]) -> str:
    # Simple, fast logic
    return f"{random.choice(adjectives)}-{random.choice(nouns)}"

# ⚠️ Caution: May be slow
async def generate_name(self, messages: list[str]) -> str:
    # AI call - adds latency
    return await self.ai_generate(messages)
```

### 7. Make Names Unique (If Needed)

```python
async def generate_name(self, messages: list[str]) -> str:
    base_name = self.generate_base_name(messages)
    
    # Add timestamp for uniqueness
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{base_name}-{timestamp}"
    
    # Or use UUID suffix
    return f"{base_name}-{uuid.uuid4().hex[:6]}"
```

---

## Examples

### Example 1: Using Default Generator

```python
from agentflow_cli.src.app.utils.thread_name_generator import AIThreadNameGenerator

# Create generator
generator = AIThreadNameGenerator()

# Generate 10 names
for i in range(10):
    name = generator.generate_name()
    print(f"{i+1}. {name}")
```

Output:
```
1. thoughtful-dialogue
2. exploring-ideas
3. deep-dive
4. building-solutions
5. creative-spark
6. meaningful-exchange
7. discovering-patterns
8. fresh-perspective
9. analytical-session
10. collaborative-journey
```

### Example 2: Custom UUID Generator

```python
# generators/uuid_gen.py
from agentflow_cli import ThreadNameGenerator
import uuid

class UUIDThreadGenerator(ThreadNameGenerator):
    async def generate_name(self, messages: list[str]) -> str:
        return f"thread-{uuid.uuid4().hex[:12]}"

# Usage
generator = UUIDThreadGenerator()
name = await generator.generate_name([])
print(name)
# Output: "thread-a1b2c3d4e5f6"
```

### Example 3: Topic-Based Generator

```python
# generators/topic.py
from agentflow_cli import ThreadNameGenerator
import re

class TopicGenerator(ThreadNameGenerator):
    TOPICS = {
        r'\b(weather|temperature|forecast)\b': 'weather',
        r'\b(help|support|issue|problem)\b': 'support',
        r'\b(code|programming|debug|error)\b': 'technical',
        r'\b(recipe|cooking|food)\b': 'cooking',
        r'\b(travel|trip|vacation)\b': 'travel',
    }
    
    async def generate_name(self, messages: list[str]) -> str:
        if not messages:
            return "general-chat"
        
        text = messages[0].lower()
        
        # Find matching topic
        for pattern, topic in self.TOPICS.items():
            if re.search(pattern, text):
                return f"{topic}-discussion"
        
        return "general-chat"

# Usage
generator = TopicGenerator()
name = await generator.generate_name(["What's the weather like?"])
print(name)
# Output: "weather-discussion"
```

### Example 4: Sequential Generator

```python
# generators/sequential.py
from agentflow_cli import ThreadNameGenerator

class SequentialGenerator(ThreadNameGenerator):
    def __init__(self):
        self.counter = 0
    
    async def generate_name(self, messages: list[str]) -> str:
        self.counter += 1
        return f"conversation-{self.counter:04d}"

# Usage
generator = SequentialGenerator()
for i in range(5):
    name = await generator.generate_name([])
    print(name)
```

Output:
```
conversation-0001
conversation-0002
conversation-0003
conversation-0004
conversation-0005
```

### Example 5: Timestamp-Based Generator

```python
# generators/timestamp.py
from agentflow_cli import ThreadNameGenerator
from datetime import datetime

class TimestampGenerator(ThreadNameGenerator):
    async def generate_name(self, messages: list[str]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"chat-{timestamp}"

# Usage
generator = TimestampGenerator()
name = await generator.generate_name([])
print(name)
# Output: "chat-20241030-143022"
```

### Example 6: Hybrid Generator

```python
# generators/hybrid.py
from agentflow_cli import ThreadNameGenerator
from agentflow_cli.src.app.utils.thread_name_generator import AIThreadNameGenerator

class HybridGenerator(ThreadNameGenerator):
    def __init__(self):
        self.ai_generator = AIThreadNameGenerator()
    
    async def generate_name(self, messages: list[str]) -> str:
        # Use AI generator for base name
        base_name = self.ai_generator.generate_name()
        
        # Add timestamp for uniqueness
        timestamp = datetime.now().strftime("%H%M%S")
        
        return f"{base_name}-{timestamp}"

# Usage
generator = HybridGenerator()
name = await generator.generate_name([])
print(name)
# Output: "thoughtful-dialogue-143022"
```

### Example 7: Integration with FastAPI

```python
# main.py
from fastapi import FastAPI
from agentflow_cli.src.app.utils.thread_name_generator import AIThreadNameGenerator

app = FastAPI()
generator = AIThreadNameGenerator()

@app.post("/threads")
async def create_thread():
    thread_name = generator.generate_name()
    thread_id = generate_thread_id()
    
    return {
        "thread_id": thread_id,
        "thread_name": thread_name
    }
```

### Example 8: Custom Configuration

```python
# generators/branded.py
from agentflow_cli import ThreadNameGenerator
import secrets

class BrandedGenerator(ThreadNameGenerator):
    PREFIXES = ["myapp", "mycompany", "myservice"]
    SUFFIXES = ["session", "chat", "thread"]
    
    async def generate_name(self, messages: list[str]) -> str:
        prefix = secrets.choice(self.PREFIXES)
        suffix = secrets.choice(self.SUFFIXES)
        random_id = secrets.token_hex(4)
        
        return f"{prefix}-{random_id}-{suffix}"

# Usage
generator = BrandedGenerator()
name = await generator.generate_name([])
print(name)
# Output: "myapp-a1b2c3d4-session"
```

---

## Testing

### Unit Tests

```python
# tests/test_thread_names.py
import pytest
from generators.custom import MyGenerator

@pytest.mark.asyncio
async def test_generate_name():
    generator = MyGenerator()
    name = await generator.generate_name([])
    
    assert isinstance(name, str)
    assert len(name) > 0
    assert "-" in name  # Check format

@pytest.mark.asyncio
async def test_name_uniqueness():
    generator = MyGenerator()
    
    names = set()
    for _ in range(100):
        name = await generator.generate_name([])
        names.add(name)
    
    # Should have variety (allow some duplicates)
    assert len(names) > 50

@pytest.mark.asyncio
async def test_with_messages():
    generator = MyGenerator()
    messages = ["Tell me about the weather"]
    
    name = await generator.generate_name(messages)
    
    assert "weather" in name.lower()
```

---

## Additional Resources

- [Configuration Guide](./configuration.md) - Complete configuration reference
- [CLI Guide](./cli-guide.md) - Command-line interface documentation
- [Examples Repository](https://github.com/10xHub/agentflow-examples) - More examples
