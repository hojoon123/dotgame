# game/views.py
import json
import random
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django.contrib.auth import get_user_model
User = get_user_model()

from .models import GameSession, BallTemplate, EnemyTemplate
from .redis_manager import get_redis


class StartGameSessionView(APIView):
    """
    POST /api/game/start_game_session/
    body: { "user_id": ... }
    => RDB: GameSession + Redis 초기화
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.data.get("user_id")
        user = get_object_or_404(User, id=user_id)

        session = GameSession.objects.create(user=user, is_active=True)
        session_id = session.id

        r = get_redis()
        r.set(f"session:{session_id}:balls", json.dumps([]))
        r.set(f"session:{session_id}:enemies", json.dumps([]))
        r.set(f"session:{session_id}:color_upgrades", json.dumps({
            "red":0,"orange":0,"yellow":0,"green":0,"blue":0,"navy":0,"purple":0
        }))
        r.set(f"session:{session_id}:info", json.dumps({"stage":1,"user_id":user_id}))

        return Response({
            "message": "게임 세션 시작",
            "session_id": session_id
        }, status=status.HTTP_201_CREATED)


class EndGameSessionView(APIView):
    """
    POST /api/game/end_game_session/
    body: { "session_id":... }
    => Redis: session:{session_id}:* 삭제
    => RDB: session.is_active=False
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.data.get("session_id")
        session = get_object_or_404(GameSession, id=session_id)
        session.is_active = False
        session.save()

        r = get_redis()
        r.delete(f"session:{session_id}:balls")
        r.delete(f"session:{session_id}:enemies")
        r.delete(f"session:{session_id}:color_upgrades")
        r.delete(f"session:{session_id}:info")

        return Response({"message": f"세션 {session_id} 종료. Redis data cleared."}, status=200)


class SummonBallView(APIView):
    """
    POST /api/game/summon_ball/
    body: { "session_id":3 }
    => DB BallTemplate(가중치pick) -> Redis balls append
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.data.get("session_id")
        session = get_object_or_404(GameSession, id=session_id)
        if not session.is_active:
            return Response({"detail":"session not active"}, status=400)

        # 1) 템플릿 전부 가져오기
        templates = BallTemplate.objects.all()
        if not templates.exists():
            return Response({"error":"No BallTemplate in DB"}, status=400)

        # 2) weight 합
        total_weight = templates.aggregate(Sum('weight'))['weight__sum'] or 1
        pick = random.randint(0, total_weight-1)

        current = 0
        chosen = None
        for tpl in templates:
            if current + tpl.weight > pick:
                chosen = tpl
                break
            current += tpl.weight
        if not chosen:
            chosen = templates.last()

        r = get_redis()
        balls_key = f"session:{session_id}:balls"
        raw_balls = r.get(balls_key)
        if not raw_balls:
            ball_list = []
        else:
            ball_list = json.loads(raw_balls)

        new_ball = {
            "color": chosen.color,
            "rarity": chosen.rarity,
            "damage": chosen.base_damage,
            "speed": chosen.base_attack_speed,
            "special": chosen.special_option,
            "is_moving": False,  # etc
        }
        ball_list.append(new_ball)
        r.set(balls_key, json.dumps(ball_list))

        return Response({
            "message": f"볼 소환: {chosen.color}/{chosen.rarity}",
            "ball_count": len(ball_list)
        }, status=201)


class SpawnEnemyView(APIView):
    """
    POST /api/game/spawn_enemy/
    body: { "session_id":3, "stage":10 }
    => DB EnemyTemplate(stage_min<=stage<=stage_max) -> Redis enemies
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.data.get("session_id")
        stage = int(request.data.get("stage", 1))

        session = get_object_or_404(GameSession, id=session_id)
        if not session.is_active:
            return Response({"detail":"session not active"}, status=400)

        candidates = EnemyTemplate.objects.filter(stage_min__lte=stage, stage_max__gte=stage)
        if not candidates.exists():
            return Response({"message":"No EnemyTemplate for stage"}, status=200)

        r = get_redis()
        enemies_key = f"session:{session_id}:enemies"
        raw = r.get(enemies_key)
        enemy_list = json.loads(raw) if raw else []

        created_names = []
        for tpl in candidates:
            e = {
                "name": tpl.name,
                "type": tpl.enemy_type,
                "hp": tpl.hp,
                "defense": tpl.defense,
                "shield": tpl.shield,
                "is_dead": False
            }
            enemy_list.append(e)
            created_names.append(tpl.name)

        r.set(enemies_key, json.dumps(enemy_list))

        return Response({
            "message": f"Stage {stage} 적 소환",
            "enemies": created_names
        }, status=201)


class UpgradeColorView(APIView):
    """
    POST /api/game/upgrade_color/
    body: { "session_id":3, "color":"red" }
    => Redis color_upgrades[color] += 1
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.data.get("session_id")
        color = request.data.get("color")

        session = get_object_or_404(GameSession, id=session_id)
        if not session.is_active:
            return Response({"detail":"session not active"}, status=400)

        r = get_redis()
        color_key = f"session:{session_id}:color_upgrades"
        raw_colors = r.get(color_key)
        if not raw_colors:
            return Response({"error":"No color_upgrades in Redis"}, status=400)
        upgrades = json.loads(raw_colors)

        if color not in upgrades:
            return Response({"error":"Invalid color"}, status=400)

        upgrades[color] += 1
        r.set(color_key, json.dumps(upgrades))

        return Response({
            "message": f"{color} 업그레이드 +1 => {upgrades[color]}"
        }, status=200)


class AttackView(APIView):
    """
    POST /api/game/attack/
    body: { "session_id":3 }
    => Redis: balls + enemies + color_upgrades -> 전투
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.data.get("session_id")
        session = get_object_or_404(GameSession, id=session_id)
        if not session.is_active:
            return Response({"detail":"session not active"}, status=400)

        r = get_redis()
        balls_key = f"session:{session_id}:balls"
        enemies_key = f"session:{session_id}:enemies"
        color_key = f"session:{session_id}:color_upgrades"

        raw_balls = r.get(balls_key)
        raw_enemies = r.get(enemies_key)
        raw_colors = r.get(color_key)

        if not raw_balls or not raw_enemies or not raw_colors:
            return Response({"message":"볼/적/업그레이드 정보 없음"}, status=200)

        ball_list = json.loads(raw_balls)
        enemy_list = json.loads(raw_enemies)
        color_upgrades = json.loads(raw_colors)

        attacked = []
        killed = []

        for b in ball_list:
            color = b["color"]
            base_dmg = b["damage"]
            plus = color_upgrades.get(color, 0)
            total_dmg = base_dmg + plus

            for e in enemy_list:
                if e["is_dead"]:
                    continue
                net_damage = max(0, total_dmg - e["defense"])
                # shield
                if net_damage>0 and e["shield"]>0:
                    if e["shield"]>= net_damage:
                        e["shield"]-= net_damage
                        net_damage=0
                    else:
                        net_damage-= e["shield"]
                        e["shield"]=0

                if net_damage>0:
                    e["hp"]-= net_damage
                    if e["hp"]<=0:
                        e["hp"]=0
                        e["is_dead"]=True
                        killed.append(e["name"])
                attacked.append(e["name"])

        # 다시 저장
        r.set(enemies_key, json.dumps(enemy_list))

        return Response({
            "message":"Attack done",
            "attacked_enemies": list(set(attacked)),
            "killed_enemies": list(set(killed))
        }, status=200)
