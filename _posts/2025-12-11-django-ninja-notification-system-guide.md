---
layout: post
title: "Django Ninja로 구현하는 실시간 알림 시스템 완벽 가이드"
date: 2025-12-11 09:00:00 +0900
categories: [Django, Backend, Real-time]
tags: [django-ninja, notification, websocket, celery, event-driven, redis, channels]
description: "Django Ninja를 활용하여 이벤트 기반 실시간 알림 시스템을 구축하는 방법을 단계별로 알아봅니다. 주문, 댓글, 좋아요 등 다양한 이벤트에 대한 알림 발송 구조를 구현합니다."
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-12-11-django-ninja-notification-system-guide.webp"
---

## 목차
1. [알림 시스템 개요](#1-알림-시스템-개요)
2. [프로젝트 설정 및 모델 설계](#2-프로젝트-설정-및-모델-설계)
3. [이벤트 기반 알림 발송 구조](#3-이벤트-기반-알림-발송-구조)
4. [Django Ninja API 구현](#4-django-ninja-api-구현)
5. [실시간 알림 (WebSocket)](#5-실시간-알림-websocket)
6. [푸시 알림 통합](#6-푸시-알림-통합)
7. [이메일/SMS 알림](#7-이메일sms-알림)
8. [알림 템플릿 시스템](#8-알림-템플릿-시스템)
9. [프로덕션 최적화](#9-프로덕션-최적화)
10. [실전 예제](#10-실전-예제)

---

## 1. 알림 시스템 개요

### 1.1 왜 이벤트 기반 알림 시스템이 필요한가?

현대적인 웹 애플리케이션에서 사용자 경험을 향상시키는 핵심 요소 중 하나는 **적시에 전달되는 알림**입니다. 주문이 완료되었을 때, 누군가 내 게시글에 댓글을 달았을 때, 새로운 메시지가 도착했을 때 - 이러한 순간들에 사용자에게 즉각적으로 알려주는 것이 중요합니다.

하지만 단순히 알림을 보내는 것만으로는 부족합니다. 시스템이 커질수록 다음과 같은 요구사항이 생깁니다:

- **다양한 이벤트 처리**: 주문, 결제, 댓글, 좋아요, 팔로우 등 수십 가지 이벤트
- **다중 채널 지원**: 인앱 알림, 푸시 알림, 이메일, SMS 동시 발송
- **성능과 확장성**: 수천 명의 사용자에게 동시에 알림을 보낼 수 있어야 함
- **유연성**: 새로운 이벤트 타입을 쉽게 추가할 수 있어야 함
- **개인화**: 사용자별 알림 설정 존중 (알림 끄기/켜기)

이번 가이드에서는 Django Ninja를 활용하여 **이벤트 기반 아키텍처**로 확장 가능한 알림 시스템을 구축하는 방법을 단계별로 살펴보겠습니다.

### 1.2 시스템 아키텍처 개요

우리가 구축할 알림 시스템의 전체 구조는 다음과 같습니다:

```
┌─────────────────┐
│  Django Views   │
│  (이벤트 발생)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Event Dispatcher│ ◄── Signal 또는 직접 호출
│  (이벤트 중개)   │
└────────┬────────┘
         │
         ├─────────────────┬─────────────────┬──────────────┐
         ▼                 ▼                 ▼              ▼
┌────────────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────┐
│ In-App Notif   │ │ Push Notif   │ │   Email     │ │   SMS    │
│   (DB 저장)     │ │  (FCM/APNs)  │ │  (SendGrid) │ │ (Twilio) │
└────────────────┘ └──────────────┘ └─────────────┘ └──────────┘
         │                                                 
         ▼                                                 
┌────────────────┐                                        
│   WebSocket    │                                        
│ (실시간 전송)   │                                        
└────────────────┘                                        
```

**핵심 컴포넌트:**

1. **Event Dispatcher**: 이벤트를 받아 적절한 알림 핸들러로 라우팅
2. **Notification Model**: DB에 알림 저장 (읽음/안읽음 상태 관리)
3. **Notification Handlers**: 각 채널별 알림 발송 로직
4. **WebSocket Layer**: Django Channels로 실시간 알림 전송
5. **Celery Tasks**: 비동기 알림 발송 (이메일, SMS 등)

### 1.3 주요 기능

이번 가이드에서 구현할 기능들:

✅ **인앱 알림**
- 읽음/안읽음 상태 관리
- 실시간 업데이트 (WebSocket)
- 알림 목록 조회 및 페이지네이션
- 일괄 읽음 처리

✅ **이벤트 타입별 알림**
- 주문 완료/배송 시작/배송 완료
- 댓글/대댓글 작성
- 좋아요/북마크
- 팔로우/언팔로우
- 시스템 공지

✅ **다중 채널 지원**
- 푸시 알림 (FCM)
- 이메일 알림
- SMS 알림 (선택적)

✅ **사용자 설정**
- 알림 타입별 on/off 설정
- 채널별 알림 수신 설정
- 조용한 시간 설정 (DND)

✅ **성능 최적화**
- Celery를 통한 비동기 처리
- Redis 캐싱
- 배치 알림 발송

---

## 2. 프로젝트 설정 및 모델 설계

### 2.1 필수 패키지 설치

먼저 프로젝트에 필요한 패키지들을 설치합니다.

```bash
# 기본 패키지
pip install django django-ninja

# 비동기 작업 처리
pip install celery redis

# 실시간 통신
pip install channels channels-redis daphne

# 푸시 알림
pip install firebase-admin

# 이메일 발송
pip install sendgrid

# 유틸리티
pip install python-decouple django-cors-headers
```

**requirements.txt:**

```txt
Django==5.0.0
django-ninja==1.1.0
celery==5.3.4
redis==5.0.1
channels==4.0.0
channels-redis==4.1.0
daphne==4.0.0
firebase-admin==6.3.0
sendgrid==6.11.0
python-decouple==3.8
django-cors-headers==4.3.1
```

### 2.2 Django 설정

**settings.py 기본 설정:**

```python
# settings.py
import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# Django Ninja 설정
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'corsheaders',
    'channels',
    
    # Local apps
    'notifications',
    'accounts',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Channels 설정
ASGI_APPLICATION = 'config.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(config('REDIS_HOST', default='127.0.0.1'), 6379)],
        },
    },
}

# Celery 설정
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'

# Firebase 설정 (푸시 알림)
FIREBASE_CREDENTIALS_PATH = config('FIREBASE_CREDENTIALS_PATH', default='')

# SendGrid 설정 (이메일)
SENDGRID_API_KEY = config('SENDGRID_API_KEY', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@example.com')

# CORS 설정
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
]
```

### 2.3 알림 모델 설계

알림 시스템의 핵심이 되는 데이터 모델을 설계합니다.

**notifications/models.py:**

```python
# notifications/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

User = get_user_model()


class NotificationType(models.TextChoices):
    """알림 타입 정의"""
    # 주문 관련
    ORDER_CREATED = 'ORDER_CREATED', '주문 완료'
    ORDER_CONFIRMED = 'ORDER_CONFIRMED', '주문 확인'
    ORDER_SHIPPED = 'ORDER_SHIPPED', '배송 시작'
    ORDER_DELIVERED = 'ORDER_DELIVERED', '배송 완료'
    ORDER_CANCELLED = 'ORDER_CANCELLED', '주문 취소'
    
    # 소셜 관련
    COMMENT_CREATED = 'COMMENT_CREATED', '댓글 작성'
    COMMENT_REPLY = 'COMMENT_REPLY', '대댓글 작성'
    POST_LIKED = 'POST_LIKED', '게시글 좋아요'
    COMMENT_LIKED = 'COMMENT_LIKED', '댓글 좋아요'
    USER_FOLLOWED = 'USER_FOLLOWED', '팔로우'
    
    # 결제 관련
    PAYMENT_COMPLETED = 'PAYMENT_COMPLETED', '결제 완료'
    PAYMENT_FAILED = 'PAYMENT_FAILED', '결제 실패'
    REFUND_COMPLETED = 'REFUND_COMPLETED', '환불 완료'
    
    # 시스템 관련
    SYSTEM_ANNOUNCEMENT = 'SYSTEM_ANNOUNCEMENT', '시스템 공지'
    ACCOUNT_VERIFIED = 'ACCOUNT_VERIFIED', '계정 인증'
    PASSWORD_CHANGED = 'PASSWORD_CHANGED', '비밀번호 변경'


class NotificationChannel(models.TextChoices):
    """알림 채널"""
    IN_APP = 'IN_APP', '인앱 알림'
    PUSH = 'PUSH', '푸시 알림'
    EMAIL = 'EMAIL', '이메일'
    SMS = 'SMS', 'SMS'


class Notification(models.Model):
    """알림 모델"""
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='수신자'
    )
    
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        verbose_name='알림 타입'
    )
    
    title = models.CharField(max_length=255, verbose_name='제목')
    message = models.TextField(verbose_name='내용')
    
    # Generic Foreign Key: 모든 모델과 연결 가능
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # 추가 데이터 (JSON)
    extra_data = models.JSONField(default=dict, blank=True)
    
    # 상태
    is_read = models.BooleanField(default=False, verbose_name='읽음 여부')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='읽은 시간')
    
    # 액션 URL
    action_url = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='액션 URL'
    )
    
    # 발송 채널
    channels = models.JSONField(
        default=list,
        verbose_name='발송 채널',
        help_text='예: ["IN_APP", "PUSH", "EMAIL"]'
    )
    
    # 발송 상태
    sent_at = models.DateTimeField(null=True, blank=True)
    push_sent = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"{self.recipient.username} - {self.get_notification_type_display()}"
    
    def mark_as_read(self):
        """읽음 처리"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at', 'updated_at'])
    
    def mark_as_unread(self):
        """안읽음 처리"""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at', 'updated_at'])
    
    def to_dict(self):
        """딕셔너리 변환 (WebSocket 전송용)"""
        return {
            'id': self.id,
            'type': self.notification_type,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'action_url': self.action_url,
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat(),
        }


class UserNotificationSettings(models.Model):
    """사용자별 알림 설정"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_settings'
    )
    
    # 알림 타입별 설정
    order_notifications = models.BooleanField(default=True, verbose_name='주문 알림')
    social_notifications = models.BooleanField(default=True, verbose_name='소셜 알림')
    payment_notifications = models.BooleanField(default=True, verbose_name='결제 알림')
    system_notifications = models.BooleanField(default=True, verbose_name='시스템 알림')
    
    # 채널별 설정
    in_app_enabled = models.BooleanField(default=True, verbose_name='인앱 알림')
    push_enabled = models.BooleanField(default=True, verbose_name='푸시 알림')
    email_enabled = models.BooleanField(default=True, verbose_name='이메일 알림')
    sms_enabled = models.BooleanField(default=False, verbose_name='SMS 알림')
    
    # 조용한 시간 (Do Not Disturb)
    dnd_enabled = models.BooleanField(default=False, verbose_name='방해 금지 모드')
    dnd_start_time = models.TimeField(null=True, blank=True, verbose_name='방해 금지 시작')
    dnd_end_time = models.TimeField(null=True, blank=True, verbose_name='방해 금지 종료')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_notification_settings'
    
    def __str__(self):
        return f"{self.user.username} 알림 설정"
    
    def is_dnd_active(self):
        """현재 방해 금지 모드 활성 여부"""
        if not self.dnd_enabled or not self.dnd_start_time or not self.dnd_end_time:
            return False
        
        now = timezone.now().time()
        if self.dnd_start_time < self.dnd_end_time:
            return self.dnd_start_time <= now <= self.dnd_end_time
        else:  # 자정을 넘어가는 경우
            return now >= self.dnd_start_time or now <= self.dnd_end_time
    
    def should_send_notification(self, notification_type, channel):
        """해당 알림을 발송해야 하는지 확인"""
        # DND 모드 확인
        if self.is_dnd_active() and channel in ['PUSH', 'SMS']:
            return False
        
        # 채널 설정 확인
        if channel == NotificationChannel.IN_APP and not self.in_app_enabled:
            return False
        elif channel == NotificationChannel.PUSH and not self.push_enabled:
            return False
        elif channel == NotificationChannel.EMAIL and not self.email_enabled:
            return False
        elif channel == NotificationChannel.SMS and not self.sms_enabled:
            return False
        
        # 알림 타입별 설정 확인
        if notification_type.startswith('ORDER_'):
            return self.order_notifications
        elif notification_type in ['COMMENT_CREATED', 'COMMENT_REPLY', 'POST_LIKED', 
                                   'COMMENT_LIKED', 'USER_FOLLOWED']:
            return self.social_notifications
        elif notification_type.startswith('PAYMENT_') or notification_type.startswith('REFUND_'):
            return self.payment_notifications
        elif notification_type.startswith('SYSTEM_'):
            return self.system_notifications
        
        return True


class DeviceToken(models.Model):
    """푸시 알림용 디바이스 토큰"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='device_tokens'
    )
    
    PLATFORM_CHOICES = [
        ('ios', 'iOS'),
        ('android', 'Android'),
        ('web', 'Web'),
    ]
    
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    token = models.CharField(max_length=500, unique=True)
    
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'device_tokens'
        unique_together = ['user', 'platform', 'token']
    
    def __str__(self):
        return f"{self.user.username} - {self.platform}"
```

### 2.4 마이그레이션 생성 및 적용

모델을 정의했으니 마이그레이션을 생성하고 적용합니다.

```bash
# 마이그레이션 생성
python manage.py makemigrations notifications

# 마이그레이션 적용
python manage.py migrate notifications

# 슈퍼유저 생성 (테스트용)
python manage.py createsuperuser
```

**Admin 패널 등록 (notifications/admin.py):**

```python
# notifications/admin.py
from django.contrib import admin
from .models import Notification, UserNotificationSettings, DeviceToken


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'recipient', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['recipient__username', 'title', 'message']
    readonly_fields = ['created_at', 'updated_at', 'sent_at', 'read_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('recipient', 'notification_type', 'title', 'message')
        }),
        ('연결 정보', {
            'fields': ('content_type', 'object_id', 'action_url', 'extra_data')
        }),
        ('상태', {
            'fields': ('is_read', 'read_at', 'channels', 'push_sent', 'email_sent', 'sms_sent')
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at', 'sent_at')
        }),
    )


@admin.register(UserNotificationSettings)
class UserNotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'in_app_enabled', 'push_enabled', 'email_enabled', 'dnd_enabled']
    list_filter = ['in_app_enabled', 'push_enabled', 'email_enabled', 'dnd_enabled']
    search_fields = ['user__username', 'user__email']


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'platform', 'is_active', 'last_used_at', 'created_at']
    list_filter = ['platform', 'is_active']
    search_fields = ['user__username', 'token']
```

이제 기본적인 데이터 모델 설계가 완료되었습니다. 다음 섹션에서는 이벤트 기반 알림 발송 구조를 구현하겠습니다.

---

## 3. 이벤트 기반 알림 발송 구조

### 3.1 이벤트 디스패처 설계

이벤트가 발생했을 때 자동으로 알림을 생성하고 발송하는 중앙 집중식 디스패처를 만듭니다. 이를 통해 코드 중복을 줄이고 새로운 이벤트 타입을 쉽게 추가할 수 있습니다.

**notifications/dispatcher.py:**

```python
# notifications/dispatcher.py
from typing import Dict, List, Any, Optional
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from .models import Notification, NotificationType, NotificationChannel
from .tasks import send_push_notification_task, send_email_notification_task

User = get_user_model()


class NotificationEvent:
    """알림 이벤트 데이터 클래스"""
    def __init__(
        self,
        event_type: str,
        recipient: User,
        title: str,
        message: str,
        related_object: Any = None,
        action_url: str = '',
        extra_data: Dict = None,
        channels: List[str] = None
    ):
        self.event_type = event_type
        self.recipient = recipient
        self.title = title
        self.message = message
        self.related_object = related_object
        self.action_url = action_url
        self.extra_data = extra_data or {}
        self.channels = channels or [NotificationChannel.IN_APP]


class NotificationDispatcher:
    """알림 발송 디스패처"""
    
    @staticmethod
    def dispatch(event: NotificationEvent) -> Notification:
        """
        이벤트를 받아 알림 생성 및 발송
        
        Args:
            event: NotificationEvent 객체
        
        Returns:
            생성된 Notification 객체
        """
        # 사용자 알림 설정 확인
        settings = NotificationDispatcher._get_user_settings(event.recipient)
        
        # 발송 가능한 채널 필터링
        allowed_channels = NotificationDispatcher._filter_channels(
            event.channels, 
            settings, 
            event.event_type
        )
        
        if not allowed_channels:
            return None  # 발송할 채널이 없음
        
        # 알림 생성
        notification = NotificationDispatcher._create_notification(event, allowed_channels)
        
        # 채널별 알림 발송
        NotificationDispatcher._send_to_channels(notification, allowed_channels)
        
        return notification
    
    @staticmethod
    def _get_user_settings(user: User):
        """사용자 알림 설정 가져오기"""
        from .models import UserNotificationSettings
        settings, _ = UserNotificationSettings.objects.get_or_create(user=user)
        return settings
    
    @staticmethod
    def _filter_channels(
        requested_channels: List[str],
        settings,
        notification_type: str
    ) -> List[str]:
        """사용자 설정에 따라 채널 필터링"""
        allowed = []
        
        for channel in requested_channels:
            if settings.should_send_notification(notification_type, channel):
                allowed.append(channel)
        
        return allowed
    
    @staticmethod
    def _create_notification(
        event: NotificationEvent,
        channels: List[str]
    ) -> Notification:
        """알림 DB 레코드 생성"""
        notification_data = {
            'recipient': event.recipient,
            'notification_type': event.event_type,
            'title': event.title,
            'message': event.message,
            'action_url': event.action_url,
            'extra_data': event.extra_data,
            'channels': channels,
        }
        
        # Generic Foreign Key 설정
        if event.related_object:
            notification_data['content_type'] = ContentType.objects.get_for_model(
                event.related_object
            )
            notification_data['object_id'] = event.related_object.pk
        
        notification = Notification.objects.create(**notification_data)
        return notification
    
    @staticmethod
    def _send_to_channels(notification: Notification, channels: List[str]):
        """각 채널로 알림 발송"""
        from .websocket import send_realtime_notification
        
        for channel in channels:
            if channel == NotificationChannel.IN_APP:
                # WebSocket으로 실시간 전송
                send_realtime_notification(notification)
            
            elif channel == NotificationChannel.PUSH:
                # Celery 비동기 작업으로 푸시 알림 발송
                send_push_notification_task.delay(notification.id)
            
            elif channel == NotificationChannel.EMAIL:
                # Celery 비동기 작업으로 이메일 발송
                send_email_notification_task.delay(notification.id)
            
            elif channel == NotificationChannel.SMS:
                # SMS 발송 (구현 필요)
                pass


# 편의 함수들
def notify_user(
    user: User,
    event_type: str,
    title: str,
    message: str,
    related_object: Any = None,
    action_url: str = '',
    extra_data: Dict = None,
    channels: List[str] = None
) -> Optional[Notification]:
    """
    사용자에게 알림 발송 (간편 함수)
    
    Example:
        notify_user(
            user=order.customer,
            event_type=NotificationType.ORDER_CREATED,
            title='주문이 완료되었습니다',
            message=f'주문번호 {order.order_number}가 접수되었습니다.',
            related_object=order,
            action_url=f'/orders/{order.id}',
            channels=['IN_APP', 'PUSH', 'EMAIL']
        )
    """
    event = NotificationEvent(
        event_type=event_type,
        recipient=user,
        title=title,
        message=message,
        related_object=related_object,
        action_url=action_url,
        extra_data=extra_data,
        channels=channels
    )
    
    return NotificationDispatcher.dispatch(event)


def notify_multiple_users(
    users: List[User],
    event_type: str,
    title: str,
    message: str,
    related_object: Any = None,
    action_url: str = '',
    extra_data: Dict = None,
    channels: List[str] = None
) -> List[Notification]:
    """
    여러 사용자에게 동시에 알림 발송
    
    Example:
        # 팔로워들에게 알림
        notify_multiple_users(
            users=post.author.followers.all(),
            event_type=NotificationType.POST_CREATED,
            title=f'{post.author.username}님이 새 글을 작성했습니다',
            message=post.title,
            related_object=post,
            channels=['IN_APP', 'PUSH']
        )
    """
    notifications = []
    
    for user in users:
        notification = notify_user(
            user=user,
            event_type=event_type,
            title=title,
            message=message,
            related_object=related_object,
            action_url=action_url,
            extra_data=extra_data,
            channels=channels
        )
        if notification:
            notifications.append(notification)
    
    return notifications
```

### 3.2 이벤트 핸들러 구현

각 비즈니스 이벤트에 대한 알림 핸들러를 구현합니다. Django Signal을 활용하여 자동으로 알림을 발송하도록 설정할 수 있습니다.

**notifications/handlers.py:**

```python
# notifications/handlers.py
from typing import List
from django.contrib.auth import get_user_model
from .models import NotificationType, NotificationChannel
from .dispatcher import notify_user, notify_multiple_users

User = get_user_model()


class OrderNotificationHandler:
    """주문 관련 알림 핸들러"""
    
    @staticmethod
    def order_created(order):
        """주문 생성 알림"""
        notify_user(
            user=order.customer,
            event_type=NotificationType.ORDER_CREATED,
            title='주문이 완료되었습니다',
            message=f'주문번호 {order.order_number}가 정상적으로 접수되었습니다.',
            related_object=order,
            action_url=f'/orders/{order.id}',
            extra_data={
                'order_number': order.order_number,
                'total_amount': str(order.total_amount),
            },
            channels=[
                NotificationChannel.IN_APP,
                NotificationChannel.PUSH,
                NotificationChannel.EMAIL
            ]
        )
    
    @staticmethod
    def order_confirmed(order):
        """주문 확인 알림"""
        notify_user(
            user=order.customer,
            event_type=NotificationType.ORDER_CONFIRMED,
            title='주문이 확인되었습니다',
            message=f'주문번호 {order.order_number}의 결제가 확인되어 배송 준비 중입니다.',
            related_object=order,
            action_url=f'/orders/{order.id}',
            channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH]
        )
    
    @staticmethod
    def order_shipped(order, tracking_number: str = ''):
        """배송 시작 알림"""
        message = f'주문번호 {order.order_number}의 배송이 시작되었습니다.'
        if tracking_number:
            message += f'\n송장번호: {tracking_number}'
        
        notify_user(
            user=order.customer,
            event_type=NotificationType.ORDER_SHIPPED,
            title='상품이 배송 중입니다',
            message=message,
            related_object=order,
            action_url=f'/orders/{order.id}/tracking',
            extra_data={'tracking_number': tracking_number},
            channels=[
                NotificationChannel.IN_APP,
                NotificationChannel.PUSH,
                NotificationChannel.SMS
            ]
        )
    
    @staticmethod
    def order_delivered(order):
        """배송 완료 알림"""
        notify_user(
            user=order.customer,
            event_type=NotificationType.ORDER_DELIVERED,
            title='배송이 완료되었습니다',
            message=f'주문하신 상품이 배송 완료되었습니다. 리뷰를 작성해주세요!',
            related_object=order,
            action_url=f'/orders/{order.id}/review',
            channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH]
        )
    
    @staticmethod
    def order_cancelled(order, reason: str = ''):
        """주문 취소 알림"""
        message = f'주문번호 {order.order_number}가 취소되었습니다.'
        if reason:
            message += f'\n취소 사유: {reason}'
        
        notify_user(
            user=order.customer,
            event_type=NotificationType.ORDER_CANCELLED,
            title='주문이 취소되었습니다',
            message=message,
            related_object=order,
            action_url=f'/orders/{order.id}',
            extra_data={'reason': reason},
            channels=[
                NotificationChannel.IN_APP,
                NotificationChannel.PUSH,
                NotificationChannel.EMAIL
            ]
        )


class SocialNotificationHandler:
    """소셜 관련 알림 핸들러"""
    
    @staticmethod
    def comment_created(comment):
        """댓글 작성 알림"""
        # 게시글 작성자에게 알림
        if comment.post.author.id != comment.author.id:
            notify_user(
                user=comment.post.author,
                event_type=NotificationType.COMMENT_CREATED,
                title='새 댓글이 달렸습니다',
                message=f'{comment.author.username}님이 댓글을 남겼습니다: "{comment.content[:50]}"',
                related_object=comment,
                action_url=f'/posts/{comment.post.id}#comment-{comment.id}',
                extra_data={
                    'post_id': comment.post.id,
                    'comment_id': comment.id,
                    'author': comment.author.username,
                },
                channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH]
            )
    
    @staticmethod
    def comment_reply(reply, parent_comment):
        """대댓글 작성 알림"""
        # 부모 댓글 작성자에게 알림
        if parent_comment.author.id != reply.author.id:
            notify_user(
                user=parent_comment.author,
                event_type=NotificationType.COMMENT_REPLY,
                title='댓글에 답글이 달렸습니다',
                message=f'{reply.author.username}님이 답글을 남겼습니다: "{reply.content[:50]}"',
                related_object=reply,
                action_url=f'/posts/{reply.post.id}#comment-{reply.id}',
                channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH]
            )
    
    @staticmethod
    def post_liked(like):
        """게시글 좋아요 알림"""
        # 게시글 작성자에게 알림 (자기 자신 제외)
        if like.post.author.id != like.user.id:
            notify_user(
                user=like.post.author,
                event_type=NotificationType.POST_LIKED,
                title='게시글에 좋아요를 받았습니다',
                message=f'{like.user.username}님이 회원님의 게시글을 좋아합니다',
                related_object=like.post,
                action_url=f'/posts/{like.post.id}',
                channels=[NotificationChannel.IN_APP]
            )
    
    @staticmethod
    def user_followed(follow):
        """팔로우 알림"""
        notify_user(
            user=follow.following,
            event_type=NotificationType.USER_FOLLOWED,
            title='새로운 팔로워',
            message=f'{follow.follower.username}님이 회원님을 팔로우하기 시작했습니다',
            related_object=follow,
            action_url=f'/users/{follow.follower.username}',
            channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH]
        )


class PaymentNotificationHandler:
    """결제 관련 알림 핸들러"""
    
    @staticmethod
    def payment_completed(payment):
        """결제 완료 알림"""
        notify_user(
            user=payment.user,
            event_type=NotificationType.PAYMENT_COMPLETED,
            title='결제가 완료되었습니다',
            message=f'{payment.amount:,}원이 정상적으로 결제되었습니다.',
            related_object=payment,
            action_url=f'/payments/{payment.id}',
            extra_data={
                'amount': str(payment.amount),
                'payment_method': payment.method,
            },
            channels=[
                NotificationChannel.IN_APP,
                NotificationChannel.EMAIL
            ]
        )
    
    @staticmethod
    def payment_failed(payment, error_message: str):
        """결제 실패 알림"""
        notify_user(
            user=payment.user,
            event_type=NotificationType.PAYMENT_FAILED,
            title='결제에 실패했습니다',
            message=f'결제 처리 중 오류가 발생했습니다: {error_message}',
            related_object=payment,
            action_url=f'/payments/{payment.id}/retry',
            extra_data={'error': error_message},
            channels=[
                NotificationChannel.IN_APP,
                NotificationChannel.PUSH,
                NotificationChannel.EMAIL
            ]
        )
    
    @staticmethod
    def refund_completed(refund):
        """환불 완료 알림"""
        notify_user(
            user=refund.user,
            event_type=NotificationType.REFUND_COMPLETED,
            title='환불이 완료되었습니다',
            message=f'{refund.amount:,}원이 환불 처리되었습니다. 영업일 기준 3-5일 내 입금됩니다.',
            related_object=refund,
            action_url=f'/refunds/{refund.id}',
            channels=[
                NotificationChannel.IN_APP,
                NotificationChannel.EMAIL
            ]
        )


class SystemNotificationHandler:
    """시스템 알림 핸들러"""
    
    @staticmethod
    def send_announcement(users: List[User], title: str, message: str, action_url: str = ''):
        """시스템 공지 발송"""
        return notify_multiple_users(
            users=users,
            event_type=NotificationType.SYSTEM_ANNOUNCEMENT,
            title=title,
            message=message,
            action_url=action_url,
            channels=[
                NotificationChannel.IN_APP,
                NotificationChannel.PUSH
            ]
        )
    
    @staticmethod
    def account_verified(user):
        """계정 인증 완료 알림"""
        notify_user(
            user=user,
            event_type=NotificationType.ACCOUNT_VERIFIED,
            title='계정 인증이 완료되었습니다',
            message='이메일 인증이 완료되었습니다. 모든 서비스를 이용하실 수 있습니다.',
            action_url='/dashboard',
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
        )
```

### 3.3 Django Signal 연동

Django의 Signal 시스템을 활용하여 모델 이벤트가 발생했을 때 자동으로 알림을 발송하도록 설정합니다.

**예: orders/signals.py (주문 앱)**

```python
# orders/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order
from notifications.handlers import OrderNotificationHandler


@receiver(post_save, sender=Order)
def order_notification_handler(sender, instance, created, **kwargs):
    """주문 생성/수정 시 알림 발송"""
    
    if created:
        # 새 주문 생성
        OrderNotificationHandler.order_created(instance)
    else:
        # 기존 주문 상태 변경
        if hasattr(instance, '_previous_status'):
            old_status = instance._previous_status
            new_status = instance.status
            
            if old_status != new_status:
                if new_status == 'confirmed':
                    OrderNotificationHandler.order_confirmed(instance)
                elif new_status == 'shipped':
                    OrderNotificationHandler.order_shipped(
                        instance, 
                        tracking_number=instance.tracking_number
                    )
                elif new_status == 'delivered':
                    OrderNotificationHandler.order_delivered(instance)
                elif new_status == 'cancelled':
                    OrderNotificationHandler.order_cancelled(
                        instance,
                        reason=instance.cancel_reason
                    )


@receiver(pre_save, sender=Order)
def store_previous_status(sender, instance, **kwargs):
    """상태 변경 감지를 위해 이전 상태 저장"""
    if instance.pk:
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            instance._previous_status = old_instance.status
        except Order.DoesNotExist:
            instance._previous_status = None


# orders/apps.py
from django.apps import AppConfig

class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'
    
    def ready(self):
        import orders.signals  # Signal 임포트
```

**예: social/signals.py (소셜 기능)**

```python
# social/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Comment, Like, Follow
from notifications.handlers import SocialNotificationHandler


@receiver(post_save, sender=Comment)
def comment_notification_handler(sender, instance, created, **kwargs):
    """댓글 생성 시 알림"""
    if created:
        if instance.parent:
            # 대댓글인 경우
            SocialNotificationHandler.comment_reply(instance, instance.parent)
        else:
            # 일반 댓글인 경우
            SocialNotificationHandler.comment_created(instance)


@receiver(post_save, sender=Like)
def like_notification_handler(sender, instance, created, **kwargs):
    """좋아요 생성 시 알림"""
    if created:
        SocialNotificationHandler.post_liked(instance)


@receiver(post_save, sender=Follow)
def follow_notification_handler(sender, instance, created, **kwargs):
    """팔로우 생성 시 알림"""
    if created:
        SocialNotificationHandler.user_followed(instance)
```

### 3.4 수동 알림 발송 예제

Signal을 사용하지 않고 직접 알림을 발송하는 방법도 있습니다. View나 비즈니스 로직에서 명시적으로 호출할 수 있습니다.

```python
# views.py 또는 services.py
from notifications.dispatcher import notify_user
from notifications.models import NotificationType, NotificationChannel
from notifications.handlers import SystemNotificationHandler

def process_payment(payment_data):
    """결제 처리 예제"""
    try:
        # 결제 로직...
        payment = Payment.objects.create(**payment_data)
        
        # 결제 성공 알림
        notify_user(
            user=payment.user,
            event_type=NotificationType.PAYMENT_COMPLETED,
            title='결제가 완료되었습니다',
            message=f'{payment.amount:,}원 결제가 완료되었습니다.',
            related_object=payment,
            action_url=f'/payments/{payment.id}',
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
        )
        
        return payment
        
    except PaymentError as e:
        # 결제 실패 알림
        notify_user(
            user=payment_data['user'],
            event_type=NotificationType.PAYMENT_FAILED,
            title='결제에 실패했습니다',
            message=str(e),
            channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH]
        )
        raise


def send_marketing_announcement():
    """마케팅 공지 발송 예제"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # 활성 사용자들에게 공지
    active_users = User.objects.filter(is_active=True)
    
    SystemNotificationHandler.send_announcement(
        users=active_users,
        title='🎉 신제품 출시!',
        message='새로운 제품이 출시되었습니다. 지금 확인해보세요!',
        action_url='/products/new'
    )
```

이제 이벤트 기반 알림 발송 구조가 완성되었습니다. 다음 섹션에서는 Django Ninja API를 구현하여 클라이언트가 알림을 조회하고 관리할 수 있도록 하겠습니다.

---

## 4. Django Ninja API 구현

### 4.1 스키마 정의

먼저 API 요청/응답에 사용할 스키마를 정의합니다.

**notifications/schemas.py:**

{% raw %}
```python
# notifications/schemas.py
from typing import List, Optional
from datetime import datetime, time
from ninja import Schema, ModelSchema
from pydantic import Field
from .models import Notification, UserNotificationSettings, NotificationType


class NotificationOut(ModelSchema):
    """알림 출력 스키마"""
    type_display: str = Field(alias='get_notification_type_display')
    
    class Config:
        model = Notification
        model_fields = [
            'id', 'notification_type', 'title', 'message',
            'is_read', 'action_url', 'extra_data', 'created_at'
        ]
    
    @staticmethod
    def resolve_type_display(obj):
        return obj.get_notification_type_display()


class NotificationListOut(Schema):
    """알림 목록 응답"""
    notifications: List[NotificationOut]
    total: int
    unread_count: int
    page: int
    page_size: int
    has_next: bool


class NotificationMarkReadIn(Schema):
    """알림 읽음 처리 요청"""
    notification_ids: List[int]


class NotificationFilterIn(Schema):
    """알림 필터 요청"""
    is_read: Optional[bool] = None
    notification_type: Optional[str] = None
    page: int = 1
    page_size: int = 20


class UserNotificationSettingsOut(ModelSchema):
    """알림 설정 출력 스키마"""
    class Config:
        model = UserNotificationSettings
        model_fields = [
            'order_notifications', 'social_notifications',
            'payment_notifications', 'system_notifications',
            'in_app_enabled', 'push_enabled',
            'email_enabled', 'sms_enabled',
            'dnd_enabled', 'dnd_start_time', 'dnd_end_time'
        ]


class UserNotificationSettingsIn(Schema):
    """알림 설정 수정 요청"""
    order_notifications: Optional[bool] = None
    social_notifications: Optional[bool] = None
    payment_notifications: Optional[bool] = None
    system_notifications: Optional[bool] = None
    
    in_app_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    
    dnd_enabled: Optional[bool] = None
    dnd_start_time: Optional[time] = None
    dnd_end_time: Optional[time] = None


class DeviceTokenIn(Schema):
    """디바이스 토큰 등록 요청"""
    platform: str = Field(..., description="ios, android, web")
    token: str = Field(..., min_length=10)


class DeviceTokenOut(Schema):
    """디바이스 토큰 응답"""
    id: int
    platform: str
    token: str
    is_active: bool
    created_at: datetime


class NotificationStatsOut(Schema):
    """알림 통계"""
    total_count: int
    unread_count: int
    today_count: int
    by_type: dict
```
{% endraw %}

### 4.2 인증 및 권한

JWT 토큰 기반 인증을 구현합니다.

**notifications/auth.py:**

```python
# notifications/auth.py
from ninja.security import HttpBearer
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
import jwt
from django.conf import settings

User = get_user_model()


class JWTAuth(HttpBearer):
    """JWT 토큰 인증"""
    
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            user_id = payload.get('user_id')
            
            if user_id:
                user = User.objects.get(id=user_id)
                return user
                
        except (jwt.DecodeError, jwt.ExpiredSignatureError, User.DoesNotExist):
            pass
        
        return None


# 인증 인스턴스
jwt_auth = JWTAuth()
```

### 4.3 API 엔드포인트 구현

**notifications/api.py:**

{% raw %}
```python
# notifications/api.py
from typing import List
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from ninja import Router
from ninja.pagination import paginate

from .models import Notification, UserNotificationSettings, DeviceToken, NotificationType
from .schemas import (
    NotificationOut, NotificationListOut, NotificationMarkReadIn,
    NotificationFilterIn, UserNotificationSettingsOut, UserNotificationSettingsIn,
    DeviceTokenIn, DeviceTokenOut, NotificationStatsOut
)
from .auth import jwt_auth

router = Router(tags=['Notifications'])


# ==================== 알림 조회 ====================

@router.get('/notifications', response=NotificationListOut, auth=jwt_auth)
def list_notifications(
    request,
    is_read: bool = None,
    notification_type: str = None,
    page: int = 1,
    page_size: int = 20
):
    """
    알림 목록 조회
    
    Query Parameters:
        - is_read: 읽음 여부 필터 (true/false)
        - notification_type: 알림 타입 필터 (ORDER_CREATED 등)
        - page: 페이지 번호
        - page_size: 페이지 크기
    """
    user = request.auth
    
    # 기본 쿼리셋
    queryset = Notification.objects.filter(recipient=user)
    
    # 필터링
    if is_read is not None:
        queryset = queryset.filter(is_read=is_read)
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    # 전체 개수 및 안읽은 개수
    total = queryset.count()
    unread_count = queryset.filter(is_read=False).count()
    
    # 페이지네이션
    start = (page - 1) * page_size
    end = start + page_size
    notifications = list(queryset[start:end])
    
    has_next = total > end
    
    return {
        'notifications': notifications,
        'total': total,
        'unread_count': unread_count,
        'page': page,
        'page_size': page_size,
        'has_next': has_next
    }


@router.get('/notifications/{notification_id}', response=NotificationOut, auth=jwt_auth)
def get_notification(request, notification_id: int):
    """특정 알림 조회"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.auth
    )
    
    # 조회 시 자동으로 읽음 처리
    if not notification.is_read:
        notification.mark_as_read()
    
    return notification


@router.get('/notifications/unread/count', auth=jwt_auth)
def get_unread_count(request):
    """안읽은 알림 개수"""
    count = Notification.objects.filter(
        recipient=request.auth,
        is_read=False
    ).count()
    
    return {'unread_count': count}


@router.get('/notifications/stats', response=NotificationStatsOut, auth=jwt_auth)
def get_notification_stats(request):
    """알림 통계"""
    user = request.auth
    
    total_count = Notification.objects.filter(recipient=user).count()
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
    
    # 오늘 받은 알림
    today = timezone.now().date()
    today_count = Notification.objects.filter(
        recipient=user,
        created_at__date=today
    ).count()
    
    # 타입별 통계
    by_type = {}
    type_counts = Notification.objects.filter(
        recipient=user
    ).values('notification_type').annotate(
        count=Count('id')
    )
    
    for item in type_counts:
        type_name = NotificationType(item['notification_type']).label
        by_type[type_name] = item['count']
    
    return {
        'total_count': total_count,
        'unread_count': unread_count,
        'today_count': today_count,
        'by_type': by_type
    }


# ==================== 알림 관리 ====================

@router.post('/notifications/{notification_id}/read', auth=jwt_auth)
def mark_notification_as_read(request, notification_id: int):
    """알림 읽음 처리"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.auth
    )
    
    notification.mark_as_read()
    
    return {'success': True, 'message': '알림을 읽음 처리했습니다.'}


@router.post('/notifications/{notification_id}/unread', auth=jwt_auth)
def mark_notification_as_unread(request, notification_id: int):
    """알림 안읽음 처리"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.auth
    )
    
    notification.mark_as_unread()
    
    return {'success': True, 'message': '알림을 안읽음 처리했습니다.'}


@router.post('/notifications/read-all', auth=jwt_auth)
def mark_all_as_read(request):
    """모든 알림 읽음 처리"""
    updated = Notification.objects.filter(
        recipient=request.auth,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    return {'success': True, 'message': f'{updated}개의 알림을 읽음 처리했습니다.'}


@router.post('/notifications/read-multiple', auth=jwt_auth)
def mark_multiple_as_read(request, data: NotificationMarkReadIn):
    """여러 알림 읽음 처리"""
    updated = Notification.objects.filter(
        id__in=data.notification_ids,
        recipient=request.auth,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    return {'success': True, 'message': f'{updated}개의 알림을 읽음 처리했습니다.'}


@router.delete('/notifications/{notification_id}', auth=jwt_auth)
def delete_notification(request, notification_id: int):
    """알림 삭제"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.auth
    )
    
    notification.delete()
    
    return {'success': True, 'message': '알림이 삭제되었습니다.'}


@router.delete('/notifications/delete-all-read', auth=jwt_auth)
def delete_all_read_notifications(request):
    """읽은 알림 전체 삭제"""
    deleted, _ = Notification.objects.filter(
        recipient=request.auth,
        is_read=True
    ).delete()
    
    return {'success': True, 'message': f'{deleted}개의 알림이 삭제되었습니다.'}


# ==================== 알림 설정 ====================

@router.get('/settings', response=UserNotificationSettingsOut, auth=jwt_auth)
def get_notification_settings(request):
    """알림 설정 조회"""
    settings, _ = UserNotificationSettings.objects.get_or_create(
        user=request.auth
    )
    return settings


@router.put('/settings', response=UserNotificationSettingsOut, auth=jwt_auth)
def update_notification_settings(request, data: UserNotificationSettingsIn):
    """알림 설정 수정"""
    settings, _ = UserNotificationSettings.objects.get_or_create(
        user=request.auth
    )
    
    # 전달된 필드만 업데이트
    for field, value in data.dict(exclude_unset=True).items():
        setattr(settings, field, value)
    
    settings.save()
    
    return settings


# ==================== 디바이스 토큰 관리 ====================

@router.post('/device-tokens', response=DeviceTokenOut, auth=jwt_auth)
def register_device_token(request, data: DeviceTokenIn):
    """디바이스 토큰 등록 (푸시 알림용)"""
    token, created = DeviceToken.objects.update_or_create(
        user=request.auth,
        platform=data.platform,
        token=data.token,
        defaults={'is_active': True}
    )
    
    return token


@router.get('/device-tokens', response=List[DeviceTokenOut], auth=jwt_auth)
def list_device_tokens(request):
    """등록된 디바이스 토큰 목록"""
    tokens = DeviceToken.objects.filter(
        user=request.auth,
        is_active=True
    )
    return list(tokens)


@router.delete('/device-tokens/{token_id}', auth=jwt_auth)
def delete_device_token(request, token_id: int):
    """디바이스 토큰 삭제"""
    token = get_object_or_404(
        DeviceToken,
        id=token_id,
        user=request.auth
    )
    
    token.is_active = False
    token.save()
    
    return {'success': True, 'message': '디바이스 토큰이 비활성화되었습니다.'}


# ==================== 테스트 알림 ====================

@router.post('/test', auth=jwt_auth)
def send_test_notification(request):
    """테스트 알림 발송"""
    from .dispatcher import notify_user
    from .models import NotificationChannel
    
    notification = notify_user(
        user=request.auth,
        event_type=NotificationType.SYSTEM_ANNOUNCEMENT,
        title='테스트 알림',
        message='알림 시스템이 정상적으로 작동하고 있습니다.',
        action_url='/dashboard',
        channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH]
    )
    
    if notification:
        return {'success': True, 'message': '테스트 알림이 발송되었습니다.', 'notification_id': notification.id}
    else:
        return {'success': False, 'message': '알림 발송에 실패했습니다.'}
```
{% endraw %}

### 4.4 메인 API 라우터에 등록

**config/api.py:**

```python
# config/api.py
from ninja import NinjaAPI
from notifications.api import router as notifications_router

api = NinjaAPI(
    title='Notification System API',
    version='1.0.0',
    description='Django Ninja 기반 알림 시스템 API'
)

# 라우터 등록
api.add_router('/notifications/', notifications_router)
```

**config/urls.py:**

```python
# config/urls.py
from django.contrib import admin
from django.urls import path
from .api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
```

### 4.5 API 테스트

이제 API를 테스트해봅시다.

**1) 알림 목록 조회:**

```bash
curl -X GET "http://localhost:8000/api/notifications/notifications?page=1&page_size=10" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**응답:**
```json
{
  "notifications": [
    {
      "id": 1,
      "notification_type": "ORDER_CREATED",
      "type_display": "주문 완료",
      "title": "주문이 완료되었습니다",
      "message": "주문번호 ORD-20251211-001이 정상적으로 접수되었습니다.",
      "is_read": false,
      "action_url": "/orders/1",
      "extra_data": {
        "order_number": "ORD-20251211-001",
        "total_amount": "50000"
      },
      "created_at": "2025-12-11T10:30:00Z"
    }
  ],
  "total": 45,
  "unread_count": 12,
  "page": 1,
  "page_size": 10,
  "has_next": true
}
```

**2) 안읽은 알림 개수 조회:**

```bash
curl -X GET "http://localhost:8000/api/notifications/notifications/unread/count" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**응답:**
```json
{
  "unread_count": 12
}
```

**3) 알림 읽음 처리:**

```bash
curl -X POST "http://localhost:8000/api/notifications/notifications/1/read" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**4) 모든 알림 읽음 처리:**

```bash
curl -X POST "http://localhost:8000/api/notifications/notifications/read-all" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**5) 알림 설정 조회:**

```bash
curl -X GET "http://localhost:8000/api/notifications/settings" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**응답:**
```json
{
  "order_notifications": true,
  "social_notifications": true,
  "payment_notifications": true,
  "system_notifications": true,
  "in_app_enabled": true,
  "push_enabled": true,
  "email_enabled": false,
  "sms_enabled": false,
  "dnd_enabled": false,
  "dnd_start_time": null,
  "dnd_end_time": null
}
```

**6) 알림 설정 수정:**

```bash
curl -X PUT "http://localhost:8000/api/notifications/settings" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "push_enabled": false,
    "dnd_enabled": true,
    "dnd_start_time": "22:00:00",
    "dnd_end_time": "08:00:00"
  }'
```

**7) 디바이스 토큰 등록 (푸시 알림용):**

```bash
curl -X POST "http://localhost:8000/api/notifications/device-tokens" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "ios",
    "token": "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]"
  }'
```

**8) 테스트 알림 발송:**

```bash
curl -X POST "http://localhost:8000/api/notifications/test" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4.6 Swagger 문서 자동 생성

Django Ninja는 자동으로 OpenAPI(Swagger) 문서를 생성합니다.

브라우저에서 접속:
- **Swagger UI**: `http://localhost:8000/api/docs`
- **ReDoc**: `http://localhost:8000/api/redoc`
- **OpenAPI JSON**: `http://localhost:8000/api/openapi.json`

이제 클라이언트가 사용할 수 있는 완전한 RESTful API가 완성되었습니다. 다음 섹션에서는 WebSocket을 통한 실시간 알림 기능을 구현하겠습니다.

---

## 5. 실시간 알림 (WebSocket)

### 5.1 Django Channels 설정

Django Channels를 사용하여 WebSocket 실시간 통신을 구현합니다.

**config/asgi.py:**

```python
# config/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

from notifications.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
```

### 5.2 WebSocket Consumer 구현

**notifications/consumers.py:**

```python
# notifications/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
import jwt
from django.conf import settings

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """실시간 알림 WebSocket Consumer"""
    
    async def connect(self):
        """WebSocket 연결"""
        # 토큰에서 사용자 인증
        self.user = await self.get_user_from_token()
        
        if not self.user:
            await self.close()
            return
        
        # 사용자별 그룹 이름
        self.group_name = f'notifications_{self.user.id}'
        
        # 그룹에 추가
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # 연결 성공 메시지
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': '알림 서비스에 연결되었습니다.'
        }))
    
    async def disconnect(self, close_code):
        """WebSocket 연결 해제"""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """클라이언트로부터 메시지 수신"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'ping':
                # Ping-Pong (연결 유지)
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
            
            elif action == 'mark_read':
                # 알림 읽음 처리
                notification_id = data.get('notification_id')
                await self.mark_notification_as_read(notification_id)
                
                await self.send(text_data=json.dumps({
                    'type': 'notification_marked_read',
                    'notification_id': notification_id
                }))
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    async def notification_message(self, event):
        """
        그룹으로부터 알림 메시지 수신
        (channel_layer.group_send로 전송된 메시지)
        """
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event['notification']
        }))
    
    async def get_user_from_token(self):
        """WebSocket 쿼리 파라미터에서 JWT 토큰 추출 및 인증"""
        query_string = self.scope.get('query_string', b'').decode()
        params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
        token = params.get('token')
        
        if not token:
            return None
        
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')
            return await self.get_user(user_id)
        except (jwt.DecodeError, jwt.ExpiredSignatureError):
            return None
    
    @database_sync_to_async
    def get_user(self, user_id):
        """DB에서 사용자 조회"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        """알림 읽음 처리"""
        from .models import Notification
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=self.user
            )
            notification.mark_as_read()
        except Notification.DoesNotExist:
            pass
```

### 5.3 WebSocket URL 라우팅

**notifications/routing.py:**

```python
# notifications/routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/notifications/', consumers.NotificationConsumer.as_asgi()),
]
```

### 5.4 실시간 알림 전송 함수

**notifications/websocket.py:**

```python
# notifications/websocket.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def send_realtime_notification(notification):
    """
    WebSocket을 통해 실시간 알림 전송
    
    Args:
        notification: Notification 모델 인스턴스
    """
    channel_layer = get_channel_layer()
    group_name = f'notifications_{notification.recipient.id}'
    
    # 알림 데이터 직렬화
    notification_data = {
        'id': notification.id,
        'type': notification.notification_type,
        'title': notification.title,
        'message': notification.message,
        'is_read': notification.is_read,
        'action_url': notification.action_url,
        'extra_data': notification.extra_data,
        'created_at': notification.created_at.isoformat(),
    }
    
    # 그룹에 메시지 전송
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'notification_message',
            'notification': notification_data
        }
    )


def send_batch_realtime_notifications(notifications):
    """
    여러 사용자에게 실시간 알림 일괄 전송
    
    Args:
        notifications: Notification 모델 인스턴스 리스트
    """
    channel_layer = get_channel_layer()
    
    for notification in notifications:
        group_name = f'notifications_{notification.recipient.id}'
        
        notification_data = {
            'id': notification.id,
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'is_read': notification.is_read,
            'action_url': notification.action_url,
            'extra_data': notification.extra_data,
            'created_at': notification.created_at.isoformat(),
        }
        
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'notification_message',
                'notification': notification_data
            }
        )
```

### 5.5 서버 실행

**Daphne (ASGI 서버) 실행:**

```bash
# 개발 환경
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# 또는 Django 기본 runserver (Channels 지원)
python manage.py runserver
```

**Redis 서버 실행 (Channel Layer용):**

```bash
redis-server
```

### 5.6 클라이언트 연동 예제

**JavaScript (React) 클라이언트:**

```javascript
// NotificationWebSocket.js
import { useEffect, useState, useRef } from 'react';

export const useNotificationWebSocket = (token) => {
  const [notifications, setNotifications] = useState([]);
  const [connected, setConnected] = useState(false);
  const ws = useRef(null);

  useEffect(() => {
    if (!token) return;

    // WebSocket 연결
    const wsUrl = `ws://localhost:8000/ws/notifications/?token=${token}`;
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('WebSocket 연결됨');
      setConnected(true);

      // Ping-Pong (연결 유지)
      const pingInterval = setInterval(() => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
          ws.current.send(JSON.stringify({
            action: 'ping',
            timestamp: Date.now()
          }));
        }
      }, 30000); // 30초마다

      return () => clearInterval(pingInterval);
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'connection_established') {
        console.log(data.message);
      } else if (data.type === 'new_notification') {
        // 새 알림 수신
        setNotifications(prev => [data.notification, ...prev]);
        
        // 브라우저 알림 표시
        if (Notification.permission === 'granted') {
          new Notification(data.notification.title, {
            body: data.notification.message,
            icon: '/notification-icon.png'
          });
        }
        
        // 알림음 재생 (선택사항)
        const audio = new Audio('/notification-sound.mp3');
        audio.play().catch(e => console.log('Audio play failed:', e));
      } else if (data.type === 'pong') {
        console.log('Pong received');
      }
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket 에러:', error);
      setConnected(false);
    };

    ws.current.onclose = () => {
      console.log('WebSocket 연결 종료');
      setConnected(false);

      // 재연결 시도 (5초 후)
      setTimeout(() => {
        console.log('재연결 시도...');
      }, 5000);
    };

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [token]);

  // 알림 읽음 처리
  const markAsRead = (notificationId) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        action: 'mark_read',
        notification_id: notificationId
      }));
    }
  };

  return { notifications, connected, markAsRead };
};


