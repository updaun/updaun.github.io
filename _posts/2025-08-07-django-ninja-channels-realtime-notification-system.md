---
layout: post
title: "Django-Ninja + Django Channels로 실시간 알림 시스템 구축하기"
date: 2025-08-07 10:00:00 +0900
categories: [Django, Python, WebSocket, Real-time]
tags: [Django, Django-Ninja, Django-Channels, WebSocket, Real-time, Notification, API, Async, ASGI, Redis]
---

실시간 웹 애플리케이션의 필수 기능 중 하나인 알림 시스템을 구축해보겠습니다. Django-Ninja로 강력한 API를 만들고, Django Channels로 실시간 WebSocket 통신을 구현하여 사용자에게 즉시 알림을 전달하는 시스템을 단계별로 구현해보겠습니다.

## 🚀 프로젝트 개요

### 구현할 기능
- **실시간 알림 전송**: 특정 이벤트 발생 시 실시간으로 클라이언트에게 알림
- **RESTful API**: Django-Ninja를 활용한 알림 관리 API
- **WebSocket 연결**: Django Channels를 통한 양방향 실시간 통신
- **알림 타입 분류**: 다양한 종류의 알림 처리
- **사용자별 알림**: 개인화된 알림 시스템

### 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Django-Ninja  │    │  Django Channels│
│   (JavaScript)  │◄──►│      API        │◄──►│   WebSocket     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                        ┌─────────────────┐    ┌─────────────────┐
                        │    Database     │    │      Redis      │
                        │   (Postgres)    │    │   (Channel Layer)│
                        └─────────────────┘    └─────────────────┘
```

## 📋 환경 설정 및 설치

### 1. 필요한 패키지 설치

```bash
# 기본 Django 및 필수 패키지
pip install django
pip install django-ninja
pip install channels[daphne]
pip install channels-redis
pip install redis

# 데이터베이스 (PostgreSQL 사용 시)
pip install psycopg2-binary

# 개발 도구
pip install python-dotenv
```

### 2. Django 프로젝트 생성 및 기본 설정

```bash
# 프로젝트 생성
django-admin startproject notification_system
cd notification_system
python manage.py startapp notifications
python manage.py startapp api
```

### 3. settings.py 설정

```python
# settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Django Apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'channels',
    
    # Local apps
    'notifications',
    'api',
]

# Channels 설정
ASGI_APPLICATION = 'notification_system.asgi.application'

# Channel layers (Redis)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'notification_db',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Redis 설정 (추가 캐시 용도)
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

### 4. ASGI 설정

```python
# asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_system.settings')

django_asgi_app = get_asgi_application()

from notifications.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
```

## 🗃️ 데이터베이스 모델 설계

### notifications/models.py

```python
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class NotificationType(models.TextChoices):
    INFO = 'info', 'Information'
    SUCCESS = 'success', 'Success'
    WARNING = 'warning', 'Warning'
    ERROR = 'error', 'Error'
    MESSAGE = 'message', 'Message'
    SYSTEM = 'system', 'System'

class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO
    )
    
    # 메타데이터
    data = models.JSONField(default=dict, blank=True)
    
    # 상태 관리
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # 선택적 링크
    action_url = models.URLField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

class NotificationSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # 알림 타입별 설정
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    realtime_notifications = models.BooleanField(default=True)
    
    # 알림 타입별 세부 설정
    info_enabled = models.BooleanField(default=True)
    success_enabled = models.BooleanField(default=True)
    warning_enabled = models.BooleanField(default=True)
    error_enabled = models.BooleanField(default=True)
    message_enabled = models.BooleanField(default=True)
    system_enabled = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Settings for {self.user.username}"
```

## 🔌 Django Channels WebSocket Consumer

### notifications/consumers.py

