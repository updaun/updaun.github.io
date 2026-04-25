---
layout: post
title: "Django Ninja로 구현하는 모바일 푸시 알림: FCM 완벽 가이드"
date: 2026-01-06 10:00:00 +0900
categories: [Django, Python, Mobile, API]
tags: [Django, Django Ninja, FCM, Push Notification, Firebase, Mobile Backend, REST API, Python]
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-01-06-django-ninja-push-notification-implementation.webp"
---

Django Ninja는 FastAPI의 영감을 받아 만들어진 Django용 현대적인 API 프레임워크입니다. 이 글에서는 Django Ninja를 활용하여 Firebase Cloud Messaging(FCM)을 통한 푸시 알림 시스템을 구축하는 방법을 알아보겠습니다. 실무에서 바로 적용 가능한 코드와 함께 다양한 푸시 알림 방식도 비교해보겠습니다.

## 📱 푸시 알림 방식 비교

모바일 앱이나 웹 서비스에 푸시 알림을 구현할 때 여러 방식을 고려할 수 있습니다. 각 방식의 특징과 장단점을 이해하면 프로젝트에 가장 적합한 솔루션을 선택할 수 있습니다.

### 1. Firebase Cloud Messaging (FCM)

**특징**
- Google에서 제공하는 무료 푸시 알림 서비스
- Android, iOS, 웹 모두 지원
- 월 무제한 메시지 전송 가능
- 토픽 기반 구독 및 그룹 메시징 지원

**장점**
```python
# ✅ 간단한 통합
# ✅ 무료 사용
# ✅ 높은 안정성과 전송률
# ✅ 풍부한 문서와 커뮤니티
# ✅ 토픽 구독, 조건부 전송 등 고급 기능
```

**단점**
```python
# ⚠️ Google 서비스 의존성
# ⚠️ 중국에서 사용 불가 (GFW로 차단)
# ⚠️ 커스터마이징 제한적
```

**적합한 경우**: 대부분의 일반적인 모바일 앱, 빠른 프로토타이핑, 예산이 제한적인 프로젝트

### 2. Apple Push Notification Service (APNs)

**특징**
- Apple에서 제공하는 iOS 전용 푸시 알림 서비스
- iOS, iPadOS, macOS, watchOS 지원
- P8 인증서 또는 P12 인증서 방식

**장점**
```python
# ✅ iOS 네이티브 지원
# ✅ 높은 전송 신뢰성
# ✅ 백그라운드 알림 지원
```

**단점**
```python
# ⚠️ iOS만 지원 (크로스 플랫폼 불가)
# ⚠️ 인증서 관리 복잡
# ⚠️ 개발자 계정 필요 (연간 $99)
```

**적합한 경우**: iOS 전용 앱, 엔터프라이즈 iOS 앱

### 3. OneSignal

**특징**
- 멀티 플랫폼 푸시 알림 SaaS
- 무료 플랜: 월 10,000명 사용자까지
- 대시보드에서 쉬운 관리

**장점**
```python
# ✅ 통합 대시보드
# ✅ A/B 테스팅 기능
# ✅ 자동화된 캠페인
# ✅ 상세한 분석 리포트
# ✅ iOS, Android, Web, Email, SMS 통합
```

**단점**
```python
# ⚠️ 대규모 사용 시 유료
# ⚠️ 외부 서비스 의존
# ⚠️ 데이터 프라이버시 고려 필요
```

**적합한 경우**: 마케팅 캠페인 중심 서비스, 분석 기능 필요한 경우

### 4. WebSocket 실시간 알림

**특징**
- 양방향 실시간 통신
- Django Channels 또는 Socket.IO 사용
- 브라우저에서 실시간 업데이트

**장점**
```python
# ✅ 완전한 컨트롤
# ✅ 실시간 양방향 통신
# ✅ 외부 서비스 의존 없음
# ✅ 커스터마이징 자유로움
```

**단점**
```python
# ⚠️ 앱 종료 시 알림 불가
# ⚠️ 배터리 소모 큼
# ⚠️ 서버 리소스 많이 사용
# ⚠️ 인프라 관리 필요
```

**적합한 경우**: 채팅 앱, 실시간 협업 도구, 대시보드

### 5. Pusher / Ably

**특징**
- 실시간 메시징 플랫폼
- WebSocket 기반 PaaS
- 쉬운 통합과 확장성

**장점**
```python
# ✅ 간단한 구현
# ✅ 자동 스케일링
# ✅ 글로벌 인프라
# ✅ 웹소켓 + 푸시 알림 통합
```

**단점**
```python
# ⚠️ 비용 발생 (메시지당 과금)
# ⚠️ 외부 서비스 의존
# ⚠️ 대규모 트래픽 시 비용 급증
```

**적합한 경우**: 빠른 MVP, 실시간 기능이 핵심인 서비스

### 📊 비교 표

| 방식 | 비용 | 난이도 | 크로스플랫폼 | 앱 종료시 | 추천도 |
|------|------|--------|-------------|-----------|--------|
| FCM | 무료 | 중 | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| APNs | $99/년 | 중-상 | ❌ (iOS만) | ✅ | ⭐⭐⭐⭐ |
| OneSignal | 무료/유료 | 하 | ✅ | ✅ | ⭐⭐⭐⭐ |
| WebSocket | 인프라 비용 | 상 | ✅ | ❌ | ⭐⭐⭐ |
| Pusher/Ably | 유료 | 하 | ✅ | 부분적 | ⭐⭐⭐ |

**결론**: 대부분의 경우 FCM이 가장 균형잡힌 선택입니다. 무료이면서도 안정적이고, 크로스 플랫폼을 지원하며, 앱이 종료된 상태에서도 푸시 알림을 전송할 수 있습니다. 이 글에서는 FCM을 중심으로 Django Ninja와의 통합을 다루겠습니다.

## 🚀 프로젝트 설정

Django Ninja와 FCM을 통합하기 위해서는 먼저 필요한 패키지를 설치하고 Firebase 프로젝트를 설정해야 합니다.

### 1. 패키지 설치

```bash
# Django Ninja 설치
pip install django-ninja

# Firebase Admin SDK 설치
pip install firebase-admin

# 환경변수 관리를 위한 python-decouple (선택사항)
pip install python-decouple
```

**requirements.txt 예시**
```txt
Django>=4.2.0
django-ninja>=1.1.0
firebase-admin>=6.4.0
python-decouple>=3.8
```

### 2. Firebase 프로젝트 생성

**단계별 가이드**:

