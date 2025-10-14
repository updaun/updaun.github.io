---
layout: post
title: "Django Ninja와 Django RQ 완전 가이드: 비동기 API와 백그라운드 작업 마스터하기"
date: 2025-10-14 10:00:00 +0900
categories: [Django, Django-Ninja, Django-RQ, Python, Background-Jobs]
tags: [Django, Django-Ninja, Django-RQ, Redis, Background-Jobs, API, Queue, Async, Performance, Celery]
author: "updaun"
image: "/assets/img/posts/2025-10-14-django-ninja-rq-complete-guide.webp"
---

현대 웹 애플리케이션에서는 즉시 처리되지 않아도 되는 작업들을 백그라운드에서 비동기적으로 처리하는 것이 중요합니다. Django Ninja와 Django RQ를 함께 사용하면 고성능 API와 효율적인 백그라운드 작업 시스템을 구축할 수 있습니다. 이 가이드에서는 단계별로 완전한 구현 방법을 알아보겠습니다.

## 🎯 Django RQ란?

Django RQ는 Python RQ(Redis Queue)를 Django에 통합한 라이브러리입니다. Redis를 백엔드로 사용하여 간단하고 빠른 백그라운드 작업 처리를 제공합니다.

### Django RQ vs Celery 비교

| 특징 | Django RQ | Celery |
|------|-----------|--------|
| **복잡성** | 간단, 최소 설정 | 복잡, 많은 설정 옵션 |
| **브로커** | Redis만 지원 | Redis, RabbitMQ, 기타 |
| **성능** | 가볍고 빠름 | 고성능, 확장성 |
| **기능** | 기본적인 큐 기능 | 고급 스케줄링, 체인 등 |
| **학습 곡선** | 낮음 | 높음 |
| **적합한 용도** | 중소규모 프로젝트 | 대규모 엔터프라이즈 |

### 핵심 장점
- **간단한 설정**: 복잡한 설정 없이 빠른 시작
- **Redis 기반**: 고속 메모리 기반 큐 시스템
- **Django 통합**: Django ORM과 완벽 호환
- **모니터링**: 내장 웹 대시보드 제공
- **실패 처리**: 자동 재시도와 실패 로그
- **스케줄링**: 지연 실행과 반복 작업 지원

### 주요 사용 사례
- 이메일 발송
- 이미지/비디오 처리
- 데이터 분석 및 리포트 생성
- 외부 API 호출
- 파일 업로드/다운로드 처리
- 알림 발송

## 📦 1단계: 환경 설정 및 설치

### 필요한 패키지 설치

```bash
# 기본 패키지 설치
pip install django-ninja django-rq redis

# 개발/운영 환경에 따른 추가 패키지
pip install rq-dashboard  # 웹 대시보드
pip install django-extensions  # 개발 도구
```

### Redis 설치 및 실행

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install redis-server

# macOS (Homebrew)
brew install redis

# Docker로 실행
docker run -d -p 6379:6379 --name redis redis:latest

# Redis 서버 시작
redis-server

# Redis 연결 테스트
redis-cli ping
# PONG 응답이 나오면 정상
```

### Django 설정

```python
# settings.py
import os
from django.core.management.utils import get_random_secret_key

# 기본 Django 설정
SECRET_KEY = os.environ.get('SECRET_KEY', get_random_secret_key())
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # 추가 앱
    'django_rq',
    'rq_dashboard',  # 선택사항: 웹 대시보드
    
    # 프로젝트 앱
    'tasks',  # 백그라운드 작업 앱
    'api',    # API 앱
]

# Redis 및 RQ 설정
RQ_QUEUES = {
    'default': {
        'HOST': os.environ.get('REDIS_HOST', 'localhost'),
        'PORT': int(os.environ.get('REDIS_PORT', 6379)),
        'DB': int(os.environ.get('REDIS_DB', 0)),
        'PASSWORD': os.environ.get('REDIS_PASSWORD', None),
        'DEFAULT_TIMEOUT': 360,
        'CONNECTION_CLASS': 'redis.connection.Connection',
    },
    'high': {  # 높은 우선순위 큐
        'HOST': os.environ.get('REDIS_HOST', 'localhost'),
        'PORT': int(os.environ.get('REDIS_PORT', 6379)),
        'DB': int(os.environ.get('REDIS_DB', 0)),
        'PASSWORD': os.environ.get('REDIS_PASSWORD', None),
        'DEFAULT_TIMEOUT': 500,
    },
    'low': {   # 낮은 우선순위 큐
        'HOST': os.environ.get('REDIS_HOST', 'localhost'),
        'PORT': int(os.environ.get('REDIS_PORT', 6379)),
        'DB': int(os.environ.get('REDIS_DB', 0)),
        'PASSWORD': os.environ.get('REDIS_PASSWORD', None),
        'DEFAULT_TIMEOUT': 500,
    }
}

