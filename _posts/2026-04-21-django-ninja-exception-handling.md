---
title: "Django Ninja 예외처리 완벽 가이드: IntegrityError부터 커스텀 예외까지"
date: 2026-04-21 09:00:00 +0900
categories: [Django, Backend]
tags: [Django, Django-Ninja, Exception, Error-Handling, IntegrityError, API]
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-04-21-django-ninja-exception-handling.webp"
---

## 개요

Django Ninja를 사용하여 RESTful API를 구축할 때, 적절한 예외 처리는 안정적이고 사용자 친화적인 API를 만드는 핵심 요소입니다. 본 포스트에서는 Django Ninja에서 IntegrityError, ValidationError 등 자주 발생하는 예외를 처리하는 방법과 커스텀 예외 핸들러를 구현하는 실전 노하우를 소개합니다.

---

## 1. Django Ninja 예외처리 기본 구조

Django Ninja는 기본적으로 예외를 자동으로 처리하지만, 프로덕션 환경에서는 더 세밀한 제어가 필요합니다.

### 1.1. 기본 예외 응답

```python
from ninja import NinjaAPI

api = NinjaAPI()

@api.get("/users/{user_id}")
def get_user(request, user_id: int):
    user = User.objects.get(id=user_id)  # DoesNotExist 발생 가능
    return {"id": user.id, "name": user.name}
```

위 코드에서 사용자를 찾지 못하면 `DoesNotExist` 예외가 발생하고, Django Ninja는 기본적으로 500 에러를 반환합니다.

---

## 2. IntegrityError 예외처리

데이터베이스 제약조건 위반 시 발생하는 IntegrityError는 API에서 가장 자주 마주치는 예외입니다.

### 2.1. 기본 IntegrityError 처리

```python
from django.db import IntegrityError
from ninja import NinjaAPI
from ninja.responses import Response

api = NinjaAPI()

@api.post("/users")
def create_user(request, payload: UserCreateSchema):
    try:
        user = User.objects.create(
            email=payload.email,
            username=payload.username
        )
        return {"id": user.id, "email": user.email}
    except IntegrityError as e:
        return Response(
            {"error": "이미 존재하는 사용자입니다."},
            status=409
        )
```

### 2.2. 세부 IntegrityError 분석

IntegrityError의 원인을 파악하여 더 명확한 에러 메시지를 반환할 수 있습니다.

```python
from django.db import IntegrityError
import re

@api.post("/users")
def create_user(request, payload: UserCreateSchema):
    try:
        user = User.objects.create(
            email=payload.email,
            username=payload.username
        )
        return {"id": user.id, "email": user.email}
    except IntegrityError as e:
        error_message = str(e)
        
        # UNIQUE constraint 위반 감지
        if 'UNIQUE constraint' in error_message or 'unique constraint' in error_message:
            # 어떤 필드가 중복되었는지 파악
            if 'email' in error_message:
                return Response(
                    {"error": "이미 사용 중인 이메일입니다.", "field": "email"},
                    status=409
                )
            elif 'username' in error_message:
                return Response(
                    {"error": "이미 사용 중인 사용자명입니다.", "field": "username"},
                    status=409
                )
        
        # NOT NULL constraint 위반 감지
        if 'NOT NULL constraint' in error_message or 'null value' in error_message:
            return Response(
                {"error": "필수 필드가 누락되었습니다."},
                status=400
            )
        
        # FOREIGN KEY constraint 위반 감지
        if 'FOREIGN KEY constraint' in error_message or 'foreign key constraint' in error_message:
            return Response(
                {"error": "존재하지 않는 참조 데이터입니다."},
                status=400
            )
        
        # 기타 IntegrityError
        return Response(
            {"error": "데이터 무결성 오류가 발생했습니다."},
            status=400
        )
```

### 2.3. 데이터베이스별 IntegrityError 처리

