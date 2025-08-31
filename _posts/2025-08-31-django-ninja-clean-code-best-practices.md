---
layout: post
title: "Django Ninja 클린 코드 가이드: 유지보수 가능한 API 설계 원칙"
date: 2025-08-31 12:00:00 +0900
categories: [Django, Clean Code]
tags: [django-ninja, clean-code, best-practices, API-design, architecture, refactoring, Python, Django]
image: "/assets/img/posts/2025-08-31-django-ninja-clean-code-best-practices.webp"
---

클린 코드는 단순히 "작동하는 코드"를 넘어서 "읽기 쉽고, 이해하기 쉽고, 변경하기 쉬운 코드"를 의미합니다. Django Ninja로 API를 개발할 때 클린 코드 원칙을 적용하면, 장기적으로 유지보수하기 쉽고 확장 가능한 시스템을 구축할 수 있습니다.

## 📋 목차

1. [클린 코드의 기본 원칙](#클린-코드의-기본-원칙)
2. [API 엔드포인트 설계](#api-엔드포인트-설계)
3. [스키마와 모델 분리](#스키마와-모델-분리)
4. [비즈니스 로직 추상화](#비즈니스-로직-추상화)
5. [에러 처리와 예외 관리](#에러-처리와-예외-관리)
6. [테스트 가능한 코드 설계](#테스트-가능한-코드-설계)
7. [성능과 가독성의 균형](#성능과-가독성의-균형)
8. [리팩토링 전략](#리팩토링-전략)

## 🎯 클린 코드의 기본 원칙

### 1. 의미 있는 이름 사용

**❌ 나쁜 예:**
```python
from ninja import NinjaAPI

api = NinjaAPI()

@api.get("/u/{id}")
def get_u(request, id: int):
    u = User.objects.get(id=id)
    return {"data": u}

@api.post("/u")
def create_u(request, data: dict):
    u = User.objects.create(**data)
    return {"msg": "ok"}
```

**✅ 좋은 예:**
```python
from ninja import NinjaAPI
from .schemas import UserSchema, UserCreateSchema
from .services import UserService

api = NinjaAPI()

@api.get("/users/{user_id}", response=UserSchema)
def get_user_by_id(request, user_id: int):
    user = UserService.get_user_by_id(user_id)
    return user

@api.post("/users", response=UserSchema)
def create_user(request, user_data: UserCreateSchema):
    created_user = UserService.create_user(user_data.dict())
    return created_user
```

### 2. 함수는 한 가지 일만 수행

**❌ 나쁜 예:**
```python
@api.post("/users")
def create_user_and_send_email(request, data: UserCreateSchema):
    # 사용자 생성
    user = User.objects.create(
        username=data.username,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name
    )
    
    # 프로필 생성
    profile = UserProfile.objects.create(
        user=user,
        bio=data.bio or ""
    )
    
    # 이메일 발송
    subject = f"Welcome {user.first_name}!"
    message = f"Thank you for joining us, {user.username}"
    send_mail(subject, message, 'noreply@example.com', [user.email])
    
    # 로그 기록
    logger.info(f"New user created: {user.username}")
    
    # 통계 업데이트
    stats = UserStats.objects.get_or_create(date=timezone.now().date())[0]
    stats.new_users += 1
    stats.save()
    
    return user
```

**✅ 좋은 예:**
```python
@api.post("/users", response=UserSchema)
def create_user(request, user_data: UserCreateSchema):
    """새 사용자를 생성합니다."""
    created_user = UserService.create_user(user_data.dict())
    return created_user

class UserService:
    @staticmethod
    def create_user(user_data: dict) -> User:
        """사용자 생성 비즈니스 로직을 처리합니다."""
        user = UserRepository.create_user(user_data)
        
        # 후속 작업들을 별도로 처리
        UserProfileService.create_default_profile(user)
        EmailService.send_welcome_email(user)
        LoggingService.log_user_creation(user)
        StatsService.increment_new_user_count()
        
        return user
```

## 🔗 API 엔드포인트 설계

### RESTful 설계 원칙

**✅ 클린한 API 구조:**
```python
from ninja import NinjaAPI, Router
from typing import List

# 리소스별 라우터 분리
users_router = Router(tags=["Users"])
posts_router = Router(tags=["Posts"])

# 사용자 관련 엔드포인트
@users_router.get("", response=List[UserSchema])
def list_users(request, page: int = 1, limit: int = 20):
    """사용자 목록을 조회합니다."""
    return UserService.get_users_paginated(page, limit)

@users_router.get("/{user_id}", response=UserSchema)
def get_user(request, user_id: int):
    """특정 사용자를 조회합니다."""
    return UserService.get_user_by_id(user_id)

@users_router.post("", response=UserSchema)
def create_user(request, user_data: UserCreateSchema):
    """새 사용자를 생성합니다."""
    return UserService.create_user(user_data.dict())

@users_router.put("/{user_id}", response=UserSchema)
def update_user(request, user_id: int, user_data: UserUpdateSchema):
    """사용자 정보를 수정합니다."""
    return UserService.update_user(user_id, user_data.dict(exclude_unset=True))

@users_router.delete("/{user_id}")
def delete_user(request, user_id: int):
    """사용자를 삭제합니다."""
    UserService.delete_user(user_id)
    return {"message": "User deleted successfully"}

# 중첩 리소스
@users_router.get("/{user_id}/posts", response=List[PostSchema])
def get_user_posts(request, user_id: int):
    """특정 사용자의 게시물 목록을 조회합니다."""
    return PostService.get_posts_by_user(user_id)

# API에 라우터 등록
api = NinjaAPI()
api.add_router("/users", users_router)
api.add_router("/posts", posts_router)
```

### 일관된 응답 형식

```python
from ninja import Schema
from typing import Optional, Any, Dict
from enum import Enum

class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"

class APIResponse(Schema):
    """표준 API 응답 형식"""
    status: ResponseStatus
    message: Optional[str] = None
    data: Optional[Any] = None
    errors: Optional[Dict[str, Any]] = None

class PaginatedResponse(Schema):
    """페이지네이션 응답 형식"""
    items: List[Any]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool

# 일관된 응답 생성을 위한 헬퍼 함수들
class ResponseBuilder:
    @staticmethod
    def success(data=None, message="Operation successful"):
        return APIResponse(
            status=ResponseStatus.SUCCESS,
            message=message,
            data=data
        )
    
    @staticmethod
    def error(message="An error occurred", errors=None):
        return APIResponse(
            status=ResponseStatus.ERROR,
            message=message,
            errors=errors
        )
    
    @staticmethod
    def paginated(items, total, page, per_page):
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            has_next=page * per_page < total,
            has_prev=page > 1
        )

# 사용 예시
@api.get("/users", response=PaginatedResponse)
def list_users(request, page: int = 1, per_page: int = 20):
    users, total = UserService.get_users_paginated(page, per_page)
    return ResponseBuilder.paginated(users, total, page, per_page)
```

## 📝 스키마와 모델 분리

### 계층별 스키마 설계

```python
# models.py
class User(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField()
    password = models.CharField(max_length=128)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# schemas/user_schemas.py
from ninja import ModelSchema, Schema
from typing import Optional
from datetime import datetime

# 입력용 스키마들
class UserCreateSchema(Schema):
    """사용자 생성 시 필요한 데이터"""
    username: str
    email: str
    password: str
    first_name: str
    last_name: str

class UserUpdateSchema(Schema):
    """사용자 정보 수정 시 사용하는 데이터"""
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

# 출력용 스키마들
class UserSchema(ModelSchema):
    """기본 사용자 정보 응답"""
    full_name: str
    
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", 
                 "is_active", "created_at"]
    
    @staticmethod
    def resolve_full_name(obj):
        return f"{obj.first_name} {obj.last_name}".strip()

class UserDetailSchema(UserSchema):
    """상세 사용자 정보 응답"""
    posts_count: int
    last_login: Optional[datetime]
    
    class Meta(UserSchema.Meta):
        fields = UserSchema.Meta.fields + ["updated_at"]
    
    @staticmethod
    def resolve_posts_count(obj):
        return obj.posts.count()

class UserListSchema(ModelSchema):
    """사용자 목록용 간소화된 스키마"""
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "is_active"]

# 보안을 고려한 스키마 분리
class PublicUserSchema(ModelSchema):
    """공개 사용자 정보"""
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]

class PrivateUserSchema(UserDetailSchema):
    """개인 정보를 포함한 사용자 정보 (본인만 조회 가능)"""
    email: str
    
    class Meta(UserDetailSchema.Meta):
        fields = UserDetailSchema.Meta.fields + ["email"]
```

### 스키마 팩토리 패턴

```python
from enum import Enum
from typing import Type, Union

class UserContext(str, Enum):
    """사용자 조회 컨텍스트"""
    PUBLIC = "public"      # 공개 프로필
    PRIVATE = "private"    # 본인 프로필
    ADMIN = "admin"        # 관리자 뷰

class UserSchemaFactory:
    """컨텍스트에 따른 적절한 스키마를 반환하는 팩토리"""
    
    _schema_mapping = {
        UserContext.PUBLIC: PublicUserSchema,
        UserContext.PRIVATE: PrivateUserSchema,
        UserContext.ADMIN: AdminUserSchema,
    }
    
    @classmethod
    def get_schema(cls, context: UserContext) -> Type[ModelSchema]:
        """컨텍스트에 맞는 스키마 클래스를 반환"""
        return cls._schema_mapping.get(context, PublicUserSchema)
    
    @classmethod
    def get_user_response(cls, user: User, context: UserContext):
        """컨텍스트에 맞는 스키마로 사용자 데이터를 직렬화"""
        schema_class = cls.get_schema(context)
        return schema_class.from_orm(user)

# API 엔드포인트에서 사용
@api.get("/users/{user_id}")
def get_user_profile(request, user_id: int):
    user = get_object_or_404(User, id=user_id)
    
    # 컨텍스트 결정
    if user == request.user:
        context = UserContext.PRIVATE
    elif request.user.is_staff:
        context = UserContext.ADMIN
    else:
        context = UserContext.PUBLIC
    
    return UserSchemaFactory.get_user_response(user, context)
```

## 🏗️ 비즈니스 로직 추상화

### 서비스 레이어 패턴

```python
# services/user_service.py
from django.db import transaction
from django.core.exceptions import ValidationError
from typing import Optional, List, Tuple
from ..models import User
from ..repositories import UserRepository
from .email_service import EmailService
from .logging_service import LoggingService

class UserService:
    """사용자 관련 비즈니스 로직을 담당하는 서비스"""
    
    @staticmethod
    def get_user_by_id(user_id: int) -> User:
        """ID로 사용자를 조회합니다."""
        user = UserRepository.find_by_id(user_id)
        if not user:
            raise ValidationError(f"User with id {user_id} not found")
        return user
    
    @staticmethod
    def get_users_paginated(page: int, per_page: int) -> Tuple[List[User], int]:
        """페이지네이션된 사용자 목록을 반환합니다."""
        if page < 1 or per_page < 1:
            raise ValidationError("Page and per_page must be positive integers")
        
        if per_page > 100:
            raise ValidationError("Maximum per_page is 100")
        
        return UserRepository.get_paginated(page, per_page)
    
    @staticmethod
    @transaction.atomic
    def create_user(user_data: dict) -> User:
        """새 사용자를 생성합니다."""
        # 비즈니스 규칙 검증
        UserService._validate_user_creation(user_data)
        
        # 사용자 생성
        user = UserRepository.create(user_data)
        
        # 후속 작업들
        UserService._handle_user_creation_side_effects(user)
        
        LoggingService.log_user_created(user)
        
        return user
    
    @staticmethod
    def _validate_user_creation(user_data: dict):
        """사용자 생성 시 비즈니스 규칙을 검증합니다."""
        if UserRepository.exists_by_username(user_data['username']):
            raise ValidationError("Username already exists")
        
        if UserRepository.exists_by_email(user_data['email']):
            raise ValidationError("Email already exists")
        
        # 추가 비즈니스 규칙들...
    
    @staticmethod
    def _handle_user_creation_side_effects(user: User):
        """사용자 생성 후 부수 효과들을 처리합니다."""
        try:
            EmailService.send_welcome_email(user)
        except Exception as e:
            # 이메일 실패는 사용자 생성을 롤백하지 않음
            LoggingService.log_email_failure(user, e)

# repositories/user_repository.py
from django.db import models
from typing import Optional, List, Tuple
from ..models import User

class UserRepository:
    """사용자 데이터 접근을 담당하는 리포지토리"""
    
    @staticmethod
    def find_by_id(user_id: int) -> Optional[User]:
        """ID로 사용자를 찾습니다."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def find_by_username(username: str) -> Optional[User]:
        """사용자명으로 사용자를 찾습니다."""
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def exists_by_username(username: str) -> bool:
        """사용자명 존재 여부를 확인합니다."""
        return User.objects.filter(username=username).exists()
    
    @staticmethod
    def exists_by_email(email: str) -> bool:
        """이메일 존재 여부를 확인합니다."""
        return User.objects.filter(email=email).exists()
    
    @staticmethod
    def get_paginated(page: int, per_page: int) -> Tuple[List[User], int]:
        """페이지네이션된 사용자 목록과 전체 개수를 반환합니다."""
        offset = (page - 1) * per_page
        
        users = list(User.objects.select_related()
                    .order_by('-created_at')[offset:offset + per_page])
        total = User.objects.count()
        
        return users, total
    
    @staticmethod
    def create(user_data: dict) -> User:
        """새 사용자를 생성합니다."""
        return User.objects.create(**user_data)
```

### 도메인 이벤트 패턴

```python
# events/user_events.py
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

@dataclass
class DomainEvent:
    """도메인 이벤트 기본 클래스"""
    occurred_at: datetime
    event_data: Dict[str, Any]

@dataclass
class UserCreatedEvent(DomainEvent):
    """사용자 생성 이벤트"""
    user_id: int
    username: str
    email: str

@dataclass
class UserUpdatedEvent(DomainEvent):
    """사용자 정보 수정 이벤트"""
    user_id: int
    changed_fields: Dict[str, Any]

# events/event_dispatcher.py
from typing import List, Callable, Dict, Type
from .user_events import DomainEvent

class EventDispatcher:
    """도메인 이벤트 디스패처"""
    
    def __init__(self):
        self._handlers: Dict[Type[DomainEvent], List[Callable]] = {}
    
    def register_handler(self, event_type: Type[DomainEvent], handler: Callable):
        """이벤트 핸들러를 등록합니다."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def dispatch(self, event: DomainEvent):
        """이벤트를 디스패치합니다."""
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # 이벤트 처리 실패는 로그만 남기고 계속 진행
                logger.error(f"Event handler failed: {e}")

# 이벤트 핸들러들
class UserEventHandlers:
    """사용자 관련 이벤트 핸들러들"""
    
    @staticmethod
    def handle_user_created(event: UserCreatedEvent):
        """사용자 생성 이벤트 처리"""
        # 환영 이메일 발송
        EmailService.send_welcome_email_async(event.user_id)
        
        # 통계 업데이트
        StatsService.increment_user_count()
        
        # 외부 서비스에 알림
        ExternalService.notify_user_created(event.user_id)

# 서비스에서 이벤트 사용
class UserService:
    def __init__(self):
        self.event_dispatcher = EventDispatcher()
        self._register_event_handlers()
    
    def _register_event_handlers(self):
        """이벤트 핸들러들을 등록합니다."""
        self.event_dispatcher.register_handler(
            UserCreatedEvent,
            UserEventHandlers.handle_user_created
        )
    
    @transaction.atomic
    def create_user(self, user_data: dict) -> User:
        """사용자를 생성하고 이벤트를 발생시킵니다."""
        user = UserRepository.create(user_data)
        
        # 이벤트 발생
        event = UserCreatedEvent(
            occurred_at=timezone.now(),
            event_data=user_data,
            user_id=user.id,
            username=user.username,
            email=user.email
        )
        
        self.event_dispatcher.dispatch(event)
        
        return user
```

## ⚠️ 에러 처리와 예외 관리

### 커스텀 예외 계층 구조

```python
# exceptions/base_exceptions.py
class APIException(Exception):
    """API 예외 기본 클래스"""
    status_code = 500
    error_code = "INTERNAL_ERROR"
    message = "An internal error occurred"
    
    def __init__(self, message: str = None, details: dict = None):
        self.message = message or self.message
        self.details = details or {}
        super().__init__(self.message)

class ValidationException(APIException):
    """유효성 검증 예외"""
    status_code = 400
    error_code = "VALIDATION_ERROR"
    message = "Validation failed"

class NotFoundError(APIException):
    """리소스를 찾을 수 없음"""
    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found"

class PermissionDeniedError(APIException):
    """권한 거부"""
    status_code = 403
    error_code = "PERMISSION_DENIED"
    message = "Permission denied"

# exceptions/user_exceptions.py
class UserNotFoundException(NotFoundError):
    """사용자를 찾을 수 없음"""
    error_code = "USER_NOT_FOUND"
    message = "User not found"

class DuplicateUsernameError(ValidationException):
    """중복된 사용자명"""
    error_code = "DUPLICATE_USERNAME"
    message = "Username already exists"

class DuplicateEmailError(ValidationException):
    """중복된 이메일"""
    error_code = "DUPLICATE_EMAIL"
    message = "Email already exists"

# API 에러 핸들러
from ninja.errors import ValidationError as NinjaValidationError

@api.exception_handler(APIException)
def api_exception_handler(request, exc: APIException):
    """커스텀 API 예외 핸들러"""
    return api.create_response(
        request,
        {
            "status": "error",
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details
        },
        status=exc.status_code
    )

@api.exception_handler(NinjaValidationError)
def validation_exception_handler(request, exc: NinjaValidationError):
    """Pydantic 유효성 검증 예외 핸들러"""
    errors = {}
    
    for error in exc.errors:
        field_path = '.'.join(str(loc) for loc in error['loc'])
        errors[field_path] = error['msg']
    
    return api.create_response(
        request,
        {
            "status": "error",
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {"field_errors": errors}
        },
        status=400
    )

# 서비스에서 예외 사용
class UserService:
    @staticmethod
    def get_user_by_id(user_id: int) -> User:
        user = UserRepository.find_by_id(user_id)
        if not user:
            raise UserNotFoundException(
                f"User with id {user_id} does not exist"
            )
        return user
    
    @staticmethod
    def create_user(user_data: dict) -> User:
        # 사용자명 중복 검사
        if UserRepository.exists_by_username(user_data['username']):
            raise DuplicateUsernameError()
        
        # 이메일 중복 검사
        if UserRepository.exists_by_email(user_data['email']):
            raise DuplicateEmailError()
        
        return UserRepository.create(user_data)
```

### 에러 응답 표준화

```python
# schemas/error_schemas.py
from ninja import Schema
from typing import Optional, Dict, Any

class ErrorDetail(Schema):
    """에러 상세 정보"""
    field: str
    message: str
    code: Optional[str] = None

class ErrorResponse(Schema):
    """표준 에러 응답"""
    status: str = "error"
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    path: str

# utils/error_utils.py
from django.utils import timezone

class ErrorResponseBuilder:
    """에러 응답 생성 유틸리티"""
    
    @staticmethod
    def build_error_response(
        request,
        error_code: str,
        message: str,
        details: Dict[str, Any] = None,
        status_code: int = 500
    ):
        """표준화된 에러 응답을 생성합니다."""
        return {
            "status": "error",
            "error_code": error_code,
            "message": message,
            "details": details or {},
            "timestamp": timezone.now().isoformat(),
            "path": request.path
        }

# API 엔드포인트에서 사용
@api.get("/users/{user_id}", response=UserSchema)
def get_user(request, user_id: int):
    """사용자 조회 - 클린한 에러 처리"""
    try:
        user = UserService.get_user_by_id(user_id)
        return user
    except UserNotFoundException as e:
        # 이미 예외 핸들러에서 처리되므로 그냥 re-raise
        raise
    except Exception as e:
        # 예상치 못한 에러는 로깅 후 일반적인 에러로 변환
        logger.error(f"Unexpected error in get_user: {e}")
        raise APIException("An unexpected error occurred")
```

## 🧪 테스트 가능한 코드 설계

### 의존성 주입

```python
# services/interfaces.py
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

class UserRepositoryInterface(ABC):
    """사용자 리포지토리 인터페이스"""
    
    @abstractmethod
    def find_by_id(self, user_id: int) -> Optional[User]:
        pass
    
    @abstractmethod
    def create(self, user_data: dict) -> User:
        pass
    
    @abstractmethod
    def exists_by_username(self, username: str) -> bool:
        pass

class EmailServiceInterface(ABC):
    """이메일 서비스 인터페이스"""
    
    @abstractmethod
    def send_welcome_email(self, user: User) -> bool:
        pass

# services/user_service.py (의존성 주입 버전)
class UserService:
    """테스트 가능한 사용자 서비스"""
    
    def __init__(
        self,
        user_repository: UserRepositoryInterface,
        email_service: EmailServiceInterface,
        logger: LoggerInterface = None
    ):
        self.user_repository = user_repository
        self.email_service = email_service
        self.logger = logger or DefaultLogger()
    
    def get_user_by_id(self, user_id: int) -> User:
        """의존성 주입된 리포지토리를 사용한 사용자 조회"""
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise UserNotFoundException(f"User {user_id} not found")
        return user
    
    def create_user(self, user_data: dict) -> User:
        """의존성 주입된 서비스들을 사용한 사용자 생성"""
        # 비즈니스 로직
        if self.user_repository.exists_by_username(user_data['username']):
            raise DuplicateUsernameError()
        
        user = self.user_repository.create(user_data)
        
        # 이메일 발송 (실패해도 사용자 생성은 성공)
        try:
            self.email_service.send_welcome_email(user)
        except Exception as e:
            self.logger.warning(f"Welcome email failed for user {user.id}: {e}")
        
        return user

# API 엔드포인트에서 DI 컨테이너 사용
class DIContainer:
    """간단한 DI 컨테이너"""
    
    def __init__(self):
        self._services = {}
    
    def register(self, interface_type, implementation):
        self._services[interface_type] = implementation
    
    def get(self, interface_type):
        return self._services.get(interface_type)

# 컨테이너 설정
container = DIContainer()
container.register(UserRepositoryInterface, UserRepository())
container.register(EmailServiceInterface, EmailService())

# API에서 사용
@api.get("/users/{user_id}", response=UserSchema)
def get_user(request, user_id: int):
    user_service = UserService(
        user_repository=container.get(UserRepositoryInterface),
        email_service=container.get(EmailServiceInterface)
    )
    user = user_service.get_user_by_id(user_id)
    return user
```

### 모킹과 단위 테스트

```python
# tests/test_user_service.py
import pytest
from unittest.mock import Mock, MagicMock
from services.user_service import UserService
from exceptions.user_exceptions import UserNotFoundException, DuplicateUsernameError

class TestUserService:
    """UserService 단위 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 실행되는 설정"""
        self.mock_user_repository = Mock()
        self.mock_email_service = Mock()
        self.mock_logger = Mock()
        
        self.user_service = UserService(
            user_repository=self.mock_user_repository,
            email_service=self.mock_email_service,
            logger=self.mock_logger
        )
    
    def test_get_user_by_id_success(self):
        """사용자 조회 성공 테스트"""
        # Given
        user_id = 1
        expected_user = User(id=1, username="testuser")
        self.mock_user_repository.find_by_id.return_value = expected_user
        
        # When
        result = self.user_service.get_user_by_id(user_id)
        
        # Then
        assert result == expected_user
        self.mock_user_repository.find_by_id.assert_called_once_with(user_id)
    
    def test_get_user_by_id_not_found(self):
        """사용자 조회 실패 테스트"""
        # Given
        user_id = 999
        self.mock_user_repository.find_by_id.return_value = None
        
        # When & Then
        with pytest.raises(UserNotFoundException):
            self.user_service.get_user_by_id(user_id)
    
    def test_create_user_success(self):
        """사용자 생성 성공 테스트"""
        # Given
        user_data = {"username": "newuser", "email": "new@example.com"}
        created_user = User(id=1, username="newuser")
        
        self.mock_user_repository.exists_by_username.return_value = False
        self.mock_user_repository.create.return_value = created_user
        self.mock_email_service.send_welcome_email.return_value = True
        
        # When
        result = self.user_service.create_user(user_data)
        
        # Then
        assert result == created_user
        self.mock_user_repository.exists_by_username.assert_called_once_with("newuser")
        self.mock_user_repository.create.assert_called_once_with(user_data)
        self.mock_email_service.send_welcome_email.assert_called_once_with(created_user)
    
    def test_create_user_duplicate_username(self):
        """중복 사용자명으로 사용자 생성 실패 테스트"""
        # Given
        user_data = {"username": "existinguser", "email": "new@example.com"}
        self.mock_user_repository.exists_by_username.return_value = True
        
        # When & Then
        with pytest.raises(DuplicateUsernameError):
            self.user_service.create_user(user_data)
        
        # create는 호출되지 않아야 함
        self.mock_user_repository.create.assert_not_called()
    
    def test_create_user_email_failure_does_not_break_creation(self):
        """이메일 발송 실패가 사용자 생성을 방해하지 않는지 테스트"""
        # Given
        user_data = {"username": "newuser", "email": "new@example.com"}
        created_user = User(id=1, username="newuser")
        
        self.mock_user_repository.exists_by_username.return_value = False
        self.mock_user_repository.create.return_value = created_user
        self.mock_email_service.send_welcome_email.side_effect = Exception("SMTP Error")
        
        # When
        result = self.user_service.create_user(user_data)
        
        # Then
        assert result == created_user
        self.mock_logger.warning.assert_called_once()
```

### 통합 테스트

```python
# tests/test_user_api.py
from ninja.testing import TestClient
from django.test import TestCase
from django.contrib.auth.models import User

class TestUserAPI(TestCase):
    """사용자 API 통합 테스트"""
    
    def setUp(self):
        self.client = TestClient(api)
        self.test_user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    def test_get_user_success(self):
        """사용자 조회 API 성공 테스트"""
        response = self.client.get(f"/users/{self.test_user.id}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["username"], "testuser")
        self.assertEqual(data["email"], "test@example.com")
    
    def test_get_user_not_found(self):
        """존재하지 않는 사용자 조회 테스트"""
        response = self.client.get("/users/999")
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["error_code"], "USER_NOT_FOUND")
    
    def test_create_user_success(self):
        """사용자 생성 API 성공 테스트"""
        user_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpass123",
            "first_name": "New",
            "last_name": "User"
        }
        
        response = self.client.post("/users", json=user_data)
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["username"], "newuser")
        
        # DB에도 실제로 생성되었는지 확인
        created_user = User.objects.get(username="newuser")
        self.assertEqual(created_user.email, "new@example.com")
    
    def test_create_user_duplicate_username(self):
        """중복 사용자명으로 사용자 생성 실패 테스트"""
        user_data = {
            "username": "testuser",  # 이미 존재하는 사용자명
            "email": "another@example.com",
            "password": "newpass123"
        }
        
        response = self.client.post("/users", json=user_data)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error_code"], "DUPLICATE_USERNAME")
```

## ⚡ 성능과 가독성의 균형

### 효율적인 데이터베이스 쿼리

```python
# repositories/optimized_user_repository.py
class OptimizedUserRepository:
    """성능 최적화된 사용자 리포지토리"""
    
    @staticmethod
    def get_users_with_posts_count(page: int, per_page: int) -> Tuple[List[User], int]:
        """게시물 개수와 함께 사용자 목록을 효율적으로 조회"""
        from django.db.models import Count
        
        offset = (page - 1) * per_page
        
        # 한 번의 쿼리로 게시물 개수까지 함께 조회
        users = User.objects.annotate(
            posts_count=Count('posts')
        ).select_related(
            'profile'  # 프로필 정보도 함께 로드
        ).order_by('-created_at')[offset:offset + per_page]
        
        # 전체 개수는 별도로 캐시된 값 사용 (성능 고려)
        total_count = cache.get_or_set(
            'total_users_count',
            lambda: User.objects.count(),
            timeout=300  # 5분
        )
        
        return list(users), total_count
    
    @staticmethod
    def get_user_with_recent_posts(user_id: int) -> Optional[User]:
        """사용자와 최근 게시물들을 효율적으로 조회"""
        from django.db.models import Prefetch
        
        try:
            return User.objects.select_related('profile').prefetch_related(
                Prefetch(
                    'posts',
                    queryset=Post.objects.select_related('category')
                                        .order_by('-created_at')[:5],
                    to_attr='recent_posts'
                )
            ).get(id=user_id)
        except User.DoesNotExist:
            return None

# 가독성을 해치지 않는 성능 최적화
class UserService:
    @staticmethod
    def get_users_dashboard_data(page: int, per_page: int) -> dict:
        """대시보드용 사용자 데이터를 효율적으로 조회"""
        # 복잡한 쿼리 최적화를 서비스 레이어에 숨김
        users, total = OptimizedUserRepository.get_users_with_posts_count(page, per_page)
        
        # 비즈니스 로직은 명확하게 분리
        dashboard_data = {
            'users': [UserService._format_user_for_dashboard(user) for user in users],
            'pagination': {
                'total': total,
                'page': page,
                'per_page': per_page,
                'has_next': page * per_page < total
            },
            'summary': UserService._get_users_summary()
        }
        
        return dashboard_data
    
    @staticmethod
    def _format_user_for_dashboard(user: User) -> dict:
        """대시보드용 사용자 데이터 포맷팅"""
        return {
            'id': user.id,
            'username': user.username,
            'full_name': f"{user.first_name} {user.last_name}".strip(),
            'posts_count': user.posts_count,  # annotated field
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat()
        }
    
    @staticmethod
    def _get_users_summary() -> dict:
        """사용자 요약 통계 (캐시 활용)"""
        return cache.get_or_set(
            'users_summary',
            lambda: {
                'total_users': User.objects.count(),
                'active_users': User.objects.filter(is_active=True).count(),
                'new_users_today': User.objects.filter(
                    created_at__date=timezone.now().date()
                ).count()
            },
            timeout=600  # 10분
        )
```

### 선택적 최적화

```python
# 성능 크리티컬한 엔드포인트는 별도로 최적화
@api.get("/users/dashboard", response=DashboardResponse)
def get_users_dashboard(request, page: int = 1, per_page: int = 20):
    """대시보드용 최적화된 사용자 목록"""
    # 복잡한 최적화는 서비스 레이어에 위임
    dashboard_data = UserService.get_users_dashboard_data(page, per_page)
    return dashboard_data

# 일반적인 CRUD는 가독성 우선
@api.get("/users/{user_id}", response=UserSchema)
def get_user(request, user_id: int):
    """단일 사용자 조회 - 가독성 우선"""
    user = UserService.get_user_by_id(user_id)
    return user

# 복잡한 비즈니스 로직은 명확한 이름으로 분리
@api.post("/users/{user_id}/activate")
def activate_user_account(request, user_id: int):
    """사용자 계정 활성화 - 명확한 의도 표현"""
    user = UserService.activate_user_account(user_id)
    return {"message": f"User {user.username} has been activated"}
```

## 🔄 리팩토링 전략

### 점진적 리팩토링

```python
# BEFORE: 모든 것이 한 곳에 있는 코드
@api.post("/users")
def create_user_old(request, data: dict):
    # 유효성 검증
    if not data.get('username'):
        return {"error": "Username is required"}
    
    if User.objects.filter(username=data['username']).exists():
        return {"error": "Username already exists"}
    
    # 사용자 생성
    user = User.objects.create(
        username=data['username'],
        email=data['email'],
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', '')
    )
    
    # 이메일 발송
    send_mail(
        'Welcome!',
        f'Welcome {user.username}!',
        'noreply@example.com',
        [user.email]
    )
    
    return {"id": user.id, "username": user.username}

# STEP 1: 스키마 도입
@api.post("/users", response=UserSchema)
def create_user_step1(request, user_data: UserCreateSchema):
    # 여전히 모든 로직이 뷰에 있지만 스키마는 적용
    if User.objects.filter(username=user_data.username).exists():
        raise ValidationException("Username already exists")
    
    user = User.objects.create(**user_data.dict())
    
    # 이메일 발송
    send_mail(
        'Welcome!',
        f'Welcome {user.username}!',
        'noreply@example.com',
        [user.email]
    )
    
    return user

# STEP 2: 서비스 레이어 도입
@api.post("/users", response=UserSchema)
def create_user_step2(request, user_data: UserCreateSchema):
    # 비즈니스 로직을 서비스로 이동
    user = UserService.create_user(user_data.dict())
    return user

# STEP 3: 예외 처리 개선
@api.post("/users", response=UserSchema)
def create_user_step3(request, user_data: UserCreateSchema):
    try:
        user = UserService.create_user(user_data.dict())
        return user
    except DuplicateUsernameError:
        # 이제 커스텀 예외 핸들러가 처리함
        raise

# FINAL: 클린한 최종 형태
@api.post("/users", response=UserSchema)
def create_user(request, user_data: UserCreateSchema):
    """새 사용자를 생성합니다."""
    user = UserService.create_user(user_data.dict())
    return user
```

### 레거시 코드 개선

```python
# 레거시 코드를 감싸는 어댑터 패턴
class LegacyUserManager:
    """기존 레거시 사용자 관리 코드"""
    
    def create_user_old_way(self, username, email, first_name="", last_name=""):
        # 복잡하고 읽기 어려운 레거시 코드
        # 하지만 잘 작동하고 있어서 함부로 바꿀 수 없음
        pass

class UserServiceAdapter:
    """레거시 코드를 새로운 인터페이스에 맞게 감싸는 어댑터"""
    
    def __init__(self):
        self.legacy_manager = LegacyUserManager()
    
    def create_user(self, user_data: dict) -> User:
        """새로운 인터페이스로 레거시 코드 호출"""
        return self.legacy_manager.create_user_old_way(
            username=user_data['username'],
            email=user_data['email'],
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', '')
        )

# API는 새로운 인터페이스 사용
@api.post("/users", response=UserSchema)
def create_user(request, user_data: UserCreateSchema):
    """어댑터를 통해 레거시 코드 사용"""
    adapter = UserServiceAdapter()
    user = adapter.create_user(user_data.dict())
    return user
```

### 기술 부채 관리

```python
# TODO 주석을 구조화하여 기술 부채 관리
class UserService:
    def create_user(self, user_data: dict) -> User:
        """
        사용자를 생성합니다.
        
        TODO: 다음 버전에서 개선할 점들
        - [ ] 이메일 발송을 비동기로 처리 (Issue #123)
        - [ ] 사용자 생성 이벤트를 큐로 처리 (Issue #124)
        - [ ] 프로필 이미지 기본값 설정 로직 개선 (Issue #125)
        
        FIXME: 임시 해결책들
        - 현재 이메일 발송 실패 시 로그만 남김 (운영팀 요청으로 임시)
        - 사용자명 유효성 검증이 클라이언트와 중복됨
        
        NOTE: 비즈니스 규칙
        - 사용자명은 3-30자, 영숫자만 허용
        - 이메일은 회사 도메인만 허용 (@company.com)
        """
        self._validate_business_rules(user_data)
        
        user = UserRepository.create(user_data)
        
        # HACK: 임시로 동기 처리 (비동기 처리 준비 중)
        try:
            EmailService.send_welcome_email(user)
        except Exception as e:
            # TODO: 큐를 사용한 재시도 로직 구현
            logger.warning(f"Welcome email failed: {e}")
        
        return user
```

## 🎯 마무리

Django Ninja에서 클린 코드를 작성하는 것은 단순히 "예쁜 코드"를 만드는 것이 아닙니다. 장기적으로 유지보수 가능하고, 확장 가능하며, 팀 전체가 이해할 수 있는 시스템을 구축하는 것입니다.

### 핵심 원칙 요약

1. **단일 책임**: 각 함수와 클래스는 하나의 명확한 목적을 가져야 합니다
2. **의존성 분리**: 비즈니스 로직을 프레임워크나 외부 라이브러리로부터 분리합니다
3. **명확한 인터페이스**: API 응답과 에러 처리를 표준화합니다
4. **테스트 가능성**: 의존성 주입과 모킹을 활용해 테스트하기 쉬운 코드를 작성합니다
5. **점진적 개선**: 완벽한 코드를 한 번에 만들려 하지 말고 지속적으로 리팩토링합니다

### 실무 적용 가이드

- **작은 프로젝트**: 기본 원칙(의미 있는 이름, 함수 분리)부터 시작
- **중간 규모**: 서비스 레이어와 예외 처리 체계 도입
- **대규모 프로젝트**: DI 컨테이너, 이벤트 시스템, 모니터링까지 구축

클린 코드는 하루아침에 만들어지지 않습니다. 지속적인 리팩토링과 팀 전체의 공감대 형성이 필요합니다. 하지만 일단 이러한 패턴이 자리잡으면, 새로운 기능 개발과 버그 수정이 훨씬 수월해집니다.

코드는 컴퓨터가 아닌 사람이 읽는 것입니다. 6개월 후의 자신과 동료들을 위해 오늘부터 클린 코드를 실천해보세요.

## 📚 참고 자료

- [Clean Code by Robert C. Martin](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882)
- [Django Ninja 공식 문서](https://django-ninja.dev/)
- [SOLID 원칙](https://en.wikipedia.org/wiki/SOLID)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)

---

*클린 코드 작성에 대한 여러분만의 노하우나 경험이 있다면 댓글로 공유해주세요!*
