---
layout: post
title: "Django Ninja로 구축하는 멀티 서비스 소셜 로그인 시스템"
date: 2025-10-30 10:30:00 +0900
categories: [Django, Authentication, Microservices]
tags: [django-ninja, social-auth, oauth, microservices, backend, python]
description: "하나의 백엔드 서버에서 여러 서비스를 지원하는 모듈화된 소셜 로그인 시스템을 Django Ninja로 구현하는 완전 가이드"
image: "/assets/images/django-ninja-social-auth-cover.webp"
author: "updaun"
image: "/assets/img/posts/2025-10-30-django-ninja-multi-service-social-auth.webp"
---

# Django Ninja로 구축하는 멀티 서비스 소셜 로그인 시스템

현대의 웹 서비스에서 소셜 로그인은 필수 기능이 되었습니다. 사용자는 복잡한 회원가입 과정 없이 기존 소셜 계정으로 간편하게 서비스를 이용하고 싶어하죠. 하지만 여러 서비스를 운영하는 기업에서는 각 서비스마다 독립적인 인증 시스템을 구축하기보다는 **하나의 통합된 인증 서버**에서 모든 서비스의 인증을 처리하는 것이 효율적입니다.

이 포스트에서는 **Django Ninja**를 활용하여 여러 서비스가 공유할 수 있는 **모듈화된 소셜 로그인 시스템**을 구축하는 방법을 살펴보겠습니다. 단순한 OAuth 연동을 넘어서, 서비스별 사용자 관리, 권한 시스템, JWT 토큰 기반 인증, 그리고 확장 가능한 아키텍처까지 다루어 실제 프로덕션 환경에서 사용할 수 있는 완전한 솔루션을 제시합니다.

## 🎯 이 포스트에서 다룰 내용

- **멀티 서비스 아키텍처 설계**: 확장 가능한 인증 시스템 구조
- **Django Ninja 기반 API 구현**: 고성능 소셜 로그인 API
- **다양한 소셜 플랫폼 지원**: Google, Facebook, GitHub, Apple 등
- **서비스별 사용자 관리**: 독립적인 사용자 프로필과 권한 관리
- **JWT 토큰 시스템**: 안전하고 확장 가능한 인증 토큰
- **실시간 세션 관리**: Redis 기반 세션 동기화
- **보안 최적화**: CORS, CSRF, Rate Limiting 등
- **모니터링 및 로깅**: 인증 이벤트 추적과 분석

---

## 🏗️ 1. 멀티 서비스 아키텍처 설계

여러 서비스를 지원하는 통합 인증 시스템을 구축하기 위해서는 먼저 확장 가능한 아키텍처를 설계해야 합니다.

### 1.1 전체 시스템 아키텍처

```python
# config/settings.py
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# Django 기본 설정
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# 애플리케이션 정의
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'social_django',
    'django_celery_beat',
    'django_celery_results',
]

LOCAL_APPS = [
    'apps.authentication',
    'apps.users',
    'apps.services',
    'apps.social_auth',
    'apps.tokens',
    'apps.permissions',
    'apps.monitoring',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# 미들웨어 설정
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.authentication.middleware.ServiceAuthMiddleware',
    'apps.monitoring.middleware.AuthLoggingMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# 데이터베이스 설정
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'multi_auth_db'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'password'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Redis 설정 (캐시 및 세션)
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'{REDIS_URL}/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50},
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
        }
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'{REDIS_URL}/2',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# 세션 설정
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'
SESSION_COOKIE_AGE = 86400  # 24시간
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# CORS 설정
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS', 
    'http://localhost:3000,http://localhost:3001,http://localhost:3002'
).split(',')

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG

# JWT 토큰 설정
JWT_SETTINGS = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# 소셜 인증 설정
AUTHENTICATION_BACKENDS = [
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.facebook.FacebookOAuth2',
    'social_core.backends.github.GithubOAuth2',
    'social_core.backends.apple.AppleIdAuth',
    'social_core.backends.kakao.KakaoOAuth2',
    'social_core.backends.naver.NaverOAuth2',
    'django.contrib.auth.backends.ModelBackend',
]

# 소셜 인증 키 설정
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('GOOGLE_OAUTH2_SECRET')

SOCIAL_AUTH_FACEBOOK_KEY = os.environ.get('FACEBOOK_KEY')
SOCIAL_AUTH_FACEBOOK_SECRET = os.environ.get('FACEBOOK_SECRET')

SOCIAL_AUTH_GITHUB_KEY = os.environ.get('GITHUB_KEY')
SOCIAL_AUTH_GITHUB_SECRET = os.environ.get('GITHUB_SECRET')

SOCIAL_AUTH_APPLE_ID_CLIENT = os.environ.get('APPLE_ID_CLIENT')
SOCIAL_AUTH_APPLE_ID_TEAM = os.environ.get('APPLE_ID_TEAM')
SOCIAL_AUTH_APPLE_ID_KEY = os.environ.get('APPLE_ID_KEY')
SOCIAL_AUTH_APPLE_ID_SECRET = os.environ.get('APPLE_ID_SECRET')

# 소셜 인증 파이프라인
SOCIAL_AUTH_PIPELINE = [
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'apps.social_auth.pipeline.get_username',
    'apps.social_auth.pipeline.create_user',
    'apps.social_auth.pipeline.create_social_user',
    'apps.social_auth.pipeline.load_extra_data',
    'apps.social_auth.pipeline.user_details',
    'apps.social_auth.pipeline.associate_service',
]

# Celery 설정 (비동기 작업)
CELERY_BROKER_URL = f'{REDIS_URL}/3'
CELERY_RESULT_BACKEND = f'{REDIS_URL}/4'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"level": "%(levelname)s", "time": "%(asctime)s", "module": "%(module)s", "message": "%(message)s"}',
        }
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/auth_system.log',
            'formatter': 'json',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'auth_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/auth_events.log',
            'formatter': 'json',
        }
    },
    'loggers': {
        'apps.authentication': {
            'handlers': ['auth_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.social_auth': {
            'handlers': ['auth_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
    },
}

# 보안 설정
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# 멀티 서비스 설정
SUPPORTED_SERVICES = {
    'web_app': {
        'name': 'Web Application',
        'domain': 'web.example.com',
        'redirect_uris': ['http://localhost:3000/auth/callback'],
        'allowed_origins': ['http://localhost:3000'],
        'token_lifetime': timedelta(hours=2),
    },
    'mobile_app': {
        'name': 'Mobile Application',
        'domain': 'mobile.example.com',
        'redirect_uris': ['myapp://auth/callback'],
        'allowed_origins': ['myapp://'],
        'token_lifetime': timedelta(days=30),
    },
    'admin_panel': {
        'name': 'Admin Panel',
        'domain': 'admin.example.com',
        'redirect_uris': ['http://localhost:3001/auth/callback'],
        'allowed_origins': ['http://localhost:3001'],
        'token_lifetime': timedelta(hours=8),
    },
    'api_service': {
        'name': 'API Service',
        'domain': 'api.example.com',
        'redirect_uris': [],
        'allowed_origins': ['*'],
        'token_lifetime': timedelta(hours=1),
    }
}

# Rate Limiting 설정
RATE_LIMIT_SETTINGS = {
    'auth_login': '10/minute',
    'auth_register': '5/minute',
    'token_refresh': '20/minute',
    'password_reset': '3/minute',
    'social_auth': '15/minute',
}

# 국제화
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# 정적 파일 설정
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 기본 자동 필드 타입
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

### 1.2 서비스 모델 및 관리 시스템

```python
# apps/services/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import URLValidator
import uuid
import secrets

class Service(models.Model):
    """등록된 서비스 정보"""
    
    SERVICE_TYPES = [
        ('web', 'Web Application'),
        ('mobile', 'Mobile Application'),
        ('desktop', 'Desktop Application'),
        ('api', 'API Service'),
        ('admin', 'Admin Panel'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('maintenance', 'Maintenance'),
    ]
    
    # 기본 정보
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # 도메인 및 URL 설정
    domain = models.CharField(max_length=255)
    allowed_origins = models.JSONField(default=list)  # CORS 허용 도메인
    redirect_uris = models.JSONField(default=list)    # OAuth 리다이렉트 URI
    
    # API 키 및 시크릿
    api_key = models.CharField(max_length=64, unique=True, editable=False)
    api_secret = models.CharField(max_length=128, editable=False)
    
    # 토큰 설정
    access_token_lifetime = models.DurationField(default=None, null=True, blank=True)
    refresh_token_lifetime = models.DurationField(default=None, null=True, blank=True)
    allow_refresh_token = models.BooleanField(default=True)
    
    # 소셜 로그인 설정
    enabled_social_providers = models.JSONField(default=list)  # ['google', 'facebook', ...]
    require_email_verification = models.BooleanField(default=True)
    auto_create_user = models.BooleanField(default=True)
    
    # 권한 및 스코프
    default_scopes = models.JSONField(default=list)
    required_scopes = models.JSONField(default=list)
    
    # 관리 정보
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_services')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 통계 필드
    total_users = models.IntegerField(default=0)
    monthly_active_users = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'services'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.slug})"
    
    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = self.generate_api_key()
        if not self.api_secret:
            self.api_secret = self.generate_api_secret()
        super().save(*args, **kwargs)
    
    def generate_api_key(self):
        """API 키 생성"""
        return f"sk_{self.slug}_{secrets.token_urlsafe(32)}"
    
    def generate_api_secret(self):
        """API 시크릿 생성"""
        return secrets.token_urlsafe(64)
    
    def regenerate_credentials(self):
        """API 키/시크릿 재생성"""
        self.api_key = self.generate_api_key()
        self.api_secret = self.generate_api_secret()
        self.save(update_fields=['api_key', 'api_secret'])
    
    def is_origin_allowed(self, origin):
        """도메인 허용 확인"""
        if '*' in self.allowed_origins:
            return True
        return origin in self.allowed_origins
    
    def is_redirect_uri_allowed(self, uri):
        """리다이렉트 URI 허용 확인"""
        return uri in self.redirect_uris
    
    def get_token_lifetime(self, token_type='access'):
        """토큰 수명 반환"""
        from django.conf import settings
        
        if token_type == 'access':
            return self.access_token_lifetime or settings.JWT_SETTINGS['ACCESS_TOKEN_LIFETIME']
        elif token_type == 'refresh':
            return self.refresh_token_lifetime or settings.JWT_SETTINGS['REFRESH_TOKEN_LIFETIME']
        
        return settings.JWT_SETTINGS['ACCESS_TOKEN_LIFETIME']

