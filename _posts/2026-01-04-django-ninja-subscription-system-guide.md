---
layout: post
title: "Django Ninja로 구독 시스템 완벽 구축하기"
date: 2026-01-04 09:00:00 +0900
categories: [Django, Backend, Subscription]
tags: [django-ninja, subscription, saas, payment, stripe, recurring-billing]
description: "Django Ninja로 SaaS 구독 시스템을 처음부터 끝까지 구축하는 실전 가이드. 구독 플랜 설계부터 결제 처리, 업그레이드/다운그레이드까지 실무에서 바로 사용 가능한 완전한 구독 시스템을 만들어봅니다."
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-01-04-django-ninja-subscription-system-guide.webp"
---

## 1. 서론

### 1.1 구독 시스템이란?

구독(Subscription) 시스템은 사용자가 서비스에 정기적으로 비용을 지불하고 지속적으로 이용할 수 있도록 하는 비즈니스 모델입니다. Netflix, Spotify, GitHub 등 우리가 매일 사용하는 많은 서비스들이 구독 모델을 사용하고 있습니다.

**구독 시스템의 핵심 요소:**

- 🎯 **정기 결제 (Recurring Billing)**: 월간/연간 등 일정 주기로 자동 결제
- 📊 **플랜 관리**: 베이직, 프로, 엔터프라이즈 등 다양한 요금제
- 🔄 **업그레이드/다운그레이드**: 플랜 변경 기능
- 💳 **결제 수단 관리**: 카드 등록, 변경, 삭제
- ⏸️ **구독 일시정지/취소**: 사용자가 자유롭게 구독 관리
- 🎁 **무료 체험 (Trial)**: 일정 기간 무료 사용
- 💰 **환불 및 크레딧**: 중도 해지 시 남은 기간 환불

**구독 모델의 장점:**

**비즈니스 관점:**
- 예측 가능한 수익 (MRR - Monthly Recurring Revenue)
- 고객 생애 가치(LTV) 증대
- 안정적인 현금 흐름
- 장기적인 고객 관계 구축

**사용자 관점:**
- 초기 비용 부담 감소
- 필요할 때만 사용하고 취소 가능
- 최신 기능 자동 업데이트
- 유연한 플랜 변경

### 1.2 왜 Django Ninja인가?

Django Ninja는 구독 시스템 구축에 매우 적합한 프레임워크입니다.

**Django Ninja의 장점:**

```python
# 직관적이고 간결한 코드
@router.post("/subscriptions/create")
def create_subscription(request, data: SubscriptionCreateSchema):
    # 타입 안정성과 자동 검증
    subscription = subscription_service.create(
        user=request.auth,
        plan_id=data.plan_id
    )
    return {"subscription_id": subscription.id}
```

**핵심 특징:**

1. **FastAPI 스타일의 간결함**
   - 데코레이터 기반 라우팅
   - 최소한의 보일러플레이트 코드
   - 빠른 개발 속도

2. **Pydantic 통합**
   - 강력한 타입 체킹
   - 자동 데이터 검증
   - IDE 자동완성 지원

3. **자동 API 문서화**
   - OpenAPI (Swagger) 자동 생성
   - 실시간 API 테스트 가능
   - 프론트엔드 개발자와 협업 용이

4. **Django의 강력함**
   - Django ORM 활용
   - 인증/권한 시스템
   - Admin 패널
   - 풍부한 생태계

**기존 Django REST Framework와 비교:**

| 특징 | Django Ninja | DRF |
|------|-------------|-----|
| 코드 간결성 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 타입 안정성 | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| 학습 곡선 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 성능 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 문서화 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

### 1.3 이 가이드에서 만들 구독 시스템

이 튜토리얼에서는 **실제 SaaS 서비스에서 사용 가능한 완전한 구독 시스템**을 구축합니다.

**구현할 기능:**

✅ **구독 플랜 관리**
```
- Basic Plan: $9.99/month
- Pro Plan: $29.99/month
- Enterprise Plan: $99.99/month
```

✅ **구독 생명주기**
- 구독 생성 (14일 무료 체험)
- 구독 활성화
- 구독 갱신
- 구독 취소
- 구독 만료

✅ **플랜 변경**
- 업그레이드 (즉시 적용)
- 다운그레이드 (다음 주기부터 적용)
- 비례 배분(Proration) 처리

✅ **결제 처리**
- Stripe 연동
- 자동 결제
- 결제 실패 처리
- 재시도 로직

✅ **사용자 관리**
- 구독 상태 확인
- 결제 내역 조회
- 결제 수단 관리
- 영수증 발급

✅ **관리자 기능**
- 구독 통계 대시보드
- 수익 분석
- 이탈 고객 관리
- 할인 쿠폰 적용

**최종 API 엔드포인트:**

```bash
# 플랜 관리
GET    /api/plans/              # 플랜 목록
GET    /api/plans/{id}/         # 플랜 상세

# 구독 관리
POST   /api/subscriptions/create/           # 구독 생성
GET    /api/subscriptions/me/               # 내 구독 조회
POST   /api/subscriptions/cancel/           # 구독 취소
POST   /api/subscriptions/reactivate/       # 구독 재활성화
POST   /api/subscriptions/change-plan/      # 플랜 변경

# 결제 관리
GET    /api/payments/history/               # 결제 내역
POST   /api/payments/update-card/           # 카드 변경
GET    /api/invoices/{id}/                  # 영수증 조회

# 웹훅
POST   /api/webhooks/stripe/                # Stripe 웹훅
```

**프로젝트 구조:**

```
subscription_service/
├── apps/
│   ├── subscriptions/
│   │   ├── models.py           # 구독, 플랜 모델
│   │   ├── schemas.py          # Pydantic 스키마
│   │   ├── services.py         # 비즈니스 로직
│   │   ├── api.py              # API 엔드포인트
│   │   └── tasks.py            # 백그라운드 작업
│   └── payments/
│       ├── models.py           # 결제 모델
│       ├── stripe_client.py    # Stripe 연동
│       └── webhooks.py         # 웹훅 처리
```

### 1.4 사전 준비사항

**필요한 지식:**
- Python 기초 (중급)
- Django 기본 개념
- REST API 이해
- 데이터베이스 기초

**개발 환경:**
- Python 3.10+
- PostgreSQL (권장) 또는 SQLite
- Stripe 계정 (무료)
- Git

**설치할 도구:**
```bash
# Python 가상환경
python -m venv venv
source venv/bin/activate

# 필수 패키지
pip install django django-ninja stripe python-dotenv
```

이제 본격적으로 구독 시스템을 만들어보겠습니다!

## 2. 프로젝트 설정

### 2.1 Django 프로젝트 생성

먼저 깨끗한 Django 프로젝트를 생성합니다.

**1) 가상환경 및 프로젝트 생성**

```bash
# 프로젝트 디렉토리 생성
mkdir subscription_service
cd subscription_service

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Django 설치
pip install django

# Django 프로젝트 생성
django-admin startproject config .

# 앱 생성
python manage.py startapp subscriptions
python manage.py startapp payments

# 디렉토리 구조 정리
mkdir -p subscriptions/services
mkdir -p payments/services
```

**2) 필수 패키지 설치**

```bash
# 핵심 패키지
pip install django-ninja==1.1.0
pip install stripe==7.9.0
pip install python-dotenv==1.0.0

# 데이터베이스 (PostgreSQL 권장)
pip install psycopg2-binary==2.9.9

# 유틸리티
pip install python-dateutil==2.8.2

# 개발 도구
pip install pytest pytest-django faker

# requirements.txt 생성
pip freeze > requirements.txt
```

**3) requirements.txt 최종본**

```txt
Django==5.0.0
django-ninja==1.1.0
stripe==7.9.0
python-dotenv==1.0.0
psycopg2-binary==2.9.9
python-dateutil==2.8.2

# 타입 체킹
pydantic==2.5.0
pydantic-settings==2.1.0

# 개발 도구
pytest==7.4.3
pytest-django==4.7.0
faker==21.0.0
```

