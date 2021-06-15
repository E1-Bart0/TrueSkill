from django.urls import path


from .consumer import Consumer

websocket_urlpatterns = [
    path("ws/basic", Consumer.as_asgi()),
]
