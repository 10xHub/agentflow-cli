from uuid import UUID

from injector import inject, singleton

from src.app.core import logger
from src.app.routers.auth.repositories import UserRepo
from src.app.routers.auth.schemas import UserSchema


@singleton
class UserService:
    """
    Service class for user-related business logic and operations.

    This class acts as an intermediary between the controllers and the
    UserRepository, facilitating user-related operations.
    """

    @inject
    def __init__(self, user_repo: UserRepo):
        """
        Initializes the UserService with a UserRepository instance.

        Args:
            user_repo (UserRepository): An instance of UserRepository to
                                        perform database operations.
        """
        self._user_repo = user_repo

    async def get_user(self, user_id: UUID) -> UserSchema:
        """
        Retrieves a user by their unique identifier (UUID).

        Args:
            user_id (UUID): The unique identifier of the user to retrieve.

        Returns:
            UserModel: An instance of UserModel containing the user's data.

        """
        # Fetch user model from the user repository.
        logger.debug(f"Fetching user with ID: {user_id}")
        return await self._user_repo.get_user(user_id)
