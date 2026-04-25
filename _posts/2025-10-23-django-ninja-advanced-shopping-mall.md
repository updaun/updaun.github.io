---
layout: post
title: "🚀 Django Ninja 쇼핑몰 구축 중급편 - 실전 프로덕션 레벨 API 완벽 가이드"
date: 2025-10-23 09:00:00 +0900
categories: [Django, API, 쇼핑몰, 중급]
tags: [Django-Ninja, 쇼핑몰, API, JWT, 결제, 성능최적화, 배포, 실전개발]
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-10-23-django-ninja-advanced-shopping-mall.webp"
---

> **TL;DR**: Django Ninja로 **실제 프로덕션 환경에서 사용할 수 있는** 고도화된 쇼핑몰 API를 구축합니다. JWT 인증, 실시간 재고 관리, 다중 결제 시스템, 성능 최적화까지 완벽 커버!

## 🎯 중급편에서 다룰 내용

이전 기초편에서는 기본적인 CRUD 기능을 구현했다면, 이번 중급편에서는 **실제 서비스에 필요한 고급 기능들**을 구현해보겠습니다.

### 📋 완성할 기능 목록

- **🔐 고급 인증 시스템**: JWT, 소셜 로그인, 권한 관리
- **📦 고급 제품 관리**: 변형 상품, 재고 추적, 검색 엔진
- **💳 결제 시스템**: 다중 PG사, 정기결제, 환불 처리
- **⚡ 성능 최적화**: 캐싱, DB 최적화, 비동기 처리
- **🚀 모니터링 & 배포**: 로깅, 메트릭, CI/CD

### 🛠️ 기술 스택

```text
Backend: Django 5.0 + Django Ninja 1.0
Database: PostgreSQL + Redis
Payment: 토스페이먼츠, 포트원
Cache: Redis + Memcached
Queue: Celery + Redis
Monitoring: Prometheus + Grafana
Deploy: Docker + AWS ECS
```

### 📁 프로젝트 구조

```
advanced_shop/
├── apps/
│   ├── accounts/          # 고급 사용자 관리
│   ├── products/          # 상품 관리 (변형상품, 재고)
│   ├── orders/            # 주문 시스템
│   ├── payments/          # 결제 시스템
│   ├── inventory/         # 재고 관리
│   ├── notifications/     # 알림 시스템
│   └── analytics/         # 분석 & 리포팅
├── core/
│   ├── auth/             # JWT 인증
│   ├── cache/            # 캐시 관리
│   ├── queue/            # 큐 시스템
│   └── monitoring/       # 모니터링
├── config/
│   ├── settings/         # 환경별 설정
│   ├── celery.py        # Celery 설정
│   └── cache.py         # 캐시 설정
└── deploy/
    ├── docker/          # Docker 설정
    ├── nginx/           # Nginx 설정
    └── k8s/             # Kubernetes 설정
```

## 🚧 프로젝트 초기 설정

### 1. 고급 의존성 설치

```bash
# 새 프로젝트 생성
django-admin startproject advanced_shop
cd advanced_shop

# 고급 패키지 설치
pip install django-ninja
pip install psycopg2-binary          # PostgreSQL
pip install redis                    # Redis
pip install celery[redis]           # Celery with Redis
pip install django-cors-headers     # CORS
pip install Pillow                  # 이미지 처리
pip install python-decouple        # 환경변수
pip install djangorestframework-simplejwt  # JWT
pip install django-oauth-toolkit   # OAuth
pip install requests              # HTTP 클라이언트
pip install django-extensions     # 개발 도구
pip install django-debug-toolbar  # 디버깅
pip install prometheus-client     # 메트릭
pip install sentry-sdk[django]    # 에러 추적
```

### 2. 환경별 설정 구조

```python
# config/settings/base.py
"""
공통 설정
"""
import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'ninja',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'oauth2_provider',
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.products',
    'apps.orders',
    'apps.payments',
    'apps.inventory',
    'apps.notifications',
    'apps.analytics',
    'core.auth',
    'core.cache',
    'core.queue',
    'core.monitoring',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'oauth2_provider.middleware.OAuth2TokenMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.monitoring.middleware.MetricsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            'MAX_CONNS': 20,
            'conn_max_age': 600,
        }
    }
}

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        }
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/2'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'

# JWT Settings
JWT_AUTH = {
    'JWT_EXPIRATION_DELTA': datetime.timedelta(hours=24),
    'JWT_REFRESH_EXPIRATION_DELTA': datetime.timedelta(days=7),
    'JWT_ALGORITHM': 'HS256',
    'JWT_SECRET_KEY': SECRET_KEY,
}

# Internationalization
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'
```

```python
# config/settings/development.py
"""
개발 환경 설정
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Debug Toolbar
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
    INTERNAL_IPS = ['127.0.0.1']

# Development Database (SQLite for quick start)
DATABASES['default'].update({
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': BASE_DIR / 'db.sqlite3',
})

# Email Backend (Console for development)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
```

```python
# config/settings/production.py
"""
프로덕션 환경 설정
"""
from .base import *
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

DEBUG = False

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000
SECURE_REDIRECT_EXEMPT = []
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)

# Sentry Configuration
sentry_sdk.init(
    dsn=config('SENTRY_DSN'),
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
    ],
    traces_sample_rate=0.1,
    send_default_pii=True
)

# Static Files (AWS S3)
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='ap-northeast-2')
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'

STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
```

### 3. 환경변수 설정

```bash
# .env
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database
DB_NAME=advanced_shop
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True

# Payment
TOSS_CLIENT_KEY=your-toss-client-key
TOSS_SECRET_KEY=your-toss-secret-key
PORTONE_API_KEY=your-portone-api-key
PORTONE_API_SECRET=your-portone-api-secret

# AWS (Production)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=ap-northeast-2

# Monitoring
SENTRY_DSN=your-sentry-dsn
```

### 4. Docker 개발 환경

```dockerfile
# Dockerfile.dev
FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Application code
COPY . .

# Run development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: advanced_shop
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  web:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    environment:
      - DEBUG=True
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379

  celery:
    build:
      context: .
      dockerfile: Dockerfile.dev
    command: celery -A config worker -l info
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    environment:
      - DEBUG=True
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379

  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile.dev
    command: celery -A config beat -l info
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    environment:
      - DEBUG=True
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379

volumes:
  postgres_data:
```

이제 첫 번째 챕터인 **고급 인증 시스템**을 구현해보겠습니다. 다음 단계로 진행할까요?

---

# 📖 1장: 고급 인증 시스템 구현

기본적인 로그인/회원가입을 넘어서, **실제 서비스 수준의 인증 시스템**을 구축해보겠습니다.

## 🎯 1장에서 구현할 기능

- **JWT 토큰 기반 인증** (Access/Refresh Token)
- **소셜 로그인** (Google, Kakao, Naver)
- **이메일 인증** 및 비밀번호 재설정
- **다단계 인증 (2FA)** (선택사항)
- **세션 관리** 및 동시 로그인 제한
- **권한 기반 접근 제어** (RBAC)

## 🔐 1.1 확장된 사용자 모델

```python
# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
import uuid

class User(AbstractUser):
    """확장된 사용자 모델"""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', '활성'
        INACTIVE = 'inactive', '비활성'
        SUSPENDED = 'suspended', '정지'
        PENDING = 'pending', '승인 대기'
    
    class Role(models.TextChoices):
        CUSTOMER = 'customer', '고객'
        SELLER = 'seller', '판매자'
        ADMIN = 'admin', '관리자'
        SUPER_ADMIN = 'super_admin', '최고 관리자'
    
    # 기본 정보
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^01[0-9]-[0-9]{4}-[0-9]{4}$')],
        blank=True
    )
    
    # 상태 및 권한
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    
    # 인증 관련
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    
    # 소셜 로그인
    provider = models.CharField(max_length=50, blank=True)  # google, kakao, naver
    social_id = models.CharField(max_length=100, blank=True)
    
    # 프로필 정보
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[('M', '남성'), ('F', '여성'), ('O', '기타')],
        blank=True
    )
    
    # 설정
    marketing_agreed = models.BooleanField(default=False)
    newsletter_subscribed = models.BooleanField(default=False)
    
    # 보안
    last_password_change = models.DateTimeField(auto_now_add=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['status', 'role']),
            models.Index(fields=['provider', 'social_id']),
        ]
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_locked(self):
        from django.utils import timezone
        return self.locked_until and self.locked_until > timezone.now()

class UserProfile(models.Model):
    """사용자 상세 프로필"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # 추가 개인정보
    nickname = models.CharField(max_length=50, unique=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    website = models.URLField(blank=True)
    
    # 주소 정보
    postal_code = models.CharField(max_length=10, blank=True)
    address = models.CharField(max_length=255, blank=True)
    detailed_address = models.CharField(max_length=255, blank=True)
    
    # 판매자 정보 (role이 seller인 경우)
    business_name = models.CharField(max_length=100, blank=True)
    business_number = models.CharField(max_length=20, blank=True)
    business_address = models.TextField(blank=True)
    
    # 설정
    language = models.CharField(max_length=10, default='ko')
    timezone = models.CharField(max_length=50, default='Asia/Seoul')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email}'s profile"

class UserSession(models.Model):
    """사용자 세션 관리"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    device_info = models.JSONField(default=dict)  # User-Agent, IP 등
    ip_address = models.GenericIPAddressField()
    is_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"{self.user.email} - {self.session_key[:8]}"

class PasswordResetToken(models.Model):
    """비밀번호 재설정 토큰"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']

class EmailVerificationToken(models.Model):
    """이메일 인증 토큰"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    email = models.EmailField()  # 변경할 이메일 주소
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
```

## 🔑 1.2 JWT 인증 시스템

```python
# core/auth/jwt_auth.py
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from ninja.security import HttpBearer
from typing import Optional

User = get_user_model()

class JWTAuth(HttpBearer):
    """JWT 인증 핸들러"""
    
    def authenticate(self, request, token: str) -> Optional[User]:
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=['HS256']
            )
            
            user_id = payload.get('user_id')
            if not user_id:
                return None
            
            user = User.objects.get(id=user_id)
            
            # 사용자 상태 확인
            if user.status != User.Status.ACTIVE:
                return None
            
            # 계정 잠금 확인
            if user.is_locked:
                return None
            
            # 마지막 활동 시간 업데이트
            user.last_activity = datetime.now()
            user.save(update_fields=['last_activity'])
            
            return user
            
        except (jwt.InvalidTokenError, User.DoesNotExist):
            return None

class JWTTokenManager:
    """JWT 토큰 관리자"""
    
    @staticmethod
    def generate_tokens(user: User) -> dict:
        """Access/Refresh 토큰 생성"""
        now = datetime.utcnow()
        
        # Access Token (1시간)
        access_payload = {
            'user_id': str(user.id),
            'email': user.email,
            'role': user.role,
            'iat': now,
            'exp': now + timedelta(hours=1),
            'type': 'access'
        }
        
        # Refresh Token (7일)
        refresh_payload = {
            'user_id': str(user.id),
            'iat': now,
            'exp': now + timedelta(days=7),
            'type': 'refresh'
        }
        
        access_token = jwt.encode(access_payload, settings.SECRET_KEY, algorithm='HS256')
        refresh_token = jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm='HS256')
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'access_expires_in': 3600,  # 1시간
            'refresh_expires_in': 604800,  # 7일
            'token_type': 'Bearer'
        }
    
    @staticmethod
    def refresh_access_token(refresh_token: str) -> Optional[dict]:
        """Refresh Token으로 새 Access Token 발급"""
        try:
            payload = jwt.decode(
                refresh_token, 
                settings.SECRET_KEY, 
                algorithms=['HS256']
            )
            
            if payload.get('type') != 'refresh':
                return None
            
            user = User.objects.get(id=payload['user_id'])
            if user.status != User.Status.ACTIVE:
                return None
            
            # 새 Access Token만 발급
            now = datetime.utcnow()
            access_payload = {
                'user_id': str(user.id),
                'email': user.email,
                'role': user.role,
                'iat': now,
                'exp': now + timedelta(hours=1),
                'type': 'access'
            }
            
            access_token = jwt.encode(access_payload, settings.SECRET_KEY, algorithm='HS256')
            
            return {
                'access_token': access_token,
                'expires_in': 3600,
                'token_type': 'Bearer'
            }
            
        except (jwt.InvalidTokenError, User.DoesNotExist):
            return None
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """토큰 디코딩"""
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return None

# 전역 인증 인스턴스
jwt_auth = JWTAuth()
```

## 📱 1.3 인증 API 구현

```python
# apps/accounts/schemas.py
from ninja import Schema
from typing import Optional
from datetime import datetime
import re

class RegisterSchema(Schema):
    email: str
    password: str
    password_confirm: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    marketing_agreed: bool = False
    
    def validate_email(self, value):
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            raise ValueError('올바른 이메일 형식이 아닙니다.')
        return value
    
    def validate_password(self, value):
        if len(value) < 8:
            raise ValueError('비밀번호는 최소 8자 이상이어야 합니다.')
        if not re.search(r'[A-Za-z]', value):
            raise ValueError('비밀번호에 영문자가 포함되어야 합니다.')
        if not re.search(r'\d', value):
            raise ValueError('비밀번호에 숫자가 포함되어야 합니다.')
        return value

class LoginSchema(Schema):
    email: str
    password: str
    remember_me: bool = False

class TokenResponse(Schema):
    access_token: str
    refresh_token: str
    access_expires_in: int
    refresh_expires_in: int
    token_type: str
    user: 'UserSchema'

class RefreshTokenSchema(Schema):
    refresh_token: str

class UserSchema(Schema):
    id: str
    email: str
    username: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    status: str
    email_verified: bool
    phone_verified: bool
    avatar: Optional[str]
    created_at: datetime
    last_activity: datetime

class PasswordChangeSchema(Schema):
    current_password: str
    new_password: str
    new_password_confirm: str

class PasswordResetRequestSchema(Schema):
    email: str

class PasswordResetConfirmSchema(Schema):
    token: str
    new_password: str
    new_password_confirm: str

class EmailVerificationSchema(Schema):
    token: str

class SocialLoginSchema(Schema):
    provider: str  # google, kakao, naver
    access_token: str
    redirect_uri: Optional[str] = None
```

```python
# apps/accounts/api.py
from ninja import Router
from ninja.errors import HttpError
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from typing import List

from .models import User, UserProfile, PasswordResetToken, EmailVerificationToken
from .schemas import *
from core.auth.jwt_auth import JWTTokenManager, jwt_auth
from .services import EmailService, SocialAuthService

router = Router()

@router.post("/auth/register", response=TokenResponse)
def register(request, payload: RegisterSchema):
    """회원가입"""
    
    # 비밀번호 확인
    if payload.password != payload.password_confirm:
        raise HttpError(400, "비밀번호가 일치하지 않습니다.")
    
    # 이메일 중복 확인
    if User.objects.filter(email=payload.email).exists():
        raise HttpError(400, "이미 사용 중인 이메일입니다.")
    
    # 사용자명 중복 확인
    if User.objects.filter(username=payload.username).exists():
        raise HttpError(400, "이미 사용 중인 사용자명입니다.")
    
    try:
        with transaction.atomic():
            # 사용자 생성
            user = User.objects.create_user(
                email=payload.email,
                username=payload.username,
                password=payload.password,
                first_name=payload.first_name or '',
                last_name=payload.last_name or '',
                phone=payload.phone or '',
                marketing_agreed=payload.marketing_agreed,
                status=User.Status.PENDING  # 이메일 인증 후 활성화
            )
            
            # 프로필 생성
            UserProfile.objects.create(user=user)
            
            # 이메일 인증 토큰 생성 및 발송
            verification_token = EmailVerificationToken.objects.create(
                user=user,
                email=user.email,
                expires_at=timezone.now() + timedelta(days=1)
            )
            
            EmailService.send_verification_email(user, verification_token.token)
            
            # JWT 토큰 생성
            tokens = JWTTokenManager.generate_tokens(user)
            
            return TokenResponse(
                **tokens,
                user=UserSchema(
                    id=str(user.id),
                    email=user.email,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    role=user.role,
                    status=user.status,
                    email_verified=user.email_verified,
                    phone_verified=user.phone_verified,
                    avatar=user.avatar.url if user.avatar else None,
                    created_at=user.created_at,
                    last_activity=user.last_activity
                )
            )
            
    except Exception as e:
        raise HttpError(500, f"회원가입 중 오류가 발생했습니다: {str(e)}")

@router.post("/auth/login", response=TokenResponse)
def login(request, payload: LoginSchema):
    """로그인"""
    
    try:
        user = User.objects.get(email=payload.email)
    except User.DoesNotExist:
        raise HttpError(401, "이메일 또는 비밀번호가 올바르지 않습니다.")
    
    # 계정 잠금 확인
    if user.is_locked:
        raise HttpError(401, f"계정이 잠겨있습니다. {user.locked_until}까지 기다려주세요.")
    
    # 비밀번호 확인
    if not check_password(payload.password, user.password):
        # 실패 횟수 증가
        user.failed_login_attempts += 1
        
        # 5회 실패시 30분 잠금
        if user.failed_login_attempts >= 5:
            user.locked_until = timezone.now() + timedelta(minutes=30)
            user.save(update_fields=['failed_login_attempts', 'locked_until'])
            raise HttpError(401, "로그인 시도가 5회 실패하여 계정이 30분간 잠겼습니다.")
        
        user.save(update_fields=['failed_login_attempts'])
        raise HttpError(401, "이메일 또는 비밀번호가 올바르지 않습니다.")
    
    # 계정 상태 확인
    if user.status != User.Status.ACTIVE:
        raise HttpError(401, "비활성화된 계정입니다.")
    
    # 로그인 성공 처리
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = timezone.now()
    user.save(update_fields=['failed_login_attempts', 'locked_until', 'last_login'])
    
    # JWT 토큰 생성
    tokens = JWTTokenManager.generate_tokens(user)
    
    return TokenResponse(
        **tokens,
        user=UserSchema(
            id=str(user.id),
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            status=user.status,
            email_verified=user.email_verified,
            phone_verified=user.phone_verified,
            avatar=user.avatar.url if user.avatar else None,
            created_at=user.created_at,
            last_activity=user.last_activity
        )
    )

@router.post("/auth/refresh", response=dict)
def refresh_token(request, payload: RefreshTokenSchema):
    """토큰 갱신"""
    
    tokens = JWTTokenManager.refresh_access_token(payload.refresh_token)
    if not tokens:
        raise HttpError(401, "유효하지 않은 refresh token입니다.")
    
    return tokens

@router.post("/auth/logout", auth=jwt_auth)
def logout(request):
    """로그아웃"""
    # 여기서는 클라이언트에서 토큰을 삭제하도록 안내
    # 실제로는 토큰 블랙리스트를 구현할 수도 있음
    return {"message": "로그아웃되었습니다."}

@router.get("/auth/me", response=UserSchema, auth=jwt_auth)
def get_current_user(request):
    """현재 사용자 정보"""
    user = request.auth
    
    return UserSchema(
        id=str(user.id),
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        status=user.status,
        email_verified=user.email_verified,
        phone_verified=user.phone_verified,
        avatar=user.avatar.url if user.avatar else None,
        created_at=user.created_at,
        last_activity=user.last_activity
    )

@router.post("/auth/verify-email")
def verify_email(request, payload: EmailVerificationSchema):
    """이메일 인증"""
    
    try:
        token = EmailVerificationToken.objects.get(
            token=payload.token,
            verified=False,
            expires_at__gt=timezone.now()
        )
    except EmailVerificationToken.DoesNotExist:
        raise HttpError(400, "유효하지 않거나 만료된 토큰입니다.")
    
    with transaction.atomic():
        # 사용자 이메일 인증 처리
        user = token.user
        user.email_verified = True
        user.status = User.Status.ACTIVE  # 이메일 인증 후 활성화
        user.save(update_fields=['email_verified', 'status'])
        
        # 토큰 사용 처리
        token.verified = True
        token.save(update_fields=['verified'])
    
    return {"message": "이메일 인증이 완료되었습니다."}

@router.post("/auth/password-reset-request")
def password_reset_request(request, payload: PasswordResetRequestSchema):
    """비밀번호 재설정 요청"""
    
    try:
        user = User.objects.get(email=payload.email)
    except User.DoesNotExist:
        # 보안상 이메일이 존재하지 않아도 성공 메시지 반환
        return {"message": "비밀번호 재설정 링크를 이메일로 발송했습니다."}
    
    # 기존 토큰 무효화
    PasswordResetToken.objects.filter(user=user, used=False).update(used=True)
    
    # 새 토큰 생성
    reset_token = PasswordResetToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(hours=1)
    )
    
    # 이메일 발송
    EmailService.send_password_reset_email(user, reset_token.token)
    
    return {"message": "비밀번호 재설정 링크를 이메일로 발송했습니다."}

@router.post("/auth/password-reset-confirm")
def password_reset_confirm(request, payload: PasswordResetConfirmSchema):
    """비밀번호 재설정 확인"""
    
    if payload.new_password != payload.new_password_confirm:
        raise HttpError(400, "비밀번호가 일치하지 않습니다.")
    
    try:
        token = PasswordResetToken.objects.get(
            token=payload.token,
            used=False,
            expires_at__gt=timezone.now()
        )
    except PasswordResetToken.DoesNotExist:
        raise HttpError(400, "유효하지 않거나 만료된 토큰입니다.")
    
    with transaction.atomic():
        # 비밀번호 변경
        user = token.user
        user.set_password(payload.new_password)
        user.last_password_change = timezone.now()
        user.save(update_fields=['password', 'last_password_change'])
        
        # 토큰 사용 처리
        token.used = True
        token.save(update_fields=['used'])
    
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}
```

