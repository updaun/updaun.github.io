---
layout: post
title: "Django Ninja API로 구축하는 고급 User 모델: 이메일 인증부터 관리자 승인까지"
date: 2025-08-02 10:00:00 +0900
categories: [Django, Python, Authentication, User Management, API]
tags: [Django, Django Ninja, User Model, Email Verification, Admin Approval, User Management, Custom User, REST API, Authentication]
---

Django로 사용자 관리 시스템을 구축할 때 기본 User 모델로는 한계가 있습니다. 실제 서비스에서는 이메일 인증, 관리자 승인, 계정 정지/활성화 등의 기능이 필요하며, 이를 API로 제공해야 하는 경우가 많습니다. 이 글에서는 Django Ninja를 사용하여 고급 User 모델을 API로 효율적으로 구현하는 방법을 단계별로 알아보겠습니다.

## 📚 고급 User 모델 설계 개요

### 구현할 기능들

1. **이메일 인증 시스템**: 회원가입 후 이메일로 인증 링크 발송
2. **관리자 승인 시스템**: 관리자가 수동으로 계정 승인
3. **계정 정지 기능**: 관리자가 사용자 계정을 정지
4. **계정 재활성화**: 정지된 계정을 다시 활성화

### User 상태 관리 전략

사용자의 상태를 체계적으로 관리하기 위해 다음과 같은 상태를 정의합니다:

```python
from django.db import models

class UserStatus(models.TextChoices):
    PENDING_EMAIL = 'pending_email', '이메일 인증 대기'
    PENDING_APPROVAL = 'pending_approval', '관리자 승인 대기'
    ACTIVE = 'active', '활성'
    SUSPENDED = 'suspended', '정지'
    DEACTIVATED = 'deactivated', '비활성'
```

## 🔧 Custom User 모델 구현

### 1. BaseUserManager 커스터마이징

먼저 사용자 생성 로직을 관리하는 매니저를 구현합니다:

```python
# accounts/managers.py
from django.contrib.auth.models import BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        """공통 사용자 생성 로직"""
        if not email:
            raise ValueError('이메일은 필수입니다.')
        
        try:
            validate_email(email)
        except ValidationError:
            raise ValueError('유효한 이메일 주소를 입력해주세요.')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        return user
    
    def create_user(self, email, password=None, **extra_fields):
        """일반 사용자 생성"""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('status', 'pending_email')
        
        user = self._create_user(email, password, **extra_fields)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """슈퍼유저 생성"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('status', 'active')
        extra_fields.setdefault('is_approved', True)
        extra_fields.setdefault('email_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('슈퍼유저는 is_staff=True여야 합니다.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('슈퍼유저는 is_superuser=True여야 합니다.')
        
        user = self._create_user(email, password, **extra_fields)
        user.save(using=self._db)
        return user
    
    def get_active_users(self):
        """활성 사용자만 조회"""
        return self.filter(status='active', is_active=True)
    
    def get_pending_approval_users(self):
        """승인 대기 사용자 조회"""
        return self.filter(status='pending_approval')
```

### 2. Custom User 모델 정의

```python
# accounts/models.py
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from .managers import CustomUserManager


class UserStatus(models.TextChoices):
    PENDING_EMAIL = 'pending_email', '이메일 인증 대기'
    PENDING_APPROVAL = 'pending_approval', '관리자 승인 대기'
    ACTIVE = 'active', '활성'
    SUSPENDED = 'suspended', '정지'
    DEACTIVATED = 'deactivated', '비활성'


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField('이메일', unique=True)
    first_name = models.CharField('이름', max_length=30, blank=True)
    last_name = models.CharField('성', max_length=30, blank=True)
    
    # 계정 상태 관리
    status = models.CharField(
        '계정 상태',
        max_length=20,
        choices=UserStatus.choices,
        default=UserStatus.PENDING_EMAIL
    )
    
    # 기본 Django 필드
    is_staff = models.BooleanField('스태프 여부', default=False)
    is_active = models.BooleanField('활성 여부', default=True)
    
    # 추가 인증 필드
    email_verified = models.BooleanField('이메일 인증 여부', default=False)
    email_verification_token = models.CharField(
        '이메일 인증 토큰', 
        max_length=64, 
        blank=True
    )
    email_verification_sent_at = models.DateTimeField(
        '이메일 인증 발송 시간', 
        null=True, 
        blank=True
    )
    
    # 관리자 승인 관련
    is_approved = models.BooleanField('관리자 승인 여부', default=False)
    approved_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_users',
        verbose_name='승인자'
    )
    approved_at = models.DateTimeField('승인 시간', null=True, blank=True)
    
    # 정지 관련
    suspended_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suspended_users',
        verbose_name='정지 처리자'
    )
    suspended_at = models.DateTimeField('정지 시간', null=True, blank=True)
    suspension_reason = models.TextField('정지 사유', blank=True)
    
    # 날짜 필드
    date_joined = models.DateTimeField('가입일', default=timezone.now)
    last_login_ip = models.GenericIPAddressField('마지막 로그인 IP', null=True, blank=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = '사용자'
        verbose_name_plural = '사용자들'
        db_table = 'auth_user'
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """전체 이름 반환"""
        return f'{self.last_name} {self.first_name}'.strip()
    
    def get_short_name(self):
        """짧은 이름 반환"""
        return self.first_name or self.email.split('@')[0]
    
    def email_user(self, subject, message, from_email=None, **kwargs):
        """이메일 발송"""
        send_mail(subject, message, from_email, [self.email], **kwargs)
    
    def can_login(self):
        """로그인 가능 여부 확인"""
        return (
            self.is_active and 
            self.email_verified and 
            self.is_approved and 
            self.status == UserStatus.ACTIVE
        )
    
    def generate_email_verification_token(self):
        """이메일 인증 토큰 생성"""
        self.email_verification_token = get_random_string(64)
        self.email_verification_sent_at = timezone.now()
        self.save(update_fields=['email_verification_token', 'email_verification_sent_at'])
        return self.email_verification_token
    
    def verify_email(self):
        """이메일 인증 처리"""
        self.email_verified = True
        self.email_verification_token = ''
        
        # 이메일 인증 후 관리자 승인 대기 상태로 변경
        if self.status == UserStatus.PENDING_EMAIL:
            self.status = UserStatus.PENDING_APPROVAL
        
        self.save(update_fields=['email_verified', 'email_verification_token', 'status'])
    
    def approve_user(self, approved_by_user):
        """관리자 승인 처리"""
        if not self.email_verified:
            raise ValueError('이메일 인증이 필요합니다.')
        
        self.is_approved = True
        self.approved_by = approved_by_user
        self.approved_at = timezone.now()
        self.status = UserStatus.ACTIVE
        self.save(update_fields=[
            'is_approved', 'approved_by', 'approved_at', 'status'
        ])
    
    def suspend_user(self, suspended_by_user, reason=''):
        """사용자 정지"""
        self.status = UserStatus.SUSPENDED
        self.suspended_by = suspended_by_user
        self.suspended_at = timezone.now()
        self.suspension_reason = reason
        self.save(update_fields=[
            'status', 'suspended_by', 'suspended_at', 'suspension_reason'
        ])
    
    def reactivate_user(self):
        """사용자 재활성화 (이메일 인증 상태에 따른 차별적 처리)"""
        if self.status == UserStatus.SUSPENDED:
            if self.email_verified:
                # 이메일 인증이 완료된 사용자는 관리자 승인 대기 상태로
                self.status = UserStatus.PENDING_APPROVAL
                self.is_approved = False
                self.approved_by = None
                self.approved_at = None
            else:
                # 이메일 인증이 안된 사용자는 이메일 인증 대기 상태로
                self.status = UserStatus.PENDING_EMAIL
                self.is_approved = False
                self.approved_by = None
                self.approved_at = None
                # 새로운 이메일 인증 토큰 생성
                self.generate_email_verification_token()
            
            # 정지 관련 정보 초기화
            self.suspended_by = None
            self.suspended_at = None
            self.suspension_reason = ''
            
            self.save(update_fields=[
                'status', 'suspended_by', 'suspended_at', 'suspension_reason',
                'is_approved', 'approved_by', 'approved_at'
            ])
```

