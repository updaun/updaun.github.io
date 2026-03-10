---
layout: post
title: "Django-Ninja로 Instagram API 연동하기: 콘텐츠 데이터 수집 자동화 가이드"
date: 2026-03-10
categories: [Django, Python, API-Integration]
tags: [django-ninja, instagram-api, meta-api, social-media, data-collection, python, backend, api-development]
image: "/assets/img/posts/2026-03-10-django-ninja-instagram-api-integration-guide.webp"
description: "Django-Ninja에서 Instagram Graph API를 활용하여 게시물 데이터(조회수, 좋아요, 댓글)를 수집하고 DB에 저장하는 실전 가이드입니다."
excerpt: "Instagram API를 Django-Ninja와 연동하여 콘텐츠 성과 데이터를 자동으로 수집하고 분석하는 방법을 단계별로 알아봅니다. Client ID부터 Access Token 발급, API 호출, DB 저장까지 완벽 구현합니다."
---

## 소개: 왜 Instagram 데이터를 수집해야 할까?

소셜 미디어 마케팅에서 **데이터 기반 의사결정**은 필수입니다. Instagram은 2026년 현재 전 세계 20억 명 이상의 월간 활성 사용자를 보유한 핵심 마케팅 채널이며, 특히 Z세대와 밀레니얼 세대에게 강력한 영향력을 발휘합니다. 브랜드나 인플루언서 입장에서 Instagram 콘텐츠의 성과를 체계적으로 추적하고 분석하는 것은 마케팅 ROI를 극대화하는 핵심 전략입니다.

Instagram Graph API는 Meta(구 Facebook)에서 제공하는 공식 API로, 비즈니스 계정이나 크리에이터 계정의 **미디어 정보, 인사이트(조회수, 좋아요, 댓글 수), 팔로워 데이터**를 프로그래밍 방식으로 가져올 수 있습니다. 이를 통해 수동으로 데이터를 기록하던 비효율적인 작업을 자동화하고, 실시간 대시보드를 구축하거나 AI 기반 콘텐츠 추천 시스템을 만들 수 있습니다.

이 가이드에서는 **Django-Ninja**라는 최신 Python 웹 프레임워크와 Instagram API를 연동하여, 계정의 게시물 데이터를 자동으로 수집하고 Django ORM으로 데이터베이스에 저장하는 전체 프로세스를 다룹니다. Meta 개발자 계정 생성부터 Access Token 발급, API 엔드포인트 설계, 에러 핸들링까지 **실전에서 바로 사용할 수 있는 코드와 함께 단계별로 설명**합니다.

## 1부: Instagram API 준비하기

### 1.1 Django-Ninja란?

**Django-Ninja**는 FastAPI의 철학을 Django에 적용한 모던한 API 프레임워크입니다. Django REST Framework(DRF)보다 **간결하고 빠르며**, Pydantic을 활용한 타입 기반 자동 검증과 자동 문서화(Swagger/OpenAPI)를 제공합니다.

**주요 장점:**
- **빠른 개발 속도**: DRF 대비 코드량이 약 40% 감소
- **성능**: FastAPI와 유사한 수준의 고속 처리 (ASGI 기반)
- **타입 안정성**: Pydantic 스키마로 런타임 에러 사전 방지
- **자동 문서화**: `/api/docs`에서 Swagger UI 자동 생성

**설치 방법:**
```bash
pip install django-ninja
pip install httpx  # Instagram API 호출용
pip install python-decouple  # 환경 변수 관리용
```

**기본 설정 (settings.py):**
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ninja',  # Django-Ninja 추가
    'instagram_collector',  # 우리가 만들 앱
]
```

Django-Ninja는 Django의 견고한 ORM과 Admin 기능을 그대로 활용하면서도, 최신 비동기 API 개발 패턴을 적용할 수 있어 Instagram API 같은 외부 서비스 연동에 최적화되어 있습니다.

### 1.2 Instagram Graph API 이해하기

Instagram Graph API는 **Instagram Business 계정**이나 **Creator 계정**의 데이터에 접근할 수 있는 공식 API입니다. 개인 계정은 지원하지 않으므로, 먼저 계정을 비즈니스 계정으로 전환해야 합니다.

**수집 가능한 주요 데이터:**

| 데이터 유형 | API 필드 | 설명 |
|-----------|---------|------|
| 미디어 ID | `id` | 게시물 고유 식별자 |
| 미디어 타입 | `media_type` | IMAGE, VIDEO, CAROUSEL_ALBUM |
| 캡션 | `caption` | 게시물 텍스트 내용 |
| 타임스탬프 | `timestamp` | 게시 일시 (ISO 8601) |
| 퍼머링크 | `permalink` | 원본 게시물 URL |
| 좋아요 수* | `like_count` | 좋아요 개수 (인사이트 권한 필요) |
| 댓글 수* | `comments_count` | 댓글 개수 |
| 저장 수* | `saved` | 북마크 개수 |
| 도달 수* | `reach` | 고유 사용자 수 |
| 노출 수* | `impressions` | 총 조회 수 |

*표시된 항목은 `instagram_business_basic` 또는 `instagram_manage_insights` 권한이 필요합니다.

**API 버전:**
- 현재 최신: **v19.0** (2026년 3월 기준)
- 엔드포인트: `https://graph.facebook.com/v19.0/`
- 권장사항: 항상 특정 버전을 명시하여 호출 (안정성)

**Rate Limit:**
- 표준: 시간당 200 calls per user
- 비즈니스 앱: 시간당 4,800 calls
- 에러 코드: `4` (API 제한 초과 시)

Instagram API는 개인정보 보호를 위해 **해시태그 검색이나 타인의 콘텐츠 조회는 제한**하며, 오직 **자신이 인증한 비즈니스 계정의 데이터만** 가져올 수 있습니다.

### 1.3 Meta 개발자 계정 및 앱 생성

Instagram API를 사용하려면 Meta for Developers에서 앱을 생성하고 인증해야 합니다.

**Step 1: Meta 개발자 계정 생성**
1. [developers.facebook.com](https://developers.facebook.com)에 접속
2. 우측 상단 "내 앱" → "앱 만들기" 클릭
3. 앱 유형 선택: **"소비자"** 또는 **"비즈니스"** (개인 프로젝트는 소비자)
4. 앱 이름 입력: 예) "InstagramCollector"
5. 앱 연락처 이메일 입력

**Step 2: Instagram Graph API 추가**
1. 대시보드에서 "제품 추가" 클릭
2. **"Instagram"** 찾기 → "설정" 클릭
3. Instagram Graph API가 제품 목록에 추가됨

**Step 3: 앱 설정 구성**
1. 좌측 메뉴 "설정" → "기본 설정" 이동
2. **앱 ID (Client ID)** 복사 - Django 설정에 사용
3. **앱 시크릿 코드 (Client Secret)** 복사 - 보안 저장 필요
4. 개인정보처리방침 URL 입력 (필수는 아니지만 권장)
5. 앱 도메인 입력: 예) `localhost` (개발용), `yourdomain.com` (운영용)

**Step 4: Instagram 테스터 추가 (중요!)**
1. 좌측 메뉴 "역할" → "역할" 이동
2. "Instagram 테스터 추가" 클릭
3. 본인의 Instagram 비즈니스 계정 사용자명 입력
4. Instagram 앱에서 "설정" → "앱 및 웹사이트" → "테스터 초대" 수락

**Step 5: 앱 모드 설정**
- 개발 모드: 테스터 계정만 접근 (초기 개발 및 테스트용)
- 라이브 모드: 모든 계정 접근 가능 (앱 검수 통과 후)