```python
from django.db import IntegrityError
from django.db.utils import DatabaseError
import sys

def handle_integrity_error(e: IntegrityError) -> dict:
    """데이터베이스 종류에 따라 IntegrityError를 처리"""
    error_message = str(e).lower()
    
    # PostgreSQL
    if 'psycopg2' in sys.modules:
        if 'duplicate key' in error_message:
            # 예: duplicate key value violates unique constraint "users_email_key"
            match = re.search(r'"(\w+)"', error_message)
            if match:
                constraint = match.group(1)
                return {
                    "error": f"중복된 값입니다: {constraint}",
                    "type": "duplicate",
                    "constraint": constraint
                }
    
    # MySQL
    elif 'mysqlclient' in sys.modules or 'pymysql' in sys.modules:
        if 'duplicate entry' in error_message:
            # 예: Duplicate entry 'test@example.com' for key 'email'
            match = re.search(r"duplicate entry '(.+)' for key '(\w+)'", error_message)
            if match:
                value, field = match.groups()
                return {
                    "error": f"중복된 {field}: {value}",
                    "type": "duplicate",
                    "field": field
                }
    
    # SQLite
    elif 'sqlite3' in sys.modules:
        if 'unique constraint failed' in error_message:
            # 예: UNIQUE constraint failed: users.email
            match = re.search(r'unique constraint failed: (\w+)\.(\w+)', error_message)
            if match:
                table, field = match.groups()
                return {
                    "error": f"중복된 {field}입니다.",
                    "type": "duplicate",
                    "field": field
                }
    
    return {"error": "데이터 무결성 오류", "type": "integrity_error"}

@api.post("/users")
def create_user(request, payload: UserCreateSchema):
    try:
        user = User.objects.create(**payload.dict())
        return {"id": user.id, "email": user.email}
    except IntegrityError as e:
        error_info = handle_integrity_error(e)
        return Response(error_info, status=409)
```

---

## 3. 자주 발생하는 예외 처리

### 3.1. DoesNotExist 예외

```python
from django.core.exceptions import ObjectDoesNotExist
from ninja.errors import HttpError

@api.get("/users/{user_id}")
def get_user(request, user_id: int):
    try:
        user = User.objects.get(id=user_id)
        return {"id": user.id, "name": user.name}
    except User.DoesNotExist:
        raise HttpError(404, "사용자를 찾을 수 없습니다.")
    except ObjectDoesNotExist:
        raise HttpError(404, "데이터를 찾을 수 없습니다.")
```

### 3.2. ValidationError 예외

```python
from django.core.exceptions import ValidationError
from ninja import Schema
from typing import Optional

class UserUpdateSchema(Schema):
    email: Optional[str] = None
    age: Optional[int] = None

@api.patch("/users/{user_id}")
def update_user(request, user_id: int, payload: UserUpdateSchema):
    try:
        user = User.objects.get(id=user_id)
        
        if payload.email:
            user.email = payload.email
        if payload.age:
            if payload.age < 0 or payload.age > 150:
                raise ValidationError("나이는 0-150 사이여야 합니다.")
            user.age = payload.age
        
        user.full_clean()  # 모델 레벨 검증
        user.save()
        
        return {"id": user.id, "email": user.email}
    
    except User.DoesNotExist:
        raise HttpError(404, "사용자를 찾을 수 없습니다.")
    
    except ValidationError as e:
        # ValidationError는 딕셔너리 또는 리스트 형태
        if hasattr(e, 'message_dict'):
            return Response(
                {"error": "검증 오류", "details": e.message_dict},
                status=400
            )
        else:
            return Response(
                {"error": "검증 오류", "details": e.messages},
                status=400
            )
    
    except IntegrityError as e:
        error_info = handle_integrity_error(e)
        return Response(error_info, status=409)
```

### 3.3. PermissionDenied 예외

```python
from django.core.exceptions import PermissionDenied

@api.delete("/users/{user_id}")
def delete_user(request, user_id: int):
    try:
        user = User.objects.get(id=user_id)
        
        # 권한 체크
        if request.user.id != user_id and not request.user.is_staff:
            raise PermissionDenied("권한이 없습니다.")
        
        user.delete()
        return {"message": "사용자가 삭제되었습니다."}
    
    except User.DoesNotExist:
        raise HttpError(404, "사용자를 찾을 수 없습니다.")
    
    except PermissionDenied as e:
        raise HttpError(403, str(e))
```

---

## 4. 커스텀 예외 핸들러

### 4.1. 글로벌 예외 핸들러 등록

Django Ninja는 `add_exception_handler`를 통해 전역 예외 핸들러를 등록할 수 있습니다.

