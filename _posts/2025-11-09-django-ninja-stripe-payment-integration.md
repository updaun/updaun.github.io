---
layout: post
title: "Django Ninja로 Stripe 해외결제 시스템 구축하기"
date: 2025-11-09 09:00:00 +0900
categories: [Django, Payment, Backend]
tags: [django-ninja, stripe, payment, subscription, webhook, api]
description: "Django Ninja와 Stripe를 활용하여 글로벌 결제 시스템을 구현하는 완벽 가이드. 일회성 결제부터 정기 구독, 환불 처리, 웹훅까지 실무에서 바로 사용 가능한 코드를 제공합니다."
---

## 1. 서론

### 1.1 왜 Stripe인가?

해외 시장을 대상으로 하는 서비스를 개발한다면 결제 시스템 선택이 매우 중요합니다. Stripe는 전 세계적으로 가장 인기 있는 결제 플랫폼 중 하나로, 다음과 같은 장점을 제공합니다:

**글로벌 지원:**
- 🌍 135개 이상의 통화 지원
- 🌏 전 세계 대부분의 국가에서 사용 가능
- 💳 주요 카드사 모두 지원 (Visa, Mastercard, American Express 등)

**개발자 친화적:**
- 📚 훌륭한 문서와 SDK
- 🛠️ 풍부한 API와 도구
- 🧪 테스트 환경 완벽 지원
- 🔐 PCI DSS 준수 자동 처리

**비용 효율성:**
- 초기 비용 없음 (종량제)
- 국내 카드: 3.6% + $0.30
- 해외 카드: 4.1% + $0.30
- 추가 숨겨진 비용 없음

**강력한 기능:**
- 일회성 결제
- 정기 구독 (Subscription)
- 분할 결제 (Installments)
- 3D Secure 인증
- 실시간 웹훅
- 상세한 분석 대시보드

### 1.2 Django Ninja의 장점

Django Ninja는 FastAPI 스타일의 Django용 API 프레임워크로, Stripe 연동에 최적입니다:

- **타입 안정성**: Pydantic을 통한 강력한 타입 체킹
- **자동 검증**: 요청/응답 데이터 자동 검증
- **빠른 개발**: 간결한 코드로 빠른 구현
- **자동 문서화**: OpenAPI/Swagger 자동 생성
- **Django 통합**: ORM, 인증 등 Django 기능 활용

### 1.3 이 글에서 다룰 내용

이 포스트에서는 실제 프로덕션 환경에서 사용 가능한 완전한 결제 시스템을 구축합니다:

**핵심 기능:**
1. Stripe 계정 설정 및 API 키 관리
2. 일회성 결제 구현 (Payment Intent)
3. 정기 구독 시스템 (Subscription)
4. 결제 수단 관리 (Payment Method)
5. 환불 처리 (Refund)
6. 웹훅을 통한 실시간 이벤트 처리
7. 프론트엔드 통합 (Stripe Elements)
8. 보안 및 에러 핸들링
9. 테스트 코드 작성
10. 프로덕션 배포

**실습 결과:**
- REST API 기반 결제 시스템
- 구독 플랜 관리
- 결제 이력 추적
- 실시간 알림
- 관리자 대시보드

## 2. Stripe 설정

### 2.1 Stripe 계정 생성

**1) 계정 가입**

[Stripe 홈페이지](https://stripe.com)에서 계정을 생성합니다.

```
1. https://dashboard.stripe.com/register 접속
2. 이메일, 비밀번호 입력
3. 이메일 인증
4. 비즈니스 정보 입력 (선택사항, 나중에 가능)
```

**2) 테스트 모드와 라이브 모드**

Stripe는 두 가지 모드를 제공합니다:

- **테스트 모드**: 개발 및 테스트용, 실제 결제 없음
- **라이브 모드**: 실제 결제 처리

Dashboard 좌측 상단에서 모드를 전환할 수 있습니다.

### 2.2 API 키 발급

**1) API 키 종류**

Stripe는 4가지 종류의 키를 제공합니다:

```
퍼블리셔블 키 (Publishable Key):
- 클라이언트 사이드에서 사용
- 공개해도 안전
- pk_test_... (테스트)
- pk_live_... (라이브)

시크릿 키 (Secret Key):
- 서버 사이드에서 사용
- 절대 공개하면 안 됨
- sk_test_... (테스트)
- sk_live_... (라이브)
```

