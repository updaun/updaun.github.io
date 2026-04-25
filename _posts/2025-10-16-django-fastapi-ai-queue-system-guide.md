---
layout: post
title: "Django + FastAPI AI 큐 시스템 구축: 사진 업로드 후 비동기 AI 처리 완벽 가이드"
date: 2025-10-16
categories: [Backend, AI, Queue]
tags: [Django, FastAPI, AI, Queue, Async, Celery, Redis, Background Processing]
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-10-16-django-fastapi-ai-queue-system-guide.webp"
---

## 개요

관리자가 Django 백엔드에 사진을 업로드하면 FastAPI AI 서비스가 큐 기반으로 순차 처리하는 시스템을 구축해보겠습니다. 서버 중단 없이 안정적으로 AI 요청을 처리하는 방법을 단계별로 알아보겠습니다.

## 시스템 아키텍처

### 전체 구조도

```
[Django Admin] → [Django Backend] → [Message Queue] → [FastAPI AI Service]
     ↓                    ↓               ↓                    ↓
  이미지 업로드        큐에 작업 추가      작업 대기열         AI 모델 처리
```

### 핵심 구성 요소

1. **Django Backend**: 이미지 업로드 및 큐 관리
2. **Message Queue**: Redis/Celery 또는 RQ 기반 작업 큐
3. **FastAPI AI Service**: AI 모델을 활용한 이미지 처리
4. **Database**: 작업 상태 및 결과 저장

## 1단계: Django 백엔드 구성

### 모델 정의

```python
# models.py
from django.db import models
from django.contrib.auth.models import User

class ImageUpload(models.Model):
    STATUS_CHOICES = [
        ('pending', '대기중'),
        ('processing', '처리중'),
        ('completed', '완료'),
        ('failed', '실패'),
    ]
    
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='uploads/')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # AI 처리 결과
    ai_result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 큐 관련 정보
    task_id = models.CharField(max_length=100, null=True, blank=True)
    priority = models.IntegerField(default=0)  # 우선순위 (높을수록 우선)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.status}"
```

### Django Admin 커스터마이징

```python
# admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import ImageUpload
from .tasks import process_image_task

@admin.register(ImageUpload)
class ImageUploadAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'priority', 'created_at', 'task_status']
    list_filter = ['status', 'created_at']
    search_fields = ['title']
    readonly_fields = ['task_id', 'ai_result', 'error_message']
    
    actions = ['reprocess_images', 'set_high_priority']
    
    def task_status(self, obj):
        if obj.status == 'pending':
            return format_html('<span style="color: orange;">⏳ 대기중</span>')
        elif obj.status == 'processing':
            return format_html('<span style="color: blue;">🔄 처리중</span>')
        elif obj.status == 'completed':
            return format_html('<span style="color: green;">✅ 완료</span>')
        else:
            return format_html('<span style="color: red;">❌ 실패</span>')
    
    def save_model(self, request, obj, form, change):
        # 새로운 이미지 업로드 시 큐에 작업 추가
        is_new = not change
        super().save_model(request, obj, form, change)
        
        if is_new:
            # 비동기 작업 큐에 추가
            task = process_image_task.delay(obj.id)
            obj.task_id = task.id
            obj.save(update_fields=['task_id'])
    
    def reprocess_images(self, request, queryset):
        """선택된 이미지들을 다시 처리"""
        for image in queryset:
            task = process_image_task.delay(image.id)
            image.task_id = task.id
            image.status = 'pending'
            image.save(update_fields=['task_id', 'status'])
        
        self.message_user(request, f"{queryset.count()}개 이미지가 재처리 큐에 추가되었습니다.")
    
    def set_high_priority(self, request, queryset):
        """선택된 이미지들의 우선순위를 높게 설정"""
        queryset.update(priority=10)
        self.message_user(request, f"{queryset.count()}개 이미지의 우선순위가 높게 설정되었습니다.")
    
    reprocess_images.short_description = "선택된 이미지 재처리"
    set_high_priority.short_description = "높은 우선순위로 설정"
```

## 2단계: Celery 큐 시스템 구성

### Celery 설정

