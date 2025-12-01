import importlib
import inspect
import logging
import os
from pathlib import Path

from agentflow.checkpointer import BaseCheckpointer
from agentflow.graph import CompiledGraph
from agentflow.store import BaseStore
from injectq import InjectQ

from agentflow_cli import BaseAuth
from agentflow_cli.src.app.core.config.graph_config import GraphConfig
from agentflow_cli.src.app.utils.thread_name_generator import ThreadNameGenerator


logger = logging.getLogger("agentflow-cli.loader")


async def load_graph(path: str) -> CompiledGraph | None:
    module_name_importable, function_name = path.split(":")

    try:
        module = importlib.import_module(module_name_importable)
        entry_point_obj = getattr(module, function_name)

        if callable(entry_point_obj):
            if inspect.iscoroutinefunction(entry_point_obj):
                app = await entry_point_obj()
            else:
                app = entry_point_obj()
        else:
            app = entry_point_obj

        if app is None:
            raise RuntimeError(f"Failed to obtain a runnable graph from {path}.")

        if isinstance(app, CompiledGraph):
            logger.info(f"Successfully loaded graph '{function_name}' from {path}.")
        else:
            raise TypeError("Loaded object is not a CompiledGraph.")

    except Exception as e:
        logger.error(f"Error loading graph from {path}: {e}")
        raise Exception(f"Failed to load graph from {path}: {e}")

    return app


def load_checkpointer(path: str | None) -> BaseCheckpointer | None:
    if not path:
        return None

    module_name_importable, function_name = path.split(":")

    try:
        module = importlib.import_module(module_name_importable)
        entry_point_obj = getattr(module, function_name)
        checkpointer = entry_point_obj

        if checkpointer is None:
            raise RuntimeError(f"Failed to obtain a BaseCheckpointer graph from {path}.")

        if isinstance(checkpointer, BaseCheckpointer):
            logger.info(f"Successfully loaded BaseCheckpointer '{function_name}' from {path}.")
        else:
            raise TypeError("Loaded object is not a BaseCheckpointer.")
    except Exception as e:
        logger.error(f"Error loading BaseCheckpointer from {path}: {e}")
        raise Exception(f"Failed to load BaseCheckpointer from {path}: {e}")

    return checkpointer


def load_store(path: str | None) -> BaseStore | None:
    if not path:
        return None

    module_name_importable, function_name = path.split(":")

    try:
        module = importlib.import_module(module_name_importable)
        entry_point_obj = getattr(module, function_name)
        store = entry_point_obj

        if store is None:
            raise RuntimeError(f"Failed to obtain a BaseStore from {path}.")

        if isinstance(store, BaseStore):
            logger.info(f"Successfully loaded graph '{function_name}' from {path}.")
        else:
            raise TypeError("Loaded object is not a BaseStore.")
    except Exception as e:
        logger.error(f"Error loading BaseStore from {path}: {e}")
        raise Exception(f"Failed to load BaseStore from {path}: {e}")

    return store


def load_container(path: str | None) -> InjectQ | None:
    if not path:
        return None

    module_name_importable, function_name = path.split(":")

    try:
        module = importlib.import_module(module_name_importable)
        entry_point_obj = getattr(module, function_name)
        container = entry_point_obj

        if container is None:
            raise RuntimeError(f"Failed to obtain a InjectQ from {path}.")

        if isinstance(container, InjectQ):
            logger.info(f"Successfully loaded InjectQ '{function_name}' from {path}.")
        else:
            raise TypeError("Loaded object is not a InjectQ.")
    except Exception as e:
        logger.error(f"Error loading InjectQ from {path}: {e}")
        raise Exception(f"Failed to load InjectQ from {path}: {e}")

    # if we have container, set it as the global instance
    if container:
        container.activate()

    return container


