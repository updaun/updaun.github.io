---
layout: post
title: "Django-Ninja로 구현하는 백그라운드 태스크 관리 전략: LLM 비동기 처리 실전 가이드"
date: 2026-02-12 10:00:00 +0900
categories: [Django, Backend, Async]
tags: [Django-Ninja, Background Tasks, Celery, Redis, LLM, Async, Python, API]
image: "/assets/img/posts/2026-02-12-django-ninja-background-task-management-strategy.webp"
---

## 들어가며

최근 LLM(Large Language Model)을 활용한 데이터 가공 프로세스가 많아지면서, 백엔드에서 오래 걸리는 작업을 효율적으로 처리하는 것이 중요해졌습니다. 예를 들어, 사용자가 업로드한 문서를 GPT-4로 요약하거나, 수집된 데이터를 Claude를 통해 분석하는 작업은 수십 초에서 수분이 걸릴 수 있습니다.

이런 상황에서 동기적으로 처리하면 사용자는 응답을 받기까지 오랜 시간을 기다려야 하고, 서버 리소스도 비효율적으로 사용됩니다. Django-Ninja와 백그라운드 태스크를 조합하면 이 문제를 우아하게 해결할 수 있습니다.

이 글에서는 Django-Ninja를 활용하여 LLM 처리와 같은 무거운 작업을 백그라운드에서 관리하는 실전 전략을 다룹니다.

## 1. 왜 백그라운드 태스크가 필요한가?

### 실제 시나리오: 데이터 분석 파이프라인

웹 크롤러가 뉴스 기사를 수집하고, 각 기사를 LLM으로 요약하는 시스템을 생각해봅시다:

```python
# ❌ 나쁜 예: 동기 처리
@api.post("/articles/analyze")
def analyze_article(request, article_id: int):
    article = Article.objects.get(id=article_id)
    
    # LLM 호출: 10~30초 소요
    summary = llm_service.summarize(article.content)
    keywords = llm_service.extract_keywords(article.content)
    sentiment = llm_service.analyze_sentiment(article.content)
    
    article.summary = summary
    article.keywords = keywords
    article.sentiment = sentiment
    article.save()
    
    return {"status": "completed"}
```

이 코드의 문제점:
- **긴 응답 시간**: 사용자가 30초 이상 대기
- **타임아웃 위험**: 프록시 서버나 브라우저 타임아웃 발생 가능
- **리소스 낭비**: 요청 처리 워커가 대기 상태로 묶임
- **스케일링 난이도**: 동시 요청 처리 능력 제한

### 백그라운드 태스크의 장점

```python
# ✅ 좋은 예: 비동기 처리
@api.post("/articles/analyze")
def analyze_article(request, article_id: int):
    # 태스크를 백그라운드로 전송
    task = analyze_article_task.delay(article_id)
    
    return {
        "status": "processing",
        "task_id": task.id,
        "check_url": f"/api/tasks/{task.id}"
    }
```

이점:
- **즉시 응답**: 0.1초 이내 응답 반환
- **안정성**: 타임아웃 걱정 없음
- **확장성**: 워커 수평 확장 가능
- **모니터링**: 태스크 상태 추적 가능

## 2. Django-Ninja + Celery 아키텍처 구성

### 시스템 구성 요소

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Client    │─────▶│ Django-Ninja │─────▶│   Redis     │
│             │◀─────│   API        │      │  (Broker)   │
└─────────────┘      └──────────────┘      └─────────────┘
                            │                      │
                            │                      ▼
                            │               ┌─────────────┐
                            │               │   Celery    │
                            │               │   Workers   │
                            │               └─────────────┘
                            │                      │
                            ▼                      ▼
                     ┌──────────────────────────────┐
                     │       PostgreSQL             │
                     │  (Task Results & App Data)   │
                     └──────────────────────────────┘
```

### 환경 설정

**1. 필요한 패키지 설치**

```bash
pip install django-ninja celery redis django-celery-results
```

**2. Celery 설정 (celery.py)**

```python
# myproject/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

app = Celery('myproject')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
```

**3. Django 설정 (settings.py)**

```python
# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30분
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25분

# 재시도 설정
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

INSTALLED_APPS = [
    # ...
    'django_celery_results',
]
```

**4. __init__.py 설정**

```python
# myproject/__init__.py
from .celery import app as celery_app

__all__ = ('celery_app',)
```

## 3. 실전 구현: LLM 데이터 가공 시스템

### 모델 정의

```python
# articles/models.py
from django.db import models
from django.contrib.postgres.fields import ArrayField

class Article(models.Model):
    class ProcessStatus(models.TextChoices):
        PENDING = 'pending', '대기중'
        PROCESSING = 'processing', '처리중'
        COMPLETED = 'completed', '완료'
        FAILED = 'failed', '실패'
    
    title = models.CharField(max_length=500)
    content = models.TextField()
    source_url = models.URLField()
    
    # LLM 가공 결과
    summary = models.TextField(blank=True)
    keywords = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        default=list
    )
    sentiment = models.CharField(max_length=20, blank=True)
    
    # 처리 상태 관리
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessStatus.choices,
        default=ProcessStatus.PENDING
    )
    task_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
