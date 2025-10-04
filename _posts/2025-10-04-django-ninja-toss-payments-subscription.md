---
layout: post
title: "Django Ninja + Toss Payments로 구독 결제 시스템 구축하기"
date: 2025-10-04 10:00:00 +0900
categories: [Django, Python, Payment, Subscription]
tags: [Django, Python, Django-Ninja, Toss-Payments, Subscription, Payment, FastAPI, API, Backend]
---

구독 기반 서비스가 급증하면서 안정적이고 확장 가능한 결제 시스템의 중요성이 커지고 있습니다. 이 글에서는 Django Ninja와 Toss Payments를 활용하여 구독 결제 시스템을 구축하는 전체 과정을 단계별로 살펴보겠습니다.

## 🎯 왜 Django Ninja + Toss Payments인가?

### Django Ninja의 장점
- **FastAPI 스타일**: 타입 힌트 기반의 직관적인 API 개발
- **자동 문서화**: Swagger UI 자동 생성
- **Django 생태계**: Django ORM, Admin 등 기존 도구 활용 가능
- **높은 성능**: Pydantic 기반 검증으로 빠른 처리 속도

### Toss Payments의 장점
- **간편한 연동**: 직관적인 API와 풍부한 문서
- **다양한 결제 수단**: 카드, 계좌이체, 간편결제 등
- **정기결제 지원**: 구독 서비스에 최적화된 빌링키 시스템
- **안정성**: 대규모 트래픽 처리 경험

## 🚀 프로젝트 설정

### 1. 필수 패키지 설치

```bash
pip install django
pip install django-ninja
pip install requests
pip install python-decouple
pip install django-cors-headers
```

### 2. Django 프로젝트 초기 설정

```python
# settings.py
import os
from decouple import config

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'subscriptions',  # 구독 앱
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

# Toss Payments 설정
TOSS_CLIENT_KEY = config('TOSS_CLIENT_KEY')
TOSS_SECRET_KEY = config('TOSS_SECRET_KEY')
TOSS_BASE_URL = 'https://api.tosspayments.com/v1'

# CORS 설정 (개발 환경)
CORS_ALLOW_ALL_ORIGINS = True  # 프로덕션에서는 특정 도메인만 허용
```

## 📊 데이터 모델 설계

### 구독 관련 모델

```python
# subscriptions/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class SubscriptionPlan(models.Model):
    """구독 플랜"""
    PLAN_TYPES = [
        ('BASIC', '베이직'),
        ('PREMIUM', '프리미엄'),
        ('ENTERPRISE', '엔터프라이즈'),
    ]
    
    BILLING_CYCLES = [
        ('MONTHLY', '월간'),
        ('QUARTERLY', '분기'),
        ('YEARLY', '연간'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name='플랜명')
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='가격')
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLES)
    features = models.JSONField(default=list, verbose_name='제공 기능')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '구독 플랜'
        verbose_name_plural = '구독 플랜들'
    
    def __str__(self):
        return f"{self.name} ({self.get_billing_cycle_display()})"

class Subscription(models.Model):
    """사용자 구독"""
    STATUSES = [
        ('ACTIVE', '활성'),
        ('INACTIVE', '비활성'),
        ('CANCELLED', '취소됨'),
        ('EXPIRED', '만료됨'),
        ('PENDING', '대기중'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUSES, default='PENDING')
    
    # 결제 관련 정보
    billing_key = models.CharField(max_length=255, null=True, blank=True)
    customer_key = models.CharField(max_length=255, unique=True)
    
    # 구독 기간
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    next_billing_date = models.DateTimeField(null=True, blank=True)
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '구독'
        verbose_name_plural = '구독들'
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"
    
    def is_active(self):
        """구독이 활성 상태인지 확인"""
        return (
            self.status == 'ACTIVE' and 
            self.end_date and 
            self.end_date > timezone.now()
        )

class Payment(models.Model):
    """결제 내역"""
    PAYMENT_TYPES = [
        ('SUBSCRIPTION', '구독 결제'),
        ('ONE_TIME', '일회성 결제'),
    ]
    
    STATUSES = [
        ('PENDING', '대기중'),
        ('COMPLETED', '완료'),
        ('FAILED', '실패'),
        ('CANCELLED', '취소'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUSES, default='PENDING')
    
    # Toss Payments 관련 정보
    toss_payment_key = models.CharField(max_length=255, unique=True)
    toss_order_id = models.CharField(max_length=255, unique=True)
    
    # 결제 상세 정보
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '결제'
        verbose_name_plural = '결제들'
    
    def __str__(self):
        return f"{self.subscription.user.username} - {self.amount}원"
```

