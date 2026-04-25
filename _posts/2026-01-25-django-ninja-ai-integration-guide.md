---
layout: post
title: "Django Ninja로 AI API 서버 구축하기 - OpenAI 통합 실전 가이드"
date: 2026-01-25
categories: [Django, AI, API]
tags: [django-ninja, openai, api, python, ai-integration]
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-01-25-django-ninja-ai-integration-guide.webp"
---

## 서론

최근 AI 기술의 발전으로 많은 웹 애플리케이션에서 AI 기능을 통합하는 것이 필수가 되었습니다. Django는 강력한 웹 프레임워크지만, REST API 개발에 있어서는 Django REST Framework(DRF)의 복잡성이 부담스러울 수 있습니다. 이때 Django Ninja가 훌륭한 대안이 됩니다.

Django Ninja는 FastAPI에서 영감을 받아 만들어진 프레임워크로, 타입 힌트 기반의 직관적인 API 개발을 가능하게 합니다. 특히 AI API를 구축할 때는 빠른 프로토타이핑과 명확한 데이터 검증이 중요한데, Django Ninja는 이 두 가지를 완벽하게 지원합니다.

이 가이드에서는 Django Ninja를 사용하여 OpenAI API를 통합하고, 실용적인 AI 기능을 제공하는 API 서버를 구축하는 전체 과정을 다룹니다.

## Django Ninja 프로젝트 설정

먼저 Django Ninja 프로젝트를 설정하고 필요한 패키지를 설치합니다.

### 필수 패키지 설치

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Django Ninja 및 OpenAI 패키지 설치
pip install django django-ninja openai python-dotenv
```

### Django 프로젝트 초기화

```bash
# Django 프로젝트 생성
django-admin startproject ai_project .
python manage.py startapp ai_api

# 마이그레이션 실행
python manage.py migrate
```

### 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하여 API 키를 안전하게 관리합니다.

```env
# .env
OPENAI_API_KEY=sk-your-api-key-here
DEBUG=True
SECRET_KEY=your-django-secret-key
```

### settings.py 설정

```python
# ai_project/settings.py
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ai_api',  # 우리가 만든 앱
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

ROOT_URLCONF = 'ai_project.urls'