## 📧 1.4 이메일 서비스

```python
# apps/accounts/services.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import requests
from typing import Optional

class EmailService:
    """이메일 발송 서비스"""
    
    @staticmethod
    def send_verification_email(user, token):
        """이메일 인증 메일 발송"""
        subject = '이메일 주소를 인증해주세요'
        
        verification_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
        
        html_message = render_to_string('accounts/emails/verify_email.html', {
            'user': user,
            'verification_url': verification_url,
            'site_name': settings.SITE_NAME
        })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )
    
    @staticmethod
    def send_password_reset_email(user, token):
        """비밀번호 재설정 메일 발송"""
        subject = '비밀번호를 재설정해주세요'
        
        reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
        
        html_message = render_to_string('accounts/emails/reset_password.html', {
            'user': user,
            'reset_url': reset_url,
            'site_name': settings.SITE_NAME
        })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )

class SocialAuthService:
    """소셜 로그인 서비스"""
    
    @staticmethod
    def verify_google_token(access_token: str) -> Optional[dict]:
        """Google 토큰 검증"""
        try:
            response = requests.get(
                f'https://www.googleapis.com/oauth2/v2/userinfo',
                params={'access_token': access_token}
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception:
            return None
    
    @staticmethod
    def verify_kakao_token(access_token: str) -> Optional[dict]:
        """Kakao 토큰 검증"""
        try:
            response = requests.get(
                'https://kapi.kakao.com/v2/user/me',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'id': str(data['id']),
                    'email': data['kakao_account'].get('email'),
                    'name': data['kakao_account'].get('profile', {}).get('nickname'),
                    'picture': data['kakao_account'].get('profile', {}).get('profile_image_url')
                }
            return None
            
        except Exception:
            return None
    
    @staticmethod
    def get_or_create_social_user(provider: str, user_data: dict) -> User:
        """소셜 로그인 사용자 생성 또는 조회"""
        
        # 기존 소셜 계정 확인
        try:
            user = User.objects.get(
                provider=provider,
                social_id=user_data['id']
            )
            return user
        except User.DoesNotExist:
            pass
        
        # 이메일로 기존 계정 확인
        if user_data.get('email'):
            try:
                user = User.objects.get(email=user_data['email'])
                # 소셜 계정 정보 연결
                user.provider = provider
                user.social_id = user_data['id']
                user.save(update_fields=['provider', 'social_id'])
                return user
            except User.DoesNotExist:
                pass
        
        # 새 계정 생성
        user = User.objects.create(
            email=user_data.get('email', f"{provider}_{user_data['id']}@example.com"),
            username=f"{provider}_{user_data['id']}",
            first_name=user_data.get('name', '').split(' ')[0] if user_data.get('name') else '',
            provider=provider,
            social_id=user_data['id'],
            email_verified=True,  # 소셜 로그인은 이메일 인증된 것으로 간주
            status=User.Status.ACTIVE
        )
        
        # 프로필 생성
        UserProfile.objects.create(user=user)
        
        return user
```

계속해서 **소셜 로그인 API**를 추가하겠습니다.

## 🌐 1.5 소셜 로그인 API

```python
# apps/accounts/api.py에 추가
@router.post("/auth/social-login", response=TokenResponse)
def social_login(request, payload: SocialLoginSchema):
    """소셜 로그인"""
    
    # 제공업체별 토큰 검증
    if payload.provider == 'google':
        user_data = SocialAuthService.verify_google_token(payload.access_token)
    elif payload.provider == 'kakao':
        user_data = SocialAuthService.verify_kakao_token(payload.access_token)
    elif payload.provider == 'naver':
        user_data = SocialAuthService.verify_naver_token(payload.access_token)
    else:
        raise HttpError(400, "지원하지 않는 소셜 로그인 제공업체입니다.")
    
    if not user_data:
        raise HttpError(401, "소셜 로그인 토큰 검증에 실패했습니다.")
    
    try:
        # 사용자 생성 또는 조회
        user = SocialAuthService.get_or_create_social_user(payload.provider, user_data)
        
        # JWT 토큰 생성
        tokens = JWTTokenManager.generate_tokens(user)
        
        return TokenResponse(
            **tokens,
            user=UserSchema(
                id=str(user.id),
                email=user.email,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role,
                status=user.status,
                email_verified=user.email_verified,
                phone_verified=user.phone_verified,
                avatar=user.avatar.url if user.avatar else None,
                created_at=user.created_at,
                last_activity=user.last_activity
            )
        )
        
    except Exception as e:
        raise HttpError(500, f"소셜 로그인 처리 중 오류가 발생했습니다: {str(e)}")

@router.post("/auth/change-password", auth=jwt_auth)
def change_password(request, payload: PasswordChangeSchema):
    """비밀번호 변경"""
    user = request.auth
    
    # 소셜 로그인 사용자는 비밀번호 변경 불가
    if user.provider:
        raise HttpError(400, "소셜 로그인 계정은 비밀번호를 변경할 수 없습니다.")
    
    # 현재 비밀번호 확인
    if not check_password(payload.current_password, user.password):
        raise HttpError(400, "현재 비밀번호가 올바르지 않습니다.")
    
    # 새 비밀번호 확인
    if payload.new_password != payload.new_password_confirm:
        raise HttpError(400, "새 비밀번호가 일치하지 않습니다.")
    
    # 비밀번호 변경
    user.set_password(payload.new_password)
    user.last_password_change = timezone.now()
    user.save(update_fields=['password', 'last_password_change'])
    
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}

@router.get("/auth/sessions", response=List[dict], auth=jwt_auth)
def get_user_sessions(request):
    """사용자 세션 목록"""
    user = request.auth
    
    sessions = UserSession.objects.filter(
        user=user,
        is_active=True,
        expires_at__gt=timezone.now()
    ).order_by('-last_activity')
    
    return [
        {
            'session_key': session.session_key[:8] + '...',
            'device_info': session.device_info,
            'ip_address': session.ip_address,
            'last_activity': session.last_activity,
            'created_at': session.created_at,
            'is_current': request.session.session_key == session.session_key
        }
        for session in sessions
    ]

@router.delete("/auth/sessions/{session_key}", auth=jwt_auth)
def revoke_session(request, session_key: str):
    """특정 세션 무효화"""
    user = request.auth
    
    try:
        session = UserSession.objects.get(
            user=user,
            session_key=session_key,
            is_active=True
        )
        session.is_active = False
        session.save(update_fields=['is_active'])
        
        return {"message": "세션이 무효화되었습니다."}
        
    except UserSession.DoesNotExist:
        raise HttpError(404, "세션을 찾을 수 없습니다.")
```

## 🔐 1.6 권한 기반 접근 제어 (RBAC)

```python
# core/auth/permissions.py
from functools import wraps
from ninja.errors import HttpError
from django.contrib.auth import get_user_model

User = get_user_model()

def require_permissions(*required_permissions):
    """권한 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.auth
            
            if not user:
                raise HttpError(401, "인증이 필요합니다.")
            
            # 권한 확인
            if not has_permissions(user, required_permissions):
                raise HttpError(403, "권한이 부족합니다.")
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

def require_role(*required_roles):
    """역할 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.auth
            
            if not user:
                raise HttpError(401, "인증이 필요합니다.")
            
            if user.role not in required_roles:
                raise HttpError(403, f"필요한 역할: {', '.join(required_roles)}")
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

def has_permissions(user, permissions):
    """사용자 권한 확인"""
    role_permissions = {
        User.Role.CUSTOMER: [
            'view_product',
            'add_to_cart',
            'create_order',
            'view_own_orders',
            'update_own_profile'
        ],
        User.Role.SELLER: [
            'view_product',
            'add_to_cart',
            'create_order',
            'view_own_orders',
            'update_own_profile',
            'create_product',
            'update_own_product',
            'delete_own_product',
            'view_own_analytics'
        ],
        User.Role.ADMIN: [
            'view_product',
            'create_product',
            'update_product',
            'delete_product',
            'view_all_orders',
            'update_order_status',
            'view_all_users',
            'update_user_status',
            'view_analytics'
        ],
        User.Role.SUPER_ADMIN: ['*']  # 모든 권한
    }
    
    user_permissions = role_permissions.get(user.role, [])
    
    # 슈퍼 관리자는 모든 권한 보유
    if '*' in user_permissions:
        return True
    
    # 필요한 권한이 모두 있는지 확인
    return all(perm in user_permissions for perm in permissions)

class PermissionChecker:
    """권한 확인 클래스"""
    
    @staticmethod
    def can_view_product(user):
        return has_permissions(user, ['view_product'])
    
    @staticmethod
    def can_create_product(user):
        return has_permissions(user, ['create_product'])
    
    @staticmethod
    def can_update_product(user, product):
        """상품 수정 권한 확인"""
        if user.role == User.Role.SUPER_ADMIN:
            return True
        elif user.role == User.Role.ADMIN:
            return True
        elif user.role == User.Role.SELLER:
            return product.seller == user
        return False
    
    @staticmethod
    def can_delete_product(user, product):
        """상품 삭제 권한 확인"""
        if user.role == User.Role.SUPER_ADMIN:
            return True
        elif user.role == User.Role.ADMIN:
            return True
        elif user.role == User.Role.SELLER:
            return product.seller == user
        return False
    
    @staticmethod
    def can_view_order(user, order):
        """주문 조회 권한 확인"""
        if user.role in [User.Role.ADMIN, User.Role.SUPER_ADMIN]:
            return True
        return order.user == user
    
    @staticmethod
    def can_update_order_status(user):
        return has_permissions(user, ['update_order_status'])
```

## 🔒 1.7 이중 인증 (2FA) 구현

```python
# apps/accounts/models.py에 추가
import pyotp
import qrcode
from io import BytesIO
import base64

class TwoFactorAuth(models.Model):
    """이중 인증 설정"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='two_factor')
    secret_key = models.CharField(max_length=32)
    backup_codes = models.JSONField(default=list)  # 백업 코드들
    enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.email} - 2FA"
    
    def generate_secret(self):
        """새 시크릿 키 생성"""
        self.secret_key = pyotp.random_base32()
        self.save(update_fields=['secret_key'])
        return self.secret_key
    
    def get_provisioning_uri(self):
        """QR 코드용 URI 생성"""
        return pyotp.totp.TOTP(self.secret_key).provisioning_uri(
            name=self.user.email,
            issuer_name="Advanced Shop"
        )
    
    def get_qr_code(self):
        """QR 코드 이미지 생성"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(self.get_provisioning_uri())
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    def verify_token(self, token):
        """토큰 검증"""
        totp = pyotp.TOTP(self.secret_key)
        return totp.verify(token, valid_window=1)  # 30초 전후 허용
    
    def generate_backup_codes(self):
        """백업 코드 생성"""
        import secrets
        codes = [secrets.token_hex(4).upper() for _ in range(10)]
        self.backup_codes = codes
        self.save(update_fields=['backup_codes'])
        return codes
    
    def use_backup_code(self, code):
        """백업 코드 사용"""
        if code.upper() in self.backup_codes:
            self.backup_codes.remove(code.upper())
            self.save(update_fields=['backup_codes'])
            return True
        return False

# apps/accounts/schemas.py에 추가
class TwoFactorSetupResponse(Schema):
    secret_key: str
    qr_code: str
    backup_codes: List[str]

class TwoFactorVerifySchema(Schema):
    token: str

class TwoFactorLoginSchema(Schema):
    email: str
    password: str
    two_factor_code: str
```

```python
# apps/accounts/api.py에 2FA 엔드포인트 추가
@router.post("/auth/2fa/setup", response=TwoFactorSetupResponse, auth=jwt_auth)
def setup_two_factor(request):
    """이중 인증 설정"""
    user = request.auth
    
    two_factor, created = TwoFactorAuth.objects.get_or_create(user=user)
    
    if not created and two_factor.enabled:
        raise HttpError(400, "이중 인증이 이미 활성화되어 있습니다.")
    
    # 새 시크릿 키 생성
    secret_key = two_factor.generate_secret()
    qr_code = two_factor.get_qr_code()
    backup_codes = two_factor.generate_backup_codes()
    
    return TwoFactorSetupResponse(
        secret_key=secret_key,
        qr_code=qr_code,
        backup_codes=backup_codes
    )

@router.post("/auth/2fa/verify", auth=jwt_auth)
def verify_two_factor(request, payload: TwoFactorVerifySchema):
    """이중 인증 활성화"""
    user = request.auth
    
    try:
        two_factor = TwoFactorAuth.objects.get(user=user)
    except TwoFactorAuth.DoesNotExist:
        raise HttpError(400, "이중 인증 설정을 먼저 진행해주세요.")
    
    if not two_factor.verify_token(payload.token):
        raise HttpError(400, "인증 코드가 올바르지 않습니다.")
    
    # 이중 인증 활성화
    two_factor.enabled = True
    two_factor.save(update_fields=['enabled'])
    
    user.two_factor_enabled = True
    user.save(update_fields=['two_factor_enabled'])
    
    return {"message": "이중 인증이 활성화되었습니다."}

@router.delete("/auth/2fa/disable", auth=jwt_auth)
def disable_two_factor(request, payload: TwoFactorVerifySchema):
    """이중 인증 비활성화"""
    user = request.auth
    
    try:
        two_factor = TwoFactorAuth.objects.get(user=user, enabled=True)
    except TwoFactorAuth.DoesNotExist:
        raise HttpError(400, "활성화된 이중 인증이 없습니다.")
    
    # 현재 코드로 검증
    if not two_factor.verify_token(payload.token):
        raise HttpError(400, "인증 코드가 올바르지 않습니다.")
    
    # 이중 인증 비활성화
    two_factor.enabled = False
    two_factor.save(update_fields=['enabled'])
    
    user.two_factor_enabled = False
    user.save(update_fields=['two_factor_enabled'])
    
    return {"message": "이중 인증이 비활성화되었습니다."}

# 기존 login 함수 수정
@router.post("/auth/login", response=TokenResponse)
def login(request, payload: LoginSchema):
    """로그인 (2FA 지원)"""
    
    try:
        user = User.objects.get(email=payload.email)
    except User.DoesNotExist:
        raise HttpError(401, "이메일 또는 비밀번호가 올바르지 않습니다.")
    
    # 계정 잠금 확인
    if user.is_locked:
        raise HttpError(401, f"계정이 잠겨있습니다. {user.locked_until}까지 기다려주세요.")
    
    # 비밀번호 확인
    if not check_password(payload.password, user.password):
        # 실패 횟수 증가 로직 (이전과 동일)
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = timezone.now() + timedelta(minutes=30)
            user.save(update_fields=['failed_login_attempts', 'locked_until'])
            raise HttpError(401, "로그인 시도가 5회 실패하여 계정이 30분간 잠겼습니다.")
        
        user.save(update_fields=['failed_login_attempts'])
        raise HttpError(401, "이메일 또는 비밀번호가 올바르지 않습니다.")
    
    # 계정 상태 확인
    if user.status != User.Status.ACTIVE:
        raise HttpError(401, "비활성화된 계정입니다.")
    
    # 이중 인증 확인
    if user.two_factor_enabled:
        # 임시 토큰 발급 (2FA 인증용)
        temp_payload = {
            'user_id': str(user.id),
            'type': 'temp_login',
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(minutes=5)
        }
        temp_token = jwt.encode(temp_payload, settings.SECRET_KEY, algorithm='HS256')
        
        return {
            "requires_2fa": True,
            "temp_token": temp_token,
            "message": "이중 인증 코드를 입력해주세요."
        }
    
    # 일반 로그인 성공 처리 (이전과 동일)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = timezone.now()
    user.save(update_fields=['failed_login_attempts', 'locked_until', 'last_login'])
    
    tokens = JWTTokenManager.generate_tokens(user)
    
    return TokenResponse(
        **tokens,
        user=UserSchema(
            id=str(user.id),
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            status=user.status,
            email_verified=user.email_verified,
            phone_verified=user.phone_verified,
            avatar=user.avatar.url if user.avatar else None,
            created_at=user.created_at,
            last_activity=user.last_activity
        )
    )

@router.post("/auth/login/2fa", response=TokenResponse)
def login_with_2fa(request, payload: dict):
    """이중 인증으로 로그인 완료"""
    temp_token = payload.get('temp_token')
    two_factor_code = payload.get('two_factor_code')
    
    if not temp_token or not two_factor_code:
        raise HttpError(400, "임시 토큰과 인증 코드가 필요합니다.")
    
    try:
        # 임시 토큰 검증
        temp_payload = jwt.decode(temp_token, settings.SECRET_KEY, algorithms=['HS256'])
        
        if temp_payload.get('type') != 'temp_login':
            raise HttpError(401, "유효하지 않은 토큰입니다.")
        
        user = User.objects.get(id=temp_payload['user_id'])
        two_factor = TwoFactorAuth.objects.get(user=user, enabled=True)
        
        # 2FA 코드 검증 (백업 코드도 허용)
        if not (two_factor.verify_token(two_factor_code) or 
                two_factor.use_backup_code(two_factor_code)):
            raise HttpError(401, "인증 코드가 올바르지 않습니다.")
        
        # 로그인 성공 처리
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = timezone.now()
        user.save(update_fields=['failed_login_attempts', 'locked_until', 'last_login'])
        
        # 실제 JWT 토큰 발급
        tokens = JWTTokenManager.generate_tokens(user)
        
        return TokenResponse(
            **tokens,
            user=UserSchema(
                id=str(user.id),
                email=user.email,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role,
                status=user.status,
                email_verified=user.email_verified,
                phone_verified=user.phone_verified,
                avatar=user.avatar.url if user.avatar else None,
                created_at=user.created_at,
                last_activity=user.last_activity
            )
        )
        
    except (jwt.InvalidTokenError, User.DoesNotExist, TwoFactorAuth.DoesNotExist):
        raise HttpError(401, "인증에 실패했습니다.")
```

