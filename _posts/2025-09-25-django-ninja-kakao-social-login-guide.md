---
layout: post
title: "Django Ninja로 구현하는 카카오 소셜 로그인 완벽 가이드"
date: 2025-09-25 10:00:00 +0900
categories: [Django, Authentication]
tags: [django-ninja, kakao login, social login, oauth2, rest api, authentication]
description: "Django Ninja를 사용하여 카카오 소셜 로그인을 구현하는 완벽한 가이드. OAuth 2.0 플로우부터 JWT 토큰 발급까지 전체 과정을 실무 중심으로 설명합니다."
author: "updaun"
image: "/assets/img/posts/2025-09-25-django-ninja-kakao-social-login-guide.webp"
---

## 개요

모던 웹 애플리케이션에서 소셜 로그인은 필수 기능이 되었습니다. 특히 한국에서 카카오 로그인은 사용자 편의성과 신뢰성 면에서 가장 인기 있는 인증 방식 중 하나입니다. 이 포스트에서는 Django Ninja를 사용하여 카카오 소셜 로그인을 구현하는 전체 과정을 설명하겠습니다.

## 1. 카카오 소셜 로그인이 필요한 이유

### 1.1 사용자 편의성
- **간편한 가입/로그인**: 복잡한 회원가입 과정 생략
- **신뢰할 수 있는 인증**: 카카오의 검증된 인증 시스템 활용
- **개인정보 최소화**: 필요한 정보만 선택적으로 수집

### 1.2 개발자 관점
- **개발 시간 단축**: 인증 로직 구현 시간 절약
- **보안성 향상**: OAuth 2.0 표준 프로토콜 사용
- **유지보수 용이**: 카카오에서 보안 업데이트 관리

## 2. 카카오 개발자 센터 설정

### 2.1 애플리케이션 등록

```bash
# 1. 카카오 개발자 센터 접속
https://developers.kakao.com/

# 2. 내 애플리케이션 > 애플리케이션 추가하기
# 3. 앱 이름, 사업자명 입력
```

### 2.2 플랫폼 설정

```javascript
// Web 플랫폼 등록
Site Domain: http://localhost:8000  // 개발환경
Site Domain: https://yourdomain.com  // 운영환경
```

### 2.3 카카오 로그인 활성화

```yaml
# 제품 설정 > 카카오 로그인
카카오 로그인 활성화: ON
Redirect URI: http://localhost:8000/api/auth/kakao/callback
```

### 2.4 동의항목 설정

```yaml
# 개인정보보호 > 개인정보
닉네임: 필수 동의
프로필 사진: 선택 동의
카카오계정(이메일): 선택 동의
```

## 3. Django 프로젝트 설정

### 3.1 필요한 패키지 설치

```bash
pip install django-ninja
pip install requests
pip install PyJWT
pip install python-decouple
```

### 3.2 환경변수 설정

```python
# .env 파일
KAKAO_CLIENT_ID=your_kakao_rest_api_key
KAKAO_CLIENT_SECRET=your_kakao_client_secret
KAKAO_REDIRECT_URI=http://localhost:8000/api/auth/kakao/callback
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 3.3 Django 설정

```python
# settings.py
from decouple import config

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ninja',
    'accounts',  # 인증 앱
]

# 카카오 로그인 설정
KAKAO_CLIENT_ID = config('KAKAO_CLIENT_ID')
KAKAO_CLIENT_SECRET = config('KAKAO_CLIENT_SECRET')
KAKAO_REDIRECT_URI = config('KAKAO_REDIRECT_URI')

# JWT 설정
JWT_SECRET_KEY = config('JWT_SECRET_KEY')
JWT_ALGORITHM = config('JWT_ALGORITHM', default='HS256')
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = config('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', default=30, cast=int)
JWT_REFRESH_TOKEN_EXPIRE_DAYS = config('JWT_REFRESH_TOKEN_EXPIRE_DAYS', default=7, cast=int)

# CORS 설정 (프론트엔드 연동 시)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React 개발서버
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True
```

## 4. 사용자 모델 설정

### 4.1 확장된 User 모델

```python
# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """확장된 사용자 모델"""
    
    # 카카오 연동 정보
    kakao_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    profile_image = models.URLField(blank=True, null=True)
    
    # 추가 사용자 정보
    nickname = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[('male', '남성'), ('female', '여성')],
        blank=True
    )
    
    # 메타데이터
    is_social_user = models.BooleanField(default=False)
    social_provider = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.username


