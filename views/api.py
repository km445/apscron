from controllers.auth import LoginUserController, LogutUserController
from controllers.users import (UserListController, UserAddController,
                               UserEditController, UserDeleteController,
                               CommonUserDataController)
from controllers.jobs import (JobListController, JobAddController,
                              JobEditController, JobDeleteController,
                              JobPauseController, CommonJobDataController)
from controllers.logs import (UserLogController, JobLogController,
                              ErrorLogController)
from utils import get_error_response
from exceptions import MethodNotAllowedException


async def login_view(request):
    return await LoginUserController(request).call()


async def logout_view(request):
    return await LogutUserController(request).call()


async def users_view(request):
    if request.method == "GET":
        return await UserListController(request).call()
    elif request.method == "POST":
        return await UserAddController(request).call()
    else:
        return await get_error_response(MethodNotAllowedException)


async def user_view(request):
    if request.method in ["GET", "PUT"]:
        return await UserEditController(request).call(**request.match_info)
    elif request.method == "DELETE":
        return await UserDeleteController(request).call(**request.match_info)
    else:
        return await get_error_response(MethodNotAllowedException)


async def common_user_data(request):
    return await CommonUserDataController(request).call()


async def jobs_view(request):
    if request.method == "GET":
        return await JobListController(request).call()
    elif request.method == "POST":
        return await JobAddController(request).call()
    else:
        return await get_error_response(MethodNotAllowedException)


async def job_view(request):
    if request.method in ["GET", "PUT"]:
        return await JobEditController(request).call(**request.match_info)
    elif request.method == "DELETE":
        return await JobDeleteController(request).call(**request.match_info)
    else:
        return await get_error_response(MethodNotAllowedException)


async def pause_job_view(request):
    return await JobPauseController(request).call(**request.match_info)


async def common_job_data(request):
    return await CommonJobDataController(request).call()


async def user_log_view(request):
    return await UserLogController(request).call()


async def job_log_view(request):
    return await JobLogController(request).call()


async def error_log_view(request):
    return await ErrorLogController(request).call()


routes = (
    dict(method="POST", path="/auth/login",
         handler=login_view, name="login_view"),
    dict(method="POST", path="/auth/logout",
         handler=logout_view, name="logout_view"),
    dict(method="*", path="/users",
         handler=users_view, name="users_view"),
    dict(method="*", path="/users/{user_id}",
         handler=user_view, name="user_view"),
    dict(method="GET", path="/users_common_data",
         handler=common_user_data, name="common_user_data"),
    dict(method="*", path="/jobs",
         handler=jobs_view, name="jobs_view"),
    dict(method="*", path="/jobs/{job_id}",
         handler=job_view, name="job_view"),
    dict(method="POST", path="/jobs/pause/{job_id}",
         handler=pause_job_view, name="pause_job_view"),
    dict(method="GET", path="/jobs_common_data",
         handler=common_job_data, name="common_job_data"),
    dict(method="GET", path="/logs/jobs",
         handler=job_log_view, name="job_log_view"),
    dict(method="GET", path="/logs/users",
         handler=user_log_view, name="user_log_view"),
    dict(method="GET", path="/logs/errors",
         handler=error_log_view, name="error_log_view"),
)
