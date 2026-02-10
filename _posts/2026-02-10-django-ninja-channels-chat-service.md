---
layout: post
title: "Django-Ninja와 Channels로 KakaoTalk 같은 채팅 서비스 만들기: 아키텍처부터 UX까지"
date: 2026-02-10 10:00:00 +0900
categories: [Django, Python, Real-time, WebSocket, Backend Architecture]
tags: [Django, Channels, Django-Ninja, WebSocket, Real-time Chat, Message Queue, UX, Backend, Async, Python]
---

KakaoTalk이나 Slack 같은 채팅 애플리케이션을 보면 마치 마법처럼 메시지가 순식간에 전달되고, 타이핑 중임이 표시되며, 예기치 않은 네트워크 끊김에도 자동으로 복구됩니다. 이런 경험을 제공하기 위해서는 단순한 REST API만으로는 부족합니다. 이 글에서는 Django 에코시스템의 강력한 도구들인 **Django-Ninja**와 **Channels**를 활용하여 프로덕션급 채팅 서비스를 어떻게 구축하는지, 그리고 사용자 경험을 어떻게 최적화하는지 자세히 살펴보겠습니다.

## 🏗️ 아키텍처: Django-Ninja vs Channels 선택하기

### Django-Ninja와 Channels의 역할 분담

매번 틀리는 개발자들이 많지만, **Django-Ninja**와 **Channels**는 경쟁 관계가 아니라 협력 관계입니다. Django-Ninja는 **빠른 REST API 개발을 위한 프레임워크**이고, Channels는 **WebSocket을 통한 양방향 실시간 통신**을 담당합니다.

```python
# Django-Ninja: 메시지 전송 (HTTP POST)
@api.post("/messages")
def send_message(request, payload: MessageSchema):
    message = Message.objects.create(
        sender=request.user,
        room=payload.room,
        content=payload.content
    )
    # Channels를 통해 실시간 전송
    notify_channel(message)
    return {"status": "sent"}

# Channels: 실시간 수신 (WebSocket)
class ChatConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data):
        data = json.loads(text_data)
        # 모든 사용자에게 즉시 전송
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat_message", "message": data}
        )
```

**설계의 핵심**: Django-Ninja는 CRUD와 비즈니스 로직을 처리하고, Channels는 그 결과를 모든 연결된 클라이언트에게 실시간으로 브로드캐스트합니다. 이 분리가 심플하고 유지보수하기 좋은 아키텍처의 시작입니다.

---

## ⚙️ 기술적 고려사항: 프로덕션 채팅 서비스의 3가지 핵심

### 1. 메시지 영속성과 재전송 전략

채팅 서비스에서 가장 중요한 것은 메시지 손실이 없다는 보장입니다. 사용자가 인터넷 연결을 잠시 잃거나, 앱을 종료했을 때도 메시지가 서버에 안전하게 저장되어 있어야 합니다.

```python
# Message 모델 설계
from django.db import models
from django.utils import timezone

class Message(models.Model):
    PENDING = "pending"
    SENT = "sent"
    READ = "read"
    
    STATUS_CHOICES = [
        (PENDING, "대기중"),
        (SENT, "전송됨"),
        (READ, "읽음"),
    ]
    
    room = models.ForeignKey('ChatRoom', on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    
    # 중요: 동시성 제어를 위한 업데이트 타임스탐프
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['room', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]

# Django-Ninja API로 메시지 로드
@api.get("/rooms/{room_id}/messages")
def get_messages(request, room_id: int, limit: int = 50, offset: int = 0):
    room = ChatRoom.objects.get(id=room_id)
    messages = Message.objects.filter(room=room).order_by('-created_at')[offset:offset+limit]
    
    # 읽지 않은 메시지 자동 읽음 처리
    unread = messages.filter(status=Message.PENDING).exclude(sender=request.user)
    unread.update(status=Message.READ)
    
    return {"messages": [MessageSchema.from_orm(m) for m in reversed(messages)]}
```

왜 이렇게 복잡한가? 왜냐하면 **메시지는 한 번 전송되면 절대 사라져서는 안 되기 때문**입니다. 상태 필드를 통해 메시지의 생명주기를 추적하고, 인덱싱으로 대량의 메시지도 빠르게 조회할 수 있게 만듭니다.