### 2.2 환경 변수 설정

보안과 유연성을 위해 환경 변수를 사용합니다.

**1) .env 파일 생성**

```bash
# .env
DEBUG=True
SECRET_KEY=your-super-secret-django-key-here-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1

# 데이터베이스 (개발 환경 - SQLite)
DATABASE_URL=sqlite:///db.sqlite3

# 데이터베이스 (프로덕션 - PostgreSQL)
# DATABASE_URL=postgresql://user:password@localhost:5432/subscription_db

# Stripe 설정 (테스트 모드)
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key
STRIPE_SECRET_KEY=sk_test_your_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# 애플리케이션 설정
DEFAULT_CURRENCY=usd
TRIAL_PERIOD_DAYS=14
```

**2) .env 파일 보안 설정**

```bash
# .gitignore 파일에 추가
echo ".env" >> .gitignore
echo "*.pyc" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "db.sqlite3" >> .gitignore
echo "venv/" >> .gitignore
```

⚠️ **중요**: `.env` 파일은 절대 Git에 커밋하지 마세요!

### 2.3 Django 설정 (settings.py)

**config/settings.py** 파일을 수정합니다.

```python
# config/settings.py
from pathlib import Path
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# 보안 설정
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')

# 애플리케이션 등록
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'ninja',
    
    # Local apps
    'subscriptions',
    'payments',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# 데이터베이스 설정
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'subscription_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# 개발 환경에서는 SQLite 사용 가능
if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# 비밀번호 검증
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# 국제화
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# 정적 파일
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# 미디어 파일
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 기본 Primary Key 타입
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Stripe 설정
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# 구독 시스템 설정
DEFAULT_CURRENCY = os.getenv('DEFAULT_CURRENCY', 'usd')
TRIAL_PERIOD_DAYS = int(os.getenv('TRIAL_PERIOD_DAYS', '14'))

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'subscriptions': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'payments': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### 2.4 URL 설정

Django Ninja API를 설정합니다.

```python
# config/urls.py
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

# API 인스턴스 생성
api = NinjaAPI(
    title="Subscription Service API",
    version="1.0.0",
    description="Django Ninja로 구현한 SaaS 구독 시스템",
    docs_url="/api/docs",  # Swagger 문서
)

# 라우터는 나중에 추가
# from subscriptions.api import router as subscriptions_router
# api.add_router("/subscriptions/", subscriptions_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
```

### 2.5 Stripe 초기화

Stripe SDK를 초기화합니다.

```python
# payments/__init__.py
import stripe
from django.conf import settings

# Stripe API 키 설정
stripe.api_key = settings.STRIPE_SECRET_KEY

# API 버전 고정 (선택사항, 권장)
stripe.api_version = '2023-10-16'
```

### 2.6 데이터베이스 마이그레이션

```bash
# 초기 마이그레이션 실행
python manage.py makemigrations
python manage.py migrate

# 슈퍼유저 생성
python manage.py createsuperuser
# Username: admin
# Email: admin@example.com
# Password: (강력한 비밀번호 입력)

# 서버 실행 테스트
python manage.py runserver
```

서버가 성공적으로 실행되면 브라우저에서 다음 URL들을 확인합니다:

- http://localhost:8000/admin - Django Admin
- http://localhost:8000/api/docs - API 문서 (아직 비어있음)

### 2.7 프로젝트 구조 확인

최종 프로젝트 구조입니다:

```
subscription_service/
├── manage.py
├── requirements.txt
├── .env
├── .gitignore
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── subscriptions/
│   ├── __init__.py
│   ├── models.py          # 구독 모델 (다음 섹션)
│   ├── schemas.py         # Pydantic 스키마
│   ├── api.py             # API 엔드포인트
│   ├── admin.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── subscription_service.py
│   └── tests/
│       └── __init__.py
├── payments/
│   ├── __init__.py
│   ├── models.py          # 결제 모델
│   ├── stripe_client.py   # Stripe 래퍼
│   └── webhooks.py        # 웹훅 처리
└── db.sqlite3
```

기본 설정이 완료되었습니다! 다음 섹션에서는 구독 시스템의 핵심인 데이터 모델을 설계하겠습니다.

## 3. 구독 모델 설계

구독 시스템의 데이터 모델을 설계합니다. 총 4개의 주요 모델이 필요합니다.

### 3.1 구독 플랜 (Plan) 모델

구독 플랜은 서비스에서 제공하는 요금제를 정의합니다.

```python
# subscriptions/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class Plan(models.Model):
    """구독 플랜 모델"""
    
    class Interval(models.TextChoices):
        MONTH = 'month', '월간'
        YEAR = 'year', '연간'
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # 플랜 정보
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    
    # 가격 정보
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='usd')
    interval = models.CharField(
        max_length=20,
        choices=Interval.choices,
        default=Interval.MONTH
    )
    interval_count = models.IntegerField(default=1)  # 매 N개월/년
    
    # Stripe 연동
    stripe_product_id = models.CharField(max_length=255, blank=True)
    stripe_price_id = models.CharField(max_length=255, blank=True)
    
    # 기능 제한
    features = models.JSONField(default=dict)
    # 예: {
    #   "max_projects": 10,
    #   "max_storage_gb": 100,
    #   "api_calls_per_month": 10000,
    #   "support_level": "email"
    # }
    
    # 무료 체험
    trial_period_days = models.IntegerField(default=0)
    
    # 상태
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    # 정렬 순서
    sort_order = models.IntegerField(default=0)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscription_plans'
        ordering = ['sort_order', 'price']
        verbose_name = '구독 플랜'
        verbose_name_plural = '구독 플랜'
    
    def __str__(self):
        return f"{self.name} - ${self.price}/{self.get_interval_display()}"
    
    @property
    def monthly_price(self):
        """월 환산 가격"""
        if self.interval == self.Interval.YEAR:
            return self.price / 12
        return self.price
    
    @property
    def yearly_price(self):
        """연 환산 가격"""
        if self.interval == self.Interval.MONTH:
            return self.price * 12
        return self.price
```

### 3.2 구독 (Subscription) 모델

사용자의 실제 구독 정보를 저장합니다.

```python
# subscriptions/models.py (계속)

class Subscription(models.Model):
    """구독 모델"""
    
    class Status(models.TextChoices):
        TRIALING = 'trialing', '체험중'
        ACTIVE = 'active', '활성'
        PAST_DUE = 'past_due', '연체'
        CANCELED = 'canceled', '취소됨'
        UNPAID = 'unpaid', '미납'
        INCOMPLETE = 'incomplete', '미완료'
        INCOMPLETE_EXPIRED = 'incomplete_expired', '만료됨'
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # 사용자 및 플랜
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    
    # Stripe 연동
    stripe_subscription_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True
    )
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    
    # 구독 상태
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INCOMPLETE
    )
    
    # 기간 정보
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    
    # 체험 기간
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    
    # 취소 정보
    cancel_at_period_end = models.BooleanField(default=False)
    cancel_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    
    # 종료 정보
    ended_at = models.DateTimeField(null=True, blank=True)
    
    # 메타데이터
    metadata = models.JSONField(default=dict, blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscriptions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['current_period_end']),
        ]
        verbose_name = '구독'
        verbose_name_plural = '구독'
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.get_status_display()})"
    
    @property
    def is_active(self):
        """활성 상태 여부"""
        return self.status in [self.Status.ACTIVE, self.Status.TRIALING]
    
    @property
    def is_trialing(self):
        """체험 중인지 확인"""
        return self.status == self.Status.TRIALING
    
    @property
    def is_canceled(self):
        """취소되었는지 확인"""
        return self.cancel_at_period_end or self.status == self.Status.CANCELED
    
    @property
    def days_until_renewal(self):
        """갱신까지 남은 일수"""
        if self.current_period_end:
            delta = self.current_period_end - timezone.now()
            return max(0, delta.days)
        return None
    
    @property
    def trial_days_remaining(self):
        """체험 기간 남은 일수"""
        if self.trial_end and self.is_trialing:
            delta = self.trial_end - timezone.now()
            return max(0, delta.days)
        return 0
    
    def cancel(self, at_period_end=True):
        """구독 취소"""
        self.cancel_at_period_end = at_period_end
        if not at_period_end:
            self.status = self.Status.CANCELED
            self.ended_at = timezone.now()
        self.canceled_at = timezone.now()
        self.save()
    
    def reactivate(self):
        """구독 재활성화"""
        if self.cancel_at_period_end:
            self.cancel_at_period_end = False
            self.cancel_at = None
            self.canceled_at = None
            self.save()
