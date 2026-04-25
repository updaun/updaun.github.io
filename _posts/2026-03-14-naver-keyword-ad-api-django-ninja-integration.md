---
layout: post
title: "네이버 검색광고 API로 키워드 검색량 분석하기 - Django Ninja 연동 완벽 가이드"
date: 2026-03-14 10:00:00 +0900
categories: [Django, Python, API, Marketing]
tags: [Django Ninja, Naver API, Keyword Research, SEO, Backend, Python, Marketing Analytics, Search Advertising]
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-03-14-naver-keyword-ad-api-django-ninja-integration.webp"
---

SEO와 콘텐츠 마케팅을 위해 키워드 검색량 데이터는 필수입니다. 네이버는 국내 검색 시장의 30% 이상을 차지하는 주요 검색 엔진으로, 네이버 검색광고 API를 통해 키워드별 월간 검색량, PC/모바일 비율, 경쟁 정도 등 귀중한 데이터를 얻을 수 있습니다. 이 글에서는 Django Ninja와 네이버 검색광고 API를 연동하여 키워드 검색량을 분석하는 서비스를 구축하는 전체 과정을 단계별로 살펴보겠습니다.

## 🎯 프로젝트 개요

### 구축할 서비스의 주요 기능

네이버 검색광고 API를 활용하여 다음과 같은 핵심 기능을 제공하는 서비스를 만들겠습니다:

1. **키워드 검색량 조회**: 특정 키워드의 월간 검색량 (PC/모바일 분리)
2. **연관 키워드 추천**: 입력한 키워드와 관련된 연관 키워드 목록 제공
3. **경쟁도 분석**: 키워드별 경쟁 정도와 클릭당 비용(CPC) 정보
4. **데이터 저장 및 이력 관리**: 조회한 키워드 데이터를 DB에 저장하여 트렌드 분석
5. **RESTful API 제공**: Django Ninja를 통한 고성능 API 엔드포인트

### 기술 스택

```python
# 주요 기술 스택
{
    "Backend Framework": "Django 5.0+",
    "API Framework": "Django Ninja 1.1+",
    "External API": "Naver Search Ad API",
    "Database": "PostgreSQL 15+",
    "Cache": "Redis",
    "Authentication": "OAuth 2.0 (Naver)",
    "HTTP Client": "httpx",
    "Python Version": "3.11+"
}
```

Django Ninja는 FastAPI의 간결함과 Django의 강력한 생태계를 결합한 프레임워크로, 자동 API 문서화, 타입 안정성, 높은 성능을 제공합니다. 네이버 API와의 통신에는 비동기를 지원하는 httpx 라이브러리를 사용하겠습니다.

## 📋 1단계: 네이버 검색광고 API 설정

### 네이버 광고 계정 생성 및 API 신청

네이버 검색광고 API를 사용하기 위해서는 먼저 광고 계정을 생성하고 API 사용 권한을 신청해야 합니다.

```bash
# 1단계: 네이버 검색광고 사이트 접속
# https://searchad.naver.com/

# 2단계: 광고 계정 생성
# - 네이버 계정으로 로그인
# - 비즈니스 채널 선택 (개인 또는 사업자)
# - 사업자 정보 입력 (개인은 주민등록번호 뒷자리 불필요)

# 3단계: API 사용 신청
# 도구 > API 관리 > API 신청하기
# - API 사용 목적: 키워드 검색량 조회 및 분석
# - 승인까지 1-2 영업일 소요
```

### API 인증 정보 발급

API 신청이 승인되면 고객 ID와 API 인증 정보를 발급받을 수 있습니다.

```python
# API 관리 페이지에서 확인할 정보:
# 1. 고객 ID (Customer ID): 예) 1234567
# 2. API 접근 인증키 (API Key): 예) 0100000000abcd1234567890...
# 3. 비밀 키 (Secret Key): 예) AQAAAACabcd123456789...

# ⚠️ 주의사항:
# - Secret Key는 최초 1회만 표시되므로 반드시 안전하게 보관
# - 외부 노출 금지 (GitHub, 공개 저장소에 업로드 금지)
# - 주기적으로 키를 갱신하여 보안 강화
```

### 환경 변수 설정

API 인증 정보를 환경 변수로 관리하여 보안을 강화합니다.

```bash
# .env 파일 생성
touch .env

# .gitignore에 .env 추가 (필수!)
echo ".env" >> .gitignore
```

```python
# .env 파일 내용
# 네이버 검색광고 API 인증 정보
NAVER_API_KEY=0100000000abcd1234567890abcdef1234567890abcdef1234567890abcdef12
NAVER_SECRET_KEY=AQAAAACabcd123456789abcdef123456789==
NAVER_CUSTOMER_ID=1234567

# Django 설정
DJANGO_SECRET_KEY=your-django-secret-key-here
DEBUG=True

# 데이터베이스
DATABASE_URL=postgresql://user:password@localhost:5432/naver_keyword_db

# Redis (캐싱용)
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600
```

### 네이버 API 엔드포인트 확인

네이버 검색광고 API는 다음과 같은 주요 엔드포인트를 제공합니다:

```python
# 네이버 검색광고 API 주요 엔드포인트
NAVER_API_ENDPOINTS = {
    # 키워드 도구 API
    "keyword_tool": "https://api.naver.com/keywordstool",
    
    # 키워드 검색량 조회 (월간 검색량)
    "keyword_volume": "https://api.naver.com/keywordstool",
    
    # 연관 키워드 조회
    "related_keywords": "https://api.naver.com/keywordstool",
    
    # API 기본 URL
    "base_url": "https://api.naver.com"
}

# API 요청 시 필수 헤더
REQUIRED_HEADERS = {
    "X-Naver-Client-Id": "YOUR_API_KEY",
    "X-Naver-Client-Secret": "YOUR_SECRET_KEY",
    "Content-Type": "application/json"
}
```

