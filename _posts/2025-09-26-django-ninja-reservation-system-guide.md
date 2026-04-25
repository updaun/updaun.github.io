---
layout: post
title: "Django Ninja로 예약 시스템 구축하기: 완전한 RESTful API 개발 가이드"
date: 2025-09-26 14:00:00 +0900
categories: [Web Development, Backend]
tags: [django, django-ninja, reservation system, rest api, python, booking system]
description: "Django Ninja를 활용하여 완전한 예약 시스템을 구축하는 방법을 단계별로 설명합니다. 사용자 인증, 예약 관리, 결제 연동까지 실무에서 사용할 수 있는 완전한 시스템을 만들어보겠습니다."
author: "updaun"
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-09-26-django-ninja-reservation-system-guide.webp"
---

## 개요

예약 시스템은 많은 비즈니스에서 핵심적인 기능입니다. 레스토랑, 병원, 미용실, 회의실 등 다양한 분야에서 활용되는 예약 시스템을 Django Ninja를 사용하여 효율적이고 확장 가능한 RESTful API로 구축하는 방법을 알아보겠습니다.

## Django Ninja를 선택하는 이유

### 1. 성능과 개발 생산성
- **FastAPI 스타일**: FastAPI의 장점을 Django에서 활용
- **자동 문서화**: OpenAPI/Swagger 자동 생성
- **타입 힌트**: Python 타입 힌트 기반 검증
- **비동기 지원**: async/await 완전 지원

### 2. Django 생태계와의 완벽한 통합
- **Django ORM**: 기존 Django 모델 그대로 활용
- **미들웨어**: Django의 모든 미들웨어 사용 가능
- **인증/권한**: Django의 강력한 인증 시스템 활용

## 프로젝트 설정

### 1. 프로젝트 초기화

```bash
# 가상환경 생성 및 활성화
python -m venv reservation_env
source reservation_env/bin/activate  # Windows: reservation_env\Scripts\activate

# Django 프로젝트 생성
pip install django django-ninja python-decouple
django-admin startproject reservation_system
cd reservation_system
python manage.py startapp reservations
```

### 2. 설정 파일 구성

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
    'reservations',
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

ROOT_URLCONF = 'reservation_system.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='reservation_db'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# 시간대 설정
TIME_ZONE = 'Asia/Seoul'
USE_TZ = True

# CORS 설정 (프론트엔드 연동용)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

## 데이터 모델 설계

### 1. 예약 시스템 모델

```python
# reservations/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, timedelta
import uuid

class Category(models.Model):
    """서비스 카테고리"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class Service(models.Model):
    """예약 가능한 서비스"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=200)
    description = models.TextField()
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    max_capacity = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.duration}min)"

class TimeSlot(models.Model):
    """시간대 관리"""
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='time_slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    available_capacity = models.PositiveIntegerField()
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['service', 'date', 'start_time']
        indexes = [
            models.Index(fields=['date', 'service']),
            models.Index(fields=['is_available']),
        ]
    
    def __str__(self):
        return f"{self.service.name} - {self.date} {self.start_time}"

class Reservation(models.Model):
    """예약 정보"""
    
    class StatusChoices(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'
        COMPLETED = 'completed', 'Completed'
        NO_SHOW = 'no_show', 'No Show'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='reservations')
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE, related_name='reservations')
    
    # 예약자 정보
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    
    # 예약 상태 및 메타데이터
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    notes = models.TextField(blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['time_slot', 'status']),
        ]
    
    def __str__(self):
        return f"{self.customer_name} - {self.service.name} ({self.status})"
    
    @property
    def is_cancellable(self):
        """취소 가능 여부 확인 (예약 시간 2시간 전까지)"""
        if self.status not in [self.StatusChoices.PENDING, self.StatusChoices.CONFIRMED]:
            return False
        
        reservation_datetime = datetime.combine(
            self.time_slot.date, 
            self.time_slot.start_time
        )
        return datetime.now() < reservation_datetime - timedelta(hours=2)

class Payment(models.Model):
    """결제 정보"""
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'
    
    class PaymentMethod(models.TextChoices):
        CARD = 'card', 'Credit Card'
        CASH = 'cash', 'Cash'
        TRANSFER = 'transfer', 'Bank Transfer'
        KAKAO_PAY = 'kakao_pay', 'Kakao Pay'
        NAVER_PAY = 'naver_pay', 'Naver Pay'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    
    # 결제 게이트웨이 정보
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Payment for {self.reservation.id} - {self.status}"
```

