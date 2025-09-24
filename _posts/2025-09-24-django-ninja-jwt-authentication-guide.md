---
layout: post
title: "Django Ninja JWT 인증 구현 가이드: 현대적 API 보안의 핵심"
date: 2025-09-24 14:00:00 +0900
categories: [Web Development, Django]
tags: [django, django-ninja, jwt, authentication, api, security, python]
description: "Django Ninja에서 JWT 토큰 기반 인증을 구현하는 완벽 가이드. JWT 선택 이유부터 실제 구현, 보안 고려사항까지 모든 과정을 다룹니다."
author: "updaun"
image: "/assets/img/posts/2025-09-24-django-ninja-jwt-authentication-guide.webp"
---

## 개요

현대 웹 애플리케이션에서 API 보안은 필수적인 요소입니다. 특히 Django Ninja를 사용한 FastAPI 스타일의 API 개발에서 JWT(JSON Web Token) 기반 인증은 가장 널리 사용되는 방식 중 하나입니다. 이 포스트에서는 JWT를 선택하는 이유부터 Django Ninja에서의 실제 구현까지 상세히 다루겠습니다.

## 1. JWT 인증을 선택하는 이유

### 1.1 전통적인 세션 기반 인증의 한계

```python
# 전통적인 Django 세션 기반 인증
from django.contrib.auth import authenticate, login
from django.http import HttpResponse

def login_view(request):
    username = request.POST['username']
    password = request.POST['password']
    user = authenticate(request, username=username, password=password)
    
    if user is not None:
        login(request, user)  # 서버 세션에 저장
        return HttpResponse("로그인 성공")
    else:
        return HttpResponse("로그인 실패")
```

**세션 기반 인증의 문제점:**
- **서버 의존성**: 세션 데이터를 서버에 저장해야 함
- **확장성 문제**: 다중 서버 환경에서 세션 동기화 필요
- **CORS 이슈**: 크로스 도메인 요청에서 쿠키 전송 제한
- **모바일 앱 호환성**: 네이티브 앱에서 쿠키 관리 복잡

### 1.2 JWT의 장점

```python
# JWT 토큰 예시
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "user_id": 123,
    "username": "john_doe",
    "exp": 1640995200,
    "iat": 1640908800
  },
  "signature": "signature_hash"
}
```

**JWT의 핵심 장점:**

1. **Stateless (무상태성)**
   - 서버가 토큰 정보를 저장하지 않음
   - 토큰 자체에 필요한 정보 포함

2. **확장성 (Scalability)**
   - 마이크로서비스 아키텍처에 적합
   - 로드 밸런싱 환경에서 자유로운 서버 선택

3. **플랫폼 독립성**
   - 웹, 모바일, 데스크톱 앱 모두 지원
   - HTTP 헤더로 간단한 전송

4. **보안성**
   - 디지털 서명으로 변조 방지
   - 만료 시간 설정으로 보안 강화

## 2. Django Ninja JWT 구현

### 2.1 프로젝트 설정

```python
# requirements.txt
django>=4.2.0
django-ninja>=1.0.0
PyJWT>=2.8.0
python-decouple>=3.8
django-cors-headers>=4.3.0

# settings.py
import os
from decouple import config
from datetime import timedelta

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'ninja',
    'accounts',  # 사용자 앱
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
JWT_SECRET_KEY = config('JWT_SECRET_KEY', default='your-secret-key-here')
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

# CORS 설정
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React 앱
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True
```

### 2.2 JWT 유틸리티 구현