# RQ 추가 설정
RQ_SHOW_ADMIN_LINK = True  # Django Admin에 RQ 링크 표시

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'rq_jobs.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'rq.worker': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### URL 설정

```python
# urls.py
from django.contrib import admin
from django.urls import path, include
from ninja import NinjaAPI
from api.views import router as api_router

# Django Ninja API 인스턴스 생성
api = NinjaAPI(
    title="Django RQ API",
    description="Django Ninja와 RQ를 활용한 백그라운드 작업 API",
    version="1.0.0"
)

# API 라우터 등록
api.add_router("/tasks/", api_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
    path('django-rq/', include('django_rq.urls')),  # RQ 관리 인터페이스
    path('rq-dashboard/', include('rq_dashboard.urls')),  # RQ 대시보드 (선택사항)
]
```

## 🔧 2단계: Django Ninja와 RQ 연동

### 작업 정의

```python
# tasks/jobs.py
import time
import logging
import requests
from typing import Optional, Dict, Any
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.conf import settings
from PIL import Image
import io
import os

logger = logging.getLogger(__name__)

# 이메일 발송 작업
def send_email_task(
    subject: str,
    message: str,
    recipient_list: list,
    from_email: Optional[str] = None,
    html_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    이메일 발송 백그라운드 작업
    """
    try:
        logger.info(f"이메일 발송 시작: {subject} -> {recipient_list}")
        
        result = send_mail(
            subject=subject,
            message=message,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"이메일 발송 완료: {result}개 발송")
        return {
            'status': 'success',
            'sent_count': result,
            'recipients': recipient_list
        }
        
    except Exception as e:
        logger.error(f"이메일 발송 실패: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e),
            'recipients': recipient_list
        }

# 이미지 처리 작업
def process_image_task(
    image_url: str,
    operations: list,
    output_path: str
) -> Dict[str, Any]:
    """
    이미지 다운로드 및 처리 작업
    """
    try:
        logger.info(f"이미지 처리 시작: {image_url}")
        
        # 이미지 다운로드
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # PIL Image로 변환
        image = Image.open(io.BytesIO(response.content))
        original_size = image.size
        
        # 작업 수행
        for operation in operations:
            if operation['type'] == 'resize':
                size = operation['size']
                image = image.resize(size, Image.Resampling.LANCZOS)
            elif operation['type'] == 'rotate':
                angle = operation['angle']
                image = image.rotate(angle, expand=True)
            elif operation['type'] == 'convert':
                format_type = operation['format']
                if format_type.upper() == 'JPEG' and image.mode == 'RGBA':
                    # RGBA -> RGB 변환 (JPEG는 투명도 미지원)
                    rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                    rgb_image.paste(image, mask=image.split()[-1])
                    image = rgb_image
        
        # 이미지 저장
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        image.save(output_path, quality=95, optimize=True)
        
        result = {
            'status': 'success',
            'original_size': original_size,
            'final_size': image.size,
            'output_path': output_path,
            'operations_applied': len(operations)
        }
        
        logger.info(f"이미지 처리 완료: {result}")
        return result
        
    except Exception as e:
        logger.error(f"이미지 처리 실패: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e),
            'image_url': image_url
        }

# 데이터 분석 작업
def analyze_data_task(
    data_source: str,
    analysis_type: str,
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    데이터 분석 백그라운드 작업
    """
    try:
        logger.info(f"데이터 분석 시작: {analysis_type}")
        
        # 시뮬레이션: 복잡한 데이터 분석
        import random
        time.sleep(random.randint(5, 15))  # 5-15초 처리 시간 시뮬레이션
        
        # 가상의 분석 결과
        results = {
            'status': 'success',
            'analysis_type': analysis_type,
            'data_source': data_source,
            'records_processed': random.randint(1000, 10000),
            'insights': [
                f"패턴 A: {random.randint(1, 100)}% 증가",
                f"패턴 B: {random.randint(1, 100)}% 감소",
                f"이상치: {random.randint(1, 50)}개 발견"
            ],
            'score': round(random.uniform(0.1, 1.0), 3),
            'parameters_used': parameters
        }
        
        logger.info(f"데이터 분석 완료: {results['records_processed']}개 레코드 처리")
        return results
        
    except Exception as e:
        logger.error(f"데이터 분석 실패: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e),
            'analysis_type': analysis_type
        }

# 외부 API 호출 작업
def fetch_external_data_task(
    api_url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    외부 API 데이터 수집 작업
    """
    try:
        logger.info(f"외부 API 호출 시작: {api_url}")
        
        response = requests.get(
            api_url,
            headers=headers or {},
            timeout=timeout
        )
        response.raise_for_status()
        
        data = response.json()
        
        result = {
            'status': 'success',
            'url': api_url,
            'status_code': response.status_code,
            'data_size': len(str(data)),
            'response_time': response.elapsed.total_seconds(),
            'data': data
        }
        
        logger.info(f"외부 API 호출 완료: {result['data_size']} bytes")
        return result
        
    except Exception as e:
        logger.error(f"외부 API 호출 실패: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e),
            'url': api_url
        }

# 사용자 알림 작업
def send_user_notification_task(
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    사용자 알림 발송 작업
    """
    try:
        logger.info(f"사용자 알림 발송: User {user_id}, Type: {notification_type}")
        
        user = User.objects.get(id=user_id)
        
        # 여기서 실제 알림 시스템과 연동
        # 예: FCM, WebSocket, 이메일 등
        
        # 시뮬레이션: 알림 발송 처리
        time.sleep(2)
        
        result = {
            'status': 'success',
            'user_id': user_id,
            'username': user.username,
            'notification_type': notification_type,
            'title': title,
            'sent_at': time.time(),
            'metadata': metadata or {}
        }
        
        logger.info(f"사용자 알림 발송 완료: {user.username}")
        return result
        
    except User.DoesNotExist:
        error_msg = f"사용자를 찾을 수 없음: {user_id}"
        logger.error(error_msg)
        return {
            'status': 'failed',
            'error': error_msg,
            'user_id': user_id
        }
    except Exception as e:
        logger.error(f"사용자 알림 발송 실패: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e),
            'user_id': user_id
        }
```