### 2. 마이그레이션 실행

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

## Pydantic 스키마 정의

### 1. 요청/응답 스키마

```python
# reservations/schemas.py
from ninja import Schema, Field
from pydantic import validator, EmailStr
from typing import List, Optional
from datetime import date, time, datetime
from decimal import Decimal
import uuid

# Base Schemas
class CategorySchema(Schema):
    id: int
    name: str
    description: str
    is_active: bool

class ServiceSchema(Schema):
    id: uuid.UUID
    category: CategorySchema
    name: str
    description: str
    duration: int
    price: Decimal
    max_capacity: int
    is_active: bool

class ServiceListSchema(Schema):
    id: uuid.UUID
    name: str
    duration: int
    price: Decimal
    category_name: str = Field(alias="category.name")

# Time Slot Schemas
class TimeSlotSchema(Schema):
    id: int
    date: date
    start_time: time
    end_time: time
    available_capacity: int
    is_available: bool

class AvailableTimeSlotSchema(Schema):
    id: int
    start_time: time
    end_time: time
    available_capacity: int

# Reservation Schemas
class ReservationCreateSchema(Schema):
    service_id: uuid.UUID
    time_slot_id: int
    customer_name: str = Field(min_length=2, max_length=100)
    customer_email: EmailStr
    customer_phone: str = Field(regex=r'^[0-9\-+().\s]+$')
    notes: Optional[str] = None
    
    @validator('customer_phone')
    def validate_phone(cls, v):
        # 전화번호 유효성 검사
        import re
        phone_pattern = r'^(?:\+?82)?(?:0)?1[0-9]{8,9}$'
        if not re.match(phone_pattern, v.replace('-', '').replace(' ', '')):
            raise ValueError('Invalid phone number format')
        return v

class ReservationUpdateSchema(Schema):
    customer_name: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    notes: Optional[str] = None

class ReservationSchema(Schema):
    id: uuid.UUID
    service: ServiceListSchema
    time_slot: TimeSlotSchema
    customer_name: str
    customer_email: str
    customer_phone: str
    status: str
    notes: str
    total_price: Decimal
    created_at: datetime
    is_cancellable: bool

class ReservationListSchema(Schema):
    id: uuid.UUID
    service_name: str = Field(alias="service.name")
    date: date = Field(alias="time_slot.date")
    start_time: time = Field(alias="time_slot.start_time")
    customer_name: str
    status: str
    total_price: Decimal
    created_at: datetime

# Search and Filter Schemas
class AvailabilityQuerySchema(Schema):
    service_id: uuid.UUID
    date: date

class ReservationFilterSchema(Schema):
    status: Optional[str] = None
    service_id: Optional[uuid.UUID] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    customer_email: Optional[str] = None

# Payment Schemas
class PaymentCreateSchema(Schema):
    method: str
    amount: Decimal

class PaymentSchema(Schema):
    id: uuid.UUID
    amount: Decimal
    method: str
    status: str
    transaction_id: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

# Statistics Schema
class ReservationStatsSchema(Schema):
    total_reservations: int
    confirmed_reservations: int
    cancelled_reservations: int
    total_revenue: Decimal
    popular_services: List[dict]
```

## API 엔드포인트 구현

### 1. 메인 API 라우터

```python
# reservation_system/urls.py
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from reservations.api import router as reservations_router

# API 인스턴스 생성
api = NinjaAPI(
    title="Reservation System API",
    version="1.0.0",
    description="A comprehensive reservation system built with Django Ninja",
    docs_url="/docs/",
)

# 라우터 등록
api.add_router("/reservations/", reservations_router, tags=["Reservations"])

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
```