```python
# accounts/jwt_utils.py
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth.models import User
from typing import Optional, Dict, Any

class JWTManager:
    """JWT 토큰 관리 클래스"""
    
    @staticmethod
    def generate_tokens(user: User) -> Dict[str, str]:
        """액세스 토큰과 리프레시 토큰 생성"""
        now = datetime.utcnow()
        
        # 액세스 토큰 (30분)
        access_payload = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'exp': now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            'iat': now,
            'type': 'access'
        }
        
        # 리프레시 토큰 (7일)
        refresh_payload = {
            'user_id': user.id,
            'exp': now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            'iat': now,
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
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """토큰 검증 및 페이로드 반환"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def get_user_from_token(token: str) -> Optional[User]:
        """토큰에서 사용자 객체 반환"""
        payload = JWTManager.verify_token(token)
        if not payload:
            return None
        
        try:
            user = User.objects.get(id=payload['user_id'])
            return user
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def refresh_access_token(refresh_token: str) -> Optional[Dict[str, str]]:
        """리프레시 토큰으로 새 액세스 토큰 생성"""
        payload = JWTManager.verify_token(refresh_token)
        
        if not payload or payload.get('type') != 'refresh':
            return None
        
        try:
            user = User.objects.get(id=payload['user_id'])
            # 새 액세스 토큰만 생성 (리프레시 토큰은 그대로 유지)
            return {
                'access_token': JWTManager.generate_tokens(user)['access_token'],
                'token_type': 'Bearer',
                'expires_in': settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
        except User.DoesNotExist:
            return None

class TokenBlacklist:
    """토큰 블랙리스트 관리"""
    _blacklist = set()
    
    @classmethod
    def add_token(cls, token: str):
        """토큰을 블랙리스트에 추가"""
        cls._blacklist.add(token)
    
    @classmethod
    def is_blacklisted(cls, token: str) -> bool:
        """토큰이 블랙리스트에 있는지 확인"""
        return token in cls._blacklist
    
    @classmethod
    def cleanup_expired_tokens(cls):
        """만료된 토큰들을 블랙리스트에서 제거"""
        current_blacklist = cls._blacklist.copy()
        for token in current_blacklist:
            payload = JWTManager.verify_token(token)
            if not payload:  # 만료되거나 유효하지 않은 토큰
                cls._blacklist.discard(token)
```

### 2.3 Django Ninja 인증 클래스

```python
# accounts/auth.py
from ninja.security import HttpBearer
from ninja import NinjaAPI
from django.contrib.auth.models import User
from django.http import HttpRequest
from typing import Optional
from .jwt_utils import JWTManager, TokenBlacklist

class JWTAuth(HttpBearer):
    """Django Ninja JWT 인증 클래스"""
    
    def authenticate(self, request: HttpRequest, token: str) -> Optional[User]:
        """토큰 인증 및 사용자 반환"""
        # 블랙리스트 확인
        if TokenBlacklist.is_blacklisted(token):
            return None
        
        # 토큰 검증
        payload = JWTManager.verify_token(token)
        if not payload:
            return None
        
        # 액세스 토큰만 허용
        if payload.get('type') != 'access':
            return None
        
        # 사용자 객체 반환
        user = JWTManager.get_user_from_token(token)
        return user


class AdminJWTAuth(JWTAuth):
    """관리자 전용 JWT 인증"""
    
    def authenticate(self, request: HttpRequest, token: str) -> Optional[User]:
        user = super().authenticate(request, token)
        if user and (user.is_staff or user.is_superuser):
            return user
        return None


# 인증 인스턴스 생성
jwt_auth = JWTAuth()
admin_auth = AdminJWTAuth()
```

### 2.4 스키마 정의

```python
# accounts/schemas.py
from ninja import Schema
from typing import Optional
from datetime import datetime

class LoginSchema(Schema):
    """로그인 요청 스키마"""
    username: str
    password: str

class RegisterSchema(Schema):
    """회원가입 요청 스키마"""
    username: str
    email: str
    password: str
    password_confirm: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserSchema(Schema):
    """사용자 정보 스키마"""
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_staff: bool
    is_active: bool
    date_joined: datetime

class TokenResponseSchema(Schema):
    """토큰 응답 스키마"""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserSchema

class RefreshTokenSchema(Schema):
    """토큰 갱신 요청 스키마"""
    refresh_token: str

class ChangePasswordSchema(Schema):
    """비밀번호 변경 스키마"""
    old_password: str
    new_password: str
    new_password_confirm: str

class ErrorSchema(Schema):
    """에러 응답 스키마"""
    error: str
    message: str
    details: Optional[dict] = None
```

### 2.5 API 엔드포인트 구현

