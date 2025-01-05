# game/urls.py
from django.urls import path
from .views import (
    StartGameSessionView,
    EndGameSessionView,
    SummonBallView,
    SpawnEnemyView,
    UpgradeColorView,
    AttackView,
)

urlpatterns = [
    path('start_game_session/', StartGameSessionView.as_view(), name='start_game_session'),
    path('end_game_session/', EndGameSessionView.as_view(), name='end_game_session'),
    path('summon_ball/', SummonBallView.as_view(), name='summon_ball'),
    path('spawn_enemy/', SpawnEnemyView.as_view(), name='spawn_enemy'),
    path('upgrade_color/', UpgradeColorView.as_view(), name='upgrade_color'),
    path('attack/', AttackView.as_view(), name='attack'),
]