## 🔧 Toss Payments 서비스 클래스

```python
# subscriptions/services.py
import requests
import base64
from django.conf import settings
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class TossPaymentsService:
    """Toss Payments API 서비스"""
    
    def __init__(self):
        self.base_url = settings.TOSS_BASE_URL
        self.secret_key = settings.TOSS_SECRET_KEY
        self.headers = {
            'Authorization': f'Basic {self._get_auth_header()}',
            'Content-Type': 'application/json',
        }
    
    def _get_auth_header(self) -> str:
        """인증 헤더 생성"""
        auth_string = f"{self.secret_key}:"
        return base64.b64encode(auth_string.encode()).decode()
    
    def confirm_payment(self, payment_key: str, order_id: str, amount: int) -> Dict[str, Any]:
        """결제 승인"""
        url = f"{self.base_url}/payments/confirm"
        data = {
            "paymentKey": payment_key,
            "orderId": order_id,
            "amount": amount
        }
        
        try:
            response = requests.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"결제 승인 실패: {e}")
            raise
    
    def issue_billing_key(self, customer_key: str, auth_key: str) -> Dict[str, Any]:
        """빌링키 발급"""
        url = f"{self.base_url}/billing/authorizations/issue"
        data = {
            "customerKey": customer_key,
            "authKey": auth_key
        }
        
        try:
            response = requests.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"빌링키 발급 실패: {e}")
            raise
    
    def charge_billing_key(self, billing_key: str, customer_key: str, 
                          order_id: str, amount: int, order_name: str) -> Dict[str, Any]:
        """빌링키로 결제 실행"""
        url = f"{self.base_url}/billing/{billing_key}"
        data = {
            "customerKey": customer_key,
            "amount": amount,
            "orderId": order_id,
            "orderName": order_name
        }
        
        try:
            response = requests.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"빌링키 결제 실패: {e}")
            raise
    
    def get_payment_info(self, payment_key: str) -> Dict[str, Any]:
        """결제 정보 조회"""
        url = f"{self.base_url}/payments/{payment_key}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"결제 정보 조회 실패: {e}")
            raise
    
    def cancel_payment(self, payment_key: str, cancel_reason: str, 
                      cancel_amount: Optional[int] = None) -> Dict[str, Any]:
        """결제 취소"""
        url = f"{self.base_url}/payments/{payment_key}/cancel"
        data = {
            "cancelReason": cancel_reason
        }
        
        if cancel_amount:
            data["cancelAmount"] = cancel_amount
        
        try:
            response = requests.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"결제 취소 실패: {e}")
            raise
```

## 🎨 Django Ninja API 구현

### 스키마 정의

```python
# subscriptions/schemas.py
from ninja import Schema
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

class SubscriptionPlanSchema(Schema):
    id: str
    name: str
    plan_type: str
    price: Decimal
    billing_cycle: str
    features: List[str]
    is_active: bool

class CreateSubscriptionSchema(Schema):
    plan_id: str
    customer_key: str

class PaymentConfirmSchema(Schema):
    payment_key: str
    order_id: str
    amount: int

class BillingKeyIssueSchema(Schema):
    customer_key: str
    auth_key: str

class SubscriptionSchema(Schema):
    id: str
    plan: SubscriptionPlanSchema
    status: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None
    created_at: datetime

class PaymentSchema(Schema):
    id: str
    amount: Decimal
    status: str
    payment_method: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime

class ErrorSchema(Schema):
    message: str
    code: Optional[str] = None
```

### API 엔드포인트

