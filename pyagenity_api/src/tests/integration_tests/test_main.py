# from starlette.testclient import TestClient

# from src.app.core.auth import get_current_user
# from src.app.main import app, injector
# from src.app.routers.auth.repositories import UserRepo
# from src.app.utils.schemas import AuthUserSchema
# from src.tests.fake_data.fake_user_repo import FakeUserRepo


# client = TestClient(app)
# injector.binder.bind(UserRepo, FakeUserRepo())


# def override_current_user():
#     return AuthUserSchema(
#         name="Test User",
#         role="admin",
#         company=1,
#         uuid="1234",
#         user_id="1234",
#         email="someone@gmail.com",
#         email_verified=True,
#         firebase={},
#         uid="1234",
#     )


# app.dependency_overrides[get_current_user] = override_current_user
