"""Unit tests for loader.py."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pathlib import Path
from injectq import InjectQ

from agentflow.core import CompiledGraph
from agentflow.storage.checkpointer import BaseCheckpointer
from agentflow.storage.store import BaseStore
from agentflow_cli import BaseAuth
from agentflow_cli.src.app.core.auth.authorization import AuthorizationBackend, DefaultAuthorizationBackend
from agentflow_cli.src.app.utils.thread_name_generator import ThreadNameGenerator
from agentflow_cli.src.app.core.config.graph_config import GraphConfig
from agentflow_cli.src.app.loader import (
    load_graph,
    load_checkpointer,
    load_store,
    load_container,
    load_auth,
    load_authorization,
    load_thread_name_generator,
    load_and_bind_auth,
    load_and_bind_authorization,
    attach_all_modules,
)


@pytest.mark.asyncio
async def test_load_graph_invalid_format():
    with pytest.raises(ValueError, match="Invalid graph path format"):
        await load_graph("invalid_path_no_colon")


@pytest.mark.asyncio
async def test_load_graph_success_callable():
    mock_graph = MagicMock(spec=CompiledGraph)
    mock_callable = MagicMock(return_value=mock_graph)
    
    mock_module = MagicMock()
    mock_module.my_graph = mock_callable
    
    with patch("importlib.import_module", return_value=mock_module) as mock_import:
        result = await load_graph("my_module:my_graph")
        assert result == mock_graph
        mock_import.assert_called_once_with("my_module")


@pytest.mark.asyncio
async def test_load_graph_success_async_callable():
    mock_graph = MagicMock(spec=CompiledGraph)
    mock_callable = AsyncMock(return_value=mock_graph)
    
    mock_module = MagicMock()
    mock_module.my_graph = mock_callable
    
    with patch("importlib.import_module", return_value=mock_module) as mock_import:
        result = await load_graph("my_module:my_graph")
        assert result == mock_graph


@pytest.mark.asyncio
async def test_load_graph_success_non_callable():
    class NonCallableGraph(CompiledGraph):
        def __init__(self):
            pass
    
    non_callable = NonCallableGraph()
    mock_module = MagicMock()
    mock_module.my_graph = non_callable
    
    with patch("importlib.import_module", return_value=mock_module):
        result = await load_graph("my_module:my_graph")
        assert result == non_callable


@pytest.mark.asyncio
async def test_load_graph_errors():
    # RuntimeError: app is None
    mock_module = MagicMock()
    mock_module.my_graph = None
    with patch("importlib.import_module", return_value=mock_module):
        with pytest.raises(Exception, match="Failed to obtain a runnable graph"):
            await load_graph("my_module:my_graph")
            
    # TypeError: Loaded object is not a CompiledGraph
    mock_module.my_graph = "not a graph"
    with patch("importlib.import_module", return_value=mock_module):
        with pytest.raises(Exception, match="Loaded object is not a CompiledGraph"):
            await load_graph("my_module:my_graph")

    # ModuleNotFoundError
    with patch("importlib.import_module", side_effect=ModuleNotFoundError("No module named foo")):
        with pytest.raises(ModuleNotFoundError):
            await load_graph("foo:bar")

    # AttributeError
    mock_module = MagicMock()
    del mock_module.bar
    with patch("importlib.import_module", return_value=mock_module):
        with pytest.raises(AttributeError):
            await load_graph("foo:bar")


def test_load_checkpointer():
    assert load_checkpointer(None) is None
    
    with pytest.raises(ValueError, match="Invalid checkpointer path format"):
        load_checkpointer("invalid_no_colon")
        
    mock_cp = MagicMock(spec=BaseCheckpointer)
    mock_module = MagicMock()
    mock_module.cp = mock_cp
    with patch("importlib.import_module", return_value=mock_module):
        assert load_checkpointer("mod:cp") == mock_cp

    # RuntimeError
    mock_module.cp = None
    with patch("importlib.import_module", return_value=mock_module):
        with pytest.raises(Exception, match="Failed to obtain a BaseCheckpointer"):
            load_checkpointer("mod:cp")

    # TypeError
    mock_module.cp = "not cp"
    with patch("importlib.import_module", return_value=mock_module):
        with pytest.raises(Exception, match="Loaded object is not a BaseCheckpointer"):
            load_checkpointer("mod:cp")

    # ModuleNotFoundError
    with patch("importlib.import_module", side_effect=ModuleNotFoundError()):
        with pytest.raises(ModuleNotFoundError):
            load_checkpointer("mod:cp")

    # AttributeError
    mock_module = MagicMock()
    del mock_module.cp
    with patch("importlib.import_module", return_value=mock_module):
        with pytest.raises(AttributeError):
            load_checkpointer("mod:cp")


def test_load_store():
    assert load_store(None) is None
    
    with pytest.raises(ValueError, match="Invalid store path format"):
        load_store("invalid")
        
    mock_store = MagicMock(spec=BaseStore)
    mock_module = MagicMock()
    mock_module.store = mock_store
    with patch("importlib.import_module", return_value=mock_module):
        assert load_store("mod:store") == mock_store

    # RuntimeError
    mock_module.store = None
    with patch("importlib.import_module", return_value=mock_module):
        with pytest.raises(Exception, match="Failed to obtain a BaseStore"):
            load_store("mod:store")

    # TypeError
    mock_module.store = "not store"
    with patch("importlib.import_module", return_value=mock_module):
        with pytest.raises(Exception, match="Loaded object is not a BaseStore"):
            load_store("mod:store")

    # ModuleNotFoundError
    with patch("importlib.import_module", side_effect=ModuleNotFoundError()):
        with pytest.raises(ModuleNotFoundError):
            load_store("mod:store")


def test_load_container():
    assert load_container(None) is None
    
    mock_container = MagicMock(spec=InjectQ)
    mock_module = MagicMock()
    mock_module.container = mock_container
    with patch("importlib.import_module", return_value=mock_module):
        assert load_container("mod:container") == mock_container
        mock_container.activate.assert_called_once()

    # Exception cases
    mock_module.container = "not container"
    with patch("importlib.import_module", return_value=mock_module):
        with pytest.raises(Exception, match="Failed to load InjectQ"):
            load_container("mod:container")


def test_load_auth():
    assert load_auth(None) is None
    
    with pytest.raises(ValueError, match="Invalid auth path format"):
        load_auth("invalid")
        
    class CustomAuth(BaseAuth):
        def authenticate(self, *args, **kwargs):
            pass
        
    # Class subclass of BaseAuth
    mock_module = MagicMock()
    mock_module.auth = CustomAuth
    with patch("importlib.import_module", return_value=mock_module):
        result = load_auth("mod:auth")
        assert isinstance(result, CustomAuth)

    # Instance of BaseAuth
    auth_instance = CustomAuth()
    mock_module.auth = auth_instance
    with patch("importlib.import_module", return_value=mock_module):
        assert load_auth("mod:auth") == auth_instance

    # TypeError
    mock_module.auth = "not auth"
    with patch("importlib.import_module", return_value=mock_module):
        with pytest.raises(Exception, match="Loaded object is not a subclass or instance of BaseAuth"):
            load_auth("mod:auth")

    # ModuleNotFoundError
    with patch("importlib.import_module", side_effect=ModuleNotFoundError()):
        with pytest.raises(ModuleNotFoundError):
            load_auth("mod:auth")


def test_load_authorization():
    assert load_authorization(None) is None
    
    class CustomAuthorization(AuthorizationBackend):
        def authorize(self, *args, **kwargs):
            pass
        
    # Class subclass
    mock_module = MagicMock()
    mock_module.authorization = CustomAuthorization
    with patch("importlib.import_module", return_value=mock_module):
        result = load_authorization("mod:authorization")
        assert isinstance(result, CustomAuthorization)

    # Instance
    auth_instance = CustomAuthorization()
    mock_module.authorization = auth_instance
    with patch("importlib.import_module", return_value=mock_module):
        assert load_authorization("mod:authorization") == auth_instance

    # TypeError
    mock_module.authorization = "not authorization"
    with patch("importlib.import_module", return_value=mock_module):
        with pytest.raises(Exception, match="Loaded object is not a subclass or instance of AuthorizationBackend"):
            load_authorization("mod:authorization")


def test_load_thread_name_generator():
    assert load_thread_name_generator(None) is None
    
    class CustomGenerator(ThreadNameGenerator):
        async def generate_name(self, messages):
            return "name"
            
    # Class subclass
    mock_module = MagicMock()
    mock_module.generator = CustomGenerator
    with patch("importlib.import_module", return_value=mock_module):
        result = load_thread_name_generator("mod:generator")
        assert isinstance(result, CustomGenerator)

    # Instance
    gen_instance = CustomGenerator()
    mock_module.generator = gen_instance
    with patch("importlib.import_module", return_value=mock_module):
        assert load_thread_name_generator("mod:generator") == gen_instance

    # TypeError
    mock_module.generator = "not generator"
    with patch("importlib.import_module", return_value=mock_module):
        with pytest.raises(Exception, match="Loaded object is not a subclass or instance of ThreadNameGenerator"):
            load_thread_name_generator("mod:generator")


def test_load_and_bind_auth():
    container = MagicMock(spec=InjectQ)
    
    # Missing method/path
    with pytest.raises(ValueError, match="Both 'method' and 'path' must be specified"):
        load_and_bind_auth(container, {"method": "custom"})
        
    # Path existence check failure
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(ValueError, match="Custom auth path does not exist"):
            load_and_bind_auth(container, {"method": "custom", "path": "custom_path.py:auth"})

    # Dotted path conversion to py file check
    with patch("pathlib.Path.exists", return_value=True):
        with patch("agentflow_cli.src.app.loader.load_auth") as mock_load_auth:
            mock_auth_instance = MagicMock(spec=BaseAuth)
            mock_load_auth.return_value = mock_auth_instance
            
            # test "custom" method
            load_and_bind_auth(container, {"method": "custom", "path": "my.auth.path:auth"})
            container.bind_instance.assert_called_with(BaseAuth, mock_auth_instance, allow_none=True)

            # test "jwt" method
            from agentflow_cli.src.app.core.auth.jwt_auth import JwtAuth
            load_and_bind_auth(container, {"method": "jwt", "path": "some_path.py:auth"})
            # JwtAuth is instantiated inside, so we check if standard JwtAuth was bound
            args, kwargs = container.bind_instance.call_args
            assert args[0] == BaseAuth
            assert isinstance(args[1], JwtAuth)

            # test "none" method
            load_and_bind_auth(container, {"method": "none", "path": "some_path.py:auth"})
            container.bind_instance.assert_called_with(BaseAuth, None, allow_none=True)


def test_load_and_bind_authorization():
    container = MagicMock(spec=InjectQ)
    
    # Path provided
    mock_auth_backend = MagicMock(spec=AuthorizationBackend)
    with patch("agentflow_cli.src.app.loader.load_authorization", return_value=mock_auth_backend):
        load_and_bind_authorization(container, "mod:auth")
        container.bind_instance.assert_called_once_with(AuthorizationBackend, mock_auth_backend)

    # Path is None
    container.reset_mock()
    load_and_bind_authorization(container, None)
    args, kwargs = container.bind_instance.call_args
    assert args[0] == AuthorizationBackend
    assert isinstance(args[1], DefaultAuthorizationBackend)


@pytest.mark.asyncio
async def test_attach_all_modules():
    config = MagicMock(spec=GraphConfig)
    config.graph_path = "mod:graph"
    config.auth_config.return_value = {"method": "none", "path": "path.py:auth"}
    config.thread_name_generator_path = "mod:generator"
    config.authorization_path = "mod:authorization"

    container = MagicMock(spec=InjectQ)
    
    mock_graph = MagicMock(spec=CompiledGraph)
    mock_generator = MagicMock(spec=ThreadNameGenerator)
    mock_auth_backend = MagicMock(spec=AuthorizationBackend)

    with patch("agentflow_cli.src.app.loader.load_graph", return_value=mock_graph), \
         patch("agentflow_cli.src.app.loader.load_thread_name_generator", return_value=mock_generator), \
         patch("agentflow_cli.src.app.loader.load_authorization", return_value=mock_auth_backend), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("agentflow_cli.src.app.core.config.media_settings.get_media_settings") as mock_get_media_settings:
         
        mock_get_media_settings.return_value = MagicMock()
        
        result = await attach_all_modules(config, container)
        
        assert result == mock_graph
        # verify bindings
        container.bind_instance.assert_any_call(BaseAuth, None, allow_none=True)
        container.bind_instance.assert_any_call(ThreadNameGenerator, mock_generator)
        container.bind_instance.assert_any_call(AuthorizationBackend, mock_auth_backend)
        
        # Test branch where config has no thread name generator and no auth config
        config.thread_name_generator_path = None
        config.auth_config.return_value = None
        
        container.reset_mock()
        await attach_all_modules(config, container)
        container.bind_instance.assert_any_call(ThreadNameGenerator, None, allow_none=True)
        container.bind_instance.assert_any_call(BaseAuth, None, allow_none=True)