```python
# subscriptions/api.py
from ninja import Router
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
import uuid
import logging

from .models import SubscriptionPlan, Subscription, Payment
from .schemas import (
    SubscriptionPlanSchema, CreateSubscriptionSchema, PaymentConfirmSchema,
    BillingKeyIssueSchema, SubscriptionSchema, PaymentSchema, ErrorSchema
)
from .services import TossPaymentsService

logger = logging.getLogger(__name__)
router = Router()

@router.get("/plans", response=List[SubscriptionPlanSchema])
def list_subscription_plans(request):
    """구독 플랜 목록 조회"""
    plans = SubscriptionPlan.objects.filter(is_active=True)
    return plans

@router.post("/subscribe", response={201: SubscriptionSchema, 400: ErrorSchema})
@method_decorator(login_required)
def create_subscription(request, data: CreateSubscriptionSchema):
    """구독 생성"""
    try:
        plan = get_object_or_404(SubscriptionPlan, id=data.plan_id, is_active=True)
        
        # 이미 활성 구독이 있는지 확인
        existing_subscription = Subscription.objects.filter(
            user=request.user,
            status='ACTIVE'
        ).first()
        
        if existing_subscription:
            return 400, {"message": "이미 활성 구독이 있습니다."}
        
        # 새 구독 생성
        subscription = Subscription.objects.create(
            user=request.user,
            plan=plan,
            customer_key=data.customer_key,
            status='PENDING'
        )
        
        return 201, subscription
        
    except Exception as e:
        logger.error(f"구독 생성 실패: {e}")
        return 400, {"message": "구독 생성에 실패했습니다."}

@router.post("/payments/confirm", response={200: PaymentSchema, 400: ErrorSchema})
@method_decorator(login_required)
def confirm_payment(request, data: PaymentConfirmSchema):
    """결제 승인"""
    try:
        toss_service = TossPaymentsService()
        
        # Toss Payments 결제 승인
        payment_result = toss_service.confirm_payment(
            payment_key=data.payment_key,
            order_id=data.order_id,
            amount=data.amount
        )
        
        # 주문 ID로 구독 찾기
        subscription = get_object_or_404(
            Subscription, 
            customer_key=payment_result['customerKey']
        )
        
        # 결제 정보 저장
        payment = Payment.objects.create(
            subscription=subscription,
            payment_type='SUBSCRIPTION',
            amount=Decimal(str(data.amount)),
            status='COMPLETED',
            toss_payment_key=data.payment_key,
            toss_order_id=data.order_id,
            payment_method=payment_result.get('method'),
            paid_at=timezone.now()
        )
        
        # 구독 활성화
        subscription.status = 'ACTIVE'
        subscription.start_date = timezone.now()
        
        # 다음 결제일 계산
        if subscription.plan.billing_cycle == 'MONTHLY':
            next_billing = timezone.now().replace(day=1) + timezone.timedelta(days=32)
            next_billing = next_billing.replace(day=1)
        elif subscription.plan.billing_cycle == 'YEARLY':
            next_billing = timezone.now().replace(year=timezone.now().year + 1)
        
        subscription.next_billing_date = next_billing
        subscription.end_date = next_billing
        subscription.save()
        
        return 200, payment
        
    except Exception as e:
        logger.error(f"결제 승인 실패: {e}")
        return 400, {"message": "결제 승인에 실패했습니다."}

@router.post("/billing/issue", response={200: dict, 400: ErrorSchema})
@method_decorator(login_required)
def issue_billing_key(request, data: BillingKeyIssueSchema):
    """빌링키 발급"""
    try:
        toss_service = TossPaymentsService()
        
        # 빌링키 발급
        billing_result = toss_service.issue_billing_key(
            customer_key=data.customer_key,
            auth_key=data.auth_key
        )
        
        # 구독에 빌링키 저장
        subscription = get_object_or_404(
            Subscription, 
            customer_key=data.customer_key,
            user=request.user
        )
        
        subscription.billing_key = billing_result['billingKey']
        subscription.save()
        
        return 200, {
            "billing_key": billing_result['billingKey'],
            "message": "빌링키가 성공적으로 발급되었습니다."
        }
        
    except Exception as e:
        logger.error(f"빌링키 발급 실패: {e}")
        return 400, {"message": "빌링키 발급에 실패했습니다."}

@router.get("/my-subscriptions", response=List[SubscriptionSchema])
@method_decorator(login_required)
def my_subscriptions(request):
    """내 구독 목록 조회"""
    subscriptions = Subscription.objects.filter(user=request.user).select_related('plan')
    return subscriptions

@router.post("/cancel/{subscription_id}", response={200: dict, 400: ErrorSchema})
@method_decorator(login_required)
def cancel_subscription(request, subscription_id: str):
    """구독 취소"""
    try:
        subscription = get_object_or_404(
            Subscription, 
            id=subscription_id, 
            user=request.user
        )
        
        if subscription.status != 'ACTIVE':
            return 400, {"message": "활성 구독이 아닙니다."}
        
        subscription.status = 'CANCELLED'
        subscription.save()
        
        return 200, {"message": "구독이 취소되었습니다."}
        
    except Exception as e:
        logger.error(f"구독 취소 실패: {e}")
        return 400, {"message": "구독 취소에 실패했습니다."}
```