### 2. 동시성 제어와 Redis 기반 메시지 큐

만약 1000명이 동시에 같은 채팅방에서 메시지를 보낸다면? 각 메시지마다 데이터베이스 쓰기가 발생하고, Channels가 1000개의 WebSocket 연결에 각각 전송해야 합니다. 이런 상황에서 병목이 생길 수 있습니다.

```python
# Redis를 활용한 메시지 큐 전략
import redis
import json
from celery import shared_task

redis_client = redis.Redis(host='localhost', port=6379, db=0)

@api.post("/messages")
def send_message(request, payload: MessageSchema):
    # 1. 즉시 메시지 저장 (동기)
    message = Message.objects.create(
        sender=request.user,
        room_id=payload.room_id,
        content=payload.content,
        status=Message.PENDING
    )
    
    # 2. Redis 큐에 저장 (비동기 처리를 위해)
    redis_client.lpush(
        f"messages:room:{payload.room_id}",
        json.dumps({
            "id": message.id,
            "sender_id": message.sender_id,
            "content": message.content,
            "created_at": message.created_at.isoformat()
        })
    )
    
    # 3. Channels 그룹에 즉시 전송 (혹은 잠시 지연)
    broadcast_message.delay(message.id)
    
    return {"id": message.id, "status": "pending"}

# Celery 태스크: 백그라운드에서 처리
@shared_task
def broadcast_message(message_id):
    try:
        message = Message.objects.get(id=message_id)
        # 모든 연결된 클라이언트에게 전송
        async_to_sync(notify_room)(message)
        message.status = Message.SENT
        message.save(update_fields=['status'])
    except Message.DoesNotExist:
        pass
```

이 방식의 이점: 데이터베이스 부하를 줄이고, 클라이언트 응답을 빠르게 하며, 동시에 안정적인 메시지 전달을 보장합니다.

### 3. 온라인 상태 관리와 Presence 시스템

사용자가 온라인인지 오프라인인지 어떻게 알 수 있을까요? WebSocket 연결 상태만으로는 부족합니다. 여러 기기에서 접속할 수 있고, 네트워크 불안정성도 고려해야 합니다.

```python
# Channels Presence 시스템
from channels.layers import get_channel_layer
import asyncio

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'room_{self.room_id}'
        self.user = self.scope['user']
        
        # 1. 사용자를 온라인 상태로 마킹
        await self.mark_online()
        
        # 2. 채팅방 그룹에 참여
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # 3. 다른 사용자들에게 알림
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_status_changed",
                "user_id": self.user.id,
                "status": "online"
            }
        )

    async def disconnect(self, close_code):
        # Redis에서 온라인 상태 제거
        await self.mark_offline()
        
        # 다른 사용자들에게 알림
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def mark_online(self):
        cache.set(f"user_online:{self.user.id}", True, timeout=300)  # 5분 타임아웃
        
    async def mark_offline(self):
        cache.delete(f"user_online:{self.user.id}")

# API로 현재 온라인 사용자 조회
@api.get("/rooms/{room_id}/online-users")
def get_online_users(request, room_id: int):
    room = ChatRoom.objects.get(id=room_id)
    online_users = []
    
    for user in room.participants.all():
        if cache.get(f"user_online:{user.id}"):
            online_users.append({"id": user.id, "name": user.get_full_name()})
    
    return {"online_users": online_users}
```

이 설계의 장점: 복수 기기 접속을 지원하고, 5분마다 자동으로 온라인 상태를 리셋하여 좀비 상태(연결 끊김을 감지하지 못한 상태)를 방지합니다.

---

## 💬 채팅 UX: 사용자 경험을 우선하는 설계

일반적으로 개발자들은 기술에 집중하다가 사용자 경험을 간과하곤 합니다. 하지만 **채팅 서비스에서의 작은 UX 차이가 서비스 만족도를 크게 좌우**합니다. 실제 사용자가 원하는 것들을 살펴봅시다.

### 1. 동시 입력 감지 (Typing Indicator)

메시지를 받기 전에 상대방이 뭔가 입력하고 있다는 것을 알 수 있다면 사용자는 답변을 준비할 수 있습니다. 이것은 단순한 기능이 아니라 **사람처럼 자연스러운 대화 경험**을 만드는 핵심입니다.