## 🚀 Django Ninja API 구현

### 1. 패키지 설치 및 설정

먼저 필요한 패키지들을 설치합니다:

```bash
pip install django-ninja
pip install pydantic[email]
```

### 2. Pydantic 스키마 정의

```python
# accounts/schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from .models import UserStatus


class UserRegistrationSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., max_length=30)
    last_name: str = Field(..., max_length=30)


class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str


class EmailVerificationSchema(BaseModel):
    token: str


class UserApprovalSchema(BaseModel):
    user_id: int
    approval_note: Optional[str] = None


class UserSuspensionSchema(BaseModel):
    user_id: int
    reason: str = Field(..., min_length=1, max_length=500)


class UserReactivationSchema(BaseModel):
    user_id: int


class UserResponseSchema(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    status: str
    email_verified: bool
    is_approved: bool
    date_joined: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserListResponseSchema(BaseModel):
    users: list[UserResponseSchema]
    total: int
    page: int
    per_page: int


class UserStatusResponseSchema(BaseModel):
    total_users: int
    recent_registrations: int
    pending_email: int
    pending_approval: int
    active: int
    suspended: int
    deactivated: int


class MessageResponseSchema(BaseModel):
    message: str
    success: bool


class ErrorResponseSchema(BaseModel):
    error: str
    detail: Optional[str] = None


class TokenResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponseSchema
```

### 3. 인증 헬퍼 함수

```python
# accounts/auth.py
from django.contrib.auth import authenticate
from django.contrib.auth.models import AnonymousUser
from ninja.security import HttpBearer
from ninja import NinjaAPI
from django.contrib.sessions.models import Session
from django.utils import timezone
from .models import CustomUser


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            # 간단한 세션 기반 인증 (실제로는 JWT 등을 사용 권장)
            session = Session.objects.get(session_key=token)
            if session.expire_date < timezone.now():
                return None
            
            user_id = session.get_decoded().get('_auth_user_id')
            if user_id:
                user = CustomUser.objects.get(id=user_id)
                if user.can_login():
                    return user
        except (Session.DoesNotExist, CustomUser.DoesNotExist):
            pass
        return None


class AdminRequired(AuthBearer):
    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if user and user.is_staff:
            return user
        return None


# 인증 인스턴스
auth = AuthBearer()
admin_auth = AdminRequired()


def get_current_user(request):
    """현재 로그인한 사용자 반환"""
    if hasattr(request, 'auth') and request.auth:
        return request.auth
    return AnonymousUser()
```

## 📱 사용자 관련 API 엔드포인트

### 1. 사용자 인증 API