class RefreshToken(models.Model):
    """JWT 리프레시 토큰 관리"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refresh_tokens')
    token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'refresh_tokens'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}'s refresh token"
```

### 4.2 모델 등록

```python
# settings.py에 추가
AUTH_USER_MODEL = 'accounts.User'
```

```bash
# 마이그레이션 실행
python manage.py makemigrations
python manage.py migrate
```

## 5. JWT 유틸리티 구현

### 5.1 JWT 헬퍼 함수

```python
# accounts/jwt_utils.py
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import RefreshToken

User = get_user_model()


class JWTManager:
    """JWT 토큰 관리 클래스"""
    
    @staticmethod
    def generate_tokens(user):
        """액세스 토큰과 리프레시 토큰 생성"""
        
        # 액세스 토큰 생성
        access_payload = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'exp': datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        
        access_token = jwt.encode(
            access_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        # 리프레시 토큰 생성
        refresh_payload = {
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            'iat': datetime.utcnow(),
            'type': 'refresh'
        }
        
        refresh_token = jwt.encode(
            refresh_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        # 리프레시 토큰 DB 저장
        RefreshToken.objects.create(
            user=user,
            token=refresh_token,
            expires_at=datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        )
        
        return access_token, refresh_token
    
    @staticmethod
    def verify_token(token, token_type='access'):
        """토큰 검증"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            if payload.get('type') != token_type:
                return None
            
            return payload
        
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def refresh_access_token(refresh_token):
        """리프레시 토큰으로 액세스 토큰 갱신"""
        payload = JWTManager.verify_token(refresh_token, 'refresh')
        
        if not payload:
            return None
        
        # DB에서 리프레시 토큰 확인
        try:
            token_obj = RefreshToken.objects.get(
                token=refresh_token,
                is_active=True,
                expires_at__gt=datetime.utcnow()
            )
            user = token_obj.user
        except RefreshToken.DoesNotExist:
            return None
        
        # 새 액세스 토큰 생성
        access_payload = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'exp': datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        
        access_token = jwt.encode(
            access_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return access_token
```

## 6. 카카오 API 서비스 구현

### 6.1 카카오 인증 서비스

```python
# accounts/kakao_service.py
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from typing import Optional, Dict, Any

User = get_user_model()


class KakaoAuthService:
    """카카오 인증 서비스"""
    
    KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
    KAKAO_USER_INFO_URL = "https://kapi.kakao.com/v2/user/me"
    
    @classmethod
    def get_access_token(cls, authorization_code: str) -> Optional[str]:
        """인가 코드로 액세스 토큰 획득"""
        
        data = {
            'grant_type': 'authorization_code',
            'client_id': settings.KAKAO_CLIENT_ID,
            'client_secret': settings.KAKAO_CLIENT_SECRET,
            'redirect_uri': settings.KAKAO_REDIRECT_URI,
            'code': authorization_code,
        }
        
        try:
            response = requests.post(cls.KAKAO_TOKEN_URL, data=data, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            return token_data.get('access_token')
        
        except requests.exceptions.RequestException as e:
            print(f"카카오 토큰 요청 실패: {e}")
            return None
    
    @classmethod
    def get_user_info(cls, access_token: str) -> Optional[Dict[str, Any]]:
        """액세스 토큰으로 사용자 정보 조회"""
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'
        }
        
        try:
            response = requests.get(cls.KAKAO_USER_INFO_URL, headers=headers, timeout=10)
            response.raise_for_status()
            
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"카카오 사용자 정보 요청 실패: {e}")
            return None
    
    @classmethod
    def create_or_update_user(cls, kakao_user_info: Dict[str, Any]) -> User:
        """카카오 사용자 정보로 User 생성 또는 업데이트"""
        
        kakao_id = str(kakao_user_info['id'])
        kakao_account = kakao_user_info.get('kakao_account', {})
        profile = kakao_account.get('profile', {})
        
        # 기본 정보 추출
        email = kakao_account.get('email', '')
        nickname = profile.get('nickname', f'user_{kakao_id}')
        profile_image_url = profile.get('profile_image_url', '')
        
        # 사용자 생성 또는 조회
        user, created = User.objects.get_or_create(
            kakao_id=kakao_id,
            defaults={
                'username': f'kakao_{kakao_id}',
                'email': email,
                'nickname': nickname,
                'profile_image': profile_image_url,
                'is_social_user': True,
                'social_provider': 'kakao',
                'is_active': True,
            }
        )
        
        # 기존 사용자 정보 업데이트
        if not created:
            user.email = email or user.email
            user.nickname = nickname or user.nickname
            user.profile_image = profile_image_url or user.profile_image
            user.save()
        
        return user
    
    @classmethod
    def process_kakao_login(cls, authorization_code: str) -> Optional[User]:
        """카카오 로그인 전체 프로세스 처리"""
        
        # 1. 액세스 토큰 획득
        access_token = cls.get_access_token(authorization_code)
        if not access_token:
            return None
        
        # 2. 사용자 정보 조회
        user_info = cls.get_user_info(access_token)
        if not user_info:
            return None
        
        # 3. 사용자 생성 또는 업데이트
        user = cls.create_or_update_user(user_info)
        
        return user