```

### Celery 태스크 구현

```python
# articles/tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from .models import Article
from .services import LLMService

logger = get_task_logger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1분 후 재시도
)
def process_article_with_llm(self, article_id: int):
    """
    기사를 LLM으로 분석하는 백그라운드 태스크
    """
    try:
        article = Article.objects.get(id=article_id)
        article.processing_status = Article.ProcessStatus.PROCESSING
        article.task_id = self.request.id
        article.save(update_fields=['processing_status', 'task_id'])
        
        logger.info(f"Processing article {article_id}")
        
        # LLM 서비스 호출
        llm_service = LLMService()
        
        # 1. 요약 생성 (10-20초)
        summary = llm_service.summarize(article.content)
        article.summary = summary
        article.save(update_fields=['summary'])
        
        # 2. 키워드 추출 (5-10초)
        keywords = llm_service.extract_keywords(article.content)
        article.keywords = keywords
        article.save(update_fields=['keywords'])
        
        # 3. 감정 분석 (5-10초)
        sentiment = llm_service.analyze_sentiment(article.content)
        article.sentiment = sentiment
        article.save(update_fields=['sentiment'])
        
        # 완료 처리
        article.processing_status = Article.ProcessStatus.COMPLETED
        article.processed_at = timezone.now()
        article.save(update_fields=['processing_status', 'processed_at'])
        
        logger.info(f"Successfully processed article {article_id}")
        return {
            'article_id': article_id,
            'status': 'completed',
            'summary_length': len(summary),
            'keywords_count': len(keywords)
        }
        
    except Article.DoesNotExist:
        logger.error(f"Article {article_id} not found")
        raise
        
    except Exception as exc:
        logger.error(f"Error processing article {article_id}: {str(exc)}")
        
        # 재시도 로직
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        
        # 최종 실패 처리
        article.processing_status = Article.ProcessStatus.FAILED
        article.error_message = str(exc)
        article.save(update_fields=['processing_status', 'error_message'])
        raise
```

### Django-Ninja API 엔드포인트

```python
# articles/api.py
from ninja import NinjaAPI, Schema
from ninja.pagination import paginate
from django.shortcuts import get_object_or_404
from typing import List
from .models import Article
from .tasks import process_article_with_llm

api = NinjaAPI()

# 스키마 정의
class ArticleCreateSchema(Schema):
    title: str
    content: str
    source_url: str

class ArticleResponseSchema(Schema):
    id: int
    title: str
    processing_status: str
    task_id: str = None
    created_at: str

class TaskStatusSchema(Schema):
    task_id: str
    status: str
    article_id: int
    result: dict = None
    error: str = None

@api.post("/articles", response=ArticleResponseSchema)
def create_article(request, payload: ArticleCreateSchema):
    """
    기사 생성 및 LLM 처리 시작
    """
    # 1. 기사 생성
    article = Article.objects.create(
        title=payload.title,
        content=payload.content,
        source_url=payload.source_url
    )
    
    # 2. 백그라운드 태스크 시작
    task = process_article_with_llm.delay(article.id)
    
    # 3. task_id 저장
    article.task_id = task.id
    article.processing_status = Article.ProcessStatus.PROCESSING
    article.save(update_fields=['task_id', 'processing_status'])
    
    return ArticleResponseSchema(
        id=article.id,
        title=article.title,
        processing_status=article.processing_status,
        task_id=task.id,
        created_at=article.created_at.isoformat()
    )

@api.get("/articles/{article_id}")
def get_article(request, article_id: int):
    """
    기사 상세 조회 (처리 결과 포함)
    """
    article = get_object_or_404(Article, id=article_id)
    
    return {
        "id": article.id,
        "title": article.title,
        "content": article.content,
        "summary": article.summary,
        "keywords": article.keywords,
        "sentiment": article.sentiment,
        "processing_status": article.processing_status,
        "task_id": article.task_id,
        "error_message": article.error_message,
        "processed_at": article.processed_at
    }

@api.get("/tasks/{task_id}", response=TaskStatusSchema)
def get_task_status(request, task_id: str):
    """
    태스크 상태 확인
    """
    from celery.result import AsyncResult
    
    task = AsyncResult(task_id)
    
    # Article에서 관련 정보 찾기
    try:
        article = Article.objects.get(task_id=task_id)
        article_id = article.id
    except Article.DoesNotExist:
        article_id = None
    
    response = {
        "task_id": task_id,
        "status": task.state,
        "article_id": article_id
    }
    
    if task.state == 'SUCCESS':
        response["result"] = task.result
    elif task.state == 'FAILURE':
        response["error"] = str(task.info)
    
    return response

@api.get("/articles", response=List[ArticleResponseSchema])
@paginate
def list_articles(request, status: str = None):
    """
    기사 목록 조회 (상태별 필터링)
    """
    queryset = Article.objects.all().order_by('-created_at')
    
    if status:
        queryset = queryset.filter(processing_status=status)
    
    return queryset
```

## 4. LLM 서비스 레이어

### OpenAI/Anthropic 통합

```python
# articles/services.py
import openai
import anthropic
from django.conf import settings
from typing import List
import time
from tenacity import retry, stop_after_attempt, wait_exponential

