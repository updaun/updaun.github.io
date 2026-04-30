---
layout: post
title: "YouTube 구조를 참고해 웨딩 라이브 송출 시스템 설계하기"
date: 2026-04-30
categories: django
author: updaun
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-04-30-youtube-inspired-wedding-live-streaming.webp"
---

# YouTube 구조를 참고해 웨딩 라이브 송출 시스템 설계하기

저번 포스트에서 Django + Nginx-RTMP로 웨딩 라이브 스트리밍 시스템의 기초를 구현했습니다. 이번엔 한 걸음 더 나아가 **"YouTube는 어떻게 동작하는가?"** 를 분석하고, 그 구조를 웨딩 서비스에 맞게 현실적으로 가져오는 방법을 설계합니다. OBS 없이 스마트폰만으로 송출하는 구조까지 포함합니다.

---

## YouTube Live Streaming 구조 분석

YouTube가 전 세계 수백만 명에게 라이브를 서빙할 수 있는 이유는 기술 자체가 특별해서가 아닙니다. **규모에 맞게 각 구간을 분리하고 최적화**했기 때문입니다.

```
[송출자]
    ↓ RTMP / RTMPS
[인제스트 서버] — 전 세계 엣지, 가장 가까운 곳으로 연결
    ↓
[트랜스코더] — 1080p / 720p / 480p / 360p 동시 생성
    ↓
[패키저] — HLS / DASH 세그먼트(~2초) 생성
    ↓
[CDN] — 전 세계 PoP에서 시청자 근처로 서빙
    ↓
[시청자] — ABR로 네트워크 상황에 따라 자동 해상도 전환
```

| 구간 | 기술 | 지연 |
|---|---|---|
| 송출 → 인제스트 | RTMP | ~0.5초 |
| 인제스트 → 트랜스코딩 | 내부 처리 | ~1초 |
| 트랜스코딩 → CDN | HLS 세그먼트 | ~2~4초 |
| CDN → 시청자 | HLS ABR | ~5~10초 |
| **총 지연 (일반)** | | **약 15~30초** |
| **총 지연 (저지연 모드)** | DASH chunked | **약 3~7초** |

---

## 우리가 가져올 것, 버릴 것

YouTube의 구조는 **수백만 명**을 위한 설계입니다. 웨딩 라이브는 **수십 ~ 수백 명**이 대상입니다. 그대로 따라 만들면 오버엔지니어링입니다.

| 구성 요소 | YouTube | 웨딩 시스템 | 이유 |
|---|---|---|---|
| 인제스트 | 글로벌 엣지 서버 | 단일 Nginx-RTMP | 결혼식은 단발성, 지역 행사 |
| 트랜스코딩 | 수천 코어 자체 처리 | FFmpeg (서버 1대) | 수백 명엔 충분 |
| 다중 해상도 | 5~6개 | 720p / 360p 2개 | 모바일 대역폭 배려 |
| 배포 | Google CDN | Cloudflare Stream 또는 직서빙 | 비용·복잡도 절감 |
| 실시간 채팅 | WebSocket 전용 인프라 | Django Channels | 규모 충분 |
| 송출 도구 | RTMP 모든 클라이언트 | **스마트폰 앱 (OBS 불필요)** | 현장 편의성 |

핵심은 **"RTMP 인제스트 → FFmpeg 트랜스코딩 → HLS 배포"** 파이프라인은 YouTube와 동일하게 가져오되, 규모만 현실에 맞게 줄이는 것입니다.

---

## 목표 아키텍처

```
[스마트폰 앱 - Larix Broadcaster or 커스텀 앱]
            ↓ RTMP
      [Nginx-RTMP 서버]
            ↓
      [FFmpeg 트랜스코더]
       ↓           ↓
  720p HLS      360p HLS    ← 다중 해상도 (YouTube 방식 차용)
       ↓           ↓
  [Django Static / Cloudflare CDN]
            ↓
      [시청자 브라우저]
       - hls.js ABR 재생    ← YouTube 방식 차용
       - WebSocket 축하 메시지
```

---

## 구현 단계

### 1단계: Nginx-RTMP + FFmpeg 다중 해상도 트랜스코딩

YouTube에서 가장 핵심적으로 차용할 부분입니다. 단일 스트림을 받아 **720p와 360p를 동시에 생성**합니다.

