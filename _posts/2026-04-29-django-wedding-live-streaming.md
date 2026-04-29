---
layout: post
title: "Django로 웨딩 라이브 스트리밍 시스템 구현하기 - 결혼식을 온라인으로 함께"
date: 2026-04-29
categories: django
author: updaun
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-04-29-django-wedding-live-streaming.webp"
---

# Django로 웨딩 라이브 스트리밍 시스템 구현하기

결혼식에 오고 싶지만 거리, 건강, 일정 때문에 참석하지 못하는 소중한 분들이 있죠. 그분들도 결혼의 순간을 함께하고, 마음을 전할 수 있다면 얼마나 좋을까요? 이번 포스트에서는 **Django + WebSocket + HLS**를 활용해 웨딩 라이브 스트리밍 시스템을 구현하는 방법을 전체 아키텍처부터 코드까지 정리합니다.

---

## 시스템 전체 구조

```
[카메라/OBS] → RTMP → [Nginx-RTMP] → HLS 변환
                                         ↓
                              [Django + Channels]
                                    ↓        ↓
                          [HLS 플레이어]  [WebSocket 축하 메시지]
                                    ↓        ↓
                              [웹 브라우저 - 하객들]
```

| 구성 요소 | 역할 |
|---|---|
| **OBS Studio** | 현장 카메라 → RTMP 송출 |
| **Nginx-RTMP** | RTMP 수신 → HLS 변환 |
| **Django Channels** | WebSocket으로 실시간 축하 메시지 |
| **Redis** | Django Channels 레이어 (메시지 브로커) |
| **hls.js** | 브라우저에서 HLS 스트림 재생 |

---

## 1단계: 환경 구성

### 패키지 설치

```bash
pip install django channels channels-redis daphne
```

### Nginx-RTMP 설치 (Ubuntu)

```bash
sudo apt install nginx libnginx-mod-rtmp
```

### `nginx.conf` 설정

```nginx
rtmp {
    server {
        listen 1935;
        chunk_size 4096;

        application live {
            live on;
            record off;

            # RTMP → HLS 변환
            hls on;
            hls_path /var/www/hls;
            hls_fragment 2s;
            hls_playlist_length 10s;
        }
    }
}

server {
    listen 80;
    
    # HLS 파일 서빙
    location /hls {
        alias /var/www/hls;
        add_header Cache-Control no-cache;
        add_header Access-Control-Allow-Origin *;
    }
}
```

Nginx를 재시작하면 OBS에서 `rtmp://서버IP/live/wedding` 으로 송출하는 것만으로 HLS 스트림이 자동 생성됩니다.

---

## 2단계: Django 프로젝트 설정

### `settings.py`

```python
INSTALLED_APPS = [
    ...
    'channels',
    'wedding_live',
]

# ASGI 설정
ASGI_APPLICATION = 'config.asgi.application'

# Redis Channel Layer
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },
    },
}
```

### `asgi.py`

```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from wedding_live import routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(routing.websocket_urlpatterns)
    ),
})
```

---

## 3단계: 앱 구현

### 모델 - `wedding_live/models.py`

```python
from django.db import models

class WeddingEvent(models.Model):
    title = models.CharField(max_length=200)
    groom = models.CharField(max_length=50)
    bride = models.CharField(max_length=50)
    date = models.DateTimeField()
    stream_key = models.CharField(max_length=100, unique=True)
    is_live = models.BooleanField(default=False)
    viewer_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.groom} ♥ {self.bride}"


class Congratulation(models.Model):
    event = models.ForeignKey(WeddingEvent, on_delete=models.CASCADE, related_name='congratulations')
    name = models.CharField(max_length=50)
    message = models.TextField()
    emoji = models.CharField(max_length=10, default='💍')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
```

### WebSocket Consumer - `wedding_live/consumers.py`

WebSocket Consumer가 핵심입니다. 축하 메시지를 받아 동일 이벤트를 시청하는 모든 사람에게 실시간으로 브로드캐스트합니다.

```python
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import WeddingEvent, Congratulation

class WeddingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.stream_key = self.scope['url_route']['kwargs']['stream_key']
        self.room_group_name = f'wedding_{self.stream_key}'

        # 그룹 참가
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # 시청자 수 증가
        await self.update_viewer_count(1)
        await self.broadcast_viewer_count()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        await self.update_viewer_count(-1)
        await self.broadcast_viewer_count()

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'congratulation':
            # DB 저장
            congrat = await self.save_congratulation(
                name=data.get('name', '익명'),
                message=data['message'],
                emoji=data.get('emoji', '💍')
            )
            # 전체 브로드캐스트
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'congratulation_message',
                    'name': congrat.name,
                    'message': congrat.message,
                    'emoji': congrat.emoji,
                    'created_at': congrat.created_at.strftime('%H:%M'),
                }
            )

    # 그룹에서 받은 메시지를 WebSocket으로 전송
    async def congratulation_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'congratulation',
            'name': event['name'],
            'message': event['message'],
            'emoji': event['emoji'],
            'created_at': event['created_at'],
        }))

    async def viewer_count_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'viewer_count',
            'count': event['count'],
        }))

    @database_sync_to_async
    def save_congratulation(self, name, message, emoji):
        event = WeddingEvent.objects.get(stream_key=self.stream_key)
        return Congratulation.objects.create(
            event=event, name=name, message=message, emoji=emoji
        )

    @database_sync_to_async
    def update_viewer_count(self, delta):
        WeddingEvent.objects.filter(
            stream_key=self.stream_key
        ).update(viewer_count=models.F('viewer_count') + delta)

    async def broadcast_viewer_count(self):
        count = await self.get_viewer_count()
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'viewer_count_update', 'count': count}
        )

    @database_sync_to_async
    def get_viewer_count(self):
        return WeddingEvent.objects.get(
            stream_key=self.stream_key
        ).viewer_count
```