class ServiceUser(models.Model):
    """서비스별 사용자 정보"""
    
    USER_ROLES = [
        ('user', 'Regular User'),
        ('moderator', 'Moderator'),
        ('admin', 'Administrator'),
        ('owner', 'Owner'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('banned', 'Banned'),
    ]
    
    # 관계 필드
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='service_users')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='service_memberships')
    
    # 사용자 상태
    role = models.CharField(max_length=20, choices=USER_ROLES, default='user')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # 서비스별 사용자 정보
    service_user_id = models.CharField(max_length=100, blank=True)  # 서비스 내 사용자 ID
    display_name = models.CharField(max_length=100, blank=True)
    avatar_url = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    
    # 권한 및 스코프
    granted_scopes = models.JSONField(default=list)
    custom_permissions = models.JSONField(default=dict)
    
    # 로그인 정보
    first_login_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    login_count = models.IntegerField(default=0)
    
    # 메타데이터
    metadata = models.JSONField(default=dict)  # 서비스별 추가 정보
    preferences = models.JSONField(default=dict)  # 사용자 설정
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'service_users'
        unique_together = ['service', 'user']
        indexes = [
            models.Index(fields=['service', 'user']),
            models.Index(fields=['service', 'service_user_id']),
            models.Index(fields=['service', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} @ {self.service.name}"
    
    def has_scope(self, scope):
        """스코프 권한 확인"""
        return scope in self.granted_scopes or scope in self.service.default_scopes
    
    def has_permission(self, permission):
        """커스텀 권한 확인"""
        return self.custom_permissions.get(permission, False)
    
    def update_login_info(self):
        """로그인 정보 업데이트"""
        from django.utils import timezone
        
        self.last_login_at = timezone.now()
        self.login_count += 1
        self.save(update_fields=['last_login_at', 'login_count'])

class ServiceScope(models.Model):
    """서비스별 권한 스코프 정의"""
    
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='scopes')
    name = models.CharField(max_length=50)
    description = models.TextField()
    is_default = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'service_scopes'
        unique_together = ['service', 'name']
    
    def __str__(self):
        return f"{self.service.name}: {self.name}"

class ServiceApiLog(models.Model):
    """서비스 API 호출 로그"""
    
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='api_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField()
    response_time = models.FloatField()  # milliseconds
    
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    request_data = models.JSONField(default=dict, blank=True)
    response_data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'service_api_logs'
        indexes = [
            models.Index(fields=['service', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['endpoint', 'created_at']),
        ]
```

### 1.3 서비스 관리 API

```python
# apps/services/schemas.py
from ninja import Schema
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import validator

class ServiceCreateSchema(Schema):
    name: str
    slug: str
    description: Optional[str] = ""
    service_type: str
    domain: str
    allowed_origins: List[str] = []
    redirect_uris: List[str] = []
    enabled_social_providers: List[str] = []
    require_email_verification: bool = True
    auto_create_user: bool = True
    default_scopes: List[str] = []
    
    @validator('service_type')
    def validate_service_type(cls, v):
        allowed_types = ['web', 'mobile', 'desktop', 'api', 'admin']
        if v not in allowed_types:
            raise ValueError(f'Service type must be one of: {allowed_types}')
        return v
    
    @validator('enabled_social_providers')
    def validate_social_providers(cls, v):
        allowed_providers = ['google', 'facebook', 'github', 'apple', 'kakao', 'naver']
        invalid_providers = [p for p in v if p not in allowed_providers]
        if invalid_providers:
            raise ValueError(f'Invalid providers: {invalid_providers}')
        return v

class ServiceUpdateSchema(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    allowed_origins: Optional[List[str]] = None
    redirect_uris: Optional[List[str]] = None
    enabled_social_providers: Optional[List[str]] = None
    require_email_verification: Optional[bool] = None
    auto_create_user: Optional[bool] = None
    default_scopes: Optional[List[str]] = None

class ServiceSchema(Schema):
    id: str
    name: str
    slug: str
    description: str
    service_type: str
    status: str
    domain: str
    allowed_origins: List[str]
    redirect_uris: List[str]
    api_key: str
    enabled_social_providers: List[str]
    require_email_verification: bool
    auto_create_user: bool
    default_scopes: List[str]
    total_users: int
    monthly_active_users: int
    created_at: datetime
    updated_at: datetime

class ServiceListSchema(Schema):
    id: str
    name: str
    slug: str
    service_type: str
    status: str
    total_users: int
    monthly_active_users: int
    created_at: datetime

class ServiceUserSchema(Schema):
    user_id: int
    username: str
    email: str
    role: str
    status: str
    service_user_id: str
    display_name: str
    avatar_url: str
    granted_scopes: List[str]
    first_login_at: datetime
    last_login_at: Optional[datetime] = None
    login_count: int

class ServiceStatsSchema(Schema):
    total_users: int
    active_users: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int
    login_count_today: int
    login_count_this_week: int
    login_count_this_month: int
    popular_providers: List[Dict[str, Any]]
```

```python
# apps/services/api.py
from ninja import Router
from ninja.security import HttpBearer
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from typing import List
import logging

from .models import Service, ServiceUser, ServiceScope
from .schemas import (
    ServiceCreateSchema, ServiceUpdateSchema, ServiceSchema,
    ServiceListSchema, ServiceUserSchema, ServiceStatsSchema
)
from apps.authentication.auth import AdminTokenAuth

logger = logging.getLogger(__name__)

router = Router(tags=["Services"])

@router.post("/services", response=ServiceSchema, auth=AdminTokenAuth())
def create_service(request, data: ServiceCreateSchema):
    """새 서비스 생성"""
    
    try:
        service = Service.objects.create(
            name=data.name,
            slug=data.slug,
            description=data.description,
            service_type=data.service_type,
            domain=data.domain,
            allowed_origins=data.allowed_origins,
            redirect_uris=data.redirect_uris,
            enabled_social_providers=data.enabled_social_providers,
            require_email_verification=data.require_email_verification,
            auto_create_user=data.auto_create_user,
            default_scopes=data.default_scopes,
            owner=request.auth
        )
        
        # 기본 스코프 생성
        default_scopes = [
            ('read_profile', 'Read user profile information'),
            ('write_profile', 'Update user profile information'),
            ('read_email', 'Access user email address'),
        ]
        
        for scope_name, scope_desc in default_scopes:
            ServiceScope.objects.create(
                service=service,
                name=scope_name,
                description=scope_desc,
                is_default=scope_name in ['read_profile', 'read_email']
            )
        
        logger.info(f"Service created: {service.slug} by {request.auth.username}")
        
        return service
        
    except Exception as e:
        logger.error(f"Error creating service: {str(e)}")
        raise

@router.get("/services", response=List[ServiceListSchema], auth=AdminTokenAuth())
def list_services(request):
    """서비스 목록 조회"""
    
    services = Service.objects.filter(
        owner=request.auth
    ).order_by('-created_at')
    
    return services

@router.get("/services/{service_slug}", response=ServiceSchema, auth=AdminTokenAuth())
def get_service(request, service_slug: str):
    """서비스 상세 조회"""
    
    service = get_object_or_404(
        Service, 
        slug=service_slug, 
        owner=request.auth
    )
    
    return service

@router.put("/services/{service_slug}", response=ServiceSchema, auth=AdminTokenAuth())
def update_service(request, service_slug: str, data: ServiceUpdateSchema):
    """서비스 정보 업데이트"""
    
    service = get_object_or_404(
        Service, 
        slug=service_slug, 
        owner=request.auth
    )
    
    # 업데이트할 필드만 수정
    update_fields = []
    for field, value in data.dict(exclude_unset=True).items():
        if hasattr(service, field):
            setattr(service, field, value)
            update_fields.append(field)
    
    if update_fields:
        service.save(update_fields=update_fields)
        logger.info(f"Service updated: {service.slug} fields: {update_fields}")
    
    return service

@router.delete("/services/{service_slug}", auth=AdminTokenAuth())
def delete_service(request, service_slug: str):
    """서비스 삭제"""
    
    service = get_object_or_404(
        Service, 
        slug=service_slug, 
        owner=request.auth
    )
    
    service_name = service.name
    service.delete()
    
    logger.info(f"Service deleted: {service_slug} ({service_name}) by {request.auth.username}")
    
    return {"message": f"Service '{service_name}' has been deleted successfully"}

@router.post("/services/{service_slug}/regenerate-credentials", response=ServiceSchema, auth=AdminTokenAuth())
def regenerate_service_credentials(request, service_slug: str):
    """서비스 API 키/시크릿 재생성"""
    
    service = get_object_or_404(
        Service, 
        slug=service_slug, 
        owner=request.auth
    )
    
    old_api_key = service.api_key
    service.regenerate_credentials()
    
    logger.warning(f"API credentials regenerated for service: {service.slug} by {request.auth.username}")
    
    return service

@router.get("/services/{service_slug}/users", response=List[ServiceUserSchema], auth=AdminTokenAuth())
def list_service_users(request, service_slug: str, page: int = 1, limit: int = 50):
    """서비스 사용자 목록"""
    
    service = get_object_or_404(
        Service, 
        slug=service_slug, 
        owner=request.auth
    )
    
    offset = (page - 1) * limit
    
    service_users = ServiceUser.objects.filter(
        service=service
    ).select_related('user').order_by('-created_at')[offset:offset + limit]
    
    return [
        {
            'user_id': su.user.id,
            'username': su.user.username,
            'email': su.user.email,
            'role': su.role,
            'status': su.status,
            'service_user_id': su.service_user_id,
            'display_name': su.display_name,
            'avatar_url': su.avatar_url,
            'granted_scopes': su.granted_scopes,
            'first_login_at': su.first_login_at,
            'last_login_at': su.last_login_at,
            'login_count': su.login_count,
        }
        for su in service_users
    ]

@router.get("/services/{service_slug}/stats", response=ServiceStatsSchema, auth=AdminTokenAuth())
def get_service_stats(request, service_slug: str):
    """서비스 통계"""
    
    service = get_object_or_404(
        Service, 
        slug=service_slug, 
        owner=request.auth
    )
    
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # 사용자 통계
    total_users = ServiceUser.objects.filter(service=service).count()
    active_users = ServiceUser.objects.filter(
        service=service, 
        status='active'
    ).count()
    
    new_users_today = ServiceUser.objects.filter(
        service=service,
        created_at__date=today
    ).count()
    
    new_users_this_week = ServiceUser.objects.filter(
        service=service,
        created_at__gte=week_ago
    ).count()
    
    new_users_this_month = ServiceUser.objects.filter(
        service=service,
        created_at__gte=month_ago
    ).count()
    
    # 로그인 통계
    login_count_today = ServiceUser.objects.filter(
        service=service,
        last_login_at__date=today
    ).count()
    
    login_count_this_week = ServiceUser.objects.filter(
        service=service,
        last_login_at__gte=week_ago
    ).count()
    
    login_count_this_month = ServiceUser.objects.filter(
        service=service,
        last_login_at__gte=month_ago
    ).count()
    
    # 인기 소셜 프로바이더
    from apps.social_auth.models import SocialAccount
    popular_providers = list(
        SocialAccount.objects.filter(
            service_user__service=service
        ).values('provider').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
    )
    
    return {
        'total_users': total_users,
        'active_users': active_users,
        'new_users_today': new_users_today,
        'new_users_this_week': new_users_this_week,
        'new_users_this_month': new_users_this_month,
        'login_count_today': login_count_today,
        'login_count_this_week': login_count_this_week,
        'login_count_this_month': login_count_this_month,
        'popular_providers': popular_providers,
    }
```

---

## 👥 2. 통합 사용자 관리 시스템

멀티 서비스 환경에서는 하나의 사용자가 여러 서비스를 사용할 수 있으므로, 통합된 사용자 관리 시스템이 필요합니다. 각 서비스별로 독립적인 프로필과 권한을 관리하면서도 중앙 집중식 인증을 제공해야 합니다.

### 2.1 확장된 사용자 모델

```python
# apps/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
import uuid

class User(AbstractUser):
    """확장된 사용자 모델"""
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('N', 'Prefer not to say'),
    ]
    
    LANGUAGE_CHOICES = [
        ('ko', 'Korean'),
        ('en', 'English'),
        ('ja', 'Japanese'),
        ('zh', 'Chinese'),
    ]
    
    # 기본 식별자
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 확장 프로필 정보
    phone_number = models.CharField(
        max_length=20, 
        blank=True,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')]
    )
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    
    # 선호 설정
    preferred_language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='ko')
    timezone = models.CharField(max_length=50, default='Asia/Seoul')
    
    # 프로필 이미지
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    avatar_url = models.URLField(blank=True)  # 소셜 로그인에서 가져온 이미지
    
    # 계정 상태
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=64, blank=True)
    phone_verification_code = models.CharField(max_length=6, blank=True)
    
    # 보안 설정
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True)
    backup_codes = models.JSONField(default=list, blank=True)
    
    # 개인정보 설정
    privacy_settings = models.JSONField(default=dict)
    marketing_consent = models.BooleanField(default=False)
    data_processing_consent = models.BooleanField(default=True)
    
    # 메타데이터
    last_password_change = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    
    # 소셜 로그인 정보
    social_providers = models.JSONField(default=list)  # 연결된 소셜 계정 목록
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['is_active', 'is_email_verified']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.email})"
    
    def get_full_name(self):
        """전체 이름 반환"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_display_name(self):
        """표시용 이름 반환"""
        return self.get_full_name() or self.username
    
    def has_social_provider(self, provider):
        """특정 소셜 프로바이더 연결 확인"""
        return provider in self.social_providers
    
    def add_social_provider(self, provider):
        """소셜 프로바이더 추가"""
        if provider not in self.social_providers:
            self.social_providers.append(provider)
            self.save(update_fields=['social_providers'])
    
    def remove_social_provider(self, provider):
        """소셜 프로바이더 제거"""
        if provider in self.social_providers:
            self.social_providers.remove(provider)
            self.save(update_fields=['social_providers'])
    
    def is_account_locked(self):
        """계정 잠금 상태 확인"""
        from django.utils import timezone
        
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False
    
    def lock_account(self, duration_minutes=30):
        """계정 잠금"""
        from django.utils import timezone
        from datetime import timedelta
        
        self.account_locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        self.save(update_fields=['account_locked_until'])
    
    def unlock_account(self):
        """계정 잠금 해제"""
        self.account_locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['account_locked_until', 'failed_login_attempts'])
    
    def increment_failed_login(self):
        """로그인 실패 횟수 증가"""
        self.failed_login_attempts += 1
        
        # 5회 실패 시 계정 잠금
        if self.failed_login_attempts >= 5:
            self.lock_account()
        else:
            self.save(update_fields=['failed_login_attempts'])
    
    def reset_failed_login(self):
        """로그인 실패 횟수 초기화"""
        self.failed_login_attempts = 0
        self.save(update_fields=['failed_login_attempts'])

class UserSession(models.Model):
    """사용자 세션 관리"""
    
    SESSION_TYPES = [
        ('web', 'Web Browser'),
        ('mobile', 'Mobile App'),
        ('desktop', 'Desktop App'),
        ('api', 'API Access'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=64, unique=True)
    session_type = models.CharField(max_length=10, choices=SESSION_TYPES, default='web')
    
    # 디바이스 정보
    device_name = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    os_name = models.CharField(max_length=50, blank=True)
    browser_name = models.CharField(max_length=50, blank=True)
    
    # 위치 및 네트워크 정보
    ip_address = models.GenericIPAddressField()
    country = models.CharField(max_length=2, blank=True)
    city = models.CharField(max_length=50, blank=True)
    
    # 세션 상태
    is_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'user_sessions'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key']),
            models.Index(fields=['expires_at']),
        ]
    
    def is_expired(self):
        """세션 만료 확인"""
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def terminate(self):
        """세션 종료"""
        self.is_active = False
        self.save(update_fields=['is_active'])
```

### 2.2 사용자 관리 API

```python
# apps/users/schemas.py
from ninja import Schema
from typing import List, Optional, Dict
from datetime import datetime, date
from pydantic import EmailStr, validator

class UserRegistrationSchema(Schema):
    username: str
    email: EmailStr
    password: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    preferred_language: str = "ko"
    marketing_consent: bool = False
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserSchema(Schema):
    id: str
    username: str
    email: str
    first_name: str
    last_name: str
    preferred_language: str
    avatar_url: str
    is_email_verified: bool
    two_factor_enabled: bool
    social_providers: List[str]
    created_at: datetime

class PasswordChangeSchema(Schema):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('New password must be at least 8 characters long')
        return v
```

```python
# apps/users/api.py
from ninja import Router
from django.db import transaction
from django.contrib.auth.hashers import check_password
from django.utils import timezone
import logging
import secrets

from .models import User, UserSession
from .schemas import UserRegistrationSchema, UserSchema, PasswordChangeSchema
from apps.authentication.auth import JWTAuth

logger = logging.getLogger(__name__)
router = Router(tags=["Users"])

@router.post("/users/register", response=UserSchema)
def register_user(request, data: UserRegistrationSchema):
    """사용자 등록"""
    
    # 중복 체크
    if User.objects.filter(username=data.username).exists():
        raise ValueError("Username already exists")
    
    if User.objects.filter(email=data.email).exists():
        raise ValueError("Email already exists")
    
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=data.username,
                email=data.email,
                password=data.password,
                first_name=data.first_name,
                last_name=data.last_name,
                preferred_language=data.preferred_language,
                marketing_consent=data.marketing_consent
            )
            
            logger.info(f"User registered: {user.username}")
            return user
            
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        raise

@router.get("/users/me", response=UserSchema, auth=JWTAuth())
def get_current_user(request):
    """현재 사용자 정보 조회"""
    return request.auth

@router.post("/users/me/change-password", auth=JWTAuth())
def change_password(request, data: PasswordChangeSchema):
    """비밀번호 변경"""
    
    user = request.auth
    
    # 현재 비밀번호 확인
    if not check_password(data.current_password, user.password):
        raise ValueError("Current password is incorrect")
    
    # 새 비밀번호로 변경
    user.set_password(data.new_password)
    user.last_password_change = timezone.now()
    user.save(update_fields=['password', 'last_password_change'])
    
    logger.info(f"Password changed for user: {user.username}")
    
    return {"message": "Password changed successfully"}
```

---

## 🔐 3. 소셜 로그인 통합 구현

이제 여러 소셜 프로바이더를 지원하는 통합 소셜 로그인 시스템을 구현해보겠습니다. OAuth 2.0 프로토콜을 기반으로 Google, Facebook, GitHub, Apple, Kakao, Naver 등의 프로바이더를 지원합니다.

### 3.1 소셜 인증 설정

```python
# config/social_auth_settings.py
from django.conf import settings

# 소셜 로그인 프로바이더 설정
SOCIAL_AUTH_PROVIDERS = {
    'google': {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'scope': ['openid', 'email', 'profile'],
        'auth_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'user_info_url': 'https://www.googleapis.com/oauth2/v2/userinfo',
    },
    'facebook': {
        'client_id': settings.FACEBOOK_CLIENT_ID,
        'client_secret': settings.FACEBOOK_CLIENT_SECRET,
        'scope': ['email', 'public_profile'],
        'auth_url': 'https://www.facebook.com/v18.0/dialog/oauth',
        'token_url': 'https://graph.facebook.com/v18.0/oauth/access_token',
        'user_info_url': 'https://graph.facebook.com/v18.0/me',
    },
    'github': {
        'client_id': settings.GITHUB_CLIENT_ID,
        'client_secret': settings.GITHUB_CLIENT_SECRET,
        'scope': ['user:email'],
        'auth_url': 'https://github.com/login/oauth/authorize',
        'token_url': 'https://github.com/login/oauth/access_token',
        'user_info_url': 'https://api.github.com/user',
    },
    'kakao': {
        'client_id': settings.KAKAO_CLIENT_ID,
        'client_secret': settings.KAKAO_CLIENT_SECRET,
        'scope': ['profile_nickname', 'account_email'],
        'auth_url': 'https://kauth.kakao.com/oauth/authorize',
        'token_url': 'https://kauth.kakao.com/oauth/token',
        'user_info_url': 'https://kapi.kakao.com/v2/user/me',
    },
    'naver': {
        'client_id': settings.NAVER_CLIENT_ID,
        'client_secret': settings.NAVER_CLIENT_SECRET,
        'scope': ['name', 'email', 'profile_image'],
        'auth_url': 'https://nid.naver.com/oauth2.0/authorize',
        'token_url': 'https://nid.naver.com/oauth2.0/token',
        'user_info_url': 'https://openapi.naver.com/v1/nid/me',
    },
    'apple': {
        'client_id': settings.APPLE_CLIENT_ID,
        'team_id': settings.APPLE_TEAM_ID,
        'key_id': settings.APPLE_KEY_ID,
        'private_key': settings.APPLE_PRIVATE_KEY,
        'scope': ['name', 'email'],
        'auth_url': 'https://appleid.apple.com/auth/authorize',
        'token_url': 'https://appleid.apple.com/auth/token',
    }
}

# 기본 설정
SOCIAL_AUTH_DEFAULTS = {
    'response_type': 'code',
    'grant_type': 'authorization_code',
    'timeout': 30,
    'max_retries': 3,
}
```

### 3.2 소셜 인증 서비스

```python
# apps/authentication/social_auth.py
import requests
import secrets
import uuid
import json
from urllib.parse import urlencode, parse_qs
from typing import Dict, Optional, Tuple
from django.core.cache import cache
from django.conf import settings
import logging

from config.social_auth_settings import SOCIAL_AUTH_PROVIDERS, SOCIAL_AUTH_DEFAULTS

logger = logging.getLogger(__name__)

class SocialAuthManager:
    """소셜 인증 관리자"""
    
    def __init__(self, provider: str, service_id: str):
        self.provider = provider
        self.service_id = service_id
        self.config = SOCIAL_AUTH_PROVIDERS.get(provider)
        
        if not self.config:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def get_authorization_url(self, redirect_uri: str) -> Tuple[str, str]:
        """인증 URL 생성"""
        
        # State 생성 (CSRF 보호)
        state = secrets.token_urlsafe(32)
        
        # Redis에 state 저장 (5분 유효)
        cache_key = f"social_auth_state:{state}"
        cache.set(cache_key, {
            'provider': self.provider,
            'service_id': self.service_id,
            'redirect_uri': redirect_uri
        }, timeout=300)
        
        # 프로바이더별 파라미터 구성
        params = {
            'client_id': self.config['client_id'],
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'state': state,
            'scope': ' '.join(self.config['scope'])
        }
        
        # Apple 특별 처리
        if self.provider == 'apple':
            params['response_mode'] = 'form_post'
        
        auth_url = f"{self.config['auth_url']}?{urlencode(params)}"
        
        logger.info(f"Generated auth URL for {self.provider}: {auth_url}")
        return auth_url, state
    
    def exchange_code_for_token(self, code: str, state: str, redirect_uri: str) -> Dict:
        """인증 코드를 액세스 토큰으로 교환"""
        
        # State 검증
        cache_key = f"social_auth_state:{state}"
        state_data = cache.get(cache_key)
        
        if not state_data:
            raise ValueError("Invalid or expired state")
        
        if state_data['provider'] != self.provider:
            raise ValueError("Provider mismatch")
        
        # State 삭제 (일회성)
        cache.delete(cache_key)
        
        # 토큰 요청 데이터
        token_data = {
            'client_id': self.config['client_id'],
            'client_secret': self.config['client_secret'],
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        }
        
        try:
            response = requests.post(
                self.config['token_url'],
                data=token_data,
                timeout=SOCIAL_AUTH_DEFAULTS['timeout']
            )
            response.raise_for_status()
            
            # Content-Type에 따른 응답 파싱
            content_type = response.headers.get('content-type', '')
            
            if 'application/json' in content_type:
                token_response = response.json()
            else:
                # Facebook, GitHub 등은 form-encoded 응답
                token_response = dict(parse_qs(response.text))
                token_response = {k: v[0] if isinstance(v, list) else v 
                                for k, v in token_response.items()}
            
            if 'access_token' not in token_response:
                raise ValueError("No access token in response")
            
            logger.info(f"Successfully exchanged code for token: {self.provider}")
            return token_response
            
        except requests.RequestException as e:
            logger.error(f"Error exchanging code for token: {str(e)}")
            raise
    
    def get_user_info(self, access_token: str) -> Dict:
        """사용자 정보 조회"""
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Facebook은 특별한 처리가 필요
        if self.provider == 'facebook':
            url = f"{self.config['user_info_url']}?fields=id,name,email,first_name,last_name,picture"
        else:
            url = self.config['user_info_url']
        
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=SOCIAL_AUTH_DEFAULTS['timeout']
            )
            response.raise_for_status()
            
            user_data = response.json()
            
            # 프로바이더별 데이터 정규화
            normalized_data = self._normalize_user_data(user_data)
            
            logger.info(f"Retrieved user info from {self.provider}")
            return normalized_data
            
        except requests.RequestException as e:
            logger.error(f"Error retrieving user info: {str(e)}")
            raise
    
    def _normalize_user_data(self, raw_data: Dict) -> Dict:
        """프로바이더별 사용자 데이터 정규화"""
        
        if self.provider == 'google':
            return {
                'provider_id': raw_data.get('id'),
                'email': raw_data.get('email'),
                'first_name': raw_data.get('given_name', ''),
                'last_name': raw_data.get('family_name', ''),
                'full_name': raw_data.get('name', ''),
                'avatar_url': raw_data.get('picture', ''),
                'email_verified': raw_data.get('verified_email', False),
                'locale': raw_data.get('locale', 'en'),
                'raw_data': raw_data
            }
        
        elif self.provider == 'facebook':
            return {
                'provider_id': raw_data.get('id'),
                'email': raw_data.get('email'),
                'first_name': raw_data.get('first_name', ''),
                'last_name': raw_data.get('last_name', ''),
                'full_name': raw_data.get('name', ''),
                'avatar_url': raw_data.get('picture', {}).get('data', {}).get('url', ''),
                'email_verified': True,  # Facebook은 검증된 이메일만 제공
                'locale': raw_data.get('locale', 'en_US'),
                'raw_data': raw_data
            }
        
        elif self.provider == 'github':
            return {
                'provider_id': str(raw_data.get('id')),
                'email': raw_data.get('email'),
                'first_name': '',
                'last_name': '',
                'full_name': raw_data.get('name', ''),
                'avatar_url': raw_data.get('avatar_url', ''),
                'email_verified': True,
                'username': raw_data.get('login', ''),
                'raw_data': raw_data
            }
        
        elif self.provider == 'kakao':
            kakao_account = raw_data.get('kakao_account', {})
            profile = kakao_account.get('profile', {})
            
            return {
                'provider_id': str(raw_data.get('id')),
                'email': kakao_account.get('email'),
                'first_name': '',
                'last_name': '',
                'full_name': profile.get('nickname', ''),
                'avatar_url': profile.get('profile_image_url', ''),
                'email_verified': kakao_account.get('is_email_verified', False),
                'raw_data': raw_data
            }
        
        elif self.provider == 'naver':
            response_data = raw_data.get('response', {})
            
            return {
                'provider_id': response_data.get('id'),
                'email': response_data.get('email'),
                'first_name': '',
                'last_name': '',
                'full_name': response_data.get('name', ''),
                'avatar_url': response_data.get('profile_image', ''),
                'email_verified': True,
                'raw_data': raw_data
            }
        
        # 기본 처리
        return {
            'provider_id': str(raw_data.get('id', raw_data.get('sub', ''))),
            'email': raw_data.get('email'),
            'first_name': raw_data.get('first_name', ''),
            'last_name': raw_data.get('last_name', ''),
            'full_name': raw_data.get('name', ''),
            'avatar_url': raw_data.get('avatar_url', raw_data.get('picture', '')),
            'email_verified': raw_data.get('email_verified', False),
            'raw_data': raw_data
        }

class SocialAccountManager:
    """소셜 계정 관리"""
    
    @staticmethod
    def link_social_account(user, provider: str, provider_data: Dict):
        """소셜 계정 연결"""
        from .models import SocialAccount
        
        social_account, created = SocialAccount.objects.get_or_create(
            user=user,
            provider=provider,
            provider_id=provider_data['provider_id'],
            defaults={
                'email': provider_data.get('email'),
                'username': provider_data.get('username', ''),
                'avatar_url': provider_data.get('avatar_url', ''),
                'raw_data': provider_data.get('raw_data', {}),
                'is_verified': provider_data.get('email_verified', False)
            }
        )
        
        if not created:
            # 기존 계정 정보 업데이트
            social_account.email = provider_data.get('email')
            social_account.username = provider_data.get('username', '')
            social_account.avatar_url = provider_data.get('avatar_url', '')
            social_account.raw_data = provider_data.get('raw_data', {})
            social_account.is_verified = provider_data.get('email_verified', False)
            social_account.save()
        
        # 사용자 소셜 프로바이더 목록 업데이트
        user.add_social_provider(provider)
        
        return social_account
    
    @staticmethod
    def find_user_by_social_account(provider: str, provider_id: str):
        """소셜 계정으로 사용자 찾기"""
        from .models import SocialAccount
        
        try:
            social_account = SocialAccount.objects.select_related('user').get(
                provider=provider,
                provider_id=provider_id
            )
            return social_account.user
        except SocialAccount.DoesNotExist:
            return None
    
    @staticmethod
    def unlink_social_account(user, provider: str):
        """소셜 계정 연결 해제"""
        from .models import SocialAccount
        
        try:
            social_account = SocialAccount.objects.get(
                user=user,
                provider=provider
            )
            social_account.delete()
            
            # 사용자 소셜 프로바이더 목록에서 제거
            user.remove_social_provider(provider)
            
            return True
        except SocialAccount.DoesNotExist:
            return False
```

### 3.3 소셜 계정 모델

```python
# apps/authentication/models.py (추가)
from django.db import models
from django.conf import settings

class SocialAccount(models.Model):
    """소셜 계정 정보"""
    
    PROVIDER_CHOICES = [
        ('google', 'Google'),
        ('facebook', 'Facebook'),
        ('github', 'GitHub'),
        ('apple', 'Apple'),
        ('kakao', 'Kakao'),
        ('naver', 'Naver'),
        ('linkedin', 'LinkedIn'),
        ('twitter', 'Twitter'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='social_accounts'
    )
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_id = models.CharField(max_length=100)  # 프로바이더에서의 사용자 ID
    
    # 프로바이더에서 가져온 정보
    email = models.EmailField(blank=True)
    username = models.CharField(max_length=150, blank=True)
    avatar_url = models.URLField(blank=True)
    
    # 메타데이터
    raw_data = models.JSONField(default=dict)  # 프로바이더 원본 데이터
    is_verified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'social_accounts'
        unique_together = [('provider', 'provider_id')]
        indexes = [
            models.Index(fields=['user', 'provider']),
            models.Index(fields=['provider', 'provider_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.provider}"

class OAuthState(models.Model):
    """OAuth 상태 관리"""
    
    state = models.CharField(max_length=64, unique=True)
    provider = models.CharField(max_length=20)
    service_id = models.UUIDField()
    redirect_uri = models.URLField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'oauth_states'
        indexes = [
            models.Index(fields=['state']),
            models.Index(fields=['expires_at']),
        ]
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
```

### 3.4 소셜 로그인 API

```python
# apps/authentication/social_api.py
from ninja import Router
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
import logging

from .social_auth import SocialAuthManager, SocialAccountManager
from .jwt_auth import JWTAuthService
from .schemas import SocialLoginInitSchema, SocialLoginCallbackSchema
from apps.services.models import Service

User = get_user_model()
logger = logging.getLogger(__name__)
router = Router(tags=["Social Authentication"])

@router.post("/auth/social/init")
def social_login_init(request, data: SocialLoginInitSchema):
    """소셜 로그인 시작"""
    
    # 서비스 확인
    try:
        service = Service.objects.get(id=data.service_id, is_active=True)
    except Service.DoesNotExist:
        raise ValueError("Invalid service")
    
    # 지원하는 프로바이더 확인
    if data.provider not in service.allowed_social_providers:
        raise ValueError(f"Provider {data.provider} not allowed for this service")
    
    try:
        # 소셜 인증 매니저 생성
        auth_manager = SocialAuthManager(data.provider, str(data.service_id))
        
        # 인증 URL 생성
        auth_url, state = auth_manager.get_authorization_url(data.redirect_uri)
        
        logger.info(f"Social login initiated: {data.provider} for service {service.name}")
        
        return {
            "auth_url": auth_url,
            "state": state,
            "provider": data.provider
        }
        
    except Exception as e:
        logger.error(f"Error initiating social login: {str(e)}")
        raise

@router.post("/auth/social/callback")
def social_login_callback(request, data: SocialLoginCallbackSchema):
    """소셜 로그인 콜백 처리"""
    
    try:
        with transaction.atomic():
            # 소셜 인증 매니저 생성
            auth_manager = SocialAuthManager(data.provider, str(data.service_id))
            
            # 1. 인증 코드를 액세스 토큰으로 교환
            token_data = auth_manager.exchange_code_for_token(
                data.code, 
                data.state, 
                data.redirect_uri
            )
            
            # 2. 사용자 정보 조회
            user_info = auth_manager.get_user_info(token_data['access_token'])
            
            # 3. 기존 소셜 계정으로 사용자 찾기
            user = SocialAccountManager.find_user_by_social_account(
                data.provider, 
                user_info['provider_id']
            )
            
            # 4. 사용자가 없으면 새로 생성 또는 이메일로 찾기
            if not user and user_info.get('email'):
                try:
                    user = User.objects.get(email=user_info['email'])
                    # 기존 사용자에게 소셜 계정 연결
                    SocialAccountManager.link_social_account(user, data.provider, user_info)
                except User.DoesNotExist:
                    # 새 사용자 생성
                    user = User.objects.create_user(
                        username=f"{data.provider}_{user_info['provider_id']}",
                        email=user_info.get('email', ''),
                        first_name=user_info.get('first_name', ''),
                        last_name=user_info.get('last_name', ''),
                        is_email_verified=user_info.get('email_verified', False),
                        avatar_url=user_info.get('avatar_url', '')
                    )
                    
                    # 소셜 계정 연결
                    SocialAccountManager.link_social_account(user, data.provider, user_info)
            
            elif not user:
                # 이메일 정보가 없는 경우 새 사용자 생성
                user = User.objects.create_user(
                    username=f"{data.provider}_{user_info['provider_id']}",
                    first_name=user_info.get('first_name', ''),
                    last_name=user_info.get('last_name', ''),
                    avatar_url=user_info.get('avatar_url', '')
                )
                
                # 소셜 계정 연결
                SocialAccountManager.link_social_account(user, data.provider, user_info)
            
            # 5. 서비스 확인 및 사용자 연결
            service = Service.objects.get(id=data.service_id, is_active=True)
            service_user, created = service.serviceuser_set.get_or_create(
                user=user,
                defaults={
                    'role': 'user',
                    'is_active': True
                }
            )
            
            # 6. JWT 토큰 생성
            jwt_service = JWTAuthService()
            access_token = jwt_service.create_access_token(user, service)
            refresh_token = jwt_service.create_refresh_token(user, service)
            
            # 7. 로그인 기록
            from .models import AuthenticationLog
            AuthenticationLog.objects.create(
                user=user,
                service=service,
                auth_method='social',
                provider=data.provider,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                is_successful=True
            )
            
            logger.info(f"Social login successful: {user.username} via {data.provider}")
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.get_full_name(),
                    "avatar_url": user.avatar_url
                },
                "service": {
                    "id": str(service.id),
                    "name": service.name,
                    "role": service_user.role
                }
            }
            
    except Exception as e:
        logger.error(f"Error in social login callback: {str(e)}")
        
        # 실패 로그 기록
        try:
            service = Service.objects.get(id=data.service_id)
            AuthenticationLog.objects.create(
                service=service,
                auth_method='social',
                provider=data.provider,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                is_successful=False,
                failure_reason=str(e)
            )
        except:
            pass
        
        raise

@router.post("/auth/social/link", auth=JWTAuth())
def link_social_account(request, data: SocialLinkSchema):
    """기존 계정에 소셜 계정 연결"""
    
    user = request.auth
    
    try:
        # 소셜 인증 매니저 생성
        auth_manager = SocialAuthManager(data.provider, str(data.service_id))
        
        # 토큰으로 사용자 정보 조회
        user_info = auth_manager.get_user_info(data.access_token)
        
        # 이미 다른 계정에 연결된 소셜 계정인지 확인
        existing_user = SocialAccountManager.find_user_by_social_account(
            data.provider, 
            user_info['provider_id']
        )
        
        if existing_user and existing_user != user:
            raise ValueError("This social account is already linked to another user")
        
        # 소셜 계정 연결
        social_account = SocialAccountManager.link_social_account(
            user, 
            data.provider, 
            user_info
        )
        
        logger.info(f"Social account linked: {user.username} + {data.provider}")
        
        return {
            "message": "Social account linked successfully",
            "provider": data.provider,
            "linked_at": social_account.created_at
        }
        
    except Exception as e:
        logger.error(f"Error linking social account: {str(e)}")
        raise

@router.delete("/auth/social/unlink/{provider}", auth=JWTAuth())
def unlink_social_account(request, provider: str):
    """소셜 계정 연결 해제"""
    
    user = request.auth
    
    # 마지막 로그인 방법인지 확인
    if user.social_accounts.count() == 1 and not user.has_usable_password():
        raise ValueError("Cannot unlink the last authentication method")
    
    success = SocialAccountManager.unlink_social_account(user, provider)
    
    if success:
        logger.info(f"Social account unlinked: {user.username} - {provider}")
        return {"message": "Social account unlinked successfully"}
    else:
        raise ValueError("Social account not found")
```

---

## 🔑 4. JWT 토큰 시스템 구현

보안성과 확장성을 고려한 JWT 기반 인증 시스템을 구현합니다. Access Token과 Refresh Token을 분리하여 보안을 강화하고, 멀티 서비스 환경에서의 토큰 관리를 최적화합니다.

### 4.1 JWT 인증 서비스

```python
# apps/authentication/jwt_auth.py
import jwt
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class JWTAuthService:
    """JWT 인증 서비스"""
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = 'HS256'
        self.access_token_expire_minutes = 15  # 15분
        self.refresh_token_expire_days = 7     # 7일
    
    def create_access_token(self, user, service=None, additional_claims: Dict = None) -> str:
        """Access Token 생성"""
        
        now = timezone.now()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            'user_id': str(user.id),
            'username': user.username,
            'email': user.email,
            'iat': int(now.timestamp()),
            'exp': int(expire.timestamp()),
            'type': 'access',
            'jti': str(uuid.uuid4())  # JWT ID
        }
        
        # 서비스 정보 추가
        if service:
            payload['service_id'] = str(service.id)
            payload['service_name'] = service.name
            
            # 서비스별 사용자 역할 추가
            try:
                service_user = service.serviceuser_set.get(user=user)
                payload['role'] = service_user.role
                payload['permissions'] = service_user.get_permissions()
            except:
                payload['role'] = 'user'
                payload['permissions'] = []
        
        # 추가 클레임
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # 토큰 블랙리스트 확인을 위해 Redis에 저장
        cache_key = f"jwt_token:{payload['jti']}"
        cache.set(cache_key, {
            'user_id': str(user.id),
            'service_id': str(service.id) if service else None,
            'created_at': now.isoformat()
        }, timeout=self.access_token_expire_minutes * 60)
        
        logger.info(f"Access token created for user: {user.username}")
        return token
    
    def create_refresh_token(self, user, service=None) -> str:
        """Refresh Token 생성"""
        
        now = timezone.now()
        expire = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            'user_id': str(user.id),
            'iat': int(now.timestamp()),
            'exp': int(expire.timestamp()),
            'type': 'refresh',
            'jti': str(uuid.uuid4())
        }
        
        if service:
            payload['service_id'] = str(service.id)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # Refresh Token은 더 오래 저장
        cache_key = f"jwt_refresh_token:{payload['jti']}"
        cache.set(cache_key, {
            'user_id': str(user.id),
            'service_id': str(service.id) if service else None,
            'created_at': now.isoformat()
        }, timeout=self.refresh_token_expire_days * 24 * 60 * 60)
        
        logger.info(f"Refresh token created for user: {user.username}")
        return token
    
    def verify_token(self, token: str) -> Tuple[Dict, bool]:
        """토큰 검증"""
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 토큰 타입 확인
            if payload.get('type') not in ['access', 'refresh']:
                return None, False
            
            # 블랙리스트 확인
            jti = payload.get('jti')
            if jti:
                cache_key = f"jwt_blacklist:{jti}"
                if cache.get(cache_key):
                    logger.warning(f"Blacklisted token used: {jti}")
                    return None, False
            
            # 사용자 존재 확인
            try:
                user = User.objects.get(id=payload['user_id'])
                if not user.is_active:
                    return None, False
            except User.DoesNotExist:
                return None, False
            
            return payload, True
            
        except jwt.ExpiredSignatureError:
            logger.warning("Expired token used")
            return None, False
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return None, False
    
    def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """Access Token 갱신"""
        
        payload, is_valid = self.verify_token(refresh_token)
        
        if not is_valid or payload.get('type') != 'refresh':
            raise ValueError("Invalid refresh token")
        
        # 사용자 및 서비스 정보 조회
        try:
            user = User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            raise ValueError("User not found")
        
        service = None
        if payload.get('service_id'):
            try:
                from apps.services.models import Service
                service = Service.objects.get(id=payload['service_id'])
            except Service.DoesNotExist:
                pass
        
        # 새로운 토큰 생성
        new_access_token = self.create_access_token(user, service)
        new_refresh_token = self.create_refresh_token(user, service)
        
        # 기존 refresh token 무효화
        self.revoke_token(refresh_token)
        
        logger.info(f"Token refreshed for user: {user.username}")
        return new_access_token, new_refresh_token
    
    def revoke_token(self, token: str) -> bool:
        """토큰 무효화 (블랙리스트 추가)"""
        
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # 만료된 토큰도 처리
            )
            
            jti = payload.get('jti')
            if jti:
                # 블랙리스트에 추가
                cache_key = f"jwt_blacklist:{jti}"
                exp = payload.get('exp', 0)
                now = int(timezone.now().timestamp())
                
                # 토큰이 아직 유효한 경우에만 블랙리스트에 추가
                if exp > now:
                    timeout = exp - now
                    cache.set(cache_key, True, timeout=timeout)
                
                logger.info(f"Token revoked: {jti}")
                return True
                
        except jwt.InvalidTokenError:
            pass
        
        return False
    
    def get_user_from_token(self, token: str):
        """토큰에서 사용자 객체 반환"""
        
        payload, is_valid = self.verify_token(token)
        
        if not is_valid:
            return None
        
        try:
            return User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            return None

class JWTAuth:
    """Django Ninja JWT 인증 클래스"""
    
    def __init__(self):
        self.jwt_service = JWTAuthService()
    
    def __call__(self, request):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return None
        
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != 'bearer':
                return None
        except ValueError:
            return None
        
        payload, is_valid = self.jwt_service.verify_token(token)
        
        if not is_valid or payload.get('type') != 'access':
            return None
        
        try:
            user = User.objects.get(id=payload['user_id'])
            
            # 사용자 객체에 토큰 정보 추가
            user.token_payload = payload
            
            return user
        except User.DoesNotExist:
            return None
```

### 4.2 인증 관련 스키마

```python
# apps/authentication/schemas.py
from ninja import Schema
from typing import Optional
from datetime import datetime

class LoginSchema(Schema):
    service_id: str
    username: str
    password: str
    remember_me: bool = False

class SocialLoginInitSchema(Schema):
    service_id: str
    provider: str
    redirect_uri: str

class SocialLoginCallbackSchema(Schema):
    service_id: str
    provider: str
    code: str
    state: str
    redirect_uri: str

class SocialLinkSchema(Schema):
    service_id: str
    provider: str
    access_token: str

class TokenRefreshSchema(Schema):
    refresh_token: str

class LoginResponseSchema(Schema):
    access_token: str
    refresh_token: str
    user: dict
    service: dict
    expires_in: int

class TokenResponseSchema(Schema):
    access_token: str
    refresh_token: str
    expires_in: int
```

### 4.3 인증 API 엔드포인트

```python
# apps/authentication/auth_api.py
from ninja import Router
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
import logging

from .jwt_auth import JWTAuthService, JWTAuth
from .schemas import LoginSchema, TokenRefreshSchema, LoginResponseSchema, TokenResponseSchema
from .models import AuthenticationLog
from apps.services.models import Service

logger = logging.getLogger(__name__)
router = Router(tags=["Authentication"])

@router.post("/auth/login", response=LoginResponseSchema)
def login(request, data: LoginSchema):
    """사용자 로그인"""
    
    # 서비스 확인
    try:
        service = Service.objects.get(id=data.service_id, is_active=True)
    except Service.DoesNotExist:
        raise ValueError("Invalid service")
    
    # 사용자 인증
    user = authenticate(username=data.username, password=data.password)
    
    if not user:
        # 실패 로그 기록
        AuthenticationLog.objects.create(
            service=service,
            auth_method='password',
            username=data.username,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            is_successful=False,
            failure_reason='Invalid credentials'
        )
        raise ValueError("Invalid credentials")
    
    if not user.is_active:
        raise ValueError("Account is disabled")
    
    # 계정 잠금 확인
    if user.is_account_locked():
        raise ValueError("Account is temporarily locked")
    
    # 서비스 사용자 확인
    try:
        service_user = service.serviceuser_set.get(user=user)
        if not service_user.is_active:
            raise ValueError("Access denied for this service")
    except service.serviceuser_set.model.DoesNotExist:
        # 새 서비스 사용자 생성
        service_user = service.serviceuser_set.create(
            user=user,
            role='user',
            is_active=True
        )
    
    try:
        with transaction.atomic():
            # JWT 토큰 생성
            jwt_service = JWTAuthService()
            access_token = jwt_service.create_access_token(user, service)
            
            # Remember me 설정에 따른 refresh token 만료 시간 조정
            if data.remember_me:
                jwt_service.refresh_token_expire_days = 30  # 30일
            
            refresh_token = jwt_service.create_refresh_token(user, service)
            
            # 로그인 성공 처리
            user.reset_failed_login()
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # 성공 로그 기록
            AuthenticationLog.objects.create(
                user=user,
                service=service,
                auth_method='password',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                is_successful=True
            )
            
            logger.info(f"User logged in: {user.username} to service {service.name}")
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.get_full_name(),
                    "avatar_url": user.avatar_url
                },
                "service": {
                    "id": str(service.id),
                    "name": service.name,
                    "role": service_user.role
                },
                "expires_in": 15 * 60  # 15분
            }
            
    except Exception as e:
        user.increment_failed_login()
        logger.error(f"Login error: {str(e)}")
        raise

@router.post("/auth/refresh", response=TokenResponseSchema)
def refresh_token(request, data: TokenRefreshSchema):
    """토큰 갱신"""
    
    try:
        jwt_service = JWTAuthService()
        access_token, refresh_token = jwt_service.refresh_access_token(data.refresh_token)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 15 * 60
        }
        
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise ValueError("Invalid refresh token")

@router.post("/auth/logout", auth=JWTAuth())
def logout(request):
    """로그아웃"""
    
    # Authorization 헤더에서 토큰 추출
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            _, token = auth_header.split()
            jwt_service = JWTAuthService()
            jwt_service.revoke_token(token)
        except:
            pass
    
    logger.info(f"User logged out: {request.auth.username}")
    return {"message": "Logged out successfully"}

@router.post("/auth/logout-all", auth=JWTAuth())
def logout_all_devices(request):
    """모든 디바이스에서 로그아웃"""
    
    user = request.auth
    
    # 사용자의 모든 세션 종료
    user.sessions.filter(is_active=True).update(is_active=False)
    
    # TODO: 사용자의 모든 JWT 토큰을 블랙리스트에 추가하는 로직
    # 현재는 개별 토큰만 무효화 가능하므로, 사용자별 토큰 추적 시스템이 필요
    
    logger.info(f"All devices logged out for user: {user.username}")
    return {"message": "Logged out from all devices"}
```

---

## 🛡️ 5. 보안 및 인가 시스템

멀티 서비스 환경에서의 보안은 매우 중요합니다. 역할 기반 접근 제어(RBAC), 2FA, 레이트 리미팅 등의 보안 기능을 구현하여 시스템을 보호합니다.

### 5.1 역할 및 권한 관리

```python
# apps/authentication/permissions.py
from enum import Enum
from typing import List, Dict, Set
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class Permission(Enum):
    """권한 정의"""
    
    # 사용자 관리
    USER_CREATE = "user.create"
    USER_READ = "user.read"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_LIST = "user.list"
    
    # 서비스 관리
    SERVICE_CREATE = "service.create"
    SERVICE_READ = "service.read"
    SERVICE_UPDATE = "service.update"
    SERVICE_DELETE = "service.delete"
    SERVICE_MANAGE = "service.manage"
    
    # 콘텐츠 관리
    CONTENT_CREATE = "content.create"
    CONTENT_READ = "content.read"
    CONTENT_UPDATE = "content.update"
    CONTENT_DELETE = "content.delete"
    CONTENT_PUBLISH = "content.publish"
    
    # 관리자
    ADMIN_PANEL = "admin.panel"
    ADMIN_ANALYTICS = "admin.analytics"
    ADMIN_LOGS = "admin.logs"
    ADMIN_SETTINGS = "admin.settings"
    
    # API 접근
    API_READ = "api.read"
    API_WRITE = "api.write"
    API_ADMIN = "api.admin"

class Role(Enum):
    """역할 정의"""
    
    SUPER_ADMIN = "super_admin"
    SERVICE_ADMIN = "service_admin"
    CONTENT_MANAGER = "content_manager"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"

# 역할별 권한 매핑
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.SUPER_ADMIN: {
        Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE, Permission.USER_DELETE, Permission.USER_LIST,
        Permission.SERVICE_CREATE, Permission.SERVICE_READ, Permission.SERVICE_UPDATE, Permission.SERVICE_DELETE, Permission.SERVICE_MANAGE,
        Permission.CONTENT_CREATE, Permission.CONTENT_READ, Permission.CONTENT_UPDATE, Permission.CONTENT_DELETE, Permission.CONTENT_PUBLISH,
        Permission.ADMIN_PANEL, Permission.ADMIN_ANALYTICS, Permission.ADMIN_LOGS, Permission.ADMIN_SETTINGS,
        Permission.API_READ, Permission.API_WRITE, Permission.API_ADMIN,
    },
    
    Role.SERVICE_ADMIN: {
        Permission.USER_READ, Permission.USER_LIST,
        Permission.SERVICE_READ, Permission.SERVICE_UPDATE, Permission.SERVICE_MANAGE,
        Permission.CONTENT_CREATE, Permission.CONTENT_READ, Permission.CONTENT_UPDATE, Permission.CONTENT_DELETE, Permission.CONTENT_PUBLISH,
        Permission.ADMIN_PANEL, Permission.ADMIN_ANALYTICS,
        Permission.API_READ, Permission.API_WRITE,
    },
    
    Role.CONTENT_MANAGER: {
        Permission.USER_READ,
        Permission.SERVICE_READ,
        Permission.CONTENT_CREATE, Permission.CONTENT_READ, Permission.CONTENT_UPDATE, Permission.CONTENT_DELETE, Permission.CONTENT_PUBLISH,
        Permission.API_READ, Permission.API_WRITE,
    },
    
    Role.MODERATOR: {
        Permission.USER_READ,
        Permission.SERVICE_READ,
        Permission.CONTENT_READ, Permission.CONTENT_UPDATE,
        Permission.API_READ,
    },
    
    Role.USER: {
        Permission.CONTENT_READ,
        Permission.API_READ,
    },
    
    Role.GUEST: {
        Permission.CONTENT_READ,
    }
}

class PermissionManager:
    """권한 관리 클래스"""
    
    @staticmethod
    def get_role_permissions(role: str) -> Set[str]:
        """역할의 권한 목록 반환"""
        
        try:
            role_enum = Role(role)
            permissions = ROLE_PERMISSIONS.get(role_enum, set())
            return {perm.value for perm in permissions}
        except ValueError:
            return set()
    
    @staticmethod
    def has_permission(user_role: str, required_permission: str) -> bool:
        """권한 확인"""
        
        user_permissions = PermissionManager.get_role_permissions(user_role)
        return required_permission in user_permissions
    
    @staticmethod
    def get_user_permissions(user, service=None) -> Set[str]:
        """사용자의 모든 권한 반환"""
        
        cache_key = f"user_permissions:{user.id}:{service.id if service else 'global'}"
        permissions = cache.get(cache_key)
        
        if permissions is None:
            permissions = set()
            
            if service:
                try:
                    service_user = service.serviceuser_set.get(user=user)
                    permissions.update(PermissionManager.get_role_permissions(service_user.role))
                except:
                    pass
            
            # 전역 권한 추가 (슈퍼유저)
            if user.is_superuser:
                permissions.update(PermissionManager.get_role_permissions(Role.SUPER_ADMIN.value))
            
            # 캐시에 저장 (5분)
            cache.set(cache_key, permissions, 300)
        
        return permissions

class PermissionRequired:
    """권한 확인 데코레이터"""
    
    def __init__(self, permission: str, service_required: bool = True):
        self.permission = permission
        self.service_required = service_required
    
    def __call__(self, func):
        def wrapper(request, *args, **kwargs):
            user = getattr(request, 'auth', None)
            
            if not user:
                raise ValueError("Authentication required")
            
            # 서비스 정보 추출
            service = None
            if self.service_required:
                token_payload = getattr(user, 'token_payload', {})
                service_id = token_payload.get('service_id')
                
                if service_id:
                    try:
                        from apps.services.models import Service
                        service = Service.objects.get(id=service_id)
                    except Service.DoesNotExist:
                        raise ValueError("Invalid service")
                else:
                    raise ValueError("Service required")
            
            # 권한 확인
            user_permissions = PermissionManager.get_user_permissions(user, service)
            
            if self.permission not in user_permissions:
                raise ValueError("Permission denied")
            
            return func(request, *args, **kwargs)
        
        return wrapper
```

### 5.2 2단계 인증 (2FA)

```python
# apps/authentication/two_factor.py
import pyotp
import qrcode
import io
import base64
import secrets
from typing import List, Tuple
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class TwoFactorAuthManager:
    """2단계 인증 관리"""
    
    @staticmethod
    def generate_secret() -> str:
        """2FA 시크릿 키 생성"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_qr_code(user, secret: str) -> str:
        """QR 코드 생성"""
        
        # TOTP URI 생성
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name=settings.APP_NAME or "Multi-Service Auth"
        )
        
        # QR 코드 이미지 생성
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Base64로 인코딩
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    @staticmethod
    def verify_totp_code(secret: str, code: str) -> bool:
        """TOTP 코드 검증"""
        
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)  # 30초 전후 허용
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> List[str]:
        """백업 코드 생성"""
        
        codes = []
        for _ in range(count):
            # 8자리 백업 코드 생성
            code = ''.join([str(secrets.randbelow(10)) for _ in range(8)])
            codes.append(f"{code[:4]}-{code[4:]}")
        
        return codes
    
    @staticmethod
    def verify_backup_code(user, code: str) -> bool:
        """백업 코드 검증"""
        
        if code in user.backup_codes:
            # 사용된 백업 코드 제거
            user.backup_codes.remove(code)
            user.save(update_fields=['backup_codes'])
            
            logger.info(f"Backup code used by user: {user.username}")
            return True
        
        return False
    
    @staticmethod
    def enable_2fa(user, totp_code: str) -> Tuple[bool, List[str]]:
        """2FA 활성화"""
        
        if not user.two_factor_secret:
            raise ValueError("2FA secret not generated")
        
        # TOTP 코드 검증
        if not TwoFactorAuthManager.verify_totp_code(user.two_factor_secret, totp_code):
            return False, []
        
        # 백업 코드 생성
        backup_codes = TwoFactorAuthManager.generate_backup_codes()
        
        # 2FA 활성화
        user.two_factor_enabled = True
        user.backup_codes = backup_codes
        user.save(update_fields=['two_factor_enabled', 'backup_codes'])
        
        logger.info(f"2FA enabled for user: {user.username}")
        return True, backup_codes
    
    @staticmethod
    def disable_2fa(user) -> bool:
        """2FA 비활성화"""
        
        user.two_factor_enabled = False
        user.two_factor_secret = ""
        user.backup_codes = []
        user.save(update_fields=['two_factor_enabled', 'two_factor_secret', 'backup_codes'])
        
        logger.info(f"2FA disabled for user: {user.username}")
        return True