```nginx
# /etc/nginx/nginx.conf

rtmp {
    server {
        listen 1935;
        chunk_size 4096;

        application live {
            live on;
            record off;

            # 수신 즉시 FFmpeg로 다중 해상도 트랜스코딩
            exec ffmpeg -i rtmp://localhost/live/$name
                # 720p
                -c:v libx264 -preset veryfast -b:v 2000k
                -maxrate 2000k -bufsize 4000k
                -vf scale=-2:720 -g 60 -c:a aac -b:a 128k -ac 2
                -f flv rtmp://localhost/hls720/$name

                # 360p
                -c:v libx264 -preset veryfast -b:v 600k
                -maxrate 600k -bufsize 1200k
                -vf scale=-2:360 -g 60 -c:a aac -b:a 96k -ac 2
                -f flv rtmp://localhost/hls360/$name;
        }

        # 720p HLS 생성
        application hls720 {
            live on;
            hls on;
            hls_path /var/www/hls/720;
            hls_fragment 2s;
            hls_playlist_length 10s;
            deny play all;
        }

        # 360p HLS 생성
        application hls360 {
            live on;
            hls on;
            hls_path /var/www/hls/360;
            hls_fragment 2s;
            hls_playlist_length 10s;
            deny play all;
        }
    }
}

server {
    listen 80;

    location /hls {
        alias /var/www/hls;
        add_header Cache-Control no-cache;
        add_header Access-Control-Allow-Origin *;
        types {
            application/vnd.apple.mpegurl m3u8;
            video/mp2t ts;
        }
    }
}
```

이 설정으로 스마트폰에서 RTMP 송출을 시작하는 순간 `/var/www/hls/720/`과 `/var/www/hls/360/` 에 HLS 세그먼트가 자동 생성됩니다.

---

### 2단계: Master Playlist 생성 (ABR - YouTube 방식)

YouTube가 네트워크 상황에 따라 해상도를 자동으로 전환하는 **ABR(Adaptive Bitrate)** 을 구현합니다. 핵심은 두 해상도를 하나의 마스터 플레이리스트로 묶는 것입니다.

```python
# wedding_live/views.py

from django.http import HttpResponse

def master_playlist(request, stream_key):
    """
    두 해상도를 묶는 HLS 마스터 플레이리스트를 동적으로 생성.
    hls.js가 이 파일을 읽고 네트워크 상황에 따라 자동 전환.
    """
    content = f"""#EXTM3U
#EXT-X-VERSION:3

#EXT-X-STREAM-INF:BANDWIDTH=2128000,RESOLUTION=1280x720
/hls/720/{stream_key}.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=696000,RESOLUTION=640x360
/hls/360/{stream_key}.m3u8
"""
    return HttpResponse(content, content_type='application/vnd.apple.mpegurl')
```

```python
# wedding_live/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('watch/<str:stream_key>/', views.watch, name='watch'),
    path('stream/<str:stream_key>/master.m3u8', views.master_playlist, name='master_playlist'),
]
```

---

### 3단계: 스마트폰 앱으로 송출 (OBS 대체)

OBS는 데스크탑 전용 소프트웨어입니다. 결혼식 현장에서는 스마트폰이 훨씬 현실적입니다.

#### 옵션 A: Larix Broadcaster 앱 (즉시 사용 가능)

설치 후 Settings → Connections → New Connection에서 아래 정보만 입력합니다.

```
URL: rtmp://서버IP/live
Stream Name: wedding_abc123
```

무료이며 iOS / Android 모두 지원합니다. 결혼 당일 담당자 스마트폰에 미리 설치하고 QR코드로 설정값을 전달하면 됩니다.

#### 옵션 B: 커스텀 앱 내 송출 기능 (Flutter)

웨딩 서비스 자체 앱이 있다면 송출 기능을 직접 내장할 수 있습니다.

```yaml
# pubspec.yaml
dependencies:
  camera: ^0.10.5
  flutter_rtmp_publisher: ^0.1.0
```

```dart
// wedding_stream_page.dart

class WeddingStreamPage extends StatefulWidget {
  final String streamKey;
  const WeddingStreamPage({required this.streamKey});

  @override
  State<WeddingStreamPage> createState() => _WeddingStreamPageState();
}

class _WeddingStreamPageState extends State<WeddingStreamPage> {
  late RtmpPublisher _publisher;
  bool _isStreaming = false;

  @override
  void initState() {
    super.initState();
    _publisher = RtmpPublisher(
      url: 'rtmp://서버IP/live',
      streamKey: widget.streamKey,
      videoConfig: VideoConfig(
        width: 1280,
        height: 720,
        fps: 30,
        bitrate: 2000 * 1024,
      ),
      audioConfig: AudioConfig(
        bitrate: 128 * 1024,
        sampleRate: 44100,
      ),
    );
  }

  void _toggleStream() async {
    if (_isStreaming) {
      await _publisher.stop();
    } else {
      await _publisher.start();
    }
    setState(() => _isStreaming = !_isStreaming);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          CameraPreview(_publisher.cameraController),
          Positioned(
            bottom: 40,
            child: ElevatedButton(
              onPressed: _toggleStream,
              style: ElevatedButton.styleFrom(
                backgroundColor: _isStreaming ? Colors.red : Colors.pink,
              ),
              child: Text(_isStreaming ? '송출 중지' : '결혼식 라이브 시작'),
            ),
          ),
        ],
      ),
    );
  }
}
```

