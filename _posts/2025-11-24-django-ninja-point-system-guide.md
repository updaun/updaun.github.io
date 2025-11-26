---
layout: post
title: "Django-Ninja로 안전한 포인트 시스템 구축하기 - 동시성 제어부터 보안까지"
date: 2025-11-24
categories: [Django, Backend, API]
tags: [Django-Ninja, Point System, Concurrency Control, Transaction, Race Condition, API Security]
image: "/assets/img/posts/2025-11-24-django-ninja-point-system-guide.webp"
---

# Django-Ninja로 안전한 포인트 시스템 구축하기 - 동시성 제어부터 보안까지

포인트 시스템은 거의 모든 서비스에서 사용되는 핵심 기능이지만, 잘못 구현하면 **Race Condition, 중복 지급, 음수 잔액** 등 심각한 문제가 발생할 수 있습니다. 

이번 포스트에서는 **Django-Ninja**를 사용하여 **안전하고 확장 가능한 포인트 시스템**을 구축하는 방법과 반드시 주의해야 할 핵심 사항들을 실전 예제와 함께 알아보겠습니다.

## 목차
1. [Django-Ninja 소개](#1-django-ninja-소개)
2. [포인트 시스템 요구사항](#2-포인트-시스템-요구사항)
3. [데이터베이스 모델 설계](#3-데이터베이스-모델-설계)
4. [기본 API 구현](#4-기본-api-구현)
5. [동시성 제어 - Race Condition 방지](#5-동시성-제어---race-condition-방지)
6. [트랜잭션 관리](#6-트랜잭션-관리)
7. [중복 요청 방지 (Idempotency)](#7-중복-요청-방지-idempotency)
8. [포인트 만료 처리](#8-포인트-만료-처리)
9. [보안 고려사항](#9-보안-고려사항)
10. [성능 최적화](#10-성능-최적화)
11. [테스트 전략](#11-테스트-전략)
12. [실전 주의사항](#12-실전-주의사항)

---

## 1. Django-Ninja 소개

### 1.1 Django-Ninja란?

**Django-Ninja**는 FastAPI에서 영감을 받은 Django용 최신 API 프레임워크입니다.

```python
# Django REST Framework (기존)
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def get_points(request, user_id):
    # 수동 검증, 수동 응답 생성
    pass

# Django-Ninja (최신)
from ninja import NinjaAPI

api = NinjaAPI()

@api.get("/users/{user_id}/points")
def get_points(request, user_id: int):
    # 자동 타입 검증, 자동 문서화
    pass
```

**주요 장점:**

```
✅ FastAPI 스타일 문법 (type hints 기반)
✅ 자동 API 문서 생성 (OpenAPI/Swagger)
✅ Pydantic 기반 검증 (빠르고 안전)
✅ 높은 성능 (DRF 대비 2-3배)
✅ 간결한 코드
✅ 비동기 지원
```

### 1.2 설치 및 기본 설정

```bash
# 설치
pip install django-ninja

# 프로젝트 생성
django-admin startproject point_system
cd point_system
python manage.py startapp points
```

**프로젝트 구조:**

```
point_system/
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── points/
│   ├── models.py
│   ├── schemas.py
│   ├── api.py
│   ├── services.py
│   └── tests/
├── manage.py
└── requirements.txt
```

**기본 설정 (config/urls.py):**

```python
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from points.api import router as points_router

api = NinjaAPI(
    title="Point System API",
    version="1.0.0",
    description="안전한 포인트 시스템 API"
)

# 포인트 라우터 등록
api.add_router("/points", points_router)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),  # /api/docs에서 Swagger UI 확인 가능
]
```

---

## 2. 포인트 시스템 요구사항

### 2.1 핵심 기능

```
1. 포인트 조회
   - 사용자 현재 잔액 조회
   - 포인트 이력 조회
   - 만료 예정 포인트 조회

2. 포인트 적립 (Earn)
   - 구매, 리뷰, 출석 등
   - 적립 사유 기록
   - 만료일 설정

3. 포인트 사용 (Use)
   - 결제 시 차감
   - 잔액 부족 검증
   - 선입선출(FIFO) 사용

4. 포인트 취소/환불
   - 주문 취소 시 복원
   - 사용 취소 처리

5. 포인트 만료
   - 자동 만료 처리
   - 만료 알림
```

### 2.2 비기능 요구사항

```
1. 동시성 제어 ⚠️ 중요!
   - Race Condition 방지
   - 음수 잔액 방지
   - 중복 적립/사용 방지

2. 정합성 보장
   - 트랜잭션 무결성
   - 원자성 (Atomicity)
   - 일관성 (Consistency)

3. 추적 가능성
   - 모든 변경 이력 기록
   - 감사 로그 (Audit Log)
   - 디버깅 가능한 정보

4. 성능
   - 빠른 조회 (인덱싱)
   - 효율적인 집계
   - 캐싱 전략

5. 보안
   - 권한 검증
   - 악의적 요청 방지
   - Rate Limiting
```

---

## 3. 데이터베이스 모델 설계

### 3.1 포인트 지갑 모델

```python
# points/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()

class PointWallet(models.Model):
    """사용자별 포인트 지갑"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='point_wallet'
    )
    
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="현재 포인트 잔액"
    )
    
    total_earned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="누적 적립 포인트"
    )
    
    total_used = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="누적 사용 포인트"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'point_wallets'
        indexes = [
            models.Index(fields=['user'], name='idx_wallet_user'),
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.balance} points"
```

### 3.2 포인트 거래 내역 모델

```python
class PointTransaction(models.Model):
    """포인트 거래 내역 (불변 로그)"""
    
    class TransactionType(models.TextChoices):
        EARN = 'EARN', '적립'
        USE = 'USE', '사용'
        CANCEL = 'CANCEL', '취소'
        EXPIRE = 'EXPIRE', '만료'
        REFUND = 'REFUND', '환불'
    
    class ReasonCode(models.TextChoices):
        PURCHASE = 'PURCHASE', '구매'
        REVIEW = 'REVIEW', '리뷰 작성'
        ATTENDANCE = 'ATTENDANCE', '출석'
        SIGNUP_BONUS = 'SIGNUP_BONUS', '가입 보너스'
        REFERRAL = 'REFERRAL', '추천'
        ADMIN = 'ADMIN', '관리자 지급'
        PAYMENT = 'PAYMENT', '결제'
        EXPIRED = 'EXPIRED', '만료'
        ORDER_CANCEL = 'ORDER_CANCEL', '주문 취소'
    
    id = models.BigAutoField(primary_key=True)
    
    wallet = models.ForeignKey(
        PointWallet,
        on_delete=models.PROTECT,  # ⚠️ CASCADE 아님! 로그 보존
        related_name='transactions'
    )
    
    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices
    )
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="포인트 금액 (양수/음수)"
    )
    
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="거래 후 잔액 (스냅샷)"
    )
    
    reason_code = models.CharField(
        max_length=20,
        choices=ReasonCode.choices
    )
    
    description = models.TextField(
        blank=True,
        help_text="거래 설명"
    )
    
    # 중복 방지용 고유 키
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="중복 요청 방지 키"
    )
    
    # 관련 엔티티 (Polymorphic)
    related_order_id = models.IntegerField(null=True, blank=True)
    related_review_id = models.IntegerField(null=True, blank=True)
    
    # 메타 정보
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='point_transactions_created'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 만료 관련
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="포인트 만료일 (적립 시에만)"
    )
    
    is_expired = models.BooleanField(
        default=False,
        help_text="만료 여부"
    )
    
    class Meta:
        db_table = 'point_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', '-created_at'], name='idx_trans_wallet_date'),
            models.Index(fields=['idempotency_key'], name='idx_trans_idempotency'),
            models.Index(fields=['expires_at'], name='idx_trans_expires'),
            models.Index(fields=['transaction_type'], name='idx_trans_type'),
        ]
    
    def __str__(self):
        return f"{self.wallet.user.username} - {self.transaction_type}: {self.amount}"
```

### 3.3 포인트 사용 추적 모델 (FIFO)

```python
class PointUsage(models.Model):
    """포인트 사용 추적 (선입선출 관리)"""
    
    earn_transaction = models.ForeignKey(
        PointTransaction,
        on_delete=models.PROTECT,
        related_name='usages',
        help_text="원본 적립 거래"
    )
    
    use_transaction = models.ForeignKey(
        PointTransaction,
        on_delete=models.PROTECT,
        related_name='usage_records',
        help_text="사용 거래"
    )
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="이 적립에서 사용된 금액"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'point_usages'
        indexes = [
            models.Index(fields=['earn_transaction'], name='idx_usage_earn'),
            models.Index(fields=['use_transaction'], name='idx_usage_use'),
        ]
```

**⚠️ 모델 설계 주의사항:**

```
1. Decimal 사용 (Float 절대 금지!)
   - Float: 부동소수점 오차 발생
   - Decimal: 정확한 소수점 계산

2. MinValueValidator로 음수 방지
   - balance는 항상 0 이상

3. 거래 내역은 불변 (Immutable)
   - on_delete=PROTECT
   - 삭제/수정 불가, 취소는 반대 거래 생성

4. 인덱스 최적화
   - 자주 조회하는 필드에 인덱스
   - 복합 인덱스로 성능 향상

5. Idempotency Key
   - 중복 요청 방지 필수
```

---

## 4. 기본 API 구현

### 4.1 Pydantic 스키마 정의

```python
# points/schemas.py
from ninja import Schema
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from enum import Enum

class TransactionTypeEnum(str, Enum):
    EARN = "EARN"
    USE = "USE"
    CANCEL = "CANCEL"
    EXPIRE = "EXPIRE"
    REFUND = "REFUND"

class ReasonCodeEnum(str, Enum):
    PURCHASE = "PURCHASE"
    REVIEW = "REVIEW"
    ATTENDANCE = "ATTENDANCE"
    SIGNUP_BONUS = "SIGNUP_BONUS"
    PAYMENT = "PAYMENT"
    ORDER_CANCEL = "ORDER_CANCEL"

# 응답 스키마
class PointBalanceOut(Schema):
    balance: Decimal
    total_earned: Decimal
    total_used: Decimal
    expiring_soon: Decimal  # 30일 내 만료 예정
    
class PointTransactionOut(Schema):
    id: int
    transaction_type: TransactionTypeEnum
    amount: Decimal
    balance_after: Decimal
    reason_code: ReasonCodeEnum
    description: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_expired: bool

class PointHistoryOut(Schema):
    transactions: List[PointTransactionOut]
    total_count: int
    page: int
    page_size: int

# 요청 스키마
class EarnPointsIn(Schema):
    amount: Decimal
    reason_code: ReasonCodeEnum
    description: str
    idempotency_key: str
    related_order_id: Optional[int] = None
    expires_days: Optional[int] = 365  # 기본 1년
    
    class Config:
        # 검증
        min_amount = Decimal('0.01')
        max_amount = Decimal('1000000.00')

class UsePointsIn(Schema):
    amount: Decimal
    reason_code: ReasonCodeEnum
    description: str
    idempotency_key: str
    related_order_id: Optional[int] = None

class ErrorOut(Schema):
    error: str
    detail: Optional[str] = None
```

### 4.2 포인트 서비스 레이어

```python
# points/services.py
from django.db import transaction, models
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from typing import Tuple, Optional
import logging

from .models import PointWallet, PointTransaction, PointUsage

logger = logging.getLogger(__name__)

class PointService:
    """포인트 비즈니스 로직"""
    
    @staticmethod
    def get_or_create_wallet(user) -> PointWallet:
        """지갑 조회 또는 생성"""
        wallet, created = PointWallet.objects.get_or_create(
            user=user,
            defaults={'balance': Decimal('0.00')}
        )
        return wallet
    
    @staticmethod
    @transaction.atomic
    def earn_points(
        user,
        amount: Decimal,
        reason_code: str,
        description: str,
        idempotency_key: str,
        expires_days: int = 365,
        related_order_id: Optional[int] = None,
        created_by = None
    ) -> Tuple[PointTransaction, bool]:
        """
        포인트 적립
        
        Returns:
            (transaction, created) - created=False면 중복 요청
        """
        # 1. 중복 체크 (Idempotency)
        existing = PointTransaction.objects.filter(
            idempotency_key=idempotency_key
        ).first()
        
        if existing:
            logger.info(f"Duplicate earn request: {idempotency_key}")
            return existing, False
        
        # 2. 지갑 조회 (행 잠금)
        wallet = PointWallet.objects.select_for_update().get(user=user)
        
        # 3. 만료일 계산
        expires_at = timezone.now() + timedelta(days=expires_days)
        
        # 4. 거래 생성
        new_balance = wallet.balance + amount
        
        trans = PointTransaction.objects.create(
            wallet=wallet,
            transaction_type=PointTransaction.TransactionType.EARN,
            amount=amount,
            balance_after=new_balance,
            reason_code=reason_code,
            description=description,
            idempotency_key=idempotency_key,
            related_order_id=related_order_id,
            created_by=created_by or user,
            expires_at=expires_at
        )
        
        # 5. 지갑 업데이트
        wallet.balance = new_balance
        wallet.total_earned += amount
        wallet.save(update_fields=['balance', 'total_earned', 'updated_at'])
        
        logger.info(
            f"Points earned - User: {user.id}, Amount: {amount}, "
            f"Balance: {new_balance}, TxID: {trans.id}"
        )
        
        return trans, True
    
    @staticmethod
    @transaction.atomic
    def use_points(
        user,
        amount: Decimal,
        reason_code: str,
        description: str,
        idempotency_key: str,
        related_order_id: Optional[int] = None,
        created_by = None
    ) -> Tuple[PointTransaction, bool]:
        """
        포인트 사용 (FIFO)
        
        ⚠️ 주의: 잔액 부족 시 ValueError 발생
        """
        # 1. 중복 체크
        existing = PointTransaction.objects.filter(
            idempotency_key=idempotency_key
        ).first()
        
        if existing:
            logger.info(f"Duplicate use request: {idempotency_key}")
            return existing, False
        
        # 2. 지갑 조회 (행 잠금)
        wallet = PointWallet.objects.select_for_update().get(user=user)
        
        # 3. 잔액 검증
        if wallet.balance < amount:
            raise ValueError(
                f"Insufficient balance. Required: {amount}, "
                f"Available: {wallet.balance}"
            )
        
        # 4. FIFO로 사용할 적립 내역 조회
        available_earns = PointTransaction.objects.filter(
            wallet=wallet,
            transaction_type=PointTransaction.TransactionType.EARN,
            is_expired=False,
            expires_at__gt=timezone.now()
        ).annotate(
            used_amount=models.Sum(
                'usages__amount',
                filter=models.Q(usages__isnull=False)
            )
        ).annotate(
            available=models.F('amount') - models.Coalesce('used_amount', Decimal('0'))
        ).filter(
            available__gt=0
        ).order_by('created_at')  # FIFO
        
        # 5. 사용 거래 생성
        new_balance = wallet.balance - amount
        
        use_trans = PointTransaction.objects.create(
            wallet=wallet,
            transaction_type=PointTransaction.TransactionType.USE,
            amount=-amount,  # 음수로 저장
            balance_after=new_balance,
            reason_code=reason_code,
            description=description,
            idempotency_key=idempotency_key,
            related_order_id=related_order_id,
            created_by=created_by or user
        )
        
        # 6. FIFO 매핑 생성
        remaining = amount
        for earn in available_earns:
            if remaining <= 0:
                break
            
            use_amount = min(remaining, earn.available)
            
            PointUsage.objects.create(
                earn_transaction=earn,
                use_transaction=use_trans,
                amount=use_amount
            )
            
            remaining -= use_amount
        
        # 7. 지갑 업데이트
        wallet.balance = new_balance
        wallet.total_used += amount
        wallet.save(update_fields=['balance', 'total_used', 'updated_at'])
        
        logger.info(
            f"Points used - User: {user.id}, Amount: {amount}, "
            f"Balance: {new_balance}, TxID: {use_trans.id}"
        )
        
        return use_trans, True
    
    @staticmethod
    def get_expiring_points(user, days: int = 30) -> Decimal:
        """만료 예정 포인트 조회"""
        wallet = PointWallet.objects.get(user=user)
        cutoff = timezone.now() + timedelta(days=days)
        
        expiring = PointTransaction.objects.filter(
            wallet=wallet,
            transaction_type=PointTransaction.TransactionType.EARN,
            is_expired=False,
            expires_at__lte=cutoff,
            expires_at__gt=timezone.now()
        ).annotate(
            used_amount=models.Sum(
                'usages__amount',
                filter=models.Q(usages__isnull=False)
            )
        ).annotate(
            available=models.F('amount') - models.Coalesce('used_amount', Decimal('0'))
        ).aggregate(
            total=models.Sum('available')
        )
        
        return expiring['total'] or Decimal('0.00')
```

### 4.3 API 엔드포인트

```python
# points/api.py
from ninja import Router
from django.shortcuts import get_object_or_404
from typing import List

from .schemas import (
    PointBalanceOut,
    PointTransactionOut,
    PointHistoryOut,
    EarnPointsIn,
    UsePointsIn,
    ErrorOut
)
from .services import PointService
from .models import PointWallet, PointTransaction

router = Router(tags=["Points"])

@router.get("/balance", response=PointBalanceOut)
def get_balance(request):
    """현재 포인트 잔액 조회"""
    user = request.user
    wallet = PointService.get_or_create_wallet(user)
    expiring_soon = PointService.get_expiring_points(user, days=30)
    
    return {
        "balance": wallet.balance,
        "total_earned": wallet.total_earned,
        "total_used": wallet.total_used,
        "expiring_soon": expiring_soon
    }

@router.get("/history", response=PointHistoryOut)
def get_history(
    request,
    page: int = 1,
    page_size: int = 20
):
    """포인트 거래 내역 조회"""
    user = request.user
    wallet = get_object_or_404(PointWallet, user=user)
    
    transactions = PointTransaction.objects.filter(
        wallet=wallet
    ).select_related('wallet__user')
    
    total_count = transactions.count()
    
    # 페이징
    start = (page - 1) * page_size
    end = start + page_size
    paginated = transactions[start:end]
    
    return {
        "transactions": list(paginated),
        "total_count": total_count,
        "page": page,
        "page_size": page_size
    }

@router.post("/earn", response={200: PointTransactionOut, 400: ErrorOut})
def earn_points(request, data: EarnPointsIn):
    """포인트 적립"""
    try:
        transaction, created = PointService.earn_points(
            user=request.user,
            amount=data.amount,
            reason_code=data.reason_code,
            description=data.description,
            idempotency_key=data.idempotency_key,
            expires_days=data.expires_days,
            related_order_id=data.related_order_id,
            created_by=request.user
        )
        
        return 200, transaction
        
    except Exception as e:
        return 400, {"error": "Failed to earn points", "detail": str(e)}

@router.post("/use", response={200: PointTransactionOut, 400: ErrorOut})
def use_points(request, data: UsePointsIn):
    """포인트 사용"""
    try:
        transaction, created = PointService.use_points(
            user=request.user,
            amount=data.amount,
            reason_code=data.reason_code,
            description=data.description,
            idempotency_key=data.idempotency_key,
            related_order_id=data.related_order_id,
            created_by=request.user
        )
        
        return 200, transaction
        
    except ValueError as e:
        # 잔액 부족
        return 400, {"error": "Insufficient balance", "detail": str(e)}
    except Exception as e:
        return 400, {"error": "Failed to use points", "detail": str(e)}
```

---

## 5. 동시성 제어 - Race Condition 방지

### 5.1 Race Condition 문제점

**시나리오: 동시에 2개의 사용 요청**

```python
# ❌ 잘못된 코드 (Race Condition 발생!)
def use_points_bad(user, amount):
    wallet = PointWallet.objects.get(user=user)  # 잠금 없음!
    
    if wallet.balance < amount:
        raise ValueError("Insufficient balance")
    
    # ⚠️ 여기서 다른 요청이 끼어들 수 있음!
    
    wallet.balance -= amount  # 동시 업데이트 → 데이터 손실!
    wallet.save()

# 문제 발생 예시:
# 초기 잔액: 1000 포인트

# 시간 T1: 요청 A가 balance 읽음 → 1000
# 시간 T2: 요청 B가 balance 읽음 → 1000 (아직 A가 저장 전)
# 시간 T3: 요청 A가 1000 - 500 = 500 저장
# 시간 T4: 요청 B가 1000 - 300 = 700 저장 (A의 변경 덮어씀!)

# 결과: 800 사용했지만 잔액 700 (200 포인트 증발!)
```

### 5.2 해결 방법 1: select_for_update (비관적 락)

```python
# ✅ 올바른 코드 (행 잠금)
from django.db import transaction

@transaction.atomic
def use_points_safe(user, amount):
    # select_for_update()로 행 잠금 (Pessimistic Locking)
    wallet = PointWallet.objects.select_for_update().get(user=user)
    
    if wallet.balance < amount:
        raise ValueError("Insufficient balance")
    
    wallet.balance -= amount
    wallet.save()
    # 트랜잭션 커밋 시 잠금 해제

# 동작 방식:
# T1: 요청 A가 select_for_update → 행 잠금 획득
# T2: 요청 B가 select_for_update → 대기 (A가 끝날 때까지)
# T3: 요청 A 완료 → 잠금 해제
# T4: 요청 B 잠금 획득 → 처리

# 결과: 순차 처리 보장 ✅
```

**select_for_update 옵션:**

```python
# 1. 기본 (잠금 대기)
wallet = PointWallet.objects.select_for_update().get(user=user)

# 2. nowait=True (잠금 실패 시 즉시 에러)
try:
    wallet = PointWallet.objects.select_for_update(nowait=True).get(user=user)
except DatabaseError:
    raise ValueError("System is busy, please try again")

# 3. skip_locked=True (잠긴 행 건너뛰기)
wallets = PointWallet.objects.select_for_update(skip_locked=True).filter(...)

# 4. of= (특정 테이블만 잠금)
wallet = PointWallet.objects.select_for_update(of=('self',)).get(user=user)
```

### 5.3 해결 방법 2: F() 표현식 (낙관적 업데이트)

```python
from django.db.models import F

@transaction.atomic
def use_points_with_f(user, amount):
    wallet = PointWallet.objects.get(user=user)
    
    # F() 표현식으로 원자적 업데이트
    updated = PointWallet.objects.filter(
        id=wallet.id,
        balance__gte=amount  # 잔액 충분한 경우만
    ).update(
        balance=F('balance') - amount,
        total_used=F('total_used') + amount
    )
    
    if updated == 0:
        raise ValueError("Insufficient balance or concurrent update")
    
    # 업데이트된 값 다시 읽기
    wallet.refresh_from_db()
    return wallet

# 장점:
# - 단일 쿼리로 처리
# - 데이터베이스 레벨에서 원자성 보장
# - select_for_update보다 빠를 수 있음

# 단점:
# - 복잡한 비즈니스 로직 처리 어려움
# - 업데이트 전 값 확인 불가
```

### 5.4 해결 방법 3: 버전 필드 (Optimistic Locking)

```python
class PointWallet(models.Model):
    # ... 기존 필드 ...
    
    version = models.IntegerField(default=0)  # 버전 필드 추가
    
    class Meta:
        db_table = 'point_wallets'

@transaction.atomic
def use_points_optimistic(user, amount):
    wallet = PointWallet.objects.get(user=user)
    current_version = wallet.version
    
    if wallet.balance < amount:
        raise ValueError("Insufficient balance")
    
    # 버전 확인하며 업데이트
    updated = PointWallet.objects.filter(
        id=wallet.id,
        version=current_version  # 버전 일치 확인
    ).update(
        balance=F('balance') - amount,
        version=F('version') + 1  # 버전 증가
    )
    
    if updated == 0:
        # 다른 요청이 먼저 수정함
        raise ValueError("Concurrent modification detected, please retry")
    
    wallet.refresh_from_db()
    return wallet

# 장점:
# - 잠금 없이 동시성 제어
# - 읽기 성능 우수
# - 충돌 감지 가능

# 단점:
# - 충돌 시 재시도 필요 (클라이언트 부담)
# - 충돌 빈번하면 비효율적
```

### 5.5 실전 권장: Hybrid 방식

```python
# ✅ 추천: select_for_update + F() 조합
@transaction.atomic
def use_points_hybrid(user, amount, idempotency_key):
    # 1. 중복 체크 (먼저)
    if PointTransaction.objects.filter(idempotency_key=idempotency_key).exists():
        existing = PointTransaction.objects.get(idempotency_key=idempotency_key)
        return existing, False
    
    # 2. 행 잠금
    wallet = PointWallet.objects.select_for_update().get(user=user)
    
    # 3. 잔액 검증
    if wallet.balance < amount:
        raise ValueError(f"Insufficient balance: {wallet.balance} < {amount}")
    
    # 4. 트랜잭션 생성
    new_balance = wallet.balance - amount
    trans = PointTransaction.objects.create(
        wallet=wallet,
        transaction_type=PointTransaction.TransactionType.USE,
        amount=-amount,
        balance_after=new_balance,
        idempotency_key=idempotency_key,
        # ...
    )
    
    # 5. 지갑 업데이트 (F() 사용)
    PointWallet.objects.filter(id=wallet.id).update(
        balance=F('balance') - amount,
        total_used=F('total_used') + amount
    )
    
    return trans, True

# 장점:
# - select_for_update로 동시성 제어
# - F()로 원자적 업데이트
# - Idempotency로 중복 방지
# - 안전하고 효율적
```

### 5.6 데이터베이스 레벨 제약조건

```python
# PostgreSQL Constraint 추가
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('points', '0001_initial'),
    ]
    
    operations = [
        migrations.RunSQL(
            # 잔액 음수 방지 (데이터베이스 레벨)
            sql="""
                ALTER TABLE point_wallets
                ADD CONSTRAINT check_positive_balance
                CHECK (balance >= 0);
            """,
            reverse_sql="""
                ALTER TABLE point_wallets
                DROP CONSTRAINT check_positive_balance;
            """
        ),
    ]

# 효과:
# - 애플리케이션 버그가 있어도 음수 잔액 방지
# - 데이터베이스가 최후의 방어선
```

---

## 6. 트랜잭션 관리

### 6.1 트랜잭션 격리 수준

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # ...
        'OPTIONS': {
            'isolation_level': psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED,
            # PostgreSQL 기본값: READ COMMITTED
        }
    }
}

# 격리 수준 비교:
"""
READ UNCOMMITTED (사용 금지):
- Dirty Read 가능
- 커밋 안 된 데이터 읽음
- 포인트 시스템에 절대 부적합 ❌

READ COMMITTED (권장):
- Dirty Read 방지
- 커밋된 데이터만 읽음
- PostgreSQL 기본값 ✅

REPEATABLE READ:
- Non-repeatable Read 방지
- 트랜잭션 내 일관성 보장
- 성능 약간 저하

SERIALIZABLE (가장 엄격):
- Phantom Read 방지
- 완전한 격리
- 성능 크게 저하
- 필요 시에만 사용
"""
```

### 6.2 트랜잭션 패턴

```python
# 패턴 1: 함수 데코레이터
from django.db import transaction

@transaction.atomic
def earn_points(user, amount):
    # 이 함수 전체가 하나의 트랜잭션
    wallet = PointWallet.objects.select_for_update().get(user=user)
    # ...
    # 성공 시 자동 commit, 예외 시 자동 rollback

# 패턴 2: Context Manager
def process_order(order):
    with transaction.atomic():
        # 블록 내부가 트랜잭션
        order.status = 'PAID'
        order.save()
        
        earn_points(order.user, order.point_amount)
        # 둘 다 성공해야 commit

# 패턴 3: 중첩 트랜잭션 (Savepoint)
@transaction.atomic
def outer_function():
    # 외부 트랜잭션
    
    try:
        with transaction.atomic():
            # 내부 Savepoint
            risky_operation()
    except Exception:
        # 내부만 rollback, 외부는 계속
        pass
    
    safe_operation()  # 계속 진행

# 패턴 4: 수동 제어 (비추천)
from django.db import connection

cursor = connection.cursor()
cursor.execute("BEGIN")
try:
    # ...
    cursor.execute("COMMIT")
except:
    cursor.execute("ROLLBACK")
    raise
```

### 6.3 트랜잭션 주의사항

```python
# ❌ 잘못된 패턴: 트랜잭션 밖에서 읽기
def bad_pattern(user_id):
    wallet = PointWallet.objects.get(user_id=user_id)  # 트랜잭션 밖
    
    with transaction.atomic():
        # 트랜잭션 내부에서 wallet 사용
        wallet.balance -= 100  # ⚠️ 이미 읽은 값, 다른 트랜잭션이 변경했을 수 있음
        wallet.save()

# ✅ 올바른 패턴: 트랜잭션 안에서 읽기
@transaction.atomic
def good_pattern(user_id):
    wallet = PointWallet.objects.select_for_update().get(user_id=user_id)
    wallet.balance -= 100
    wallet.save()

# ❌ 잘못된 패턴: 외부 API 호출
@transaction.atomic
def bad_external_call(user, amount):
    wallet = PointWallet.objects.select_for_update().get(user=user)
    wallet.balance += amount
    wallet.save()
    
    # ⚠️ 트랜잭션 내에서 외부 API 호출 (절대 금지!)
    requests.post("https://api.example.com/notify", ...)
    # 외부 API가 느리면 트랜잭션이 오래 유지 → 잠금 대기 증가

# ✅ 올바른 패턴: 트랜잭션 분리
@transaction.atomic
def good_external_call(user, amount):
    wallet = PointWallet.objects.select_for_update().get(user=user)
    wallet.balance += amount
    wallet.save()
    transaction_id = wallet.transactions.latest('id').id

# 트랜잭션 밖에서 외부 호출
def after_commit(transaction_id):
    requests.post("https://api.example.com/notify", ...)

# Django 4.0+ on_commit 훅
from django.db.transaction import on_commit

@transaction.atomic
def with_on_commit(user, amount):
    wallet = PointWallet.objects.select_for_update().get(user=user)
    wallet.balance += amount
    wallet.save()
    
    # 트랜잭션 커밋 후 실행
    on_commit(lambda: notify_external_api(wallet.id))
```

### 6.4 데드락 방지

```python
# 데드락 시나리오:
"""
시간 T1: Transaction A가 User 1 잠금
시간 T2: Transaction B가 User 2 잠금
시간 T3: Transaction A가 User 2 잠금 시도 → 대기
시간 T4: Transaction B가 User 1 잠금 시도 → 대기
→ 데드락 발생! (서로 기다림)
"""

# ✅ 해결 방법 1: 일관된 잠금 순서
@transaction.atomic
def transfer_points(from_user_id, to_user_id, amount):
    # 항상 ID 순서대로 잠금
    user_ids = sorted([from_user_id, to_user_id])
    
    wallet1 = PointWallet.objects.select_for_update().get(user_id=user_ids[0])
    wallet2 = PointWallet.objects.select_for_update().get(user_id=user_ids[1])
    
    # 실제 처리는 원래 순서대로
    if from_user_id == user_ids[0]:
        from_wallet, to_wallet = wallet1, wallet2
    else:
        from_wallet, to_wallet = wallet2, wallet1
    
    # 포인트 이체
    from_wallet.balance -= amount
    to_wallet.balance += amount
    from_wallet.save()
    to_wallet.save()

# ✅ 해결 방법 2: 타임아웃 설정
from django.db import DatabaseError

@transaction.atomic
def with_timeout(user_id, amount):
    try:
        wallet = PointWallet.objects.select_for_update(
            nowait=True  # 즉시 실패
        ).get(user_id=user_id)
        # ...
    except DatabaseError:
        raise ValueError("System is busy, please try again later")

# ✅ 해결 방법 3: 재시도 로직
import time
from functools import wraps

def retry_on_deadlock(max_retries=3, delay=0.1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except DatabaseError as e:
                    if 'deadlock' in str(e).lower():
                        if attempt < max_retries - 1:
                            time.sleep(delay * (2 ** attempt))  # Exponential backoff
                            continue
                    raise
            return None
        return wrapper
    return decorator

@retry_on_deadlock(max_retries=3)
@transaction.atomic
def safe_operation(user_id, amount):
    # ...
    pass
```

---

## 7. 중복 요청 방지 (Idempotency)

### 7.1 Idempotency Key 전략

```python
# Idempotency Key 생성 (클라이언트 측)
import uuid
from datetime import datetime

def generate_idempotency_key(user_id, action, context):
    """
    고유한 Idempotency Key 생성
    
    Format: {user_id}:{action}:{context}:{timestamp}:{random}
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = uuid.uuid4().hex[:8]
    
    return f"{user_id}:{action}:{context}:{timestamp}:{random_part}"

# 예시:
# 주문 완료 시 포인트 적립
order_id = 12345
key = generate_idempotency_key(
    user_id=request.user.id,
    action="earn",
    context=f"order_{order_id}"
)
# 결과: "42:earn:order_12345:20250124153045:a1b2c3d4"

# API 요청
POST /api/points/earn
{
    "amount": 1000,
    "reason_code": "PURCHASE",
    "idempotency_key": "42:earn:order_12345:20250124153045:a1b2c3d4",
    "related_order_id": 12345
}
```

### 7.2 중복 처리 로직

```python
# 서버 측 중복 체크
@transaction.atomic
def earn_points_idempotent(user, amount, idempotency_key, **kwargs):
    """Idempotent 포인트 적립"""
    
    # 1. 기존 거래 조회
    existing = PointTransaction.objects.filter(
        idempotency_key=idempotency_key
    ).first()
    
    if existing:
        # 2-1. 중복 요청
        logger.warning(
            f"Duplicate request detected - Key: {idempotency_key}, "
            f"Original TxID: {existing.id}"
        )
        
        # 기존 거래 반환 (재처리 없음)
        return existing, False  # (transaction, created)
    
    # 2-2. 새로운 요청
    try:
        wallet = PointWallet.objects.select_for_update().get(user=user)
        
        # 거래 생성
        trans = PointTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            idempotency_key=idempotency_key,
            **kwargs
        )
        
        # 지갑 업데이트
        wallet.balance += amount
        wallet.save()
        
        logger.info(f"New transaction created - TxID: {trans.id}")
        return trans, True
        
    except IntegrityError as e:
        # 3. Race Condition으로 동시 생성 시도
        # (unique constraint 위배)
        existing = PointTransaction.objects.get(
            idempotency_key=idempotency_key
        )
        logger.warning(f"Race condition handled - Key: {idempotency_key}")
        return existing, False

# API 응답
@router.post("/earn")
def earn_points_endpoint(request, data: EarnPointsIn):
    trans, created = earn_points_idempotent(
        user=request.user,
        amount=data.amount,
        idempotency_key=data.idempotency_key,
        # ...
    )
    
    # HTTP 상태 코드
    status_code = 201 if created else 200
    
    return status_code, {
        "transaction": trans,
        "created": created,  # 클라이언트가 중복인지 알 수 있음
        "message": "Points earned" if created else "Duplicate request (already processed)"
    }
```

### 7.3 Idempotency Key 관리

```python
# Key 유효기간 설정
class PointTransaction(models.Model):
    # ...
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True
    )
    idempotency_expires_at = models.DateTimeField(
        default=lambda: timezone.now() + timedelta(days=7),
        help_text="Idempotency Key 만료일 (7일)"
    )

# 만료된 키 정리 (Celery Task)
from celery import shared_task

@shared_task
def cleanup_expired_idempotency_keys():
    """만료된 Idempotency Key 정리"""
    cutoff = timezone.now() - timedelta(days=7)
    
    # 만료된 키만 NULL로 변경 (거래 내역은 유지)
    updated = PointTransaction.objects.filter(
        created_at__lt=cutoff,
        idempotency_key__isnull=False
    ).update(
        idempotency_key=None,  # 재사용 가능하게
        idempotency_expires_at=None
    )
    
    logger.info(f"Cleaned up {updated} expired idempotency keys")
    return updated

# Celery Beat 스케줄링
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'cleanup-idempotency-keys': {
        'task': 'points.tasks.cleanup_expired_idempotency_keys',
        'schedule': crontab(hour=3, minute=0),  # 매일 오전 3시
    },
}
```

### 7.4 클라이언트 재시도 전략

```typescript
// 프론트엔드 (TypeScript/React)
async function earnPoints(
  amount: number,
  orderId: number,
  maxRetries = 3
): Promise<PointTransaction> {
  // Idempotency Key 생성 (한 번만)
  const idempotencyKey = `${userId}:earn:order_${orderId}:${Date.now()}:${randomHex()}`;
  
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const response = await fetch('/api/points/earn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount,
          reason_code: 'PURCHASE',
          idempotency_key: idempotencyKey,  // 동일한 키 사용!
          related_order_id: orderId
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        
        if (data.created) {
          console.log('포인트 적립 성공');
        } else {
          console.log('이미 처리된 요청');
        }
        
        return data.transaction;
      }
      
      // 일시적 오류 (500, 503 등)
      if (response.status >= 500 && attempt < maxRetries - 1) {
        await delay(1000 * Math.pow(2, attempt));  // Exponential backoff
        continue;
      }
      
      throw new Error(`API Error: ${response.status}`);
      
    } catch (error) {
      if (attempt === maxRetries - 1) {
        throw error;
      }
      await delay(1000 * Math.pow(2, attempt));
    }
  }
  
  throw new Error('Max retries exceeded');
}

// 핵심: 같은 idempotencyKey로 재시도
// → 서버에서 중복으로 인식하여 한 번만 처리됨 ✅
```

---

## 8. 포인트 만료 처리

### 8.1 만료 배치 작업

```python
# points/tasks.py (Celery Task)
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

@shared_task
def expire_points_batch():
    """만료된 포인트 일괄 처리"""
    now = timezone.now()
    
    # 만료 대상 조회
    expired_earns = PointTransaction.objects.filter(
        transaction_type=PointTransaction.TransactionType.EARN,
        is_expired=False,
        expires_at__lte=now
    ).select_related('wallet').annotate(
        used_amount=models.Sum(
            'usages__amount',
            filter=models.Q(usages__isnull=False)
        )
    ).annotate(
        available=models.F('amount') - models.Coalesce('used_amount', Decimal('0'))
    ).filter(
        available__gt=0  # 잔액 있는 것만
    )
    
    total_expired_amount = Decimal('0')
    total_count = 0
    
    for earn in expired_earns:
        try:
            with transaction.atomic():
                # 1. 지갑 잠금
                wallet = PointWallet.objects.select_for_update().get(
                    id=earn.wallet_id
                )
                
                # 2. 만료 거래 생성
                expire_amount = earn.available
                new_balance = wallet.balance - expire_amount
                
                PointTransaction.objects.create(
                    wallet=wallet,
                    transaction_type=PointTransaction.TransactionType.EXPIRE,
                    amount=-expire_amount,
                    balance_after=new_balance,
                    reason_code=PointTransaction.ReasonCode.EXPIRED,
                    description=f"만료: {earn.description}",
                    idempotency_key=f"expire_{earn.id}_{now.timestamp()}",
                    created_by=None
                )
                
                # 3. 원본 적립 만료 표시
                earn.is_expired = True
                earn.save(update_fields=['is_expired'])
                
                # 4. 지갑 업데이트
                wallet.balance = new_balance
                wallet.save(update_fields=['balance', 'updated_at'])
                
                total_expired_amount += expire_amount
                total_count += 1
                
                logger.info(
                    f"Points expired - User: {wallet.user_id}, "
                    f"Amount: {expire_amount}, EarnTxID: {earn.id}"
                )
                
        except Exception as e:
            logger.error(f"Failed to expire points - EarnTxID: {earn.id}, Error: {e}")
            continue
    
    logger.info(
        f"Points expiration completed - "
        f"Count: {total_count}, Total: {total_expired_amount}"
    )
    
    return {
        'total_count': total_count,
        'total_amount': float(total_expired_amount)
    }

# Celery Beat 스케줄
CELERY_BEAT_SCHEDULE = {
    'expire-points': {
        'task': 'points.tasks.expire_points_batch',
        'schedule': crontab(hour=0, minute=0),  # 매일 자정
    },
}
```

### 8.2 만료 예정 알림

```python
@shared_task
def notify_expiring_points():
    """만료 예정 포인트 알림 (7일 전)"""
    cutoff_start = timezone.now() + timedelta(days=7)
    cutoff_end = cutoff_start + timedelta(days=1)
    
    # 7일 후 만료 예정인 사용자
    expiring = PointTransaction.objects.filter(
        transaction_type=PointTransaction.TransactionType.EARN,
        is_expired=False,
        expires_at__gte=cutoff_start,
        expires_at__lt=cutoff_end
    ).annotate(
        used_amount=models.Sum(
            'usages__amount',
            filter=models.Q(usages__isnull=False)
        )
    ).annotate(
        available=models.F('amount') - models.Coalesce('used_amount', Decimal('0'))
    ).filter(
        available__gt=0
    ).values('wallet__user_id').annotate(
        total_expiring=models.Sum('available')
    )
    
    for item in expiring:
        user_id = item['wallet__user_id']
        amount = item['total_expiring']
        
        # 이메일/푸시 알림 발송
        send_notification(
            user_id=user_id,
            title="포인트 만료 예정",
            message=f"{amount} 포인트가 7일 후 만료됩니다."
        )
    
    logger.info(f"Sent expiring notifications to {len(expiring)} users")
```

### 8.3 만료 방지 (연장)

```python
@transaction.atomic
def extend_point_expiry(user, days_to_extend=90):
    """
    포인트 만료일 연장 (프로모션 등)
    
    ⚠️ 주의: 남용 방지를 위해 관리자만 호출 가능하도록
    """
    wallet = PointWallet.objects.select_for_update().get(user=user)
    
    # 만료 예정 포인트 조회
    expiring_soon = PointTransaction.objects.filter(
        wallet=wallet,
        transaction_type=PointTransaction.TransactionType.EARN,
        is_expired=False,
        expires_at__lte=timezone.now() + timedelta(days=30)
    )
    
    extended_count = 0
    for trans in expiring_soon:
        trans.expires_at += timedelta(days=days_to_extend)
        trans.save(update_fields=['expires_at'])
        extended_count += 1
    
    logger.info(
        f"Extended {extended_count} point transactions for user {user.id}"
    )
    
    return extended_count
```

---

## 9. 보안 고려사항

### 9.1 권한 검증

```python
# points/auth.py
from ninja.security import HttpBearer
from django.contrib.auth.models import AnonymousUser

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            # JWT 검증 또는 Session 확인
            user = get_user_from_token(token)
            return user
        except:
            return None

# API에 인증 적용
from ninja import Router
from .auth import AuthBearer

router = Router(auth=AuthBearer(), tags=["Points"])

@router.get("/balance")
def get_balance(request):
    # request.user는 자동으로 인증된 사용자
    user = request.auth  # 또는 request.user
    # ...

# 본인 확인
@router.get("/users/{user_id}/points")
def get_user_points(request, user_id: int):
    # 본인 또는 관리자만 조회 가능
    if request.user.id != user_id and not request.user.is_staff:
        return 403, {"error": "Permission denied"}
    
    wallet = PointWallet.objects.get(user_id=user_id)
    return {"balance": wallet.balance}
```

### 9.2 Rate Limiting

```python
# Django-ratelimit 사용
from django_ratelimit.decorators import ratelimit
from django.core.cache import cache
import hashlib

def rate_limit_key(group, request):
    """Rate limit key 생성"""
    return f"{group}:{request.user.id}"

# API에 Rate Limit 적용
from ninja import Router
from functools import wraps

def rate_limit(max_requests=10, period=60):
    """
    Rate Limiting 데코레이터
    
    Args:
        max_requests: 최대 요청 수
        period: 기간 (초)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # 키 생성
            key = f"rate_limit:{func.__name__}:{request.user.id}"
            
            # 현재 카운트
            count = cache.get(key, 0)
            
            if count >= max_requests:
                return 429, {
                    "error": "Too many requests",
                    "detail": f"Maximum {max_requests} requests per {period} seconds"
                }
            
            # 카운트 증가
            cache.set(key, count + 1, period)
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator

# 사용
@router.post("/use")
@rate_limit(max_requests=10, period=60)  # 1분에 10회
def use_points(request, data: UsePointsIn):
    # ...
    pass

# IP 기반 Rate Limit (악의적 요청 방지)
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@router.post("/earn")
def earn_points_with_ip_limit(request, data: EarnPointsIn):
    ip = get_client_ip(request)
    key = f"rate_limit:earn:ip:{ip}"
    
    count = cache.get(key, 0)
    if count >= 100:  # IP당 1시간에 100회
        return 429, {"error": "Too many requests from this IP"}
    
    cache.set(key, count + 1, 3600)
    
    # 실제 처리
    # ...
```

### 9.3 입력 검증 강화

```python
# schemas.py
from ninja import Schema
from pydantic import validator, Field
from decimal import Decimal

class EarnPointsIn(Schema):
    amount: Decimal = Field(..., gt=0, le=1000000)
    reason_code: str
    description: str = Field(..., min_length=1, max_length=500)
    idempotency_key: str = Field(..., min_length=10, max_length=255)
    related_order_id: Optional[int] = Field(None, gt=0)
    
    @validator('amount')
    def validate_amount(cls, v):
        # 소수점 2자리까지만
        if v.as_tuple().exponent < -2:
            raise ValueError('Amount must have at most 2 decimal places')
        
        # 최소값
        if v < Decimal('0.01'):
            raise ValueError('Amount must be at least 0.01')
        
        return v
    
    @validator('reason_code')
    def validate_reason_code(cls, v):
        valid_codes = [
            'PURCHASE', 'REVIEW', 'ATTENDANCE',
            'SIGNUP_BONUS', 'REFERRAL', 'ADMIN'
        ]
        if v not in valid_codes:
            raise ValueError(f'Invalid reason_code. Must be one of: {valid_codes}')
        return v
    
    @validator('idempotency_key')
    def validate_idempotency_key(cls, v):
        # 영숫자, 하이픈, 언더스코어만 허용
        import re
        if not re.match(r'^[a-zA-Z0-9_:-]+$', v):
            raise ValueError('Idempotency key contains invalid characters')
        return v

# SQL Injection 방지 (ORM 사용으로 기본 방지)
# ✅ 올바른 방식
def get_transactions(user_id):
    return PointTransaction.objects.filter(wallet__user_id=user_id)

# ❌ 절대 금지!
def bad_query(user_id):
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM transactions WHERE user_id = {user_id}")
    # → SQL Injection 취약점!
```

### 9.4 민감 정보 보호

```python
# 로그에서 민감 정보 마스킹
import logging
import re

class SensitiveDataFilter(logging.Filter):
    """민감 정보 필터링"""
    
    def filter(self, record):
        # 로그 메시지에서 카드번호, 이메일 등 마스킹
        if hasattr(record, 'msg'):
            msg = str(record.msg)
            
            # 카드번호 마스킹
            msg = re.sub(r'\d{13,16}', '****-****-****-****', msg)
            
            # 이메일 마스킹
            msg = re.sub(
                r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'***@\2',
                msg
            )
            
            record.msg = msg
        
        return True

# settings.py
LOGGING = {
    'version': 1,
    'filters': {
        'sensitive_data': {
            '()': 'points.filters.SensitiveDataFilter',
        }
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'points.log',
            'filters': ['sensitive_data'],
        }
    },
    'loggers': {
        'points': {
            'handlers': ['file'],
            'level': 'INFO',
        }
    }
}

# API 응답에서 민감 정보 제외
class PointTransactionOut(Schema):
    id: int
    amount: Decimal
    created_at: datetime
    # ❌ 포함하지 말아야 할 것들:
    # - created_by (다른 사용자 정보)
    # - internal_notes (내부 메모)
    # - ip_address (IP 주소)
```

### 9.5 관리자 기능 보안

```python
# 관리자 전용 엔드포인트
from ninja import Router

admin_router = Router(tags=["Admin"])

@admin_router.post("/users/{user_id}/adjust-points")
def admin_adjust_points(
    request,
    user_id: int,
    amount: Decimal,
    reason: str
):
    # 관리자 권한 확인
    if not request.user.is_staff:
        return 403, {"error": "Admin access required"}
    
    # 감사 로그 기록
    audit_log = AdminAction.objects.create(
        admin_user=request.user,
        action_type='ADJUST_POINTS',
        target_user_id=user_id,
        data={
            'amount': str(amount),
            'reason': reason
        },
        ip_address=get_client_ip(request),
        timestamp=timezone.now()
    )
    
    # 포인트 조정
    try:
        if amount > 0:
            trans, _ = PointService.earn_points(
                user=User.objects.get(id=user_id),
                amount=amount,
                reason_code='ADMIN',
                description=f"관리자 지급: {reason}",
                idempotency_key=f"admin_{audit_log.id}_{timezone.now().timestamp()}",
                created_by=request.user
            )
        else:
            trans, _ = PointService.use_points(
                user=User.objects.get(id=user_id),
                amount=-amount,
                reason_code='ADMIN',
                description=f"관리자 차감: {reason}",
                idempotency_key=f"admin_{audit_log.id}_{timezone.now().timestamp()}",
                created_by=request.user
            )
        
        return {"success": True, "transaction": trans}
        
    except Exception as e:
        audit_log.error_message = str(e)
        audit_log.save()
        return 500, {"error": str(e)}

# 감사 로그 모델
class AdminAction(models.Model):
    admin_user = models.ForeignKey(User, on_delete=models.PROTECT)
    action_type = models.CharField(max_length=50)
    target_user_id = models.IntegerField()
    data = models.JSONField()
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        db_table = 'admin_actions'
        indexes = [
            models.Index(fields=['admin_user', '-timestamp']),
            models.Index(fields=['target_user_id', '-timestamp']),
        ]
```

---

## 10. 성능 최적화

### 10.1 데이터베이스 최적화

```python
# 1. 적절한 인덱스
class PointTransaction(models.Model):
    # ...
    
    class Meta:
        indexes = [
            # 복합 인덱스 (자주 함께 조회되는 필드)
            models.Index(
                fields=['wallet', '-created_at'],
                name='idx_wallet_date'
            ),
            # 만료 처리용
            models.Index(
                fields=['transaction_type', 'is_expired', 'expires_at'],
                name='idx_expire_query'
            ),
            # Idempotency 조회용
            models.Index(
                fields=['idempotency_key'],
                name='idx_idempotency'
            ),
        ]

# 2. 쿼리 최적화
def get_point_history_optimized(user_id, page=1, page_size=20):
    """N+1 쿼리 방지"""
    
    # ❌ 나쁜 예: N+1 문제
    transactions = PointTransaction.objects.filter(wallet__user_id=user_id)
    for trans in transactions:
        print(trans.wallet.user.username)  # 매번 DB 조회!
    
    # ✅ 좋은 예: select_related
    transactions = PointTransaction.objects.filter(
        wallet__user_id=user_id
    ).select_related(
        'wallet__user',  # JOIN으로 한 번에 조회
        'created_by'
    ).prefetch_related(
        'usages__earn_transaction'  # 관련 사용 내역
    )[page_size * (page - 1):page_size * page]
    
    return transactions

# 3. 집계 쿼리 최적화
def get_monthly_stats(user_id, year, month):
    """월별 통계"""
    from django.db.models import Sum, Count
    
    start_date = datetime(year, month, 1)
    end_date = (start_date + timedelta(days=32)).replace(day=1)
    
    stats = PointTransaction.objects.filter(
        wallet__user_id=user_id,
        created_at__gte=start_date,
        created_at__lt=end_date
    ).aggregate(
        total_earned=Sum(
            'amount',
            filter=models.Q(transaction_type='EARN')
        ),
        total_used=Sum(
            'amount',
            filter=models.Q(transaction_type='USE')
        ),
        transaction_count=Count('id')
    )
    
    return stats

# 4. 부분 인덱스 (PostgreSQL)
class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            # 만료되지 않은 적립만 인덱스
            sql="""
                CREATE INDEX idx_active_earns 
                ON point_transactions (wallet_id, expires_at)
                WHERE transaction_type = 'EARN' 
                AND is_expired = false;
            """,
            reverse_sql="DROP INDEX idx_active_earns;"
        ),
    ]
```

### 10.2 캐싱 전략

```python
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

# 1. 잔액 캐싱
def get_balance_cached(user_id):
    """잔액 조회 (캐싱)"""
    cache_key = f"point_balance:{user_id}"
    
    # 캐시 조회
    balance = cache.get(cache_key)
    
    if balance is None:
        # DB 조회
        wallet = PointWallet.objects.get(user_id=user_id)
        balance = wallet.balance
        
        # 캐시 저장 (5분)
        cache.set(cache_key, balance, 300)
    
    return balance

# 2. 캐시 무효화
@transaction.atomic
def use_points_with_cache(user, amount, **kwargs):
    """포인트 사용 + 캐시 무효화"""
    
    trans, created = PointService.use_points(user, amount, **kwargs)
    
    if created:
        # 캐시 삭제
        cache_key = f"point_balance:{user.id}"
        cache.delete(cache_key)
        
        # 관련 캐시도 삭제
        cache.delete(f"point_expiring:{user.id}")
        cache.delete(f"point_history:{user.id}:*")  # 패턴 삭제
    
    return trans, created

# 3. 통계 캐싱 (장기)
def get_total_stats():
    """전체 통계 (1시간 캐싱)"""
    cache_key = "point_total_stats"
    
    stats = cache.get(cache_key)
    
    if stats is None:
        from django.db.models import Sum, Count
        
        stats = {
            'total_users': PointWallet.objects.count(),
            'total_balance': PointWallet.objects.aggregate(
                total=Sum('balance')
            )['total'],
            'total_transactions': PointTransaction.objects.count(),
        }
        
        cache.set(cache_key, stats, 3600)  # 1시간
    
    return stats

# 4. Redis를 활용한 분산 잠금
import redis
from contextlib import contextmanager

redis_client = redis.Redis(host='localhost', port=6379, db=0)

@contextmanager
def redis_lock(key, timeout=10):
    """Redis 분산 잠금"""
    lock_key = f"lock:{key}"
    
    # 잠금 획득 시도
    acquired = redis_client.set(lock_key, '1', nx=True, ex=timeout)
    
    if not acquired:
        raise ValueError("Could not acquire lock")
    
    try:
        yield
    finally:
        redis_client.delete(lock_key)

# 사용
def process_with_lock(user_id):
    with redis_lock(f"user_points:{user_id}"):
        # 중복 방지된 처리
        pass
```

### 10.3 배치 처리 최적화

```python
# 대량 포인트 지급
def bulk_earn_points(user_point_list):
    """
    배치로 포인트 지급
    
    Args:
        user_point_list: [(user_id, amount, reason), ...]
    """
    from django.db import transaction
    
    transactions_to_create = []
    wallets_to_update = {}
    
    with transaction.atomic():
        # 1. 지갑 일괄 조회 및 잠금
        user_ids = [item[0] for item in user_point_list]
        wallets = {
            w.user_id: w 
            for w in PointWallet.objects.select_for_update().filter(
                user_id__in=user_ids
            )
        }
        
        # 2. 거래 생성 준비
        now = timezone.now()
        
        for user_id, amount, reason in user_point_list:
            wallet = wallets[user_id]
            new_balance = wallet.balance + amount
            
            transactions_to_create.append(
                PointTransaction(
                    wallet=wallet,
                    transaction_type='EARN',
                    amount=amount,
                    balance_after=new_balance,
                    reason_code=reason,
                    idempotency_key=f"bulk_{user_id}_{now.timestamp()}",
                    expires_at=now + timedelta(days=365)
                )
            )
            
            wallets_to_update[wallet.id] = {
                'balance': new_balance,
                'total_earned': wallet.total_earned + amount
            }
        
        # 3. 일괄 생성
        PointTransaction.objects.bulk_create(transactions_to_create)
        
        # 4. 일괄 업데이트
        for wallet_id, updates in wallets_to_update.items():
            PointWallet.objects.filter(id=wallet_id).update(**updates)
    
    return len(transactions_to_create)

# Celery로 비동기 처리
@shared_task
def process_daily_attendance_points():
    """출석 체크 포인트 일괄 지급"""
    
    # 오늘 출석한 사용자
    attended_users = Attendance.objects.filter(
        date=timezone.now().date()
    ).values_list('user_id', flat=True)
    
    # 배치 지급
    user_point_list = [
        (user_id, Decimal('10.00'), 'ATTENDANCE')
        for user_id in attended_users
    ]
    
    count = bulk_earn_points(user_point_list)
    
    logger.info(f"Attendance points granted to {count} users")
    return count
```

---

## 11. 테스트 전략

### 11.1 단위 테스트

```python
# points/tests/test_services.py
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from points.services import PointService
from points.models import PointWallet, PointTransaction

User = get_user_model()

class PointServiceTest(TransactionTestCase):
    """포인트 서비스 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
    
    def test_earn_points_success(self):
        """포인트 적립 성공"""
        # Given
        amount = Decimal('1000.00')
        
        # When
        trans, created = PointService.earn_points(
            user=self.user,
            amount=amount,
            reason_code='PURCHASE',
            description='테스트 구매',
            idempotency_key='test_earn_1'
        )
        
        # Then
        self.assertTrue(created)
        self.assertEqual(trans.amount, amount)
        
        wallet = PointWallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, amount)
        self.assertEqual(wallet.total_earned, amount)
    
    def test_earn_points_idempotency(self):
        """중복 적립 방지"""
        # Given
        key = 'test_idempotency_1'
        
        # When - 첫 번째 요청
        trans1, created1 = PointService.earn_points(
            user=self.user,
            amount=Decimal('100.00'),
            reason_code='PURCHASE',
            description='테스트',
            idempotency_key=key
        )
        
        # When - 두 번째 요청 (같은 키)
        trans2, created2 = PointService.earn_points(
            user=self.user,
            amount=Decimal('100.00'),
            reason_code='PURCHASE',
            description='테스트',
            idempotency_key=key
        )
        
        # Then
        self.assertTrue(created1)
        self.assertFalse(created2)  # 중복 요청
        self.assertEqual(trans1.id, trans2.id)  # 같은 거래
        
        wallet = PointWallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal('100.00'))  # 한 번만 적립
    
    def test_use_points_insufficient_balance(self):
        """잔액 부족 시 사용 실패"""
        # Given
        PointService.earn_points(
            user=self.user,
            amount=Decimal('100.00'),
            reason_code='PURCHASE',
            description='테스트',
            idempotency_key='earn_1'
        )
        
        # When & Then
        with self.assertRaises(ValueError) as context:
            PointService.use_points(
                user=self.user,
                amount=Decimal('200.00'),  # 잔액보다 많음
                reason_code='PAYMENT',
                description='테스트',
                idempotency_key='use_1'
            )
        
        self.assertIn('Insufficient balance', str(context.exception))
        
        # 잔액 변동 없음
        wallet = PointWallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal('100.00'))
    
    def test_use_points_fifo(self):
        """FIFO 순서로 사용"""
        # Given - 3번 적립
        PointService.earn_points(
            self.user, Decimal('100.00'), 'PURCHASE', 'First', 'earn_1'
        )
        PointService.earn_points(
            self.user, Decimal('200.00'), 'PURCHASE', 'Second', 'earn_2'
        )
        PointService.earn_points(
            self.user, Decimal('300.00'), 'PURCHASE', 'Third', 'earn_3'
        )
        
        # When - 250 사용
        PointService.use_points(
            self.user, Decimal('250.00'), 'PAYMENT', 'Test', 'use_1'
        )
        
        # Then - 첫 번째(100) + 두 번째 일부(150) 사용
        from points.models import PointUsage
        
        usages = PointUsage.objects.filter(
            use_transaction__idempotency_key='use_1'
        ).order_by('earn_transaction__created_at')
        
        self.assertEqual(len(usages), 2)
        self.assertEqual(usages[0].amount, Decimal('100.00'))  # First 전체
        self.assertEqual(usages[1].amount, Decimal('150.00'))  # Second 일부
```

### 11.2 동시성 테스트

```python
import threading
from django.test import TransactionTestCase

class ConcurrencyTest(TransactionTestCase):
    """동시성 제어 테스트"""
    
    def test_concurrent_use_points(self):
        """동시에 포인트 사용 시 Race Condition 방지"""
        # Given
        user = User.objects.create_user(username='concurrent_test')
        PointService.earn_points(
            user, Decimal('1000.00'), 'PURCHASE', 'Init', 'init_1'
        )
        
        results = []
        errors = []
        
        def use_points_thread(amount, key):
            try:
                trans, created = PointService.use_points(
                    user, amount, 'PAYMENT', 'Test', key
                )
                results.append((trans, created))
            except Exception as e:
                errors.append(e)
        
        # When - 동시에 10개 요청 (각 200 포인트)
        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=use_points_thread,
                args=(Decimal('200.00'), f'concurrent_{i}')
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Then
        # 5개 성공, 5개 실패 (잔액 1000, 200씩 5번 = 1000)
        self.assertEqual(len(results), 5)
        self.assertEqual(len(errors), 5)
        
        # 최종 잔액 0
        wallet = PointWallet.objects.get(user=user)
        self.assertEqual(wallet.balance, Decimal('0.00'))
        
        # 모든 에러가 잔액 부족
        for error in errors:
            self.assertIn('Insufficient balance', str(error))
```

### 11.3 통합 테스트

```python
# API 통합 테스트
from ninja.testing import TestClient
from config.urls import api

class PointAPITest(TestCase):
    """포인트 API 통합 테스트"""
    
    def setUp(self):
        self.client = TestClient(api)
        self.user = User.objects.create_user(
            username='apitest',
            password='testpass123'
        )
        # 인증 토큰
        self.token = generate_token(self.user)
    
    def test_earn_points_api(self):
        """포인트 적립 API"""
        response = self.client.post(
            '/points/earn',
            json={
                'amount': '1000.00',
                'reason_code': 'PURCHASE',
                'description': 'API 테스트',
                'idempotency_key': 'api_test_1'
            },
            headers={'Authorization': f'Bearer {self.token}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['amount'], '1000.00')
    
    def test_get_balance_api(self):
        """잔액 조회 API"""
        # Given - 포인트 적립
        PointService.earn_points(
            self.user, Decimal('5000.00'), 'PURCHASE', 'Test', 'setup_1'
        )
        
        # When
        response = self.client.get(
            '/points/balance',
            headers={'Authorization': f'Bearer {self.token}'}
        )
        
        # Then
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['balance'], '5000.00')
```

---

## 12. 실전 주의사항

### 12.1 반드시 피해야 할 실수

```python
# ❌ 실수 1: Float 사용
class BadPointWallet(models.Model):
    balance = models.FloatField()  # 절대 금지!

# 문제:
0.1 + 0.2 = 0.30000000000000004  # 부동소수점 오차
1000.00 - 0.01 = 999.99... 또는 1000.00  # 불확실

# ✅ 올바른 방법: Decimal
from decimal import Decimal

class PointWallet(models.Model):
    balance = models.DecimalField(max_digits=12, decimal_places=2)

# 사용:
balance = Decimal('1000.00')
balance -= Decimal('0.01')  # 정확히 999.99


# ❌ 실수 2: 트랜잭션 없이 잔액 업데이트
def bad_update(user_id, amount):
    wallet = PointWallet.objects.get(user_id=user_id)
    wallet.balance += amount  # Race Condition!
    wallet.save()

# ✅ 올바른 방법
@transaction.atomic
def good_update(user_id, amount):
    wallet = PointWallet.objects.select_for_update().get(user_id=user_id)
    wallet.balance += amount
    wallet.save()


# ❌ 실수 3: Idempotency 없음
def bad_earn(user, amount):
    # 중복 요청 시 여러 번 적립!
    wallet = PointWallet.objects.get(user=user)
    wallet.balance += amount
    wallet.save()

# ✅ 올바른 방법
def good_earn(user, amount, idempotency_key):
    if PointTransaction.objects.filter(idempotency_key=idempotency_key).exists():
        return  # 중복 방지
    # ...


# ❌ 실수 4: 거래 내역 삭제/수정
def bad_cancel(transaction_id):
    trans = PointTransaction.objects.get(id=transaction_id)
    trans.delete()  # 감사 추적 불가!

# ✅ 올바른 방법
def good_cancel(transaction_id):
    original = PointTransaction.objects.get(id=transaction_id)
    # 반대 거래 생성
    PointTransaction.objects.create(
        wallet=original.wallet,
        transaction_type='CANCEL',
        amount=-original.amount,
        # ...
    )


# ❌ 실수 5: 만료 체크 없이 사용
def bad_use(user, amount):
    wallet = PointWallet.objects.get(user=user)
    if wallet.balance >= amount:
        wallet.balance -= amount  # 만료된 포인트도 사용!
        wallet.save()

# ✅ 올바른 방법
def good_use(user, amount):
    # 만료되지 않은 포인트만 조회
    available_earns = PointTransaction.objects.filter(
        wallet__user=user,
        transaction_type='EARN',
        is_expired=False,
        expires_at__gt=timezone.now()  # 만료 체크!
    )
    # FIFO로 사용
    # ...
```

### 12.2 성능 주의사항

```python
# ⚠️ 주의 1: 큰 테이블 전체 스캔
def bad_query():
    # 수백만 건 조회 → 느림!
    all_trans = PointTransaction.objects.all()

# ✅ 개선: 페이징 또는 필터링
def good_query(user_id, page=1, size=20):
    return PointTransaction.objects.filter(
        wallet__user_id=user_id
    )[:size]


# ⚠️ 주의 2: N+1 쿼리
def bad_history(user_id):
    trans = PointTransaction.objects.filter(wallet__user_id=user_id)
    for t in trans:
        print(t.wallet.user.username)  # 매번 쿼리!

# ✅ 개선: select_related
def good_history(user_id):
    trans = PointTransaction.objects.filter(
        wallet__user_id=user_id
    ).select_related('wallet__user')


# ⚠️ 주의 3: 비효율적 집계
def bad_sum(user_id):
    trans = PointTransaction.objects.filter(wallet__user_id=user_id)
    total = sum([t.amount for t in trans])  # 파이썬에서 계산!

# ✅ 개선: DB 집계
def good_sum(user_id):
    result = PointTransaction.objects.filter(
        wallet__user_id=user_id
    ).aggregate(total=Sum('amount'))
    return result['total']
```

### 12.3 체크리스트

**배포 전 필수 확인:**

```
□ Decimal 사용 (Float 금지)
□ select_for_update로 동시성 제어
□ @transaction.atomic 사용
□ Idempotency Key 구현
□ 잔액 음수 방지 (DB Constraint)
□ 만료 처리 배치 작업
□ 인덱스 최적화
□ Rate Limiting 적용
□ 입력 검증 강화
□ 로깅 및 모니터링
□ 단위 테스트 작성
□ 동시성 테스트 작성
□ API 문서화
□ 에러 핸들링
□ 감사 로그 구현
```

---

## 결론

### 핵심 요약

Django-Ninja로 안전한 포인트 시스템을 구축하기 위한 핵심 원칙:

1. **동시성 제어**: `select_for_update()` + `@transaction.atomic` 필수
2. **Idempotency**: 중복 요청 방지로 정합성 보장
3. **Decimal 사용**: Float 절대 금지, 정확한 금액 계산
4. **불변 로그**: 거래 내역 삭제/수정 금지, 취소는 반대 거래로
5. **FIFO 관리**: 포인트 사용 시 선입선출 구현
6. **만료 처리**: 자동 배치 작업으로 만료 포인트 관리
7. **보안**: 인증, 권한, Rate Limiting, 입력 검증
8. **성능**: 인덱싱, 쿼리 최적화, 캐싱 전략
9. **테스트**: 단위, 동시성, 통합 테스트 작성
10. **모니터링**: 로깅, 감사 추적, 알림

### 실전 적용 순서

```
1단계: 기본 구조 (1-2일)
- 모델 설계 (Decimal, 인덱스)
- 기본 API (조회, 적립, 사용)
- Pydantic 스키마

2단계: 동시성 제어 (1일)
- select_for_update 적용
- transaction.atomic 적용
- 음수 방지 Constraint

3단계: Idempotency (1일)
- Idempotency Key 구현
- 중복 처리 로직
- 테스트 작성

4단계: FIFO & 만료 (1-2일)
- PointUsage 모델
- FIFO 사용 로직
- 만료 배치 작업

5단계: 보안 & 성능 (1-2일)
- 인증/권한
- Rate Limiting
- 쿼리 최적화
- 캐싱

6단계: 운영 준비 (1일)
- 로깅/모니터링
- 감사 로그
- API 문서화
```

### 추가 학습 자료

- [Django-Ninja 공식 문서](https://django-ninja.rest-framework.com/)
- [Django 트랜잭션 가이드](https://docs.djangoproject.com/en/stable/topics/db/transactions/)
- [PostgreSQL Lock 모드](https://www.postgresql.org/docs/current/explicit-locking.html)
- [Idempotency 패턴](https://stripe.com/docs/api/idempotent_requests)

**안전하고 확장 가능한 포인트 시스템 구축 화이팅!** 🚀💰

---

## 참고 코드

전체 예제 코드는 GitHub에서 확인할 수 있습니다:
- [Django-Ninja Point System Example](https://github.com/example/django-ninja-points)