앱 검수(App Review)는 본인 계정만 사용할 경우 필요하지 않으며, 다른 사용자를 위한 서비스를 만들 때만 필요합니다. 이 가이드에서는 **개발 모드에서 자신의 계정 데이터만 수집**하는 시나리오를 다룹니다.

## 2부: Access Token 발급 및 Django 설정

### 2.1 Access Token 발급 방법

Instagram API 호출을 위해서는 **Access Token**이 필수입니다. Meta는 세 가지 토큰 유형을 제공합니다:

**토큰 유형 비교:**

| 토큰 유형 | 유효 기간 | 갱신 | 권장 용도 |
|----------|----------|------|----------|
| **Short-lived Token** | 1시간 | 불가 | 초기 인증 |
| **Long-lived Token** | 60일 | 자동 갱신 가능 | 개발/테스트 |
| **Page Token** | 무제한 | 페이지 연결 시 | 운영 환경 |

**방법 1: Graph API Explorer 사용 (빠른 테스트용)**

1. [Graph API Explorer](https://developers.facebook.com/tools/explorer/)에 접속
2. 상단 Meta 앱 드롭다운에서 생성한 앱 선택
3. 사용자 또는 페이지: "Instagram 비즈니스 계정" 선택
4. 권한 추가:
   - `instagram_basic`
   - `instagram_manage_insights`
   - `pages_show_list`
   - `pages_read_engagement`
5. "Generate Access Token" 클릭
6. Instagram 로그인 및 권한 승인
7. 생성된 토큰 복사 (이것은 1시간짜리 Short-lived Token)

**방법 2: Long-lived Token으로 변환 (권장)**

Short-lived Token을 받았다면, 60일 유효한 Long-lived Token으로 변환해야 합니다.

```bash
curl -X GET "https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id={APP_ID}&client_secret={APP_SECRET}&fb_exchange_token={SHORT_LIVED_TOKEN}"
```

**Python 코드로 변환:**
```python
import httpx

def exchange_token(short_token, app_id, app_secret):
    url = "https://graph.facebook.com/v19.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_token,
    }
    
    response = httpx.get(url, params=params)
    data = response.json()
    
    if "access_token" in data:
        print(f"Long-lived Token: {data['access_token']}")
        print(f"Expires in: {data['expires_in']} seconds (~60 days)")
        return data['access_token']
    else:
        print(f"Error: {data}")
        return None

# 사용 예시
long_token = exchange_token(
    short_token="YOUR_SHORT_LIVED_TOKEN",
    app_id="YOUR_APP_ID",
    app_secret="YOUR_APP_SECRET"
)
```

**방법 3: Instagram Business Account ID 확인**

Access Token을 발급받았다면, API 호출에 필요한 Instagram Business Account ID를 확인해야 합니다.

```bash
# 연결된 Facebook 페이지의 Instagram 계정 조회
curl -X GET "https://graph.facebook.com/v19.0/me/accounts?fields=instagram_business_account&access_token={YOUR_ACCESS_TOKEN}"
```

응답 예시:
```json
{
  "data": [
    {
      "instagram_business_account": {
        "id": "17841405793187218"
      },
      "id": "10823746"
    }
  ]
}
```

`instagram_business_account.id` 값이 바로 우리가 사용할 **Instagram Business Account ID**입니다. 이 ID를 Django 설정에 저장합니다.

### 2.2 Django 프로젝트 구조 설계

효율적인 Instagram 데이터 수집을 위한 Django 앱 구조를 설계하겠습니다.

**프로젝트 구조:**
```
myproject/
├── manage.py
├── myproject/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── instagram_collector/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py          # 데이터베이스 모델
│   ├── schemas.py         # Pydantic 스키마
│   ├── services.py        # 비즈니스 로직 (API 호출)
│   ├── api.py             # Django-Ninja 엔드포인트
│   └── migrations/
└── .env                   # 환경 변수 (민감 정보)
```

**앱 생성:**
```bash
python manage.py startapp instagram_collector
```

**.env 파일 생성 (보안 중요!):**
```env
# Instagram API Credentials
INSTAGRAM_APP_ID=your_app_id_here
INSTAGRAM_APP_SECRET=your_app_secret_here
INSTAGRAM_ACCESS_TOKEN=your_long_lived_token_here
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_instagram_account_id_here

# API Configuration
INSTAGRAM_API_VERSION=v19.0
```

**settings.py 수정:**
```python
from decouple import config

# Instagram API 설정
INSTAGRAM_CONFIG = {
    'APP_ID': config('INSTAGRAM_APP_ID'),
    'APP_SECRET': config('INSTAGRAM_APP_SECRET'),
    'ACCESS_TOKEN': config('INSTAGRAM_ACCESS_TOKEN'),
    'BUSINESS_ACCOUNT_ID': config('INSTAGRAM_BUSINESS_ACCOUNT_ID'),
    'API_VERSION': config('INSTAGRAM_API_VERSION', default='v19.0'),
    'BASE_URL': 'https://graph.facebook.com',
}

# Installed Apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ninja',
    'instagram_collector',
]
```

**urls.py 설정 (프로젝트 루트):**
```python
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from instagram_collector.api import router as instagram_router

# Ninja API 인스턴스 생성
api = NinjaAPI(
    title="Instagram Collector API",
    version="1.0.0",
    description="Instagram 콘텐츠 데이터 수집 API"
)

# Instagram 라우터 등록
api.add_router("/instagram/", instagram_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),  # /api/docs 에서 Swagger 확인 가능
]
```

이제 Django 프로젝트의 기본 설정이 완료되었습니다. 다음 단계에서는 데이터베이스 모델과 API 호출 로직을 구현하겠습니다.

### 2.3 데이터베이스 모델 설계

Instagram 미디어 데이터를 저장할 Django 모델을 설계합니다.

**instagram_collector/models.py:**
```python
from django.db import models
from django.utils import timezone


class InstagramMedia(models.Model):
    """Instagram 미디어(게시물) 정보"""
    
    MEDIA_TYPE_CHOICES = [
        ('IMAGE', '이미지'),
        ('VIDEO', '비디오'),
        ('CAROUSEL_ALBUM', '다중 이미지/비디오'),
    ]
    
    # 기본 정보
    instagram_id = models.CharField(max_length=255, unique=True, 
                                     verbose_name="Instagram 미디어 ID")
    media_type = models.CharField(max_length=50, choices=MEDIA_TYPE_CHOICES,
                                   verbose_name="미디어 타입")
    caption = models.TextField(blank=True, null=True, 
                                verbose_name="게시물 텍스트")
    permalink = models.URLField(max_length=500, verbose_name="게시물 URL")
    
    # 미디어 파일
    media_url = models.URLField(max_length=500, blank=True, null=True,
                                 verbose_name="미디어 파일 URL")
    thumbnail_url = models.URLField(max_length=500, blank=True, null=True,
                                     verbose_name="썸네일 URL (비디오용)")
    
    # 타임스탬프
    timestamp = models.DateTimeField(verbose_name="게시 일시")
    created_at = models.DateTimeField(auto_now_add=True, 
                                       verbose_name="수집 일시")
    updated_at = models.DateTimeField(auto_now=True, 
                                       verbose_name="최종 업데이트")
    
    class Meta:
        db_table = 'instagram_media'
        verbose_name = 'Instagram 미디어'
        verbose_name_plural = 'Instagram 미디어 목록'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['instagram_id']),
        ]
    
    def __str__(self):
        return f"{self.media_type} - {self.instagram_id}"


class InstagramInsight(models.Model):
    """Instagram 미디어 인사이트(성과 데이터)"""
    
    media = models.ForeignKey(
        InstagramMedia, 
        on_delete=models.CASCADE,
        related_name='insights',
        verbose_name="미디어"
    )
    
    # 인게이지먼트 지표
    like_count = models.IntegerField(default=0, verbose_name="좋아요 수")
    comments_count = models.IntegerField(default=0, verbose_name="댓글 수")
    saved_count = models.IntegerField(default=0, verbose_name="저장 수")
    
    # 도달 및 노출
    reach = models.IntegerField(default=0, verbose_name="도달 수")
    impressions = models.IntegerField(default=0, verbose_name="노출 수")
    
    # 비디오 전용 지표
    video_views = models.IntegerField(default=0, blank=True, null=True,
                                       verbose_name="비디오 조회 수")
    
    # 수집 시점
    collected_at = models.DateTimeField(auto_now_add=True,
                                         verbose_name="데이터 수집 시각")
    
    class Meta:
        db_table = 'instagram_insight'
        verbose_name = 'Instagram 인사이트'
        verbose_name_plural = 'Instagram 인사이트 목록'
        ordering = ['-collected_at']
        indexes = [
            models.Index(fields=['media', '-collected_at']),
        ]
    
    def __str__(self):
        return f"{self.media.instagram_id} - {self.collected_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def engagement_rate(self):
        """인게이지먼트율 계산 (도달 수 기준)"""
        if self.reach == 0:
            return 0
        engagement = self.like_count + self.comments_count + self.saved_count
        return round((engagement / self.reach) * 100, 2)


class InstagramAccount(models.Model):
    """Instagram 비즈니스 계정 정보"""
    
    instagram_business_account_id = models.CharField(
        max_length=255, 
        unique=True,
        verbose_name="Instagram 비즈니스 계정 ID"
    )
    username = models.CharField(max_length=255, verbose_name="사용자명")
    name = models.CharField(max_length=255, blank=True, verbose_name="계정 이름")
    biography = models.TextField(blank=True, verbose_name="자기소개")
    profile_picture_url = models.URLField(max_length=500, blank=True,
                                           verbose_name="프로필 사진 URL")
    
    # 통계
    followers_count = models.IntegerField(default=0, verbose_name="팔로워 수")
    follows_count = models.IntegerField(default=0, verbose_name="팔로잉 수")
    media_count = models.IntegerField(default=0, verbose_name="게시물 수")
    
    # 메타 정보
    last_synced_at = models.DateTimeField(null=True, blank=True,
                                            verbose_name="마지막 동기화")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'instagram_account'
        verbose_name = 'Instagram 계정'
        verbose_name_plural = 'Instagram 계정 목록'
    
    def __str__(self):
        return f"@{self.username}"
```

**마이그레이션 실행:**
```bash
python manage.py makemigrations instagram_collector
python manage.py migrate
```

이제 Instagram 데이터를 저장할 데이터베이스 테이블이 생성되었습니다. 다음 단계에서는 Instagram API를 호출하는 서비스 로직을 구현하겠습니다.

## 3부: Instagram API 호출 구현

### 3.1 서비스 레이어 설계

Instagram API 호출 로직을 책임과 관심사에 따라 분리하여 재사용 가능한 서비스 클래스로 구현합니다.

**instagram_collector/services.py:**
```python
import httpx
from typing import List, Dict, Optional
from datetime import datetime
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class InstagramAPIClient:
    """Instagram Graph API 클라이언트"""
    
    def __init__(self):
        self.config = settings.INSTAGRAM_CONFIG
        self.base_url = f"{self.config['BASE_URL']}/{self.config['API_VERSION']}"
        self.access_token = self.config['ACCESS_TOKEN']
        self.business_account_id = self.config['BUSINESS_ACCOUNT_ID']
        self.client = httpx.Client(timeout=30.0)
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """API 요청 헬퍼 메서드"""
        url = f"{self.base_url}/{endpoint}"
        
        default_params = {"access_token": self.access_token}
        if params:
            default_params.update(params)
        
        try:
            response = self.client.get(url, params=default_params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            raise
    
    def get_account_info(self) -> Dict:
        """계정 정보 조회"""
        fields = [
            "id",
            "username",
            "name",
            "biography",
            "profile_picture_url",
            "followers_count",
            "follows_count",
            "media_count"
        ]
        
        endpoint = f"{self.business_account_id}"
        params = {"fields": ",".join(fields)}
        
        return self._make_request(endpoint, params)
    
    def get_media_list(self, limit: int = 25) -> List[Dict]:
        """미디어 목록 조회 (최신순)"""
        fields = [
            "id",
            "media_type",
            "media_url",
            "thumbnail_url",
            "permalink",
            "caption",
            "timestamp",
            "username"
        ]
        
        endpoint = f"{self.business_account_id}/media"
        params = {
            "fields": ",".join(fields),
            "limit": limit
        }
        
        data = self._make_request(endpoint, params)
        return data.get('data', [])
    
    def get_media_insights(self, media_id: str) -> Dict:
        """특정 미디어의 인사이트 조회"""
        endpoint = f"{media_id}/insights"
        
        # 미디어 타입에 따라 사용 가능한 메트릭이 다름
        metrics = [
            "engagement",
            "impressions",
            "reach",
            "saved"
        ]
        
        params = {"metric": ",".join(metrics)}
        
        try:
            data = self._make_request(endpoint, params)
            
            # 응답 데이터를 딕셔너리로 변환
            insights = {}
            for item in data.get('data', []):
                insights[item['name']] = item['values'][0]['value']
            
            return insights
        except Exception as e:
            logger.warning(f"Failed to get insights for media {media_id}: {str(e)}")
            return {}
    
    def get_media_detail(self, media_id: str) -> Dict:
        """특정 미디어의 상세 정보 조회 (좋아요, 댓글 수 포함)"""
        fields = [
            "id",
            "media_type",
            "media_url",
            "thumbnail_url",
            "permalink",
            "caption",
            "timestamp",
            "like_count",
            "comments_count"
        ]
        
        endpoint = f"{media_id}"
        params = {"fields": ",".join(fields)}
        
        return self._make_request(endpoint, params)
    
    def close(self):
        """HTTP 클라이언트 종료"""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class InstagramDataCollector:
    """Instagram 데이터 수집 및 저장 서비스"""
    
    def __init__(self):
        self.api_client = InstagramAPIClient()
    
    def sync_account_info(self):
        """계정 정보 동기화"""
        from .models import InstagramAccount
        
        try:
            account_data = self.api_client.get_account_info()
            
            account, created = InstagramAccount.objects.update_or_create(
                instagram_business_account_id=account_data['id'],
                defaults={
                    'username': account_data.get('username', ''),
                    'name': account_data.get('name', ''),
                    'biography': account_data.get('biography', ''),
                    'profile_picture_url': account_data.get('profile_picture_url', ''),
                    'followers_count': account_data.get('followers_count', 0),
                    'follows_count': account_data.get('follows_count', 0),
                    'media_count': account_data.get('media_count', 0),
                    'last_synced_at': timezone.now(),
                }
            )
            
            action = "생성" if created else "업데이트"
            logger.info(f"Instagram 계정 정보 {action}: @{account.username}")
            
            return account
        except Exception as e:
            logger.error(f"계정 정보 동기화 실패: {str(e)}")
            raise
    
    def sync_media_list(self, limit: int = 25):
        """미디어 목록 동기화"""
        from .models import InstagramMedia
        
        try:
            media_list = self.api_client.get_media_list(limit=limit)
            
            synced_count = 0
            for media_data in media_list:
                # 타임스탬프 파싱
                timestamp = datetime.fromisoformat(
                    media_data['timestamp'].replace('Z', '+00:00')
                )
                
                media, created = InstagramMedia.objects.update_or_create(
                    instagram_id=media_data['id'],
                    defaults={
                        'media_type': media_data.get('media_type', 'IMAGE'),
                        'caption': media_data.get('caption', ''),
                        'permalink': media_data.get('permalink', ''),
                        'media_url': media_data.get('media_url', ''),
                        'thumbnail_url': media_data.get('thumbnail_url', ''),
                        'timestamp': timestamp,
                    }
                )
                
                synced_count += 1
                action = "추가" if created else "업데이트"
                logger.info(f"미디어 {action}: {media.instagram_id}")
            
            logger.info(f"총 {synced_count}개 미디어 동기화 완료")
            return synced_count
        except Exception as e:
            logger.error(f"미디어 목록 동기화 실패: {str(e)}")
            raise
    
    def sync_media_insights(self, media_instagram_id: str):
        """특정 미디어의 인사이트 수집"""
        from .models import InstagramMedia, InstagramInsight
        
        try:
            # 미디어 객체 조회
            media = InstagramMedia.objects.get(instagram_id=media_instagram_id)
            
            # 상세 정보 (좋아요, 댓글 수) 조회
            media_detail = self.api_client.get_media_detail(media_instagram_id)
            
            # 인사이트 (도달, 노출, 저장) 조회
            insights_data = self.api_client.get_media_insights(media_instagram_id)
            
            # 인사이트 저장
            insight = InstagramInsight.objects.create(
                media=media,
                like_count=media_detail.get('like_count', 0),
                comments_count=media_detail.get('comments_count', 0),
                saved_count=insights_data.get('saved', 0),
                reach=insights_data.get('reach', 0),
                impressions=insights_data.get('impressions', 0),
            )
            
            logger.info(
                f"인사이트 수집 완료: {media.instagram_id} - "
                f"좋아요 {insight.like_count}, 댓글 {insight.comments_count}, "
                f"도달 {insight.reach}, 노출 {insight.impressions}"
            )
            
            return insight
        except InstagramMedia.DoesNotExist:
            logger.error(f"미디어를 찾을 수 없음: {media_instagram_id}")
            raise
        except Exception as e:
            logger.error(f"인사이트 수집 실패: {str(e)}")
            raise
    
    def sync_all_media_insights(self):
        """모든 미디어의 인사이트 일괄 수집"""
        from .models import InstagramMedia
        
        media_list = InstagramMedia.objects.all()
        success_count = 0
        fail_count = 0
        
        for media in media_list:
            try:
                self.sync_media_insights(media.instagram_id)
                success_count += 1
            except Exception as e:
                logger.error(f"미디어 {media.instagram_id} 인사이트 수집 실패: {str(e)}")
                fail_count += 1
        
        logger.info(
            f"인사이트 일괄 수집 완료 - 성공: {success_count}, 실패: {fail_count}"
        )
        
        return {"success": success_count, "fail": fail_count}
    
    def close(self):
        """리소스 정리"""
        self.api_client.close()
```

이 서비스 클래스는 두 가지 주요 역할을 수행합니다:

1. **InstagramAPIClient**: Instagram Graph API와의 통신을 담당
2. **InstagramDataCollector**: API 데이터를 Django 모델로 변환하여 저장

핵심 기능:
- `sync_account_info()`: 계정 정보 동기화
- `sync_media_list()`: 최근 미디어 목록 동기화
- `sync_media_insights()`: 특정 미디어의 성과 데이터 수집
- `sync_all_media_insights()`: 모든 미디어의 인사이트 일괄 수집

### 3.2 Pydantic 스키마 정의

Django-Ninja는 Pydantic 스키마를 사용하여 요청/응답 데이터를 검증하고 자동 문서화합니다.

**instagram_collector/schemas.py:**
```python
from ninja import Schema
from datetime import datetime
from typing import Optional, List


class MediaSchema(Schema):
    """미디어 기본 정보 스키마"""
    id: int
    instagram_id: str
    media_type: str
    caption: Optional[str] = None
    permalink: str
    media_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    timestamp: datetime
    created_at: datetime
    updated_at: datetime


class InsightSchema(Schema):
    """인사이트 정보 스키마"""
    id: int
    media_id: int
    like_count: int
    comments_count: int
    saved_count: int
    reach: int
    impressions: int
    video_views: Optional[int] = None
    collected_at: datetime
    engagement_rate: float


class MediaDetailSchema(Schema):
    """미디어 상세 정보 (인사이트 포함)"""
    media: MediaSchema
    latest_insight: Optional[InsightSchema] = None


class AccountSchema(Schema):
    """계정 정보 스키마"""
    id: int
    instagram_business_account_id: str
    username: str
    name: str
    biography: str
    profile_picture_url: str
    followers_count: int
    follows_count: int
    media_count: int
    last_synced_at: Optional[datetime] = None


class SyncResponseSchema(Schema):
    """동기화 응답 스키마"""
    success: bool
    message: str
    count: Optional[int] = None


class ErrorSchema(Schema):
    """에러 응답 스키마"""
    error: str
    detail: Optional[str] = None
```

### 3.3 Django-Ninja API 엔드포인트 구현

이제 실제로 HTTP 요청을 처리할 API 엔드포인트를 작성합니다.

**instagram_collector/api.py:**
```python
from ninja import Router
from typing import List
from django.shortcuts import get_object_or_404
from .models import InstagramMedia, InstagramAccount, InstagramInsight
from .schemas import (
    MediaSchema,
    MediaDetailSchema,
    AccountSchema,
    InsightSchema,
    SyncResponseSchema,
    ErrorSchema
)
from .services import InstagramDataCollector
import logging

logger = logging.getLogger(__name__)
router = Router(tags=["Instagram"])


@router.get("/account", response=AccountSchema, summary="계정 정보 조회")
def get_account_info(request):
    """
    Instagram 비즈니스 계정 정보를 조회합니다.
    DB에 정보가 없으면 None을 반환합니다.
    """
    account = InstagramAccount.objects.first()
    if not account:
        return None
    return account


@router.post("/account/sync", response=SyncResponseSchema, summary="계정 정보 동기화")
def sync_account(request):
    """
    Instagram API를 호출하여 계정 정보를 동기화합니다.
    팔로워 수, 게시물 수 등이 업데이트됩니다.
    """
    try:
        collector = InstagramDataCollector()
        account = collector.sync_account_info()
        collector.close()
        
        return {
            "success": True,
            "message": f"계정 @{account.username} 정보가 동기화되었습니다."
        }
    except Exception as e:
        logger.error(f"계정 동기화 실패: {str(e)}")
        return {
            "success": False,
            "message": f"동기화 실패: {str(e)}"
        }


@router.get("/media", response=List[MediaSchema], summary="미디어 목록 조회")
def list_media(request, limit: int = 25):
    """
    저장된 Instagram 미디어 목록을 조회합니다.
    
    - **limit**: 조회할 개수 (기본값: 25)
    """
    media_list = InstagramMedia.objects.all()[:limit]
    return list(media_list)


@router.post("/media/sync", response=SyncResponseSchema, summary="미디어 목록 동기화")
def sync_media(request, limit: int = 25):
    """
    Instagram API를 호출하여 최근 미디어 목록을 동기화합니다.
    
    - **limit**: 동기화할 미디어 개수 (기본값: 25, 최대: 100)
    """
    try:
        collector = InstagramDataCollector()
        count = collector.sync_media_list(limit=min(limit, 100))
        collector.close()
        
        return {
            "success": True,
            "message": f"{count}개의 미디어가 동기화되었습니다.",
            "count": count
        }
    except Exception as e:
        logger.error(f"미디어 동기화 실패: {str(e)}")
        return {
            "success": False,
            "message": f"동기화 실패: {str(e)}"
        }


@router.get("/media/{media_id}", response=MediaDetailSchema, summary="미디어 상세 조회")
def get_media_detail(request, media_id: int):
    """
    특정 미디어의 상세 정보와 최신 인사이트를 조회합니다.
    
    - **media_id**: 미디어 DB ID (instagram_id 아님)
    """
    media = get_object_or_404(InstagramMedia, id=media_id)
    latest_insight = media.insights.first()  # 최신 인사이트
    
    return {
        "media": media,
        "latest_insight": latest_insight
    }


@router.post("/media/{media_id}/insights/sync", 
             response=SyncResponseSchema, 
             summary="미디어 인사이트 수집")
def sync_media_insights(request, media_id: int):
    """
    특정 미디어의 인사이트(조회수, 좋아요, 댓글 등)를 수집합니다.
    
    - **media_id**: 미디어 DB ID
    """
    try:
        media = get_object_or_404(InstagramMedia, id=media_id)
        
        collector = InstagramDataCollector()
        insight = collector.sync_media_insights(media.instagram_id)
        collector.close()
        
        return {
            "success": True,
            "message": (
                f"인사이트 수집 완료 - "
                f"좋아요: {insight.like_count}, "
                f"댓글: {insight.comments_count}, "
                f"도달: {insight.reach}"
            )
        }
    except Exception as e:
        logger.error(f"인사이트 수집 실패: {str(e)}")
        return {
            "success": False,
            "message": f"수집 실패: {str(e)}"
        }


@router.post("/insights/sync-all", response=SyncResponseSchema, summary="전체 인사이트 일괄 수집")
def sync_all_insights(request):
    """
    모든 미디어의 인사이트를 일괄 수집합니다.
    주의: 미디어가 많으면 시간이 오래 걸릴 수 있습니다.
    """
    try:
        collector = InstagramDataCollector()
        result = collector.sync_all_media_insights()
        collector.close()
        
        return {
            "success": True,
            "message": (
                f"일괄 수집 완료 - "
                f"성공: {result['success']}, "
                f"실패: {result['fail']}"
            ),
            "count": result['success']
        }
    except Exception as e:
        logger.error(f"일괄 수집 실패: {str(e)}")
        return {
            "success": False,
            "message": f"일괄 수집 실패: {str(e)}"
        }


@router.get("/insights/latest", response=List[InsightSchema], summary="최신 인사이트 목록")
def list_latest_insights(request, limit: int = 20):
    """
    최근 수집된 인사이트 목록을 조회합니다.
    
    - **limit**: 조회할 개수 (기본값: 20)
    """
    insights = InstagramInsight.objects.select_related('media').all()[:limit]
    return list(insights)
```

**API 엔드포인트 정리:**

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/instagram/account` | 계정 정보 조회 |
| POST | `/api/instagram/account/sync` | 계정 정보 동기화 |
| GET | `/api/instagram/media` | 미디어 목록 조회 |
| POST | `/api/instagram/media/sync` | 미디어 동기화 |
| GET | `/api/instagram/media/{id}` | 미디어 상세 조회 |
| POST | `/api/instagram/media/{id}/insights/sync` | 인사이트 수집 |
| POST | `/api/instagram/insights/sync-all` | 전체 인사이트 일괄 수집 |
| GET | `/api/instagram/insights/latest` | 최신 인사이트 목록 |

이제 Django-Ninja API가 완성되었습니다. 서버를 실행하고 `/api/docs`에 접속하면 자동 생성된 Swagger 문서에서 모든 엔드포인트를 테스트할 수 있습니다.

## 4부: Django Admin 및 실전 활용

### 4.1 Django Admin 커스터마이징

Django Admin을 통해 수집된 Instagram 데이터를 시각적으로 관리할 수 있습니다.

**instagram_collector/admin.py:**
```python
from django.contrib import admin
from django.utils.html import format_html
from .models import InstagramAccount, InstagramMedia, InstagramInsight


@admin.register(InstagramAccount)
class InstagramAccountAdmin(admin.ModelAdmin):
    """계정 정보 관리"""
    
    list_display = [
        'username_with_image',
        'name',
        'followers_count',
        'follows_count',
        'media_count',
        'last_synced_at'
    ]
    
    readonly_fields = [
        'instagram_business_account_id',
        'profile_picture_preview',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('instagram_business_account_id', 'username', 'name', 'biography')
        }),
        ('프로필 이미지', {
            'fields': ('profile_picture_url', 'profile_picture_preview')
        }),
        ('통계', {
            'fields': ('followers_count', 'follows_count', 'media_count')
        }),
        ('메타 정보', {
            'fields': ('last_synced_at', 'created_at', 'updated_at')
        }),
    )
    
    def username_with_image(self, obj):
        if obj.profile_picture_url:
            return format_html(
                '<img src="{}" style="width: 30px; height: 30px; border-radius: 50%; '
                'margin-right: 10px; vertical-align: middle;"/> @{}',
                obj.profile_picture_url,
                obj.username
            )
        return f"@{obj.username}"
    username_with_image.short_description = '사용자명'
    
    def profile_picture_preview(self, obj):
        if obj.profile_picture_url:
            return format_html(
                '<img src="{}" style="max-width: 200px; border-radius: 10px;"/>',
                obj.profile_picture_url
            )
        return "이미지 없음"
    profile_picture_preview.short_description = '프로필 사진 미리보기'