```

## 7. Django Ninja API 구현

### 7.1 인증 스키마 정의

```python
# accounts/schemas.py
from ninja import Schema
from typing import Optional
from datetime import datetime


class KakaoLoginUrlResponse(Schema):
    """카카오 로그인 URL 응답"""
    login_url: str


class TokenResponse(Schema):
    """토큰 응답"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class UserProfileResponse(Schema):
    """사용자 프로필 응답"""
    id: int
    username: str
    email: str
    nickname: str
    profile_image: Optional[str] = None
    is_social_user: bool
    social_provider: str
    created_at: datetime


class RefreshTokenRequest(Schema):
    """리프레시 토큰 요청"""
    refresh_token: str


class ErrorResponse(Schema):
    """에러 응답"""
    error: str
    message: str
```

### 7.2 인증 클래스 구현

```python
# accounts/auth.py
from ninja.security import HttpBearer
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from .jwt_utils import JWTManager

User = get_user_model()


class JWTAuth(HttpBearer):
    """JWT 인증 클래스"""
    
    def authenticate(self, request: HttpRequest, token: str):
        """JWT 토큰 인증"""
        payload = JWTManager.verify_token(token, 'access')
        
        if not payload:
            return None
        
        try:
            user = User.objects.get(id=payload['user_id'])
            return user
        except User.DoesNotExist:
            return None


# 인증 인스턴스 생성
jwt_auth = JWTAuth()
```

### 7.3 카카오 인증 API 구현

```python
# accounts/api.py
from ninja import Router
from ninja.responses import Response
from django.conf import settings
from django.http import HttpRequest
from urllib.parse import urlencode
from .schemas import (
    KakaoLoginUrlResponse, 
    TokenResponse, 
    UserProfileResponse, 
    RefreshTokenRequest,
    ErrorResponse
)
from .kakao_service import KakaoAuthService
from .jwt_utils import JWTManager
from .auth import jwt_auth

auth_router = Router()


@auth_router.get("/kakao/login-url", response=KakaoLoginUrlResponse)
def get_kakao_login_url(request: HttpRequest):
    """카카오 로그인 URL 생성"""
    
    params = {
        'client_id': settings.KAKAO_CLIENT_ID,
        'redirect_uri': settings.KAKAO_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'profile_nickname,profile_image,account_email',
    }
    
    login_url = f"https://kauth.kakao.com/oauth/authorize?{urlencode(params)}"
    
    return {
        "login_url": login_url
    }


@auth_router.post("/kakao/callback", response={200: TokenResponse, 400: ErrorResponse})
def kakao_callback(request: HttpRequest, code: str):
    """카카오 로그인 콜백 처리"""
    
    try:
        # 카카오 로그인 처리
        user = KakaoAuthService.process_kakao_login(code)
        
        if not user:
            return 400, {
                "error": "KAKAO_LOGIN_FAILED",
                "message": "카카오 로그인에 실패했습니다."
            }
        
        # JWT 토큰 생성
        access_token, refresh_token = JWTManager.generate_tokens(user)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    except Exception as e:
        return 400, {
            "error": "INTERNAL_ERROR",
            "message": f"로그인 처리 중 오류가 발생했습니다: {str(e)}"
        }


@auth_router.post("/refresh", response={200: TokenResponse, 400: ErrorResponse})
def refresh_token(request: HttpRequest, data: RefreshTokenRequest):
    """액세스 토큰 갱신"""
    
    access_token = JWTManager.refresh_access_token(data.refresh_token)
    
    if not access_token:
        return 400, {
            "error": "INVALID_REFRESH_TOKEN",
            "message": "유효하지 않은 리프레시 토큰입니다."
        }
    
    return {
        "access_token": access_token,
        "refresh_token": data.refresh_token,  # 기존 리프레시 토큰 유지
        "token_type": "Bearer",
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@auth_router.get("/profile", auth=jwt_auth, response=UserProfileResponse)
def get_user_profile(request: HttpRequest):
    """사용자 프로필 조회"""
    
    user = request.auth
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "nickname": user.nickname,
        "profile_image": user.profile_image,
        "is_social_user": user.is_social_user,
        "social_provider": user.social_provider,
        "created_at": user.created_at
    }


@auth_router.post("/logout", auth=jwt_auth)
def logout(request: HttpRequest):
    """로그아웃 (리프레시 토큰 무효화)"""
    
    user = request.auth
    
    # 사용자의 모든 리프레시 토큰 비활성화
    from .models import RefreshToken
    RefreshToken.objects.filter(user=user, is_active=True).update(is_active=False)
    
    return {"message": "로그아웃되었습니다."}
```

## 8. 메인 API 연결

### 8.1 Django Ninja API 설정

```python
# main/api.py
from ninja import NinjaAPI
from accounts.api import auth_router

api = NinjaAPI(
    title="Django Ninja with Kakao Login API",
    version="1.0.0",
    description="카카오 소셜 로그인이 구현된 Django Ninja API"
)

# 인증 라우터 등록
api.add_router("/auth/", auth_router)


@api.get("/health")
def health_check(request):
    """헬스 체크"""
    return {"status": "healthy"}


# 보호된 API 예시
from accounts.auth import jwt_auth

@api.get("/protected", auth=jwt_auth)
def protected_endpoint(request):
    """JWT 인증이 필요한 보호된 엔드포인트"""
    user = request.auth
    return {
        "message": f"안녕하세요, {user.nickname}님!",
        "user_id": user.id
    }
```

### 8.2 URL 설정

```python
# urls.py
from django.contrib import admin
from django.urls import path
from main.api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
```

## 9. 프론트엔드 연동 예시

### 9.1 JavaScript 클라이언트

```javascript
// kakaoAuth.js
class KakaoAuthClient {
    constructor(baseURL = 'http://localhost:8000/api') {
        this.baseURL = baseURL;
        this.accessToken = localStorage.getItem('access_token');
        this.refreshToken = localStorage.getItem('refresh_token');
    }
    
    // 카카오 로그인 URL 획득
    async getKakaoLoginUrl() {
        const response = await fetch(`${this.baseURL}/auth/kakao/login-url`);
        const data = await response.json();
        return data.login_url;
    }
    
    // 카카오 로그인 처리
    async processKakaoCallback(code) {
        const response = await fetch(`${this.baseURL}/auth/kakao/callback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ code })
        });
        
        if (response.ok) {
            const tokens = await response.json();
            this.setTokens(tokens.access_token, tokens.refresh_token);
            return tokens;
        }
        
        throw new Error('카카오 로그인 실패');
    }
    
    // 토큰 저장
    setTokens(accessToken, refreshToken) {
        this.accessToken = accessToken;
        this.refreshToken = refreshToken;
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
    }
    
    // 인증된 API 요청
    async authenticatedRequest(url, options = {}) {
        const headers = {
            'Authorization': `Bearer ${this.accessToken}`,
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        let response = await fetch(`${this.baseURL}${url}`, {
            ...options,
            headers
        });
        
        // 토큰 만료 시 갱신 시도
        if (response.status === 401) {
            const refreshed = await this.refreshAccessToken();
            if (refreshed) {
                headers['Authorization'] = `Bearer ${this.accessToken}`;
                response = await fetch(`${this.baseURL}${url}`, {
                    ...options,
                    headers
                });
            }
        }
        
        return response;
    }
    
    // 액세스 토큰 갱신
    async refreshAccessToken() {
        if (!this.refreshToken) return false;
        
        try {
            const response = await fetch(`${this.baseURL}/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    refresh_token: this.refreshToken
                })
            });
            
            if (response.ok) {
                const tokens = await response.json();
                this.setTokens(tokens.access_token, tokens.refresh_token);
                return true;
            }
        } catch (error) {
            console.error('토큰 갱신 실패:', error);
        }
        
        return false;
    }
    
    // 사용자 프로필 조회
    async getUserProfile() {
        const response = await this.authenticatedRequest('/auth/profile');
        return response.json();
    }
    
    // 로그아웃
    async logout() {
        await this.authenticatedRequest('/auth/logout', { method: 'POST' });
        this.clearTokens();
    }
    
    // 토큰 삭제
    clearTokens() {
        this.accessToken = null;
        this.refreshToken = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    }
}

// 사용 예시
const authClient = new KakaoAuthClient();

// 카카오 로그인 버튼 클릭 처리
document.getElementById('kakao-login-btn').addEventListener('click', async () => {
    const loginUrl = await authClient.getKakaoLoginUrl();
    window.location.href = loginUrl;
});

// 카카오 콜백 페이지에서 처리
const urlParams = new URLSearchParams(window.location.search);
const code = urlParams.get('code');

if (code) {
    authClient.processKakaoCallback(code)
        .then(tokens => {
            console.log('로그인 성공:', tokens);
            // 메인 페이지로 리다이렉트
            window.location.href = '/dashboard';
        })
        .catch(error => {
            console.error('로그인 실패:', error);
        });
}
```

### 9.2 React 컴포넌트 예시

```jsx
// KakaoLogin.jsx
import React, { useState, useEffect } from 'react';
import { KakaoAuthClient } from './kakaoAuth';

const KakaoLogin = () => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(false);
    const authClient = new KakaoAuthClient();

    useEffect(() => {
        // 페이지 로드 시 사용자 정보 확인
        checkUserStatus();
        
        // 카카오 콜백 처리
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        
        if (code) {
            handleKakaoCallback(code);
        }
    }, []);

    const checkUserStatus = async () => {
        try {
            const profile = await authClient.getUserProfile();
            setUser(profile);
        } catch (error) {
            console.log('사용자 정보 없음');
        }
    };

    const handleKakaoLogin = async () => {
        setLoading(true);
        try {
            const loginUrl = await authClient.getKakaoLoginUrl();
            window.location.href = loginUrl;
        } catch (error) {
            console.error('로그인 URL 생성 실패:', error);
            setLoading(false);
        }
    };

    const handleKakaoCallback = async (code) => {
        setLoading(true);
        try {
            await authClient.processKakaoCallback(code);
            const profile = await authClient.getUserProfile();
            setUser(profile);
            
            // URL 정리
            window.history.replaceState({}, document.title, window.location.pathname);
        } catch (error) {
            console.error('카카오 로그인 처리 실패:', error);
        }
        setLoading(false);
    };

    const handleLogout = async () => {
        try {
            await authClient.logout();
            setUser(null);
        } catch (error) {
            console.error('로그아웃 실패:', error);
        }
    };

    if (loading) {
        return <div className="loading">로그인 처리 중...</div>;
    }

    return (
        <div className="kakao-login">
            {user ? (
                <div className="user-info">
                    <img src={user.profile_image} alt="프로필" />
                    <h3>{user.nickname}님 환영합니다!</h3>
                    <p>이메일: {user.email}</p>
                    <button onClick={handleLogout}>로그아웃</button>
                </div>
            ) : (
                <button 
                    className="kakao-login-btn"
                    onClick={handleKakaoLogin}
                    disabled={loading}
                >
                    카카오로 로그인
                </button>
            )}
        </div>
    );
};

export default KakaoLogin;
```

## 10. 테스트 구현

### 10.1 유닛 테스트

```python
# accounts/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, Mock
from .kakao_service import KakaoAuthService
from .jwt_utils import JWTManager

User = get_user_model()


class KakaoAuthServiceTest(TestCase):
    """카카오 인증 서비스 테스트"""
    
    def setUp(self):
        self.mock_kakao_user_info = {
            'id': 12345678,
            'kakao_account': {
                'email': 'test@example.com',
                'profile': {
                    'nickname': '테스트사용자',
                    'profile_image_url': 'https://example.com/profile.jpg'
                }
            }
        }
    
    @patch('accounts.kakao_service.requests.post')
    def test_get_access_token_success(self, mock_post):
        """액세스 토큰 획득 성공 테스트"""
        mock_response = Mock()
        mock_response.json.return_value = {'access_token': 'test_token'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        token = KakaoAuthService.get_access_token('test_code')
        
        self.assertEqual(token, 'test_token')
        mock_post.assert_called_once()
    
    @patch('accounts.kakao_service.requests.get')
    def test_get_user_info_success(self, mock_get):
        """사용자 정보 조회 성공 테스트"""
        mock_response = Mock()
        mock_response.json.return_value = self.mock_kakao_user_info
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        user_info = KakaoAuthService.get_user_info('test_token')
        
        self.assertEqual(user_info, self.mock_kakao_user_info)
        mock_get.assert_called_once()
    
    def test_create_or_update_user(self):
        """사용자 생성/업데이트 테스트"""
        user = KakaoAuthService.create_or_update_user(self.mock_kakao_user_info)
        
        self.assertEqual(user.kakao_id, '12345678')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.nickname, '테스트사용자')
        self.assertTrue(user.is_social_user)
        self.assertEqual(user.social_provider, 'kakao')


class JWTManagerTest(TestCase):
    """JWT 매니저 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
    
    def test_generate_tokens(self):
        """토큰 생성 테스트"""
        access_token, refresh_token = JWTManager.generate_tokens(self.user)
        
        self.assertIsNotNone(access_token)
        self.assertIsNotNone(refresh_token)
        
        # 액세스 토큰 검증
        access_payload = JWTManager.verify_token(access_token, 'access')
        self.assertEqual(access_payload['user_id'], self.user.id)
        
        # 리프레시 토큰 검증
        refresh_payload = JWTManager.verify_token(refresh_token, 'refresh')
        self.assertEqual(refresh_payload['user_id'], self.user.id)
    
    def test_refresh_access_token(self):
        """액세스 토큰 갱신 테스트"""
        _, refresh_token = JWTManager.generate_tokens(self.user)
        
        new_access_token = JWTManager.refresh_access_token(refresh_token)
        
        self.assertIsNotNone(new_access_token)
        
        # 새 액세스 토큰 검증
        payload = JWTManager.verify_token(new_access_token, 'access')
        self.assertEqual(payload['user_id'], self.user.id)