### 2. 예약 시스템 API

```python
# reservations/api.py
from ninja import Router, Query
from ninja.pagination import paginate, PageNumberPagination
from ninja.responses import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count, Sum
from typing import List
from datetime import datetime, date, timedelta

from .models import Category, Service, TimeSlot, Reservation, Payment
from .schemas import (
    CategorySchema, ServiceSchema, ServiceListSchema,
    TimeSlotSchema, AvailableTimeSlotSchema,
    ReservationCreateSchema, ReservationUpdateSchema, 
    ReservationSchema, ReservationListSchema,
    AvailabilityQuerySchema, ReservationFilterSchema,
    PaymentCreateSchema, PaymentSchema,
    ReservationStatsSchema
)

router = Router()

# 카테고리 및 서비스 조회
@router.get("/categories", response=List[CategorySchema])
def list_categories(request):
    """활성 카테고리 목록 조회"""
    return Category.objects.filter(is_active=True)

@router.get("/services", response=List[ServiceListSchema])
def list_services(request, category_id: int = None):
    """서비스 목록 조회"""
    queryset = Service.objects.filter(is_active=True).select_related('category')
    
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    
    return queryset

@router.get("/services/{service_id}", response=ServiceSchema)
def get_service(request, service_id: str):
    """특정 서비스 상세 조회"""
    service = get_object_or_404(Service, id=service_id, is_active=True)
    return service

# 시간대 및 가용성 조회
@router.get("/availability", response=List[AvailableTimeSlotSchema])
def check_availability(request, query: AvailabilityQuerySchema = Query(...)):
    """특정 날짜의 예약 가능한 시간대 조회"""
    time_slots = TimeSlot.objects.filter(
        service_id=query.service_id,
        date=query.date,
        is_available=True,
        available_capacity__gt=0
    ).order_by('start_time')
    
    return time_slots

@router.get("/availability/calendar/{service_id}")
def get_availability_calendar(request, service_id: str, year: int, month: int):
    """월별 예약 가능 날짜 캘린더"""
    from calendar import monthrange
    
    # 해당 월의 모든 날짜 조회
    last_day = monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)
    
    available_dates = TimeSlot.objects.filter(
        service_id=service_id,
        date__range=[start_date, end_date],
        is_available=True,
        available_capacity__gt=0
    ).values_list('date', flat=True).distinct()
    
    return {
        "year": year,
        "month": month,
        "available_dates": list(available_dates)
    }

# 예약 관리
@router.post("/", response=ReservationSchema)
@transaction.atomic
def create_reservation(request, payload: ReservationCreateSchema):
    """새 예약 생성"""
    
    # 서비스 및 시간대 검증
    service = get_object_or_404(Service, id=payload.service_id, is_active=True)
    time_slot = get_object_or_404(
        TimeSlot, 
        id=payload.time_slot_id, 
        service=service,
        is_available=True,
        available_capacity__gt=0
    )
    
    # 과거 날짜 예약 방지
    reservation_datetime = datetime.combine(time_slot.date, time_slot.start_time)
    if reservation_datetime <= datetime.now():
        return Response(
            {"error": "Cannot make reservations for past dates"},
            status=400
        )
    
    # 중복 예약 확인
    existing_reservation = Reservation.objects.filter(
        customer_email=payload.customer_email,
        time_slot=time_slot,
        status__in=['pending', 'confirmed']
    ).exists()
    
    if existing_reservation:
        return Response(
            {"error": "You already have a reservation for this time slot"},
            status=400
        )
    
    # 예약 생성
    reservation = Reservation.objects.create(
        user=request.user if request.user.is_authenticated else None,
        service=service,
        time_slot=time_slot,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        customer_phone=payload.customer_phone,
        notes=payload.notes or "",
        total_price=service.price,
        status=Reservation.StatusChoices.PENDING
    )
    
    # 가용 용량 감소
    time_slot.available_capacity -= 1
    if time_slot.available_capacity == 0:
        time_slot.is_available = False
    time_slot.save()
    
    return reservation

@router.get("/", response=List[ReservationListSchema])
@paginate(PageNumberPagination, page_size=20)
def list_reservations(request, filters: ReservationFilterSchema = Query(...)):
    """예약 목록 조회 (필터링 지원)"""
    queryset = Reservation.objects.select_related(
        'service', 'time_slot'
    ).order_by('-created_at')
    
    # 사용자별 필터링 (인증된 사용자만 자신의 예약 조회)
    if request.user.is_authenticated and not request.user.is_staff:
        queryset = queryset.filter(user=request.user)
    
    # 필터 적용
    if filters.status:
        queryset = queryset.filter(status=filters.status)
    
    if filters.service_id:
        queryset = queryset.filter(service_id=filters.service_id)
    
    if filters.date_from:
        queryset = queryset.filter(time_slot__date__gte=filters.date_from)
    
    if filters.date_to:
        queryset = queryset.filter(time_slot__date__lte=filters.date_to)
    
    if filters.customer_email:
        queryset = queryset.filter(customer_email__icontains=filters.customer_email)
    
    return queryset

@router.get("/{reservation_id}", response=ReservationSchema)
def get_reservation(request, reservation_id: str):
    """특정 예약 상세 조회"""
    reservation = get_object_or_404(
        Reservation.objects.select_related('service', 'time_slot', 'service__category'),
        id=reservation_id
    )
    
    # 권한 확인
    if request.user.is_authenticated:
        if not request.user.is_staff and reservation.user != request.user:
            return Response({"error": "Permission denied"}, status=403)
    
    return reservation

@router.put("/{reservation_id}", response=ReservationSchema)
@transaction.atomic
def update_reservation(request, reservation_id: str, payload: ReservationUpdateSchema):
    """예약 정보 수정"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # 권한 및 상태 확인
    if request.user.is_authenticated and not request.user.is_staff:
        if reservation.user != request.user:
            return Response({"error": "Permission denied"}, status=403)
    
    if reservation.status not in ['pending', 'confirmed']:
        return Response(
            {"error": "Cannot update cancelled or completed reservations"},
            status=400
        )
    
    # 정보 업데이트
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(reservation, field, value)
    
    reservation.save()
    return reservation

@router.post("/{reservation_id}/cancel")
@transaction.atomic  
def cancel_reservation(request, reservation_id: str):
    """예약 취소"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # 권한 확인
    if request.user.is_authenticated and not request.user.is_staff:
        if reservation.user != request.user:
            return Response({"error": "Permission denied"}, status=403)
    
    # 취소 가능 여부 확인
    if not reservation.is_cancellable:
        return Response(
            {"error": "This reservation cannot be cancelled"},
            status=400
        )
    
    # 취소 처리
    reservation.status = Reservation.StatusChoices.CANCELLED
    reservation.cancelled_at = datetime.now()
    reservation.save()
    
    # 시간대 가용성 복구
    time_slot = reservation.time_slot
    time_slot.available_capacity += 1
    time_slot.is_available = True
    time_slot.save()
    
    return {"message": "Reservation cancelled successfully"}

@router.post("/{reservation_id}/confirm")
def confirm_reservation(request, reservation_id: str):
    """예약 확정 (관리자만)"""
    if not request.user.is_staff:
        return Response({"error": "Staff access required"}, status=403)
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    if reservation.status != Reservation.StatusChoices.PENDING:
        return Response(
            {"error": "Only pending reservations can be confirmed"},
            status=400
        )
    
    reservation.status = Reservation.StatusChoices.CONFIRMED
    reservation.save()
    
    return {"message": "Reservation confirmed successfully"}

# 결제 관리
@router.post("/{reservation_id}/payment", response=PaymentSchema)
@transaction.atomic
def create_payment(request, reservation_id: str, payload: PaymentCreateSchema):
    """결제 생성"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # 기존 결제 확인
    if hasattr(reservation, 'payment'):
        return Response(
            {"error": "Payment already exists for this reservation"},
            status=400
        )
    
    # 결제 생성
    payment = Payment.objects.create(
        reservation=reservation,
        amount=payload.amount,
        method=payload.method,
        status=Payment.PaymentStatus.PENDING
    )
    
    # 실제 결제 게이트웨이 연동 로직 (예: 아임포트, 토스페이먼츠 등)
    # payment_result = process_payment(payment)
    
    # 결제 성공 시 예약 확정
    # if payment_result['success']:
    #     payment.status = Payment.PaymentStatus.COMPLETED
    #     payment.transaction_id = payment_result['transaction_id']
    #     payment.completed_at = datetime.now()
    #     payment.save()
    #     
    #     reservation.status = Reservation.StatusChoices.CONFIRMED
    #     reservation.save()
    
    return payment

# 통계 및 관리
@router.get("/stats/overview", response=ReservationStatsSchema)
def get_reservation_stats(request, date_from: date = None, date_to: date = None):
    """예약 통계 조회 (관리자만)"""
    if not request.user.is_staff:
        return Response({"error": "Staff access required"}, status=403)
    
    # 기본 날짜 범위 설정 (최근 30일)
    if not date_from:
        date_from = date.today() - timedelta(days=30)
    if not date_to:
        date_to = date.today()
    
    queryset = Reservation.objects.filter(
        created_at__date__range=[date_from, date_to]
    )
    
    # 기본 통계
    total_reservations = queryset.count()
    confirmed_reservations = queryset.filter(status='confirmed').count()
    cancelled_reservations = queryset.filter(status='cancelled').count()
    
    # 총 수익
    total_revenue = queryset.filter(
        status__in=['confirmed', 'completed']
    ).aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    # 인기 서비스
    popular_services = queryset.filter(
        status__in=['confirmed', 'completed']
    ).values(
        'service__name'
    ).annotate(
        count=Count('id'),
        revenue=Sum('total_price')
    ).order_by('-count')[:5]
    
    return {
        "total_reservations": total_reservations,
        "confirmed_reservations": confirmed_reservations,
        "cancelled_reservations": cancelled_reservations,
        "total_revenue": total_revenue,
        "popular_services": list(popular_services)
    }

# 시간대 관리 (관리자 전용)
@router.post("/admin/time-slots/generate")
def generate_time_slots(request, service_id: str, start_date: date, end_date: date):
    """시간대 자동 생성 (관리자만)"""
    if not request.user.is_staff:
        return Response({"error": "Staff access required"}, status=403)
    
    service = get_object_or_404(Service, id=service_id)
    
    # 기본 운영 시간 설정 (9:00 - 18:00)
    from datetime import time as dt_time
    
    operating_hours = [
        (dt_time(9, 0), dt_time(10, 0)),
        (dt_time(10, 0), dt_time(11, 0)),
        (dt_time(11, 0), dt_time(12, 0)),
        (dt_time(14, 0), dt_time(15, 0)),
        (dt_time(15, 0), dt_time(16, 0)),
        (dt_time(16, 0), dt_time(17, 0)),
        (dt_time(17, 0), dt_time(18, 0)),
    ]
    
    created_slots = []
    current_date = start_date
    
    while current_date <= end_date:
        # 주말 제외 (선택사항)
        if current_date.weekday() < 5:  # 월-금요일만
            for start_time, end_time in operating_hours:
                slot, created = TimeSlot.objects.get_or_create(
                    service=service,
                    date=current_date,
                    start_time=start_time,
                    defaults={
                        'end_time': end_time,
                        'available_capacity': service.max_capacity,
                        'is_available': True,
                    }
                )
                
                if created:
                    created_slots.append(slot)
        
        current_date += timedelta(days=1)
    
    return {
        "message": f"Generated {len(created_slots)} time slots",
        "created_slots": len(created_slots)
    }
```

