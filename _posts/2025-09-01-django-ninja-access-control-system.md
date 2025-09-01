---
layout: post
title: "Django-Ninja로 구축하는 현대적 접근제어 시스템: JWT 인증부터 RBAC까지"
date: 2025-09-01 10:00:00 +0900
categories: [Django, Python, API, Security]
tags: [Django-Ninja, JWT, RBAC, Authentication, Authorization, API, Security, Access Control, FastAPI-style]
---

Django-Ninja는 FastAPI에서 영감을 받아 만들어진 Django용 고성능 웹 API 프레임워크입니다. 이 글에서는 Django-Ninja를 활용하여 JWT 인증과 역할 기반 접근제어(RBAC)를 구현하는 현대적인 접근제어 시스템을 구축해보겠습니다.

## 🚀 Django-Ninja 소개

Django-Ninja는 다음과 같은 특징을 가집니다:
- **FastAPI-style** 문법으로 직관적인 API 개발
- **자동 OpenAPI/Swagger 문서화**
- **Pydantic 기반 데이터 검증**
- **높은 성능**과 타입 힌팅 지원

## 📋 프로젝트 설정

### 1. 패키지 설치

```bash
pip install django-ninja
pip install PyJWT
pip install python-decouple
pip install django-cors-headers
```

### 2. Django 설정

**settings.py**
```python
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
    'accounts',  # 사용자 관리
    'access_control',  # 접근제어 시스템
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

# JWT 설정
JWT_SECRET_KEY = config('JWT_SECRET_KEY', default='your-secret-key')
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

# CORS 설정
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

## 🏗️ 데이터 모델 설계

### 1. 사용자 확장 모델

**accounts/models.py**
```python
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
```

### 2. 역할 기반 접근제어 모델

**access_control/models.py**
```python
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Role(models.Model):
    """역할 모델"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Permission(models.Model):
    """권한 모델"""
    name = models.CharField(max_length=100, unique=True)
    codename = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    resource = models.CharField(max_length=50)  # user, project, document 등
    action = models.CharField(max_length=20)    # create, read, update, delete

    def __str__(self):
        return f"{self.resource}:{self.action}"

class RolePermission(models.Model):
    """역할-권한 관계"""
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('role', 'permission')

class UserRole(models.Model):
    """사용자-역할 관계"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    granted_by = models.ForeignKey(
        User, 
        related_name='granted_roles', 
        on_delete=models.SET_NULL, 
        null=True
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'role')

class AccessLog(models.Model):
    """접근 로그"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    resource = models.CharField(max_length=100)
    action = models.CharField(max_length=50)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    success = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.resource}:{self.action} - {self.success}"
```

## 🔐 JWT 인증 시스템

### 1. JWT 유틸리티

**utils/jwt_utils.py**
```python
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

def generate_tokens(user):
    """액세스 토큰과 리프레시 토큰 생성"""
    
    # 액세스 토큰
    access_payload = {
        'user_id': user.id,
        'email': user.email,
        'exp': datetime.utcnow() + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        ),
        'iat': datetime.utcnow(),
        'type': 'access'
    }
    
    # 리프레시 토큰
    refresh_payload = {
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        ),
        'iat': datetime.utcnow(),
        'type': 'refresh'
    }
    
    access_token = jwt.encode(
        access_payload, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    refresh_token = jwt.encode(
        refresh_payload, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

def decode_token(token):
    """토큰 디코딩 및 검증"""
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")

def get_user_from_token(token):
    """토큰에서 사용자 객체 추출"""
    try:
        payload = decode_token(token)
        user = User.objects.get(id=payload['user_id'])
        return user
    except (ValueError, User.DoesNotExist):
        return None
```

### 2. 인증 클래스

**utils/auth.py**
```python
from ninja.security import HttpBearer
from django.contrib.auth import get_user_model
from .jwt_utils import get_user_from_token

User = get_user_model()

class JWTAuth(HttpBearer):
    def authenticate(self, request, token):
        user = get_user_from_token(token)
        if user and user.is_active:
            return user
        return None

# 전역 JWT 인증 인스턴스
jwt_auth = JWTAuth()
```

## 🔒 권한 체크 시스템

### 1. 권한 체크 데코레이터

**utils/permissions.py**
```python
from functools import wraps
from ninja.errors import HttpError
from access_control.models import UserRole, RolePermission

def require_permission(resource, action):
    """권한 체크 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.auth
            if not user:
                raise HttpError(401, "Authentication required")
            
            if user.is_superuser:
                return func(request, *args, **kwargs)
            
            # 사용자 역할 확인
            user_roles = UserRole.objects.filter(
                user=user, 
                role__is_active=True
            ).select_related('role')
            
            # 권한 체크
            has_permission = False
            for user_role in user_roles:
                role_permissions = RolePermission.objects.filter(
                    role=user_role.role,
                    permission__resource=resource,
                    permission__action=action
                )
                if role_permissions.exists():
                    has_permission = True
                    break
            
            if not has_permission:
                raise HttpError(403, f"Permission denied: {resource}:{action}")
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

