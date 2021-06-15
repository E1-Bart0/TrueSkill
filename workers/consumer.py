import json
from json import JSONDecodeError

from channels.generic.websocket import AsyncWebsocketConsumer

from workers.handler import matchmaking, unknown_module, introduced_module
from workers.models import Msg


@matchmaking
@unknown_module
@introduced_module
class Consumer(AsyncWebsocketConsumer):
    handlers = {}

    async def receive(self, text_data=None, bytes_data=None):
        try:
            content = json.loads(text_data)
        except JSONDecodeError as err:
            error = Msg(type="error", message={"raw_data": text_data, "error": err.args}).json
            await self.send(text_data=error)
        else:
            await self.message_handler(content)

    async def message_handler(self, content):
        handler = self.handlers.get(content.get("type"), self.handlers["unknown"])
        response = await handler(self, content)
        await self.send(text_data=response)