```python
# celery_config.py
import os
from celery import Celery
from django.conf import settings

# Django 설정 모듈 지정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

app = Celery('ai_processor')

# Django settings 사용
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# 큐 라우팅 설정
app.conf.task_routes = {
    'myapp.tasks.process_image_task': {'queue': 'ai_processing'},
    'myapp.tasks.cleanup_task': {'queue': 'cleanup'},
}

# 우선순위 큐 설정
app.conf.task_default_priority = 5
app.conf.worker_prefetch_multiplier = 1  # 순차 처리를 위해
app.conf.task_acks_late = True
app.conf.worker_prefetch_multiplier = 1

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
```

### Django 설정

```python
# settings.py
import os

# Celery 설정
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'

# 큐 설정
CELERY_TASK_ROUTES = {
    'myapp.tasks.process_image_task': {
        'queue': 'ai_processing',
        'routing_key': 'ai_processing',
    },
}

# 우선순위 큐 설정
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_QUEUES = {
    'ai_processing': {
        'exchange': 'ai_processing',
        'exchange_type': 'direct',
        'routing_key': 'ai_processing',
    },
}

# 실패 재시도 설정
CELERY_TASK_ANNOTATIONS = {
    'myapp.tasks.process_image_task': {
        'rate_limit': '10/m',  # 분당 10개 작업
        'time_limit': 300,     # 5분 타임아웃
        'soft_time_limit': 240, # 4분 소프트 타임아웃
        'retry_kwargs': {'max_retries': 3, 'countdown': 60},
    }
}
```

### Celery 작업 정의

```python
# tasks.py
import requests
import logging
from celery import shared_task
from django.conf import settings
from .models import ImageUpload

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_image_task(self, image_id):
    """
    이미지 AI 처리 작업
    우선순위에 따라 처리되며, 실패 시 재시도
    """
    try:
        # 이미지 객체 가져오기
        image_obj = ImageUpload.objects.get(id=image_id)
        
        # 상태 업데이트
        image_obj.status = 'processing'
        image_obj.save(update_fields=['status'])
        
        logger.info(f"AI 처리 시작: {image_obj.title} (ID: {image_id})")
        
        # FastAPI 서비스 호출
        fastapi_url = settings.FASTAPI_AI_SERVICE_URL
        
        # 이미지 파일 전송 준비
        with open(image_obj.image.path, 'rb') as image_file:
            files = {'file': image_file}
            data = {
                'image_id': image_id,
                'priority': image_obj.priority,
                'metadata': {
                    'title': image_obj.title,
                    'uploaded_by': image_obj.uploaded_by.username
                }
            }
            
            # FastAPI에 요청
            response = requests.post(
                f"{fastapi_url}/process-image/",
                files=files,
                data=data,
                timeout=300  # 5분 타임아웃
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 성공 시 결과 저장
                image_obj.ai_result = result
                image_obj.status = 'completed'
                image_obj.error_message = None
                
                logger.info(f"AI 처리 완료: {image_obj.title}")
                
            else:
                raise Exception(f"FastAPI 오류: {response.status_code} - {response.text}")
    
    except ImageUpload.DoesNotExist:
        logger.error(f"이미지를 찾을 수 없음: ID {image_id}")
        return
    
    except Exception as exc:
        logger.error(f"AI 처리 실패: {image_obj.title} - {str(exc)}")
        
        # 재시도 로직
        if self.request.retries < self.max_retries:
            logger.info(f"재시도 예정: {self.request.retries + 1}/{self.max_retries}")
            
            # 지수 백오프로 재시도
            countdown = 2 ** self.request.retries * 60  # 1분, 2분, 4분
            raise self.retry(exc=exc, countdown=countdown)
        
        # 최종 실패
        image_obj.status = 'failed'
        image_obj.error_message = str(exc)
    
    finally:
        image_obj.save()

@shared_task
def cleanup_failed_tasks():
    """실패한 작업들 정리"""
    from datetime import datetime, timedelta
    
    # 24시간 이상 처리중인 작업들을 실패로 변경
    stale_threshold = datetime.now() - timedelta(hours=24)
    
    stale_images = ImageUpload.objects.filter(
        status='processing',
        updated_at__lt=stale_threshold
    )
    
    count = stale_images.update(
        status='failed',
        error_message='처리 시간 초과로 인한 자동 실패 처리'
    )
    
    logger.info(f"정리된 오래된 작업: {count}개")
    return count
```

