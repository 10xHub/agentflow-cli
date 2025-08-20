from tortoise import fields

from .inheritance_table import CustomManager, TimestampMixin
from .user_constants import UserTypesConst


class UserTable(TimestampMixin):
    """
    UserTable model representing a user in the database.

    Attributes:
        user_id (UUIDField): Primary key for the user, not auto-generated.
        email (CharField): Email address of the user, indexed and unique.
        fullname (CharField): Full name of the user, default is an empty string.
        phone (CharField): Phone number of the user, default is an empty string.
        token (CharField): Token associated with the user, indexed, default is an empty string.
        type (IntField): Type of the user, default is UserTypesConst.USER.

    Methods:
        __str__: Returns the full name of the user.

    Meta:
        table (str): Name of the database table.

    PydanticMeta:
        exclude (list): Fields to exclude from Pydantic model.
    """

    user_id = fields.UUIDField(primary_key=True, generated=False)
    email = fields.CharField(db_index=True, unique=True, null=False, max_length=255)
    fullname = fields.CharField(max_length=1000, default="")
    phone = fields.CharField(max_length=100, default="")
    token = fields.CharField(max_length=1000, default="", db_index=True)
    type = fields.IntField(max_length=1000, default=UserTypesConst.USER)

    def __str__(self):
        return self.fullname

    class Meta:
        table = "t_user"
        manager = CustomManager()

    class PydanticMeta:
        exclude = ["created_at", "status"]