```python
class ChatConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data):
        data = json.loads(text_data)
        
        if data['type'] == 'typing':
            # 다른 사용자에게 타이핑 상태 전송
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_typing",
                    "user_id": self.user.id,
                    "user_name": self.user.get_full_name()
                }
            )
        
        elif data['type'] == 'stop_typing':
            # 타이핑 중지 알림
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_stop_typing",
                    "user_id": self.user.id
                }
            )
        
        elif data['type'] == 'message':
            # 실제 메시지 전송
            await self.send_actual_message(data)

    async def user_typing(self, event):
        # 브라우저에 타이핑 상태 전송
        await self.send(text_data=json.dumps({
            "type": "typing",
            "user_id": event['user_id'],
            "user_name": event['user_name']
        }))
```

**클라이언트 구현 (JavaScript)**:
```javascript
let typingTimeout;

inputElement.addEventListener('input', (e) => {
    // 타이핑 시작
    socket.send(JSON.stringify({type: 'typing'}));
    
    // 300ms 동안 입력이 없으면 타이핑 중지로 간주
    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(() => {
        socket.send(JSON.stringify({type: 'stop_typing'}));
    }, 300);
});

// 수신 측에서 표시
socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'typing') {
        showTypingIndicator(data.user_name);
    } else if (data.type === 'stop_typing') {
        hideTypingIndicator(data.user_id);
    }
};
```

이 기능이 중요한 이유: 상대방의 반응성을 보여주어 대화가 끊어지지 않은 느낌을 유지합니다.

### 2. 메시지 상태 표시 (Message Status)

KakaoTalk에서 메시지 옆에 보이는 작은 체크 표시들 - 이것들이 사용자가 메시지를 받았는지, 읽었는지 알 수 있게 해줍니다. 이는 매우 중요한 피드백 메커니즘입니다.

```python
class MessageSchema(BaseModel):
    id: int
    content: str
    sender_id: int
    created_at: datetime
    status: str  # "pending" | "sent" | "read"
    
    class Config:
        from_attributes = True

# WebSocket을 통해 상태 업데이트 전송
async def update_message_status(message_id: int, new_status: str):
    message = await sync_to_async(Message.objects.get)(id=message_id)
    await sync_to_async(message.update)(status=new_status)
    
    # 모든 참여자에게 상태 업데이트 전송
    await channel_layer.group_send(
        f"room_{message.room_id}",
        {
            "type": "message_status_update",
            "message_id": message_id,
            "status": new_status,
            "updated_at": message.updated_at.isoformat()
        }
    )
```

**클라이언트에서의 상태 표시**:
```javascript
// 메시지 수신 시 상태 업데이트
socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'message_status_update') {
        updateMessageUI(data.message_id, data.status);
        // "보냄" → "전송됨" → "읽음"으로 자동 업데이트
    }
};

function updateMessageUI(messageId, status) {
    const messageEl = document.querySelector(`[data-message-id="${messageId}"]`);
    
    if (status === 'sent') {
        messageEl.classList.add('sent');
    } else if (status === 'read') {
        messageEl.classList.add('read');
        messageEl.querySelector('.timestamp').textContent = '읽음';
    }
}
```

### 3. 오프라인 메시지 큐와 자동 재전송

사용자가 인터넷 연결을 잃었을 때 메시지를 로컬에 저장했다가, 재연결되면 자동으로 전송하는 기능입니다. **KakaoTalk의 가장 중요한 UX 중 하나**입니다.

```python
class ChatConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data):
        data = json.loads(text_data)
        
        if data['type'] == 'message':
            message = await self.save_message(data)
            
            # 즉시 ACK 전송 (클라이언트에 수신 확인)
            await self.send(text_data=json.dumps({
                "type": "message_ack",
                "local_id": data.get('local_id'),  # 클라이언트에서 생성한 임시 ID
                "message_id": message.id,
                "status": "pending"
            }))
            
            # 비동기로 다른 사용자에게 전송
            await self.notify_other_users(message)
```