## 3단계: FastAPI AI 서비스 구성

### FastAPI 애플리케이션

```python
# main.py
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from typing import Optional
import json
from queue import PriorityQueue
import threading
from datetime import datetime

from .ai_processor import AIImageProcessor
from .models import ProcessingRequest, ProcessingResult

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Image Processing Service", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 큐와 워커 관리
processing_queue = PriorityQueue()
is_processing = False
processor_lock = threading.Lock()

# AI 모델 초기화 (앱 시작 시 한 번만)
ai_processor = AIImageProcessor()

class QueueManager:
    def __init__(self):
        self.queue = PriorityQueue()
        self.is_running = False
        self.current_task = None
        
    async def add_task(self, request: ProcessingRequest):
        """우선순위에 따라 작업을 큐에 추가"""
        priority = -request.priority  # 높은 숫자가 먼저 처리되도록 음수 변환
        self.queue.put((priority, datetime.now(), request))
        logger.info(f"큐에 작업 추가: {request.image_id} (우선순위: {request.priority})")
        
        # 워커가 실행중이 아니면 시작
        if not self.is_running:
            asyncio.create_task(self.process_queue())
    
    async def process_queue(self):
        """큐의 작업들을 순차적으로 처리"""
        self.is_running = True
        
        while not self.queue.empty():
            try:
                priority, timestamp, request = self.queue.get()
                self.current_task = request
                
                logger.info(f"AI 처리 시작: {request.image_id}")
                
                # AI 모델로 이미지 처리
                result = await ai_processor.process_image(
                    request.image_data,
                    request.metadata
                )
                
                # 결과를 Django 백엔드에 콜백
                await self.send_callback(request.image_id, result)
                
                logger.info(f"AI 처리 완료: {request.image_id}")
                
            except Exception as e:
                logger.error(f"처리 중 오류: {e}")
                # 실패 시에도 콜백 전송
                await self.send_callback(
                    request.image_id, 
                    {"error": str(e), "status": "failed"}
                )
            
            finally:
                self.current_task = None
        
        self.is_running = False
        logger.info("큐 처리 완료")
    
    async def send_callback(self, image_id: int, result: dict):
        """Django 백엔드에 처리 결과 전송"""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                callback_url = f"{DJANGO_CALLBACK_URL}/api/ai-callback/"
                
                response = await client.post(
                    callback_url,
                    json={
                        "image_id": image_id,
                        "result": result,
                        "timestamp": datetime.now().isoformat()
                    },
                    timeout=30
                )
                
                if response.status_code != 200:
                    logger.error(f"콜백 실패: {response.status_code}")
        
        except Exception as e:
            logger.error(f"콜백 전송 오류: {e}")

# 큐 매니저 인스턴스
queue_manager = QueueManager()

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 AI 모델 로드"""
    logger.info("AI 모델 로딩 중...")
    await ai_processor.load_model()
    logger.info("AI 서비스 준비 완료")

@app.post("/process-image/")
async def process_image(
    file: UploadFile = File(...),
    image_id: int = Form(...),
    priority: int = Form(default=0),
    metadata: str = Form(default="{}")
):
    """
    이미지 처리 요청을 큐에 추가
    """
    try:
        # 이미지 데이터 읽기
        image_data = await file.read()
        
        # 메타데이터 파싱
        try:
            metadata_dict = json.loads(metadata)
        except:
            metadata_dict = {}
        
        # 처리 요청 객체 생성
        request = ProcessingRequest(
            image_id=image_id,
            image_data=image_data,
            priority=priority,
            metadata=metadata_dict,
            filename=file.filename
        )
        
        # 큐에 추가
        await queue_manager.add_task(request)
        
        return {
            "status": "queued",
            "image_id": image_id,
            "message": "이미지가 처리 큐에 추가되었습니다",
            "queue_size": queue_manager.queue.qsize()
        }
    
    except Exception as e:
        logger.error(f"이미지 처리 요청 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queue-status/")
async def get_queue_status():
    """큐 상태 조회"""
    return {
        "queue_size": queue_manager.queue.qsize(),
        "is_processing": queue_manager.is_running,
        "current_task": queue_manager.current_task.image_id if queue_manager.current_task else None
    }

@app.get("/health/")
async def health_check():
    """서비스 상태 확인"""
    return {
        "status": "healthy",
        "model_loaded": ai_processor.is_loaded,
        "queue_size": queue_manager.queue.qsize(),
        "timestamp": datetime.now().isoformat()
    }
```

