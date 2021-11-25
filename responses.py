from collections import OrderedDict


class ControllerResponse(OrderedDict):

    def __init__(self, ok, data=None, messages=[]):
        super(ControllerResponse, self).__init__(
            ok=ok, data=data, messages=messages)