### Pydantic 스키마 정의

```python
# api/schemas.py
from ninja import Schema
from pydantic import Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    QUEUED = "queued"
    STARTED = "started"
    FINISHED = "finished"
    FAILED = "failed"
    DEFERRED = "deferred"
    CANCELED = "canceled"

class QueueName(str, Enum):
    DEFAULT = "default"
    HIGH = "high"
    LOW = "low"

# 이메일 작업 스키마
class EmailJobSchema(Schema):
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1)
    recipient_list: List[str] = Field(..., min_items=1)
    from_email: Optional[str] = None
    html_message: Optional[str] = None
    queue: QueueName = QueueName.DEFAULT
    delay: Optional[int] = Field(None, ge=0, description="지연 시간(초)")
    
    @validator('recipient_list')
    def validate_emails(cls, v):
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        for email in v:
            if not re.match(email_pattern, email):
                raise ValueError(f'Invalid email format: {email}')
        return v

# 이미지 처리 작업 스키마
class ImageOperation(Schema):
    type: str = Field(..., regex="^(resize|rotate|convert)$")
    size: Optional[List[int]] = Field(None, min_items=2, max_items=2)
    angle: Optional[float] = None
    format: Optional[str] = Field(None, regex="^(JPEG|PNG|WEBP)$")

class ImageJobSchema(Schema):
    image_url: str = Field(..., regex=r'^https?://.+')
    operations: List[ImageOperation] = Field(..., min_items=1)
    output_filename: str = Field(..., min_length=1)
    queue: QueueName = QueueName.DEFAULT
    delay: Optional[int] = Field(None, ge=0)

# 데이터 분석 작업 스키마
class DataAnalysisJobSchema(Schema):
    data_source: str = Field(..., min_length=1)
    analysis_type: str = Field(..., regex="^(trend|correlation|anomaly|prediction)$")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    queue: QueueName = QueueName.LOW  # 분석 작업은 낮은 우선순위
    delay: Optional[int] = Field(None, ge=0)

# 외부 API 호출 스키마
class ExternalAPIJobSchema(Schema):
    api_url: str = Field(..., regex=r'^https?://.+')
    headers: Optional[Dict[str, str]] = None
    timeout: int = Field(30, ge=1, le=300)
    queue: QueueName = QueueName.DEFAULT
    delay: Optional[int] = Field(None, ge=0)

# 알림 작업 스키마
class NotificationJobSchema(Schema):
    user_id: int = Field(..., gt=0)
    notification_type: str = Field(..., regex="^(email|push|sms|in_app)$")
    title: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=500)
    metadata: Optional[Dict[str, Any]] = None
    queue: QueueName = QueueName.HIGH  # 알림은 높은 우선순위
    delay: Optional[int] = Field(None, ge=0)

# 작업 응답 스키마
class JobResponseSchema(Schema):
    job_id: str
    status: JobStatus
    queue: str
    created_at: datetime
    enqueued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timeout: int
    
class JobListSchema(Schema):
    jobs: List[JobResponseSchema]
    total: int
    queue: str
    
class QueueStatsSchema(Schema):
    name: str
    count: int
    failed_count: int
    deferred_count: int
    started_count: int
    finished_count: int
```

### API 엔드포인트 구현