```python
# accounts/api.py
from ninja import NinjaAPI, Query
from ninja.pagination import paginate, PageNumberPagination
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q, Count
from typing import List

from .models import CustomUser, UserStatus
from .schemas import *
from .auth import auth, admin_auth, get_current_user

api = NinjaAPI(title="User Management API", version="1.0.0")


@api.post("/auth/register", response={201: MessageResponseSchema, 400: ErrorResponseSchema})
def register_user(request, data: UserRegistrationSchema):
    """사용자 회원가입"""
    try:
        # 이메일 중복 확인
        if CustomUser.objects.filter(email=data.email).exists():
            return 400, {"error": "이미 존재하는 이메일입니다."}
        
        # 사용자 생성
        user = CustomUser.objects.create_user(
            email=data.email,
            password=data.password,
            first_name=data.first_name,
            last_name=data.last_name
        )
        
        # 이메일 인증 토큰 생성 및 발송
        token = user.generate_email_verification_token()
        send_verification_email(user, token, request)
        
        return 201, {
            "message": "회원가입이 완료되었습니다. 이메일을 확인하여 인증을 완료해주세요.",
            "success": True
        }
        
    except Exception as e:
        return 400, {"error": "회원가입 처리 중 오류가 발생했습니다.", "detail": str(e)}


@api.post("/auth/login", response={200: TokenResponseSchema, 401: ErrorResponseSchema})
def login_user(request, data: UserLoginSchema):
    """사용자 로그인"""
    user = authenticate(request, username=data.email, password=data.password)
    
    if user is None:
        return 401, {"error": "이메일 또는 비밀번호가 잘못되었습니다."}
    
    # 사용자 상태별 처리
    if user.status == UserStatus.PENDING_EMAIL:
        return 401, {"error": "이메일 인증이 필요합니다. 이메일을 확인해주세요."}
    
    elif user.status == UserStatus.PENDING_APPROVAL:
        return 401, {"error": "관리자 승인을 기다리고 있습니다. 잠시만 기다려주세요."}
    
    elif user.status == UserStatus.SUSPENDED:
        return 401, {"error": f"계정이 정지되었습니다. 정지 사유: {user.suspension_reason}"}
    
    elif user.status == UserStatus.DEACTIVATED:
        return 401, {"error": "비활성화된 계정입니다. 고객센터에 문의해주세요."}
    
    elif user.status == UserStatus.ACTIVE:
        # 정상 로그인
        login(request, user)
        
        # 로그인 IP 저장
        save_login_ip(request, user)
        
        return 200, {
            "access_token": request.session.session_key,
            "token_type": "bearer",
            "user": UserResponseSchema.from_orm(user)
        }
    
    return 401, {"error": "로그인할 수 없는 계정 상태입니다."}


@api.post("/auth/logout", auth=auth, response={200: MessageResponseSchema})
def logout_user(request):
    """사용자 로그아웃"""
    logout(request)
    return {"message": "로그아웃되었습니다.", "success": True}


@api.get("/auth/me", auth=auth, response=UserResponseSchema)
def get_current_user_info(request):
    """현재 로그인한 사용자 정보"""
    return UserResponseSchema.from_orm(request.auth)


def send_verification_email(user, token, request):
    """이메일 인증 메일 발송"""
    verification_url = request.build_absolute_uri(
        f"/api/auth/verify-email?token={token}"
    )
    
    subject = '[사이트명] 이메일 인증을 완료해주세요'
    message = f"""
    안녕하세요 {user.get_short_name()}님!
    
    회원가입을 완료하려면 아래 링크를 클릭하여 이메일 인증을 완료해주세요.
    
    {verification_url}
    
    이 링크는 24시간 후 만료됩니다.
    
    감사합니다.
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def save_login_ip(request, user):
    """로그인 IP 저장"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    user.last_login_ip = ip
    user.save(update_fields=['last_login_ip'])
```

### 2. 이메일 인증 API

```python
@api.get("/auth/verify-email", response={200: MessageResponseSchema, 400: ErrorResponseSchema})
def verify_email(request, token: str = Query(...)):
    """이메일 인증 처리"""
    try:
        user = CustomUser.objects.get(
            email_verification_token=token,
            email_verified=False
        )
        
        # 토큰 만료 확인 (24시간)
        if user.email_verification_sent_at:
            expiry_time = user.email_verification_sent_at + timezone.timedelta(hours=24)
            if timezone.now() > expiry_time:
                return 400, {"error": "인증 링크가 만료되었습니다."}
        
        # 이메일 인증 처리
        user.verify_email()
        
        return 200, {
            "message": "이메일 인증이 완료되었습니다. 관리자 승인을 기다려주세요.",
            "success": True
        }
        
    except CustomUser.DoesNotExist:
        return 400, {"error": "유효하지 않은 인증 토큰입니다."}


@api.post("/auth/resend-verification", response={200: MessageResponseSchema, 400: ErrorResponseSchema})
def resend_verification_email(request, email: EmailStr):
    """이메일 인증 재발송"""
    try:
        user = CustomUser.objects.get(
            email=email,
            email_verified=False,
            status=UserStatus.PENDING_EMAIL
        )
        
        # 인증 메일 재발송
        token = user.generate_email_verification_token()
        send_verification_email(user, token, request)
        
        return 200, {
            "message": "인증 이메일이 재발송되었습니다.",
            "success": True
        }
        
    except CustomUser.DoesNotExist:
        return 400, {"error": "해당 이메일로 가입된 계정을 찾을 수 없습니다."}
```

## 👨‍💼 관리자 API 엔드포인트

### 1. 사용자 목록 및 통계 API

```python
@api.get("/admin/users", auth=admin_auth, response=UserListResponseSchema)
@paginate(PageNumberPagination, page_size=20)
def get_users_list(
    request,
    status: Optional[str] = Query(None),
    email_verified: Optional[bool] = Query(None),
    is_approved: Optional[bool] = Query(None),
    search: Optional[str] = Query(None)
):
    """사용자 목록 조회 (관리자용)"""
    queryset = CustomUser.objects.all().select_related('approved_by', 'suspended_by')
    
    # 필터링
    if status:
        queryset = queryset.filter(status=status)
    if email_verified is not None:
        queryset = queryset.filter(email_verified=email_verified)
    if is_approved is not None:
        queryset = queryset.filter(is_approved=is_approved)
    if search:
        queryset = queryset.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    queryset = queryset.order_by('-date_joined')
    return queryset


@api.get("/admin/users/statistics", auth=admin_auth, response=UserStatusResponseSchema)
def get_user_statistics(request):
    """사용자 통계 조회"""
    total_users = CustomUser.objects.count()
    
    status_counts = CustomUser.objects.aggregate(
        pending_email=Count('id', filter=Q(status=UserStatus.PENDING_EMAIL)),
        pending_approval=Count('id', filter=Q(status=UserStatus.PENDING_APPROVAL)),
        active=Count('id', filter=Q(status=UserStatus.ACTIVE)),
        suspended=Count('id', filter=Q(status=UserStatus.SUSPENDED)),
        deactivated=Count('id', filter=Q(status=UserStatus.DEACTIVATED)),
    )
    
    # 최근 가입자 (7일)
    week_ago = timezone.now() - timezone.timedelta(days=7)
    recent_registrations = CustomUser.objects.filter(
        date_joined__gte=week_ago
    ).count()
    
    return {
        'total_users': total_users,
        'recent_registrations': recent_registrations,
        **status_counts
    }


@api.get("/admin/users/pending-approval", auth=admin_auth, response=List[UserResponseSchema])
def get_pending_approval_users(request):
    """승인 대기 사용자 목록"""
    users = CustomUser.objects.filter(
        status=UserStatus.PENDING_APPROVAL,
        email_verified=True
    ).order_by('date_joined')
    
    return [UserResponseSchema.from_orm(user) for user in users]
```