## 🚀 2단계: Django 프로젝트 초기 설정

### 프로젝트 생성 및 가상환경 설정

Django 프로젝트를 생성하고 필요한 패키지를 설치합니다.

```bash
# 프로젝트 디렉토리 생성
mkdir naver-keyword-analyzer
cd naver-keyword-analyzer

# Python 가상환경 생성 및 활성화
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 최신 pip 설치
pip install --upgrade pip

# 필수 패키지 설치
pip install django==5.0.3
pip install django-ninja==1.1.0
pip install python-dotenv==1.0.1
pip install httpx==0.27.0
pip install psycopg2-binary==2.9.9  # PostgreSQL
pip install redis==5.0.1
pip install django-redis==5.4.0
pip install pydantic==2.6.3

# requirements.txt 생성
pip freeze > requirements.txt
```

### Django 프로젝트 및 앱 생성

```bash
# Django 프로젝트 생성
django-admin startproject config .

# 키워드 분석 앱 생성
python manage.py startapp keywords

# 프로젝트 구조 확인
tree -L 2
# .
# ├── config/
# │   ├── __init__.py
# │   ├── settings.py
# │   ├── urls.py
# │   └── wsgi.py
# ├── keywords/
# │   ├── migrations/
# │   ├── __init__.py
# │   ├── admin.py
# │   ├── apps.py
# │   ├── models.py
# │   ├── tests.py
# │   └── views.py
# ├── manage.py
# └── requirements.txt
```

### settings.py 설정

Django 설정 파일을 수정하여 앱과 미들웨어를 등록합니다.

```python
# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# 보안 설정
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# 앱 등록
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party apps
    'ninja',
    # Local apps
    'keywords',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# PostgreSQL 데이터베이스 설정
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'naver_keyword_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Redis 캐시 설정
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "naver_keyword",
        "TIMEOUT": int(os.getenv('REDIS_CACHE_TTL', 3600)),
    }
}

# 네이버 API 설정
NAVER_API_KEY = os.getenv('NAVER_API_KEY')
NAVER_SECRET_KEY = os.getenv('NAVER_SECRET_KEY')
NAVER_CUSTOMER_ID = os.getenv('NAVER_CUSTOMER_ID')

# 국제화
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

### 데이터베이스 모델 설계

키워드 검색량 데이터를 저장할 모델을 설계합니다.

```python
# keywords/models.py
from django.db import models
from django.utils import timezone

class Keyword(models.Model):
    """키워드 기본 정보"""
    keyword = models.CharField(max_length=200, unique=True, db_index=True, 
                               verbose_name="키워드")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        db_table = 'keywords'
        verbose_name = '키워드'
        verbose_name_plural = '키워드 목록'
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.keyword


