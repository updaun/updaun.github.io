---
layout: post
title: "토스 앱인토스(Apps in Toss) 로그인 OAuth 2.0 구현 완벽 가이드"
date: 2025-11-15 09:00:00 +0900
categories: [OAuth, Toss, Integration]
tags: [toss, apps-in-toss, oauth2, login, authentication, sdk, api-integration, react]
description: "토스 앱인토스 플랫폼의 OAuth 2.0 로그인을 처음부터 끝까지 구현하는 완벽 가이드. 인가 코드 발급부터 사용자 정보 복호화, 로그인 연결 해제까지 실전 예제 코드와 함께."
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-11-15-toss-apps-in-toss-login-implementation.webp"
---

## 1. 서론

### 1.1 토스 앱인토스 로그인이란?

토스 앱인토스(Apps in Toss)는 토스 앱 내에서 작동하는 미니 앱 플랫폼입니다. **토스 로그인**을 통해 2,500만 토스 사용자의 안전한 본인인증과 개인정보를 활용할 수 있습니다.

**주요 특징:**
- 🔐 **간편한 인증**: 별도 회원가입 없이 토스 계정으로 즉시 로그인
- 📱 **원클릭 로그인**: 이미 로그인한 사용자는 클릭 한 번으로 재로그인
- 🔒 **안전한 데이터**: AES-256-GCM 암호화로 개인정보 보호
- ✅ **본인인증 완료**: 토스에서 이미 인증된 실명, 휴대폰, CI 정보 제공

### 1.2 OAuth 2.0 플로우 개요

```
┌─────────────┐                                      ┌──────────────┐
│   사용자    │                                      │  토스 서버   │
│ (토스앱)    │                                      │              │
└──────┬──────┘                                      └──────┬───────┘
       │                                                    │
       │ 1. appLogin() 호출                                │
       ├──────────────────────────────────────────────────►│
       │                                                    │
       │    약관 동의 화면 (최초 1회)                       │
       │◄───────────────────────────────────────────────── │
       │                                                    │
       │ 2. 인가 코드 반환 (유효시간 10분)                  │
       │◄───────────────────────────────────────────────── │
       │                                                    │
       │                                                    │
┌──────▼──────┐                                      ┌─────▼────────┐
│   프론트    │                                      │  백엔드      │
│   엔드      │                                      │  서버        │
└──────┬──────┘                                      └──────┬───────┘
       │                                                    │
       │ 3. authorizationCode + referrer 전달               │
       ├───────────────────────────────────────────────────►│
       │                                                    │
       │                                      4. POST /generate-token
       │                                      (인가코드 → AccessToken)
       │                                                    ├──────►
       │                                                    │
       │                                      5. AccessToken 반환
       │                                      (유효시간 1시간)
       │                                                    │◄──────
       │                                                    │
       │                                      6. GET /login-me
       │                                      (Authorization: Bearer)
       │                                                    ├──────►
       │                                                    │
       │                                      7. 암호화된 사용자 정보
       │                                                    │◄──────
       │                                                    │
       │ 8. 복호화된 사용자 정보 응답                        │
       │◄───────────────────────────────────────────────────┤
       │                                                    │
```

**핵심 단계:**
1. **인가 코드 받기**: SDK의 `appLogin()` 호출
2. **AccessToken 발급**: 인가 코드 → AccessToken 교환
3. **사용자 정보 조회**: AccessToken으로 암호화된 정보 받기
4. **정보 복호화**: AES-256-GCM으로 평문 변환
5. **토큰 관리**: RefreshToken으로 AccessToken 갱신

### 1.3 제공되는 사용자 정보

| 필드 | 타입 | 암호화 | 설명 |
|------|------|--------|------|
| userKey | number | ❌ | 토스 내 고유 사용자 식별자 |
| name | string | ✅ | 실명 |
| phone | string | ✅ | 휴대전화번호 (하이픈 없음) |
| birthday | string | ✅ | 생년월일 (yyyyMMdd) |
| ci | string | ✅ | 본인확인정보 (CI) |
| di | string | ✅ | 중복가입확인정보 (항상 null) |
| gender | string | ✅ | 성별 (MALE/FEMALE) |
| nationality | string | ✅ | 국적 (LOCAL/FOREIGNER) |
| email | string | ✅ | 이메일 (점유인증 미완료) |
| agreedTerms | array | ❌ | 동의한 약관 태그 목록 |

⚠️ **중요**: 모든 개인정보는 **AES-256-GCM 암호화**되어 전달됩니다.

### 1.4 필요한 준비물

**1) 앱인토스 콘솔 설정**
```
https://console-apps-in-toss.toss.im/

1. 앱 등록 및 승인
2. 로그인 기능 활성화
3. 약관 등록 (필수/선택 약관)
4. Redirect URI 설정
5. 복호화 키 이메일 수신
```

**2) 환경별 API 엔드포인트**

```bash
# 프로덕션 (실제 토스앱)
BASE_URL=https://apps-in-toss-api.toss.im

# 샌드박스 (테스트용 앱)
# 샌드박스 앱 다운로드 필요
# https://developers-apps-in-toss.toss.im/development/test/sandbox.html
```

**3) SDK 설치**

```bash
# npm
npm install @toss/app-bridge

# yarn
yarn add @toss/app-bridge
```

### 1.5 이 글에서 다룰 내용

1. ✅ **프론트엔드 구현** - React + Toss SDK
2. ✅ **백엔드 구현** - Node.js Express + FastAPI
3. ✅ **사용자 정보 복호화** - AES-256-GCM
4. ✅ **토큰 관리** - RefreshToken
5. ✅ **로그인 연결 해제** - 로그아웃 & 콜백
6. ✅ **에러 핸들링** - 트러블슈팅

시작하겠습니다! 🚀

## 2. 프론트엔드 구현 - 인가 코드 받기

### 2.1 프로젝트 초기 설정

**1) React 프로젝트 생성 및 SDK 설치**

```bash
# React 프로젝트 생성 (Vite)
npm create vite@latest toss-login-app -- --template react-ts
cd toss-login-app

# Toss SDK 설치
npm install @toss/app-bridge

# 추가 의존성
npm install axios
npm install @types/node -D
```

**2) 프로젝트 구조**

```
toss-login-app/
├── src/
│   ├── App.tsx                 # 메인 컴포넌트
│   ├── hooks/
│   │   └── useTossLogin.ts     # 로그인 커스텀 훅
│   ├── services/
│   │   └── authService.ts      # API 통신
│   ├── types/
│   │   └── auth.ts             # 타입 정의
│   └── utils/
│       └── constants.ts        # 상수
├── .env                        # 환경 변수
└── package.json
```

**3) 환경 변수 설정**

```bash
# .env
VITE_API_BASE_URL=http://localhost:3000/api
VITE_TOSS_API_BASE_URL=https://apps-in-toss-api.toss.im
```

### 2.2 타입 정의

```typescript
// src/types/auth.ts

/**
 * appLogin 응답 타입
 */
export interface TossLoginResponse {
  authorizationCode: string;  // 인가 코드 (10분 유효)
  referrer: 'sandbox' | 'DEFAULT';  // sandbox: 샌드박스앱, DEFAULT: 토스앱
}

/**
 * 토큰 발급 요청
 */
export interface GenerateTokenRequest {
  authorizationCode: string;
  referrer: string;
}

/**
 * 토큰 발급 응답
 */
export interface TokenResponse {
  tokenType: 'Bearer';
  accessToken: string;    // 1시간 유효
  refreshToken: string;   // 14일 유효
  expiresIn: number;      // 만료 시간(초)
  scope: string;          // 인가된 scope (공백 구분)
}

/**
 * 사용자 정보 (암호화된 상태)
 */
export interface EncryptedUserInfo {
  userKey: number;
  scope: string;
  agreedTerms: string[];  // 약관 태그 배열
  name?: string;          // 암호화됨
  phone?: string;         // 암호화됨
  birthday?: string;      // 암호화됨 (yyyyMMdd)
  ci?: string;            // 암호화됨
  di?: string | null;     // 항상 null
  gender?: string;        // 암호화됨 (MALE/FEMALE)
  nationality?: string;   // 암호화됨 (LOCAL/FOREIGNER)
  email?: string | null;  // 암호화됨
}

/**
 * 사용자 정보 (복호화된 상태)
 */
export interface DecryptedUserInfo extends Omit<EncryptedUserInfo, 'name' | 'phone' | 'birthday' | 'ci' | 'gender' | 'nationality' | 'email'> {
  name?: string;
  phone?: string;
  birthday?: string;
  ci?: string;
  gender?: 'MALE' | 'FEMALE';
  nationality?: 'LOCAL' | 'FOREIGNER';
  email?: string | null;
}

/**
 * API 응답 래퍼
 */
export interface TossApiResponse<T> {
  resultType: 'SUCCESS' | 'FAIL';
  success?: T;
  error?: {
    errorCode: string;
    reason: string;
  };
}
```

