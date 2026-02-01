---
layout: post
title: "Django Ninja와 Hugging Face 모델 통합 - 로컬 LLM으로 비용 제로 AI API 구축하기"
date: 2026-01-31
categories: django
author: updaun
image: "/assets/img/posts/2026-01-31-django-ninja-huggingface-integration-guide.webp"
---

# Django Ninja와 Hugging Face 모델 통합 - 로컬 LLM으로 비용 제로 AI API 구축하기

OpenAI나 Anthropic 같은 클라우드 AI 서비스는 강력하지만 API 호출 비용이 빠르게 누적되고, 민감한 데이터를 외부 서버로 전송해야 하며, 인터넷 연결이 필수입니다. Hugging Face의 오픈소스 모델을 사용하면 초기 학습 비용 없이 수백 개의 검증된 모델을 무료로 활용할 수 있고, 서버 내부에서 추론을 실행해 데이터 유출 위험을 차단하며, 한번 다운로드한 모델은 네트워크 없이도 작동합니다. 이 글에서는 Django Ninja를 기반으로 Hugging Face Transformers 라이브러리를 통합하고, 텍스트 생성·감정 분석·번역·요약·질의응답 같은 다양한 NLP 작업을 REST API로 제공하며, GPU 가속·모델 캐싱·배치 처리·비동기 워커 구조까지 실서비스에 필요한 최적화 기법을 단계별로 구현합니다. 단순한 predict 예제를 넘어, 프로덕션 환경에서 안정적으로 운영 가능한 아키텍처와 구체적인 코드를 제공합니다.

## Hugging Face 모델 선택 기준과 추천 모델

Hugging Face Hub에는 50만 개 이상의 모델이 공개되어 있지만, 프로덕션 환경에서는 모델 크기·추론 속도·메모리 사용량·정확도의 균형을 고려해야 합니다. 대형 모델(LLaMA 70B, GPT-NeoX 20B 등)은 정확도가 높지만 추론에 A100 GPU가 필요하고 응답 시간이 수 초에서 수십 초까지 걸려 실시간 API로는 부적합합니다. 반면 경량 모델(DistilBERT, TinyBERT, MobileBERT)은 CPU에서도 100ms 이내 응답이 가능하지만 복잡한 문맥 이해나 창의적 생성에서는 한계가 있습니다. 중형 모델이 실용적인 선택이며, 작업별 추천 모델은 다음과 같습니다. 감정 분석에는 `distilbert-base-uncased-finetuned-sst-2-english` (66M 파라미터, GPU 메모리 300MB)가 일반적이지만 한국어라면 `beomi/kcbert-base` (110M)를 권장합니다. 텍스트 생성은 `gpt2` (124M)가 가장 가볍고 빠르며, 더 나은 품질이 필요하면 `EleutherAI/gpt-neo-1.3B`나 `facebook/opt-1.3b`를 선택합니다. 한국어 생성은 `skt/kogpt2-base-v2`(125M)가 표준입니다. 번역 작업은 `Helsinki-NLP/opus-mt-en-ko`(300M)와 `opus-mt-ko-en`을 조합하고, 요약은 `facebook/bart-large-cnn`(400M)이 영문 뉴스에 강하며, 질의응답은 `deepset/roberta-base-squad2`(125M)가 정확도와 속도가 균형적입니다. 모델 다운로드는 첫 실행 시 자동으로 이루어지며 `~/.cache/huggingface/`에 저장되므로, Docker 환경이라면 이 디렉터리를 볼륨 마운트해 재빌드 시 재다운로드를 방지해야 합니다.

## 아키텍처 설계와 동기·비동기 처리 전략

Hugging Face 모델은 추론 시 CPU나 GPU를 집중적으로 사용하므로, Django의 기본 동기 처리 방식으로는 한 요청이 처리되는 동안 다른 요청이 대기해야 하는 병목이 발생합니다. 프로덕션 환경에서는 동기 API와 비동기 워커를 분리하는 하이브리드 아키텍처가 필요합니다. 클라이언트가 `/api/predict`에 요청을 보내면 Django Ninja는 입력 텍스트를 검증하고 Celery 큐에 작업을 등록한 후 `job_id`를 즉시 반환합니다. Celery 워커는 별도 프로세스에서 Hugging Face 모델을 로드하고 추론을 실행하며, 결과를 Redis나 PostgreSQL에 저장합니다. 클라이언트는 `/api/result/{job_id}`를 폴링하거나 WebSocket으로 완료 알림을 받아 결과를 조회합니다. 간단한 작업(감정 분석 같은 분류)은 응답 시간이 100~300ms로 짧아서 동기 엔드포인트로 제공할 수 있지만, 타임아웃을 5초 정도로 설정해 예외 상황을 대비합니다. 텍스트 생성이나 요약처럼 시간이 오래 걸리는 작업은 반드시 비동기로 처리해야 하며, 배치 처리 기능을 추가해 여러 입력을 한 번에 처리하면 GPU 활용률을 높일 수 있습니다. 모델은 서버 시작 시 메모리에 로드하고 재사용해야 하며, 매 요청마다 로드하면 수 초가 소요되므로 전역 캐시나 Singleton 패턴을 적용합니다. GPU가 있으면 `device=0`으로 설정하고, CPU 전용 환경이라면 `torch.set_num_threads()`로 멀티코어를 활용합니다.