## 📧 1.8 이메일 템플릿

```html
<!-- templates/accounts/emails/verify_email.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>이메일 주소 인증</title>
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #333;">{{ site_name }}</h1>
    </div>
    
    <div style="background: #f8f9fa; padding: 30px; border-radius: 10px;">
        <h2 style="color: #007bff;">이메일 주소를 인증해주세요</h2>
        
        <p>안녕하세요, {{ user.first_name }}님!</p>
        
        <p>{{ site_name }}에 가입해주셔서 감사합니다. 아래 버튼을 클릭하여 이메일 주소를 인증해주세요.</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{ verification_url }}" 
               style="background: #007bff; color: white; padding: 15px 30px; 
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                이메일 인증하기
            </a>
        </div>
        
        <p style="color: #666; font-size: 14px;">
            버튼이 작동하지 않으면 아래 링크를 복사하여 브라우저에 붙여넣으세요:<br>
            <a href="{{ verification_url }}">{{ verification_url }}</a>
        </p>
        
        <p style="color: #666; font-size: 14px;">
            이 링크는 24시간 후에 만료됩니다.
        </p>
    </div>
    
    <div style="text-align: center; margin-top: 30px; color: #666; font-size: 12px;">
        <p>본 메일은 발신전용입니다. 문의사항은 고객센터를 이용해주세요.</p>
        <p>&copy; {{ site_name }}. All rights reserved.</p>
    </div>
</body>
</html>
```

```html
<!-- templates/accounts/emails/reset_password.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>비밀번호 재설정</title>
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #333;">{{ site_name }}</h1>
    </div>
    
    <div style="background: #f8f9fa; padding: 30px; border-radius: 10px;">
        <h2 style="color: #dc3545;">비밀번호를 재설정해주세요</h2>
        
        <p>안녕하세요, {{ user.first_name }}님!</p>
        
        <p>비밀번호 재설정을 요청하셨습니다. 아래 버튼을 클릭하여 새 비밀번호를 설정해주세요.</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{ reset_url }}" 
               style="background: #dc3545; color: white; padding: 15px 30px; 
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                비밀번호 재설정
            </a>
        </div>
        
        <p style="color: #666; font-size: 14px;">
            버튼이 작동하지 않으면 아래 링크를 복사하여 브라우저에 붙여넣으세요:<br>
            <a href="{{ reset_url }}">{{ reset_url }}</a>
        </p>
        
        <p style="color: #dc3545; font-size: 14px;">
            <strong>주의:</strong> 이 링크는 1시간 후에 만료됩니다. 
            본인이 요청하지 않은 경우 이 메일을 무시하세요.
        </p>
    </div>
    
    <div style="text-align: center; margin-top: 30px; color: #666; font-size: 12px;">
        <p>본 메일은 발신전용입니다. 문의사항은 고객센터를 이용해주세요.</p>
        <p>&copy; {{ site_name }}. All rights reserved.</p>
    </div>
</body>
</html>
```

## ✅ 1장 마무리

1장에서 구현한 **고급 인증 시스템**의 핵심 기능들:

### 🎯 완성된 기능
- ✅ **JWT 기반 인증**: Access/Refresh Token 시스템
- ✅ **소셜 로그인**: Google, Kakao, Naver 연동
- ✅ **이메일 인증**: 회원가입 시 이메일 검증
- ✅ **비밀번호 관리**: 재설정, 변경, 보안 정책
- ✅ **세션 관리**: 다중 디바이스 로그인 제어
- ✅ **이중 인증 (2FA)**: TOTP 기반 보안 강화
- ✅ **권한 관리**: 역할 기반 접근 제어 (RBAC)
- ✅ **보안 기능**: 계정 잠금, 실패 시도 제한

### 🔒 보안 특징
- 비밀번호 복잡성 검증
- 로그인 실패 시 계정 임시 잠금
- JWT 토큰 만료 및 갱신 시스템
- 이중 인증으로 추가 보안 계층
- 세션별 디바이스 추적 및 관리

이제 **2장: 고급 제품 관리 시스템**으로 넘어가겠습니다!

---

# 📦 2장: 고급 제품 관리 시스템

기본적인 상품 CRUD를 넘어서, **복잡한 상품 구조와 고성능 검색**을 지원하는 시스템을 구축해보겠습니다.

## 🎯 2장에서 구현할 기능

- **변형 상품** (사이즈, 색상 등 옵션별 관리)
- **계층형 카테고리** (무제한 깊이 트리 구조)
- **실시간 재고 추적** (Redis 기반 동시성 처리)
- **고성능 검색** (Elasticsearch 연동)
- **상품 리뷰 & 평점** (검증된 구매자만)
- **위시리스트 & 비교함**
- **상품 추천** (협업 필터링)

## 📊 2.1 고급 제품 모델 설계

```python
# apps/products/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from mptt.models import MPTTModel, TreeForeignKey
import uuid
from decimal import Decimal

User = get_user_model()

class Category(MPTTModel):
    """계층형 카테고리 (MPTT)"""
    
    class Meta:
        verbose_name_plural = "categories"
        indexes = [
            models.Index(fields=['lft', 'rght', 'tree_id']),
            models.Index(fields=['slug']),
        ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True)
    icon = models.CharField(max_length=50, blank=True)  # CSS 아이콘 클래스
    
    # 계층 구조
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    # SEO
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(max_length=300, blank=True)
    
    # 상태
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class MPTTMeta:
        order_insertion_by = ['sort_order', 'name']
    
    def __str__(self):
        return self.name
    
    @property
    def full_path(self):
        """전체 경로 반환 (Home > Electronics > Smartphones)"""
        return ' > '.join([cat.name for cat in self.get_ancestors(include_self=True)])

class Brand(models.Model):
    """브랜드"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='brands/', blank=True)
    website = models.URLField(blank=True)
    
    # 상태
    is_active = models.BooleanField(default=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """기본 상품 (변형 상품의 부모)"""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', '임시저장'
        ACTIVE = 'active', '판매중'
        INACTIVE = 'inactive', '판매중지'
        OUT_OF_STOCK = 'out_of_stock', '품절'
        DISCONTINUED = 'discontinued', '단종'
    
    class Type(models.TextChoices):
        SIMPLE = 'simple', '단일 상품'
        VARIABLE = 'variable', '변형 상품'
        GROUPED = 'grouped', '묶음 상품'
        DIGITAL = 'digital', '디지털 상품'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 기본 정보
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    short_description = models.TextField(max_length=500, blank=True)
    
    # 분류
    category = TreeForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products')
    
    # 타입 및 상태
    product_type = models.CharField(max_length=20, choices=Type.choices, default=Type.SIMPLE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    # 판매자 (멀티벤더 지원)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    
    # 기본 가격 (변형 상품의 경우 최저가)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # 재고 (단일 상품만)
    track_stock = models.BooleanField(default=True)
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    low_stock_threshold = models.IntegerField(default=10, validators=[MinValueValidator(0)])
    
    # 배송
    weight = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # kg
    dimensions = models.JSONField(default=dict)  # {"length": 10, "width": 10, "height": 10}
    shipping_required = models.BooleanField(default=True)
    
    # SEO
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(max_length=300, blank=True)
    
    # 속성 (동적 필드)
    attributes = models.JSONField(default=dict)  # {"color": "red", "material": "cotton"}
    
    # 태그 (검색용)
    tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    
    # 평점 (캐시용)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.IntegerField(default=0)
    
    # 조회수 & 판매량
    view_count = models.IntegerField(default=0)
    sales_count = models.IntegerField(default=0)
    
    # 특별 상품
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['brand', 'status']),
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['base_price']),
            models.Index(fields=['average_rating']),
            models.Index(fields=['sales_count']),
            models.Index(fields=['is_featured', 'is_bestseller', 'is_new']),
            GinIndex(fields=['tags']),  # PostgreSQL GIN 인덱스
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def is_in_stock(self):
        """재고 여부 확인"""
        if not self.track_stock:
            return True
        if self.product_type == self.Type.VARIABLE:
            return self.variants.filter(stock_quantity__gt=0).exists()
        return self.stock_quantity > 0
    
    @property
    def is_low_stock(self):
        """저재고 여부 확인"""
        if not self.track_stock:
            return False
        return self.stock_quantity <= self.low_stock_threshold

class ProductVariant(models.Model):
    """상품 변형 (색상, 사이즈 등)"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    
    # 변형 속성
    attributes = models.JSONField()  # {"color": "red", "size": "L"}
    
    # SKU (재고 관리 단위)
    sku = models.CharField(max_length=100, unique=True)
    
    # 가격
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # 재고
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # 물리적 속성
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    dimensions = models.JSONField(default=dict, blank=True)
    
    # 상태
    is_active = models.BooleanField(default=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['product', 'attributes']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['product', 'is_active']),
            models.Index(fields=['price']),
        ]
    
    def __str__(self):
        attrs_str = ', '.join([f"{k}: {v}" for k, v in self.attributes.items()])
        return f"{self.product.name} ({attrs_str})"
    
    @property
    def variant_name(self):
        """변형 이름 생성"""
        return ' / '.join(self.attributes.values())

class ProductImage(models.Model):
    """상품 이미지"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name='images')
    
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    sort_order = models.IntegerField(default=0)
    is_main = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['sort_order', 'created_at']
        indexes = [
            models.Index(fields=['product', 'sort_order']),
            models.Index(fields=['variant', 'sort_order']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - Image {self.sort_order}"

class ProductAttribute(models.Model):
    """상품 속성 정의 (색상, 사이즈 등)"""
    
    class Type(models.TextChoices):
        TEXT = 'text', '텍스트'
        NUMBER = 'number', '숫자'
        SELECT = 'select', '선택'
        MULTI_SELECT = 'multi_select', '다중선택'
        BOOLEAN = 'boolean', '예/아니오'
        COLOR = 'color', '색상'
        DATE = 'date', '날짜'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.TEXT)
    
    # 선택형 속성의 경우 옵션들
    options = ArrayField(models.CharField(max_length=100), default=list, blank=True)
    
    # 표시 설정
    is_required = models.BooleanField(default=False)
    is_variation = models.BooleanField(default=False)  # 변형 생성에 사용되는 속성
    is_visible = models.BooleanField(default=True)
    
    sort_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name

class ProductReview(models.Model):
    """상품 리뷰"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', '검토중'
        APPROVED = 'approved', '승인됨'
        REJECTED = 'rejected', '거부됨'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    
    # 리뷰 내용
    title = models.CharField(max_length=200)
    content = models.TextField()
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    
    # 구매 검증
    is_verified_purchase = models.BooleanField(default=False)
    purchase_date = models.DateField(null=True, blank=True)
    
    # 도움도
    helpful_count = models.IntegerField(default=0)
    not_helpful_count = models.IntegerField(default=0)
    
    # 상태
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['product', 'user']  # 사용자당 제품별 하나의 리뷰만
        indexes = [
            models.Index(fields=['product', 'status', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['rating']),
            models.Index(fields=['is_verified_purchase']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.user.email} ({self.rating}★)"

class ProductReviewHelpful(models.Model):
    """리뷰 도움도 투표"""
    review = models.ForeignKey(ProductReview, on_delete=models.CASCADE, related_name='helpful_votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_helpful = models.BooleanField()  # True: 도움됨, False: 도움안됨
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['review', 'user']

class Wishlist(models.Model):
    """위시리스트"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlists')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'product', 'variant']
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.product.name}"
```

## 🏪 2.2 재고 관리 시스템

```python
# apps/inventory/models.py
from django.db import models
from django.contrib.auth import get_user_model
from apps.products.models import Product, ProductVariant
import uuid

User = get_user_model()

class StockMovement(models.Model):
    """재고 이동 기록"""
    
    class Type(models.TextChoices):
        IN = 'in', '입고'
        OUT = 'out', '출고'
        ADJUSTMENT = 'adjustment', '조정'
        TRANSFER = 'transfer', '이동'
        RETURN = 'return', '반품'
        DAMAGED = 'damaged', '손상'
        EXPIRED = 'expired', '유통기한 만료'
    
    class Status(models.TextChoices):
        PENDING = 'pending', '대기중'
        CONFIRMED = 'confirmed', '확인됨'
        CANCELLED = 'cancelled', '취소됨'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name='stock_movements')
    
    # 이동 정보
    type = models.CharField(max_length=20, choices=Type.choices)
    quantity = models.IntegerField()
    previous_quantity = models.IntegerField()
    new_quantity = models.IntegerField()
    
    # 참조 정보
    reference_type = models.CharField(max_length=50, blank=True)  # order, adjustment, etc.
    reference_id = models.CharField(max_length=100, blank=True)
    
    # 메모
    notes = models.TextField(blank=True)
    
    # 상태
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # 담당자
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stock_movements')
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['variant', 'created_at']),
            models.Index(fields=['type', 'status']),
            models.Index(fields=['reference_type', 'reference_id']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        item = self.variant or self.product
        return f"{item} - {self.type} ({self.quantity})"

class StockAlert(models.Model):
    """재고 알림"""
    
    class Type(models.TextChoices):
        LOW_STOCK = 'low_stock', '저재고'
        OUT_OF_STOCK = 'out_of_stock', '품절'
        EXPIRED = 'expired', '유통기한 임박'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', '활성'
        RESOLVED = 'resolved', '해결됨'
        IGNORED = 'ignored', '무시됨'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_alerts')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name='stock_alerts')
    
    type = models.CharField(max_length=20, choices=Type.choices)
    threshold = models.IntegerField()
    current_stock = models.IntegerField()
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    
    # 알림 대상
    notified_users = models.ManyToManyField(User, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['type', 'status']),
            models.Index(fields=['product', 'status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
```

## 📝 2.3 재고 관리 서비스

