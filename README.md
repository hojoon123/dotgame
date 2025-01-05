# dotgame
 <!DOCTYPE html>
<html>
<head>
</head>
<body style="font-family: sans-serif; line-height: 1.4;">

<!-- 서버 README 시작 -->
<h1>서버 (Django+Channels) 저장소</h1>

<h2>프로젝트 개요</h2>
<p>
이 저장소는 <strong>Django</strong>(DRF) + <strong>Channels</strong>를 활용한 
실시간 웹 게임 서버입니다.
</p>

<ul>
  <li>
    <strong>주요 기능</strong>
    <ol>
      <li>게임 세션 생성/종료 (DRF API)</li>
      <li>실시간 통신 (WebSocket) &middot; 0.1초 간격 틱(<code>tick_internal</code>) 진행</li>
      <li>맵/경로 &mdash; 큰 사각형 + 작은 사각형 "구멍" &middot; 적의 반시계 이동</li>
      <li>볼(플레이어 유닛) 이동 &mdash; 우클릭으로 좌표 이동 &middot; 공격(사거리, 쿨다운, 업그레이드 등)</li>
      <li>스테이지(Wave) 진행 &mdash; 50초마다 다음 스테이지로 넘어가며 계속 진행</li>
    </ol>
  </li>
</ul>

<h2>기술 스택</h2>
<ul>
  <li>Python 3</li>
  <li>Django 3+/4+</li>
  <li>Django Channels (Redis Channel Layer)</li>
  <li>Redis (실시간 상태 저장/메시지 큐)</li>
</ul>

<h2>설치 &amp; 실행</h2>
<ol>
  <li><strong>Python 가상환경 설정</strong>
    <pre><code>python -m venv venv
source venv/bin/activate
</code></pre>
  </li>
  <li><strong>필요 패키지 설치</strong>
    <pre><code>pip install -r requirements.txt
</code></pre>
  </li>
  <li><strong>Redis 서버 실행</strong> (예: Docker)
    <pre><code>docker run -p 6379:6379 redis
</code></pre>
  </li>
  <li><strong>마이그레이션 &amp; 서버 실행</strong>
    <pre><code>python manage.py makemigrations
python manage.py migrate
python manage.py runserver
</code></pre>
    <p>또는 Channels 전용 daphne 사용:</p>
    <pre><code>daphne <PROJECT_NAME>.asgi:application --port 8000
</code></pre>
  </li>
</ol>

<h2>주요 파일 구조</h2>
<pre><code>server/
 ├─ manage.py
 ├─ &lt;project_name&gt;/
 │   ├─ settings.py
 │   ├─ asgi.py
 │   └─ ...
 ├─ game/
 │   ├─ consumers.py     (websocket 로직)
 │   ├─ wave_config.py   (스테이지 파라미터)
 │   ├─ urls.py
 │   └─ ...
 └─ requirements.txt
</code></pre>

<p>
<strong>consumers.py</strong>: 실시간 로직 (틱, 적/볼 이동, 공격, etc.) <br/>
<strong>wave_config.py</strong>: 스테이지(duration, boss 스폰 등) <br/>
<strong>asgi.py</strong>: Channels 설정 (ProtocolTypeRouter, URLRouter)
</p>

<h2>사용 예시</h2>
<ol>
  <li>API(선택): <code>/api/game/start_session/</code> &rarr; <code>session_id</code> 발급</li>
  <li>클라이언트(WebSocket) 연결: <code>ws://localhost:8000/ws/game/&lt;session_id&gt;/</code></li>
  <li>
    <strong>Actions</strong>
    <ul>
      <li><code>{action:"summon_ball"}</code> &rarr; 볼 소환</li>
      <li><code>{action:"move_ball", ball_idx, tx, ty}</code> &rarr; 볼 이동</li>
      <li><code>{action:"upgrade_color", color:"red"}</code> &rarr; 업그레이드</li>
    </ul>
  </li>
  <li>서버는 주기적으로
    <code>{ kind:"tick_update", stage, time_in_stage, enemies, balls, ... }</code> 를
    브로드캐스트
  </li>
</ol>

</body>
</html>


![image](https://github.com/user-attachments/assets/4eeb949a-7880-4ccf-a556-85475cb7ce00)