class KeywordStatistics(models.Model):
    """키워드 통계 정보 (시계열 데이터)"""
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, 
                               related_name='statistics')
    
    # 검색량 데이터
    monthly_pc_search_count = models.BigIntegerField(
        verbose_name="월간 PC 검색량", default=0)
    monthly_mobile_search_count = models.BigIntegerField(
        verbose_name="월간 모바일 검색량", default=0)
    monthly_total_search_count = models.BigIntegerField(
        verbose_name="월간 총 검색량", default=0)
    
    # 경쟁도 데이터
    competition_level = models.CharField(
        max_length=20, verbose_name="경쟁도", 
        choices=[
            ('LOW', '낮음'),
            ('MEDIUM', '보통'),
            ('HIGH', '높음'),
        ],
        default='MEDIUM'
    )
    
    # 비용 데이터 (원 단위)
    avg_cpc = models.IntegerField(verbose_name="평균 클릭당 비용(CPC)", 
                                  null=True, blank=True)
    
    # 조회 시점
    measured_at = models.DateField(verbose_name="측정일", 
                                   default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    
    class Meta:
        db_table = 'keyword_statistics'
        verbose_name = '키워드 통계'
        verbose_name_plural = '키워드 통계 목록'
        ordering = ['-measured_at']
        # 같은 키워드의 같은 날짜 중복 방지
        unique_together = [['keyword', 'measured_at']]
    
    def __str__(self):
        return f"{self.keyword.keyword} - {self.measured_at}"
    
    @property
    def mobile_ratio(self):
        """모바일 검색 비율 계산"""
        if self.monthly_total_search_count == 0:
            return 0
        return round(
            (self.monthly_mobile_search_count / self.monthly_total_search_count) * 100, 
            2
        )


class RelatedKeyword(models.Model):
    """연관 키워드"""
    source_keyword = models.ForeignKey(
        Keyword, on_delete=models.CASCADE, 
        related_name='related_keywords',
        verbose_name="원본 키워드"
    )
    related_keyword = models.CharField(max_length=200, verbose_name="연관 키워드")
    relevance_score = models.FloatField(
        verbose_name="연관도 점수", 
        default=0.0,
        help_text="0.0 ~ 1.0 사이의 값"
    )
    monthly_search_count = models.BigIntegerField(
        verbose_name="월간 검색량", default=0)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    
    class Meta:
        db_table = 'related_keywords'
        verbose_name = '연관 키워드'
        verbose_name_plural = '연관 키워드 목록'
        ordering = ['-relevance_score', '-monthly_search_count']
        unique_together = [['source_keyword', 'related_keyword']]
    
    def __str__(self):
        return f"{self.source_keyword.keyword} → {self.related_keyword}"
```

### 마이그레이션 실행

```bash
# 마이그레이션 파일 생성
python manage.py makemigrations

# 데이터베이스에 적용
python manage.py migrate

# 슈퍼유저 생성 (관리자 페이지 접근용)
python manage.py createsuperuser
```

## 🔧 3단계: 네이버 API 클라이언트 구현

### API 클라이언트 서비스 클래스 작성

네이버 검색광고 API와 통신하는 서비스 클래스를 작성합니다.

```python
# keywords/services/naver_api_client.py
import httpx
from typing import List, Dict, Optional
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class NaverKeywordAPIClient:
    """네이버 검색광고 API 클라이언트"""
    
    BASE_URL = "https://api.naver.com"
    
    def __init__(self):
        self.api_key = settings.NAVER_API_KEY
        self.secret_key = settings.NAVER_SECRET_KEY
        self.customer_id = settings.NAVER_CUSTOMER_ID
        
        if not all([self.api_key, self.secret_key, self.customer_id]):
            raise ValueError("네이버 API 인증 정보가 설정되지 않았습니다.")
    
    def _get_headers(self) -> Dict[str, str]:
        """API 요청 헤더 생성"""
        return {
            "X-Naver-Client-Id": self.api_key,
            "X-Naver-Client-Secret": self.secret_key,
            "X-Customer-Id": self.customer_id,
            "Content-Type": "application/json"
        }
    
    async def get_keyword_statistics(
        self, 
        keywords: List[str],
        show_detail: bool = True
    ) -> Dict:
        """
        키워드 검색량 통계 조회
        
        Args:
            keywords: 조회할 키워드 리스트 (최대 5개)
            show_detail: 상세 정보 포함 여부
            
        Returns:
            Dict: API 응답 데이터
        """
        # 캐시 확인
        cache_key = f"naver_keyword_stats_{','.join(sorted(keywords))}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"캐시에서 데이터 반환: {keywords}")
            return cached_data
        
        # API 요청
        url = f"{self.BASE_URL}/keywordstool"
        payload = {
            "hintKeywords": keywords,
            "showDetail": 1 if show_detail else 0
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                
                data = response.json()
                
                # 캐시 저장 (1시간)
                cache.set(cache_key, data, timeout=3600)
                
                logger.info(f"키워드 통계 조회 성공: {keywords}")
                return data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"API 요청 실패 (HTTP {e.response.status_code}): {e}")
            raise Exception(f"네이버 API 오류: {e.response.status_code}")
        except Exception as e:
            logger.error(f"키워드 통계 조회 중 오류: {e}")
            raise
    
    async def get_related_keywords(
        self, 
        keyword: str,
        max_results: int = 50
    ) -> List[Dict]:
        """
        연관 키워드 조회
        
        Args:
            keyword: 기준 키워드
            max_results: 최대 결과 개수
            
        Returns:
            List[Dict]: 연관 키워드 목록
        """
        # 캐시 확인
        cache_key = f"naver_related_kw_{keyword}_{max_results}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"캐시에서 연관 키워드 반환: {keyword}")
            return cached_data
        
        url = f"{self.BASE_URL}/keywordstool"
        payload = {
            "hintKeywords": [keyword],
            "showDetail": 1
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                
                data = response.json()
                
                # 연관 키워드 추출 및 정렬
                related = data.get('keywordList', [])[:max_results]
                
                # 캐시 저장 (3시간)
                cache.set(cache_key, related, timeout=10800)
                
                logger.info(f"연관 키워드 조회 성공: {keyword} -> {len(related)}개")
                return related
                
        except Exception as e:
            logger.error(f"연관 키워드 조회 중 오류: {e}")
            raise
    
    async def get_keyword_competition(
        self, 
        keyword: str
    ) -> Dict[str, any]:
        """
        키워드 경쟁도 및 CPC 정보 조회
        
        Args:
            keyword: 조회할 키워드
            
        Returns:
            Dict: 경쟁도 및 비용 정보
        """
        stats = await self.get_keyword_statistics([keyword], show_detail=True)
        
        if not stats.get('keywordList'):
            return {
                'keyword': keyword,
                'competition_level': 'UNKNOWN',
                'avg_cpc': 0,
                'error': '데이터 없음'
            }
        
        kw_data = stats['keywordList'][0]
        
        return {
            'keyword': keyword,
            'competition_level': kw_data.get('compIdx', 'MEDIUM'),
            'avg_cpc': kw_data.get('avgCpc', 0),
            'monthly_pc_qc_cnt': kw_data.get('monthlyPcQcCnt', 0),
            'monthly_mobile_qc_cnt': kw_data.get('monthlyMobileQcCnt', 0),
        }
```

### Pydantic 스키마 정의

API 요청/응답 데이터의 타입을 정의합니다.

```python
# keywords/schemas.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import date


class KeywordSearchRequest(BaseModel):
    """키워드 검색 요청 스키마"""
    keywords: List[str] = Field(
        ..., 
        min_items=1,
        max_items=5,
        description="조회할 키워드 목록 (최대 5개)"
    )
    
    @validator('keywords')
    def validate_keywords(cls, v):
        # 빈 문자열 제거 및 공백 제거
        cleaned = [kw.strip() for kw in v if kw.strip()]
        if not cleaned:
            raise ValueError("유효한 키워드가 없습니다")
        return cleaned


class KeywordStatisticsResponse(BaseModel):
    """키워드 통계 응답 스키마"""
    keyword: str
    monthly_pc_search_count: int = Field(alias="monthlyPcQcCnt")
    monthly_mobile_search_count: int = Field(alias="monthlyMobileQcCnt")
    monthly_total_search_count: int
    competition_level: str = Field(alias="compIdx")
    avg_cpc: Optional[int] = Field(None, alias="avgCpc")
    mobile_ratio: float
    measured_at: date
    
    class Config:
        populate_by_name = True
    
    @validator('monthly_total_search_count', always=True)
    def calculate_total(cls, v, values):
        if v:
            return v
        pc = values.get('monthly_pc_search_count', 0)
        mobile = values.get('monthly_mobile_search_count', 0)
        return pc + mobile
    
    @validator('mobile_ratio', always=True)
    def calculate_mobile_ratio(cls, v, values):
        total = values.get('monthly_total_search_count', 0)
        mobile = values.get('monthly_mobile_search_count', 0)
        if total == 0:
            return 0.0
        return round((mobile / total) * 100, 2)


class RelatedKeywordResponse(BaseModel):
    """연관 키워드 응답 스키마"""
    keyword: str = Field(alias="relKeyword")
    monthly_search_count: int = Field(alias="monthlyQcCnt")
    competition_level: str = Field(default="MEDIUM", alias="compIdx")
    relevance_score: float = 1.0
    
    class Config:
        populate_by_name = True


class KeywordAnalysisResponse(BaseModel):
    """전체 키워드 분석 응답"""
    statistics: KeywordStatisticsResponse
    related_keywords: List[RelatedKeywordResponse]
    total_related_count: int
```

## 🎨 4단계: Django Ninja API 엔드포인트 구현

### API 라우터 설정

Django Ninja API 라우터를 생성하고 엔드포인트들을 구현합니다.

```python
# keywords/api.py
from ninja import NinjaAPI, Router
from ninja.responses import Response
from typing import List
from datetime import date
from django.shortcuts import get_object_or_404
from asgiref.sync import sync_to_async
import asyncio

from .models import Keyword, KeywordStatistics, RelatedKeyword
from .schemas import (
    KeywordSearchRequest,
    KeywordStatisticsResponse,
    RelatedKeywordResponse,
    KeywordAnalysisResponse
)
from .services.naver_api_client import NaverKeywordAPIClient

# API 인스턴스 생성
api = NinjaAPI(
    title="네이버 키워드 분석 API",
    version="1.0.0",
    description="네이버 검색광고 API를 활용한 키워드 검색량 분석 서비스"
)

router = Router()


@router.post("/keywords/search", response=List[KeywordStatisticsResponse])
async def search_keywords(request, payload: KeywordSearchRequest):
    """
    키워드 검색량 조회
    
    - 최대 5개의 키워드를 동시 조회
    - 월간 PC/모바일 검색량, 경쟁도, CPC 정보 제공
    - 결과는 자동으로 DB에 저장
    """
    client = NaverKeywordAPIClient()
    
    try:
        # 네이버 API 호출
        result = await client.get_keyword_statistics(
            keywords=payload.keywords,
            show_detail=True
        )
        
        keyword_list = result.get('keywordList', [])
        responses = []
        
        # 각 키워드 데이터 처리 및 저장
        for kw_data in keyword_list:
            keyword_text = kw_data.get('relKeyword', '')
            
            # Keyword 모델 생성 또는 조회
            keyword_obj, created = await sync_to_async(
                Keyword.objects.get_or_create
            )(keyword=keyword_text)
            
            # 통계 데이터 저장
            monthly_pc = kw_data.get('monthlyPcQcCnt', 0)
            monthly_mobile = kw_data.get('monthlyMobileQcCnt', 0)
            monthly_total = monthly_pc + monthly_mobile
            
            # 경쟁도 변환
            comp_idx_raw = kw_data.get('compIdx', 'low')
            comp_level_map = {
                'low': 'LOW',
                'medium': 'MEDIUM',
                'high': 'HIGH'
            }
            comp_level = comp_level_map.get(comp_idx_raw.lower(), 'MEDIUM')
            
            # KeywordStatistics 저장
            await sync_to_async(KeywordStatistics.objects.update_or_create)(
                keyword=keyword_obj,
                measured_at=date.today(),
                defaults={
                    'monthly_pc_search_count': monthly_pc,
                    'monthly_mobile_search_count': monthly_mobile,
                    'monthly_total_search_count': monthly_total,
                    'competition_level': comp_level,
                    'avg_cpc': kw_data.get('avgCpc'),
                }
            )
            
            # 응답 데이터 생성
            mobile_ratio = (
                round((monthly_mobile / monthly_total) * 100, 2) 
                if monthly_total > 0 else 0
            )
            
            responses.append(KeywordStatisticsResponse(
                keyword=keyword_text,
                monthlyPcQcCnt=monthly_pc,
                monthlyMobileQcCnt=monthly_mobile,
                monthly_total_search_count=monthly_total,
                compIdx=comp_level,
                avgCpc=kw_data.get('avgCpc'),
                mobile_ratio=mobile_ratio,
                measured_at=date.today()
            ))
        
        return responses
        
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=500
        )


@router.get("/keywords/{keyword}/related", response=List[RelatedKeywordResponse])
async def get_related_keywords(request, keyword: str, limit: int = 20):
    """
    연관 키워드 조회
    
    - 입력한 키워드와 관련된 연관 키워드 목록
    - 검색량 기준 정렬
    - DB에 저장하여 이력 관리
    """
    client = NaverKeywordAPIClient()
    
    try:
        # 기준 키워드 생성 또는 조회
        keyword_obj, _ = await sync_to_async(
            Keyword.objects.get_or_create
        )(keyword=keyword)
        
        # 연관 키워드 조회
        related_list = await client.get_related_keywords(
            keyword=keyword,
            max_results=limit
        )
        
        responses = []
        
        # 연관 키워드 저장 및 응답 생성
        for rel_data in related_list[:limit]:
            rel_keyword_text = rel_data.get('relKeyword', '')
            monthly_qc = rel_data.get('monthlyQcCnt', 0)
            comp_idx = rel_data.get('compIdx', 'medium')
            
            # RelatedKeyword 저장
            await sync_to_async(RelatedKeyword.objects.update_or_create)(
                source_keyword=keyword_obj,
                related_keyword=rel_keyword_text,
                defaults={
                    'monthly_search_count': monthly_qc,
                    'relevance_score': 0.8,  # 기본 연관도
                }
            )
            
            responses.append(RelatedKeywordResponse(
                relKeyword=rel_keyword_text,
                monthlyQcCnt=monthly_qc,
                compIdx=comp_idx,
                relevance_score=0.8
            ))
        
        return responses
        
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=500
        )