**2) API 키 확인**

Dashboard → Developers → API keys

```bash
# 테스트 모드 키 (예시)
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxx
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxx

# 라이브 모드 키 (프로덕션)
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxxx
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxxx
```

⚠️ **중요**: Secret Key는 절대 코드에 하드코딩하지 마세요!

### 2.3 웹훅 엔드포인트 설정

웹훅은 Stripe 이벤트를 실시간으로 수신하는 데 필수입니다.

**1) 웹훅 엔드포인트 등록**

Dashboard → Developers → Webhooks → Add endpoint

```
Endpoint URL: https://your-domain.com/api/payments/webhook
Events to listen: 
  ✓ payment_intent.succeeded
  ✓ payment_intent.payment_failed
  ✓ customer.subscription.created
  ✓ customer.subscription.updated
  ✓ customer.subscription.deleted
  ✓ invoice.paid
  ✓ invoice.payment_failed
```

**2) 웹훅 시크릿 발급**

웹훅 생성 후 Signing secret을 확인합니다:

```bash
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

이 시크릿은 웹훅 요청의 진위를 확인하는 데 사용됩니다.

**3) 로컬 개발용 웹훅 (Stripe CLI)**

로컬 개발 시에는 Stripe CLI를 사용합니다:

```bash
# Stripe CLI 설치 (macOS)
brew install stripe/stripe-cli/stripe

# 또는 직접 다운로드
# https://stripe.com/docs/stripe-cli

# 로그인
stripe login

# 웹훅 포워딩
stripe listen --forward-to localhost:8000/api/payments/webhook

# 출력되는 webhook signing secret 복사
# whsec_...
```

### 2.4 테스트 카드 번호

Stripe는 다양한 시나리오를 테스트할 수 있는 카드 번호를 제공합니다:

**성공 케이스:**
```
카드 번호: 4242 4242 4242 4242
만료일: 미래의 아무 날짜 (예: 12/34)
CVC: 아무 3자리 (예: 123)
우편번호: 아무 숫자 (예: 12345)
```

**3D Secure 인증 필요:**
```
카드 번호: 4000 0027 6000 3184
- 3D Secure 인증 플로우 테스트
```

**결제 실패:**
```
카드 번호: 4000 0000 0000 0002
- 카드 거부 시뮬레이션
```

**잔액 부족:**
```
카드 번호: 4000 0000 0000 9995
- 잔액 부족 에러
```

전체 테스트 카드 목록: https://stripe.com/docs/testing

### 2.5 Stripe 요금 구조

**한국 카드:**
```
일반 결제: 3.6% + ₩35
- Visa, Mastercard, American Express
```

**해외 카드:**
```
국제 카드: 4.1% + ₩35
- 통화 변환 수수료 포함
```

**구독 (Subscription):**
```
동일한 요금 구조 적용
추가 비용 없음
```

**환불:**
```
환불 시 수수료 반환되지 않음
부분 환불 가능
```

**추가 기능 (선택사항):**
```
Stripe Radar (사기 방지): 0.05 / transaction
Stripe Billing (구독 관리): 무료
Stripe Terminal (오프라인): 별도 요금
```

### 2.6 계정 활성화 (프로덕션용)

라이브 모드를 사용하려면 계정 활성화가 필요합니다:

**필요 정보:**
1. 비즈니스 정보
   - 회사명
   - 업종
   - 웹사이트 URL
   
2. 대표자 정보
   - 이름
   - 생년월일
   - 주소
   
3. 은행 계좌 정보
   - 정산 받을 계좌
   - 계좌번호
   - 은행명

**검증 프로세스:**
- 보통 1-3 영업일 소요
- 추가 서류 요청 가능 (사업자등록증 등)
- 승인 후 라이브 결제 가능

### 2.7 대시보드 둘러보기

Stripe Dashboard는 강력한 관리 도구입니다:

**주요 기능:**
- **홈**: 실시간 매출, 트랜잭션 현황
- **결제**: 모든 결제 내역 조회
- **고객**: 고객 정보 관리
- **구독**: 구독 현황 관리
- **청구서**: 인보이스 관리
- **분쟁**: 차지백 처리
- **보고서**: 상세한 매출 분석
- **개발자**: API 키, 웹훅, 로그

## 3. Django 프로젝트 설정

### 3.1 프로젝트 구조

완성될 프로젝트 구조입니다:

```
payment_service/
├── manage.py
├── requirements.txt
├── .env
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── asgi.py
├── apps/
│   └── payments/
│       ├── __init__.py
│       ├── models.py
│       ├── schemas.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── stripe_client.py
│       │   ├── payment_service.py
│       │   └── subscription_service.py
│       ├── api.py
│       ├── webhooks.py
│       └── tests/
│           ├── __init__.py
│           ├── test_payments.py
│           └── test_webhooks.py
├── frontend/
│   └── payment.html
└── static/
    └── js/
        └── stripe-checkout.js
