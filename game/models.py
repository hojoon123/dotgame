from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class GameSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"GameSession {self.id} (User={self.user}, active={self.is_active})"

class BallTemplate(models.Model):
    color = models.CharField(max_length=20)
    rarity = models.CharField(max_length=20)
    weight = models.IntegerField(default=1)  # 등장 확률 가중치
    base_damage = models.IntegerField(default=1)
    base_attack_speed = models.FloatField(default=1.0)
    special_option = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"[{self.color}/{self.rarity}] dmg={self.base_damage}, w={self.weight}"

class EnemyTemplate(models.Model):
    ENEMY_TYPE_CHOICES = [
        ('normal', '일반'),
        ('hunt', '사냥몹'),
        ('boss', '보스'),
    ]
    name = models.CharField(max_length=50)
    enemy_type = models.CharField(max_length=10, choices=ENEMY_TYPE_CHOICES)
    hp = models.IntegerField(default=10)
    defense = models.IntegerField(default=0)
    shield = models.IntegerField(default=0)
    stage_min = models.IntegerField(default=1)
    stage_max = models.IntegerField(default=999)

    def __str__(self):
        return f"{self.name}({self.enemy_type}, HP={self.hp}, def={self.defense}, sh={self.shield})"