1. [Firebase Console](https://console.firebase.google.com/) 접속
2. "프로젝트 추가" 클릭
3. 프로젝트 이름 입력 (예: my-django-app)
4. Google Analytics 설정 (선택사항)
5. 프로젝트 생성 완료

### 3. FCM 서비스 계정 키 생성

Firebase 프로젝트에서 서버가 FCM API를 호출하려면 인증이 필요합니다. 서비스 계정 키를 생성하여 Django 프로젝트에 통합하겠습니다.

**Firebase Console에서**:
```
1. 프로젝트 설정 (⚙️) → "프로젝트 설정"
2. "서비스 계정" 탭 클릭
3. "새 비공개 키 생성" 클릭
4. JSON 파일 다운로드 (예: serviceAccountKey.json)
```

**보안 주의사항**:
```python
# ⚠️ 절대 Git에 커밋하지 마세요!
# .gitignore에 추가하세요

# .gitignore
serviceAccountKey.json
firebase-credentials.json
*.json  # 또는 더 구체적으로
```

### 4. Django 프로젝트 구조

```
my_project/
├── manage.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── notifications/
│   ├── __init__.py
│   ├── models.py          # 디바이스 토큰 저장
│   ├── schemas.py         # Pydantic 스키마
│   ├── api.py            # Django Ninja API
│   ├── services.py        # FCM 비즈니스 로직
│   └── firebase_config.py # Firebase 초기화
├── serviceAccountKey.json # FCM 서비스 계정 키
└── requirements.txt
```

### 5. Django 앱 생성

```bash
# notifications 앱 생성
python manage.py startapp notifications

# 데이터베이스 마이그레이션
python manage.py makemigrations
python manage.py migrate
```

**settings.py에 앱 추가**:
```python
# config/settings.py

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'ninja',
    
    # Local apps
    'notifications',
]

# Firebase 설정
FIREBASE_CREDENTIALS_PATH = BASE_DIR / 'serviceAccountKey.json'
```

### 6. Firebase 초기화

Firebase Admin SDK를 Django 프로젝트에서 사용하기 위해 초기화 코드를 작성합니다. 이 코드는 서버 시작 시 한 번만 실행되어야 합니다.

**notifications/firebase_config.py**:
```python
import firebase_admin
from firebase_admin import credentials
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def initialize_firebase():
    """
    Firebase Admin SDK 초기화
    
    주의: 이 함수는 앱 시작 시 한 번만 호출되어야 합니다.
    여러 번 호출 시 에러가 발생할 수 있습니다.
    """
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(str(settings.FIREBASE_CREDENTIALS_PATH))
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise
    else:
        logger.info("Firebase already initialized")
```

**notifications/apps.py**:
```python
from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    
    def ready(self):
        """앱이 로드될 때 Firebase 초기화"""
        from .firebase_config import initialize_firebase
        initialize_firebase()
```

**중요**: `INSTALLED_APPS`에서 앱 이름을 전체 경로로 변경:
```python
# config/settings.py
INSTALLED_APPS = [
    # ...
    'notifications.apps.NotificationsConfig',  # 변경
]
```

이제 Django 서버를 시작하면 Firebase가 자동으로 초기화됩니다. 다음 섹션에서는 디바이스 토큰을 저장할 데이터베이스 모델을 만들겠습니다.

## 💾 데이터베이스 모델 설계

푸시 알림을 전송하려면 각 사용자의 디바이스 토큰을 저장해야 합니다. 한 사용자가 여러 디바이스(스마트폰, 태블릿 등)를 가질 수 있으므로 이를 고려한 모델을 설계하겠습니다.

### 1. DeviceToken 모델

**notifications/models.py**:
```python
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class DeviceToken(models.Model):
    """
    사용자 디바이스의 FCM 토큰을 저장하는 모델
    
    한 사용자가 여러 디바이스를 가질 수 있으므로
    user와 device_token은 일대다 관계입니다.
    """
    
    class DeviceType(models.TextChoices):
        ANDROID = 'ANDROID', 'Android'
        IOS = 'IOS', 'iOS'
        WEB = 'WEB', 'Web'
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='device_tokens',
        verbose_name='사용자'
    )
    
    device_token = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='FCM 디바이스 토큰',
        db_index=True
    )
    
    device_type = models.CharField(
        max_length=10,
        choices=DeviceType.choices,
        default=DeviceType.ANDROID,
        verbose_name='디바이스 타입'
    )
    
    device_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='디바이스 이름',
        help_text='예: Samsung Galaxy S21, iPhone 13 Pro'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성 상태',
        help_text='비활성화된 토큰은 푸시 알림을 받지 않습니다'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )
    
    last_used_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='마지막 사용일시'
    )
    
    class Meta:
        db_table = 'device_tokens'
        verbose_name = '디바이스 토큰'
        verbose_name_plural = '디바이스 토큰 목록'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['device_token']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.device_type} ({self.device_token[:20]}...)"
    
    def mark_as_used(self):
        """토큰 사용 시간 업데이트"""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])


class NotificationLog(models.Model):
    """
    전송된 푸시 알림 기록을 저장하는 모델
    
    디버깅과 분석을 위해 전송 이력을 기록합니다.
    """
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', '대기중'
        SENT = 'SENT', '전송완료'
        FAILED = 'FAILED', '전송실패'
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notification_logs',
        verbose_name='수신자'
    )
    
    device_token = models.ForeignKey(
        DeviceToken,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notification_logs',
        verbose_name='디바이스 토큰'
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name='알림 제목'
    )
    
    body = models.TextField(
        verbose_name='알림 내용'
    )
    
    data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='추가 데이터',
        help_text='커스텀 키-값 쌍'
    )
    
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='전송 상태'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='에러 메시지'
    )
    
    fcm_message_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='FCM 메시지 ID'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )
    
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='전송일시'
    )
    
    class Meta:
        db_table = 'notification_logs'
        verbose_name = '알림 로그'
        verbose_name_plural = '알림 로그 목록'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.status})"
```

### 2. 마이그레이션 실행

```bash
# 마이그레이션 파일 생성
python manage.py makemigrations notifications

# 데이터베이스에 적용
python manage.py migrate notifications
```

### 3. Admin 등록 (선택사항)

Django Admin에서 토큰과 로그를 관리할 수 있도록 등록합니다.

**notifications/admin.py**:
```python
from django.contrib import admin
from .models import DeviceToken, NotificationLog

@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_type', 'device_name', 'is_active', 'created_at', 'last_used_at']
    list_filter = ['device_type', 'is_active', 'created_at']
    search_fields = ['user__username', 'user__email', 'device_token', 'device_name']
    readonly_fields = ['created_at', 'updated_at', 'last_used_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'device_token', 'device_type', 'device_name')
        }),
        ('상태', {
            'fields': ('is_active',)
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at', 'last_used_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'status', 'created_at', 'sent_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'title', 'body']
    readonly_fields = ['created_at', 'sent_at', 'fcm_message_id']
    
    fieldsets = (
        ('수신자 정보', {
            'fields': ('user', 'device_token')
        }),
        ('알림 내용', {
            'fields': ('title', 'body', 'data')
        }),
        ('전송 상태', {
            'fields': ('status', 'error_message', 'fcm_message_id')
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'sent_at'),
            'classes': ('collapse',)
        }),
    )
```

### 4. 모델 설계 포인트

**왜 DeviceToken을 별도 모델로 분리했나?**
```python
# ❌ 안 좋은 방법: User 모델에 직접 추가
class User:
    fcm_token = models.CharField(max_length=255)  # 한 개만 저장 가능

# ✅ 좋은 방법: 별도 모델로 분리
class DeviceToken:
    user = models.ForeignKey(User)  # 여러 개 저장 가능
    device_token = models.CharField(max_length=255)
```

**장점**:
- 한 사용자가 여러 디바이스 사용 가능
- 디바이스별 타입과 이름 관리
- 비활성 토큰 관리 용이
- 토큰 만료 시 개별 삭제 가능

**NotificationLog의 필요성**:
- 알림 전송 이력 추적
- 실패한 알림 재전송 기능 구현
- 사용자별 알림 통계 분석
- 디버깅 및 문제 해결

데이터베이스 모델을 완성했습니다. 다음 섹션에서는 Pydantic 스키마와 Django Ninja API를 구현하겠습니다.

## 📝 Pydantic 스키마 정의

Django Ninja는 FastAPI처럼 Pydantic을 사용하여 요청/응답 데이터를 검증합니다. API의 입출력 스키마를 정의하겠습니다.

**notifications/schemas.py**:
```python
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from ninja import Schema

# ============= 요청 스키마 =============

class DeviceTokenRegisterSchema(Schema):
    """디바이스 토큰 등록 요청"""
    device_token: str = Field(
        ...,
        min_length=10,
        description="FCM 디바이스 토큰"
    )
    device_type: str = Field(
        ...,
        description="디바이스 타입 (ANDROID, IOS, WEB)"
    )
    device_name: Optional[str] = Field(
        None,
        max_length=100,
        description="디바이스 이름 (예: iPhone 13 Pro)"
    )
    
    @validator('device_type')
    def validate_device_type(cls, v):
        allowed = ['ANDROID', 'IOS', 'WEB']
        if v.upper() not in allowed:
            raise ValueError(f'device_type must be one of {allowed}')
        return v.upper()


class SendNotificationSchema(Schema):
    """단일 사용자에게 알림 전송 요청"""
    user_id: int = Field(..., description="수신자 사용자 ID")
    title: str = Field(..., min_length=1, max_length=200, description="알림 제목")
    body: str = Field(..., min_length=1, description="알림 내용")
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="추가 데이터 (커스텀 키-값 쌍)"
    )
    image_url: Optional[str] = Field(
        None,
        description="알림 이미지 URL"
    )


class SendBulkNotificationSchema(Schema):
    """여러 사용자에게 알림 전송 요청"""
    user_ids: List[int] = Field(
        ...,
        min_items=1,
        max_items=1000,
        description="수신자 사용자 ID 목록 (최대 1000명)"
    )
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)
    data: Optional[Dict[str, Any]] = None


class SendTopicNotificationSchema(Schema):
    """토픽 구독자들에게 알림 전송 요청"""
    topic: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="토픽 이름 (예: news, promotions)"
    )
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)
    data: Optional[Dict[str, Any]] = None
    
    @validator('topic')
    def validate_topic(cls, v):
        # 토픽 이름은 영문자, 숫자, 하이픈, 언더스코어만 허용
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Topic name must contain only letters, numbers, hyphens, and underscores')
        return v


class SubscribeToTopicSchema(Schema):
    """토픽 구독 요청"""
    topic: str = Field(..., description="구독할 토픽 이름")
    device_tokens: Optional[List[str]] = Field(
        None,
        description="구독할 디바이스 토큰 목록 (미제공 시 현재 사용자의 모든 토큰)"
    )


# ============= 응답 스키마 =============

class DeviceTokenResponse(Schema):
    """디바이스 토큰 응답"""
    id: int
    device_token: str
    device_type: str
    device_name: Optional[str]
    is_active: bool
    created_at: datetime
    last_used_at: datetime


class NotificationResponse(Schema):
    """알림 전송 응답"""
    success: bool
    message: str
    notification_id: Optional[int] = None
    fcm_message_id: Optional[str] = None


class BulkNotificationResponse(Schema):
    """대량 알림 전송 응답"""
    success: bool
    total: int
    sent: int
    failed: int
    details: List[Dict[str, Any]] = []


class ErrorResponse(Schema):
    """에러 응답"""
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None


class SuccessResponse(Schema):
    """성공 응답"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


# ============= 알림 히스토리 스키마 =============

class NotificationLogResponse(Schema):
    """알림 로그 응답"""
    id: int
    title: str
    body: str
    data: Dict[str, Any]
    status: str
    error_message: Optional[str]
    created_at: datetime
    sent_at: Optional[datetime]
    
    @staticmethod
    def from_orm(obj):
        return NotificationLogResponse(
            id=obj.id,
            title=obj.title,
            body=obj.body,
            data=obj.data,
            status=obj.status,
            error_message=obj.error_message,
            created_at=obj.created_at,
            sent_at=obj.sent_at
        )


class PaginatedNotificationLogResponse(Schema):
    """페이지네이션된 알림 로그 응답"""
    count: int
    next: Optional[str]
    previous: Optional[str]
    results: List[NotificationLogResponse]
```

### 스키마 설계 포인트

**1. Validator 활용**
```python
@validator('device_type')
def validate_device_type(cls, v):
    # 입력값 검증 및 정규화
    return v.upper()
```
- 데이터 일관성 보장
- DB에 저장되기 전 검증
- 에러 조기 발견

**2. Field 제약사항**
```python
user_ids: List[int] = Field(
    ...,
    min_items=1,      # 최소 1개
    max_items=1000    # 최대 1000개 (FCM 제한)
)
```
- API 남용 방지
- FCM 제한사항 준수
- 명확한 문서화

**3. Optional vs Required**
```python
title: str = Field(...)              # 필수
data: Optional[Dict] = None          # 선택
```
- 명확한 API 계약
- 자동 문서 생성
- 타입 안정성

다음 섹션에서는 이 스키마들을 사용하는 실제 API 엔드포인트를 구현하겠습니다.

## 🔥 FCM 서비스 로직 구현

Firebase Admin SDK를 사용하여 실제로 푸시 알림을 전송하는 비즈니스 로직을 구현합니다. 서비스 레이어를 분리하여 코드 재사용성과 테스트 용이성을 높입니다.

**notifications/services.py**:
```python
from typing import List, Dict, Any, Optional, Tuple
from firebase_admin import messaging
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
import logging

from .models import DeviceToken, NotificationLog

User = get_user_model()
logger = logging.getLogger(__name__)


class FCMService:
    """Firebase Cloud Messaging 서비스"""
    
    @staticmethod
    def send_to_device(
        device_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        단일 디바이스에 푸시 알림 전송
        
        Args:
            device_token: FCM 디바이스 토큰
            title: 알림 제목
            body: 알림 내용
            data: 추가 데이터 (모든 값은 문자열이어야 함)
            image_url: 이미지 URL
        
        Returns:
            (성공여부, FCM 메시지 ID, 에러 메시지)
        """
        try:
            # 알림 메시지 생성
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            
            # Android 설정
            android_config = messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    icon='notification_icon',
                    color='#FF0000',
                    sound='default',
                )
            )
            
            # iOS 설정
            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=title,
                            body=body
                        ),
                        badge=1,
                        sound='default'
                    )
                )
            )
            
            # 데이터 문자열 변환 (FCM은 문자열만 허용)
            str_data = None
            if data:
                str_data = {k: str(v) for k, v in data.items()}
            
            # 메시지 객체 생성
            message = messaging.Message(
                notification=notification,
                data=str_data,
                token=device_token,
                android=android_config,
                apns=apns_config
            )
            
            # FCM으로 전송
            response = messaging.send(message)
            logger.info(f"Successfully sent message: {response}")
            
            return True, response, None
            
        except messaging.UnregisteredError:
            error_msg = "Device token is unregistered or invalid"
            logger.warning(f"{error_msg}: {device_token}")
            return False, None, error_msg
            
        except messaging.SenderIdMismatchError:
            error_msg = "Sender ID mismatch"
            logger.error(f"{error_msg}: {device_token}")
            return False, None, error_msg
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to send notification: {error_msg}")
            return False, None, error_msg
    
    @staticmethod
    def send_to_user(
        user: User,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image_url: Optional[str] = None,
        log_notification: bool = True
    ) -> Dict[str, Any]:
        """
        특정 사용자의 모든 활성 디바이스에 알림 전송
        
        Args:
            user: 사용자 객체
            title: 알림 제목
            body: 알림 내용
            data: 추가 데이터
            image_url: 이미지 URL
            log_notification: 알림 로그 저장 여부
        
        Returns:
            전송 결과 딕셔너리
        """
        # 활성 디바이스 토큰 조회
        device_tokens = DeviceToken.objects.filter(
            user=user,
            is_active=True
        )
        
        if not device_tokens.exists():
            return {
                'success': False,
                'message': 'No active device tokens found',
                'sent': 0,
                'failed': 0
            }
        
        sent_count = 0
        failed_count = 0
        results = []
        
        for device in device_tokens:
            success, message_id, error = FCMService.send_to_device(
                device_token=device.device_token,
                title=title,
                body=body,
                data=data,
                image_url=image_url
            )
            
            if success:
                sent_count += 1
                device.mark_as_used()
                
                # 성공 로그 저장
                if log_notification:
                    NotificationLog.objects.create(
                        user=user,
                        device_token=device,
                        title=title,
                        body=body,
                        data=data or {},
                        status=NotificationLog.Status.SENT,
                        fcm_message_id=message_id,
                        sent_at=timezone.now()
                    )
            else:
                failed_count += 1
                
                # 실패 로그 저장
                if log_notification:
                    NotificationLog.objects.create(
                        user=user,
                        device_token=device,
                        title=title,
                        body=body,
                        data=data or {},
                        status=NotificationLog.Status.FAILED,
                        error_message=error
                    )
                
                # 토큰이 무효한 경우 비활성화
                if 'unregistered' in error.lower() or 'invalid' in error.lower():
                    device.is_active = False
                    device.save()
            
            results.append({
                'device_token': device.device_token[:20] + '...',
                'device_type': device.device_type,
                'success': success,
                'error': error
            })
        
        return {
            'success': sent_count > 0,
            'message': f'Sent to {sent_count}/{sent_count + failed_count} devices',
            'sent': sent_count,
            'failed': failed_count,
            'results': results
        }
    
    @staticmethod
    def send_to_multiple_users(
        user_ids: List[int],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        여러 사용자에게 알림 전송
        
        Args:
            user_ids: 사용자 ID 목록
            title: 알림 제목
            body: 알림 내용
            data: 추가 데이터
            image_url: 이미지 URL
        
        Returns:
            전송 결과 딕셔너리
        """
        users = User.objects.filter(id__in=user_ids)
        
        total_sent = 0
        total_failed = 0
        user_results = []
        
        for user in users:
            result = FCMService.send_to_user(
                user=user,
                title=title,
                body=body,
                data=data,
                image_url=image_url
            )
            
            total_sent += result['sent']
            total_failed += result['failed']
            
            user_results.append({
                'user_id': user.id,
                'username': user.username,
                'sent': result['sent'],
                'failed': result['failed']
            })
        
        return {
            'success': total_sent > 0,
            'total_users': len(users),
            'total_sent': total_sent,
            'total_failed': total_failed,
            'details': user_results
        }
    
    @staticmethod
    def send_to_topic(
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        토픽 구독자들에게 알림 전송
        
        Args:
            topic: 토픽 이름
            title: 알림 제목
            body: 알림 내용
            data: 추가 데이터
            image_url: 이미지 URL
        
        Returns:
            (성공여부, FCM 메시지 ID, 에러 메시지)
        """
        try:
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            
            message = messaging.Message(
                notification=notification,
                data=data,
                topic=topic
            )
            
            response = messaging.send(message)
            logger.info(f"Successfully sent message to topic {topic}: {response}")
            
            return True, response, None
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to send notification to topic {topic}: {error_msg}")
            return False, None, error_msg
    
    @staticmethod
    def subscribe_to_topic(
        device_tokens: List[str],
        topic: str
    ) -> Dict[str, Any]:
        """
        디바이스 토큰들을 토픽에 구독
        
        Args:
            device_tokens: 디바이스 토큰 목록
            topic: 토픽 이름
        
        Returns:
            구독 결과 딕셔너리
        """
        try:
            response = messaging.subscribe_to_topic(device_tokens, topic)
            
            success_count = response.success_count
            failure_count = response.failure_count
            
            logger.info(
                f"Topic subscription - Topic: {topic}, "
                f"Success: {success_count}, Failed: {failure_count}"
            )
            
            return {
                'success': True,
                'success_count': success_count,
                'failure_count': failure_count,
                'errors': [error.reason for error in response.errors] if response.errors else []
            }
            
        except Exception as e:
            logger.error(f"Failed to subscribe to topic {topic}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def unsubscribe_from_topic(
        device_tokens: List[str],
        topic: str
    ) -> Dict[str, Any]:
        """
        디바이스 토큰들의 토픽 구독 해제
        
        Args:
            device_tokens: 디바이스 토큰 목록
            topic: 토픽 이름
        
        Returns:
            구독 해제 결과 딕셔너리
        """
        try:
            response = messaging.unsubscribe_from_topic(device_tokens, topic)
            
            return {
                'success': True,
                'success_count': response.success_count,
                'failure_count': response.failure_count
            }
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from topic {topic}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
```

### 서비스 레이어 설계 포인트

**1. 에러 처리**
```python
try:
    response = messaging.send(message)
    return True, response, None
except messaging.UnregisteredError:
    # 토큰 무효 - 비활성화 처리
    return False, None, "Token unregistered"
except Exception as e:
    # 일반 에러
    return False, None, str(e)
```
- FCM 특정 에러 처리
- 무효 토큰 자동 비활성화
- 로깅을 통한 디버깅 지원

**2. 플랫폼별 설정**
```python
# Android 설정
android_config = messaging.AndroidConfig(
    priority='high',
    notification=messaging.AndroidNotification(
        icon='notification_icon',
        color='#FF0000'
    )
)

# iOS 설정
apns_config = messaging.APNSConfig(...)
```
- 플랫폼별 최적화
- 커스텀 아이콘/사운드 지원
- 우선순위 설정

**3. 로깅 시스템**
```python
if log_notification:
    NotificationLog.objects.create(
        status=NotificationLog.Status.SENT,
        fcm_message_id=message_id
    )
```
- 전송 이력 추적
- 실패 알림 재전송
- 통계 및 분석 데이터

다음 섹션에서는 이 서비스를 사용하는 Django Ninja API를 구현하겠습니다.

## 🌐 Django Ninja API 엔드포인트

이제 서비스 로직을 노출하는 REST API를 Django Ninja로 구현합니다. 인증, 권한 검사, 에러 핸들링을 포함한 완전한 API를 만들어 보겠습니다.

**notifications/api.py**:
```python
from typing import List
from ninja import Router
from ninja.security import HttpBearer
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator

from .models import DeviceToken, NotificationLog
from .schemas import (
    DeviceTokenRegisterSchema,
    DeviceTokenResponse,
    SendNotificationSchema,
    SendBulkNotificationSchema,
    SendTopicNotificationSchema,
    SubscribeToTopicSchema,
    NotificationResponse,
    BulkNotificationResponse,
    ErrorResponse,
    SuccessResponse,
    NotificationLogResponse,
    PaginatedNotificationLogResponse
)
from .services import FCMService

User = get_user_model()

# 라우터 생성
router = Router(tags=["Push Notifications"])


# ============= 인증 =============

class AuthBearer(HttpBearer):
    """JWT Bearer 토큰 인증"""
    def authenticate(self, request, token):
        # 실제 환경에서는 JWT 토큰 검증 로직 구현
        # 예시로 간단히 사용자 조회
        try:
            # JWT 디코딩 로직 필요 (예: PyJWT 사용)
            # user_id = decode_jwt(token)
            # return User.objects.get(id=user_id)
            
            # 임시: 토큰이 있으면 첫 번째 사용자 반환 (개발용)
            return User.objects.first()
        except:
            return None


# ============= 디바이스 토큰 관리 =============

@router.post(
    "/devices/register",
    response={200: DeviceTokenResponse, 400: ErrorResponse},
    auth=AuthBearer(),
    summary="디바이스 토큰 등록",
    description="사용자의 디바이스 FCM 토큰을 등록합니다."
)
def register_device_token(request, payload: DeviceTokenRegisterSchema):
    """
    디바이스 토큰 등록
    
    - 이미 존재하는 토큰은 업데이트
    - 새로운 토큰은 생성
    """
    try:
        device_token, created = DeviceToken.objects.update_or_create(
            user=request.auth,
            device_token=payload.device_token,
            defaults={
                'device_type': payload.device_type,
                'device_name': payload.device_name or '',
                'is_active': True
            }
        )
        
        return 200, DeviceTokenResponse(
            id=device_token.id,
            device_token=device_token.device_token,
            device_type=device_token.device_type,
            device_name=device_token.device_name,
            is_active=device_token.is_active,
            created_at=device_token.created_at,
            last_used_at=device_token.last_used_at
        )
    
    except Exception as e:
        return 400, ErrorResponse(error=str(e))


@router.get(
    "/devices",
    response=List[DeviceTokenResponse],
    auth=AuthBearer(),
    summary="내 디바이스 목록 조회",
    description="현재 사용자의 등록된 모든 디바이스 토큰 목록을 조회합니다."
)
def list_my_devices(request):
    """내 디바이스 목록 조회"""
    devices = DeviceToken.objects.filter(user=request.auth)
    
    return [
        DeviceTokenResponse(
            id=device.id,
            device_token=device.device_token,
            device_type=device.device_type,
            device_name=device.device_name,
            is_active=device.is_active,
            created_at=device.created_at,
            last_used_at=device.last_used_at
        )
        for device in devices
    ]


@router.delete(
    "/devices/{device_id}",
    response={200: SuccessResponse, 404: ErrorResponse},
    auth=AuthBearer(),
    summary="디바이스 토큰 삭제",
    description="특정 디바이스 토큰을 삭제합니다."
)
def delete_device_token(request, device_id: int):
    """디바이스 토큰 삭제"""
    try:
        device = get_object_or_404(
            DeviceToken,
            id=device_id,
            user=request.auth
        )
        device.delete()
        
        return 200, SuccessResponse(
            message="Device token deleted successfully"
        )
    
    except Exception as e:
        return 404, ErrorResponse(error=str(e))


# ============= 알림 전송 =============

@router.post(
    "/send",
    response={200: NotificationResponse, 400: ErrorResponse},
    auth=AuthBearer(),
    summary="단일 사용자에게 알림 전송",
    description="특정 사용자의 모든 활성 디바이스에 푸시 알림을 전송합니다."
)
def send_notification(request, payload: SendNotificationSchema):
    """단일 사용자에게 알림 전송"""
    try:
        user = get_object_or_404(User, id=payload.user_id)
        
        result = FCMService.send_to_user(
            user=user,
            title=payload.title,
            body=payload.body,
            data=payload.data,
            image_url=payload.image_url
        )
        
        if result['success']:
            return 200, NotificationResponse(
                success=True,
                message=result['message']
            )
        else:
            return 400, ErrorResponse(
                error=result['message']
            )
    
    except Exception as e:
        return 400, ErrorResponse(error=str(e))


@router.post(
    "/send/bulk",
    response={200: BulkNotificationResponse, 400: ErrorResponse},
    auth=AuthBearer(),
    summary="여러 사용자에게 알림 전송",
    description="여러 사용자에게 동시에 푸시 알림을 전송합니다. (최대 1000명)"
)
def send_bulk_notification(request, payload: SendBulkNotificationSchema):
    """여러 사용자에게 알림 전송"""
    try:
        result = FCMService.send_to_multiple_users(
            user_ids=payload.user_ids,
            title=payload.title,
            body=payload.body,
            data=payload.data
        )
        
        return 200, BulkNotificationResponse(
            success=result['success'],
            total=result['total_users'],
            sent=result['total_sent'],
            failed=result['total_failed'],
            details=result['details']
        )
    
    except Exception as e:
        return 400, ErrorResponse(error=str(e))


@router.post(
    "/send/topic",
    response={200: NotificationResponse, 400: ErrorResponse},
    auth=AuthBearer(),
    summary="토픽 구독자들에게 알림 전송",
    description="특정 토픽을 구독한 모든 사용자에게 푸시 알림을 전송합니다."
)
def send_topic_notification(request, payload: SendTopicNotificationSchema):
    """토픽 구독자들에게 알림 전송"""
    try:
        success, message_id, error = FCMService.send_to_topic(
            topic=payload.topic,
            title=payload.title,
            body=payload.body,
            data=payload.data
        )
        
        if success:
            return 200, NotificationResponse(
                success=True,
                message=f"Notification sent to topic: {payload.topic}",
                fcm_message_id=message_id
            )
        else:
            return 400, ErrorResponse(error=error)
    
    except Exception as e:
        return 400, ErrorResponse(error=str(e))


# ============= 토픽 구독 관리 =============

@router.post(
    "/topics/subscribe",
    response={200: SuccessResponse, 400: ErrorResponse},
    auth=AuthBearer(),
    summary="토픽 구독",
    description="디바이스 토큰을 특정 토픽에 구독합니다."
)
def subscribe_to_topic(request, payload: SubscribeToTopicSchema):
    """토픽 구독"""
    try:
        # 디바이스 토큰이 제공되지 않으면 사용자의 모든 토큰 사용
        if payload.device_tokens:
            tokens = payload.device_tokens
        else:
            devices = DeviceToken.objects.filter(
                user=request.auth,
                is_active=True
            )
            tokens = [device.device_token for device in devices]
        
        if not tokens:
            return 400, ErrorResponse(
                error="No device tokens available"
            )
        
        result = FCMService.subscribe_to_topic(
            device_tokens=tokens,
            topic=payload.topic
        )
        
        if result['success']:
            return 200, SuccessResponse(
                message=f"Subscribed to topic: {payload.topic}",
                data={
                    'success_count': result['success_count'],
                    'failure_count': result['failure_count']
                }
            )
        else:
            return 400, ErrorResponse(error=result['error'])
    
    except Exception as e:
        return 400, ErrorResponse(error=str(e))


@router.post(
    "/topics/unsubscribe",
    response={200: SuccessResponse, 400: ErrorResponse},
    auth=AuthBearer(),
    summary="토픽 구독 해제",
    description="디바이스 토큰의 특정 토픽 구독을 해제합니다."
)
def unsubscribe_from_topic(request, payload: SubscribeToTopicSchema):
    """토픽 구독 해제"""
    try:
        if payload.device_tokens:
            tokens = payload.device_tokens
        else:
            devices = DeviceToken.objects.filter(
                user=request.auth,
                is_active=True
            )
            tokens = [device.device_token for device in devices]
        
        result = FCMService.unsubscribe_from_topic(
            device_tokens=tokens,
            topic=payload.topic
        )
        
        if result['success']:
            return 200, SuccessResponse(
                message=f"Unsubscribed from topic: {payload.topic}",
                data={
                    'success_count': result['success_count'],
                    'failure_count': result['failure_count']
                }
            )
        else:
            return 400, ErrorResponse(error=result['error'])
    
    except Exception as e:
        return 400, ErrorResponse(error=str(e))


# ============= 알림 히스토리 =============

@router.get(
    "/history",
    response=PaginatedNotificationLogResponse,
    auth=AuthBearer(),
    summary="내 알림 히스토리 조회",
    description="현재 사용자가 받은 푸시 알림 히스토리를 조회합니다."
)
def get_notification_history(request, page: int = 1, page_size: int = 20):
    """내 알림 히스토리 조회"""
    logs = NotificationLog.objects.filter(
        user=request.auth
    ).order_by('-created_at')
    
    paginator = Paginator(logs, page_size)
    page_obj = paginator.get_page(page)
    
    return PaginatedNotificationLogResponse(
        count=paginator.count,
        next=f"?page={page + 1}" if page_obj.has_next() else None,
        previous=f"?page={page - 1}" if page_obj.has_previous() else None,
        results=[
            NotificationLogResponse.from_orm(log)
            for log in page_obj
        ]
    )
```

### API 통합

**config/urls.py**:
```python
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from notifications.api import router as notifications_router

# NinjaAPI 인스턴스 생성
api = NinjaAPI(
    title="Push Notification API",
    version="1.0.0",
    description="Django Ninja를 사용한 FCM 푸시 알림 API"
)

# 라우터 등록
api.add_router("/notifications/", notifications_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
```

### API 테스트

**서버 실행**:
```bash
python manage.py runserver
```

**Swagger UI 접속**:
```
http://localhost:8000/api/docs
```

Django Ninja는 자동으로 Swagger UI를 제공하여 API를 쉽게 테스트할 수 있습니다.

**cURL 예시**:
```bash
# 1. 디바이스 토큰 등록
curl -X POST http://localhost:8000/api/notifications/devices/register \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_token": "fcm_device_token_here",
    "device_type": "ANDROID",
    "device_name": "Samsung Galaxy S21"
  }'

# 2. 알림 전송
curl -X POST http://localhost:8000/api/notifications/send \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "title": "새로운 메시지",
    "body": "안녕하세요! 새로운 메시지가 도착했습니다.",
    "data": {
      "type": "message",
      "message_id": "123"
    }
  }'

# 3. 토픽 구독
curl -X POST http://localhost:8000/api/notifications/topics/subscribe \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "news"
  }'

# 4. 토픽 알림 전송
curl -X POST http://localhost:8000/api/notifications/send/topic \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "news",
    "title": "속보",
    "body": "중요한 뉴스가 있습니다!"
  }'
```

### API 설계 포인트

**1. RESTful 설계**
```python
POST   /api/notifications/devices/register   # 토큰 등록
GET    /api/notifications/devices            # 목록 조회
DELETE /api/notifications/devices/{id}       # 삭제
POST   /api/notifications/send               # 알림 전송
```
- 명확한 리소스 경로
- HTTP 메서드 의미론적 사용
- 일관된 응답 형식

**2. 인증 및 권한**
```python
@router.post("/send", auth=AuthBearer())
def send_notification(request, payload):
    # request.auth로 현재 사용자 접근
    user = request.auth
```
- Bearer 토큰 인증
- 엔드포인트별 인증 요구
- 사용자별 리소스 격리

**3. 자동 문서화**
```python
@router.post(
    "/send",
    summary="단일 사용자에게 알림 전송",
    description="특정 사용자의 모든 활성 디바이스에..."
)
```
- Swagger UI 자동 생성
- API 명세 자동 문서화
- 대화형 테스트 환경

다음 섹션에서는 모바일 클라이언트 통합 방법을 알아보겠습니다.

## 📱 모바일 클라이언트 통합

Django API가 준비되었으니 이제 Android, iOS, Web 클라이언트에서 FCM을 통합하는 방법을 알아보겠습니다.

### 1. Android (Kotlin) 통합

**build.gradle (Project level)**:
```gradle
buildscript {
    dependencies {
        classpath 'com.google.gms:google-services:4.4.0'
    }
}
```

**build.gradle (App level)**:
```gradle
plugins {
    id 'com.android.application'
    id 'com.google.gms.google-services'
}

dependencies {
    implementation platform('com.google.firebase:firebase-bom:32.7.0')
    implementation 'com.google.firebase:firebase-messaging-ktx'
    implementation 'com.squareup.retrofit2:retrofit:2.9.0'
    implementation 'com.squareup.retrofit2:converter-gson:2.9.0'
}
```

**MyFirebaseMessagingService.kt**:
```kotlin
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import android.util.Log

class MyFirebaseMessagingService : FirebaseMessagingService() {
    
    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.d(TAG, "New FCM token: $token")
        
        // Django API에 토큰 등록
        sendTokenToServer(token)
    }
    
    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        
        // 알림 제목과 본문
        val title = message.notification?.title ?: "알림"
        val body = message.notification?.body ?: ""
        
        // 커스텀 데이터
        val data = message.data
        val messageType = data["type"]
        val messageId = data["message_id"]
        
        Log.d(TAG, "Message received: $title - $body")
        Log.d(TAG, "Data: type=$messageType, id=$messageId")
        
        // 알림 표시
        showNotification(title, body, data)
    }
    
    private fun sendTokenToServer(token: String) {
        val api = RetrofitClient.create()
        val deviceInfo = DeviceTokenRequest(
            deviceToken = token,
            deviceType = "ANDROID",
            deviceName = "${Build.MANUFACTURER} ${Build.MODEL}"
        )
        
        api.registerDeviceToken(deviceInfo).enqueue(object : Callback<DeviceTokenResponse> {
            override fun onResponse(call: Call<DeviceTokenResponse>, response: Response<DeviceTokenResponse>) {
                if (response.isSuccessful) {
                    Log.d(TAG, "Token registered successfully")
                } else {
                    Log.e(TAG, "Failed to register token: ${response.code()}")
                }
            }
            
            override fun onFailure(call: Call<DeviceTokenResponse>, t: Throwable) {
                Log.e(TAG, "Error registering token", t)
            }
        })
    }
    
    private fun showNotification(title: String, body: String, data: Map<String, String>) {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        
        // Android 8.0 이상에서는 채널 필요
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Push Notifications",
                NotificationManager.IMPORTANCE_HIGH
            )
            notificationManager.createNotificationChannel(channel)
        }
        
        // 알림 클릭 시 이동할 인텐트
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            putExtra("type", data["type"])
            putExtra("message_id", data["message_id"])
        }
        
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(title)
            .setContentText(body)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()
        
        notificationManager.notify(System.currentTimeMillis().toInt(), notification)
    }
    
    companion object {
        private const val TAG = "FCMService"
        private const val CHANNEL_ID = "push_notifications"
    }
}
```

**AndroidManifest.xml**:
```xml
<manifest>
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    
    <application>
        <service
            android:name=".MyFirebaseMessagingService"
            android:exported="false">
            <intent-filter>
                <action android:name="com.google.firebase.MESSAGING_EVENT" />
            </intent-filter>
        </service>
        
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_icon"
            android:resource="@drawable/ic_notification" />
        
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_color"
            android:resource="@color/colorPrimary" />
    </application>
</manifest>
```

### 2. iOS (Swift) 통합

**Podfile**:
```ruby
platform :ios, '13.0'
use_frameworks!

target 'YourApp' do
  pod 'Firebase/Messaging'
  pod 'Alamofire', '~> 5.8'
end
```

**AppDelegate.swift**:
```swift
import UIKit
import Firebase
import UserNotifications

@main
class AppDelegate: UIResponder, UIApplicationDelegate, UNUserNotificationCenterDelegate, MessagingDelegate {
    
    func application(_ application: UIApplication,
                    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        
        // Firebase 초기화
        FirebaseApp.configure()
        
        // 알림 권한 요청
        UNUserNotificationCenter.current().delegate = self
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { granted, error in
            print("Notification permission granted: \(granted)")
        }
        
        application.registerForRemoteNotifications()
        
        // FCM 델리게이트 설정
        Messaging.messaging().delegate = self
        
        return true
    }
    
    // FCM 토큰 업데이트
    func messaging(_ messaging: Messaging, didReceiveRegistrationToken fcmToken: String?) {
        print("FCM token: \(fcmToken ?? "")")
        
        if let token = fcmToken {
            sendTokenToServer(token: token)
        }
    }
    
    // 포그라운드 알림 수신
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                               willPresent notification: UNNotification,
                               withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        
        let userInfo = notification.request.content.userInfo
        print("Foreground notification received: \(userInfo)")
        
        // iOS 14 이상
        completionHandler([[.banner, .badge, .sound]])
    }
    
    // 알림 클릭 시
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                               didReceive response: UNNotificationResponse,
                               withCompletionHandler completionHandler: @escaping () -> Void) {
        
        let userInfo = response.notification.request.content.userInfo
        
        if let type = userInfo["type"] as? String,
           let messageId = userInfo["message_id"] as? String {
            print("Notification tapped: type=\(type), id=\(messageId)")
            
            // 적절한 화면으로 이동
            handleNotificationTap(type: type, messageId: messageId)
        }
        
        completionHandler()
    }
    
    private func sendTokenToServer(token: String) {
        let url = "https://your-api.com/api/notifications/devices/register"
        let parameters: [String: Any] = [
            "device_token": token,
            "device_type": "IOS",
            "device_name": UIDevice.current.name
        ]
        
        AF.request(url, method: .post, parameters: parameters, encoding: JSONEncoding.default)
            .validate()
            .responseJSON { response in
                switch response.result {
                case .success:
                    print("Token registered successfully")
                case .failure(let error):
                    print("Error registering token: \(error)")
                }
            }
    }
    
    private func handleNotificationTap(type: String, messageId: String) {
        // 타입에 따라 적절한 화면으로 이동
        switch type {
        case "message":
            // 메시지 화면으로 이동
            break
        case "order":
            // 주문 상세 화면으로 이동
            break
        default:
            break
        }
    }
}
```

### 3. Web (JavaScript) 통합

**firebase-config.js**:
```javascript
import { initializeApp } from 'firebase/app';
import { getMessaging, getToken, onMessage } from 'firebase/messaging';

const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "your-app.firebaseapp.com",
  projectId: "your-project-id",
  storageBucket: "your-app.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abcdef"
};

// Firebase 초기화
const app = initializeApp(firebaseConfig);
const messaging = getMessaging(app);

// FCM 토큰 가져오기
export async function requestNotificationPermission() {
  try {
    const permission = await Notification.requestPermission();
    
    if (permission === 'granted') {
      console.log('Notification permission granted');
      
      const token = await getToken(messaging, {
        vapidKey: 'YOUR_VAPID_KEY'
      });
      
      console.log('FCM Token:', token);
      
      // Django API에 토큰 등록
      await registerTokenToServer(token);
      
      return token;
    } else {
      console.log('Notification permission denied');
      return null;
    }
  } catch (error) {
    console.error('Error getting FCM token:', error);
    return null;
  }
}

// 포그라운드 메시지 수신
export function onMessageListener() {
  return new Promise((resolve) => {
    onMessage(messaging, (payload) => {
      console.log('Message received:', payload);
      resolve(payload);
    });
  });
}

// 서버에 토큰 등록
async function registerTokenToServer(token) {
  try {
    const response = await fetch('https://your-api.com/api/notifications/devices/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('authToken')}`
      },
      body: JSON.stringify({
        device_token: token,
        device_type: 'WEB',
        device_name: navigator.userAgent
      })
    });
    
    if (response.ok) {
      console.log('Token registered successfully');
    } else {
      console.error('Failed to register token:', response.status);
    }
  } catch (error) {
    console.error('Error registering token:', error);
  }
}
```

**firebase-messaging-sw.js** (Service Worker):
```javascript
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "YOUR_API_KEY",
  authDomain: "your-app.firebaseapp.com",
  projectId: "your-project-id",
  storageBucket: "your-app.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abcdef"
});

