---
layout: post
title: "Django Ninja 세련된 코딩 가이드: 클린하고 유지보수 가능한 API 설계"
date: 2025-10-05 10:00:00 +0900
categories: [Django, Python, Clean Code, Architecture]
tags: [Django, Python, Django-Ninja, Clean-Code, Architecture, API-Design, Best-Practices, SOLID]
author: "updaun"
image: "/assets/img/posts/2025-10-05-django-ninja-clean-code-guide.webp"
---

Django Ninja를 사용하면서 단순히 동작하는 코드가 아닌, 아름답고 유지보수 가능한 코드를 작성하는 것은 장기적으로 프로젝트의 성공을 좌우합니다. 이 글에서는 Django Ninja의 특성을 활용하여 세련되고 클린한 API를 설계하는 방법을 상세히 알아보겠습니다.

## 🎯 클린 코드의 핵심 원칙

### 1. 단일 책임 원칙 (Single Responsibility Principle)

**❌ 나쁜 예시**
```python
# api.py - 모든 로직이 뒤섞인 형태
from ninja import Router
from django.contrib.auth.models import User
from django.core.mail import send_mail
import logging

router = Router()

@router.post("/users", response={201: dict, 400: dict})
def create_user(request, data: dict):
    # 검증, 비즈니스 로직, 외부 서비스 호출이 모두 섞여있음
    if not data.get('email'):
        return 400, {"error": "Email is required"}
    
    if User.objects.filter(email=data['email']).exists():
        return 400, {"error": "Email already exists"}
    
    user = User.objects.create_user(
        username=data['username'],
        email=data['email'],
        password=data['password']
    )
    
    # 이메일 발송
    send_mail(
        'Welcome!',
        f'Hello {user.username}',
        'from@example.com',
        [user.email],
    )
    
    logging.info(f"User created: {user.username}")
    
    return 201, {"id": user.id, "message": "User created successfully"}
```

**✅ 좋은 예시**
```python
# schemas.py - 데이터 검증 책임
from ninja import Schema
from pydantic import validator, EmailStr
from typing import Optional

class CreateUserSchema(Schema):
    username: str
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class UserResponseSchema(Schema):
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    date_joined: datetime

# services.py - 비즈니스 로직 책임
from django.contrib.auth.models import User
from django.db import transaction
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class UserService:
    """사용자 관련 비즈니스 로직"""
    
    @staticmethod
    def create_user(user_data: CreateUserSchema) -> User:
        """새 사용자 생성"""
        with transaction.atomic():
            user = User.objects.create_user(
                username=user_data.username,
                email=user_data.email,
                password=user_data.password,
                first_name=user_data.first_name or '',
                last_name=user_data.last_name or '',
            )
            
            logger.info(f"User created successfully: {user.username}")
            return user
    
    @staticmethod
    def check_email_availability(email: str) -> bool:
        """이메일 중복 확인"""
        return not User.objects.filter(email=email).exists()
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """ID로 사용자 조회"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

# notifications.py - 알림 서비스 책임
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """알림 관련 서비스"""
    
    @staticmethod
    def send_welcome_email(user: User) -> bool:
        """환영 이메일 발송"""
        try:
            send_mail(
                subject='Welcome to Our Platform!',
                message=f'Hello {user.get_full_name() or user.username}, welcome to our platform!',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info(f"Welcome email sent to {user.email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.email}: {e}")
            return False

# api.py - API 컨트롤러 책임만
from ninja import Router
from ninja.errors import HttpError
from .schemas import CreateUserSchema, UserResponseSchema
from .services import UserService
from .notifications import NotificationService

router = Router(tags=["Users"])

@router.post("/users", response={201: UserResponseSchema, 400: dict})
def create_user(request, data: CreateUserSchema):
    """새 사용자 생성"""
    # 이메일 중복 확인
    if not UserService.check_email_availability(data.email):
        raise HttpError(400, "Email already exists")
    
    # 사용자 생성
    user = UserService.create_user(data)
    
    # 환영 이메일 발송 (비동기로 처리하는 것이 더 좋음)
    NotificationService.send_welcome_email(user)
    
    return 201, user
```

### 2. 의존성 역전 원칙 (Dependency Inversion Principle)

