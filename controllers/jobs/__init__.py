from importlib import import_module
from datetime import datetime

from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger

import config
from constants import (LogType, JobTrigger, AvailableJob,
                       trigger_map, BSVariant, Permission)
from controllers import UniversalController
from utils import flash
from exceptions import ServiceException


class BaseJobUniversalController(UniversalController):

    def _job_to_dict(self, job):
        attrs = ["id", "name", "next_run_time", "kwargs"]
        job_dict = {}
        for a in attrs:
            attr = getattr(job, a, None)
            if isinstance(attr, datetime):
                attr = attr.strftime("%Y-%m-%d %H:%M:%S")
            job_dict[a] = attr
        return job_dict

    def _verify_kwargs(self, kwargs):
        if not isinstance(kwargs, dict):
            raise ServiceException("Invalid job config")
        return kwargs

    def _verify_trigger(self, trigger):
        trigger_data = trigger_map.get(trigger)
        if not trigger_data:
            raise ServiceException("Invalid job trigger %s" % trigger)
        trigger_parameters_list = trigger_data["parameters"]
        trigger_class = trigger_data["trigger"]
        trigger_parameters = {}
        try:
            for param in trigger_parameters_list:
                received_param = self.request_data["data"].get(param)
                if received_param and received_param.isdigit():
                    trigger_parameters[param] = int(received_param)
                else:
                    trigger_parameters[param] = received_param or None
            trigger = trigger_class(
                timezone=config.DEFAULT_TIMEZONE, **trigger_parameters)
        except (TypeError, ValueError):
            raise ServiceException(
                "Invalid parameters for %s trigger" % trigger)
        return trigger

    def _verify_module(self, module, valid_modules):
        if module not in valid_modules:
            raise ServiceException("Invalid module %s" % module)

    def _verify_job(self, job_id):
        job = self.request.app["apscheduler"].get_job(job_id)
        if not job:
            raise ServiceException("Job id %s was not found" % job_id)
        if not self.user.is_admin and job.args[-1] != self.user.id:
            raise ServiceException(
                "User %s has no access to job id %s" % (
                    self.user.username, job_id))
        return job


class JobListController(BaseJobUniversalController):
    required_permissions = [Permission.UserListView.name]

    def __init__(self, request):
        super(JobListController, self).__init__(
            request, LogType.JobListView.id)
        self.save_log = False

    async def _call(self):
        jobs = self.request.app["apscheduler"].get_jobs()
        jobs = [self._job_to_dict(j)
                for j in jobs
                if self.user.is_admin or j.args[-1] == self.user.id]
        return {"items": jobs, "filters": self._get_filters()}