### 2.3 Toss SDK 로그인 구현

```typescript
// src/hooks/useTossLogin.ts
import { useCallback, useState } from 'react';
import { appLogin } from '@toss/app-bridge';
import { TossLoginResponse, DecryptedUserInfo } from '../types/auth';
import { authService } from '../services/authService';

export const useTossLogin = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<DecryptedUserInfo | null>(null);

  /**
   * 1단계: 인가 코드 받기
   */
  const getAuthorizationCode = useCallback(async (): Promise<TossLoginResponse | null> => {
    try {
      const result = await appLogin();
      
      console.log('✅ Authorization code received:', {
        code: result.authorizationCode.substring(0, 20) + '...',
        referrer: result.referrer
      });
      
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '로그인 실패';
      console.error('❌ appLogin failed:', errorMessage);
      setError(errorMessage);
      return null;
    }
  }, []);

  /**
   * 전체 로그인 플로우
   */
  const login = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // 1. 인가 코드 받기
      const authResult = await getAuthorizationCode();
      if (!authResult) {
        throw new Error('인가 코드를 받을 수 없습니다.');
      }

      // 2. AccessToken 발급 (백엔드 호출)
      const tokenResponse = await authService.generateToken({
        authorizationCode: authResult.authorizationCode,
        referrer: authResult.referrer
      });

      // 3. 토큰 저장
      localStorage.setItem('accessToken', tokenResponse.accessToken);
      localStorage.setItem('refreshToken', tokenResponse.refreshToken);

      // 4. 사용자 정보 조회 (백엔드가 복호화해서 반환)
      const userInfo = await authService.getUserInfo(tokenResponse.accessToken);
      setUser(userInfo);

      console.log('✅ Login successful:', userInfo);
      return userInfo;

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '로그인 처리 실패';
      console.error('❌ Login failed:', errorMessage);
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [getAuthorizationCode]);

  /**
   * 로그아웃
   */
  const logout = useCallback(async () => {
    try {
      const accessToken = localStorage.getItem('accessToken');
      if (accessToken) {
        await authService.removeAccess(accessToken);
      }
      
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      setUser(null);
      
      console.log('✅ Logout successful');
    } catch (err) {
      console.error('❌ Logout failed:', err);
      // 로그아웃은 실패해도 로컬 데이터는 삭제
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      setUser(null);
    }
  }, []);

  return {
    login,
    logout,
    loading,
    error,
    user,
    isLoggedIn: !!user
  };
};
```

### 2.4 API 서비스 레이어

```typescript
// src/services/authService.ts
import axios from 'axios';
import {
  GenerateTokenRequest,
  TokenResponse,
  DecryptedUserInfo,
  TossApiResponse
} from '../types/auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

class AuthService {
  /**
   * AccessToken 발급
   */
  async generateToken(request: GenerateTokenRequest): Promise<TokenResponse> {
    const response = await axios.post<TokenResponse>(
      `${API_BASE_URL}/auth/token`,
      request
    );
    return response.data;
  }

  /**
   * 사용자 정보 조회 (백엔드가 복호화 수행)
   */
  async getUserInfo(accessToken: string): Promise<DecryptedUserInfo> {
    const response = await axios.get<DecryptedUserInfo>(
      `${API_BASE_URL}/auth/me`,
      {
        headers: {
          Authorization: `Bearer ${accessToken}`
        }
      }
    );
    return response.data;
  }

  /**
   * AccessToken 재발급
   */
  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    const response = await axios.post<TokenResponse>(
      `${API_BASE_URL}/auth/refresh`,
      { refreshToken }
    );
    return response.data;
  }

  /**
   * 로그인 연결 끊기
   */
  async removeAccess(accessToken: string): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/auth/logout`,
      {},
      {
        headers: {
          Authorization: `Bearer ${accessToken}`
        }
      }
    );
  }
}

export const authService = new AuthService();
```

### 2.5 React 컴포넌트 예제

{% raw %}
```tsx
// src/App.tsx
import React from 'react';
import { useTossLogin } from './hooks/useTossLogin';