```

### 3.2 환경 설정

**1) 가상환경 및 Django 설치**

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Django 프로젝트 생성
pip install django
django-admin startproject config .
python manage.py startapp apps/payments

# 필요한 패키지 설치
pip install django-ninja stripe python-dotenv celery redis pydantic
```

**2) requirements.txt**

```txt
Django==5.0.0
django-ninja==1.1.0
stripe==7.9.0
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0

# 비동기 작업 (선택)
celery==5.3.4
redis==5.0.1

# 데이터베이스 (PostgreSQL 권장)
psycopg2-binary==2.9.9

# 개발 도구
pytest==7.4.3
pytest-django==4.7.0
pytest-cov==4.1.0
faker==21.0.0
requests-mock==1.11.0
```

**3) .env 파일**

```bash
# Django
DEBUG=True
SECRET_KEY=your-django-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# Stripe Keys (테스트 모드)
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# 통화 설정
STRIPE_CURRENCY=usd
STRIPE_COUNTRY=US

# 데이터베이스
DATABASE_URL=postgresql://user:password@localhost:5432/payment_db

# Celery (비동기 작업)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# 로깅
LOG_LEVEL=INFO
```

⚠️ `.env` 파일은 `.gitignore`에 추가하세요!

```bash
# .gitignore
.env
*.pyc
__pycache__/
db.sqlite3
venv/
.pytest_cache/
htmlcov/
```

**4) settings.py 수정**

```python
# config/settings.py
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

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
    'apps.payments',
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
        'DIRS': [BASE_DIR / 'frontend'],
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

# 데이터베이스
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'payment_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Stripe 설정
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
STRIPE_CURRENCY = os.getenv('STRIPE_CURRENCY', 'usd')
STRIPE_COUNTRY = os.getenv('STRIPE_COUNTRY', 'US')

# Celery 설정 (선택)
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# 정적 파일
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'payments.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'apps.payments': {
            'handlers': ['console', 'file'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'stripe': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# 보안 설정 (프로덕션)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    
    # CSRF 토큰이 필요한 경우
    CSRF_TRUSTED_ORIGINS = [
        'https://yourdomain.com',
    ]
```

### 3.3 Django Ninja API 설정

```python
# config/urls.py
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from ninja import NinjaAPI

from apps.payments.api import router as payments_router
from apps.payments.webhooks import router as webhooks_router

# API 인스턴스 생성
api = NinjaAPI(
    title="Payment Service API",
    version="1.0.0",
    description="Stripe 기반 결제 시스템 API",
    docs_url="/api/docs",
)

# 라우터 추가
api.add_router("/payments/", payments_router)
api.add_router("/webhooks/", webhooks_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
    
    # 프론트엔드 (데모용)
    path('', TemplateView.as_view(template_name='payment.html'), name='payment'),
]
```

### 3.4 Stripe SDK 초기화

```python
# apps/payments/__init__.py
import stripe
from django.conf import settings

# Stripe API 키 설정
stripe.api_key = settings.STRIPE_SECRET_KEY

# API 버전 지정 (선택사항, 권장)
stripe.api_version = '2023-10-16'

# 로깅 활성화 (개발 시)
if settings.DEBUG:
    stripe.log = 'debug'
```

### 3.5 데이터베이스 마이그레이션

```bash
# 데이터베이스 생성 (PostgreSQL)
createdb payment_db

# 마이그레이션 생성 및 적용
python manage.py makemigrations
python manage.py migrate

# 관리자 계정 생성
python manage.py createsuperuser
```