**✅ 인터페이스 기반 설계**
```python
# interfaces.py - 추상화 정의
from abc import ABC, abstractmethod
from typing import List, Optional
from django.contrib.auth.models import User

class EmailServiceInterface(ABC):
    """이메일 서비스 인터페이스"""
    
    @abstractmethod
    def send_email(self, to: str, subject: str, message: str) -> bool:
        pass

class UserRepositoryInterface(ABC):
    """사용자 저장소 인터페이스"""
    
    @abstractmethod
    def create_user(self, user_data: dict) -> User:
        pass
    
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        pass
    
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        pass

# implementations.py - 구현체
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

class DjangoEmailService(EmailServiceInterface):
    """Django 이메일 서비스 구현"""
    
    def send_email(self, to: str, subject: str, message: str) -> bool:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to],
                fail_silently=False,
            )
            return True
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False

class DjangoUserRepository(UserRepositoryInterface):
    """Django ORM 사용자 저장소 구현"""
    
    def create_user(self, user_data: dict) -> User:
        return User.objects.create_user(**user_data)
    
    def get_by_email(self, email: str) -> Optional[User]:
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            return None
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

# services.py - 의존성 주입 활용
class UserService:
    def __init__(
        self, 
        user_repo: UserRepositoryInterface,
        email_service: EmailServiceInterface
    ):
        self.user_repo = user_repo
        self.email_service = email_service
    
    def create_user_with_welcome(self, user_data: CreateUserSchema) -> User:
        """사용자 생성 및 환영 이메일 발송"""
        # 이메일 중복 확인
        if self.user_repo.get_by_email(user_data.email):
            raise ValueError("Email already exists")
        
        # 사용자 생성
        user = self.user_repo.create_user(user_data.dict())
        
        # 환영 이메일 발송
        self.email_service.send_email(
            to=user.email,
            subject="Welcome!",
            message=f"Hello {user.username}, welcome to our platform!"
        )
        
        return user

# dependency_injection.py - 의존성 컨테이너
from functools import lru_cache

@lru_cache()
def get_email_service() -> EmailServiceInterface:
    return DjangoEmailService()

@lru_cache()
def get_user_repository() -> UserRepositoryInterface:
    return DjangoUserRepository()

@lru_cache()
def get_user_service() -> UserService:
    return UserService(
        user_repo=get_user_repository(),
        email_service=get_email_service()
    )

# api.py - 깔끔한 API 컨트롤러
from ninja import Router
from ninja.errors import HttpError
from django.http import HttpRequest
from .dependency_injection import get_user_service

router = Router(tags=["Users"])

@router.post("/users", response={201: UserResponseSchema})
def create_user(request: HttpRequest, data: CreateUserSchema):
    """새 사용자 생성"""
    user_service = get_user_service()
    
    try:
        user = user_service.create_user_with_welcome(data)
        return 201, user
    except ValueError as e:
        raise HttpError(400, str(e))
```

## 🏗️ 계층화된 아키텍처 설계

### 1. 도메인 중심 설계 (Domain-Driven Design)