```python
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Notification, NotificationSettings

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 사용자 인증 확인
        if self.scope["user"].is_anonymous:
            await self.close()
            return
        
        self.user = self.scope["user"]
        self.user_group_name = f"user_{self.user.id}"
        
        # 그룹에 조인
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # 연결 시 읽지 않은 알림 개수 전송
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'unread_count': unread_count,
            'message': f'Connected as {self.user.username}'
        }))

    async def disconnect(self, close_code):
        # 그룹에서 제거
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'mark_as_read':
                notification_id = text_data_json.get('notification_id')
                await self.mark_notification_as_read(notification_id)
            
            elif message_type == 'get_notifications':
                notifications = await self.get_recent_notifications()
                await self.send(text_data=json.dumps({
                    'type': 'notifications_list',
                    'notifications': notifications
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    # 새 알림 수신 핸들러
    async def notification_message(self, event):
        # 사용자 설정 확인
        settings = await self.get_notification_settings()
        
        if not settings.realtime_notifications:
            return
        
        notification_type = event['notification']['notification_type']
        if not await self.is_notification_type_enabled(settings, notification_type):
            return
        
        # 클라이언트에게 알림 전송
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event['notification']
        }))

    # 데이터베이스 작업 메서드들
    @database_sync_to_async
    def get_unread_count(self):
        return Notification.objects.filter(
            recipient=self.user, 
            is_read=False
        ).count()

    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=self.user
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False

    @database_sync_to_async
    def get_recent_notifications(self):
        notifications = Notification.objects.filter(
            recipient=self.user
        ).order_by('-created_at')[:20]
        
        return [
            {
                'id': str(notification.id),
                'title': notification.title,
                'message': notification.message,
                'notification_type': notification.notification_type,
                'is_read': notification.is_read,
                'created_at': notification.created_at.isoformat(),
                'action_url': notification.action_url,
                'data': notification.data,
            }
            for notification in notifications
        ]

    @database_sync_to_async
    def get_notification_settings(self):
        settings, created = NotificationSettings.objects.get_or_create(
            user=self.user
        )
        return settings

    @database_sync_to_async
    def is_notification_type_enabled(self, settings, notification_type):
        type_mapping = {
            'info': settings.info_enabled,
            'success': settings.success_enabled,
            'warning': settings.warning_enabled,
            'error': settings.error_enabled,
            'message': settings.message_enabled,
            'system': settings.system_enabled,
        }
        return type_mapping.get(notification_type, True)
```

### notifications/routing.py

```python
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
```

## 🚀 Django-Ninja API 구현

### api/schemas.py

```python
from ninja import Schema, ModelSchema
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from notifications.models import Notification, NotificationType

class NotificationCreateSchema(Schema):
    title: str
    message: str
    notification_type: NotificationType = NotificationType.INFO
    action_url: Optional[str] = None
    data: Optional[dict] = {}

class NotificationResponseSchema(ModelSchema):
    class Config:
        model = Notification
        model_fields = [
            'id', 'title', 'message', 'notification_type',
            'is_read', 'created_at', 'action_url', 'data'
        ]

class NotificationListSchema(Schema):
    notifications: List[NotificationResponseSchema]
    unread_count: int
    total_count: int

class NotificationSettingsSchema(Schema):
    email_notifications: bool = True
    push_notifications: bool = True
    realtime_notifications: bool = True
    info_enabled: bool = True
    success_enabled: bool = True
    warning_enabled: bool = True
    error_enabled: bool = True
    message_enabled: bool = True
    system_enabled: bool = True

class BulkNotificationSchema(Schema):
    user_ids: List[int]
    title: str
    message: str
    notification_type: NotificationType = NotificationType.INFO
    action_url: Optional[str] = None
    data: Optional[dict] = {}
```

### api/views.py

