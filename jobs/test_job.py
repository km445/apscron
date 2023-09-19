from datetime import datetime

from jobs import BaseJobController


class APSJob(BaseJobController):
    """
    <div>
    docstring for test_job 1
    </div>
    """

    async def _call(self, *args, **kwargs):
        # self._verify_job_kwargs(kwargs, ["foo", "foo2"])
        print("test_job _call")
        print(datetime.now())
        print(self)
        print(args)
        print(kwargs)
        self.job_result["finished_at"] = str(datetime.now())
        # raise JobException("job exception")
        # return "result"