```

### 10.2 API 테스트

```python
# accounts/test_api.py
from django.test import TestCase
from ninja.testing import TestClient
from unittest.mock import patch
from main.api import api


class KakaoAuthAPITest(TestCase):
    """카카오 인증 API 테스트"""
    
    def setUp(self):
        self.client = TestClient(api)
    
    def test_get_kakao_login_url(self):
        """카카오 로그인 URL 생성 테스트"""
        response = self.client.get("/auth/kakao/login-url")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('login_url', data)
        self.assertIn('kauth.kakao.com', data['login_url'])
    
    @patch('accounts.api.KakaoAuthService.process_kakao_login')
    @patch('accounts.api.JWTManager.generate_tokens')
    def test_kakao_callback_success(self, mock_generate_tokens, mock_process_login):
        """카카오 콜백 성공 테스트"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Mock 설정
        mock_user = User(id=1, username='testuser')
        mock_process_login.return_value = mock_user
        mock_generate_tokens.return_value = ('access_token', 'refresh_token')
        
        response = self.client.post("/auth/kakao/callback", json={"code": "test_code"})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['access_token'], 'access_token')
        self.assertEqual(data['refresh_token'], 'refresh_token')
    
    def test_kakao_callback_failure(self):
        """카카오 콜백 실패 테스트"""
        with patch('accounts.api.KakaoAuthService.process_kakao_login', return_value=None):
            response = self.client.post("/auth/kakao/callback", json={"code": "invalid_code"})
            
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertEqual(data['error'], 'KAKAO_LOGIN_FAILED')
```

## 11. 보안 고려사항

### 11.1 토큰 보안

```python
# accounts/security.py
import secrets
from django.conf import settings
from django.core.cache import cache
from datetime import datetime, timedelta


class SecurityManager:
    """보안 관리 클래스"""
    
    @staticmethod
    def generate_secure_secret():
        """안전한 시크릿 키 생성"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def is_token_blacklisted(token):
        """토큰 블랙리스트 확인"""
        return cache.get(f"blacklisted_token:{token}", False)
    
    @staticmethod
    def blacklist_token(token, expire_time):
        """토큰 블랙리스트 추가"""
        cache.set(
            f"blacklisted_token:{token}",
            True,
            timeout=expire_time
        )
    
    @staticmethod
    def validate_redirect_uri(redirect_uri):
        """리다이렉트 URI 검증"""
        allowed_domains = [
            'localhost:3000',
            'localhost:8000',
            'yourdomain.com'
        ]
        
        from urllib.parse import urlparse
        parsed_uri = urlparse(redirect_uri)
        
        return parsed_uri.netloc in allowed_domains