class InstagramInsightInline(admin.TabularInline):
    """미디어 상세 페이지에서 인사이트를 인라인으로 표시"""
    model = InstagramInsight
    extra = 0
    readonly_fields = ['collected_at', 'engagement_rate']
    fields = [
        'like_count',
        'comments_count',
        'saved_count',
        'reach',
        'impressions',
        'engagement_rate',
        'collected_at'
    ]
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(InstagramMedia)
class InstagramMediaAdmin(admin.ModelAdmin):
    """미디어 관리"""
    
    list_display = [
        'media_preview',
        'instagram_id_short',
        'media_type',
        'caption_short',
        'timestamp',
        'latest_stats'
    ]
    
    list_filter = ['media_type', 'timestamp']
    search_fields = ['instagram_id', 'caption']
    readonly_fields = [
        'instagram_id',
        'media_preview_large',
        'permalink_link',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('instagram_id', 'media_type', 'timestamp')
        }),
        ('콘텐츠', {
            'fields': ('caption', 'media_preview_large', 'permalink_link')
        }),
        ('미디어 URL', {
            'fields': ('media_url', 'thumbnail_url'),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [InstagramInsightInline]
    
    def media_preview(self, obj):
        if obj.media_url:
            if obj.media_type == 'VIDEO':
                url = obj.thumbnail_url or obj.media_url
            else:
                url = obj.media_url
            
            return format_html(
                '<img src="{}" style="width: 60px; height: 60px; object-fit: cover; '
                'border-radius: 5px;"/>',
                url
            )
        return "이미지 없음"
    media_preview.short_description = '미리보기'
    
    def media_preview_large(self, obj):
        if obj.media_url:
            if obj.media_type == 'VIDEO':
                url = obj.thumbnail_url or obj.media_url
                return format_html(
                    '<img src="{}" style="max-width: 400px; border-radius: 10px;"/>'
                    '<p style="color: #666;">비디오 썸네일</p>',
                    url
                )
            else:
                return format_html(
                    '<img src="{}" style="max-width: 400px; border-radius: 10px;"/>',
                    obj.media_url
                )
        return "이미지 없음"
    media_preview_large.short_description = '미디어 미리보기'
    
    def instagram_id_short(self, obj):
        return f"{obj.instagram_id[:15]}..."
    instagram_id_short.short_description = 'ID'
    
    def caption_short(self, obj):
        if obj.caption:
            return obj.caption[:50] + "..." if len(obj.caption) > 50 else obj.caption
        return "-"
    caption_short.short_description = '캡션'
    
    def permalink_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank">Instagram에서 보기 →</a>',
            obj.permalink
        )
    permalink_link.short_description = '원본 링크'
    
    def latest_stats(self, obj):
        insight = obj.insights.first()
        if insight:
            return format_html(
                '<div style="font-size: 11px; line-height: 1.4;">'
                '❤️ {}<br/>'
                '💬 {}<br/>'
                '👁️ {}<br/>'
                '📊 {}%'
                '</div>',
                insight.like_count,
                insight.comments_count,
                insight.impressions,
                insight.engagement_rate
            )
        return "-"
    latest_stats.short_description = '최신 성과'


@admin.register(InstagramInsight)
class InstagramInsightAdmin(admin.ModelAdmin):
    """인사이트 관리"""
    
    list_display = [
        'media_link',
        'like_count',
        'comments_count',
        'saved_count',
        'reach',
        'impressions',
        'engagement_rate_display',
        'collected_at'
    ]
    
    list_filter = ['collected_at']
    search_fields = ['media__instagram_id', 'media__caption']
    readonly_fields = ['media', 'collected_at', 'engagement_rate_display']
    
    fieldsets = (
        ('미디어 정보', {
            'fields': ('media',)
        }),
        ('인게이지먼트', {
            'fields': ('like_count', 'comments_count', 'saved_count')
        }),
        ('도달/노출', {
            'fields': ('reach', 'impressions')
        }),
        ('비디오', {
            'fields': ('video_views',),
            'classes': ('collapse',)
        }),
        ('분석', {
            'fields': ('engagement_rate_display', 'collected_at')
        }),
    )
    
    def media_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            f"/admin/instagram_collector/instagrammedia/{obj.media.id}/change/",
            f"{obj.media.instagram_id[:15]}..."
        )
    media_link.short_description = '미디어'
    
    def engagement_rate_display(self, obj):
        rate = obj.engagement_rate
        color = "#28a745" if rate > 5 else "#ffc107" if rate > 2 else "#dc3545"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.2f}%</span>',
            color,
            rate
        )
    engagement_rate_display.short_description = '인게이지먼트율'
    
    def has_add_permission(self, request):
        return False
