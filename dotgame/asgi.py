# dotgame/asgi.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dotgame.settings')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import game.routing

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": URLRouter(
        game.routing.websocket_urlpatterns
    ),
})