def load_auth(path: str | None) -> BaseAuth | None:
    if not path:
        return None

    module_name_importable, function_name = path.split(":")

    try:
        module = importlib.import_module(module_name_importable)
        entry_point_obj = getattr(module, function_name)

        # If it's a class, instantiate it; if it's an instance, use as is
        if inspect.isclass(entry_point_obj) and issubclass(entry_point_obj, BaseAuth):
            auth = entry_point_obj()
        elif isinstance(entry_point_obj, BaseAuth):
            auth = entry_point_obj
        else:
            raise TypeError("Loaded object is not a subclass or instance of BaseAuth.")

        logger.info(f"Successfully loaded BaseAuth '{function_name}' from {path}.")
    except Exception as e:
        logger.error(f"Error loading BaseAuth from {path}: {e}")
        raise Exception(f"Failed to load BaseAuth from {path}: {e}")

    return auth


def load_thread_name_generator(path: str | None) -> ThreadNameGenerator | None:
    if not path:
        return None

    module_name_importable, function_name = path.split(":")

    try:
        module = importlib.import_module(module_name_importable)
        entry_point_obj = getattr(module, function_name)

        # If it's a class, instantiate it; if it's an instance, use as is
        if inspect.isclass(entry_point_obj) and issubclass(entry_point_obj, ThreadNameGenerator):
            thread_name_generator = entry_point_obj()
        elif isinstance(entry_point_obj, ThreadNameGenerator):
            thread_name_generator = entry_point_obj
        else:
            raise TypeError("Loaded object is not a subclass or instance of ThreadNameGenerator.")

        logger.info(f"Successfully loaded ThreadNameGenerator '{function_name}' from {path}.")
    except Exception as e:
        logger.error(f"Error loading ThreadNameGenerator from {path}: {e}")
        raise Exception(f"Failed to load ThreadNameGenerator from {path}: {e}")

    return thread_name_generator


async def attach_all_modules(
    config: GraphConfig,
    container: InjectQ,
) -> CompiledGraph | None:
    graph = await load_graph(config.graph_path)
    logger.info("All modules attached successfully")

    # This binding we have done already in the library
    # # Bind checkpointer instance if configured
    # checkpointer = load_checkpointer(config.checkpointer_path)
    # container.bind_instance(BaseCheckpointer, checkpointer, allow_none=True)

    # # Bind store instance if configured
    # store = load_store(config.store_path)
    # container.bind_instance(BaseStore, store, allow_none=True)

    # load auth backend
    auth_config = config.auth_config()
    if auth_config:
        method = auth_config.get("method", None)
        path = auth_config.get("path", None)
        if not path or not method:
            raise ValueError("Both 'method' and 'path' must be specified in auth_config.")

        # Extract file path before the ':' for existence check
        module_or_path = path.split(":", 1)[0] if ":" in path else path

        # Simple handling: if it appears to be a filesystem path, use it; otherwise
        # convert dotted module path to a file path like src/auth/custom_auth.py
        if os.path.sep in module_or_path or module_or_path.endswith(".py"):
            file_path = Path(module_or_path)
        elif "." in module_or_path and os.path.sep not in module_or_path:
            file_path = Path(module_or_path.replace(".", os.path.sep) + ".py")
        else:
            file_path = Path(module_or_path)

        if not file_path.exists():
            raise ValueError(f"Custom auth path does not exist: {module_or_path}")

        if method == "custom":
            auth_backend = load_auth(
                path,
            )
            container.bind_instance(BaseAuth, auth_backend)
        elif method == "jwt":
            from agentflow_cli.src.app.core.auth.jwt_auth import JwtAuth

            jwt_auth = JwtAuth()
            container.bind_instance(BaseAuth, jwt_auth)

        elif method == "none":
            container.bind_instance(BaseAuth, None, allow_none=True)
    else:
        # bind None
        container.bind_instance(BaseAuth, None, allow_none=True)

    # load thread name generator
    thread_name_generator_path = config.thread_name_generator_path
    if thread_name_generator_path:
        thread_name_generator = load_thread_name_generator(thread_name_generator_path)
        container.bind_instance(ThreadNameGenerator, thread_name_generator)
    else:
        # bind None if not configured
        container.bind_instance(ThreadNameGenerator, None, allow_none=True)

    logger.info("Container loaded successfully")
    logger.debug(f"Container dependency graph: {container.get_dependency_graph()}")

    return graph