### 2. 사용자 승인 API

```python
@api.post("/admin/users/approve", auth=admin_auth, response={200: MessageResponseSchema, 400: ErrorResponseSchema})
def approve_user(request, data: UserApprovalSchema):
    """사용자 승인"""
    try:
        user = get_object_or_404(CustomUser, id=data.user_id)
        
        if user.status != UserStatus.PENDING_APPROVAL:
            return 400, {"error": "승인 대기 상태가 아닙니다."}
        
        if not user.email_verified:
            return 400, {"error": "이메일 인증이 완료되지 않았습니다."}
        
        # 사용자 승인
        user.approve_user(request.auth)
        
        # 승인 알림 이메일 발송
        send_approval_email(user, request)
        
        return 200, {
            "message": f"{user.email} 사용자가 승인되었습니다.",
            "success": True
        }
        
    except Exception as e:
        return 400, {"error": "승인 처리 중 오류가 발생했습니다.", "detail": str(e)}


@api.post("/admin/users/approve-bulk", auth=admin_auth, response={200: MessageResponseSchema})
def approve_users_bulk(request, user_ids: List[int]):
    """사용자 일괄 승인"""
    count = 0
    
    for user_id in user_ids:
        try:
            user = CustomUser.objects.get(
                id=user_id,
                status=UserStatus.PENDING_APPROVAL,
                email_verified=True
            )
            user.approve_user(request.auth)
            send_approval_email(user, request)
            count += 1
        except CustomUser.DoesNotExist:
            continue
    
    return {
        "message": f"{count}명의 사용자가 승인되었습니다.",
        "success": True
    }


def send_approval_email(user, request):
    """승인 알림 이메일 발송"""
    subject = '[사이트명] 계정이 승인되었습니다'
    message = f"""
    안녕하세요 {user.get_short_name()}님!
    
    귀하의 계정이 관리자에 의해 승인되었습니다.
    이제 모든 서비스를 이용하실 수 있습니다.
    
    로그인: {request.build_absolute_uri('/api/auth/login')}
    
    감사합니다.
    """
    
    user.email_user(subject, message)
```

### 3. 사용자 정지 API

```python
@api.post("/admin/users/suspend", auth=admin_auth, response={200: MessageResponseSchema, 400: ErrorResponseSchema})
def suspend_user(request, data: UserSuspensionSchema):
    """사용자 정지"""
    try:
        user = get_object_or_404(CustomUser, id=data.user_id)
        
        if user.status != UserStatus.ACTIVE:
            return 400, {"error": "활성 상태가 아닙니다."}
        
        if user.is_superuser:
            return 400, {"error": "슈퍼유저는 정지할 수 없습니다."}
        
        # 사용자 정지
        user.suspend_user(request.auth, data.reason)
        
        # 정지 알림 이메일 발송
        send_suspension_email(user, data.reason)
        
        return 200, {
            "message": f"{user.email} 사용자가 정지되었습니다.",
            "success": True
        }
        
    except Exception as e:
        return 400, {"error": "정지 처리 중 오류가 발생했습니다.", "detail": str(e)}


@api.post("/admin/users/suspend-bulk", auth=admin_auth, response={200: MessageResponseSchema})
def suspend_users_bulk(request, user_ids: List[int], reason: str):
    """사용자 일괄 정지"""
    count = 0
    
    for user_id in user_ids:
        try:
            user = CustomUser.objects.get(
                id=user_id,
                status=UserStatus.ACTIVE,
                is_superuser=False
            )
            user.suspend_user(request.auth, reason)
            send_suspension_email(user, reason)
            count += 1
        except CustomUser.DoesNotExist:
            continue
    
    return {
        "message": f"{count}명의 사용자가 정지되었습니다.",
        "success": True
    }


def send_suspension_email(user, reason):
    """정지 알림 이메일 발송"""
    subject = '[사이트명] 계정이 정지되었습니다'
    message = f"""
    안녕하세요 {user.get_short_name()}님!
    
    귀하의 계정이 다음 사유로 정지되었습니다:
    
    정지 사유: {reason}
    정지 시간: {user.suspended_at}
    
    문의사항이 있으시면 고객센터로 연락해주세요.
    
    감사합니다.
    """
    
    user.email_user(subject, message)
```

### 4. 사용자 재활성화 API (이메일 인증 상태별 처리)

