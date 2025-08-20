from tortoise import Model

from src.app.core import logger


class Router:
    """
    A database router to control which database to use for read and write operations.

    Methods:
        db_for_read(model: type[Model]) -> str:
            Determines the database to use for read operations.

        db_for_write(model: type[Model]) -> str:
            Determines the database to use for write operations.
    """

    def db_for_read(self, model: type[Model]):
        logger.debug(f"Reading from database: {model}")
        return "master"

    def db_for_write(self, model: type[Model]):
        logger.debug(f"Writing to database: {model}")
        return "master"