```python
from ninja import NinjaAPI
from django.db import IntegrityError
from django.core.exceptions import ValidationError, PermissionDenied, ObjectDoesNotExist
import logging

api = NinjaAPI()
logger = logging.getLogger(__name__)

# IntegrityError 핸들러
@api.exception_handler(IntegrityError)
def handle_integrity_error(request, exc):
    logger.error(f"IntegrityError: {exc}", exc_info=True)
    error_info = handle_integrity_error(exc)
    return api.create_response(
        request,
        error_info,
        status=409
    )

# ValidationError 핸들러
@api.exception_handler(ValidationError)
def handle_validation_error(request, exc):
    logger.warning(f"ValidationError: {exc}")
    if hasattr(exc, 'message_dict'):
        details = exc.message_dict
    else:
        details = {"non_field_errors": exc.messages}
    
    return api.create_response(
        request,
        {"error": "검증 오류", "details": details},
        status=400
    )

# DoesNotExist 핸들러
@api.exception_handler(ObjectDoesNotExist)
def handle_does_not_exist(request, exc):
    logger.info(f"ObjectDoesNotExist: {exc}")
    return api.create_response(
        request,
        {"error": "요청한 리소스를 찾을 수 없습니다."},
        status=404
    )

# PermissionDenied 핸들러
@api.exception_handler(PermissionDenied)
def handle_permission_denied(request, exc):
    logger.warning(f"PermissionDenied: {exc}")
    return api.create_response(
        request,
        {"error": "권한이 없습니다.", "message": str(exc)},
        status=403
    )

# 일반 Exception 핸들러 (catch-all)
@api.exception_handler(Exception)
def handle_generic_exception(request, exc):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return api.create_response(
        request,
        {"error": "서버 오류가 발생했습니다."},
        status=500
    )
```

### 4.2. 커스텀 예외 클래스 정의

```python
from ninja.errors import HttpError

class DuplicateResourceError(HttpError):
    def __init__(self, message: str = "중복된 리소스입니다.", field: str = None):
        super().__init__(409, message)
        self.field = field

class ResourceNotFoundError(HttpError):
    def __init__(self, resource: str = "리소스"):
        super().__init__(404, f"{resource}를 찾을 수 없습니다.")

class BusinessLogicError(HttpError):
    def __init__(self, message: str):
        super().__init__(400, message)

# 사용 예시
@api.post("/users")
def create_user(request, payload: UserCreateSchema):
    try:
        # 이메일 중복 체크
        if User.objects.filter(email=payload.email).exists():
            raise DuplicateResourceError("이미 사용 중인 이메일입니다.", field="email")
        
        user = User.objects.create(**payload.dict())
        return {"id": user.id, "email": user.email}
    
    except IntegrityError as e:
        # IntegrityError도 커스텀 예외로 변환
        error_info = handle_integrity_error(e)
        if error_info.get("type") == "duplicate":
            raise DuplicateResourceError(
                error_info["error"],
                field=error_info.get("field")
            )
        raise BusinessLogicError(error_info["error"])
```

### 4.3. 데코레이터 기반 예외 처리

```python
from functools import wraps
from ninja.responses import Response
import logging

logger = logging.getLogger(__name__)

def handle_db_exceptions(func):
    """데이터베이스 예외를 자동으로 처리하는 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except IntegrityError as e:
            logger.error(f"IntegrityError in {func.__name__}: {e}")
            error_info = handle_integrity_error(e)
            return Response(error_info, status=409)
        except ObjectDoesNotExist as e:
            logger.info(f"ObjectDoesNotExist in {func.__name__}: {e}")
            return Response(
                {"error": "요청한 리소스를 찾을 수 없습니다."},
                status=404
            )
        except ValidationError as e:
            logger.warning(f"ValidationError in {func.__name__}: {e}")
            details = e.message_dict if hasattr(e, 'message_dict') else {"non_field_errors": e.messages}
            return Response(
                {"error": "검증 오류", "details": details},
                status=400
            )
    return wrapper

# 사용 예시
@api.post("/users")
@handle_db_exceptions
def create_user(request, payload: UserCreateSchema):
    user = User.objects.create(**payload.dict())
    return {"id": user.id, "email": user.email}

@api.get("/users/{user_id}")
@handle_db_exceptions
def get_user(request, user_id: int):
    user = User.objects.get(id=user_id)
    return {"id": user.id, "name": user.name}
```