class LLMService:
    """
    LLM API 호출을 관리하는 서비스 클래스
    """
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def summarize(self, content: str, max_length: int = 200) -> str:
        """
        기사 요약 생성
        """
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": f"다음 기사를 {max_length}자 이내로 요약해주세요. 핵심 내용만 간결하게 작성하세요."
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            raise Exception(f"요약 생성 실패: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def extract_keywords(self, content: str, max_keywords: int = 10) -> List[str]:
        """
        키워드 추출
        """
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": f"다음 기사에서 최대 {max_keywords}개의 핵심 키워드를 추출하세요. 콤마로 구분하여 반환하세요."
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                temperature=0.2,
                max_tokens=200
            )
            
            keywords_text = response.choices[0].message.content.strip()
            keywords = [k.strip() for k in keywords_text.split(',')]
            return keywords[:max_keywords]
            
        except Exception as e:
            raise Exception(f"키워드 추출 실패: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def analyze_sentiment(self, content: str) -> str:
        """
        감정 분석 (긍정/부정/중립)
        """
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=100,
                messages=[
                    {
                        "role": "user",
                        "content": f"다음 기사의 감정을 분석하여 '긍정', '부정', '중립' 중 하나로만 답변하세요:\n\n{content}"
                    }
                ]
            )
            
            sentiment = response.content[0].text.strip()
            
            # 표준화
            if '긍정' in sentiment:
                return '긍정'
            elif '부정' in sentiment:
                return '부정'
            else:
                return '중립'
            
        except Exception as e:
            raise Exception(f"감정 분석 실패: {str(e)}")
    
    def process_batch(self, articles: List[dict]) -> List[dict]:
        """
        여러 기사를 배치로 처리
        """
        results = []
        
        for article in articles:
            try:
                result = {
                    'id': article['id'],
                    'summary': self.summarize(article['content']),
                    'keywords': self.extract_keywords(article['content']),
                    'sentiment': self.analyze_sentiment(article['content'])
                }
                results.append(result)
                
                # API 레이트 리밋 고려
                time.sleep(0.5)
                
            except Exception as e:
                results.append({
                    'id': article['id'],
                    'error': str(e)
                })
        
        return results
```

### 비용 최적화 전략

```python
# articles/services.py (추가)
class CachedLLMService(LLMService):
    """
    캐싱을 통한 비용 최적화
    """
    
    def __init__(self):
        super().__init__()
        from django.core.cache import cache
        self.cache = cache
    
    def _get_cache_key(self, operation: str, content: str) -> str:
        import hashlib
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"llm:{operation}:{content_hash}"
    
    def summarize(self, content: str, max_length: int = 200) -> str:
        cache_key = self._get_cache_key('summary', content)
        cached = self.cache.get(cache_key)
        
        if cached:
            return cached
        
        result = super().summarize(content, max_length)
        
        # 7일간 캐싱
        self.cache.set(cache_key, result, timeout=60*60*24*7)
        
        return result
    
    def extract_keywords(self, content: str, max_keywords: int = 10) -> List[str]:
        cache_key = self._get_cache_key('keywords', content)
        cached = self.cache.get(cache_key)
        
        if cached:
            return cached
        
        result = super().extract_keywords(content, max_keywords)
        
        # 7일간 캐싱
        self.cache.set(cache_key, result, timeout=60*60*24*7)
        
        return result
```

## 5. 프론트엔드 통합: 실시간 상태 업데이트

### React/Vue에서 폴링 방식

```javascript
// ArticleProcessor.jsx
import { useState, useEffect } from 'react';
import axios from 'axios';

function ArticleProcessor() {
  const [article, setArticle] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState('idle');
  const [progress, setProgress] = useState(0);

  // 기사 제출
  const submitArticle = async (articleData) => {
    try {
      const response = await axios.post('/api/articles', articleData);
      setTaskId(response.data.task_id);
      setArticle(response.data);
      setStatus('processing');
      
      // 폴링 시작
      startPolling(response.data.task_id);
    } catch (error) {
      console.error('Failed to submit article:', error);
      setStatus('error');
    }
  };

  // 태스크 상태 폴링
  const startPolling = (taskId) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await axios.get(`/api/tasks/${taskId}`);
        const taskStatus = response.data.status;
        
        if (taskStatus === 'SUCCESS') {
          setStatus('completed');
          setProgress(100);
          clearInterval(pollInterval);
          
          // 완성된 기사 데이터 가져오기
          fetchArticleDetails(response.data.article_id);
        } else if (taskStatus === 'FAILURE') {
          setStatus('error');
          clearInterval(pollInterval);
        } else if (taskStatus === 'PROCESSING') {
          // 진행률 시뮬레이션 (실제로는 태스크에서 progress 반환)
          setProgress(prev => Math.min(prev + 10, 90));
        }
      } catch (error) {
        console.error('Polling error:', error);
        clearInterval(pollInterval);
      }
    }, 2000); // 2초마다 체크

    // 5분 후 타임아웃
    setTimeout(() => clearInterval(pollInterval), 5 * 60 * 1000);
  };

  const fetchArticleDetails = async (articleId) => {
    const response = await axios.get(`/api/articles/${articleId}`);
    setArticle(response.data);
  };

  return (
    <div className="article-processor">
      {status === 'idle' && (
        <ArticleForm onSubmit={submitArticle} />
      )}
      
      {status === 'processing' && (
        <ProgressIndicator progress={progress} />
      )}
      
      {status === 'completed' && article && (
        <ArticleResult
          summary={article.summary}
          keywords={article.keywords}
          sentiment={article.sentiment}
        />
      )}
      
      {status === 'error' && (
        <ErrorMessage message="처리 중 오류가 발생했습니다." />
      )}
    </div>
  );
}
```

### WebSocket으로 실시간 알림 (고급)

```python
# articles/consumers.py (Django Channels)
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Article

class ArticleProcessConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.article_id = self.scope['url_route']['kwargs']['article_id']
        self.room_group_name = f'article_{self.article_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def article_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'article_update',
            'data': event['data']
        }))
```

```python
# articles/tasks.py에 추가
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@shared_task(bind=True)
def process_article_with_llm(self, article_id: int):
    channel_layer = get_channel_layer()
    
    try:
        article = Article.objects.get(id=article_id)
        
        # 요약 완료 알림
        summary = llm_service.summarize(article.content)
        article.summary = summary
        article.save()
        
        async_to_sync(channel_layer.group_send)(
            f'article_{article_id}',
            {
                'type': 'article_update',
                'data': {
                    'step': 'summary_completed',
                    'progress': 33
                }
            }
        )
        
        # 키워드 완료 알림
        keywords = llm_service.extract_keywords(article.content)
        article.keywords = keywords
        article.save()
        
        async_to_sync(channel_layer.group_send)(
            f'article_{article_id}',
            {
                'type': 'article_update',
                'data': {
                    'step': 'keywords_completed',
                    'progress': 66
                }
            }
        )
        
        # 감정 분석 완료 알림
        sentiment = llm_service.analyze_sentiment(article.content)
        article.sentiment = sentiment
        article.processing_status = Article.ProcessStatus.COMPLETED
        article.save()
        
        async_to_sync(channel_layer.group_send)(
            f'article_{article_id}',
            {
                'type': 'article_update',
                'data': {
                    'step': 'all_completed',
                    'progress': 100,
                    'result': {
                        'summary': summary,
                        'keywords': keywords,
                        'sentiment': sentiment
                    }
                }
            }
        )
        
    except Exception as exc:
        async_to_sync(channel_layer.group_send)(
            f'article_{article_id}',
            {
                'type': 'article_update',
                'data': {
                    'step': 'error',
                    'error': str(exc)
                }
            }
        )
        raise
```

```javascript
// WebSocket 클라이언트
function ArticleProcessorWithWebSocket({ articleId }) {
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);

  useEffect(() => {
    const ws = new WebSocket(
      `ws://localhost:8000/ws/articles/${articleId}/`
    );

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'article_update') {
        setProgress(data.data.progress);
        
        if (data.data.step === 'all_completed') {
          setResult(data.data.result);
        }
      }
    };

    return () => ws.close();
  }, [articleId]);

  return (
    <div>
      <ProgressBar value={progress} />
      {result && <ResultDisplay result={result} />}
    </div>
  );
}
```

## 6. 모니터링 및 에러 핸들링

### Flower로 Celery 모니터링

```bash
# Flower 설치 및 실행
pip install flower

# Flower 시작
celery -A myproject flower --port=5555
```

브라우저에서 `http://localhost:5555` 접속하면:
- 실행 중인 태스크 현황
- 워커 상태 및 성능
- 태스크 성공/실패 통계
- 개별 태스크 실행 히스토리

### Sentry 통합

```python
# settings.py
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
    ],
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
)
```

```python
# articles/tasks.py
from sentry_sdk import capture_exception, capture_message

@shared_task(bind=True)
def process_article_with_llm(self, article_id: int):
    try:
        # ... 처리 로직
        pass
    except Exception as exc:
        # Sentry에 에러 리포트
        capture_exception(exc)
        
        # 추가 컨텍스트 전달
        with sentry_sdk.push_scope() as scope:
            scope.set_context("article", {
                "id": article_id,
                "retry_count": self.request.retries
            })
            capture_message(
                f"Article {article_id} processing failed after {self.request.retries} retries",
                level="error"
            )
        
        raise
```

### 커스텀 에러 핸들링

```python
# articles/exceptions.py
class LLMProcessingError(Exception):
    """LLM 처리 관련 에러"""
    pass

class LLMRateLimitError(LLMProcessingError):
    """API 레이트 리밋 초과"""
    pass

class LLMTimeoutError(LLMProcessingError):
    """API 타임아웃"""
    pass

# articles/tasks.py
@shared_task(
    bind=True,
    autoretry_for=(LLMRateLimitError, LLMTimeoutError),
    retry_backoff=True,
    retry_backoff_max=600,  # 최대 10분
    retry_jitter=True,
    max_retries=5
)
def process_article_with_llm(self, article_id: int):
    try:
        # ... 처리 로직
        pass
    except openai.RateLimitError as e:
        raise LLMRateLimitError(f"OpenAI rate limit: {str(e)}")
    except openai.Timeout as e:
        raise LLMTimeoutError(f"OpenAI timeout: {str(e)}")
```

