from tortoise import fields

from .inheritance_table import CustomManager, TimestampMixin
from .user_constants import UserTableConst


class UserDeviceTable(TimestampMixin):
    """
    UserDeviceTable represents a table for storing user device information.

    Attributes:
        id (int): Primary key for the table.
        device_name (str): Name of the device, with a maximum length of 100 characters.
        device_id (str): Unique identifier for the device, with a maximum length of 100 characters.
        location (str): Location of the device, with a maximum length of 100 characters.
        user (ForeignKeyField): Foreign key relationship to the user table.

    Methods:
        __str__(): Returns the device name as the string representation of the object.

    Meta:
        table (str): Name of the table in the database.

    PydanticMeta:
        exclude (list): List of fields to exclude from Pydantic model serialization.
    """

    id = fields.IntField(pk=True)
    device_name = fields.CharField(max_length=100, default="")
    device_id = fields.CharField(max_length=100, default="")
    location = fields.CharField(max_length=100, default="")

    user = fields.ForeignKeyField(UserTableConst.USER_TABLE, related_name="device_user")

    def __str__(self):
        return self.device_name

    class Meta:
        table = "t_user_devices"
        manager = CustomManager()

    class PydanticMeta:
        exclude = ["created_at", "updated_at", "status"]