이제 기본 설정이 완료되었습니다. 다음 섹션에서는 결제 모델과 서비스를 구현하겠습니다.

## 4. 결제 모델 및 서비스 구현

### 4.1 데이터 모델 정의

```python
# apps/payments/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class StripeCustomer(models.Model):
    """Stripe 고객 정보"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='stripe_customer'
    )
    stripe_customer_id = models.CharField(max_length=255, unique=True)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'stripe_customers'
        verbose_name = 'Stripe 고객'
        verbose_name_plural = 'Stripe 고객'
    
    def __str__(self):
        return f"{self.user.username} - {self.stripe_customer_id}"


class Payment(models.Model):
    """결제 정보"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', '대기중'
        PROCESSING = 'processing', '처리중'
        SUCCEEDED = 'succeeded', '성공'
        FAILED = 'failed', '실패'
        CANCELED = 'canceled', '취소'
        REFUNDED = 'refunded', '환불'
        PARTIALLY_REFUNDED = 'partially_refunded', '부분환불'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 고객 정보
    customer = models.ForeignKey(
        StripeCustomer,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payments'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payments'
    )
    
    # Stripe 정보
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)
    stripe_charge_id = models.CharField(max_length=255, blank=True)
    
    # 결제 상세
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
    
    # 메타데이터
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # 에러 정보
    error_message = models.TextField(blank=True)
    error_code = models.CharField(max_length=100, blank=True)
    
    # 환불 정보
    refunded_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    refund_reason = models.TextField(blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    succeeded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['stripe_payment_intent_id']),
        ]
    
    def __str__(self):
        return f"{self.id} - {self.amount} {self.currency} - {self.status}"
    
    @property
    def is_refundable(self):
        """환불 가능 여부"""
        return (
            self.status == self.Status.SUCCEEDED and
            self.refunded_amount < self.amount
        )
    
    @property
    def remaining_amount(self):
        """환불 가능 잔액"""
        return self.amount - self.refunded_amount


class Subscription(models.Model):
    """구독 정보"""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', '활성'
        PAST_DUE = 'past_due', '연체'
        CANCELED = 'canceled', '취소'
        INCOMPLETE = 'incomplete', '미완료'
        INCOMPLETE_EXPIRED = 'incomplete_expired', '만료됨'
        TRIALING = 'trialing', '체험중'
        UNPAID = 'unpaid', '미납'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 고객 정보
    customer = models.ForeignKey(
        StripeCustomer,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    
    # Stripe 정보
    stripe_subscription_id = models.CharField(max_length=255, unique=True)
    stripe_price_id = models.CharField(max_length=255)
    stripe_product_id = models.CharField(max_length=255)
    
    # 구독 상세
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INCOMPLETE
    )
    plan_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='usd')
    interval = models.CharField(max_length=20)  # month, year
    interval_count = models.IntegerField(default=1)
    
    # 기간 정보
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    cancel_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
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
            models.Index(fields=['status']),
            models.Index(fields=['stripe_subscription_id']),
        ]
    
    def __str__(self):
        return f"{self.plan_name} - {self.status}"
    
    @property
    def is_active(self):
        """활성 상태 여부"""
        return self.status in [self.Status.ACTIVE, self.Status.TRIALING]
    
    @property
    def days_until_renewal(self):
        """갱신까지 남은 일수"""
        if self.current_period_end:
            delta = self.current_period_end - timezone.now()
            return delta.days
        return None


class Product(models.Model):
    """상품 정보"""
    
    stripe_product_id = models.CharField(max_length=255, unique=True)
    stripe_price_id = models.CharField(max_length=255, unique=True)
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # 가격 정보
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='usd')
    
    # 구독 상품인 경우
    is_recurring = models.BooleanField(default=False)
    interval = models.CharField(max_length=20, blank=True)  # month, year
    interval_count = models.IntegerField(default=1)
    
    # 메타데이터
    metadata = models.JSONField(default=dict, blank=True)
    features = models.JSONField(default=list, blank=True)
    
    # 상태
    is_active = models.BooleanField(default=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class WebhookEvent(models.Model):
    """Webhook 이벤트 로그"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    
    # 이벤트 데이터
    data = models.JSONField()
    
    # 처리 상태
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # 에러 정보
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'webhook_events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['stripe_event_id']),
            models.Index(fields=['event_type']),
            models.Index(fields=['processed']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.stripe_event_id}"
```