```

Admin 사이트에서는:
- **계정 목록**: 프로필 이미지와 함께 팔로워 수, 게시물 수 확인
- **미디어 목록**: 썸네일 미리보기, 최신 성과 지표 한눈에 확인
- **인사이트 목록**: 좋아요, 댓글, 도달, 노출 데이터 및 인게이지먼트율

### 4.2 실전 활용 시나리오

**시나리오 1: 서버 시작 및 테스트**

```bash
# 개발 서버 실행
python manage.py runserver

# 브라우저에서 Swagger UI 접속
# http://localhost:8000/api/docs
```

**시나리오 2: 초기 데이터 수집**

```python
# Django Shell에서 실행
python manage.py shell

from instagram_collector.services import InstagramDataCollector

collector = InstagramDataCollector()

# 1. 계정 정보 동기화
account = collector.sync_account_info()
print(f"계정: @{account.username}, 팔로워: {account.followers_count}")

# 2. 최근 25개 게시물 동기화
count = collector.sync_media_list(limit=25)
print(f"{count}개 미디어 동기화 완료")

# 3. 모든 게시물의 인사이트 수집
result = collector.sync_all_media_insights()
print(f"성공: {result['success']}, 실패: {result['fail']}")

collector.close()
```

**시나리오 3: Celery로 주기적 수집 자동화**

Instagram 인사이트는 시간에 따라 변하므로, Celery Beat를 사용해 주기적으로 수집하는 것이 좋습니다.

```bash
# Celery 및 Redis 설치
pip install celery redis
```

**celery.py (프로젝트 루트):**
```python
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