### 메트릭 수집

```python
# articles/tasks.py
from django.core.cache import cache
import time

@shared_task(bind=True)
def process_article_with_llm(self, article_id: int):
    start_time = time.time()
    
    try:
        # ... 처리 로직
        
        # 성공 메트릭
        processing_time = time.time() - start_time
        cache.incr('metrics:articles:processed:success')
        cache.lpush('metrics:articles:processing_times', processing_time)
        
        return {
            'article_id': article_id,
            'processing_time': processing_time
        }
        
    except Exception as exc:
        # 실패 메트릭
        cache.incr('metrics:articles:processed:failure')
        raise

# 메트릭 조회 API
@api.get("/metrics/articles")
def get_article_metrics(request):
    success_count = cache.get('metrics:articles:processed:success') or 0
    failure_count = cache.get('metrics:articles:processed:failure') or 0
    processing_times = cache.lrange('metrics:articles:processing_times', 0, 99)
    
    avg_time = sum(float(t) for t in processing_times) / len(processing_times) if processing_times else 0
    
    return {
        'total_processed': success_count + failure_count,
        'success_count': success_count,
        'failure_count': failure_count,
        'success_rate': success_count / (success_count + failure_count) if (success_count + failure_count) > 0 else 0,
        'average_processing_time': round(avg_time, 2)
    }
```

## 7. 성능 최적화 전략

### 배치 처리

여러 기사를 한 번에 처리하여 API 호출 최적화:

```python
# articles/tasks.py
@shared_task
def process_articles_batch(article_ids: List[int]):
    """
    여러 기사를 배치로 처리
    """
    articles = Article.objects.filter(id__in=article_ids)
    
    # 모든 컨텐츠를 한 번에 준비
    contents = [
        {"id": article.id, "content": article.content}
        for article in articles
    ]
    
    # 배치 처리
    llm_service = CachedLLMService()
    results = llm_service.process_batch(contents)
    
    # 결과 저장
    for result in results:
        if 'error' not in result:
            article = Article.objects.get(id=result['id'])
            article.summary = result['summary']
            article.keywords = result['keywords']
            article.sentiment = result['sentiment']
            article.processing_status = Article.ProcessStatus.COMPLETED
            article.save()

# API 엔드포인트
@api.post("/articles/batch")
def create_articles_batch(request, articles: List[ArticleCreateSchema]):
    """
    여러 기사를 한 번에 생성하고 배치 처리
    """
    created_articles = []
    
    for article_data in articles:
        article = Article.objects.create(
            title=article_data.title,
            content=article_data.content,
            source_url=article_data.source_url
        )
        created_articles.append(article)
    
    # 배치 태스크 시작
    article_ids = [a.id for a in created_articles]
    task = process_articles_batch.delay(article_ids)
    
    return {
        "created_count": len(created_articles),
        "task_id": task.id,
        "article_ids": article_ids
    }
```

### 우선순위 큐

중요한 태스크를 먼저 처리:

```python
# settings.py
CELERY_TASK_ROUTES = {
    'articles.tasks.process_article_with_llm': {'queue': 'default'},
    'articles.tasks.process_urgent_article': {'queue': 'high_priority'},
    'articles.tasks.daily_batch_process': {'queue': 'low_priority'},
}

# articles/tasks.py
@shared_task(queue='high_priority')
def process_urgent_article(article_id: int):
    """
    긴급 기사 우선 처리
    """
    # ... 처리 로직
    pass

# Celery 워커 실행 (여러 큐 처리)
# celery -A myproject worker -Q high_priority,default,low_priority -c 4
```

### 동적 타임아웃

기사 길이에 따라 동적 타임아웃 설정:

```python
@shared_task(bind=True)
def process_article_with_llm(self, article_id: int):
    article = Article.objects.get(id=article_id)
    
    # 컨텐츠 길이 기반 타임아웃 계산
    content_length = len(article.content)
    estimated_time = (content_length / 1000) * 5  # 1000자당 5초
    timeout = max(60, min(600, estimated_time))  # 1분~10분
    
    # 동적 타임아웃 적용
    self.update_state(
        state='PROCESSING',
        meta={'timeout': timeout}
    )
    
    # 처리 로직...
```

### 부분 결과 저장

LLM 호출마다 중간 결과를 저장하여 실패 시 재시작 최소화:

```python
@shared_task(bind=True)
def process_article_with_llm(self, article_id: int):
    article = Article.objects.get(id=article_id)
    llm_service = LLMService()
    
    # 1. 요약 (이미 완료되었으면 스킵)
    if not article.summary:
        article.summary = llm_service.summarize(article.content)
        article.save(update_fields=['summary'])
    
    # 2. 키워드 (이미 완료되었으면 스킵)
    if not article.keywords:
        article.keywords = llm_service.extract_keywords(article.content)
        article.save(update_fields=['keywords'])
    
    # 3. 감정 분석 (이미 완료되었으면 스킵)
    if not article.sentiment:
        article.sentiment = llm_service.analyze_sentiment(article.content)
        article.save(update_fields=['sentiment'])
    
    # 모든 처리 완료
    article.processing_status = Article.ProcessStatus.COMPLETED
    article.processed_at = timezone.now()
    article.save(update_fields=['processing_status', 'processed_at'])
```

