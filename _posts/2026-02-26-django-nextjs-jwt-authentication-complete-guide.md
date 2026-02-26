---
layout: post
title: "Django & Next.js JWT 인증 완벽 가이드: Access/Refresh 토큰 관리부터 보안까지"
date: 2026-02-26 10:00:00 +0900
categories: [Django, Next.js, Security]
tags: [Django, Next.js, JWT, Authentication, Authorization, Security, Cookie, Token, REST API]
---

JWT(JSON Web Token)는 현대 웹 애플리케이션에서 가장 널리 사용되는 인증 방식입니다. 이 글에서는 Django 백엔드와 Next.js 프론트엔드 환경에서 JWT를 활용한 인증/인가 시스템을 구축하고, 실무에서 마주하는 다양한 환경(개발/스테이징/프로덕션)과 플랫폼(웹/모바일웹/앱)에서 안전하게 토큰을 관리하는 방법을 상세히 다룹니다.

## 🎯 JWT 인증의 전체 흐름 이해하기

### JWT란 무엇인가?

JWT는 세 부분으로 구성된 토큰 형식입니다:

```
Header.Payload.Signature
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjMsImV4cCI6MTY0MDk5NTIwMH0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

**Header**: 토큰 타입과 해싱 알고리즘 정보
**Payload**: 사용자 정보와 메타데이터 (claims)
**Signature**: 토큰의 무결성을 검증하는 서명

### Access Token과 Refresh Token의 역할

**Access Token (짧은 수명: 15분 ~ 1시간)**
- API 요청 시 인증에 사용
- 짧은 수명으로 보안 강화
- 탈취되더라도 피해 최소화

**Refresh Token (긴 수명: 7일 ~ 30일)**
- Access Token 갱신 전용
- 안전한 저장소에 보관 필수
- 한 번만 사용 가능하도록 구현 권장 (Rotation)

## 🔧 Django 백엔드 JWT 구현

### 1. 기본 설정 및 패키지 설치

```bash
# Django REST Framework와 JWT 라이브러리 설치
pip install django djangorestframework djangorestframework-simplejwt
pip install django-cors-headers  # CORS 설정용
```

### 2. Django 설정 (settings.py)

```python
# settings.py
from datetime import timedelta

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    
    # Your apps
    'accounts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS를 최상단에 배치
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# REST Framework 설정
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

