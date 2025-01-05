"""
game/serializers.py
단순히 ModelSerializer로 Ball, Enemy, GameSession 직렬화
"""
from rest_framework import serializers
from .models import GameSession, Ball, Enemy

class GameSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameSession
        fields = '__all__'

class BallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ball
        fields = '__all__'

class EnemySerializer(serializers.ModelSerializer):
    class Meta:
        model = Enemy
        fields = '__all__'