```python
# domains/user/models.py - 도메인 모델
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from enum import Enum

class UserStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    INACTIVE = 'inactive', 'Inactive'
    SUSPENDED = 'suspended', 'Suspended'
    PENDING = 'pending', 'Pending'

class User(AbstractUser):
    """사용자 도메인 모델"""
    status = models.CharField(
        max_length=20,
        choices=UserStatus.choices,
        default=UserStatus.PENDING
    )
    phone_number = models.CharField(max_length=20, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    profile_image = models.URLField(blank=True)
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def activate(self):
        """사용자 활성화"""
        self.status = UserStatus.ACTIVE
        self.save(update_fields=['status', 'updated_at'])
    
    def deactivate(self):
        """사용자 비활성화"""
        self.status = UserStatus.INACTIVE
        self.save(update_fields=['status', 'updated_at'])
    
    def is_profile_complete(self) -> bool:
        """프로필 완성도 확인"""
        required_fields = [
            self.first_name, 
            self.last_name, 
            self.phone_number
        ]
        return all(field.strip() for field in required_fields)
    
    @property
    def full_name(self) -> str:
        """전체 이름 반환"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def __str__(self):
        return f"{self.username} ({self.email})"

# domains/user/value_objects.py - 값 객체
from dataclasses import dataclass
from typing import Optional
import re

@dataclass(frozen=True)
class Email:
    """이메일 값 객체"""
    value: str
    
    def __post_init__(self):
        if not self._is_valid_email(self.value):
            raise ValueError(f"Invalid email format: {self.value}")
    
    @staticmethod
    def _is_valid_email(email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def domain(self) -> str:
        """도메인 반환"""
        return self.value.split('@')[1]

@dataclass(frozen=True)
class PhoneNumber:
    """전화번호 값 객체"""
    value: str
    
    def __post_init__(self):
        if not self._is_valid_phone(self.value):
            raise ValueError(f"Invalid phone number format: {self.value}")
    
    @staticmethod
    def _is_valid_phone(phone: str) -> bool:
        # 한국 전화번호 패턴
        pattern = r'^01[0-9]-\d{4}-\d{4}$'
        return re.match(pattern, phone) is not None
    
    def formatted(self) -> str:
        """포맷된 전화번호 반환"""
        return self.value

# domains/user/services.py - 도메인 서비스
from typing import List, Optional
from django.db import transaction
from .models import User, UserStatus
from .value_objects import Email, PhoneNumber

class UserDomainService:
    """사용자 도메인 서비스"""
    
    @staticmethod
    def can_change_email(user: User, new_email: str) -> bool:
        """이메일 변경 가능 여부 확인"""
        # 이미 같은 이메일인 경우
        if user.email == new_email:
            return False
        
        # 다른 사용자가 사용 중인 이메일인 경우
        if User.objects.filter(email=new_email).exclude(id=user.id).exists():
            return False
        
        # 최근 이메일 변경 이력 확인 (예: 30일 이내 변경 불가)
        # 실제로는 EmailChangeHistory 모델이 필요
        return True
    
    @staticmethod
    def calculate_user_score(user: User) -> int:
        """사용자 점수 계산"""
        score = 0
        
        # 프로필 완성도
        if user.is_profile_complete():
            score += 50
        
        # 활성 상태
        if user.status == UserStatus.ACTIVE:
            score += 30
        
        # 이메일 인증
        if user.email and '@' in user.email:
            score += 20
        
        return score
    
    @staticmethod
    @transaction.atomic
    def merge_users(primary_user: User, secondary_user: User) -> User:
        """사용자 계정 병합"""
        # 이차 사용자의 데이터를 주 사용자로 이전
        if not primary_user.phone_number and secondary_user.phone_number:
            primary_user.phone_number = secondary_user.phone_number
        
        if not primary_user.birth_date and secondary_user.birth_date:
            primary_user.birth_date = secondary_user.birth_date
        
        # 관련 데이터 이전 (Orders, Posts 등)
        # secondary_user.orders.update(user=primary_user)
        # secondary_user.posts.update(author=primary_user)
        
        primary_user.save()
        secondary_user.delete()
        
        return primary_user
```

### 2. 레이어별 책임 분리