function App() {
  const { login, logout, loading, error, user, isLoggedIn } = useTossLogin();

  const handleLogin = async () => {
    try {
      await login();
      alert('로그인 성공!');
    } catch (err) {
      alert('로그인 실패: ' + (err instanceof Error ? err.message : '알 수 없는 오류'));
    }
  };

  const handleLogout = async () => {
    await logout();
    alert('로그아웃 완료');
  };

  return (
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto' }}>
      <h1>토스 로그인 데모</h1>

      {!isLoggedIn ? (
        <div>
          <button
            onClick={handleLogin}
            disabled={loading}
            style={{
              padding: '12px 24px',
              fontSize: '16px',
              backgroundColor: '#3182F6',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? '로그인 중...' : '토스로 로그인'}
          </button>
          {error && (
            <p style={{ color: 'red', marginTop: '10px' }}>
              오류: {error}
            </p>
          )}
        </div>
      ) : (
        <div>
          <h2>환영합니다! 🎉</h2>
          <div style={{
            backgroundColor: '#f5f5f5',
            padding: '16px',
            borderRadius: '8px',
            marginBottom: '16px'
          }}>
            <p><strong>이름:</strong> {user?.name || 'N/A'}</p>
            <p><strong>휴대폰:</strong> {user?.phone || 'N/A'}</p>
            <p><strong>생년월일:</strong> {user?.birthday || 'N/A'}</p>
            <p><strong>성별:</strong> {user?.gender || 'N/A'}</p>
            <p><strong>국적:</strong> {user?.nationality || 'N/A'}</p>
            <p><strong>사용자 키:</strong> {user?.userKey}</p>
            <p><strong>동의한 약관:</strong> {user?.agreedTerms.join(', ')}</p>
          </div>
          <button
            onClick={handleLogout}
            style={{
              padding: '12px 24px',
              fontSize: '16px',
              backgroundColor: '#E5E8EB',
              color: '#333',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer'
            }}
          >
            로그아웃
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
```
{% endraw %}

### 2.6 최초 로그인 vs 재로그인

**최초 로그인 플로우:**

```typescript
// 1. appLogin() 호출
const result = await appLogin();

// 2. 토스 로그인 화면 표시
//    - 사용자가 약관 동의
//    - 필수 약관 모두 동의 필요

// 3. 인가 코드 반환
// {
//   authorizationCode: "abc123...",
//   referrer: "DEFAULT"
// }
```

**이미 로그인한 경우:**

```typescript
// 1. appLogin() 호출
const result = await appLogin();

// 2. 별도 화면 없이 즉시 인가 코드 반환
// {
//   authorizationCode: "xyz789...",
//   referrer: "DEFAULT"
// }

// 사용자 경험: 버튼 클릭 → 즉시 로그인 완료
```

### 2.7 샌드박스 환경 테스트

```typescript
// 개발 시 referrer 확인
const result = await appLogin();

if (result.referrer === 'sandbox') {
  console.log('🔧 샌드박스 환경에서 실행 중');
} else {
  console.log('✅ 프로덕션 토스앱에서 실행 중');
}

// 백엔드에 referrer를 함께 전송
await authService.generateToken({
  authorizationCode: result.authorizationCode,
  referrer: result.referrer  // 환경 구분용
});
```

**샌드박스 앱 설치:**
```
https://developers-apps-in-toss.toss.im/development/test/sandbox.html

1. 샌드박스 앱 다운로드
2. 개발자 계정으로 로그인
3. 앱 테스트 진행
```

### 2.8 에러 핸들링

```typescript
// src/hooks/useTossLogin.ts (에러 처리 강화)

const getAuthorizationCode = useCallback(async () => {
  try {
    const result = await appLogin();
    return result;
  } catch (err) {
    // appLogin 실패 원인
    if (err instanceof Error) {
      switch (err.message) {
        case 'User cancelled':
          setError('사용자가 로그인을 취소했습니다.');
          break;
        case 'Network error':
          setError('네트워크 오류가 발생했습니다. 인터넷 연결을 확인하세요.');
          break;
        case 'Not in Toss app':
          setError('토스 앱에서만 사용할 수 있습니다.');
          break;
        default:
          setError(`로그인 실패: ${err.message}`);
      }
    }
    return null;
  }
}, []);

// API 호출 에러 처리
const login = useCallback(async () => {
  try {
    // ... 기존 코드
  } catch (err) {
    if (axios.isAxiosError(err)) {
      if (err.response?.status === 401) {
        setError('인증 실패. 다시 로그인해주세요.');
      } else if (err.response?.status === 400) {
        setError('잘못된 요청입니다.');
      } else {
        setError('서버 오류가 발생했습니다.');
      }
    }
    throw err;
  }
}, [getAuthorizationCode]);
```

프론트엔드 구현이 완료되었습니다! 다음 섹션에서 백엔드를 구현하겠습니다.

## 3. 백엔드 구현 - Node.js Express

### 3.1 프로젝트 초기 설정

```bash
# 프로젝트 생성
mkdir toss-login-backend
cd toss-login-backend
npm init -y

# 의존성 설치
npm install express axios cors dotenv
npm install @types/express @types/cors @types/node typescript ts-node nodemon -D

# TypeScript 설정
npx tsc --init
```

**프로젝트 구조:**

```
toss-login-backend/
├── src/
│   ├── index.ts              # 서버 진입점
│   ├── routes/
│   │   └── auth.ts           # 인증 라우터
│   ├── services/
│   │   ├── tossApi.ts        # 토스 API 클라이언트
│   │   └── crypto.ts         # 복호화 서비스
│   ├── types/
│   │   └── index.ts          # 타입 정의
│   └── config/
│       └── constants.ts      # 상수
├── .env                      # 환경 변수
├── tsconfig.json
└── package.json
```

**환경 변수 설정:**

```bash
# .env
PORT=3000
TOSS_API_BASE_URL=https://apps-in-toss-api.toss.im
TOSS_DECRYPTION_KEY=your_decryption_key_from_email
TOSS_AAD=your_aad_from_email
CORS_ORIGIN=http://localhost:5173
```

### 3.2 타입 정의

```typescript
// src/types/index.ts

/**
 * 토스 API 응답 래퍼
 */
export interface TossApiResponse<T> {
  resultType: 'SUCCESS' | 'FAIL';
  success?: T;
  error?: {
    errorCode: string;
    reason: string;
  };
}

/**
 * AccessToken 발급 요청
 */
export interface GenerateTokenRequest {
  authorizationCode: string;
  referrer: string;
}

/**
 * AccessToken 응답
 */
export interface TokenData {
  tokenType: 'Bearer';
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  scope: string;
}

/**
 * RefreshToken 요청
 */
export interface RefreshTokenRequest {
  refreshToken: string;
}

/**
 * 암호화된 사용자 정보
 */
export interface EncryptedUserData {
  userKey: number;
  scope: string;
  agreedTerms: string[];
  name?: string;        // ENCRYPTED_VALUE
  phone?: string;       // ENCRYPTED_VALUE
  birthday?: string;    // ENCRYPTED_VALUE
  ci?: string;          // ENCRYPTED_VALUE
  di?: string | null;
  gender?: string;      // ENCRYPTED_VALUE
  nationality?: string; // ENCRYPTED_VALUE
  email?: string | null;
}

/**
 * 복호화된 사용자 정보
 */
export interface DecryptedUserData extends EncryptedUserData {
  name?: string;
  phone?: string;
  birthday?: string;
  ci?: string;
  gender?: 'MALE' | 'FEMALE';
  nationality?: 'LOCAL' | 'FOREIGNER';
}

/**
 * 로그인 연결 해제 콜백
 */
export interface UnlinkCallbackData {
  userKey: number;
  referrer: 'UNLINK' | 'WITHDRAWAL_TERMS' | 'WITHDRAWAL_TOSS';
}
```

### 3.3 토스 API 클라이언트

```typescript
// src/services/tossApi.ts
import axios, { AxiosInstance } from 'axios';
import {
  TossApiResponse,
  GenerateTokenRequest,
  TokenData,
  RefreshTokenRequest,
  EncryptedUserData
} from '../types';

class TossApiService {
  private client: AxiosInstance;
  private baseURL: string;

  constructor() {
    this.baseURL = process.env.TOSS_API_BASE_URL || 'https://apps-in-toss-api.toss.im';
    this.client = axios.create({
      baseURL: this.baseURL,
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: 10000
    });
  }

  /**
   * 2. AccessToken 발급
   * POST /api-partner/v1/apps-in-toss/user/oauth2/generate-token
   */
  async generateToken(request: GenerateTokenRequest): Promise<TokenData> {
    try {
      const response = await this.client.post<TossApiResponse<TokenData>>(
        '/api-partner/v1/apps-in-toss/user/oauth2/generate-token',
        request
      );

      if (response.data.resultType === 'SUCCESS' && response.data.success) {
        console.log('✅ Token generated successfully');
        return response.data.success;
      }

      throw new Error(
        response.data.error?.reason || 'Token generation failed'
      );
    } catch (error) {
      if (axios.isAxiosError(error)) {
        // invalid_grant: 인가 코드 만료 또는 중복 사용
        if (error.response?.data?.error === 'invalid_grant') {
          throw new Error('인가 코드가 만료되었거나 이미 사용되었습니다.');
        }
        throw new Error(
          error.response?.data?.error?.reason || '토큰 발급 실패'
        );
      }
      throw error;
    }
  }

  /**
   * 3. AccessToken 재발급
   * POST /api-partner/v1/apps-in-toss/user/oauth2/refresh-token
   */
  async refreshToken(request: RefreshTokenRequest): Promise<TokenData> {
    try {
      const response = await this.client.post<TossApiResponse<TokenData>>(
        '/api-partner/v1/apps-in-toss/user/oauth2/refresh-token',
        request
      );

      if (response.data.resultType === 'SUCCESS' && response.data.success) {
        console.log('✅ Token refreshed successfully');
        return response.data.success;
      }

      throw new Error(
        response.data.error?.reason || 'Token refresh failed'
      );
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          error.response?.data?.error?.reason || '토큰 갱신 실패'
        );
      }
      throw error;
    }
  }

  /**
   * 4. 사용자 정보 조회
   * GET /api-partner/v1/apps-in-toss/user/oauth2/login-me
   */
  async getUserInfo(accessToken: string): Promise<EncryptedUserData> {
    try {
      const response = await this.client.get<TossApiResponse<EncryptedUserData>>(
        '/api-partner/v1/apps-in-toss/user/oauth2/login-me',
        {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        }
      );

      if (response.data.resultType === 'SUCCESS' && response.data.success) {
        console.log('✅ User info retrieved successfully');
        return response.data.success;
      }

      throw new Error(
        response.data.error?.reason || 'Failed to get user info'
      );
    } catch (error) {
      if (axios.isAxiosError(error)) {
        // invalid_grant: 토큰 만료
        if (error.response?.data?.error === 'invalid_grant') {
          throw new Error('AccessToken이 만료되었습니다. 재발급이 필요합니다.');
        }
        throw new Error(
          error.response?.data?.error?.reason || '사용자 정보 조회 실패'
        );
      }
      throw error;
    }
  }

  /**
   * 6. 로그인 연결 끊기 (AccessToken)
   * POST /api-partner/v1/apps-in-toss/user/oauth2/access/remove-by-access-token
   */
  async removeAccessByToken(accessToken: string): Promise<void> {
    try {
      const response = await this.client.post(
        '/api-partner/v1/apps-in-toss/user/oauth2/access/remove-by-access-token',
        {},
        {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        }
      );

      if (response.data.resultType === 'SUCCESS') {
        console.log('✅ Access removed successfully');
        return;
      }

      throw new Error(
        response.data.error?.reason || 'Failed to remove access'
      );
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          error.response?.data?.error?.reason || '연결 해제 실패'
        );
      }
      throw error;
    }
  }

  /**
   * 6. 로그인 연결 끊기 (UserKey)
   * POST /api-partner/v1/apps-in-toss/user/oauth2/access/remove-by-user-key
   */
  async removeAccessByUserKey(accessToken: string, userKey: number): Promise<void> {
    try {
      const response = await this.client.post(
        '/api-partner/v1/apps-in-toss/user/oauth2/access/remove-by-user-key',
        { userKey },
        {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        }
      );

      if (response.data.resultType === 'SUCCESS') {
        console.log('✅ Access removed by userKey successfully');
        return;
      }

      throw new Error(
        response.data.error?.reason || 'Failed to remove access by userKey'
      );
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          error.response?.data?.error?.reason || '연결 해제 실패'
        );
      }
      throw error;
    }
  }
}

