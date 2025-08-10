---
layout: post
title: "Django + 토스페이먼츠로 구독 결제 시스템 구현하기: 완전 가이드"
date: 2025-08-08 10:00:00 +0900
categories: [Django, Python, Payment, TossPayments]
tags: [Django, TossPayments, Subscription, Billing, Payment, API, Webhook, 토스페이먼츠, 구독결제, 정기결제]
---

SaaS나 구독 기반 서비스를 개발할 때 가장 중요한 부분 중 하나가 바로 결제 시스템입니다. 특히 한국에서는 토스페이먼츠가 개발자 친화적인 API와 안정적인 서비스로 많은 개발자들의 선택을 받고 있습니다. 이 글에서는 Django와 토스페이먼츠를 활용해 구독 결제 시스템을 처음부터 끝까지 구현하는 방법을 단계별로 알아보겠습니다.

## 🎯 구독 결제 시스템 아키텍처 개요

### 구독 결제 시스템의 핵심 구성요소

구독 결제 시스템을 구현하기 전에 전체적인 아키텍처를 이해해야 합니다:

```
사용자 → Django 앱 → 토스페이먼츠 API
    ↓         ↑              ↓
결제 요청  → 결제 처리 → 결제 승인/실패
    ↓         ↑              ↓
DB 저장   ← 웹훅 수신 ← 상태 변경 알림
```

**주요 컴포넌트:**
- **Subscription Model**: 구독 정보 관리
- **Payment Model**: 결제 내역 관리  
- **Plan Model**: 구독 플랜 정보
- **Webhook Handler**: 토스페이먼츠 상태 변경 처리
- **Billing Service**: 정기 결제 로직

## 📋 사전 준비사항

### 1. 토스페이먼츠 계정 설정