```python
# application/user/dto.py - 데이터 전송 객체
from dataclasses import dataclass
from typing import Optional
from datetime import date, datetime

@dataclass
class CreateUserCommand:
    """사용자 생성 명령"""
    username: str
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    birth_date: Optional[date] = None

@dataclass
class UserQuery:
    """사용자 조회 쿼리"""
    user_id: Optional[int] = None
    email: Optional[str] = None
    username: Optional[str] = None
    status: Optional[str] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None

@dataclass
class UserDto:
    """사용자 DTO"""
    id: int
    username: str
    email: str
    full_name: str
    status: str
    is_profile_complete: bool
    created_at: datetime
    last_login: Optional[datetime] = None

# application/user/handlers.py - 애플리케이션 서비스
from typing import List, Optional
from django.db import transaction
from domains.user.models import User
from domains.user.services import UserDomainService
from .dto import CreateUserCommand, UserQuery, UserDto

class UserApplicationService:
    """사용자 애플리케이션 서비스"""
    
    @transaction.atomic
    def create_user(self, command: CreateUserCommand) -> UserDto:
        """사용자 생성"""
        # 이메일 중복 확인
        if User.objects.filter(email=command.email).exists():
            raise ValueError("Email already exists")
        
        # 사용자 생성
        user = User.objects.create_user(
            username=command.username,
            email=command.email,
            password=command.password,
            first_name=command.first_name or '',
            last_name=command.last_name or '',
            phone_number=command.phone_number or '',
            birth_date=command.birth_date,
        )
        
        return self._user_to_dto(user)
    
    def get_user(self, query: UserQuery) -> Optional[UserDto]:
        """사용자 조회"""
        user = self._find_user(query)
        return self._user_to_dto(user) if user else None
    
    def get_users(self, query: UserQuery) -> List[UserDto]:
        """사용자 목록 조회"""
        queryset = User.objects.all()
        
        if query.status:
            queryset = queryset.filter(status=query.status)
        
        if query.created_from:
            queryset = queryset.filter(created_at__gte=query.created_from)
        
        if query.created_to:
            queryset = queryset.filter(created_at__lte=query.created_to)
        
        return [self._user_to_dto(user) for user in queryset]
    
    def activate_user(self, user_id: int) -> UserDto:
        """사용자 활성화"""
        user = User.objects.get(id=user_id)
        user.activate()
        return self._user_to_dto(user)
    
    def _find_user(self, query: UserQuery) -> Optional[User]:
        """사용자 검색"""
        if query.user_id:
            try:
                return User.objects.get(id=query.user_id)
            except User.DoesNotExist:
                return None
        
        if query.email:
            try:
                return User.objects.get(email=query.email)
            except User.DoesNotExist:
                return None
        
        if query.username:
            try:
                return User.objects.get(username=query.username)
            except User.DoesNotExist:
                return None
        
        return None
    
    def _user_to_dto(self, user: User) -> UserDto:
        """User 모델을 DTO로 변환"""
        return UserDto(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            status=user.status,
            is_profile_complete=user.is_profile_complete(),
            created_at=user.created_at,
            last_login=user.last_login,
        )

# presentation/user/schemas.py - API 스키마
from ninja import Schema
from typing import Optional
from datetime import date, datetime
from enum import Enum

class UserStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

class CreateUserRequest(Schema):
    """사용자 생성 요청"""
    username: str
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    birth_date: Optional[date] = None
    
    class Config:
        schema_extra = {
            "example": {
                "username": "johndoe",
                "email": "john@example.com",
                "password": "securepassword123",
                "first_name": "John",
                "last_name": "Doe",
                "phone_number": "010-1234-5678",
                "birth_date": "1990-01-01"
            }
        }

class UserResponse(Schema):
    """사용자 응답"""
    id: int
    username: str
    email: str
    full_name: str
    status: UserStatusEnum
    is_profile_complete: bool
    created_at: datetime
    last_login: Optional[datetime] = None

class UserListQuery(Schema):
    """사용자 목록 조회 쿼리"""
    status: Optional[UserStatusEnum] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None
    page: int = 1
    size: int = 20

# presentation/user/api.py - API 컨트롤러
from ninja import Router, Query
from ninja.errors import HttpError
from ninja.pagination import paginate, PageNumberPagination
from typing import List
from application.user.handlers import UserApplicationService
from application.user.dto import CreateUserCommand, UserQuery
from .schemas import CreateUserRequest, UserResponse, UserListQuery

router = Router(tags=["Users"])
user_service = UserApplicationService()

@router.post("/", response={201: UserResponse})
def create_user(request, data: CreateUserRequest):
    """사용자 생성"""
    try:
        command = CreateUserCommand(
            username=data.username,
            email=data.email,
            password=data.password,
            first_name=data.first_name,
            last_name=data.last_name,
            phone_number=data.phone_number,
            birth_date=data.birth_date,
        )
        
        user_dto = user_service.create_user(command)
        return 201, user_dto
    
    except ValueError as e:
        raise HttpError(400, str(e))

@router.get("/{user_id}", response={200: UserResponse, 404: dict})
def get_user(request, user_id: int):
    """사용자 조회"""
    query = UserQuery(user_id=user_id)
    user_dto = user_service.get_user(query)
    
    if not user_dto:
        raise HttpError(404, "User not found")
    
    return user_dto

@router.get("/", response=List[UserResponse])
@paginate(PageNumberPagination, page_size=20)
def list_users(request, filters: UserListQuery = Query(...)):
    """사용자 목록 조회"""
    query = UserQuery(
        status=filters.status,
        created_from=filters.created_from,
        created_to=filters.created_to,
    )
    
    return user_service.get_users(query)

@router.patch("/{user_id}/activate", response={200: UserResponse})
def activate_user(request, user_id: int):
    """사용자 활성화"""
    try:
        user_dto = user_service.activate_user(user_id)
        return user_dto
    except User.DoesNotExist:
        raise HttpError(404, "User not found")
```

## 🔧 고급 패턴과 기법

### 1. 미들웨어 패턴