```python
from ninja import NinjaAPI, Query
from ninja.security import django_auth
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db import transaction
from typing import List, Optional
from uuid import UUID

from notifications.models import Notification, NotificationSettings
from notifications.services import NotificationService
from .schemas import (
    NotificationCreateSchema, 
    NotificationResponseSchema,
    NotificationListSchema,
    NotificationSettingsSchema,
    BulkNotificationSchema
)

api = NinjaAPI(title="Notification API", version="1.0.0")

@api.get("/notifications", response=NotificationListSchema, auth=django_auth)
def list_notifications(
    request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    unread_only: bool = Query(False)
):
    """사용자의 알림 목록 조회"""
    queryset = Notification.objects.filter(recipient=request.user)
    
    if unread_only:
        queryset = queryset.filter(is_read=False)
    
    total_count = queryset.count()
    unread_count = Notification.objects.filter(
        recipient=request.user, 
        is_read=False
    ).count()
    
    notifications = queryset.order_by('-created_at')[offset:offset + limit]
    
    return {
        "notifications": notifications,
        "unread_count": unread_count,
        "total_count": total_count
    }

@api.post("/notifications", response=NotificationResponseSchema, auth=django_auth)
def create_notification(request, payload: NotificationCreateSchema):
    """새 알림 생성 (자신에게)"""
    notification = NotificationService.create_notification(
        recipient=request.user,
        title=payload.title,
        message=payload.message,
        notification_type=payload.notification_type,
        action_url=payload.action_url,
        data=payload.data
    )
    return notification

@api.post("/notifications/bulk", auth=django_auth)
def create_bulk_notifications(request, payload: BulkNotificationSchema):
    """여러 사용자에게 일괄 알림 전송"""
    if not request.user.is_staff:
        return {"error": "Permission denied"}, 403
    
    users = User.objects.filter(id__in=payload.user_ids)
    notifications = []
    
    with transaction.atomic():
        for user in users:
            notification = NotificationService.create_notification(
                recipient=user,
                title=payload.title,
                message=payload.message,
                notification_type=payload.notification_type,
                action_url=payload.action_url,
                data=payload.data
            )
            notifications.append(notification)
    
    return {
        "message": f"Created {len(notifications)} notifications",
        "count": len(notifications)
    }

@api.put("/notifications/{notification_id}/read", auth=django_auth)
def mark_as_read(request, notification_id: UUID):
    """알림을 읽음으로 표시"""
    notification = get_object_or_404(
        Notification, 
        id=notification_id, 
        recipient=request.user
    )
    notification.mark_as_read()
    return {"message": "Notification marked as read"}

@api.put("/notifications/mark-all-read", auth=django_auth)
def mark_all_as_read(request):
    """모든 알림을 읽음으로 표시"""
    updated_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(is_read=True)
    
    return {"message": f"Marked {updated_count} notifications as read"}

@api.delete("/notifications/{notification_id}", auth=django_auth)
def delete_notification(request, notification_id: UUID):
    """알림 삭제"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user
    )
    notification.delete()
    return {"message": "Notification deleted"}

@api.get("/notifications/settings", response=NotificationSettingsSchema, auth=django_auth)
def get_notification_settings(request):
    """알림 설정 조회"""
    settings, created = NotificationSettings.objects.get_or_create(
        user=request.user
    )
    return settings

@api.put("/notifications/settings", response=NotificationSettingsSchema, auth=django_auth)
def update_notification_settings(request, payload: NotificationSettingsSchema):
    """알림 설정 업데이트"""
    settings, created = NotificationSettings.objects.get_or_create(
        user=request.user
    )
    
    for field, value in payload.dict().items():
        setattr(settings, field, value)
    
    settings.save()
    return settings

@api.get("/notifications/unread-count", auth=django_auth)
def get_unread_count(request):
    """읽지 않은 알림 개수 조회"""
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    return {"unread_count": count}
```

## 🔧 알림 서비스 구현

### notifications/services.py

