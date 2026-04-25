---
layout: post
title: "Django Ninja로 Apple 소셜 로그인 완벽 구현 가이드"
date: 2025-12-15 10:00:00 +0900
categories: [Django, Backend, Authentication]
tags: [django-ninja, apple-login, sign-in-with-apple, oauth, jwt, social-login, authentication]
description: "Django Ninja를 활용하여 Apple 소셜 로그인(Sign in with Apple)을 처음부터 끝까지 구현하는 방법을 알아봅니다. JWT 검증, Apple Developer 설정, 보안 처리까지 완벽 가이드."
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-12-15-django-ninja-apple-social-login.webp"
---

## 목차
1. [Apple 소셜 로그인 소개](#1-apple-소셜-로그인-소개)
2. [Apple Developer 설정](#2-apple-developer-설정)
3. [Django 프로젝트 설정](#3-django-프로젝트-설정)
4. [JWT 토큰 검증 구현](#4-jwt-토큰-검증-구현)
5. [Django Ninja API 구현](#5-django-ninja-api-구현)
6. [사용자 생성 및 로그인 처리](#6-사용자-생성-및-로그인-처리)
7. [클라이언트 연동 (iOS/Web)](#7-클라이언트-연동-iosweb)
8. [보안 및 에러 처리](#8-보안-및-에러-처리)
9. [테스트 및 디버깅](#9-테스트-및-디버깅)
10. [프로덕션 배포](#10-프로덕션-배포)

---

## 1. Apple 소셜 로그인 소개

### 1.1 Sign in with Apple이란?

**Sign in with Apple**은 Apple이 제공하는 소셜 로그인 서비스로, iOS 13 이상의 모든 기기에서 사용할 수 있습니다. 2019년 WWDC에서 발표된 이후, Apple은 앱스토어 정책을 통해 다른 소셜 로그인(구글, 페이스북 등)을 제공하는 앱이라면 Apple 로그인도 필수로 제공하도록 요구하고 있습니다.

**주요 특징:**

✅ **강력한 프라이버시** - 사용자가 이메일을 숨길 수 있음 (Relay 이메일)
✅ **빠른 인증** - Face ID/Touch ID로 즉시 로그인
✅ **필수 구현** - 다른 소셜 로그인 제공 시 Apple 로그인 필수
✅ **크로스 플랫폼** - iOS, macOS, watchOS, Web 모두 지원
✅ **보안** - Apple의 강력한 보안 인프라 활용

### 1.2 인증 플로우 이해하기

Apple 로그인의 전체 흐름은 다음과 같습니다:

```
┌─────────┐                ┌─────────────┐                ┌─────────────┐
│  Client │                │ Your Server │                │   Apple     │
│ (iOS/Web)│                │(Django Ninja)│               │  Identity   │
└────┬────┘                └──────┬──────┘                └──────┬──────┘
     │                             │                              │
     │ 1. Apple 로그인 버튼 클릭    │                              │
     ├────────────────────────────────────────────────────────>│
     │                             │                              │
     │ 2. Apple 로그인 화면        │                              │
     │<────────────────────────────────────────────────────────┤
     │                             │                              │
     │ 3. Face ID/비밀번호 인증    │                              │
     ├────────────────────────────────────────────────────────>│
     │                             │                              │
     │ 4. Authorization Code +     │                              │
     │    Identity Token (JWT)     │                              │
     │<────────────────────────────────────────────────────────┤
     │                             │                              │
     │ 5. POST /api/auth/apple     │                              │
     │    { identityToken, user }  │                              │
     ├────────────────────────────>│                              │
     │                             │                              │
     │                             │ 6. JWT 검증 요청              │
     │                             ├────────────────────────────>│
     │                             │                              │
     │                             │ 7. Apple Public Keys         │
     │                             │<────────────────────────────┤
     │                             │                              │
     │                             │ 8. JWT 서명 검증             │
     │                             │    + 사용자 정보 추출         │
     │                             │                              │
     │ 9. Access Token 발급        │                              │
     │    { accessToken, user }    │                              │
     │<────────────────────────────┤                              │
     │                             │                              │
```

**핵심 포인트:**

1. **Identity Token (JWT)**: Apple이 발급하는 JWT 토큰에 사용자 정보가 담겨있음
2. **서버 검증**: 서버에서 Apple Public Key로 JWT 서명을 검증해야 함
3. **Relay Email**: 사용자가 이메일 숨기기를 선택하면 `privaterelay.appleid.com` 이메일 제공
4. **일회성 정보**: `user` 정보(이름, 이메일)는 최초 로그인 시에만 제공됨

### 1.3 필요한 준비물

**필수 요구사항:**

- ✅ Apple Developer 계정 (유료, 연 $99)
- ✅ 등록된 App ID
- ✅ Service ID (웹 로그인용)
- ✅ Django 프로젝트 (Django 4.2+)
- ✅ Django Ninja 설치
- ✅ SSL 인증서 (HTTPS 필수)

**선택 사항:**

- 📱 iOS 앱 (네이티브 앱 개발 시)
- 🌐 웹 도메인 (웹 로그인 구현 시)
- 🔐 JWT 라이브러리 (PyJWT)

---

## 2. Apple Developer 설정

### 2.1 Apple Developer 계정 준비

Apple 소셜 로그인을 구현하려면 유료 Apple Developer 계정이 필요합니다.

**계정 생성:**

```
1. https://developer.apple.com 접속
2. [Account] 클릭
3. Apple ID로 로그인
4. [Join the Apple Developer Program] 선택
5. 연간 $99 결제
6. 승인 대기 (보통 24시간 이내)
```

### 2.2 App ID 생성

**1단계: Certificates, Identifiers & Profiles 접속**

```
1. Apple Developer 사이트 로그인
2. [Certificates, Identifiers & Profiles] 메뉴
3. 좌측 [Identifiers] 클릭
4. [+] 버튼 클릭
```

**2단계: App ID 등록**

```
1. [App IDs] 선택
2. [Continue] 클릭

3. 정보 입력:
   - Description: "My App"
   - Bundle ID: "com.yourcompany.yourapp"
   - Explicit 선택 (Wildcard 아님)

4. Capabilities 중 [Sign In with Apple] 체크
5. [Continue] → [Register] 클릭
```

### 2.3 Service ID 생성 (웹 로그인용)

Service ID는 웹 환경에서 Apple 로그인을 구현할 때 필요합니다.

**Service ID 등록:**

```
1. [Identifiers] → [+] 버튼
2. [Services IDs] 선택
3. [Continue] 클릭

4. 정보 입력:
   - Description: "My App Web Login"
   - Identifier: "com.yourcompany.yourapp.service"
   
5. [Sign In with Apple] 체크
6. [Configure] 클릭

7. Domains and Subdomains:
   - Primary Domain: "yourdomain.com"
   - 예: "api.myapp.com"

8. Return URLs:
   - https://yourdomain.com/api/auth/apple/callback
   - 예: "https://api.myapp.com/api/auth/apple/callback"

9. [Save] → [Continue] → [Register]
```

⚠️ **중요**: Return URL은 HTTPS여야 하며, 실제 배포된 도메인이어야 합니다. localhost는 불가능합니다.

### 2.4 Key 생성

Apple 로그인 검증을 위한 Private Key를 생성합니다.

**Key 생성 절차:**

```
1. 좌측 메뉴에서 [Keys] 선택
2. [+] 버튼 클릭

3. Key 설정:
   - Key Name: "Apple Login Key"
   - [Sign In with Apple] 체크
   - [Configure] 클릭
   
4. Primary App ID 선택:
   - 앞서 만든 App ID 선택
   - [Save] 클릭

5. [Continue] → [Register]

6. Key 다운로드:
   - [Download] 버튼 클릭
   - AuthKey_XXXXXXXXXX.p8 파일 저장
   - ⚠️ 이 파일은 다시 다운로드 불가능!
   
7. Key ID 기록:
   - 10자리 Key ID 복사 (예: "AB12CD34EF")
```

**다운로드한 파일 관리:**

```bash
# 프로젝트 루트에 저장 (Git에는 커밋하지 말 것!)
mkdir -p config/apple/
mv ~/Downloads/AuthKey_XXXXXXXXXX.p8 config/apple/

# .gitignore에 추가
echo "config/apple/*.p8" >> .gitignore
```

### 2.5 Team ID 확인

```
1. Apple Developer 사이트 우측 상단
2. 계정 이름 옆에 Team ID 표시
3. 10자리 영숫자 (예: "XYZ1234ABC")
4. 이 값을 기록해둡니다
```

### 2.6 설정 정보 정리

이제 다음 정보들을 모두 확보했습니다:

```python
# settings.py 또는 .env 파일에 저장할 정보

APPLE_TEAM_ID = "XYZ1234ABC"           # Team ID
APPLE_CLIENT_ID = "com.yourcompany.yourapp"  # App ID (Bundle ID)
APPLE_SERVICE_ID = "com.yourcompany.yourapp.service"  # Service ID
APPLE_KEY_ID = "AB12CD34EF"            # Key ID
APPLE_PRIVATE_KEY_PATH = "config/apple/AuthKey_AB12CD34EF.p8"
```

**보안 팁:**

```python
# .env 파일 사용 (python-decouple)
pip install python-decouple

# .env
APPLE_TEAM_ID=XYZ1234ABC
APPLE_CLIENT_ID=com.yourcompany.yourapp
APPLE_SERVICE_ID=com.yourcompany.yourapp.service
APPLE_KEY_ID=AB12CD34EF
APPLE_PRIVATE_KEY_PATH=config/apple/AuthKey_AB12CD34EF.p8

# settings.py
from decouple import config

APPLE_TEAM_ID = config('APPLE_TEAM_ID')
APPLE_CLIENT_ID = config('APPLE_CLIENT_ID')
APPLE_SERVICE_ID = config('APPLE_SERVICE_ID')
APPLE_KEY_ID = config('APPLE_KEY_ID')
APPLE_PRIVATE_KEY_PATH = config('APPLE_PRIVATE_KEY_PATH')
```

이제 Apple Developer 설정이 완료되었습니다. 다음 섹션에서는 Django 프로젝트 설정을 진행하겠습니다.

---

## 3. Django 프로젝트 설정

### 3.1 필수 패키지 설치

Apple 소셜 로그인 구현에 필요한 Python 패키지들을 설치합니다.

```bash
# 기본 패키지
pip install django django-ninja

# JWT 처리
pip install PyJWT cryptography

# HTTP 요청
pip install requests

# 환경 변수 관리
pip install python-decouple

# CORS 처리 (프론트엔드 분리 시)
pip install django-cors-headers
```

**requirements.txt:**

```txt
Django==5.0.0
django-ninja==1.1.0
PyJWT==2.8.0
cryptography==41.0.7
requests==2.31.0
python-decouple==3.8
django-cors-headers==4.3.1
```

### 3.2 Django 설정

**settings.py 기본 설정:**

```python
# config/settings.py
import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'corsheaders',
    
    # Local apps
    'accounts',
    'authentication',
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

ROOT_URLCONF = 'config.urls'

# Apple Login 설정
APPLE_TEAM_ID = config('APPLE_TEAM_ID')
APPLE_CLIENT_ID = config('APPLE_CLIENT_ID')
APPLE_SERVICE_ID = config('APPLE_SERVICE_ID', default=APPLE_CLIENT_ID)
APPLE_KEY_ID = config('APPLE_KEY_ID')
APPLE_PRIVATE_KEY_PATH = os.path.join(BASE_DIR, config('APPLE_PRIVATE_KEY_PATH'))

# JWT 설정
JWT_SECRET_KEY = config('JWT_SECRET_KEY', default=SECRET_KEY)
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_LIFETIME = 3600 * 24 * 7  # 7일

# CORS 설정 (프론트엔드 분리 시)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
]

CORS_ALLOW_CREDENTIALS = True
```

### 3.3 User 모델 설정

Apple 로그인을 지원하는 커스텀 User 모델을 만듭니다.

**accounts/models.py:**

```python
# accounts/models.py
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
import uuid


class UserManager(BaseUserManager):
    """커스텀 User 매니저"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('이메일은 필수입니다')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()  # 소셜 로그인은 비밀번호 없음
        
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """커스텀 User 모델"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, verbose_name='이메일')
    
    # 소셜 로그인 정보
    apple_user_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Apple User ID'
    )
    
    # 기본 정보
    name = models.CharField(max_length=100, blank=True, verbose_name='이름')
    profile_image = models.URLField(blank=True, verbose_name='프로필 이미지')
    
    # 권한
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'users'
        verbose_name = '사용자'
        verbose_name_plural = '사용자'
    
    def __str__(self):
        return self.email
    
    def update_last_login(self):
        """마지막 로그인 시간 업데이트"""
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])
```

**settings.py에 User 모델 등록:**

```python
# settings.py에 추가
AUTH_USER_MODEL = 'accounts.User'
```

### 3.4 마이그레이션

```bash
# 마이그레이션 생성
python manage.py makemigrations accounts

# 마이그레이션 적용
python manage.py migrate

# 슈퍼유저 생성 (테스트용)
python manage.py createsuperuser
```

### 3.5 Admin 패널 등록

**accounts/admin.py:**

```python
# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'name', 'apple_user_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'is_staff', 'created_at']
    search_fields = ['email', 'name', 'apple_user_id']
    ordering = ['-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('email', 'name', 'profile_image')
        }),
        ('소셜 로그인', {
            'fields': ('apple_user_id',)
        }),
        ('권한', {
            'fields': ('is_active', 'is_staff', 'is_superuser')
        }),
        ('타임스탬프', {
            'fields': ('last_login', 'created_at', 'updated_at')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
```

이제 Django 프로젝트의 기본 설정이 완료되었습니다. 다음 섹션에서는 JWT 토큰 검증을 구현하겠습니다.

---

## 4. JWT 토큰 검증 구현

### 4.1 Apple Public Keys 가져오기

Apple은 JWT 토큰을 RSA 알고리즘으로 서명합니다. 서버에서 이를 검증하려면 Apple의 Public Keys가 필요합니다.

**authentication/apple_auth.py:**

```python
# authentication/apple_auth.py
import jwt
import time
import requests
from typing import Dict, Optional
from django.conf import settings
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


class AppleAuthService:
    """Apple 로그인 인증 서비스"""
    
    APPLE_PUBLIC_KEYS_URL = 'https://appleid.apple.com/auth/keys'
    APPLE_ISSUER = 'https://appleid.apple.com'
    
    def __init__(self):
        self.team_id = settings.APPLE_TEAM_ID
        self.client_id = settings.APPLE_CLIENT_ID
        self.service_id = settings.APPLE_SERVICE_ID
        self.key_id = settings.APPLE_KEY_ID
        self.private_key_path = settings.APPLE_PRIVATE_KEY_PATH
        
        self._public_keys = None
        self._keys_last_fetched = 0
        self._keys_cache_duration = 3600  # 1시간
    
    def get_apple_public_keys(self) -> Dict:
        """
        Apple Public Keys 가져오기 (캐싱 포함)
        """
        current_time = time.time()
        
        # 캐시 확인
        if self._public_keys and (current_time - self._keys_last_fetched) < self._keys_cache_duration:
            return self._public_keys
        
        # Apple에서 Public Keys 가져오기
        try:
            response = requests.get(self.APPLE_PUBLIC_KEYS_URL, timeout=10)
            response.raise_for_status()
            
            self._public_keys = response.json()
            self._keys_last_fetched = current_time
            
            return self._public_keys
        
        except requests.RequestException as e:
            raise Exception(f'Apple Public Keys 가져오기 실패: {str(e)}')
    
    def decode_identity_token(self, identity_token: str) -> Dict:
        """
        Identity Token (JWT) 디코딩 및 검증
        
        Args:
            identity_token: Apple에서 발급한 JWT 토큰
        
        Returns:
            디코딩된 사용자 정보
        
        Raises:
            jwt.InvalidTokenError: 토큰이 유효하지 않은 경우
        """
        # JWT 헤더 파싱 (키 찾기 위함)
        unverified_header = jwt.get_unverified_header(identity_token)
        key_id = unverified_header.get('kid')
        algorithm = unverified_header.get('alg', 'RS256')
        
        if not key_id:
            raise jwt.InvalidTokenError('JWT 헤더에 kid가 없습니다')
        
        # Apple Public Keys에서 해당 키 찾기
        public_keys = self.get_apple_public_keys()
        public_key = None
        
        for key in public_keys.get('keys', []):
            if key.get('kid') == key_id:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                break
        
        if not public_key:
            raise jwt.InvalidTokenError(f'해당 kid({key_id})의 Public Key를 찾을 수 없습니다')
        
        # JWT 검증 및 디코딩
        try:
            decoded = jwt.decode(
                identity_token,
                public_key,
                algorithms=[algorithm],
                audience=self.client_id,  # 또는 self.service_id (웹의 경우)
                issuer=self.APPLE_ISSUER
            )
            
            return decoded
        
        except jwt.ExpiredSignatureError:
            raise jwt.InvalidTokenError('토큰이 만료되었습니다')
        
        except jwt.InvalidAudienceError:
            # 웹 로그인의 경우 service_id로 재시도
            decoded = jwt.decode(
                identity_token,
                public_key,
                algorithms=[algorithm],
                audience=self.service_id,
                issuer=self.APPLE_ISSUER
            )
            return decoded
        
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f'JWT 검증 실패: {str(e)}')
    
    def verify_identity_token(self, identity_token: str) -> Optional[Dict]:
        """
        Identity Token 검증 및 사용자 정보 추출
        
        Returns:
            {
                'sub': 'apple_user_id',
                'email': 'user@example.com',
                'email_verified': True,
                'is_private_email': False
            }
        """
        try:
            decoded = self.decode_identity_token(identity_token)
            
            # 사용자 정보 추출
            user_info = {
                'apple_user_id': decoded.get('sub'),
                'email': decoded.get('email'),
                'email_verified': decoded.get('email_verified', False),
                'is_private_email': decoded.get('is_private_email', False),
            }
            
            return user_info
        
        except jwt.InvalidTokenError as e:
            print(f'Token verification failed: {str(e)}')
            return None


# 싱글톤 인스턴스
apple_auth_service = AppleAuthService()
```

### 4.2 JWT 검증 로직 설명

**검증 단계:**

```python
# 1. JWT 헤더에서 kid (Key ID) 추출
header = jwt.get_unverified_header(token)
kid = header['kid']

# 2. Apple Public Keys에서 해당 kid의 키 찾기
public_keys = requests.get('https://appleid.apple.com/auth/keys')
matching_key = [k for k in public_keys['keys'] if k['kid'] == kid][0]

# 3. Public Key로 서명 검증
decoded = jwt.decode(
    token,
    matching_key,
    algorithms=['RS256'],
    audience='com.yourcompany.yourapp',  # Your Client ID
    issuer='https://appleid.apple.com'
)

# 4. 사용자 정보 추출
apple_user_id = decoded['sub']
email = decoded['email']
```

**decoded JWT 예제:**

```json
{
  "iss": "https://appleid.apple.com",
  "aud": "com.yourcompany.yourapp",
  "exp": 1703001234,
  "iat": 1702987834,
  "sub": "001234.abcd1234efgh5678.1234",
  "c_hash": "abc123def456",
  "email": "user@privaterelay.appleid.com",
  "email_verified": "true",
  "is_private_email": "true",
  "auth_time": 1702987834,
  "nonce_supported": true
}
```

---

## 5. Django Ninja API 구현

### 5.1 Schemas 정의

**authentication/schemas.py:**

```python
# authentication/schemas.py
from typing import Optional
from ninja import Schema
from pydantic import EmailStr, Field


class AppleLoginRequest(Schema):
    """Apple 로그인 요청"""
    identity_token: str = Field(..., description="Apple Identity Token (JWT)")
    authorization_code: Optional[str] = Field(None, description="Authorization Code")
    
    # 최초 로그인 시에만 제공되는 사용자 정보
    user: Optional[dict] = Field(None, description="사용자 정보 (최초 로그인 시)")


class AppleUserInfo(Schema):
    """Apple 사용자 정보 (최초 로그인 시)"""
    name: Optional[dict] = None  # {"firstName": "John", "lastName": "Doe"}
    email: Optional[EmailStr] = None


class UserOut(Schema):
    """사용자 정보 응답"""
    id: str
    email: str
    name: str
    profile_image: str
    apple_user_id: Optional[str] = None


class AuthTokenResponse(Schema):
    """인증 토큰 응답"""
    access_token: str
    token_type: str = "Bearer"
    user: UserOut


class ErrorResponse(Schema):
    """에러 응답"""
    error: str
    detail: Optional[str] = None
```

### 5.2 JWT Token 생성 유틸리티

**authentication/jwt_utils.py:**

```python
# authentication/jwt_utils.py
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from typing import Dict


def create_access_token(user_id: str, email: str) -> str:
    """
    JWT Access Token 생성
    
    Args:
        user_id: 사용자 ID (UUID)
        email: 사용자 이메일
    
    Returns:
        JWT 토큰 문자열
    """
    now = datetime.utcnow()
    payload = {
        'user_id': str(user_id),
        'email': email,
        'exp': now + timedelta(seconds=settings.JWT_ACCESS_TOKEN_LIFETIME),
        'iat': now,
        'type': 'access'
    }
    
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return token


def decode_access_token(token: str) -> Dict:
    """
    JWT Access Token 디코딩
    
    Args:
        token: JWT 토큰 문자열
    
    Returns:
        디코딩된 payload
    
    Raises:
        jwt.InvalidTokenError: 토큰이 유효하지 않은 경우
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    
    except jwt.ExpiredSignatureError:
        raise jwt.InvalidTokenError('토큰이 만료되었습니다')
    
    except jwt.InvalidTokenError as e:
        raise jwt.InvalidTokenError(f'유효하지 않은 토큰: {str(e)}')
```

### 5.3 API 엔드포인트 구현

**authentication/api.py:**

```python
# authentication/api.py
from ninja import Router
from django.db import transaction
from accounts.models import User
from .schemas import AppleLoginRequest, AuthTokenResponse, ErrorResponse
from .apple_auth import apple_auth_service
from .jwt_utils import create_access_token

router = Router(tags=['Authentication'])


@router.post('/apple', response={200: AuthTokenResponse, 400: ErrorResponse})
def apple_login(request, data: AppleLoginRequest):
    """
    Apple 소셜 로그인
    
    Flow:
        1. Identity Token 검증
        2. 사용자 조회 또는 생성
        3. JWT Access Token 발급
    
    Args:
        data: AppleLoginRequest
            - identity_token: Apple Identity Token (필수)
            - user: 사용자 정보 (최초 로그인 시에만 제공됨)
    
    Returns:
        AuthTokenResponse: Access Token 및 사용자 정보
    
    Errors:
        400: 토큰 검증 실패 또는 잘못된 요청
    """
    try:
        # 1. Identity Token 검증
        apple_user_info = apple_auth_service.verify_identity_token(data.identity_token)
        
        if not apple_user_info:
            return 400, {
                'error': 'invalid_token',
                'detail': 'Identity Token 검증에 실패했습니다'
            }
        
        apple_user_id = apple_user_info['apple_user_id']
        email = apple_user_info['email']
        
        if not apple_user_id or not email:
            return 400, {
                'error': 'missing_user_info',
                'detail': '필수 사용자 정보가 누락되었습니다'
            }
        
        # 2. 사용자 조회 또는 생성
        with transaction.atomic():
            user, created = User.objects.get_or_create(
                apple_user_id=apple_user_id,
                defaults={
                    'email': email,
                    'name': '',
                }
            )
            
            # 최초 로그인: 추가 정보 업데이트
            if created and data.user:
                user_data = data.user
                
                # 이름 업데이트
                if isinstance(user_data, dict) and 'name' in user_data:
                    name_info = user_data['name']
                    if isinstance(name_info, dict):
                        first_name = name_info.get('firstName', '')
                        last_name = name_info.get('lastName', '')
                        user.name = f"{first_name} {last_name}".strip()
                        user.save(update_fields=['name'])
            
            # 마지막 로그인 시간 업데이트
            user.update_last_login()
        
        # 3. Access Token 생성
        access_token = create_access_token(user.id, user.email)
        
        # 4. 응답
        return 200, {
            'access_token': access_token,
            'token_type': 'Bearer',
            'user': {
                'id': str(user.id),
                'email': user.email,
                'name': user.name,
                'profile_image': user.profile_image,
                'apple_user_id': user.apple_user_id,
            }
        }
    
    except Exception as e:
        return 400, {
            'error': 'server_error',
            'detail': str(e)
        }


@router.get('/me', response={200: dict, 401: ErrorResponse})
def get_current_user(request):
    """
    현재 로그인한 사용자 정보 조회
    
    Headers:
        Authorization: Bearer {access_token}
    
    Returns:
        사용자 정보
    """
    # Authorization 헤더에서 토큰 추출
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return 401, {
            'error': 'unauthorized',
            'detail': 'Authorization 헤더가 없거나 형식이 올바르지 않습니다'
        }
    
    token = auth_header.split(' ')[1]
    
    try:
        from .jwt_utils import decode_access_token
        
        # 토큰 디코딩
        payload = decode_access_token(token)
        user_id = payload.get('user_id')
        
        # 사용자 조회
        user = User.objects.get(id=user_id)
        
        return 200, {
            'id': str(user.id),
            'email': user.email,
            'name': user.name,
            'profile_image': user.profile_image,
            'apple_user_id': user.apple_user_id,
        }
    
    except Exception as e:
        return 401, {
            'error': 'invalid_token',
            'detail': str(e)
        }
```

### 5.4 URL 라우팅

**config/api.py:**

```python
# config/api.py
from ninja import NinjaAPI
from authentication.api import router as auth_router

api = NinjaAPI(
    title='My App API',
    version='1.0.0',
    description='Apple 소셜 로그인 API'
)

# 라우터 등록
api.add_router('/auth/', auth_router)
```

**config/urls.py:**

```python
# config/urls.py
from django.contrib import admin
from django.urls import path
from .api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
```

---

## 6. 사용자 생성 및 로그인 처리

### 6.1 회원가입 vs 로그인 구분

Apple 로그인은 회원가입과 로그인을 구분하지 않습니다. 최초 로그인이 곧 회원가입입니다.

```python
# 사용자 조회/생성 로직
user, created = User.objects.get_or_create(
    apple_user_id=apple_user_id,
    defaults={
        'email': email,
        'name': extract_name_from_data(data.user),
    }
)

if created:
    # 최초 로그인 (회원가입)
    print(f'새 사용자 생성: {user.email}')
    # 웰컴 이메일 발송, 기본 설정 등
else:
    # 기존 사용자 로그인
    print(f'기존 사용자 로그인: {user.email}')
```

### 6.2 Relay Email 처리

사용자가 "이메일 숨기기"를 선택하면 Apple이 Relay 이메일을 제공합니다.

```python
# Relay 이메일 예시
email = "abc123def456@privaterelay.appleid.com"

# Relay 이메일 확인
is_relay = email.endswith('@privaterelay.appleid.com')

if is_relay:
    # Relay 이메일로 전송한 메일은 Apple이 사용자의 실제 이메일로 전달
    # 단, 발신자 검증 필요 (SPF, DKIM 설정)
    pass
```

**Relay 이메일로 메일 보내기:**

```python
# 이메일 발송 시 주의사항
from django.core.mail import send_mail

def send_welcome_email(user):
    # Relay 이메일이든 실제 이메일이든 동일하게 처리
    send_mail(
        subject='환영합니다!',
        message='회원가입을 축하합니다.',
        from_email='noreply@yourdomain.com',
        recipient_list=[user.email],
        fail_silently=False,
    )
```

### 6.3 사용자 정보 업데이트

```python
# authentication/services.py
from accounts.models import User
from typing import Optional, Dict


def update_user_from_apple_data(user: User, apple_data: Optional[Dict]) -> User:
    """
    Apple에서 제공한 사용자 정보로 업데이트
    
    Note: 이름 정보는 최초 로그인 시에만 제공됨
    """
    if not apple_data:
        return user
    
    updated = False
    
    # 이름 업데이트
    if 'name' in apple_data:
        name_info = apple_data['name']
        if isinstance(name_info, dict):
            first_name = name_info.get('firstName', '')
            last_name = name_info.get('lastName', '')
            full_name = f"{first_name} {last_name}".strip()
            
            if full_name and not user.name:
                user.name = full_name
                updated = True
    
    # 이메일 업데이트 (변경되는 경우는 거의 없음)
    if 'email' in apple_data and apple_data['email']:
        if user.email != apple_data['email']:
            user.email = apple_data['email']
            updated = True
    
    if updated:
        user.save()
    
    return user
```

---

## 7. 클라이언트 연동 (iOS/Web)

### 7.1 iOS 클라이언트 (SwiftUI)

**Apple 로그인 버튼 구현:**

```swift
// LoginView.swift
import SwiftUI
import AuthenticationServices

struct LoginView: View {
    @State private var isLoading = false
    @State private var errorMessage: String?
    
    var body: some View {
        VStack(spacing: 20) {
            Text("로그인")
                .font(.largeTitle)
                .bold()
            
            // Apple 로그인 버튼
            SignInWithAppleButton(
                onRequest: { request in
                    request.requestedScopes = [.fullName, .email]
                },
                onCompletion: { result in
                    handleSignInWithApple(result: result)
                }
            )
            .signInWithAppleButtonStyle(.black)
            .frame(height: 50)
            .padding()
            
            if isLoading {
                ProgressView()
            }
            
            if let errorMessage = errorMessage {
                Text(errorMessage)
                    .foregroundColor(.red)
                    .font(.caption)
            }
        }
        .padding()
    }
    
    func handleSignInWithApple(result: Result<ASAuthorization, Error>) {
        switch result {
        case .success(let authorization):
            if let appleIDCredential = authorization.credential as? ASAuthorizationAppleIDCredential {
                // Identity Token 추출
                guard let identityTokenData = appleIDCredential.identityToken,
                      let identityToken = String(data: identityTokenData, encoding: .utf8) else {
                    errorMessage = "Identity Token을 가져올 수 없습니다"
                    return
                }
                
                // 서버로 전송할 데이터 구성
                var userData: [String: Any] = [:]
                
                // 이름 정보 (최초 로그인 시에만 제공)
                if let fullName = appleIDCredential.fullName {
                    userData["name"] = [
                        "firstName": fullName.givenName ?? "",
                        "lastName": fullName.familyName ?? ""
                    ]
                }
                
                // 이메일 (최초 로그인 시에만 제공)
                if let email = appleIDCredential.email {
                    userData["email"] = email
                }
                
                // 서버 API 호출
                sendToServer(
                    identityToken: identityToken,
                    userData: userData.isEmpty ? nil : userData
                )
            }
            
        case .failure(let error):
            errorMessage = "로그인 실패: \(error.localizedDescription)"
        }
    }
    
    func sendToServer(identityToken: String, userData: [String: Any]?) {
        isLoading = true
        
        // API 요청 데이터
        var requestData: [String: Any] = [
            "identity_token": identityToken
        ]
        
        if let userData = userData {
            requestData["user"] = userData
        }
        
        // JSON으로 변환
        guard let jsonData = try? JSONSerialization.data(withJSONObject: requestData) else {
            errorMessage = "데이터 변환 실패"
            isLoading = false
            return
        }
        
        // API 호출
        var request = URLRequest(url: URL(string: "https://api.yourdomain.com/api/auth/apple")!)
        request.httpMethod = "POST"
        request.httpBody = jsonData
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            DispatchQueue.main.async {
                isLoading = false
                
                if let error = error {
                    errorMessage = "네트워크 오류: \(error.localizedDescription)"
                    return
                }
                
                guard let data = data else {
                    errorMessage = "응답 데이터 없음"
                    return
                }
                
                // 응답 파싱
                if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    if let accessToken = json["access_token"] as? String {
                        // 로그인 성공
                        print("Access Token: \(accessToken)")
                        // UserDefaults에 저장하거나 Keychain에 저장
                        UserDefaults.standard.set(accessToken, forKey: "access_token")
                        
                        // 메인 화면으로 이동
                        // ...
                    } else if let error = json["error"] as? String {
                        errorMessage = "로그인 실패: \(error)"
                    }
                }
            }
        }.resume()
    }
}
```

### 7.2 웹 클라이언트 (JavaScript)

**Apple 로그인 버튼 (HTML + JS):**

```html
<!-- login.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Apple 로그인</title>
    <meta name="appleid-signin-client-id" content="com.yourcompany.yourapp.service">
    <meta name="appleid-signin-scope" content="name email">
    <meta name="appleid-signin-redirect-uri" content="https://yourdomain.com/api/auth/apple/callback">
    <meta name="appleid-signin-state" content="signin">
    <meta name="appleid-signin-use-popup" content="true">
</head>
<body>
    <div id="appleid-signin" data-color="black" data-border="true" data-type="sign in"></div>
    
    <script type="text/javascript" src="https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js"></script>
    <script>
        // Apple 로그인 이벤트 리스너
        document.addEventListener('AppleIDSignInOnSuccess', (event) => {
            const data = event.detail.authorization;
            
            // Identity Token
            const identityToken = data.id_token;
            
            // 사용자 정보 (최초 로그인 시에만)
            const user = data.user ? {
                name: data.user.name,
                email: data.user.email
            } : null;
            
            // 서버로 전송
            fetch('https://api.yourdomain.com/api/auth/apple', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    identity_token: identityToken,
                    user: user
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.access_token) {
                    // 로그인 성공
                    localStorage.setItem('access_token', data.access_token);
                    window.location.href = '/dashboard';
                } else {
                    alert('로그인 실패: ' + (data.error || '알 수 없는 오류'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('네트워크 오류가 발생했습니다');
            });
        });
        
        document.addEventListener('AppleIDSignInOnFailure', (event) => {
            console.error('Apple 로그인 실패:', event.detail.error);
            alert('Apple 로그인에 실패했습니다');
        });
    </script>
</body>
</html>
```

**React 예제:**

```jsx
// AppleLoginButton.jsx
import React from 'react';
import AppleLogin from 'react-apple-login';

const AppleLoginButton = () => {
  const handleAppleResponse = (response) => {
    const { authorization } = response;
    
    // 서버로 전송
    fetch('https://api.yourdomain.com/api/auth/apple', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        identity_token: authorization.id_token,
        user: response.user || null,
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.access_token) {
          localStorage.setItem('access_token', data.access_token);
          window.location.href = '/dashboard';
        }
      })
      .catch((error) => {
        console.error('Error:', error);
      });
  };

  return (
    <AppleLogin
      clientId="com.yourcompany.yourapp.service"
      redirectURI="https://yourdomain.com/api/auth/apple/callback"
      usePopup={true}
      callback={handleAppleResponse}
      scope="name email"
      responseMode="form_post"
      render={(props) => (
        <button onClick={props.onClick} className="apple-login-btn">
          <img src="/apple-logo.svg" alt="Apple" />
          Sign in with Apple
        </button>
      )}
    />
  );
};

export default AppleLoginButton;
```

---

## 8. 보안 및 에러 처리

### 8.1 보안 체크리스트

```python
# authentication/security.py
from functools import wraps
from django.http import JsonResponse
from .jwt_utils import decode_access_token


def require_auth(view_func):
    """
    인증 데코레이터
    
    Usage:
        @require_auth
        def my_view(request):
            user_id = request.user_id
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({
                'error': 'unauthorized',
                'detail': 'Authorization 헤더가 필요합니다'
            }, status=401)
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = decode_access_token(token)
            request.user_id = payload.get('user_id')
            request.user_email = payload.get('email')
            return view_func(request, *args, **kwargs)
        
        except Exception as e:
            return JsonResponse({
                'error': 'invalid_token',
                'detail': str(e)
            }, status=401)
    
    return wrapper
```

**보안 체크리스트:**

```
✅ JWT Secret Key를 환경 변수로 관리
✅ Apple Private Key 파일을 Git에 커밋하지 않기
✅ HTTPS 필수 (개발 환경 제외)
✅ CORS 설정 정확히 하기
✅ Rate Limiting 적용 (DDoS 방지)
✅ 토큰 만료 시간 설정 (7일 권장)
✅ Refresh Token 구현 (선택)
```

### 8.2 에러 처리

```python
# authentication/exceptions.py
class AppleAuthException(Exception):
    """Apple 인증 관련 예외"""
    pass


class InvalidTokenException(AppleAuthException):
    """유효하지 않은 토큰"""
    pass


class UserInfoMissingException(AppleAuthException):
    """사용자 정보 누락"""
    pass


# 에러 핸들러
@router.exception_handler(AppleAuthException)
def handle_apple_auth_exception(request, exc):
    return JsonResponse({
        'error': 'apple_auth_error',
        'detail': str(exc)
    }, status=400)
```

### 8.3 로깅

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/apple_auth.log',
        },
    },
    'loggers': {
        'authentication': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# authentication/api.py에서 사용
import logging

logger = logging.getLogger('authentication')

@router.post('/apple')
def apple_login(request, data: AppleLoginRequest):
    logger.info(f'Apple login attempt')
    
    try:
        # ...
        logger.info(f'Apple login success: {user.email}')
    except Exception as e:
        logger.error(f'Apple login failed: {str(e)}')
```

---

## 9. 테스트 및 디버깅

### 9.1 테스트 케이스

```python
# authentication/tests.py
from django.test import TestCase, Client
from accounts.models import User
import jwt


class AppleLoginTestCase(TestCase):
    def setUp(self):
        self.client = Client()
    
    def test_apple_login_success(self):
        """정상 로그인 테스트"""
        # Mock Identity Token 생성 (실제로는 Apple에서 발급)
        # 주의: 실제 테스트에서는 Mock이 필요합니다
        
        response = self.client.post('/api/auth/apple', {
            'identity_token': 'mock_token',
            'user': {
                'name': {'firstName': 'John', 'lastName': 'Doe'},
                'email': 'john@example.com'
            }
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.json())
    
    def test_apple_login_invalid_token(self):
        """유효하지 않은 토큰 테스트"""
        response = self.client.post('/api/auth/apple', {
            'identity_token': 'invalid_token'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
```

### 9.2 디버깅 팁

```python
# 1. Identity Token 내용 확인
import jwt

identity_token = "eyJraWQiOiI4NkQ4..."
decoded = jwt.decode(identity_token, options={"verify_signature": False})
print(decoded)

# 2. Apple Public Keys 확인
import requests
response = requests.get('https://appleid.apple.com/auth/keys')
print(response.json())

# 3. 토큰 헤더 확인
header = jwt.get_unverified_header(identity_token)
print(f"kid: {header.get('kid')}")
print(f"alg: {header.get('alg')}")
```

**자주 발생하는 문제:**

| 에러 | 원인 | 해결 방법 |
|------|------|----------|
| `Invalid audience` | Client ID가 틀림 | Service ID 또는 App ID 확인 |
| `Invalid signature` | Public Key가 틀림 | Apple Keys 다시 가져오기 |
| `Token expired` | 토큰이 만료됨 | 클라이언트에서 새로 발급 |
| `User info missing` | 2회차 이상 로그인 | user 파라미터 optional 처리 |

---

## 10. 프로덕션 배포

### 10.1 환경 변수 설정

```bash
# .env.production
DEBUG=False
SECRET_KEY=your-super-secret-key-here-change-this
ALLOWED_HOSTS=api.yourdomain.com,yourdomain.com

APPLE_TEAM_ID=XYZ1234ABC
APPLE_CLIENT_ID=com.yourcompany.yourapp
APPLE_SERVICE_ID=com.yourcompany.yourapp.service
APPLE_KEY_ID=AB12CD34EF
APPLE_PRIVATE_KEY_PATH=config/apple/AuthKey_AB12CD34EF.p8

JWT_SECRET_KEY=another-super-secret-jwt-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_LIFETIME=604800

DATABASE_URL=postgresql://user:password@localhost/dbname
REDIS_URL=redis://localhost:6379/0
```

### 10.2 HTTPS 설정

```python
# settings.py (프로덕션)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
```

### 10.3 배포 체크리스트

```
프로덕션 배포 전 확인사항:

✅ Apple Developer에 Return URL 등록 확인
✅ 도메인 HTTPS 적용 확인
✅ 환경 변수 모두 설정 확인
✅ Private Key 파일 업로드 (Git 제외)
✅ CORS 설정 프로덕션 도메인으로 변경
✅ Rate Limiting 적용
✅ 로깅 설정 확인
✅ 데이터베이스 백업 설정
✅ 모니터링 도구 연동 (Sentry 등)
✅ iOS 앱 App Store 제출 시 Apple 로그인 포함
```

### 10.4 성능 최적화

```python
# 1. Apple Public Keys 캐싱 (Redis)
from django.core.cache import cache

def get_apple_public_keys_cached():
    keys = cache.get('apple_public_keys')
    
    if not keys:
        response = requests.get('https://appleid.apple.com/auth/keys')
        keys = response.json()
        cache.set('apple_public_keys', keys, timeout=3600)  # 1시간
    
    return keys

# 2. DB 쿼리 최적화
user = User.objects.select_related().get(apple_user_id=apple_user_id)

# 3. 비동기 처리 (Celery)
from celery import shared_task

@shared_task
def send_welcome_email_async(user_id):
    user = User.objects.get(id=user_id)
    send_welcome_email(user)
```

---

## 결론

### 핵심 요약

Django Ninja로 Apple 소셜 로그인을 구현하는 전체 과정을 살펴보았습니다.

**구현 단계:**

1. ✅ **Apple Developer 설정** - App ID, Service ID, Key 생성
2. ✅ **Django 프로젝트** - User 모델, 패키지 설치
3. ✅ **JWT 검증** - Apple Public Keys로 토큰 검증
4. ✅ **API 구현** - Django Ninja 엔드포인트
5. ✅ **클라이언트 연동** - iOS, Web 로그인 버튼
6. ✅ **보안 처리** - 인증, 에러 핸들링, 로깅
7. ✅ **배포** - 프로덕션 설정, HTTPS, 모니터링

**주요 포인트:**

- 🔐 **보안**: Apple Private Key는 절대 노출하지 않기
- 📧 **Relay Email**: 사용자가 이메일 숨기기 선택 가능
- 🔄 **일회성 정보**: 이름, 이메일은 최초 로그인 시에만 제공
- ✅ **검증 필수**: Identity Token을 반드시 서버에서 검증
- 🌐 **HTTPS 필수**: 로컬 개발 외에는 반드시 HTTPS 사용

### 추가 기능

**고급 구현:**

```python
# 1. Refresh Token 구현
def create_refresh_token(user_id):
    # ...

# 2. 회원 탈퇴 처리
@router.post('/revoke-apple')
def revoke_apple_login(request):
    # Apple 연동 해제 API 호출
    # ...

# 3. 다중 소셜 로그인
# Google, Facebook과 함께 구현
```

### 참고 자료

- [Sign in with Apple 공식 문서](https://developer.apple.com/sign-in-with-apple/)
- [Apple Identity Token 검증](https://developer.apple.com/documentation/sign_in_with_apple/sign_in_with_apple_rest_api/verifying_a_user)
- [Django Ninja 공식 문서](https://django-ninja.rest-framework.com/)
- [PyJWT 문서](https://pyjwt.readthedocs.io/)

**문제 발생 시:**

- Apple Developer Forums
- Stack Overflow
- GitHub Issues (django-ninja)

이제 여러분의 서비스에 Apple 소셜 로그인을 구현해보세요! 🚀

---

**질문이나 피드백**은 댓글로 남겨주세요! 😊