---

## 5. 트랜잭션과 예외 처리

데이터베이스 트랜잭션 내에서 예외가 발생하면 자동으로 롤백됩니다.

### 5.1. 트랜잭션 기본 사용

```python
from django.db import transaction

@api.post("/orders")
def create_order(request, payload: OrderCreateSchema):
    try:
        with transaction.atomic():
            # 주문 생성
            order = Order.objects.create(
                user_id=payload.user_id,
                total_amount=payload.total_amount
            )
            
            # 주문 항목 생성
            for item in payload.items:
                OrderItem.objects.create(
                    order=order,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price=item.price
                )
            
            # 재고 감소
            for item in payload.items:
                product = Product.objects.select_for_update().get(id=item.product_id)
                if product.stock < item.quantity:
                    raise BusinessLogicError(f"{product.name}의 재고가 부족합니다.")
                product.stock -= item.quantity
                product.save()
            
            return {"order_id": order.id, "message": "주문이 완료되었습니다."}
    
    except Product.DoesNotExist:
        raise HttpError(404, "상품을 찾을 수 없습니다.")
    
    except BusinessLogicError as e:
        raise HttpError(400, str(e))
    
    except IntegrityError as e:
        logger.error(f"주문 생성 실패: {e}")
        return Response(
            {"error": "주문 처리 중 오류가 발생했습니다."},
            status=500
        )
```

### 5.2. 중첩 트랜잭션과 예외

```python
from django.db import transaction

@api.post("/complex-operation")
def complex_operation(request, payload: ComplexSchema):
    try:
        with transaction.atomic():
            # 외부 트랜잭션
            user = User.objects.create(email=payload.email)
            
            try:
                # 내부 세이브포인트
                with transaction.atomic():
                    profile = Profile.objects.create(
                        user=user,
                        bio=payload.bio
                    )
            except IntegrityError:
                # 프로필 생성 실패해도 사용자는 생성됨
                logger.warning(f"프로필 생성 실패, 사용자만 생성: {user.id}")
            
            # 필수 작업
            Membership.objects.create(user=user, plan="free")
            
            return {"user_id": user.id, "message": "작업 완료"}
    
    except IntegrityError as e:
        # 외부 트랜잭션 실패 시 모두 롤백
        error_info = handle_integrity_error(e)
        return Response(error_info, status=409)
```

---

## 6. 실전 예제: 완전한 CRUD API