```python
import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from typing import Optional, Dict, Any

from .models import Notification, NotificationType, NotificationSettings

class NotificationService:
    
    @staticmethod
    def create_notification(
        recipient: User,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        action_url: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        send_realtime: bool = True
    ) -> Notification:
        """알림 생성 및 실시간 전송"""
        
        # 알림 생성
        notification = Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            action_url=action_url,
            data=data or {}
        )
        
        # 실시간 전송
        if send_realtime:
            NotificationService.send_realtime_notification(notification)
        
        return notification
    
    @staticmethod
    def send_realtime_notification(notification: Notification):
        """WebSocket을 통한 실시간 알림 전송"""
        channel_layer = get_channel_layer()
        user_group_name = f"user_{notification.recipient.id}"
        
        notification_data = {
            'id': str(notification.id),
            'title': notification.title,
            'message': notification.message,
            'notification_type': notification.notification_type,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
            'action_url': notification.action_url,
            'data': notification.data,
        }
        
        async_to_sync(channel_layer.group_send)(
            user_group_name,
            {
                'type': 'notification_message',
                'notification': notification_data
            }
        )
        
        # 전송 상태 업데이트
        notification.is_sent = True
        notification.save(update_fields=['is_sent'])
    
    @staticmethod
    def create_system_notification(
        title: str,
        message: str,
        user_ids: Optional[list] = None,
        notification_type: NotificationType = NotificationType.SYSTEM
    ):
        """시스템 알림 생성 (모든 사용자 또는 특정 사용자들)"""
        
        if user_ids:
            users = User.objects.filter(id__in=user_ids)
        else:
            users = User.objects.filter(is_active=True)
        
        notifications = []
        for user in users:
            notification = NotificationService.create_notification(
                recipient=user,
                title=title,
                message=message,
                notification_type=notification_type
            )
            notifications.append(notification)
        
        return notifications
    
    @staticmethod
    def notify_user_action(
        actor: User,
        recipient: User,
        action: str,
        object_name: str,
        action_url: Optional[str] = None
    ):
        """사용자 액션에 대한 알림 (좋아요, 댓글 등)"""
        
        title = f"{actor.username}님이 {action}했습니다"
        message = f"{actor.username}님이 당신의 {object_name}에 {action}했습니다."
        
        return NotificationService.create_notification(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=NotificationType.INFO,
            action_url=action_url,
            data={
                'actor_id': actor.id,
                'actor_username': actor.username,
                'action': action,
                'object_name': object_name
            }
        )
```

## 🌐 프론트엔드 구현

### static/js/notifications.js

```javascript
class NotificationManager {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        
        this.init();
    }
    
    init() {
        this.connect();
        this.setupUI();
        this.loadNotifications();
    }
    
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
        
        try {
            this.socket = new WebSocket(wsUrl);
            this.setupSocketHandlers();
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.handleReconnect();
        }
    }
    
    setupSocketHandlers() {
        this.socket.onopen = (event) => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.updateConnectionStatus(true);
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.socket.onclose = (event) => {
            console.log('WebSocket disconnected');
            this.isConnected = false;
            this.updateConnectionStatus(false);
            
            if (!event.wasClean) {
                this.handleReconnect();
            }
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'connection_established':
                this.updateUnreadCount(data.unread_count);
                this.showToast('연결되었습니다', 'success');
                break;
                
            case 'new_notification':
                this.displayNotification(data.notification);
                this.playNotificationSound();
                this.updateUnreadCount();
                break;
                
            case 'notifications_list':
                this.displayNotificationsList(data.notifications);
                break;
                
            case 'error':
                console.error('Notification error:', data.message);
                break;
        }
    }
    
    displayNotification(notification) {
        // 브라우저 알림 표시
        if (Notification.permission === 'granted') {
            new Notification(notification.title, {
                body: notification.message,
                icon: '/static/images/notification-icon.png',
                tag: notification.id
            });
        }
        
        // 인앱 토스트 알림
        this.showToast(notification.title, notification.notification_type, notification.message);
        
        // 알림 목록에 추가
        this.addNotificationToList(notification);
    }
    
    showToast(title, type = 'info', message = '') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-header">
                <strong class="toast-title">${title}</strong>
                <button type="button" class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
            ${message ? `<div class="toast-body">${message}</div>` : ''}
        `;
        
        const container = document.getElementById('toast-container') || this.createToastContainer();
        container.appendChild(toast);
        
        // 자동 제거
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 5000);
    }
    
    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    }
    
    markAsRead(notificationId) {
        if (this.isConnected) {
            this.socket.send(JSON.stringify({
                type: 'mark_as_read',
                notification_id: notificationId
            }));
        }
        
        // API 호출로도 동기화
        fetch(`/api/notifications/${notificationId}/read`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            }
        });
    }
    
    loadNotifications() {
        fetch('/api/notifications?limit=20', {
            headers: {
                'Authorization': 'Bearer ' + this.getAuthToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            this.displayNotificationsList(data.notifications);
            this.updateUnreadCount(data.unread_count);
        })
        .catch(error => console.error('Failed to load notifications:', error));
    }
    
    setupUI() {
        // 브라우저 알림 권한 요청
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
        
        // 알림 벨 아이콘 클릭 이벤트
        const notificationBell = document.getElementById('notification-bell');
        if (notificationBell) {
            notificationBell.addEventListener('click', () => {
                this.toggleNotificationPanel();
            });
        }
    }
    
    toggleNotificationPanel() {
        const panel = document.getElementById('notification-panel');
        if (panel) {
            panel.classList.toggle('show');
            
            if (panel.classList.contains('show')) {
                this.requestNotifications();
            }
        }
    }
    
    requestNotifications() {
        if (this.isConnected) {
            this.socket.send(JSON.stringify({
                type: 'get_notifications'
            }));
        }
    }
    
    updateUnreadCount(count = null) {
        if (count === null) {
            // API에서 실시간 개수 가져오기
            fetch('/api/notifications/unread-count')
                .then(response => response.json())
                .then(data => {
                    this.updateUnreadCountDisplay(data.unread_count);
                });
        } else {
            this.updateUnreadCountDisplay(count);
        }
    }
    
    updateUnreadCountDisplay(count) {
        const badge = document.getElementById('unread-count-badge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }
        }
    }
    
    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectDelay * this.reconnectAttempts);
        } else {
            console.error('Max reconnection attempts reached');
            this.showToast('연결이 끊어졌습니다. 페이지를 새로고침해주세요.', 'error');
        }
    }
    
    playNotificationSound() {
        const audio = new Audio('/static/sounds/notification.mp3');
        audio.volume = 0.3;
        audio.play().catch(e => console.log('Cannot play notification sound:', e));
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
    
    getAuthToken() {
        // JWT 토큰이나 세션 기반 인증에 따라 구현
        return localStorage.getItem('auth_token') || '';
    }
}

