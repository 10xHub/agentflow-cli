"""Root pytest configuration.

Provides the ``--integration`` gate. Tests marked ``@pytest.mark.integration`` talk to
real external services (Redis, Postgres) and are skipped unless the flag is passed, so
a default ``pytest`` run never depends on infrastructure being up.

Note: ``tests/integration_tests/`` is *not* covered by this gate. Despite the name those
are in-process end-to-end tests against a real FastAPI app with an ``InMemoryCheckpointer``
- they need no external services and must always run.
"""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run tests marked `integration`, which require real Redis/Postgres.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    if config.getoption("--integration"):
        return

    skip_integration = pytest.mark.skip(reason="needs --integration (real Redis/Postgres)")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