// NotificationBell.jsx - 사용 예제
import React, { useState } from 'react';
import { useNotificationWebSocket } from './NotificationWebSocket';

const NotificationBell = ({ token }) => {
  const { notifications, connected, markAsRead } = useNotificationWebSocket(token);
  const [showDropdown, setShowDropdown] = useState(false);

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="notification-bell">
      <button onClick={() => setShowDropdown(!showDropdown)}>
        🔔
        {unreadCount > 0 && (
          <span className="badge">{unreadCount}</span>
        )}
      </button>

      {showDropdown && (
        <div className="notification-dropdown">
          <div className="header">
            <h3>알림</h3>
            <span className={connected ? 'connected' : 'disconnected'}>
              {connected ? '●' : '○'}
            </span>
          </div>

          <div className="notification-list">
            {notifications.length === 0 ? (
              <p className="empty">알림이 없습니다</p>
            ) : (
              notifications.map(notif => (
                <div
                  key={notif.id}
                  className={`notification-item ${notif.is_read ? 'read' : 'unread'}`}
                  onClick={() => {
                    markAsRead(notif.id);
                    if (notif.action_url) {
                      window.location.href = notif.action_url;
                    }
                  }}
                >
                  <h4>{notif.title}</h4>
                  <p>{notif.message}</p>
                  <span className="time">
                    {new Date(notif.created_at).toLocaleString('ko-KR')}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
```

**CSS 스타일:**

```css
/* NotificationBell.css */
.notification-bell {
  position: relative;
}

.notification-bell button {
  position: relative;
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
}

.notification-bell .badge {
  position: absolute;
  top: -5px;
  right: -5px;
  background: #ff4444;
  color: white;
  border-radius: 50%;
  padding: 2px 6px;
  font-size: 12px;
  font-weight: bold;
}

.notification-dropdown {
  position: absolute;
  top: 40px;
  right: 0;
  width: 350px;
  max-height: 500px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
}

.notification-dropdown .header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
}

.notification-dropdown .header h3 {
  margin: 0;
  font-size: 16px;
}

.notification-dropdown .connected {
  color: #4caf50;
  font-size: 10px;
}

.notification-dropdown .disconnected {
  color: #999;
  font-size: 10px;
}

.notification-list {
  max-height: 400px;
  overflow-y: auto;
}

.notification-item {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background 0.2s;
}

.notification-item:hover {
  background: #f9f9f9;
}

.notification-item.unread {
  background: #e3f2fd;
}

.notification-item h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 600;
}

.notification-item p {
  margin: 0 0 4px 0;
  font-size: 13px;
  color: #666;
}

.notification-item .time {
  font-size: 11px;
  color: #999;
}

.notification-list .empty {
  padding: 32px;
  text-align: center;
  color: #999;
}
```

### 5.7 WebSocket 테스트

**Python 테스트 클라이언트:**

```python
# test_websocket.py
import asyncio
import websockets
import json

async def test_notification_websocket():
    token = "YOUR_JWT_TOKEN_HERE"
    uri = f"ws://localhost:8000/ws/notifications/?token={token}"
    
    async with websockets.connect(uri) as websocket:
        print("WebSocket 연결됨")
        
        # 메시지 수신
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                print(f"수신: {data}")
                
                if data['type'] == 'new_notification':
                    print(f"새 알림: {data['notification']['title']}")
                    
                    # 알림 읽음 처리
                    await websocket.send(json.dumps({
                        'action': 'mark_read',
                        'notification_id': data['notification']['id']
                    }))
            
            except websockets.exceptions.ConnectionClosed:
                print("연결 종료")
                break

if __name__ == "__main__":
    asyncio.run(test_notification_websocket())
```

실행:
```bash
python test_websocket.py
```

이제 실시간 알림 시스템이 완성되었습니다. 다음 섹션에서는 푸시 알림 통합을 구현하겠습니다.

---

## 6. 푸시 알림 통합

### 6.1 Firebase Cloud Messaging (FCM) 설정

**Firebase 프로젝트 설정:**

1. [Firebase Console](https://console.firebase.google.com/)에서 프로젝트 생성
2. 프로젝트 설정 → 서비스 계정 → 새 비공개 키 생성
3. JSON 파일 다운로드 후 프로젝트에 저장

**notifications/tasks.py (Celery):**

```python
# notifications/tasks.py
from celery import shared_task
from django.conf import settings
import firebase_admin
from firebase_admin import credentials, messaging
from .models import Notification, DeviceToken

# Firebase 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)


@shared_task
def send_push_notification_task(notification_id):
    """푸시 알림 발송 (비동기)"""
    try:
        notification = Notification.objects.get(id=notification_id)
        user = notification.recipient
        
        # 사용자의 활성 디바이스 토큰 조회
        device_tokens = DeviceToken.objects.filter(
            user=user,
            is_active=True
        ).values_list('token', flat=True)
        
        if not device_tokens:
            return f"No device tokens for user {user.id}"
        
        # FCM 메시지 생성
        messages = []
        for token in device_tokens:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=notification.title,
                    body=notification.message,
                ),
                data={
                    'notification_id': str(notification.id),
                    'type': notification.notification_type,
                    'action_url': notification.action_url or '',
                },
                token=token,
            )
            messages.append(message)
        
        # 일괄 발송
        response = messaging.send_all(messages)
        
        # 발송 상태 업데이트
        notification.push_sent = True
        notification.save(update_fields=['push_sent'])
        
        return f"Successfully sent {response.success_count} messages"
    
    except Notification.DoesNotExist:
        return f"Notification {notification_id} not found"
    except Exception as e:
        return f"Error: {str(e)}"


@shared_task
def send_email_notification_task(notification_id):
    """이메일 알림 발송 (비동기)"""
    try:
        notification = Notification.objects.get(id=notification_id)
        user = notification.recipient
        
        # SendGrid 또는 Django Email 사용
        from django.core.mail import send_mail
        
        send_mail(
            subject=notification.title,
            message=notification.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        notification.email_sent = True
        notification.save(update_fields=['email_sent'])
        
        return f"Email sent to {user.email}"
    
    except Exception as e:
        return f"Error: {str(e)}"
```

### 6.2 Celery 설정

**config/celery.py:**

```python
# config/celery.py
from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
```

**Celery Worker 실행:**

```bash
# Worker 실행
celery -A config worker -l info

# Beat 실행 (주기적 작업용)
celery -A config beat -l info
```

---

## 7. 이메일/SMS 알림

### 7.1 SendGrid 이메일 통합

```python
# notifications/email_service.py
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.conf import settings
from django.template.loader import render_to_string


class EmailNotificationService:
    """이메일 알림 서비스"""
    
    @staticmethod
    def send_notification_email(notification):
        """알림 이메일 발송"""
        user = notification.recipient
        
        # HTML 템플릿 렌더링
        html_content = render_to_string('emails/notification.html', {
            'user': user,
            'notification': notification,
        })
        
        message = Mail(
            from_email=settings.DEFAULT_FROM_EMAIL,
            to_emails=user.email,
            subject=notification.title,
            html_content=html_content
        )
        
        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            return response.status_code == 202
        except Exception as e:
            print(f"Email error: {e}")
            return False
```

**이메일 템플릿 (templates/emails/notification.html):**

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #3182F6; color: white; padding: 20px; text-align: center; }
        .content { background: #f9f9f9; padding: 20px; }
        .button { display: inline-block; padding: 12px 24px; background: #3182F6; 
                  color: white; text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ notification.title }}</h1>
        </div>
        <div class="content">
            <p>안녕하세요, {{ user.username }}님!</p>
            <p>{{ notification.message }}</p>
            
            {% if notification.action_url %}
            <p style="text-align: center; margin-top: 20px;">
                <a href="https://yoursite.com{{ notification.action_url }}" class="button">
                    확인하기
                </a>
            </p>
            {% endif %}
        </div>
    </div>
</body>
</html>
```

---

## 8. 알림 템플릿 시스템

### 8.1 동적 알림 템플릿

```python
# notifications/templates.py
from typing import Dict
from .models import NotificationType


class NotificationTemplate:
    """알림 템플릿 관리"""
    
    TEMPLATES = {
        NotificationType.ORDER_CREATED: {
            'title': '주문이 완료되었습니다',
            'message': '주문번호 {order_number}가 정상적으로 접수되었습니다.',
            'action_url': '/orders/{order_id}',
        },
        NotificationType.ORDER_SHIPPED: {
            'title': '상품이 배송 중입니다',
            'message': '주문번호 {order_number}의 배송이 시작되었습니다.\n송장번호: {tracking_number}',
            'action_url': '/orders/{order_id}/tracking',
        },
        NotificationType.COMMENT_CREATED: {
            'title': '새 댓글이 달렸습니다',
            'message': '{author}님이 댓글을 남겼습니다: "{content}"',
            'action_url': '/posts/{post_id}#comment-{comment_id}',
        },
        NotificationType.POST_LIKED: {
            'title': '게시글에 좋아요를 받았습니다',
            'message': '{liker}님이 회원님의 게시글을 좋아합니다',
            'action_url': '/posts/{post_id}',
        },
    }
    
    @classmethod
    def get_notification_content(cls, notification_type: str, data: Dict) -> Dict[str, str]:
        """
        템플릿을 사용하여 알림 내용 생성
        
        Example:
            content = NotificationTemplate.get_notification_content(
                NotificationType.ORDER_CREATED,
                {'order_number': 'ORD-001', 'order_id': 123}
            )
        """
        template = cls.TEMPLATES.get(notification_type)
        
        if not template:
            return {
                'title': '알림',
                'message': '새로운 알림이 있습니다.',
                'action_url': ''
            }
        
        return {
            'title': template['title'].format(**data),
            'message': template['message'].format(**data),
            'action_url': template['action_url'].format(**data),
        }


# 사용 예제
from notifications.templates import NotificationTemplate
from notifications.dispatcher import notify_user
from notifications.models import NotificationType

def create_order_notification(order):
    content = NotificationTemplate.get_notification_content(
        NotificationType.ORDER_CREATED,
        {
            'order_number': order.order_number,
            'order_id': order.id,
        }
    )
    
    notify_user(
        user=order.customer,
        event_type=NotificationType.ORDER_CREATED,
        title=content['title'],
        message=content['message'],
        related_object=order,
        action_url=content['action_url'],
        channels=['IN_APP', 'PUSH', 'EMAIL']
    )
```

---

## 9. 프로덕션 최적화

### 9.1 데이터베이스 인덱싱

```python
# notifications/models.py (최적화된 인덱스)
class Notification(models.Model):
    # ... 기존 필드들 ...
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
            models.Index(fields=['recipient', 'notification_type', 'is_read']),
        ]
```

### 9.2 배치 알림 처리

```python
# notifications/batch.py
from typing import List
from django.contrib.auth import get_user_model
from .models import Notification
from .websocket import send_batch_realtime_notifications

User = get_user_model()


def create_batch_notifications(users: List[User], notification_data: dict) -> List[Notification]:
    """대량 알림 생성 (bulk_create 사용)"""
    notifications = [
        Notification(
            recipient=user,
            **notification_data
        )
        for user in users
    ]
    
    # 한 번에 DB 삽입
    created_notifications = Notification.objects.bulk_create(notifications)
    
    # 실시간 알림 발송
    send_batch_realtime_notifications(created_notifications)
    
    # 푸시/이메일은 Celery로 비동기 처리
    for notif in created_notifications:
        if 'PUSH' in notification_data.get('channels', []):
            from .tasks import send_push_notification_task
            send_push_notification_task.delay(notif.id)
    
    return created_notifications
```

### 9.3 Redis 캐싱

```python
# notifications/cache.py
from django.core.cache import cache


def get_unread_count_cached(user_id):
    """캐시된 안읽은 알림 개수"""
    cache_key = f'unread_count_{user_id}'
    count = cache.get(cache_key)
    
    if count is None:
        from .models import Notification
        count = Notification.objects.filter(
            recipient_id=user_id,
            is_read=False
        ).count()
        cache.set(cache_key, count, timeout=300)  # 5분
    
    return count


def invalidate_unread_count_cache(user_id):
    """캐시 무효화"""
    cache_key = f'unread_count_{user_id}'
    cache.delete(cache_key)
```

### 9.4 오래된 알림 정리

```python
# notifications/management/commands/cleanup_old_notifications.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from notifications.models import Notification


class Command(BaseCommand):
    help = '90일 이상 읽은 알림 삭제'
    
    def handle(self, *args, **options):
        ninety_days_ago = timezone.now() - timedelta(days=90)
        
        deleted, _ = Notification.objects.filter(
            is_read=True,
            read_at__lt=ninety_days_ago
        ).delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'{deleted}개의 오래된 알림이 삭제되었습니다.')
        )
```

**Cron 설정:**
```bash
# 매일 새벽 3시 실행
0 3 * * * cd /path/to/project && python manage.py cleanup_old_notifications
```

---

## 10. 실전 예제

### 10.1 전자상거래 주문 흐름

```python
# orders/services.py
from notifications.handlers import OrderNotificationHandler
from notifications.templates import NotificationTemplate


class OrderService:
    """주문 서비스"""
    
    @staticmethod
    def create_order(customer, cart_items):
        """주문 생성"""
        order = Order.objects.create(
            customer=customer,
            order_number=generate_order_number(),
            status='pending'
        )
        
        for item in cart_items:
            OrderItem.objects.create(order=order, **item)
        
        # 주문 생성 알림
        OrderNotificationHandler.order_created(order)
        
        return order
    
    @staticmethod
    def confirm_payment(order):
        """결제 확인"""
        order.status = 'confirmed'
        order.save()
        
        # 주문 확인 알림
        OrderNotificationHandler.order_confirmed(order)
    
    @staticmethod
    def ship_order(order, tracking_number):
        """배송 시작"""
        order.status = 'shipped'
        order.tracking_number = tracking_number
        order.save()
        
        # 배송 시작 알림
        OrderNotificationHandler.order_shipped(order, tracking_number)
    
    @staticmethod
    def complete_delivery(order):
        """배송 완료"""
        order.status = 'delivered'
        order.save()
        
        # 배송 완료 알림
        OrderNotificationHandler.order_delivered(order)
```

### 10.2 소셜 미디어 인터랙션

```python
# social/views.py
from ninja import Router
from notifications.handlers import SocialNotificationHandler

router = Router()


@router.post('/posts/{post_id}/like')
def like_post(request, post_id: int):
    """게시글 좋아요"""
    post = get_object_or_404(Post, id=post_id)
    
    like, created = Like.objects.get_or_create(
        user=request.auth,
        post=post
    )
    
    if created:
        # 좋아요 알림
        SocialNotificationHandler.post_liked(like)
        return {'success': True, 'message': '좋아요를 눌렀습니다.'}
    else:
        like.delete()
        return {'success': True, 'message': '좋아요를 취소했습니다.'}


@router.post('/posts/{post_id}/comments')
def create_comment(request, post_id: int, content: str):
    """댓글 작성"""
    post = get_object_or_404(Post, id=post_id)
    
    comment = Comment.objects.create(
        post=post,
        author=request.auth,
        content=content
    )
    
    # 댓글 알림 (Signal로 자동 발송되지만 수동으로도 가능)
    # SocialNotificationHandler.comment_created(comment)
    
    return {'success': True, 'comment_id': comment.id}
```

### 10.3 시스템 공지 발송

```python
# admin/views.py
from notifications.handlers import SystemNotificationHandler
from django.contrib.auth import get_user_model

User = get_user_model()


def send_system_announcement(title, message, action_url='', target='all'):
    """시스템 공지 발송"""
    
    if target == 'all':
        users = User.objects.filter(is_active=True)
    elif target == 'premium':
        users = User.objects.filter(is_active=True, is_premium=True)
    else:
        users = User.objects.filter(is_active=True)
    
    notifications = SystemNotificationHandler.send_announcement(
        users=users,
        title=title,
        message=message,
        action_url=action_url
    )
    
    return len(notifications)


# 사용 예제
count = send_system_announcement(
    title='🎉 신규 기능 출시!',
    message='새로운 프리미엄 기능이 추가되었습니다. 지금 확인해보세요!',
    action_url='/features/new',
    target='all'
)
print(f'{count}명에게 공지를 발송했습니다.')
```

---

## 결론

이번 가이드에서는 Django Ninja를 활용하여 **이벤트 기반 실시간 알림 시스템**을 처음부터 끝까지 구축하는 방법을 살펴보았습니다.

### 핵심 요약

✅ **이벤트 기반 아키텍처**
- Event Dispatcher 패턴으로 확장 가능한 구조
- Django Signal을 활용한 자동 알림 발송
- 새로운 이벤트 타입 쉽게 추가 가능

✅ **다중 채널 지원**
- 인앱 알림 (WebSocket)
- 푸시 알림 (FCM)
- 이메일 알림 (SendGrid)
- SMS 알림 (확장 가능)

✅ **실시간 통신**
- Django Channels + Redis
- WebSocket 기반 실시간 알림
- Ping-Pong으로 연결 유지

✅ **비동기 처리**
- Celery를 통한 백그라운드 작업
- 대량 알림 배치 처리
- 성능 최적화

✅ **사용자 경험**
- 알림 타입별 설정
- 채널별 on/off
- 조용한 시간 (DND) 모드
- 읽음/안읽음 상태 관리

### 프로덕션 체크리스트

- [ ] Redis 서버 설정 및 모니터링
- [ ] Celery Worker 프로세스 관리 (Supervisor/Systemd)
- [ ] Firebase 프로젝트 설정 및 서비스 계정 키 관리
- [ ] SendGrid/이메일 서비스 API 키 설정
- [ ] 데이터베이스 인덱스 최적화
- [ ] 오래된 알림 정리 Cron Job 설정
- [ ] 알림 발송 실패 재시도 로직
- [ ] 모니터링 및 로깅 (Sentry, CloudWatch)
- [ ] 부하 테스트 및 성능 튜닝
- [ ] HTTPS/WSS 보안 설정

### 추가 개선 사항

**1. 알림 우선순위**
```python
class NotificationPriority(models.TextChoices):
    LOW = 'LOW', '낮음'
    NORMAL = 'NORMAL', '보통'
    HIGH = 'HIGH', '높음'
    URGENT = 'URGENT', '긴급'

# 긴급 알림은 모든 채널로 즉시 발송
# 낮은 우선순위는 배치로 처리
```

**2. 알림 그룹화**
```python
# "홍길동님 외 5명이 회원님의 게시글을 좋아합니다"
# 같은 타입의 알림을 그룹화하여 표시
```

**3. 알림 구독/구독 해제**
```python
# 특정 게시글, 특정 사용자에 대한 알림만 받기
class NotificationSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    enabled = models.BooleanField(default=True)
```

**4. 알림 분석**
```python
# 알림 오픈율, 클릭율 추적
class NotificationAnalytics(models.Model):
    notification = models.OneToOneField(Notification, on_delete=models.CASCADE)
    opened_at = models.DateTimeField(null=True)
    clicked_at = models.DateTimeField(null=True)
    action_taken = models.BooleanField(default=False)
```

이 시스템을 기반으로 여러분의 서비스에 맞는 알림 기능을 구축해보세요! 🚀

### 참고 자료

- [Django Ninja 공식 문서](https://django-ninja.rest-framework.com/)
- [Django Channels 공식 문서](https://channels.readthedocs.io/)
- [Firebase Cloud Messaging](https://firebase.google.com/docs/cloud-messaging)
- [Celery 공식 문서](https://docs.celeryproject.org/)
- [Redis 공식 문서](https://redis.io/documentation)

---

**GitHub 저장소**: 전체 소스 코드는 [여기](https://github.com/yourusername/django-ninja-notifications)에서 확인하실 수 있습니다.

**질문이나 피드백**은 댓글로 남겨주세요! 😊