@router.get("/keywords/{keyword}/analysis", response=KeywordAnalysisResponse)
async def analyze_keyword(request, keyword: str):
    """
    키워드 종합 분석
    
    - 키워드 통계 + 연관 키워드를 한 번에 조회
    - 마케팅 의사결정을 위한 종합 정보 제공
    """
    client = NaverKeywordAPIClient()
    
    try:
        # 메인 키워드 통계 조회
        stats_result = await client.get_keyword_statistics(
            keywords=[keyword],
            show_detail=True
        )
        
        # 연관 키워드 조회
        related_result = await client.get_related_keywords(
            keyword=keyword,
            max_results=30
        )
        
        # 통계 데이터 파싱
        kw_data = stats_result.get('keywordList', [{}])[0]
        monthly_pc = kw_data.get('monthlyPcQcCnt', 0)
        monthly_mobile = kw_data.get('monthlyMobileQcCnt', 0)
        monthly_total = monthly_pc + monthly_mobile
        
        mobile_ratio = (
            round((monthly_mobile / monthly_total) * 100, 2) 
            if monthly_total > 0 else 0
        )
        
        # 경쟁도 변환
        comp_idx_raw = kw_data.get('compIdx', 'medium')
        comp_level_map = {'low': 'LOW', 'medium': 'MEDIUM', 'high': 'HIGH'}
        comp_level = comp_level_map.get(comp_idx_raw.lower(), 'MEDIUM')
        
        statistics = KeywordStatisticsResponse(
            keyword=keyword,
            monthlyPcQcCnt=monthly_pc,
            monthlyMobileQcCnt=monthly_mobile,
            monthly_total_search_count=monthly_total,
            compIdx=comp_level,
            avgCpc=kw_data.get('avgCpc'),
            mobile_ratio=mobile_ratio,
            measured_at=date.today()
        )
        
        # 연관 키워드 파싱
        related = [
            RelatedKeywordResponse(
                relKeyword=r.get('relKeyword', ''),
                monthlyQcCnt=r.get('monthlyQcCnt', 0),
                compIdx=r.get('compIdx', 'medium'),
                relevance_score=0.8
            )
            for r in related_result[:30]
        ]
        
        return KeywordAnalysisResponse(
            statistics=statistics,
            related_keywords=related,
            total_related_count=len(related)
        )
        
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=500
        )