```python
# api/views.py
from ninja import Router
from django.http import JsonResponse
from django_rq import get_queue, get_connection
from rq import Queue
from rq.job import Job
from rq.registry import (
    StartedJobRegistry, 
    FinishedJobRegistry, 
    FailedJobRegistry,
    DeferredJobRegistry
)
from typing import List, Optional
import json
from datetime import datetime

from tasks.jobs import (
    send_email_task,
    process_image_task,
    analyze_data_task,
    fetch_external_data_task,
    send_user_notification_task
)
from .schemas import *

router = Router()

def job_to_dict(job: Job) -> dict:
    """RQ Job 객체를 딕셔너리로 변환"""
    return {
        'job_id': job.id,
        'status': job.get_status(),
        'queue': job.origin,
        'created_at': job.created_at.isoformat() if job.created_at else None,
        'enqueued_at': job.enqueued_at.isoformat() if job.enqueued_at else None,
        'started_at': job.started_at.isoformat() if job.started_at else None,
        'ended_at': job.ended_at.isoformat() if job.ended_at else None,
        'result': job.result,
        'error': str(job.exc_info) if job.exc_info else None,
        'timeout': job.timeout or 180
    }

@router.post("/email", response=JobResponseSchema, tags=["Jobs"])
async def send_email_job(request, data: EmailJobSchema):
    """이메일 발송 작업 생성"""
    queue = get_queue(data.queue.value)
    
    job = queue.enqueue(
        send_email_task,
        subject=data.subject,
        message=data.message,
        recipient_list=data.recipient_list,
        from_email=data.from_email,
        html_message=data.html_message,
        job_timeout='5m',
        delay=data.delay
    )
    
    return JobResponseSchema(**job_to_dict(job))

@router.post("/image", response=JobResponseSchema, tags=["Jobs"])
async def process_image_job(request, data: ImageJobSchema):
    """이미지 처리 작업 생성"""
    queue = get_queue(data.queue.value)
    
    # 출력 경로 생성
    output_path = f"media/processed/{data.output_filename}"
    operations = [op.dict() for op in data.operations]
    
    job = queue.enqueue(
        process_image_task,
        image_url=data.image_url,
        operations=operations,
        output_path=output_path,
        job_timeout='10m',
        delay=data.delay
    )
    
    return JobResponseSchema(**job_to_dict(job))

@router.post("/analysis", response=JobResponseSchema, tags=["Jobs"])
async def create_analysis_job(request, data: DataAnalysisJobSchema):
    """데이터 분석 작업 생성"""
    queue = get_queue(data.queue.value)
    
    job = queue.enqueue(
        analyze_data_task,
        data_source=data.data_source,
        analysis_type=data.analysis_type,
        parameters=data.parameters,
        job_timeout='30m',
        delay=data.delay
    )
    
    return JobResponseSchema(**job_to_dict(job))

@router.post("/external-api", response=JobResponseSchema, tags=["Jobs"])
async def fetch_external_data_job(request, data: ExternalAPIJobSchema):
    """외부 API 호출 작업 생성"""
    queue = get_queue(data.queue.value)
    
    job = queue.enqueue(
        fetch_external_data_task,
        api_url=data.api_url,
        headers=data.headers,
        timeout=data.timeout,
        job_timeout='5m',
        delay=data.delay
    )
    
    return JobResponseSchema(**job_to_dict(job))

@router.post("/notification", response=JobResponseSchema, tags=["Jobs"])
async def send_notification_job(request, data: NotificationJobSchema):
    """사용자 알림 작업 생성"""
    queue = get_queue(data.queue.value)
    
    job = queue.enqueue(
        send_user_notification_task,
        user_id=data.user_id,
        notification_type=data.notification_type,
        title=data.title,
        message=data.message,
        metadata=data.metadata,
        job_timeout='2m',
        delay=data.delay
    )
    
    return JobResponseSchema(**job_to_dict(job))

@router.get("/job/{job_id}", response=JobResponseSchema, tags=["Monitoring"])
async def get_job_status(request, job_id: str):
    """특정 작업 상태 조회"""
    try:
        connection = get_connection()
        job = Job.fetch(job_id, connection=connection)
        return JobResponseSchema(**job_to_dict(job))
    except Exception as e:
        return JsonResponse({"error": f"Job not found: {str(e)}"}, status=404)

@router.delete("/job/{job_id}", tags=["Monitoring"])
async def cancel_job(request, job_id: str):
    """작업 취소"""
    try:
        connection = get_connection()
        job = Job.fetch(job_id, connection=connection)
        job.cancel()
        return {"message": f"Job {job_id} cancelled successfully"}
    except Exception as e:
        return JsonResponse({"error": f"Failed to cancel job: {str(e)}"}, status=400)

@router.get("/jobs", response=JobListSchema, tags=["Monitoring"])
async def list_jobs(
    request, 
    queue: QueueName = QueueName.DEFAULT,
    status: Optional[JobStatus] = None,
    limit: int = 50
):
    """작업 목록 조회"""
    connection = get_connection()
    q = Queue(queue.value, connection=connection)
    
    jobs = []
    
    if status is None or status == JobStatus.QUEUED:
        jobs.extend(q.jobs)
    
    if status is None or status == JobStatus.STARTED:
        started_registry = StartedJobRegistry(queue.value, connection=connection)
        for job_id in started_registry.get_job_ids():
            try:
                job = Job.fetch(job_id, connection=connection)
                jobs.append(job)
            except:
                continue
    
    if status is None or status == JobStatus.FINISHED:
        finished_registry = FinishedJobRegistry(queue.value, connection=connection)
        for job_id in finished_registry.get_job_ids()[:limit]:
            try:
                job = Job.fetch(job_id, connection=connection)
                jobs.append(job)
            except:
                continue
    
    if status is None or status == JobStatus.FAILED:
        failed_registry = FailedJobRegistry(queue.value, connection=connection)
        for job_id in failed_registry.get_job_ids()[:limit]:
            try:
                job = Job.fetch(job_id, connection=connection)
                jobs.append(job)
            except:
                continue
    
    # 작업을 딕셔너리로 변환
    job_dicts = [job_to_dict(job) for job in jobs[:limit]]
    
    return JobListSchema(
        jobs=job_dicts,
        total=len(job_dicts),
        queue=queue.value
    )

@router.get("/queues/stats", response=List[QueueStatsSchema], tags=["Monitoring"])
async def get_queue_stats(request):
    """모든 큐의 통계 정보"""
    connection = get_connection()
    stats = []
    
    for queue_name in ['default', 'high', 'low']:
        queue = Queue(queue_name, connection=connection)
        
        # 각 레지스트리에서 작업 수 계산
        started_registry = StartedJobRegistry(queue_name, connection=connection)
        finished_registry = FinishedJobRegistry(queue_name, connection=connection)
        failed_registry = FailedJobRegistry(queue_name, connection=connection)
        deferred_registry = DeferredJobRegistry(queue_name, connection=connection)
        
        stats.append(QueueStatsSchema(
            name=queue_name,
            count=len(queue),
            failed_count=len(failed_registry),
            deferred_count=len(deferred_registry),
            started_count=len(started_registry),
            finished_count=len(finished_registry)
        ))
    
    return stats

@router.post("/queues/{queue_name}/clear", tags=["Management"])
async def clear_queue(request, queue_name: str):
    """큐 비우기"""
    try:
        queue = get_queue(queue_name)
        cleared_count = queue.empty()
        return {"message": f"Cleared {cleared_count} jobs from {queue_name} queue"}
    except Exception as e:
        return JsonResponse({"error": f"Failed to clear queue: {str(e)}"}, status=400)

@router.post("/jobs/retry-failed", tags=["Management"])
async def retry_failed_jobs(request, queue: QueueName = QueueName.DEFAULT):
    """실패한 작업 재시도"""
    connection = get_connection()
    failed_registry = FailedJobRegistry(queue.value, connection=connection)
    
    retry_count = 0
    for job_id in failed_registry.get_job_ids():
        try:
            job = Job.fetch(job_id, connection=connection)
            job.retry()
            retry_count += 1
        except:
            continue
    
    return {"message": f"Retried {retry_count} failed jobs in {queue.value} queue"}
```

