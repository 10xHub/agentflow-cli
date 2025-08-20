# from unittest.mock import AsyncMock, MagicMock
# from uuid import UUID

# import pytest

# from src.app.routers.auth.repositories import UserRepo
# from src.app.routers.auth.schemas import UserSchema
# from src.app.routers.auth.services import UserService


# @pytest.fixture
# def user_repo_mock():
#     """Fixture for user repo mock."""
#     return AsyncMock(spec=UserRepo)


# @pytest.fixture
# def user_service(user_repo_mock):
#     """Fixture for user service."""
#     return UserService(user_repo_mock)


# @pytest.mark.asyncio
# async def test_get_user_success(user_service, user_repo_mock):
#     # Arrange
#     user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
#     mock_user = MagicMock(spec=UserSchema)
#     mock_user.user_id = user_id
#     mock_user.fullname = "testuser"
#     user_repo_mock.get_user.return_value = mock_user

#     # Act
#     result = await user_service.get_user(user_id)

#     # Assert
#     user_repo_mock.get_user.assert_called_once_with(user_id)
#     assert isinstance(result, UserSchema)
#     assert str(result.user_id) == str(user_id)
#     assert result.fullname == "testuser"


# @pytest.mark.asyncio
# async def test_get_user_success2(user_service, user_repo_mock):
#     # Arrange
#     user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
#     user_repo_mock.get_user.return_value = UserSchema(
#         user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
#         fullname="testuser",
#         phone="1234567890",
#         token="",
#         type=0,
#         email="testuser@example.com",
#     )

#     # Act
#     result = await user_service.get_user(user_id)

#     # Assert
#     user_repo_mock.get_user.assert_called_once_with(user_id)
#     assert isinstance(result, UserSchema)
#     assert str(result.user_id) == str(user_id)
#     assert result.fullname == "testuser"


# @pytest.mark.asyncio
# async def test_get_user_not_found(user_service, user_repo_mock):
#     # Arrange
#     user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
#     user_repo_mock.get_user.side_effect = Exception("User not found")

#     # Act & Assert
#     with pytest.raises(Exception, match="User not found"):
#         await user_service.get_user(user_id)

#     user_repo_mock.get_user.assert_called_once_with(user_id)