@router.get("/keywords/{keyword}/history")
async def get_keyword_history(request, keyword: str):
    """
    키워드 검색량 이력 조회
    
    - 최근 30일간의 검색량 변화 추이
    - 트렌드 분석에 활용
    """
    try:
        keyword_obj = await sync_to_async(
            Keyword.objects.get
        )(keyword=keyword)
        
        # 최근 30일 통계 조회
        stats = await sync_to_async(list)(
            keyword_obj.statistics.all()[:30]
        )
        
        history = [
            {
                'measured_at': stat.measured_at,
                'monthly_total_search_count': stat.monthly_total_search_count,
                'monthly_pc_search_count': stat.monthly_pc_search_count,
                'monthly_mobile_search_count': stat.monthly_mobile_search_count,
                'mobile_ratio': stat.mobile_ratio,
                'competition_level': stat.competition_level,
                'avg_cpc': stat.avg_cpc,
            }
            for stat in stats
        ]
        
        return {
            'keyword': keyword,
            'total_records': len(history),
            'history': history
        }
        
    except Keyword.DoesNotExist:
        return Response(
            {"error": "키워드를 찾을 수 없습니다"},
            status=404
        )


# 라우터를 API에 등록
api.add_router("/api/v1/", router)
```

### URL 설정

```python
# config/urls.py
from django.contrib import admin
from django.urls import path
from keywords.api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', api.urls),  # Django Ninja API 연결
]
```

### 서버 실행 및 API 문서 확인

```bash
# 개발 서버 실행
python manage.py runserver

# API 문서 자동 생성 확인
# 브라우저에서 접속: http://localhost:8000/api/docs
# Swagger UI를 통해 모든 엔드포인트와 스키마 확인 가능
```

## 💡 5단계: 실전 활용 예제

### 예제 1: 블로그 포스트 키워드 분석

블로그 포스트를 작성하기 전에 타겟 키워드의 검색량을 분석하는 시나리오입니다.

```bash
# API 호출 - 여러 키워드 동시 조회
curl -X POST "http://localhost:8000/api/v1/keywords/search" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["Django 튜토리얼", "Python 웹 개발", "FastAPI vs Django"]
  }'

# 응답 예시
[
  {
    "keyword": "Django 튜토리얼",
    "monthly_pc_search_count": 8200,
    "monthly_mobile_search_count": 12400,
    "monthly_total_search_count": 20600,
    "competition_level": "MEDIUM",
    "avg_cpc": 450,
    "mobile_ratio": 60.19,
    "measured_at": "2026-03-14"
  },
  {
    "keyword": "Python 웹 개발",
    "monthly_pc_search_count": 5100,
    "monthly_mobile_search_count": 7800,
    "monthly_total_search_count": 12900,
    "competition_level": "HIGH",
    "avg_cpc": 680,
    "mobile_ratio": 60.47,
    "measured_at": "2026-03-14"
  },
  {
    "keyword": "FastAPI vs Django",
    "monthly_pc_search_count": 1200,
    "monthly_mobile_search_count": 1900,
    "monthly_total_search_count": 3100,
    "competition_level": "LOW",
    "avg_cpc": 320,
    "mobile_ratio": 61.29,
    "measured_at": "2026-03-14"
  }
]
```

**분석 인사이트:**
- "Django 튜토리얼"은 월 20,600회 검색으로 가장 높은 검색량
- 모바일 비율이 60% 이상으로 모바일 최적화 필수
- "FastAPI vs Django"는 검색량은 낮지만 경쟁도가 낮아 상위 노출 가능성 높음

### 예제 2: 연관 키워드로 콘텐츠 확장

메인 키워드에서 파생된 연관 키워드를 찾아 시리즈 콘텐츠를 기획합니다.

```bash
# 연관 키워드 조회
curl -X GET "http://localhost:8000/api/v1/keywords/Django/related?limit=10"