const messaging = firebase.messaging();

// 백그라운드 메시지 수신
messaging.onBackgroundMessage((payload) => {
  console.log('Background message received:', payload);
  
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    icon: '/firebase-logo.png',
    badge: '/badge-icon.png',
    data: payload.data
  };
  
  self.registration.showNotification(notificationTitle, notificationOptions);
});

// 알림 클릭 이벤트
self.addEventListener('notificationclick', (event) => {
  console.log('Notification clicked:', event.notification.data);
  
  event.notification.close();
  
  // 특정 URL로 이동
  const urlToOpen = event.notification.data.url || '/';
  
  event.waitUntil(
    clients.openWindow(urlToOpen)
  );
});
```

**React 컴포넌트 예시**:
```jsx
import React, { useEffect, useState } from 'react';
import { requestNotificationPermission, onMessageListener } from './firebase-config';

function NotificationHandler() {
  const [notification, setNotification] = useState(null);
  
  useEffect(() => {
    // 알림 권한 요청 및 토큰 등록
    requestNotificationPermission();
    
    // 포그라운드 메시지 리스너
    onMessageListener()
      .then((payload) => {
        setNotification({
          title: payload.notification.title,
          body: payload.notification.body
        });
        
        // 토스트 알림 표시
        showToast(payload.notification.title, payload.notification.body);
      })
      .catch((err) => console.error('Failed to receive message:', err));
  }, []);
  
  const showToast = (title, body) => {
    // 토스트 알림 라이브러리 사용 (예: react-toastify)
    console.log(`Toast: ${title} - ${body}`);
  };
  
  return (
    <div>
      {notification && (
        <div className="notification-toast">
          <h4>{notification.title}</h4>
          <p>{notification.body}</p>
        </div>
      )}
    </div>
  );
}