```python
@api.post("/admin/users/reactivate", auth=admin_auth, response={200: MessageResponseSchema, 400: ErrorResponseSchema})
def reactivate_user(request, data: UserReactivationSchema):
    """사용자 재활성화 (이메일 인증 상태에 따른 차별적 처리)"""
    try:
        user = get_object_or_404(CustomUser, id=data.user_id)
        
        if user.status != UserStatus.SUSPENDED:
            return 400, {"error": "정지 상태가 아닙니다."}
        
        # 이메일 인증 상태에 따른 차별적 처리
        old_email_verified = user.email_verified
        user.reactivate_user()
        
        if old_email_verified:
            # 이메일 인증이 완료된 사용자 -> 관리자 승인 대기 상태
            message_text = f"{user.email} 사용자가 재활성화되었습니다. (관리자 승인 대기 상태)"
            send_reactivation_approval_needed_email(user, request)
        else:
            # 이메일 인증이 안된 사용자 -> 이메일 인증 대기 상태
            message_text = f"{user.email} 사용자가 재활성화되었습니다. (이메일 인증 필요)"
            # 새로운 인증 토큰으로 이메일 발송
            send_verification_email(user, user.email_verification_token, request)
        
        return 200, {
            "message": message_text,
            "success": True
        }
        
    except Exception as e:
        return 400, {"error": "재활성화 처리 중 오류가 발생했습니다.", "detail": str(e)}


@api.get("/admin/users/{user_id}/reactivation-info", auth=admin_auth)
def get_reactivation_info(request, user_id: int):
    """재활성화 시 처리 방식 미리보기"""
    try:
        user = get_object_or_404(CustomUser, id=user_id)
        
        if user.status != UserStatus.SUSPENDED:
            return {"error": "정지 상태가 아닙니다."}
        
        if user.email_verified:
            next_status = "관리자 승인 대기"
            description = "이메일 인증이 완료된 사용자이므로 관리자 승인 대기 상태로 변경됩니다."
        else:
            next_status = "이메일 인증 대기"
            description = "이메일 인증이 완료되지 않은 사용자이므로 이메일 인증 대기 상태로 변경되고 새로운 인증 이메일이 발송됩니다."
        
        return {
            "user_email": user.email,
            "current_status": user.get_status_display(),
            "email_verified": user.email_verified,
            "next_status": next_status,
            "description": description
        }
        
    except Exception as e:
        return {"error": str(e)}


def send_reactivation_approval_needed_email(user, request):
    """재활성화 후 승인 필요 알림 이메일"""
    subject = '[사이트명] 계정이 재활성화되었습니다 (승인 대기)'
    message = f"""
    안녕하세요 {user.get_short_name()}님!
    
    귀하의 계정이 재활성화되었습니다.
    현재 관리자 승인을 기다리고 있는 상태입니다.
    
    승인이 완료되면 다시 모든 서비스를 이용하실 수 있습니다.
    
    감사합니다.
    """
    
    user.email_user(subject, message)
```

## 🔧 URL 및 설정

### URL 구성

```python
# urls.py (프로젝트 메인)
from django.contrib import admin
from django.urls import path
from accounts.api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
```

### settings.py 설정

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ninja',  # Django Ninja 추가
    'accounts',
]

AUTH_USER_MODEL = 'accounts.CustomUser'

# 이메일 설정
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'your-email@gmail.com'

# 인증 백엔드
AUTHENTICATION_BACKENDS = [
    'accounts.backends.CustomAuthenticationBackend',
]