# JWT 설정
SIMPLE_JWT = {
    # Access Token 수명 (15분)
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    
    # Refresh Token 수명 (7일)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    
    # Refresh Token 자동 갱신 (True 권장)
    'ROTATE_REFRESH_TOKENS': True,
    
    # 사용된 Refresh Token 블랙리스트 추가
    'BLACKLIST_AFTER_ROTATION': True,
    
    # 알고리즘
    'ALGORITHM': 'HS256',
    
    # 서명 키 (환경변수로 관리 필수!)
    'SIGNING_KEY': os.environ.get('JWT_SECRET_KEY', SECRET_KEY),
    
    # 토큰 타입
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    
    # Payload에 포함할 정보
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    
    # 토큰 검증 설정
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# 환경별 CORS 설정
if os.environ.get('ENVIRONMENT') == 'production':
    CORS_ALLOWED_ORIGINS = [
        'https://yourdomain.com',
        'https://www.yourdomain.com',
    ]
    CORS_ALLOW_CREDENTIALS = True
    
    # 프로덕션 쿠키 설정
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'None'  # Cross-site 쿠키 허용
    CSRF_COOKIE_SAMESITE = 'None'
    
elif os.environ.get('ENVIRONMENT') == 'staging':
    CORS_ALLOWED_ORIGINS = [
        'https://staging.yourdomain.com',
    ]
    CORS_ALLOW_CREDENTIALS = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
else:  # 로컬 개발 환경
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ]
    CORS_ALLOW_CREDENTIALS = True
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
```

### 3. 커스텀 JWT Views 구현

```python
# accounts/views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import authenticate
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    로그인 API
    - Username과 Password로 인증
    - HttpOnly 쿠키에 Refresh Token 저장
    - Response body에 Access Token 반환
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 사용자 인증
    user = authenticate(username=username, password=password)
    
    if user is None:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # JWT 토큰 생성
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)
    
    # Response 생성
    response = Response({
        'access': access_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        }
    }, status=status.HTTP_200_OK)
    
    # Refresh Token을 HttpOnly 쿠키에 저장
    # HttpOnly: JavaScript에서 접근 불가 (XSS 방어)
    # Secure: HTTPS에서만 전송 (중간자 공격 방어)
    # SameSite: CSRF 방어
    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        httponly=True,  # XSS 공격 방어
        secure=settings.SESSION_COOKIE_SECURE,  # 환경별 설정
        samesite=settings.SESSION_COOKIE_SAMESITE,  # CSRF 공격 방어
        max_age=60 * 60 * 24 * 7,  # 7일
        path='/api/auth/',  # Refresh 경로에서만 전송
    )
    
    logger.info(f"User {user.username} logged in successfully")
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """
    Access Token 갱신 API
    - HttpOnly 쿠키에서 Refresh Token 추출
    - 새로운 Access Token 발급
    - Refresh Token Rotation 적용 시 새로운 Refresh Token도 발급
    """
    # 쿠키에서 Refresh Token 추출
    refresh_token = request.COOKIES.get('refresh_token')
    
    if not refresh_token:
        return Response(
            {'error': 'Refresh token not found'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        # Refresh Token 검증 및 새 토큰 발급
        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)
        
        response = Response({
            'access': access_token,
        }, status=status.HTTP_200_OK)
        
        # Rotation이 활성화된 경우, 새로운 Refresh Token도 발급
        if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS'):
            # 기존 토큰을 블랙리스트에 추가
            if settings.SIMPLE_JWT.get('BLACKLIST_AFTER_ROTATION'):
                try:
                    refresh.blacklist()
                except AttributeError:
                    # Blacklist가 설치되지 않은 경우
                    pass
            
            # 새로운 Refresh Token 발급
            new_refresh = RefreshToken.for_user(refresh.user)
            new_refresh_token = str(new_refresh)
            
            # 새로운 Refresh Token을 쿠키에 저장
            response.set_cookie(
                key='refresh_token',
                value=new_refresh_token,
                httponly=True,
                secure=settings.SESSION_COOKIE_SECURE,
                samesite=settings.SESSION_COOKIE_SAMESITE,
                max_age=60 * 60 * 24 * 7,
                path='/api/auth/',
            )
        
        logger.info(f"Access token refreshed for user {refresh.user.username}")
        return response
        
    except TokenError as e:
        logger.warning(f"Invalid refresh token: {str(e)}")
        return Response(
            {'error': 'Invalid or expired refresh token'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    로그아웃 API
    - Refresh Token을 블랙리스트에 추가
    - 쿠키에서 Refresh Token 삭제
    """
    try:
        refresh_token = request.COOKIES.get('refresh_token')
        
        if refresh_token:
            token = RefreshToken(refresh_token)
            # Refresh Token을 블랙리스트에 추가
            token.blacklist()
        
        response = Response(
            {'message': 'Logout successful'},
            status=status.HTTP_200_OK
        )
        
        # 쿠키에서 Refresh Token 삭제
        response.delete_cookie('refresh_token', path='/api/auth/')
        
        logger.info(f"User {request.user.username} logged out")
        return response
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return Response(
            {'error': 'Logout failed'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_token(request):
    """
    토큰 검증 API
    - Access Token의 유효성 확인
    - 사용자 정보 반환
    """
    return Response({
        'valid': True,
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def check_token(request):
    """
    토큰 변조 검증 API
    - 클라이언트에서 받은 토큰을 검증
    - 변조된 토큰 탐지
    """
    token = request.data.get('token')
    
    if not token:
        return Response(
            {'error': 'Token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # 토큰 검증 (서명 확인, 만료 시간 확인)
        from rest_framework_simplejwt.tokens import AccessToken
        AccessToken(token)
        
        return Response({
            'valid': True,
            'message': 'Token is valid'
        })
        
    except TokenError as e:
        # 토큰이 변조되었거나 만료됨
        logger.warning(f"Invalid token detected: {str(e)}")
        return Response({
            'valid': False,
            'error': str(e),
            'message': 'Token is invalid or expired'
        }, status=status.HTTP_401_UNAUTHORIZED)
```

### 4. URL 라우팅 설정

```python
# accounts/urls.py
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('refresh/', views.refresh_token, name='refresh'),
    path('verify/', views.verify_token, name='verify'),
    path('check/', views.check_token, name='check'),
]

# project/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
]
```

### 5. 커스텀 미들웨어: 자동 토큰 갱신

```python
# accounts/middleware.py
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class JWTRefreshMiddleware(MiddlewareMixin):
    """
    Access Token이 곧 만료될 경우 자동으로 갱신하는 미들웨어
    - Access Token의 남은 수명이 5분 이하일 때 자동 갱신
    - Response에 새 토큰을 X-New-Access-Token 헤더로 전달
    """
    
    def process_request(self, request):
        """요청 처리 전"""
        pass
    
    def process_response(self, request, response):
        """응답 처리 후"""
        # Authorization 헤더에서 토큰 추출
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return response
        
        try:
            # Access Token 추출 및 검증
            token = auth_header.split(' ')[1]
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token)
            
            # 토큰의 남은 수명 확인
            from datetime import datetime, timezone
            exp_timestamp = validated_token['exp']
            exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            time_until_expiry = (exp_datetime - now).total_seconds()
            
            # 5분 이하로 남았을 때 자동 갱신
            if time_until_expiry < 300:  # 5분 = 300초
                refresh_token = request.COOKIES.get('refresh_token')
                
                if refresh_token:
                    try:
                        refresh = RefreshToken(refresh_token)
                        new_access_token = str(refresh.access_token)
                        
                        # 새 토큰을 헤더에 추가
                        response['X-New-Access-Token'] = new_access_token
                        logger.info(f"Access token auto-refreshed for user")
                        
                    except TokenError:
                        logger.warning("Failed to refresh token automatically")
        
        except Exception as e:
            logger.debug(f"Token refresh check failed: {str(e)}")
        
        return response
```

미들웨어를 settings.py에 추가:

```python
# settings.py
MIDDLEWARE = [
    # ... 기존 미들웨어들
    'accounts.middleware.JWTRefreshMiddleware',  # JWT 자동 갱신
]
```

## 🎨 Next.js 프론트엔드 JWT 구현

### 1. API 클라이언트 구성

```typescript
// lib/api/client.ts
import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios';

// 환경별 API URL 설정
const getBaseURL = () => {
  if (process.env.NEXT_PUBLIC_ENVIRONMENT === 'production') {
    return 'https://api.yourdomain.com';
  } else if (process.env.NEXT_PUBLIC_ENVIRONMENT === 'staging') {
    return 'https://api.staging.yourdomain.com';
  } else {
    return 'http://localhost:8000';
  }
};

// Axios 인스턴스 생성
const apiClient: AxiosInstance = axios.create({
  baseURL: getBaseURL(),
  timeout: 10000,
  withCredentials: true,  // 쿠키 전송 활성화
  headers: {
    'Content-Type': 'application/json',
  },
});

// Access Token 저장소 (메모리)
let accessToken: string | null = null;

export const setAccessToken = (token: string | null) => {
  accessToken = token;
};

export const getAccessToken = () => {
  return accessToken;
};

// Request Interceptor: 모든 요청에 Access Token 추가
apiClient.interceptors.request.use(
  (config) => {
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor: 토큰 만료 시 자동 갱신
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: any) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => {
    // 자동 갱신된 토큰이 있으면 업데이트
    const newAccessToken = response.headers['x-new-access-token'];
    if (newAccessToken) {
      setAccessToken(newAccessToken);
      console.log('Access token auto-refreshed');
    }
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & {
      _retry?: boolean;
    };

    // 401 에러이고 재시도하지 않은 요청인 경우
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Refresh 요청 자체가 실패한 경우는 재시도하지 않음
      if (originalRequest.url?.includes('/api/auth/refresh/')) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // 이미 토큰 갱신 중이면 대기열에 추가
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return apiClient(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Refresh Token으로 새 Access Token 발급
        const response = await apiClient.post('/api/auth/refresh/');
        const newAccessToken = response.data.access;

        setAccessToken(newAccessToken);
        processQueue(null, newAccessToken);

        // 실패했던 요청 재시도
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        }
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh Token도 만료된 경우
        processQueue(refreshError, null);
        setAccessToken(null);
        
        // 로그인 페이지로 리다이렉트
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
```

### 2. 인증 서비스 구현

```typescript
// lib/api/auth.ts
import apiClient, { setAccessToken, getAccessToken } from './client';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
}

export interface LoginResponse {
  access: string;
  user: User;
}

export const authService = {
  /**
   * 로그인
   */
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>(
      '/api/auth/login/',
      credentials
    );
    
    // Access Token을 메모리에 저장
    setAccessToken(response.data.access);
    
    // 사용자 정보를 로컬스토리지에 저장 (선택사항)
    if (typeof window !== 'undefined') {
      localStorage.setItem('user', JSON.stringify(response.data.user));
    }
    
    return response.data;
  },

  /**
   * 로그아웃
   */
  async logout(): Promise<void> {
    try {
      await apiClient.post('/api/auth/logout/');
    } finally {
      // 토큰 및 사용자 정보 삭제
      setAccessToken(null);
      if (typeof window !== 'undefined') {
        localStorage.removeItem('user');
      }
    }
  },

  /**
   * 토큰 검증 및 사용자 정보 가져오기
   */
  async verifyToken(): Promise<User | null> {
    try {
      const response = await apiClient.get<{ user: User }>('/api/auth/verify/');
      return response.data.user;
    } catch (error) {
      return null;
    }
  },

  /**
   * 현재 Access Token 가져오기
   */
  getAccessToken(): string | null {
    return getAccessToken();
  },

  /**
   * 토큰 변조 검증
   */
  async checkToken(token: string): Promise<boolean> {
    try {
      const response = await apiClient.post('/api/auth/check/', { token });
      return response.data.valid;
    } catch (error) {
      return false;
    }
  },
};
```

### 3. Auth Context & Hook 구현

```typescript
// contexts/AuthContext.tsx
'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService, User } from '@/lib/api/auth';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // 초기 인증 상태 확인
  useEffect(() => {
    const initAuth = async () => {
      // 로컬스토리지에서 사용자 정보 로드
      const storedUser = localStorage.getItem('user');
      if (storedUser) {
        setUser(JSON.parse(storedUser));
      }

      // 토큰 검증
      try {
        const verifiedUser = await authService.verifyToken();
        if (verifiedUser) {
          setUser(verifiedUser);
          localStorage.setItem('user', JSON.stringify(verifiedUser));
        } else {
          // 토큰이 유효하지 않으면 사용자 정보 삭제
          setUser(null);
          localStorage.removeItem('user');
        }
      } catch (error) {
        setUser(null);
        localStorage.removeItem('user');
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (username: string, password: string) => {
    try {
      const response = await authService.login({ username, password });
      setUser(response.user);
    } catch (error) {
      throw error;
    }
  };

  const logout = async () => {
    try {
      await authService.logout();
    } finally {
      setUser(null);
    }
  };

  const refreshUser = async () => {
    try {
      const verifiedUser = await authService.verifyToken();
      if (verifiedUser) {
        setUser(verifiedUser);
        localStorage.setItem('user', JSON.stringify(verifiedUser));
      }
    } catch (error) {
      console.error('Failed to refresh user:', error);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
```

### 4. 로그인 페이지 구현

```typescript
// app/login/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(username, password);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.error || 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <h2 className="text-center text-3xl font-bold">Sign in</h2>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 text-red-500 p-3 rounded">
              {error}
            </div>
          )}
          
          <div>
            <label htmlFor="username" className="block text-sm font-medium">
              Username
            </label>
            <input
              id="username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  );
}
```

### 5. Protected Route 구현

```typescript
// components/ProtectedRoute.tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

export default function ProtectedRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
```

## 🌐 환경별 쿠키 관리 전략

### 1. 프로덕션 환경

프로덕션에서는 최고 수준의 보안이 필요합니다:

```python
# Django settings.py (Production)
CORS_ALLOWED_ORIGINS = [
    'https://yourdomain.com',
]
CORS_ALLOW_CREDENTIALS = True

# 쿠키 보안 설정
SESSION_COOKIE_SECURE = True  # HTTPS에서만 전송
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'Lax'  # 'Strict' 또는 'Lax' 권장
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True  # JavaScript 접근 차단
```

**프로덕션 쿠키 설정 원칙:**
- `Secure=True`: HTTPS 필수
- `SameSite=Lax`: CSRF 공격 방어 (동일 사이트 요청만 허용)
- `HttpOnly=True`: XSS 공격 방어 (JavaScript 접근 차단)
- `Domain`: 서브도메인 공유 필요 시 `.yourdomain.com` 설정

### 2. 스테이징 환경

스테이징은 프로덕션과 동일한 설정을 사용하되, 도메인만 다르게:

```python
# Django settings.py (Staging)
CORS_ALLOWED_ORIGINS = [
    'https://staging.yourdomain.com',
]
CORS_ALLOW_CREDENTIALS = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
```

### 3. 로컬 개발 환경

로컬에서는 HTTP를 사용하므로 Secure 옵션을 비활성화:

```python
# Django settings.py (Local)
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
CORS_ALLOW_CREDENTIALS = True

SESSION_COOKIE_SECURE = False  # HTTP 허용
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
```

### 4. 환경 변수 관리

```bash
# .env.local
NEXT_PUBLIC_ENVIRONMENT=local
NEXT_PUBLIC_API_URL=http://localhost:8000

# .env.staging
NEXT_PUBLIC_ENVIRONMENT=staging
NEXT_PUBLIC_API_URL=https://api.staging.yourdomain.com

# .env.production
NEXT_PUBLIC_ENVIRONMENT=production
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

## 📱 플랫폼별 토큰 관리 전략

### 1. 웹 브라우저

**Access Token**: 메모리 (JavaScript 변수)
**Refresh Token**: HttpOnly 쿠키

```typescript
// 웹에서의 토큰 저장
let accessToken: string | null = null;  // 메모리

// Refresh Token은 서버가 HttpOnly 쿠키로 자동 관리
```

**장점:**
- XSS 공격에 안전 (Refresh Token이 JavaScript로 접근 불가)
- 페이지 새로고침 시 Refresh Token 유지
- 간단한 구현

**단점:**
- 페이지 새로고침 시 Access Token 손실 (재로그인 또는 자동 갱신 필요)

### 2. 모바일 웹

모바일 웹도 일반 웹과 동일하게 처리하되, Safari의 ITP(Intelligent Tracking Prevention) 고려:

```typescript
// iOS Safari에서 쿠키 사용 시 주의사항
// - SameSite=None은 Secure와 함께 사용 필수
// - 7일 이상 사이트 방문이 없으면 쿠키 삭제됨

// 대안: localStorage + 서버 검증
const saveTokens = (access: string, refresh: string) => {
  // Access Token은 메모리
  setAccessToken(access);
  
  // Refresh Token은 localStorage (암호화 권장)
  if (typeof window !== 'undefined') {
    localStorage.setItem('rt', encryptToken(refresh));
  }
};
```

### 3. 네이티브 앱 (React Native)

네이티브 앱에서는 쿠키 대신 안전한 저장소 사용:

```typescript
// React Native에서의 토큰 저장
import * as SecureStore from 'expo-secure-store';

// Access Token: 메모리
let accessToken: string | null = null;

// Refresh Token: Secure Storage
export const saveRefreshToken = async (token: string) => {
  await SecureStore.setItemAsync('refresh_token', token);
};

export const getRefreshToken = async () => {
  return await SecureStore.getItemAsync('refresh_token');
};

export const deleteRefreshToken = async () => {
  await SecureStore.deleteItemAsync('refresh_token');
};

// 로그인 시
const login = async (username: string, password: string) => {
  const response = await api.post('/api/auth/login/', {
    username,
    password,
  });
  
  // Access Token은 메모리에
  accessToken = response.data.access;
  
  // Refresh Token은 Secure Storage에
  await saveRefreshToken(response.data.refresh);
};

// 앱 시작 시 토큰 복원
const initAuth = async () => {
  const refreshToken = await getRefreshToken();
  
  if (refreshToken) {
    try {
      // Refresh Token으로 새 Access Token 발급
      const response = await api.post('/api/auth/refresh/', {
        refresh: refreshToken,
      });
      accessToken = response.data.access;
      
      // Rotation이 적용된 경우 새 Refresh Token 저장
      if (response.data.refresh) {
        await saveRefreshToken(response.data.refresh);
      }
    } catch (error) {
      // Refresh Token이 만료되면 로그인 페이지로
      await deleteRefreshToken();
    }
  }
};
```

**네이티브 앱용 Django API 수정:**

```python
# accounts/views.py
@api_view(['POST'])
@permission_classes([AllowAny])
def mobile_login(request):
    """모바일 앱용 로그인 API - 쿠키 대신 Response Body로 토큰 반환"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    if user is None:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    refresh = RefreshToken.for_user(user)
    
    # 모바일에서는 쿠키 대신 Response Body에 모든 토큰 포함
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),  # Refresh Token도 Body에 포함
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def mobile_refresh(request):
    """모바일 앱용 토큰 갱신 API"""
    refresh_token = request.data.get('refresh')
    
    if not refresh_token:
        return Response(
            {'error': 'Refresh token required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        refresh = RefreshToken(refresh_token)
        
        response_data = {
            'access': str(refresh.access_token),
        }
        
        # Rotation 적용 시 새 Refresh Token도 반환
        if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS'):
            new_refresh = RefreshToken.for_user(refresh.user)
            response_data['refresh'] = str(new_refresh)
            
            # 기존 토큰 블랙리스트 추가
            if settings.SIMPLE_JWT.get('BLACKLIST_AFTER_ROTATION'):
                try:
                    refresh.blacklist()
                except AttributeError:
                    pass
        
        return Response(response_data)
        
    except TokenError:
        return Response(
            {'error': 'Invalid or expired refresh token'},
            status=status.HTTP_401_UNAUTHORIZED
        )
```

## 🔄 Access Token 만료 처리

### 1. 자동 갱신 전략

**전략 A: 만료 시점에 갱신 (Lazy Refresh)**

클라이언트가 401 에러를 받으면 자동으로 갱신:

```typescript
// 이미 구현된 Axios Interceptor 사용
// 401 에러 발생 → 자동으로 /api/auth/refresh/ 호출
// 성공 시 실패한 요청 재시도
```

**장점:**
- 구현이 간단
- 불필요한 갱신 요청 없음

**단점:**
- 첫 번째 요청이 항상 실패
- 사용자 경험이 약간 저하될 수 있음

**전략 B: 만료 전 갱신 (Proactive Refresh)**

토큰이 만료되기 전에 미리 갱신:

```typescript
// lib/api/tokenManager.ts
import { jwtDecode } from 'jwt-decode';
import { authService } from './auth';

interface JWTPayload {
  exp: number;
  user_id: number;
}

export const checkAndRefreshToken = async () => {
  const token = authService.getAccessToken();
  
  if (!token) return;
  
  try {
    const decoded = jwtDecode<JWTPayload>(token);
    const currentTime = Date.now() / 1000;
    const timeUntilExpiry = decoded.exp - currentTime;
    
    // 5분 이하로 남았으면 갱신
    if (timeUntilExpiry < 300) {
      console.log('Token expiring soon, refreshing...');
      await apiClient.post('/api/auth/refresh/');
    }
  } catch (error) {
    console.error('Token check failed:', error);
  }
};

// 주기적으로 체크 (1분마다)
if (typeof window !== 'undefined') {
  setInterval(checkAndRefreshToken, 60000);
}
```

**장점:**
- 사용자 경험 향상 (요청 실패 없음)
- 토큰 만료로 인한 서비스 중단 최소화

**단점:**
- 추가적인 백그라운드 요청 발생
- 구현이 복잡

### 2. 백그라운드 자동 갱신 (권장)

서버의 미들웨어와 클라이언트의 Interceptor를 조합:

1. **서버**: 토큰 만료 5분 전부터 Response 헤더에 새 토큰 포함
2. **클라이언트**: Response Interceptor에서 자동으로 토큰 업데이트

```typescript
// Response Interceptor (이미 구현됨)
apiClient.interceptors.response.use(
  (response) => {
    // X-New-Access-Token 헤더가 있으면 자동 업데이트
    const newAccessToken = response.headers['x-new-access-token'];
    if (newAccessToken) {
      setAccessToken(newAccessToken);
    }
    return response;
  },
  // ...
);
```

이 방식은 사용자가 API를 호출하는 동안 토큰이 자동으로 갱신되어 추가 요청 없이 seamless한 경험을 제공합니다.

## 🛡️ Access Token 변조 대응

### 1. 토큰 변조 탐지 메커니즘

JWT는 서명(Signature)을 통해 변조를 탐지합니다:

```python
# JWT 구조
# Header.Payload.Signature

# Signature 생성 과정
signature = HMACSHA256(
    base64UrlEncode(header) + "." + base64UrlEncode(payload),
    secret_key
)

# 변조 탐지
# 1. Payload나 Header가 변경되면
# 2. 다시 계산한 Signature가 기존 Signature와 일치하지 않음
# 3. 토큰이 유효하지 않다고 판단
```

### 2. Django에서 변조된 토큰 처리

Django REST Framework Simple JWT는 자동으로 변조를 탐지합니다:

```python
# rest_framework_simplejwt의 내부 동작
try:
    # 토큰 디코딩 및 검증
    token = AccessToken(token_string)
    # 서명 검증, 만료 시간 확인, 발급자 확인 등
except TokenError as e:
    # 변조된 토큰 또는 만료된 토큰
    # - InvalidToken: 서명이 일치하지 않음 (변조됨)
    # - TokenBackendError: 디코딩 실패
    # - TokenExpired: 만료됨
    raise AuthenticationFailed('Token is invalid')
```

### 3. 변조 탐지 및 로깅

```python
# accounts/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.exceptions import AuthenticationFailed
import logging

logger = logging.getLogger(__name__)


class CustomJWTAuthentication(JWTAuthentication):
    """커스텀 JWT 인증 - 변조 탐지 강화"""
    
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except InvalidToken as e:
            # 변조된 토큰 로깅
            token = self.get_raw_token(
                self.get_header(request)
            )
            logger.warning(
                f"Invalid token detected from IP {request.META.get('REMOTE_ADDR')}: {str(e)}"
            )
            
            # 반복적인 변조 시도 감지
            self.log_suspicious_activity(request)
            
            raise AuthenticationFailed('Token is invalid or has been tampered with')
        except TokenError as e:
            logger.info(f"Token error: {str(e)}")
            raise AuthenticationFailed('Token is invalid')
    
    def log_suspicious_activity(self, request):
        """의심스러운 활동 로깅 (Rate Limiting, IP 차단 등과 연동)"""
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT')
        
        # Redis 또는 DB에 기록하여 일정 횟수 이상 시도 시 차단
        from django.core.cache import cache
        
        cache_key = f'suspicious_token_attempts:{ip_address}'
        attempts = cache.get(cache_key, 0)
        attempts += 1
        cache.set(cache_key, attempts, 3600)  # 1시간 동안 유지
        
        if attempts > 5:
            logger.error(
                f"Multiple invalid token attempts from {ip_address}. "
                f"User-Agent: {user_agent}"
            )
            # 알림 전송, IP 차단 등의 추가 조치
```

settings.py에서 커스텀 인증 클래스 사용:

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'accounts.authentication.CustomJWTAuthentication',
    ),
}
```

### 4. 클라이언트 측 변조 처리

```typescript
// lib/api/client.ts
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      const errorData = error.response.data as any;
      
      // 토큰 변조가 감지된 경우
      if (errorData?.error?.includes('tampered') || 
          errorData?.error?.includes('invalid')) {
        
        console.error('Token tampering detected!');
        
        // 모든 토큰 삭제
        setAccessToken(null);
        localStorage.removeItem('user');
        
        // 강제 로그아웃 및 로그인 페이지로 이동
        alert('Security issue detected. Please login again.');
        window.location.href = '/login';
        
        return Promise.reject(error);
      }
    }
    
    // 기타 에러 처리...
    return Promise.reject(error);
  }
);
```

### 5. 추가 보안 강화 방법

**A. JWT ID (jti) 사용**

각 토큰에 고유 ID를 부여하여 일회성 사용 강제:

```python
# settings.py
SIMPLE_JWT = {
    # ...
    'JTI_CLAIM': 'jti',  # JWT ID 클레임 활성화
}

# models.py
from django.db import models

class UsedToken(models.Model):
    """사용된 토큰을 추적하는 모델"""
    jti = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['jti']),
        ]

# authentication.py
class JTIValidationMixin:
    """JTI 검증 믹스인"""
    
    def validate_jti(self, token):
        jti = token.get('jti')
        
        # 이미 사용된 토큰인지 확인
        if UsedToken.objects.filter(jti=jti).exists():
            raise InvalidToken('Token has already been used')
        
        # 토큰 사용 기록
        UsedToken.objects.create(
            jti=jti,
            user_id=token.get('user_id')
        )
```

**B. 클라이언트 Fingerprinting**

토큰에 클라이언트 정보를 포함하여 토큰 탈취 방지:

```python
# accounts/views.py
import hashlib

def generate_fingerprint(request):
    """클라이언트 fingerprint 생성"""
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
    
    fingerprint_string = f"{user_agent}{accept_language}{accept_encoding}"
    return hashlib.sha256(fingerprint_string.encode()).hexdigest()


@api_view(['POST'])
@permission_classes([AllowAny])
def login_with_fingerprint(request):
    """Fingerprint를 포함한 로그인"""
    # ... 기존 인증 로직
    
    user = authenticate(username=username, password=password)
    
    # Fingerprint 생성
    fingerprint = generate_fingerprint(request)
    
    # 커스텀 토큰 생성
    refresh = RefreshToken.for_user(user)
    refresh['fingerprint'] = fingerprint  # Payload에 fingerprint 추가
    
    # ... 나머지 로직


# 인증 시 fingerprint 검증
class FingerprintJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        validated_token = self.get_validated_token(
            self.get_raw_token(self.get_header(request))
        )
        
        # Fingerprint 검증
        token_fingerprint = validated_token.get('fingerprint')
        current_fingerprint = generate_fingerprint(request)
        
        if token_fingerprint != current_fingerprint:
            logger.warning(
                f"Fingerprint mismatch! Token may have been stolen. "
                f"User: {validated_token.get('user_id')}"
            )
            raise AuthenticationFailed('Token fingerprint mismatch')
        
        return self.get_user(validated_token), validated_token
```

**C. IP 화이트리스트 (엔터프라이즈용)**

특정 IP 대역에서만 토큰 사용 허용:

```python
# accounts/authentication.py
class IPRestrictedJWTAuthentication(JWTAuthentication):
    """IP 주소 제한을 포함한 JWT 인증"""
    
    ALLOWED_IP_RANGES = [
        # 사무실 IP 대역
        '203.0.113.0/24',
        # VPN IP 대역
        '198.51.100.0/24',
    ]
    
    def authenticate(self, request):
        # 토큰 검증
        user, validated_token = super().authenticate(request)
        
        # IP 주소 확인
        client_ip = self.get_client_ip(request)
        
        if not self.is_ip_allowed(client_ip):
            logger.warning(
                f"Access denied from unauthorized IP: {client_ip} "
                f"for user {user.username}"
            )
            raise AuthenticationFailed('Access denied from this IP address')
        
        return user, validated_token
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 가져오기 (프록시 고려)"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_ip_allowed(self, ip):
        """IP 주소가 허용된 범위에 있는지 확인"""
        from ipaddress import ip_address, ip_network
        
        client_ip = ip_address(ip)
        
        for ip_range in self.ALLOWED_IP_RANGES:
            if client_ip in ip_network(ip_range):
                return True
        
        return False
```

## 🔐 보안 Best Practices

### 1. 토큰 수명 설정 지침

```python
# 권장 설정
SIMPLE_JWT = {
    # 일반 서비스
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),  # 15분
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),     # 7일
    
    # 고보안 서비스 (금융, 의료 등)
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),   # 5분
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=24),   # 24시간
    
    # 낮은 보안 요구사항 (공개 콘텐츠 등)
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),     # 1시간
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),    # 30일
}
```

### 2. HTTPS 필수

프로덕션 환경에서는 반드시 HTTPS 사용:

```python
# settings.py (Production)
SECURE_SSL_REDIRECT = True  # HTTP를 HTTPS로 자동 리다이렉트
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000  # HSTS 활성화 (1년)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### 3. 시크릿 키 관리

JWT 서명에 사용되는 시크릿 키는 환경변수로 관리:

```bash
# .env
JWT_SECRET_KEY=your-super-secret-key-at-least-32-characters-long
```

```python
# settings.py
import os
from dotenv import load_dotenv

load_dotenv()

SIMPLE_JWT = {
    'SIGNING_KEY': os.environ.get('JWT_SECRET_KEY'),
}

# 시크릿 키가 설정되지 않았으면 에러
if not os.environ.get('JWT_SECRET_KEY'):
    raise ValueError('JWT_SECRET_KEY environment variable is not set')
```

### 4. Rate Limiting

무차별 대입 공격 방어:

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',  # 익명 사용자: 시간당 100회
        'user': '1000/hour',  # 인증된 사용자: 시간당 1000회
        'login': '5/minute',  # 로그인: 분당 5회
    }
}

# accounts/views.py
from rest_framework.throttling import AnonRateThrottle

class LoginRateThrottle(AnonRateThrottle):
    rate = '5/minute'

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login(request):
    # 로그인 로직
    pass
```

### 5. 로깅 및 모니터링

보안 이벤트를 체계적으로 로깅:

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/security.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'accounts': {  # accounts 앱의 로거
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# accounts/views.py
logger.info(f"Login attempt for user: {username} from IP: {request.META.get('REMOTE_ADDR')}")
logger.warning(f"Failed login attempt for user: {username}")
logger.error(f"Multiple failed login attempts from IP: {ip_address}")
```

## 🚀 고급 패턴: Sliding Sessions

사용자가 활동하는 동안 자동으로 세션을 연장하는 "Sliding Session" 패턴:

```python
# accounts/middleware.py
from datetime import datetime, timezone, timedelta
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

class SlidingSessionMiddleware(MiddlewareMixin):
    """
    사용자 활동 시 자동으로 토큰 수명 연장
    - 마지막 활동 후 일정 시간 경과 시 갱신
    """
    
    def process_response(self, request, response):
        # 인증된 요청인지 확인
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return response
        
        # 마지막 활동 시간 확인
        last_activity = request.session.get('last_activity')
        now = datetime.now(timezone.utc)
        
        should_refresh = False
        
        if last_activity:
            last_activity_dt = datetime.fromisoformat(last_activity)
            time_since_activity = (now - last_activity_dt).total_seconds()
            
            # 10분 이상 경과 시 갱신
            if time_since_activity > 600:
                should_refresh = True
        else:
            should_refresh = True
        
        if should_refresh:
            # 새로운 토큰 발급
            refresh_token = request.COOKIES.get('refresh_token')
            
            if refresh_token:
                try:
                    refresh = RefreshToken(refresh_token)
                    new_access = str(refresh.access_token)
                    
                    # 새 토큰을 헤더에 추가
                    response['X-New-Access-Token'] = new_access
                    
                    # 마지막 활동 시간 업데이트
                    request.session['last_activity'] = now.isoformat()
                    
                except:
                    pass
        
        return response
```

## 📊 성능 최적화

### 1. 토큰 캐싱

자주 검증되는 토큰을 Redis에 캐싱:

```python
# accounts/authentication.py
from django.core.cache import cache
import hashlib

class CachedJWTAuthentication(JWTAuthentication):
    """토큰 검증 결과를 캐싱하는 인증 클래스"""
    
    CACHE_TTL = 300  # 5분
    
    def get_validated_token(self, raw_token):
        # 토큰 해시 생성
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        cache_key = f'jwt_validated:{token_hash}'
        
        # 캐시에서 검증 결과 확인
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # 검증 수행
        validated_token = super().get_validated_token(raw_token)
        
        # 결과 캐싱
        cache.set(cache_key, validated_token, self.CACHE_TTL)
        
        return validated_token
```

### 2. 비동기 처리

로깅이나 알림을 비동기로 처리하여 응답 시간 최소화:

```python
# accounts/tasks.py
from celery import shared_task

@shared_task
def log_suspicious_activity(ip_address, user_agent, attempts):
    """의심스러운 활동을 비동기로 로깅"""
    # DB에 기록
    # 알림 전송
    # 관리자에게 이메일 발송
    pass

# accounts/authentication.py
def log_suspicious_activity(self, request):
    # 비동기로 처리
    log_suspicious_activity.delay(
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT'),
        attempts=attempts
    )
```

## 🧪 테스트 코드

JWT 인증 시스템의 테스트:

```python
# accounts/tests.py
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

class JWTAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_login_success(self):
        """정상 로그인 테스트"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh_token', response.cookies)
    
    def test_login_invalid_credentials(self):
        """잘못된 인증 정보로 로그인 시도"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpassword',
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_access_protected_endpoint(self):
        """보호된 엔드포인트 접근 테스트"""
        # 로그인
        login_response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        })
        access_token = login_response.data['access']
        
        # 토큰으로 보호된 엔드포인트 접근
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get('/api/auth/verify/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], 'testuser')
    
    def test_token_refresh(self):
        """토큰 갱신 테스트"""
        # 로그인
        login_response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        })
        
        # Refresh Token으로 새 Access Token 발급
        refresh_response = self.client.post('/api/auth/refresh/')
        
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)
    
    def test_tampered_token(self):
        """변조된 토큰 테스트"""
        # 정상 로그인
        login_response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        })
        access_token = login_response.data['access']
        
        # 토큰 변조 (마지막 문자 변경)
        tampered_token = access_token[:-1] + 'X'
        
        # 변조된 토큰으로 접근 시도
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tampered_token}')
        response = self.client.get('/api/auth/verify/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_logout(self):
        """로그아웃 테스트"""
        # 로그인
        login_response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        })
        access_token = login_response.data['access']
        
        # 로그아웃
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_response = self.client.post('/api/auth/logout/')
        
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        
        # 로그아웃 후 Refresh Token 사용 불가
        refresh_response = self.client.post('/api/auth/refresh/')
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
```

## 📝 완전한 구현 체크리스트

### Django 백엔드

- [ ] djangorestframework-simplejwt 설치 및 설정
- [ ] Access Token 수명 설정 (15분 권장)
- [ ] Refresh Token 수명 설정 (7일 권장)
- [ ] Refresh Token Rotation 활성화
- [ ] 환경별 CORS 설정 (로컬/스테이징/프로덕션)
- [ ] HttpOnly 쿠키로 Refresh Token 저장
- [ ] 로그인/로그아웃/갱신 API 구현
- [ ] 토큰 변조 탐지 및 로깅
- [ ] Rate Limiting 적용
- [ ] HTTPS 강제 (프로덕션)
- [ ] 시크릿 키 환경변수 관리
- [ ] 보안 로깅 설정
- [ ] 테스트 코드 작성

### Next.js 프론트엔드

- [ ] Axios 인스턴스 생성 및 환경별 baseURL 설정
- [ ] withCredentials 활성화 (쿠키 전송)
- [ ] Access Token 메모리 저장
- [ ] Request Interceptor로 토큰 자동 추가
- [ ] Response Interceptor로 401 에러 자동 처리
- [ ] 토큰 갱신 로직 구현
- [ ] Auth Context/Provider 구현
- [ ] Protected Route 구현
- [ ] 로그인/로그아웃 페이지 구현
- [ ] 토큰 만료 알림 UI
- [ ] 네트워크 에러 처리

### 모바일 앱 (React Native)

- [ ] Secure Storage 라이브러리 설치
- [ ] Refresh Token을 Secure Storage에 저장
- [ ] Access Token은 메모리에 저장
- [ ] 앱 시작 시 토큰 복원 로직
- [ ] 모바일용 로그인/갱신 API 엔드포인트
- [ ] 네이티브 인증 (생체인증) 통합 (선택)

### 보안

- [ ] HTTPS 적용 (프로덕션)
- [ ] Secure, HttpOnly, SameSite 쿠키 플래그 설정
- [ ] JWT 서명 알고리즘 적절히 선택 (HS256 또는 RS256)
- [ ] 토큰 블랙리스트 구현
- [ ] Rate Limiting
- [ ] 의심스러운 활동 로깅 및 알림
- [ ] IP 화이트리스트 (필요 시)
- [ ] Fingerprinting (필요 시)
- [ ] 정기적인 시크릿 키 로테이션

## 🎓 결론

Django와 Next.js를 활용한 JWT 인증 시스템은 현대적이고 확장 가능한 인증 솔루션입니다. 이 가이드에서 다룬 내용을 정리하면:

### 핵심 포인트

1. **Access Token은 짧게, Refresh Token은 길게**
   - Access Token: 15분 (API 요청용)
   - Refresh Token: 7일 (갱신 전용)

2. **Refresh Token은 HttpOnly 쿠키에 저장**
   - XSS 공격 방어
   - 자동으로 서버에 전송

3. **Access Token은 메모리에 저장**
   - JavaScript 변수로 관리
   - 페이지 새로고침 시 자동 갱신

4. **환경별 쿠키 설정**
   - 프로덕션: Secure=True, SameSite=Lax
   - 로컬: Secure=False

5. **플랫폼별 전략**
   - 웹: HttpOnly 쿠키
   - 앱: Secure Storage

6. **자동 갱신**
   - Response Interceptor 활용
   - 사용자 경험 향상

7. **변조 탐지**
   - JWT 서명 검증
   - 로깅 및 알림
   - Rate Limiting

이 가이드의 모든 코드는 실제 프로덕션 환경에서 검증된 패턴을 기반으로 작성되었습니다. 프로젝트의 보안 요구사항과 규모에 맞게 조정하여 사용하시기 바랍니다.

### 다음 단계

- OAuth 2.0 통합 (소셜 로그인)
- Multi-Factor Authentication (MFA)
- Single Sign-On (SSO)
- JWT 대안 (Paseto, Macaroons) 검토
- Zero Trust Architecture 적용

JWT 인증은 시작일 뿐입니다. 지속적인 보안 업데이트와 모니터링을 통해 안전한 애플리케이션을 유지하세요! 🔐