```

### 3.3 구독 히스토리 모델

구독 변경 이력을 추적합니다.

```python
# subscriptions/models.py (계속)

class SubscriptionHistory(models.Model):
    """구독 이력 모델"""
    
    class EventType(models.TextChoices):
        CREATED = 'created', '생성'
        ACTIVATED = 'activated', '활성화'
        CANCELED = 'canceled', '취소'
        REACTIVATED = 'reactivated', '재활성화'
        PLAN_CHANGED = 'plan_changed', '플랜 변경'
        RENEWED = 'renewed', '갱신'
        EXPIRED = 'expired', '만료'
        PAYMENT_FAILED = 'payment_failed', '결제 실패'
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='history'
    )
    
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices
    )
    
    # 변경 전/후 데이터
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    
    # 추가 정보
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'subscription_history'
        ordering = ['-created_at']
        verbose_name = '구독 이력'
        verbose_name_plural = '구독 이력'
    
    def __str__(self):
        return f"{self.subscription.user.username} - {self.get_event_type_display()}"
```

### 3.4 사용량 추적 모델

사용량 기반 과금을 위한 모델입니다 (선택사항).

```python
# subscriptions/models.py (계속)

class UsageRecord(models.Model):
    """사용량 기록 모델"""
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='usage_records'
    )
    
    # 사용량 정보
    metric = models.CharField(max_length=100)  # api_calls, storage_gb 등
    quantity = models.IntegerField()
    
    # 기간
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # 메타데이터
    metadata = models.JSONField(default=dict, blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'usage_records'
        ordering = ['-period_start']
        indexes = [
            models.Index(fields=['subscription', 'metric']),
            models.Index(fields=['period_start', 'period_end']),
        ]
        verbose_name = '사용량 기록'
        verbose_name_plural = '사용량 기록'
    
    def __str__(self):
        return f"{self.subscription.user.username} - {self.metric}: {self.quantity}"
```

### 3.5 결제 모델

```python
# payments/models.py
from django.db import models
from django.contrib.auth.models import User
from subscriptions.models import Subscription
import uuid


class Payment(models.Model):
    """결제 모델"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', '대기중'
        PROCESSING = 'processing', '처리중'
        SUCCEEDED = 'succeeded', '성공'
        FAILED = 'failed', '실패'
        REFUNDED = 'refunded', '환불'
        PARTIALLY_REFUNDED = 'partially_refunded', '부분환불'
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # 사용자 및 구독
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payments'
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    
    # Stripe 정보
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True
    )
    stripe_charge_id = models.CharField(max_length=255, blank=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True)
    
    # 결제 정보
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='usd')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # 결제 수단
    payment_method_type = models.CharField(max_length=50, blank=True)
    card_brand = models.CharField(max_length=50, blank=True)
    card_last4 = models.CharField(max_length=4, blank=True)
    
    # 설명
    description = models.TextField(blank=True)
    
    # 환불 정보
    refunded_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    # 에러 정보
    error_message = models.TextField(blank=True)
    
    # 메타데이터
    metadata = models.JSONField(default=dict, blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]
        verbose_name = '결제'
        verbose_name_plural = '결제'
    
    def __str__(self):
        return f"{self.user.username if self.user else 'Unknown'} - ${self.amount}"
    
    @property
    def is_refundable(self):
        """환불 가능 여부"""
        return (
            self.status == self.Status.SUCCEEDED and
            self.refunded_amount < self.amount
        )
```

### 3.6 마이그레이션 실행

모델을 데이터베이스에 적용합니다.

```bash
# 마이그레이션 파일 생성
python manage.py makemigrations subscriptions
python manage.py makemigrations payments

# 마이그레이션 적용
python manage.py migrate

# 출력 예시:
# Applying subscriptions.0001_initial... OK
# Applying payments.0001_initial... OK
```

### 3.7 Admin 패널 설정

Django Admin에서 모델을 관리할 수 있도록 설정합니다.

```python
# subscriptions/admin.py
from django.contrib import admin
from .models import Plan, Subscription, SubscriptionHistory, UsageRecord


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'price', 'currency', 'interval',
        'is_active', 'is_featured', 'created_at'
    ]
    list_filter = ['is_active', 'is_featured', 'interval']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['sort_order', 'price']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'plan', 'status',
        'current_period_end', 'cancel_at_period_end', 'created_at'
    ]
    list_filter = ['status', 'cancel_at_period_end', 'plan']
    search_fields = ['user__username', 'user__email', 'stripe_subscription_id']
    readonly_fields = [
        'stripe_subscription_id', 'stripe_customer_id',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'


@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'event_type', 'created_at']
    list_filter = ['event_type', 'created_at']
    readonly_fields = ['subscription', 'event_type', 'old_data', 'new_data', 'created_at']
    date_hierarchy = 'created_at'


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'metric', 'quantity', 'period_start', 'period_end']
    list_filter = ['metric', 'period_start']
    search_fields = ['subscription__user__username']
    date_hierarchy = 'period_start'
```

```python
# payments/admin.py
from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'amount', 'currency', 'status',
        'payment_method_type', 'created_at'
    ]
    list_filter = ['status', 'currency', 'payment_method_type']
    search_fields = [
        'user__username', 'user__email',
        'stripe_payment_intent_id', 'stripe_charge_id'
    ]
    readonly_fields = [
        'stripe_payment_intent_id', 'stripe_charge_id',
        'stripe_invoice_id', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'
```

### 3.8 샘플 데이터 생성

테스트를 위한 샘플 플랜을 생성합니다.

```python
# subscriptions/management/commands/create_sample_plans.py
from django.core.management.base import BaseCommand
from subscriptions.models import Plan


class Command(BaseCommand):
    help = '샘플 구독 플랜 생성'

    def handle(self, *args, **options):
        plans_data = [
            {
                'name': 'Basic',
                'slug': 'basic',
                'description': '개인 사용자를 위한 기본 플랜',
                'price': 9.99,
                'interval': Plan.Interval.MONTH,
                'features': {
                    'max_projects': 3,
                    'max_storage_gb': 5,
                    'api_calls_per_month': 1000,
                    'support_level': 'email',
                },
                'trial_period_days': 14,
                'sort_order': 1,
            },
            {
                'name': 'Pro',
                'slug': 'pro',
                'description': '전문가를 위한 프로 플랜',
                'price': 29.99,
                'interval': Plan.Interval.MONTH,
                'features': {
                    'max_projects': 10,
                    'max_storage_gb': 50,
                    'api_calls_per_month': 10000,
                    'support_level': 'priority',
                },
                'trial_period_days': 14,
                'is_featured': True,
                'sort_order': 2,
            },
            {
                'name': 'Enterprise',
                'slug': 'enterprise',
                'description': '기업을 위한 무제한 플랜',
                'price': 99.99,
                'interval': Plan.Interval.MONTH,
                'features': {
                    'max_projects': -1,  # 무제한
                    'max_storage_gb': -1,
                    'api_calls_per_month': -1,
                    'support_level': '24/7',
                },
                'trial_period_days': 30,
                'sort_order': 3,
            },
        ]

        for plan_data in plans_data:
            plan, created = Plan.objects.get_or_create(
                slug=plan_data['slug'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {plan.name} 플랜 생성 완료')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'- {plan.name} 플랜 이미 존재')
                )
```

```bash
# management 디렉토리 생성
mkdir -p subscriptions/management/commands
touch subscriptions/management/__init__.py
touch subscriptions/management/commands/__init__.py

# 샘플 플랜 생성
python manage.py create_sample_plans
```

데이터 모델 설계가 완료되었습니다! 다음 섹션에서는 이 모델을 활용한 API를 구현하겠습니다.

## 4. Pydantic 스키마 정의

Django Ninja는 Pydantic을 사용하여 데이터를 검증하고 직렬화합니다. API 요청/응답 스키마를 정의합니다.

### 4.1 플랜 스키마

```python
# subscriptions/schemas.py
from pydantic import BaseModel, Field, UUID4
from typing import Optional, Dict, List
from decimal import Decimal
from datetime import datetime


class PlanSchema(BaseModel):
    """플랜 응답 스키마"""
    id: UUID4
    name: str
    slug: str
    description: str
    price: Decimal
    currency: str
    interval: str
    interval_count: int
    features: Dict
    trial_period_days: int
    is_active: bool
    is_featured: bool
    
    class Config:
        from_attributes = True  # Pydantic v2
        # orm_mode = True  # Pydantic v1


class PlanListSchema(BaseModel):
    """플랜 목록 응답"""
    plans: List[PlanSchema]
    count: int
```

### 4.2 구독 스키마

```python
# subscriptions/schemas.py (계속)

class SubscriptionCreateSchema(BaseModel):
    """구독 생성 요청"""
    plan_id: UUID4 = Field(..., description="플랜 ID")
    payment_method_id: Optional[str] = Field(
        None,
        description="Stripe Payment Method ID"
    )


class SubscriptionSchema(BaseModel):
    """구독 응답 스키마"""
    id: UUID4
    user_id: int
    plan: PlanSchema
    status: str
    current_period_start: datetime
    current_period_end: datetime
    trial_start: Optional[datetime]
    trial_end: Optional[datetime]
    cancel_at_period_end: bool
    canceled_at: Optional[datetime]
    is_active: bool
    is_trialing: bool
    days_until_renewal: Optional[int]
    
    class Config:
        from_attributes = True


class SubscriptionCancelSchema(BaseModel):
    """구독 취소 요청"""
    cancel_immediately: bool = Field(
        False,
        description="즉시 취소 여부 (False=기간 종료 시)"
    )
    reason: Optional[str] = Field(None, description="취소 사유")


class SubscriptionChangePlanSchema(BaseModel):
    """플랜 변경 요청"""
    new_plan_id: UUID4 = Field(..., description="새 플랜 ID")
    proration_behavior: str = Field(
        'create_prorations',
        description="비례 배분 방식 (create_prorations|none)"
    )
```

### 4.3 결제 스키마

```python
# payments/schemas.py
from pydantic import BaseModel, Field, UUID4
from typing import Optional
from decimal import Decimal
from datetime import datetime


class PaymentSchema(BaseModel):
    """결제 응답 스키마"""
    id: UUID4
    amount: Decimal
    currency: str
    status: str
    payment_method_type: Optional[str]
    card_brand: Optional[str]
    card_last4: Optional[str]
    description: str
    created_at: datetime
    paid_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class PaymentListSchema(BaseModel):
    """결제 목록 응답"""
    payments: list[PaymentSchema]
    count: int
```

## 5. 구독 서비스 로직 구현

비즈니스 로직을 서비스 레이어로 분리합니다.

### 5.1 Stripe 클라이언트 래퍼

```python
# payments/stripe_client.py
import stripe
from django.conf import settings
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Stripe API 래퍼"""
    
    @staticmethod
    def create_customer(email: str, name: Optional[str] = None) -> stripe.Customer:
        """Stripe 고객 생성"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
            )
            logger.info(f"Stripe 고객 생성: {customer.id}")
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"고객 생성 실패: {str(e)}")
            raise
    
    @staticmethod
    def create_subscription(
        customer_id: str,
        price_id: str,
        trial_period_days: Optional[int] = None,
        payment_method: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> stripe.Subscription:
        """Stripe 구독 생성"""
        try:
            params = {
                'customer': customer_id,
                'items': [{'price': price_id}],
                'metadata': metadata or {},
            }
            
            if trial_period_days and trial_period_days > 0:
                params['trial_period_days'] = trial_period_days
            
            if payment_method:
                params['default_payment_method'] = payment_method
            
            subscription = stripe.Subscription.create(**params)
            logger.info(f"Stripe 구독 생성: {subscription.id}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"구독 생성 실패: {str(e)}")
            raise
    
    @staticmethod
    def cancel_subscription(
        subscription_id: str,
        cancel_at_period_end: bool = True
    ) -> stripe.Subscription:
        """Stripe 구독 취소"""
        try:
            if cancel_at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)
            
            logger.info(f"Stripe 구독 취소: {subscription_id}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"구독 취소 실패: {str(e)}")
            raise
    
    @staticmethod
    def update_subscription(
        subscription_id: str,
        new_price_id: str,
        proration_behavior: str = 'create_prorations'
    ) -> stripe.Subscription:
        """Stripe 구독 업데이트"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            subscription = stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': subscription['items']['data'][0].id,
                    'price': new_price_id,
                }],
                proration_behavior=proration_behavior
            )
            
            logger.info(f"Stripe 구독 업데이트: {subscription_id}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"구독 업데이트 실패: {str(e)}")
            raise
    
    @staticmethod
    def create_product(name: str, description: str = "") -> stripe.Product:
        """Stripe 상품 생성"""
        try:
            product = stripe.Product.create(
                name=name,
                description=description,
            )
            logger.info(f"Stripe 상품 생성: {product.id}")
            return product
        except stripe.error.StripeError as e:
            logger.error(f"상품 생성 실패: {str(e)}")
            raise
    
    @staticmethod
    def create_price(
        product_id: str,
        amount: int,  # 센트 단위
        currency: str = 'usd',
        interval: str = 'month',
        interval_count: int = 1
    ) -> stripe.Price:
        """Stripe 가격 생성"""
        try:
            price = stripe.Price.create(
                product=product_id,
                unit_amount=amount,
                currency=currency,
                recurring={
                    'interval': interval,
                    'interval_count': interval_count,
                }
            )
            logger.info(f"Stripe 가격 생성: {price.id}")
            return price
        except stripe.error.StripeError as e:
            logger.error(f"가격 생성 실패: {str(e)}")
            raise
```

### 5.2 구독 서비스

```python
# subscriptions/services/subscription_service.py
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from subscriptions.models import Plan, Subscription, SubscriptionHistory
from payments.stripe_client import StripeService
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SubscriptionService:
    """구독 비즈니스 로직"""
    
    def __init__(self):
        self.stripe = StripeService()
    
    @transaction.atomic
    def create_subscription(
        self,
        user: User,
        plan: Plan,
        payment_method_id: Optional[str] = None
    ) -> Subscription:
        """
        구독 생성
        
        Args:
            user: 사용자
            plan: 구독 플랜
            payment_method_id: Stripe Payment Method ID
            
        Returns:
            생성된 구독
        """
        # 1. 기존 활성 구독 확인
        existing_subscription = Subscription.objects.filter(
            user=user,
            status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING]
        ).first()
        
        if existing_subscription:
            raise ValueError("이미 활성 구독이 있습니다.")
        
        # 2. Stripe 고객 확인 또는 생성
        stripe_customer_id = self._get_or_create_stripe_customer(user)
        
        # 3. Stripe 구독 생성
        stripe_subscription = self.stripe.create_subscription(
            customer_id=stripe_customer_id,
            price_id=plan.stripe_price_id,
            trial_period_days=plan.trial_period_days,
            payment_method=payment_method_id,
            metadata={
                'user_id': user.id,
                'plan_id': str(plan.id),
            }
        )
        
        # 4. 로컬 구독 생성
        subscription = Subscription.objects.create(
            user=user,
            plan=plan,
            stripe_subscription_id=stripe_subscription.id,
            stripe_customer_id=stripe_customer_id,
            status=stripe_subscription.status,
            current_period_start=timezone.datetime.fromtimestamp(
                stripe_subscription.current_period_start,
                tz=timezone.utc
            ),
            current_period_end=timezone.datetime.fromtimestamp(
                stripe_subscription.current_period_end,
                tz=timezone.utc
            ),
            trial_start=timezone.datetime.fromtimestamp(
                stripe_subscription.trial_start,
                tz=timezone.utc
            ) if stripe_subscription.trial_start else None,
            trial_end=timezone.datetime.fromtimestamp(
                stripe_subscription.trial_end,
                tz=timezone.utc
            ) if stripe_subscription.trial_end else None,
        )
        
        # 5. 이력 기록
        SubscriptionHistory.objects.create(
            subscription=subscription,
            event_type=SubscriptionHistory.EventType.CREATED,
            new_data={'plan': plan.name, 'status': subscription.status}
        )
        
        logger.info(f"구독 생성 완료: {subscription.id}")
        return subscription
    
    @transaction.atomic
    def cancel_subscription(
        self,
        subscription: Subscription,
        cancel_immediately: bool = False,
        reason: Optional[str] = None
    ) -> Subscription:
        """
        구독 취소
        
        Args:
            subscription: 구독
            cancel_immediately: 즉시 취소 여부
            reason: 취소 사유
            
        Returns:
            업데이트된 구독
        """
        # 1. Stripe 구독 취소
        self.stripe.cancel_subscription(
            subscription.stripe_subscription_id,
            cancel_at_period_end=not cancel_immediately
        )
        
        # 2. 로컬 구독 업데이트
        subscription.cancel(at_period_end=not cancel_immediately)
        
        # 3. 이력 기록
        SubscriptionHistory.objects.create(
            subscription=subscription,
            event_type=SubscriptionHistory.EventType.CANCELED,
            notes=reason or '',
            new_data={
                'cancel_immediately': cancel_immediately,
                'canceled_at': str(subscription.canceled_at)
            }
        )
        
        logger.info(f"구독 취소: {subscription.id}")
        return subscription
    
    @transaction.atomic
    def reactivate_subscription(self, subscription: Subscription) -> Subscription:
        """
        구독 재활성화
        
        Args:
            subscription: 구독
            
        Returns:
            업데이트된 구독
        """
        if not subscription.cancel_at_period_end:
            raise ValueError("취소 예정 상태가 아닙니다.")
        
        # 1. Stripe 구독 재활성화
        self.stripe.update_subscription(
            subscription.stripe_subscription_id,
            new_price_id=subscription.plan.stripe_price_id
        )
        
        # 2. 로컬 구독 업데이트
        subscription.reactivate()
        
        # 3. 이력 기록
        SubscriptionHistory.objects.create(
            subscription=subscription,
            event_type=SubscriptionHistory.EventType.REACTIVATED
        )
        
        logger.info(f"구독 재활성화: {subscription.id}")
        return subscription
    
    @transaction.atomic
    def change_plan(
        self,
        subscription: Subscription,
        new_plan: Plan,
        proration_behavior: str = 'create_prorations'
    ) -> Subscription:
        """
        플랜 변경
        
        Args:
            subscription: 구독
            new_plan: 새 플랜
            proration_behavior: 비례 배분 방식
            
        Returns:
            업데이트된 구독
        """
        old_plan = subscription.plan
        
        # 1. Stripe 구독 업데이트
        self.stripe.update_subscription(
            subscription.stripe_subscription_id,
            new_price_id=new_plan.stripe_price_id,
            proration_behavior=proration_behavior
        )
        
        # 2. 로컬 구독 업데이트
        subscription.plan = new_plan
        subscription.save()
        
        # 3. 이력 기록
        SubscriptionHistory.objects.create(
            subscription=subscription,
            event_type=SubscriptionHistory.EventType.PLAN_CHANGED,
            old_data={'plan': old_plan.name, 'price': str(old_plan.price)},
            new_data={'plan': new_plan.name, 'price': str(new_plan.price)}
        )
        
        logger.info(f"플랜 변경: {old_plan.name} -> {new_plan.name}")
        return subscription
    
    def _get_or_create_stripe_customer(self, user: User) -> str:
        """Stripe 고객 ID 조회 또는 생성"""
        # 기존 구독에서 customer_id 확인
        subscription = Subscription.objects.filter(
            user=user,
            stripe_customer_id__isnull=False
        ).first()
        
        if subscription:
            return subscription.stripe_customer_id
        
        # 새 고객 생성
        customer = self.stripe.create_customer(
            email=user.email,
            name=user.get_full_name() or user.username
        )
        
        return customer.id