```python
# accounts/api.py
from ninja import Router
from ninja.errors import HttpError
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .schemas import (
    LoginSchema, RegisterSchema, UserSchema, TokenResponseSchema,
    RefreshTokenSchema, ChangePasswordSchema, ErrorSchema
)
from .jwt_utils import JWTManager, TokenBlacklist
from .auth import jwt_auth, admin_auth

router = Router()

@router.post("/login", response={200: TokenResponseSchema, 401: ErrorSchema})
def login(request, data: LoginSchema):
    """사용자 로그인"""
    user = authenticate(
        request,
        username=data.username,
        password=data.password
    )
    
    if not user:
        raise HttpError(401, "Invalid credentials")
    
    if not user.is_active:
        raise HttpError(401, "Account is disabled")
    
    # JWT 토큰 생성
    tokens = JWTManager.generate_tokens(user)
    
    return {
        **tokens,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_staff": user.is_staff,
            "is_active": user.is_active,
            "date_joined": user.date_joined
        }
    }

@router.post("/register", response={201: TokenResponseSchema, 400: ErrorSchema})
def register(request, data: RegisterSchema):
    """사용자 회원가입"""
    # 비밀번호 확인
    if data.password != data.password_confirm:
        raise HttpError(400, "Passwords do not match")
    
    # 사용자명 중복 확인
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Username already exists")
    
    # 이메일 중복 확인
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, "Email already exists")
    
    try:
        # 비밀번호 유효성 검사
        validate_password(data.password)
        
        # 사용자 생성
        with transaction.atomic():
            user = User.objects.create_user(
                username=data.username,
                email=data.email,
                password=data.password,
                first_name=data.first_name or "",
                last_name=data.last_name or ""
            )
        
        # JWT 토큰 생성
        tokens = JWTManager.generate_tokens(user)
        
        return {
            **tokens,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_staff": user.is_staff,
                "is_active": user.is_active,
                "date_joined": user.date_joined
            }
        }
    
    except ValidationError as e:
        raise HttpError(400, f"Password validation error: {', '.join(e.messages)}")

@router.post("/refresh", response={200: dict, 401: ErrorSchema})
def refresh_token(request, data: RefreshTokenSchema):
    """액세스 토큰 갱신"""
    new_tokens = JWTManager.refresh_access_token(data.refresh_token)
    
    if not new_tokens:
        raise HttpError(401, "Invalid refresh token")
    
    return new_tokens

@router.get("/me", auth=jwt_auth, response=UserSchema)
def get_current_user(request):
    """현재 사용자 정보 조회"""
    user = request.auth
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_staff": user.is_staff,
        "is_active": user.is_active,
        "date_joined": user.date_joined
    }

@router.post("/change-password", auth=jwt_auth, response={200: dict, 400: ErrorSchema})
def change_password(request, data: ChangePasswordSchema):
    """비밀번호 변경"""
    user = request.auth
    
    # 현재 비밀번호 확인
    if not user.check_password(data.old_password):
        raise HttpError(400, "Current password is incorrect")
    
    # 새 비밀번호 확인
    if data.new_password != data.new_password_confirm:
        raise HttpError(400, "New passwords do not match")
    
    try:
        # 비밀번호 유효성 검사
        validate_password(data.new_password, user)
        
        # 비밀번호 변경
        user.set_password(data.new_password)
        user.save()
        
        return {"message": "Password changed successfully"}
    
    except ValidationError as e:
        raise HttpError(400, f"Password validation error: {', '.join(e.messages)}")

@router.post("/logout", auth=jwt_auth, response={200: dict})
def logout(request):
    """로그아웃 (토큰 블랙리스트 추가)"""
    # Authorization 헤더에서 토큰 추출
    authorization = request.headers.get('Authorization', '')
    if authorization.startswith('Bearer '):
        token = authorization[7:]  # 'Bearer ' 제거
        TokenBlacklist.add_token(token)
    
    return {"message": "Successfully logged out"}

@router.get("/protected", auth=jwt_auth, response={200: dict})
def protected_route(request):
    """보호된 라우트 예시"""
    user = request.auth
    return {
        "message": f"Hello, {user.username}! This is a protected route.",
        "user_id": user.id,
        "timestamp": "2025-09-24T14:00:00Z"
    }

@router.get("/admin-only", auth=admin_auth, response={200: dict})
def admin_only_route(request):
    """관리자 전용 라우트"""
    user = request.auth
    return {
        "message": f"Hello, admin {user.username}!",
        "users_count": User.objects.count(),
        "active_users_count": User.objects.filter(is_active=True).count()
    }
```

### 2.6 메인 API 설정

```python
# urls.py (프로젝트 루트)
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from accounts.api import router as auth_router

api = NinjaAPI(
    title="Django Ninja JWT API",
    version="1.0.0",
    description="JWT 인증을 사용하는 Django Ninja API"
)

# 라우터 등록
api.add_router("/auth", auth_router, tags=["Authentication"])

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
```