### 연결 풀링

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mydb',
        'USER': 'myuser',
        'PASSWORD': 'mypass',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,  # 10분간 연결 유지
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Redis 연결 풀링
CELERY_BROKER_POOL_LIMIT = 10
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
```

## 8. 실전 운영 팁

### 로컬 개발 환경 설정

```bash
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: myuser
      POSTGRES_PASSWORD: mypass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  celery_worker:
    build: .
    command: celery -A myproject worker -l info -c 2
    depends_on:
      - redis
      - postgres
    environment:
      - DJANGO_SETTINGS_MODULE=myproject.settings
      - CELERY_BROKER_URL=redis://redis:6379/0
    volumes:
      - .:/app

  celery_beat:
    build: .
    command: celery -A myproject beat -l info
    depends_on:
      - redis
      - postgres
    environment:
      - DJANGO_SETTINGS_MODULE=myproject.settings
      - CELERY_BROKER_URL=redis://redis:6379/0
    volumes:
      - .:/app

  flower:
    build: .
    command: celery -A myproject flower --port=5555
    ports:
      - "5555:5555"
    depends_on:
      - redis
      - celery_worker
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0

volumes:
  redis_data:
  postgres_data:
```

```bash
# 로컬 개발 시작
docker-compose up -d

# Django 서버 실행
python manage.py runserver

# API 테스트
curl -X POST http://localhost:8000/api/articles \
  -H "Content-Type: application/json" \
  -d '{
    "title": "테스트 기사",
    "content": "이것은 테스트 기사 내용입니다...",
    "source_url": "https://example.com/article/1"
  }'
```

### 프로덕션 배포

```bash
# requirements.txt
Django==5.0.0
django-ninja==1.1.0
celery==5.3.4
redis==5.0.1
django-celery-results==2.5.1
psycopg2-binary==2.9.9
openai==1.10.0
anthropic==0.18.0
tenacity==8.2.3
sentry-sdk==1.40.0
flower==2.0.1
gunicorn==21.2.0
```

```bash
# Supervisor 설정 (celery_worker.conf)
[program:celery_worker]
command=/path/to/venv/bin/celery -A myproject worker -l info -c 4 --max-tasks-per-child=1000
directory=/path/to/project
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker_error.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
stopasgroup=true
killasgroup=true

[program:celery_beat]
command=/path/to/venv/bin/celery -A myproject beat -l info
directory=/path/to/project
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/beat.log
stderr_logfile=/var/log/celery/beat_error.log
autostart=true
autorestart=true
startsecs=10
```

### 주기적인 태스크 정리

```python
# articles/tasks.py
from celery import shared_task
from celery.schedules import crontab
from django.utils import timezone
from datetime import timedelta

@shared_task
def cleanup_old_tasks():
    """
    완료된 태스크 정리 (30일 이상 된 것)
    """
    from django_celery_results.models import TaskResult
    
    threshold = timezone.now() - timedelta(days=30)
    deleted_count = TaskResult.objects.filter(
        date_done__lt=threshold
    ).delete()[0]
    
    return f"Deleted {deleted_count} old tasks"

@shared_task
def retry_failed_articles():
    """
    실패한 기사 재처리
    """
    failed_articles = Article.objects.filter(
        processing_status=Article.ProcessStatus.FAILED,
        created_at__gte=timezone.now() - timedelta(hours=24)
    )
    
    for article in failed_articles:
        process_article_with_llm.delay(article.id)
    
    return f"Retrying {failed_articles.count()} failed articles"

# settings.py에 추가
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'cleanup-old-tasks': {
        'task': 'articles.tasks.cleanup_old_tasks',
        'schedule': crontab(hour=2, minute=0),  # 매일 새벽 2시
    },
    'retry-failed-articles': {
        'task': 'articles.tasks.retry_failed_articles',
        'schedule': crontab(hour='*/6'),  # 6시간마다
    },
}
```

### 테스트 작성

```python
# articles/tests.py
from django.test import TestCase
from unittest.mock import patch, MagicMock
from .tasks import process_article_with_llm
from .models import Article

class ArticleProcessingTestCase(TestCase):
    
    def setUp(self):
        self.article = Article.objects.create(
            title="Test Article",
            content="This is a test article content for LLM processing.",
            source_url="https://example.com/test"
        )
    
    @patch('articles.tasks.LLMService')
    def test_successful_processing(self, mock_llm_service):
        # Mock LLM responses
        mock_service = mock_llm_service.return_value
        mock_service.summarize.return_value = "Test summary"
        mock_service.extract_keywords.return_value = ["test", "article"]
        mock_service.analyze_sentiment.return_value = "긍정"
        
        # Execute task
        result = process_article_with_llm(self.article.id)
        
        # Assertions
        self.article.refresh_from_db()
        self.assertEqual(self.article.summary, "Test summary")
        self.assertEqual(self.article.keywords, ["test", "article"])
        self.assertEqual(self.article.sentiment, "긍정")
        self.assertEqual(
            self.article.processing_status,
            Article.ProcessStatus.COMPLETED
        )
    
    @patch('articles.tasks.LLMService')
    def test_processing_failure_and_retry(self, mock_llm_service):
        # Mock LLM failure
        mock_service = mock_llm_service.return_value
        mock_service.summarize.side_effect = Exception("API Error")
        
        # Execute task (should fail)
        with self.assertRaises(Exception):
            process_article_with_llm(self.article.id)
        
        # Check failure status
        self.article.refresh_from_db()
        self.assertEqual(
            self.article.processing_status,
            Article.ProcessStatus.FAILED
        )
        self.assertIn("API Error", self.article.error_message)