class TwoFactorMiddleware:
    """2FA 확인 미들웨어"""
    
    def __init__(self):
        self.required_endpoints = [
            '/api/admin/',
            '/api/services/manage/',
            '/api/users/admin/',
        ]
    
    def require_2fa_verification(self, user, request_path: str) -> bool:
        """2FA 검증이 필요한지 확인"""
        
        if not user.two_factor_enabled:
            return False
        
        # 관리자 기능은 2FA 필수
        for endpoint in self.required_endpoints:
            if request_path.startswith(endpoint):
                return True
        
        return False
    
    def is_2fa_verified(self, user) -> bool:
        """2FA 검증 상태 확인"""
        
        cache_key = f"2fa_verified:{user.id}"
        return cache.get(cache_key, False)
    
    def mark_2fa_verified(self, user, duration_minutes: int = 30):
        """2FA 검증 완료 표시"""
        
        cache_key = f"2fa_verified:{user.id}"
        cache.set(cache_key, True, timeout=duration_minutes * 60)
        
        logger.info(f"2FA verification marked for user: {user.username}")

# 2FA API 스키마
class TwoFactorSetupSchema(Schema):
    pass

class TwoFactorVerifySchema(Schema):
    code: str

class TwoFactorBackupSchema(Schema):
    backup_code: str