export default NotificationHandler;
```

### 클라이언트 통합 체크리스트

**Android**:
- ✅ Firebase SDK 통합
- ✅ google-services.json 추가
- ✅ FirebaseMessagingService 구현
- ✅ 알림 채널 생성 (Android 8.0+)
- ✅ 알림 권한 요청 (Android 13+)

**iOS**:
- ✅ Firebase SDK 통합
- ✅ GoogleService-Info.plist 추가
- ✅ APNs 인증서 설정
- ✅ MessagingDelegate 구현
- ✅ 알림 권한 요청

**Web**:
- ✅ Firebase SDK 통합
- ✅ VAPID 키 설정
- ✅ Service Worker 등록
- ✅ 알림 권한 요청
- ✅ HTTPS 필수

다음 섹션에서는 알림 클릭 시 특정 페이지로 이동하는 딥링킹을 구현하겠습니다.

## 🔗 Deep Linking: 알림 클릭 시 특정 페이지로 이동

푸시 알림의 진정한 가치는 사용자를 적절한 화면으로 안내하는 데 있습니다. 주문 완료 알림을 클릭하면 주문 상세 페이지로, 새 메시지 알림을 클릭하면 채팅방으로 바로 이동해야 합니다. 이를 구현하는 방법을 플랫폼별로 알아보겠습니다.

### 1. 딥링크 URL 스키마 설계

먼저 일관된 딥링크 구조를 설계합니다. 모든 플랫폼에서 동일한 데이터 구조를 사용하면 유지보수가 쉽습니다.

**딥링크 스키마 예시**:
```python
# notifications/deeplink.py