```

## 6. 구독 API 엔드포인트 구현

이제 Django Ninja API 엔드포인트를 구현합니다.

### 6.1 인증 설정

```python
# subscriptions/auth.py
from ninja.security import HttpBearer
from django.contrib.auth.models import User
from typing import Optional


class AuthBearer(HttpBearer):
    """간단한 Bearer 토큰 인증 (JWT로 대체 권장)"""
    
    def authenticate(self, request, token):
        # 실제로는 JWT 토큰 검증 등을 구현
        # 여기서는 Django 세션 인증 사용
        if request.user.is_authenticated:
            return request.user
        return None
```

### 6.2 플랜 API

```python
# subscriptions/api.py
from ninja import Router
from typing import List
from django.shortcuts import get_object_or_404
from subscriptions.models import Plan
from subscriptions.schemas import PlanSchema, PlanListSchema

router = Router()


@router.get("/plans", response=PlanListSchema, tags=["Plans"])
def list_plans(request):
    """
    모든 활성 플랜 조회
    
    Returns:
        활성 플랜 목록
    """
    plans = Plan.objects.filter(is_active=True)
    return {
        "plans": plans,
        "count": plans.count()
    }


@router.get("/plans/{slug}", response=PlanSchema, tags=["Plans"])
def get_plan(request, slug: str):
    """
    특정 플랜 상세 조회
    
    Args:
        slug: 플랜 slug
        
    Returns:
        플랜 상세 정보
    """
    plan = get_object_or_404(Plan, slug=slug, is_active=True)
    return plan
