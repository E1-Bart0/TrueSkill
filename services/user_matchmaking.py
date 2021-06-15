import asyncio
import random
from typing import Type, Sequence, Optional

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from game_auth.models import User
from services.redis_hash import RedisHMapMatchmakingStorage
from services.true_skill import TrueSkills

redis_hash = RedisHMapMatchmakingStorage("TestHMap1")


class MM:
    probability = 0.5

    @staticmethod
    def calculate_mu_sigma_for_users(winner: Type[User], looser: Type[User]) -> Sequence[Sequence[float]]:
        """
        :param winner: User
        :param looser: User
        :return: ((winner.mu, winner.sigma), (looser.mu, looser.sigma))
        """
        winner_sigma = winner.sigma
        winner_mu = winner.mu

        looser_sigma = looser.sigma
        looser_mu = looser.mu
        return TrueSkills.calculate_winner(
            winner_mu, winner_sigma, looser_mu, looser_sigma
        ), TrueSkills.calculate_looser(winner_mu, winner_sigma, looser_mu, looser_sigma)

    @staticmethod
    def update_mu_sigma_for_users(winner: Type[User], looser: Type[User], data: Sequence[Sequence[float]]) -> None:
        """
        :param winner: User
        :param looser: User
        :param data: ((winner.mu, winner.sigma), (looser.mu, looser.sigma))
        :return: None
        """
        for user, (mu, sigma) in zip((winner, looser), data):
            user.update(mu=mu, sigma=sigma)

    @staticmethod
    def match_1_vs_1_random_winner(users: Sequence[User]) -> None:
        """Calculate new mu and sigma for winner and looser and update users"""
        users = list(users)
        random.shuffle(users)
        new_mu_sigmas_for_users = MM.calculate_mu_sigma_for_users(*users)
        MM.update_mu_sigma_for_users(*users, new_mu_sigmas_for_users)
        return users

    @classmethod
    async def find_match_for_user(  # noqa: CCR001
        cls, consumer: AsyncWebsocketConsumer.__class__, user: Type[User], search_times: Optional[int] = 0
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
    async def _find_enemy_in_redis(cls, user, search_times, consumer):
        """For each enemy in redis we calculating probability his match with User"""
        for enemy in redis_hash:
            prob = TrueSkills.get_match_probability(user.mu, user.sigma, enemy["mu"], enemy["sigma"])
            if prob > cls.probability - (0.01 * search_times) and enemy["uuid"] != str(user.uuid):
                await cls.callback_to_consumer(consumer, user, enemy)
                return True

    @classmethod
    async def callback_to_consumer(cls, consumer, user, enemy):
        enemy = await cls.find_user_model(enemy["uuid"])
        redis_hash.pop_users(user, enemy)
        await consumer.handlers["matchmaking"].start_match(consumer, user, enemy)

    @staticmethod
    @database_sync_to_async
    def find_user_model(user_uuid: str):
        return User.objects.get(uuid=user_uuid)