```python
# middleware/authentication.py - 인증 미들웨어
from ninja.security import HttpBearer
from ninja.errors import HttpError
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
import jwt
from django.conf import settings

User = get_user_model()

class JWTAuth(HttpBearer):
    """JWT 인증"""
    
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=['HS256']
            )
            user = User.objects.get(id=payload['user_id'])
            return user
        except (jwt.DecodeError, jwt.ExpiredSignatureError, User.DoesNotExist):
            return None

# middleware/logging.py - 로깅 미들웨어
import logging
import time
from ninja import NinjaAPI
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)

class APILoggingMiddleware:
    """API 요청/응답 로깅"""
    
    def __init__(self, api: NinjaAPI):
        self.api = api
        self._setup_hooks()
    
    def _setup_hooks(self):
        """API 훅 설정"""
        @self.api.exception_handler(Exception)
        def handle_exception(request: HttpRequest, exc: Exception):
            logger.error(
                f"API Error: {request.method} {request.path} - {exc}",
                extra={
                    'method': request.method,
                    'path': request.path,
                    'user': getattr(request, 'user', None),
                    'exception': str(exc),
                }
            )
            raise exc
    
    def log_request(self, request: HttpRequest):
        """요청 로깅"""
        request._start_time = time.time()
        logger.info(
            f"API Request: {request.method} {request.path}",
            extra={
                'method': request.method,
                'path': request.path,
                'user': getattr(request, 'user', None),
                'ip': self._get_client_ip(request),
            }
        )
    
    def log_response(self, request: HttpRequest, response: HttpResponse):
        """응답 로깅"""
        duration = time.time() - getattr(request, '_start_time', time.time())
        logger.info(
            f"API Response: {request.method} {request.path} - {response.status_code}",
            extra={
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration': duration,
                'user': getattr(request, 'user', None),
            }
        )
    
    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR', '')

# middleware/rate_limiting.py - 속도 제한
from django.core.cache import cache
from ninja.errors import HttpError
from django.http import HttpRequest
import time
from typing import Dict, Tuple

class RateLimitMiddleware:
    """API 속도 제한"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # 1분
    
    def check_rate_limit(self, request: HttpRequest) -> bool:
        """속도 제한 확인"""
        key = self._get_cache_key(request)
        current_time = int(time.time())
        window_start = current_time - self.window_size
        
        # 현재 윈도우의 요청 수 가져오기
        requests = cache.get(key, [])
        
        # 오래된 요청 제거
        requests = [req_time for req_time in requests if req_time > window_start]
        
        # 제한 확인
        if len(requests) >= self.requests_per_minute:
            return False
        
        # 현재 요청 추가
        requests.append(current_time)
        cache.set(key, requests, self.window_size)
        
        return True
    
    def _get_cache_key(self, request: HttpRequest) -> str:
        """캐시 키 생성"""
        user_id = getattr(request.user, 'id', None) if hasattr(request, 'user') else None
        if user_id:
            return f"rate_limit:user:{user_id}"
        
        # 익명 사용자는 IP 기반
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        return f"rate_limit:ip:{ip}"
```

### 2. 이벤트 주도 아키텍처

```python
# events/base.py - 이벤트 시스템 기반
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type
from dataclasses import dataclass
from datetime import datetime
import uuid

@dataclass
class DomainEvent:
    """도메인 이벤트 기본 클래스"""
    event_id: str
    occurred_at: datetime
    aggregate_id: str
    event_type: str
    data: Dict[str, Any]
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.occurred_at:
            self.occurred_at = datetime.utcnow()

class EventHandler(ABC):
    """이벤트 핸들러 인터페이스"""
    
    @abstractmethod
    def handle(self, event: DomainEvent) -> None:
        pass

class EventDispatcher:
    """이벤트 디스패처"""
    
    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
    
    def register(self, event_type: str, handler: EventHandler):
        """이벤트 핸들러 등록"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def dispatch(self, event: DomainEvent):
        """이벤트 발송"""
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler.handle(event)
            except Exception as e:
                # 로깅 및 에러 처리
                print(f"Event handler error: {e}")

# events/user_events.py - 사용자 이벤트
from dataclasses import dataclass
from typing import Dict, Any
from .base import DomainEvent

@dataclass
class UserCreatedEvent(DomainEvent):
    """사용자 생성 이벤트"""
    
    def __init__(self, user_id: int, email: str, username: str):
        super().__init__(
            event_id='',
            occurred_at=None,
            aggregate_id=str(user_id),
            event_type='user.created',
            data={
                'user_id': user_id,
                'email': email,
                'username': username,
            }
        )

@dataclass
class UserActivatedEvent(DomainEvent):
    """사용자 활성화 이벤트"""
    
    def __init__(self, user_id: int):
        super().__init__(
            event_id='',
            occurred_at=None,
            aggregate_id=str(user_id),
            event_type='user.activated',
            data={'user_id': user_id}
        )

# events/handlers.py - 이벤트 핸들러 구현
from .base import EventHandler, DomainEvent
from application.user.dto import UserDto
import logging

logger = logging.getLogger(__name__)

class WelcomeEmailHandler(EventHandler):
    """환영 이메일 발송 핸들러"""
    
    def handle(self, event: DomainEvent) -> None:
        if event.event_type == 'user.created':
            user_data = event.data
            logger.info(f"Sending welcome email to {user_data['email']}")
            # 실제 이메일 발송 로직
            # email_service.send_welcome_email(user_data['email'])

class UserAnalyticsHandler(EventHandler):
    """사용자 분석 데이터 수집 핸들러"""
    
    def handle(self, event: DomainEvent) -> None:
        if event.event_type in ['user.created', 'user.activated']:
            logger.info(f"Recording analytics for event: {event.event_type}")
            # 분석 데이터 수집
            # analytics_service.record_event(event)

class AuditLogHandler(EventHandler):
    """감사 로그 핸들러"""
    
    def handle(self, event: DomainEvent) -> None:
        logger.info(f"Audit log: {event.event_type} - {event.data}")
        # 감사 로그 저장
        # audit_service.log_event(event)

# main.py - 이벤트 시스템 설정
from events.base import EventDispatcher
from events.handlers import WelcomeEmailHandler, UserAnalyticsHandler, AuditLogHandler

# 이벤트 디스패처 설정
event_dispatcher = EventDispatcher()

# 핸들러 등록
event_dispatcher.register('user.created', WelcomeEmailHandler())
event_dispatcher.register('user.created', UserAnalyticsHandler())
event_dispatcher.register('user.created', AuditLogHandler())
event_dispatcher.register('user.activated', UserAnalyticsHandler())
event_dispatcher.register('user.activated', AuditLogHandler())

# application/user/handlers.py - 이벤트 발송 추가
class UserApplicationService:
    def __init__(self, event_dispatcher: EventDispatcher):
        self.event_dispatcher = event_dispatcher
    
    @transaction.atomic
    def create_user(self, command: CreateUserCommand) -> UserDto:
        """사용자 생성"""
        # ... 기존 로직 ...
        
        # 이벤트 발송
        event = UserCreatedEvent(
            user_id=user.id,
            email=user.email,
            username=user.username
        )
        self.event_dispatcher.dispatch(event)
        
        return self._user_to_dto(user)
```