## 📊 3단계: 모니터링 및 관리

### RQ Dashboard 설정

```python
# rq_dashboard_settings.py
RQ_DASHBOARD_SETTINGS = {
    'REDIS_URL': 'redis://localhost:6379/0',
    'REDIS_PASSWORD': None,
    'REDIS_DB': 0,
    'POLL_INTERVAL': 2500,  # 2.5초마다 업데이트
    'DELETE_JOBS': True,    # 작업 삭제 허용
    'WEB_BACKGROUND': 'white',
}
```

### 커스텀 관리 명령어

```python
# management/commands/rq_monitor.py
from django.core.management.base import BaseCommand
from django_rq import get_connection, get_queue
from rq import Worker
import time

class Command(BaseCommand):
    help = 'RQ 큐 모니터링 명령어'
    
    def add_arguments(self, parser):
        parser.add_argument('--queue', type=str, default='default', help='모니터링할 큐 이름')
        parser.add_argument('--interval', type=int, default=5, help='모니터링 간격(초)')
    
    def handle(self, *args, **options):
        queue_name = options['queue']
        interval = options['interval']
        
        connection = get_connection()
        queue = get_queue(queue_name)
        
        self.stdout.write(f"Monitoring queue: {queue_name}")
        self.stdout.write(f"Update interval: {interval} seconds")
        self.stdout.write("-" * 50)
        
        try:
            while True:
                # 큐 상태 출력
                queued_jobs = len(queue)
                workers = Worker.all(connection=connection)
                active_workers = [w for w in workers if w.state == 'busy']
                
                self.stdout.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                self.stdout.write(f"Queued jobs: {queued_jobs}")
                self.stdout.write(f"Active workers: {len(active_workers)}")
                self.stdout.write(f"Total workers: {len(workers)}")
                
                if active_workers:
                    self.stdout.write("Active jobs:")
                    for worker in active_workers:
                        current_job = worker.get_current_job()
                        if current_job:
                            self.stdout.write(f"  - {current_job.func_name} (ID: {current_job.id})")
                
                self.stdout.write("-" * 50)
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.stdout.write("\nMonitoring stopped.")
```