마이그레이션을 생성하고 적용합니다:

```bash
python manage.py makemigrations payments
python manage.py migrate
```

### 4.2 Stripe 클라이언트 래퍼

```python
# apps/payments/services/stripe_client.py
import stripe
from django.conf import settings
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class StripeClientError(Exception):
    """Stripe 클라이언트 에러"""
    pass


class StripeClient:
    """Stripe API 클라이언트 래퍼"""
    
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY
    
    # ===== Customer 관리 =====
    
    def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> stripe.Customer:
        """
        Stripe 고객 생성
        
        Args:
            email: 이메일
            name: 이름
            metadata: 메타데이터
            
        Returns:
            Stripe Customer 객체
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            logger.info(f"Stripe 고객 생성: {customer.id}")
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"고객 생성 실패: {str(e)}")
            raise StripeClientError(f"고객 생성 실패: {str(e)}")
    
    def retrieve_customer(self, customer_id: str) -> stripe.Customer:
        """고객 정보 조회"""
        try:
            return stripe.Customer.retrieve(customer_id)
        except stripe.error.StripeError as e:
            logger.error(f"고객 조회 실패: {str(e)}")
            raise StripeClientError(f"고객 조회 실패: {str(e)}")
    
    def update_customer(
        self,
        customer_id: str,
        **kwargs
    ) -> stripe.Customer:
        """고객 정보 수정"""
        try:
            return stripe.Customer.modify(customer_id, **kwargs)
        except stripe.error.StripeError as e:
            logger.error(f"고객 수정 실패: {str(e)}")
            raise StripeClientError(f"고객 수정 실패: {str(e)}")
    
    # ===== Payment Intent 관리 =====
    
    def create_payment_intent(
        self,
        amount: int,
        currency: str = 'usd',
        customer: Optional[str] = None,
        payment_method: Optional[str] = None,
        metadata: Optional[Dict] = None,
        description: Optional[str] = None,
        automatic_payment_methods: bool = True
    ) -> stripe.PaymentIntent:
        """
        Payment Intent 생성
        
        Args:
            amount: 금액 (센트 단위, 예: 1000 = $10.00)
            currency: 통화 코드
            customer: Stripe Customer ID
            payment_method: Payment Method ID
            metadata: 메타데이터
            description: 설명
            automatic_payment_methods: 자동 결제 수단 활성화
            
        Returns:
            Stripe PaymentIntent 객체
        """
        try:
            params = {
                'amount': amount,
                'currency': currency,
                'metadata': metadata or {},
            }
            
            if description:
                params['description'] = description
            
            if customer:
                params['customer'] = customer
            
            if payment_method:
                params['payment_method'] = payment_method
                params['confirm'] = True
            
            if automatic_payment_methods:
                params['automatic_payment_methods'] = {'enabled': True}
            
            payment_intent = stripe.PaymentIntent.create(**params)
            logger.info(f"Payment Intent 생성: {payment_intent.id}")
            return payment_intent
            
        except stripe.error.StripeError as e:
            logger.error(f"Payment Intent 생성 실패: {str(e)}")
            raise StripeClientError(f"결제 생성 실패: {str(e)}")
    
    def retrieve_payment_intent(self, payment_intent_id: str) -> stripe.PaymentIntent:
        """Payment Intent 조회"""
        try:
            return stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.StripeError as e:
            logger.error(f"Payment Intent 조회 실패: {str(e)}")
            raise StripeClientError(f"결제 조회 실패: {str(e)}")
    
    def confirm_payment_intent(
        self,
        payment_intent_id: str,
        payment_method: Optional[str] = None
    ) -> stripe.PaymentIntent:
        """Payment Intent 확인"""
        try:
            params = {}
            if payment_method:
                params['payment_method'] = payment_method
            
            return stripe.PaymentIntent.confirm(payment_intent_id, **params)
        except stripe.error.StripeError as e:
            logger.error(f"Payment Intent 확인 실패: {str(e)}")
            raise StripeClientError(f"결제 확인 실패: {str(e)}")
    
    def cancel_payment_intent(self, payment_intent_id: str) -> stripe.PaymentIntent:
        """Payment Intent 취소"""
        try:
            return stripe.PaymentIntent.cancel(payment_intent_id)
        except stripe.error.StripeError as e:
            logger.error(f"Payment Intent 취소 실패: {str(e)}")
            raise StripeClientError(f"결제 취소 실패: {str(e)}")
    
    # ===== Refund 관리 =====
    
    def create_refund(
        self,
        payment_intent_id: str,
        amount: Optional[int] = None,
        reason: Optional[str] = None
    ) -> stripe.Refund:
        """
        환불 생성
        
        Args:
            payment_intent_id: Payment Intent ID
            amount: 환불 금액 (None이면 전액 환불)
            reason: 환불 사유
            
        Returns:
            Stripe Refund 객체
        """
        try:
            params = {'payment_intent': payment_intent_id}
            
            if amount:
                params['amount'] = amount
            
            if reason:
                params['reason'] = reason
            
            refund = stripe.Refund.create(**params)
            logger.info(f"환불 생성: {refund.id}")
            return refund
            
        except stripe.error.StripeError as e:
            logger.error(f"환불 생성 실패: {str(e)}")
            raise StripeClientError(f"환불 실패: {str(e)}")
    
    # ===== Subscription 관리 =====
    
    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_period_days: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> stripe.Subscription:
        """
        구독 생성
        
        Args:
            customer_id: Stripe Customer ID
            price_id: Stripe Price ID
            trial_period_days: 체험 기간 (일)
            metadata: 메타데이터
            
        Returns:
            Stripe Subscription 객체
        """
        try:
            params = {
                'customer': customer_id,
                'items': [{'price': price_id}],
                'metadata': metadata or {},
            }
            
            if trial_period_days:
                params['trial_period_days'] = trial_period_days
            
            subscription = stripe.Subscription.create(**params)
            logger.info(f"구독 생성: {subscription.id}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"구독 생성 실패: {str(e)}")
            raise StripeClientError(f"구독 생성 실패: {str(e)}")
    
    def retrieve_subscription(self, subscription_id: str) -> stripe.Subscription:
        """구독 조회"""
        try:
            return stripe.Subscription.retrieve(subscription_id)
        except stripe.error.StripeError as e:
            logger.error(f"구독 조회 실패: {str(e)}")
            raise StripeClientError(f"구독 조회 실패: {str(e)}")
    
    def cancel_subscription(
        self,
        subscription_id: str,
        cancel_at_period_end: bool = True
    ) -> stripe.Subscription:
        """
        구독 취소
        
        Args:
            subscription_id: Subscription ID
            cancel_at_period_end: 기간 종료 시 취소 여부
            
        Returns:
            Stripe Subscription 객체
        """
        try:
            if cancel_at_period_end:
                # 현재 주기 종료 시 취소
                return stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                # 즉시 취소
                return stripe.Subscription.delete(subscription_id)
                
        except stripe.error.StripeError as e:
            logger.error(f"구독 취소 실패: {str(e)}")
            raise StripeClientError(f"구독 취소 실패: {str(e)}")
    
    # ===== Product & Price 관리 =====
    
    def create_product(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> stripe.Product:
        """상품 생성"""
        try:
            return stripe.Product.create(
                name=name,
                description=description,
                metadata=metadata or {}
            )
        except stripe.error.StripeError as e:
            logger.error(f"상품 생성 실패: {str(e)}")
            raise StripeClientError(f"상품 생성 실패: {str(e)}")
    
    def create_price(
        self,
        product_id: str,
        amount: int,
        currency: str = 'usd',
        recurring: Optional[Dict] = None
    ) -> stripe.Price:
        """
        가격 생성
        
        Args:
            product_id: Product ID
            amount: 금액 (센트)
            currency: 통화
            recurring: 정기 결제 설정 {'interval': 'month', 'interval_count': 1}
            
        Returns:
            Stripe Price 객체
        """
        try:
            params = {
                'product': product_id,
                'unit_amount': amount,
                'currency': currency,
            }
            
            if recurring:
                params['recurring'] = recurring
            
            return stripe.Price.create(**params)
            
        except stripe.error.StripeError as e:
            logger.error(f"가격 생성 실패: {str(e)}")
            raise StripeClientError(f"가격 생성 실패: {str(e)}")
```

이제 핵심 모델과 Stripe 클라이언트가 완성되었습니다. 다음 섹션에서는 결제 API를 구현하겠습니다.