## 인증 및 권한 관리

### 1. JWT 인증 통합

```python
# reservations/auth.py
from ninja.security import HttpBearer
from django.contrib.auth.models import User
from django.conf import settings
import jwt

class JWTAuth(HttpBearer):
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user = User.objects.get(id=payload['user_id'])
            return user
        except (jwt.InvalidTokenError, User.DoesNotExist):
            return None

# API에 인증 적용
from ninja import NinjaAPI

api = NinjaAPI(auth=JWTAuth())
```

### 2. 권한 데코레이터

```python
# reservations/decorators.py
from functools import wraps
from ninja.responses import Response

def staff_required(view_func):
    """관리자 권한 필요"""
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return Response({"error": "Staff access required"}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapped_view

def owner_or_staff_required(view_func):
    """소유자 또는 관리자 권한 필요"""
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)
        
        # 관리자는 모든 권한
        if request.user.is_staff:
            return view_func(request, *args, **kwargs)
        
        # 소유자 권한 확인 로직 (각 뷰에서 구현)
        return view_func(request, *args, **kwargs)
    return wrapped_view
```

## 결제 시스템 연동

### 1. 아임포트 결제 연동

```python
# reservations/payments.py
import requests
from django.conf import settings
from typing import Dict, Any

class PaymentGateway:
    """결제 게이트웨이 통합"""
    
    def __init__(self):
        self.iamport_key = settings.IAMPORT_KEY
        self.iamport_secret = settings.IAMPORT_SECRET
        self.base_url = "https://api.iamport.kr"
    
    def get_access_token(self) -> str:
        """아임포트 액세스 토큰 획득"""
        url = f"{self.base_url}/users/getToken"
        data = {
            "imp_key": self.iamport_key,
            "imp_secret": self.iamport_secret
        }
        
        response = requests.post(url, data=data)
        result = response.json()
        
        if result.get("code") == 0:
            return result["response"]["access_token"]
        else:
            raise Exception(f"Failed to get access token: {result.get('message')}")
    
    def verify_payment(self, imp_uid: str) -> Dict[str, Any]:
        """결제 검증"""
        access_token = self.get_access_token()
        
        url = f"{self.base_url}/payments/{imp_uid}"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = requests.get(url, headers=headers)
        result = response.json()
        
        if result.get("code") == 0:
            return result["response"]
        else:
            raise Exception(f"Payment verification failed: {result.get('message')}")
    
    def cancel_payment(self, imp_uid: str, amount: int, reason: str) -> Dict[str, Any]:
        """결제 취소"""
        access_token = self.get_access_token()
        
        url = f"{self.base_url}/payments/cancel"
        headers = {"Authorization": f"Bearer {access_token}"}
        data = {
            "imp_uid": imp_uid,
            "amount": amount,
            "reason": reason
        }
        
        response = requests.post(url, headers=headers, data=data)
        result = response.json()
        
        if result.get("code") == 0:
            return result["response"]
        else:
            raise Exception(f"Payment cancellation failed: {result.get('message')}")

# 결제 처리 함수
def process_payment(payment: Payment, imp_uid: str) -> bool:
    """결제 처리 및 검증"""
    gateway = PaymentGateway()
    
    try:
        # 결제 검증
        payment_info = gateway.verify_payment(imp_uid)
        
        # 금액 검증
        if payment_info["amount"] != int(payment.amount):
            raise Exception("Payment amount mismatch")
        
        # 결제 완료 처리
        payment.status = Payment.PaymentStatus.COMPLETED
        payment.transaction_id = imp_uid
        payment.gateway_response = payment_info
        payment.completed_at = timezone.now()
        payment.save()
        
        # 예약 확정
        reservation = payment.reservation
        reservation.status = Reservation.StatusChoices.CONFIRMED
        reservation.save()
        
        return True
        
    except Exception as e:
        # 결제 실패 처리
        payment.status = Payment.PaymentStatus.FAILED
        payment.gateway_response = {"error": str(e)}
        payment.save()
        
        return False
```

