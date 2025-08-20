import strawberry


@strawberry.type
class UserItem:
    name: str
    id: int
    email: str


@strawberry.type
class Query:
    """
    Query class for GraphQL schema.

    This class defines the root query type for the GraphQL schema using Strawberry.

    Attributes:
        example (str): A simple example field that returns a greeting message.
        users (list[UserItem]): An asynchronous field that returns a list of users.

    Methods:
        example(info: strawberry.Info) -> str:
            Returns a greeting message using the context information.

        users(info: strawberry.Info, offset: int = 0, limit: int = 10) -> list[UserItem]:
            Asynchronously fetches a list of users with pagination support.
            In a real application, this would fetch users from a database or another data source.
            For demonstration purposes, it returns dummy data.

            Args:
                info (strawberry.Info): The GraphQL context information.
                offset (int, optional): The starting index for pagination. Defaults to 0.
                limit (int, optional): The maximum number of users to return. Defaults to 10.

            Returns:
                list[UserItem]: A list of UserItem objects.
    """

    @strawberry.field
    def example(self, info: strawberry.Info) -> str:
        return f"Hello {info.context.name}, {info.context.greeting}"

    @strawberry.field
    async def users(
        self, info: strawberry.Info, offset: int = 0, limit: int = 10
    ) -> list[UserItem]:
        # In a real application, this would fetch users from a
        # database or another data source
        # For demonstration purposes, returning dummy data
        users = [
            UserItem(name="User1", id=1, email="user1@example.com"),  # type: ignore
            UserItem(name="User2", id=2, email="user2@example.com"),  # type: ignore
            UserItem(name="User3", id=3, email="user3@example.com"),  # type: ignore
            UserItem(name="User1", id=1, email="user1@example.com"),  # type: ignore
            UserItem(name="User2", id=2, email="user2@example.com"),  # type: ignore
            UserItem(name="User3", id=3, email="user3@example.com"),  # type: ignore
            UserItem(name="User1", id=1, email="user1@example.com"),  # type: ignore
            UserItem(name="User2", id=2, email="user2@example.com"),  # type: ignore
            UserItem(name="User3", id=3, email="user3@example.com"),  # type: ignore
        ]
        # Apply offset and limit to the list of users
        return users[offset : offset + limit]