// 페이지 로드 시 알림 매니저 초기화
document.addEventListener('DOMContentLoaded', () => {
    window.notificationManager = new NotificationManager();
});
```

### templates/notifications/notification_widget.html

```html
<!-- 알림 위젯 -->
<div class="notification-widget">
    <!-- 알림 벨 아이콘 -->
    <button id="notification-bell" class="notification-bell">
        <i class="fas fa-bell"></i>
        <span id="unread-count-badge" class="notification-badge" style="display: none;">0</span>
    </button>
    
    <!-- 알림 패널 -->
    <div id="notification-panel" class="notification-panel">
        <div class="notification-header">
            <h3>알림</h3>
            <button id="mark-all-read" class="btn btn-sm btn-outline-secondary">
                모두 읽음
            </button>
        </div>
        
        <div id="notification-list" class="notification-list">
            <!-- 알림 목록이 여기에 동적으로 추가됩니다 -->
        </div>
        
        <div class="notification-footer">
            <a href="/notifications/" class="btn btn-primary btn-sm">
                모든 알림 보기
            </a>
        </div>
    </div>
</div>

<!-- 연결 상태 표시 -->
<div id="connection-status" class="connection-status">
    <span class="status-indicator"></span>
    <span class="status-text">연결 중...</span>
</div>

<!-- 토스트 컨테이너 -->
<div id="toast-container" class="toast-container"></div>
```

### static/css/notifications.css

```css
/* 알림 위젯 스타일 */
.notification-widget {
    position: relative;
    display: inline-block;
}

.notification-bell {
    position: relative;
    background: none;
    border: none;
    font-size: 1.5rem;
    color: #6c757d;
    cursor: pointer;
    padding: 0.5rem;
    border-radius: 50%;
    transition: all 0.3s ease;
}

.notification-bell:hover {
    background-color: #f8f9fa;
    color: #495057;
}

.notification-badge {
    position: absolute;
    top: 0;
    right: 0;
    background-color: #dc3545;
    color: white;
    border-radius: 50%;
    width: 20px;
    height: 20px;
    font-size: 0.75rem;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
}

.notification-panel {
    position: absolute;
    top: 100%;
    right: 0;
    width: 350px;
    background: white;
    border: 1px solid #dee2e6;
    border-radius: 0.5rem;
    box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
    z-index: 1050;
    display: none;
    max-height: 500px;
    overflow-y: auto;
}

.notification-panel.show {
    display: block;
}

.notification-header {
    padding: 1rem;
    border-bottom: 1px solid #dee2e6;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.notification-header h3 {
    margin: 0;
    font-size: 1.1rem;
}