class JobAddController(BaseJobUniversalController):
    required_permissions = [Permission.JobAddView.name]

    def __init__(self, request):
        super(JobAddController, self).__init__(
            request, LogType.JobAddView.id)

    async def _call(self):
        available_jobs = list(AvailableJob.get_dicts())
        verified_data = self._verify_request_data(
            ("name", "kwargs", "module", "trigger"))
        valid_modules = [m.get("name") for m in available_jobs]
        job_module = verified_data["module"]
        self._verify_module(job_module, valid_modules)
        job_module = "jobs.%s" % job_module
        job_name = verified_data["name"]
        job_id = "__".join([verified_data["module"],
                            datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")])
        job_kwargs = self._verify_kwargs(verified_data["kwargs"])
        job_trigger = self._verify_trigger(verified_data["trigger"])

        self.request.app["apscheduler"].add_job(
            f'{job_module}:APSJob.job_import', job_trigger,
            id=job_id,
            name=job_name,
            args=[job_module, job_id, self.user.id],
            kwargs=job_kwargs,
            replace_existing=True)
        response_data = {
            "job_id": job_id, "job_name": job_name, "job_kwargs": job_kwargs}
        self.db_log_data["response_data"] = response_data
        flash(self.request, "New job %s has been added" % job_id,
              BSVariant.Success.name, BSVariant.Success.title)
        return response_data


class JobEditController(BaseJobUniversalController):

    def __init__(self, request):
        if request.method == "GET":
            log_type = LogType.JobGetView.id
            required_permissions = [Permission.JobGetView.name]
        else:
            log_type = LogType.JobEditView.id
            required_permissions = [Permission.JobEditView.name]
        super(JobEditController, self).__init__(request, log_type)
        self.required_permissions = required_permissions

    async def _call(self, job_id):
        job = self._verify_job(job_id)
        context = {"id": job.id,
                   "name": job.name,
                   "kwargs": job.kwargs,
                   "module": job.args[0].split(".")[-1],
                   "next_run_time": str(job.next_run_time)}
        if isinstance(job.trigger, CronTrigger):
            for field in job.trigger.fields:
                context[field.name] = str(field)
            self._set_start_end_date(context, job)
            context["trigger"] = "cron"
        elif isinstance(job.trigger, IntervalTrigger):
            context["days"] = job.trigger.interval.days
            context["seconds"] = job.trigger.interval.seconds
            self._set_start_end_date(context, job)
            context["trigger"] = "interval"
        elif isinstance(job.trigger, DateTrigger):
            context["run_date"] = job.trigger.run_date.strftime(
                "%Y-%m-%d %H:%M:%S")
            context["trigger"] = "date"

        if self.request.method == "GET":
            self.save_log = False
            return context

        verified_data = self._verify_request_data(
            ("name", "kwargs", "module", "trigger"))
        available_jobs = list(AvailableJob.get_dicts())
        valid_modules = [m.get("name") for m in available_jobs]
        job_module = verified_data["module"]
        self._verify_module(job_module, valid_modules)
        job_module = "jobs.%s" % job_module
        job_name = verified_data["name"]
        job_kwargs = self._verify_kwargs(verified_data["kwargs"])
        job_trigger = self._verify_trigger(verified_data["trigger"])

        self.request.app["apscheduler"].add_job(
            f'{job_module}:APSJob.job_import', job_trigger,
            id=job.id,
            name=job_name,
            args=[job_module, job_id, self.user.id],
            kwargs=job_kwargs,
            replace_existing=True,
            next_run_time=job_trigger.start_date or job.next_run_time)
        response_data = {
            "job_id": job.id, "job_name": job_name, "job_kwargs": job_kwargs}
        self.db_log_data["response_data"] = response_data
        flash(self.request, "Job %s has been updated" % job.id,
              BSVariant.Success.name, BSVariant.Success.title)
        return response_data

    def _set_start_end_date(self, context, job):
        if job.trigger.start_date:
            context["start_date"] = job.trigger.start_date.strftime(
                "%Y-%m-%d %H:%M:%S")
        else:
            context["start_date"] = None
        if job.trigger.end_date:
            context["end_date"] = job.trigger.end_date.strftime(
                "%Y-%m-%d %H:%M:%S")
        else:
            context["end_date"] = None


class JobDeleteController(BaseJobUniversalController):
    required_permissions = [Permission.JobDeleteView.name]

    def __init__(self, request):
        super(JobDeleteController, self).__init__(
            request, LogType.JobDeleteView.id)

    async def _call(self, job_id):
        job = self._verify_job(job_id)
        job.remove()
        message = "Job %s has been deleted" % job_id
        response_data = {"message": message}
        self.db_log_data["response_data"] = response_data
        flash(self.request, message,
              BSVariant.Danger.name, BSVariant.Warning.title)
        return response_data


class JobPauseController(BaseJobUniversalController):
    required_permissions = [Permission.JobPauseView.name]

    def __init__(self, request):
        super(JobPauseController, self).__init__(
            request, LogType.JobPauseView.id)

    async def _call(self, job_id):
        job = self._verify_job(job_id)
        if job.next_run_time:
            job.pause()
            message = "Job %s has been paused" % job_id
        else:
            job.resume()
            message = "Job %s has been resumed" % job_id
        response_data = {"message": message}
        self.db_log_data["response_data"] = response_data
        flash(self.request, message,
              BSVariant.Success.name, BSVariant.Success.title)
        return response_data


class CommonJobDataController(BaseJobUniversalController):
    related_permissions = [
        Permission.JobAddView.name,
        Permission.JobGetView.name]

    def __init__(self, request):
        super(CommonJobDataController, self).__init__(
            request, LogType.CommonJobDataView.id)

    async def _call(self):
        available_jobs = list(AvailableJob.get_dicts())
        job_triggers = list(JobTrigger.get_dicts())
        for j in available_jobs:
            module_name = j["name"]
            j["job_doc"] = import_module(
                "jobs.%s" % module_name).APSJob.__doc__
        return {"job_triggers": job_triggers, "available_jobs": available_jobs}