```

### 11.2 Rate Limiting

```python
# accounts/middleware.py
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
import time


class RateLimitMiddleware(MiddlewareMixin):
    """API 요청 제한 미들웨어"""
    
    def process_request(self, request):
        if request.path.startswith('/api/auth/'):
            client_ip = self.get_client_ip(request)
            
            # 분당 10회 제한
            key = f"rate_limit:{client_ip}"
            current_requests = cache.get(key, 0)
            
            if current_requests >= 10:
                return JsonResponse({
                    'error': 'RATE_LIMIT_EXCEEDED',
                    'message': '요청 횟수 제한을 초과했습니다.'
                }, status=429)
            
            cache.set(key, current_requests + 1, 60)  # 1분 후 초기화
        
        return None
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

## 12. 모니터링 및 로깅

### 12.1 로깅 설정

```python
# settings.py에 추가
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/kakao_auth.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'accounts': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 12.2 로깅 구현

```python
# accounts/kakao_service.py에 로깅 추가
import logging

logger = logging.getLogger(__name__)


class KakaoAuthService:
    """카카오 인증 서비스 (로깅 추가)"""
    
    @classmethod
    def process_kakao_login(cls, authorization_code: str) -> Optional[User]:
        """카카오 로그인 전체 프로세스 처리"""
        
        logger.info(f"카카오 로그인 시작: code={authorization_code[:10]}...")
        
        try:
            # 1. 액세스 토큰 획득
            access_token = cls.get_access_token(authorization_code)
            if not access_token:
                logger.error("카카오 액세스 토큰 획득 실패")
                return None
            
            logger.info("카카오 액세스 토큰 획득 성공")
            
            # 2. 사용자 정보 조회
            user_info = cls.get_user_info(access_token)
            if not user_info:
                logger.error("카카오 사용자 정보 조회 실패")
                return None
            
            logger.info(f"카카오 사용자 정보 조회 성공: kakao_id={user_info['id']}")
            
            # 3. 사용자 생성 또는 업데이트
            user = cls.create_or_update_user(user_info)
            
            logger.info(f"사용자 생성/업데이트 완료: user_id={user.id}, created={'created' if user.date_joined.date() == timezone.now().date() else 'updated'}")
            
            return user
        
        except Exception as e:
            logger.error(f"카카오 로그인 처리 중 오류: {str(e)}")
            return None