### 메인 API 설정

```python
# main/api.py
from ninja import NinjaAPI
from subscriptions.api import router as subscriptions_router

api = NinjaAPI(
    title="Subscription API",
    description="Django Ninja + Toss Payments 구독 시스템",
    version="1.0.0"
)

api.add_router("/subscriptions", subscriptions_router)
```

```python
# urls.py
from django.contrib import admin
from django.urls import path
from main.api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
```

## 🔄 정기결제 자동화

### Celery를 활용한 정기결제

```python
# subscriptions/tasks.py
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import uuid
import logging

from .models import Subscription, Payment
from .services import TossPaymentsService

logger = logging.getLogger(__name__)

@shared_task
def process_recurring_payments():
    """정기결제 처리"""
    today = timezone.now().date()
    
    # 오늘 결제해야 하는 구독들 조회
    subscriptions = Subscription.objects.filter(
        status='ACTIVE',
        next_billing_date__date=today,
        billing_key__isnull=False
    ).select_related('plan', 'user')
    
    logger.info(f"처리할 정기결제: {subscriptions.count()}건")
    
    for subscription in subscriptions:
        try:
            process_subscription_payment.delay(subscription.id)
        except Exception as e:
            logger.error(f"구독 {subscription.id} 결제 작업 스케줄링 실패: {e}")

@shared_task
def process_subscription_payment(subscription_id):
    """개별 구독 결제 처리"""
    try:
        with transaction.atomic():
            subscription = Subscription.objects.select_for_update().get(id=subscription_id)
            
            if subscription.status != 'ACTIVE' or not subscription.billing_key:
                logger.warning(f"구독 {subscription_id}는 결제 조건에 맞지 않습니다.")
                return
            
            toss_service = TossPaymentsService()
            order_id = f"recurring_{subscription.id}_{int(timezone.now().timestamp())}"
            
            # 빌링키로 결제 실행
            payment_result = toss_service.charge_billing_key(
                billing_key=subscription.billing_key,
                customer_key=subscription.customer_key,
                order_id=order_id,
                amount=int(subscription.plan.price),
                order_name=f"{subscription.plan.name} 정기결제"
            )
            
            # 결제 정보 저장
            payment = Payment.objects.create(
                subscription=subscription,
                payment_type='SUBSCRIPTION',
                amount=subscription.plan.price,
                status='COMPLETED',
                toss_payment_key=payment_result['paymentKey'],
                toss_order_id=order_id,
                payment_method=payment_result.get('method'),
                paid_at=timezone.now()
            )
            
            # 다음 결제일 업데이트
            if subscription.plan.billing_cycle == 'MONTHLY':
                next_billing = subscription.next_billing_date + timezone.timedelta(days=30)
            elif subscription.plan.billing_cycle == 'YEARLY':
                next_billing = subscription.next_billing_date.replace(
                    year=subscription.next_billing_date.year + 1
                )
            
            subscription.next_billing_date = next_billing
            subscription.end_date = next_billing
            subscription.save()
            
            logger.info(f"구독 {subscription_id} 정기결제 성공")
            
    except Exception as e:
        logger.error(f"구독 {subscription_id} 정기결제 실패: {e}")
        
        # 결제 실패 처리
        try:
            subscription = Subscription.objects.get(id=subscription_id)
            Payment.objects.create(
                subscription=subscription,
                payment_type='SUBSCRIPTION',
                amount=subscription.plan.price,
                status='FAILED',
                toss_order_id=order_id,
                failure_reason=str(e)
            )
            
            # 3회 연속 실패 시 구독 중지
            recent_failures = Payment.objects.filter(
                subscription=subscription,
                status='FAILED',
                created_at__gte=timezone.now() - timezone.timedelta(days=90)
            ).count()
            
            if recent_failures >= 3:
                subscription.status = 'INACTIVE'
                subscription.save()
                logger.warning(f"구독 {subscription_id} 연속 실패로 인한 비활성화")
                
        except Exception as save_error:
            logger.error(f"결제 실패 정보 저장 오류: {save_error}")
```