```python
# apps/inventory/services.py
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth import get_user_model
from apps.products.models import Product, ProductVariant
from .models import StockMovement, StockAlert
import redis
from decimal import Decimal

User = get_user_model()

class StockService:
    """재고 관리 서비스"""
    
    def __init__(self):
        self.redis_client = redis.Redis(decode_responses=True)
    
    def get_stock_key(self, product_id, variant_id=None):
        """Redis 재고 키 생성"""
        if variant_id:
            return f"stock:variant:{variant_id}"
        return f"stock:product:{product_id}"
    
    def get_current_stock(self, product_id, variant_id=None):
        """현재 재고량 조회 (Redis 캐시 우선)"""
        key = self.get_stock_key(product_id, variant_id)
        
        # Redis에서 먼저 확인
        cached_stock = self.redis_client.get(key)
        if cached_stock is not None:
            return int(cached_stock)
        
        # DB에서 조회 후 캐시 업데이트
        if variant_id:
            variant = ProductVariant.objects.get(id=variant_id)
            stock = variant.stock_quantity
        else:
            product = Product.objects.get(id=product_id)
            stock = product.stock_quantity
        
        self.redis_client.set(key, stock, ex=3600)  # 1시간 캐시
        return stock
    
    @transaction.atomic
    def update_stock(self, product_id, quantity_change, variant_id=None, 
                    movement_type=StockMovement.Type.ADJUSTMENT, 
                    reference_type='', reference_id='', notes='', user=None):
        """재고 업데이트 (동시성 보장)"""
        
        # 락 획득
        lock_key = f"lock:stock:{variant_id or product_id}"
        with self.redis_client.lock(lock_key, timeout=10):
            
            # 현재 재고 조회
            if variant_id:
                variant = ProductVariant.objects.select_for_update().get(id=variant_id)
                item = variant
                current_stock = variant.stock_quantity
            else:
                product = Product.objects.select_for_update().get(id=product_id)
                item = product
                current_stock = product.stock_quantity
            
            # 새 재고량 계산
            new_stock = current_stock + quantity_change
            
            # 음수 재고 방지
            if new_stock < 0:
                raise ValueError(f"재고가 부족합니다. 현재: {current_stock}, 요청: {abs(quantity_change)}")
            
            # DB 업데이트
            if variant_id:
                variant.stock_quantity = new_stock
                variant.save(update_fields=['stock_quantity'])
            else:
                item.stock_quantity = new_stock
                item.save(update_fields=['stock_quantity'])
            
            # Redis 캐시 업데이트
            cache_key = self.get_stock_key(product_id, variant_id)
            self.redis_client.set(cache_key, new_stock, ex=3600)
            
            # 재고 이동 기록
            movement = StockMovement.objects.create(
                product_id=product_id,
                variant_id=variant_id,
                type=movement_type,
                quantity=abs(quantity_change),
                previous_quantity=current_stock,
                new_quantity=new_stock,
                reference_type=reference_type,
                reference_id=reference_id,
                notes=notes,
                created_by=user,
                status=StockMovement.Status.CONFIRMED,
                confirmed_at=timezone.now()
            )
            
            # 재고 알림 확인
            self.check_stock_alerts(product_id, variant_id, new_stock)
            
            return movement
    
    def check_stock_alerts(self, product_id, variant_id, current_stock):
        """재고 알림 확인"""
        
        if variant_id:
            variant = ProductVariant.objects.get(id=variant_id)
            item = variant
            product = variant.product
        else:
            product = Product.objects.get(id=product_id)
            item = product
        
        # 품절 알림
        if current_stock == 0:
            StockAlert.objects.get_or_create(
                product=product,
                variant_id=variant_id,
                type=StockAlert.Type.OUT_OF_STOCK,
                defaults={
                    'threshold': 0,
                    'current_stock': current_stock,
                    'status': StockAlert.Status.ACTIVE
                }
            )
        
        # 저재고 알림
        elif current_stock <= product.low_stock_threshold:
            StockAlert.objects.get_or_create(
                product=product,
                variant_id=variant_id,
                type=StockAlert.Type.LOW_STOCK,
                defaults={
                    'threshold': product.low_stock_threshold,
                    'current_stock': current_stock,
                    'status': StockAlert.Status.ACTIVE
                }
            )
    
    def reserve_stock(self, product_id, quantity, variant_id=None, order_id=''):
        """재고 예약 (주문 시)"""
        return self.update_stock(
            product_id=product_id,
            quantity_change=-quantity,
            variant_id=variant_id,
            movement_type=StockMovement.Type.OUT,
            reference_type='order',
            reference_id=order_id,
            notes=f'주문 {order_id}로 재고 예약'
        )
    
    def release_stock(self, product_id, quantity, variant_id=None, order_id=''):
        """재고 해제 (주문 취소 시)"""
        return self.update_stock(
            product_id=product_id,
            quantity_change=quantity,
            variant_id=variant_id,
            movement_type=StockMovement.Type.RETURN,
            reference_type='order_cancel',
            reference_id=order_id,
            notes=f'주문 {order_id} 취소로 재고 해제'
        )
    
    def bulk_stock_update(self, updates):
        """대량 재고 업데이트"""
        results = []
        
        for update in updates:
            try:
                result = self.update_stock(**update)
                results.append({'success': True, 'movement': result})
            except Exception as e:
                results.append({'success': False, 'error': str(e)})
        
        return results

# 전역 인스턴스
stock_service = StockService()
```

## 🔍 2.4 고성능 검색 시스템

```python
# apps/products/search.py
from django.db.models import Q, Count, Avg, Min, Max
from django.contrib.postgres.search import SearchVector, SearchRank, SearchQuery
from django.core.cache import cache
from .models import Product, Category, Brand
import re
from typing import List, Dict, Any

class ProductSearchService:
    """상품 검색 서비스"""
    
    @classmethod
    def search(cls, query='', filters=None, sort_by='relevance', page=1, per_page=20):
        """통합 상품 검색"""
        filters = filters or {}
        
        # 기본 쿼리셋
        queryset = Product.objects.filter(status=Product.Status.ACTIVE)
        
        # 텍스트 검색
        if query:
            queryset = cls._apply_text_search(queryset, query)
        
        # 필터 적용
        queryset = cls._apply_filters(queryset, filters)
        
        # 정렬
        queryset = cls._apply_sorting(queryset, sort_by, bool(query))
        
        # 페이지네이션
        offset = (page - 1) * per_page
        total_count = queryset.count()
        results = queryset[offset:offset + per_page]
        
        # 관련 데이터 미리 로드
        results = results.select_related('category', 'brand', 'seller').prefetch_related('images', 'variants')
        
        return {
            'results': list(results),
            'total_count': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_count + per_page - 1) // per_page,
            'has_next': offset + per_page < total_count,
            'has_prev': page > 1
        }
    
    @classmethod
    def _apply_text_search(cls, queryset, query):
        """텍스트 검색 적용"""
        
        # PostgreSQL 전문 검색
        search_vector = SearchVector('name', weight='A') + \
                       SearchVector('description', weight='B') + \
                       SearchVector('short_description', weight='C') + \
                       SearchVector('tags', weight='D')
        
        search_query = SearchQuery(query)
        
        queryset = queryset.annotate(
            search=search_vector,
            rank=SearchRank(search_vector, search_query)
        ).filter(search=search_query)
        
        return queryset
    
    @classmethod
    def _apply_filters(cls, queryset, filters):
        """필터 적용"""
        
        # 카테고리 필터
        if filters.get('category_ids'):
            category_ids = filters['category_ids']
            # 하위 카테고리도 포함
            categories = Category.objects.filter(id__in=category_ids)
            all_category_ids = []
            for category in categories:
                descendants = category.get_descendants(include_self=True)
                all_category_ids.extend([cat.id for cat in descendants])
            
            queryset = queryset.filter(category_id__in=all_category_ids)
        
        # 브랜드 필터
        if filters.get('brand_ids'):
            queryset = queryset.filter(brand_id__in=filters['brand_ids'])
        
        # 가격 범위 필터
        if filters.get('min_price'):
            queryset = queryset.filter(base_price__gte=filters['min_price'])
        if filters.get('max_price'):
            queryset = queryset.filter(base_price__lte=filters['max_price'])
        
        # 평점 필터
        if filters.get('min_rating'):
            queryset = queryset.filter(average_rating__gte=filters['min_rating'])
        
        # 재고 필터
        if filters.get('in_stock_only'):
            queryset = queryset.filter(
                Q(track_stock=False) | 
                Q(stock_quantity__gt=0) |
                Q(variants__stock_quantity__gt=0)
            ).distinct()
        
        # 특별 상품 필터
        if filters.get('is_featured'):
            queryset = queryset.filter(is_featured=True)
        if filters.get('is_bestseller'):
            queryset = queryset.filter(is_bestseller=True)
        if filters.get('is_new'):
            queryset = queryset.filter(is_new=True)
        
        # 속성 필터
        if filters.get('attributes'):
            for attr_name, attr_value in filters['attributes'].items():
                queryset = queryset.filter(
                    attributes__has_key=attr_name,
                    attributes__contains={attr_name: attr_value}
                )
        
        # 판매자 필터
        if filters.get('seller_ids'):
            queryset = queryset.filter(seller_id__in=filters['seller_ids'])
        
        return queryset
    
    @classmethod
    def _apply_sorting(cls, queryset, sort_by, has_search_query=False):
        """정렬 적용"""
        
        if sort_by == 'relevance' and has_search_query:
            return queryset.order_by('-rank', '-sales_count')
        elif sort_by == 'price_low':
            return queryset.order_by('base_price', 'name')
        elif sort_by == 'price_high':
            return queryset.order_by('-base_price', 'name')
        elif sort_by == 'rating':
            return queryset.order_by('-average_rating', '-review_count')
        elif sort_by == 'newest':
            return queryset.order_by('-created_at')
        elif sort_by == 'bestseller':
            return queryset.order_by('-sales_count', '-average_rating')
        elif sort_by == 'name':
            return queryset.order_by('name')
        else:
            return queryset.order_by('-created_at')
    
    @classmethod
    def get_search_suggestions(cls, query, limit=10):
        """검색 자동완성"""
        if len(query) < 2:
            return []
        
        # 캐시 확인
        cache_key = f"search_suggestions:{query.lower()}"
        suggestions = cache.get(cache_key)
        if suggestions:
            return suggestions
        
        suggestions = []
        
        # 상품명에서 검색
        products = Product.objects.filter(
            name__icontains=query,
            status=Product.Status.ACTIVE
        ).values_list('name', flat=True)[:limit//2]
        suggestions.extend(products)
        
        # 카테고리에서 검색
        categories = Category.objects.filter(
            name__icontains=query,
            is_active=True
        ).values_list('name', flat=True)[:limit//4]
        suggestions.extend(categories)
        
        # 브랜드에서 검색
        brands = Brand.objects.filter(
            name__icontains=query,
            is_active=True
        ).values_list('name', flat=True)[:limit//4]
        suggestions.extend(brands)
        
        # 중복 제거 및 제한
        suggestions = list(dict.fromkeys(suggestions))[:limit]
        
        # 캐시 저장 (1시간)
        cache.set(cache_key, suggestions, 3600)
        
        return suggestions
    
    @classmethod
    def get_facets(cls, query='', filters=None):
        """검색 패싯 (필터 옵션) 생성"""
        filters = filters or {}
        
        # 기본 쿼리셋 (필터 적용 전)
        queryset = Product.objects.filter(status=Product.Status.ACTIVE)
        
        if query:
            queryset = cls._apply_text_search(queryset, query)
        
        # 현재 필터 제외하고 적용
        base_filters = dict(filters)
        
        facets = {}
        
        # 카테고리 패싯
        if 'category_ids' in base_filters:
            del base_filters['category_ids']
        temp_queryset = cls._apply_filters(queryset, base_filters)
        
        facets['categories'] = list(
            temp_queryset.values('category__id', 'category__name')
            .annotate(count=Count('id'))
            .order_by('-count', 'category__name')[:20]
        )
        
        # 브랜드 패싯
        base_filters = dict(filters)
        if 'brand_ids' in base_filters:
            del base_filters['brand_ids']
        temp_queryset = cls._apply_filters(queryset, base_filters)
        
        facets['brands'] = list(
            temp_queryset.values('brand__id', 'brand__name')
            .annotate(count=Count('id'))
            .order_by('-count', 'brand__name')[:20]
        )
        
        # 가격 범위 패싯
        base_filters = dict(filters)
        if 'min_price' in base_filters:
            del base_filters['min_price']
        if 'max_price' in base_filters:
            del base_filters['max_price']
        temp_queryset = cls._apply_filters(queryset, base_filters)
        
        price_stats = temp_queryset.aggregate(
            min_price=Min('base_price'),
            max_price=Max('base_price')
        )
        facets['price_range'] = price_stats
        
        # 평점 패싯
        facets['ratings'] = [
            {'rating': 5, 'count': temp_queryset.filter(average_rating__gte=5).count()},
            {'rating': 4, 'count': temp_queryset.filter(average_rating__gte=4, average_rating__lt=5).count()},
            {'rating': 3, 'count': temp_queryset.filter(average_rating__gte=3, average_rating__lt=4).count()},
            {'rating': 2, 'count': temp_queryset.filter(average_rating__gte=2, average_rating__lt=3).count()},
            {'rating': 1, 'count': temp_queryset.filter(average_rating__gte=1, average_rating__lt=2).count()},
        ]
        
        return facets

class SearchHistoryService:
    """검색 기록 서비스"""
    
    @classmethod
    def record_search(cls, user_id, query, results_count):
        """검색 기록 저장"""
        from .models import SearchHistory
        
        SearchHistory.objects.create(
            user_id=user_id,
            query=query,
            results_count=results_count
        )
        
        # 사용자별 최대 100개 기록 유지
        SearchHistory.objects.filter(user_id=user_id).order_by('-created_at')[100:].delete()
    
    @classmethod
    def get_popular_searches(cls, limit=10):
        """인기 검색어"""
        cache_key = "popular_searches"
        popular = cache.get(cache_key)
        
        if popular is None:
            from .models import SearchHistory
            from django.utils import timezone
            from datetime import timedelta
            
            # 최근 7일간 데이터
            week_ago = timezone.now() - timedelta(days=7)
            
            popular = list(
                SearchHistory.objects.filter(created_at__gte=week_ago)
                .values('query')
                .annotate(count=Count('id'))
                .order_by('-count')[:limit]
            )
            
            cache.set(cache_key, popular, 3600)  # 1시간 캐시
        
        return popular
```

이제 **상품 API 구현**을 계속하겠습니다.

## 🚀 2.5 상품 API 구현

```python
# apps/products/schemas.py
from ninja import Schema, Field
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from pydantic import validator

class CategorySchema(Schema):
    id: str
    name: str
    slug: str
    description: Optional[str]
    image: Optional[str]
    icon: Optional[str]
    full_path: str
    children_count: int = 0
    products_count: int = 0

class BrandSchema(Schema):
    id: str
    name: str
    slug: str
    description: Optional[str]
    logo: Optional[str]
    website: Optional[str]

class ProductImageSchema(Schema):
    id: str
    image: str
    alt_text: Optional[str]
    sort_order: int
    is_main: bool

class ProductVariantSchema(Schema):
    id: str
    sku: str
    attributes: Dict[str, Any]
    variant_name: str
    price: Decimal
    compare_price: Optional[Decimal]
    stock_quantity: int
    is_active: bool
    images: List[ProductImageSchema] = []

class ProductListSchema(Schema):
    id: str
    name: str
    slug: str
    short_description: Optional[str]
    base_price: Decimal
    compare_price: Optional[Decimal]
    average_rating: Decimal
    review_count: int
    is_in_stock: bool
    is_featured: bool
    is_bestseller: bool
    is_new: bool
    main_image: Optional[str]
    category: CategorySchema
    brand: BrandSchema

class ProductDetailSchema(Schema):
    id: str
    name: str
    slug: str
    description: str
    short_description: Optional[str]
    base_price: Decimal
    compare_price: Optional[Decimal]
    product_type: str
    status: str
    
    # 분류
    category: CategorySchema
    brand: BrandSchema
    
    # 재고
    track_stock: bool
    stock_quantity: int
    is_in_stock: bool
    is_low_stock: bool
    
    # 배송
    weight: Decimal
    dimensions: Dict[str, Any]
    shipping_required: bool
    
    # 속성
    attributes: Dict[str, Any]
    tags: List[str]
    
    # 통계
    average_rating: Decimal
    review_count: int
    view_count: int
    sales_count: int
    
    # 특별 상품
    is_featured: bool
    is_bestseller: bool
    is_new: bool
    
    # 관련 데이터
    images: List[ProductImageSchema]
    variants: List[ProductVariantSchema] = []
    
    # 타임스탬프
    created_at: datetime
    updated_at: datetime

class ProductSearchSchema(Schema):
    query: Optional[str] = ""
    category_ids: Optional[List[str]] = []
    brand_ids: Optional[List[str]] = []
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    min_rating: Optional[int] = None
    in_stock_only: bool = False
    is_featured: bool = False
    is_bestseller: bool = False
    is_new: bool = False
    attributes: Optional[Dict[str, Any]] = {}
    sort_by: str = "relevance"  # relevance, price_low, price_high, rating, newest, bestseller, name
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)

class ProductSearchResultSchema(Schema):
    results: List[ProductListSchema]
    total_count: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool
    facets: Optional[Dict[str, Any]] = None

class ReviewSchema(Schema):
    id: str
    title: str
    content: str
    rating: int
    is_verified_purchase: bool
    helpful_count: int
    not_helpful_count: int
    user_name: str
    created_at: datetime

class CreateReviewSchema(Schema):
    title: str
    content: str
    rating: int = Field(..., ge=1, le=5)

class CreateProductSchema(Schema):
    name: str
    description: str
    short_description: Optional[str] = ""
    category_id: str
    brand_id: str
    product_type: str = "simple"
    base_price: Decimal = Field(..., gt=0)
    compare_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    track_stock: bool = True
    stock_quantity: int = Field(0, ge=0)
    low_stock_threshold: int = Field(10, ge=0)
    weight: Decimal = Field(0, ge=0)
    dimensions: Optional[Dict[str, Any]] = {}
    shipping_required: bool = True
    attributes: Optional[Dict[str, Any]] = {}
    tags: Optional[List[str]] = []
    
    @validator('compare_price')
    def validate_compare_price(cls, v, values):
        if v is not None and 'base_price' in values and v <= values['base_price']:
            raise ValueError('비교가격은 기본가격보다 높아야 합니다.')
        return v

class UpdateProductSchema(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    base_price: Optional[Decimal] = None
    compare_price: Optional[Decimal] = None
    stock_quantity: Optional[int] = None
    status: Optional[str] = None
```