```

### 로깅 전략

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
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/celery.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'celery': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'articles.tasks': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    },
}
```

## 9. 비용 관리 및 LLM API 최적화

### API 호출 비용 추적

```python
# articles/models.py
class ArticleProcessingCost(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    operation = models.CharField(max_length=50)  # summarize, keywords, sentiment
    tokens_used = models.IntegerField()
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6)
    model_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

# articles/services.py
class LLMService:
    # 모델별 비용 (1000 토큰당 USD)
    PRICING = {
        'gpt-4-turbo-preview': {'input': 0.01, 'output': 0.03},
        'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
        'claude-3-sonnet': {'input': 0.003, 'output': 0.015},
    }
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = self.PRICING.get(model, {'input': 0, 'output': 0})
        input_cost = (input_tokens / 1000) * pricing['input']
        output_cost = (output_tokens / 1000) * pricing['output']
        return input_cost + output_cost
    
    def summarize(self, content: str, max_length: int = 200) -> str:
        response = self.openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[...],
            temperature=0.3,
            max_tokens=500
        )
        
        # 비용 계산 및 저장
        usage = response.usage
        cost = self._calculate_cost(
            'gpt-4-turbo-preview',
            usage.prompt_tokens,
            usage.completion_tokens
        )
        
        # 비용 기록 (별도 태스크에서 저장)
        from .tasks import record_api_cost
        record_api_cost.delay(
            article_id=self.current_article_id,
            operation='summarize',
            tokens=usage.total_tokens,
            cost=cost,
            model='gpt-4-turbo-preview'
        )
        
        return response.choices[0].message.content.strip()

# articles/tasks.py
@shared_task
def record_api_cost(article_id: int, operation: str, tokens: int, cost: float, model: str):
    """
    API 비용 기록
    """
    from .models import ArticleProcessingCost
    
    ArticleProcessingCost.objects.create(
        article_id=article_id,
        operation=operation,
        tokens_used=tokens,
        estimated_cost=cost,
        model_name=model
    )
```

### 비용 모니터링 대시보드

```python
# articles/api.py
@api.get("/metrics/costs")
def get_cost_metrics(request, days: int = 30):
    """
    비용 통계 조회
    """
    from django.db.models import Sum, Avg, Count
    from datetime import timedelta
    
    threshold = timezone.now() - timedelta(days=days)
    
    costs = ArticleProcessingCost.objects.filter(
        created_at__gte=threshold
    ).aggregate(
        total_cost=Sum('estimated_cost'),
        total_tokens=Sum('tokens_used'),
        avg_cost_per_article=Avg('estimated_cost'),
        total_operations=Count('id')
    )
    
    # 작업별 비용
    by_operation = ArticleProcessingCost.objects.filter(
        created_at__gte=threshold
    ).values('operation').annotate(
        total_cost=Sum('estimated_cost'),
        count=Count('id')
    )
    
    # 모델별 비용
    by_model = ArticleProcessingCost.objects.filter(
        created_at__gte=threshold
    ).values('model_name').annotate(
        total_cost=Sum('estimated_cost'),
        count=Count('id')
    )
    
    return {
        'period_days': days,
        'total_cost_usd': float(costs['total_cost'] or 0),
        'total_tokens': costs['total_tokens'] or 0,
        'avg_cost_per_article': float(costs['avg_cost_per_article'] or 0),
        'total_operations': costs['total_operations'],
        'by_operation': list(by_operation),
        'by_model': list(by_model),
        'daily_average_usd': float(costs['total_cost'] or 0) / days
    }
```

### 비용 절감 전략

```python
# articles/services.py
class CostOptimizedLLMService(CachedLLMService):
    """
    비용 최적화된 LLM 서비스
    """
    
    def summarize(self, content: str, max_length: int = 200) -> str:
        # 1. 캐시 확인
        cached = self._get_from_cache('summary', content)
        if cached:
            return cached
        
        # 2. 짧은 컨텐츠는 GPT-3.5 사용 (비용 95% 절감)
        content_length = len(content)
        model = "gpt-3.5-turbo" if content_length < 2000 else "gpt-4-turbo-preview"
        
        # 3. 프롬프트 최적화 (토큰 절약)
        if content_length > 4000:
            # 긴 컨텐츠는 청크 단위로 요약 후 재요약
            chunks = self._split_content(content, chunk_size=2000)
            chunk_summaries = [
                self._summarize_chunk(chunk, model="gpt-3.5-turbo")
                for chunk in chunks
            ]
            combined = " ".join(chunk_summaries)
            result = self._summarize_chunk(combined, model=model)
        else:
            result = self._call_openai(content, model)
        
        # 4. 캐시 저장
        self._save_to_cache('summary', content, result)
        
        return result
    
    def _split_content(self, content: str, chunk_size: int = 2000) -> List[str]:
        """
        컨텐츠를 청크로 분할
        """
        words = content.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1
            
            if current_length >= chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
```