app = Celery('myproject')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat 스케줄 설정
app.conf.beat_schedule = {
    'sync-instagram-data-daily': {
        'task': 'instagram_collector.tasks.sync_all_instagram_data',
        'schedule': crontab(hour=9, minute=0),  # 매일 오전 9시
    },
    'sync-instagram-insights-hourly': {
        'task': 'instagram_collector.tasks.sync_insights',
        'schedule': crontab(minute=0),  # 매 시간마다
    },
}
```

**instagram_collector/tasks.py:**
```python
from celery import shared_task
from .services import InstagramDataCollector
import logging

logger = logging.getLogger(__name__)


@shared_task
def sync_all_instagram_data():
    """모든 Instagram 데이터 동기화 (계정 정보 + 미디어)"""
    try:
        collector = InstagramDataCollector()
        
        # 계정 정보 동기화
        account = collector.sync_account_info()
        logger.info(f"계정 동기화 완료: @{account.username}")
        
        # 최근 50개 미디어 동기화
        count = collector.sync_media_list(limit=50)
        logger.info(f"미디어 동기화 완료: {count}개")
        
        collector.close()
        return {"status": "success", "media_count": count}
    except Exception as e:
        logger.error(f"동기화 실패: {str(e)}")
        return {"status": "failed", "error": str(e)}