### 3. 캐싱 전략

```python
# caching/decorators.py - 캐싱 데코레이터
from functools import wraps
from django.core.cache import cache
from typing import Any, Callable, Optional
import json
import hashlib

def cache_result(
    timeout: int = 300,
    key_prefix: str = '',
    vary_on: Optional[list] = None
):
    """결과 캐싱 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = _generate_cache_key(
                func.__name__, 
                args, 
                kwargs, 
                key_prefix, 
                vary_on
            )
            
            # 캐시에서 결과 조회
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # 함수 실행 및 결과 캐싱
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator

def _generate_cache_key(
    func_name: str, 
    args: tuple, 
    kwargs: dict, 
    prefix: str, 
    vary_on: Optional[list]
) -> str:
    """캐시 키 생성"""
    key_parts = [prefix, func_name] if prefix else [func_name]
    
    # vary_on이 지정된 경우 해당 파라미터만 사용
    if vary_on:
        for param in vary_on:
            if param in kwargs:
                key_parts.append(f"{param}:{kwargs[param]}")
    else:
        # 모든 인수를 키에 포함
        args_str = json.dumps(args, sort_keys=True, default=str)
        kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
        key_parts.extend([args_str, kwargs_str])
    
    key_string = ':'.join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()

# caching/strategies.py - 캐싱 전략
from django.core.cache import cache
from typing import List, Optional
from application.user.dto import UserDto, UserQuery

class UserCacheService:
    """사용자 캐싱 서비스"""
    
    CACHE_TIMEOUT = 300  # 5분
    KEY_PREFIX = 'user'
    
    @classmethod
    def get_user_by_id(cls, user_id: int) -> Optional[UserDto]:
        """ID로 사용자 캐시 조회"""
        cache_key = f"{cls.KEY_PREFIX}:id:{user_id}"
        return cache.get(cache_key)
    
    @classmethod
    def set_user(cls, user: UserDto) -> None:
        """사용자 캐시 저장"""
        cache_key = f"{cls.KEY_PREFIX}:id:{user.id}"
        cache.set(cache_key, user, cls.CACHE_TIMEOUT)
        
        # 이메일로도 캐싱
        email_key = f"{cls.KEY_PREFIX}:email:{user.email}"
        cache.set(email_key, user, cls.CACHE_TIMEOUT)
    
    @classmethod
    def invalidate_user(cls, user_id: int, email: str = None) -> None:
        """사용자 캐시 무효화"""
        cache_key = f"{cls.KEY_PREFIX}:id:{user_id}"
        cache.delete(cache_key)
        
        if email:
            email_key = f"{cls.KEY_PREFIX}:email:{email}"
            cache.delete(email_key)
    
    @classmethod
    def get_user_list(cls, query_hash: str) -> Optional[List[UserDto]]:
        """사용자 목록 캐시 조회"""
        cache_key = f"{cls.KEY_PREFIX}:list:{query_hash}"
        return cache.get(cache_key)
    
    @classmethod
    def set_user_list(cls, query_hash: str, users: List[UserDto]) -> None:
        """사용자 목록 캐시 저장"""
        cache_key = f"{cls.KEY_PREFIX}:list:{query_hash}"
        cache.set(cache_key, users, cls.CACHE_TIMEOUT // 2)  # 짧은 TTL

# application/user/handlers.py - 캐싱 적용
class UserApplicationService:
    def get_user(self, query: UserQuery) -> Optional[UserDto]:
        """사용자 조회 (캐싱 적용)"""
        # 캐시에서 먼저 조회
        if query.user_id:
            cached_user = UserCacheService.get_user_by_id(query.user_id)
            if cached_user:
                return cached_user
        
        # 데이터베이스에서 조회
        user = self._find_user(query)
        if not user:
            return None
        
        user_dto = self._user_to_dto(user)
        
        # 캐시에 저장
        UserCacheService.set_user(user_dto)
        
        return user_dto
    
    @cache_result(timeout=300, vary_on=['status', 'created_from', 'created_to'])
    def get_users(self, query: UserQuery) -> List[UserDto]:
        """사용자 목록 조회 (캐싱 적용)"""
        # 기존 로직...
        pass
```