## 알림 시스템 구현

### 1. 이메일 알림

```python
# reservations/notifications.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from celery import shared_task
from .models import Reservation

@shared_task
def send_reservation_confirmation(reservation_id: str):
    """예약 확인 이메일 발송"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)
        
        subject = f"예약 확인 - {reservation.service.name}"
        
        context = {
            'reservation': reservation,
            'customer_name': reservation.customer_name,
            'service_name': reservation.service.name,
            'date': reservation.time_slot.date,
            'start_time': reservation.time_slot.start_time,
        }
        
        html_message = render_to_string('emails/reservation_confirmation.html', context)
        plain_message = render_to_string('emails/reservation_confirmation.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reservation.customer_email],
            html_message=html_message,
        )
        
    except Exception as e:
        print(f"Failed to send confirmation email: {e}")

@shared_task
def send_reservation_reminder(reservation_id: str):
    """예약 리마인더 이메일 발송"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)
        
        if reservation.status != Reservation.StatusChoices.CONFIRMED:
            return
        
        subject = f"예약 리마인더 - {reservation.service.name}"
        
        context = {
            'reservation': reservation,
            'customer_name': reservation.customer_name,
            'service_name': reservation.service.name,
            'date': reservation.time_slot.date,
            'start_time': reservation.time_slot.start_time,
        }
        
        html_message = render_to_string('emails/reservation_reminder.html', context)
        plain_message = render_to_string('emails/reservation_reminder.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reservation.customer_email],
            html_message=html_message,
        )
        
    except Exception as e:
        print(f"Failed to send reminder email: {e}")
```

