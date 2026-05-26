---
layout: post
title: "Django + Next.js 웹앱을 안드로이드 앱으로 만들어 플레이스토어에 배포하기 — 2026 실전 가이드"
date: 2026-05-26
categories: [android, django]
tags: [django, nextjs, android, pwa, twa, capacitor, google-play, mobile]
author: updaun
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-05-26-django-nextjs-android-app-deploy-guide.webp"
---

# Django + Next.js 웹앱을 안드로이드 앱으로 만들어 플레이스토어에 배포하기 — 2026 실전 가이드

Django로 백엔드 API를 만들고, Next.js로 프론트를 구성하는 조합은 이미 익숙합니다. 문제는 여기서 "이걸 앱으로도 내고 싶다"고 생각하는 순간 시작됩니다.

> Kotlin으로 처음부터 다시 짜야 하나? React Native로 포팅해야 하나?

**아닙니다.** 이미 돌아가는 웹앱이 있다면, 그걸 **거의 그대로** 안드로이드 앱으로 만드는 방법이 있습니다. 이 글은 Django + Next.js 스택을 쓰는 개발자가 **웹앱 코드 재작성 없이** 안드로이드 앱을 만들고, 구글 플레이스토어에 출시하기까지의 전체 과정을 다룹니다.

---

## 방법 선택 — TWA vs Capacitor vs 네이티브

먼저 세 가지 선택지를 비교합니다.

| | **TWA (Trusted Web Activity)** | **Capacitor** | **Kotlin 네이티브** |
|---|---|---|---|
| **원리** | Chrome이 웹사이트를 전체 화면으로 렌더링 | WebView 안에 정적 빌드를 번들링 | 처음부터 네이티브 코드 작성 |
| **코드 변경** | 거의 없음 | `output: 'export'` 설정 필요 | 전부 새로 작성 |
| **네이티브 API** | Service Worker 범위 내 (알림, 오프라인) | 카메라·GPS·파일시스템 등 플러그인 | 제한 없음 |
| **앱 크기** | 1~5MB | 5~20MB | 기능에 따라 다름 |
| **Django SSR** | 서버 렌더링 그대로 사용 가능 | 정적 export만 가능 (SSR 불가) | 해당 없음 |
| **업데이트** | 웹 배포 = 앱 업데이트 (스토어 심사 불필요) | 웹 코드 변경 시 `cap sync` + 스토어 재배포 | 스토어 재배포 |
| **추천 상황** | SSR·SEO 필요, 웹과 동일한 경험 | 카메라·블루투스 등 디바이스 API 필요 | 복잡한 네이티브 UX |

### 이 글의 구성

**Part A**에서는 대부분의 Django + Next.js 앱에 가장 현실적인 **TWA 방식**을 다루고, **Part B**에서는 디바이스 네이티브 기능이 필요할 때 쓰는 **Capacitor 방식**을 다룹니다.

---

# Part A: TWA — 웹앱을 거의 그대로 앱으로

TWA(Trusted Web Activity)는 **Chrome이 내 웹사이트를 전체 화면으로 보여주는 네이티브 앱 껍데기**입니다. WebView가 아니라 실제 Chrome 엔진이 돌기 때문에 Service Worker, 푸시 알림, 오프라인 캐싱이 모두 동작합니다.

핵심 장점: **Django SSR, API Route, middleware — 모든 서버 기능을 그대로 쓸 수 있습니다.** 앱은 단지 `https://your-domain.com`을 Chrome으로 여는 것이고, Django 서버가 평소처럼 응답합니다.

## A-1. 전제 조건

```text
✅ Django + Next.js 앱이 HTTPS로 배포되어 있음
✅ 도메인을 소유하고 있음 (예: app.example.com)
✅ Node.js 18+ 설치됨
✅ JDK 17+ 설치됨
```

## A-2. Next.js를 PWA로 만들기

TWA가 동작하려면 웹앱이 **PWA 설치 조건**을 충족해야 합니다:
1. HTTPS로 서빙
2. Web App Manifest (`manifest.json`)
3. Service Worker 등록

