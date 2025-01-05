from django.urls import re_path
from .consumers import GameConsumer

websocket_urlpatterns = [
    # 끝에 / 붙였을 때
    re_path(r"^ws/game/(?P<session_id>\d+)/?$", GameConsumer.as_asgi()),
]
