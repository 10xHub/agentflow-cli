# import pytest

# from src.app.tasks.user_tasks import add_task_math, post_processing_user


# @pytest.mark.asyncio
# async def test_add_task_math():
#     task = await add_task_math.kiq(x=5, y=5)
#     result = await task.wait_result()
#     assert result.return_value == 10  # noqa


# @pytest.mark.asyncio
# async def test_post_processing_user():
#     task = await post_processing_user.kiq(user_id=5)
#     result = await task.wait_result()
#     assert result.return_value is None