### 2. 이메일 템플릿

```html
<!-- templates/emails/reservation_confirmation.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>예약 확인</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #f8f9fa; padding: 20px; text-align: center; }
        .content { padding: 20px; }
        .reservation-details { background-color: #e9ecef; padding: 15px; margin: 20px 0; }
        .footer { text-align: center; color: #6c757d; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>예약이 확인되었습니다!</h1>
        </div>
        
        <div class="content">
            <p>안녕하세요, {{ customer_name }}님!</p>
            
            <p>다음 예약이 성공적으로 접수되었습니다:</p>
            
            <div class="reservation-details">
                <h3>예약 정보</h3>
                <p><strong>서비스:</strong> {{ service_name }}</p>
                <p><strong>날짜:</strong> {{ date }}</p>
                <p><strong>시간:</strong> {{ start_time }}</p>
                <p><strong>예약 번호:</strong> {{ reservation.id }}</p>
            </div>
            
            <p>예약 변경이나 취소가 필요한 경우, 예약 시간 2시간 전까지 가능합니다.</p>
            
            <p>감사합니다!</p>
        </div>
        
        <div class="footer">
            <p>이 메일은 자동으로 발송된 메일입니다.</p>
        </div>
    </div>
</body>
</html>
```

## 테스트 및 검증

