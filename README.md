
# Pyagenity API

A Python library for building AI agent graphs with FastAPI backend and CLI tools.

## Installation

```bash
pip install pyagenity-api
```

## Quick Start

1. **Initialize a new project:**
```bash
pyagenity init
```

2. **Create your graph file (e.g., `my_graph.py`):**
```python
from pyagenity.graph import StateGraph
from pyagenity.state.agent_state import AgentState

# Your graph logic here
```

3. **Update `pyagenity.json`:**
```json
{
  "graphs": {
    "my_agent": "my_graph:app"
  }
}
```

4. **Run the API server:**
```bash
pyagenity api
```

## CLI Commands

- `pyagenity init` - Create a default config file
- `pyagenity api` - Start the API server
- `pyagenity version` - Show version information

## Configuration

The `pyagenity.json` file supports:

```json
{
  "graphs": {
    "agent_name": "module.path:object_name"
  },
  "env": ".env",
  "auth": "None"
}
```

## File Resolution

The CLI automatically finds your config file in this order:
1. Absolute path (if provided)
2. Current working directory
3. Package installation directory (fallback)

## Project Structure
```
your_project/
├── pyagenity.json          # Configuration file
├── my_graph.py            # Your graph implementation
├── requirements.txt       # Your dependencies
└── .env                   # Environment variables
```

## Setup

### Prerequisites
- Python 3.x
- pip
- [Any other prerequisites]

### Installation
1. Clone the repository:
    ```bash
    git clone https://github.com/10XScale-in/backend-base.git
    ```

2. Create a virtual environment and activate:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Database

### Database Configuration
The database configuration is located in `src/app/db/setup_database.py`.

### Database Migration
We use Aerich for database migrations. Follow these steps to manage your database:

1. Initialize the database initially:
    ```bash
    aerich init -t src.app.db.setup_database.TORTOISE_ORM
    ```

2. Create initial database schema:
    ```bash
    aerich init-db
    ```

3. Generate migration files:
    ```bash
    aerich migrate
    ```

4. Apply migrations:
    ```bash
    aerich upgrade
    ```

5. Revert migrations (if needed):
    ```bash
    aerich downgrade
    ```

## Running the Application

### Command Line
To run the FastAPI application using Uvicorn:
1. Start the application:
    ```bash
    uvicorn src.app.main:app --reload
    ```

2. You can also run the debugger.

### VS Code
Add the following configuration to your `.vscode/launch.json` file:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "src.app.main:app",
                "--host",
                "localhost",
                "--port",
                "8880"
            ],
            "jinja": true,
            "justMyCode": true
        }
    ]
}
```
Then you can run and debug the application using the VS Code debugger.
### Run the Broker
1. Run the taskiq worker
```taskiq worker src.app.worker:broker -fsd -tp 'src/**/*_tasks.py' --reload
```
## Development

### Pre-commit Hooks
We use pre-commit hooks to ensure code quality. To set them up:
1. Install the pre-commit package:
    ```bash
    pip install pre-commit
    ```
2. Install the git hook scripts:
    ```bash
    pre-commit install
    ```
### Code Style
    1.ruff,
    2.mypy,
    3.bandit
## Testing
    1.pytest


# Resources
https://keda.sh/
Get all the fixers
pytest --fixtures
https://www.tutorialspoint.com/pytest/pytest_run_tests_in_parallel.html