@shared_task
def sync_insights():
    """모든 미디어의 인사이트 동기화"""
    try:
        collector = InstagramDataCollector()
        result = collector.sync_all_media_insights()
        collector.close()
        
        logger.info(f"인사이트 동기화 - 성공: {result['success']}, 실패: {result['fail']}")
        return result
    except Exception as e:
        logger.error(f"인사이트 동기화 실패: {str(e)}")
        return {"status": "failed", "error": str(e)}
```

**Celery 실행:**
```bash
# Worker 실행 (터미널 1)
celery -A myproject worker --loglevel=info

# Beat 실행 (터미널 2)
celery -A myproject beat --loglevel=info
```

**시나리오 4: 데이터 분석 쿼리**

```python
from django.db.models import Avg, Max, Min
from instagram_collector.models import InstagramMedia, InstagramInsight

# 평균 인게이지먼트율이 가장 높은 미디어 타입 찾기
from django.db.models import Q, F, FloatField
from django.db.models.functions import Cast

insights = InstagramInsight.objects.select_related('media').all()

# 미디어 타입별 평균 인게이지먼트율
for media_type in ['IMAGE', 'VIDEO', 'CAROUSEL_ALBUM']:
    avg_engagement = insights.filter(media__media_type=media_type).aggregate(
        avg_rate=Avg(
            (F('like_count') + F('comments_count') + F('saved_count')) * 100.0 / F('reach'),
            output_field=FloatField()
        )
    )
    print(f"{media_type}: {avg_engagement['avg_rate']:.2f}%")

# 가장 성과가 좋은 게시물 Top 5
top_posts = InstagramInsight.objects.select_related('media').order_by('-reach')[:5]
for insight in top_posts:
    print(f"도달: {insight.reach} | {insight.media.caption[:50]}")

# 특정 기간의 총 인게이지먼트
from datetime import datetime, timedelta
last_30_days = datetime.now() - timedelta(days=30)