```

### 6.3 구독 API

```python
# subscriptions/api.py (계속)
from ninja.security import django_auth
from subscriptions.models import Subscription
from subscriptions.schemas import (
    SubscriptionCreateSchema,
    SubscriptionSchema,
    SubscriptionCancelSchema,
    SubscriptionChangePlanSchema
)
from subscriptions.services.subscription_service import SubscriptionService


@router.post(
    "/subscriptions/create",
    response=SubscriptionSchema,
    auth=django_auth,
    tags=["Subscriptions"]
)
def create_subscription(request, data: SubscriptionCreateSchema):
    """
    새 구독 생성
    
    Args:
        data: 구독 생성 데이터
        
    Returns:
        생성된 구독 정보
    """
    plan = get_object_or_404(Plan, id=data.plan_id)
    
    service = SubscriptionService()
    subscription = service.create_subscription(
        user=request.user,
        plan=plan,
        payment_method_id=data.payment_method_id
    )
    
    return subscription


@router.get(
    "/subscriptions/me",
    response=SubscriptionSchema,
    auth=django_auth,
    tags=["Subscriptions"]
)
def get_my_subscription(request):
    """
    내 구독 조회
    
    Returns:
        현재 활성 구독
    """
    subscription = get_object_or_404(
        Subscription,
        user=request.user,
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING]
    )
    
    return subscription