### 1. API 테스트

```python
# reservations/tests.py
from django.test import TestCase
from django.contrib.auth.models import User
from ninja.testing import TestClient
from datetime import date, time
from .models import Category, Service, TimeSlot, Reservation
from .api import router

class ReservationAPITest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 테스트 데이터 생성
        self.category = Category.objects.create(
            name='Test Category',
            description='Test Description'
        )
        
        self.service = Service.objects.create(
            category=self.category,
            name='Test Service',
            description='Test Service Description',
            duration=60,
            price=50000,
            max_capacity=5
        )
        
        self.time_slot = TimeSlot.objects.create(
            service=self.service,
            date=date(2025, 10, 1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            available_capacity=5
        )
    
    def test_list_services(self):
        """서비스 목록 조회 테스트"""
        response = self.client.get("/services")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
    
    def test_create_reservation(self):
        """예약 생성 테스트"""
        payload = {
            "service_id": str(self.service.id),
            "time_slot_id": self.time_slot.id,
            "customer_name": "홍길동",
            "customer_email": "hong@example.com",
            "customer_phone": "010-1234-5678"
        }
        
        response = self.client.post("/", json=payload)
        self.assertEqual(response.status_code, 200)
        
        # DB 확인
        reservation = Reservation.objects.first()
        self.assertEqual(reservation.customer_name, "홍길동")
        self.assertEqual(reservation.status, "pending")
    
    def test_check_availability(self):
        """가용성 확인 테스트"""
        response = self.client.get(
            "/availability",
            params={
                "service_id": str(self.service.id),
                "date": "2025-10-01"
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["available_capacity"], 5)
```

