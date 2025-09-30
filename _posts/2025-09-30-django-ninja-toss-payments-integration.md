---
layout: post
title: "Django Ninja로 Toss Payments 결제 시스템 구축하기 - 초보자 완벽 가이드"
date: 2025-09-30 10:00:00 +0900
categories: [Web Development, Backend, Payment]
tags: [django, django-ninja, toss-payments, payment-integration, fintech, e-commerce]
description: "Django Ninja와 Toss Payments API를 활용하여 안전하고 신뢰할 수 있는 결제 시스템을 구축하는 방법을 초보자도 쉽게 이해할 수 있도록 단계별로 설명합니다. 결제 승인부터 웹훅 처리까지 완전한 결제 플로우를 구현해보겠습니다."
author: "updaun"
image: "/assets/img/posts/2025-09-30-django-ninja-toss-payments-integration.webp"
---

## 개요

현대 웹 서비스에서 결제 기능은 필수적입니다. 특히 한국에서는 Toss Payments가 간편하고 안전한 결제 솔루션으로 널리 사용되고 있습니다. Django Ninja를 활용하여 Toss Payments와 연동하는 완전한 결제 시스템을 구축하는 방법을 알아보겠습니다.

## Toss Payments의 장점

### 1. 간편한 연동
- **SDK 제공**: 다양한 언어와 프레임워크 지원
- **풍부한 문서**: 상세한 API 문서와 예제 코드
- **테스트 환경**: 샌드박스 환경에서 안전한 테스트 가능

### 2. 다양한 결제 수단
- **카드 결제**: 신용카드, 체크카드
- **간편 결제**: 토스페이, 페이코, 카카오페이 등
- **계좌 이체**: 실시간 계좌이체
- **가상계좌**: 무통장 입금

### 3. 강력한 보안
- **PCI DSS 인증**: 국제 보안 표준 준수
- **암호화 통신**: TLS 1.2 이상 사용
- **웹훅 검증**: 요청 무결성 보장

### 4. 편리한 관리
- **대시보드**: 실시간 결제 현황 모니터링
- **정산 관리**: 자동 정산 및 세금계산서 발행
- **통계 분석**: 상세한 결제 데이터 분석

## 프로젝트 설정

### 1. 의존성 설치

```bash
# 가상환경 생성 및 활성화
python -m venv toss_payments_env
source toss_payments_env/bin/activate  # Linux/Mac
# toss_payments_env\Scripts\activate  # Windows

# 필수 패키지 설치
pip install django django-ninja
pip install requests python-decouple
pip install celery redis django-redis
pip install cryptography pyjwt
pip install django-cors-headers
pip install Pillow  # 이미지 처리용

# requirements.txt 생성
pip freeze > requirements.txt
```

### 2. Django 프로젝트 생성

```bash
# Django 프로젝트 생성
django-admin startproject toss_payment_project
cd toss_payment_project

# 결제 앱 생성
python manage.py startapp payments

# 데이터베이스 마이그레이션
python manage.py makemigrations
python manage.py migrate

# 관리자 계정 생성
python manage.py createsuperuser
```

### 3. Django 설정

```python
# settings.py
import os
from decouple import config
from datetime import timedelta

# 기본 Django 설정
DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('SECRET_KEY')

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# 데이터베이스 설정
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # 개발용
        'NAME': BASE_DIR / 'db.sqlite3',
        # 실제 운영환경에서는 PostgreSQL 사용 권장
        # 'ENGINE': 'django.db.backends.postgresql',
        # 'NAME': config('DB_NAME'),
        # 'USER': config('DB_USER'),
        # 'PASSWORD': config('DB_PASSWORD'),
        # 'HOST': config('DB_HOST', default='localhost'),
        # 'PORT': config('DB_PORT', default='5432'),
    }
}

# Toss Payments 설정
TOSS_PAYMENTS_SETTINGS = {
    # API 키 설정 (테스트/라이브)
    'CLIENT_KEY': config('TOSS_CLIENT_KEY'),  # 클라이언트 키 (프론트엔드용)
    'SECRET_KEY': config('TOSS_SECRET_KEY'),  # 시크릿 키 (서버용)
    'IS_SANDBOX': config('TOSS_IS_SANDBOX', default=True, cast=bool),  # 테스트 환경 여부
    
    # API URL
    'API_BASE_URL': 'https://api.tosspayments.com' if not config('TOSS_IS_SANDBOX', default=True, cast=bool) 
                   else 'https://api.tosspayments.com',  # 샌드박스와 라이브 URL 동일
    
    # 결제 설정
    'CURRENCY': 'KRW',  # 통화
    'MAX_PAYMENT_AMOUNT': 10000000,  # 최대 결제 금액 (1천만원)
    'MIN_PAYMENT_AMOUNT': 100,  # 최소 결제 금액 (100원)
    
    # 콜백 URL 설정
    'SUCCESS_URL': config('TOSS_SUCCESS_URL', default='http://localhost:3000/payment/success'),
    'FAIL_URL': config('TOSS_FAIL_URL', default='http://localhost:3000/payment/fail'),
    'WEBHOOK_URL': config('TOSS_WEBHOOK_URL', default='http://localhost:8000/api/payments/webhook'),
    
    # 타임아웃 설정
    'PAYMENT_TIMEOUT_MINUTES': 30,  # 결제 대기 시간
    'API_TIMEOUT_SECONDS': 30,  # API 요청 타임아웃
}

# 캐시 설정 (결제 상태 관리용)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Celery 설정 (비동기 작업용)
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'

# 미디어 파일 설정
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# CORS 설정 (프론트엔드 연동용)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React 개발 서버
    "http://127.0.0.1:3000",
    config('FRONTEND_URL', default='http://localhost:3000'),
]

CORS_ALLOW_CREDENTIALS = True

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'payments.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'payments': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'payments',  # 결제 앱
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

ROOT_URLCONF = 'toss_payment_project.urls'

# 보안 설정
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# 세션 설정
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600  # 1시간

# CSRF 설정
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
```

