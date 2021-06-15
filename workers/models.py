import json


class Msg:
    type = None
    message = {}

    def __init__(self, type: str = None, message=None):  # noqa: A002
        self.type = type or self.type
        self.message = message or self.message

    @property
    def json(self) -> str:
        return json.dumps({"type": self.type, "message": self.message})

    @property
    def raw(self) -> dict:
        return {"type": self.type, "message": self.message}