### 월별 예산 알림

```python
# articles/tasks.py
@shared_task
def check_monthly_budget():
    """
    월별 예산 초과 확인 및 알림
    """
    from django.core.mail import send_mail
    from datetime import datetime
    
    # 이번 달 시작일
    today = timezone.now()
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 이번 달 총 비용
    total_cost = ArticleProcessingCost.objects.filter(
        created_at__gte=month_start
    ).aggregate(total=Sum('estimated_cost'))['total'] or 0
    
    budget_limit = 1000  # USD
    usage_percent = (float(total_cost) / budget_limit) * 100
    
    if usage_percent >= 80:
        # 예산 80% 초과 시 알림
        send_mail(
            subject=f'⚠️ LLM API 예산 {usage_percent:.1f}% 사용',
            message=f'''
            현재 월간 LLM API 사용 비용: ${total_cost:.2f}
            예산: ${budget_limit:.2f}
            사용률: {usage_percent:.1f}%
            
            남은 예산: ${budget_limit - float(total_cost):.2f}
            ''',
            from_email='noreply@example.com',
            recipient_list=['admin@example.com'],
        )
    
    return {
        'total_cost': float(total_cost),
        'budget_limit': budget_limit,
        'usage_percent': usage_percent
    }

# settings.py에 추가
CELERY_BEAT_SCHEDULE = {
    'check-monthly-budget': {
        'task': 'articles.tasks.check_monthly_budget',
        'schedule': crontab(hour=9, minute=0),  # 매일 오전 9시
    },
}
```

## 마치며

Django-Ninja와 Celery를 조합한 백그라운드 태스크 관리는 LLM을 활용한 데이터 가공 시스템에서 필수적인 아키텍처 패턴입니다. 이 글에서 다룬 전략들을 정리하면:

### 핵심 포인트

**1. 아키텍처 설계**
- Django-Ninja: 빠른 API 개발과 타입 안전성
- Celery: 안정적인 백그라운드 태스크 처리
- Redis: 고성능 메시지 브로커
- PostgreSQL: 태스크 결과 및 애플리케이션 데이터 저장

**2. 성능 최적화**
- 캐싱으로 중복 LLM 호출 방지
- 배치 처리로 API 호출 최소화
- 우선순위 큐로 중요 작업 우선 처리
- 부분 결과 저장으로 재시작 비용 최소화

**3. 안정성 확보**
- 자동 재시도 메커니즘
- Sentry 통합으로 에러 추적
- Flower로 실시간 모니터링
- 메트릭 수집으로 성능 분석

**4. 비용 관리**
- API 호출 비용 추적
- 모델 선택 최적화 (GPT-3.5 vs GPT-4)
- 월별 예산 알림
- 컨텐츠 길이 기반 전략 선택

### 실무 적용 가이드

**시작 단계**
```bash
# 1. 기본 설정
pip install django-ninja celery redis django-celery-results

# 2. 로컬 환경 구축
docker-compose up -d redis postgres

# 3. Celery 워커 시작
celery -A myproject worker -l info

# 4. API 서버 시작
python manage.py runserver
```

**확장 단계**
- WebSocket으로 실시간 진행 상황 표시
- 여러 워커로 수평 확장
- 프로덕션 환경 배포 (Supervisor/systemd)
- 모니터링 대시보드 구축

### 추가 학습 리소스

- [Django-Ninja 공식 문서](https://django-ninja.rest-framework.com/)
- [Celery 공식 문서](https://docs.celeryproject.org/)
- [Flower 모니터링 가이드](https://flower.readthedocs.io/)
- [OpenAI API 베스트 프랙티스](https://platform.openai.com/docs/guides/production-best-practices)

### 다음 단계

이 아키텍처를 기반으로 다음과 같은 고급 기능을 추가할 수 있습니다:

- **멀티 모델 전략**: 작업별로 최적 모델 자동 선택
- **A/B 테스트**: 프롬프트 버전별 품질 비교
- **스트리밍 응답**: LLM 출력을 실시간으로 전송
- **분산 처리**: 여러 서버에 걸친 워커 클러스터
- **ML Ops**: 모델 성능 모니터링 및 자동 최적화

백그라운드 태스크 관리는 단순한 기술적 선택이 아니라, 사용자 경험과 시스템 안정성, 운영 비용을 모두 개선하는 핵심 전략입니다. LLM을 활용한 서비스를 개발한다면 이 패턴을 적극 활용해보세요.

---

**관련 글**
- [Django 5.0 & 5.1 주요 기능 리뷰](/posts/django-5.0-5.1-major-features-review/)
- AWS 서버리스 아키텍처와의 비교
- 프로덕션 Django 성능 튜닝 가이드
