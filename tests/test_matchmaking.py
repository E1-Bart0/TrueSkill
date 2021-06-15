import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

from conf.asgi import application
from game_auth.models import User


@database_sync_to_async
def get_all_users_from_db():
    return list(User.objects.all())


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_connection():
    communicator = WebsocketCommunicator(application, "/ws/basic")
    assert not len(await get_all_users_from_db())
    connected, _ = await communicator.connect()
    assert connected
    assert len(await get_all_users_from_db())