### 건강 상태 체크 API

```python
# api/health.py
from ninja import Router
from django_rq import get_connection, get_queue
from rq import Worker
import redis

health_router = Router()

@health_router.get("/health", tags=["Health"])
async def health_check(request):
    """시스템 건강 상태 체크"""
    try:
        # Redis 연결 테스트
        connection = get_connection()
        connection.ping()
        
        # 큐 상태 체크
        queues_status = {}
        for queue_name in ['default', 'high', 'low']:
            queue = get_queue(queue_name)
            queues_status[queue_name] = {
                'jobs_count': len(queue),
                'is_empty': queue.is_empty()
            }
        
        # 워커 상태 체크
        workers = Worker.all(connection=connection)
        workers_status = {
            'total': len(workers),
            'active': len([w for w in workers if w.state == 'busy']),
            'idle': len([w for w in workers if w.state == 'idle'])
        }
        
        return {
            'status': 'healthy',
            'redis': 'connected',
            'queues': queues_status,
            'workers': workers_status,
            'timestamp': time.time()
        }
        
    except redis.ConnectionError:
        return {
            'status': 'unhealthy',
            'redis': 'disconnected',
            'error': 'Redis connection failed'
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }
```

## ⚡ 4단계: 성능 최적화

### 워커 설정 최적화

```python
# worker_config.py
import os
from rq import Worker
from django_rq import get_connection

class OptimizedWorker(Worker):
    """최적화된 RQ 워커"""
    
    def __init__(self, *args, **kwargs):
        # 워커별 설정
        kwargs.setdefault('default_result_ttl', 500)  # 결과 보존 시간
        kwargs.setdefault('default_worker_ttl', 420)  # 워커 TTL
        kwargs.setdefault('default_job_timeout', 180)  # 기본 작업 타임아웃
        
        super().__init__(*args, **kwargs)
    
    def work(self, *args, **kwargs):
        """메모리 사용량 모니터링과 함께 작업 처리"""
        import psutil
        process = psutil.Process(os.getpid())
        
        def log_memory_usage():
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            if memory_mb > 500:  # 500MB 초과시 경고
                self.log.warning(f"High memory usage: {memory_mb:.1f}MB")
        
        # 작업 처리 전후 메모리 사용량 체크
        original_perform_job = self.perform_job
        
        def perform_job_with_monitoring(job, queue):
            log_memory_usage()
            result = original_perform_job(job, queue)
            log_memory_usage()
            return result
        
        self.perform_job = perform_job_with_monitoring
        
        return super().work(*args, **kwargs)
```

### 배치 작업 처리

```python
# tasks/batch_jobs.py
from typing import List, Dict, Any
from django_rq import get_queue
import time

def process_batch_emails(email_batches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """이메일 배치 처리"""
    results = []
    failed_count = 0
    
    for batch in email_batches:
        try:
            result = send_email_task(
                subject=batch['subject'],
                message=batch['message'],
                recipient_list=batch['recipients'],
                from_email=batch.get('from_email'),
                html_message=batch.get('html_message')
            )
            results.append(result)
            
            if result['status'] == 'failed':
                failed_count += 1
                
        except Exception as e:
            failed_count += 1
            results.append({
                'status': 'failed',
                'error': str(e),
                'batch': batch
            })
    
    return {
        'total_batches': len(email_batches),
        'successful': len(email_batches) - failed_count,
        'failed': failed_count,
        'results': results
    }

# 배치 작업 API 엔드포인트
@router.post("/batch/emails", response=JobResponseSchema, tags=["Batch"])
async def process_batch_emails_job(request, batches: List[EmailJobSchema]):
    """이메일 배치 처리 작업"""
    queue = get_queue('low')  # 배치 작업은 낮은 우선순위
    
    # 스키마를 딕셔너리로 변환
    batch_data = [batch.dict() for batch in batches]
    
    job = queue.enqueue(
        process_batch_emails,
        email_batches=batch_data,
        job_timeout='30m'
    )
    
    return JobResponseSchema(**job_to_dict(job))
```

### 메모리 최적화