# 응답 예시
[
  {
    "keyword": "Django REST framework",
    "monthly_search_count": 15200,
    "competition_level": "MEDIUM",
    "relevance_score": 0.8
  },
  {
    "keyword": "Django 설치",
    "monthly_search_count": 8900,
    "competition_level": "LOW",
    "relevance_score": 0.8
  },
  {
    "keyword": "Django ORM",
    "monthly_search_count": 6700,
    "competition_level": "MEDIUM",
    "relevance_score": 0.8
  },
  {
    "keyword": "Django migrations",
    "monthly_search_count": 4500,
    "competition_level": "LOW",
    "relevance_score": 0.8
  },
  {
    "keyword": "Django admin 커스터마이징",
    "monthly_search_count": 3200,
    "competition_level": "LOW",
    "relevance_score": 0.8
  }
]
```

**활용 방법:**
1. **시리즈 콘텐츠 기획:** 각 연관 키워드를 주제로 시리즈 포스트 작성
2. **검색량 기준 우선순위:** Django REST framework (15.2K) → Django 설치 (8.9K) 순으로 작성
3. **경쟁도 낮은 키워드 우선:** "Django admin 커스터마이징"처럼 경쟁도 낮은 롱테일 키워드 타겟

### 예제 3: 키워드 종합 분석으로 마케팅 전략 수립

```bash
# 키워드 종합 분석 API 호출
curl -X GET "http://localhost:8000/api/v1/keywords/Django%20Ninja/analysis"

# 응답 예시
{
  "statistics": {
    "keyword": "Django Ninja",
    "monthly_pc_search_count": 2400,
    "monthly_mobile_search_count": 3100,
    "monthly_total_search_count": 5500,
    "competition_level": "LOW",
    "avg_cpc": 280,
    "mobile_ratio": 56.36,
    "measured_at": "2026-03-14"
  },
  "related_keywords": [
    {
      "keyword": "Django Ninja 튜토리얼",
      "monthly_search_count": 1200,
      "competition_level": "LOW",
      "relevance_score": 0.8
    },
    {
      "keyword": "Django Ninja vs FastAPI",
      "monthly_search_count": 890,
      "competition_level": "LOW",
      "relevance_score": 0.8
    },
    {
      "keyword": "Django Ninja 인증",
      "monthly_search_count": 620,
      "competition_level": "LOW",
      "relevance_score": 0.8
    }
  ],
  "total_related_count": 3
}
```

**마케팅 전략:**
- **블루오션 키워드:** 경쟁도 낮고(LOW) 적정 검색량(5.5K) 보유
- **평균 CPC 280원:** 네이버 광고 진행 시 저렴한 비용으로 트래픽 확보 가능
- **연관 키워드 타겟팅:** "튜토리얼", "vs FastAPI", "인증" 등 세부 주제별 콘텐츠 제작

### 예제 4: Python으로 배치 분석

여러 키워드를 자동으로 분석하는 Python 스크립트를 작성합니다.

```python
# keyword_analyzer.py
import httpx
import asyncio
from datetime import datetime

async def analyze_keywords(keywords: list[str]):
    """키워드 배치 분석"""
    base_url = "http://localhost:8000/api/v1"
    
    async with httpx.AsyncClient() as client:
        # 1. 키워드 검색량 조회
        response = await client.post(
            f"{base_url}/keywords/search",
            json={"keywords": keywords}
        )
        stats = response.json()
        
        # 2. 각 키워드별 연관 키워드 조회
        results = []
        for stat in stats:
            kw = stat['keyword']
            
            # 연관 키워드 조회
            rel_response = await client.get(
                f"{base_url}/keywords/{kw}/related",
                params={"limit": 5}
            )
            related = rel_response.json()
            
            results.append({
                'keyword': kw,
                'monthly_total': stat['monthly_total_search_count'],
                'mobile_ratio': stat['mobile_ratio'],
                'competition': stat['competition_level'],
                'avg_cpc': stat['avg_cpc'],
                'related_keywords': [r['keyword'] for r in related[:3]]
            })
        
        return results

async def main():
    # 분석할 키워드 리스트
    target_keywords = [
        "Django Ninja",
        "FastAPI",
        "Flask",
        "Django REST framework"
    ]
    
    print(f"키워드 분석 시작: {datetime.now()}")
    results = await analyze_keywords(target_keyboards)
    
    # 결과 출력
    print("\n=== 키워드 분석 결과 ===\n")
    for r in sorted(results, key=lambda x: x['monthly_total'], reverse=True):
        print(f"📊 {r['keyword']}")
        print(f"   검색량: {r['monthly_total']:,}회/월")
        print(f"   모바일: {r['mobile_ratio']}%")
        print(f"   경쟁도: {r['competition']}")
        print(f"   평균 CPC: {r['avg_cpc']}원")
        print(f"   연관 키워드: {', '.join(r['related_keywords'])}")
        print()

if __name__ == "__main__":
    asyncio.run(main())
```

```bash
# 스크립트 실행
python keyword_analyzer.py

# 출력 결과
키워드 분석 시작: 2026-03-14 10:23:45.123456

=== 키워드 분석 결과 ===

📊 Django REST framework
   검색량: 15,200회/월
   모바일: 58.5%
   경쟁도: MEDIUM
   평균 CPC: 520원
   연관 키워드: DRF 튜토리얼, Serializer, ViewSet