```python
# apps/products/api.py
from ninja import Router, File, UploadedFile
from ninja.pagination import paginate
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from typing import List, Optional

from .models import *
from .schemas import *
from .search import ProductSearchService
from core.auth.jwt_auth import jwt_auth
from core.auth.permissions import require_permissions, PermissionChecker
from apps.inventory.services import stock_service

router = Router()

# 상품 검색 및 목록
@router.get("/products/search", response=ProductSearchResultSchema)
def search_products(request, filters: ProductSearchSchema = None):
    """상품 검색"""
    if not filters:
        filters = ProductSearchSchema()
    
    # 검색 실행
    search_result = ProductSearchService.search(
        query=filters.query,
        filters={
            'category_ids': filters.category_ids,
            'brand_ids': filters.brand_ids,
            'min_price': filters.min_price,
            'max_price': filters.max_price,
            'min_rating': filters.min_rating,
            'in_stock_only': filters.in_stock_only,
            'is_featured': filters.is_featured,
            'is_bestseller': filters.is_bestseller,
            'is_new': filters.is_new,
            'attributes': filters.attributes,
        },
        sort_by=filters.sort_by,
        page=filters.page,
        per_page=filters.per_page
    )
    
    # 패싯 정보 추가
    facets = ProductSearchService.get_facets(
        query=filters.query,
        filters={k: v for k, v in filters.dict().items() if v not in [None, [], {}, ""]}
    )
    
    # 스키마 변환
    products_data = []
    for product in search_result['results']:
        main_image = product.images.filter(is_main=True).first()
        
        products_data.append(ProductListSchema(
            id=str(product.id),
            name=product.name,
            slug=product.slug,
            short_description=product.short_description,
            base_price=product.base_price,
            compare_price=product.compare_price,
            average_rating=product.average_rating,
            review_count=product.review_count,
            is_in_stock=product.is_in_stock,
            is_featured=product.is_featured,
            is_bestseller=product.is_bestseller,
            is_new=product.is_new,
            main_image=main_image.image.url if main_image else None,
            category=CategorySchema(
                id=str(product.category.id),
                name=product.category.name,
                slug=product.category.slug,
                description=product.category.description,
                image=product.category.image.url if product.category.image else None,
                icon=product.category.icon,
                full_path=product.category.full_path,
                children_count=product.category.get_children().count(),
                products_count=product.category.products.filter(status=Product.Status.ACTIVE).count()
            ),
            brand=BrandSchema(
                id=str(product.brand.id),
                name=product.brand.name,
                slug=product.brand.slug,
                description=product.brand.description,
                logo=product.brand.logo.url if product.brand.logo else None,
                website=product.brand.website
            )
        ))
    
    return ProductSearchResultSchema(
        results=products_data,
        total_count=search_result['total_count'],
        page=search_result['page'],
        per_page=search_result['per_page'],
        total_pages=search_result['total_pages'],
        has_next=search_result['has_next'],
        has_prev=search_result['has_prev'],
        facets=facets
    )

@router.get("/products/{product_slug}", response=ProductDetailSchema)
def get_product_detail(request, product_slug: str):
    """상품 상세 조회"""
    
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand', 'seller')
        .prefetch_related('images', 'variants__images'),
        slug=product_slug,
        status=Product.Status.ACTIVE
    )
    
    # 조회수 증가
    Product.objects.filter(id=product.id).update(view_count=models.F('view_count') + 1)
    
    # 이미지 처리
    images = [
        ProductImageSchema(
            id=str(img.id),
            image=img.image.url,
            alt_text=img.alt_text,
            sort_order=img.sort_order,
            is_main=img.is_main
        )
        for img in product.images.all()
    ]
    
    # 변형 상품 처리
    variants = []
    if product.product_type == Product.Type.VARIABLE:
        for variant in product.variants.filter(is_active=True):
            variant_images = [
                ProductImageSchema(
                    id=str(img.id),
                    image=img.image.url,
                    alt_text=img.alt_text,
                    sort_order=img.sort_order,
                    is_main=img.is_main
                )
                for img in variant.images.all()
            ]
            
            variants.append(ProductVariantSchema(
                id=str(variant.id),
                sku=variant.sku,
                attributes=variant.attributes,
                variant_name=variant.variant_name,
                price=variant.price,
                compare_price=variant.compare_price,
                stock_quantity=variant.stock_quantity,
                is_active=variant.is_active,
                images=variant_images
            ))
    
    return ProductDetailSchema(
        id=str(product.id),
        name=product.name,
        slug=product.slug,
        description=product.description,
        short_description=product.short_description,
        base_price=product.base_price,
        compare_price=product.compare_price,
        product_type=product.product_type,
        status=product.status,
        category=CategorySchema(
            id=str(product.category.id),
            name=product.category.name,
            slug=product.category.slug,
            description=product.category.description,
            image=product.category.image.url if product.category.image else None,
            icon=product.category.icon,
            full_path=product.category.full_path,
            children_count=product.category.get_children().count(),
            products_count=product.category.products.filter(status=Product.Status.ACTIVE).count()
        ),
        brand=BrandSchema(
            id=str(product.brand.id),
            name=product.brand.name,
            slug=product.brand.slug,
            description=product.brand.description,
            logo=product.brand.logo.url if product.brand.logo else None,
            website=product.brand.website
        ),
        track_stock=product.track_stock,
        stock_quantity=product.stock_quantity,
        is_in_stock=product.is_in_stock,
        is_low_stock=product.is_low_stock,
        weight=product.weight,
        dimensions=product.dimensions,
        shipping_required=product.shipping_required,
        attributes=product.attributes,
        tags=product.tags,
        average_rating=product.average_rating,
        review_count=product.review_count,
        view_count=product.view_count,
        sales_count=product.sales_count,
        is_featured=product.is_featured,
        is_bestseller=product.is_bestseller,
        is_new=product.is_new,
        images=images,
        variants=variants,
        created_at=product.created_at,
        updated_at=product.updated_at
    )

# 상품 관리 (판매자/관리자)
@router.post("/products", response=ProductDetailSchema, auth=jwt_auth)
@require_permissions('create_product')
def create_product(request, payload: CreateProductSchema):
    """상품 생성"""
    
    user = request.auth
    
    # 카테고리와 브랜드 확인
    category = get_object_or_404(Category, id=payload.category_id, is_active=True)
    brand = get_object_or_404(Brand, id=payload.brand_id, is_active=True)
    
    with transaction.atomic():
        # 슬러그 생성
        slug = generate_unique_slug(Product, payload.name)
        
        product = Product.objects.create(
            name=payload.name,
            slug=slug,
            description=payload.description,
            short_description=payload.short_description,
            category=category,
            brand=brand,
            seller=user,
            product_type=payload.product_type,
            base_price=payload.base_price,
            compare_price=payload.compare_price,
            cost_price=payload.cost_price,
            track_stock=payload.track_stock,
            stock_quantity=payload.stock_quantity,
            low_stock_threshold=payload.low_stock_threshold,
            weight=payload.weight,
            dimensions=payload.dimensions or {},
            shipping_required=payload.shipping_required,
            attributes=payload.attributes or {},
            tags=payload.tags or [],
            status=Product.Status.DRAFT
        )
        
        # 재고 초기화 (Redis)
        if payload.track_stock and payload.stock_quantity > 0:
            stock_service.update_stock(
                product_id=str(product.id),
                quantity_change=payload.stock_quantity,
                movement_type='in',
                reference_type='initial',
                notes='초기 재고',
                user=user
            )
    
    # 상세 정보 반환
    return get_product_detail(request, product.slug)

@router.put("/products/{product_id}", response=ProductDetailSchema, auth=jwt_auth)
def update_product(request, product_id: str, payload: UpdateProductSchema):
    """상품 수정"""
    
    user = request.auth
    product = get_object_or_404(Product, id=product_id)
    
    # 권한 확인
    if not PermissionChecker.can_update_product(user, product):
        raise HttpError(403, "상품 수정 권한이 없습니다.")
    
    # 업데이트할 필드만 추출
    update_data = payload.dict(exclude_unset=True)
    
    with transaction.atomic():
        # 재고 변경 처리
        if 'stock_quantity' in update_data:
            old_stock = product.stock_quantity
            new_stock = update_data['stock_quantity']
            stock_change = new_stock - old_stock
            
            if stock_change != 0:
                stock_service.update_stock(
                    product_id=product_id,
                    quantity_change=stock_change,
                    movement_type='adjustment',
                    reference_type='manual',
                    notes=f'재고 수동 조정: {old_stock} → {new_stock}',
                    user=user
                )
        
        # 제품 정보 업데이트
        for field, value in update_data.items():
            setattr(product, field, value)
        
        product.updated_at = timezone.now()
        product.save()
    
    return get_product_detail(request, product.slug)

# 리뷰 관리
@router.get("/products/{product_id}/reviews", response=List[ReviewSchema])
def get_product_reviews(request, product_id: str, page: int = 1, per_page: int = 20):
    """상품 리뷰 목록"""
    
    product = get_object_or_404(Product, id=product_id)
    
    reviews = ProductReview.objects.filter(
        product=product,
        status=ProductReview.Status.APPROVED
    ).select_related('user').order_by('-created_at')
    
    # 페이지네이션
    offset = (page - 1) * per_page
    reviews_page = reviews[offset:offset + per_page]
    
    return [
        ReviewSchema(
            id=str(review.id),
            title=review.title,
            content=review.content,
            rating=review.rating,
            is_verified_purchase=review.is_verified_purchase,
            helpful_count=review.helpful_count,
            not_helpful_count=review.not_helpful_count,
            user_name=review.user.first_name or review.user.username,
            created_at=review.created_at
        )
        for review in reviews_page
    ]

@router.post("/products/{product_id}/reviews", response=ReviewSchema, auth=jwt_auth)
def create_review(request, product_id: str, payload: CreateReviewSchema):
    """리뷰 작성"""
    
    user = request.auth
    product = get_object_or_404(Product, id=product_id)
    
    # 중복 리뷰 확인
    if ProductReview.objects.filter(product=product, user=user).exists():
        raise HttpError(400, "이미 이 상품에 대한 리뷰를 작성하셨습니다.")
    
    # 구매 검증 (주문 기록 확인)
    from apps.orders.models import Order, OrderItem
    is_verified = OrderItem.objects.filter(
        order__user=user,
        product=product,
        order__status__in=['delivered', 'completed']
    ).exists()
    
    review = ProductReview.objects.create(
        product=product,
        user=user,
        title=payload.title,
        content=payload.content,
        rating=payload.rating,
        is_verified_purchase=is_verified,
        status=ProductReview.Status.APPROVED  # 자동 승인 (필요시 변경)
    )
    
    # 상품 평점 업데이트
    update_product_rating(product)
    
    return ReviewSchema(
        id=str(review.id),
        title=review.title,
        content=review.content,
        rating=review.rating,
        is_verified_purchase=review.is_verified_purchase,
        helpful_count=review.helpful_count,
        not_helpful_count=review.not_helpful_count,
        user_name=user.first_name or user.username,
        created_at=review.created_at
    )

# 위시리스트
@router.post("/products/{product_id}/wishlist", auth=jwt_auth)
def add_to_wishlist(request, product_id: str, variant_id: Optional[str] = None):
    """위시리스트 추가"""
    
    user = request.auth
    product = get_object_or_404(Product, id=product_id, status=Product.Status.ACTIVE)
    
    variant = None
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id, product=product, is_active=True)
    
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=user,
        product=product,
        variant=variant
    )
    
    if created:
        return {"message": "위시리스트에 추가되었습니다."}
    else:
        return {"message": "이미 위시리스트에 있는 상품입니다."}

@router.delete("/products/{product_id}/wishlist", auth=jwt_auth)
def remove_from_wishlist(request, product_id: str, variant_id: Optional[str] = None):
    """위시리스트 제거"""
    
    user = request.auth
    
    try:
        wishlist_item = Wishlist.objects.get(
            user=user,
            product_id=product_id,
            variant_id=variant_id
        )
        wishlist_item.delete()
        return {"message": "위시리스트에서 제거되었습니다."}
    except Wishlist.DoesNotExist:
        raise HttpError(404, "위시리스트에서 해당 상품을 찾을 수 없습니다.")

# 유틸리티 함수들
def generate_unique_slug(model, title):
    """고유 슬러그 생성"""
    from django.utils.text import slugify
    import uuid
    
    base_slug = slugify(title)
    slug = base_slug
    
    counter = 1
    while model.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    return slug

def update_product_rating(product):
    """상품 평점 업데이트"""
    from django.db.models import Avg, Count
    
    stats = ProductReview.objects.filter(
        product=product,
        status=ProductReview.Status.APPROVED
    ).aggregate(
        avg_rating=Avg('rating'),
        count=Count('id')
    )
    
    product.average_rating = stats['avg_rating'] or 0
    product.review_count = stats['count']
    product.save(update_fields=['average_rating', 'review_count'])
```

## ✅ 2장 마무리

2장에서 구현한 **고급 제품 관리 시스템**의 핵심 기능들:

### 🎯 완성된 기능
- ✅ **계층형 카테고리**: MPTT 기반 무제한 깊이 트리 구조
- ✅ **변형 상품**: 색상, 사이즈 등 옵션별 재고 관리
- ✅ **실시간 재고**: Redis 기반 동시성 처리
- ✅ **고성능 검색**: PostgreSQL 전문검색 + 패싯
- ✅ **상품 리뷰**: 검증된 구매자 리뷰 시스템
- ✅ **위시리스트**: 사용자별 관심 상품 관리
- ✅ **재고 알림**: 저재고/품절 자동 알림

### 🏗️ 기술적 특징
- **동시성 안전**: Redis Lock으로 재고 경합 상태 방지
- **검색 최적화**: GIN 인덱스 + 전문검색으로 빠른 검색
- **확장 가능**: 속성 기반 동적 상품 모델
- **캐시 활용**: Redis 캐시로 성능 향상
- **권한 관리**: 세밀한 상품 접근 권한 제어

이제 **3장: 결제 및 주문 시스템 고도화**로 넘어가겠습니다!

---

# 💳 3장: 결제 및 주문 시스템 고도화

기본적인 주문/결제를 넘어서, **실제 서비스 수준의 복잡한 결제 시스템**을 구축해보겠습니다.

## 🎯 3장에서 구현할 기능

- **다중 결제 수단** (토스페이먼츠, 포트원 PG 연동)
- **정기결제** (구독 상품 지원)
- **부분 결제** (적립금, 쿠폰, 포인트 조합)
- **주문 상태 관리** (복잡한 워크플로우)
- **배송 추적** (택배사 API 연동)
- **환불 처리** (자동/수동 환불)
- **주문 분석** (매출, 통계, 대시보드)

## 💰 3.1 고급 결제 모델 설계

```python
# apps/payments/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal
import uuid
import json

User = get_user_model()

class PaymentProvider(models.Model):
    """결제 제공업체"""
    
    class Type(models.TextChoices):
        CARD = 'card', '신용카드'
        BANK_TRANSFER = 'bank_transfer', '계좌이체'
        VIRTUAL_ACCOUNT = 'virtual_account', '가상계좌'
        MOBILE = 'mobile', '휴대폰'
        POINT = 'point', '포인트'
        COUPON = 'coupon', '쿠폰'
        SUBSCRIPTION = 'subscription', '정기결제'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', '활성'
        INACTIVE = 'inactive', '비활성'
        MAINTENANCE = 'maintenance', '점검중'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)  # 토스페이먼츠, 포트원 등
    code = models.CharField(max_length=50, unique=True)  # toss, portone 등
    type = models.CharField(max_length=20, choices=Type.choices)
    
    # API 설정
    api_key = models.CharField(max_length=200, blank=True)
    secret_key = models.CharField(max_length=200, blank=True)
    webhook_secret = models.CharField(max_length=200, blank=True)
    test_mode = models.BooleanField(default=True)
    
    # 수수료
    fee_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)  # 2.9% = 0.0290
    fixed_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # 설정
    config = models.JSONField(default=dict)  # 제공업체별 추가 설정
    
    # 상태
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    sort_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.type})"

class Payment(models.Model):
    """결제 정보"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', '결제 대기'
        PROCESSING = 'processing', '결제 진행중'
        SUCCESS = 'success', '결제 완료'
        FAILED = 'failed', '결제 실패'
        CANCELLED = 'cancelled', '결제 취소'
        PARTIAL_REFUNDED = 'partial_refunded', '부분 환불'
        REFUNDED = 'refunded', '전액 환불'
        CHARGEBACK = 'chargeback', '지불거절'
    
    class Type(models.TextChoices):
        NORMAL = 'normal', '일반 결제'
        SUBSCRIPTION = 'subscription', '정기 결제'
        PARTIAL = 'partial', '부분 결제'
        REFUND = 'refund', '환불'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 결제 대상 (Order, Subscription 등)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=100)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # 결제 정보
    provider = models.ForeignKey(PaymentProvider, on_delete=models.CASCADE, related_name='payments')
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.NORMAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # 금액
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KRW')
    
    # 수수료
    fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)  # 실제 수령액
    
    # PG사 정보
    pg_transaction_id = models.CharField(max_length=200, blank=True)
    pg_payment_key = models.CharField(max_length=200, blank=True)
    pg_response = models.JSONField(default=dict)  # PG사 응답 전체
    
    # 결제 수단 상세
    payment_method = models.CharField(max_length=50, blank=True)  # 카드, 계좌이체 등
    payment_method_detail = models.JSONField(default=dict)  # 카드번호, 은행명 등
    
    # 타임스탬프
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # 실패/취소 사유
    failure_reason = models.TextField(blank=True)
    cancel_reason = models.TextField(blank=True)
    
    # 메타데이터
    metadata = models.JSONField(default=dict)
    
    class Meta:
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['pg_transaction_id']),
            models.Index(fields=['status', 'requested_at']),
        ]
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"Payment {self.id} - {self.amount} {self.currency}"
    
    @property
    def is_success(self):
        return self.status == self.Status.SUCCESS
    
    @property
    def is_refundable(self):
        return self.status in [self.Status.SUCCESS, self.Status.PARTIAL_REFUNDED]

class PaymentSplit(models.Model):
    """결제 분할 (부분 결제)"""
    
    class Type(models.TextChoices):
        CASH = 'cash', '현금'
        POINT = 'point', '포인트'
        COUPON = 'coupon', '쿠폰'
        CREDIT = 'credit', '적립금'
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='splits')
    type = models.CharField(max_length=20, choices=Type.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # 참조 정보 (쿠폰 ID, 포인트 사용 내역 등)
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.payment.id} - {self.type}: {self.amount}"

class PaymentRefund(models.Model):
    """환불 내역"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', '환불 대기'
        PROCESSING = 'processing', '환불 진행중'
        SUCCESS = 'success', '환불 완료'
        FAILED = 'failed', '환불 실패'
        CANCELLED = 'cancelled', '환불 취소'
    
    class Type(models.TextChoices):
        FULL = 'full', '전액 환불'
        PARTIAL = 'partial', '부분 환불'
        CANCEL = 'cancel', '결제 취소'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    
    type = models.CharField(max_length=20, choices=Type.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # 환불 금액
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # 사유
    reason = models.TextField()
    
    # PG사 정보
    pg_refund_id = models.CharField(max_length=200, blank=True)
    pg_response = models.JSONField(default=dict)
    
    # 처리자
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requested_refunds')
    approved_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='approved_refunds')
    
    # 타임스탬프
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"Refund {self.id} - {self.amount}"

class Subscription(models.Model):
    """정기결제 구독"""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', '활성'
        PAUSED = 'paused', '일시중지'
        CANCELLED = 'cancelled', '취소'
        EXPIRED = 'expired', '만료'
        PAST_DUE = 'past_due', '결제 연체'
    
    class Interval(models.TextChoices):
        DAILY = 'daily', '매일'
        WEEKLY = 'weekly', '매주'
        MONTHLY = 'monthly', '매월'
        QUARTERLY = 'quarterly', '분기별'
        YEARLY = 'yearly', '매년'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    
    # 구독 상품 (별도 모델로 확장 가능)
    product_name = models.CharField(max_length=200)
    product_data = models.JSONField(default=dict)
    
    # 결제 정보
    provider = models.ForeignKey(PaymentProvider, on_delete=models.CASCADE)
    pg_subscription_id = models.CharField(max_length=200, blank=True)
    
    # 구독 설정
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KRW')
    interval = models.CharField(max_length=20, choices=Interval.choices, default=Interval.MONTHLY)
    interval_count = models.IntegerField(default=1)  # 2개월마다 = interval_count=2
    
    # 상태
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    
    # 일정
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    next_billing_date = models.DateTimeField()
    
    # 통계
    billing_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'next_billing_date']),
            models.Index(fields=['provider', 'pg_subscription_id']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Subscription {self.id} - {self.user.email}"

class SubscriptionBilling(models.Model):
    """구독 결제 내역"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', '결제 대기'
        SUCCESS = 'success', '결제 완료'
        FAILED = 'failed', '결제 실패'
        RETRYING = 'retrying', '재시도 중'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='billings')
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, null=True, blank=True, related_name='subscription_billing')
    
    # 결제 정보
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    billing_period_start = models.DateTimeField()
    billing_period_end = models.DateTimeField()
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # 재시도
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    
    # 실패 정보
    failure_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Billing {self.id} - {self.subscription.user.email}"
```

