class UserTypesConst:
    ADMIN = 0
    USER = 1


# All the tables inside this module
# To create relation with other module
class UserTableConst:
    USER_TABLE = "tables.UserTable"
    DEVICE_TABLE = "tables.UserDeviceTable"


# All the tables inside this module will be registered
USER_TABLES = [
    "src.app.db.tables.user_tables",
    "src.app.db.tables.user_device_tables",
]
