import asyncio
import uuid
from typing import Type

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer

from game_auth.models import User, Room
from services.redis_hash import RedisHMap
from services.user_matchmaking import MM
from workers.models import Msg

redis_storage_user_channel_name = RedisHMap("UserChannelName")


def matchmaking(consumer: AsyncWebsocketConsumer.__class__):
    async def match(self: AsyncWebsocketConsumer.__class__, content: dict) -> str:
        action = content["message"]["type"]

        if action == "find_match":
            await find_enemy_for(self)
        if action == "match_finished":
            await finish_match(self)

        msg = Msg(type="OK", message={"success": "True"})
        return msg.json

    async def find_enemy_for(self: AsyncWebsocketConsumer.__class__):
        user = self.scope["user"]
        loop = asyncio.get_event_loop()
        loop.create_task(MM.find_match_for_user(self, user))

    async def start_match(self: AsyncWebsocketConsumer.__class__, user: Type[User], enemy: Type[User]):
        user_channel_name = self.channel_name
        enemy_channel_name = redis_storage_user_channel_name[str(enemy.uuid)]
        await add_users_to_channel_group((user, user_channel_name), (enemy, enemy_channel_name))

    async def add_users_to_channel_group(*channel_names):
        room = await create_new_room()
        channel_layer = get_channel_layer()
        for user, channel_name in channel_names:
            await add_user_to_room(room, user)
            await channel_layer.group_add(str(room), channel_name)

        msg = Msg(
            type="found_match",
            message={f"user{index}": str(user.uuid) for index, (user, _) in enumerate(channel_names)},
        )
        main_msg = Msg(type="matchmaking_room_send", message=msg.json)

        # await database_sync_to_async(room.save)()
        await channel_layer.group_send(str(room), main_msg.raw)

    async def discard_user_from_channel_group(self: AsyncWebsocketConsumer.__class__, room_name):
        user = self.scope["user"]
        await delete_room(user.my_room.all())
        await self.channel_layer.group_discard(room_name, self.channel_name)

    async def finish_match(self: AsyncWebsocketConsumer):
        user = self.scope["user"]

        room, users = await get_room_and_users(user)
        users = await database_sync_to_async(MM.match_1_vs_1_random_winner)(users)
        msg = Msg(type="match_finished", message={str(u.uuid): str(u) for u in users})
        main_msg = Msg(type="matchmaking_room_send", message=msg.json)

        await self.channel_layer.group_send(str(room), main_msg.raw)
        await discard_user_from_channel_group(self, str(room))

    @database_sync_to_async
    def find_user(user_uuid):
        return User.objects.get(uuid=user_uuid)

    @database_sync_to_async
    def get_all_users_from_db():
        return User.objects.all()

    @database_sync_to_async
    def create_new_room():
        return Room.objects.create()

    @database_sync_to_async
    def add_user_to_room(room, user):
        return room.users.add(user)

    @database_sync_to_async
    def delete_room(room):
        return room.delete()

    @database_sync_to_async
    def get_room_and_users(user):
        room = user.my_room.first()
        users = room.users.all()
        return room, users

    async def matchmaking_room_send(self, event):
        await self.send(text_data=event["message"])

    consumer.handlers["matchmaking"] = match
    consumer.handlers["matchmaking"].start_match = start_match
    consumer.matchmaking_room_send = matchmaking_room_send
    return consumer


def unknown_module(
    consumer: AsyncWebsocketConsumer.__class__,
) -> AsyncWebsocketConsumer.__class__:
    """module for handle unknown message"""

    async def unknown(*_args, **_kwargs) -> str:
        msg = Msg(type="error", message={"error": "unknown type message"})
        return msg.json

    consumer.handlers["unknown"] = unknown
    return consumer


def introduced_module(
    consumer: AsyncWebsocketConsumer.__class__,
) -> AsyncWebsocketConsumer.__class__:
    """module for handle introduced"""

    async def introduced(context, *_args) -> str:
        user = context.scope["user"]
        msg = Msg(type="introduced", message={"user": user.username})
        return msg.json

    consumer.handlers["introduced"] = introduced

    # closure parent's method
    old_connect = consumer.connect

    async def connect(self: AsyncWebsocketConsumer.__class__):
        """this override connect method"""
        user = await add_user_to_db()
        self.scope["user"] = user
        redis_storage_user_channel_name.add(str(user.uuid), self.channel_name)

        # call parent method
        await old_connect(self)

    consumer.connect = connect

    # closure parent's method
    old_disconnect = consumer.disconnect

    async def disconnect(self, close_code):
        """this override disconnect method"""
        user = self.scope["user"]
        redis_storage_user_channel_name.pop(str(user.uuid))

        # call parent method
        await old_disconnect(self, close_code)

    @database_sync_to_async
    def add_user_to_db():
        username = uuid.uuid4()
        return User.objects.create(username=username, uuid=username)

    consumer.disconnect = disconnect
    return consumer
