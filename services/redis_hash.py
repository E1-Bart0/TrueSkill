import json
from typing import Type, Union, Iterable, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from game_auth.models import User

import redis

from conf.settings import REDIS_HOST, REDIS_PORT


class RedisHMap:
    def __init__(self, structure_name):
        self._redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1)
        expiration_time = 180
        self._redis.expire(structure_name, expiration_time)
        self.name = structure_name

    def __contains__(self, user: Type[User]) -> bool:
        return self._redis.hexists(self.name, str(user.uuid))

    def __len__(self) -> int:
        return self._redis.hlen(self.name)

    def __iter__(self) -> Iterable[dict]:
        users = self._redis.hgetall(self.name)
        return map(lambda x: {x[0].decode(): x[1].decode()}, users.items())

    def __getitem__(self, item: str):
        return self._redis.hget(self.name, item).decode()

    def add(self, key: str, value: str) -> bool:
        return self._redis.hset(self.name, key=key, value=value)

    def pop(self, *keys: Sequence[str]):
        "Delete ``keys`` from hash ``name``"
        self._redis.hdel(self.name, 1, *keys)


class RedisHMapMatchmakingStorage(RedisHMap):
    def add_if_not_exists(self, user: Type[User]) -> bool:
        """Add user to storage. Returns 1 if User added and 0 if it's not"""
        return self._redis.hset(self.name, key=str(user.uuid), value=str(user))

    def pop_users(self, *users: Sequence[Union[User, dict]]):
        users_uuids = [str(user.uuid) if isinstance(user, User) else user["uuid"] for user in users]
        self._redis.hdel(self.name, 1, *users_uuids)

    def __iter__(self) -> Iterable[dict]:
        """
        :return: Iter({'uuid': str, 'mu': float, 'sigma': float})
        """
        users = self._redis.hgetall(self.name)
        return map(
            lambda x: {"uuid": x[0].decode(), **json.loads(x[1].decode())},
            users.items(),
        )