**클라이언트 구현**:
```javascript
class ChatClient {
    constructor() {
        this.messageQueue = [];
        this.isOnline = navigator.onLine;
        window.addEventListener('online', () => this.onOnline());
        window.addEventListener('offline', () => this.onOffline());
    }
    
    sendMessage(content) {
        const localId = Date.now().toString();
        const messageObj = {
            type: 'message',
            content: content,
            local_id: localId,
            sent_at: new Date().toISOString()
        };
        
        if (this.isOnline && socket.readyState === WebSocket.OPEN) {
            // 즉시 전송
            socket.send(JSON.stringify(messageObj));
        } else {
            // 로컬에 저장
            this.messageQueue.push(messageObj);
            localStorage.setItem('unsent_messages', JSON.stringify(this.messageQueue));
            this.showOfflineIndicator();
        }
    }
    
    onOnline() {
        this.isOnline = true;
        // 로컬 큐의 메시지를 모두 전송
        const pending = JSON.parse(localStorage.getItem('unsent_messages') || '[]');
        pending.forEach(msg => {
            socket.send(JSON.stringify(msg));
        });
        localStorage.removeItem('unsent_messages');
        this.hideOfflineIndicator();
    }
    
    onOffline() {
        this.isOnline = false;
        this.showOfflineIndicator();
    }
}
```

이 기능이 없으면: 사용자가 메시지를 썼는데 네트워크가 끊기면 메시지가 사라집니다 (개발자가 전송 실패를 감지하지 못한 경우). 이는 최악의 UX입니다.

### 4. 메시지 로딩 최적화와 페이지네이션

채팅이 오래될수록 메시지는 수천, 수만 개가 됩니다. 모든 메시지를 메모리에 로드하면 앱이 느려집니다. **가상 스크롤**을 사용하여 보이는 메시지만 렌더링해야 합니다.

```python
# 백엔드: 커서 기반 페이지네이션
@api.get("/rooms/{room_id}/messages")
def get_messages(request, room_id: int, limit: int = 30, before: int = None):
    room = ChatRoom.objects.get(id=room_id)
    
    query = Message.objects.filter(room=room)
    
    # before 파라미터: 이 메시지 ID 이전의 메시지들을 로드
    if before:
        query = query.filter(id__lt=before)
    
    messages = list(query.order_by('-created_at')[:limit])
    
    return {
        "messages": [MessageSchema.from_orm(m) for m in reversed(messages)],
        "older_cursor": messages[0].id if messages else None
    }
```

**클라이언트: Intersection Observer를 활용한 가상 스크롤**:
```javascript
class VirtualChatScroll {
    constructor(container) {
        this.container = container;
        this.observedElements = new Map();
        this.setupObserver();
    }
    
    setupObserver() {
        // 화면에서 벗어난 메시지 DOM 제거
        this.observer = new IntersectionObserver(
            (entries) => {
                entries.forEach(entry => {
                    if (!entry.isIntersecting) {
                        // 화면에서 벗어났으면 DOM에서 제거 (데이터는 메모리에 유지)
                        entry.target.remove();
                    }
                });
            },
            {rootMargin: '200px'}  // 스크롤 여유 200px
        );
    }
    
    addMessage(message) {
        if (this.container.children.length > 500) {
            // 메시지가 500개를 넘으면 가장 오래된 것부터 제거
            const oldMessages = this.container.querySelectorAll('[data-message-id]');
            oldMessages[0]?.remove();
        }
        
        const el = this.createMessageElement(message);
        this.container.appendChild(el);
        this.observer.observe(el);
    }
}
```

---

## 🔧 실제 구현: 완전한 예제 코드

지금까지의 모든 개념을 통합한 완전한 모듈을 만들어봅시다.