### AI 프로세서 모듈

```python
# ai_processor.py
import asyncio
import logging
from typing import Dict, Any
import numpy as np
from PIL import Image
import io

logger = logging.getLogger(__name__)

class AIImageProcessor:
    def __init__(self):
        self.model = None
        self.is_loaded = False
    
    async def load_model(self):
        """AI 모델 로드 (앱 시작 시 한 번만 실행)"""
        try:
            # 여기에 실제 AI 모델 로딩 코드 작성
            # 예: YOLO, OpenCV, TensorFlow, PyTorch 등
            
            # 예시: 더미 모델 로드
            await asyncio.sleep(2)  # 모델 로딩 시뮬레이션
            self.model = "loaded_ai_model"
            self.is_loaded = True
            
            logger.info("AI 모델 로드 완료")
            
        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
            raise
    
    async def process_image(self, image_data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """이미지 AI 처리"""
        if not self.is_loaded:
            raise Exception("AI 모델이 로드되지 않았습니다")
        
        try:
            # 이미지 전처리
            image = Image.open(io.BytesIO(image_data))
            
            # AI 모델 추론 (비동기 처리)
            result = await self._run_inference(image, metadata)
            
            return {
                "status": "success",
                "result": result,
                "image_info": {
                    "size": image.size,
                    "format": image.format,
                    "mode": image.mode
                },
                "processing_time": result.get("processing_time", 0)
            }
            
        except Exception as e:
            logger.error(f"이미지 처리 오류: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _run_inference(self, image: Image.Image, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """실제 AI 추론 실행"""
        # CPU 집약적 작업을 별도 스레드에서 실행
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._sync_inference, image, metadata)
        return result
    
    def _sync_inference(self, image: Image.Image, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """동기 AI 추론 (실제 모델 추론 코드)"""
        import time
        start_time = time.time()
        
        # 여기에 실제 AI 모델 추론 코드 작성
        # 예시: 객체 검출, 분류, 세그멘테이션 등
        
        # 더미 처리 (실제로는 모델 추론)
        time.sleep(2)  # AI 처리 시뮬레이션
        
        processing_time = time.time() - start_time
        
        return {
            "detected_objects": [
                {"class": "person", "confidence": 0.95, "bbox": [100, 100, 200, 300]},
                {"class": "car", "confidence": 0.87, "bbox": [300, 150, 500, 400]}
            ],
            "processing_time": processing_time,
            "metadata": metadata
        }
```

### 데이터 모델

```python
# models.py
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class ProcessingRequest(BaseModel):
    image_id: int
    image_data: bytes
    priority: int = 0
    metadata: Dict[str, Any] = {}
    filename: Optional[str] = None
    created_at: datetime = datetime.now()

class ProcessingResult(BaseModel):
    image_id: int
    status: str
    result: Dict[str, Any]
    error: Optional[str] = None
    processing_time: float = 0.0
    completed_at: datetime = datetime.now()
```

## 4단계: Django 콜백 처리

### 콜백 API 뷰

```python
# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging
from .models import ImageUpload

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def ai_callback(request):
    """FastAPI로부터 AI 처리 결과 수신"""
    try:
        data = json.loads(request.body)
        image_id = data.get('image_id')
        result = data.get('result')
        
        # 이미지 객체 업데이트
        image_obj = ImageUpload.objects.get(id=image_id)
        
        if result.get('status') == 'success':
            image_obj.status = 'completed'
            image_obj.ai_result = result
            image_obj.error_message = None
        else:
            image_obj.status = 'failed'
            image_obj.error_message = result.get('error', '알 수 없는 오류')
        
        image_obj.save()
        
        logger.info(f"AI 처리 결과 수신: {image_id} - {image_obj.status}")
        
        return JsonResponse({"status": "success"})
    
    except ImageUpload.DoesNotExist:
        logger.error(f"이미지를 찾을 수 없음: {image_id}")
        return JsonResponse({"error": "Image not found"}, status=404)
    
    except Exception as e:
        logger.error(f"콜백 처리 오류: {e}")
        return JsonResponse({"error": str(e)}, status=500)
```

