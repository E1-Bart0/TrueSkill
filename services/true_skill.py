from functools import lru_cache
from math import sqrt, pi, exp
from typing import Sequence

from scipy import stats


class TrueSkills:
    mu_0 = 25
    k = 3
    sigma_0 = 25 / k
    Beta = sigma_0 / 2
    draw_margin = 0

    @classmethod
    @lru_cache
    def c(cls, sigma_winner: float, sigma_looser: float) -> float:
        c_square = 2 * pow(cls.Beta, 2) + pow(sigma_winner, 2) + pow(sigma_looser, 2)
        return sqrt(c_square)

    @classmethod
    @lru_cache
    def t_multiply_by_c(cls, mu_winner: float, mu_looser: float) -> float:
        return mu_winner - mu_looser

    @classmethod
    @lru_cache
    def normal_distribution(cls, x: float, mu: float = 25, sigma: float = 8.33) -> float:
        power = -pow((x - mu), 2) / (2 * pow(sigma, 2))
        return exp(power) / (sqrt(2 * pi) * sigma)

    @classmethod
    @lru_cache
    def cumulative_distribution(cls, x: float, mu: float = 25, sigma: float = 8.333) -> float:
        return stats.norm.cdf(x, loc=mu, scale=sigma)

    @classmethod
    def v(cls, x: float, y: float) -> float:
        return cls.normal_distribution(x - y) / cls.cumulative_distribution(x - y)

    @classmethod
    def w(cls, x: float, y: float) -> float:
        v = cls.v(x, y)
        return v * (v + x - y)

    @classmethod
    def calculate_sigma_winner(
        cls,
        mu_winner: float,
        sigma_winner: float,
        mu_looser: float,
        sigma_looser: float,
    ) -> float:
        c = cls.c(sigma_winner, sigma_looser)
        t = cls.t_multiply_by_c(mu_winner, mu_looser) / c
        w = cls.w(t, cls.draw_margin / c)
        sigma_square = pow(sigma_winner, 2) * (1 - pow(sigma_winner, 2) / pow(c, 2) * w)
        return sqrt(sigma_square)

    @classmethod
    def calculate_sigma_looser(
        cls,
        mu_winner: float,
        sigma_winner: float,
        mu_looser: float,
        sigma_looser: float,
    ) -> float:
        c = cls.c(sigma_winner, sigma_looser)
        t = cls.t_multiply_by_c(mu_winner, mu_looser) / c
        w = cls.w(t, cls.draw_margin / c)
        sigma_square = pow(sigma_looser, 2) * (1 - pow(sigma_looser, 2) / pow(c, 2) * w)
        return sqrt(sigma_square)

    @classmethod
    def calculate_mu_winner(
        cls,
        mu_winner: float,
        sigma_winner: float,
        mu_looser: float,
        sigma_looser: float,
    ) -> float:
        c = cls.c(sigma_winner, sigma_looser)
        t = cls.t_multiply_by_c(mu_winner, mu_looser) / c
        v = cls.v(t, cls.draw_margin / c)
        return mu_winner + pow(sigma_winner, 2) / c * v

    @classmethod
    def calculate_mu_looser(
        cls,
        mu_winner: float,
        sigma_winner: float,
        mu_looser: float,
        sigma_looser: float,
    ) -> float:
        c = cls.c(sigma_winner, sigma_looser)
        t = cls.t_multiply_by_c(mu_winner, mu_looser) / c
        v = cls.v(t, cls.draw_margin / c)
        return mu_looser - pow(sigma_looser, 2) / c * v

    @classmethod
    def calculate_winner(
        cls,
        mu_winner: float,
        sigma_winner: float,
        mu_looser: float,
        sigma_looser: float,
    ) -> Sequence[float]:
        mu = cls.calculate_mu_winner(mu_winner, sigma_winner, mu_looser, sigma_looser)
        sigma = cls.calculate_sigma_winner(mu_winner, sigma_winner, mu_looser, sigma_looser)
        return mu, sigma

    @classmethod
    def calculate_looser(
        cls,
        mu_winner: float,
        sigma_winner: float,
        mu_looser: float,
        sigma_looser: float,
    ) -> Sequence[float]:
        mu = cls.calculate_mu_looser(mu_winner, sigma_winner, mu_looser, sigma_looser)
        sigma = cls.calculate_sigma_looser(mu_winner, sigma_winner, mu_looser, sigma_looser)
        return mu, sigma

    @classmethod
    def calculate_new_mu_sigma_for_winner_looser(
        cls,
        mu_winner: float,
        sigma_winner: float,
        mu_looser: float,
        sigma_looser: float,
    ) -> Sequence[Sequence[float]]:
        winner = TrueSkills.calculate_winner(mu_winner, sigma_winner, mu_looser, sigma_looser)
        looser = TrueSkills.calculate_looser(mu_winner, sigma_winner, mu_looser, sigma_looser)
        return winner, looser

    @classmethod
    def calculate_rating(cls, mu: float, sigma: float) -> int:
        return int(mu * 100 - cls.k * sigma * 10)

    @classmethod
    def get_match_probability(cls, mu_user1: float, sigma_user1: float, mu_user2: float, sigma_user2: float) -> float:
        c = cls.c(sigma_user1, sigma_user2)
        d = 2 * pow(cls.Beta, 2) / pow(c, 2)
        power = -pow((mu_user1 - mu_user2), 2) / (2 * pow(c, 2))
        return exp(power) * sqrt(d)

    @classmethod
    def chance_to_win(cls, rating_user1, rating_user2):
        return 1 / (1 + 10 ** ((rating_user1 - rating_user2) / 400))