@router.post(
    "/subscriptions/cancel",
    response=SubscriptionSchema,
    auth=django_auth,
    tags=["Subscriptions"]
)
def cancel_subscription(request, data: SubscriptionCancelSchema):
    """
    구독 취소
    
    Args:
        data: 취소 데이터
        
    Returns:
        업데이트된 구독
    """
    subscription = get_object_or_404(
        Subscription,
        user=request.user,
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING]
    )
    
    service = SubscriptionService()
    subscription = service.cancel_subscription(
        subscription=subscription,
        cancel_immediately=data.cancel_immediately,
        reason=data.reason
    )
    
    return subscription


@router.post(
    "/subscriptions/reactivate",
    response=SubscriptionSchema,
    auth=django_auth,
    tags=["Subscriptions"]
)
def reactivate_subscription(request):
    """
    구독 재활성화
    
    Returns:
        재활성화된 구독
    """
    subscription = get_object_or_404(
        Subscription,
        user=request.user,
        cancel_at_period_end=True
    )
    
    service = SubscriptionService()
    subscription = service.reactivate_subscription(subscription)
    
    return subscription


@router.post(
    "/subscriptions/change-plan",
    response=SubscriptionSchema,
    auth=django_auth,
    tags=["Subscriptions"]
)
def change_plan(request, data: SubscriptionChangePlanSchema):
    """
    플랜 변경
    
    Args:
        data: 플랜 변경 데이터
        
    Returns:
        업데이트된 구독
    """
    subscription = get_object_or_404(
        Subscription,
        user=request.user,
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING]
    )
    
    new_plan = get_object_or_404(Plan, id=data.new_plan_id)
    
    service = SubscriptionService()
    subscription = service.change_plan(
        subscription=subscription,
        new_plan=new_plan,
        proration_behavior=data.proration_behavior
    )
    
    return subscription
```

### 6.4 URL 등록

```python
# config/urls.py (업데이트)
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from subscriptions.api import router as subscriptions_router

# API 인스턴스
api = NinjaAPI(
    title="Subscription Service API",
    version="1.0.0",
    description="Django Ninja로 구현한 SaaS 구독 시스템",
    docs_url="/api/docs",
)

# 라우터 등록
api.add_router("/", subscriptions_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
```

### 6.5 API 테스트

서버를 실행하고 API를 테스트합니다.

```bash
# 서버 실행
python manage.py runserver

# Swagger 문서 확인
# http://localhost:8000/api/docs
```

**Swagger UI에서 테스트 가능한 엔드포인트:**

1. `GET /api/plans` - 플랜 목록 조회
2. `GET /api/plans/{slug}` - 플랜 상세 조회
3. `POST /api/subscriptions/create` - 구독 생성
4. `GET /api/subscriptions/me` - 내 구독 조회
5. `POST /api/subscriptions/cancel` - 구독 취소
6. `POST /api/subscriptions/reactivate` - 구독 재활성화
7. `POST /api/subscriptions/change-plan` - 플랜 변경

**cURL로 테스트:**

```bash
# 플랜 목록 조회
curl http://localhost:8000/api/plans

# 응답 예시:
{
  "plans": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "Basic",
      "slug": "basic",
      "price": "9.99",
      "interval": "month",
      ...
    }
  ],
  "count": 3
}
```

구독 API가 완성되었습니다! 다음 섹션에서는 Stripe 결제 처리를 구현하겠습니다.

## 7. Stripe 연동 및 결제 처리

Stripe와 플랜을 연동하고 실제 결제를 처리합니다.

### 7.1 Stripe에 플랜 등록

플랜을 Stripe에 등록하는 관리 명령을 만듭니다.

```python
# subscriptions/management/commands/sync_stripe_plans.py
from django.core.management.base import BaseCommand
from subscriptions.models import Plan
from payments.stripe_client import StripeService


class Command(BaseCommand):
    help = 'Stripe에 플랜 동기화'

    def handle(self, *args, **options):
        stripe_service = StripeService()
        
        for plan in Plan.objects.filter(is_active=True):
            # Product가 없으면 생성
            if not plan.stripe_product_id:
                product = stripe_service.create_product(
                    name=plan.name,
                    description=plan.description
                )
                plan.stripe_product_id = product.id
                self.stdout.write(f"✓ Product 생성: {plan.name}")
            
            # Price가 없으면 생성
            if not plan.stripe_price_id:
                # Decimal을 센트로 변환
                amount_cents = int(plan.price * 100)
                
                price = stripe_service.create_price(
                    product_id=plan.stripe_product_id,
                    amount=amount_cents,
                    currency=plan.currency,
                    interval=plan.interval,
                    interval_count=plan.interval_count
                )
                plan.stripe_price_id = price.id
                self.stdout.write(f"✓ Price 생성: ${plan.price}")
            
            plan.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ {plan.name} 동기화 완료')
            )
```

```bash
# 플랜을 Stripe에 등록
python manage.py sync_stripe_plans
```

### 7.2 결제 수단 관리 API

```python
# payments/api.py
from ninja import Router
from ninja.security import django_auth
from payments.schemas import PaymentListSchema
from payments.models import Payment

router = Router()


@router.get(
    "/payments/history",
    response=PaymentListSchema,
    auth=django_auth,
    tags=["Payments"]
)
def payment_history(request):
    """
    결제 내역 조회
    
    Returns:
        사용자의 결제 내역
    """
    payments = Payment.objects.filter(user=request.user)
    
    return {
        "payments": payments,
        "count": payments.count()
    }


@router.post(
    "/payments/setup-intent",
    auth=django_auth,
    tags=["Payments"]
)
def create_setup_intent(request):
    """
    결제 수단 등록을 위한 Setup Intent 생성
    
    Returns:
        Setup Intent 클라이언트 시크릿
    """
    import stripe
    from subscriptions.services.subscription_service import SubscriptionService
    
    service = SubscriptionService()
    customer_id = service._get_or_create_stripe_customer(request.user)
    
    setup_intent = stripe.SetupIntent.create(
        customer=customer_id,
        payment_method_types=['card'],
    )
    
    return {
        "client_secret": setup_intent.client_secret,
        "customer_id": customer_id
    }
```

```python
# config/urls.py (payments 라우터 추가)
from payments.api import router as payments_router