def get_user_permissions(user):
    """사용자의 모든 권한 조회"""
    if user.is_superuser:
        return ['*:*']  # 슈퍼유저는 모든 권한
    
    user_roles = UserRole.objects.filter(
        user=user, 
        role__is_active=True
    ).select_related('role')
    
    permissions = set()
    for user_role in user_roles:
        role_permissions = RolePermission.objects.filter(
            role=user_role.role
        ).select_related('permission')
        
        for rp in role_permissions:
            permissions.add(f"{rp.permission.resource}:{rp.permission.action}")
    
    return list(permissions)
```

## 🌐 API 엔드포인트 구현

### 1. Pydantic 스키마

**schemas.py**
```python
from ninja import Schema
from typing import Optional, List
from datetime import datetime

# 인증 관련
class LoginSchema(Schema):
    email: str
    password: str

class TokenResponse(Schema):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int

class RefreshTokenSchema(Schema):
    refresh_token: str

# 사용자 관련
class UserSchema(Schema):
    id: int
    email: str
    username: str
    department: str
    is_active: bool
    created_at: datetime

class UserCreateSchema(Schema):
    email: str
    username: str
    password: str
    department: Optional[str] = None

# 역할/권한 관련
class RoleSchema(Schema):
    id: int
    name: str
    description: str
    is_active: bool

class PermissionSchema(Schema):
    id: int
    name: str
    codename: str
    resource: str
    action: str

class UserRoleAssignSchema(Schema):
    user_id: int
    role_id: int
    expires_at: Optional[datetime] = None
```

### 2. 인증 API

**api/auth.py**
```python
from ninja import Router
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from utils.jwt_utils import generate_tokens, decode_token
from utils.auth import jwt_auth
from schemas import LoginSchema, TokenResponse, RefreshTokenSchema
from ninja.errors import HttpError

User = get_user_model()
auth_router = Router(tags=["Authentication"])

@auth_router.post("/login", response=TokenResponse)
def login(request, credentials: LoginSchema):
    """사용자 로그인"""
    user = authenticate(
        request=request,
        username=credentials.email,
        password=credentials.password
    )
    
    if not user:
        raise HttpError(401, "Invalid credentials")
    
    if not user.is_active:
        raise HttpError(401, "Account is disabled")
    
    tokens = generate_tokens(user)
    return tokens

@auth_router.post("/refresh", response=TokenResponse)
def refresh_token(request, token_data: RefreshTokenSchema):
    """토큰 갱신"""
    try:
        payload = decode_token(token_data.refresh_token)
        
        if payload.get('type') != 'refresh':
            raise HttpError(401, "Invalid token type")
        
        user = User.objects.get(id=payload['user_id'])
        if not user.is_active:
            raise HttpError(401, "Account is disabled")
        
        tokens = generate_tokens(user)
        return tokens
        
    except (ValueError, User.DoesNotExist):
        raise HttpError(401, "Invalid refresh token")

@auth_router.post("/logout")
def logout(request):
    """로그아웃 (클라이언트 측에서 토큰 제거)"""
    return {"message": "Successfully logged out"}

@auth_router.get("/me", auth=jwt_auth)
def get_current_user(request):
    """현재 사용자 정보"""
    from utils.permissions import get_user_permissions
    
    user = request.auth
    permissions = get_user_permissions(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "department": user.department,
        "permissions": permissions
    }
```

### 3. 사용자 관리 API

**api/users.py**
```python
from ninja import Router
from django.contrib.auth import get_user_model
from utils.auth import jwt_auth
from utils.permissions import require_permission
from schemas import UserSchema, UserCreateSchema
from typing import List
from ninja.errors import HttpError

User = get_user_model()
users_router = Router(tags=["Users"], auth=jwt_auth)

@users_router.get("/", response=List[UserSchema])
@require_permission("user", "read")
def list_users(request):
    """사용자 목록 조회"""
    users = User.objects.all()
    return users

@users_router.post("/", response=UserSchema)
@require_permission("user", "create")
def create_user(request, user_data: UserCreateSchema):
    """새 사용자 생성"""
    if User.objects.filter(email=user_data.email).exists():
        raise HttpError(400, "Email already exists")
    
    user = User.objects.create_user(
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        department=user_data.department or ""
    )
    return user

@users_router.get("/{user_id}", response=UserSchema)
@require_permission("user", "read")
def get_user(request, user_id: int):
    """특정 사용자 조회"""
    try:
        user = User.objects.get(id=user_id)
        return user
    except User.DoesNotExist:
        raise HttpError(404, "User not found")