## 🎨 프론트엔드 연동

### HTML 결제 페이지

```html
<!-- templates/subscription/payment.html -->
<!DOCTYPE html>
<html>
<head>
    <title>구독 결제</title>
    <script src="https://js.tosspayments.com/v1/payment"></script>
</head>
<body>
    <div id="payment-form">
        <h2>{{ plan.name }} 구독</h2>
        <p>월 {{ plan.price }}원</p>
        
        <button id="payment-button">결제하기</button>
        <button id="billing-button">빌링키 등록</button>
    </div>

    <script>
        const clientKey = '{{ toss_client_key }}';
        const tossPayments = TossPayments(clientKey);
        
        // 일회성 결제
        document.getElementById('payment-button').addEventListener('click', function() {
            const orderId = 'order_' + Date.now();
            
            tossPayments.requestPayment('카드', {
                amount: {{ plan.price }},
                orderId: orderId,
                orderName: '{{ plan.name }} 구독',
                customerName: '{{ user.get_full_name }}',
                customerEmail: '{{ user.email }}',
                successUrl: window.location.origin + '/api/subscriptions/payments/success',
                failUrl: window.location.origin + '/api/subscriptions/payments/fail',
            });
        });
        
        // 빌링키 등록
        document.getElementById('billing-button').addEventListener('click', function() {
            const customerKey = 'customer_{{ user.id }}';
            
            tossPayments.requestBillingAuth('카드', {
                customerKey: customerKey,
                successUrl: window.location.origin + '/api/subscriptions/billing/success',
                failUrl: window.location.origin + '/api/subscriptions/billing/fail',
            });
        });
    </script>
</body>
</html>
```

### JavaScript 클라이언트

```javascript
// static/js/subscription.js
class SubscriptionManager {
    constructor(apiBaseUrl) {
        this.apiBaseUrl = apiBaseUrl;
    }
    
    async getPlans() {
        const response = await fetch(`${this.apiBaseUrl}/subscriptions/plans`);
        return await response.json();
    }
    
    async createSubscription(planId, customerKey) {
        const response = await fetch(`${this.apiBaseUrl}/subscriptions/subscribe`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken(),
            },
            body: JSON.stringify({
                plan_id: planId,
                customer_key: customerKey
            })
        });
        return await response.json();
    }
    
    async confirmPayment(paymentKey, orderId, amount) {
        const response = await fetch(`${this.apiBaseUrl}/subscriptions/payments/confirm`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken(),
            },
            body: JSON.stringify({
                payment_key: paymentKey,
                order_id: orderId,
                amount: amount
            })
        });
        return await response.json();
    }
    
    async issueBillingKey(customerKey, authKey) {
        const response = await fetch(`${this.apiBaseUrl}/subscriptions/billing/issue`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken(),
            },
            body: JSON.stringify({
                customer_key: customerKey,
                auth_key: authKey
            })
        });
        return await response.json();
    }
    
    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
}

// 사용 예시
const subscriptionManager = new SubscriptionManager('/api');

// 구독 플랜 로드
subscriptionManager.getPlans().then(plans => {
    console.log('구독 플랜:', plans);
});
```