api.add_router("/", subscriptions_router)
api.add_router("/", payments_router)
```

## 8. 웹훅 처리

Stripe 웹훅을 처리하여 구독 상태를 자동으로 동기화합니다.

### 8.1 웹훅 핸들러

```python
# payments/webhooks.py
from ninja import Router
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from subscriptions.models import Subscription
from payments.models import Payment
from django.utils import timezone
import stripe
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.post("/webhook/stripe")
@csrf_exempt
def stripe_webhook(request):
    """
    Stripe 웹훅 엔드포인트
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.error("Invalid payload")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature")
        return HttpResponse(status=400)
    
    # 이벤트 타입별 처리
    event_type = event['type']
    data = event['data']['object']
    
    logger.info(f"Webhook received: {event_type}")
    
    handlers = {
        'customer.subscription.created': handle_subscription_created,
        'customer.subscription.updated': handle_subscription_updated,
        'customer.subscription.deleted': handle_subscription_deleted,
        'invoice.paid': handle_invoice_paid,
        'invoice.payment_failed': handle_invoice_payment_failed,
    }
    
    handler = handlers.get(event_type)
    if handler:
        try:
            handler(data)
        except Exception as e:
            logger.error(f"Webhook handler error: {str(e)}")
            return HttpResponse(status=500)
    
    return HttpResponse(status=200)


def handle_subscription_created(subscription_data):
    """구독 생성 이벤트"""
    stripe_subscription_id = subscription_data['id']
    
    subscription = Subscription.objects.filter(
        stripe_subscription_id=stripe_subscription_id
    ).first()
    
    if subscription:
        subscription.status = subscription_data['status']
        subscription.save()
        logger.info(f"Subscription created: {stripe_subscription_id}")


def handle_subscription_updated(subscription_data):
    """구독 업데이트 이벤트"""
    stripe_subscription_id = subscription_data['id']
    
    subscription = Subscription.objects.filter(
        stripe_subscription_id=stripe_subscription_id
    ).first()
    
    if subscription:
        subscription.status = subscription_data['status']
        subscription.current_period_start = timezone.datetime.fromtimestamp(
            subscription_data['current_period_start'],
            tz=timezone.utc
        )
        subscription.current_period_end = timezone.datetime.fromtimestamp(
            subscription_data['current_period_end'],
            tz=timezone.utc
        )
        
        if subscription_data.get('cancel_at_period_end'):
            subscription.cancel_at_period_end = True
        
        subscription.save()
        logger.info(f"Subscription updated: {stripe_subscription_id}")


def handle_subscription_deleted(subscription_data):
    """구독 삭제 이벤트"""
    stripe_subscription_id = subscription_data['id']
    
    subscription = Subscription.objects.filter(
        stripe_subscription_id=stripe_subscription_id
    ).first()
    
    if subscription:
        subscription.status = Subscription.Status.CANCELED
        subscription.ended_at = timezone.now()
        subscription.save()
        logger.info(f"Subscription deleted: {stripe_subscription_id}")


def handle_invoice_paid(invoice_data):
    """결제 성공 이벤트"""
    subscription_id = invoice_data.get('subscription')
    
    if subscription_id:
        subscription = Subscription.objects.filter(
            stripe_subscription_id=subscription_id
        ).first()
        
        if subscription:
            # 결제 기록 생성
            Payment.objects.create(
                user=subscription.user,
                subscription=subscription,
                stripe_invoice_id=invoice_data['id'],
                stripe_charge_id=invoice_data.get('charge'),
                amount=invoice_data['amount_paid'] / 100,  # 센트 -> 달러
                currency=invoice_data['currency'],
                status=Payment.Status.SUCCEEDED,
                paid_at=timezone.now(),
                metadata=invoice_data.get('metadata', {})
            )
            
            logger.info(f"Invoice paid: {invoice_data['id']}")


def handle_invoice_payment_failed(invoice_data):
    """결제 실패 이벤트"""
    subscription_id = invoice_data.get('subscription')
    
    if subscription_id:
        subscription = Subscription.objects.filter(
            stripe_subscription_id=subscription_id
        ).first()
        
        if subscription:
            subscription.status = Subscription.Status.PAST_DUE
            subscription.save()
            
            # 실패 기록
            Payment.objects.create(
                user=subscription.user,
                subscription=subscription,
                stripe_invoice_id=invoice_data['id'],
                amount=invoice_data['amount_due'] / 100,
                currency=invoice_data['currency'],
                status=Payment.Status.FAILED,
                error_message=invoice_data.get('last_finalization_error', {}).get('message', ''),
                metadata=invoice_data.get('metadata', {})
            )
            
            logger.warning(f"Invoice payment failed: {invoice_data['id']}")
```

```python
# config/urls.py (웹훅 라우터 추가)
from payments.webhooks import router as webhook_router

api.add_router("/", webhook_router)
```

### 8.2 로컬 웹훅 테스트

```bash
# Stripe CLI 설치 (macOS)
brew install stripe/stripe-cli/stripe

# 또는 다운로드
# https://stripe.com/docs/stripe-cli

# Stripe 로그인
stripe login

# 웹훅 포워딩
stripe listen --forward-to localhost:8000/api/webhook/stripe

# 출력된 webhook signing secret을 .env에 추가
# STRIPE_WEBHOOK_SECRET=whsec_...

# 이벤트 트리거 (테스트용)
stripe trigger customer.subscription.created
stripe trigger invoice.paid
```

## 9. 테스트 코드 작성

구독 시스템이 올바르게 작동하는지 확인하는 테스트를 작성합니다.

### 9.1 테스트 설정

```python
# conftest.py (pytest 설정)
import pytest
from django.contrib.auth.models import User
from subscriptions.models import Plan


@pytest.fixture
def user(db):
    """테스트 사용자"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def plan(db):
    """테스트 플랜"""
    return Plan.objects.create(
        name='Test Plan',
        slug='test-plan',
        price=9.99,
        currency='usd',
        interval=Plan.Interval.MONTH,
        trial_period_days=14,
        is_active=True
    )
```

### 9.2 구독 서비스 테스트

```python
# subscriptions/tests/test_subscription_service.py
import pytest
from unittest.mock import Mock, patch
from subscriptions.services.subscription_service import SubscriptionService
from subscriptions.models import Subscription


@pytest.mark.django_db
class TestSubscriptionService:
    
    @patch('subscriptions.services.subscription_service.StripeService')
    def test_create_subscription(self, mock_stripe, user, plan):
        """구독 생성 테스트"""
        # Mock Stripe 응답
        mock_stripe_subscription = Mock()
        mock_stripe_subscription.id = 'sub_test123'
        mock_stripe_subscription.status = 'trialing'
        mock_stripe_subscription.current_period_start = 1640000000
        mock_stripe_subscription.current_period_end = 1642592000
        mock_stripe_subscription.trial_start = 1640000000
        mock_stripe_subscription.trial_end = 1641209600
        
        mock_stripe.return_value.create_subscription.return_value = mock_stripe_subscription
        mock_stripe.return_value.create_customer.return_value = Mock(id='cus_test123')
        
        # 서비스 실행
        service = SubscriptionService()
        subscription = service.create_subscription(
            user=user,
            plan=plan
        )
        
        # 검증
        assert subscription.user == user
        assert subscription.plan == plan
        assert subscription.status == 'trialing'
        assert subscription.stripe_subscription_id == 'sub_test123'
    
    @patch('subscriptions.services.subscription_service.StripeService')
    def test_cancel_subscription(self, mock_stripe, user, plan):
        """구독 취소 테스트"""
        # 구독 생성
        subscription = Subscription.objects.create(
            user=user,
            plan=plan,
            stripe_subscription_id='sub_test123',
            stripe_customer_id='cus_test123',
            status=Subscription.Status.ACTIVE,
            current_period_start='2024-01-01T00:00:00Z',
            current_period_end='2024-02-01T00:00:00Z'
        )
        
        # 서비스 실행
        service = SubscriptionService()
        service.cancel_subscription(subscription, cancel_immediately=False)
        
        # 검증
        subscription.refresh_from_db()
        assert subscription.cancel_at_period_end == True
        assert subscription.canceled_at is not None
```

### 9.3 API 테스트

```python
# subscriptions/tests/test_api.py
import pytest
from ninja.testing import TestClient
from config.urls import api


@pytest.mark.django_db
class TestPlanAPI:
    
    def test_list_plans(self, plan):
        """플랜 목록 조회 테스트"""
        client = TestClient(api)
        response = client.get("/plans")
        
        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 1
        assert data['plans'][0]['name'] == 'Test Plan'
    
    def test_get_plan_by_slug(self, plan):
        """플랜 상세 조회 테스트"""
        client = TestClient(api)
        response = client.get(f"/plans/{plan.slug}")
        
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'Test Plan'
        assert data['slug'] == 'test-plan'
```

```bash
# 테스트 실행
pytest

# 커버리지와 함께 실행
pytest --cov=subscriptions --cov=payments