@users_router.put("/{user_id}", response=UserSchema)
@require_permission("user", "update")
def update_user(request, user_id: int, user_data: UserCreateSchema):
    """사용자 정보 수정"""
    try:
        user = User.objects.get(id=user_id)
        user.email = user_data.email
        user.username = user_data.username
        user.department = user_data.department or ""
        user.save()
        return user
    except User.DoesNotExist:
        raise HttpError(404, "User not found")

@users_router.delete("/{user_id}")
@require_permission("user", "delete")
def delete_user(request, user_id: int):
    """사용자 삭제"""
    try:
        user = User.objects.get(id=user_id)
        user.delete()
        return {"message": "User deleted successfully"}
    except User.DoesNotExist:
        raise HttpError(404, "User not found")
```

### 4. 역할/권한 관리 API

**api/access_control.py**
```python
from ninja import Router
from access_control.models import Role, Permission, UserRole, RolePermission
from utils.auth import jwt_auth
from utils.permissions import require_permission
from schemas import RoleSchema, PermissionSchema, UserRoleAssignSchema
from typing import List
from ninja.errors import HttpError

access_router = Router(tags=["Access Control"], auth=jwt_auth)

# 역할 관리
@access_router.get("/roles", response=List[RoleSchema])
@require_permission("role", "read")
def list_roles(request):
    """역할 목록 조회"""
    return Role.objects.filter(is_active=True)

@access_router.post("/roles", response=RoleSchema)
@require_permission("role", "create")
def create_role(request, role_data: RoleSchema):
    """새 역할 생성"""
    role = Role.objects.create(
        name=role_data.name,
        description=role_data.description
    )
    return role

# 권한 관리
@access_router.get("/permissions", response=List[PermissionSchema])
@require_permission("permission", "read")
def list_permissions(request):
    """권한 목록 조회"""
    return Permission.objects.all()

# 사용자 역할 할당
@access_router.post("/assign-role")
@require_permission("user_role", "create")
def assign_role_to_user(request, assignment: UserRoleAssignSchema):
    """사용자에게 역할 할당"""
    try:
        user_role, created = UserRole.objects.get_or_create(
            user_id=assignment.user_id,
            role_id=assignment.role_id,
            defaults={
                'granted_by': request.auth,
                'expires_at': assignment.expires_at
            }
        )
        
        if not created:
            raise HttpError(400, "Role already assigned to user")
        
        return {"message": "Role assigned successfully"}
    except Exception as e:
        raise HttpError(400, str(e))

@access_router.delete("/revoke-role/{user_id}/{role_id}")
@require_permission("user_role", "delete")
def revoke_role_from_user(request, user_id: int, role_id: int):
    """사용자 역할 해제"""
    try:
        user_role = UserRole.objects.get(user_id=user_id, role_id=role_id)
        user_role.delete()
        return {"message": "Role revoked successfully"}
    except UserRole.DoesNotExist:
        raise HttpError(404, "User role assignment not found")
```

## 📊 메인 API 설정

**main.py**
```python
from ninja import NinjaAPI
from api.auth import auth_router
from api.users import users_router
from api.access_control import access_router

api = NinjaAPI(
    title="Access Control System API",
    description="Django-Ninja 기반 접근제어 시스템",
    version="1.0.0"
)

# 라우터 등록
api.add_router("/auth", auth_router)
api.add_router("/users", users_router)
api.add_router("/access", access_router)

@api.get("/health")
def health_check(request):
    return {"status": "healthy", "message": "Access Control System is running"}
```

**urls.py**
```python
from django.contrib import admin
from django.urls import path
from main import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
```

## 🧪 테스트 코드

**tests/test_auth.py**
```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from ninja.testing import TestClient
from main import api

User = get_user_model()

