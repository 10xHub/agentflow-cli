from abc import ABC, abstractmethod
from uuid import UUID

from src.app.routers.auth.schemas import UserSchema


class UserRepoAbstract(ABC):
    """
    Abstract base class for user-related database operations.

    This class provides abstract methods to interact with the user data
    stored in the database.
    """

    @abstractmethod
    async def get_user(self, user_id: UUID) -> UserSchema:
        """
        Retrieves a user by their unique identifier (UUID).

        Args:
            user_id (UUID): The unique identifier of the user.

        Returns:
            UserModel: An instance of the UserModel containing the user data.

        Raises:
            DoesNotExist: If the user is not found.
        """
        raise NotImplementedError