.notification-list {
    max-height: 300px;
    overflow-y: auto;
}

.notification-item {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #f8f9fa;
    cursor: pointer;
    transition: background-color 0.2s ease;
}

.notification-item:hover {
    background-color: #f8f9fa;
}

.notification-item.unread {
    background-color: #e3f2fd;
    border-left: 4px solid #2196f3;
}

.notification-title {
    font-weight: 600;
    margin-bottom: 0.25rem;
    font-size: 0.9rem;
}

.notification-message {
    color: #6c757d;
    font-size: 0.8rem;
    margin-bottom: 0.25rem;
}

.notification-time {
    color: #adb5bd;
    font-size: 0.75rem;
}

.notification-footer {
    padding: 0.75rem 1rem;
    border-top: 1px solid #dee2e6;
    text-align: center;
}

/* 토스트 알림 스타일 */
.toast-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1060;
}

.toast {
    background: white;
    border-radius: 0.5rem;
    box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.1);
    margin-bottom: 0.5rem;
    max-width: 300px;
    border-left: 4px solid;
    animation: slideInRight 0.3s ease;
}

.toast-info { border-left-color: #17a2b8; }
.toast-success { border-left-color: #28a745; }
.toast-warning { border-left-color: #ffc107; }
.toast-error { border-left-color: #dc3545; }

.toast-header {
    padding: 0.75rem 1rem 0.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.toast-title {
    font-weight: 600;
    font-size: 0.9rem;
}

.toast-close {
    background: none;
    border: none;
    font-size: 1.2rem;
    cursor: pointer;
    color: #6c757d;
}

.toast-body {
    padding: 0 1rem 0.75rem;
    font-size: 0.8rem;
    color: #6c757d;
}

/* 연결 상태 표시 */
.connection-status {
    position: fixed;
    bottom: 20px;
    left: 20px;
    background: white;
    padding: 0.5rem 1rem;
    border-radius: 2rem;
    box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.1);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8rem;
    z-index: 1000;
}

.status-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #6c757d;
}

.status-indicator.connected {
    background-color: #28a745;
}

.status-indicator.disconnected {
    background-color: #dc3545;
}

/* 애니메이션 */
@keyframes slideInRight {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

/* 반응형 디자인 */
@media (max-width: 768px) {
    .notification-panel {
        width: 90vw;
        right: -20px;
    }
    
    .toast-container {
        right: 10px;
        left: 10px;
    }
    
    .toast {
        max-width: none;
    }
}
```

## 🧪 사용 예제 및 테스트

### notifications/management/commands/test_notifications.py

```python
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from notifications.services import NotificationService
from notifications.models import NotificationType

class Command(BaseCommand):
    help = 'Test notification system'
    
    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, help='User ID to send notification to')
        parser.add_argument('--type', type=str, default='info', help='Notification type')
        parser.add_argument('--title', type=str, default='Test Notification', help='Notification title')
        parser.add_argument('--message', type=str, default='This is a test notification', help='Notification message')
    
    def handle(self, *args, **options):
        user_id = options['user_id']
        if not user_id:
            # 첫 번째 사용자에게 전송
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR('No users found'))
                return
        else:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User with ID {user_id} not found'))
                return
        
        # 알림 생성 및 전송
        notification = NotificationService.create_notification(
            recipient=user,
            title=options['title'],
            message=options['message'],
            notification_type=options['type'],
            action_url='https://example.com/test',
            data={'test': True}
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Notification sent to {user.username} (ID: {notification.id})'
            )
        )
```

### 사용 예제

```python
# views.py에서 알림 발송 예제
from notifications.services import NotificationService

# 1. 단일 사용자에게 알림
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # 좋아요 로직...
    
    # 포스트 작성자에게 알림
    NotificationService.notify_user_action(
        actor=request.user,
        recipient=post.author,
        action="좋아요를",
        object_name="포스트",
        action_url=f"/posts/{post.id}/"
    )

# 2. 시스템 알림 (모든 사용자)
def send_maintenance_notice():
    NotificationService.create_system_notification(
        title="시스템 점검 안내",
        message="오늘 밤 12시부터 2시까지 시스템 점검이 있습니다.",
        notification_type=NotificationType.WARNING
    )

# 3. 특정 사용자들에게 알림
def notify_premium_users():
    premium_user_ids = [1, 2, 3, 4, 5]
    NotificationService.create_system_notification(
        title="프리미엄 기능 업데이트",
        message="새로운 프리미엄 기능이 추가되었습니다!",
        user_ids=premium_user_ids,
        notification_type=NotificationType.SUCCESS
    )
```

## 🚀 배포 및 운영

### 1. 프로덕션 설정

```python
# settings.py (프로덕션)
import os

# Redis 설정 (클러스터 환경)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [
                (os.getenv('REDIS_HOST', 'localhost'), 6379),
            ],
            "capacity": 1500,
            "expiry": 60,
        },
    },
}

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'notifications.log',
        },
    },
    'loggers': {
        'notifications': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 2. Docker 설정

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "notification_system.asgi:application"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - redis
      - postgres
    environment:
      - REDIS_HOST=redis
      - DB_HOST=postgres
      
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
      
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: notification_db
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
```

### 3. 모니터링 및 성능 최적화

```python
# notifications/monitoring.py
import logging
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

logger = logging.getLogger('notifications')

class NotificationMetrics:
    
    @staticmethod
    def track_notification_sent(notification_type: str):
        """알림 전송 메트릭 추적"""
        key = f"notifications_sent_{notification_type}_{timezone.now().date()}"
        cache.set(key, cache.get(key, 0) + 1, 86400)  # 24시간
    
    @staticmethod
    def track_websocket_connection():
        """WebSocket 연결 메트릭"""
        key = f"ws_connections_{timezone.now().date()}"
        cache.set(key, cache.get(key, 0) + 1, 86400)
    
    @staticmethod
    def get_daily_metrics():
        """일일 메트릭 조회"""
        today = timezone.now().date()
        return {
            'notifications_sent': cache.get(f"notifications_sent_info_{today}", 0),
            'ws_connections': cache.get(f"ws_connections_{today}", 0),
            'db_queries': len(connection.queries),
        }
```

## 📈 성능 최적화 팁

### 1. 데이터베이스 최적화

```python
# 인덱스 추가 마이그레이션
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY idx_notifications_recipient_unread ON notifications_notification(recipient_id) WHERE is_read = false;",
            reverse_sql="DROP INDEX idx_notifications_recipient_unread;"
        ),
    ]
