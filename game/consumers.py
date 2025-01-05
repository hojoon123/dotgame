# game/consumers.py
import json
import asyncio
import random
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from .wave_config import get_stage_info
from .redis_manager import get_redis

INTERNAL_TICK = 0.1
BROADCAST_INTERVAL = 0.5

"""
큰 사각형을 (20,20)-(20,380)-(380,380)-(380,20)-(20,20) 로 설정
작은 사각형을 (100,100)-(300,100)-(300,300)-(100,300)-(100,100)
적은 PATH_POINTS를 따라 반시계 이동
"""
PATH_POINTS = [
    (20,20),(20,380),(100,380),(100,300),(300,300),(300,100),(100,100),(100,20)
    # 다시 (20,20)로
]

class GameConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.group_name = f"session_{self.session_id}"

        await self.accept()
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        r = get_redis()
        init_state = {
            "stage": 1,
            "time_in_stage": 0.0,
            "enemies": [],
            "balls": [],
            "color_upgrades": {
                "red":0,"orange":0,"yellow":0,"green":0,"blue":0,"navy":0,"purple":0
            },
            "attack_effects": [],
            "last_broadcast": 0.0,
            "is_active": True
        }
        r.set(self.state_key, json.dumps(init_state))

        self.loop_task = asyncio.create_task(self.main_loop())
        await self.send_json({"message":"세션 연결 성공"})

    @property
    def state_key(self):
        return f"session:{self.session_id}:state"

    async def disconnect(self, code):
        if self.loop_task:
            self.loop_task.cancel()
        r = get_redis()
        raw = r.get(self.state_key)
        if raw:
            st = json.loads(raw)
            st["is_active"] = False
            r.set(self.state_key, json.dumps(st))
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        action = content.get("action")
        if action == "end_game":
            await self.end_game()
        elif action == "summon_ball":
            await self.summon_ball()
            await self.broadcast_state(force=True)
        elif action == "upgrade_color":
            c = content.get("color","red")
            await self.upgrade_color(c)
            await self.broadcast_state(force=True)
        elif action == "move_ball":
            idx = content.get("ball_idx",0)
            tx = float(content.get("tx",200))
            ty = float(content.get("ty",200))
            print(f"[DEBUG] move_ball idx={idx}, target=({tx},{ty})")  # 디버그
            await self.move_ball(idx, tx, ty)
        else:
            await self.send_json({"error":"unknown action"})

    async def main_loop(self):
        try:
            while True:
                await asyncio.sleep(INTERNAL_TICK)
                await self.tick_internal()
        except asyncio.CancelledError:
            pass

    async def tick_internal(self):
        r = get_redis()
        raw = r.get(self.state_key)
        if not raw: return
        st = json.loads(raw)
        if not st["is_active"]: return

        st["time_in_stage"] += INTERNAL_TICK
        t = st["time_in_stage"]
        stage = st["stage"]
        wave = get_stage_info(stage)
        wave_duration = wave["duration"]
        spawn_duration = wave["spawn_duration"]
        is_boss = wave["boss"]

        # 1초마다 적 스폰
        sec_int = int(t)
        sec_prev = int(t - INTERNAL_TICK)
        if sec_int != sec_prev and t <= spawn_duration:
            await self.spawn_enemy(st, is_boss=(is_boss and sec_int==0))

        self.move_enemies(st)
        self.move_balls(st)
        self.balls_attack(st)
        self.update_attack_effects(st)

        if t >= wave_duration:
            st["stage"] += 1
            st["time_in_stage"] = 0
            # 적 죽이는 코드 제거 => 적이 계속 유지
            print(f"[DEBUG] Stage => {st['stage']} (no mass kill)")  # 디버그

        r.set(self.state_key, json.dumps(st))

        # broadcast
        last_b = st["last_broadcast"]
        if (t - last_b) >= BROADCAST_INTERVAL:
            await self.broadcast_state()
            st["last_broadcast"] = t
            r.set(self.state_key, json.dumps(st))

    async def spawn_enemy(self, st, is_boss=False):
        """
        적을 (20,20)에서 시작
        """
        if is_boss:
            e = {
                "name":"Boss",
                "hp":200, "defense":10, "shield":10,
                "path_idx":0,"speed":8.0, "is_dead":False,
                "x":PATH_POINTS[0][0],"y":PATH_POINTS[0][1],
            }
        else:
            e = {
                "name": random.choice(["Slime","Wolf","Goblin"]),
                "hp":10,"defense":1,"shield":0,
                "path_idx":0,"speed": random.uniform(5,8),
                "is_dead":False,
                "x":PATH_POINTS[0][0],"y":PATH_POINTS[0][1],
            }
        st["enemies"].append(e)

    def move_enemies(self, st):
        dt = INTERNAL_TICK
        for e in st["enemies"]:
            if e["is_dead"]:
                continue
            idx = e.get("path_idx",0)
            path_len = len(PATH_POINTS)
            if idx >= path_len-1:
                nxt = 0
            else:
                nxt = idx+1
            cx, cy = PATH_POINTS[idx]
            tx, ty = PATH_POINTS[nxt]
            x, y = e["x"], e["y"]
            dx = tx - x
            dy = ty - y
            dist = (dx*dx + dy*dy)**0.5
            step = e["speed"] * dt
            if step >= dist:
                e["x"] = tx
                e["y"] = ty
                e["path_idx"] = nxt
            else:
                ratio = step/dist
                e["x"] += dx* ratio
                e["y"] += dy* ratio

    def move_balls(self, st):
        dt = INTERNAL_TICK
        for b in st["balls"]:
            tx = b.get("target_x", b["x"])
            ty = b.get("target_y", b["y"])
            spd= 15.0  # 볼 이동속도 조금 증가
            dx= tx - b["x"]
            dy= ty - b["y"]
            dist= (dx*dx + dy*dy)**0.5
            if dist>0:
                step= spd* dt
                if step>= dist:
                    b["x"]= tx
                    b["y"]= ty
                else:
                    rr= step/dist
                    b["x"]+= dx* rr
                    b["y"]+= dy* rr

    def balls_attack(self, st):
        dt= INTERNAL_TICK
        eff= st["attack_effects"]
        color_up= st["color_upgrades"]

        for b in st["balls"]:
            cd= b.get("cooldown",0)
            if cd>0:
                cd-= dt
                if cd<0: cd=0
                b["cooldown"]= cd
                if cd>0:
                    continue
            # 공격력 + 업그레이드
            dmg= b.get("damage",5) + color_up.get(b["color"],0)

            # 사거리=80 (좀 늘림)
            bestDist=80
            target=None
            bx, by= b["x"], b["y"]
            for e in st["enemies"]:
                if e["is_dead"]: continue
                dx= e["x"]- bx; dy= e["y"]- by
                dist= (dx*dx+ dy*dy)**0.5
                if dist< bestDist:
                    bestDist= dist
                    target= e
            if target:
                net= max(0, dmg- target.get("defense",0))
                sh= target.get("shield",0)
                if sh>0 and net>0:
                    if sh>= net:
                        target["shield"]-= net
                        net=0
                    else:
                        net-= sh
                        target["shield"]=0
                if net>0:
                    target["hp"]-= net
                    if target["hp"]<=0:
                        target["hp"]=0
                        target["is_dead"]=True

                eff.append({
                    "x1": bx,"y1":by,
                    "x2": target["x"],"y2":target["y"],
                    "timer": 0.3
                })
                b["cooldown"]=1.0

    def update_attack_effects(self, st):
        dt= INTERNAL_TICK
        old= st["attack_effects"]
        newEff=[]
        for e in old:
            e["timer"]-= dt
            if e["timer"]>0:
                newEff.append(e)
        st["attack_effects"]= newEff

    async def move_ball(self, idx, tx, ty):
        print(f"[DEBUG] move_ball => idx={idx}, target=({tx},{ty})")
        r= get_redis()
        raw= r.get(self.state_key)
        if not raw:return
        st= json.loads(raw)
        if idx<0 or idx>= len(st["balls"]):
            await self.send_json({"error": "invalid ball idx"})
            return
        b= st["balls"][idx]
        b["target_x"]= tx
        b["target_y"]= ty
        r.set(self.state_key, json.dumps(st))
        await self.send_json({
            "message":f"볼 {idx} 이동 => ({tx:.1f},{ty:.1f})"
        })

    async def summon_ball(self):
        r= get_redis()
        raw= r.get(self.state_key)
        if not raw:return
        st= json.loads(raw)
        c= random.choice(["red","blue","purple","orange","yellow","green","navy"])
        rty= random.choice(["common","rare","epic"])
        b={
            "x":200,"y":200,
            "target_x":200,"target_y":200,
            "color":c,
            "rarity":rty,
            "damage":5,
            "cooldown":0
        }
        st["balls"].append(b)
        r.set(self.state_key, json.dumps(st))
        await self.send_json({"message":f"볼 소환: {c}/{rty}"})

    async def upgrade_color(self, c):
        r= get_redis()
        raw= r.get(self.state_key)
        if not raw:return
        st= json.loads(raw)
        up= st["color_upgrades"]
        if c not in up: up[c]=0
        up[c]+=1
        r.set(self.state_key, json.dumps(st))
        await self.send_json({"message":f"{c} 업그레이드 => {up[c]}"})

    async def end_game(self):
        r= get_redis()
        raw= r.get(self.state_key)
        if raw:
            st= json.loads(raw)
            st["is_active"]=False
            r.set(self.state_key, json.dumps(st))
        await self.broadcast_state(force=True)
        await self.send_json({"message":"게임 종료"})
        await self.close()

    async def broadcast_state(self, force=False):
        r= get_redis()
        raw= r.get(self.state_key)
        if not raw:return
        st= json.loads(raw)
        living= [ e for e in st["enemies"] if not e["is_dead"]]
        data={
            "kind":"tick_update",
            "stage": st["stage"],
            "time_in_stage": st["time_in_stage"],
            "enemies": living,
            "balls": st["balls"],
            "upgrades": st["color_upgrades"],
            "effects": st["attack_effects"]
        }
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type":"send_state",
                "payload": data
            }
        )

    async def send_state(self, event):
        await self.send_json(event["payload"])
