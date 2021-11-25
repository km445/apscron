from controllers.front import (
    FrontLoginController, FrontGetUsersController, FrontPostUsersController,
    FrontGetUserController, FrontGetJobsController, FrontPostJobsController,
    FrontGetJobController, FrontLogController, FrontErrorController)


async def front_login_view(request):
    return await FrontLoginController(request).call()


async def front_get_users_view(request):
    return await FrontGetUsersController(request).call()


async def front_post_users_view(request):
    return await FrontPostUsersController(request).call()


async def front_get_user_view(request):
    return await FrontGetUserController(request).call()


async def front_get_jobs_view(request):
    return await FrontGetJobsController(request).call()


async def front_post_jobs_view(request):
    return await FrontPostJobsController(request).call()


async def front_get_job_view(request):
    return await FrontGetJobController(request).call()


async def front_user_log_view(request):
    return await FrontLogController(request).call("users")


async def front_job_log_view(request):
    return await FrontLogController(request).call("jobs")


async def front_error_log_view(request):
    return await FrontLogController(request).call("errors")


async def front_error_view(request):
    return await FrontErrorController(request).call()


routes = (
    dict(method="GET", path="/front/login",
         handler=front_login_view, name="front_login_view"),
    dict(method="GET", path="/front/users",
         handler=front_get_users_view, name="front_get_users_view"),
    dict(method="GET", path="/front/users/add",
         handler=front_post_users_view, name="front_post_users_view"),
    dict(method="GET", path="/front/users/{user_id}",
         handler=front_get_user_view, name="front_get_user_view"),
    dict(method="GET", path="/front/jobs",
         handler=front_get_jobs_view, name="front_get_jobs_view"),
    dict(method="GET", path="/front/jobs/add",
         handler=front_post_jobs_view, name="front_post_jobs_view"),
    dict(method="GET", path="/front/jobs/{job_id}",
         handler=front_get_job_view, name="front_get_job_view"),
    dict(method="GET", path="/front/logs/jobs",
         handler=front_job_log_view, name="front_job_log_view"),
    dict(method="GET", path="/front/logs/users",
         handler=front_user_log_view, name="front_user_log_view"),
    dict(method="GET", path="/front/logs/errors",
         handler=front_error_log_view, name="front_error_log_view"),
    dict(method="GET", path="/front/error",
         handler=front_error_view, name="front_error_view"),
)
