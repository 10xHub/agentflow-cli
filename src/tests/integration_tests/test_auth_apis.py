# from src.tests.integration_tests.test_main import client


# # ruff: noqa: PLR2004
# def test_get_user_api():
#     user_id = "123e4567-e89b-12d3-a456-426614174000"
#     response = client.get(f"v1/users/{user_id}")

#     assert response.status_code == 200
#     user_data = response.json()
#     data = user_data["data"]
#     assert data["user_id"] == user_id
#     assert data["fullname"] == "testuser"
#     assert data["email"] == "testuser@example.com"


# def test_get_invalid_input():
#     user_id = "nonexistent-uuid"
#     response = client.get(f"v1/users/{user_id}")
#     assert response.status_code == 422


# def test_get_not_found():
#     user_id = "90387798-cbc0-4df7-9ce2-308fd9ee9fbf"
#     response = client.get(f"v1/users/{user_id}")
#     assert response.status_code == 404