class DeepLinkBuilder:
    """딥링크 URL 생성기"""
    
    # 앱 URL 스키마
    SCHEME = "myapp://"  # 또는 "https://yourdomain.com/app/"
    
    # 라우트 정의
    ROUTES = {
        'home': '',
        'profile': 'profile/{user_id}',
        'order_detail': 'orders/{order_id}',
        'product_detail': 'products/{product_id}',
        'chat': 'chats/{chat_id}',
        'notification_center': 'notifications',
        'promotion': 'promotions/{promotion_id}',
        'article': 'articles/{article_id}',
    }
    
    @classmethod
    def build(cls, route_name: str, **params) -> dict:
        """
        딥링크 데이터 생성
        
        Args:
            route_name: 라우트 이름 (예: 'order_detail')
            **params: URL 파라미터 (예: order_id=123)
        
        Returns:
            FCM data payload
        """
        if route_name not in cls.ROUTES:
            raise ValueError(f"Unknown route: {route_name}")
        
        route_template = cls.ROUTES[route_name]
        path = route_template.format(**params) if params else route_template
        
        return {
            'click_action': 'OPEN_ACTIVITY',
            'route': route_name,
            'path': path,
            'url': f"{cls.SCHEME}{path}",
            **{k: str(v) for k, v in params.items()}
        }
    
    @classmethod
    def for_order(cls, order_id: int) -> dict:
        """주문 상세 딥링크"""
        return cls.build('order_detail', order_id=order_id)
    
    @classmethod
    def for_product(cls, product_id: int) -> dict:
        """상품 상세 딥링크"""
        return cls.build('product_detail', product_id=product_id)
    
    @classmethod
    def for_chat(cls, chat_id: int) -> dict:
        """채팅방 딥링크"""
        return cls.build('chat', chat_id=chat_id)
    
    @classmethod
    def for_profile(cls, user_id: int) -> dict:
        """프로필 딥링크"""
        return cls.build('profile', user_id=user_id)


# 사용 예시
def send_order_notification(order):
    """주문 알림 with 딥링크"""
    deeplink_data = DeepLinkBuilder.for_order(order.id)
    
    FCMService.send_to_user(
        user=order.user,
        title="주문이 완료되었습니다",
        body=f"{order.product_name} 주문이 접수되었습니다.",
        data=deeplink_data
    )
```

### 2. Android 딥링크 구현

Android에서는 Intent와 Activity를 통해 딥링크를 처리합니다.

**AndroidManifest.xml**:
```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application>
        <!-- MainActivity: 앱 진입점 -->
        <activity
            android:name=".MainActivity"
            android:launchMode="singleTop"
            android:exported="true">
            
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
            
            <!-- 커스텀 URL 스키마 (myapp://) -->
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="myapp" />
            </intent-filter>
            
            <!-- App Links (https://yourdomain.com/app/*) -->
            <intent-filter android:autoVerify="true">
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data 
                    android:scheme="https"
                    android:host="yourdomain.com"
                    android:pathPrefix="/app" />
            </intent-filter>
        </activity>
    </application>
</manifest>
```

**MyFirebaseMessagingService.kt** (수정):
```kotlin
class MyFirebaseMessagingService : FirebaseMessagingService() {
    
    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        
        val title = message.notification?.title ?: "알림"
        val body = message.notification?.body ?: ""
        val data = message.data
        
        Log.d(TAG, "Message data: $data")
        
        // 딥링크 데이터 추출
        val route = data["route"]
        val path = data["path"]
        val url = data["url"]
        
        // 알림 표시 (딥링크 포함)
        showNotification(title, body, data)
    }
    
    private fun showNotification(
        title: String,
        body: String,
        data: Map<String, String>
    ) {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) 
            as NotificationManager
        
        // 알림 클릭 시 실행할 Intent 생성
        val intent = createDeepLinkIntent(data)
        
        val pendingIntent = PendingIntent.getActivity(
            this,
            System.currentTimeMillis().toInt(),
            intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(title)
            .setContentText(body)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)  // 딥링크 Intent 설정
            .build()
        
        notificationManager.notify(System.currentTimeMillis().toInt(), notification)
    }
    
    private fun createDeepLinkIntent(data: Map<String, String>): Intent {
        """딥링크 Intent 생성"""
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            
            // 모든 딥링크 데이터를 Intent extras로 추가
            data.forEach { (key, value) ->
                putExtra(key, value)
            }
        }
        
        return intent
    }
}
```

**MainActivity.kt**:
```kotlin
import android.os.Bundle
import android.net.Uri
import androidx.appcompat.app.AppCompatActivity
import androidx.navigation.findNavController

class MainActivity : AppCompatActivity() {
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        // 딥링크 처리
        handleDeepLink(intent)
    }
    
    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        setIntent(intent)
        
        // 앱이 이미 실행 중일 때 딥링크 처리
        intent?.let { handleDeepLink(it) }
    }
    
    private fun handleDeepLink(intent: Intent) {
        // 방법 1: Intent extras에서 데이터 가져오기 (FCM data)
        val route = intent.getStringExtra("route")
        val orderId = intent.getStringExtra("order_id")
        val productId = intent.getStringExtra("product_id")
        val chatId = intent.getStringExtra("chat_id")
        
        // 방법 2: URL에서 데이터 파싱 (URL scheme)
        val data: Uri? = intent.data
        
        when {
            // FCM data 기반 라우팅
            route == "order_detail" && orderId != null -> {
                navigateToOrderDetail(orderId)
            }
            route == "product_detail" && productId != null -> {
                navigateToProductDetail(productId)
            }
            route == "chat" && chatId != null -> {
                navigateToChat(chatId)
            }
            
            // URL scheme 기반 라우팅 (myapp://orders/123)
            data != null -> {
                handleUriDeepLink(data)
            }
        }
    }
    
    private fun handleUriDeepLink(uri: Uri) {
        val path = uri.path ?: return
        val segments = path.split("/").filter { it.isNotEmpty() }
        
        when {
            segments.size >= 2 && segments[0] == "orders" -> {
                navigateToOrderDetail(segments[1])
            }
            segments.size >= 2 && segments[0] == "products" -> {
                navigateToProductDetail(segments[1])
            }
            segments.size >= 2 && segments[0] == "chats" -> {
                navigateToChat(segments[1])
            }
            segments.size >= 2 && segments[0] == "profile" -> {
                navigateToProfile(segments[1])
            }
        }
    }
    
    private fun navigateToOrderDetail(orderId: String) {
        val navController = findNavController(R.id.nav_host_fragment)
        val bundle = Bundle().apply {
            putString("order_id", orderId)
        }
        navController.navigate(R.id.orderDetailFragment, bundle)
    }
    
    private fun navigateToProductDetail(productId: String) {
        val navController = findNavController(R.id.nav_host_fragment)
        val bundle = Bundle().apply {
            putString("product_id", productId)
        }
        navController.navigate(R.id.productDetailFragment, bundle)
    }
    
    private fun navigateToChat(chatId: String) {
        val navController = findNavController(R.id.nav_host_fragment)
        val bundle = Bundle().apply {
            putString("chat_id", chatId)
        }
        navController.navigate(R.id.chatFragment, bundle)
    }
    
    private fun navigateToProfile(userId: String) {
        val navController = findNavController(R.id.nav_host_fragment)
        val bundle = Bundle().apply {
            putString("user_id", userId)
        }
        navController.navigate(R.id.profileFragment, bundle)
    }
}
```

### 3. iOS 딥링크 구현

iOS에서는 Universal Links와 URL Schemes를 사용합니다.

**Info.plist**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
    <!-- URL Schemes (myapp://) -->
    <key>CFBundleURLTypes</key>
    <array>
        <dict>
            <key>CFBundleURLSchemes</key>
            <array>
                <string>myapp</string>
            </array>
            <key>CFBundleURLName</key>
            <string>com.yourcompany.myapp</string>
        </dict>
    </array>
    
    <!-- Universal Links (https://yourdomain.com/app/*) -->
    <key>com.apple.developer.associated-domains</key>
    <array>
        <string>applinks:yourdomain.com</string>
    </array>
</dict>
</plist>
```