```python
from ninja import NinjaAPI, Schema, Field
from ninja.errors import HttpError
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from typing import List, Optional
import logging

api = NinjaAPI()
logger = logging.getLogger(__name__)

# 스키마 정의
class UserCreateSchema(Schema):
    email: str = Field(..., min_length=3, max_length=255)
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)

class UserUpdateSchema(Schema):
    email: Optional[str] = Field(None, min_length=3, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=50)

class UserResponseSchema(Schema):
    id: int
    email: str
    username: str
    created_at: datetime

# CREATE
@api.post("/users", response=UserResponseSchema)
def create_user(request, payload: UserCreateSchema):
    """사용자 생성"""
    try:
        # 중복 체크 (IntegrityError 전에 명시적으로 체크)
        if User.objects.filter(email=payload.email).exists():
            raise HttpError(409, "이미 사용 중인 이메일입니다.")
        
        if User.objects.filter(username=payload.username).exists():
            raise HttpError(409, "이미 사용 중인 사용자명입니다.")
        
        with transaction.atomic():
            user = User.objects.create_user(
                email=payload.email,
                username=payload.username,
                password=payload.password
            )
            
            # 프로필 자동 생성
            Profile.objects.create(user=user)
            
            logger.info(f"새 사용자 생성: {user.id} - {user.email}")
            return user
    
    except IntegrityError as e:
        logger.error(f"사용자 생성 실패: {e}")
        error_info = handle_integrity_error(e)
        raise HttpError(409, error_info["error"])
    
    except ValidationError as e:
        details = e.message_dict if hasattr(e, 'message_dict') else {"error": e.messages}
        raise HttpError(400, details)

# READ (단일)
@api.get("/users/{user_id}", response=UserResponseSchema)
def get_user(request, user_id: int):
    """사용자 조회"""
    try:
        user = User.objects.select_related('profile').get(id=user_id)
        return user
    except User.DoesNotExist:
        raise HttpError(404, "사용자를 찾을 수 없습니다.")

# READ (목록)
@api.get("/users", response=List[UserResponseSchema])
def list_users(request, skip: int = 0, limit: int = 20):
    """사용자 목록 조회"""
    if limit > 100:
        raise HttpError(400, "limit은 100 이하여야 합니다.")
    
    users = User.objects.all()[skip:skip+limit]
    return users

# UPDATE
@api.patch("/users/{user_id}", response=UserResponseSchema)
def update_user(request, user_id: int, payload: UserUpdateSchema):
    """사용자 수정"""
    try:
        user = User.objects.get(id=user_id)
        
        # 권한 체크
        if request.user.id != user_id and not request.user.is_staff:
            raise HttpError(403, "권한이 없습니다.")
        
        # 중복 체크
        if payload.email and payload.email != user.email:
            if User.objects.filter(email=payload.email).exists():
                raise HttpError(409, "이미 사용 중인 이메일입니다.")
            user.email = payload.email
        
        if payload.username and payload.username != user.username:
            if User.objects.filter(username=payload.username).exists():
                raise HttpError(409, "이미 사용 중인 사용자명입니다.")
            user.username = payload.username
        
        user.full_clean()
        user.save()
        
        logger.info(f"사용자 수정: {user.id}")
        return user
    
    except User.DoesNotExist:
        raise HttpError(404, "사용자를 찾을 수 없습니다.")
    
    except ValidationError as e:
        details = e.message_dict if hasattr(e, 'message_dict') else {"error": e.messages}
        raise HttpError(400, details)
    
    except IntegrityError as e:
        error_info = handle_integrity_error(e)
        raise HttpError(409, error_info["error"])

# DELETE
@api.delete("/users/{user_id}")
def delete_user(request, user_id: int):
    """사용자 삭제"""
    try:
        user = User.objects.get(id=user_id)
        
        # 권한 체크
        if request.user.id != user_id and not request.user.is_staff:
            raise HttpError(403, "권한이 없습니다.")
        
        with transaction.atomic():
            user.delete()
        
        logger.info(f"사용자 삭제: {user_id}")
        return {"message": "사용자가 삭제되었습니다."}
    
    except User.DoesNotExist:
        raise HttpError(404, "사용자를 찾을 수 없습니다.")
```

---

## 7. 예외 로깅 및 모니터링

### 7.1. 구조화된 로깅

```python
import logging
import json
from datetime import datetime

class APIExceptionLogger:
    def __init__(self):
        self.logger = logging.getLogger('api.exceptions')
    
    def log_exception(self, request, exc, status_code):
        """구조화된 예외 로그"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "status_code": status_code,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "path": request.path,
            "method": request.method,
            "user_id": getattr(request.user, 'id', None),
            "ip_address": request.META.get('REMOTE_ADDR'),
            "user_agent": request.META.get('HTTP_USER_AGENT'),
        }
        
        if status_code >= 500:
            self.logger.error(json.dumps(log_data), exc_info=True)
        elif status_code >= 400:
            self.logger.warning(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))

exception_logger = APIExceptionLogger()

# 전역 핸들러에 로깅 추가
@api.exception_handler(Exception)
def handle_exception_with_logging(request, exc):
    status_code = getattr(exc, 'status_code', 500)
    exception_logger.log_exception(request, exc, status_code)
    
    return api.create_response(
        request,
        {"error": "서버 오류가 발생했습니다."},
        status=status_code
    )
```

### 7.2. Sentry 연동

```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True
)

@api.exception_handler(Exception)
def handle_exception_with_sentry(request, exc):
    # Sentry에 추가 컨텍스트 전달
    with sentry_sdk.push_scope() as scope:
        scope.set_context("request", {
            "path": request.path,
            "method": request.method,
            "user_id": getattr(request.user, 'id', None),
        })
        sentry_sdk.capture_exception(exc)
    
    return api.create_response(
        request,
        {"error": "서버 오류가 발생했습니다."},
        status=500
    )
```

