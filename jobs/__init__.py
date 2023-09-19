import os
import traceback
from datetime import datetime
from importlib import import_module

import config
from models import JobLog, async_db_manager
from utils import get_log


log = get_log(os.path.join(config.DIRS["LOG_TO"], config.LOGGER["file"]),
              config.LOGGER["level"], config.LOGGER["formatter"], "apscron")


class JobException(Exception):
    pass


class BaseJobController(object):

    def __init__(self):
        self.log_model = JobLog
        self.job_result = {}
        self.log = log
        self.db = async_db_manager

    async def job_import(*args, **kwargs):
        try:
            job_module = import_module(args[0])
            job_class = getattr(job_module, "APSJob")
            await job_class().call(*args, **kwargs)
        except Exception as e:
            log.exception(e)

    async def call(self, *args, **kwargs):
        job_id = args[1]
        user_id = args[2]
        job_data = kwargs
        try:
            self.log.info("Job %s started with params: %s" %
                          (job_id, job_data))
            self.db_log_data = {
                "user": user_id,
                "job_id": job_id,
                "job_data": job_data,
                "job_result": self.job_result,
                "started_at": datetime.now()
            }
            await self._call(**kwargs)
            self.log.info("Job %s finished with result: %s" %
                          (job_id, self.job_result))
        except JobException as e:
            self.log.warning(traceback.format_exc())
            self.db_log_data["error"] = e
        except Exception as e:
            self.log.exception(e)
            self.db_log_data["error"] = e
        finally:
            if not self.db_log_data.get("finished_at"):
                self.db_log_data["finished_at"] = datetime.now()
            await self.db.create(self.log_model, **self.db_log_data)

    def _call(self, *args, **kwargs):
        raise NotImplementedError("_call")

    def _verify_job_kwargs(self, kwargs, required_keys):
        for key in required_keys:
            if not kwargs.get(key):
                raise JobException(
                    f"Invalid job settings, required key {key} is invalid")
