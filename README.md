
# Project Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Setup](#setup)
   - [Prerequisites](#prerequisites)
   - [Installation](#installation)
4. [Database](#database)
   - [Configuration](#database-configuration)
   - [Migration](#database-migration)
5. [Running the Application](#running-the-application)
   - [Command Line](#command-line)
   - [VS Code](#vs-code)
6. [Development](#development)
   - [Pre-commit Hooks](#pre-commit-hooks)
   - [Code Style](#code-style)
7. [API Documentation](#api-documentation)
8. [Testing](#testing)


## Introduction
Welcome to the 10XScale-in Backend Base project. This FastAPI-based application serves as a robust foundation for building scalable and efficient backend services. Our project is designed with modern development practices in mind, offering a streamlined setup process and powerful features to accelerate your development workflow.

Key Features:
- FastAPI framework for high-performance, easy-to-use REST APIs
- Aerich for smooth database migrations and management
- Pre-commit hooks for maintaining code quality
- VS Code integration for enhanced debugging capabilities
- Comprehensive documentation to guide you through setup and development

This backend base is ideal for developers looking to quickly bootstrap a new project or for teams aiming to standardize their backend infrastructure. Whether you're building a small service or laying the groundwork for a large-scale application, our project provides the tools and structure you need to succeed.

The documentation that follows will guide you through setting up your development environment, running the application, managing the database, and contributing to the project. We've designed this guide to be as comprehensive as possible, ensuring that both newcomers and experienced developers can quickly get up to speed.

Let's get started on building your next great backend service!

## Project Structure
```
project_root/
├── src/
│   └── app/
│       ├── main.py
│       └── db/
│           └── setup_database.py
├── tests/
├── requirements.txt
├── .pre-commit-config.yaml
└── README.md
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

