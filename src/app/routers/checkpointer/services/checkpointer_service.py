"""Checkpointer service layer."""

from typing import Optional

from langchain_core.runnables import RunnableConfig
from pyagenity.base import BaseCheckpointer
from pyagenity.memory import MemoryCheckpointer

from src.app.routers.checkpointer.schemas.checkpointer_schemas import (
    CheckpointerResponseSchema,
    CleanupSchema,
    DeleteMessageSchema,
    GetMessageSchema,
    ListMessagesSchema,
    MessageResponseSchema,
    MessagesListResponseSchema,
    PutMessagesSchema,
    StateResponseSchema,
    StateSchema,
)


class CheckpointerService:
    """Service for checkpointer operations."""

    def __init__(self, checkpointer: Optional[BaseCheckpointer] = None):
        """Initialize the checkpointer service.

        Args:
            checkpointer: The checkpointer instance to use.
                If None, a default memory checkpointer will be created.
        """
        self.checkpointer = checkpointer or MemoryCheckpointer()

    def _check_checkpointer(self) -> Optional[CheckpointerResponseSchema]:
        """Check if checkpointer is available.

        Returns:
            Error response if checkpointer is null, None if available.
        """
        if self.checkpointer is None:
            return CheckpointerResponseSchema(
                success=False, message="Checkpointer is not available or not initialized"
            )
        return None

    async def get_state(self, schema: StateSchema) -> StateResponseSchema:
        """Get state from checkpointer.

        Args:
            schema: The state schema with config.

        Returns:
            State response with state data or error.
        """
        error_response = self._check_checkpointer()
        if error_response:
            return StateResponseSchema(success=False, message=error_response.message)

        try:
            config = RunnableConfig(**schema.config)
            state = await self.checkpointer.aget(config)

            if state is None:
                return StateResponseSchema(
                    success=True, message="No state found for the given configuration", state=None
                )

            return StateResponseSchema(
                success=True,
                message="State retrieved successfully",
                state=state.as_dict() if hasattr(state, "as_dict") else dict(state),
            )
        except Exception as e:
            return StateResponseSchema(success=False, message=f"Failed to get state: {e!s}")

    async def put_state(self, schema: StateSchema) -> StateResponseSchema:
        """Put state to checkpointer.

        Args:
            schema: The state schema with config and state data.

        Returns:
            State response indicating success or failure.
        """
        error_response = self._check_checkpointer()
        if error_response:
            return StateResponseSchema(success=False, message=error_response.message)

        try:
            config = RunnableConfig(**schema.config)
            await self.checkpointer.aput(config, schema.state)

            return StateResponseSchema(
                success=True, message="State stored successfully", state=schema.state
            )
        except Exception as e:
            return StateResponseSchema(success=False, message=f"Failed to put state: {e!s}")

    async def clear_state(self, schema: StateSchema) -> CheckpointerResponseSchema:
        """Clear state from checkpointer.

        Args:
            schema: The state schema with config.

        Returns:
            Response indicating success or failure.
        """
        error_response = self._check_checkpointer()
        if error_response:
            return error_response

        try:
            config = RunnableConfig(**schema.config)
            await self.checkpointer.aclear(config)

            return CheckpointerResponseSchema(success=True, message="State cleared successfully")
        except Exception as e:
            return CheckpointerResponseSchema(
                success=False, message=f"Failed to clear state: {e!s}"
            )

    async def put_messages(self, schema: PutMessagesSchema) -> CheckpointerResponseSchema:
        """Put messages to checkpointer.

        Args:
            schema: The put messages schema.

        Returns:
            Response indicating success or failure.
        """
        error_response = self._check_checkpointer()
        if error_response:
            return error_response

        try:
            config = RunnableConfig(**schema.config)
            await self.checkpointer.aput_messages(config, schema.messages, metadata=schema.metadata)

            return CheckpointerResponseSchema(
                success=True, message=f"Successfully stored {len(schema.messages)} messages"
            )
        except Exception as e:
            return CheckpointerResponseSchema(
                success=False, message=f"Failed to put messages: {e!s}"
            )

    async def get_message(self, schema: GetMessageSchema) -> MessageResponseSchema:
        """Get a message from checkpointer.

        Args:
            schema: The get message schema.

        Returns:
            Message response with message data or error.
        """
        error_response = self._check_checkpointer()
        if error_response:
            return MessageResponseSchema(success=False, message=error_response.message)

        try:
            config = RunnableConfig(**schema.config)
            message = await self.checkpointer.aget_message(config)

            if message is None:
                return MessageResponseSchema(
                    success=True,
                    message="No message found for the given configuration",
                    message_data=None,
                )

            # Convert message to dict if it has to_dict method
            message_data = message.to_dict() if hasattr(message, "to_dict") else dict(message)

            return MessageResponseSchema(
                success=True, message="Message retrieved successfully", message_data=message_data
            )
        except Exception as e:
            return MessageResponseSchema(success=False, message=f"Failed to get message: {e!s}")

    async def list_messages(self, schema: ListMessagesSchema) -> MessagesListResponseSchema:
        """List messages from checkpointer.

        Args:
            schema: The list messages schema.

        Returns:
            Messages list response with messages data or error.
        """
        error_response = self._check_checkpointer()
        if error_response:
            return MessagesListResponseSchema(success=False, message=error_response.message)

        try:
            config = RunnableConfig(**schema.config)
            messages = await self.checkpointer.alist_messages(
                config, search=schema.search, offset=schema.offset, limit=schema.limit
            )

            # Convert messages to dict format
            messages_data = []
            for msg in messages:
                if hasattr(msg, "to_dict"):
                    messages_data.append(msg.to_dict())
                else:
                    messages_data.append(dict(msg))

            return MessagesListResponseSchema(
                success=True,
                message=f"Retrieved {len(messages_data)} messages",
                messages=messages_data,
                total=len(messages_data),
            )
        except Exception as e:
            return MessagesListResponseSchema(
                success=False, message=f"Failed to list messages: {e!s}"
            )

    async def delete_message(self, schema: DeleteMessageSchema) -> CheckpointerResponseSchema:
        """Delete a message from checkpointer.

        Args:
            schema: The delete message schema.

        Returns:
            Response indicating success or failure.
        """
        error_response = self._check_checkpointer()
        if error_response:
            return error_response

        try:
            config = RunnableConfig(**schema.config)
            await self.checkpointer.adelete_message(config)

            return CheckpointerResponseSchema(success=True, message="Message deleted successfully")
        except Exception as e:
            return CheckpointerResponseSchema(
                success=False, message=f"Failed to delete message: {e!s}"
            )

    async def cleanup(self, schema: CleanupSchema) -> CheckpointerResponseSchema:
        """Cleanup checkpointer.

        Args:
            schema: The cleanup schema.

        Returns:
            Response indicating success or failure.
        """
        error_response = self._check_checkpointer()
        if error_response:
            return error_response

        try:
            config = RunnableConfig(**schema.config)
            await self.checkpointer.acleanup(config)

            return CheckpointerResponseSchema(
                success=True, message="Cleanup completed successfully"
            )
        except Exception as e:
            return CheckpointerResponseSchema(success=False, message=f"Failed to cleanup: {e!s}")