```python
# utils/memory_optimization.py
import gc
import psutil
import os
from functools import wraps

def memory_monitor(threshold_mb: int = 300):
    """메모리 사용량 모니터링 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 작업 전 메모리 사용량
            process = psutil.Process(os.getpid())
            memory_before = process.memory_info().rss / 1024 / 1024
            
            try:
                result = func(*args, **kwargs)
                
                # 작업 후 메모리 사용량
                memory_after = process.memory_info().rss / 1024 / 1024
                memory_used = memory_after - memory_before
                
                # 임계값 초과시 가비지 컬렉션 실행
                if memory_after > threshold_mb:
                    gc.collect()
                    memory_final = process.memory_info().rss / 1024 / 1024
                    print(f"Memory usage: {memory_before:.1f}MB -> {memory_after:.1f}MB -> {memory_final:.1f}MB")
                
                return result
                
            except Exception as e:
                # 예외 발생시에도 메모리 정리
                gc.collect()
                raise e
                
        return wrapper
    return decorator

# 사용 예제
@memory_monitor(threshold_mb=400)
def memory_intensive_task(data_size: int):
    """메모리 집약적 작업 예제"""
    large_data = [i for i in range(data_size)]
    processed_data = [x * 2 for x in large_data]
    return len(processed_data)
```

## 🚀 5단계: 배포 및 운영

### Docker 설정

```dockerfile
# Dockerfile.worker
FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# RQ 워커 실행 스크립트
COPY scripts/start-worker.sh /start-worker.sh
RUN chmod +x /start-worker.sh

CMD ["/start-worker.sh"]
```

```bash
# scripts/start-worker.sh
#!/bin/bash

# 환경 변수 설정
export DJANGO_SETTINGS_MODULE=project.settings.production

# Django 설정 확인
python manage.py check

# RQ 워커 시작
echo "Starting RQ worker for queue: ${QUEUE_NAME:-default}"
python manage.py rqworker ${QUEUE_NAME:-default} \
    --worker-class utils.memory_optimization.OptimizedWorker \
    --verbosity 2
```

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
    restart: unless-stopped

  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DJANGO_SETTINGS_MODULE=project.settings.production
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - redis
    restart: unless-stopped

  worker-default:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      - DJANGO_SETTINGS_MODULE=project.settings.production
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - QUEUE_NAME=default
    depends_on:
      - redis
    restart: unless-stopped
    scale: 2

  worker-high:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      - DJANGO_SETTINGS_MODULE=project.settings.production
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - QUEUE_NAME=high
    depends_on:
      - redis
    restart: unless-stopped
    scale: 1

  worker-low:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      - DJANGO_SETTINGS_MODULE=project.settings.production
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - QUEUE_NAME=low
    depends_on:
      - redis
    restart: unless-stopped
    scale: 3

  rq-dashboard:
    image: eoranged/rq-dashboard
    ports:
      - "9181:9181"
    environment:
      - RQ_DASHBOARD_REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    restart: unless-stopped

volumes:
  redis_data:
```

### 모니터링 및 알림

```python
# monitoring/alerts.py
import smtplib
from email.mime.text import MimeType
from django.conf import settings
from django_rq import get_connection
from rq import Worker
import time

class RQMonitor:
    def __init__(self):
        self.connection = get_connection()
        self.alert_thresholds = {
            'queue_size': 100,      # 큐에 100개 이상 작업이 쌓이면 알림
            'failed_jobs': 10,      # 실패한 작업이 10개 이상이면 알림
            'no_workers': True,     # 워커가 없으면 알림
            'memory_usage': 80      # 메모리 사용률 80% 이상이면 알림
        }
    
    def check_queue_health(self):
        """큐 건강 상태 체크"""
        alerts = []
        
        # 워커 상태 체크
        workers = Worker.all(connection=self.connection)
        if not workers and self.alert_thresholds['no_workers']:
            alerts.append("No RQ workers are running!")
        
        # 각 큐별 상태 체크
        for queue_name in ['default', 'high', 'low']:
            from django_rq import get_queue
            queue = get_queue(queue_name)
            
            # 큐 크기 체크
            queue_size = len(queue)
            if queue_size >= self.alert_thresholds['queue_size']:
                alerts.append(f"Queue '{queue_name}' has {queue_size} pending jobs")
            
            # 실패한 작업 체크
            from rq.registry import FailedJobRegistry
            failed_registry = FailedJobRegistry(queue_name, connection=self.connection)
            failed_count = len(failed_registry)
            if failed_count >= self.alert_thresholds['failed_jobs']:
                alerts.append(f"Queue '{queue_name}' has {failed_count} failed jobs")
        
        return alerts
    
    def send_alert(self, message: str):
        """알림 발송"""
        if not settings.ALERT_EMAIL_RECIPIENTS:
            return
        
        try:
            msg = MimeText(f"""
RQ 모니터링 알림

시간: {time.strftime('%Y-%m-%d %H:%M:%S')}
메시지: {message}

시스템을 확인해주세요.
            """)
            
            msg['Subject'] = f'[RQ Alert] {message}'
            msg['From'] = settings.DEFAULT_FROM_EMAIL
            msg['To'] = ', '.join(settings.ALERT_EMAIL_RECIPIENTS)
            
            with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                if settings.EMAIL_USE_TLS:
                    server.starttls()
                server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                server.send_message(msg)
                
        except Exception as e:
            print(f"Failed to send alert: {e}")