export const tossApiService = new TossApiService();
```

### 3.4 AES-256-GCM 복호화 서비스

```typescript
// src/services/crypto.ts
import * as crypto from 'crypto';
import { EncryptedUserData, DecryptedUserData } from '../types';

class CryptoService {
  private decryptionKey: Buffer;
  private aad: Buffer;

  constructor() {
    const key = process.env.TOSS_DECRYPTION_KEY;
    const aad = process.env.TOSS_AAD;

    if (!key || !aad) {
      throw new Error('TOSS_DECRYPTION_KEY and TOSS_AAD must be set in environment variables');
    }

    // Hex 문자열을 Buffer로 변환
    this.decryptionKey = Buffer.from(key, 'hex');
    this.aad = Buffer.from(aad, 'hex');

    console.log('✅ Crypto service initialized');
    console.log(`   Key length: ${this.decryptionKey.length} bytes`);
    console.log(`   AAD length: ${this.aad.length} bytes`);
  }

  /**
   * AES-256-GCM 복호화
   * 
   * 데이터 형식:
   * [IV (12 bytes)] + [Encrypted Data] + [Auth Tag (16 bytes)]
   */
  private decrypt(encryptedData: string): string {
    try {
      // Base64 디코딩
      const buffer = Buffer.from(encryptedData, 'base64');

      // IV 추출 (처음 12바이트)
      const iv = buffer.slice(0, 12);
      
      // 암호문 + Auth Tag
      const encryptedWithTag = buffer.slice(12);
      
      // Auth Tag 추출 (마지막 16바이트)
      const authTag = encryptedWithTag.slice(-16);
      
      // 암호문
      const encrypted = encryptedWithTag.slice(0, -16);

      // Decipher 생성
      const decipher = crypto.createDecipheriv(
        'aes-256-gcm',
        this.decryptionKey,
        iv
      );

      // AAD 설정
      decipher.setAAD(this.aad);
      
      // Auth Tag 설정
      decipher.setAuthTag(authTag);

      // 복호화
      let decrypted = decipher.update(encrypted, undefined, 'utf8');
      decrypted += decipher.final('utf8');

      return decrypted;
    } catch (error) {
      console.error('❌ Decryption failed:', error);
      throw new Error('복호화 실패: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  }

  /**
   * 사용자 정보 복호화
   */
  decryptUserData(encryptedData: EncryptedUserData): DecryptedUserData {
    const decrypted: DecryptedUserData = {
      ...encryptedData
    };

    // 암호화된 필드만 복호화
    const fieldsToDecrypt: (keyof EncryptedUserData)[] = [
      'name',
      'phone',
      'birthday',
      'ci',
      'gender',
      'nationality'
    ];

    for (const field of fieldsToDecrypt) {
      const value = encryptedData[field];
      if (value && typeof value === 'string' && value !== 'null') {
        try {
          decrypted[field] = this.decrypt(value) as any;
        } catch (error) {
          console.error(`Failed to decrypt field: ${field}`, error);
          decrypted[field] = undefined;
        }
      }
    }

    // email은 암호화되어 있지만 null일 수 있음
    if (encryptedData.email && encryptedData.email !== 'null') {
      try {
        decrypted.email = this.decrypt(encryptedData.email);
      } catch (error) {
        console.error('Failed to decrypt email', error);
        decrypted.email = null;
      }
    }

    console.log('✅ User data decrypted successfully');
    return decrypted;
  }
}

export const cryptoService = new CryptoService();
```

### 3.5 인증 라우터

```typescript
// src/routes/auth.ts
import { Router, Request, Response } from 'express';
import { tossApiService } from '../services/tossApi';
import { cryptoService } from '../services/crypto';
import {
  GenerateTokenRequest,
  RefreshTokenRequest,
  UnlinkCallbackData
} from '../types';

const router = Router();

/**
 * POST /api/auth/token
 * AccessToken 발급
 */
router.post('/token', async (req: Request, res: Response) => {
  try {
    const request: GenerateTokenRequest = req.body;

    if (!request.authorizationCode || !request.referrer) {
      return res.status(400).json({
        error: 'authorizationCode and referrer are required'
      });
    }

    const tokenData = await tossApiService.generateToken(request);
    
    res.json(tokenData);
  } catch (error) {
    console.error('Token generation error:', error);
    res.status(500).json({
      error: error instanceof Error ? error.message : 'Token generation failed'
    });
  }
});

/**
 * POST /api/auth/refresh
 * AccessToken 재발급
 */
router.post('/refresh', async (req: Request, res: Response) => {
  try {
    const request: RefreshTokenRequest = req.body;

    if (!request.refreshToken) {
      return res.status(400).json({
        error: 'refreshToken is required'
      });
    }

    const tokenData = await tossApiService.refreshToken(request);
    
    res.json(tokenData);
  } catch (error) {
    console.error('Token refresh error:', error);
    res.status(500).json({
      error: error instanceof Error ? error.message : 'Token refresh failed'
    });
  }
});

/**
 * GET /api/auth/me
 * 사용자 정보 조회 (복호화된 데이터 반환)
 */
router.get('/me', async (req: Request, res: Response) => {
  try {
    const authHeader = req.headers.authorization;

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({
        error: 'Authorization header is required'
      });
    }

    const accessToken = authHeader.substring(7);

    // 1. 토스 API에서 암호화된 사용자 정보 조회
    const encryptedUserData = await tossApiService.getUserInfo(accessToken);

    // 2. 복호화
    const decryptedUserData = cryptoService.decryptUserData(encryptedUserData);

    res.json(decryptedUserData);
  } catch (error) {
    console.error('Get user info error:', error);
    res.status(500).json({
      error: error instanceof Error ? error.message : 'Failed to get user info'
    });
  }
});

/**
 * POST /api/auth/logout
 * 로그인 연결 끊기
 */
router.post('/logout', async (req: Request, res: Response) => {
  try {
    const authHeader = req.headers.authorization;

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({
        error: 'Authorization header is required'
      });
    }

    const accessToken = authHeader.substring(7);

    await tossApiService.removeAccessByToken(accessToken);

    res.json({ success: true });
  } catch (error) {
    console.error('Logout error:', error);
    res.status(500).json({
      error: error instanceof Error ? error.message : 'Logout failed'
    });
  }
});

/**
 * POST /api/auth/logout-by-user-key
 * UserKey로 로그인 연결 끊기
 */
router.post('/logout-by-user-key', async (req: Request, res: Response) => {
  try {
    const authHeader = req.headers.authorization;
    const { userKey } = req.body;

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({
        error: 'Authorization header is required'
      });
    }

    if (!userKey) {
      return res.status(400).json({
        error: 'userKey is required'
      });
    }

    const accessToken = authHeader.substring(7);

    await tossApiService.removeAccessByUserKey(accessToken, userKey);

    res.json({ success: true, userKey });
  } catch (error) {
    console.error('Logout by userKey error:', error);
    res.status(500).json({
      error: error instanceof Error ? error.message : 'Logout failed'
    });
  }
});

/**
 * POST /api/auth/unlink-callback
 * 토스에서 연결 해제 시 콜백
 */
