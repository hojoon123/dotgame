from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # users 앱 (회원가입, 로그인 등)
    path('api/users/', include('users.urls')),

    # game 앱 (소환, 업그레이드, 세션 등)
    path('api/game/', include('game.urls')),
]
