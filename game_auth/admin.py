from django.contrib import admin

# Register your models here.
from game_auth.models import User, Room


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    fields = ("uuid", "mu", "sigma", "username")
    list_display = (
        "uuid",
        "mu",
        "sigma",
        "rating",
    )


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    pass