# OpenAI 설정
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
```

이제 기본적인 Django 프로젝트 설정이 완료되었습니다. Django Ninja의 강점은 복잡한 설정 없이도 즉시 API 개발을 시작할 수 있다는 점입니다.

## OpenAI 클라이언트 통합

OpenAI API를 Django 프로젝트에 통합하기 위해 재사용 가능한 서비스 레이어를 구축합니다.

### AI 서비스 모듈 생성

`ai_api/services.py` 파일을 생성하여 OpenAI 클라이언트를 관리합니다.

```python
# ai_api/services.py
from openai import OpenAI
from django.conf import settings
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AIService:
    """OpenAI API를 관리하는 서비스 클래스"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def generate_text(
        self,
        prompt: str,
        model: str = "gpt-4",
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        텍스트 생성 API
        
        Args:
            prompt: 사용자 입력 프롬프트
            model: 사용할 GPT 모델
            max_tokens: 최대 토큰 수
            temperature: 생성 다양성 (0-2)
        
        Returns:
            생성된 텍스트와 메타데이터
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return {
                "text": response.choices[0].message.content,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "finish_reason": response.choices[0].finish_reason
            }
        
        except Exception as e:
            logger.error(f"OpenAI API Error: {str(e)}")
            raise
    
    def analyze_image(
        self,
        image_url: str,
        prompt: str = "What's in this image?"
    ) -> Dict[str, Any]:
        """
        이미지 분석 API (GPT-4 Vision)
        
        Args:
            image_url: 분석할 이미지 URL
            prompt: 분석 요청 프롬프트
        
        Returns:
            이미지 분석 결과
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                max_tokens=500
            )
            
            return {
                "analysis": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        
        except Exception as e:
            logger.error(f"Image Analysis Error: {str(e)}")
            raise
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        텍스트 임베딩 생성
        
        Args:
            texts: 임베딩할 텍스트 리스트
        
        Returns:
            임베딩 벡터 리스트
        """
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            
            return [item.embedding for item in response.data]
        
        except Exception as e:
            logger.error(f"Embedding Error: {str(e)}")
            raise

# 싱글톤 인스턴스
ai_service = AIService()
```

이 서비스 레이어는 Django Ninja API 엔드포인트와 OpenAI API 사이의 중간 계층 역할을 합니다. 로깅, 에러 핸들링, 그리고 재사용성을 제공합니다.

## Django Ninja API 엔드포인트 구현

이제 Django Ninja를 사용하여 실제 API 엔드포인트를 구현합니다.

### 스키마 정의

먼저 요청과 응답에 사용할 스키마를 정의합니다.

```python
# ai_api/schemas.py
from ninja import Schema
from typing import Optional, List, Dict

class TextGenerationRequest(Schema):
    """텍스트 생성 요청 스키마"""
    prompt: str
    model: str = "gpt-4"
    max_tokens: int = 1000
    temperature: float = 0.7
    
    class Config:
        schema_extra = {
            "example": {
                "prompt": "Python으로 간단한 웹 스크래퍼를 만드는 방법을 설명해주세요.",
                "model": "gpt-4",
                "max_tokens": 1000,
                "temperature": 0.7
            }
        }

class TextGenerationResponse(Schema):
    """텍스트 생성 응답 스키마"""
    text: str
    model: str
    usage: Dict[str, int]
    finish_reason: str

class ImageAnalysisRequest(Schema):
    """이미지 분석 요청 스키마"""
    image_url: str
    prompt: str = "What's in this image?"
    
    class Config:
        schema_extra = {
            "example": {
                "image_url": "https://example.com/image.jpg",
                "prompt": "이 이미지에서 어떤 감정을 느낄 수 있나요?"
            }
        }

class ImageAnalysisResponse(Schema):
    """이미지 분석 응답 스키마"""
    analysis: str
    usage: Dict[str, int]

class EmbeddingRequest(Schema):
    """임베딩 생성 요청 스키마"""
    texts: List[str]
    
    class Config:
        schema_extra = {
            "example": {
                "texts": [
                    "Django는 Python 웹 프레임워크입니다.",
                    "FastAPI는 빠른 API 개발에 적합합니다."
                ]
            }
        }

class EmbeddingResponse(Schema):
    """임베딩 생성 응답 스키마"""
    embeddings: List[List[float]]
    dimension: int
    count: int

class ErrorResponse(Schema):
    """에러 응답 스키마"""
    detail: str
    error_code: Optional[str] = None
```

### API 라우터 구현

```python
# ai_api/api.py
from ninja import NinjaAPI, Router
from typing import List
import logging

from .schemas import (
    TextGenerationRequest, TextGenerationResponse,
    ImageAnalysisRequest, ImageAnalysisResponse,
    EmbeddingRequest, EmbeddingResponse,
    ErrorResponse
)
from .services import ai_service

logger = logging.getLogger(__name__)

# NinjaAPI 인스턴스 생성
api = NinjaAPI(
    title="AI API Server",
    version="1.0.0",
    description="Django Ninja를 사용한 OpenAI 통합 API 서버"
)

# AI 라우터 생성
ai_router = Router(tags=["AI"])

@ai_router.post(
    "/generate-text",
    response={200: TextGenerationResponse, 500: ErrorResponse},
    summary="텍스트 생성",
    description="GPT 모델을 사용하여 텍스트를 생성합니다."
)
def generate_text(request, payload: TextGenerationRequest):
    """
    프롬프트를 기반으로 AI 텍스트를 생성합니다.
    
    - **prompt**: 생성할 텍스트에 대한 프롬프트
    - **model**: 사용할 GPT 모델 (기본값: gpt-4)
    - **max_tokens**: 생성할 최대 토큰 수
    - **temperature**: 생성 다양성 (0-2, 기본값: 0.7)
    """
    try:
        result = ai_service.generate_text(
            prompt=payload.prompt,
            model=payload.model,
            max_tokens=payload.max_tokens,
            temperature=payload.temperature
        )
        return 200, result
    except Exception as e:
        logger.error(f"Text generation failed: {str(e)}")
        return 500, {"detail": str(e), "error_code": "GENERATION_ERROR"}

@ai_router.post(
    "/analyze-image",
    response={200: ImageAnalysisResponse, 500: ErrorResponse},
    summary="이미지 분석",
    description="GPT-4 Vision을 사용하여 이미지를 분석합니다."
)
def analyze_image(request, payload: ImageAnalysisRequest):
    """
    이미지 URL을 받아서 내용을 분석합니다.
    
    - **image_url**: 분석할 이미지의 공개 URL
    - **prompt**: 분석 요청 내용 (선택사항)
    """
    try:
        result = ai_service.analyze_image(
            image_url=payload.image_url,
            prompt=payload.prompt
        )
        return 200, result
    except Exception as e:
        logger.error(f"Image analysis failed: {str(e)}")
        return 500, {"detail": str(e), "error_code": "ANALYSIS_ERROR"}

@ai_router.post(
    "/create-embeddings",
    response={200: EmbeddingResponse, 500: ErrorResponse},
    summary="텍스트 임베딩 생성",
    description="텍스트를 벡터로 변환합니다."
)
def create_embeddings(request, payload: EmbeddingRequest):
    """
    텍스트 리스트를 임베딩 벡터로 변환합니다.
    
    - **texts**: 임베딩할 텍스트 리스트
    """
    try:
        embeddings = ai_service.create_embeddings(payload.texts)
        return 200, {
            "embeddings": embeddings,
            "dimension": len(embeddings[0]) if embeddings else 0,
            "count": len(embeddings)
        }
    except Exception as e:
        logger.error(f"Embedding creation failed: {str(e)}")
        return 500, {"detail": str(e), "error_code": "EMBEDDING_ERROR"}

@ai_router.get(
    "/health",
    summary="헬스 체크",
    description="API 서버 상태를 확인합니다."
)
def health_check(request):
    """API 서버가 정상적으로 작동하는지 확인합니다."""
    return {"status": "healthy", "service": "AI API"}

# 라우터 등록
api.add_router("/ai", ai_router)
```

### URL 설정

```python
# ai_project/urls.py
from django.contrib import admin
from django.urls import path
from ai_api.api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),  # Django Ninja API
]
```

이제 서버를 실행하면 `/api/docs`에서 자동 생성된 Swagger 문서를 확인할 수 있습니다!

## 스트리밍 응답 구현

AI 응답을 실시간으로 스트리밍하면 사용자 경험을 크게 향상시킬 수 있습니다. Django Ninja에서 스트리밍 응답을 구현하는 방법을 알아봅니다.

### 스트리밍 서비스 추가

```python
# ai_api/services.py에 추가
from django.http import StreamingHttpResponse
import json

class AIService:
    # ... 기존 코드 ...
    
    def stream_text_generation(
        self,
        prompt: str,
        model: str = "gpt-4",
        temperature: float = 0.7
    ):
        """
        스트리밍 방식으로 텍스트 생성
        
        Args:
            prompt: 사용자 프롬프트
            model: GPT 모델
            temperature: 생성 다양성
        
        Yields:
            텍스트 청크
        """
        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                stream=True  # 스트리밍 활성화
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    yield f"data: {json.dumps({'content': content})}\n\n"
            
            yield "data: [DONE]\n\n"
        
        except Exception as e:
            logger.error(f"Streaming Error: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
```

### 스트리밍 엔드포인트 추가

```python
# ai_api/api.py에 추가
from django.http import StreamingHttpResponse

@ai_router.post(
    "/stream-text",
    summary="텍스트 스트리밍 생성",
    description="실시간으로 텍스트를 스트리밍합니다."
)
def stream_text(request, payload: TextGenerationRequest):
    """
    Server-Sent Events (SSE) 방식으로 텍스트를 스트리밍합니다.
    """
    response = StreamingHttpResponse(
        ai_service.stream_text_generation(
            prompt=payload.prompt,
            model=payload.model,
            temperature=payload.temperature
        ),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
```

### 클라이언트 사용 예제

```javascript
// JavaScript에서 스트리밍 응답 처리
async function streamAIResponse(prompt) {
    const response = await fetch('/api/ai/stream-text', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            prompt: prompt,
            model: 'gpt-4',
            temperature: 0.7
        })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data === '[DONE]') {
                    console.log('스트리밍 완료');
                    return;
                }
                
                try {
                    const json = JSON.parse(data);
                    if (json.content) {
                        // 실시간으로 텍스트 표시
                        document.getElementById('output').innerText += json.content;
                    }
                } catch (e) {
                    console.error('JSON 파싱 에러:', e);
                }
            }
        }
    }
}

// 사용 예제
streamAIResponse('Python으로 간단한 웹 서버를 만드는 방법을 설명해주세요.');
```

스트리밍 방식을 사용하면 사용자가 전체 응답을 기다리지 않고 즉시 결과를 확인할 수 있어 훨씬 더 반응성 있는 애플리케이션을 만들 수 있습니다.

## 에러 핸들링 및 비용 최적화

프로덕션 환경에서는 견고한 에러 핸들링과 비용 최적화가 필수적입니다.

### 커스텀 예외 처리

```python
# ai_api/exceptions.py
class AIServiceException(Exception):
    """AI 서비스 기본 예외"""
    pass

class RateLimitException(AIServiceException):
    """API 요청 제한 초과"""
    pass

class InvalidRequestException(AIServiceException):
    """잘못된 요청"""
    pass

class InsufficientQuotaException(AIServiceException):
    """할당량 부족"""
    pass
```

### 에러 핸들러 등록

```python
# ai_api/api.py에 추가
from ninja import NinjaAPI
from ninja.errors import ValidationError
from .exceptions import (
    AIServiceException,
    RateLimitException,
    InsufficientQuotaException
)

@api.exception_handler(RateLimitException)
def handle_rate_limit(request, exc):
    return api.create_response(
        request,
        {"detail": "API 요청 제한을 초과했습니다. 잠시 후 다시 시도해주세요."},
        status=429
    )

@api.exception_handler(InsufficientQuotaException)
def handle_quota_error(request, exc):
    return api.create_response(
        request,
        {"detail": "API 할당량이 부족합니다. 관리자에게 문의하세요."},
        status=402
    )

@api.exception_handler(ValidationError)
def handle_validation_error(request, exc):
    return api.create_response(
        request,
        {"detail": "입력 데이터가 올바르지 않습니다.", "errors": exc.errors},
        status=422
    )

@api.exception_handler(AIServiceException)
def handle_ai_service_error(request, exc):
    logger.error(f"AI Service Error: {str(exc)}")
    return api.create_response(
        request,
        {"detail": "AI 서비스 처리 중 오류가 발생했습니다."},
        status=500
    )
```

### 요청 제한 (Rate Limiting)

```python
# ai_api/middleware.py
from django.core.cache import cache
from django.http import JsonResponse
import time

class RateLimitMiddleware:
    """API 요청 제한 미들웨어"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limit = 100  # 분당 요청 수
        self.window = 60  # 시간 윈도우 (초)
    
    def __call__(self, request):
        if request.path.startswith('/api/ai/'):
            # IP 기반 요청 제한
            client_ip = self.get_client_ip(request)
            cache_key = f'rate_limit:{client_ip}'
            
            requests = cache.get(cache_key, [])
            now = time.time()
            
            # 시간 윈도우 내의 요청만 유지
            requests = [req_time for req_time in requests 
                       if now - req_time < self.window]
            
            if len(requests) >= self.rate_limit:
                return JsonResponse(
                    {'detail': '요청 제한을 초과했습니다.'},
                    status=429
                )
            
            requests.append(now)
            cache.set(cache_key, requests, self.window)
        
        return self.get_response(request)
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

### 비용 추적 및 모니터링

```python
# ai_api/models.py
from django.db import models
from django.contrib.auth.models import User

class APIUsage(models.Model):
    """API 사용량 추적 모델"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    endpoint = models.CharField(max_length=100)
    model = models.CharField(max_length=50)
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['endpoint', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.endpoint} - {self.total_tokens} tokens"

# ai_api/services.py에 추가
class AIService:
    # 모델별 가격 (1000 토큰당 USD)
    PRICING = {
        'gpt-4': {'input': 0.03, 'output': 0.06},
        'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
        'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
    }
    
    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """토큰 사용량 기반 비용 계산"""
        pricing = self.PRICING.get(model, self.PRICING['gpt-4'])
        
        input_cost = (prompt_tokens / 1000) * pricing['input']
        output_cost = (completion_tokens / 1000) * pricing['output']
        
        return input_cost + output_cost
    
    def log_usage(self, endpoint: str, model: str, usage: dict, user=None):
        """API 사용량 로깅"""
        from .models import APIUsage
        
        cost = self.calculate_cost(
            model,
            usage['prompt_tokens'],
            usage['completion_tokens']
        )
        
        APIUsage.objects.create(
            user=user,
            endpoint=endpoint,
            model=model,
            prompt_tokens=usage['prompt_tokens'],
            completion_tokens=usage['completion_tokens'],
            total_tokens=usage['total_tokens'],
            estimated_cost=cost
        )
        
        return cost
```

### 캐싱 전략

```python
# ai_api/services.py에 추가
from django.core.cache import cache
import hashlib

class AIService:
    # ... 기존 코드 ...
    
    def get_cached_or_generate(
        self,
        prompt: str,
        model: str = "gpt-4",
        **kwargs
    ) -> Dict[str, Any]:
        """
        캐시를 활용한 텍스트 생성
        동일한 요청은 캐시된 결과 반환
        """
        # 캐시 키 생성
        cache_key = self._generate_cache_key(prompt, model, kwargs)
        
        # 캐시 확인
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for prompt: {prompt[:50]}...")
            return cached_result
        
        # 캐시 미스 - API 호출
        result = self.generate_text(prompt, model, **kwargs)
        
        # 결과 캐싱 (24시간)
        cache.set(cache_key, result, 60 * 60 * 24)
        
        return result
    
    def _generate_cache_key(self, prompt: str, model: str, params: dict) -> str:
        """캐시 키 생성"""
        key_string = f"{prompt}:{model}:{sorted(params.items())}"
        return f"ai_cache:{hashlib.md5(key_string.encode()).hexdigest()}"
```

이러한 최적화를 통해 API 비용을 크게 절감하고 안정적인 서비스를 제공할 수 있습니다.

## 테스트 및 배포

프로덕션 배포 전 철저한 테스트가 필요합니다.

### 단위 테스트

```python
# ai_api/tests.py
from django.test import TestCase
from unittest.mock import patch, MagicMock
from .services import AIService
from .schemas import TextGenerationRequest

class AIServiceTestCase(TestCase):
    """AI 서비스 단위 테스트"""
    
    def setUp(self):
        self.ai_service = AIService()
    
    @patch('openai.OpenAI')
    def test_generate_text_success(self, mock_openai):
        """텍스트 생성 성공 테스트"""
        # Mock 설정
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.model = "gpt-4"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        mock_response.choices[0].finish_reason = "stop"
        
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        # 테스트 실행
        result = self.ai_service.generate_text("Test prompt")
        
        # 검증
        self.assertEqual(result['text'], "Test response")
        self.assertEqual(result['model'], "gpt-4")
        self.assertEqual(result['usage']['total_tokens'], 30)
    
    def test_cache_key_generation(self):
        """캐시 키 생성 테스트"""
        key1 = self.ai_service._generate_cache_key("prompt", "gpt-4", {})
        key2 = self.ai_service._generate_cache_key("prompt", "gpt-4", {})
        key3 = self.ai_service._generate_cache_key("different", "gpt-4", {})
        
        self.assertEqual(key1, key2)
        self.assertNotEqual(key1, key3)
    
    def test_cost_calculation(self):
        """비용 계산 테스트"""
        cost = self.ai_service.calculate_cost("gpt-4", 1000, 1000)
        expected = (1000/1000 * 0.03) + (1000/1000 * 0.06)
        self.assertEqual(cost, expected)

class APIEndpointTestCase(TestCase):
    """API 엔드포인트 통합 테스트"""
    
    @patch('ai_api.services.ai_service.generate_text')
    def test_generate_text_endpoint(self, mock_generate):
        """텍스트 생성 엔드포인트 테스트"""
        mock_generate.return_value = {
            'text': 'Generated text',
            'model': 'gpt-4',
            'usage': {'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30},
            'finish_reason': 'stop'
        }
        
        response = self.client.post(
            '/api/ai/generate-text',
            data={
                'prompt': 'Test prompt',
                'model': 'gpt-4',
                'max_tokens': 1000,
                'temperature': 0.7
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['text'], 'Generated text')
    
    def test_health_check(self):
        """헬스 체크 엔드포인트 테스트"""
        response = self.client.get('/api/ai/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'healthy')

# 테스트 실행
# python manage.py test ai_api
```

### Docker 배포 설정

```dockerfile
# Dockerfile
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트
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
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "ai_project.wsgi:application"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    command: gunicorn ai_project.wsgi:application --bind 0.0.0.0:8000 --workers 4
    volumes:
      - .:/app
      - static_volume:/app/staticfiles
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=ai_api
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/app/staticfiles
    ports:
      - "80:80"
    depends_on:
      - web

volumes:
  postgres_data:
  static_volume:
```

### requirements.txt

```txt
Django==5.0.1
django-ninja==1.1.0
openai==1.10.0
python-dotenv==1.0.0
gunicorn==21.2.0
psycopg2-binary==2.9.9
redis==5.0.1
django-redis==5.4.0
```

### 프로덕션 설정

```python
# ai_project/settings_prod.py
from .settings import *

DEBUG = False
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']

# 캐시 설정
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# 로깅 설정
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
            'filename': '/var/log/django/ai_api.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}

# 보안 설정
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
```

### 배포 스크립트

```bash
#!/bin/bash
# deploy.sh

echo "🚀 Django Ninja AI API 배포 시작..."

# 환경 변수 로드
source .env

# Docker 이미지 빌드
echo "📦 Docker 이미지 빌드 중..."
docker-compose build

# 데이터베이스 마이그레이션
echo "🗄️ 데이터베이스 마이그레이션..."
docker-compose run --rm web python manage.py migrate

# 정적 파일 수집
echo "📁 정적 파일 수집..."
docker-compose run --rm web python manage.py collectstatic --noinput

# 컨테이너 시작
echo "🎯 서비스 시작..."
docker-compose up -d

echo "✅ 배포 완료!"
echo "API 문서: http://your-domain.com/api/docs"
```

## 결론

Django Ninja를 사용한 AI API 서버 구축의 전체 과정을 살펴보았습니다. 이 가이드에서 다룬 주요 내용을 정리하면:

### 핵심 포인트

1. **Django Ninja의 장점**
   - FastAPI 스타일의 직관적인 API 개발
   - 자동 문서화 (Swagger/OpenAPI)
   - 타입 안정성과 데이터 검증
   - Django 생태계와의 완벽한 통합

2. **AI 통합 베스트 프랙티스**
   - 서비스 레이어 패턴으로 비즈니스 로직 분리
   - 스키마를 통한 명확한 API 계약
   - 스트리밍 응답으로 UX 향상
   - 에러 핸들링과 로깅

3. **프로덕션 준비사항**
   - Rate Limiting으로 서비스 보호
   - 캐싱을 통한 비용 절감
   - 사용량 추적 및 모니터링
   - 컨테이너화 및 배포 자동화

### 다음 단계

이 기본 구조를 바탕으로 다음과 같은 기능을 추가할 수 있습니다:

- **인증 및 권한 관리**: JWT 토큰 기반 인증
- **웹소켓 통합**: 실시간 양방향 통신
- **백그라운드 작업**: Celery를 통한 비동기 처리
- **벡터 데이터베이스**: 임베딩 기반 검색 (Pinecone, Weaviate)
- **멀티모달 AI**: 이미지 생성, 음성 인식 등

### 참고 자료

- [Django Ninja 공식 문서](https://django-ninja.rest-framework.com/)
- [OpenAI API 문서](https://platform.openai.com/docs)
- [Django 공식 문서](https://docs.djangoproject.com/)

Django Ninja와 OpenAI의 조합은 빠르고 확장 가능한 AI 애플리케이션을 구축하는 데 이상적인 선택입니다. 이 가이드가 여러분의 AI 프로젝트에 도움이 되기를 바랍니다!

---

**관련 포스트**
- [Django 5.0/5.1 주요 기능 리뷰]({% post_url 2025-01-17-django-5.0-5.1-major-features-review %})

**태그**: #Django #DjangoNinja #OpenAI #AI #API #Python #WebDevelopment

