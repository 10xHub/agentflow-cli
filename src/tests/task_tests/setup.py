from injector import Injector

from src.app.routers.auth.repositories import UserRepo
from src.tests.fake_data.fake_user_repo import FakeUserRepo


def register_fake_repos(injector: Injector):
    """
    Registers fake repositories for testing purposes.

    This function binds the `FakeUserRepo` to the `UserRepo` interface using the provided injector.

    Args:
        injector (Injector): The dependency injector used to bind the fake repositories.
    """
    injector.binder.bind(UserRepo, FakeUserRepo())