total_engagement = InstagramInsight.objects.filter(
    collected_at__gte=last_30_days
).aggregate(
    total_likes=Avg('like_count'),
    total_comments=Avg('comments_count'),
    total_reach=Avg('reach')
)
print(f"최근 30일 평균: {total_engagement}")
```

### 4.3 에러 핸들링 및 모니터링

**일반적인 에러와 해결 방법:**

**1. Access Token 만료 (OAuthException)**
```python
# 에러 메시지: "Error validating access token: Session has expired"
# 해결: Long-lived token을 새로 발급하고 .env 파일 업데이트
```

**2. Rate Limit 초과 (Error Code 4)**
```python
# services.py에 Rate Limit 핸들링 추가

def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
    try:
        response = self.client.get(url, params=default_params)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:  # Rate Limit
            logger.warning("Rate limit reached. Waiting 60 seconds...")
            import time
            time.sleep(60)
            return self._make_request(endpoint, params)  # 재시도
        raise
```

**3. 권한 부족 (Permission Error)**
```python
# 에러: "Insufficient permissions for this operation"
# 해결: Graph API Explorer에서 필요한 권한 재확인
# - instagram_basic
# - instagram_manage_insights
# - pages_show_list
```

**4. 미디어 인사이트 접근 불가**
```python
# 일부 미디어는 24시간 이내 인사이트가 생성되지 않을 수 있음
# services.py에서 예외 처리

def get_media_insights(self, media_id: str) -> Dict:
    try:
        data = self._make_request(endpoint, params)
        # ... 처리
    except Exception as e:
        # 24시간 미만 게시물이거나 데이터 없음
        logger.warning(f"Insights not available for {media_id}: {str(e)}")
        return {}  # 빈 딕셔너리 반환
```

**로깅 설정 (settings.py):**
```python
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
            'class': 'logging.FileHandler',
            'filename': 'logs/instagram_collector.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'instagram_collector': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### 4.4 성능 최적화 팁

**1. 대량 데이터 수집 시 Bulk Create 사용**
```python
# services.py의 sync_media_list 메서드 최적화

def sync_media_list(self, limit: int = 25):
    media_list = self.api_client.get_media_list(limit=limit)
    
    media_objects = []
    for media_data in media_list:
        timestamp = datetime.fromisoformat(
            media_data['timestamp'].replace('Z', '+00:00')
        )
        
        media_objects.append(InstagramMedia(
            instagram_id=media_data['id'],
            media_type=media_data.get('media_type', 'IMAGE'),
            caption=media_data.get('caption', ''),
            permalink=media_data.get('permalink', ''),
            media_url=media_data.get('media_url', ''),
            thumbnail_url=media_data.get('thumbnail_url', ''),
            timestamp=timestamp,
        ))
    
    # Bulk create with ignore_conflicts (중복 무시)
    InstagramMedia.objects.bulk_create(
        media_objects,
        ignore_conflicts=True
    )
    
    return len(media_objects)
```

**2. Select Related로 N+1 쿼리 방지**
```python
# API에서 미디어 + 인사이트 조회 시

media_list = InstagramMedia.objects.prefetch_related('insights').all()[:25]
```

**3. 캐싱 활용**
```bash
pip install django-redis
```

```python
# settings.py
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# api.py에 캐싱 적용
from django.core.cache import cache

@router.get("/media", response=List[MediaSchema])
def list_media(request, limit: int = 25):
    cache_key = f"media_list_{limit}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return cached_data
    
    media_list = list(InstagramMedia.objects.all()[:limit])
    cache.set(cache_key, media_list, 300)  # 5분 캐싱
    return media_list
```

## 5부: 보안 및 배포

### 5.1 보안 Best Practices

**1. 환경 변수 보호**
```bash
# .gitignore에 추가 (절대 커밋 금지!)
.env
*.env
.env.local
.env.production
```

**2. Access Token 암호화 저장**
```python
# settings.py
from cryptography.fernet import Fernet

# 암호화 키 생성 (최초 1회만)
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key())"

ENCRYPTION_KEY = config('ENCRYPTION_KEY')  # .env에 저장
cipher = Fernet(ENCRYPTION_KEY)

# 토큰 암호화 헬퍼
def encrypt_token(token: str) -> str:
    return cipher.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    return cipher.decrypt(encrypted_token.encode()).decode()
```

**3. API 인증 및 권한 제어**
```python
# api.py에 인증 추가

from ninja.security import HttpBearer

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        # 간단한 토큰 인증 (실무에서는 JWT 등 사용)
        if token == settings.API_SECRET_KEY:
            return token
        return None

# API에 인증 적용
@router.post("/media/sync", auth=AuthBearer(), response=SyncResponseSchema)
def sync_media(request, limit: int = 25):
    # ... 구현
```

**4. HTTPS 강제 사용**
```python
# settings.py (운영 환경)
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

**5. CORS 설정**
```bash
pip install django-cors-headers
```

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    # ...
]

# 개발 환경
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# 운영 환경
# CORS_ALLOWED_ORIGINS = [
#     "https://yourdomain.com",
# ]
```

**6. 민감 데이터 로깅 방지**
```python
# services.py
def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
    # Access Token을 로그에 출력하지 않음
    safe_params = {k: v for k, v in params.items() if k != 'access_token'}
    logger.info(f"API 요청: {endpoint}, params: {safe_params}")
    
    # ... 요청 처리
```

### 5.2 배포 가이드

**Option 1: Docker 배포**

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 정적 파일 수집
RUN python manage.py collectstatic --noinput

# Gunicorn으로 실행
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "myproject.wsgi:application"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: instagram_db
      POSTGRES_USER: instagram_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  web:
    build: .
    command: gunicorn myproject.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
      - redis

  celery_worker:
    build: .
    command: celery -A myproject worker --loglevel=info
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - db
      - redis

  celery_beat:
    build: .
    command: celery -A myproject beat --loglevel=info
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
```

**배포 명령:**
```bash
# 이미지 빌드 및 컨테이너 실행
docker-compose up -d

# 마이그레이션 실행
docker-compose exec web python manage.py migrate

# Superuser 생성
docker-compose exec web python manage.py createsuperuser

# 로그 확인
docker-compose logs -f web
```

**Option 2: AWS EC2 배포**

```bash
# EC2 인스턴스 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 필수 패키지 설치
sudo apt update
sudo apt install python3-pip python3-venv postgresql postgresql-contrib nginx

# 프로젝트 클론
git clone https://github.com/yourusername/instagram-collector.git
cd instagram-collector

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
pip install gunicorn

# .env 파일 생성 (민감 정보 설정)
nano .env

# 데이터베이스 마이그레이션
python manage.py migrate
python manage.py collectstatic

# Gunicorn 서비스 설정
sudo nano /etc/systemd/system/instagram-collector.service
```

**/etc/systemd/system/instagram-collector.service:**
```ini
[Unit]
Description=Instagram Collector Gunicorn
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/instagram-collector
Environment="PATH=/home/ubuntu/instagram-collector/venv/bin"
ExecStart=/home/ubuntu/instagram-collector/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/home/ubuntu/instagram-collector/instagram.sock \
    myproject.wsgi:application

[Install]
WantedBy=multi-user.target
```

**Nginx 설정:**
```nginx
# /etc/nginx/sites-available/instagram-collector

server {
    listen 80;
    server_name your-domain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /home/ubuntu/instagram-collector;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/ubuntu/instagram-collector/instagram.sock;
    }
}
```

**서비스 시작:**
```bash
# Gunicorn 서비스 활성화
sudo systemctl start instagram-collector
sudo systemctl enable instagram-collector

# Nginx 설정 활성화
sudo ln -s /etc/nginx/sites-available/instagram-collector /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx

# Celery 설정 (별도 서비스로)
sudo systemctl start celery-worker
sudo systemctl start celery-beat
```

**Option 3: Heroku 배포 (간편)**

```bash
# Heroku CLI 설치 및 로그인
heroku login