**AppDelegate.swift** (수정):
```swift
import UIKit
import Firebase

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    
    var window: UIWindow?
    
    func application(_ application: UIApplication,
                    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        
        FirebaseApp.configure()
        UNUserNotificationCenter.current().delegate = self
        Messaging.messaging().delegate = self
        
        // 앱이 종료 상태에서 알림 클릭으로 실행된 경우
        if let notification = launchOptions?[.remoteNotification] as? [String: Any] {
            handleNotificationData(notification)
        }
        
        return true
    }
    
    // URL Scheme 처리 (myapp://orders/123)
    func application(_ app: UIApplication,
                    open url: URL,
                    options: [UIApplication.OpenURLOptionsKey : Any] = [:]) -> Bool {
        
        print("Opening URL: \(url)")
        handleDeepLink(url: url)
        return true
    }
    
    // Universal Links 처리 (https://yourdomain.com/app/orders/123)
    func application(_ application: UIApplication,
                    continue userActivity: NSUserActivity,
                    restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void) -> Bool {
        
        guard userActivity.activityType == NSUserActivityTypeBrowsingWeb,
              let url = userActivity.webpageURL else {
            return false
        }
        
        print("Universal Link: \(url)")
        handleDeepLink(url: url)
        return true
    }
    
    private func handleDeepLink(url: URL) {
        """URL을 파싱하여 적절한 화면으로 이동"""
        let pathComponents = url.pathComponents.filter { $0 != "/" }
        
        guard pathComponents.count >= 2 else { return }
        
        let screen = pathComponents[0]
        let id = pathComponents[1]
        
        switch screen {
        case "orders":
            navigateToOrderDetail(orderId: id)
        case "products":
            navigateToProductDetail(productId: id)
        case "chats":
            navigateToChat(chatId: id)
        case "profile":
            navigateToProfile(userId: id)
        default:
            break
        }
    }
    
    private func handleNotificationData(_ userInfo: [String: Any]) {
        """FCM data에서 딥링크 정보 추출 및 처리"""
        
        // 딥링크 데이터 추출
        guard let route = userInfo["route"] as? String else { return }
        
        switch route {
        case "order_detail":
            if let orderId = userInfo["order_id"] as? String {
                navigateToOrderDetail(orderId: orderId)
            }
        case "product_detail":
            if let productId = userInfo["product_id"] as? String {
                navigateToProductDetail(productId: productId)
            }
        case "chat":
            if let chatId = userInfo["chat_id"] as? String {
                navigateToChat(chatId: chatId)
            }
        case "profile":
            if let userId = userInfo["user_id"] as? String {
                navigateToProfile(userId: userId)
            }
        default:
            break
        }
    }
    
    // MARK: - Navigation Methods
    
    private func navigateToOrderDetail(orderId: String) {
        DispatchQueue.main.async {
            guard let navigationController = self.window?.rootViewController as? UINavigationController else { return }
            
            let storyboard = UIStoryboard(name: "Main", bundle: nil)
            if let orderDetailVC = storyboard.instantiateViewController(withIdentifier: "OrderDetailViewController") as? OrderDetailViewController {
                orderDetailVC.orderId = orderId
                navigationController.pushViewController(orderDetailVC, animated: true)
            }
        }
    }
    
    private func navigateToProductDetail(productId: String) {
        DispatchQueue.main.async {
            guard let navigationController = self.window?.rootViewController as? UINavigationController else { return }
            
            let storyboard = UIStoryboard(name: "Main", bundle: nil)
            if let productDetailVC = storyboard.instantiateViewController(withIdentifier: "ProductDetailViewController") as? ProductDetailViewController {
                productDetailVC.productId = productId
                navigationController.pushViewController(productDetailVC, animated: true)
            }
        }
    }
    
    private func navigateToChat(chatId: String) {
        DispatchQueue.main.async {
            guard let navigationController = self.window?.rootViewController as? UINavigationController else { return }
            
            let storyboard = UIStoryboard(name: "Main", bundle: nil)
            if let chatVC = storyboard.instantiateViewController(withIdentifier: "ChatViewController") as? ChatViewController {
                chatVC.chatId = chatId
                navigationController.pushViewController(chatVC, animated: true)
            }
        }
    }
    
    private func navigateToProfile(userId: String) {
        DispatchQueue.main.async {
            guard let navigationController = self.window?.rootViewController as? UINavigationController else { return }
            
            let storyboard = UIStoryboard(name: "Main", bundle: nil)
            if let profileVC = storyboard.instantiateViewController(withIdentifier: "ProfileViewController") as? ProfileViewController {
                profileVC.userId = userId
                navigationController.pushViewController(profileVC, animated: true)
            }
        }
    }
}

extension AppDelegate: UNUserNotificationCenterDelegate {
    
    // 알림 클릭 시 (포그라운드/백그라운드 모두)
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                               didReceive response: UNNotificationResponse,
                               withCompletionHandler completionHandler: @escaping () -> Void) {
        
        let userInfo = response.notification.request.content.userInfo
        print("Notification tapped with data: \(userInfo)")
        
        // 딥링크 처리
        handleNotificationData(userInfo)
        
        completionHandler()
    }
}
```

**SwiftUI 버전**:
```swift
import SwiftUI

@main
struct MyApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var navigationManager = NavigationManager()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(navigationManager)
                .onOpenURL { url in
                    // URL Scheme / Universal Link 처리
                    navigationManager.handleDeepLink(url: url)
                }
        }
    }
}

class NavigationManager: ObservableObject {
    @Published var selectedTab: Tab = .home
    @Published var orderToShow: String?
    @Published var productToShow: String?
    @Published var chatToShow: String?
    
    enum Tab {
        case home, orders, products, profile
    }
    
    func handleDeepLink(url: URL) {
        let pathComponents = url.pathComponents.filter { $0 != "/" }
        guard pathComponents.count >= 2 else { return }
        
        let screen = pathComponents[0]
        let id = pathComponents[1]
        
        switch screen {
        case "orders":
            selectedTab = .orders
            orderToShow = id
        case "products":
            selectedTab = .products
            productToShow = id
        case "chats":
            chatToShow = id
        default:
            break
        }
    }
    
    func handleNotificationData(_ userInfo: [String: Any]) {
        guard let route = userInfo["route"] as? String else { return }
        
        switch route {
        case "order_detail":
            if let orderId = userInfo["order_id"] as? String {
                selectedTab = .orders
                orderToShow = orderId
            }
        case "product_detail":
            if let productId = userInfo["product_id"] as? String {
                selectedTab = .products
                productToShow = productId
            }
        default:
            break
        }
    }
}
```

### 4. Web 딥링크 구현

웹에서는 URL 라우팅으로 처리합니다.

**firebase-config.js** (수정):
```javascript
import { getMessaging, onMessage } from 'firebase/messaging';
import { useNavigate } from 'react-router-dom';

// 포그라운드 메시지 처리
export function setupNotificationHandlers(navigate) {
  const messaging = getMessaging();
  
  onMessage(messaging, (payload) => {
    console.log('Foreground message received:', payload);
    
    const { title, body } = payload.notification;
    const data = payload.data;
    
    // 토스트 알림 표시
    showToast(title, body, () => {
      handleNotificationClick(data, navigate);
    });
  });
}

function handleNotificationClick(data, navigate) {
  """알림 클릭 시 라우팅"""
  const { route, order_id, product_id, chat_id, user_id } = data;
  
  switch (route) {
    case 'order_detail':
      navigate(`/orders/${order_id}`);
      break;
    case 'product_detail':
      navigate(`/products/${product_id}`);
      break;
    case 'chat':
      navigate(`/chats/${chat_id}`);
      break;
    case 'profile':
      navigate(`/profile/${user_id}`);
      break;
    default:
      navigate('/');
  }
}
```

**firebase-messaging-sw.js** (수정):
```javascript
// Service Worker에서 백그라운드 알림 클릭 처리

messaging.onBackgroundMessage((payload) => {
  const { title, body } = payload.notification;
  const data = payload.data;
  
  const notificationOptions = {
    body: body,
    icon: '/firebase-logo.png',
    badge: '/badge-icon.png',
    data: data  // 딥링크 데이터 포함
  };
  
  self.registration.showNotification(title, notificationOptions);
});

// 알림 클릭 이벤트
self.addEventListener('notificationclick', (event) => {
  console.log('Notification clicked:', event.notification.data);
  
  event.notification.close();
  
  // 딥링크 데이터에서 URL 생성
  const data = event.notification.data;
  const url = buildUrlFromData(data);
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // 이미 열린 탭이 있으면 해당 탭으로 포커스
        for (let client of clientList) {
          if (client.url.includes(self.registration.scope) && 'focus' in client) {
            client.focus();
            client.postMessage({
              type: 'NOTIFICATION_CLICK',
              data: data
            });
            return;
          }
        }
        // 열린 탭이 없으면 새 창 열기
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
  );
});

function buildUrlFromData(data) {
  """딥링크 데이터로 URL 생성"""
  const { route, order_id, product_id, chat_id, user_id } = data;
  const baseUrl = self.registration.scope;
  
  switch (route) {
    case 'order_detail':
      return `${baseUrl}orders/${order_id}`;
    case 'product_detail':
      return `${baseUrl}products/${product_id}`;
    case 'chat':
      return `${baseUrl}chats/${chat_id}`;
    case 'profile':
      return `${baseUrl}profile/${user_id}`;
    default:
      return baseUrl;
  }
}
```

**React 컴포넌트**:
```jsx
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { setupNotificationHandlers } from './firebase-config';

function App() {
  const navigate = useNavigate();
  
  useEffect(() => {
    // 알림 핸들러 설정
    setupNotificationHandlers(navigate);
    
    // Service Worker에서 온 메시지 처리
    navigator.serviceWorker?.addEventListener('message', (event) => {
      if (event.data.type === 'NOTIFICATION_CLICK') {
        const data = event.data.data;
        handleDeepLink(data);
      }
    });
  }, [navigate]);
  
  const handleDeepLink = (data) => {
    const { route, order_id, product_id, chat_id, user_id } = data;
    
    switch (route) {
      case 'order_detail':
        navigate(`/orders/${order_id}`);
        break;
      case 'product_detail':
        navigate(`/products/${product_id}`);
        break;
      case 'chat':
        navigate(`/chats/${chat_id}`);
        break;
      case 'profile':
        navigate(`/profile/${user_id}`);
        break;
    }
  };
  
  return (
    <div className="App">
      {/* 앱 컨텐츠 */}
    </div>
  );
}
```

### 5. 실전 사용 예시

**Django API에서 딥링크 포함 알림 전송**:
```python
# notifications/use_cases.py

from .services import FCMService
from .deeplink import DeepLinkBuilder

def send_order_confirmed_notification(order):
    """주문 확인 알림"""
    deeplink = DeepLinkBuilder.for_order(order.id)
    
    FCMService.send_to_user(
        user=order.user,
        title="🎉 주문이 확인되었습니다",
        body=f"{order.product_name} 주문이 접수되었습니다. 배송 준비 중입니다.",
        data=deeplink
    )

def send_new_message_notification(message):
    """새 메시지 알림"""
    deeplink = DeepLinkBuilder.for_chat(message.chat_id)
    
    FCMService.send_to_user(
        user=message.recipient,
        title=f"💬 {message.sender.name}님의 메시지",
        body=message.preview_text,
        data=deeplink
    )

def send_promotion_notification(user, promotion):
    """프로모션 알림"""
    deeplink = DeepLinkBuilder.build(
        'promotion',
        promotion_id=promotion.id
    )
    
    FCMService.send_to_user(
        user=user,
        title=f"🎁 {promotion.discount_rate}% 특별 할인!",
        body=promotion.description,
        data=deeplink,
        image_url=promotion.banner_url
    )

def send_product_back_in_stock_notification(user, product):
    """재입고 알림"""
    deeplink = DeepLinkBuilder.for_product(product.id)
    
    FCMService.send_to_user(
        user=user,
        title="✨ 관심 상품이 재입고되었습니다",
        body=f"{product.name}이(가) 다시 입고되었습니다. 지금 확인하세요!",
        data=deeplink,
        image_url=product.thumbnail_url
    )
```