## 🔒 보안 및 에러 처리

### 웹훅 보안

```python
# subscriptions/webhooks.py
import hmac
import hashlib
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
import json
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def toss_webhook(request):
    """Toss Payments 웹훅 처리"""
    try:
        # 웹훅 서명 검증
        signature = request.headers.get('TossPayments-Signature')
        if not verify_webhook_signature(request.body, signature):
            logger.warning("웹훅 서명 검증 실패")
            return HttpResponseBadRequest("Invalid signature")
        
        # 웹훅 데이터 파싱
        webhook_data = json.loads(request.body)
        event_type = webhook_data.get('eventType')
        
        # 이벤트 타입별 처리
        if event_type == 'PAYMENT_STATUS_CHANGED':
            handle_payment_status_changed(webhook_data['data'])
        elif event_type == 'BILLING_KEY_STATUS_CHANGED':
            handle_billing_key_status_changed(webhook_data['data'])
        
        return HttpResponse("OK")
        
    except Exception as e:
        logger.error(f"웹훅 처리 실패: {e}")
        return HttpResponseBadRequest("Webhook processing failed")

def verify_webhook_signature(payload, signature):
    """웹훅 서명 검증"""
    expected_signature = hmac.new(
        settings.TOSS_SECRET_KEY.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

def handle_payment_status_changed(payment_data):
    """결제 상태 변경 처리"""
    payment_key = payment_data.get('paymentKey')
    status = payment_data.get('status')
    
    try:
        payment = Payment.objects.get(toss_payment_key=payment_key)
        
        if status == 'DONE':
            payment.status = 'COMPLETED'
        elif status == 'CANCELED':
            payment.status = 'CANCELLED'
        elif status == 'FAILED':
            payment.status = 'FAILED'
            payment.failure_reason = payment_data.get('failureReason')
        
        payment.save()
        logger.info(f"결제 {payment_key} 상태 업데이트: {status}")
        
    except Payment.DoesNotExist:
        logger.warning(f"결제 정보를 찾을 수 없음: {payment_key}")
```

### 에러 처리 및 로깅

```python
# subscriptions/exceptions.py
class SubscriptionError(Exception):
    """구독 관련 에러"""
    pass

class PaymentError(Exception):
    """결제 관련 에러"""
    pass

class BillingKeyError(Exception):
    """빌링키 관련 에러"""
    pass

# subscriptions/decorators.py
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def handle_payment_errors(func):
    """결제 에러 처리 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PaymentError as e:
            logger.error(f"결제 에러: {e}")
            return {"error": "결제 처리 중 오류가 발생했습니다."}
        except Exception as e:
            logger.error(f"예상치 못한 에러: {e}")
            return {"error": "시스템 오류가 발생했습니다."}
    
    return wrapper
```

## 📊 관리자 인터페이스

```python
# subscriptions/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import SubscriptionPlan, Subscription, Payment

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price', 'billing_cycle', 'is_active', 'created_at']
    list_filter = ['plan_type', 'billing_cycle', 'is_active']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'start_date', 'end_date', 'next_billing_date']
    list_filter = ['status', 'plan__plan_type', 'created_at']
    search_fields = ['user__username', 'user__email', 'customer_key']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'plan')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['subscription_user', 'amount', 'status', 'payment_method', 'paid_at']
    list_filter = ['status', 'payment_type', 'payment_method', 'created_at']
    search_fields = ['subscription__user__username', 'toss_payment_key', 'toss_order_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def subscription_user(self, obj):
        return obj.subscription.user.username
    subscription_user.short_description = '사용자'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('subscription__user')
```

## 🧪 테스트 코드