## 의존성 설치와 환경 설정

먼저 필요한 라이브러리를 설치합니다. PyTorch는 CUDA 버전에 따라 설치 명령이 다르므로 [공식 사이트](https://pytorch.org)에서 확인해야 합니다.

```bash
# CUDA 12.1이 있는 경우 (GPU 서버)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# CPU 전용 환경
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Hugging Face와 Django 관련 패키지
pip install transformers accelerate sentencepiece protobuf
pip install django-ninja celery redis django-redis
pip install python-dotenv psycopg2-binary

# 선택 사항: 모델 양자화로 메모리 절약 (고급)
pip install bitsandbytes optimum
```

`settings.py`에 환경 설정을 추가합니다.

```python
# settings.py
import os
from dotenv import load_dotenv

load_dotenv()

# Hugging Face 설정
HUGGINGFACE_CACHE_DIR = os.getenv("HF_HOME", "~/.cache/huggingface")
HUGGINGFACE_MODEL_DEVICE = os.getenv("HF_DEVICE", "cpu")  # "cuda:0" 또는 "cpu"

# 모델별 설정
SENTIMENT_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"
TEXT_GENERATION_MODEL = "gpt2"
TRANSLATION_MODEL_EN_KO = "Helsinki-NLP/opus-mt-en-ko"
SUMMARIZATION_MODEL = "facebook/bart-large-cnn"

# Celery 설정
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "Asia/Seoul"

# Redis 캐시 (모델 결과 캐싱용)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}
```

`.env` 파일을 생성해 민감한 정보를 관리합니다.

```env
# .env
HF_HOME=/app/.cache/huggingface
HF_DEVICE=cuda:0
DJANGO_SECRET_KEY=your-secret-key-here
REDIS_URL=redis://localhost:6379
```

## 모델 매니저 클래스 구현과 Singleton 패턴

Hugging Face 모델은 첫 로드 시 수백 MB에서 수 GB의 가중치 파일을 다운로드하고 메모리에 적재하므로, 매 요청마다 로드하면 성능이 극도로 떨어집니다. Singleton 패턴으로 모델을 한 번만 로드하고 전역에서 재사용하는 `ModelManager` 클래스를 구현합니다.

```python
# ai/model_manager.py
import torch
from transformers import (
    pipeline, 
    AutoTokenizer, 
    AutoModelForSequenceClassification,
    AutoModelForCausalLM,
    AutoModelForSeq2SeqLM
)
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class ModelManager:
    """Singleton 패턴으로 Hugging Face 모델을 관리하는 클래스"""
    
    _instance = None
    _models = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """서버 시작 시 모델 초기화"""
        self.device = settings.HUGGINGFACE_MODEL_DEVICE
        logger.info(f"Initializing models on device: {self.device}")
        
        # GPU 사용 가능 여부 확인
        if self.device.startswith("cuda") and not torch.cuda.is_available():
            logger.warning("CUDA not available, falling back to CPU")
            self.device = "cpu"
        
        # CPU 사용 시 멀티스레딩 최적화
        if self.device == "cpu":
            torch.set_num_threads(4)  # 코어 수에 맞게 조정
    
    def get_sentiment_pipeline(self):
        """감정 분석 파이프라인 반환 (캐싱)"""
        if "sentiment" not in self._models:
            logger.info("Loading sentiment analysis model...")
            self._models["sentiment"] = pipeline(
                "sentiment-analysis",
                model=settings.SENTIMENT_MODEL,
                device=0 if self.device.startswith("cuda") else -1
            )
        return self._models["sentiment"]
    
    def get_text_generation_pipeline(self):
        """텍스트 생성 파이프라인 반환"""
        if "text_generation" not in self._models:
            logger.info("Loading text generation model...")
            self._models["text_generation"] = pipeline(
                "text-generation",
                model=settings.TEXT_GENERATION_MODEL,
                device=0 if self.device.startswith("cuda") else -1,
                max_length=512,
                truncation=True
            )
        return self._models["text_generation"]
    
    def get_translation_pipeline(self, direction="en_to_ko"):
        """번역 파이프라인 반환 (영어→한국어)"""
        key = f"translation_{direction}"
        if key not in self._models:
            logger.info(f"Loading translation model: {direction}")
            model_name = settings.TRANSLATION_MODEL_EN_KO if direction == "en_to_ko" else "Helsinki-NLP/opus-mt-ko-en"
            self._models[key] = pipeline(
                "translation",
                model=model_name,
                device=0 if self.device.startswith("cuda") else -1
            )
        return self._models[key]
    
    def get_summarization_pipeline(self):
        """요약 파이프라인 반환"""
        if "summarization" not in self._models:
            logger.info("Loading summarization model...")
            self._models["summarization"] = pipeline(
                "summarization",
                model=settings.SUMMARIZATION_MODEL,
                device=0 if self.device.startswith("cuda") else -1
            )
        return self._models["summarization"]
    
    def cleanup(self):
        """메모리 정리 (서버 종료 시)"""
        logger.info("Cleaning up models...")
        for name, model in self._models.items():
            del model
        self._models.clear()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

# 전역 인스턴스
model_manager = ModelManager()
```

이 클래스는 `__new__` 메서드를 오버라이드해 항상 같은 인스턴스를 반환하고, 각 모델을 `_models` 딕셔너리에 캐싱합니다. `pipeline` 함수는 Hugging Face의 고수준 API로 토크나이저와 모델을 자동으로 로드하며, `device` 파라미터로 GPU/CPU를 지정합니다. GPU 사용 시 `device=0`(첫 번째 GPU), CPU는 `device=-1`입니다. `max_length`와 `truncation`은 긴 텍스트가 입력될 때 자동으로 잘라서 처리하도록 합니다.

## Django Ninja API 엔드포인트 구현

이제 실제 API를 구현합니다. 먼저 Pydantic 스키마를 정의하고, 각 작업에 대한 엔드포인트를 생성합니다.

```python
# ai/schemas.py
from ninja import Schema
from typing import Optional, List

class SentimentRequest(Schema):
    text: str
    
class SentimentResponse(Schema):
    label: str  # POSITIVE, NEGATIVE
    score: float  # 0.0 ~ 1.0
    
class TextGenerationRequest(Schema):
    prompt: str
    max_length: Optional[int] = 100
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    
class TextGenerationResponse(Schema):
    generated_text: str
    
class TranslationRequest(Schema):
    text: str
    source_lang: str = "en"  # en, ko
    target_lang: str = "ko"  # ko, en
    
class TranslationResponse(Schema):
    translated_text: str
    
class SummarizationRequest(Schema):
    text: str
    max_length: Optional[int] = 130
    min_length: Optional[int] = 30
    
class SummarizationResponse(Schema):
    summary: str
    
class BatchRequest(Schema):
    texts: List[str]
    
class ErrorResponse(Schema):
    error: str
    detail: Optional[str] = None
```

API 라우터를 구현합니다.

```python
# ai/api.py
from ninja import Router
from django.core.cache import cache
from .schemas import (
    SentimentRequest, SentimentResponse,
    TextGenerationRequest, TextGenerationResponse,
    TranslationRequest, TranslationResponse,
    SummarizationRequest, SummarizationResponse,
    ErrorResponse
)
from .model_manager import model_manager
import logging
import hashlib

logger = logging.getLogger(__name__)
router = Router()

def get_cache_key(prefix: str, text: str) -> str:
    """텍스트 해시로 캐시 키 생성"""
    text_hash = hashlib.md5(text.encode()).hexdigest()
    return f"{prefix}:{text_hash}"

@router.post("/sentiment", response={200: SentimentResponse, 400: ErrorResponse})
def analyze_sentiment(request, data: SentimentRequest):
    """감정 분석 API (동기 처리)"""
    try:
        # 캐시 확인 (같은 텍스트는 재계산 안 함)
        cache_key = get_cache_key("sentiment", data.text)
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info("Cache hit for sentiment analysis")
            return cached_result
        
        # 모델 실행
        pipeline = model_manager.get_sentiment_pipeline()
        result = pipeline(data.text)[0]
        
        response = SentimentResponse(
            label=result["label"],
            score=round(result["score"], 4)
        )
        
        # 결과 캐싱 (1시간)
        cache.set(cache_key, response.dict(), timeout=3600)
        
        return response
    except Exception as e:
        logger.error(f"Sentiment analysis error: {str(e)}")
        return 400, ErrorResponse(error="Analysis failed", detail=str(e))

@router.post("/generate", response={200: TextGenerationResponse, 400: ErrorResponse})
def generate_text(request, data: TextGenerationRequest):
    """텍스트 생성 API"""
    try:
        if len(data.prompt) > 500:
            return 400, ErrorResponse(error="Prompt too long", detail="Maximum 500 characters")
        
        pipeline = model_manager.get_text_generation_pipeline()
        result = pipeline(
            data.prompt,
            max_length=data.max_length,
            temperature=data.temperature,
            top_p=data.top_p,
            do_sample=True,
            num_return_sequences=1
        )[0]
        
        return TextGenerationResponse(generated_text=result["generated_text"])
    except Exception as e:
        logger.error(f"Text generation error: {str(e)}")
        return 400, ErrorResponse(error="Generation failed", detail=str(e))

@router.post("/translate", response={200: TranslationResponse, 400: ErrorResponse})
def translate_text(request, data: TranslationRequest):
    """번역 API"""
    try:
        direction = f"{data.source_lang}_to_{data.target_lang}"
        if direction not in ["en_to_ko", "ko_to_en"]:
            return 400, ErrorResponse(error="Invalid language pair")
        
        cache_key = get_cache_key(f"translate_{direction}", data.text)
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        pipeline = model_manager.get_translation_pipeline(direction)
        result = pipeline(data.text)[0]
        
        response = TranslationResponse(translated_text=result["translation_text"])
        cache.set(cache_key, response.dict(), timeout=3600)
        
        return response
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return 400, ErrorResponse(error="Translation failed", detail=str(e))

@router.post("/summarize", response={200: SummarizationResponse, 400: ErrorResponse})
def summarize_text(request, data: SummarizationRequest):
    """텍스트 요약 API"""
    try:
        if len(data.text) < 100:
            return 400, ErrorResponse(error="Text too short for summarization")
        
        pipeline = model_manager.get_summarization_pipeline()
        result = pipeline(
            data.text,
            max_length=data.max_length,
            min_length=data.min_length,
            do_sample=False
        )[0]
        
        return SummarizationResponse(summary=result["summary_text"])
    except Exception as e:
        logger.error(f"Summarization error: {str(e)}")
        return 400, ErrorResponse(error="Summarization failed", detail=str(e))

@router.get("/health")
def health_check(request):
    """헬스 체크 및 모델 상태 확인"""
    return {
        "status": "healthy",
        "models_loaded": list(model_manager._models.keys()),
        "device": model_manager.device
    }
```

메인 URL에 라우터를 등록합니다.

```python
# urls.py
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from ai.api import router as ai_router

api = NinjaAPI(title="Hugging Face AI API", version="1.0.0")
api.add_router("/ai", ai_router)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
```

이제 API를 테스트할 수 있습니다. 서버를 시작하면 `/api/docs`에서 자동 생성된 Swagger 문서를 확인할 수 있습니다.

## Celery를 활용한 비동기 처리와 배치 작업

텍스트 생성이나 긴 문서 요약은 수 초에서 수십 초가 걸릴 수 있으므로, HTTP 요청이 타임아웃되기 전에 비동기로 처리해야 합니다. Celery 워커를 구성하고 작업 큐를 설정합니다.

```python
# celery.py (프로젝트 루트)
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("huggingface_ai")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
```

비동기 작업을 정의합니다.

```python
# ai/tasks.py
from celery import shared_task
from .model_manager import model_manager
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def async_text_generation(self, prompt: str, max_length: int = 100, temperature: float = 0.7):
    """비동기 텍스트 생성 작업"""
    try:
        logger.info(f"Starting async generation for prompt: {prompt[:50]}...")
        pipeline = model_manager.get_text_generation_pipeline()
        result = pipeline(
            prompt,
            max_length=max_length,
            temperature=temperature,
            do_sample=True,
            num_return_sequences=1
        )[0]
        return {
            "status": "completed",
            "generated_text": result["generated_text"]
        }
    except Exception as e:
        logger.error(f"Generation task failed: {str(e)}")
        # 재시도 (최대 3회)
        raise self.retry(exc=e, countdown=5)

@shared_task(bind=True)
def async_summarization(self, text: str, max_length: int = 130, min_length: int = 30):
    """비동기 요약 작업"""
    try:
        logger.info(f"Starting summarization for text length: {len(text)}")
        pipeline = model_manager.get_summarization_pipeline()
        result = pipeline(
            text,
            max_length=max_length,
            min_length=min_length,
            do_sample=False
        )[0]
        return {
            "status": "completed",
            "summary": result["summary_text"]
        }
    except Exception as e:
        logger.error(f"Summarization task failed: {str(e)}")
        return {"status": "failed", "error": str(e)}

@shared_task
def batch_sentiment_analysis(texts: list):
    """배치 감정 분석 (여러 텍스트 한번에 처리)"""
    try:
        logger.info(f"Processing batch of {len(texts)} texts")
        pipeline = model_manager.get_sentiment_pipeline()
        # 파이프라인은 리스트를 받아 병렬 처리
        results = pipeline(texts)
        return {
            "status": "completed",
            "results": [
                {"text": text, "label": r["label"], "score": r["score"]}
                for text, r in zip(texts, results)
            ]
        }
    except Exception as e:
        logger.error(f"Batch analysis failed: {str(e)}")
        return {"status": "failed", "error": str(e)}
```

비동기 API 엔드포인트를 추가합니다.

```python
# ai/api.py에 추가
from .tasks import async_text_generation, async_summarization, batch_sentiment_analysis
from ninja import Schema
from typing import Optional

class AsyncJobRequest(Schema):
    prompt: str
    max_length: Optional[int] = 100
    
class AsyncJobResponse(Schema):
    job_id: str
    status: str
    
class JobResultResponse(Schema):
    job_id: str
    status: str  # PENDING, SUCCESS, FAILURE
    result: Optional[dict] = None
    error: Optional[str] = None

@router.post("/generate/async", response={202: AsyncJobResponse, 400: ErrorResponse})
def generate_text_async(request, data: AsyncJobRequest):
    """비동기 텍스트 생성 API"""
    try:
        task = async_text_generation.delay(data.prompt, data.max_length)
        return 202, AsyncJobResponse(
            job_id=task.id,
            status="PENDING"
        )
    except Exception as e:
        logger.error(f"Async generation failed: {str(e)}")
        return 400, ErrorResponse(error="Failed to queue task", detail=str(e))

@router.get("/job/{job_id}", response=JobResultResponse)
def get_job_result(request, job_id: str):
    """작업 결과 조회 API"""
    from celery.result import AsyncResult
    
    task = AsyncResult(job_id)
    
    if task.state == "PENDING":
        return JobResultResponse(job_id=job_id, status="PENDING")
    elif task.state == "SUCCESS":
        return JobResultResponse(
            job_id=job_id,
            status="SUCCESS",
            result=task.result
        )
    elif task.state == "FAILURE":
        return JobResultResponse(
            job_id=job_id,
            status="FAILURE",
            error=str(task.info)
        )
    else:
        return JobResultResponse(job_id=job_id, status=task.state)

@router.post("/sentiment/batch", response={202: AsyncJobResponse})
def analyze_sentiment_batch(request, data: BatchRequest):
    """배치 감정 분석 API"""
    task = batch_sentiment_analysis.delay(data.texts)
    return 202, AsyncJobResponse(job_id=task.id, status="PENDING")
```

Celery 워커를 시작합니다.

```bash
# 터미널 1: Redis 시작
redis-server

# 터미널 2: Celery 워커 시작
celery -A config worker --loglevel=info --concurrency=2

# 터미널 3: Django 서버 시작
python manage.py runserver
```

클라이언트는 다음과 같이 비동기 작업을 요청하고 결과를 폴링합니다.

```python
import requests
import time

# 비동기 작업 시작
response = requests.post("http://localhost:8000/api/ai/generate/async", json={
    "prompt": "Once upon a time in a galaxy far away",
    "max_length": 200
})
job_id = response.json()["job_id"]

# 결과 폴링 (최대 60초 대기)
for _ in range(60):
    result = requests.get(f"http://localhost:8000/api/ai/job/{job_id}")
    data = result.json()
    if data["status"] == "SUCCESS":
        print(data["result"]["generated_text"])
        break
    elif data["status"] == "FAILURE":
        print(f"Error: {data['error']}")
        break
    time.sleep(1)
```

## 성능 최적화와 GPU 메모리 관리

프로덕션 환경에서는 메모리 사용량을 제어하고 추론 속도를 최대화해야 합니다. 여러 최적화 기법을 적용할 수 있습니다.

### 1. 모델 양자화로 메모리 절약

FP16이나 INT8 양자화를 적용하면 모델 크기를 절반 이하로 줄이고 추론 속도를 2배 이상 높일 수 있습니다.

```python
# ai/model_manager.py에 추가
import torch
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

def get_quantized_text_generation_pipeline(self):
    """8bit 양자화된 텍스트 생성 모델"""
    if "text_generation_8bit" not in self._models:
        logger.info("Loading 8bit quantized text generation model...")
        
        # 8bit 양자화 설정
        quantization_config = BitsAndBytesConfig(
            load_in_8bit=True,
            llm_int8_threshold=6.0
        )
        
        model = AutoModelForCausalLM.from_pretrained(
            settings.TEXT_GENERATION_MODEL,
            quantization_config=quantization_config,
            device_map="auto"
        )
        
        tokenizer = AutoTokenizer.from_pretrained(settings.TEXT_GENERATION_MODEL)
        
        self._models["text_generation_8bit"] = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer
        )
    return self._models["text_generation_8bit"]
```

### 2. 배치 처리로 GPU 활용률 극대화

여러 입력을 묶어서 한 번에 처리하면 GPU를 효율적으로 사용할 수 있습니다.

```python
# ai/tasks.py에 추가
@shared_task
def batch_translation(texts: list, direction: str = "en_to_ko"):
    """배치 번역 작업 (최대 32개까지 동시 처리)"""
    try:
        pipeline = model_manager.get_translation_pipeline(direction)
        # 32개씩 청크로 나눠서 처리
        batch_size = 32
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = pipeline(batch)
            results.extend([r["translation_text"] for r in batch_results])
        
        return {"status": "completed", "translations": results}
    except Exception as e:
        logger.error(f"Batch translation failed: {str(e)}")
        return {"status": "failed", "error": str(e)}
```

### 3. 동적 패딩으로 불필요한 계산 줄이기

긴 시퀀스와 짧은 시퀀스를 함께 처리할 때 최대 길이로 패딩하면 낭비가 심합니다.

```python
from transformers import DataCollatorWithPadding

def get_sentiment_pipeline_optimized(self):
    """동적 패딩이 적용된 감정 분석 파이프라인"""
    if "sentiment_optimized" not in self._models:
        tokenizer = AutoTokenizer.from_pretrained(settings.SENTIMENT_MODEL)
        model = AutoModelForSequenceClassification.from_pretrained(
            settings.SENTIMENT_MODEL
        ).to(self.device)
        
        self._models["sentiment_optimized"] = pipeline(
            "sentiment-analysis",
            model=model,
            tokenizer=tokenizer,
            padding=True,  # 동적 패딩 활성화
            truncation=True,
            max_length=512
        )
    return self._models["sentiment_optimized"]
```

### 4. TorchScript 컴파일로 추론 가속

자주 사용하는 모델은 TorchScript로 컴파일하면 10~30% 빨라집니다.

```python
import torch

def compile_model_to_torchscript(model, sample_input):
    """모델을 TorchScript로 컴파일"""
    model.eval()
    with torch.no_grad():
        traced_model = torch.jit.trace(model, sample_input)
    return traced_model

# 사용 예시
# traced_model = compile_model_to_torchscript(model, sample_tensor)
# traced_model.save("model_traced.pt")
```

### 5. GPU 메모리 모니터링과 자동 정리

```python
# ai/utils.py
import torch
import logging

logger = logging.getLogger(__name__)

def log_gpu_memory():
    """GPU 메모리 사용량 로깅"""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**3  # GB
        reserved = torch.cuda.memory_reserved() / 1024**3
        logger.info(f"GPU Memory: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved")

def clear_gpu_cache():
    """GPU 캐시 정리"""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        logger.info("GPU cache cleared")

# Celery 작업 후 자동 정리
@shared_task
def cleanup_task():
    """주기적으로 GPU 메모리 정리 (크론 작업)"""
    log_gpu_memory()
    clear_gpu_cache()
    log_gpu_memory()
```

Celery Beat를 사용해 주기적으로 메모리를 정리합니다.

```python
# settings.py에 추가
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'cleanup-gpu-every-hour': {
        'task': 'ai.tasks.cleanup_task',
        'schedule': crontab(minute=0),  # 매 시간마다
    },
}
```

이 최적화 기법들을 적용하면 같은 하드웨어에서 2~3배 많은 요청을 처리할 수 있습니다.

## 에러 처리와 모니터링

프로덕션 환경에서는 모델 로드 실패, OOM(Out of Memory), 타임아웃 등 다양한 예외 상황에 대비해야 합니다.

### 1. 포괄적인 예외 처리

```python
# ai/exceptions.py
class ModelLoadError(Exception):
    """모델 로드 실패 예외"""
    pass

class InferenceError(Exception):
    """추론 실행 실패 예외"""
    pass

class GPUMemoryError(Exception):
    """GPU 메모리 부족 예외"""
    pass

# ai/model_manager.py에 추가
from .exceptions import ModelLoadError, InferenceError, GPUMemoryError

def get_sentiment_pipeline(self):
    """에러 처리가 강화된 감정 분석 파이프라인"""
    try:
        if "sentiment" not in self._models:
            logger.info("Loading sentiment analysis model...")
            self._models["sentiment"] = pipeline(
                "sentiment-analysis",
                model=settings.SENTIMENT_MODEL,
                device=0 if self.device.startswith("cuda") else -1
            )
        return self._models["sentiment"]
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            logger.error("GPU OOM error, falling back to CPU")
            torch.cuda.empty_cache()
            # CPU로 폴백
            self._models["sentiment"] = pipeline(
                "sentiment-analysis",
                model=settings.SENTIMENT_MODEL,
                device=-1
            )
            return self._models["sentiment"]
        raise ModelLoadError(f"Failed to load model: {str(e)}")
    except Exception as e:
        raise ModelLoadError(f"Unexpected error loading model: {str(e)}")
```

### 2. 타임아웃과 재시도 로직

```python
# ai/utils.py
import signal
from contextlib import contextmanager

class TimeoutError(Exception):
    pass

@contextmanager
def timeout(seconds):
    """함수 실행에 타임아웃 적용"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

# 사용 예시
from .utils import timeout, TimeoutError

@router.post("/generate/with-timeout", response={200: TextGenerationResponse, 400: ErrorResponse})
def generate_text_with_timeout(request, data: TextGenerationRequest):
    """타임아웃이 적용된 텍스트 생성"""
    try:
        with timeout(10):  # 10초 타임아웃
            pipeline = model_manager.get_text_generation_pipeline()
            result = pipeline(data.prompt, max_length=data.max_length)[0]
            return TextGenerationResponse(generated_text=result["generated_text"])
    except TimeoutError:
        return 400, ErrorResponse(
            error="Request timeout",
            detail="Generation took too long, try async endpoint"
        )
    except Exception as e:
        return 400, ErrorResponse(error="Generation failed", detail=str(e))
```

### 3. Prometheus와 Grafana로 모니터링

```python
# requirements.txt에 추가
# prometheus-client

# ai/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# 메트릭 정의
request_count = Counter(
    'ai_requests_total',
    'Total AI API requests',
    ['endpoint', 'status']
)

inference_duration = Histogram(
    'ai_inference_duration_seconds',
    'Time spent on model inference',
    ['model_type']
)

gpu_memory_usage = Gauge(
    'ai_gpu_memory_bytes',
    'GPU memory usage in bytes'
)

# 사용 예시
@router.post("/sentiment", response={200: SentimentResponse, 400: ErrorResponse})
def analyze_sentiment_with_metrics(request, data: SentimentRequest):
    """메트릭이 추가된 감정 분석"""
    start_time = time.time()
    try:
        pipeline = model_manager.get_sentiment_pipeline()
        result = pipeline(data.text)[0]
        
        response = SentimentResponse(
            label=result["label"],
            score=round(result["score"], 4)
        )
        
        # 성공 메트릭 기록
        request_count.labels(endpoint='sentiment', status='success').inc()
        inference_duration.labels(model_type='sentiment').observe(time.time() - start_time)
        
        return response
    except Exception as e:
        request_count.labels(endpoint='sentiment', status='error').inc()
        logger.error(f"Sentiment analysis error: {str(e)}")
        return 400, ErrorResponse(error="Analysis failed", detail=str(e))

# Prometheus 엔드포인트
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from django.http import HttpResponse

def metrics_view(request):
    """Prometheus 메트릭 노출"""
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)

# urls.py에 추가
from ai.metrics import metrics_view
urlpatterns += [
    path("metrics", metrics_view),
]
```

### 4. 구조화된 로깅

```python
# settings.py에 추가
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/ai_api.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'loggers': {
        'ai': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# pip install python-json-logger
```

이렇게 구조화된 로깅을 사용하면 ELK 스택이나 CloudWatch로 쉽게 분석할 수 있습니다.

## Docker 배포와 멀티 스테이지 빌드

Hugging Face 모델을 포함한 Docker 이미지는 수 GB에 달할 수 있으므로, 효율적인 빌드 전략이 필요합니다.

```dockerfile
# Dockerfile
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04 AS base

# Python 설치
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성만 먼저 설치 (캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 모델 사전 다운로드 (이미지 빌드 시)
FROM base AS model-download
RUN python3 -c "from transformers import pipeline; \
    pipeline('sentiment-analysis', model='distilbert-base-uncased-finetuned-sst-2-english'); \
    pipeline('text-generation', model='gpt2');"

# 최종 이미지
FROM base AS final
COPY --from=model-download /root/.cache/huggingface /root/.cache/huggingface
COPY . .

# 환경 변수
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/root/.cache/huggingface
ENV DJANGO_SETTINGS_MODULE=config.settings

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8000/api/ai/health')"

# 실행
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
```

Docker Compose로 전체 스택을 구성합니다.

```yaml
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ai_db
      POSTGRES_USER: ai_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ai_user"]
      interval: 5s
      timeout: 3s
      retries: 5

  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120
    volumes:
      - .:/app
      - model_cache:/root/.cache/huggingface
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://ai_user:${DB_PASSWORD}@db:5432/ai_db
      - REDIS_URL=redis://redis:6379/0
      - HF_DEVICE=cuda:0
    depends_on:
      redis:
        condition: service_healthy
      db:
        condition: service_healthy
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  celery:
    build: .
    command: celery -A config worker --loglevel=info --concurrency=1
    volumes:
      - .:/app
      - model_cache:/root/.cache/huggingface
    environment:
      - DATABASE_URL=postgresql://ai_user:${DB_PASSWORD}@db:5432/ai_db
      - REDIS_URL=redis://redis:6379/0
      - HF_DEVICE=cuda:0
    depends_on:
      - redis
      - db
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  celery-beat:
    build: .
    command: celery -A config beat --loglevel=info
    volumes:
      - .:/app
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - db

volumes:
  redis_data:
  postgres_data:
  model_cache:  # 모델 캐시 영구 저장
```

배포 명령:

```bash
# 이미지 빌드 (모델 사전 다운로드 포함)
docker-compose build

# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f web

# GPU 사용 확인
docker exec -it <container_id> nvidia-smi
```

## 프로덕션 체크리스트와 보안 고려사항

프로덕션 배포 전 다음 사항을 확인해야 합니다.

### 1. 성능 및 스케일링
- [ ] GPU 메모리 프로파일링 완료 (nvidia-smi, torch.cuda.memory_summary())
- [ ] 동시 요청 처리 테스트 (Locust, JMeter 등)
- [ ] Celery 워커 개수 최적화 (CPU: 2n+1, GPU: 1~2개)
- [ ] 모델 캐시 볼륨 마운트 확인
- [ ] Rate Limiting 설정 (Django Ratelimit 또는 Nginx)

```python
# settings.py에 추가
# pip install django-ratelimit
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='100/h', method='POST')
@router.post("/sentiment")
def analyze_sentiment(request, data: SentimentRequest):
    # ...
```

### 2. 보안
- [ ] API 키 인증 구현 (JWT 또는 API Key)
- [ ] HTTPS 설정 (Let's Encrypt, Nginx 리버스 프록시)
- [ ] CORS 정책 설정
- [ ] 입력 검증 및 SQL Injection 방지
- [ ] Rate Limiting으로 DDoS 방지

```python
# ai/authentication.py
from ninja.security import HttpBearer
from django.conf import settings

class ApiKeyAuth(HttpBearer):
    def authenticate(self, request, token):
        if token == settings.API_SECRET_KEY:
            return token
        return None

# API에 적용
api = NinjaAPI(auth=ApiKeyAuth())
```

### 3. 모니터링 및 알림
- [ ] Prometheus + Grafana 대시보드 구성
- [ ] Sentry로 에러 트래킹
- [ ] CloudWatch/ELK로 로그 집계
- [ ] GPU 메모리 부족 시 알림 설정
- [ ] 응답 시간 95 percentile 모니터링

### 4. 비용 최적화
- [ ] 사용하지 않는 모델은 언로드
- [ ] 캐싱으로 중복 계산 방지 (Redis TTL 설정)
- [ ] AWS Spot Instance 또는 Preemptible VM 활용
- [ ] 모델 양자화 적용 (FP16, INT8)

### 5. 백업 및 복구
- [ ] 모델 파일 백업 (S3, GCS 등)
- [ ] 데이터베이스 정기 백업
- [ ] Docker 이미지 버전 관리
- [ ] 롤백 계획 수립

이 체크리스트를 모두 완료하면 안정적이고 확장 가능한 AI API 서비스를 운영할 수 있습니다.

## 실전 예제: 고객 리뷰 분석 시스템

이제 배운 내용을 종합해서 실제 서비스를 구축해봅니다. 고객 리뷰를 받아 감정을 분석하고, 부정 리뷰는 요약해서 알림을 보내는 시스템입니다.

```python
# ai/services.py
from .model_manager import model_manager
from .tasks import async_summarization
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class ReviewAnalysisService:
    """고객 리뷰 분석 서비스"""
    
    @staticmethod
    def analyze_review(review_text: str, review_id: int):
        """리뷰 감정 분석 및 처리"""
        # 1. 감정 분석
        sentiment_pipeline = model_manager.get_sentiment_pipeline()
        sentiment = sentiment_pipeline(review_text)[0]
        
        logger.info(f"Review {review_id} analyzed: {sentiment['label']} ({sentiment['score']:.2f})")
        
        # 2. 부정 리뷰이고 긴 경우 요약
        if sentiment['label'] == 'NEGATIVE' and len(review_text) > 200:
            summary_task = async_summarization.delay(review_text, max_length=50)
            logger.info(f"Summarization task created: {summary_task.id}")
            return {
                "review_id": review_id,
                "sentiment": sentiment['label'],
                "score": sentiment['score'],
                "summary_job_id": summary_task.id,
                "requires_attention": True
            }
        
        return {
            "review_id": review_id,
            "sentiment": sentiment['label'],
            "score": sentiment['score'],
            "requires_attention": sentiment['label'] == 'NEGATIVE'
        }
    
    @staticmethod
    def batch_analyze_reviews(reviews: list):
        """여러 리뷰를 배치로 분석"""
        texts = [r['text'] for r in reviews]
        pipeline = model_manager.get_sentiment_pipeline()
        results = pipeline(texts)
        
        analyzed = []
        for review, sentiment in zip(reviews, results):
            analyzed.append({
                "review_id": review['id'],
                "text": review['text'][:100] + "...",
                "sentiment": sentiment['label'],
                "score": sentiment['score']
            })
        
        # 통계 계산
        negative_count = sum(1 for r in results if r['label'] == 'NEGATIVE')
        positive_count = len(results) - negative_count
        
        return {
            "total": len(reviews),
            "positive": positive_count,
            "negative": negative_count,
            "negative_rate": negative_count / len(reviews) if reviews else 0,
            "reviews": analyzed
        }

# API 엔드포인트
from .services import ReviewAnalysisService
from ninja import Schema

class ReviewRequest(Schema):
    review_id: int
    text: str

class BatchReviewRequest(Schema):
    reviews: list

@router.post("/reviews/analyze")
def analyze_review(request, data: ReviewRequest):
    """개별 리뷰 분석"""
    result = ReviewAnalysisService.analyze_review(data.text, data.review_id)
    return result

@router.post("/reviews/batch-analyze")
def batch_analyze_reviews(request, data: BatchReviewRequest):
    """배치 리뷰 분석"""
    result = ReviewAnalysisService.batch_analyze_reviews(data.reviews)
    return result
```

프론트엔드 연동 예제 (JavaScript):

```javascript
// 개별 리뷰 분석
async function analyzeReview(reviewId, text) {
    const response = await fetch('http://localhost:8000/api/ai/reviews/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer YOUR_API_KEY'
        },
        body: JSON.stringify({
            review_id: reviewId,
            text: text
        })
    });
    
    const result = await response.json();
    
    if (result.requires_attention) {
        // 관리자에게 알림
        console.log(`⚠️ Negative review detected: ${reviewId}`);
        if (result.summary_job_id) {
            // 요약 결과 폴링
            pollSummary(result.summary_job_id);
        }
    }
    
    return result;
}

// 배치 분석
async function analyzeBatchReviews(reviews) {
    const response = await fetch('http://localhost:8000/api/ai/reviews/batch-analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer YOUR_API_KEY'
        },
        body: JSON.stringify({ reviews })
    });
    
    const result = await response.json();
    console.log(`Negative rate: ${(result.negative_rate * 100).toFixed(1)}%`);
    
    return result;
}

// 예시 사용
const reviews = [
    { id: 1, text: "Great product! Love it!" },
    { id: 2, text: "Terrible quality, broke after one day. Very disappointed with the customer service." },
    { id: 3, text: "Average, nothing special" }
];

analyzeBatchReviews(reviews);
```

이 예제는 실제 이커머스나 SaaS 서비스에서 고객 피드백을 자동으로 분류하고 우선순위를 매기는 데 사용할 수 있습니다.

## 마치며

이 글에서는 Django Ninja와 Hugging Face Transformers를 통합해 비용 제로로 운영 가능한 AI API를 구축하는 전 과정을 다뤘습니다. OpenAI나 Claude 같은 클라우드 서비스에 비해 초기 설정이 복잡하지만, 한번 구축하면 무제한으로 사용할 수 있고, 데이터가 외부로 나가지 않으며, 네트워크 장애에도 영향받지 않는다는 장점이 있습니다. 특히 감정 분석, 분류, 번역처럼 명확한 작업에서는 경량 모델로도 충분한 정확도를 달성할 수 있어 실용적입니다. GPU가 없는 환경이라면 CPU 최적화 기법(양자화, 배치 처리, TorchScript)을 적극 활용하고, GPU가 있다면 여러 모델을 메모리에 올려두고 병렬로 서비스할 수 있습니다. Celery를 통한 비동기 처리와 Redis 캐싱을 결합하면 수백~수천 명의 동시 사용자를 처리할 수 있는 확장 가능한 시스템을 만들 수 있습니다. 프로덕션 배포 시에는 모니터링·에러 트래킹·보안 설정을 빠뜨리지 말고, GPU 메모리 프로파일링을 통해 적절한 워커 수를 설정해야 합니다. Hugging Face Hub에는 계속해서 새로운 모델이 공개되므로, 작업에 맞는 최신 모델을 찾아 교체하면 성능을 지속적으로 개선할 수 있습니다. 이 가이드를 기반으로 챗봇, 문서 분석, 추천 시스템 등 다양한 AI 서비스를 직접 구축해보시기 바랍니다.

