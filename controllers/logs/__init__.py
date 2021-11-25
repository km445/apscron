import json

from constants import LogType, Permission
from controllers import UniversalController
from utils import convert_types

from models import UserLog, JobLog, ErrorLog


class BaseLogUniversalController(UniversalController):
    save_log = False

    def __init__(self, request):
        super(BaseLogUniversalController, self).__init__(
            request, LogType.LogView.id)

    async def _call(self):
        data = await self._process()
        data["items"] = json.loads(data.get("items"))
        return data


class UserLogController(BaseLogUniversalController):
    text_filter_names = ("id", "user")
    select_filter_names = ("log_type",)
    daterange_filter_names = ("created_at",)
    text_like_filter_names = ("error", "request_data", "response_data",
                              "request_ip", "request_url")
    model = UserLog
    required_permissions = [Permission.UserLogView.name]

    async def _process(self):
        query = self._select_query()
        result = await self._filter_query(query)
        logs = list(await self.db.execute(self._get_list(result).dicts()))
        pagination = await self._get_pagination(result)
        return {"log_title": "APScron User Logs",
                "items": json.dumps(logs, default=convert_types),
                "filters": self._get_filters(),
                "pagination": pagination}


class JobLogController(BaseLogUniversalController):
    text_filter_names = ("id", "user")
    daterange_filter_names = ("started_at", "finished_at")
    text_like_filter_names = ("error", "job_id")
    model = JobLog
    required_permissions = [Permission.JobLogView.name]

    async def _process(self):
        query = self._select_query()
        result = await self._filter_query(query)
        logs = list(await self.db.execute(self._get_list(result).dicts()))
        pagination = await self._get_pagination(result)
        return {"log_title": "APScron Job Logs",
                "items": json.dumps(logs, default=convert_types),
                "filters": self._get_filters(),
                "pagination": pagination}


class ErrorLogController(BaseLogUniversalController):
    text_filter_names = ("id",)
    daterange_filter_names = ("created_at",)
    text_like_filter_names = (
        "request_data", "request_ip", "request_url", "error", "traceback")
    model = ErrorLog
    required_permissions = [Permission.ErrorLogView.name]

    async def _process(self):
        query = self._select_query()
        result = await self._filter_query(query)
        logs = list(await self.db.execute(self._get_list(result).dicts()))
        pagination = await self._get_pagination(result)
        return {"log_title": "APScron Error Logs",
                "items": json.dumps(logs, default=convert_types),
                "filters": self._get_filters(),
                "pagination": pagination}