# 앱 생성
heroku create instagram-collector-app

# PostgreSQL 추가
heroku addons:create heroku-postgresql:mini

# Redis 추가
heroku addons:create heroku-redis:mini

# 환경 변수 설정
heroku config:set INSTAGRAM_ACCESS_TOKEN=your_token
heroku config:set INSTAGRAM_APP_ID=your_app_id
# ... 기타 환경 변수

# 배포
git push heroku main

# 마이그레이션
heroku run python manage.py migrate

# Celery worker 실행 (Procfile에 정의)
heroku ps:scale worker=1
```

**Procfile:**
```
web: gunicorn myproject.wsgi --log-file -
worker: celery -A myproject worker --loglevel=info
beat: celery -A myproject beat --loglevel=info
```

### 5.3 모니터링 및 알림

**Sentry 에러 트래킹 설정**
```bash
pip install sentry-sdk
```

```python
# settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=config('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=True,
    environment=config('ENVIRONMENT', default='development'),
)
```

**Slack 알림 (수집 완료 시)**
```python
# services.py에 Slack 웹훅 추가

import httpx

def send_slack_notification(message: str):
    webhook_url = settings.SLACK_WEBHOOK_URL
    if not webhook_url:
        return
    
    payload = {
        "text": message,
        "username": "Instagram Collector Bot",
        "icon_emoji": ":camera:"
    }
    
    try:
        httpx.post(webhook_url, json=payload, timeout=5.0)
    except Exception as e:
        logger.error(f"Slack 알림 전송 실패: {str(e)}")

# tasks.py에서 사용
@shared_task
def sync_all_instagram_data():
    try:
        collector = InstagramDataCollector()
        account = collector.sync_account_info()
        count = collector.sync_media_list(limit=50)
        collector.close()
        
        send_slack_notification(
            f"✅ Instagram 데이터 동기화 완료\n"
            f"계정: @{account.username}\n"
            f"미디어: {count}개"
        )
        
        return {"status": "success", "media_count": count}
    except Exception as e:
        send_slack_notification(f"❌ 동기화 실패: {str(e)}")
        raise
```

### 5.4 확장 아이디어

**1. 해시태그 분석**
```python
# 캡션에서 해시태그 추출 및 통계
import re

def extract_hashtags(caption: str) -> List[str]:
    return re.findall(r'#(\w+)', caption)

# 가장 많이 사용된 해시태그 Top 10
from collections import Counter

all_captions = InstagramMedia.objects.values_list('caption', flat=True)
all_hashtags = []
for caption in all_captions:
    if caption:
        all_hashtags.extend(extract_hashtags(caption))

top_hashtags = Counter(all_hashtags).most_common(10)
```

**2. 최적 게시 시간 분석**
```python
from django.db.models.functions import ExtractHour
from django.db.models import Avg

# 시간대별 평균 도달 수
hourly_performance = InstagramInsight.objects.annotate(
    hour=ExtractHour('media__timestamp')
).values('hour').annotate(
    avg_reach=Avg('reach'),
    avg_engagement=Avg(F('like_count') + F('comments_count'))
).order_by('-avg_reach')

print("최적 게시 시간:")
for item in hourly_performance[:5]:
    print(f"{item['hour']}시: 도달 {item['avg_reach']:.0f}, 인게이지먼트 {item['avg_engagement']:.0f}")
```

**3. 대시보드 구축 (Chart.js)**
```python
# api.py에 차트 데이터 엔드포인트 추가

@router.get("/analytics/performance-trend")
def get_performance_trend(request, days: int = 30):
    """최근 N일간 성과 추이"""
    from datetime import datetime, timedelta
    from django.db.models.functions import TruncDate
    
    start_date = datetime.now() - timedelta(days=days)
    
    daily_stats = InstagramInsight.objects.filter(
        collected_at__gte=start_date
    ).annotate(
        date=TruncDate('collected_at')
    ).values('date').annotate(
        total_likes=Avg('like_count'),
        total_comments=Avg('comments_count'),
        total_reach=Avg('reach'),
        total_impressions=Avg('impressions')
    ).order_by('date')
    
    return {
        "labels": [item['date'].strftime('%Y-%m-%d') for item in daily_stats],
        "datasets": [
            {
                "label": "도달 수",
                "data": [item['total_reach'] for item in daily_stats]
            },
            {
                "label": "노출 수",
                "data": [item['total_impressions'] for item in daily_stats]
            }
        ]
    }
```

**4. AI 기반 캡션 추천**
```python
# OpenAI GPT를 활용한 캡션 분석

import openai

def analyze_top_performing_captions():
    """성과 좋은 게시물의 캡션 패턴 분석"""
    top_posts = InstagramInsight.objects.select_related('media').order_by('-reach')[:10]
    
    captions = [post.media.caption for post in top_posts if post.media.caption]
    
    prompt = f"""
    다음은 Instagram에서 가장 성과가 좋았던 게시물의 캡션들입니다:
    
    {captions}
    
    이 캡션들의 공통 패턴과 특징을 분석하고, 새로운 게시물을 위한 캡션 작성 가이드라인을 제시해주세요.
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content
```

## 결론

이 가이드에서는 Django-Ninja와 Instagram Graph API를 연동하여 Instagram 콘텐츠 데이터를 자동으로 수집하고 분석하는 전체 시스템을 구축했습니다.

**구현한 주요 기능:**
- ✅ Meta 개발자 계정 설정 및 Access Token 발급
- ✅ Django-Ninja 기반 RESTful API 구축
- ✅ Instagram 미디어 및 인사이트 자동 수집
- ✅ Django ORM을 통한 데이터베이스 저장
- ✅ 시각적 Django Admin 대시보드
- ✅ Celery를 활용한 주기적 데이터 동기화
- ✅ 에러 핸들링 및 로깅
- ✅ 보안 Best Practices
- ✅ Docker/AWS/Heroku 배포 가이드

**핵심 학습 포인트:**
1. **Django-Ninja**는 FastAPI의 장점을 Django에 가져온 강력한 API 프레임워크입니다
2. **Instagram Graph API**는 비즈니스 계정의 풍부한 인사이트 데이터를 제공합니다
3. **서비스 레이어 패턴**을 통해 API 호출 로직과 비즈니스 로직을 분리하면 유지보수가 쉽습니다
4. **Celery Beat**로 주기적 데이터 수집을 자동화하면 실시간 분석이 가능합니다
5. **보안**은 선택이 아닌 필수입니다 - 환경 변수, 암호화, HTTPS를 항상 적용하세요

**다음 단계:**
- Frontend (React/Vue) 연동으로 시각적 대시보드 구축
- 머신러닝 모델로 콘텐츠 성과 예측
- 멀티 계정 관리 기능 추가
- Instagram Stories, Reels 데이터 수집 확장
- 경쟁사 분석 기능 (공개 데이터 활용)

Instagram API를 활용하면 데이터 기반 소셜 미디어 마케팅 전략을 수립할 수 있습니다. 이 시스템을 기반으로 자신만의 Instagram 분석 도구를 만들어보세요!

**참고 자료:**
- [Instagram Graph API 공식 문서](https://developers.facebook.com/docs/instagram-api)
- [Django-Ninja 공식 문서](https://django-ninja.rest-framework.com/)
- [Meta for Developers](https://developers.facebook.com/)
- [Celery 공식 문서](https://docs.celeryproject.org/)

---

*이 포스트가 도움이 되었다면 GitHub에 Star를 눌러주세요! 질문이나 피드백은 댓글로 남겨주시면 감사하겠습니다.* 🚀