```

### 2. 캐싱 전략

```python
# notifications/cache.py
from django.core.cache import cache
from django.contrib.auth.models import User

class NotificationCache:
    
    @staticmethod
    def get_unread_count(user_id: int) -> int:
        key = f"unread_count_{user_id}"
        count = cache.get(key)
        
        if count is None:
            from .models import Notification
            count = Notification.objects.filter(
                recipient_id=user_id,
                is_read=False
            ).count()
            cache.set(key, count, 300)  # 5분 캐시
        
        return count
    
    @staticmethod
    def invalidate_unread_count(user_id: int):
        key = f"unread_count_{user_id}"
        cache.delete(key)
```

## 🎯 결론

Django-Ninja와 Django Channels를 결합한 실시간 알림 시스템을 구축해보았습니다. 이 시스템의 주요 특징은:

### ✅ 구현된 기능
- **실시간 WebSocket 통신**으로 즉시 알림 전달
- **RESTful API**를 통한 알림 관리
- **사용자별 개인화** 설정
- **다양한 알림 타입** 지원
- **확장 가능한 아키텍처**

### 🔧 확장 가능한 부분
- **푸시 알림** (FCM, APNs 연동)
- **이메일 알림** (Celery + 이메일 서비스)
- **알림 템플릿** 시스템
- **A/B 테스트** 기능
- **분석 및 메트릭** 대시보드

### 💡 운영 시 고려사항
- **Redis 클러스터링**으로 고가용성 확보
- **WebSocket 연결 관리** 및 메모리 최적화
- **데이터베이스 쿼리 최적화** 및 캐싱
- **에러 핸들링** 및 모니터링

이 실시간 알림 시스템을 통해 사용자 참여도를 높이고, 중요한 이벤트를 놓치지 않도록 도와주는 견고한 서비스를 구축할 수 있습니다.