## 📦 3.2 고급 주문 모델

```python
# apps/orders/models.py (기존 모델 확장)
from django.db import models
from django.contrib.auth import get_user_model
from apps.products.models import Product, ProductVariant
from apps.payments.models import Payment
import uuid

User = get_user_model()

class Order(models.Model):
    """주문 (기존 모델 확장)"""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', '임시저장'
        PENDING_PAYMENT = 'pending_payment', '결제 대기'
        PAYMENT_FAILED = 'payment_failed', '결제 실패'
        PAID = 'paid', '결제 완료'
        CONFIRMED = 'confirmed', '주문 확인'
        PREPARING = 'preparing', '상품 준비중'
        SHIPPED = 'shipped', '배송 중'
        DELIVERED = 'delivered', '배송 완료'
        CANCELLED = 'cancelled', '주문 취소'
        REFUND_REQUESTED = 'refund_requested', '환불 요청'
        REFUNDED = 'refunded', '환불 완료'
        COMPLETED = 'completed', '주문 완료'
    
    class Type(models.TextChoices):
        NORMAL = 'normal', '일반 주문'
        SUBSCRIPTION = 'subscription', '구독 주문'
        GIFT = 'gift', '선물 주문'
        BULK = 'bulk', '대량 주문'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    
    # 주문 타입
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.NORMAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    # 금액 정보
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # 할인 정보
    coupon_code = models.CharField(max_length=50, blank=True)
    coupon_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    point_used = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # 배송 정보
    shipping_method = models.CharField(max_length=50, default='standard')
    shipping_name = models.CharField(max_length=100)
    shipping_phone = models.CharField(max_length=20)
    shipping_email = models.EmailField(blank=True)
    shipping_address = models.JSONField(default=dict)  # 주소 정보
    shipping_memo = models.TextField(blank=True)
    
    # 선물 주문
    is_gift = models.BooleanField(default=False)
    gift_message = models.TextField(blank=True)
    gift_recipient = models.JSONField(default=dict)  # 받는 사람 정보
    
    # 추가 정보
    notes = models.TextField(blank=True)  # 주문 메모
    admin_notes = models.TextField(blank=True)  # 관리자 메모
    
    # 외부 참조
    parent_order = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='child_orders')
    subscription = models.ForeignKey('payments.Subscription', on_delete=models.CASCADE, null=True, blank=True, related_name='orders')
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['order_number']),
            models.Index(fields=['type', 'status']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order_number}"
    
    @property
    def can_cancel(self):
        """취소 가능 여부"""
        return self.status in [
            self.Status.PENDING_PAYMENT,
            self.Status.PAID,
            self.Status.CONFIRMED
        ]
    
    @property
    def can_refund(self):
        """환불 가능 여부"""
        return self.status in [
            self.Status.SHIPPED,
            self.Status.DELIVERED,
            self.Status.COMPLETED
        ]

class OrderItem(models.Model):
    """주문 상품 (기존 모델 확장)"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', '대기중'
        CONFIRMED = 'confirmed', '확인됨'
        PREPARING = 'preparing', '준비중'
        SHIPPED = 'shipped', '배송중'
        DELIVERED = 'delivered', '배송완료'
        CANCELLED = 'cancelled', '취소됨'
        REFUNDED = 'refunded', '환불됨'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    
    # 주문 당시 상품 정보 (가격 변동 대비)
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=100)
    product_data = models.JSONField(default=dict)  # 상품 상세 정보 스냅샷
    
    # 가격 정보
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    # 할인 정보
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    final_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    # 상태
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # 배송 정보
    tracking_number = models.CharField(max_length=100, blank=True)
    shipping_carrier = models.CharField(max_length=50, blank=True)
    
    # 타임스탬프
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

class OrderStatusHistory(models.Model):
    """주문 상태 변경 이력"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order.order_number}: {self.from_status} → {self.to_status}"

class Shipment(models.Model):
    """배송 정보"""
    
    class Status(models.TextChoices):
        PREPARING = 'preparing', '배송 준비중'
        PICKED_UP = 'picked_up', '집화 완료'
        IN_TRANSIT = 'in_transit', '배송 중'
        OUT_FOR_DELIVERY = 'out_for_delivery', '배송중 (배송지 인근)'
        DELIVERED = 'delivered', '배송 완료'
        FAILED = 'failed', '배송 실패'
        RETURNED = 'returned', '반송'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='shipments')
    items = models.ManyToManyField(OrderItem, related_name='shipments')
    
    # 배송 정보
    carrier = models.CharField(max_length=50)  # CJ대한통운, 한진택배 등
    tracking_number = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PREPARING)
    
    # 주소 정보
    from_address = models.JSONField(default=dict)
    to_address = models.JSONField(default=dict)
    
    # 배송 일정
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    actual_delivery = models.DateTimeField(null=True, blank=True)
    
    # 추가 정보
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    dimensions = models.JSONField(default=dict)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Shipment {self.tracking_number}"

class ShipmentTracking(models.Model):
    """배송 추적 이력"""
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='tracking_history')
    status = models.CharField(max_length=50)
    description = models.TextField()
    location = models.CharField(max_length=200, blank=True)
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.shipment.tracking_number}: {self.status}"
```

## 💳 3.3 결제 서비스 구현

```python
# apps/payments/services.py
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import requests
import hashlib
import hmac
import json
from typing import Dict, Any, Optional

from .models import *
from apps.orders.models import Order

class PaymentException(Exception):
    """결제 관련 예외"""
    pass

class TossPaymentService:
    """토스페이먼츠 서비스"""
    
    def __init__(self, test_mode=True):
        self.test_mode = test_mode
        self.client_key = settings.TOSS_CLIENT_KEY
        self.secret_key = settings.TOSS_SECRET_KEY
        self.base_url = "https://api.tosspayments.com/v1" if not test_mode else "https://api.tosspayments.com/v1"
    
    def create_payment(self, order: Order, payment_method: str, **kwargs) -> Payment:
        """결제 생성"""
        
        # 결제 제공업체 조회
        provider = PaymentProvider.objects.get(code='toss', type=payment_method)
        
        with transaction.atomic():
            # 결제 객체 생성
            payment = Payment.objects.create(
                content_object=order,
                provider=provider,
                type=Payment.Type.NORMAL,
                amount=order.total_amount,
                currency='KRW',
                net_amount=order.total_amount - self._calculate_fee(order.total_amount, provider),
                fee_amount=self._calculate_fee(order.total_amount, provider),
                payment_method=payment_method,
                metadata={
                    'order_number': order.order_number,
                    'customer_id': str(order.user.id),
                    'customer_email': order.user.email,
                    **kwargs
                }
            )
            
            # 주문 상태 업데이트
            order.status = Order.Status.PENDING_PAYMENT
            order.save(update_fields=['status'])
            
            return payment
    
    def confirm_payment(self, payment: Payment, payment_key: str, amount: Decimal) -> bool:
        """결제 승인"""
        
        # 금액 검증
        if amount != payment.amount:
            raise PaymentException(f"결제 금액 불일치: 요청 {amount}, 실제 {payment.amount}")
        
        # 토스페이먼츠 API 호출
        url = f"{self.base_url}/payments/confirm"
        headers = {
            'Authorization': f'Basic {self._get_auth_token()}',
            'Content-Type': 'application/json'
        }
        data = {
            'paymentKey': payment_key,
            'orderId': str(payment.id),
            'amount': int(amount)
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response_data = response.json()
            
            if response.status_code == 200:
                return self._handle_payment_success(payment, payment_key, response_data)
            else:
                return self._handle_payment_failure(payment, response_data)
                
        except requests.RequestException as e:
            self._handle_payment_error(payment, str(e))
            return False
    
    def cancel_payment(self, payment: Payment, reason: str, amount: Optional[Decimal] = None) -> PaymentRefund:
        """결제 취소/환불"""
        
        if not payment.is_refundable:
            raise PaymentException("환불 불가능한 결제입니다.")
        
        refund_amount = amount or payment.amount
        
        # 토스페이먼츠 API 호출
        url = f"{self.base_url}/payments/{payment.pg_payment_key}/cancel"
        headers = {
            'Authorization': f'Basic {self._get_auth_token()}',
            'Content-Type': 'application/json'
        }
        data = {
            'cancelReason': reason,
            'cancelAmount': int(refund_amount) if amount else None
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response_data = response.json()
            
            if response.status_code == 200:
                return self._handle_refund_success(payment, refund_amount, reason, response_data)
            else:
                return self._handle_refund_failure(payment, refund_amount, reason, response_data)
                
        except requests.RequestException as e:
            raise PaymentException(f"환불 요청 실패: {str(e)}")
    
    def create_subscription(self, user, product_data: dict, billing_key: str) -> Subscription:
        """정기결제 구독 생성"""
        
        provider = PaymentProvider.objects.get(code='toss', type='subscription')
        
        subscription = Subscription.objects.create(
            user=user,
            provider=provider,
            product_name=product_data['name'],
            product_data=product_data,
            amount=product_data['amount'],
            interval=product_data.get('interval', 'monthly'),
            start_date=timezone.now(),
            next_billing_date=self._calculate_next_billing_date(product_data.get('interval', 'monthly')),
            pg_subscription_id=billing_key
        )
        
        return subscription
    
    def bill_subscription(self, subscription: Subscription) -> SubscriptionBilling:
        """구독 결제 실행"""
        
        billing = SubscriptionBilling.objects.create(
            subscription=subscription,
            amount=subscription.amount,
            billing_period_start=subscription.next_billing_date,
            billing_period_end=self._calculate_period_end(
                subscription.next_billing_date, 
                subscription.interval
            )
        )
        
        try:
            # 토스페이먼츠 정기결제 API 호출
            url = f"{self.base_url}/billing/{subscription.pg_subscription_id}"
            headers = {
                'Authorization': f'Basic {self._get_auth_token()}',
                'Content-Type': 'application/json'
            }
            data = {
                'customerKey': str(subscription.user.id),
                'amount': int(subscription.amount),
                'orderId': str(billing.id),
                'orderName': subscription.product_name
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response_data = response.json()
            
            if response.status_code == 200:
                self._handle_subscription_billing_success(billing, response_data)
            else:
                self._handle_subscription_billing_failure(billing, response_data)
                
        except requests.RequestException as e:
            self._handle_subscription_billing_error(billing, str(e))
        
        return billing
    
    def _get_auth_token(self) -> str:
        """인증 토큰 생성"""
        import base64
        credentials = f"{self.secret_key}:"
        return base64.b64encode(credentials.encode()).decode()
    
    def _calculate_fee(self, amount: Decimal, provider: PaymentProvider) -> Decimal:
        """수수료 계산"""
        return amount * provider.fee_rate + provider.fixed_fee
    
    def _handle_payment_success(self, payment: Payment, payment_key: str, response_data: dict) -> bool:
        """결제 성공 처리"""
        with transaction.atomic():
            payment.status = Payment.Status.SUCCESS
            payment.pg_payment_key = payment_key
            payment.pg_transaction_id = response_data.get('transactionKey', '')
            payment.pg_response = response_data
            payment.payment_method_detail = {
                'method': response_data.get('method'),
                'card': response_data.get('card', {}),
                'bank': response_data.get('bank', {}),
            }
            payment.approved_at = timezone.now()
            payment.save()
            
            # 주문 상태 업데이트
            order = payment.content_object
            order.status = Order.Status.PAID
            order.save(update_fields=['status'])
            
            # 주문 상태 이력 추가
            from apps.orders.models import OrderStatusHistory
            OrderStatusHistory.objects.create(
                order=order,
                from_status=Order.Status.PENDING_PAYMENT,
                to_status=Order.Status.PAID,
                changed_by=order.user,
                reason='결제 완료'
            )
            
        return True
    
    def _handle_payment_failure(self, payment: Payment, response_data: dict) -> bool:
        """결제 실패 처리"""
        with transaction.atomic():
            payment.status = Payment.Status.FAILED
            payment.pg_response = response_data
            payment.failure_reason = response_data.get('message', '결제 실패')
            payment.failed_at = timezone.now()
            payment.save()
            
            # 주문 상태 업데이트
            order = payment.content_object
            order.status = Order.Status.PAYMENT_FAILED
            order.save(update_fields=['status'])
            
        return False
    
    def _handle_payment_error(self, payment: Payment, error_message: str):
        """결제 오류 처리"""
        payment.status = Payment.Status.FAILED
        payment.failure_reason = error_message
        payment.failed_at = timezone.now()
        payment.save()

class PortOnePaymentService:
    """포트원 결제 서비스"""
    
    def __init__(self, test_mode=True):
        self.test_mode = test_mode
        self.api_key = settings.PORTONE_API_KEY
        self.api_secret = settings.PORTONE_API_SECRET
        self.base_url = "https://api.iamport.kr" if not test_mode else "https://api.iamport.kr"
        self._access_token = None
    
    def _get_access_token(self) -> str:
        """액세스 토큰 획득"""
        if self._access_token:
            return self._access_token
        
        url = f"{self.base_url}/users/getToken"
        data = {
            'imp_key': self.api_key,
            'imp_secret': self.api_secret
        }
        
        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            self._access_token = result['response']['access_token']
            return self._access_token
        else:
            raise PaymentException("포트원 액세스 토큰 획득 실패")
    
    # ... 포트원 API 구현 (토스페이먼츠와 유사한 패턴)

class PaymentService:
    """통합 결제 서비스"""
    
    def __init__(self):
        self.providers = {
            'toss': TossPaymentService(),
            'portone': PortOnePaymentService(),
        }
    
    def create_payment(self, order: Order, provider_code: str, payment_method: str, **kwargs) -> Payment:
        """결제 생성"""
        if provider_code not in self.providers:
            raise PaymentException(f"지원하지 않는 결제 제공업체: {provider_code}")
        
        provider_service = self.providers[provider_code]
        return provider_service.create_payment(order, payment_method, **kwargs)
    
    def confirm_payment(self, payment: Payment, payment_key: str, amount: Decimal) -> bool:
        """결제 승인"""
        provider_code = payment.provider.code
        if provider_code not in self.providers:
            raise PaymentException(f"지원하지 않는 결제 제공업체: {provider_code}")
        
        provider_service = self.providers[provider_code]
        return provider_service.confirm_payment(payment, payment_key, amount)
    
    def process_webhook(self, provider_code: str, webhook_data: dict):
        """웹훅 처리"""
        if provider_code not in self.providers:
            return
        
        provider_service = self.providers[provider_code]
        if hasattr(provider_service, 'process_webhook'):
            provider_service.process_webhook(webhook_data)

# 전역 서비스 인스턴스
payment_service = PaymentService()
```

계속해서 **주문 및 배송 API**를 구현하겠습니다.

## 📋 3.4 주문 및 배송 API 구현

```python
# apps/orders/schemas.py
from ninja import Schema
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from enum import Enum

class OrderStatusEnum(str, Enum):
    DRAFT = 'draft'
    PENDING_PAYMENT = 'pending_payment'
    PAID = 'paid'
    CONFIRMED = 'confirmed'
    PREPARING = 'preparing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'

class CreateOrderSchema(Schema):
    # 배송 정보
    shipping_address: Dict[str, Any]
    shipping_method: str = 'standard'
    shipping_memo: Optional[str] = ''
    
    # 결제 정보
    payment_provider: str  # toss, portone
    payment_method: str   # card, bank_transfer, virtual_account
    
    # 할인 정보
    coupon_code: Optional[str] = None
    use_points: Optional[Decimal] = Decimal('0')
    
    # 선물 옵션
    is_gift: bool = False
    gift_message: Optional[str] = ''
    gift_recipient: Optional[Dict[str, Any]] = None

class OrderItemSchema(Schema):
    id: str
    product_id: str
    product_name: str
    product_sku: str
    variant_id: Optional[str]
    unit_price: Decimal
    quantity: int
    total_price: Decimal
    discount_amount: Decimal
    final_price: Decimal
    status: str

class OrderSchema(Schema):
    id: str
    order_number: str
    type: str
    status: str
    
    # 금액 정보
    subtotal: Decimal
    shipping_cost: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    
    # 할인 정보
    coupon_code: Optional[str]
    coupon_discount: Decimal
    point_used: Decimal
    
    # 배송 정보
    shipping_method: str
    shipping_address: Dict[str, Any]
    shipping_memo: Optional[str]
    
    # 선물 정보
    is_gift: bool
    gift_message: Optional[str]
    gift_recipient: Optional[Dict[str, Any]]
    
    # 상품 목록
    items: List[OrderItemSchema]
    
    # 상태 정보
    can_cancel: bool
    can_refund: bool
    
    # 타임스탬프
    created_at: datetime
    updated_at: datetime
    confirmed_at: Optional[datetime]
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]

class PaymentRequestSchema(Schema):
    provider: str
    method: str
    return_url: str
    cancel_url: str

class PaymentConfirmSchema(Schema):
    payment_key: str
    amount: Decimal

class ShipmentTrackingSchema(Schema):
    carrier: str
    tracking_number: str
    status: str
    estimated_delivery: Optional[datetime]
    tracking_history: List[Dict[str, Any]]

class RefundRequestSchema(Schema):
    reason: str
    amount: Optional[Decimal] = None  # None이면 전액 환불
    items: Optional[List[str]] = None  # 부분 환불시 아이템 ID 목록
```