### 4. 환경변수 설정

```bash
# .env 파일 생성
DEBUG=True
SECRET_KEY=your-secret-key-here

# Toss Payments 설정 (테스트 키)
TOSS_CLIENT_KEY=test_ck_D5GePWvyJnrK0W0k6q8gLzN97Eoqo56A
TOSS_SECRET_KEY=test_sk_zXLkKEypNArWmo50nX3lmeaxYG5R
TOSS_IS_SANDBOX=True

# URL 설정
TOSS_SUCCESS_URL=http://localhost:3000/payment/success
TOSS_FAIL_URL=http://localhost:3000/payment/fail
TOSS_WEBHOOK_URL=http://localhost:8000/api/payments/webhook
FRONTEND_URL=http://localhost:3000

# Redis 설정
REDIS_URL=redis://localhost:6379/0

# 데이터베이스 설정 (PostgreSQL 사용시)
# DB_NAME=toss_payments
# DB_USER=postgres
# DB_PASSWORD=your-password
# DB_HOST=localhost
# DB_PORT=5432
```

## 데이터 모델 설계

### 1. 결제 관련 모델

```python
# payments/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import datetime, timedelta
import uuid
import json

class PaymentMethod(models.Model):
    """결제 수단 관리"""
    
    class MethodType(models.TextChoices):
        CARD = 'card', '카드'
        TRANSFER = 'transfer', '계좌이체'
        VIRTUAL_ACCOUNT = 'virtual_account', '가상계좌'
        MOBILE_PHONE = 'mobile_phone', '휴대폰'
        GIFT_CERTIFICATE = 'gift_certificate', '상품권'
        EASY_PAY = 'easy_pay', '간편결제'
    
    name = models.CharField(max_length=50, unique=True)
    method_type = models.CharField(max_length=20, choices=MethodType.choices)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    
    # 수수료 설정
    fee_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)  # 수수료율 (%)
    fixed_fee = models.PositiveIntegerField(default=0)  # 고정 수수료 (원)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_method_type_display()})"

class Product(models.Model):
    """상품 관리"""
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.PositiveIntegerField(validators=[MinValueValidator(100)])  # 최소 100원
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    
    # 재고 관리
    stock_quantity = models.PositiveIntegerField(default=0)
    is_digital = models.BooleanField(default=False)  # 디지털 상품 여부
    
    # 상태 관리
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def is_available(self, quantity=1):
        """재고 확인"""
        if self.is_digital:
            return True
        return self.stock_quantity >= quantity

class Order(models.Model):
    """주문 관리"""
    
    class OrderStatus(models.TextChoices):
        PENDING = 'pending', '결제 대기'
        PAID = 'paid', '결제 완료'
        CANCELLED = 'cancelled', '주문 취소'
        REFUNDED = 'refunded', '환불 완료'
        PARTIAL_REFUNDED = 'partial_refunded', '부분 환불'
        SHIPPED = 'shipped', '배송 중'
        DELIVERED = 'delivered', '배송 완료'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.CharField(max_length=50, unique=True)  # Toss에서 사용할 주문 ID
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    
    # 주문 정보
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    total_amount = models.PositiveIntegerField()  # 총 주문 금액
    discount_amount = models.PositiveIntegerField(default=0)  # 할인 금액
    shipping_fee = models.PositiveIntegerField(default=0)  # 배송비
    final_amount = models.PositiveIntegerField()  # 최종 결제 금액
    
    # 배송 정보
    shipping_name = models.CharField(max_length=50, blank=True)
    shipping_phone = models.CharField(max_length=20, blank=True)
    shipping_address = models.TextField(blank=True)
    shipping_memo = models.TextField(blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order_id} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            # 주문 ID 자동 생성 (날짜 + UUID 조합)
            today = datetime.now().strftime('%Y%m%d')
            short_uuid = str(uuid.uuid4()).replace('-', '')[:8].upper()
            self.order_id = f"ORD{today}{short_uuid}"
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    """주문 상품 관리"""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.PositiveIntegerField()  # 주문 당시 상품 가격
    total_price = models.PositiveIntegerField()  # quantity * unit_price
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

class Payment(models.Model):
    """결제 정보 관리"""
    
    class PaymentStatus(models.TextChoices):
        READY = 'ready', '결제 준비'
        IN_PROGRESS = 'in_progress', '결제 진행중'
        WAITING_FOR_DEPOSIT = 'waiting_for_deposit', '입금 대기'
        DONE = 'done', '결제 완료'
        CANCELED = 'canceled', '결제 취소'
        PARTIAL_CANCELED = 'partial_canceled', '부분 취소'
        ABORTED = 'aborted', '결제 중단'
        EXPIRED = 'expired', '결제 만료'
    
    class PaymentProvider(models.TextChoices):
        TOSS = 'toss', 'Toss Payments'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_key = models.CharField(max_length=200, unique=True, blank=True)  # Toss 결제 키
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    
    # 결제 정보
    provider = models.CharField(max_length=20, choices=PaymentProvider.choices, default=PaymentProvider.TOSS)
    method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=30, choices=PaymentStatus.choices, default=PaymentStatus.READY)
    
    # 금액 정보
    amount = models.PositiveIntegerField()  # 결제 요청 금액
    balance_amount = models.PositiveIntegerField(default=0)  # 잔액 (부분취소 시 사용)
    supplied_amount = models.PositiveIntegerField(default=0)  # 공급가액
    vat = models.PositiveIntegerField(default=0)  # 부가세
    
    # Toss 관련 정보
    toss_payment_key = models.CharField(max_length=200, blank=True)
    toss_transaction_key = models.CharField(max_length=200, blank=True)
    toss_order_id = models.CharField(max_length=64, blank=True)
    
    # 결제 수단별 상세 정보 (JSON)
    method_details = models.JSONField(default=dict, blank=True)
    
    # 실패 정보
    failure_code = models.CharField(max_length=50, blank=True)
    failure_message = models.TextField(blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_key']),
            models.Index(fields=['toss_payment_key']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.payment_key} - {self.amount}원"
    
    def is_success(self):
        return self.status == self.PaymentStatus.DONE
    
    def is_failed(self):
        return self.status in [
            self.PaymentStatus.CANCELED,
            self.PaymentStatus.ABORTED,
            self.PaymentStatus.EXPIRED
        ]
    
    def set_expires_at(self, minutes=30):
        """결제 만료 시간 설정"""
        self.expires_at = timezone.now() + timedelta(minutes=minutes)

class PaymentEvent(models.Model):
    """결제 이벤트 로그"""
    
    class EventType(models.TextChoices):
        PAYMENT_CREATED = 'payment_created', '결제 생성'
        PAYMENT_APPROVED = 'payment_approved', '결제 승인'
        PAYMENT_CANCELED = 'payment_canceled', '결제 취소'
        PAYMENT_FAILED = 'payment_failed', '결제 실패'
        WEBHOOK_RECEIVED = 'webhook_received', '웹훅 수신'
        REFUND_REQUESTED = 'refund_requested', '환불 요청'
        REFUND_COMPLETED = 'refund_completed', '환불 완료'
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    
    # 이벤트 상세 정보
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # 요청 정보
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment', 'event_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.payment.payment_key} - {self.get_event_type_display()}"

class Refund(models.Model):
    """환불 관리"""
    
    class RefundStatus(models.TextChoices):
        PENDING = 'pending', '환불 대기'
        IN_PROGRESS = 'in_progress', '환불 진행중'
        COMPLETED = 'completed', '환불 완료'
        FAILED = 'failed', '환불 실패'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    
    # 환불 정보
    refund_amount = models.PositiveIntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=RefundStatus.choices, default=RefundStatus.PENDING)
    
    # Toss 환불 정보
    toss_refund_key = models.CharField(max_length=200, blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # 실패 정보
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Refund {self.id} - {self.refund_amount}원"
```

이제 다음 단계로 넘어가겠습니다. 계속해서 서비스 클래스를 구현하겠습니다.