## 🧪 테스트 전략

### 1. 단위 테스트

```python
# tests/unit/test_user_domain.py - 도메인 단위 테스트
import pytest
from django.test import TestCase
from domains.user.models import User, UserStatus
from domains.user.services import UserDomainService
from domains.user.value_objects import Email, PhoneNumber

class TestUserModel(TestCase):
    """사용자 모델 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_user_activation(self):
        """사용자 활성화 테스트"""
        self.user.activate()
        self.assertEqual(self.user.status, UserStatus.ACTIVE)
    
    def test_user_deactivation(self):
        """사용자 비활성화 테스트"""
        self.user.deactivate()
        self.assertEqual(self.user.status, UserStatus.INACTIVE)
    
    def test_profile_completion_check(self):
        """프로필 완성도 확인 테스트"""
        self.assertFalse(self.user.is_profile_complete())
        
        self.user.first_name = 'Test'
        self.user.last_name = 'User'
        self.user.phone_number = '010-1234-5678'
        self.user.save()
        
        self.assertTrue(self.user.is_profile_complete())

class TestValueObjects:
    """값 객체 테스트"""
    
    def test_valid_email(self):
        """유효한 이메일 테스트"""
        email = Email('test@example.com')
        assert email.value == 'test@example.com'
        assert email.domain() == 'example.com'
    
    def test_invalid_email(self):
        """유효하지 않은 이메일 테스트"""
        with pytest.raises(ValueError):
            Email('invalid-email')
    
    def test_valid_phone_number(self):
        """유효한 전화번호 테스트"""
        phone = PhoneNumber('010-1234-5678')
        assert phone.value == '010-1234-5678'
    
    def test_invalid_phone_number(self):
        """유효하지 않은 전화번호 테스트"""
        with pytest.raises(ValueError):
            PhoneNumber('invalid-phone')

# tests/unit/test_user_service.py - 서비스 단위 테스트
from unittest.mock import Mock, patch
from application.user.handlers import UserApplicationService
from application.user.dto import CreateUserCommand, UserQuery

class TestUserApplicationService:
    """사용자 애플리케이션 서비스 테스트"""
    
    def setUp(self):
        self.service = UserApplicationService()
    
    @patch('domains.user.models.User.objects.filter')
    @patch('domains.user.models.User.objects.create_user')
    def test_create_user_success(self, mock_create_user, mock_filter):
        """사용자 생성 성공 테스트"""
        # Mock 설정
        mock_filter.return_value.exists.return_value = False
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.email = 'test@example.com'
        mock_create_user.return_value = mock_user
        
        # 테스트 실행
        command = CreateUserCommand(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        result = self.service.create_user(command)
        
        # 검증
        assert result.username == 'testuser'
        assert result.email == 'test@example.com'
        mock_create_user.assert_called_once()
    
    @patch('domains.user.models.User.objects.filter')
    def test_create_user_duplicate_email(self, mock_filter):
        """중복 이메일로 사용자 생성 실패 테스트"""
        # Mock 설정
        mock_filter.return_value.exists.return_value = True
        
        # 테스트 실행 및 검증
        command = CreateUserCommand(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        with pytest.raises(ValueError, match="Email already exists"):
            self.service.create_user(command)
```