---

### 4단계: Django Channels - 실시간 축하 메시지

WebSocket Consumer는 이전 포스트와 동일한 구조입니다. 여기서는 **이모지 반응** 기능을 추가합니다. 시청자가 이모지를 누르면 모든 시청자 화면에 이모지가 떠오르는 YouTube의 Super Thanks와 유사한 기능입니다.

```python
# wedding_live/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import WeddingEvent, Congratulation

class WeddingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.stream_key = self.scope['url_route']['kwargs']['stream_key']
        self.room_group_name = f'wedding_{self.stream_key}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self._broadcast_viewer_count(delta=1)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self._broadcast_viewer_count(delta=-1)

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data['type'] == 'congratulation':
            congrat = await self._save_congratulation(data)
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'congratulation_message',
                **congrat,
            })

        elif data['type'] == 'emoji_reaction':
            # DB 저장 없이 즉시 브로드캐스트 (YouTube Super Thanks 방식)
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'emoji_burst',
                'emoji': data['emoji'],
            })

    async def congratulation_message(self, event):
        await self.send(text_data=json.dumps({'type': 'congratulation', **event}))

    async def emoji_burst(self, event):
        await self.send(text_data=json.dumps({'type': 'emoji_burst', 'emoji': event['emoji']}))

    async def viewer_count_update(self, event):
        await self.send(text_data=json.dumps({'type': 'viewer_count', 'count': event['count']}))

    @database_sync_to_async
    def _save_congratulation(self, data):
        event = WeddingEvent.objects.get(stream_key=self.stream_key)
        c = Congratulation.objects.create(
            event=event,
            name=data.get('name', '익명'),
            message=data['message'],
            emoji=data.get('emoji', '💍'),
        )
        return {
            'name': c.name,
            'message': c.message,
            'emoji': c.emoji,
            'created_at': c.created_at.strftime('%H:%M'),
        }

    async def _broadcast_viewer_count(self, delta):
        count = await self._update_viewer_count(delta)
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'viewer_count_update',
            'count': count,
        })

    @database_sync_to_async
    def _update_viewer_count(self, delta):
        from django.db.models import F
        WeddingEvent.objects.filter(stream_key=self.stream_key).update(
            viewer_count=F('viewer_count') + delta
        )
        return WeddingEvent.objects.get(stream_key=self.stream_key).viewer_count
```

---