### URL 설정

```python
# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/ai-callback/', views.ai_callback, name='ai_callback'),
]
```

## 5단계: 배포 및 운영

### Docker Compose 설정

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

  django:
    build: ./django_backend
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - FASTAPI_AI_SERVICE_URL=http://fastapi:8001
    depends_on:
      - redis
    volumes:
      - ./media:/app/media

  celery:
    build: ./django_backend
    command: celery -A myproject worker -l info -Q ai_processing
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - django
    volumes:
      - ./media:/app/media

  celery-beat:
    build: ./django_backend
    command: celery -A myproject beat -l info
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

  fastapi:
    build: ./fastapi_ai
    ports:
      - "8001:8001"
    environment:
      - DJANGO_CALLBACK_URL=http://django:8000
    volumes:
      - ./ai_models:/app/models

volumes:
  redis_data:
```

### 모니터링 스크립트

```python
# monitoring.py
import requests
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemMonitor:
    def __init__(self):
        self.django_url = "http://localhost:8000"
        self.fastapi_url = "http://localhost:8001"
    
    def check_services(self):
        """서비스 상태 확인"""
        try:
            # FastAPI 상태 확인
            fastapi_health = requests.get(f"{self.fastapi_url}/health/", timeout=10)
            
            if fastapi_health.status_code == 200:
                data = fastapi_health.json()
                logger.info(f"FastAPI 상태: 정상 (큐 크기: {data.get('queue_size', 0)})")
            else:
                logger.error("FastAPI 서비스 비정상")
            
            # Django 상태 확인 (관리자 페이지)
            django_health = requests.get(f"{self.django_url}/admin/", timeout=10)
            
            if django_health.status_code == 200:
                logger.info("Django 서비스: 정상")
            else:
                logger.error("Django 서비스 비정상")
                
        except Exception as e:
            logger.error(f"서비스 확인 오류: {e}")
    
    def monitor_queue(self):
        """큐 상태 모니터링"""
        try:
            response = requests.get(f"{self.fastapi_url}/queue-status/", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"큐 상태 - 크기: {data['queue_size']}, 처리중: {data['is_processing']}")
                
                # 큐가 너무 많이 쌓이면 알림
                if data['queue_size'] > 100:
                    logger.warning(f"큐 크기 경고: {data['queue_size']}개 작업 대기중")
                    
        except Exception as e:
            logger.error(f"큐 모니터링 오류: {e}")

def main():
    monitor = SystemMonitor()
    
    while True:
        monitor.check_services()
        monitor.monitor_queue()
        time.sleep(60)  # 1분마다 확인

if __name__ == "__main__":
    main()
```

## 성능 최적화 팁

### 1. 큐 우선순위 관리

```python
# 긴급 처리가 필요한 경우
ImageUpload.objects.filter(id=image_id).update(priority=10)
process_image_task.delay(image_id)
```

### 2. 배치 처리

```python
@shared_task
def batch_process_images(image_ids):
    """여러 이미지를 한 번에 처리"""
    for image_id in image_ids:
        process_image_task.delay(image_id)
```

### 3. 리소스 모니터링

```python
# 시스템 리소스 확인
import psutil

@shared_task
def monitor_resources():
    cpu_percent = psutil.cpu_percent()
    memory_percent = psutil.virtual_memory().percent
    
    if cpu_percent > 80 or memory_percent > 80:
        logger.warning(f"리소스 사용량 높음 - CPU: {cpu_percent}%, Memory: {memory_percent}%")
```

## 마무리

이 가이드를 통해 Django와 FastAPI를 연동한 안정적인 AI 큐 시스템을 구축할 수 있습니다. 핵심은 다음과 같습니다:

1. **비동기 처리**: Celery를 통한 백그라운드 작업 처리
2. **우선순위 큐**: 중요한 작업을 먼저 처리
3. **오류 처리**: 재시도 메커니즘과 실패 알림
4. **모니터링**: 시스템 상태 실시간 확인
5. **확장성**: 여러 워커로 병렬 처리 가능

이 시스템을 통해 서버 중단 없이 안정적으로 AI 서비스를 운영할 수 있습니다.