### 6. 딥링크 테스트

**Android ADB 명령어**:
```bash
# URL Scheme 테스트
adb shell am start -W -a android.intent.action.VIEW \
  -d "myapp://orders/123" com.yourcompany.myapp

# App Link 테스트
adb shell am start -W -a android.intent.action.VIEW \
  -d "https://yourdomain.com/app/orders/123" com.yourcompany.myapp
```

**iOS 시뮬레이터**:
```bash
# URL Scheme 테스트
xcrun simctl openurl booted "myapp://orders/123"

# Universal Link 테스트
xcrun simctl openurl booted "https://yourdomain.com/app/orders/123"
```

**웹 브라우저**:
```javascript
// 개발자 도구 콘솔에서
window.location.href = '/orders/123';
```

### 7. 딥링크 분석 및 추적

```python
# notifications/models.py에 추가

class NotificationLog(models.Model):
    # ... 기존 필드 ...
    
    # 딥링크 추적
    deeplink_route = models.CharField(max_length=50, blank=True)
    deeplink_clicked = models.BooleanField(default=False)
    deeplink_clicked_at = models.DateTimeField(null=True, blank=True)
    
    def mark_deeplink_clicked(self):
        """딥링크 클릭 기록"""
        self.deeplink_clicked = True
        self.deeplink_clicked_at = timezone.now()
        self.save(update_fields=['deeplink_clicked', 'deeplink_clicked_at'])


# API 엔드포인트 추가
@router.post("/notifications/{notification_id}/track-click")
def track_notification_click(request, notification_id: int):
    """알림 클릭 추적"""
    try:
        log = NotificationLog.objects.get(
            id=notification_id,
            user=request.auth
        )
        log.mark_deeplink_clicked()
        
        return {"success": True, "message": "Click tracked"}
    except NotificationLog.DoesNotExist:
        return {"success": False, "error": "Notification not found"}
```

이제 푸시 알림을 클릭하면 사용자가 정확히 원하는 페이지로 이동하게 됩니다! 다음 섹션에서는 고급 기능과 최적화를 다루겠습니다.

## 🚀 고급 기능 및 최적화

실무에서 푸시 알림 시스템을 운영할 때 필요한 고급 기능과 최적화 방법을 알아보겠습니다.

### 1. Celery를 사용한 비동기 처리

대량의 알림을 전송할 때는 비동기 작업 큐를 사용하여 서버 부하를 줄이고 응답 속도를 개선할 수 있습니다.

**설치**:
```bash
pip install celery redis
```

**config/celery.py**:
```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

**config/settings.py**:
```python
# Celery 설정
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'
```

**notifications/tasks.py**:
```python
from celery import shared_task
from django.contrib.auth import get_user_model
from .services import FCMService
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_notification_async(self, user_id, title, body, data=None, image_url=None):
    """
    비동기로 알림 전송
    
    실패 시 3번까지 재시도
    """
    try:
        user = User.objects.get(id=user_id)
        result = FCMService.send_to_user(
            user=user,
            title=title,
            body=body,
            data=data,
            image_url=image_url
        )
        return result
    
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'success': False, 'error': 'User not found'}
    
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        # 재시도 (exponential backoff)
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task
def send_bulk_notifications_async(user_ids, title, body, data=None):
    """
    대량 알림을 개별 태스크로 분산 처리
    """
    from celery import group
    
    # 각 사용자별로 개별 태스크 생성
    job = group(
        send_notification_async.s(user_id, title, body, data)
        for user_id in user_ids
    )
    
    result = job.apply_async()
    return f"Scheduled {len(user_ids)} notifications"


@shared_task
def send_scheduled_notification(user_id, title, body, data=None, send_at=None):
    """
    예약된 시간에 알림 전송
    
    Usage:
        from datetime import datetime, timedelta
        send_at = datetime.now() + timedelta(hours=1)
        send_scheduled_notification.apply_async(
            args=[user_id, title, body, data],
            eta=send_at
        )
    """
    return send_notification_async(user_id, title, body, data)


@shared_task
def cleanup_old_notifications():
    """
    오래된 알림 로그 정리 (주기적 실행)
    
    Celery Beat으로 매일 실행:
    CELERY_BEAT_SCHEDULE = {
        'cleanup-notifications': {
            'task': 'notifications.tasks.cleanup_old_notifications',
            'schedule': crontab(hour=2, minute=0),  # 매일 오전 2시
        }
    }
    """
    from datetime import timedelta
    from django.utils import timezone
    from .models import NotificationLog
    
    # 30일 이전 로그 삭제
    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count = NotificationLog.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"Cleaned up {deleted_count} old notification logs")
    return deleted_count


@shared_task
def deactivate_inactive_tokens():
    """
    장기간 사용되지 않은 토큰 비활성화
    """
    from datetime import timedelta
    from django.utils import timezone
    from .models import DeviceToken
    
    # 90일 이상 사용되지 않은 토큰
    cutoff_date = timezone.now() - timedelta(days=90)
    updated_count = DeviceToken.objects.filter(
        last_used_at__lt=cutoff_date,
        is_active=True
    ).update(is_active=False)
    
    logger.info(f"Deactivated {updated_count} inactive tokens")
    return updated_count
```

**API에서 비동기 태스크 사용**:
```python
# notifications/api.py

@router.post("/send/async")
def send_notification_async_endpoint(request, payload: SendNotificationSchema):
    """비동기로 알림 전송"""
    from .tasks import send_notification_async
    
    task = send_notification_async.delay(
        user_id=payload.user_id,
        title=payload.title,
        body=payload.body,
        data=payload.data,
        image_url=payload.image_url
    )
    
    return {
        'success': True,
        'message': 'Notification scheduled',
        'task_id': task.id
    }
```

### 2. 알림 우선순위 및 배치 처리

**notifications/services.py 확장**:
```python
class NotificationPriority:
    """알림 우선순위"""
    CRITICAL = 'critical'    # 즉시 전송
    HIGH = 'high'           # 5분 이내
    NORMAL = 'normal'       # 1시간 이내
    LOW = 'low'            # 배치 처리


@shared_task
def batch_send_low_priority_notifications():
    """
    낮은 우선순위 알림을 배치로 처리
    
    매 시간마다 실행되어 대기 중인 알림을 한 번에 전송
    """
    from .models import NotificationQueue
    
    pending_notifications = NotificationQueue.objects.filter(
        priority=NotificationPriority.LOW,
        status='pending'
    )
    
    for notification in pending_notifications:
        send_notification_async.delay(
            user_id=notification.user_id,
            title=notification.title,
            body=notification.body,
            data=notification.data
        )
        notification.status = 'sent'
        notification.save()
```

### 3. A/B 테스팅

**notifications/ab_testing.py**:
```python
import random
from typing import Dict, Any

class NotificationABTest:
    """알림 A/B 테스팅"""
    
    @staticmethod
    def get_variant(user_id: int, test_name: str) -> str:
        """
        사용자에게 일관된 변형(variant) 할당
        
        같은 user_id와 test_name은 항상 같은 변형을 반환
        """
        hash_value = hash(f"{user_id}_{test_name}")
        return 'A' if hash_value % 2 == 0 else 'B'
    
    @staticmethod
    def get_notification_content(
        user_id: int,
        test_name: str,
        variant_a: Dict[str, Any],
        variant_b: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        A/B 테스트에 따른 알림 컨텐츠 반환
        
        Usage:
            content = NotificationABTest.get_notification_content(
                user_id=user.id,
                test_name='welcome_message',
                variant_a={'title': '환영합니다!', 'body': '...'},
                variant_b={'title': '안녕하세요!', 'body': '...'}
            )
        """
        variant = NotificationABTest.get_variant(user_id, test_name)
        return variant_a if variant == 'A' else variant_b


# 사용 예시
def send_welcome_notification(user):
    """환영 메시지 A/B 테스팅"""
    content = NotificationABTest.get_notification_content(
        user_id=user.id,
        test_name='welcome_message_v2',
        variant_a={
            'title': '🎉 회원가입을 축하합니다!',
            'body': '특별 할인 쿠폰을 드립니다.'
        },
        variant_b={
            'title': '환영합니다!',
            'body': '가입 감사 쿠폰이 지급되었습니다.'
        }
    )
    
    FCMService.send_to_user(
        user=user,
        title=content['title'],
        body=content['body'],
        data={'ab_test': 'welcome_message_v2', 'variant': content.get('variant')}
    )
```

### 4. 알림 템플릿 시스템

**notifications/templates.py**:
```python
from typing import Dict, Any
from string import Template

class NotificationTemplate:
    """알림 템플릿 관리"""
    
    TEMPLATES = {
        'order_confirmed': {
            'title': '주문이 확정되었습니다',
            'body': Template('$product_name 주문이 확정되었습니다. 배송 준비 중입니다.'),
            'data': {
                'type': 'order',
                'action': 'view_order'
            }
        },
        'order_shipped': {
            'title': '상품이 발송되었습니다',
            'body': Template('$product_name이(가) 발송되었습니다. 운송장번호: $tracking_number'),
            'data': {
                'type': 'order',
                'action': 'track_shipment'
            }
        },
        'new_message': {
            'title': Template('$sender_name님의 메시지'),
            'body': Template('$message_preview'),
            'data': {
                'type': 'message',
                'action': 'open_chat'
            }
        },
        'promotion': {
            'title': Template('$discount_rate% 할인 이벤트!'),
            'body': Template('$product_name을(를) 특별가로 만나보세요!'),
            'data': {
                'type': 'promotion',
                'action': 'view_product'
            }
        }
    }
    
    @classmethod
    def render(cls, template_name: str, **kwargs) -> Dict[str, Any]:
        """
        템플릿 렌더링
        
        Usage:
            notification = NotificationTemplate.render(
                'order_shipped',
                product_name='노트북',
                tracking_number='123456789'
            )
        """
        if template_name not in cls.TEMPLATES:
            raise ValueError(f"Template '{template_name}' not found")
        
        template = cls.TEMPLATES[template_name]
        
        result = {
            'title': template['title'],
            'body': template['body'],
            'data': template['data'].copy()
        }
        
        # Template 문자열 치환
        if isinstance(result['title'], Template):
            result['title'] = result['title'].safe_substitute(**kwargs)
        
        if isinstance(result['body'], Template):
            result['body'] = result['body'].safe_substitute(**kwargs)
        
        # data에 추가 정보 병합
        result['data'].update(kwargs)
        
        return result


# 사용 예시
def send_order_notification(order):
    """주문 알림 전송"""
    notification = NotificationTemplate.render(
        'order_shipped',
        product_name=order.product.name,
        tracking_number=order.tracking_number,
        order_id=str(order.id)
    )
    
    FCMService.send_to_user(
        user=order.user,
        title=notification['title'],
        body=notification['body'],
        data=notification['data']
    )
```

### 5. 알림 구독 설정

사용자가 알림 유형별로 구독을 관리할 수 있도록 합니다.

**notifications/models.py 추가**:
```python
class NotificationPreference(models.Model):
    """사용자별 알림 구독 설정"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preference'
    )
    
    # 알림 유형별 구독 설정
    enable_order_notifications = models.BooleanField(default=True)
    enable_message_notifications = models.BooleanField(default=True)
    enable_promotion_notifications = models.BooleanField(default=True)
    enable_system_notifications = models.BooleanField(default=True)
    
    # 야간 알림 설정 (예: 22:00 ~ 08:00)
    do_not_disturb_enabled = models.BooleanField(default=False)
    dnd_start_time = models.TimeField(default='22:00:00')
    dnd_end_time = models.TimeField(default='08:00:00')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_preferences'
        verbose_name = '알림 설정'
        verbose_name_plural = '알림 설정 목록'


