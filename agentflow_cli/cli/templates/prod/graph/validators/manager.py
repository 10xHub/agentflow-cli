from agentflow.utils.callbacks import CallbackManager

from .lifecyle import AgentLifecycleHook
from .validators import prompt_validator


callback_manager = CallbackManager()
callback_manager.register_input_validator(prompt_validator)
callback_manager.register_lifecycle_hook(AgentLifecycleHook())