```python
# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class ChatRoom(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    
    def __str__(self):
        return self.name

class Message(models.Model):
    STATUS_CHOICES = [
        ('pending', '대기중'),
        ('sent', '전송됨'),
        ('read', '읽음'),
    ]
    
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['room', 'created_at']),
        ]

# schemas.py (Ninja)
from ninja import Schema

class MessageSchema(Schema):
    id: int
    sender_id: int
    content: str
    status: str
    created_at: str

class CreateMessageSchema(Schema):
    content: str
    room_id: int
    local_id: str = None  # 클라이언트 로컬 ID

# api.py (Ninja)
from ninja import Router
from django.shortcuts import get_object_or_404

router = Router()

@router.post("/messages/")
def create_message(request, data: CreateMessageSchema):
    room = get_object_or_404(ChatRoom, id=data.room_id)
    
    message = Message.objects.create(
        room=room,
        sender=request.user,
        content=data.content,
        status='pending'
    )
    
    return {
        "message_id": message.id,
        "local_id": data.local_id,
        "status": "pending"
    }

@router.get("/rooms/{room_id}/messages/")
def get_messages(request, room_id: int, limit: int = 30, before: int = None):
    room = get_object_or_404(ChatRoom, id=room_id)
    query = Message.objects.filter(room=room)
    
    if before:
        query = query.filter(id__lt=before)
    
    messages = list(query.order_by('-created_at')[:limit])
    
    return {
        "messages": [MessageSchema.from_orm(m) for m in reversed(messages)],
        "older_cursor": messages[0].id if messages else None
    }

# consumers.py (Channels)
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_room_{self.room_id}'
        self.user = self.scope['user']
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # 온라인 상태 브로드캐스트
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_status",
                "user_id": self.user.id,
                "status": "online"
            }
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "user_id": self.user.id,
                "status": "offline"
            }
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            
            if data.get('type') == 'message':
                message = await self.save_message(data['content'])
                
                # ACK 전송
                await self.send(json.dumps({
                    "type": "message_ack",
                    "message_id": message.id,
                    "local_id": data.get('local_id'),
                    "status": "pending"
                }))
                
                # 다른 사용자에게 전송
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message",
                        "message_id": message.id,
                        "sender_id": self.user.id,
                        "content": message.content,
                        "created_at": message.created_at.isoformat()
                    }
                )
            
            elif data.get('type') == 'typing':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "user_typing",
                        "user_id": self.user.id,
                        "user_name": self.user.get_full_name()
                    }
                )
        
        except json.JSONDecodeError:
            await self.send(json.dumps({"error": "Invalid JSON"}))

    async def chat_message(self, event):
        await self.send(json.dumps({
            "type": "message",
            "message_id": event['message_id'],
            "sender_id": event['sender_id'],
            "content": event['content'],
            "created_at": event['created_at']
        }))

    async def user_status(self, event):
        await self.send(json.dumps({
            "type": "user_status",
            "user_id": event['user_id'],
            "status": event['status']
        }))

    async def user_typing(self, event):
        await self.send(json.dumps({
            "type": "typing",
            "user_id": event['user_id'],
            "user_name": event['user_name']
        }))

    @database_sync_to_async
    def save_message(self, content):
        return Message.objects.create(
            room_id=self.room_id,
            sender=self.user,
            content=content,
            status='pending'
        )
```

---

## 🎯 배포 시 필수 확인사항

마지막으로, 프로덕션 환경에서 꼭 확인해야 할 사항들을 정리했습니다.

### 1. Redis 설정 (메시지 큐 및 캐시)

```python
# settings.py
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
            'capacity': 10000,
            'expiry': 10,
        },
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### 2. ASGI 설정 (프로덕션 준비)

```python
# asgi.py
import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.urls import path
from apps.chat.consumers import ChatConsumer

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter([
            path('ws/chat/<int:room_id>/', ChatConsumer.as_asgi()),
        ])
    ),
})
```

### 3. Nginx 설정 (WebSocket 프록시)

```nginx
upstream django_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name example.com;
    
    location / {
        proxy_pass http://django_app;
    }
    
    location /ws/ {
        proxy_pass http://django_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
    }
}
```

---

## 📝 결론

Django-Ninja와 Channels를 조합하면 **REST API의 단순함과 WebSocket의 실시간성을 모두 활용**할 수 있습니다. 하지만 이 기술스택은 도구일 뿐, 진정한 중요성은 **사용자 경험**에 있습니다.

- **빠른 메시지 전송**: 사용자는 지연을 느끼면 서비스를 떠난다
- **신뢰성**: 메시지 손실은 절대 용인할 수 없다
- **자연스러움**: 타이핑 표시, 읽음 표시 같은 작은 기능들이 크다
- **복원력**: 네트워크가 끊겨도 자동으로 복구되어야 한다

이 네 가지를 항상 명심하고 개발한다면, KakaoTalk 같은 훌륭한 채팅 앱을 만들 수 있습니다. 행운을 빕니다!