class AuthTestCase(TestCase):
    def setUp(self):
        self.client = TestClient(api)
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

    def test_login_success(self):
        response = self.client.post('/auth/login', {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('access_token', data)
        self.assertIn('refresh_token', data)

    def test_login_invalid_credentials(self):
        response = self.client.post('/auth/login', {
            'email': 'test@example.com',
            'password': 'wrongpass'
        })
        
        self.assertEqual(response.status_code, 401)

    def test_protected_endpoint_without_token(self):
        response = self.client.get('/auth/me')
        self.assertEqual(response.status_code, 401)

    def test_protected_endpoint_with_token(self):
        # 로그인하여 토큰 획득
        login_response = self.client.post('/auth/login', {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        token = login_response.json()['access_token']
        
        # 토큰으로 보호된 엔드포인트 접근
        response = self.client.get('/auth/me', 
            headers={'Authorization': f'Bearer {token}'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['email'], 'test@example.com')
```

## 🚀 사용법 및 실행

### 1. 마이그레이션 실행

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 2. 초기 데이터 설정

**management/commands/setup_permissions.py**
```python
from django.core.management.base import BaseCommand
from access_control.models import Role, Permission, RolePermission

class Command(BaseCommand):
    help = 'Setup initial roles and permissions'

    def handle(self, *args, **options):
        # 권한 생성
        permissions_data = [
            ('user', 'create', 'Create users'),
            ('user', 'read', 'Read users'),
            ('user', 'update', 'Update users'),
            ('user', 'delete', 'Delete users'),
            ('role', 'create', 'Create roles'),
            ('role', 'read', 'Read roles'),
            ('role', 'update', 'Update roles'),
            ('role', 'delete', 'Delete roles'),
        ]
        
        for resource, action, description in permissions_data:
            Permission.objects.get_or_create(
                resource=resource,
                action=action,
                defaults={
                    'name': f'{resource.title()} {action.title()}',
                    'codename': f'{action}_{resource}',
                    'description': description
                }
            )
        
        # 역할 생성
        admin_role, _ = Role.objects.get_or_create(
            name='Admin',
            defaults={'description': 'System administrator'}
        )
        
        user_role, _ = Role.objects.get_or_create(
            name='User',
            defaults={'description': 'Regular user'}
        )
        
        # 관리자 역할에 모든 권한 할당
        for permission in Permission.objects.all():
            RolePermission.objects.get_or_create(
                role=admin_role,
                permission=permission
            )
        
        # 일반 사용자는 읽기 권한만
        read_permissions = Permission.objects.filter(action='read')
        for permission in read_permissions:
            RolePermission.objects.get_or_create(
                role=user_role,
                permission=permission
            )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully setup permissions')
        )
```

### 3. 서버 실행

```bash
python manage.py setup_permissions
python manage.py runserver
```

## 📖 API 문서 확인

Django-Ninja는 자동으로 OpenAPI/Swagger 문서를 생성합니다:

- **Swagger UI**: http://127.0.0.1:8000/api/docs
- **ReDoc**: http://127.0.0.1:8000/api/redoc
- **OpenAPI 스키마**: http://127.0.0.1:8000/api/openapi.json

## 🔍 실제 사용 예시

### 1. 프론트엔드에서 API 호출

```javascript
// 로그인
const login = async (email, password) => {
    const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    return data;
};

// 인증이 필요한 API 호출
const fetchUsers = async () => {
    const token = localStorage.getItem('access_token');
    const response = await fetch('/api/users/', {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });
    
    return response.json();
};
```

### 2. 권한 확인 예시

```python
# 특정 사용자의 권한 확인
from utils.permissions import get_user_permissions

user = User.objects.get(email='admin@example.com')
permissions = get_user_permissions(user)
print(permissions)  # ['user:create', 'user:read', 'user:update', 'user:delete', ...]
```

## 🔧 고급 기능

### 1. 동적 권한 체크

```python
@users_router.get("/profile/{user_id}")
@require_permission("user", "read")
def get_user_profile(request, user_id: int):
    """사용자는 자신의 프로필만 조회 가능"""
    current_user = request.auth
    
    # 관리자가 아닌 경우 본인 정보만 조회 가능
    if not current_user.is_superuser and current_user.id != user_id:
        raise HttpError(403, "Can only access your own profile")
    
    user = User.objects.get(id=user_id)
    return user
```

### 2. 접근 로그 기록

```python
def log_access(user, resource, action, request, success=True):
    """접근 로그 기록"""
    from access_control.models import AccessLog
    
    AccessLog.objects.create(
        user=user,
        resource=resource,
        action=action,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        success=success
    )

# 데코레이터에 로그 기능 추가
def require_permission_with_log(resource, action):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.auth
            try:
                # 권한 체크 로직...
                result = func(request, *args, **kwargs)
                log_access(user, resource, action, request, success=True)
                return result
            except HttpError as e:
                log_access(user, resource, action, request, success=False)
                raise e
        return wrapper
    return decorator
```

## 🎯 결론

Django-Ninja를 활용한 접근제어 시스템의 주요 장점:

1. **현대적인 API 개발**: FastAPI 스타일의 직관적인 문법
2. **자동 문서화**: OpenAPI/Swagger 자동 생성
3. **타입 안정성**: Pydantic 기반 데이터 검증
4. **유연한 권한 시스템**: RBAC 기반 세밀한 권한 제어
5. **확장성**: 새로운 권한과 역할을 쉽게 추가 가능

이 시스템을 기반으로 조직의 요구사항에 맞는 접근제어 시스템을 구축할 수 있습니다. Django-Ninja의 강력한 기능과 함께 보안성과 사용성을 모두 확보한 API를 개발할 수 있습니다.

**다음 포스트에서는** Django-Ninja와 React를 연동한 실시간 권한 관리 대시보드 구축에 대해 다뤄보겠습니다.
