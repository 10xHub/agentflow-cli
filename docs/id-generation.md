# ID Generation Guide

This guide covers using the Snowflake ID generator for generating unique, distributed, and time-sortable IDs in your AgentFlow application.

## Table of Contents

- [Overview](#overview)
- [What is Snowflake ID?](#what-is-snowflake-id)
- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [Configuration](#configuration)
- [Best Practices](#best-practices)

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
from agentflow.graph import StateGraph
```

### Create Generator and Use with StateGraph

```python
# Create generator (reads configuration from environment variables)
id_generator = SnowFlakeIdGenerator()

# Use with StateGraph
graph = StateGraph[MyAgentState](MyAgentState(), id_generator=id_generator)
```

The generator will automatically read configuration from environment variables (recommended for production).

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

## Troubleshooting

### ImportError: No module named 'snowflakekit'

**Solution:**
```bash
pip install snowflakekit
```

### ValueError: All configuration parameters must be provided

**Solution:**
Set all required environment variables:

```bash
# .env
SNOWFLAKE_EPOCH=1704067200000
SNOWFLAKE_NODE_ID=1
SNOWFLAKE_WORKER_ID=1
```

### Duplicate IDs Generated

**Possible causes:**
1. Same NODE_ID and WORKER_ID on multiple servers
2. System clock went backwards
3. Generating IDs faster than supported (>4096/ms)

**Solutions:**
- Ensure unique NODE_ID/WORKER_ID combinations per server instance
- Use NTP to keep clocks synchronized
- Increase sequence bits if higher throughput is needed

---

## Additional Resources

- [Twitter Snowflake](https://blog.twitter.com/engineering/en_us/a/2010/announcing-snowflake) - Original Snowflake algorithm
- [Configuration Guide](./configuration.md) - Complete configuration reference
- [Deployment Guide](./deployment.md) - Production deployment strategies