```python
# subscriptions/tests.py
from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from unittest.mock import patch, MagicMock

from .models import SubscriptionPlan, Subscription, Payment
from .services import TossPaymentsService

class SubscriptionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.plan = SubscriptionPlan.objects.create(
            name='베이직 플랜',
            plan_type='BASIC',
            price=Decimal('9900'),
            billing_cycle='MONTHLY'
        )
    
    def test_subscription_creation(self):
        """구독 생성 테스트"""
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            customer_key='test_customer_123'
        )
        
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.plan, self.plan)
        self.assertEqual(subscription.status, 'PENDING')
    
    def test_subscription_is_active(self):
        """구독 활성 상태 확인 테스트"""
        from django.utils import timezone
        
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            customer_key='test_customer_123',
            status='ACTIVE',
            end_date=timezone.now() + timezone.timedelta(days=30)
        )
        
        self.assertTrue(subscription.is_active())

class TossPaymentsServiceTest(TestCase):
    def setUp(self):
        self.service = TossPaymentsService()
    
    @patch('subscriptions.services.requests.post')
    def test_confirm_payment(self, mock_post):
        """결제 승인 테스트"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'paymentKey': 'test_payment_key',
            'orderId': 'test_order_id',
            'amount': 9900,
            'status': 'DONE'
        }
        mock_post.return_value = mock_response
        
        result = self.service.confirm_payment(
            payment_key='test_payment_key',
            order_id='test_order_id',
            amount=9900
        )
        
        self.assertEqual(result['paymentKey'], 'test_payment_key')
        self.assertEqual(result['status'], 'DONE')

class SubscriptionAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.plan = SubscriptionPlan.objects.create(
            name='베이직 플랜',
            plan_type='BASIC',
            price=Decimal('9900'),
            billing_cycle='MONTHLY'
        )
    
    def test_list_plans(self):
        """플랜 목록 조회 테스트"""
        response = self.client.get('/api/subscriptions/plans')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], '베이직 플랜')
    
    def test_create_subscription_unauthorized(self):
        """비인증 사용자 구독 생성 테스트"""
        response = self.client.post('/api/subscriptions/subscribe', {
            'plan_id': str(self.plan.id),
            'customer_key': 'test_customer_123'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 302)  # 로그인 리다이렉트
```

## 🚀 배포 및 운영

### 환경 변수 설정

```bash
# .env
DEBUG=False
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@localhost/dbname

# Toss Payments
TOSS_CLIENT_KEY=test_ck_your_client_key
TOSS_SECRET_KEY=test_sk_your_secret_key

# Celery (Redis)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
```

### Docker 설정

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
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
      - DATABASE_URL=postgresql://postgres:password@db:5432/subscription_db
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: subscription_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:6-alpine
  
  celery:
    build: .
    command: celery -A config worker -l info
    depends_on:
      - db
      - redis
  
  celery-beat:
    build: .
    command: celery -A config beat -l info
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
```

## 🎯 마무리

Django Ninja와 Toss Payments를 활용한 구독 결제 시스템을 성공적으로 구축했습니다. 이 시스템의 주요 특징은 다음과 같습니다:

### ✅ 구현된 핵심 기능
- **구독 플랜 관리**: 다양한 요금제와 결제 주기 지원
- **안전한 결제 처리**: Toss Payments API를 통한 보안 결제
- **정기결제 자동화**: Celery를 통한 스케줄링과 자동 처리
- **빌링키 관리**: 카드 정보 없는 자동 결제 구현
- **웹훅 처리**: 실시간 결제 상태 동기화

### 🔧 기술적 장점
- **타입 안정성**: Pydantic 스키마를 통한 데이터 검증
- **자동 문서화**: Swagger UI를 통한 API 문서 제공
- **확장성**: Django ORM과 Celery를 활용한 확장 가능한 구조
- **보안**: 웹훅 서명 검증과 에러 처리

### 🚀 추후 개선 방향
- **알림 시스템**: 결제 실패, 구독 만료 알림
- **분석 대시보드**: 구독 통계와 매출 분석
- **쿠폰 시스템**: 할인 쿠폰과 프로모션 기능
- **다중 결제수단**: 다양한 PG사 연동

이러한 구독 결제 시스템을 통해 안정적이고 확장 가능한 SaaS 서비스를 구축할 수 있습니다. Django의 강력한 생태계와 Toss Payments의 간편한 API가 만나 개발자 친화적이면서도 사용자에게는 편리한 결제 경험을 제공할 수 있습니다.