```

### 5.3 레이트 리미팅

```python
# apps/authentication/rate_limiting.py
from django.core.cache import cache
from django.http import JsonResponse
from typing import Dict, Tuple
import time
import hashlib
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """레이트 리미터"""
    
    def __init__(self):
        self.limits = {
            'login': {'requests': 5, 'window': 300},  # 5분에 5회
            'register': {'requests': 3, 'window': 3600},  # 1시간에 3회
            'password_reset': {'requests': 3, 'window': 3600},  # 1시간에 3회
            'social_login': {'requests': 10, 'window': 300},  # 5분에 10회
            'api_general': {'requests': 100, 'window': 3600},  # 1시간에 100회
            'api_sensitive': {'requests': 20, 'window': 3600},  # 1시간에 20회
        }
    
    def get_client_identifier(self, request) -> str:
        """클라이언트 식별자 생성"""
        
        # IP 주소 기반
        ip = request.META.get('REMOTE_ADDR', '')
        
        # 인증된 사용자인 경우 사용자 ID 추가
        if hasattr(request, 'auth') and request.auth:
            user_id = str(request.auth.id)
            identifier = f"user:{user_id}:{ip}"
        else:
            identifier = f"ip:{ip}"
        
        return hashlib.md5(identifier.encode()).hexdigest()
    
    def is_rate_limited(self, request, action: str) -> Tuple[bool, Dict]:
        """레이트 리미트 확인"""
        
        if action not in self.limits:
            return False, {}
        
        limit_config = self.limits[action]
        client_id = self.get_client_identifier(request)
        cache_key = f"rate_limit:{action}:{client_id}"
        
        current_time = int(time.time())
        window_start = current_time - limit_config['window']
        
        # 현재 요청 기록 조회
        requests = cache.get(cache_key, [])
        
        # 윈도우 범위 내의 요청만 필터링
        requests = [req_time for req_time in requests if req_time > window_start]
        
        # 현재 요청 추가
        requests.append(current_time)
        
        # 캐시 업데이트
        cache.set(cache_key, requests, timeout=limit_config['window'])
        
        # 제한 확인
        is_limited = len(requests) > limit_config['requests']
        
        rate_limit_info = {
            'limit': limit_config['requests'],
            'remaining': max(0, limit_config['requests'] - len(requests)),
            'reset_time': window_start + limit_config['window'],
            'retry_after': limit_config['window'] if is_limited else 0
        }
        
        if is_limited:
            logger.warning(f"Rate limit exceeded for {client_id} on {action}")
        
        return is_limited, rate_limit_info
    
    def rate_limit_response(self, rate_limit_info: Dict) -> JsonResponse:
        """레이트 리미트 응답 생성"""
        
        response = JsonResponse({
            'error': 'Rate limit exceeded',
            'detail': f"Too many requests. Try again in {rate_limit_info['retry_after']} seconds.",
            'rate_limit': rate_limit_info
        }, status=429)
        
        # 레이트 리미트 헤더 추가
        response['X-RateLimit-Limit'] = rate_limit_info['limit']
        response['X-RateLimit-Remaining'] = rate_limit_info['remaining']
        response['X-RateLimit-Reset'] = rate_limit_info['reset_time']
        response['Retry-After'] = rate_limit_info['retry_after']
        
        return response

