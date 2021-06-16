import json

import redis

from conf.settings import REDIS_HOST, REDIS_PORT


class RedisHMap:

    def __init__(self, structure_name):
        self._redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1)
        expiration_time = 180
        self._redis.expire(structure_name, expiration_time)
        self.name = structure_name

    def __contains__(self, user):
        return self._redis.hexists(self.name, str(user.uuid))

    def __len__(self):
        return self._redis.hlen(self.name)

    def __iter__(self):
        users = self._redis.hgetall(self.name)
        return map(lambda x: {'uuid': x[0].decode(), **json.loads(x[1].decode())}, users.items())

    def __getitem__(self, item: str):
        return self._redis.hget(self.name, item).decode()

    def add_uuid_value(self, user):
        return self._redis.hset(self.name, key=str(user.uuid), value=str(user))

    def add(self, key: str, value: str):
        return self._redis.hset(self.name, key=key, value=value)

    def pop_user(self, user):
        if isinstance(user, dict):
            user_uuid = user['uuid']
        else:
            user_uuid = str(user.uuid)
        self._redis.hdel(self.name, 1, user_uuid)
        return self

    def pop(self, key: str):
        self._redis.hdel(self.name, 1, key)

    def find(self, value):
        return map(lambda x: x.decode(), self._redis.hscan(self.name, value))