### A-2-1. Web App Manifest 생성

Next.js App Router에서는 `app/manifest.ts`를 만들면 자동으로 `/manifest.webmanifest`를 생성합니다.

```typescript
// app/manifest.ts
import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "내 서비스 이름",
    short_name: "내서비스",
    description: "Django + Next.js 기반 서비스",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#6b5b95",
    orientation: "portrait",
    icons: [
      {
        src: "/icons/icon-192x192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/icons/icon-512x512.png",
        sizes: "512x512",
        type: "image/png",
      },
    ],
  };
}
```

> **`display: "standalone"` 필수**: TWA가 이 값을 보고 전체 화면 모드를 활성화합니다.

### A-2-2. 아이콘 준비

`public/icons/` 폴더에 아이콘을 넣습니다:

| 파일 | 용도 |
|------|------|
| `icon-192x192.png` | manifest, Android 런처 |
| `icon-512x512.png` | manifest, 스플래시 |
| `icon-maskable-192x192.png` | 적응형 아이콘 (안전 영역 고려) |

> **maskable 아이콘**: Android가 원형·사각형 등 다양한 모양으로 잘라 쓰는 아이콘입니다. [maskable.app](https://maskable.app/editor)에서 미리보기 가능합니다.

### A-2-3. Service Worker 등록

가장 간단한 방법 — `public/sw.js`에 최소 Service Worker를 만듭니다:

```javascript
// public/sw.js
self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(clients.claim());
});

self.addEventListener("fetch", (event) => {
  event.respondWith(fetch(event.request));
});
```

루트 레이아웃에서 등록:

```typescript
// app/layout.tsx 내 <head> 또는 useEffect
"use client";
import { useEffect } from "react";

export function ServiceWorkerRegister() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js", { scope: "/" });
    }
  }, []);
  return null;
}
```

> **오프라인 캐싱이 필요하다면**: `Serwist`(`@serwist/next`) 또는 `next-pwa`를 쓰면 런타임 캐싱·프리캐싱을 자동 구성할 수 있습니다. 이 글에서는 TWA 등록 자체에 집중하므로 최소 구현만 다룹니다.

### A-2-4. PWA 검증

배포 후 Chrome DevTools → **Application → Manifest** 탭에서:

- ✅ "Installability" 항목이 모두 초록색
- ✅ Service Worker가 등록됨
- ✅ `display: standalone`

또는 **Lighthouse PWA 감사**를 돌려서 100점을 확인합니다.

## A-3. Bubblewrap으로 TWA 안드로이드 프로젝트 생성

Bubblewrap은 구글 크롬 팀이 만든 CLI로, PWA의 manifest를 읽어 **TWA 안드로이드 프로젝트를 자동 생성**합니다.

### A-3-1. 설치

```bash
npm install -g @aspect-build/aspect-cache 2>/dev/null
npm install -g @aspect-build/bazelrc 2>/dev/null
npm install -g @aspect-build/bazel 2>/dev/null
npm install -g @aspect-build/webpack 2>/dev/null

npm install -g @bubblewrap/cli
```

### A-3-2. 프로젝트 초기화

```bash
mkdir my-app-twa && cd my-app-twa

bubblewrap init --manifest=https://app.example.com/manifest.webmanifest
```

Bubblewrap이 manifest를 읽고 대화형으로 물어봅니다:

```text
? Domain: app.example.com
? URL path: /
? Application name: 내 서비스 이름
? Short name: 내서비스
? Application ID: com.example.myapp       ← 플레이스토어에서 영구히 사용되는 ID
? Starting version code: 1
? Starting version name: 1.0.0
? Display mode: standalone
? Status bar color: #6b5b95
? Splash screen color: #ffffff

? Do you want to create a signing key? (Y/n) Y
? Keystore password: ******
? Key alias: upload
? Key password: ******
```

> **Application ID는 변경 불가**: 한번 플레이스토어에 등록하면 바꿀 수 없습니다. `com.회사명.앱이름` 형식을 권장합니다.

> **Keystore 파일 백업 필수**: 분실하면 앱을 업데이트할 수 없습니다. 안전한 곳에 별도 보관하세요.

이 과정이 끝나면 `twa-manifest.json`과 Android 프로젝트 파일이 생성됩니다.

### A-3-3. 빌드

```bash
bubblewrap build
```

빌드 결과물:

| 파일 | 용도 |
|------|------|
| `app-release-signed.apk` | 테스트용 |
| `app-release-bundle.aab` | **플레이스토어 업로드용** |

## A-4. Digital Asset Links — 브라우저 바 제거의 핵심

TWA에서 가장 중요하면서 가장 많이 실수하는 부분입니다. **assetlinks.json** 파일이 올바르지 않으면 앱 상단에 Chrome 주소창이 표시됩니다.

### A-4-1. 구조

```json
// https://app.example.com/.well-known/assetlinks.json
[
  {
    "relation": ["delegate_permission/common.handle_all_urls"],
    "target": {
      "namespace": "android_app",
      "package_name": "com.example.myapp",
      "sha256_cert_fingerprints": [
        "AA:BB:CC:DD:..."
      ]
    }
  }
]
```

### A-4-2. 어떤 fingerprint를 넣어야 하나?

여기서 90%의 실수가 발생합니다. **세 가지 키**가 존재합니다:

| 키 | 생성 시점 | 용도 |
|----|-----------|------|
| Debug key | Android Studio 기본 | 로컬 테스트용 |
| **Upload key** | Bubblewrap이 생성한 keystore | AAB에 서명해서 업로드 |
| **App signing key** | Play Console이 생성 | 실제 사용자에게 배포되는 APK 서명 |

**assetlinks.json에 넣어야 할 것: App signing key의 SHA-256**

이 키는 **AAB를 처음 Play Console에 업로드한 후에만** 확인할 수 있습니다.

```text
Play Console → 앱 선택 → 설정 → 앱 무결성 → 앱 서명 키 인증서
→ SHA-256 인증서 핑거프린트 복사
```

### A-4-3. Next.js에서 assetlinks.json 서빙

**방법 1: `public` 폴더 (정적)**

```text
public/.well-known/assetlinks.json
```

> **주의**: Next.js의 middleware가 이 경로를 리다이렉트하면 안 됩니다. middleware에서 `/.well-known/`을 제외하세요.

```typescript
// middleware.ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  if (request.nextUrl.pathname.startsWith("/.well-known/")) {
    return NextResponse.next();
  }
  // 기존 middleware 로직...
}
```

**방법 2: Route Handler (동적)**

```typescript
// app/.well-known/assetlinks.json/route.ts
import { NextResponse } from "next/server";

export async function GET() {
  const assetLinks = [
    {
      relation: ["delegate_permission/common.handle_all_urls"],
      target: {
        namespace: "android_app",
        package_name: "com.example.myapp",
        sha256_cert_fingerprints: [
          process.env.PLAY_SIGNING_KEY_SHA256!,
        ],
      },
    },
  ];
  return NextResponse.json(assetLinks);
}
```

### A-4-4. 검증

```bash
# 1. 파일이 접근 가능한지
curl -v https://app.example.com/.well-known/assetlinks.json

# 2. Content-Type이 application/json인지
# 3. Google의 공식 검증 도구
```

[Google Digital Asset Links 검증 도구](https://developers.google.com/digital-asset-links/tools/generator)에서 도메인·패키지명·핑거프린트를 넣고 **"Test statement"** 통과를 확인합니다.

## A-5. Django 쪽에서 할 일

Django가 API 서버이고 Next.js가 프론트라면, Django 자체에 특별히 수정할 것은 없습니다. 하지만 다음을 확인하세요:

### A-5-1. CORS 설정 확인

TWA는 Chrome이므로 **일반 웹 요청과 동일**합니다. Django의 CORS 설정에 프론트 도메인이 이미 허용되어 있다면 추가 작업 불필요.

```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "https://app.example.com",
]
```

### A-5-2. 푸시 알림 (Django → 앱)

TWA에서는 **Web Push API**가 그대로 동작합니다. Django 서버에서 `pywebpush`로 푸시를 보내면 앱에서도 받을 수 있습니다.

```python
# Django 측 — Web Push 발송
from pywebpush import webpush

webpush(
    subscription_info=user_subscription,  # 프론트에서 받은 구독 정보
    data="새 알림이 있습니다",
    vapid_private_key="your-vapid-private-key",
    vapid_claims={"sub": "mailto:admin@example.com"},
)
```

```typescript
// Next.js 측 — 구독 등록
const registration = await navigator.serviceWorker.ready;
const subscription = await registration.pushManager.subscribe({
  userVisibleOnly: true,
  applicationServerKey: process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY,
});

// Django API로 구독 정보 전송
await fetch("/api/push/subscribe/", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(subscription),
});
```

### A-5-3. Django 인증 & 세션

TWA 안에서 로그인하면 Chrome의 쿠키에 세션이 저장됩니다. **JWT, 세션 쿠키, OAuth 모두 웹과 동일하게 동작**합니다. 별도 처리 불필요.

## A-6. 플레이스토어 배포

### A-6-1. 전체 흐름

```text
[1] Play Console 개발자 계정 생성 ($25)
      ↓
[2] 앱 생성 → 스토어 리스팅 작성
      ↓
[3] 내부 테스트 트랙에 AAB 업로드
      ↓
[4] App signing key SHA-256 확인 → assetlinks.json 업데이트 → 배포
      ↓
[5] 실기기에서 URL바 없이 동작하는지 확인
      ↓
[6] 클로즈드 테스트 (개인 계정: 12명 × 14일)
      ↓
[7] 프로덕션 신청 → 심사 (3~7 영업일)
      ↓
[8] 출시 🎉
```

### A-6-2. 스토어 리스팅 필수 항목

| 항목 | 규격 |
|------|------|
| 앱 이름 | 최대 30자 |
| 짧은 설명 | 최대 80자 |
| 상세 설명 | 최대 4,000자 |
| 앱 아이콘 | 512×512px, PNG 32비트 |
| 대표 그래픽 | 1024×500px, JPEG 또는 24비트 PNG |
| 스크린샷 | 최소 2장, JPEG/PNG |
| 개인정보처리방침 URL | 필수 |
| 콘텐츠 등급 | 설문 응답 후 자동 부여 |
| 데이터 안전 | 수집하는 데이터 유형 선언 |

### A-6-3. 개인 계정의 클로즈드 테스트 (14일 장벽)

2023년 11월 이후 생성된 **개인 계정**은 프로덕션 출시 전 필수:

- 테스터 **12명**이 **14일 연속** 옵트인 유지
- 카운트가 12 미만으로 떨어지면 **리셋**
- 15~18명으로 시작해서 버퍼 확보 권장
- **조직 계정**(사업자등록증 필요)은 이 단계 면제

### A-6-4. TWA 앱 업데이트가 쉬운 이유

TWA의 가장 큰 장점: **웹을 업데이트하면 앱도 즉시 반영됩니다.**

```text
Django 코드 수정 → 서버 배포
Next.js 코드 수정 → Vercel/서버 배포
  ↓
앱 사용자가 다음에 열면 → 최신 버전 자동 표시
  ↓
스토어 심사 불필요!
```

AAB 자체를 업데이트해야 하는 경우:
- 앱 아이콘 변경
- Application ID나 버전 코드 변경
- 스플래시 화면 색상 변경

```bash
# twa-manifest.json에서 versionCode, versionName 수정 후
bubblewrap build
# 새 AAB를 Play Console에 업로드
```

---

# Part B: Capacitor — 네이티브 API가 필요할 때

카메라, GPS, 블루투스, 파일 시스템, 네이티브 푸시(FCM) 등이 필요하다면 Capacitor가 답입니다. Capacitor는 웹앱을 **네이티브 WebView 안에 번들링**하고, 플러그인을 통해 디바이스 API를 호출할 수 있게 합니다.

## B-1. 제약 사항: 정적 export 필수

Capacitor는 웹 파일을 앱 안에 **패키징**하므로, Next.js의 SSR·API Route·middleware는 앱 내부에서 동작하지 않습니다.

**두 가지 접근법**:

| 방식 | 설명 | 장단점 |
|------|------|--------|
| **정적 export** | `output: 'export'`로 HTML/CSS/JS 생성, 앱에 번들링 | API는 Django에 fetch. SSR 불가 |
| **원격 URL 모드** | WebView가 배포된 웹 URL을 로딩 | SSR 가능하지만 오프라인 불가, TWA와 유사 |

이 글에서는 **정적 export + Django API** 조합을 다룹니다.

## B-2. Next.js 정적 export 설정

```typescript
// next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: {
    unoptimized: true, // next/image 최적화는 서버 필요 → 비활성
  },
};

export default nextConfig;
```

```bash
npm run build
# → out/ 폴더에 정적 파일 생성
```

> **SSR·API Route를 쓰고 있었다면**: 해당 로직을 **Django API 호출**로 전환해야 합니다. `getServerSideProps` → `useEffect + fetch`, `API Route` → Django endpoint.

## B-3. Capacitor 설치 & 초기화

```bash
# Capacitor CLI 및 코어 설치
npm install @capacitor/core @capacitor/cli

# 초기화
npx cap init "내서비스" "com.example.myapp" --web-dir out

# Android 플랫폼 추가
npm install @capacitor/android
npx cap add android
```

`capacitor.config.ts`가 생성됩니다:

```typescript
// capacitor.config.ts
import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.example.myapp",
  appName: "내서비스",
  webDir: "out",
  server: {
    // 개발 중 라이브 리로드 (프로덕션에서는 제거)
    // url: "http://192.168.0.10:3000",
    // cleartext: true,
  },
};

export default config;
```

## B-4. 빌드 & 실행

```bash
# 1. Next.js 빌드
npm run build

# 2. 웹 파일을 Android 프로젝트에 복사
npx cap sync

# 3. Android Studio에서 열기
npx cap open android
```

Android Studio에서 **Run** 버튼으로 에뮬레이터 또는 실기기에서 테스트합니다.

## B-5. Django API 연결

Capacitor 앱 안에서 Django API를 호출할 때 주의점:

### B-5-1. API Base URL 관리

```typescript
// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://api.example.com";

export async function apiFetch(path: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
```

### B-5-2. Django CORS 설정

Capacitor 앱의 Origin은 `capacitor://localhost` (Android) 또는 `ionic://localhost` (iOS)입니다:

```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "https://app.example.com",      # 웹
    "capacitor://localhost",          # Capacitor Android
    "ionic://localhost",              # Capacitor iOS
]

# 또는 개발 중에는
CORS_ALLOW_ALL_ORIGINS = True  # 프로덕션에서는 절대 비활성화
```

### B-5-3. 인증 토큰 관리

Capacitor에서는 쿠키 기반 세션보다 **JWT 토큰**이 더 안정적입니다:

```typescript
// lib/auth.ts
import { Preferences } from "@capacitor/preferences";

export async function saveToken(token: string) {
  await Preferences.set({ key: "auth_token", value: token });
}

export async function getToken(): Promise<string | null> {
  const { value } = await Preferences.get({ key: "auth_token" });
  return value;
}

export async function authFetch(path: string, options?: RequestInit) {
  const token = await getToken();
  return apiFetch(path, {
    ...options,
    headers: {
      ...options?.headers,
      Authorization: token ? `Bearer ${token}` : "",
    },
  });
}
```

```python
# Django 측 — djangorestframework-simplejwt 사용 예시
# urls.py
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("api/token/", TokenObtainPairView.as_view()),
    path("api/token/refresh/", TokenRefreshView.as_view()),
]
```

## B-6. 네이티브 기능 추가 예시

### B-6-1. 푸시 알림 (FCM + Django)

```bash
npm install @capacitor/push-notifications
npx cap sync
```

```typescript
// hooks/usePushNotifications.ts
import { PushNotifications } from "@capacitor/push-notifications";
import { authFetch } from "@/lib/auth";

export async function initPush() {
  const permission = await PushNotifications.requestPermissions();
  if (permission.receive !== "granted") return;

  await PushNotifications.register();

  PushNotifications.addListener("registration", async (token) => {
    // Django 서버에 FCM 토큰 등록
    await authFetch("/api/devices/register/", {
      method: "POST",
      body: JSON.stringify({
        registration_id: token.value,
        type: "android",
      }),
    });
  });

  PushNotifications.addListener("pushNotificationReceived", (notification) => {
    console.log("Push received:", notification);
  });

  PushNotifications.addListener(
    "pushNotificationActionPerformed",
    (notification) => {
      // 알림 탭 시 특정 페이지로 이동
      const url = notification.notification.data?.url;
      if (url) window.location.href = url;
    }
  );
}
```

```python
# Django 측 — fcm-django 사용
# models.py
from fcm_django.models import FCMDevice

# 푸시 발송
device = FCMDevice.objects.filter(user=target_user, active=True).first()
device.send_message(
    title="새 알림",
    body="주문이 접수되었습니다.",
    data={"url": "/orders/123"},
)
```

### B-6-2. 카메라

```bash
npm install @capacitor/camera
npx cap sync
```

```typescript
import { Camera, CameraResultType } from "@capacitor/camera";

async function takePhoto() {
  const photo = await Camera.getPhoto({
    resultType: CameraResultType.Base64,
    quality: 80,
  });

  // Django API로 이미지 업로드
  await authFetch("/api/photos/upload/", {
    method: "POST",
    body: JSON.stringify({ image: photo.base64String }),
  });
}
```

## B-7. 릴리즈 빌드 & 서명

```bash
# 1. Next.js 빌드
npm run build

# 2. Capacitor 동기화
npx cap sync

# 3. Android Studio에서 릴리즈 빌드
# Build → Generate Signed Bundle / APK → Android App Bundle → release
```

또는 CLI로:

```bash
cd android
./gradlew bundleRelease
# → android/app/build/outputs/bundle/release/app-release.aab
```

> `android/app/build.gradle`에서 `targetSdk = 35` 확인 필수 (2026년 요구사항).

---

# 공통: 어떤 방식이든 확인해야 할 것

## 체크리스트

```text
[ ] targetSdk = 35 (API 레벨 35 이상)
[ ] AAB 파일로 빌드 (APK 아님)
[ ] Keystore 파일 안전한 곳에 백업
[ ] 개인정보처리방침 URL 준비
[ ] 스크린샷 최소 2장 (1080×1920 이상 권장)
[ ] 대표 그래픽 1024×500px
[ ] 앱 아이콘 512×512px
[ ] 데이터 안전 섹션 작성
[ ] 콘텐츠 등급 설문 완료
[ ] (TWA) assetlinks.json에 Play signing key SHA-256
[ ] (TWA) Chrome DevTools에서 브라우저 바 안 뜨는지 확인
[ ] (Capacitor) CORS에 capacitor://localhost 허용
[ ] (개인 계정) 클로즈드 테스트 12명 × 14일
```

## 방식별 업데이트 비교

| 변경 사항 | TWA | Capacitor |
|-----------|-----|-----------|
| Django API 수정 | 서버 배포만 → 앱 자동 반영 | 서버 배포만 → 앱 자동 반영 |
| Next.js UI 수정 | 웹 배포만 → **앱 자동 반영** | `build` → `cap sync` → **스토어 재배포** |
| 네이티브 코드 수정 | 해당 없음 | 스토어 재배포 |
| 앱 아이콘/버전 변경 | `bubblewrap build` → 스토어 재배포 | Android Studio → 스토어 재배포 |

---

## 추천 의사결정 트리

```text
Django + Next.js 웹앱이 이미 있다
    │
    ├─ 카메라·GPS·블루투스 등 디바이스 API가 필요한가?
    │   ├─ Yes → Capacitor (Part B)
    │   └─ No
    │       ├─ SSR·서버 기능을 앱에서도 그대로 쓰고 싶은가?
    │       │   ├─ Yes → TWA (Part A) ← 대부분 여기
    │       │   └─ No → 정적 export 가능하면 Capacitor도 OK
    │       └─ 웹 배포 = 앱 업데이트가 중요한가?
    │           ├─ Yes → TWA (Part A)
    │           └─ No → 둘 다 OK
    │
    └─ 앱 전용 복잡한 UX가 필요한가?
        ├─ Yes → Kotlin 네이티브 (이 글 범위 밖)
        └─ No → TWA 또는 Capacitor
```

---

## 전체 타임라인 (현실적 추정)

| 단계 | TWA | Capacitor |
|------|-----|-----------|
| PWA/정적 export 설정 | 반나절 | 1~2일 (SSR → fetch 전환) |
| 앱 프로젝트 생성 | 1~2시간 | 반나절 |
| assetlinks / CORS 설정 | 반나절 (삽질 포함) | 1시간 |
| 네이티브 기능 추가 | 해당 없음 | 1~3일 |
| 스토어 리스팅 작성 | 1일 | 1일 |
| 클로즈드 테스트 (개인 계정) | **14일** | **14일** |
| 심사 | 3~7 영업일 | 3~7 영업일 |
| **합계** | **약 3~4주** | **약 4~5주** |

---

## 참고 자료

| 자료 | 링크 |
|------|------|
| Next.js PWA 공식 가이드 | [nextjs.org/docs/app/guides/progressive-web-apps](https://nextjs.org/docs/app/guides/progressive-web-apps) |
| Bubblewrap CLI | [github.com/GoogleChromeLabs/bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap) |
| PWABuilder | [pwabuilder.com](https://www.pwabuilder.com/) |
| Digital Asset Links 검증 | [developers.google.com/digital-asset-links/tools/generator](https://developers.google.com/digital-asset-links/tools/generator) |
| Capacitor 공식 문서 | [capacitorjs.com/docs](https://capacitorjs.com/docs) |
| Capacitor + Next.js 가이드 | [capgo.app/blog/nextjs-mobile-app-capacitor-from-scratch](https://capgo.app/blog/nextjs-mobile-app-capacitor-from-scratch/) |
| fcm-django | [github.com/xtrinch/fcm-django](https://github.com/xtrinch/fcm-django) |
| Serwist (Service Worker) | [serwist.pages.dev](https://serwist.pages.dev/) |
| 클로즈드 테스트 요구사항 | [support.google.com/googleplay/android-developer/answer/14151465](https://support.google.com/googleplay/android-developer/answer/14151465) |
| 이 블로그: 안드로이드 앱 입문 가이드 | [이전 포스트 참고](/android/2026/05/25/android-app-google-play-store-beginner-guide/) |

---

## 정리

Django + Next.js 웹앱을 안드로이드 앱으로 만드는 가장 현실적인 경로를 정리하면:

**대부분의 경우 TWA면 충분합니다.** 이미 잘 돌아가는 웹앱을 Bubblewrap으로 감싸면 3~5MB짜리 앱이 나오고, Django의 SSR·인증·API가 모두 그대로 동작합니다. 웹을 업데이트하면 앱도 즉시 반영되니 운영 부담도 적습니다. 핵심은 **assetlinks.json의 SHA-256 핑거프린트를 Play signing key 것으로 넣는 것**입니다.

**카메라·GPS 같은 디바이스 API가 필요하면 Capacitor**를 쓰되, Next.js를 정적 export로 전환하고 SSR 로직을 Django API 호출로 바꿔야 합니다.

어떤 방식이든 **스토어 배포 과정**(계정 등록, 리스팅, 클로즈드 테스트, 심사)은 동일합니다. 가장 오래 걸리는 건 코딩이 아니라 **14일 클로즈드 테스트 대기**입니다.
