from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.logger import logger
from fastapi_injector import Injected
from taskiq import AsyncTaskiqTask

from src.app.routers.auth.schemas import UserSchema
from src.app.routers.auth.services import UserService
from src.app.tasks.user_tasks import add_task_math
from src.app.utils import generate_swagger_responses, success_response


# dependencies=[Depends(get_current_user)]
router = APIRouter(
    tags=["User"],
)


@router.get(
    "/v1/users/{user_id}",
    responses=generate_swagger_responses(UserSchema),
    summary="Get user details",
    description="Get user details by user id",
    openapi_extra={},
)
async def user_details(
    request: Request,
    user_id: UUID,
    service: UserService = Injected(UserService),
):
    res2: AsyncTaskiqTask = await add_task_math.kiq(
        x=5,
        y=5,
    )
    logger.info(res2.task_id)

    #
    # res3: AsyncTaskiqTask = await post_processing_user.kiq(
    #     user_id=5
    # )
    # print(res3.task_id)
    # res = await service.get_user(user_id)
    return success_response({"message": "success"}, request)