## 3. 고급 기능 구현

### 3.1 토큰 블랙리스트 DB 저장

```python
# accounts/models.py
from django.db import models
from django.contrib.auth.models import User

class BlacklistedToken(models.Model):
    """블랙리스트 토큰 모델"""
    token = models.TextField(unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    blacklisted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'blacklisted_tokens'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Blacklisted token for {self.user.username}"

class UserLoginHistory(models.Model):
    """사용자 로그인 기록"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    login_time = models.DateTimeField(auto_now_add=True)
    is_successful = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'user_login_history'
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time}"
```

### 3.2 개선된 JWT 관리

```python
# accounts/jwt_utils.py (업데이트)
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from .models import BlacklistedToken
from typing import Optional, Dict, Any
import hashlib

class EnhancedJWTManager:
    """향상된 JWT 관리 클래스"""
    
    @staticmethod
    def generate_tokens(user: User, request=None) -> Dict[str, str]:
        """액세스 토큰과 리프레시 토큰 생성"""
        now = datetime.utcnow()
        
        # 디바이스 정보 추가
        device_info = {}
        if request:
            device_info = {
                'ip_address': EnhancedJWTManager.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200]
            }
        
        # 액세스 토큰
        access_payload = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'exp': now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            'iat': now,
            'type': 'access',
            'jti': EnhancedJWTManager.generate_jti(),  # JWT ID
            **device_info
        }
        
        # 리프레시 토큰
        refresh_payload = {
            'user_id': user.id,
            'exp': now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            'iat': now,
            'type': 'refresh',
            'jti': EnhancedJWTManager.generate_jti(),
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
        
        # 캐시에 토큰 정보 저장 (선택적)
        cache_key = f"user_tokens:{user.id}"
        cache.set(cache_key, {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'created_at': now.isoformat()
        }, timeout=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    @staticmethod
    def generate_jti() -> str:
        """JWT ID 생성"""
        import uuid
        return str(uuid.uuid4())
    
    @staticmethod
    def get_client_ip(request) -> str:
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def blacklist_token(token: str, user: User = None):
        """토큰을 데이터베이스 블랙리스트에 추가"""
        payload = EnhancedJWTManager.verify_token(token)
        if payload:
            BlacklistedToken.objects.create(
                token=token,
                user_id=payload.get('user_id') or (user.id if user else None),
                expires_at=datetime.fromtimestamp(payload['exp'])
            )
    
    @staticmethod
    def is_token_blacklisted(token: str) -> bool:
        """토큰이 블랙리스트에 있는지 확인"""
        return BlacklistedToken.objects.filter(token=token).exists()
    
    @staticmethod
    def cleanup_expired_blacklisted_tokens():
        """만료된 블랙리스트 토큰 정리"""
        BlacklistedToken.objects.filter(
            expires_at__lt=datetime.utcnow()
        ).delete()
```

### 3.3 미들웨어 및 보안 강화

```python
# accounts/middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from .models import UserLoginHistory
import json

class SecurityMiddleware(MiddlewareMixin):
    """보안 미들웨어"""
    
    def process_request(self, request):
        # API 요청 로깅
        if request.path.startswith('/api/'):
            self.log_api_request(request)
        
        # Rate limiting (간단한 구현)
        if self.is_rate_limited(request):
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests'
            }, status=429)
    
    def log_api_request(self, request):
        """API 요청 로깅"""
        # 로깅 로직 구현
        pass
    
    def is_rate_limited(self, request) -> bool:
        """Rate limiting 확인"""
        # 간단한 rate limiting 로직
        return False

class LoginHistoryMiddleware(MiddlewareMixin):
    """로그인 기록 미들웨어"""
    
    def process_request(self, request):
        if request.path == '/api/auth/login' and request.method == 'POST':
            # 로그인 시도 기록
            self.record_login_attempt(request)
    
    def record_login_attempt(self, request):
        """로그인 시도 기록"""
        try:
            data = json.loads(request.body)
            username = data.get('username')
            
            if username:
                ip_address = self.get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                
                # 로그인 기록 로직 구현
                pass
        except:
            pass
    
    def get_client_ip(self, request):
        """클라이언트 IP 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

## 4. 프론트엔드 연동

### 4.1 JavaScript/React 클라이언트

```javascript
// auth.js - JWT 인증 클라이언트
class AuthService {
    constructor(baseURL = 'http://localhost:8000/api') {
        this.baseURL = baseURL;
        this.accessToken = localStorage.getItem('access_token');
        this.refreshToken = localStorage.getItem('refresh_token');
    }