# 모니터링 실행 스크립트
def run_monitoring():
    monitor = RQMonitor()
    
    while True:
        try:
            alerts = monitor.check_queue_health()
            
            for alert in alerts:
                print(f"ALERT: {alert}")
                monitor.send_alert(alert)
            
            time.sleep(60)  # 1분마다 체크
            
        except KeyboardInterrupt:
            print("Monitoring stopped")
            break
        except Exception as e:
            print(f"Monitoring error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_monitoring()
```

### 프로덕션 설정

```python
# settings/production.py
from .base import *
import os

DEBUG = False

# RQ 프로덕션 설정
RQ_QUEUES = {
    'default': {
        'HOST': os.environ.get('REDIS_HOST', 'localhost'),
        'PORT': int(os.environ.get('REDIS_PORT', 6379)),
        'DB': 0,
        'PASSWORD': os.environ.get('REDIS_PASSWORD'),
        'DEFAULT_TIMEOUT': 360,
        'CONNECTION_CLASS': 'redis.connection.Connection',
        'CONNECTION_KWARGS': {
            'health_check_interval': 30,
            'socket_keepalive': True,
            'socket_keepalive_options': {},
        },
    },
    'high': {
        'HOST': os.environ.get('REDIS_HOST', 'localhost'),
        'PORT': int(os.environ.get('REDIS_PORT', 6379)),
        'DB': 1,
        'PASSWORD': os.environ.get('REDIS_PASSWORD'),
        'DEFAULT_TIMEOUT': 180,
        'CONNECTION_CLASS': 'redis.connection.Connection',
    },
    'low': {
        'HOST': os.environ.get('REDIS_HOST', 'localhost'),
        'PORT': int(os.environ.get('REDIS_PORT', 6379)),
        'DB': 2,
        'PASSWORD': os.environ.get('REDIS_PASSWORD'),
        'DEFAULT_TIMEOUT': 600,
        'CONNECTION_CLASS': 'redis.connection.Connection',
    }
}

# 알림 설정
ALERT_EMAIL_RECIPIENTS = os.environ.get('ALERT_EMAIL_RECIPIENTS', '').split(',')

# 로깅 설정
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
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/rq.log',
            'maxBytes': 10485760,  # 10MB
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
        'rq.worker': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'tasks': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

## 🎯 마무리

Django Ninja와 Django RQ를 함께 사용하면 강력하고 확장 가능한 웹 애플리케이션을 구축할 수 있습니다. 이 가이드에서 다룬 내용을 정리하면:

### ✅ 주요 구현 사항
- **완전한 통합**: Django Ninja API와 RQ 백그라운드 작업의 seamless 연동
- **다양한 작업 유형**: 이메일, 이미지 처리, 데이터 분석, API 호출 등
- **우선순위 큐**: high, default, low 큐를 통한 작업 우선순위 관리
- **실시간 모니터링**: 상태 조회, 통계, 건강 체크 API
- **오류 처리**: 실패 작업 재시도, 예외 처리, 로깅

### 🚀 성능 최적화
- **메모리 관리**: 메모리 사용량 모니터링과 가비지 컬렉션
- **배치 처리**: 대량 작업의 효율적 처리
- **연결 풀링**: Redis 연결 최적화
- **워커 스케일링**: Docker Compose를 통한 수평 확장

### 🔧 운영 고려사항
- **컨테이너화**: Docker를 통한 일관된 배포
- **모니터링**: 자동화된 건강 체크와 알림
- **확장성**: 워커 수 조정과 큐 분리
- **안정성**: 재시도 로직과 실패 처리

### 📈 다음 단계
- **고급 스케줄링**: 주기적 작업과 cron 스타일 스케줄링
- **작업 체이닝**: 연관된 작업들의 파이프라인 구성
- **메트릭스 수집**: Prometheus/Grafana 연동
- **CI/CD**: 자동화된 배포 파이프라인

Django RQ는 간단하면서도 강력한 백그라운드 작업 솔루션입니다. 이 가이드를 참고하여 여러분의 프로젝트에 맞는 최적의 구성을 만들어보세요!

> 💡 **팁**: 프로덕션 환경에서는 Redis 클러스터링과 센티널을 고려하여 고가용성을 확보하는 것이 좋습니다.