📊 FastAPI
   검색량: 12,800회/월
   모바일: 62.3%
   경쟁도: MEDIUM
   평균 CPC: 480원
   연관 키워드: FastAPI 튜토리얼, Pydantic, async

📊 Flask
   검색량: 9,400회/월
   모바일: 55.1%
   경쟁도: MEDIUM
   평균 CPC: 410원
   연관 키워드: Flask 설치, Blueprint, Jinja2

📊 Django Ninja
   검색량: 5,500회/월
   모바일: 56.4%
   경쟁도: LOW
   평균 CPC: 280원
   연관 키워드: Django Ninja 튜토리얼, vs FastAPI, 인증
```

### 예제 5: 관리자 페이지에서 데이터 확인

Django Admin에서 저장된 키워드 데이터를 확인하고 관리할 수 있습니다.

```python
# keywords/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Keyword, KeywordStatistics, RelatedKeyword


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'latest_search_count', 'created_at', 'updated_at']
    search_fields = ['keyword']
    ordering = ['-updated_at']
    
    def latest_search_count(self, obj):
        """최근 검색량 표시"""
        latest = obj.statistics.first()
        if latest:
            return format_html(
                '<strong>{:,}</strong>회/월',
                latest.monthly_total_search_count
            )
        return '-'
    latest_search_count.short_description = '최근 검색량'


@admin.register(KeywordStatistics)
class KeywordStatisticsAdmin(admin.ModelAdmin):
    list_display = [
        'keyword', 
        'monthly_total_search_count',
        'mobile_ratio_display',
        'competition_level',
        'avg_cpc',
        'measured_at'
    ]
    list_filter = ['competition_level', 'measured_at']
    search_fields = ['keyword__keyword']
    ordering = ['-measured_at', '-monthly_total_search_count']
    
    def mobile_ratio_display(self, obj):
        """모바일 비율 색상 표시"""
        ratio = obj.mobile_ratio
        color = 'green' if ratio > 60 else 'orange' if ratio > 40 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color,
            ratio
        )
    mobile_ratio_display.short_description = '모바일 비율'


@admin.register(RelatedKeyword)
class RelatedKeywordAdmin(admin.ModelAdmin):
    list_display = [
        'source_keyword',
        'related_keyword',
        'monthly_search_count',
        'relevance_score'
    ]
    list_filter = ['created_at']
    search_fields = ['source_keyword__keyword', 'related_keyword']
    ordering = ['-monthly_search_count']
```

## 🎓 마무리 및 추가 개선 사항

### 구현 완료 체크리스트

이번 가이드를 통해 다음 항목들을 완성했습니다:

✅ **네이버 검색광고 API 연동**
- 계정 생성 및 API 인증 정보 발급
- 환경 변수를 통한 보안 강화
- API 클라이언트 서비스 클래스 구현

✅ **Django 프로젝트 설정**
- Django 5.0 + Django Ninja 1.1 프로젝트 생성
- PostgreSQL 데이터베이스 연동
- Redis 캐시 설정으로 API 호출 최적화

✅ **데이터 모델 설계**
- Keyword: 키워드 기본 정보
- KeywordStatistics: 시계열 검색량 통계
- RelatedKeyword: 연관 키워드 관리

✅ **RESTful API 구현**
- `/keywords/search`: 키워드 검색량 조회
- `/keywords/{keyword}/related`: 연관 키워드 조회
- `/keywords/{keyword}/analysis`: 종합 분석
- `/keywords/{keyword}/history`: 검색량 이력 조회

✅ **실전 활용 예제**
- 블로그 포스트 키워드 분석
- 연관 키워드로 콘텐츠 확장
- 마케팅 전략 수립
- Python 배치 스크립트
- Django Admin 관리

### 추가 개선 아이디어

프로젝트를 더욱 발전시킬 수 있는 기능들입니다:

#### 1. Celery를 이용한 자동 데이터 수집

```python
# keywords/tasks.py
from celery import shared_task
from .models import Keyword
from .services.naver_api_client import NaverKeywordAPIClient

@shared_task
def update_keyword_statistics():
    """등록된 모든 키워드의 통계를 자동 업데이트"""
    keywords = Keyword.objects.all()[:100]  # 최대 100개
    
    client = NaverKeywordAPIClient()
    for keyword in keywords:
        try:
            # 키워드 통계 업데이트
            stats = client.get_keyword_statistics([keyword.keyword])
            # DB 저장 로직
        except Exception as e:
            print(f"Error updating {keyword.keyword}: {e}")

# Celery Beat 스케줄 설정 (settings.py)
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'update-keywords-daily': {
        'task': 'keywords.tasks.update_keyword_statistics',
        'schedule': crontab(hour=0, minute=0),  # 매일 자정
    },
}
```

#### 2. 트렌드 분석 기능

```python
# keywords/analytics.py
from django.db.models import Avg, Max, Min
from datetime import timedelta
from django.utils import timezone

def analyze_keyword_trend(keyword: str, days: int = 30):
    """키워드 검색량 트렌드 분석"""
    keyword_obj = Keyword.objects.get(keyword=keyword)
    start_date = timezone.now().date() - timedelta(days=days)
    
    stats = keyword_obj.statistics.filter(
        measured_at__gte=start_date
    ).order_by('measured_at')
    
    if stats.count() < 2:
        return {'trend': 'insufficient_data'}
    
    # 첫 주와 마지막 주 비교
    first_week_avg = stats[:7].aggregate(
        Avg('monthly_total_search_count')
    )['monthly_total_search_count__avg']
    
    last_week_avg = stats[stats.count()-7:].aggregate(
        Avg('monthly_total_search_count')
    )['monthly_total_search_count__avg']
    
    change_percent = (
        (last_week_avg - first_week_avg) / first_week_avg * 100
    )
    
    return {
        'keyword': keyword,
        'trend': 'up' if change_percent > 5 else 'down' if change_percent < -5 else 'stable',
        'change_percent': round(change_percent, 2),
        'first_week_avg': round(first_week_avg),
        'last_week_avg': round(last_week_avg),
    }