    async login(username, password) {
        try {
            const response = await fetch(`${this.baseURL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password })
            });

            if (response.ok) {
                const data = await response.json();
                this.setTokens(data.access_token, data.refresh_token);
                return data;
            } else {
                const error = await response.json();
                throw new Error(error.message || 'Login failed');
            }
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    }

    async register(userData) {
        try {
            const response = await fetch(`${this.baseURL}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userData)
            });

            if (response.ok) {
                const data = await response.json();
                this.setTokens(data.access_token, data.refresh_token);
                return data;
            } else {
                const error = await response.json();
                throw new Error(error.message || 'Registration failed');
            }
        } catch (error) {
            console.error('Registration error:', error);
            throw error;
        }
    }

    async logout() {
        try {
            await fetch(`${this.baseURL}/auth/logout`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.accessToken}`,
                    'Content-Type': 'application/json',
                }
            });
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.clearTokens();
        }
    }

    async refreshAccessToken() {
        if (!this.refreshToken) {
            throw new Error('No refresh token available');
        }

        try {
            const response = await fetch(`${this.baseURL}/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ refresh_token: this.refreshToken })
            });

            if (response.ok) {
                const data = await response.json();
                this.setTokens(data.access_token, this.refreshToken);
                return data.access_token;
            } else {
                this.clearTokens();
                throw new Error('Token refresh failed');
            }
        } catch (error) {
            console.error('Token refresh error:', error);
            this.clearTokens();
            throw error;
        }
    }

    async apiCall(url, options = {}) {
        const config = {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            }
        };

        // 토큰이 있으면 Authorization 헤더 추가
        if (this.accessToken) {
            config.headers.Authorization = `Bearer ${this.accessToken}`;
        }

        try {
            let response = await fetch(`${this.baseURL}${url}`, config);

            // 401 에러 시 토큰 갱신 시도
            if (response.status === 401 && this.refreshToken) {
                await this.refreshAccessToken();
                config.headers.Authorization = `Bearer ${this.accessToken}`;
                response = await fetch(`${this.baseURL}${url}`, config);
            }

            if (response.ok) {
                return await response.json();
            } else {
                const error = await response.json();
                throw new Error(error.message || 'API call failed');
            }
        } catch (error) {
            console.error('API call error:', error);
            throw error;
        }
    }

    setTokens(accessToken, refreshToken) {
        this.accessToken = accessToken;
        this.refreshToken = refreshToken;
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
    }

    clearTokens() {
        this.accessToken = null;
        this.refreshToken = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    }

    isAuthenticated() {
        return !!this.accessToken;
    }

    async getCurrentUser() {
        return await this.apiCall('/auth/me');
    }
}

// 사용 예시
const authService = new AuthService();

// React 컴포넌트에서 사용
const LoginComponent = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleLogin = async (e) => {
        e.preventDefault();
        try {
            const result = await authService.login(username, password);
            console.log('Login successful:', result);
            // 로그인 성공 후 리다이렉트
            window.location.href = '/dashboard';
        } catch (error) {
            setError(error.message);
        }
    };

    return (
        <form onSubmit={handleLogin}>
            <input
                type="text"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
            />
            <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
            />
            <button type="submit">Login</button>
            {error && <div className="error">{error}</div>}
        </form>
    );
};
```

## 5. 보안 고려사항

### 5.1 토큰 보안

```python
# accounts/security.py
import hashlib
import hmac
from django.conf import settings
from django.core.cache import cache
from datetime import datetime, timedelta