### 5단계: 프론트엔드 - ABR 재생 + 이모지 버스트

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>{{ event.groom }} ♥ {{ event.bride }} 결혼식 라이브</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Noto Sans KR', sans-serif; background: #fdf6f0; }
        .container { max-width: 1000px; margin: 0 auto; padding: 20px; }
        h1 { text-align: center; color: #8b4f6e; padding: 20px 0; font-size: 22px; }

        /* 플레이어 */
        .player-wrap { position: relative; background: #000; border-radius: 12px; overflow: hidden; }
        #video { width: 100%; display: block; max-height: 500px; }
        .badge {
            position: absolute; top: 12px; padding: 4px 12px;
            border-radius: 20px; font-size: 13px; font-weight: bold;
        }
        .live-badge { left: 12px; background: #e74c3c; color: #fff; }
        .viewer-badge { right: 12px; background: rgba(0,0,0,0.55); color: #fff; }

        /* 이모지 버스트 레이어 */
        #emoji-layer {
            position: absolute; inset: 0;
            pointer-events: none; overflow: hidden;
        }
        .floating-emoji {
            position: absolute; bottom: 0; font-size: 28px;
            animation: floatUp 2.5s ease-out forwards;
        }
        @keyframes floatUp {
            0%   { transform: translateY(0) scale(1); opacity: 1; }
            100% { transform: translateY(-300px) scale(1.4); opacity: 0; }
        }

        /* 하단 패널 */
        .panel { display: flex; gap: 16px; margin-top: 20px; }
        .chat-box {
            flex: 1; background: #fff; border-radius: 12px;
            padding: 16px; height: 340px; overflow-y: auto;
            box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        }
        .msg { padding: 10px 0; border-bottom: 1px solid #f5e8f0; }
        .msg .meta { font-weight: bold; color: #8b4f6e; font-size: 14px; }
        .msg .text { color: #444; font-size: 14px; margin-top: 3px; }
        .msg .time { color: #bbb; font-size: 11px; margin-top: 2px; }

        .input-box {
            width: 280px; background: #fff; border-radius: 12px;
            padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.07);
            display: flex; flex-direction: column; gap: 10px;
        }
        .input-box h3 { color: #8b4f6e; font-size: 15px; }
        input, textarea {
            width: 100%; border: 1px solid #e0c8d8; border-radius: 8px;
            padding: 8px 12px; font-size: 13px; font-family: inherit;
        }
        textarea { height: 70px; resize: none; }

        /* 이모지 선택 */
        .emoji-row { display: flex; gap: 6px; flex-wrap: wrap; }
        .emoji-btn {
            font-size: 20px; background: none;
            border: 2px solid transparent; border-radius: 8px;
            padding: 2px 5px; cursor: pointer;
        }
        .emoji-btn.selected { border-color: #8b4f6e; background: #fdf0f6; }

        /* 즉각 이모지 반응 버튼 */
        .reaction-row { display: flex; gap: 8px; }
        .reaction-btn {
            flex: 1; font-size: 22px; background: #fdf0f6;
            border: none; border-radius: 10px;
            padding: 6px; cursor: pointer; transition: transform 0.1s;
        }
        .reaction-btn:active { transform: scale(1.3); }

        /* 전송 버튼 */
        .send-btn {
            background: #8b4f6e; color: #fff; border: none;
            border-radius: 8px; padding: 10px; font-size: 14px; cursor: pointer;
        }
        .send-btn:hover { background: #7a3d5d; }
    </style>
</head>
<body>
<div class="container">
    <h1>💍 {{ event.groom }} & {{ event.bride }} 결혼식</h1>

    <div class="player-wrap">
        <video id="video" controls playsinline autoplay muted></video>
        <span class="badge live-badge">🔴 LIVE</span>
        <span class="badge viewer-badge" id="viewer-count">👁 0명</span>
        <div id="emoji-layer"></div>
    </div>

    <div class="panel">
        <div class="chat-box" id="chat-box">
            {% for msg in recent_messages %}
            <div class="msg">
                <div class="meta">{{ msg.emoji }} {{ msg.name }}</div>
                <div class="text">{{ msg.message }}</div>
                <div class="time">{{ msg.created_at|time:"H:i" }}</div>
            </div>
            {% endfor %}
        </div>

        <div class="input-box">
            <h3>💌 축하 메시지</h3>
            <input type="text" id="name-input" placeholder="이름 (익명 가능)" maxlength="20">

            <div class="emoji-row" id="emoji-row">
                {% for e in "💍 🎊 🌸 💐 🥂 ❤️ 🎉 🕊️"|split:" " %}
                <button class="emoji-btn" data-emoji="{{ e }}">{{ e }}</button>
                {% endfor %}
            </div>

            <textarea id="msg-input" placeholder="두 분의 앞날을 축복합니다 ✨" maxlength="100"></textarea>
            <button class="send-btn" id="send-btn">축하 보내기 💍</button>

            <div style="border-top: 1px solid #f0e0ea; padding-top: 10px;">
                <div style="font-size: 13px; color: #999; margin-bottom: 8px;">즉각 반응</div>
                <div class="reaction-row">
                    <button class="reaction-btn" data-emoji="🎊">🎊</button>
                    <button class="reaction-btn" data-emoji="❤️">❤️</button>
                    <button class="reaction-btn" data-emoji="👏">👏</button>
                    <button class="reaction-btn" data-emoji="😭">😭</button>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
// ─── HLS ABR 재생 (YouTube 방식) ───────────────────────────
const video = document.getElementById('video');
const masterUrl = "{% url 'master_playlist' event.stream_key %}";

if (Hls.isSupported()) {
    const hls = new Hls({ lowLatencyMode: true });
    hls.loadSource(masterUrl);
    hls.attachMedia(video);
} else if (video.canPlayType('application/vnd.apple.mpegurl')) {
    video.src = masterUrl;
}

// ─── WebSocket 연결 ────────────────────────────────────────
const ws = new WebSocket(`ws://${location.host}/ws/wedding/{{ event.stream_key }}/`);
const chatBox = document.getElementById('chat-box');

ws.onmessage = ({ data }) => {
    const msg = JSON.parse(data);

    if (msg.type === 'congratulation') {
        const div = document.createElement('div');
        div.className = 'msg';
        div.innerHTML = `
            <div class="meta">${msg.emoji} ${msg.name}</div>
            <div class="text">${msg.message}</div>
            <div class="time">${msg.created_at}</div>
        `;
        chatBox.prepend(div);
    }

    if (msg.type === 'viewer_count') {
        document.getElementById('viewer-count').textContent = `👁 ${msg.count}명`;
    }

    if (msg.type === 'emoji_burst') {
        spawnEmoji(msg.emoji);
    }
};

// ─── 이모지 버스트 애니메이션 ──────────────────────────────
function spawnEmoji(emoji) {
    const layer = document.getElementById('emoji-layer');
    const el = document.createElement('span');
    el.className = 'floating-emoji';
    el.textContent = emoji;
    el.style.left = (10 + Math.random() * 80) + '%';
    layer.appendChild(el);
    setTimeout(() => el.remove(), 2500);
}

// ─── 이모지 선택 ───────────────────────────────────────────
let selectedEmoji = '💍';
document.querySelectorAll('.emoji-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.emoji-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        selectedEmoji = btn.dataset.emoji;
    });
});
document.querySelector('.emoji-btn').classList.add('selected');

// ─── 축하 메시지 전송 ──────────────────────────────────────
document.getElementById('send-btn').addEventListener('click', () => {
    const name = document.getElementById('name-input').value.trim() || '익명';
    const message = document.getElementById('msg-input').value.trim();
    if (!message) return;

    ws.send(JSON.stringify({ type: 'congratulation', name, message, emoji: selectedEmoji }));
    document.getElementById('msg-input').value = '';
});

// ─── 즉각 이모지 반응 ──────────────────────────────────────
document.querySelectorAll('.reaction-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        ws.send(JSON.stringify({ type: 'emoji_reaction', emoji: btn.dataset.emoji }));
    });
});
</script>
</body>
</html>
```

---

## 전체 흐름 정리

```
결혼 당일 현장
─────────────────────────────────────────────────────
1. 담당자 스마트폰 → Larix Broadcaster 실행
   → rtmp://서버IP/live/wedding_abc123 으로 RTMP 송출

서버 (자동 처리)
─────────────────────────────────────────────────────
2. Nginx-RTMP 수신
3. FFmpeg 트랜스코딩 → 720p + 360p HLS 동시 생성
4. Django가 마스터 플레이리스트(master.m3u8)로 두 해상도 묶음

하객 시청 (링크 접속)
─────────────────────────────────────────────────────
5. hls.js가 마스터 플레이리스트 읽고 ABR 재생 시작
   → Wi-Fi 환경이면 720p, LTE 약하면 자동으로 360p 전환
6. WebSocket 연결 → 실시간 축하 메시지 + 이모지 반응
```

---

## YouTube와 최종 비교

| 항목 | YouTube | 우리 웨딩 시스템 |
|---|---|---|
| 송출 | OBS, 모바일 앱 | **스마트폰 앱 (Larix / 커스텀)** |
| 인제스트 | 글로벌 엣지 | Nginx-RTMP 단일 서버 |
| 트랜스코딩 | 자체 수천 코어 | **FFmpeg (서버 1대)** |
| 다중 해상도 | 5~6개 | **720p + 360p** |
| 배포 | Google CDN | 직서빙 or Cloudflare |
| ABR 전환 | 자체 플레이어 | **hls.js** |
| 실시간 채팅 | 전용 인프라 | **Django Channels + Redis** |
| 이모지 반응 | Super Thanks | **WebSocket emoji burst** |
| 목표 동시 시청 | 수백만 명 | 수십 ~ 수백 명 |

YouTube의 구조를 **그대로 모방하되, 규모를 현실에 맞게** 줄인 것이 이번 설계의 핵심입니다. 기술 선택의 방향은 같고, 인프라 규모만 다릅니다.

---

## 마무리

"YouTube는 어떻게 동작하는가"를 이해하면 라이브 스트리밍의 각 구간이 왜 그렇게 설계됐는지 보입니다. RTMP 인제스트, FFmpeg 트랜스코딩, HLS ABR 배포는 YouTube가 발명한 개념이 아닙니다. 오픈소스 기술들을 조합한 것이고, 우리도 같은 조합을 사용할 수 있습니다.

결혼식은 일생에 한 번입니다. 오지 못한 소중한 분들도 실시간으로 함께하고 이모지로 축하를 전할 수 있는 경험, 생각보다 가까운 기술로 만들 수 있습니다. 💍

---

*구현 중 막히는 부분은 댓글로 남겨주세요!*