### 2. 통합 테스트

```python
# tests/integration/test_user_api.py - API 통합 테스트
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth import get_user_model
import json

User = get_user_model()

class TestUserAPI(TestCase):
    """사용자 API 통합 테스트"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_user_api(self):
        """사용자 생성 API 테스트"""
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123',
            'first_name': 'New',
            'last_name': 'User'
        }
        
        response = self.client.post(
            '/api/users/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        
        response_data = response.json()
        self.assertEqual(response_data['username'], 'newuser')
        self.assertEqual(response_data['email'], 'new@example.com')
    
    def test_get_user_api(self):
        """사용자 조회 API 테스트"""
        response = self.client.get(f'/api/users/{self.user.id}/')
        
        self.assertEqual(response.status_code, 200)
        
        response_data = response.json()
        self.assertEqual(response_data['id'], self.user.id)
        self.assertEqual(response_data['username'], self.user.username)
    
    def test_get_nonexistent_user_api(self):
        """존재하지 않는 사용자 조회 API 테스트"""
        response = self.client.get('/api/users/99999/')
        
        self.assertEqual(response.status_code, 404)
    
    def test_list_users_api(self):
        """사용자 목록 조회 API 테스트"""
        # 추가 사용자 생성
        User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='pass123'
        )
        
        response = self.client.get('/api/users/')
        
        self.assertEqual(response.status_code, 200)
        
        response_data = response.json()
        self.assertEqual(len(response_data), 2)

# tests/integration/test_user_events.py - 이벤트 통합 테스트
from django.test import TestCase
from unittest.mock import Mock, patch
from application.user.handlers import UserApplicationService
from application.user.dto import CreateUserCommand
from events.base import EventDispatcher
from events.handlers import WelcomeEmailHandler

class TestUserEvents(TestCase):
    """사용자 이벤트 통합 테스트"""
    
    def setUp(self):
        self.event_dispatcher = EventDispatcher()
        self.welcome_handler = Mock(spec=WelcomeEmailHandler)
        self.event_dispatcher.register('user.created', self.welcome_handler)
        
        self.service = UserApplicationService(self.event_dispatcher)
    
    @patch('domains.user.models.User.objects.filter')
    @patch('domains.user.models.User.objects.create_user')
    def test_user_creation_triggers_welcome_event(
        self, 
        mock_create_user, 
        mock_filter
    ):
        """사용자 생성 시 환영 이벤트 발생 테스트"""
        # Mock 설정
        mock_filter.return_value.exists.return_value = False
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = 'testuser'
        mock_user.email = 'test@example.com'
        mock_create_user.return_value = mock_user
        
        # 테스트 실행
        command = CreateUserCommand(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.service.create_user(command)
        
        # 이벤트 핸들러 호출 확인
        self.welcome_handler.handle.assert_called_once()
```

## 🎯 마무리

Django Ninja를 활용한 세련된 코딩은 단순히 문법을 아름답게 작성하는 것을 넘어서, 장기적으로 유지보수 가능하고 확장 가능한 시스템을 구축하는 것입니다.

### ✅ 핵심 원칙 요약

1. **단일 책임 원칙**: 각 클래스와 함수는 하나의 명확한 책임만 가져야 합니다
2. **의존성 역전**: 구체적인 구현이 아닌 추상화에 의존해야 합니다
3. **계층화 아키텍처**: 도메인, 애플리케이션, 인프라스트럭처 계층을 명확히 분리합니다
4. **이벤트 주도 설계**: 느슨한 결합을 위해 이벤트를 활용합니다
5. **테스트 가능한 설계**: 단위 테스트와 통합 테스트가 용이한 구조를 만듭니다

### 🚀 실무 적용 가이드

- **점진적 적용**: 기존 프로젝트에 한 번에 모든 패턴을 적용하지 말고 점진적으로 도입
- **팀 컨벤션**: 팀 내에서 일관된 코딩 스타일과 아키텍처 패턴 합의
- **지속적 리팩토링**: 코드 품질을 지속적으로 개선하는 문화 구축
- **문서화**: 아키텍처 결정사항과 패턴 적용 이유를 명확히 문서화

이러한 접근 방식을 통해 Django Ninja 프로젝트를 더욱 전문적이고 maintainable한 수준으로 끌어올릴 수 있습니다. 코드는 작성하는 순간보다 읽고 수정하는 시간이 훨씬 많다는 점을 항상 염두에 두고 개발해야 합니다.