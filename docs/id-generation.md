# ID Generation Guide

This guide covers using the Snowflake ID generator for generating unique, distributed, and time-sortable IDs in your AgentFlow application.

## Table of Contents

- [Overview](#overview)
- [What is Snowflake ID?](#what-is-snowflake-id)
- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [Configuration](#configuration)
- [Advanced Usage](#advanced-usage)
- [Best Practices](#best-practices)
- [Examples](#examples)

---

## Overview

AgentFlow includes a Snowflake ID generator based on Twitter's Snowflake algorithm for generating unique, distributed, time-sortable 64-bit IDs.

### Key Features

- ✅ **Unique:** Guaranteed unique across distributed systems
- ✅ **Time-sortable:** IDs are roughly chronological
- ✅ **High performance:** Can generate thousands of IDs per second
- ✅ **Distributed:** Works across multiple nodes and workers
- ✅ **64-bit integers:** Efficient storage and indexing
- ✅ **Configurable:** Adjust bit allocation for your needs

---

## What is Snowflake ID?

A Snowflake ID is a 64-bit integer composed of:

```
|-------|-----------|--------|--------|----------|
|  Sign |   Time    |  Node  | Worker | Sequence |
|   1   |    39     |   5    |   8    |    11    |
|-------|-----------|--------|--------|----------|
```

### Default Bit Allocation

| Component | Bits | Range | Description |
|-----------|------|-------|-------------|
| Sign | 1 | 0 | Always 0 (positive) |
| Time | 39 | 0 - 17.4 years | Milliseconds since epoch |
| Node | 5 | 0 - 31 | Node/datacenter ID |
| Worker | 8 | 0 - 255 | Worker/process ID |
| Sequence | 11 | 0 - 4095 | Per-millisecond counter |

### Example ID

```
ID: 1234567890123456789

Breakdown:
- Time: 1609459200000 (Jan 1, 2021 00:00:00 UTC + offset)
- Node ID: 5
- Worker ID: 3
- Sequence: 42
```

### Advantages

1. **Distributed Generation:** No coordination needed between nodes
2. **Time Ordering:** IDs generated later have higher values
3. **Database Friendly:** 64-bit integers are efficiently indexed
4. **High Throughput:** Up to 4096 IDs per millisecond per worker
5. **No Lookups:** No need to query a database or service

---

## Installation

### Required Package

```bash
pip install snowflakekit
```

Or install with agentflow-cli:

```bash
pip install "10xscale-agentflow-cli[snowflakekit]"
```

### Verify Installation

```python
from agentflow_cli import SnowFlakeIdGenerator

# This will raise ImportError if snowflakekit is not installed
generator = SnowFlakeIdGenerator()
```

---

## Basic Usage

### Import

```python
from agentflow_cli import SnowFlakeIdGenerator
```

### Create Generator

**Using environment variables:**
```python
# Generator will read from environment variables
generator = SnowFlakeIdGenerator()
```

**Using explicit configuration:**
```python
generator = SnowFlakeIdGenerator(
    snowflake_epoch=1609459200000,  # Jan 1, 2021 (milliseconds)
    total_bits=64,
    snowflake_time_bits=39,
    snowflake_node_bits=5,
    snowflake_node_id=1,
    snowflake_worker_bits=8,
    snowflake_worker_id=1
)
```

### Generate IDs

```python
# Generate a single ID
id = await generator.generate()
print(f"Generated ID: {id}")
# Output: Generated ID: 1234567890123456789

# Generate multiple IDs
ids = [await generator.generate() for _ in range(10)]
print(f"Generated {len(ids)} IDs")
```

### Complete Example

```python
import asyncio
from agentflow_cli import SnowFlakeIdGenerator

async def main():
    # Create generator
    generator = SnowFlakeIdGenerator(
        snowflake_epoch=1609459200000,
        snowflake_node_id=1,
        snowflake_worker_id=1
    )
    
    # Generate IDs
    for i in range(5):
        id = await generator.generate()
        print(f"ID {i+1}: {id}")

# Run
asyncio.run(main())
```

Output:
```
ID 1: 1234567890123456789
ID 2: 1234567890123456790
ID 3: 1234567890123456791
ID 4: 1234567890123456792
ID 5: 1234567890123456793
```

---

## Configuration

### Environment Variables

Set these in your `.env` file:

```bash
# Required
SNOWFLAKE_EPOCH=1609459200000  # Milliseconds since Unix epoch

# Node and Worker IDs (required)
SNOWFLAKE_NODE_ID=1            # 0-31 (with 5 bits)
SNOWFLAKE_WORKER_ID=1          # 0-255 (with 8 bits)

# Optional (defaults shown)
SNOWFLAKE_TOTAL_BITS=64
SNOWFLAKE_TIME_BITS=39
SNOWFLAKE_NODE_BITS=5
SNOWFLAKE_WORKER_BITS=8
```

### Choosing an Epoch

The epoch is the starting point for time measurement. Choose a date close to your service launch:

```python
from datetime import datetime

# Calculate epoch in milliseconds
epoch_date = datetime(2024, 1, 1, 0, 0, 0)
epoch_ms = int(epoch_date.timestamp() * 1000)
print(f"SNOWFLAKE_EPOCH={epoch_ms}")

# Output: SNOWFLAKE_EPOCH=1704067200000
```

**Why choose a custom epoch?**
- Extends the time range (default 39 bits = ~17.4 years from epoch)
- If epoch = Jan 1, 2024, you can generate IDs until ~2041

### Node and Worker IDs

Assign unique IDs across your infrastructure:

```bash
# Production setup
# Server 1
SNOWFLAKE_NODE_ID=1
SNOWFLAKE_WORKER_ID=1

# Server 2
SNOWFLAKE_NODE_ID=1
SNOWFLAKE_WORKER_ID=2

# Server 3 (different datacenter)
SNOWFLAKE_NODE_ID=2
SNOWFLAKE_WORKER_ID=1
```

### Bit Allocation

Customize bit allocation for your use case:

**Default (total 64 bits):**
```bash
SNOWFLAKE_TIME_BITS=39     # ~17 years
SNOWFLAKE_NODE_BITS=5      # 32 nodes
SNOWFLAKE_WORKER_BITS=8    # 256 workers per node
# Sequence bits = 64 - 1 - 39 - 5 - 8 = 11 bits = 4096 IDs/ms
```

**High concurrency (fewer nodes, more throughput):**
```bash
SNOWFLAKE_TIME_BITS=39     # ~17 years
SNOWFLAKE_NODE_BITS=3      # 8 nodes
SNOWFLAKE_WORKER_BITS=6    # 64 workers per node
# Sequence bits = 15 bits = 32768 IDs/ms
```

**Many nodes (distributed):**
```bash
SNOWFLAKE_TIME_BITS=39     # ~17 years
SNOWFLAKE_NODE_BITS=8      # 256 nodes
SNOWFLAKE_WORKER_BITS=5    # 32 workers per node
# Sequence bits = 11 bits = 4096 IDs/ms
```

**Long time range:**
```bash
SNOWFLAKE_TIME_BITS=41     # ~69 years
SNOWFLAKE_NODE_BITS=4      # 16 nodes
SNOWFLAKE_WORKER_BITS=7    # 128 workers per node
# Sequence bits = 11 bits = 4096 IDs/ms
```

### Validation

Bit allocation must follow these rules:

1. Total must equal 64: `1 + time + node + worker + sequence = 64`
2. All components must be positive
3. Node ID must be < 2^node_bits
4. Worker ID must be < 2^worker_bits

---

## Advanced Usage

### Using in FastAPI Endpoints

```python
from fastapi import FastAPI, Depends
from agentflow_cli import SnowFlakeIdGenerator
from injectq import InjectQ

app = FastAPI()

# Setup dependency injection
container = InjectQ()
generator = SnowFlakeIdGenerator(
    snowflake_epoch=1609459200000,
    snowflake_node_id=1,
    snowflake_worker_id=1
)
container.bind_instance(SnowFlakeIdGenerator, generator)

@app.post("/users")
async def create_user(
    name: str,
    id_generator: SnowFlakeIdGenerator = Depends(lambda: container.get(SnowFlakeIdGenerator))
):
    user_id = await id_generator.generate()
    
    # Save user to database
    user = {
        "id": user_id,
        "name": name
    }
    
    return user
```

### Using in Database Models

```python
from sqlalchemy import Column, BigInteger, String
from sqlalchemy.ext.declarative import declarative_base
from agentflow_cli import SnowFlakeIdGenerator

Base = declarative_base()
id_generator = SnowFlakeIdGenerator()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(100))
    email = Column(String(100))
    
    def __init__(self, name: str, email: str):
        self.id = None  # Will be set before insert
        self.name = name
        self.email = email

# Before inserting
async def create_user(name: str, email: str):
    user = User(name, email)
    user.id = await id_generator.generate()
    
    # Save to database
    db.add(user)
    db.commit()
    
    return user
```

### Using in AgentFlow Graphs

```python
# graph/user_agent.py
from agentflow.graph import StateGraph
from agentflow_cli import SnowFlakeIdGenerator
from injectq import Inject

id_generator = SnowFlakeIdGenerator()

async def create_user_node(
    state: AgentState,
    config: dict,
    generator: SnowFlakeIdGenerator = Inject[SnowFlakeIdGenerator]
):
    # Generate unique user ID
    user_id = await generator.generate()
    
    # Create user record
    user = {
        "id": user_id,
        "name": state.user_input,
        "created_at": datetime.now()
    }
    
    return {"user": user}

# Setup graph
graph = StateGraph()
graph.add_node("create_user", create_user_node)
app = graph.compile()
```

### Decoding Snowflake IDs

```python
def decode_snowflake(id: int, epoch: int = 1609459200000) -> dict:
    """Decode a Snowflake ID into its components."""
    # Extract components
    sequence = id & 0x7FF  # 11 bits
    worker_id = (id >> 11) & 0xFF  # 8 bits
    node_id = (id >> 19) & 0x1F  # 5 bits
    timestamp_ms = (id >> 24) + epoch  # 39 bits
    
    # Convert timestamp to datetime
    from datetime import datetime
    timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
    
    return {
        "id": id,
        "timestamp": timestamp,
        "timestamp_ms": timestamp_ms,
        "node_id": node_id,
        "worker_id": worker_id,
        "sequence": sequence
    }

# Usage
id = 1234567890123456789
components = decode_snowflake(id)
print(f"Generated at: {components['timestamp']}")
print(f"Node ID: {components['node_id']}")
print(f"Worker ID: {components['worker_id']}")
print(f"Sequence: {components['sequence']}")
```

---

## Best Practices

### 1. Choose Epoch Carefully

```python
# ✅ Good: Recent epoch extends time range
SNOWFLAKE_EPOCH=1704067200000  # Jan 1, 2024

# ❌ Bad: Using distant past wastes time range
SNOWFLAKE_EPOCH=0  # Jan 1, 1970
```

### 2. Assign Unique Node/Worker IDs

```python
# ✅ Good: Unique across infrastructure
# Server 1: NODE_ID=1, WORKER_ID=1
# Server 2: NODE_ID=1, WORKER_ID=2
# Server 3: NODE_ID=2, WORKER_ID=1

# ❌ Bad: Same IDs on multiple servers
# All servers: NODE_ID=1, WORKER_ID=1  # Collisions!
```

### 3. Use Environment Variables

```python
# ✅ Good: Configuration from environment
generator = SnowFlakeIdGenerator()

# ❌ Bad: Hard-coded configuration
generator = SnowFlakeIdGenerator(
    snowflake_node_id=1,  # What if deployed to different node?
    snowflake_worker_id=1
)
```

### 4. Handle Errors

```python
try:
    generator = SnowFlakeIdGenerator()
except ImportError:
    print("Error: snowflakekit not installed")
    print("Install with: pip install snowflakekit")
```

### 5. Monitor ID Generation

```python
import time

async def monitor_id_generation():
    generator = SnowFlakeIdGenerator()
    
    start = time.time()
    count = 10000
    
    for _ in range(count):
        await generator.generate()
    
    elapsed = time.time() - start
    rate = count / elapsed
    
    print(f"Generated {count} IDs in {elapsed:.2f}s")
    print(f"Rate: {rate:.0f} IDs/second")
```

### 6. Use BigInt in Databases

```sql
-- PostgreSQL
CREATE TABLE users (
    id BIGINT PRIMARY KEY,  -- Not INT!
    name VARCHAR(100)
);

-- MySQL
CREATE TABLE users (
    id BIGINT UNSIGNED PRIMARY KEY,
    name VARCHAR(100)
);
```

### 7. Validate Bit Configuration

```python
def validate_config(time_bits, node_bits, worker_bits):
    total = 1 + time_bits + node_bits + worker_bits
    sequence_bits = 64 - total
    
    if sequence_bits < 1:
        raise ValueError("Not enough bits for sequence")
    
    if sequence_bits > 20:
        print(f"Warning: {sequence_bits} sequence bits may be excessive")
    
    time_range_years = (2 ** time_bits) / (1000 * 60 * 60 * 24 * 365)
    print(f"Time range: ~{time_range_years:.1f} years")
    
    print(f"Max nodes: {2 ** node_bits}")
    print(f"Max workers per node: {2 ** worker_bits}")
    print(f"Max IDs per millisecond: {2 ** sequence_bits}")
```

---

## Examples

### Example 1: Basic Setup

```python
# .env
SNOWFLAKE_EPOCH=1704067200000
SNOWFLAKE_NODE_ID=1
SNOWFLAKE_WORKER_ID=1

# app.py
from agentflow_cli import SnowFlakeIdGenerator
import asyncio

async def main():
    generator = SnowFlakeIdGenerator()
    
    # Generate 5 IDs
    for i in range(5):
        id = await generator.generate()
        print(f"ID {i+1}: {id}")

asyncio.run(main())
```

### Example 2: FastAPI Integration

```python
# main.py
from fastapi import FastAPI, Depends
from agentflow_cli import SnowFlakeIdGenerator
from pydantic import BaseModel

app = FastAPI()
generator = SnowFlakeIdGenerator()

class User(BaseModel):
    name: str
    email: str

@app.post("/users")
async def create_user(user: User):
    user_id = await generator.generate()
    
    return {
        "id": user_id,
        "name": user.name,
        "email": user.email
    }

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    # Decode ID
    components = decode_snowflake(user_id)
    
    return {
        "id": user_id,
        "created_at": components["timestamp"],
        "node_id": components["node_id"]
    }
```

### Example 3: Multi-Node Setup

```bash
# node1.env
SNOWFLAKE_EPOCH=1704067200000
SNOWFLAKE_NODE_ID=1
SNOWFLAKE_WORKER_ID=1

# node2.env
SNOWFLAKE_EPOCH=1704067200000
SNOWFLAKE_NODE_ID=1
SNOWFLAKE_WORKER_ID=2

# node3.env (different datacenter)
SNOWFLAKE_EPOCH=1704067200000
SNOWFLAKE_NODE_ID=2
SNOWFLAKE_WORKER_ID=1
```

### Example 4: High Throughput Test

```python
import asyncio
import time
from agentflow_cli import SnowFlakeIdGenerator

async def benchmark():
    generator = SnowFlakeIdGenerator()
    
    # Generate 100,000 IDs
    count = 100000
    start = time.time()
    
    ids = set()
    for _ in range(count):
        id = await generator.generate()
        ids.add(id)
    
    elapsed = time.time() - start
    rate = count / elapsed
    
    print(f"Generated {count:,} IDs in {elapsed:.2f}s")
    print(f"Rate: {rate:,.0f} IDs/second")
    print(f"All unique: {len(ids) == count}")

asyncio.run(benchmark())
```

Output:
```
Generated 100,000 IDs in 0.45s
Rate: 222,222 IDs/second
All unique: True
```

### Example 5: Database Integration

```python
from sqlalchemy import create_engine, Column, BigInteger, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from agentflow_cli import SnowFlakeIdGenerator

Base = declarative_base()
generator = SnowFlakeIdGenerator()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(100))
    email = Column(String(100))

# Create engine and session
engine = create_engine('postgresql://user:pass@localhost/db')
Session = sessionmaker(bind=engine)

async def create_user(name: str, email: str):
    session = Session()
    
    # Generate ID
    user_id = await generator.generate()
    
    # Create user
    user = User(id=user_id, name=name, email=email)
    session.add(user)
    session.commit()
    
    print(f"Created user {user_id}: {name}")
    
    session.close()
    return user
```

---

## Troubleshooting

### ImportError: No module named 'snowflakekit'

**Solution:**
```bash
pip install snowflakekit
```

### ValueError: All configuration parameters must be provided

**Solution:**
Either provide all parameters explicitly or set environment variables:

```bash
# .env
SNOWFLAKE_EPOCH=1704067200000
SNOWFLAKE_NODE_ID=1
SNOWFLAKE_WORKER_ID=1
SNOWFLAKE_TOTAL_BITS=64
SNOWFLAKE_TIME_BITS=39
SNOWFLAKE_NODE_BITS=5
SNOWFLAKE_WORKER_BITS=8
```

### Duplicate IDs Generated

**Possible causes:**
1. Same NODE_ID and WORKER_ID on multiple servers
2. System clock went backwards
3. Generating IDs faster than supported (>4096/ms)

**Solutions:**
- Ensure unique NODE_ID/WORKER_ID combinations
- Use NTP to keep clocks synchronized
- Increase sequence bits if needed

### IDs Not Sortable

**Cause:** Using different epochs on different nodes

**Solution:** Use the same epoch across all nodes

---

## Additional Resources

- [Twitter Snowflake](https://blog.twitter.com/engineering/en_us/a/2010/announcing-snowflake) - Original Snowflake algorithm
- [Configuration Guide](./configuration.md) - Complete configuration reference
- [Deployment Guide](./deployment.md) - Production deployment strategies
