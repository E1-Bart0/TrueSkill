import asyncio
import random
from typing import Sequence, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game_auth.models import User

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from trueskill import quality, rate, Rating

from services.redis_hash import RedisHMapMatchmakingStorage

redis_hash = RedisHMapMatchmakingStorage("TestHMap1")


class MM:
    probability = 0.5

    @classmethod
    def calculate_mu_sigma_for_users(cls, *users: User) -> Sequence[Sequence[Rating]]:
        """
        :param users: from winner to looser
        :return: ((winner.mu, winner.sigma), (looser.mu, looser.sigma))
        """
        rating_group = [(Rating(u.mu, u.sigma),) for u in users]
        return rate(rating_group)

    @staticmethod
    def get_match_probability(*mu_and_sigmas: Sequence[float]):
        rating_group = [(Rating(mu, sigma),) for mu, sigma in mu_and_sigmas]
        return quality(rating_group)

    @staticmethod
    def update_mu_sigma_for_users(users: Sequence[User], data: Sequence[Sequence[Rating]]) -> None:
        """
        :param users: from winner to looser
        :param data: ((winner.mu, winner.sigma), (looser.mu, looser.sigma))
        :return: None
        """
        for user, tuple_with_rating in zip(users, data):
            user.update(mu=tuple_with_rating[0].mu, sigma=tuple_with_rating[1].sigma)

    @staticmethod
    def calculate_rating(mu, sigma):
        return 10 * (10 * mu - 3 * sigma)

    @staticmethod
    def match_1_vs_1_random_winner(users: Sequence[User]) -> None:
        """Calculate new mu and sigma for winner and looser and update users"""
        users = list(users)
        random.shuffle(users)
        new_mu_sigmas_for_users = MM.calculate_mu_sigma_for_users(*users)
        MM.update_mu_sigma_for_users(users, new_mu_sigmas_for_users)
        return users

    @classmethod
    async def find_match_for_user(  # noqa: CCR001
        cls, consumer: AsyncWebsocketConsumer.__class__, user: User, search_times: Optional[int] = 0
    ) -> None:
        """
        Find User and Enemy else just wait and increase user probability to find match

        :param consumer: AsyncWebsocketConsumer
        :param user: User
        :param search_times: int how match this function called
        :return: (User, User)
        """
        was_added = redis_hash.add_if_not_exists(user)
        if not was_added:
            return
        while True:
            if user not in redis_hash:
                return
            if len(redis_hash) > 1:
                is_enemy_found = await cls._find_enemy_in_redis(user, search_times, consumer)
                if is_enemy_found:
                    return
                search_times += 1
            await asyncio.sleep(1)

    @classmethod
    async def _find_enemy_in_redis(
        cls, user: User, search_times: int, consumer: AsyncWebsocketConsumer.__class__
    ) -> bool:
        """For each enemy in redis we calculating probability his match with User"""
        for enemy in redis_hash:
            prob = cls.get_match_probability((user.mu, user.sigma), (enemy["mu"], enemy["sigma"]))
            if prob > cls.probability - (0.01 * search_times) and enemy["uuid"] != str(user.uuid):
                await cls.callback_to_consumer(consumer, user, enemy)
                return True
        return False

    @classmethod
    async def callback_to_consumer(cls, consumer: AsyncWebsocketConsumer.__class__, user: User, enemy: dict):
        enemy = await cls.find_user_model(enemy["uuid"])
        redis_hash.pop_users(user, enemy)
        await consumer.handlers["matchmaking"].start_match(consumer, user, enemy)

    @staticmethod
    @database_sync_to_async
    def find_user_model(user_uuid: str):
        return User.objects.get(uuid=user_uuid)
