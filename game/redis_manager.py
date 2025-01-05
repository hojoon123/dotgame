# game/redis_manager.py
import redis
from django.conf import settings

REDIS_HOST = getattr(settings, 'REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(getattr(settings, 'REDIS_PORT', 6379))

# 단일 Redis connection
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

def get_redis():
    return r
