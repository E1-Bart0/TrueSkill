import asyncio
import random
from typing import Type, Sequence, Optional

from channels.db import database_sync_to_async

from game_auth.models import User
from services.redis_hash import RedisHMap
from services.true_skill import TrueSkills

redis_hash = RedisHMap('TestHMap1')


class MM:
    probability = 0.5

    @staticmethod
    def calculate_mu_sigma_for_users(
            winner: Type[User], looser: Type[User]
    ) -> Sequence[Sequence[float]]:
        """

        :param winner: User
        :param looser: User
        :return: ((winner.mu, winner.sigma), (looser.mu, looser.sigma))
        """
        winner_sigma = winner.sigma
        winner_mu = winner.mu

        looser_sigma = looser.sigma
        looser_mu = looser.mu
        return TrueSkills.calculate_winner(winner_mu, winner_sigma, looser_mu, looser_sigma), \
               TrueSkills.calculate_looser(winner_mu, winner_sigma, looser_mu, looser_sigma)

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
    async def find_match_for_user(cls, consumer, user: Type[User], search_times: Optional[int] = 0) -> None:
        """
        Find User and Enemy else just wait and increase user probability to find match

        :param user: User
        :param search_times: int how match this function called
        :return: (User, User)
        """
        if not search_times and not redis_hash.add_uuid_value(user):
            return

        while True:
            if user not in redis_hash:
                return
            if len(redis_hash) > 1:
                user_uuid = str(user.uuid)
                for enemy in redis_hash:
                    prob = TrueSkills.get_match_probability(user.mu, user.sigma, enemy['mu'], enemy['sigma'])
                    if prob > cls.probability - (0.01 * search_times) and enemy['uuid'] != user_uuid:
                        return await cls.callback_to_consumer(consumer, user, enemy)
                search_times += 1
            await asyncio.sleep(1)

    @classmethod
    async def callback_to_consumer(cls, consumer, user, enemy):
        enemy = await cls.find_user_model(enemy['uuid'])
        redis_hash.pop_user(enemy)
        redis_hash.pop_user(user)
        await consumer.handlers['matchmaking'].start_match(consumer, user, enemy)

    @staticmethod
    @database_sync_to_async
    def find_user_model(user_uuid: str):
        return User.objects.get(uuid=user_uuid)