def rate_limit(action: str):
    """레이트 리미팅 데코레이터"""
    
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            limiter = RateLimiter()
            is_limited, rate_limit_info = limiter.is_rate_limited(request, action)
            
            if is_limited:
                return limiter.rate_limit_response(rate_limit_info)
            
            # 응답에 레이트 리미트 정보 추가
            response = func(request, *args, **kwargs)
            
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = rate_limit_info['limit']
                response.headers['X-RateLimit-Remaining'] = rate_limit_info['remaining']
                response.headers['X-RateLimit-Reset'] = rate_limit_info['reset_time']
            
            return response
        
        return wrapper
    return decorator
```

---

## 🚀 6. 배포 및 운영

마지막으로 실제 운영 환경에서 사용할 수 있도록 배포 설정과 모니터링을 구성해보겠습니다.

### 6.1 배포 설정

```python
# config/production_settings.py
import os
from .base_settings import *

# 보안 설정
SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# HTTPS 설정
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# 데이터베이스 설정
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# Redis 설정
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'ssl_cert_reqs': None,
            },
        }
    }
}

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"level": "%(levelname)s", "time": "%(asctime)s", "module": "%(module)s", "message": "%(message)s"}',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/auth_service.log',
            'maxBytes': 1024*1024*50,  # 50MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'sentry': {
            'level': 'ERROR',
            'class': 'sentry_sdk.integrations.logging.SentryHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps': {
            'handlers': ['file', 'console', 'sentry'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Celery 설정
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND')
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
```

### 6.2 Docker 설정

```dockerfile
# Dockerfile
FROM python:3.11-slim

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 정적 파일 수집
RUN python manage.py collectstatic --noinput

# 비특권 사용자로 실행
RUN useradd --create-home --shell /bin/bash app
USER app

# 서버 실행
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "config.wsgi:application"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - DB_HOST=postgres
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - ./logs:/var/log/django
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
  
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
  
  celery:
    build: .
    command: celery -A config worker -l info
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - DB_HOST=postgres
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web

volumes:
  postgres_data:
  redis_data:
```

### 6.3 모니터링 및 로깅

```python
# apps/monitoring/health_check.py
from ninja import Router
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)
router = Router(tags=["Monitoring"])

@router.get("/health")
def health_check(request):
    """시스템 상태 확인"""
    
    status = "healthy"
    checks = {}
    
    # 데이터베이스 연결 확인
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
        status = "unhealthy"
    
    # Redis 연결 확인
    try:
        cache.set("health_check", "test", 10)
        cache.get("health_check")
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"
        status = "unhealthy"
    
    # 디스크 사용량 확인
    try:
        import shutil
        disk_usage = shutil.disk_usage("/")
        free_percentage = (disk_usage.free / disk_usage.total) * 100
        
        if free_percentage < 10:
            checks["disk"] = f"warning: {free_percentage:.1f}% free"
            if status == "healthy":
                status = "warning"
        else:
            checks["disk"] = f"healthy: {free_percentage:.1f}% free"
    except Exception as e:
        checks["disk"] = f"unknown: {str(e)}"
    
    response_data = {
        "status": status,
        "timestamp": timezone.now().isoformat(),
        "checks": checks
    }
    
    if status == "unhealthy":
        logger.error(f"Health check failed: {checks}")
        return response_data, 503
    elif status == "warning":
        logger.warning(f"Health check warning: {checks}")
    
    return response_data

@router.get("/metrics")
def system_metrics(request):
    """시스템 메트릭"""
    
    from django.contrib.auth import get_user_model
    from apps.services.models import Service
    from apps.authentication.models import AuthenticationLog
    
    User = get_user_model()
    
    # 사용자 통계
    total_users = User.objects.count()
    active_users_today = AuthenticationLog.objects.filter(
        created_at__date=timezone.now().date(),
        is_successful=True
    ).values('user').distinct().count()
    
    # 서비스 통계
    total_services = Service.objects.filter(is_active=True).count()
    
    # 인증 통계
    today = timezone.now().date()
    login_attempts_today = AuthenticationLog.objects.filter(
        created_at__date=today
    ).count()
    
    successful_logins_today = AuthenticationLog.objects.filter(
        created_at__date=today,
        is_successful=True
    ).count()
    
    return {
        "users": {
            "total": total_users,
            "active_today": active_users_today
        },
        "services": {
            "total": total_services
        },
        "authentication": {
            "login_attempts_today": login_attempts_today,
            "successful_logins_today": successful_logins_today,
            "success_rate": (successful_logins_today / login_attempts_today * 100) if login_attempts_today > 0 else 0
        },
        "timestamp": timezone.now().isoformat()
    }
```

## 📋 결론

Django Ninja를 활용한 멀티 서비스 소셜 로그인 시스템을 구축해보았습니다. 이 시스템의 주요 특징과 장점을 정리하면 다음과 같습니다:

### 🎯 핵심 기능

1. **멀티 서비스 아키텍처**: 하나의 인증 서버로 여러 서비스 지원
2. **소셜 로그인 통합**: Google, Facebook, GitHub, Apple, Kakao, Naver 등 주요 프로바이더 지원
3. **JWT 기반 인증**: Access Token과 Refresh Token 분리로 보안 강화
4. **역할 기반 접근 제어**: 서비스별 세밀한 권한 관리
5. **2단계 인증**: TOTP와 백업 코드를 통한 추가 보안
6. **레이트 리미팅**: API 남용 방지 및 시스템 보호

### 🔧 기술적 장점

- **확장성**: 새로운 서비스와 프로바이더 쉽게 추가 가능
- **보안성**: 현대적 보안 표준 준수 (OAuth 2.0, JWT, 2FA)
- **성능**: Redis 캐싱과 최적화된 데이터베이스 쿼리
- **유지보수성**: 모듈화된 구조와 명확한 책임 분리
- **모니터링**: 포괄적인 로깅과 헬스 체크 시스템

### 🚀 운영 고려사항

1. **데이터베이스 최적화**: 인덱스 설정과 쿼리 최적화
2. **캐시 전략**: Redis를 활용한 세션 관리와 토큰 캐싱
3. **보안 업데이트**: 정기적인 의존성 업데이트와 보안 패치
4. **백업 및 복구**: 정기적인 데이터베이스 백업과 재해 복구 계획
5. **성능 모니터링**: APM 도구를 통한 실시간 성능 추적

### 📈 향후 발전 방향

- **마이크로서비스 분리**: 서비스가 커지면 인증 서비스 분리 고려
- **API 게이트웨이**: Kong, AWS API Gateway 등을 통한 통합 관리
- **쿠버네티스 배포**: 컨테이너 오케스트레이션으로 확장성 향상
- **GraphQL 지원**: REST API와 함께 GraphQL 엔드포인트 제공
- **AI 기반 보안**: 이상 로그인 탐지와 자동 보안 대응

이렇게 구축한 시스템은 스타트업부터 대기업까지 다양한 규모의 조직에서 활용할 수 있는 견고하고 확장 가능한 인증 솔루션입니다. Django Ninja의 현대적 API 개발 경험과 Python 생태계의 풍부한 라이브러리를 활용하여 효율적으로 개발할 수 있었습니다.

---

### 📚 참고 자료

- [Django Ninja 공식 문서](https://django-ninja.rest-framework.com/)
- [OAuth 2.0 RFC](https://tools.ietf.org/html/rfc6749)
- [JWT 공식 사이트](https://jwt.io/)
- [OWASP 인증 가이드](https://owasp.org/www-project-authentication-cheat-sheet/)
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [Facebook Login](https://developers.facebook.com/docs/facebook-login/)
- [GitHub OAuth Apps](https://docs.github.com/en/developers/apps/building-oauth-apps)

### 🏷️ 태그

`Django` `Django-Ninja` `소셜로그인` `OAuth` `JWT` `멀티서비스` `인증` `보안` `Python` `API` `2FA` `RBAC`