router.post('/unlink-callback', async (req: Request, res: Response) => {
  try {
    const data: UnlinkCallbackData = req.body;

    console.log('🔔 Unlink callback received:', data);

    // TODO: 데이터베이스에서 사용자 처리
    // - UNLINK: 사용자가 직접 연결 해제
    // - WITHDRAWAL_TERMS: 약관 동의 철회
    // - WITHDRAWAL_TOSS: 토스 회원 탈퇴

    res.json({ success: true });
  } catch (error) {
    console.error('Unlink callback error:', error);
    res.status(500).json({
      error: error instanceof Error ? error.message : 'Callback processing failed'
    });
  }
});

/**
 * GET /api/auth/unlink-callback
 * GET 방식 콜백 (쿼리 파라미터)
 */
router.get('/unlink-callback', async (req: Request, res: Response) => {
  try {
    const { userKey, referrer } = req.query;

    console.log('🔔 Unlink callback received (GET):', { userKey, referrer });

    res.json({ success: true });
  } catch (error) {
    console.error('Unlink callback error:', error);
    res.status(500).json({
      error: error instanceof Error ? error.message : 'Callback processing failed'
    });
  }
});

export default router;
```

### 3.6 서버 진입점

```typescript
// src/index.ts
import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import authRouter from './routes/auth';

// 환경 변수 로드
dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// 미들웨어
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'http://localhost:5173',
  credentials: true
}));
app.use(express.json());

// 라우터
app.use('/api/auth', authRouter);