---

## 8. 테스트

### 8.1. 예외 처리 유닛 테스트

```python
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
import json

User = get_user_model()

class UserAPIExceptionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
    
    def test_create_user_duplicate_email(self):
        """이메일 중복 시 409 에러"""
        data = {
            'email': 'test@example.com',
            'username': 'newuser',
            'password': 'testpass123'
        }
        response = self.client.post(
            '/api/users',
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn('이메일', response.json()['error'])
    
    def test_get_nonexistent_user(self):
        """존재하지 않는 사용자 조회 시 404"""
        response = self.client.get('/api/users/99999')
        self.assertEqual(response.status_code, 404)
    
    def test_update_user_without_permission(self):
        """권한 없이 수정 시 403"""
        other_user = User.objects.create_user(
            email='other@example.com',
            username='otheruser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        data = {'email': 'newemail@example.com'}
        response = self.client.patch(
            f'/api/users/{other_user.id}',
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)
    
    def test_integrity_error_handling(self):
        """IntegrityError 처리 확인"""
        from django.db import connection
        from django.db.utils import IntegrityError
        
        with self.assertRaises(IntegrityError):
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO auth_user (email, username) VALUES (%s, %s)",
                    ['test@example.com', 'testuser']
                )
```

---

## 9. 모범 사례 및 팁

### 9.1. 예외 처리 모범 사례

1. **구체적인 예외부터 처리**: 일반적인 Exception은 마지막에
2. **명확한 에러 메시지**: 사용자가 이해하고 대응할 수 있는 메시지
3. **적절한 HTTP 상태 코드 사용**
4. **민감한 정보 노출 방지**: 스택 트레이스, DB 상세 정보 등
5. **일관된 에러 응답 형식**

```python
# 표준 에러 응답 형식
{
    "error": "사용자 친화적인 메시지",
    "code": "DUPLICATE_EMAIL",  # 선택적: 에러 코드
    "details": {  # 선택적: 추가 정보
        "field": "email",
        "value": "test@example.com"
    }
}
```

### 9.2. 피해야 할 안티패턴

```python
# ❌ 나쁜 예: 모든 예외를 무시
@api.post("/users")
def create_user(request, payload: UserCreateSchema):
    try:
        user = User.objects.create(**payload.dict())
        return user
    except:  # 너무 광범위
        return {"error": "오류"}  # 정보 부족

# ❌ 나쁜 예: 민감한 정보 노출
except IntegrityError as e:
    return Response({"error": str(e)}, status=500)  # DB 상세 정보 노출

# ✅ 좋은 예
@api.post("/users")
def create_user(request, payload: UserCreateSchema):
    try:
        user = User.objects.create(**payload.dict())
        return user
    except IntegrityError as e:
        logger.error(f"User creation failed: {e}", exc_info=True)
        error_info = handle_integrity_error(e)
        return Response(error_info, status=409)
    except ValidationError as e:
        details = e.message_dict if hasattr(e, 'message_dict') else e.messages
        return Response({"error": "검증 오류", "details": details}, status=400)
```

---

## 10. 결론

Django Ninja에서의 효과적인 예외 처리는 안정적이고 유지보수 가능한 API를 만드는 핵심입니다. 본 가이드에서 다룬 내용을 정리하면:

- **IntegrityError**: 데이터베이스별 특성을 고려한 세밀한 처리
- **전역 예외 핸들러**: 일관된 에러 응답과 중복 코드 제거
- **커스텀 예외**: 비즈니스 로직에 맞는 명확한 예외 계층
- **로깅 및 모니터링**: 운영 환경에서의 빠른 문제 파악
- **트랜잭션**: 데이터 일관성 보장

이러한 패턴들을 적용하면 사용자 경험을 개선하고, 디버깅 시간을 단축하며, 안정적인 API 서비스를 제공할 수 있습니다.

---

**관련 포스트:**
- Django Ninja 시작하기
- Django REST API 성능 최적화
- Django 데이터베이스 트랜잭션 완벽 가이드

**참고 자료:**
- [Django Ninja 공식 문서](https://django-ninja.rest-framework.com/)
- [Django 예외 처리 가이드](https://docs.djangoproject.com/en/stable/ref/exceptions/)
