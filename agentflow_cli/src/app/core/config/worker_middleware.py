# from typing import Any

# from taskiq import TaskiqMessage, TaskiqMiddleware, TaskiqResult

# from agentflow_cli.src.app.core import logger


# class MonitoringMiddleware(TaskiqMiddleware):
#     """
#     Middleware for monitoring task execution in Taskiq.

#     This middleware logs various stages of task execution, including startup,
#     shutdown, pre-execution, post-save, and error handling.

#     Methods:
#         startup: Logs a debug message when the middleware starts up.
#         shutdown: Logs a debug message when the middleware shuts down.
#         pre_execute: Logs an info message before a task is executed.
#         post_save: Logs info and debug messages after a task is saved.
#         on_error: Logs error messages when an exception occurs during task execution.
#     """

#     def startup(self) -> None:
#         """
#         Perform startup operations.

#         This method logs a debug message indicating that the startup process is running.

#         Returns:
#             None
#         """
#         logger.debug("RUNNING STARTUP")

#     def shutdown(self) -> None:
#         """
#         Perform shutdown operations.

#         This method logs a debug message indicating that the shutdown process is running.

#         Returns:
#             None
#         """
#         logger.debug("RUNNING SHUTDOWN")

#     def pre_execute(self, message: "TaskiqMessage") -> TaskiqMessage:
#         """
#         Pre-execution hook for processing a TaskiqMessage.

#         This method is called before the task execution begins. It logs the task ID
#         of the incoming message and returns the message unchanged.

#         Args:
#             message (TaskiqMessage): The message to be processed.

#         Returns:
#             TaskiqMessage: The same message that was passed in.
#         """
#         logger.info(f"PRE EXECUTE: {message.task_id}")
#         return message

#     def post_save(self, message: "TaskiqMessage", result: "TaskiqResult[Any]") -> None:
#         """
#         Handles post-save operations for a task.

#         This method is called after a task is saved. It logs the task ID and the result of the
#           task.

#         Args:
#             message (TaskiqMessage): The message object containing task details.
#             result (TaskiqResult[Any]): The result object containing the outcome of the task.

#         Returns:
#             None
#         """
#         logger.info(f"Saved Task: {message.task_id}")
#         logger.debug(f"Result: {result.return_value}")

#     def on_error(
#         self,
#         message: "TaskiqMessage",
#         result: "TaskiqResult[Any]",
#         exception: BaseException,
#     ) -> None:
#         """
#         Handles errors that occur during task execution.

#         Args:
#             message (TaskiqMessage): The message associated with the task.
#             result (TaskiqResult[Any]): The result of the task execution.
#             exception (BaseException): The exception that was raised.

#         Returns:
#             None
#         """
#         logger.error(f"Exception on task: {message.task_id}", exc_info=exception)
#         logger.error(
#             f"Exception on task {message.task_id} Result: {result.return_value if result
#               else None}"
#         )