### 2. 성능 테스트

```python
# performance_test.py
import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor

async def make_request(session, url, data=None):
    """비동기 HTTP 요청"""
    if data:
        async with session.post(url, json=data) as response:
            return await response.json()
    else:
        async with session.get(url) as response:
            return await response.json()

async def performance_test():
    """성능 테스트 실행"""
    base_url = "http://localhost:8000/api/reservations"
    
    # 동시 요청 수
    concurrent_requests = 100
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        
        # 서비스 목록 조회 테스트
        tasks = [
            make_request(session, f"{base_url}/services")
            for _ in range(concurrent_requests)
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Completed {concurrent_requests} requests in {duration:.2f} seconds")
        print(f"Average response time: {duration/concurrent_requests:.3f} seconds")
        print(f"Requests per second: {concurrent_requests/duration:.2f}")

if __name__ == "__main__":
    asyncio.run(performance_test())
```

## 배포 및 운영

### 1. Docker 설정

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 정적 파일 수집
RUN python manage.py collectstatic --noinput

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "reservation_system.wsgi:application"]
```

### 2. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: reservation_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: your_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./media:/app/media

  celery:
    build: .
    command: celery -A reservation_system worker -l info
    environment:
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  celery-beat:
    build: .
    command: celery -A reservation_system beat -l info
    environment:
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
```

### 3. 모니터링 설정

```python
# reservation_system/monitoring.py
import logging
from django.core.management.base import BaseCommand
from django.db import connection
from reservations.models import Reservation, TimeSlot
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check system health and metrics'
    
    def handle(self, *args, **options):
        """시스템 상태 점검"""
        
        # 데이터베이스 연결 확인
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write("✅ Database connection: OK")
        except Exception as e:
            self.stdout.write(f"❌ Database connection: {e}")
        
        # 예약 통계
        today = datetime.now().date()
        
        today_reservations = Reservation.objects.filter(
            time_slot__date=today
        ).count()
        
        pending_reservations = Reservation.objects.filter(
            status='pending',
            time_slot__date__gte=today
        ).count()
        
        # 가용성 점검
        available_slots = TimeSlot.objects.filter(
            date__gte=today,
            is_available=True,
            available_capacity__gt=0
        ).count()
        
        self.stdout.write(f"📊 Today's reservations: {today_reservations}")
        self.stdout.write(f"⏳ Pending reservations: {pending_reservations}")
        self.stdout.write(f"📅 Available slots: {available_slots}")
        
        # 성능 메트릭
        from django.db import connection
        queries_count = len(connection.queries)
        
        self.stdout.write(f"🔍 Database queries: {queries_count}")
```

## 결론

Django Ninja를 활용한 예약 시스템 구축을 통해 다음과 같은 주요 기능들을 구현했습니다:

### 🎯 주요 구현 사항

1. **완전한 RESTful API**: OpenAPI/Swagger 자동 문서화
2. **실시간 가용성 확인**: 동시성 문제 해결
3. **유연한 예약 관리**: 상태 기반 워크플로우
4. **결제 시스템 연동**: 아임포트 등 PG사 연동
5. **권한 기반 접근 제어**: JWT 토큰 인증
6. **알림 시스템**: 이메일 자동 발송
7. **성능 최적화**: 인덱싱 및 쿼리 최적화
8. **모니터링**: 시스템 상태 추적

### 💡 Django Ninja의 장점

- **빠른 개발**: FastAPI 스타일의 직관적인 API 개발
- **자동 검증**: Pydantic 스키마 기반 데이터 검증
- **완벽한 문서화**: 인터랙티브 API 문서 자동 생성
- **Django 통합**: 기존 Django 프로젝트와 완벽 호환
- **성능**: 높은 처리량과 낮은 지연시간

이 예약 시스템은 레스토랑, 클리닉, 서비스업체 등 다양한 업종에 맞게 커스터마이징하여 사용할 수 있으며, 확장성과 유지보수성을 고려하여 설계되었습니다.