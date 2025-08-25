# from uuid import UUID

# from fastapi_injector import InjectedTaskiq

# from src.app.routers.auth.services import UserService
# from src.app.worker import broker


# @broker.task(task_name="add_task_math")
# def add_task_math(x: int, y: int):
#     """
#     Adds two integers together.

#     Args:
#         x (int): The first integer.
#         y (int): The second integer.

#     Returns:
#         int: The sum of the two integers.
#     """
#     return x + y


# @broker.task(task_name="user_service_post_processing")
# async def post_processing_user(user_id: int, service: UserService = InjectedTaskiq(UserService)):
#     """
#     Post-processes a user by fetching user details using the provided user service.

#     Args:
#         user_id (int): The ID of the user to be processed.
#         service (UserService, optional): An instance of UserService to fetch user details.
#             Defaults to an injected instance of UserService.

#     Returns:
#         dict: A dictionary representation of the user details.
#     """
#     user = await service.get_user(UUID("2b1e2ae4-ff8a-48f3-8729-be0d754432e9"))
#     return user.dict()
