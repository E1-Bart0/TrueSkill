import json
import uuid as uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from services.user_matchmaking import MM


class User(AbstractUser):
    uuid = models.UUIDField(primary_key=True, db_index=True, default=uuid.uuid4)
    mu = models.FloatField(default=25)
    sigma = models.FloatField(default=8.333)

    @property
    def rating(self):
        return MM.calculate_rating(self.mu, self.sigma)

    @property
    def as_string(self):
        user_dict = {"uuid": str(self.uuid), "mu": self.mu, "sigma": self.sigma}
        return json.dumps(user_dict)

    def update(self, mu: float, sigma: float) -> None:
        self.mu = mu
        self.sigma = sigma
        self.save()

    def __str__(self):
        return json.dumps({"mu": self.mu, "sigma": self.sigma})


class Room(models.Model):
    users = models.ManyToManyField("User", blank=True, related_name="my_room")

    def __str__(self):
        return str(self.id)
