from collections import namedtuple

from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger


class Constant(type):
    def get_dicts(cls):
        for k, v in cls.__dict__.items():
            if not k.startswith("__"):
                yield v._asdict()


permission = namedtuple("permission", "id name label")
job_trigger = namedtuple("job_trigger", "id name label description")
available_job = namedtuple("available_job", "name label")
log_type = namedtuple("log_type", "id label")
bs_variant = namedtuple("bs_variant", "id name label title")
boolean_type = namedtuple("boolean_type", "id label")


class Permission(object, metaclass=Constant):
    UserLoginView = permission(1, "post_login_view", "Login")
    UserLogoutView = permission(2, "post_logout_view", "Logout")
    UserListView = permission(3, "get_users_view", "View user list")
    UserAddView = permission(4, "post_users_view", "Add users")
    UserGetView = permission(5, "get_user_view", "View user")
    UserEditView = permission(6, "put_user_view", "Edit user")
    UserDeleteView = permission(7, "delete_user_view", "Delete user")
    UserLogView = permission(8, "get_user_log_view", "View user log")
    JobListView = permission(9, "get_jobs_view", "View job list")
    JobAddView = permission(10, "post_jobs_view", "Add jobs")
    JobGetView = permission(11, "get_job_view", "View job")
    JobEditView = permission(12, "put_job_view", "Edit job")
    JobDeleteView = permission(13, "delete_job_view", "Delete jobs")
    JobPauseView = permission(14, "post_pause_job_view", "Pause/resume jobs")
    JobLogView = permission(15, "get_job_log_view", "View job log")
    ErrorLogView = permission(16, "get_error_log_view", "View error log")


class JobTrigger(object, metaclass=Constant):
    Cron = job_trigger(1, "cron", "Cron",
                       ("Job triggers when current time matches all "
                        "specified time constraints, similarly to how "
                        "the UNIX cron scheduler works."))
    Date = job_trigger(2, "date", "Date",
                       ("Schedules a job to be executed once "
                        "at the specified time."))
    Interval = job_trigger(3, "interval", "Interval",
                           ("Schedules a job to be run periodically, "
                            "on selected intervals."))


class AvailableJob(object, metaclass=Constant):
    TestJob = available_job("test_job", "Test Job")
    MonitorSockets = available_job("monitor_sockets", "Monitor sockets")


class BSVariant(object, metaclass=Constant):
    Default = bs_variant(1, "default", "Default", "Message")
    Primary = bs_variant(2, "primary", "Primary", "Message")
    Secondary = bs_variant(3, "secondary", "Secondary", "Message")
    Danger = bs_variant(4, "danger", "Danger", "Error")
    Warning = bs_variant(5, "warning", "Warning", "Warning")
    Success = bs_variant(6, "success", "Success", "Success")
    Info = bs_variant(7, "info", "Info", "Info")
    Light = bs_variant(8, "light", "Light", "Message")
    Dark = bs_variant(9, "dark", "Dark", "Message")


class ControllerResult:
    Success = True
    Failure = False


class LogType(object, metaclass=Constant):
    UserLoginView = log_type(1, "User login")
    UserLogoutView = log_type(2, "User logout")
    UserListView = log_type(3, "User list")
    UserAddView = log_type(4, "User add")
    UserGetView = log_type(5, "User view")
    UserEditView = log_type(6, "User edit")
    UserDeleteView = log_type(7, "User delete")
    JobListView = log_type(8, "Job list")
    JobAddView = log_type(9, "Job add")
    JobGetView = log_type(10, "Job view")
    JobEditView = log_type(11, "Job edit")
    JobDeleteView = log_type(12, "Job delete")
    JobPauseView = log_type(13, "Job pause")
    CommonJobDataView = log_type(14, "Common job data view")
    CommonUserDataView = log_type(15, "Common user data view")
    LogView = log_type(16, "Log view")


class BooleanType(object, metaclass=Constant):
    FalseType = boolean_type("false", "False")
    TrueType = boolean_type("true", "True")


trigger_map = {
    "cron": {
        "trigger": CronTrigger,
        "parameters": ["year", "month", "day", "day_of_week", "hour",
                       "minute", "start_date", "end_date"]},
    "interval": {
        "trigger": IntervalTrigger,
        "parameters": ["weeks", "days", "hours", "minutes",
                       "seconds", "start_date", "end_date"]},
    "date": {
        "trigger": DateTrigger,
        "parameters": ["run_date"]}}

filter_labels = {
    "id": "Specify ID",
    "user": "Specify User ID",
    "request_ip": "Specify Request IP",
    "log_type": "Select Log type",
    "created_at": "Select created range",
    "request_data": "Specify Request data",
    "request_url": "Specify Request URL",
    "response_data": "Specify Response data",
    "last_login_at": "Select last login range",
    "started_at": "Select started range",
    "finished_at": "Select finished range",
    "username": "Specify Username",
    "is_admin": "User is admin",
    "is_active": "User is active",
    "error": "Specify error text",
    "traceback": "Specify error traceback text",
    "job_id": "Specify Job ID"
}