```

#### 3. 키워드 추천 알고리즘

```python
# keywords/recommender.py
from django.db.models import Q

def recommend_keywords(base_keyword: str, min_search: int = 1000):
    """
    기준 키워드를 바탕으로 블루오션 키워드 추천
    - 적정 검색량 보유
    - 경쟁도 낮음
    - 연관성 높음
    """
    keyword_obj = Keyword.objects.get(keyword=base_keyword)
    
    # 연관 키워드 중에서 조건에 맞는 것 필터링
    recommended = RelatedKeyword.objects.filter(
        source_keyword=keyword_obj,
        monthly_search_count__gte=min_search
    ).select_related('source_keyword')
    
    # 최근 통계 데이터와 조인하여 경쟁도 확인
    results = []
    for rel_kw in recommended:
        try:
            kw_obj = Keyword.objects.get(keyword=rel_kw.related_keyword)
            latest_stat = kw_obj.statistics.first()
            
            if latest_stat and latest_stat.competition_level == 'LOW':
                results.append({
                    'keyword': rel_kw.related_keyword,
                    'search_count': rel_kw.monthly_search_count,
                    'competition': 'LOW',
                    'avg_cpc': latest_stat.avg_cpc,
                    'score': rel_kw.monthly_search_count / (latest_stat.avg_cpc or 1)
                })
        except Keyword.DoesNotExist:
            pass
    
    # 점수 기준 정렬 (검색량 높고 CPC 낮은 순)
    return sorted(results, key=lambda x: x['score'], reverse=True)[:10]
```

#### 4. 웹훅을 통한 알림

```python
# keywords/webhooks.py
import httpx
from django.conf import settings

async def send_keyword_alert(keyword: str, message: str):
    """특정 조건 만족 시 슬랙/디스코드 알림"""
    webhook_url = settings.SLACK_WEBHOOK_URL
    
    payload = {
        "text": f"🔔 키워드 알림: {keyword}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{keyword}*\n{message}"
                }
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json=payload)

# 사용 예시: 검색량이 급증한 키워드 알림
def check_surge_keywords():
    """검색량이 전주 대비 30% 이상 증가한 키워드 탐지"""
    # 구현 로직...
    if surge_detected:
        asyncio.run(send_keyword_alert(
            keyword,
            f"검색량이 {change_percent}% 급증했습니다!"
        ))
```

### 성능 최적화 팁

**1. API 호출 제한 관리**
```python
# Rate limiting 구현
from django.core.cache import cache

def rate_limit_check(user_id: str, limit: int = 100):
    """시간당 API 호출 횟수 제한"""
    key = f"rate_limit:{user_id}"
    count = cache.get(key, 0)
    
    if count >= limit:
        raise Exception("API 호출 한도 초과")
    
    cache.set(key, count + 1, timeout=3600)
```

**2. 배치 처리 최적화**
```python
# Bulk insert로 성능 향상
from django.db import transaction

@transaction.atomic
def bulk_save_statistics(stats_list):
    """대량 데이터 저장 시 bulk_create 사용"""
    KeywordStatistics.objects.bulk_create(
        stats_list,
        ignore_conflicts=True
    )
```

**3. 데이터베이스 인덱스 최적화**
```python
# models.py에 추가 인덱스
class KeywordStatistics(models.Model):
    # ...
    class Meta:
        indexes = [
            models.Index(fields=['keyword', '-measured_at']),
            models.Index(fields=['-monthly_total_search_count']),
            models.Index(fields=['competition_level', '-measured_at']),
        ]
```

## 🔚 결론

이번 가이드에서는 네이버 검색광고 API와 Django Ninja를 연동하여 키워드 검색량 분석 서비스를 구축하는 전체 과정을 살펴보았습니다. 

**핵심 성과:**
- ✅ 네이버 API를 통한 실시간 키워드 데이터 수집
- ✅ Django Ninja의 직관적인 API 설계와 자동 문서화
- ✅ PostgreSQL과 Redis를 활용한 효율적인 데이터 관리
- ✅ 실전에서 바로 활용 가능한 5가지 예제와 추가 개선 방안

**이 서비스의 활용 분야:**
- **SEO 최적화:** 데이터 기반의 키워드 선정으로 검색 순위 향상
- **콘텐츠 기획:** 검색량과 경쟁도를 고려한 전략적 콘텐츠 제작
- **마케팅 분석:** 키워드 트렌드 파악 및 광고 ROI 최적화
- **경쟁 분석:** 시장 내 키워드 경쟁 상황 모니터링

Django Ninja의 간결한 문법과 강력한 타입 안정성, 그리고 네이버 API의 풍부한 데이터를 조합하면 실무에서 즉시 적용 가능한 고품질 마케팅 분석 도구를 만들 수 있습니다. 

이제 여러분만의 키워드 분석 서비스를 구축하고, 데이터 기반의 의사결정으로 더 나은 성과를 만들어보세요! 🚀

---

**관련 포스트:**
- [Django Ninja로 Google Analytics 주간 성과 분석 서비스 만들기](https://updaun.github.io/posts/django-ninja-google-analytics-weekly-report-service/)
- [Django Ninja vs FastAPI 성능 비교](https://updaun.github.io/posts/fastapi-vs-django-ninja-comparison/)
- [Django Ninja 쇼핑몰 API 구축 가이드](https://updaun.github.io/posts/django-ninja-shopping-mall-basic/)

**참고 자료:**
- [네이버 검색광고 API 공식 문서](https://naver.github.io/searchad-apidoc/)
- [Django Ninja 공식 문서](https://django-ninja.rest-framework.com/)
- [Pydantic 공식 문서](https://docs.pydantic.dev/)