# 세션 설정
SESSION_COOKIE_AGE = 86400 * 7  # 7일
SESSION_SAVE_EVERY_REQUEST = True
```

## � API 문서 및 테스트

### Swagger UI 접근

Django Ninja는 자동으로 API 문서를 생성합니다:

```
http://localhost:8000/api/docs
```

### API 엔드포인트 요약

| 엔드포인트 | 메소드 | 설명 | 인증 필요 |
|-----------|--------|------|----------|
| `/api/auth/register` | POST | 회원가입 | ❌ |
| `/api/auth/login` | POST | 로그인 | ❌ |
| `/api/auth/logout` | POST | 로그아웃 | ✅ |
| `/api/auth/me` | GET | 현재 사용자 정보 | ✅ |
| `/api/auth/verify-email` | GET | 이메일 인증 | ❌ |
| `/api/auth/resend-verification` | POST | 인증 이메일 재발송 | ❌ |
| `/api/admin/users` | GET | 사용자 목록 | 🔒 관리자 |
| `/api/admin/users/statistics` | GET | 사용자 통계 | 🔒 관리자 |
| `/api/admin/users/pending-approval` | GET | 승인 대기 목록 | 🔒 관리자 |
| `/api/admin/users/approve` | POST | 사용자 승인 | 🔒 관리자 |
| `/api/admin/users/approve-bulk` | POST | 일괄 승인 | 🔒 관리자 |
| `/api/admin/users/suspend` | POST | 사용자 정지 | 🔒 관리자 |
| `/api/admin/users/suspend-bulk` | POST | 일괄 정지 | 🔒 관리자 |
| `/api/admin/users/reactivate` | POST | 사용자 재활성화 | 🔒 관리자 |
| `/api/admin/users/{id}/reactivation-info` | GET | 재활성화 정보 | 🔒 관리자 |

### 프론트엔드 연동 예시

```javascript
// JavaScript 클라이언트 예시
class UserAPI {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
        this.token = localStorage.getItem('access_token');
    }

    async register(userData) {
        const response = await fetch(`${this.baseURL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(userData)
        });
        return response.json();
    }

    async login(email, password) {
        const response = await fetch(`${this.baseURL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password })
        });
        
        if (response.ok) {
            const data = await response.json();
            this.token = data.access_token;
            localStorage.setItem('access_token', this.token);
            return data;
        }
        throw new Error('Login failed');
    }

    async getCurrentUser() {
        const response = await fetch(`${this.baseURL}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${this.token}`,
            }
        });
        return response.json();
    }

    async approveUser(userId, approvalNote = null) {
        const response = await fetch(`${this.baseURL}/admin/users/approve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`,
            },
            body: JSON.stringify({ 
                user_id: userId, 
                approval_note: approvalNote 
            })
        });
        return response.json();
    }

    async suspendUser(userId, reason) {
        const response = await fetch(`${this.baseURL}/admin/users/suspend`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`,
            },
            body: JSON.stringify({ 
                user_id: userId, 
                reason: reason 
            })
        });
        return response.json();
    }

    async reactivateUser(userId) {
        const response = await fetch(`${this.baseURL}/admin/users/reactivate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`,
            },
            body: JSON.stringify({ user_id: userId })
        });
        return response.json();
    }
}

// 사용 예시
const userAPI = new UserAPI();

// 사용자 등록
userAPI.register({
    email: 'user@example.com',
    password: 'securepassword123',
    first_name: '홍길동',
    last_name: '홍'
}).then(result => {
    console.log('Registration result:', result);
});

// 로그인
userAPI.login('user@example.com', 'securepassword123')
    .then(result => {
        console.log('Login successful:', result.user);
    })
    .catch(error => {
        console.error('Login failed:', error);
    });
```

## 🔐 커스텀 인증 백엔드 구현

### 사용자 상태 확인 백엔드

```python
# accounts/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import UserStatus

User = get_user_model()


class CustomAuthenticationBackend(ModelBackend):
    """커스텀 인증 백엔드"""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """사용자 인증"""
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        if username is None or password is None:
            return
        
        try:
            user = User.objects.get(**{User.USERNAME_FIELD: username})
        except User.DoesNotExist:
            # 타이밍 공격 방지를 위한 더미 비밀번호 검증
            User().set_password(password)
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
    
    def user_can_authenticate(self, user):
        """사용자 로그인 가능 여부 확인"""
        # 기본 is_active 확인
        if not super().user_can_authenticate(user):
            return False
        
        # 커스텀 로그인 가능 조건 확인
        return user.can_login()
    
    def get_user(self, user_id):
        """사용자 ID로 사용자 조회"""
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        
        return user if self.user_can_authenticate(user) else None
```

## 🚨 로그인 시 상태별 처리

### 커스텀 로그인 뷰

```python
# accounts/views.py (추가)
from django.contrib.auth.views import LoginView
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .models import UserStatus


class CustomLoginView(LoginView):
    """커스텀 로그인 뷰"""
    template_name = 'accounts/login.html'
    
    def form_valid(self, form):
        """폼 유효성 검사 통과 시"""
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        
        user = authenticate(
            self.request, 
            username=username, 
            password=password
        )
        
        if user is not None:
            # 사용자 상태별 처리
            if user.status == UserStatus.PENDING_EMAIL:
                messages.error(
                    self.request, 
                    '이메일 인증이 필요합니다. 이메일을 확인해주세요.'
                )
                return self.form_invalid(form)
            
            elif user.status == UserStatus.PENDING_APPROVAL:
                messages.error(
                    self.request, 
                    '관리자 승인을 기다리고 있습니다. 잠시만 기다려주세요.'
                )
                return self.form_invalid(form)
            
            elif user.status == UserStatus.SUSPENDED:
                messages.error(
                    self.request, 
                    f'계정이 정지되었습니다. 정지 사유: {user.suspension_reason}'
                )
                return self.form_invalid(form)
            
            elif user.status == UserStatus.DEACTIVATED:
                messages.error(
                    self.request, 
                    '비활성화된 계정입니다. 고객센터에 문의해주세요.'
                )
                return self.form_invalid(form)
            
            elif user.status == UserStatus.ACTIVE:
                # 정상 로그인
                login(self.request, user)
                
                # 로그인 IP 저장
                self.save_login_ip(user)
                
                messages.success(
                    self.request, 
                    f'환영합니다, {user.get_short_name()}님!'
                )
                return super().form_valid(form)
        
        return self.form_invalid(form)
    
    def save_login_ip(self, user):
        """로그인 IP 저장"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        
        user.last_login_ip = ip
        user.save(update_fields=['last_login_ip'])
```

## 📊 모니터링 및 통계

### 사용자 상태 대시보드

```python
# accounts/dashboard.py
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import CustomUser, UserStatus


class UserStatusDashboard:
    """사용자 상태 대시보드"""
    
    @staticmethod
    def get_user_statistics():
        """사용자 통계 조회"""
        total_users = CustomUser.objects.count()
        
        status_counts = CustomUser.objects.aggregate(
            pending_email=Count('id', filter=Q(status=UserStatus.PENDING_EMAIL)),
            pending_approval=Count('id', filter=Q(status=UserStatus.PENDING_APPROVAL)),
            active=Count('id', filter=Q(status=UserStatus.ACTIVE)),
            suspended=Count('id', filter=Q(status=UserStatus.SUSPENDED)),
            deactivated=Count('id', filter=Q(status=UserStatus.DEACTIVATED)),
        )
        
        # 최근 가입자 (7일)
        week_ago = timezone.now() - timedelta(days=7)
        recent_registrations = CustomUser.objects.filter(
            date_joined__gte=week_ago
        ).count()
        
        return {
            'total_users': total_users,
            'recent_registrations': recent_registrations,
            **status_counts
        }
    
    @staticmethod
    def get_pending_approvals():
        """승인 대기 사용자 목록"""
        return CustomUser.objects.filter(
            status=UserStatus.PENDING_APPROVAL,
            email_verified=True
        ).order_by('date_joined')
    
    @staticmethod
    def get_recent_suspensions(days=30):
        """최근 정지된 사용자 목록"""
        since = timezone.now() - timedelta(days=days)
        return CustomUser.objects.filter(
            status=UserStatus.SUSPENDED,
            suspended_at__gte=since
        ).select_related('suspended_by').order_by('-suspended_at')
```

## ⚡ 성능 최적화 팁

### 1. 데이터베이스 인덱스 최적화

```python
# accounts/models.py (인덱스 추가)
class CustomUser(AbstractBaseUser, PermissionsMixin):
    # ... 기존 필드들 ...
    
    class Meta:
        verbose_name = '사용자'
        verbose_name_plural = '사용자들'
        db_table = 'auth_user'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['email_verified']),
            models.Index(fields=['is_approved']),
            models.Index(fields=['status', 'email_verified', 'is_approved']),
            models.Index(fields=['date_joined']),
            models.Index(fields=['suspended_at']),
        ]
```

### 2. 쿼리 최적화

```python
# accounts/querysets.py
from django.db import models
from .models import UserStatus


class CustomUserQuerySet(models.QuerySet):
    """최적화된 쿼리셋"""
    
    def active_users(self):
        """활성 사용자 조회"""
        return self.filter(
            status=UserStatus.ACTIVE,
            is_active=True,
            email_verified=True,
            is_approved=True
        )
    
    def pending_approval(self):
        """승인 대기 사용자"""
        return self.filter(
            status=UserStatus.PENDING_APPROVAL,
            email_verified=True
        )
    
    def with_approval_info(self):
        """승인 정보 포함"""
        return self.select_related('approved_by', 'suspended_by')
    
    def recent_registrations(self, days=7):
        """최근 가입자"""
        from django.utils import timezone
        from datetime import timedelta
        
        since = timezone.now() - timedelta(days=days)
        return self.filter(date_joined__gte=since)


# managers.py에서 사용
class CustomUserManager(BaseUserManager):
    def get_queryset(self):
        return CustomUserQuerySet(self.model, using=self._db)
    
    def active_users(self):
        return self.get_queryset().active_users()
    
    def pending_approval(self):
        return self.get_queryset().pending_approval()
```

## 🧪 테스트 코드

### 단위 테스트

```python
# tests/test_user_model.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.models import CustomUser, UserStatus


class CustomUserModelTest(TestCase):
    """User 모델 테스트"""
    
    def setUp(self):
        self.admin_user = CustomUser.objects.create_superuser(
            email='admin@example.com',
            password='testpass123'
        )
    
    def test_create_user(self):
        """일반 사용자 생성 테스트"""
        user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='테스트',
            last_name='사용자'
        )
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.status, UserStatus.PENDING_EMAIL)
        self.assertFalse(user.email_verified)
        self.assertFalse(user.is_approved)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
    
    def test_email_verification(self):
        """이메일 인증 테스트"""
        user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # 토큰 생성
        token = user.generate_email_verification_token()
        self.assertTrue(token)
        self.assertTrue(user.email_verification_token)
        
        # 이메일 인증
        user.verify_email()
        self.assertTrue(user.email_verified)
        self.assertEqual(user.status, UserStatus.PENDING_APPROVAL)
        self.assertEqual(user.email_verification_token, '')
    
    def test_user_approval(self):
        """사용자 승인 테스트"""
        user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # 이메일 인증 완료
        user.verify_email()
        
        # 관리자 승인
        user.approve_user(self.admin_user)
        
        self.assertTrue(user.is_approved)
        self.assertEqual(user.approved_by, self.admin_user)
        self.assertEqual(user.status, UserStatus.ACTIVE)
        self.assertIsNotNone(user.approved_at)
    
    def test_user_suspension(self):
        """사용자 정지 테스트"""
        user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # 활성 상태로 만들기
        user.verify_email()
        user.approve_user(self.admin_user)
        
        # 정지 처리
        reason = '테스트 정지'
        user.suspend_user(self.admin_user, reason)
        
        self.assertEqual(user.status, UserStatus.SUSPENDED)
        self.assertEqual(user.suspended_by, self.admin_user)
        self.assertEqual(user.suspension_reason, reason)
        self.assertIsNotNone(user.suspended_at)
    
    def test_user_reactivation(self):
        """사용자 재활성화 테스트"""
        user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # 정지 상태로 만들기
        user.verify_email()
        user.approve_user(self.admin_user)
        user.suspend_user(self.admin_user, '테스트')
        
        # 재활성화
        user.reactivate_user()
        
        if user.email_verified:
            # 이메일 인증 완료된 사용자는 관리자 승인 대기 상태로 변경
            self.assertEqual(user.status, UserStatus.PENDING_APPROVAL)
            self.assertFalse(user.is_approved)
        else:
            # 이메일 인증 안된 사용자는 이메일 인증 대기 상태로 변경
            self.assertEqual(user.status, UserStatus.PENDING_EMAIL)
            self.assertFalse(user.is_approved)
            self.assertTrue(user.email_verification_token)  # 새 토큰 생성됨
        
        self.assertIsNone(user.suspended_by)
        self.assertIsNone(user.suspended_at)
        self.assertEqual(user.suspension_reason, '')
    
    def test_can_login(self):
        """로그인 가능 여부 테스트"""
        user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # 초기 상태: 로그인 불가
        self.assertFalse(user.can_login())
        
        # 이메일 인증 후: 여전히 로그인 불가
        user.verify_email()
        self.assertFalse(user.can_login())
        
        # 승인 후: 로그인 가능
        user.approve_user(self.admin_user)
        self.assertTrue(user.can_login())
        
        # 정지 후: 로그인 불가
        user.suspend_user(self.admin_user, '테스트')
        self.assertFalse(user.can_login())
    
    def test_user_reactivation_with_email_verified(self):
        """이메일 인증 완료된 사용자 재활성화 테스트"""
        user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # 활성 상태로 만들고 정지
        user.verify_email()
        user.approve_user(self.admin_user)
        user.suspend_user(self.admin_user, '테스트')
        
        # 재활성화 (이메일 인증 완료된 상태)
        user.reactivate_user()
        
        self.assertEqual(user.status, UserStatus.PENDING_APPROVAL)
        self.assertFalse(user.is_approved)
        self.assertTrue(user.email_verified)  # 이메일 인증은 유지
    
    def test_user_reactivation_without_email_verified(self):
        """이메일 인증 안된 사용자 재활성화 테스트"""
        user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # 이메일 인증 없이 강제로 활성화 후 정지
        user.status = UserStatus.ACTIVE
        user.is_approved = True
        user.save()
        user.suspend_user(self.admin_user, '테스트')
        
        # 재활성화 (이메일 인증 안된 상태)
        user.reactivate_user()
        
        self.assertEqual(user.status, UserStatus.PENDING_EMAIL)
        self.assertFalse(user.is_approved)
        self.assertFalse(user.email_verified)
        self.assertTrue(user.email_verification_token)  # 새 토큰 생성됨
```

### API 테스트

```python
# tests/test_api.py
from django.test import TestCase
from django.test.client import Client
from django.urls import reverse
import json
from accounts.models import CustomUser, UserStatus


class UserAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = CustomUser.objects.create_superuser(
            email='admin@example.com',
            password='testpass123'
        )
    
    def test_user_registration_api(self):
        """사용자 등록 API 테스트"""
        data = {
            "email": "test@example.com",
            "password": "testpass123",
            "first_name": "테스트",
            "last_name": "사용자"
        }
        
        response = self.client.post(
            '/api/auth/register',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        self.assertTrue(CustomUser.objects.filter(email="test@example.com").exists())
    
    def test_user_login_api(self):
        """사용자 로그인 API 테스트"""
        # 활성 사용자 생성
        user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        user.verify_email()
        user.approve_user(self.admin_user)
        
        data = {
            "email": "test@example.com",
            "password": "testpass123"
        }
        
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn('access_token', response_data)
        self.assertIn('user', response_data)
    
    def test_user_approval_api(self):
        """사용자 승인 API 테스트"""
        # 승인 대기 사용자 생성
        user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        user.verify_email()
        
        # 관리자 로그인
        self.client.login(email='admin@example.com', password='testpass123')
        
        data = {
            "user_id": user.id,
            "approval_note": "승인 완료"
        }
        
        response = self.client.post(
            '/api/admin/users/approve',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.status, UserStatus.ACTIVE)
        self.assertTrue(user.is_approved)
    
    def test_user_suspension_api(self):
        """사용자 정지 API 테스트"""
        # 활성 사용자 생성
        user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        user.verify_email()
        user.approve_user(self.admin_user)
        
        # 관리자 로그인
        self.client.login(email='admin@example.com', password='testpass123')
        
        data = {
            "user_id": user.id,
            "reason": "테스트 정지"
        }
        
        response = self.client.post(
            '/api/admin/users/suspend',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.status, UserStatus.SUSPENDED)
        self.assertEqual(user.suspension_reason, "테스트 정지")
    
    def test_user_reactivation_api(self):
        """사용자 재활성화 API 테스트"""
        # 정지된 사용자 생성
        user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        user.verify_email()
        user.approve_user(self.admin_user)
        user.suspend_user(self.admin_user, '테스트')
        
        # 관리자 로그인
        self.client.login(email='admin@example.com', password='testpass123')
        
        data = {"user_id": user.id}
        
        response = self.client.post(
            '/api/admin/users/reactivate',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        # 이메일 인증된 사용자는 승인 대기 상태로
        self.assertEqual(user.status, UserStatus.PENDING_APPROVAL)
        self.assertFalse(user.is_approved)
```

## 🔧 설정 및 배포

### requirements.txt

```txt
Django==4.2.7
django-ninja==1.0.1
pydantic[email]==2.5.0
```

### 마이그레이션 및 초기 설정

```bash
# 패키지 설치
pip install -r requirements.txt

# 마이그레이션 생성 및 적용
python manage.py makemigrations accounts
python manage.py migrate

# 슈퍼유저 생성
python manage.py createsuperuser

# 개발 서버 실행
python manage.py runserver
```

### 프로덕션 환경 설정

```python
# settings/production.py
import os
from .base import *

DEBUG = False
ALLOWED_HOSTS = ['your-domain.com']

# 보안 설정
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# 데이터베이스 (PostgreSQL 권장)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}

# Redis 캐시 (선택사항)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# 이메일 설정
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL')

# 로깅
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/user_management.log',
        },
    },
    'loggers': {
        'accounts': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 📋 마이그레이션 및 초기 데이터

### 마이그레이션 생성 및 적용

```bash
# 마이그레이션 생성
python manage.py makemigrations accounts

# 마이그레이션 적용
python manage.py migrate

# 슈퍼유저 생성
python manage.py createsuperuser
```

### 초기 데이터 fixture

```python
# accounts/fixtures/initial_data.json
[
    {
        "model": "accounts.customuser",
        "pk": 1,
        "fields": {
            "email": "admin@example.com",
            "first_name": "관리자",
            "last_name": "시스템",
            "is_staff": true,
            "is_superuser": true,
            "is_active": true,
            "status": "active",
            "email_verified": true,
            "is_approved": true,
            "date_joined": "2025-08-01T00:00:00Z"
        }
    }
]
```

## 🚀 결론

이 글에서 구현한 Django Ninja 기반 고급 User 모델 API는 다음과 같은 특징을 가집니다:

### ✅ 주요 기능
- **완전한 REST API**: Django Ninja 기반의 현대적인 API
- **이메일 인증 시스템**: 토큰 기반 이메일 인증
- **관리자 승인 워크플로우**: 체계적인 사용자 승인 프로세스
- **지능적 재활성화**: 이메일 인증 상태에 따른 차별적 처리
- **상태 기반 로그인 제어**: 5단계 사용자 상태 관리
- **자동 API 문서**: Swagger UI 지원

### 🎯 핵심 개선사항

1. **재활성화 로직 개선**:
   - 이메일 인증 완료 사용자 → 관리자 승인 대기 상태
   - 이메일 미인증 사용자 → 이메일 인증 대기 상태 + 새 토큰 발급

2. **API 우선 설계**:
   - RESTful API 엔드포인트
   - Pydantic 스키마 기반 데이터 검증
   - 자동 API 문서 생성

3. **확장 가능한 인증**:
   - 토큰 기반 인증 (세션/JWT 선택 가능)
   - 역할별 권한 관리
   - 관리자 전용 엔드포인트

### 🔧 실무 적용 포인트

1. **프론트엔드 친화적**: React, Vue.js 등과 쉬운 연동
2. **모바일 앱 지원**: REST API로 모바일 앱 개발 가능
3. **마이크로서비스 아키텍처**: 독립적인 사용자 관리 서비스
4. **테스트 용이성**: API 테스트 자동화 가능
5. **문서화 자동화**: Swagger UI로 개발자 경험 향상

이 구현을 통해 현대적인 웹/모바일 애플리케이션에 적합한 사용자 관리 시스템을 구축할 수 있으며, 특히 정지된 사용자의 재활성화 시 이메일 인증 상태를 고려한 차별적 처리로 보안성과 사용자 경험을 모두 향상시킬 수 있습니다.

**다음 글에서는 JWT 인증과 Redis를 활용한 고급 세션 관리 기법에 대해 다뤄보겠습니다!**