// 헬스 체크
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// 서버 시작
app.listen(PORT, () => {
  console.log(`✅ Server running on http://localhost:${PORT}`);
  console.log(`   Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`   CORS origin: ${process.env.CORS_ORIGIN}`);
});
```

### 3.7 실행 스크립트

```json
// package.json
{
  "name": "toss-login-backend",
  "version": "1.0.0",
  "scripts": {
    "dev": "nodemon --exec ts-node src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js"
  }
}
```

```bash
# 개발 서버 실행
npm run dev

# 프로덕션 빌드
npm run build
npm start
```

백엔드 구현이 완료되었습니다! 다음 섹션에서 FastAPI 버전을 구현하겠습니다.

## 4. 백엔드 구현 - Python FastAPI

### 4.1 프로젝트 초기 설정

```bash
# 프로젝트 생성
mkdir toss-login-fastapi
cd toss-login-fastapi

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install fastapi uvicorn httpx pydantic-settings python-dotenv pycryptodome
```

**프로젝트 구조:**

```
toss-login-fastapi/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 앱
│   ├── config.py            # 설정
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic 모델
│   ├── services/
│   │   ├── __init__.py
│   │   ├── toss_api.py      # 토스 API 클라이언트
│   │   └── crypto.py        # 복호화 서비스
│   └── routers/
│       ├── __init__.py
│       └── auth.py          # 인증 라우터
├── .env
├── requirements.txt
└── README.md
```

**환경 변수:**

```bash
# .env
TOSS_API_BASE_URL=https://apps-in-toss-api.toss.im
TOSS_DECRYPTION_KEY=your_decryption_key_hex
TOSS_AAD=your_aad_hex
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

### 4.2 Pydantic 모델 정의

```python
# app/models/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, Literal

class GenerateTokenRequest(BaseModel):
    """AccessToken 발급 요청"""
    authorization_code: str = Field(..., alias="authorizationCode")
    referrer: str

    class Config:
        populate_by_name = True

class TokenResponse(BaseModel):
    """토큰 응답"""
    token_type: Literal["Bearer"] = Field(..., alias="tokenType")
    access_token: str = Field(..., alias="accessToken")
    refresh_token: str = Field(..., alias="refreshToken")
    expires_in: int = Field(..., alias="expiresIn")
    scope: str

    class Config:
        populate_by_name = True

class RefreshTokenRequest(BaseModel):
    """RefreshToken 재발급 요청"""
    refresh_token: str = Field(..., alias="refreshToken")

    class Config:
        populate_by_name = True

class EncryptedUserInfo(BaseModel):
    """암호화된 사용자 정보"""
    user_key: int = Field(..., alias="userKey")
    scope: str
    agreed_terms: list[str] = Field(..., alias="agreedTerms")
    name: Optional[str] = None
    phone: Optional[str] = None
    birthday: Optional[str] = None
    ci: Optional[str] = None
    di: Optional[str] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    email: Optional[str] = None

    class Config:
        populate_by_name = True

class DecryptedUserInfo(BaseModel):
    """복호화된 사용자 정보"""
    user_key: int = Field(..., alias="userKey")
    scope: str
    agreed_terms: list[str] = Field(..., alias="agreedTerms")
    name: Optional[str] = None
    phone: Optional[str] = None
    birthday: Optional[str] = None
    ci: Optional[str] = None
    di: Optional[str] = None
    gender: Optional[Literal["MALE", "FEMALE"]] = None
    nationality: Optional[Literal["LOCAL", "FOREIGNER"]] = None
    email: Optional[str] = None

    class Config:
        populate_by_name = True

class TossApiResponse(BaseModel):
    """토스 API 응답 래퍼"""
    result_type: Literal["SUCCESS", "FAIL"] = Field(..., alias="resultType")
    success: Optional[dict] = None
    error: Optional[dict] = None

    class Config:
        populate_by_name = True

class UnlinkCallbackData(BaseModel):
    """로그인 연결 해제 콜백"""
    user_key: int = Field(..., alias="userKey")
    referrer: Literal["UNLINK", "WITHDRAWAL_TERMS", "WITHDRAWAL_TOSS"]

    class Config:
        populate_by_name = True
```

### 4.3 설정 파일

```python
# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache
import json

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 토스 API
    toss_api_base_url: str = "https://apps-in-toss-api.toss.im"
    toss_decryption_key: str
    toss_aad: str
    
    # 서버
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # CORS
    cors_origins: str = '["http://localhost:5173"]'
    
    @property
    def cors_origins_list(self) -> list[str]:
        """CORS origins를 리스트로 파싱"""
        return json.loads(self.cors_origins)
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤"""
    return Settings()
```

### 4.4 AES-256-GCM 복호화 서비스

```python
# app/services/crypto.py
import base64
from Crypto.Cipher import AES
from app.config import get_settings
from app.models.schemas import EncryptedUserInfo, DecryptedUserInfo
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

class CryptoService:
    """AES-256-GCM 복호화 서비스"""
    
    def __init__(self):
        # Hex 문자열을 바이트로 변환
        self.decryption_key = bytes.fromhex(settings.toss_decryption_key)
        self.aad = bytes.fromhex(settings.toss_aad)
        
        logger.info("✅ Crypto service initialized")
        logger.info(f"   Key length: {len(self.decryption_key)} bytes")
        logger.info(f"   AAD length: {len(self.aad)} bytes")
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        AES-256-GCM 복호화
        
        데이터 형식: [IV (12 bytes)] + [Encrypted Data] + [Auth Tag (16 bytes)]
        """
        try:
            # Base64 디코딩
            buffer = base64.b64decode(encrypted_data)
            
            # IV 추출 (처음 12바이트)
            iv = buffer[:12]
            
            # Auth Tag 추출 (마지막 16바이트)
            auth_tag = buffer[-16:]
            
            # 암호문 추출
            ciphertext = buffer[12:-16]
            
            # Cipher 생성
            cipher = AES.new(
                self.decryption_key,
                AES.MODE_GCM,
                nonce=iv
            )
            
            # AAD 설정
            cipher.update(self.aad)
            
            # 복호화
            decrypted = cipher.decrypt_and_verify(ciphertext, auth_tag)
            
            return decrypted.decode('utf-8')
            
        except Exception as e:
            logger.error(f"❌ Decryption failed: {e}")
            raise ValueError(f"복호화 실패: {str(e)}")
    
    def decrypt_user_data(
        self, 
        encrypted_data: EncryptedUserInfo
    ) -> DecryptedUserInfo:
        """사용자 정보 복호화"""
        
        # 기본 데이터 복사
        decrypted_dict = encrypted_data.model_dump()
        
        # 암호화된 필드 복호화
        encrypted_fields = [
            'name', 'phone', 'birthday', 'ci', 
            'gender', 'nationality'
        ]
        
        for field in encrypted_fields:
            value = getattr(encrypted_data, field)
            if value and value != 'null':
                try:
                    decrypted_dict[field] = self.decrypt(value)
                except Exception as e:
                    logger.error(f"Failed to decrypt field '{field}': {e}")
                    decrypted_dict[field] = None
        
        # email 처리
        if encrypted_data.email and encrypted_data.email != 'null':
            try:
                decrypted_dict['email'] = self.decrypt(encrypted_data.email)
            except Exception as e:
                logger.error(f"Failed to decrypt email: {e}")
                decrypted_dict['email'] = None
        
        logger.info("✅ User data decrypted successfully")
        return DecryptedUserInfo(**decrypted_dict)

# 싱글톤 인스턴스
crypto_service = CryptoService()
```

### 4.5 토스 API 클라이언트

```python
# app/services/toss_api.py
import httpx
from app.config import get_settings
from app.models.schemas import (
    GenerateTokenRequest,
    TokenResponse,
    RefreshTokenRequest,
    EncryptedUserInfo,
    TossApiResponse
)
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

class TossApiService:
    """토스 API 클라이언트"""
    
    def __init__(self):
        self.base_url = settings.toss_api_base_url
        self.timeout = 10.0
    
    async def generate_token(
        self, 
        request: GenerateTokenRequest
    ) -> TokenResponse:
        """
        AccessToken 발급
        POST /api-partner/v1/apps-in-toss/user/oauth2/generate-token
        """
        url = f"{self.base_url}/api-partner/v1/apps-in-toss/user/oauth2/generate-token"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url,
                    json=request.model_dump(by_alias=True),
                    headers={"Content-Type": "application/json"}
                )
                
                # invalid_grant 에러 처리
                if response.status_code == 400:
                    data = response.json()
                    if data.get("error") == "invalid_grant":
                        raise ValueError("인가 코드가 만료되었거나 이미 사용되었습니다.")
                
                response.raise_for_status()
                
                data = TossApiResponse(**response.json())
                
                if data.result_type == "SUCCESS" and data.success:
                    logger.info("✅ Token generated successfully")
                    return TokenResponse(**data.success)
                
                raise ValueError(
                    data.error.get("reason", "Token generation failed")
                    if data.error else "Token generation failed"
                )
                
            except httpx.HTTPError as e:
                logger.error(f"❌ Token generation failed: {e}")
                raise ValueError(f"토큰 발급 실패: {str(e)}")
    
    async def refresh_token(
        self, 
        request: RefreshTokenRequest
    ) -> TokenResponse:
        """
        AccessToken 재발급
        POST /api-partner/v1/apps-in-toss/user/oauth2/refresh-token
        """
        url = f"{self.base_url}/api-partner/v1/apps-in-toss/user/oauth2/refresh-token"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url,
                    json=request.model_dump(by_alias=True),
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                
                data = TossApiResponse(**response.json())
                
                if data.result_type == "SUCCESS" and data.success:
                    logger.info("✅ Token refreshed successfully")
                    return TokenResponse(**data.success)
                
                raise ValueError(
                    data.error.get("reason", "Token refresh failed")
                    if data.error else "Token refresh failed"
                )
                
            except httpx.HTTPError as e:
                logger.error(f"❌ Token refresh failed: {e}")
                raise ValueError(f"토큰 갱신 실패: {str(e)}")
    
    async def get_user_info(self, access_token: str) -> EncryptedUserInfo:
        """
        사용자 정보 조회
        GET /api-partner/v1/apps-in-toss/user/oauth2/login-me
        """
        url = f"{self.base_url}/api-partner/v1/apps-in-toss/user/oauth2/login-me"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                # invalid_grant 에러 처리
                if response.status_code == 401:
                    data = response.json()
                    if data.get("error") == "invalid_grant":
                        raise ValueError("AccessToken이 만료되었습니다.")
                
                response.raise_for_status()
                
                data = TossApiResponse(**response.json())
                
                if data.result_type == "SUCCESS" and data.success:
                    logger.info("✅ User info retrieved successfully")
                    return EncryptedUserInfo(**data.success)
                
                raise ValueError(
                    data.error.get("reason", "Failed to get user info")
                    if data.error else "Failed to get user info"
                )
                
            except httpx.HTTPError as e:
                logger.error(f"❌ Get user info failed: {e}")
                raise ValueError(f"사용자 정보 조회 실패: {str(e)}")
    
    async def remove_access_by_token(self, access_token: str) -> None:
        """
        로그인 연결 끊기 (AccessToken)
        POST /api-partner/v1/apps-in-toss/user/oauth2/access/remove-by-access-token
        """
        url = f"{self.base_url}/api-partner/v1/apps-in-toss/user/oauth2/access/remove-by-access-token"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                response.raise_for_status()
                
                logger.info("✅ Access removed successfully")
                
            except httpx.HTTPError as e:
                logger.error(f"❌ Remove access failed: {e}")
                raise ValueError(f"연결 해제 실패: {str(e)}")
    
    async def remove_access_by_user_key(
        self, 
        access_token: str, 
        user_key: int
    ) -> None:
        """
        로그인 연결 끊기 (UserKey)
        POST /api-partner/v1/apps-in-toss/user/oauth2/access/remove-by-user-key
        """
        url = f"{self.base_url}/api-partner/v1/apps-in-toss/user/oauth2/access/remove-by-user-key"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url,
                    json={"userKey": user_key},
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                response.raise_for_status()
                
                logger.info(f"✅ Access removed by userKey: {user_key}")
                
            except httpx.HTTPError as e:
                logger.error(f"❌ Remove access by userKey failed: {e}")
                raise ValueError(f"연결 해제 실패: {str(e)}")

# 싱글톤 인스턴스
toss_api_service = TossApiService()
```

### 4.6 인증 라우터

```python
# app/routers/auth.py
from fastapi import APIRouter, Header, HTTPException, status
from typing import Optional
from app.models.schemas import (
    GenerateTokenRequest,
    TokenResponse,
    RefreshTokenRequest,
    DecryptedUserInfo,
    UnlinkCallbackData
)
from app.services.toss_api import toss_api_service
from app.services.crypto import crypto_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/token", response_model=TokenResponse)
async def generate_token(request: GenerateTokenRequest):
    """
    AccessToken 발급
    
    - **authorizationCode**: 인가 코드 (10분 유효)
    - **referrer**: sandbox | DEFAULT
    """
    try:
        token_data = await toss_api_service.generate_token(request)
        return token_data
    except Exception as e:
        logger.error(f"Token generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    AccessToken 재발급
    
    - **refreshToken**: RefreshToken (14일 유효)
    """
    try:
        token_data = await toss_api_service.refresh_token(request)
        return token_data
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/me", response_model=DecryptedUserInfo)
async def get_user_info(authorization: Optional[str] = Header(None)):
    """
    사용자 정보 조회 (복호화된 데이터)
    
    - **Authorization**: Bearer {accessToken}
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required"
        )
    
    access_token = authorization[7:]  # "Bearer " 제거
    
    try:
        # 1. 암호화된 사용자 정보 조회
        encrypted_data = await toss_api_service.get_user_info(access_token)
        
        # 2. 복호화
        decrypted_data = crypto_service.decrypt_user_data(encrypted_data)
        
        return decrypted_data
        
    except Exception as e:
        logger.error(f"Get user info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """
    로그인 연결 끊기
    
    - **Authorization**: Bearer {accessToken}
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required"
        )
    
    access_token = authorization[7:]
    
    try:
        await toss_api_service.remove_access_by_token(access_token)
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/logout-by-user-key")
async def logout_by_user_key(
    user_key: int,
    authorization: Optional[str] = Header(None)
):
    """
    UserKey로 로그인 연결 끊기
    
    - **userKey**: 사용자 식별자
    - **Authorization**: Bearer {accessToken}
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required"
        )
    
    access_token = authorization[7:]
    
    try:
        await toss_api_service.remove_access_by_user_key(access_token, user_key)
        return {"success": True, "userKey": user_key}
        
    except Exception as e:
        logger.error(f"Logout by userKey error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/unlink-callback")
async def unlink_callback_post(data: UnlinkCallbackData):
    """
    토스 연결 해제 콜백 (POST)
    
    - **userKey**: 사용자 식별자
    - **referrer**: UNLINK | WITHDRAWAL_TERMS | WITHDRAWAL_TOSS
    """
    logger.info(f"🔔 Unlink callback received: {data}")
    
    # TODO: 데이터베이스 처리
    # - UNLINK: 사용자가 직접 연결 해제
    # - WITHDRAWAL_TERMS: 약관 동의 철회
    # - WITHDRAWAL_TOSS: 토스 회원 탈퇴
    
    return {"success": True}

@router.get("/unlink-callback")
async def unlink_callback_get(userKey: int, referrer: str):
    """
    토스 연결 해제 콜백 (GET)
    
    - **userKey**: 사용자 식별자
    - **referrer**: UNLINK | WITHDRAWAL_TERMS | WITHDRAWAL_TOSS
    """
    logger.info(f"🔔 Unlink callback received (GET): userKey={userKey}, referrer={referrer}")
    
    return {"success": True}
```

### 4.7 메인 앱

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import auth
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
settings = get_settings()

# FastAPI 앱
app = FastAPI(
    title="Toss Login API",
    description="토스 앱인토스 로그인 OAuth 2.0 구현",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router, prefix="/api")

# 헬스 체크
@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "ok",
        "service": "toss-login-api",
        "version": "1.0.0"
    }

@app.on_event("startup")
async def startup_event():
    """앱 시작 이벤트"""
    logger.info("✅ Toss Login API started")
    logger.info(f"   Environment: {'development' if settings.debug else 'production'}")
    logger.info(f"   CORS origins: {settings.cors_origins_list}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
```

### 4.8 실행

```bash
# 서버 실행
python -m app.main

# 또는 uvicorn 직접 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# API 문서 확인
# http://localhost:8000/docs
```

**requirements.txt:**

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
httpx==0.25.2
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
pycryptodome==3.19.0
```

FastAPI 백엔드 구현 완료! 다음 섹션에서 테스트와 배포를 다루겠습니다.

## 5. 전체 플로우 테스트 & 트러블슈팅

### 5.1 통합 테스트 시나리오

**1) 로컬 환경 전체 플로우 테스트**

```bash
# 1. 백엔드 실행 (Terminal 1)
cd toss-login-backend
npm run dev
# 또는
cd toss-login-fastapi
python -m app.main

# 2. 프론트엔드 실행 (Terminal 2)
cd toss-login-app
npm run dev

# 3. 샌드박스 앱에서 테스트
# - 샌드박스 앱 설치 및 개발자 로그인
# - http://localhost:5173 접속
# - 로그인 버튼 클릭
```

**2) Postman/cURL 테스트**

```bash
# Step 1: AccessToken 발급
curl -X POST http://localhost:3000/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "authorizationCode": "your_authorization_code",
    "referrer": "sandbox"
  }'

# 응답:
# {
#   "tokenType": "Bearer",
#   "accessToken": "eyJraWQi...",
#   "refreshToken": "xNEYPASw...",
#   "expiresIn": 3599,
#   "scope": "user_ci user_name user_phone"
# }

# Step 2: 사용자 정보 조회
ACCESS_TOKEN="your_access_token"

curl -X GET http://localhost:3000/api/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 응답 (복호화된 데이터):
# {
#   "userKey": 443731104,
#   "name": "홍길동",
#   "phone": "01012345678",
#   "birthday": "19900101",
#   "ci": "...",
#   "gender": "MALE",
#   "nationality": "LOCAL",
#   "agreedTerms": ["terms_tag1", "terms_tag2"]
# }

# Step 3: 토큰 갱신
REFRESH_TOKEN="your_refresh_token"

curl -X POST http://localhost:3000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refreshToken": "'$REFRESH_TOKEN'"
  }'

# Step 4: 로그아웃
curl -X POST http://localhost:3000/api/auth/logout \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 5.2 에러 시나리오 테스트

**1) 만료된 인가 코드**

```javascript
// 프론트엔드
const result = await appLogin();

// 10분 후 토큰 발급 시도
await authService.generateToken({
  authorizationCode: result.authorizationCode, // 만료됨
  referrer: result.referrer
});

// 에러 응답:
// {
//   "error": "invalid_grant"
// }
// 또는
// {
//   "error": "인가 코드가 만료되었거나 이미 사용되었습니다."
// }

// 해결책: 다시 appLogin() 호출
```

**2) 중복 토큰 발급**

```javascript
const result = await appLogin();

// 첫 번째 호출 (성공)
const token1 = await authService.generateToken({
  authorizationCode: result.authorizationCode,
  referrer: result.referrer
});

// 두 번째 호출 (실패)
const token2 = await authService.generateToken({
  authorizationCode: result.authorizationCode, // 이미 사용됨
  referrer: result.referrer
});

// 에러: "invalid_grant"
```

**3) 만료된 AccessToken**

```python
# 백엔드
@router.get("/me")
async def get_user_info(authorization: str = Header(None)):
    access_token = authorization[7:]
    
    try:
        encrypted_data = await toss_api_service.get_user_info(access_token)
        # ...
    except ValueError as e:
        if "만료" in str(e):
            # AccessToken 만료 → RefreshToken으로 재발급 필요
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="AccessToken expired. Please refresh."
            )
```

**프론트엔드 자동 갱신 로직:**

```typescript
// src/services/authService.ts
class AuthService {
  async getUserInfo(accessToken: string): Promise<DecryptedUserInfo> {
    try {
      const response = await axios.get(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 401) {
        // AccessToken 만료 → 자동 갱신
        const refreshToken = localStorage.getItem('refreshToken');
        if (refreshToken) {
          const newToken = await this.refreshToken(refreshToken);
          localStorage.setItem('accessToken', newToken.accessToken);
          
          // 재시도
          return this.getUserInfo(newToken.accessToken);
        }
      }
      throw error;
    }
  }
}
```

### 5.3 트러블슈팅

**문제 1: 로컬 개발 중 인증 에러**

```
증상: appLogin() 호출 시 "인증 실패" 또는 "Not in Toss app"
```

**원인 & 해결책:**

```markdown
1. 샌드박스 앱 미설치
   → https://developers-apps-in-toss.toss.im/development/test/sandbox.html
   → 샌드박스 앱 다운로드 및 개발자 로그인

2. 개발자 계정 로그인 안 됨
   → 샌드박스 앱 실행 → 우측 상단 메뉴 → 개발자 로그인

3. 인증 토큰 만료
   → 새로운 토큰 발급 (appLogin 재호출)

4. 콘솔에서 앱 승인 안 됨
   → https://console-apps-in-toss.toss.im/
   → 앱 상태 확인 → 로그인 기능 활성화
```

**문제 2: 복호화 실패**

```python
# 에러:
# ValueError: 복호화 실패: MAC check failed
```

**원인 & 해결책:**

```markdown
1. 잘못된 복호화 키 또는 AAD
   → 토스 콘솔 이메일에서 받은 키 확인
   → Hex 형식인지 확인 (Base64 아님)

2. IV 또는 Auth Tag 추출 오류
   → 데이터 형식: [IV 12바이트] + [암호문] + [AuthTag 16바이트]
   → buffer 슬라이싱 위치 확인

3. AAD 미설정
   → cipher.setAAD(aad) / cipher.update(aad) 호출 확인
```

**복호화 테스트 코드:**

```python
# test_crypto.py
from app.services.crypto import crypto_service

# 토스 API에서 받은 암호화된 샘플 데이터
encrypted_name = "ENCRYPTED_VALUE_FROM_API"

try:
    decrypted = crypto_service.decrypt(encrypted_name)
    print(f"✅ Decryption successful: {decrypted}")
except Exception as e:
    print(f"❌ Decryption failed: {e}")
```

**문제 3: CORS 에러**

```
Access to XMLHttpRequest has been blocked by CORS policy
```

**해결책:**

```typescript
// 백엔드 CORS 설정 확인
// Express
app.use(cors({
  origin: 'http://localhost:5173',
  credentials: true
}));

// FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**문제 4: RefreshToken 갱신 실패**

```
에러: "Token refresh failed"
```

**원인 & 해결책:**

```markdown
1. RefreshToken 만료 (14일)
   → 사용자에게 재로그인 요청

2. 네트워크 타임아웃
   → httpx timeout 증가 (default 10초)

3. 서버 에러
   → 로그 확인 → 토스 API 상태 확인
```

### 5.4 토큰 관리 모범 사례

**1) 안전한 토큰 저장**

```typescript
// ❌ 나쁜 예: localStorage (XSS 공격 취약)
localStorage.setItem('accessToken', token);

// ✅ 좋은 예: HttpOnly 쿠키 (서버에서 설정)
// 백엔드
res.cookie('accessToken', token, {
  httpOnly: true,
  secure: true,
  sameSite: 'strict',
  maxAge: 3600000 // 1시간
});
```

**2) 토큰 만료 처리**

```typescript
// Axios Interceptor
axios.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const refreshToken = localStorage.getItem('refreshToken');
      if (refreshToken) {
        const newToken = await authService.refreshToken(refreshToken);
        localStorage.setItem('accessToken', newToken.accessToken);
        
        // 원래 요청 재시도
        originalRequest.headers['Authorization'] = `Bearer ${newToken.accessToken}`;
        return axios(originalRequest);
      }
    }
    
    return Promise.reject(error);
  }
);
```

**3) 토큰 갱신 타이밍**

```typescript
// expiresIn 기반 자동 갱신
const scheduleTokenRefresh = (expiresIn: number) => {
  // 만료 5분 전에 갱신
  const refreshTime = (expiresIn - 300) * 1000;
  
  setTimeout(async () => {
    const refreshToken = localStorage.getItem('refreshToken');
    if (refreshToken) {
      const newToken = await authService.refreshToken(refreshToken);
      localStorage.setItem('accessToken', newToken.accessToken);
      
      // 재귀적으로 스케줄링
      scheduleTokenRefresh(newToken.expiresIn);
    }
  }, refreshTime);
};

// 로그인 후 호출
const { expiresIn } = tokenResponse;
scheduleTokenRefresh(expiresIn);
```

### 5.5 콘솔 설정 체크리스트

```markdown
## 앱인토스 콘솔 설정 확인

### 1. 앱 등록
- [ ] 앱 이름, 설명, 아이콘 등록
- [ ] 앱 승인 완료

### 2. 로그인 기능 활성화
- [ ] "로그인" 기능 토글 활성화
- [ ] Redirect URI 설정 (로컬: http://localhost:5173)
- [ ] 프로덕션 도메인 등록

### 3. 약관 등록
- [ ] 필수 약관 등록 (서비스 이용약관, 개인정보 처리방침)
- [ ] 선택 약관 등록 (마케팅 수신 동의 등)
- [ ] 약관 태그 설정 (terms_tag1, terms_tag2)

### 4. 복호화 키 수신
- [ ] 이메일로 복호화 키 수신 확인
- [ ] 복호화 키 환경 변수 설정
- [ ] AAD 값 환경 변수 설정

### 5. 콜백 URL 설정 (선택)
- [ ] 연결 해제 콜백 URL 입력
- [ ] Basic Auth 헤더 설정 (필요시)
- [ ] GET/POST 방식 선택
```

### 5.6 성능 최적화

**1) 토큰 캐싱**

```python
# 백엔드: 사용자 정보 캐싱 (Redis)
from redis import Redis
import json

redis_client = Redis(host='localhost', port=6379, db=0)

async def get_user_info_cached(access_token: str) -> DecryptedUserInfo:
    # 캐시 조회
    cache_key = f"user_info:{access_token[:20]}"
    cached = redis_client.get(cache_key)
    
    if cached:
        logger.info("✅ Cache hit")
        return DecryptedUserInfo(**json.loads(cached))
    
    # 캐시 미스: API 호출 및 복호화
    encrypted_data = await toss_api_service.get_user_info(access_token)
    decrypted_data = crypto_service.decrypt_user_data(encrypted_data)
    
    # 캐시 저장 (1시간)
    redis_client.setex(
        cache_key,
        3600,
        decrypted_data.model_dump_json()
    )
    
    return decrypted_data
```

**2) 복호화 배치 처리**

```python
# 여러 필드 한 번에 복호화
async def decrypt_batch(encrypted_fields: dict) -> dict:
    loop = asyncio.get_event_loop()
    
    tasks = {
        field: loop.run_in_executor(
            None, 
            crypto_service.decrypt, 
            value
        )
        for field, value in encrypted_fields.items()
        if value and value != 'null'
    }
    
    results = await asyncio.gather(*tasks.values())
    
    return {
        field: result
        for field, result in zip(tasks.keys(), results)
    }
```

## 6. 결론

### 6.1 구현 요약

이 가이드에서 다룬 내용:

✅ **프론트엔드 (React + TypeScript)**
- Toss SDK `appLogin()` 통합
- 커스텀 훅 `useTossLogin` 구현
- 자동 토큰 갱신 로직

✅ **백엔드 (Node.js Express & Python FastAPI)**
- 토스 API 클라이언트
- AES-256-GCM 복호화
- RESTful API 엔드포인트

✅ **보안 & 성능**
- 토큰 안전 저장
- 자동 갱신
- 에러 핸들링
- 캐싱 전략

### 6.2 핵심 포인트

**1) OAuth 2.0 플로우**

```
appLogin() 
  → authorizationCode (10분)
  → AccessToken (1시간) 
  → RefreshToken (14일)
  → 사용자 정보 (암호화)
  → 복호화 (AES-256-GCM)
```

**2) 타임라인**

| 단계 | 유효시간 | 갱신 방법 |
|------|---------|----------|
| 인가 코드 | 10분 | appLogin() 재호출 |
| AccessToken | 1시간 | RefreshToken 사용 |
| RefreshToken | 14일 | 재로그인 필요 |

**3) 에러 코드**

| 코드 | 의미 | 해결책 |
|------|------|--------|
| `invalid_grant` | 코드/토큰 만료 | 재발급 |
| `USER_NOT_FOUND` | 사용자 없음 | 재로그인 |
| `INTERNAL_ERROR` | 서버 오류 | 재시도 |
| `BAD_REQUEST_RETRIEVE_CERT_RESULT_EXCEEDED_LIMIT` | 조회 횟수 초과 | DI 없는 API 사용 |

### 6.3 프로덕션 체크리스트

```markdown
## 배포 전 확인사항

### 환경 설정
- [ ] .env 파일 프로덕션 값으로 변경
- [ ] CORS origins 프로덕션 도메인 추가
- [ ] HTTPS 활성화

### 보안
- [ ] 복호화 키 환경 변수로 관리
- [ ] API 키 GitHub에 업로드 안 됨 확인
- [ ] HttpOnly 쿠키 사용
- [ ] Rate limiting 설정

### 토스 콘솔
- [ ] 프로덕션 도메인 Redirect URI 등록
- [ ] 약관 최신 버전 확인
- [ ] 콜백 URL 설정 (연결 해제)

### 테스트
- [ ] 로컬 환경 전체 플로우 테스트
- [ ] 샌드박스 환경 테스트
- [ ] 토큰 만료 시나리오 테스트
- [ ] 에러 핸들링 테스트

### 모니터링
- [ ] 로그 설정 (Winston, Sentry)
- [ ] 토큰 발급 실패율 모니터링
- [ ] API 응답 시간 모니터링
```

### 6.4 확장 가능성

**단기 확장:**
- 소셜 로그인 통합 (카카오, 네이버)
- 사용자 프로필 관리
- 약관 동의 이력 저장

**장기 확장:**
- 다중 토큰 관리 (여러 기기)
- 세션 관리 (Redis)
- 사용자 활동 로그
- 분석 대시보드

### 6.5 참고 자료

**공식 문서:**
- [토스 앱인토스 개발 가이드](https://developers-apps-in-toss.toss.im/)
- [토스 로그인 API](https://developers-apps-in-toss.toss.im/login/develop.html)
- [Toss App Bridge SDK](https://www.npmjs.com/package/@toss/app-bridge)

**코드 저장소:**
- [GitHub: toss-login-example](https://github.com/your-repo/toss-login-example)

**관련 기술:**
- [OAuth 2.0 RFC](https://datatracker.ietf.org/doc/html/rfc6749)
- [AES-GCM 암호화](https://en.wikipedia.org/wiki/Galois/Counter_Mode)

---

축하합니다! 토스 앱인토스 로그인 구현을 완료했습니다! 🎉

이제 2,500만 토스 사용자에게 안전하고 간편한 로그인 경험을 제공할 수 있습니다. 궁금한 점은 [토스 개발자 커뮤니티](https://developers-apps-in-toss.toss.im/)에 문의하세요!

