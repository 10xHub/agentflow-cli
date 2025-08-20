from uuid import UUID

from injector import singleton

from src.app.core import logger
from src.app.db import UserTable
from src.app.routers.auth.schemas import UserSchema

from .abstract_user_repo import UserRepoAbstract


@singleton
class UserRepo(UserRepoAbstract):
    """
    Repository class for user-related database operations.

    This class provides methods to interact with the user data
    stored in the database.
    """

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
        model = await UserTable.get(user_id=user_id)
        # Convert the retrieved database model into a UserModel instance.
        logger.debug(f"Retrieved user: {model} from the database with ID: {user_id}")
        return UserSchema(
            user_id=model.user_id,
            email=model.email,
            fullname=model.fullname,
            phone=model.phone,
            token=model.token,
            type=model.type,
        )