```

## 13. 배포 고려사항

### 13.1 환경별 설정

```python
# settings/production.py
from .base import *

# 보안 설정
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'api.yourdomain.com']

# HTTPS 강제
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# 카카오 설정 (운영환경)
KAKAO_REDIRECT_URI = config('KAKAO_REDIRECT_URI_PROD')

# CORS 설정 (운영환경)
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]

# JWT 보안 강화
JWT_SECRET_KEY = config('JWT_SECRET_KEY_PROD')
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15  # 운영환경에서는 더 짧게
```

### 13.2 Docker 설정

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "main.wsgi:application"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DJANGO_SETTINGS_MODULE=settings.production
    env_file:
      - .env.prod
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: kakao_auth_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

## 결론

Django Ninja를 사용한 카카오 소셜 로그인 구현은 다음과 같은 장점을 제공합니다:

### ✅ **주요 장점**
1. **빠른 개발**: Django Ninja의 FastAPI 스타일 API로 빠른 개발
2. **자동 문서화**: OpenAPI 스펙 자동 생성
3. **타입 안정성**: Pydantic 스키마를 통한 타입 검증
4. **확장성**: JWT 기반 인증으로 마이크로서비스 아키텍처 지원

### 🔧 **핵심 구현 사항**
- OAuth 2.0 플로우 완전 구현
- JWT 액세스/리프레시 토큰 관리
- 사용자 정보 자동 동기화
- 포괄적인 에러 처리

### 🛡️ **보안 고려사항**
- HTTPS 강제 사용
- 토큰 만료시간 관리
- Rate Limiting 적용
- 입력값 검증 및 SQL 인젝션 방지

이 가이드를 통해 안전하고 확장 가능한 카카오 소셜 로그인 시스템을 구축할 수 있습니다. 추가적인 소셜 로그인 제공자(구글, 네이버 등)도 같은 패턴으로 쉽게 확장할 수 있습니다.