먼저 [토스페이먼츠 개발자센터](https://developers.tosspayments.com/)에서 계정을 생성하고 API 키를 발급받아야 합니다.

```python
# settings.py
TOSS_PAYMENTS_SECRET_KEY = 'test_sk_...'  # 실제 환경에서는 환경변수로 관리
TOSS_PAYMENTS_CLIENT_KEY = 'test_ck_...'
TOSS_PAYMENTS_BASE_URL = 'https://api.tosspayments.com'
```

### 2. 필요한 패키지 설치

```bash
pip install requests
pip install django-environ  # 환경변수 관리용
pip install celery  # 비동기 작업용 (선택사항)
```

## 🗄️ 데이터베이스 모델 설계

### 핵심 모델 구조

```python
# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class SubscriptionPlan(models.Model):
    """구독 플랜 모델"""
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(max_length=20, choices=[
        ('MONTHLY', '월간'),
        ('YEARLY', '연간'),
    ])
    features = models.JSONField(default=dict)  # 플랜별 기능
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.price}원/{self.get_billing_cycle_display()}"

class Subscription(models.Model):
    """구독 모델"""
    STATUS_CHOICES = [
        ('ACTIVE', '활성'),
        ('CANCELED', '취소됨'),
        ('PAST_DUE', '연체'),
        ('PAUSED', '일시정지'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    # 토스페이먼츠 관련 필드
    billing_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    customer_key = models.CharField(max_length=255)
    
    # 구독 기간 관리
    start_date = models.DateTimeField(default=timezone.now)
    next_billing_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    
    # 메타 정보
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"
    
    @property
    def is_active(self):
        return self.status == 'ACTIVE' and (
            not self.end_date or self.end_date > timezone.now()
        )

class Payment(models.Model):
    """결제 내역 모델"""
    STATUS_CHOICES = [
        ('PENDING', '대기중'),
        ('DONE', '완료'),
        ('CANCELED', '취소'),
        ('FAILED', '실패'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    
    # 토스페이먼츠 관련 필드
    payment_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    order_id = models.CharField(max_length=255, unique=True)
    
    # 결제 정보
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    method = models.CharField(max_length=50, null=True, blank=True)  # 카드, 계좌이체 등
    
    # 결제 시점
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # 실패 정보
    failure_code = models.CharField(max_length=50, null=True, blank=True)
    failure_message = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"{self.subscription.user.username} - {self.amount}원 ({self.status})"
```

## 💳 빌링키 등록 및 관리

### 1. 빌링키 등록 프로세스

구독 결제를 위해서는 먼저 사용자의 결제 수단을 등록해야 합니다. 토스페이먼츠에서는 이를 '빌링키'라고 합니다.

```python
# services.py
import requests
import base64
from django.conf import settings
from .models import Subscription, Payment
import uuid

class TossPaymentsService:
    def __init__(self):
        self.secret_key = settings.TOSS_PAYMENTS_SECRET_KEY
        self.base_url = settings.TOSS_PAYMENTS_BASE_URL
        self.headers = {
            'Authorization': f'Basic {self._get_auth_header()}',
            'Content-Type': 'application/json'
        }
    
    def _get_auth_header(self):
        """Basic Auth 헤더 생성"""
        credentials = f"{self.secret_key}:"
        return base64.b64encode(credentials.encode()).decode()
    
    def issue_billing_key(self, customer_key, card_number, card_expiry_year, 
                         card_expiry_month, card_password, customer_identity_number):
        """빌링키 발급"""
        url = f"{self.base_url}/v1/billing/authorizations/issue"
        
        data = {
            "customerKey": customer_key,
            "cardNumber": card_number,
            "cardExpirationYear": card_expiry_year,
            "cardExpirationMonth": card_expiry_month,
            "cardPassword": card_password,
            "customerIdentityNumber": customer_identity_number
        }
        
        try:
            response = requests.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"빌링키 발급 실패: {str(e)}")
    
    def confirm_billing_key(self, billing_key, customer_key):
        """빌링키 확인"""
        url = f"{self.base_url}/v1/billing/authorizations/issue"
        
        data = {
            "billingKey": billing_key,
            "customerKey": customer_key
        }
        
        try:
            response = requests.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"빌링키 확인 실패: {str(e)}")
```

### 2. 프론트엔드 빌링키 등록 구현

```html
<!-- billing_setup.html -->
<!DOCTYPE html>
<html>
<head>
    <title>결제 수단 등록</title>
    <script src="https://js.tosspayments.com/v1/payment"></script>
</head>
<body>
    <div id="billing-form">
        <h2>결제 수단 등록</h2>
        <div id="payment-method"></div>
        <button id="confirm-button">등록하기</button>
    </div>

    <script>
        const clientKey = '{% raw %}{{ toss_client_key }}{% endraw %}';
        const customerKey = '{% raw %}{{ customer_key }}{% endraw %}';
        const tossPayments = TossPayments(clientKey);
        
        // 결제창 위젯 렌더링
        const payment = tossPayments.payment({
            customerKey: customerKey
        });
        
        // 카드 등록 위젯
        const paymentMethodWidget = payment.renderPaymentMethod(
            '#payment-method',
            { variantKey: 'DEFAULT' }
        );
        
        // 등록 버튼 클릭 처리
        document.getElementById('confirm-button').addEventListener('click', async () => {
            try {
                await payment.requestBillingAuth({
                    method: 'CARD',
                    successUrl: window.location.origin + '/billing/success/',
                    failUrl: window.location.origin + '/billing/fail/',
                });
            } catch (error) {
                console.error('빌링키 등록 오류:', error);
                alert('결제 수단 등록에 실패했습니다.');
            }
        });
    </script>
</body>
</html>
```

### 3. 빌링키 등록 뷰 구현

```python
# views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import uuid
import json

@login_required
def billing_setup(request):
    """빌링키 등록 페이지"""
    customer_key = f"customer_{request.user.id}_{uuid.uuid4().hex[:8]}"
    
    context = {
        'toss_client_key': settings.TOSS_PAYMENTS_CLIENT_KEY,
        'customer_key': customer_key,
    }
    return render(request, 'billing_setup.html', context)

@login_required
def billing_success(request):
    """빌링키 등록 성공 처리"""
    auth_key = request.GET.get('authKey')
    customer_key = request.GET.get('customerKey')
    
    if not auth_key or not customer_key:
        messages.error(request, '잘못된 요청입니다.')
        return redirect('billing_setup')
    
    try:
        # 토스페이먼츠 API로 빌링키 확인
        toss_service = TossPaymentsService()
        billing_result = toss_service.confirm_billing_key(auth_key, customer_key)
        
        # 구독 객체에 빌링키 저장
        subscription = get_or_create_subscription(request.user, customer_key)
        subscription.billing_key = billing_result['billingKey']
        subscription.save()
        
        messages.success(request, '결제 수단이 성공적으로 등록되었습니다.')
        return redirect('subscription_plans')
        
    except Exception as e:
        messages.error(request, f'결제 수단 등록에 실패했습니다: {str(e)}')
        return redirect('billing_setup')

@login_required  
def billing_fail(request):
    """빌링키 등록 실패 처리"""
    error_code = request.GET.get('code')
    error_message = request.GET.get('message')
    
    messages.error(request, f'결제 수단 등록에 실패했습니다: {error_message}')
    return redirect('billing_setup')
```

## 🔄 정기 결제 구현

### 1. 정기 결제 서비스 클래스

```python
# services.py (추가)
from datetime import timedelta
from dateutil.relativedelta import relativedelta

class SubscriptionBillingService:
    def __init__(self):
        self.toss_service = TossPaymentsService()
    
    def process_subscription_payment(self, subscription):
        """구독 정기 결제 처리"""
        if not subscription.billing_key:
            raise Exception("빌링키가 등록되지 않았습니다.")
        
        order_id = f"subscription_{subscription.id}_{int(timezone.now().timestamp())}"
        
        try:
            # 토스페이먼츠 정기 결제 요청
            payment_result = self.toss_service.request_billing_payment(
                billing_key=subscription.billing_key,
                customer_key=subscription.customer_key,
                amount=int(subscription.plan.price),
                order_id=order_id,
                order_name=f"{subscription.plan.name} 구독료"
            )
            
            # Payment 객체 생성
            payment = Payment.objects.create(
                subscription=subscription,
                payment_key=payment_result.get('paymentKey'),
                order_id=order_id,
                amount=subscription.plan.price,
                status='DONE' if payment_result.get('status') == 'DONE' else 'FAILED',
                method=payment_result.get('method'),
                approved_at=timezone.now() if payment_result.get('status') == 'DONE' else None
            )
            
            if payment.status == 'DONE':
                # 다음 결제일 계산
                self._update_next_billing_date(subscription)
                messages = f"결제가 완료되었습니다. (결제키: {payment.payment_key})"
            else:
                subscription.status = 'PAST_DUE'
                subscription.save()
                messages = "결제에 실패했습니다."
            
            return payment
            
        except Exception as e:
            # 결제 실패 처리
            Payment.objects.create(
                subscription=subscription,
                order_id=order_id,
                amount=subscription.plan.price,
                status='FAILED',
                failure_message=str(e)
            )
            subscription.status = 'PAST_DUE'
            subscription.save()
            raise e
    
    def _update_next_billing_date(self, subscription):
        """다음 결제일 업데이트"""
        if subscription.plan.billing_cycle == 'MONTHLY':
            subscription.next_billing_date += relativedelta(months=1)
        elif subscription.plan.billing_cycle == 'YEARLY':
            subscription.next_billing_date += relativedelta(years=1)
        
        subscription.save()

# TossPaymentsService 클래스에 추가 메서드
class TossPaymentsService:
    # ... 기존 코드 ...
    
    def request_billing_payment(self, billing_key, customer_key, amount, order_id, order_name):
        """빌링키를 사용한 정기 결제 요청"""
        url = f"{self.base_url}/v1/billing/{billing_key}"
        
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
            raise Exception(f"정기 결제 요청 실패: {str(e)}")
```

### 2. Celery를 활용한 자동 정기 결제

```python
# tasks.py
from celery import shared_task
from django.utils import timezone
from .models import Subscription
from .services import SubscriptionBillingService
import logging

logger = logging.getLogger(__name__)

@shared_task
def process_due_subscriptions():
    """결제일이 도래한 구독들을 처리"""
    today = timezone.now().date()
    due_subscriptions = Subscription.objects.filter(
        status='ACTIVE',
        next_billing_date__date__lte=today,
        billing_key__isnull=False
    )
    
    billing_service = SubscriptionBillingService()
    
    for subscription in due_subscriptions:
        try:
            payment = billing_service.process_subscription_payment(subscription)
            logger.info(f"구독 {subscription.id} 결제 성공: {payment.payment_key}")
        except Exception as e:
            logger.error(f"구독 {subscription.id} 결제 실패: {str(e)}")

@shared_task
def retry_failed_payments():
    """실패한 결제 재시도"""
    from datetime import timedelta
    
    retry_date = timezone.now() - timedelta(days=3)
    failed_subscriptions = Subscription.objects.filter(
        status='PAST_DUE',
        updated_at__gte=retry_date,
        billing_key__isnull=False
    )
    
    billing_service = SubscriptionBillingService()
    
    for subscription in failed_subscriptions:
        try:
            payment = billing_service.process_subscription_payment(subscription)
            subscription.status = 'ACTIVE'
            subscription.save()
            logger.info(f"구독 {subscription.id} 재결제 성공: {payment.payment_key}")
        except Exception as e:
            logger.error(f"구독 {subscription.id} 재결제 실패: {str(e)}")
```

### 3. Celery Beat 스케줄링 설정

```python
# settings.py
from celery.schedules import crontab

# Celery 설정
CELERY_BEAT_SCHEDULE = {
    'process-due-subscriptions': {
        'task': 'subscriptions.tasks.process_due_subscriptions',
        'schedule': crontab(hour=9, minute=0),  # 매일 오전 9시
    },
    'retry-failed-payments': {
        'task': 'subscriptions.tasks.retry_failed_payments',
        'schedule': crontab(hour=10, minute=0),  # 매일 오전 10시
    },
}

CELERY_TIMEZONE = 'Asia/Seoul'
```

## 🔗 웹훅 처리

### 1. 토스페이먼츠 웹훅 핸들러

```python
# webhooks.py
import json
import hmac
import hashlib
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.conf import settings
from .models import Payment, Subscription
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def toss_webhook(request):
    """토스페이먼츠 웹훅 처리"""
    try:
        # 서명 검증
        if not verify_webhook_signature(request):
            logger.warning("웹훅 서명 검증 실패")
            return HttpResponse(status=401)
        
        payload = json.loads(request.body)
        event_type = payload.get('eventType')
        data = payload.get('data', {})
        
        # 결제 완료 이벤트 처리
        if event_type == 'Payment.StatusChanged':
            handle_payment_status_changed(data)
        
        # 빌링키 삭제 이벤트 처리
        elif event_type == 'BillingKey.Deleted':
            handle_billing_key_deleted(data)
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"웹훅 처리 오류: {str(e)}")
        return HttpResponse(status=500)

def verify_webhook_signature(request):
    """웹훅 서명 검증"""
    signature = request.headers.get('TossPayments-Signature')
    if not signature:
        return False
    
    # 실제 환경에서는 토스페이먼츠에서 제공하는 웹훅 서명 검증 로직 구현
    # 현재는 간단한 검증만 수행
    return True

def handle_payment_status_changed(data):
    """결제 상태 변경 처리"""
    payment_key = data.get('paymentKey')
    status = data.get('status')
    order_id = data.get('orderId')
    
    try:
        payment = Payment.objects.get(order_id=order_id)
        
        if status == 'DONE':
            payment.status = 'DONE'
            payment.payment_key = payment_key
            payment.approved_at = timezone.now()
            
            # 구독 상태도 활성화
            subscription = payment.subscription
            if subscription.status == 'PAST_DUE':
                subscription.status = 'ACTIVE'
                subscription.save()
                
        elif status == 'CANCELED':
            payment.status = 'CANCELED'
            
        elif status == 'FAILED':
            payment.status = 'FAILED'
            payment.failure_code = data.get('failure', {}).get('code')
            payment.failure_message = data.get('failure', {}).get('message')
        
        payment.save()
        logger.info(f"결제 {payment_key} 상태 업데이트: {status}")
        
    except Payment.DoesNotExist:
        logger.error(f"결제 정보를 찾을 수 없음: {order_id}")

def handle_billing_key_deleted(data):
    """빌링키 삭제 처리"""
    billing_key = data.get('billingKey')
    customer_key = data.get('customerKey')
    
    try:
        subscription = Subscription.objects.get(
            billing_key=billing_key,
            customer_key=customer_key
        )
        
        # 구독 취소 처리
        subscription.status = 'CANCELED'
        subscription.billing_key = None
        subscription.end_date = timezone.now()
        subscription.save()
        
        logger.info(f"구독 {subscription.id} 빌링키 삭제로 인한 취소")
        
    except Subscription.DoesNotExist:
        logger.error(f"구독 정보를 찾을 수 없음: {billing_key}")
```

### 2. 웹훅 URL 등록

```python
# urls.py
from django.urls import path
from . import webhooks

urlpatterns = [
    # ... 기존 URL 패턴 ...
    path('webhooks/toss/', webhooks.toss_webhook, name='toss_webhook'),
]
```

## 📊 구독 관리 뷰 구현

### 1. 구독 플랜 선택 및 구독 시작

```python
# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SubscriptionPlan, Subscription
from .services import SubscriptionBillingService
from dateutil.relativedelta import relativedelta

@login_required
def subscription_plans(request):
    """구독 플랜 목록"""
    plans = SubscriptionPlan.objects.filter(is_active=True)
    current_subscription = Subscription.objects.filter(
        user=request.user,
        status='ACTIVE'
    ).first()
    
    context = {
        'plans': plans,
        'current_subscription': current_subscription,
    }
    return render(request, 'subscriptions/plans.html', context)

@login_required
def subscribe_to_plan(request, plan_id):
    """구독 플랜 구독"""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
    
    # 기존 활성 구독 확인
    existing_subscription = Subscription.objects.filter(
        user=request.user,
        status='ACTIVE'
    ).first()
    
    if existing_subscription:
        messages.warning(request, '이미 활성화된 구독이 있습니다.')
        return redirect('subscription_detail')
    
    if request.method == 'POST':
        # 빌링키가 등록되어 있는지 확인
        if not hasattr(request.user, 'billing_key') or not request.user.billing_key:
            messages.error(request, '결제 수단을 먼저 등록해주세요.')
            return redirect('billing_setup')
        
        try:
            # 구독 생성
            subscription = Subscription.objects.create(
                user=request.user,
                plan=plan,
                customer_key=f"customer_{request.user.id}_{uuid.uuid4().hex[:8]}",
                billing_key=request.user.billing_key,  # 사용자와 연결된 빌링키
                next_billing_date=calculate_next_billing_date(plan)
            )
            
            # 첫 번째 결제 처리
            billing_service = SubscriptionBillingService()
            payment = billing_service.process_subscription_payment(subscription)
            
            messages.success(request, f'{plan.name} 구독이 시작되었습니다!')
            return redirect('subscription_detail')
            
        except Exception as e:
            messages.error(request, f'구독 생성에 실패했습니다: {str(e)}')
    
    context = {'plan': plan}
    return render(request, 'subscriptions/subscribe.html', context)

@login_required
def subscription_detail(request):
    """구독 상세 정보"""
    subscription = get_object_or_404(
        Subscription,
        user=request.user,
        status='ACTIVE'
    )
    
    recent_payments = subscription.payments.order_by('-requested_at')[:5]
    
    context = {
        'subscription': subscription,
        'recent_payments': recent_payments,
    }
    return render(request, 'subscriptions/detail.html', context)

@login_required
def cancel_subscription(request):
    """구독 취소"""
    subscription = get_object_or_404(
        Subscription,
        user=request.user,
        status='ACTIVE'
    )
    
    if request.method == 'POST':
        subscription.status = 'CANCELED'
        subscription.end_date = timezone.now()
        subscription.save()
        
        messages.success(request, '구독이 취소되었습니다.')
        return redirect('subscription_plans')
    
    context = {'subscription': subscription}
    return render(request, 'subscriptions/cancel.html', context)

def calculate_next_billing_date(plan):
    """다음 결제일 계산"""
    now = timezone.now()
    
    if plan.billing_cycle == 'MONTHLY':
        return now + relativedelta(months=1)
    elif plan.billing_cycle == 'YEARLY':
        return now + relativedelta(years=1)
    else:
        return now + relativedelta(months=1)  # 기본값
```

### 2. 템플릿 구현

```html
<!-- subscriptions/plans.html -->
<div class="subscription-plans">
    <h2>구독 플랜 선택</h2>
    
    {% raw %}{% if current_subscription %}{% endraw %}
        <div class="current-subscription">
            <h3>현재 구독: {% raw %}{{ current_subscription.plan.name }}{% endraw %}</h3>
            <p>다음 결제일: {% raw %}{{ current_subscription.next_billing_date|date:"Y-m-d" }}{% endraw %}</p>
            <a href="{% raw %}{% url 'subscription_detail' %}{% endraw %}" class="btn btn-primary">구독 관리</a>
        </div>
    {% raw %}{% else %}{% endraw %}
        <div class="plans-grid">
            {% raw %}{% for plan in plans %}{% endraw %}
                <div class="plan-card">
                    <h3>{% raw %}{{ plan.name }}{% endraw %}</h3>
                    <div class="price">
                        {% raw %}{{ plan.price|floatformat:0 }}{% endraw %}원
                        <span class="cycle">/ {% raw %}{{ plan.get_billing_cycle_display }}{% endraw %}</span>
                    </div>
                    
                    <ul class="features">
                        {% raw %}{% for feature, value in plan.features.items %}{% endraw %}
                            <li>{% raw %}{{ feature }}{% endraw %}: {% raw %}{{ value }}{% endraw %}</li>
                        {% raw %}{% endfor %}{% endraw %}
                    </ul>
                    
                    <a href="{% raw %}{% url 'subscribe_to_plan' plan.id %}{% endraw %}" class="btn btn-success">
                        구독하기
                    </a>
                </div>
            {% raw %}{% endfor %}{% endraw %}
        </div>
    {% raw %}{% endif %}{% endraw %}
</div>
```

```html
{% raw %}
<!-- subscriptions/detail.html -->
<div class="subscription-detail">
    <h2>구독 관리</h2>
    
    <div class="subscription-info">
        <h3>{{ subscription.plan.name }}</h3>
        <p><strong>상태:</strong> {{ subscription.get_status_display }}</p>
        <p><strong>다음 결제일:</strong> {{ subscription.next_billing_date|date:"Y-m-d H:i" }}</p>
        <p><strong>월/연 요금:</strong> {{ subscription.plan.price|floatformat:0 }}원</p>
    </div>
    
    <div class="subscription-actions">
        <a href="{% url 'cancel_subscription' %}" class="btn btn-danger">구독 취소</a>
        <a href="{% url 'billing_setup' %}" class="btn btn-secondary">결제 수단 변경</a>
    </div>
    
    <div class="payment-history">
        <h3>결제 내역</h3>
        <table class="table">
            <thead>
                <tr>
                    <th>결제일</th>
                    <th>금액</th>
                    <th>상태</th>
                    <th>결제 방법</th>
                </tr>
            </thead>
            <tbody>
                {% for payment in recent_payments %}
                    <tr>
                        <td>{{ payment.requested_at|date:"Y-m-d H:i" }}</td>
                        <td>{{ payment.amount|floatformat:0 }}원</td>
                        <td>
                            <span class="status-badge status-{{ payment.status|lower }}">
                                {{ payment.get_status_display }}
                            </span>
                        </td>
                        <td>{{ payment.method|default:"-" }}</td>
                    </tr>
                {% empty %}
                    <tr>
                        <td colspan="4">결제 내역이 없습니다.</td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endraw %}
```

## 🛡️ 보안 및 에러 처리

### 1. 환경변수를 통한 API 키 관리

```python
# settings.py
import environ

env = environ.Env()
environ.Env.read_env()

# 토스페이먼츠 설정
TOSS_PAYMENTS_SECRET_KEY = env('TOSS_PAYMENTS_SECRET_KEY')
TOSS_PAYMENTS_CLIENT_KEY = env('TOSS_PAYMENTS_CLIENT_KEY')
TOSS_PAYMENTS_BASE_URL = env('TOSS_PAYMENTS_BASE_URL', default='https://api.tosspayments.com')

# 웹훅 보안을 위한 설정
TOSS_WEBHOOK_SECRET = env('TOSS_WEBHOOK_SECRET', default='')
```

```bash
# .env 파일
TOSS_PAYMENTS_SECRET_KEY=test_sk_your_secret_key
TOSS_PAYMENTS_CLIENT_KEY=test_ck_your_client_key
TOSS_PAYMENTS_BASE_URL=https://api.tosspayments.com
TOSS_WEBHOOK_SECRET=your_webhook_secret
```

### 2. 에러 처리 및 로깅

```python
# exceptions.py
class PaymentError(Exception):
    """결제 관련 에러"""
    def __init__(self, message, error_code=None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class BillingKeyError(Exception):
    """빌링키 관련 에러"""
    pass

class SubscriptionError(Exception):
    """구독 관련 에러"""
    pass

# services.py (개선된 버전)
import logging
from .exceptions import PaymentError, BillingKeyError

logger = logging.getLogger(__name__)

class TossPaymentsService:
    def request_billing_payment(self, billing_key, customer_key, amount, order_id, order_name):
        """빌링키를 사용한 정기 결제 요청 (개선된 버전)"""
        url = f"{self.base_url}/v1/billing/{billing_key}"
        
        data = {
            "customerKey": customer_key,
            "amount": amount,
            "orderId": order_id,
            "orderName": order_name
        }
        
        try:
            response = requests.post(url, json=data, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            
            # 에러 응답 처리
            error_data = response.json() if response.content else {}
            error_code = error_data.get('code')
            error_message = error_data.get('message', '알 수 없는 오류')
            
            logger.error(f"토스페이먼츠 API 오류: {error_code} - {error_message}")
            
            # 에러 코드별 처리
            if error_code in ['INVALID_BILLING_KEY', 'EXPIRED_BILLING_KEY']:
                raise BillingKeyError(f"빌링키 오류: {error_message}")
            elif error_code in ['INSUFFICIENT_FUNDS', 'CARD_COMPANY_DECLINE']:
                raise PaymentError(f"결제 실패: {error_message}", error_code)
            else:
                raise PaymentError(f"결제 요청 실패: {error_message}", error_code)
                
        except requests.exceptions.Timeout:
            raise PaymentError("결제 요청 시간 초과")
        except requests.exceptions.ConnectionError:
            raise PaymentError("결제 서버 연결 실패")
        except requests.exceptions.RequestException as e:
            raise PaymentError(f"결제 요청 오류: {str(e)}")
```

### 3. 데이터베이스 트랜잭션 처리

```python
# services.py (트랜잭션 처리 추가)
from django.db import transaction

class SubscriptionBillingService:
    @transaction.atomic
    def process_subscription_payment(self, subscription):
        """구독 정기 결제 처리 (트랜잭션 적용)"""
        order_id = f"subscription_{subscription.id}_{int(timezone.now().timestamp())}"
        
        # Payment 객체 먼저 생성 (PENDING 상태)
        payment = Payment.objects.create(
            subscription=subscription,
            order_id=order_id,
            amount=subscription.plan.price,
            status='PENDING'
        )
        
        try:
            # 토스페이먼츠 API 호출
            payment_result = self.toss_service.request_billing_payment(
                billing_key=subscription.billing_key,
                customer_key=subscription.customer_key,
                amount=int(subscription.plan.price),
                order_id=order_id,
                order_name=f"{subscription.plan.name} 구독료"
            )
            
            # 결제 성공 시 업데이트
            payment.payment_key = payment_result.get('paymentKey')
            payment.status = 'DONE'
            payment.method = payment_result.get('method')
            payment.approved_at = timezone.now()
            payment.save()
            
            # 다음 결제일 업데이트
            self._update_next_billing_date(subscription)
            
            logger.info(f"구독 결제 성공: {subscription.id} - {payment.payment_key}")
            return payment
            
        except Exception as e:
            # 결제 실패 시 Payment 상태 업데이트
            payment.status = 'FAILED'
            payment.failure_message = str(e)
            payment.save()
            
            # 구독 상태도 업데이트
            subscription.status = 'PAST_DUE'
            subscription.save()
            
            logger.error(f"구독 결제 실패: {subscription.id} - {str(e)}")
            raise e
```

## 📈 모니터링 및 관리

### 1. 관리자 페이지 설정

```python
# admin.py
from django.contrib import admin
from .models import SubscriptionPlan, Subscription, Payment

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'billing_cycle', 'is_active', 'created_at']
    list_filter = ['billing_cycle', 'is_active']
    search_fields = ['name']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'next_billing_date', 'created_at']
    list_filter = ['status', 'plan', 'created_at']
    search_fields = ['user__username', 'user__email', 'customer_key']
    readonly_fields = ['billing_key', 'customer_key', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'plan')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['subscription_user', 'amount', 'status', 'method', 'requested_at']
    list_filter = ['status', 'method', 'requested_at']
    search_fields = ['subscription__user__username', 'order_id', 'payment_key']
    readonly_fields = ['payment_key', 'order_id', 'requested_at', 'approved_at']
    
    def subscription_user(self, obj):
        return obj.subscription.user.username
    subscription_user.short_description = '사용자'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('subscription__user')
```

### 2. 대시보드 뷰

```python
# views.py (관리자용 대시보드)
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta

@staff_member_required
def subscription_dashboard(request):
    """구독 대시보드"""
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    
    # 통계 데이터
    stats = {
        'total_subscriptions': Subscription.objects.filter(status='ACTIVE').count(),
        'monthly_revenue': Payment.objects.filter(
            status='DONE',
            approved_at__date__gte=last_30_days
        ).aggregate(total=Sum('amount'))['total'] or 0,
        'new_subscriptions_30d': Subscription.objects.filter(
            created_at__date__gte=last_30_days
        ).count(),
        'failed_payments_30d': Payment.objects.filter(
            status='FAILED',
            requested_at__date__gte=last_30_days
        ).count(),
    }
    
    # 플랜별 구독 현황
    plan_stats = SubscriptionPlan.objects.annotate(
        active_subscriptions=Count('subscription', filter=models.Q(subscription__status='ACTIVE'))
    ).filter(is_active=True)
    
    context = {
        'stats': stats,
        'plan_stats': plan_stats,
    }
    return render(request, 'admin/subscription_dashboard.html', context)
```

## 🎉 마무리

이제 Django와 토스페이먼츠를 활용한 완전한 구독 결제 시스템을 구축했습니다! 구현한 주요 기능들을 정리하면:

### ✅ 구현된 기능들

1. **빌링키 등록 및 관리**
   - 안전한 카드 정보 등록
   - 토스페이먼츠 위젯 활용

2. **정기 결제 자동화**
   - Celery를 통한 스케줄링
   - 실패 시 재시도 로직

3. **웹훅 처리**
   - 실시간 결제 상태 동기화
   - 안전한 서명 검증

4. **구독 관리**
   - 구독 시작/취소
   - 결제 내역 조회

5. **에러 처리 및 보안**
   - 트랜잭션 처리
   - 환경변수 관리
   - 로깅 시스템

### 🚀 추가로 고려할 사항

**프로덕션 배포 시 체크리스트:**

1. **환경변수 설정**
   ```bash
   # 실제 API 키로 변경
   TOSS_PAYMENTS_SECRET_KEY=live_sk_...
   TOSS_PAYMENTS_CLIENT_KEY=live_ck_...
   ```

2. **Redis/데이터베이스 설정**
   ```python
   # Celery용 Redis 설정
   CELERY_BROKER_URL = 'redis://localhost:6379/0'
   ```

3. **로깅 설정**
   ```python
   LOGGING = {
       'handlers': {
           'file': {
               'filename': '/var/log/django/subscriptions.log',
           }
       }
   }
   ```

4. **HTTPS 설정** (결제 시스템은 필수)

5. **웹훅 엔드포인트 등록**
   - 토스페이먼츠 개발자센터에서 웹훅 URL 등록

### 💡 개선 방향

- **쿠폰 및 할인 시스템** 추가
- **플랜 변경** 기능 구현
- **결제 실패 알림** 시스템
- **구독 분석 대시보드** 강화
- **API 응답시간 모니터링**

이제 여러분도 안정적이고 확장 가능한 구독 결제 시스템을 구축할 수 있습니다. 토스페이먼츠의 개발자 친화적인 API와 Django의 강력한 기능을 결합하면 복잡해 보이는 결제 시스템도 체계적으로 구현할 수 있습니다!

---

**관련 자료:**
- [토스페이먼츠 개발자 문서](https://docs.tosspayments.com/)
- [Django 공식 문서](https://docs.djangoproject.com/)
- [Celery 공식 문서](https://docs.celeryproject.org/)