# 특정 테스트만 실행
pytest subscriptions/tests/test_api.py -v
```

## 10. 프론트엔드 통합 예시

간단한 구독 결제 페이지 예시입니다.

### 10.1 HTML 템플릿

```html
<!-- templates/subscribe.html -->
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>구독하기</title>
    <script src="https://js.stripe.com/v3/"></script>
    <style>
        .plan-card {
            border: 1px solid #ddd;
            padding: 20px;
            margin: 10px;
            border-radius: 8px;
        }
        .plan-card.featured {
            border-color: #4CAF50;
            box-shadow: 0 4px 8px rgba(76, 175, 80, 0.2);
        }
        #card-element {
            border: 1px solid #ddd;
            padding: 12px;
            border-radius: 4px;
        }
        .error {
            color: red;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <h1>플랜 선택</h1>
    
    <div id="plans-container"></div>
    
    <div id="payment-form" style="display: none;">
        <h2>결제 정보 입력</h2>
        <div id="card-element"></div>
        <div id="card-errors" class="error"></div>
        <button id="submit-button">구독하기</button>
    </div>

    <script>
        const stripe = Stripe('{{ publishable_key }}');
        const elements = stripe.elements();
        const cardElement = elements.create('card');
        
        let selectedPlanId = null;
        
        // 플랜 목록 로드
        fetch('/api/plans')
            .then(res => res.json())
            .then(data => {
                const container = document.getElementById('plans-container');
                data.plans.forEach(plan => {
                    const card = document.createElement('div');
                    card.className = 'plan-card' + (plan.is_featured ? ' featured' : '');
                    card.innerHTML = `
                        <h3>${plan.name}</h3>
                        <p>${plan.description}</p>
                        <p><strong>$${plan.price}/${plan.interval}</strong></p>
                        <button onclick="selectPlan('${plan.id}')">선택</button>
                    `;
                    container.appendChild(card);
                });
            });
        
        function selectPlan(planId) {
            selectedPlanId = planId;
            document.getElementById('payment-form').style.display = 'block';
            cardElement.mount('#card-element');
        }
        
        // 결제 처리
        document.getElementById('submit-button').addEventListener('click', async () => {
            const {error, paymentMethod} = await stripe.createPaymentMethod({
                type: 'card',
                card: cardElement,
            });
            
            if (error) {
                document.getElementById('card-errors').textContent = error.message;
                return;
            }
            
            // 구독 생성 API 호출
            const response = await fetch('/api/subscriptions/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    plan_id: selectedPlanId,
                    payment_method_id: paymentMethod.id
                })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                alert('구독이 완료되었습니다!');
                window.location.href = '/dashboard';
            } else {
                alert('구독 실패: ' + result.detail);
            }
        });
    </script>
</body>
</html>
```

### 10.2 뷰 추가

```python
# subscriptions/views.py
from django.shortcuts import render
from django.conf import settings


def subscribe_page(request):
    """구독 페이지"""
    return render(request, 'subscribe.html', {
        'publishable_key': settings.STRIPE_PUBLISHABLE_KEY
    })
```

```python
# config/urls.py
from subscriptions.views import subscribe_page

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
    path('subscribe/', subscribe_page, name='subscribe'),
]
```

## 11. 프로덕션 체크리스트

실제 서비스를 런칭하기 전 확인 사항입니다.

### 11.1 보안

- [ ] `.env` 파일을 Git에서 제외
- [ ] `SECRET_KEY`를 강력한 값으로 변경
- [ ] `DEBUG=False` 설정
- [ ] HTTPS 사용
- [ ] Stripe 라이브 키 사용
- [ ] CSRF 보호 활성화
- [ ] Rate limiting 설정
- [ ] SQL Injection 방지 (ORM 사용)

### 11.2 Stripe 설정

- [ ] Stripe 계정 활성화
- [ ] 비즈니스 정보 등록
- [ ] 은행 계좌 등록
- [ ] 웹훅 엔드포인트 등록 (HTTPS)
- [ ] 테스트 모드 → 라이브 모드 전환
- [ ] Stripe Radar 활성화 (사기 방지)

### 11.3 데이터베이스

- [ ] PostgreSQL 사용
- [ ] 자동 백업 설정
- [ ] 인덱스 최적화
- [ ] Connection pooling 설정

### 11.4 모니터링

- [ ] 에러 추적 (Sentry)
- [ ] 로깅 설정
- [ ] 성능 모니터링
- [ ] 구독 지표 대시보드

### 11.5 이메일 알림

```python
# subscriptions/notifications.py
from django.core.mail import send_mail
from django.conf import settings


def send_subscription_confirmation(subscription):
    """구독 확인 이메일"""
    send_mail(
        subject=f'{subscription.plan.name} 구독이 시작되었습니다',
        message=f'안녕하세요 {subscription.user.username}님,\n\n'
                f'{subscription.plan.name} 플랜 구독이 시작되었습니다.\n'
                f'다음 결제일: {subscription.current_period_end.strftime("%Y-%m-%d")}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[subscription.user.email],
    )


def send_payment_failed_notification(subscription):
    """결제 실패 알림"""
    send_mail(
        subject='결제가 실패했습니다',
        message=f'안녕하세요 {subscription.user.username}님,\n\n'
                f'구독 결제가 실패했습니다.\n'
                f'카드 정보를 확인해주세요.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[subscription.user.email],
    )
```

## 12. 결론

축하합니다! Django Ninja를 사용하여 완전한 구독 시스템을 구축했습니다.

### 12.1 구현한 내용

✅ **핵심 기능**
- 구독 플랜 관리
- 구독 생성 및 취소
- 플랜 변경 (업그레이드/다운그레이드)
- 무료 체험 기간
- Stripe 결제 연동
- 웹훅을 통한 자동 동기화

✅ **기술 스택**
- Django + Django Ninja
- Stripe API
- PostgreSQL
- Pydantic (데이터 검증)
- JWT 인증 (선택)

✅ **아키텍처**
- 서비스 레이어 패턴
- RESTful API 설계
- 자동 API 문서화
- 테스트 주도 개발

### 12.2 다음 단계

**고급 기능 추가:**

1. **쿠폰 시스템**
```python
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.IntegerField()
    valid_until = models.DateTimeField()
    max_uses = models.IntegerField(default=1)
```

2. **사용량 기반 과금**
```python
def record_api_usage(subscription, count):
    """API 사용량 기록"""
    UsageRecord.objects.create(
        subscription=subscription,
        metric='api_calls',
        quantity=count
    )
```

3. **팀 구독**
```python
class TeamSubscription(models.Model):
    subscription = models.ForeignKey(Subscription)
    members = models.ManyToManyField(User)
    max_members = models.IntegerField()
```

4. **어드온 기능**
```python
class Addon(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subscriptions = models.ManyToManyField(Subscription)
```

### 12.3 추가 학습 자료

**Django Ninja:**
- 공식 문서: https://django-ninja.rest-framework.com/
- GitHub: https://github.com/vitalik/django-ninja

**Stripe:**
- Stripe 문서: https://stripe.com/docs
- Subscription 가이드: https://stripe.com/docs/billing/subscriptions/overview

**커뮤니티:**
- Django 포럼: https://forum.djangoproject.com/
- Stack Overflow: [django-ninja] 태그

### 12.4 마치며

이 가이드에서는 실제 프로덕션 환경에서 사용 가능한 구독 시스템을 처음부터 끝까지 구축했습니다. Django Ninja의 간결한 문법과 Stripe의 강력한 기능을 활용하면 복잡한 결제 시스템도 쉽게 구현할 수 있습니다.

구독 시스템은 SaaS 비즈니스의 핵심이므로 보안과 안정성에 특히 주의를 기울여야 합니다. 충분한 테스트와 모니터링을 통해 사용자에게 신뢰할 수 있는 서비스를 제공하세요.

**핵심 포인트:**
1. **타입 안정성**: Pydantic으로 데이터 검증
2. **서비스 레이어**: 비즈니스 로직 분리
3. **웹훅 처리**: 실시간 동기화
4. **테스트**: 신뢰할 수 있는 코드
5. **문서화**: 자동 생성되는 API 문서

여러분의 SaaS 서비스가 성공하기를 바랍니다! 🚀

---

**관련 포스트:**
- [Django Ninja로 Stripe 해외결제 시스템 구축하기](/2025/11/09/django-ninja-stripe-payment-integration/)
- [Django REST Framework vs Django Ninja 비교](/posts/drf-vs-ninja/)
- [SaaS 비즈니스 지표 분석 (MRR, Churn, LTV)](/posts/saas-metrics/)

**질문이나 피드백:**
- GitHub: [프로젝트 저장소]
- 이메일: your@email.com
- Twitter: @yourhandle