def should_send_notification(user, notification_type):
    """알림 전송 여부 확인"""
    try:
        prefs = user.notification_preference
    except NotificationPreference.DoesNotExist:
        # 설정이 없으면 기본값으로 생성
        prefs = NotificationPreference.objects.create(user=user)
    
    # 알림 유형별 체크
    type_enabled_map = {
        'order': prefs.enable_order_notifications,
        'message': prefs.enable_message_notifications,
        'promotion': prefs.enable_promotion_notifications,
        'system': prefs.enable_system_notifications
    }
    
    if not type_enabled_map.get(notification_type, True):
        return False
    
    # 방해 금지 모드 체크
    if prefs.do_not_disturb_enabled:
        from django.utils import timezone
        current_time = timezone.localtime().time()
        
        if prefs.dnd_start_time <= prefs.dnd_end_time:
            # 예: 22:00 ~ 23:59
            if prefs.dnd_start_time <= current_time <= prefs.dnd_end_time:
                return False
        else:
            # 예: 22:00 ~ 08:00 (다음날)
            if current_time >= prefs.dnd_start_time or current_time <= prefs.dnd_end_time:
                return False
    
    return True
```

### 6. 성능 최적화 팁

**1) 데이터베이스 인덱스**
```python
# 자주 조회되는 필드에 인덱스 추가
class DeviceToken(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['device_token']),
            models.Index(fields=['last_used_at']),
        ]
```

**2) 쿼리 최적화**
```python
# ❌ N+1 쿼리 문제
for user in users:
    devices = user.device_tokens.all()  # 각 user마다 쿼리

# ✅ prefetch_related 사용
users = User.objects.prefetch_related('device_tokens').all()
for user in users:
    devices = user.device_tokens.all()  # 한 번의 쿼리로 해결
```

**3) Redis 캐싱**
```python
from django.core.cache import cache

def get_user_device_tokens(user_id):
    """디바이스 토큰 캐싱"""
    cache_key = f'device_tokens:{user_id}'
    tokens = cache.get(cache_key)
    
    if tokens is None:
        tokens = list(
            DeviceToken.objects.filter(
                user_id=user_id,
                is_active=True
            ).values_list('device_token', flat=True)
        )
        cache.set(cache_key, tokens, timeout=3600)  # 1시간
    
    return tokens
```

**4) 배치 크기 조절**
```python
# FCM은 한 번에 최대 500개 토큰 지원
def send_to_many_devices(tokens, message):
    """대량 토큰을 배치로 처리"""
    from firebase_admin import messaging
    
    batch_size = 500
    results = []
    
    for i in range(0, len(tokens), batch_size):
        batch_tokens = tokens[i:i + batch_size]
        
        multicast = messaging.MulticastMessage(
            tokens=batch_tokens,
            notification=message
        )
        
        batch_response = messaging.send_multicast(multicast)
        results.append(batch_response)
    
    return results
```

고급 기능과 최적화 방법을 살펴보았습니다. 다음은 마무리와 트러블슈팅 팁입니다.

## 🔧 트러블슈팅

실무에서 자주 마주치는 문제들과 해결 방법을 정리했습니다.

### 1. Firebase 초기화 문제

**문제**: `ValueError: The default Firebase app already exists.`

**원인**: Firebase를 여러 번 초기화 시도

**해결**:
```python
import firebase_admin

def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(...)
        firebase_admin.initialize_app(cred)
```

### 2. 토큰이 무효화되는 경우

**문제**: `UnregisteredError` 또는 `InvalidArgumentError`

**원인**:
- 앱 재설치
- 토큰 갱신
- 앱 데이터 삭제

**해결**:
```python
try:
    messaging.send(message)
except messaging.UnregisteredError:
    # 토큰 비활성화
    device.is_active = False
    device.save()
except messaging.InvalidArgumentError:
    # 잘못된 토큰 형식
    device.delete()
```

### 3. iOS에서 알림이 안 오는 경우

**체크리스트**:
```swift
// 1. 알림 권한 확인
UNUserNotificationCenter.current().getNotificationSettings { settings in
    print("Authorization status: \(settings.authorizationStatus)")
}

// 2. APNs 토큰 확인
func application(_ application: UIApplication, 
                didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
    let token = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
    print("APNs token: \(token)")
}

// 3. FCM 토큰 확인
Messaging.messaging().token { token, error in
    if let token = token {
        print("FCM token: \(token)")
    }
}
```

**흔한 원인**:
- APNs 인증서 만료
- 프로비저닝 프로필 문제
- Push Notification capability 미설정
- Firebase 프로젝트에 APNs 키 미등록

### 4. Android에서 백그라운드 알림이 안 오는 경우

**원인**: 배터리 최적화

**해결**:
```kotlin
// AndroidManifest.xml
<uses-permission android:name="android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS" />

// 배터리 최적화 제외 요청
val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
    data = Uri.parse("package:$packageName")
}
startActivity(intent)
```

### 5. 데이터 메시지 vs 알림 메시지

**차이점**:
```python
# 알림 메시지 (Notification Message)
# - 앱이 백그라운드일 때 시스템이 자동으로 표시
# - 커스터마이징 제한적
message = messaging.Message(
    notification=messaging.Notification(
        title="제목",
        body="내용"
    ),
    token=token
)

# 데이터 메시지 (Data Message)
# - 항상 앱에서 처리
# - 완전한 커스터마이징 가능
# - 백그라운드에서도 onMessageReceived 호출
message = messaging.Message(
    data={
        'title': '제목',
        'body': '내용',
        'custom_field': 'value'
    },
    token=token
)
```

### 6. 대량 전송 시 Rate Limit

**FCM 제한사항**:
- 초당 최대 600,000 메시지
- 한 번에 최대 500개 토큰 (멀티캐스트)

**해결**:
```python
def send_with_rate_limit(tokens, message):
    """Rate limit을 고려한 전송"""
    import time
    
    batch_size = 500
    delay = 0.1  # 100ms 딜레이
    
    for i in range(0, len(tokens), batch_size):
        batch = tokens[i:i + batch_size]
        messaging.send_multicast(...)
        
        if i + batch_size < len(tokens):
            time.sleep(delay)
```

### 7. 로깅 및 모니터링

**구조화된 로깅**:
```python
import logging
import json

logger = logging.getLogger(__name__)

def log_notification_event(event_type, user_id, success, **kwargs):
    """구조화된 알림 로그"""
    log_data = {
        'event': event_type,
        'user_id': user_id,
        'success': success,
        'timestamp': timezone.now().isoformat(),
        **kwargs
    }
    
    if success:
        logger.info(json.dumps(log_data))
    else:
        logger.error(json.dumps(log_data))

# 사용
log_notification_event(
    event_type='notification_sent',
    user_id=user.id,
    success=True,
    notification_type='order',
    device_count=3
)
```

**Sentry 통합**:
```python
import sentry_sdk

try:
    messaging.send(message)
except Exception as e:
    sentry_sdk.capture_exception(e)
    sentry_sdk.set_context("notification", {
        "user_id": user.id,
        "title": title,
        "device_count": device_count
    })
```

### 8. 테스트 전략

**단위 테스트**:
```python
from unittest.mock import patch, MagicMock
from django.test import TestCase

class FCMServiceTest(TestCase):
    
    @patch('firebase_admin.messaging.send')
    def test_send_notification_success(self, mock_send):
        """알림 전송 성공 테스트"""
        mock_send.return_value = 'message-id-123'
        
        success, message_id, error = FCMService.send_to_device(
            device_token='test-token',
            title='Test',
            body='Test body'
        )
        
        self.assertTrue(success)
        self.assertEqual(message_id, 'message-id-123')
        self.assertIsNone(error)
        mock_send.assert_called_once()
    
    @patch('firebase_admin.messaging.send')
    def test_send_notification_unregistered(self, mock_send):
        """무효 토큰 테스트"""
        from firebase_admin import messaging
        mock_send.side_effect = messaging.UnregisteredError('Invalid token')
        
        success, message_id, error = FCMService.send_to_device(
            device_token='invalid-token',
            title='Test',
            body='Test body'
        )
        
        self.assertFalse(success)
        self.assertIn('unregistered', error.lower())
```

**통합 테스트**:
```python
from django.test import TestCase
from rest_framework.test import APIClient

class NotificationAPITest(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_register_device_token(self):
        """디바이스 토큰 등록 테스트"""
        response = self.client.post('/api/notifications/devices/register', {
            'device_token': 'test-fcm-token',
            'device_type': 'ANDROID',
            'device_name': 'Test Device'
        }, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            DeviceToken.objects.filter(
                user=self.user,
                device_token='test-fcm-token'
            ).exists()
        )
```

## 📊 성능 및 비용 고려사항

### FCM 무료 사용량
- ✅ **무제한 메시지**: 전송 수 제한 없음
- ✅ **무료**: 추가 비용 없음
- ⚠️ **Rate Limit**: 초당 60만 메시지

### 서버 리소스 추정
```python
# 10만 명 사용자 기준

# 1. 데이터베이스 용량
# - DeviceToken: 약 50MB (사용자당 2개 디바이스)
# - NotificationLog: 약 1GB/월 (일 평균 10개 알림)

# 2. API 요청
# - 디바이스 등록: 1,000 req/day
# - 알림 전송: 1,000,000 req/day
# - 토큰 조회: 10,000 req/day

# 3. Celery 워커
# - 최소 3개 워커 권장
# - 메모리: 워커당 256MB
# - CPU: 워커당 1 vCPU

# 4. Redis
# - 메모리: 최소 512MB
# - 캐시 + Celery 브로커용
```

### 비용 절감 팁
1. **로그 정리**: 오래된 로그 주기적 삭제
2. **토큰 정리**: 비활성 토큰 자동 삭제
3. **배치 처리**: 낮은 우선순위 알림은 배치로 처리
4. **캐싱**: 자주 조회되는 데이터 캐싱
5. **인덱스 최적화**: 쿼리 성능 개선

## 🎯 결론

이 글에서는 Django Ninja와 Firebase Cloud Messaging을 사용하여 완전한 푸시 알림 시스템을 구축하는 방법을 알아보았습니다.

### 핵심 내용 정리

**1. 아키텍처**
- Django Ninja로 RESTful API 구축
- Firebase Admin SDK로 FCM 통합
- Celery로 비동기 처리
- Redis로 캐싱 및 작업 큐

**2. 주요 기능**
- ✅ 디바이스 토큰 관리
- ✅ 단일/대량 알림 전송
- ✅ 토픽 기반 구독
- ✅ 알림 히스토리 추적
- ✅ 사용자 알림 설정
- ✅ 템플릿 시스템

**3. 최적화**
- 비동기 작업 큐
- 데이터베이스 인덱싱
- Redis 캐싱
- 배치 처리

**4. 크로스 플랫폼 지원**
- Android (Kotlin)
- iOS (Swift)
- Web (JavaScript)

### 다음 단계

이 시스템을 더 발전시키려면:

1. **분석 대시보드**: 알림 전송률, 클릭률 시각화
2. **A/B 테스팅**: 알림 메시지 최적화
3. **머신러닝**: 사용자별 최적 전송 시간 예측
4. **다국어 지원**: 사용자 언어별 알림 템플릿
5. **리치 미디어**: 이미지, 비디오, 인터랙티브 알림

### 참고 자료

- [Firebase Cloud Messaging 공식 문서](https://firebase.google.com/docs/cloud-messaging)
- [Django Ninja 공식 문서](https://django-ninja.rest-framework.com/)
- [Firebase Admin SDK Python](https://firebase.google.com/docs/admin/setup)
- [Celery 공식 문서](https://docs.celeryq.dev/)

### 전체 코드 저장소

이 글의 전체 코드는 GitHub에서 확인할 수 있습니다:
```bash
git clone https://github.com/your-repo/django-ninja-fcm
cd django-ninja-fcm
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Django Ninja와 FCM을 사용하면 확장 가능하고 안정적인 푸시 알림 시스템을 쉽게 구축할 수 있습니다. 실무에서 바로 적용하여 사용자 경험을 향상시켜 보세요! 🚀