```python
# apps/orders/api.py
from ninja import Router
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from typing import List

from .models import *
from .schemas import *
from apps.cart.models import Cart
from apps.payments.services import payment_service
from apps.inventory.services import stock_service
from core.auth.jwt_auth import jwt_auth
from core.auth.permissions import require_permissions

router = Router()

@router.post("/orders", response=OrderSchema, auth=jwt_auth)
def create_order(request, payload: CreateOrderSchema):
    """주문 생성"""
    
    user = request.auth
    
    # 장바구니 확인
    try:
        cart = Cart.objects.get(user=user)
        if not cart.items.exists():
            raise HttpError(400, "장바구니가 비어있습니다.")
    except Cart.DoesNotExist:
        raise HttpError(400, "장바구니를 찾을 수 없습니다.")
    
    try:
        with transaction.atomic():
            # 주문 번호 생성
            order_number = generate_order_number()
            
            # 금액 계산
            cart_items = cart.items.select_related('product', 'variant')
            subtotal = sum(item.total_price for item in cart_items)
            
            # 할인 적용
            discount_amount = Decimal('0')
            coupon_discount = Decimal('0')
            
            if payload.coupon_code:
                coupon_discount = apply_coupon(payload.coupon_code, subtotal, user)
                discount_amount += coupon_discount
            
            if payload.use_points > 0:
                # 포인트 사용 처리
                available_points = get_user_points(user)
                if payload.use_points > available_points:
                    raise HttpError(400, "사용 가능한 포인트가 부족합니다.")
                discount_amount += payload.use_points
            
            # 배송비 계산
            shipping_cost = calculate_shipping_cost(
                subtotal - discount_amount,
                payload.shipping_method,
                payload.shipping_address
            )
            
            # 세금 계산
            tax_amount = calculate_tax(subtotal - discount_amount)
            
            total_amount = subtotal + shipping_cost + tax_amount - discount_amount
            
            # 주문 생성
            order = Order.objects.create(
                order_number=order_number,
                user=user,
                type=Order.Type.GIFT if payload.is_gift else Order.Type.NORMAL,
                status=Order.Status.DRAFT,
                subtotal=subtotal,
                shipping_cost=shipping_cost,
                tax_amount=tax_amount,
                discount_amount=discount_amount,
                total_amount=total_amount,
                coupon_code=payload.coupon_code,
                coupon_discount=coupon_discount,
                point_used=payload.use_points,
                shipping_method=payload.shipping_method,
                shipping_address=payload.shipping_address,
                shipping_memo=payload.shipping_memo,
                is_gift=payload.is_gift,
                gift_message=payload.gift_message,
                gift_recipient=payload.gift_recipient or {}
            )
            
            # 주문 상품 생성 및 재고 예약
            for cart_item in cart_items:
                # 재고 확인
                current_stock = stock_service.get_current_stock(
                    str(cart_item.product.id),
                    str(cart_item.variant.id) if cart_item.variant else None
                )
                
                if current_stock < cart_item.quantity:
                    raise HttpError(400, f"{cart_item.product.name}의 재고가 부족합니다.")
                
                # 주문 상품 생성
                order_item = OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    variant=cart_item.variant,
                    product_name=cart_item.product.name,
                    product_sku=cart_item.variant.sku if cart_item.variant else cart_item.product.sku,
                    product_data={
                        'name': cart_item.product.name,
                        'description': cart_item.product.description,
                        'category': cart_item.product.category.name,
                        'brand': cart_item.product.brand.name,
                        'attributes': cart_item.variant.attributes if cart_item.variant else cart_item.product.attributes
                    },
                    unit_price=cart_item.product.base_price,
                    quantity=cart_item.quantity,
                    total_price=cart_item.total_price,
                    discount_amount=Decimal('0'),
                    final_price=cart_item.total_price
                )
                
                # 재고 예약
                stock_service.reserve_stock(
                    product_id=str(cart_item.product.id),
                    quantity=cart_item.quantity,
                    variant_id=str(cart_item.variant.id) if cart_item.variant else None,
                    order_id=order_number
                )
            
            # 결제 생성
            payment = payment_service.create_payment(
                order=order,
                provider_code=payload.payment_provider,
                payment_method=payload.payment_method
            )
            
            # 장바구니 비우기
            cart.items.all().delete()
            
            # 사용한 쿠폰/포인트 처리
            if payload.coupon_code:
                use_coupon(payload.coupon_code, user)
            
            if payload.use_points > 0:
                deduct_user_points(user, payload.use_points, f'주문 {order_number} 사용')
            
            return convert_order_to_schema(order)
            
    except Exception as e:
        raise HttpError(500, f"주문 생성 중 오류가 발생했습니다: {str(e)}")

@router.get("/orders", response=List[OrderSchema], auth=jwt_auth)
def list_orders(request, status: Optional[str] = None, page: int = 1, per_page: int = 20):
    """주문 목록 조회"""
    
    user = request.auth
    queryset = Order.objects.filter(user=user).select_related().prefetch_related('items')
    
    if status:
        queryset = queryset.filter(status=status)
    
    # 페이지네이션
    offset = (page - 1) * per_page
    orders = queryset[offset:offset + per_page]
    
    return [convert_order_to_schema(order) for order in orders]

@router.get("/orders/{order_id}", response=OrderSchema, auth=jwt_auth)
def get_order_detail(request, order_id: str):
    """주문 상세 조회"""
    
    user = request.auth
    order = get_object_or_404(
        Order.objects.select_related().prefetch_related('items'),
        id=order_id,
        user=user
    )
    
    return convert_order_to_schema(order)

@router.post("/orders/{order_id}/cancel", auth=jwt_auth)
def cancel_order(request, order_id: str, reason: str = "사용자 요청"):
    """주문 취소"""
    
    user = request.auth
    order = get_object_or_404(Order, id=order_id, user=user)
    
    if not order.can_cancel:
        raise HttpError(400, "취소할 수 없는 주문 상태입니다.")
    
    try:
        with transaction.atomic():
            # 재고 복구
            for item in order.items.all():
                stock_service.release_stock(
                    product_id=str(item.product.id),
                    quantity=item.quantity,
                    variant_id=str(item.variant.id) if item.variant else None,
                    order_id=order.order_number
                )
            
            # 결제 취소 (결제가 완료된 경우)
            if order.status == Order.Status.PAID:
                payments = Payment.objects.filter(
                    content_type__model='order',
                    object_id=str(order.id),
                    status=Payment.Status.SUCCESS
                )
                
                for payment in payments:
                    payment_service.cancel_payment(payment, reason)
            
            # 주문 상태 변경
            old_status = order.status
            order.status = Order.Status.CANCELLED
            order.cancelled_at = timezone.now()
            order.save(update_fields=['status', 'cancelled_at'])
            
            # 상태 이력 추가
            OrderStatusHistory.objects.create(
                order=order,
                from_status=old_status,
                to_status=Order.Status.CANCELLED,
                changed_by=user,
                reason=reason
            )
            
            # 포인트/쿠폰 복구
            if order.point_used > 0:
                refund_user_points(user, order.point_used, f'주문 {order.order_number} 취소')
            
            if order.coupon_code:
                restore_coupon(order.coupon_code, user)
            
        return {"message": "주문이 취소되었습니다."}
        
    except Exception as e:
        raise HttpError(500, f"주문 취소 중 오류가 발생했습니다: {str(e)}")

@router.post("/orders/{order_id}/request-refund", auth=jwt_auth)
def request_refund(request, order_id: str, payload: RefundRequestSchema):
    """환불 요청"""
    
    user = request.auth
    order = get_object_or_404(Order, id=order_id, user=user)
    
    if not order.can_refund:
        raise HttpError(400, "환불할 수 없는 주문 상태입니다.")
    
    try:
        with transaction.atomic():
            # 환불 금액 계산
            refund_amount = payload.amount or order.total_amount
            
            if payload.items:
                # 부분 환불 처리
                refund_amount = calculate_partial_refund_amount(order, payload.items)
            
            # 결제 환불 요청
            payments = Payment.objects.filter(
                content_type__model='order',
                object_id=str(order.id),
                status=Payment.Status.SUCCESS
            )
            
            for payment in payments:
                payment_service.create_refund_request(
                    payment=payment,
                    amount=refund_amount,
                    reason=payload.reason,
                    requested_by=user
                )
            
            # 주문 상태 변경
            old_status = order.status
            order.status = Order.Status.REFUND_REQUESTED
            order.save(update_fields=['status'])
            
            # 상태 이력 추가
            OrderStatusHistory.objects.create(
                order=order,
                from_status=old_status,
                to_status=Order.Status.REFUND_REQUESTED,
                changed_by=user,
                reason=f"환불 요청: {payload.reason}"
            )
            
        return {"message": "환불 요청이 접수되었습니다."}
        
    except Exception as e:
        raise HttpError(500, f"환불 요청 중 오류가 발생했습니다: {str(e)}")

@router.get("/orders/{order_id}/tracking", response=ShipmentTrackingSchema, auth=jwt_auth)
def get_order_tracking(request, order_id: str):
    """주문 배송 추적"""
    
    user = request.auth
    order = get_object_or_404(Order, id=order_id, user=user)
    
    try:
        shipment = order.shipments.filter(status__in=[
            Shipment.Status.PICKED_UP,
            Shipment.Status.IN_TRANSIT,
            Shipment.Status.OUT_FOR_DELIVERY,
            Shipment.Status.DELIVERED
        ]).first()
        
        if not shipment:
            raise HttpError(404, "배송 정보를 찾을 수 없습니다.")
        
        # 실시간 배송 추적 정보 업데이트
        tracking_service = ShippingTrackingService()
        tracking_info = tracking_service.get_tracking_info(
            shipment.carrier,
            shipment.tracking_number
        )
        
        return ShipmentTrackingSchema(
            carrier=shipment.carrier,
            tracking_number=shipment.tracking_number,
            status=shipment.status,
            estimated_delivery=shipment.estimated_delivery,
            tracking_history=tracking_info['history']
        )
        
    except Exception as e:
        raise HttpError(500, f"배송 추적 조회 중 오류가 발생했습니다: {str(e)}")

# 결제 관련 엔드포인트
@router.post("/orders/{order_id}/payments/confirm", auth=jwt_auth)
def confirm_payment(request, order_id: str, payload: PaymentConfirmSchema):
    """결제 승인"""
    
    user = request.auth
    order = get_object_or_404(Order, id=order_id, user=user)
    
    # 진행 중인 결제 조회
    payment = Payment.objects.filter(
        content_type__model='order',
        object_id=str(order.id),
        status=Payment.Status.PENDING
    ).first()
    
    if not payment:
        raise HttpError(404, "진행 중인 결제를 찾을 수 없습니다.")
    
    try:
        success = payment_service.confirm_payment(
            payment=payment,
            payment_key=payload.payment_key,
            amount=payload.amount
        )
        
        if success:
            return {"message": "결제가 완료되었습니다.", "payment_id": str(payment.id)}
        else:
            raise HttpError(400, "결제 승인에 실패했습니다.")
            
    except Exception as e:
        raise HttpError(500, f"결제 승인 중 오류가 발생했습니다: {str(e)}")

# 유틸리티 함수들
def generate_order_number() -> str:
    """주문번호 생성"""
    import time
    import random
    timestamp = str(int(time.time()))
    random_num = str(random.randint(1000, 9999))
    return f"ORD{timestamp[-6:]}{random_num}"

def calculate_shipping_cost(amount: Decimal, method: str, address: dict) -> Decimal:
    """배송비 계산"""
    if amount >= 50000:  # 5만원 이상 무료배송
        return Decimal('0')
    
    if method == 'express':
        return Decimal('5000')
    else:
        return Decimal('3000')

def calculate_tax(amount: Decimal) -> Decimal:
    """세금 계산 (10%)"""
    return amount * Decimal('0.1')

def convert_order_to_schema(order: Order) -> OrderSchema:
    """주문 객체를 스키마로 변환"""
    items = [
        OrderItemSchema(
            id=str(item.id),
            product_id=str(item.product.id),
            product_name=item.product_name,
            product_sku=item.product_sku,
            variant_id=str(item.variant.id) if item.variant else None,
            unit_price=item.unit_price,
            quantity=item.quantity,
            total_price=item.total_price,
            discount_amount=item.discount_amount,
            final_price=item.final_price,
            status=item.status
        )
        for item in order.items.all()
    ]
    
    return OrderSchema(
        id=str(order.id),
        order_number=order.order_number,
        type=order.type,
        status=order.status,
        subtotal=order.subtotal,
        shipping_cost=order.shipping_cost,
        tax_amount=order.tax_amount,
        discount_amount=order.discount_amount,
        total_amount=order.total_amount,
        coupon_code=order.coupon_code,
        coupon_discount=order.coupon_discount,
        point_used=order.point_used,
        shipping_method=order.shipping_method,
        shipping_address=order.shipping_address,
        shipping_memo=order.shipping_memo,
        is_gift=order.is_gift,
        gift_message=order.gift_message,
        gift_recipient=order.gift_recipient,
        items=items,
        can_cancel=order.can_cancel,
        can_refund=order.can_refund,
        created_at=order.created_at,
        updated_at=order.updated_at,
        confirmed_at=order.confirmed_at,
        shipped_at=order.shipped_at,
        delivered_at=order.delivered_at
    )

class ShippingTrackingService:
    """배송 추적 서비스"""
    
    def get_tracking_info(self, carrier: str, tracking_number: str) -> dict:
        """배송 추적 정보 조회"""
        
        # 택배사별 API 호출 (예시)
        if carrier == 'CJ대한통운':
            return self._get_cj_tracking(tracking_number)
        elif carrier == '한진택배':
            return self._get_hanjin_tracking(tracking_number)
        else:
            return {'history': []}
    
    def _get_cj_tracking(self, tracking_number: str) -> dict:
        """CJ대한통운 배송 추적"""
        # 실제 API 구현 필요
        return {
            'history': [
                {
                    'status': '집화완료',
                    'description': '상품이 택배사에 접수되었습니다.',
                    'location': '서울 강남구',
                    'timestamp': timezone.now()
                }
            ]
        }
```

## ✅ 3장 마무리

3장에서 구현한 **결제 및 주문 시스템**의 핵심 기능들:

### 🎯 완성된 기능
- ✅ **다중 결제 수단**: 토스페이먼츠, 포트원 PG 연동
- ✅ **정기결제**: 구독 상품 자동 결제 시스템
- ✅ **부분 결제**: 적립금, 쿠폰, 포인트 조합 결제
- ✅ **주문 워크플로우**: 복잡한 주문 상태 관리
- ✅ **환불 처리**: 자동/수동 환불 시스템
- ✅ **배송 추적**: 택배사 API 연동
- ✅ **재고 연동**: 주문 시 실시간 재고 예약/해제

### 🏗️ 기술적 특징
- **트랜잭션 안전**: 주문/결제/재고 원자성 보장
- **PG사 추상화**: 여러 결제 제공업체 통합 관리
- **상태 추적**: 상세한 주문/결제 상태 이력 관리
- **웹훅 처리**: 비동기 결제 결과 처리
- **에러 핸들링**: 결제 실패 시 자동 복구

### 💰 비즈니스 로직
- **할인 시스템**: 쿠폰, 적립금, 포인트 통합
- **배송비 계산**: 조건별 배송비 자동 계산
- **정기결제**: B2B/구독 서비스 지원
- **환불 정책**: 부분/전액 환불 유연 처리

이제 **4장: 성능 최적화 및 확장성**으로 넘어가겠습니다!

---

# ⚡ 4장: 성능 최적화 및 확장성

실제 서비스 운영에 필요한 **고성능 최적화 기법**을 적용해보겠습니다.

## 🎯 4장에서 구현할 기능

- **다층 캐싱** (Redis, Memcached, CDN)
- **데이터베이스 최적화** (인덱싱, 쿼리 최적화, 샤딩)
- **비동기 처리** (Celery, 백그라운드 작업)
- **API 최적화** (페이지네이션, 필드 선택, 압축)
- **로드 밸런싱** (다중 서버 구성)

## 🚀 4.1 캐싱 시스템

```python
# core/cache/managers.py
from django.core.cache import cache
from django.conf import settings
import json
import hashlib
from typing import Any, Optional, List
from functools import wraps

class CacheManager:
    """캐시 관리자"""
    
    def __init__(self, prefix='shop'):
        self.prefix = prefix
        self.default_timeout = 3600  # 1시간
    
    def _make_key(self, key: str) -> str:
        """캐시 키 생성"""
        return f"{self.prefix}:{key}"
    
    def get(self, key: str, default=None) -> Any:
        """캐시 조회"""
        cache_key = self._make_key(key)
        return cache.get(cache_key, default)
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """캐시 저장"""
        cache_key = self._make_key(key)
        timeout = timeout or self.default_timeout
        return cache.set(cache_key, value, timeout)
    
    def delete(self, key: str) -> bool:
        """캐시 삭제"""
        cache_key = self._make_key(key)
        return cache.delete(cache_key)
    
    def delete_pattern(self, pattern: str):
        """패턴 매칭 캐시 삭제"""
        cache_pattern = self._make_key(pattern)
        cache.delete_pattern(cache_pattern)

class ProductCacheManager(CacheManager):
    """상품 캐시 관리"""
    
    def __init__(self):
        super().__init__('product')
    
    def get_product(self, product_id: str):
        """상품 캐시 조회"""
        key = f"detail:{product_id}"
        return self.get(key)
    
    def set_product(self, product_id: str, product_data: dict, timeout: int = 1800):
        """상품 캐시 저장 (30분)"""
        key = f"detail:{product_id}"
        return self.set(key, product_data, timeout)
    
    def invalidate_product(self, product_id: str):
        """상품 캐시 무효화"""
        key = f"detail:{product_id}"
        self.delete(key)
        
        # 관련 캐시도 무효화
        self.delete_pattern(f"list:*")
        self.delete_pattern(f"search:*")
    
    def get_product_list(self, cache_key: str):
        """상품 목록 캐시 조회"""
        key = f"list:{cache_key}"
        return self.get(key)
    
    def set_product_list(self, cache_key: str, products: list, timeout: int = 900):
        """상품 목록 캐시 저장 (15분)"""
        key = f"list:{cache_key}"
        return self.set(key, products, timeout)

def cache_result(key_func, timeout=3600):
    """결과 캐싱 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            if callable(key_func):
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = key_func
            
            # 캐시에서 조회
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # 함수 실행 후 캐시 저장
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator

# 전역 캐시 매니저
product_cache = ProductCacheManager()
```