class SecurityManager:
    """보안 관리 클래스"""
    
    @staticmethod
    def validate_token_signature(token: str, expected_signature: str) -> bool:
        """토큰 서명 검증"""
        calculated_signature = hmac.new(
            settings.JWT_SECRET_KEY.encode(),
            token.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(calculated_signature, expected_signature)
    
    @staticmethod
    def check_rate_limit(user_id: int, action: str, limit: int = 5, window: int = 300) -> bool:
        """Rate limiting 확인"""
        cache_key = f"rate_limit:{user_id}:{action}"
        current_count = cache.get(cache_key, 0)
        
        if current_count >= limit:
            return False
        
        cache.set(cache_key, current_count + 1, window)
        return True
    
    @staticmethod
    def log_security_event(user_id: int, event_type: str, details: dict):
        """보안 이벤트 로깅"""
        from .models import SecurityEvent
        
        SecurityEvent.objects.create(
            user_id=user_id,
            event_type=event_type,
            details=details,
            timestamp=datetime.utcnow()
        )

# 추가 보안 모델
class SecurityEvent(models.Model):
    """보안 이벤트 로그"""
    EVENT_TYPES = [
        ('login_success', 'Successful Login'),
        ('login_failed', 'Failed Login'),
        ('token_refresh', 'Token Refresh'),
        ('password_change', 'Password Change'),
        ('suspicious_activity', 'Suspicious Activity'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    details = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'security_events'
        ordering = ['-timestamp']
```

### 5.2 환경 변수 보안

```python
# .env (환경 변수)
DEBUG=False
SECRET_KEY=your-very-long-and-complex-secret-key-here
JWT_SECRET_KEY=another-very-secure-jwt-secret-key
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Redis 설정 (세션 및 캐시용)
REDIS_URL=redis://localhost:6379/0

# 이메일 설정
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# 보안 설정
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com

# JWT 설정
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=HS256
```

## 6. 테스트 구현

### 6.1 API 테스트

```python
# tests/test_auth_api.py
from django.test import TestCase
from django.contrib.auth.models import User
from ninja.testing import TestClient
from accounts.api import router
from accounts.jwt_utils import JWTManager

class AuthAPITestCase(TestCase):
    """인증 API 테스트"""
    
    def setUp(self):
        self.client = TestClient(router)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_login_success(self):
        """로그인 성공 테스트"""
        response = self.client.post("/login", json={
            "username": "testuser",
            "password": "testpass123"
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('access_token', data)
        self.assertIn('refresh_token', data)
        self.assertEqual(data['user']['username'], 'testuser')
    
    def test_login_invalid_credentials(self):
        """잘못된 인증 정보로 로그인 테스트"""
        response = self.client.post("/login", json={
            "username": "testuser",
            "password": "wrongpassword"
        })
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn('error', data)
    
    def test_protected_route_with_valid_token(self):
        """유효한 토큰으로 보호된 라우트 접근"""
        tokens = JWTManager.generate_tokens(self.user)
        
        response = self.client.get(
            "/protected",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('message', data)
    
    def test_protected_route_without_token(self):
        """토큰 없이 보호된 라우트 접근"""
        response = self.client.get("/protected")
        
        self.assertEqual(response.status_code, 401)
    
    def test_token_refresh(self):
        """토큰 갱신 테스트"""
        tokens = JWTManager.generate_tokens(self.user)
        
        response = self.client.post("/refresh", json={
            "refresh_token": tokens['refresh_token']
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('access_token', data)
```

## 7. 배포 고려사항

### 7.1 프로덕션 설정

```python
# settings/production.py
import os
from .base import *

DEBUG = False

# 보안 설정
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# HTTPS 강제
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# JWT 보안 강화
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15  # 프로덕션에서는 더 짧게
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

# 데이터베이스 설정 (PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# Redis 캐시 설정
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/auth.log',
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

## 결론

Django Ninja와 JWT를 활용한 인증 시스템은 현대적인 웹 애플리케이션의 보안 요구사항을 효과적으로 만족시킵니다. 이 가이드에서 다룬 내용들을 통해:

1. **JWT의 핵심 장점**: Stateless, 확장성, 플랫폼 독립성
2. **완전한 구현**: 로그인, 회원가입, 토큰 갱신, 로그아웃
3. **고급 기능**: 토큰 블랙리스트, 보안 이벤트 로깅, Rate limiting
4. **프론트엔드 연동**: JavaScript/React 클라이언트 예시
5. **보안 고려사항**: 토큰 보안, 환경 변수 관리
6. **테스트**: 포괄적인 API 테스트 구현
7. **배포 준비**: 프로덕션 환경 설정

JWT 기반 인증은 마이크로서비스 아키텍처와 모던 프론트엔드 프레임워크와의 완벽한 호환성을 제공하며, Django Ninja의 FastAPI 스타일 개발 경험과 결합하여 개발자 친화적이면서도 보안성이 뛰어난 API를 구축할 수 있습니다.