### URL 라우팅 - `wedding_live/routing.py`

```python
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/wedding/(?P<stream_key>\w+)/$', consumers.WeddingConsumer.as_asgi()),
]
```

### View - `wedding_live/views.py`

```python
from django.shortcuts import render, get_object_or_404
from .models import WeddingEvent, Congratulation

def watch(request, stream_key):
    event = get_object_or_404(WeddingEvent, stream_key=stream_key)
    recent_messages = event.congratulations.all()[:20]

    context = {
        'event': event,
        'recent_messages': recent_messages,
        'hls_url': f'/hls/{stream_key}.m3u8',
        'ws_url': f'ws://{request.get_host()}/ws/wedding/{stream_key}/',
    }
    return render(request, 'wedding_live/watch.html', context)
```

---

## 4단계: 프론트엔드 구현

HLS 재생은 `hls.js`를 사용하고, 축하 메시지는 WebSocket으로 실시간 처리합니다.

### `templates/wedding_live/watch.html`

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>{{ event.groom }} ♥ {{ event.bride }} 결혼식 라이브</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
        body { font-family: 'Noto Sans KR', sans-serif; background: #fdf6f0; margin: 0; }
        .container { max-width: 960px; margin: 0 auto; padding: 20px; }
        h1 { text-align: center; color: #8b4f6e; }
        .player-wrap { position: relative; background: #000; border-radius: 12px; overflow: hidden; }
        #video { width: 100%; display: block; }
        .live-badge {
            position: absolute; top: 12px; left: 12px;
            background: #e74c3c; color: #fff;
            padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: bold;
        }
        .viewer-count {
            position: absolute; top: 12px; right: 12px;
            background: rgba(0,0,0,0.6); color: #fff;
            padding: 4px 10px; border-radius: 20px; font-size: 13px;
        }
        .chat-section { margin-top: 24px; display: flex; gap: 20px; }
        .chat-box {
            flex: 1; background: #fff; border-radius: 12px;
            padding: 16px; height: 360px; overflow-y: auto;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .message { padding: 10px 0; border-bottom: 1px solid #f0e0ea; }
        .message .name { font-weight: bold; color: #8b4f6e; }
        .message .emoji { font-size: 20px; }
        .message .text { color: #555; margin-top: 4px; }
        .message .time { font-size: 11px; color: #bbb; margin-top: 2px; }
        .input-section { background: #fff; border-radius: 12px; padding: 16px; width: 300px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .input-section h3 { margin: 0 0 12px; color: #8b4f6e; }
        input, textarea {
            width: 100%; box-sizing: border-box;
            border: 1px solid #e0c8d8; border-radius: 8px;
            padding: 8px 12px; margin-bottom: 10px; font-size: 14px;
        }
        textarea { height: 80px; resize: none; }
        .emoji-picker { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
        .emoji-btn {
            font-size: 22px; background: none; border: 2px solid transparent;
            border-radius: 8px; cursor: pointer; padding: 2px 6px;
        }
        .emoji-btn.selected { border-color: #8b4f6e; }
        button[type=submit] {
            width: 100%; background: #8b4f6e; color: #fff;
            border: none; border-radius: 8px; padding: 10px;
            font-size: 15px; cursor: pointer;
        }
        button[type=submit]:hover { background: #7a3d5d; }
    </style>
</head>
<body>
<div class="container">
    <h1>💍 {{ event.groom }} & {{ event.bride }} 결혼식</h1>

    <div class="player-wrap">
        <video id="video" controls playsinline></video>
        <span class="live-badge">🔴 LIVE</span>
        <span class="viewer-count" id="viewer-count">👁 0명 시청 중</span>
    </div>

    <div class="chat-section">
        <div class="chat-box" id="chat-box">
            {% for msg in recent_messages %}
            <div class="message">
                <span class="emoji">{{ msg.emoji }}</span>
                <span class="name">{{ msg.name }}</span>
                <div class="text">{{ msg.message }}</div>
                <div class="time">{{ msg.created_at|time:"H:i" }}</div>
            </div>
            {% endfor %}
        </div>

        <div class="input-section">
            <h3>💌 축하 메시지 보내기</h3>
            <input type="text" id="name-input" placeholder="이름 (익명 가능)" maxlength="20">
            <div class="emoji-picker">
                {% for emoji in "💍 🎊 🌸 💐 🥂 ❤️ 🎉 🕊️"|split:" " %}
                <button class="emoji-btn" data-emoji="{{ emoji }}">{{ emoji }}</button>
                {% endfor %}
            </div>
            <textarea id="message-input" placeholder="두 분의 앞날을 축하합니다 ✨" maxlength="100"></textarea>
            <button type="submit" id="send-btn">축하 보내기 💍</button>
        </div>
    </div>
</div>

<script>
    // HLS 재생
    const video = document.getElementById('video');
    const hlsUrl = "{{ hls_url }}";

    if (Hls.isSupported()) {
        const hls = new Hls();
        hls.loadSource(hlsUrl);
        hls.attachMedia(video);
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = hlsUrl;
    }

    // WebSocket 연결
    const ws = new WebSocket("{{ ws_url }}");
    const chatBox = document.getElementById('chat-box');

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'congratulation') {
            const div = document.createElement('div');
            div.className = 'message';
            div.innerHTML = `
                <span class="emoji">${data.emoji}</span>
                <span class="name">${data.name}</span>
                <div class="text">${data.message}</div>
                <div class="time">${data.created_at}</div>
            `;
            chatBox.prepend(div);
        }

        if (data.type === 'viewer_count') {
            document.getElementById('viewer-count').textContent = `👁 ${data.count}명 시청 중`;
        }
    };

    // 이모지 선택
    let selectedEmoji = '💍';
    document.querySelectorAll('.emoji-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.emoji-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            selectedEmoji = btn.dataset.emoji;
        });
    });
    document.querySelector('.emoji-btn').classList.add('selected');

    // 메시지 전송
    document.getElementById('send-btn').addEventListener('click', () => {
        const name = document.getElementById('name-input').value.trim() || '익명';
        const message = document.getElementById('message-input').value.trim();
        if (!message) return;

        ws.send(JSON.stringify({
            type: 'congratulation',
            name: name,
            message: message,
            emoji: selectedEmoji,
        }));

        document.getElementById('message-input').value = '';
    });
</script>
</body>
</html>
```

---

## 5단계: OBS 송출 설정

OBS Studio에서 아래와 같이 설정하면 결혼식 현장 영상을 바로 서버로 보낼 수 있습니다.

| 항목 | 설정값 |
|---|---|
| **서버** | `rtmp://서버IP/live` |
| **스트림 키** | `wedding` (WeddingEvent의 stream_key와 동일) |
| **비트레이트** | 2500 ~ 4000 Kbps |
| **키프레임 간격** | 2초 |
| **인코더** | x264 또는 NVENC |

---

## 전체 실행 순서

```bash
# 1. Redis 실행
redis-server

# 2. Django 마이그레이션
python manage.py migrate

# 3. WeddingEvent 생성 (Django Admin 또는 shell)
python manage.py shell
>>> from wedding_live.models import WeddingEvent
>>> from django.utils import timezone
>>> WeddingEvent.objects.create(
...     title="철수 & 영희 결혼식",
...     groom="철수",
...     bride="영희",
...     date=timezone.now(),
...     stream_key="wedding",
...     is_live=True
... )

# 4. ASGI 서버 실행 (Daphne)
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# 5. OBS에서 RTMP 송출 시작
# → 하객들은 http://서버IP:8000/watch/wedding/ 접속
```

---

## 확장 아이디어

기본 기능 외에도 아래 기능들을 추가하면 더욱 특별한 경험을 만들 수 있습니다.

- **카카오톡 초대 링크**: 간단한 URL 공유로 온라인 하객 초대
- **실시간 이모지 반응**: 화면에 이모지가 떠오르는 효과 (CSS animation)
- **녹화 저장**: Nginx-RTMP의 `record all` 옵션으로 영상 자동 저장, 식이 끝난 후 다시보기 제공
- **비밀번호 보호**: 초대받은 분들만 시청할 수 있도록 뷰에서 PIN 인증 추가
- **영상 품질 선택**: FFmpeg로 480p / 720p 다중 해상도 HLS 변환

---

## 마무리

Django Channels와 HLS를 조합하면 생각보다 간단하게 웨딩 라이브 스트리밍 시스템을 만들 수 있습니다. 결혼식에 오지 못한 해외 가족, 거동이 불편한 어른들도 실시간으로 함께하고 축하를 전할 수 있다는 것이 가장 큰 가치입니다.

결혼식은 일생에 한 번의 순간입니다. 더 많은 사람과 그 순간을 나눌 수 있도록, 이 시스템이 조금이나마 도움이 되길 바랍니다. 💍

---

*이 글이 도움이 되셨다면 공유해주세요! 구현 중 궁금한 점은 댓글로 남겨주세요.*