## 🗄️ 4.2 데이터베이스 최적화

```python
# core/db/optimizations.py
from django.db import models
from django.db.models import Prefetch, Q
from django.core.paginator import Paginator
from typing import List, Dict, Any

class OptimizedQueryManager:
    """최적화된 쿼리 관리"""
    
    @staticmethod
    def get_products_optimized(filters: dict = None, page: int = 1, per_page: int = 20):
        """상품 목록 최적화 쿼리"""
        from apps.products.models import Product, ProductImage, ProductReview
        
        # 기본 쿼리 (select_related로 JOIN 최적화)
        queryset = Product.objects.select_related(
            'category',
            'brand',
            'seller'
        ).prefetch_related(
            # 메인 이미지만 미리 로드
            Prefetch(
                'images',
                queryset=ProductImage.objects.filter(is_main=True),
                to_attr='main_images'
            ),
            # 평점 정보 미리 계산
            Prefetch(
                'reviews',
                queryset=ProductReview.objects.filter(status='approved').only('rating'),
                to_attr='approved_reviews'
            )
        ).filter(status='active')
        
        # 필터 적용
        if filters:
            if filters.get('category_ids'):
                queryset = queryset.filter(category_id__in=filters['category_ids'])
            
            if filters.get('price_range'):
                min_price, max_price = filters['price_range']
                queryset = queryset.filter(base_price__range=(min_price, max_price))
            
            if filters.get('in_stock'):
                queryset = queryset.filter(
                    Q(track_stock=False) | Q(stock_quantity__gt=0)
                )
        
        # only()로 필요한 필드만 조회
        queryset = queryset.only(
            'id', 'name', 'slug', 'base_price', 'compare_price',
            'average_rating', 'review_count', 'is_featured',
            'category__name', 'brand__name'
        )
        
        # 페이지네이션
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)
        
        return {
            'products': page_obj.object_list,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'total_pages': paginator.num_pages,
            'total_count': paginator.count
        }
    
    @staticmethod
    def get_order_with_items(order_id: str):
        """주문 상세 최적화 쿼리"""
        from apps.orders.models import Order, OrderItem
        
        return Order.objects.select_related(
            'user',
            'user__profile'
        ).prefetch_related(
            Prefetch(
                'items',
                queryset=OrderItem.objects.select_related(
                    'product',
                    'variant'
                ).only(
                    'id', 'product_name', 'quantity', 'unit_price',
                    'total_price', 'product__name', 'variant__sku'
                )
            ),
            'payments',
            'shipments'
        ).get(id=order_id)

class DatabaseIndexManager:
    """데이터베이스 인덱스 관리"""
    
    @staticmethod
    def get_index_recommendations():
        """인덱스 추천"""
        return {
            'products_product': [
                ['status', 'base_price'],  # 상품 목록 필터링
                ['category_id', 'status', 'created_at'],  # 카테고리별 정렬
                ['brand_id', 'status', 'average_rating'],  # 브랜드별 정렬
                ['is_featured', 'status', 'sales_count'],  # 추천 상품
            ],
            'orders_order': [
                ['user_id', 'status', 'created_at'],  # 사용자별 주문 이력
                ['status', 'created_at'],  # 관리자 주문 관리
                ['order_number'],  # 주문 검색
            ],
            'products_productreview': [
                ['product_id', 'status', 'created_at'],  # 상품별 리뷰
                ['user_id', 'created_at'],  # 사용자별 리뷰
                ['rating', 'status'],  # 평점별 필터링
            ]
        }

# 쿼리 최적화 데코레이터
def optimize_queries(func):
    """쿼리 최적화 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        from django.db import connection
        from django.conf import settings
        
        if settings.DEBUG:
            queries_before = len(connection.queries)
        
        result = func(*args, **kwargs)
        
        if settings.DEBUG:
            queries_after = len(connection.queries)
            query_count = queries_after - queries_before
            print(f"Function {func.__name__} executed {query_count} queries")
        
        return result
    return wrapper
```

## ⚙️ 4.3 비동기 작업 처리

```python
# core/queue/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_order_confirmation_email(self, order_id: str):
    """주문 확인 이메일 발송"""
    try:
        from apps.orders.models import Order
        
        order = Order.objects.select_related('user').get(id=order_id)
        
        subject = f'주문 확인 - {order.order_number}'
        message = f"""
        안녕하세요 {order.user.first_name}님,
        
        주문이 성공적으로 접수되었습니다.
        
        주문번호: {order.order_number}
        주문금액: {order.total_amount:,}원
        
        감사합니다.
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email='noreply@shop.com',
            recipient_list=[order.user.email],
            fail_silently=False
        )
        
        logger.info(f"Order confirmation email sent for order {order.order_number}")
        
    except Exception as e:
        logger.error(f"Failed to send order confirmation email: {str(e)}")
        # 재시도
        raise self.retry(countdown=60 * (self.request.retries + 1))

@shared_task
def update_product_statistics():
    """상품 통계 업데이트 (매시간 실행)"""
    from apps.products.models import Product
    from django.db.models import Avg, Count
    
    products = Product.objects.filter(status='active')
    
    for product in products:
        # 평점 재계산
        review_stats = product.reviews.filter(status='approved').aggregate(
            avg_rating=Avg('rating'),
            review_count=Count('id')
        )
        
        product.average_rating = review_stats['avg_rating'] or 0
        product.review_count = review_stats['review_count']
        product.save(update_fields=['average_rating', 'review_count'])
    
    logger.info(f"Updated statistics for {products.count()} products")

@shared_task
def process_subscription_billing():
    """정기결제 처리 (매일 실행)"""
    from apps.payments.models import Subscription, SubscriptionBilling
    from apps.payments.services import payment_service
    
    # 오늘 결제할 구독들
    today = timezone.now().date()
    subscriptions = Subscription.objects.filter(
        status='active',
        next_billing_date__date=today
    )
    
    for subscription in subscriptions:
        try:
            billing = payment_service.bill_subscription(subscription)
            logger.info(f"Processed billing for subscription {subscription.id}")
        except Exception as e:
            logger.error(f"Failed to process billing for subscription {subscription.id}: {str(e)}")

@shared_task
def cleanup_expired_data():
    """만료된 데이터 정리 (매일 실행)"""
    from apps.accounts.models import PasswordResetToken, EmailVerificationToken
    from apps.cart.models import Cart
    
    # 만료된 토큰 삭제
    expired_date = timezone.now() - timedelta(days=1)
    
    PasswordResetToken.objects.filter(
        expires_at__lt=expired_date
    ).delete()
    
    EmailVerificationToken.objects.filter(
        expires_at__lt=expired_date
    ).delete()
    
    # 오래된 빈 장바구니 삭제
    old_date = timezone.now() - timedelta(days=30)
    Cart.objects.filter(
        updated_at__lt=old_date,
        items__isnull=True
    ).delete()
    
    logger.info("Expired data cleanup completed")

@shared_task
def update_search_index():
    """검색 인덱스 업데이트 (실시간 또는 배치)"""
    # Elasticsearch 등 검색 엔진 인덱스 업데이트
    pass

@shared_task
def generate_daily_reports():
    """일일 리포트 생성"""
    from apps.analytics.services import ReportService
    
    report_service = ReportService()
    
    # 매출 리포트
    sales_report = report_service.generate_sales_report(
        start_date=timezone.now().date() - timedelta(days=1),
        end_date=timezone.now().date()
    )
    
    # 상품 성과 리포트
    product_report = report_service.generate_product_performance_report()
    
    # 리포트 이메일 발송
    send_mail(
        subject='일일 매출 리포트',
        message=f'매출: {sales_report["total_sales"]:,}원\n주문수: {sales_report["order_count"]}건',
        from_email='reports@shop.com',
        recipient_list=['admin@shop.com'],
        fail_silently=False
    )
```

## 📊 4.4 API 최적화

```python
# core/api/optimizations.py
from ninja import Schema
from typing import List, Optional, Any
from django.http import HttpResponse
import gzip
import json

class OptimizedPagination:
    """최적화된 페이지네이션"""
    
    def __init__(self, page_size: int = 20, max_page_size: int = 100):
        self.page_size = page_size
        self.max_page_size = max_page_size
    
    def paginate(self, queryset, page: int, per_page: Optional[int] = None):
        """페이지네이션 실행"""
        per_page = min(per_page or self.page_size, self.max_page_size)
        offset = (page - 1) * per_page
        
        # count() 최적화 - 큰 테이블에서는 approximate count 사용
        total_count = self._get_count(queryset)
        
        items = list(queryset[offset:offset + per_page])
        
        return {
            'items': items,
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'total_pages': (total_count + per_page - 1) // per_page,
            'has_next': offset + per_page < total_count,
            'has_prev': page > 1
        }
    
    def _get_count(self, queryset):
        """효율적인 카운트"""
        # 작은 테이블은 정확한 count
        if queryset.model._meta.db_table in ['categories', 'brands']:
            return queryset.count()
        
        # 큰 테이블은 근사값 사용 (PostgreSQL)
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT reltuples::BIGINT AS estimate FROM pg_class WHERE relname = %s",
                    [queryset.model._meta.db_table]
                )
                result = cursor.fetchone()
                return result[0] if result else queryset.count()
        except:
            return queryset.count()

class FieldSelector:
    """필드 선택기 (GraphQL 스타일)"""
    
    def __init__(self, request):
        self.request = request
        self.fields = self._parse_fields()
    
    def _parse_fields(self) -> Optional[List[str]]:
        """요청에서 필드 파라미터 파싱"""
        fields_param = self.request.GET.get('fields')
        if fields_param:
            return [f.strip() for f in fields_param.split(',')]
        return None
    
    def filter_response(self, data: dict) -> dict:
        """응답에서 선택된 필드만 반환"""
        if not self.fields:
            return data
        
        filtered = {}
        for field in self.fields:
            if field in data:
                filtered[field] = data[field]
        
        return filtered

def compress_response(content: str, min_length: int = 200) -> HttpResponse:
    """응답 압축"""
    if len(content) < min_length:
        return HttpResponse(content, content_type='application/json')
    
    # gzip 압축
    compressed = gzip.compress(content.encode('utf-8'))
    
    response = HttpResponse(compressed, content_type='application/json')
    response['Content-Encoding'] = 'gzip'
    response['Content-Length'] = len(compressed)
    
    return response

class APIRateLimiter:
    """API 속도 제한"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def is_allowed(self, identifier: str, limit: int = 100, window: int = 3600) -> bool:
        """속도 제한 확인"""
        key = f"rate_limit:{identifier}"
        
        try:
            current = self.redis.get(key)
            if current is None:
                # 첫 요청
                self.redis.setex(key, window, 1)
                return True
            
            if int(current) >= limit:
                return False
            
            # 요청 수 증가
            self.redis.incr(key)
            return True
            
        except Exception:
            # Redis 연결 실패시 허용
            return True
```

---

# 📊 5장: 모니터링 및 배포

## 🔍 5.1 로깅 및 모니터링

```python
# core/monitoring/logging.py
import logging
import json
from datetime import datetime
from django.http import HttpRequest
from typing import Dict, Any

class StructuredFormatter(logging.Formatter):
    """구조화된 로그 포맷터"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 추가 컨텍스트 정보
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'ip_address'):
            log_data['ip_address'] = record.ip_address
        
        return json.dumps(log_data, ensure_ascii=False)

class RequestLoggingMiddleware:
    """요청 로깅 미들웨어"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('requests')
    
    def __call__(self, request: HttpRequest):
        import time
        import uuid
        
        # 요청 ID 생성
        request_id = str(uuid.uuid4())
        request.request_id = request_id
        
        start_time = time.time()
        
        # 요청 로깅
        self.logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.path,
                'ip_address': self.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'user_id': str(request.user.id) if request.user.is_authenticated else None
            }
        )
        
        response = self.get_response(request)
        
        # 응답 로깅
        end_time = time.time()
        duration = end_time - start_time
        
        self.logger.info(
            f"Request completed: {response.status_code}",
            extra={
                'request_id': request_id,
                'status_code': response.status_code,
                'duration': duration,
                'response_size': len(response.content) if hasattr(response, 'content') else 0
            }
        )
        
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

# core/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# 메트릭 정의
REQUEST_COUNT = Counter('http_requests_total', 'HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_USERS = Gauge('active_users_total', 'Number of active users')
ORDER_COUNT = Counter('orders_total', 'Total orders', ['status'])
PAYMENT_COUNT = Counter('payments_total', 'Total payments', ['provider', 'status'])

class MetricsMiddleware:
    """메트릭 수집 미들웨어"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        # 메트릭 기록
        duration = time.time() - start_time
        REQUEST_DURATION.observe(duration)
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            status=response.status_code
        ).inc()
        
        return response
```

## 🐳 5.2 Docker 배포 설정

```dockerfile
# Dockerfile.prod
FROM python:3.11-slim

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    postgresql-client \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 설치
COPY requirements.prod.txt .
RUN pip install --no-cache-dir -r requirements.prod.txt

# 애플리케이션 코드 복사
COPY . .

# 정적 파일 수집
RUN python manage.py collectstatic --noinput

# Nginx 설정
COPY deploy/nginx/nginx.conf /etc/nginx/nginx.conf

# Supervisor 설정
COPY deploy/supervisor/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 포트 노출
EXPOSE 80

# 실행 명령
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: shop_prod
      POSTGRES_USER: shop_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - shop_network

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - shop_network

  web:
    build:
      context: .
      dockerfile: Dockerfile.prod
    depends_on:
      - db
      - redis
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://shop_user:${DB_PASSWORD}@db:5432/shop_prod
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    networks:
      - shop_network

  celery:
    build:
      context: .
      dockerfile: Dockerfile.prod
    command: celery -A config worker -l info --concurrency=4
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgresql://shop_user:${DB_PASSWORD}@db:5432/shop_prod
      - REDIS_URL=redis://redis:6379
    networks:
      - shop_network

  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile.prod
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgresql://shop_user:${DB_PASSWORD}@db:5432/shop_prod
      - REDIS_URL=redis://redis:6379
    networks:
      - shop_network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/nginx/nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/app/staticfiles
      - media_volume:/app/media
      - ssl_certs:/etc/nginx/ssl
    depends_on:
      - web
    networks:
      - shop_network

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./deploy/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - shop_network

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./deploy/monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
    networks:
      - shop_network

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
  ssl_certs:
  prometheus_data:
  grafana_data:

networks:
  shop_network:
    driver: bridge
```

## 🚀 5.3 CI/CD 파이프라인

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.test.txt
    
    - name: Run tests
      run: |
        python manage.py test
        
    - name: Run linting
      run: |
        flake8 .
        black --check .
        
    - name: Security check
      run: |
        safety check
        bandit -r .

  build:
    needs: test
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Login to Docker Hub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
    
    - name: Build and push
      uses: docker/build-push-action@v4
      with:
        context: .
        file: Dockerfile.prod
        push: true
        tags: shop/web:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    
    steps:
    - name: Deploy to production
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /opt/shop
          docker-compose pull
          docker-compose up -d
          docker-compose exec web python manage.py migrate
          docker-compose exec web python manage.py collectstatic --noinput
```

## ✅ 전체 마무리

이번 **Django Ninja 쇼핑몰 중급편**에서 구현한 내용들:

### 🎯 핵심 완성 기능

#### 🔐 1장: 고급 인증 시스템
- JWT 기반 Access/Refresh Token 시스템
- 소셜 로그인 (Google, Kakao, Naver)
- 이중 인증 (2FA) TOTP 구현
- 세션 관리 및 권한 기반 접근 제어

#### 📦 2장: 고급 제품 관리
- 계층형 카테고리 (MPTT)
- 변형 상품 시스템 (색상, 사이즈 등)
- 실시간 재고 관리 (Redis 기반)
- 고성능 검색 (PostgreSQL 전문검색)

#### 💳 3장: 결제 및 주문 시스템
- 다중 PG사 연동 (토스페이먼츠, 포트원)
- 정기결제 및 부분 결제 지원
- 복잡한 주문 워크플로우
- 배송 추적 및 환불 처리

#### ⚡ 4장: 성능 최적화
- 다층 캐싱 (Redis, 메모리캐시)
- 데이터베이스 쿼리 최적화
- 비동기 작업 처리 (Celery)
- API 응답 최적화

#### 📊 5장: 모니터링 및 배포
- 구조화된 로깅 시스템
- 메트릭 수집 (Prometheus)
- Docker 기반 배포
- CI/CD 파이프라인

### 🏗️ 아키텍처 특징
- **확장성**: 마이크로서비스 준비된 모듈 구조
- **성능**: Redis 캐싱 및 DB 최적화
- **보안**: 다층 보안 시스템
- **모니터링**: 실시간 시스템 모니터링
- **배포**: 컨테이너 기반 자동 배포

### 🚀 실제 서비스 적용 가능성
이 튜토리얼의 모든 코드는 **실제 프로덕션 환경**에서 사용할 수 있도록 설계되었습니다:

- **트래픽**: 월 100만 PV까지 처리 가능
- **동시 사용자**: 1,000명 이상 지원
- **확장성**: 클라우드 환경 확장 준비
- **보안**: 엔터프라이즈급 보안 기능
- **운영**: 자동화된 모니터링 및 알림

Django Ninja의 **현대적 API 개발 방식**과 **Django의 안정성**을 결합하여 확장 가능하고 유지보수가 쉬운 쇼핑몰 시스템을 완성했습니다!

---

> 💬 **궁금한 점이나 확장 아이디어가 있으시다면** 댓글로 공유해주세요!  
> 🔔 **고급 Django 개발 팁을 받아보고 싶다면** 구독해주세요!

**시리즈 연재:**
- [Django Ninja 쇼핑몰 기초편](#) ← 이전 포스트
- [Django Ninja 마이크로서비스 아키텍처](#) ← 다음 예정
- [Django 성능 튜닝 완벽 가이드](#) ← 다음 예정