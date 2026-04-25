---
layout: post
title: "FastAPI + LangGraph MSA 환경에서 LLM Streaming API 성능 최적화 완벽 가이드"
date: 2025-12-17 09:00:00 +0900
categories: [Backend, Performance, AI]
tags: [FastAPI, LangGraph, LLM, MSA, Redis, RAG, VectorDB, Performance, Streaming, Optimization]
description: "FastAPI와 LangGraph 기반 MSA LLM Streaming API의 성능을 획기적으로 향상시키는 실전 최적화 기법"
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-12-17-fastapi-langgraph-llm-api-performance-optimization.webp"
---

## 목차

1. [소개 - 시스템 아키텍처 개요](#1-소개---시스템-아키텍처-개요)
2. [현재 시스템 분석 및 병목 지점 식별](#2-현재-시스템-분석-및-병목-지점-식별)
3. [FastAPI 성능 최적화](#3-fastapi-성능-최적화)
4. [LangGraph 워크플로우 최적화](#4-langgraph-워크플로우-최적화)
5. [Redis Checkpoint 최적화](#5-redis-checkpoint-최적화)
6. [Vector DB & RAG 최적화](#6-vector-db--rag-최적화)
7. [Streaming 응답 최적화](#7-streaming-응답-최적화)
8. [MSA 레벨 최적화](#8-msa-레벨-최적화)
9. [모니터링 및 프로파일링](#9-모니터링-및-프로파일링)
10. [결론 및 최적화 체크리스트](#10-결론-및-최적화-체크리스트)

---

## 1. 소개 - 시스템 아키텍처 개요

### 1.1 기술 스택 소개

현대적인 LLM 서비스는 다양한 기술의 조합으로 구성됩니다. 본 가이드에서 다루는 시스템은 다음과 같은 기술 스택을 사용합니다:

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│                    (Web/Mobile/API Client)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway                              │
│              (Load Balancer + Rate Limiter)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┬─────────────┐
        ▼                             ▼             ▼
┌───────────────┐            ┌────────────────┐  ┌─────────────┐
│   FastAPI     │            │   FastAPI      │  │  FastAPI    │
│   Service 1   │            │   Service 2    │  │  Service N  │
│               │            │                │  │             │
│  - LangGraph  │            │  - LangGraph   │  │ - LangGraph │
│  - RAG Logic  │            │  - RAG Logic   │  │ - RAG Logic │
└───────┬───────┘            └────────┬───────┘  └──────┬──────┘
        │                             │                  │
        └──────────────┬──────────────┴──────────────────┘
                       │
        ┌──────────────┴──────────────┬─────────────┐
        ▼                             ▼             ▼
┌───────────────┐            ┌────────────────┐  ┌─────────────┐
│     Redis     │            │   Vector DB    │  │  LLM API    │
│  (Checkpoint) │            │  (Chroma/Qdrant│  │  (OpenAI/   │
│               │            │   /Pinecone)   │  │   Anthropic)│
└───────────────┘            └────────────────┘  └─────────────┘
```

**핵심 구성 요소:**

1. **FastAPI**: 고성능 비동기 Python 웹 프레임워크
2. **LangGraph**: LLM 워크플로우 오케스트레이션 (상태 관리, 그래프 기반 실행)
3. **Redis**: Checkpoint 저장 및 캐싱
4. **Vector DB**: 임베딩 검색 (RAG)
5. **LLM Provider**: OpenAI, Anthropic, 자체 모델 등

### 1.2 시스템 특성

**Streaming API의 특징:**

```python
# 일반적인 Streaming API 구조
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        async for chunk in langgraph_workflow.astream(
            {"messages": request.messages},
            config={"configurable": {"thread_id": request.thread_id}}
        ):
            # 1. Redis에서 checkpoint 로드
            # 2. Vector DB에서 관련 문서 검색 (RAG)
            # 3. LLM API 호출
            # 4. 결과 스트리밍
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

**성능 요구사항:**

| 지표 | 목표 | 현재 (최적화 전) |
|------|------|------------------|
| 첫 토큰 응답 시간 (TTFT) | < 500ms | 1.2s ~ 2.5s |
| 토큰당 처리 시간 | < 50ms | 80ms ~ 150ms |
| 동시 처리 요청 | 500+ | 200 ~ 300 |
| 메모리 사용량 | < 2GB per instance | 3.5GB ~ 4.5GB |
| Redis 레이턴시 | < 10ms | 25ms ~ 50ms |
| Vector 검색 속도 | < 100ms | 300ms ~ 600ms |

### 1.3 성능 병목의 주요 원인

**일반적인 성능 저하 요인:**

```python
# ❌ 안티패턴 예시
async def process_chat(message: str, thread_id: str):
    # 문제 1: 동기 블로킹 호출
    checkpoint = redis_client.get(f"checkpoint:{thread_id}")  # 🔴 블로킹
    
    # 문제 2: 매번 임베딩 생성
    embedding = await openai.embeddings.create(input=message)  # 🔴 중복 계산
    
    # 문제 3: 순차 실행
    docs = await vector_db.search(embedding)  # ⏳ 대기
    response = await llm.generate(context=docs)  # ⏳ 대기
    
    # 문제 4: 체크포인트 저장 시 블로킹
    redis_client.set(f"checkpoint:{thread_id}", checkpoint)  # 🔴 블로킹
```

**최적화 필요 영역:**

1. 🔴 **I/O 병목**: Redis, Vector DB, LLM API 호출
2. 🔴 **메모리 병목**: 대규모 컨텍스트, 임베딩 캐싱
3. 🔴 **CPU 병목**: 임베딩 생성, 텍스트 전처리
4. 🔴 **네트워크 병목**: 서비스 간 통신, 외부 API 호출

### 1.4 최적화 전략 개요

**성능 최적화는 다음 레벨로 진행됩니다:**

```
Level 1: 코드 레벨 최적화
  ├─ 비동기 I/O 최대 활용
  ├─ 불필요한 연산 제거
  └─ 효율적인 데이터 구조

Level 2: 인프라 레벨 최적화
  ├─ Redis 파이프라이닝
  ├─ Vector DB 인덱스 튜닝
  └─ 커넥션 풀 관리

Level 3: 아키텍처 레벨 최적화
  ├─ 캐싱 전략
  ├─ 배치 처리
  └─ 병렬 실행

Level 4: 시스템 레벨 최적화
  ├─ 수평 확장 (Scale-out)
  ├─ 로드 밸런싱
  └─ CDN 및 엣지 캐싱
```

**최적화 우선순위 결정 (Pareto 원칙):**

```python
# 성능 프로파일링 결과 예시
{
    "total_request_time": "2.5s",
    "breakdown": {
        "vector_search": "0.6s (24%)",      # 👈 1순위 최적화
        "llm_api_call": "1.2s (48%)",       # 👈 2순위 (외부 의존)
        "checkpoint_load": "0.3s (12%)",    # 👈 3순위 최적화
        "embedding_generation": "0.2s (8%)",
        "preprocessing": "0.2s (8%)"
    }
}
```

> **💡 핵심 원칙**: 측정하지 않으면 최적화할 수 없습니다. 항상 프로파일링부터 시작하세요!

다음 섹션에서는 현재 시스템을 정확히 분석하고 병목 지점을 식별하는 방법을 알아보겠습니다.

---

## 2. 현재 시스템 분석 및 병목 지점 식별

### 2.1 성능 측정 도구 설정

최적화의 첫 단계는 정확한 측정입니다. 다음 도구들을 활용하여 시스템을 분석합니다.

**기본 프로파일링 미들웨어:**

```python
# middleware/profiling.py
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict
import json

logger = logging.getLogger(__name__)

class ProfilingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 요청 메타데이터
        request.state.timings = {}
        
        # 응답 처리
        response = await call_next(request)
        
        # 총 처리 시간
        total_time = time.time() - start_time
        
        # 로깅
        logger.info(json.dumps({
            "path": request.url.path,
            "method": request.method,
            "total_time": f"{total_time:.3f}s",
            "timings": getattr(request.state, "timings", {}),
            "status_code": response.status_code
        }))
        
        # 응답 헤더에 타이밍 정보 추가
        response.headers["X-Process-Time"] = str(total_time)
        
        return response


# 타이밍 컨텍스트 매니저
class Timer:
    def __init__(self, request: Request, name: str):
        self.request = request
        self.name = name
        self.start = None
    
    def __enter__(self):
        self.start = time.time()
        return self
    
    def __exit__(self, *args):
        duration = time.time() - self.start
        if hasattr(self.request.state, "timings"):
            self.request.state.timings[self.name] = f"{duration:.3f}s"
```

**사용 예시:**

```python
# main.py
from fastapi import FastAPI, Request
from middleware.profiling import ProfilingMiddleware, Timer

app = FastAPI()
app.add_middleware(ProfilingMiddleware)

@app.post("/chat/stream")
async def chat_stream(request: Request, chat_request: ChatRequest):
    # Redis checkpoint 로드 측정
    with Timer(request, "redis_load"):
        checkpoint = await redis_client.get(f"checkpoint:{chat_request.thread_id}")
    
    # Vector 검색 측정
    with Timer(request, "vector_search"):
        docs = await vector_db.search(chat_request.query, k=5)
    
    # LLM 호출 측정
    with Timer(request, "llm_generation"):
        async for chunk in langgraph_app.astream(
            {"messages": chat_request.messages},
            config={"configurable": {"thread_id": chat_request.thread_id}}
        ):
            yield chunk
```

### 2.2 병목 지점 식별

**Python cProfile 활용:**

```python
# profiling/cpu_profiler.py
import cProfile
import pstats
import io
from functools import wraps

def profile_function(func):
    """함수 단위 CPU 프로파일링"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        
        result = await func(*args, **kwargs)
        
        profiler.disable()
        
        # 결과 출력
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats('cumulative')
        stats.print_stats(20)  # 상위 20개 함수
        
        print(f"\n=== Profile for {func.__name__} ===")
        print(stream.getvalue())
        
        return result
    
    return wrapper


# 사용 예시
@profile_function
async def process_rag_query(query: str):
    embedding = await generate_embedding(query)
    results = await vector_db.search(embedding)
    return results
```

**메모리 프로파일링 (memory_profiler):**

```python
# requirements.txt에 추가
# memory-profiler==0.61.0

# profiling/memory_profiler.py
from memory_profiler import profile

@profile
async def load_large_checkpoint(thread_id: str):
    """메모리 사용량 추적"""
    checkpoint = await redis_client.get(f"checkpoint:{thread_id}")
    
    # 대용량 체크포인트 처리
    parsed = json.loads(checkpoint)  # 🔍 메모리 사용량 측정
    
    return parsed
```

### 2.3 실제 프로파일링 결과 분석

**Case Study: 실제 병목 지점 발견**

```python
# 프로파일링 결과 예시
"""
=== Request: POST /chat/stream ===
Total Time: 2.45s

Breakdown:
  redis_load:        0.28s  (11.4%)  🟡 최적화 가능
  vector_search:     0.65s  (26.5%)  🔴 주요 병목
  embedding_gen:     0.18s  (7.3%)   🟢 양호
  llm_api_call:      1.15s  (46.9%)  🔴 외부 의존
  checkpoint_save:   0.19s  (7.8%)   🟡 최적화 가능

Memory Usage:
  Peak: 3.8 GB
  Checkpoint data: 450 MB  🔴 과다
  Vector cache: 1.2 GB     🟡 최적화 가능
  Model context: 2.1 GB    🔴 과다
"""
```

**병목 지점 우선순위:**

```python
# profiling/bottleneck_analyzer.py
from dataclasses import dataclass
from typing import List
import statistics

@dataclass
class BottleneckReport:
    component: str
    avg_time: float
    p95_time: float
    p99_time: float
    percentage: float
    severity: str  # HIGH, MEDIUM, LOW
    
    @property
    def optimization_priority(self) -> int:
        """최적화 우선순위 (1-10)"""
        if self.percentage > 20 and self.p95_time > 0.5:
            return 10  # 긴급
        elif self.percentage > 15 or self.p95_time > 0.3:
            return 7   # 높음
        elif self.percentage > 10:
            return 5   # 중간
        else:
            return 3   # 낮음


class PerformanceAnalyzer:
    def __init__(self):
        self.metrics = []
    
    def analyze(self, timings: List[Dict]) -> List[BottleneckReport]:
        """타이밍 데이터를 분석하여 병목 보고서 생성"""
        reports = []
        
        for component in ["redis_load", "vector_search", "llm_api_call"]:
            times = [t.get(component, 0) for t in timings if component in t]
            
            if not times:
                continue
            
            total_avg = statistics.mean([sum(t.values()) for t in timings])
            
            report = BottleneckReport(
                component=component,
                avg_time=statistics.mean(times),
                p95_time=statistics.quantiles(times, n=20)[18],  # 95th percentile
                p99_time=statistics.quantiles(times, n=100)[98], # 99th percentile
                percentage=(statistics.mean(times) / total_avg) * 100,
                severity="HIGH" if statistics.mean(times) > 0.5 else "MEDIUM"
            )
            
            reports.append(report)
        
        # 우선순위로 정렬
        return sorted(reports, key=lambda r: r.optimization_priority, reverse=True)
```

### 2.4 주요 병목 지점 정리

**1. Vector Search (26.5% - 최우선 최적화 대상)**

```python
# 문제 코드
async def rag_query(query: str):
    # 🔴 문제: 매번 임베딩 생성
    embedding = await openai_client.embeddings.create(
        input=query,
        model="text-embedding-ada-002"
    )
    
    # 🔴 문제: 비효율적인 검색 (인덱스 미사용)
    results = await vector_db.similarity_search(
        embedding.data[0].embedding,
        k=10  # 너무 많은 결과
    )
    
    return results
```

**최적화 방향:**
- ✅ 임베딩 캐싱 (Redis)
- ✅ 검색 결과 수 줄이기 (k=10 → k=3)
- ✅ HNSW 인덱스 활용
- ✅ 배치 검색 구현

**2. Redis Checkpoint (11.4% - 중요도 높음)**

```python
# 문제 코드
async def save_checkpoint(thread_id: str, state: Dict):
    # 🔴 문제: 동기 블로킹 호출
    redis_client.set(
        f"checkpoint:{thread_id}",
        json.dumps(state),  # 🔴 압축 없음
        ex=3600
    )
```

**최적화 방향:**
- ✅ 비동기 Redis 클라이언트 사용 (redis.asyncio)
- ✅ 데이터 압축 (gzip)
- ✅ 파이프라이닝 활용
- ✅ TTL 최적화

**3. LLM API Call (46.9% - 외부 의존)**

```python
# 문제: 외부 API 의존도가 높음
# 최적화가 제한적이지만 개선 가능한 부분:
# - 프롬프트 최적화 (토큰 수 감소)
# - Streaming 버퍼링
# - 타임아웃 설정
```

**최적화 방향:**
- ✅ 프롬프트 토큰 최적화 (컨텍스트 압축)
- ✅ 병렬 요청 (여러 모델 동시 호출)
- ✅ Fallback 전략 (타임아웃 시 캐시된 응답)

### 2.5 성능 목표 설정

**측정 결과 기반 목표:**

| 구성 요소 | 현재 (P95) | 목표 (P95) | 개선율 |
|-----------|-----------|-----------|--------|
| Vector Search | 650ms | 150ms | 77% ↓ |
| Redis Load | 280ms | 50ms | 82% ↓ |
| Checkpoint Save | 190ms | 30ms | 84% ↓ |
| Total TTFT | 2.5s | 500ms | 80% ↓ |
| Throughput | 200 req/s | 800 req/s | 300% ↑ |

**최적화 로드맵:**

```
Week 1-2: 빠른 성과 (Quick Wins)
  ├─ Redis 비동기 전환
  ├─ Vector 검색 k값 조정
  └─ 불필요한 로깅 제거
  예상 개선: 30-40%

Week 3-4: 중급 최적화
  ├─ 임베딩 캐싱 구현
  ├─ Redis 파이프라이닝
  └─ LangGraph 노드 병렬화
  예상 개선: 추가 30-40%

Week 5-6: 고급 최적화
  ├─ Vector DB 인덱스 튜닝
  ├─ Checkpoint 압축
  └─ MSA 레벨 캐싱
  예상 개선: 추가 20-30%
```

다음 섹션에서는 FastAPI 레벨에서의 구체적인 성능 최적화 기법을 다루겠습니다.

---

## 3. FastAPI 성능 최적화

### 3.1 비동기 I/O 완전 활용

FastAPI는 비동기를 기본으로 지원하지만, 실수로 동기 코드를 사용하면 성능이 크게 저하됩니다.

**❌ 안티패턴 - 동기 블로킹 코드:**

```python
# BAD: 동기 Redis 클라이언트
import redis

redis_client = redis.Redis(host='localhost', port=6379)

@app.post("/chat")
async def chat(request: ChatRequest):
    # ⚠️ 비동기 함수에서 동기 호출 - 이벤트 루프 블로킹!
    checkpoint = redis_client.get(f"checkpoint:{request.thread_id}")
    
    # ⚠️ 순차 실행 - 불필요한 대기
    embedding = await generate_embedding(request.query)
    docs = await vector_search(embedding)
    
    return {"response": "..."}
```

**✅ 최적화 - 완전한 비동기 구현:**

```python
# GOOD: 비동기 Redis 클라이언트
import redis.asyncio as redis
from typing import List, Tuple
import asyncio

# 비동기 Redis 클라이언트 초기화
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True,
    max_connections=50  # 커넥션 풀 크기
)

@app.post("/chat")
async def chat(request: ChatRequest):
    # ✅ 병렬 실행 (asyncio.gather)
    checkpoint, embedding = await asyncio.gather(
        redis_client.get(f"checkpoint:{request.thread_id}"),
        generate_embedding(request.query)
    )
    
    # Vector 검색은 임베딩 결과가 필요하므로 순차 실행
    docs = await vector_search(embedding)
    
    return {"response": "..."}
```

**성능 개선 측정:**

```python
# Before: 순차 실행
# redis_get: 50ms + embedding: 150ms = 200ms

# After: 병렬 실행
# max(redis_get: 50ms, embedding: 150ms) = 150ms
# 개선: 25% 단축
```

### 3.2 커넥션 풀 최적화

**문제: 매 요청마다 커넥션 생성**

```python
# ❌ BAD: 커넥션 재사용 없음
@app.post("/chat")
async def chat(request: ChatRequest):
    # 매번 새로운 Redis 커넥션 생성
    redis_client = await redis.from_url("redis://localhost")
    data = await redis_client.get("key")
    await redis_client.close()  # 커넥션 닫기
```

**✅ 최적화: 커넥션 풀 사용**

```python
# GOOD: 전역 커넥션 풀
from contextlib import asynccontextmanager

# 애플리케이션 생명주기 관리
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 커넥션 풀 초기화
    app.state.redis = redis.Redis(
        host='localhost',
        port=6379,
        max_connections=100,  # 최대 커넥션 수
        socket_keepalive=True,
        socket_connect_timeout=5,
        retry_on_timeout=True
    )
    
    # Vector DB 커넥션도 초기화
    app.state.vector_db = await init_vector_db()
    
    yield
    
    # 종료 시 정리
    await app.state.redis.close()
    await app.state.vector_db.close()

app = FastAPI(lifespan=lifespan)

@app.post("/chat")
async def chat(request: Request, chat_request: ChatRequest):
    # 재사용 가능한 커넥션 사용
    redis_client = request.app.state.redis
    data = await redis_client.get("key")
```

**외부 API 커넥션 풀 (httpx):**

```python
# httpx로 LLM API 호출 시 커넥션 풀
import httpx

@asynccontextmanager
async def lifespan(app: FastAPI):
    # HTTP 클라이언트 풀
    app.state.http_client = httpx.AsyncClient(
        limits=httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20
        ),
        timeout=httpx.Timeout(30.0)
    )
    
    yield
    
    await app.state.http_client.aclose()

# LLM API 호출
async def call_llm_api(prompt: str, http_client: httpx.AsyncClient):
    response = await http_client.post(
        "https://api.openai.com/v1/chat/completions",
        json={"model": "gpt-4", "messages": [{"role": "user", "content": prompt}]},
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}
    )
    return response.json()
```

### 3.3 응답 캐싱 전략

**API 응답 캐싱 (Redis + 데코레이터):**

```python
# utils/cache.py
from functools import wraps
import json
import hashlib
from typing import Callable, Any

def cache_response(
    ttl: int = 300,  # 5분
    key_prefix: str = "cache"
):
    """API 응답 캐싱 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            redis_client = request.app.state.redis
            
            # 캐시 키 생성 (요청 파라미터 기반)
            cache_key_data = {
                "path": str(request.url),
                "args": str(args),
                "kwargs": str(kwargs)
            }
            cache_key = f"{key_prefix}:{hashlib.md5(json.dumps(cache_key_data).encode()).hexdigest()}"
            
            # 캐시 확인
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # 캐시 미스 - 실제 함수 실행
            result = await func(request, *args, **kwargs)
            
            # 결과 캐싱
            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result)
            )
            
            return result
        
        return wrapper
    return decorator


# 사용 예시
@app.get("/popular-queries")
@cache_response(ttl=3600, key_prefix="popular")  # 1시간 캐싱
async def get_popular_queries(request: Request):
    # 무거운 쿼리
    results = await db.execute("SELECT ... FROM ... GROUP BY ...")
    return {"queries": results}
```

**조건부 캐싱 (사용자별):**

```python
from fastapi import Depends

def get_cache_key(user_id: str, query: str) -> str:
    """사용자별 캐시 키 생성"""
    return f"user:{user_id}:query:{hashlib.md5(query.encode()).hexdigest()}"

@app.post("/chat")
async def chat(
    request: Request,
    chat_request: ChatRequest,
    user_id: str = Depends(get_current_user)
):
    redis_client = request.app.state.redis
    cache_key = get_cache_key(user_id, chat_request.query)
    
    # 동일한 질문에 대한 캐시 확인
    cached_response = await redis_client.get(cache_key)
    if cached_response and not chat_request.force_new:
        return json.loads(cached_response)
    
    # 새로운 응답 생성
    response = await generate_response(chat_request)
    
    # 캐싱 (5분)
    await redis_client.setex(cache_key, 300, json.dumps(response))
    
    return response
```

### 3.4 미들웨어 최적화

**❌ 비효율적인 미들웨어:**

```python
# BAD: 동기 미들웨어가 모든 요청을 블로킹
class SlowMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # ⚠️ 동기 로깅 - 파일 I/O 블로킹
        with open("access.log", "a") as f:
            f.write(f"{request.url}\n")
        
        response = await call_next(request)
        
        # ⚠️ 동기 DB 쿼리
        db.execute("INSERT INTO access_log ...")
        
        return response
```

**✅ 최적화된 미들웨어:**

```python
# GOOD: 비동기 + 백그라운드 작업
from fastapi import BackgroundTasks
import aiofiles

class OptimizedMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 빠른 응답 먼저
        response = await call_next(request)
        
        # 로깅은 백그라운드에서
        asyncio.create_task(self.log_async(request))
        
        return response
    
    async def log_async(self, request: Request):
        """비동기 로깅"""
        async with aiofiles.open("access.log", "a") as f:
            await f.write(f"{request.url}\n")
```

**조건부 미들웨어 적용:**

```python
# 특정 경로에만 미들웨어 적용
from starlette.middleware.base import BaseHTTPMiddleware

class ConditionalMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # /admin 경로에만 인증 체크
        if request.url.path.startswith("/admin"):
            # 인증 로직
            pass
        
        return await call_next(request)
```

### 3.5 백그라운드 작업 활용

**무거운 작업을 백그라운드로:**

```python
from fastapi import BackgroundTasks

async def send_analytics(user_id: str, action: str):
    """분석 데이터 전송 (무거운 작업)"""
    await asyncio.sleep(2)  # 외부 API 호출 시뮬레이션
    print(f"Analytics sent for {user_id}")

@app.post("/chat")
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks
):
    # 즉시 응답 생성
    response = await generate_response(request.query)
    
    # 백그라운드에서 분석 데이터 전송
    background_tasks.add_task(send_analytics, request.user_id, "chat")
    
    # 로깅도 백그라운드에서
    background_tasks.add_task(log_conversation, request, response)
    
    return response
```

### 3.6 Request Body 크기 제한

**대용량 요청으로 인한 메모리 폭발 방지:**

```python
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 1024 * 1024):  # 1MB
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        # Content-Length 확인
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            raise HTTPException(
                status_code=413,
                detail=f"Request body too large. Max size: {self.max_size} bytes"
            )
        
        return await call_next(request)

app.add_middleware(RequestSizeLimitMiddleware, max_size=5 * 1024 * 1024)  # 5MB
```

### 3.7 Response 압축

**Gzip 압축으로 네트워크 전송 최적화:**

```python
from fastapi.middleware.gzip import GZipMiddleware

# Gzip 압축 활성화
app.add_middleware(GZipMiddleware, minimum_size=1000)  # 1KB 이상만 압축

# 압축 효과 측정
"""
Before:
  Response size: 250 KB
  Transfer time: 500ms (on 4Mbps)

After (gzip):
  Compressed size: 45 KB (82% reduction)
  Transfer time: 90ms (on 4Mbps)
  
총 개선: 410ms (82% 단축)
"""
```

### 3.8 Worker 설정 최적화

**Uvicorn 설정:**

```python
# main.py
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=4,  # CPU 코어 수에 맞춰 조정
        loop="uvloop",  # 더 빠른 이벤트 루프
        http="httptools",  # 더 빠른 HTTP 파서
        log_level="warning",  # 프로덕션에서는 warning 이상만
        access_log=False,  # 액세스 로그 비활성화 (성능 향상)
        limit_concurrency=1000,  # 최대 동시 연결 수
        limit_max_requests=10000,  # Worker 재시작 전 처리할 최대 요청 수
        timeout_keep_alive=5  # Keep-alive 타임아웃
    )
```

**Gunicorn + Uvicorn Worker:**

```bash
# 프로덕션 배포 시
gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --max-requests 10000 \
    --max-requests-jitter 1000
```

### 3.9 성능 개선 요약

**FastAPI 최적화 체크리스트:**

```python
# ✅ 적용된 최적화
optimizations = {
    "async_io": {
        "status": "완료",
        "improvement": "25-30%",
        "notes": "모든 I/O를 비동기로 전환"
    },
    "connection_pooling": {
        "status": "완료",
        "improvement": "15-20%",
        "notes": "Redis, HTTP, DB 커넥션 풀"
    },
    "response_caching": {
        "status": "완료",
        "improvement": "40-60% (캐시 히트 시)",
        "notes": "자주 요청되는 데이터 캐싱"
    },
    "middleware_optimization": {
        "status": "완료",
        "improvement": "10-15%",
        "notes": "백그라운드 작업 활용"
    },
    "compression": {
        "status": "완료",
        "improvement": "80% (전송 시간)",
        "notes": "Gzip 압축"
    }
}

# 예상 총 개선: 50-70% (캐시 미스 시), 80-90% (캐시 히트 시)
```

다음 섹션에서는 LangGraph 워크플로우 최적화를 다루겠습니다.

---

## 4. LangGraph 워크플로우 최적화

### 4.1 LangGraph 구조 이해

LangGraph는 LLM 애플리케이션을 위한 상태 기반 워크플로우 프레임워크입니다.

**기본 LangGraph 구조:**

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Annotated
import operator

# 상태 정의
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    context: str
    retrieved_docs: list
    final_response: str

# 노드 함수 정의
async def retrieve_node(state: AgentState):
    """문서 검색 노드"""
    query = state["messages"][-1]
    docs = await vector_db.search(query, k=3)
    return {"retrieved_docs": docs}

async def generate_node(state: AgentState):
    """LLM 생성 노드"""
    context = "\n".join(state["retrieved_docs"])
    response = await llm.ainvoke(state["messages"], context=context)
    return {"final_response": response}

# 그래프 구성
workflow = StateGraph(AgentState)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generate_node)
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)

# Checkpoint 설정
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)
```

### 4.2 노드 병렬 실행

**❌ 순차 실행 (느림):**

```python
# BAD: 독립적인 작업을 순차 실행
async def process_node(state: AgentState):
    # 300ms
    user_context = await load_user_context(state["user_id"])
    
    # 400ms
    relevant_docs = await vector_search(state["query"])
    
    # 200ms
    recent_history = await load_conversation_history(state["thread_id"])
    
    # 총 시간: 900ms
    return {
        "context": user_context,
        "docs": relevant_docs,
        "history": recent_history
    }
```

**✅ 병렬 실행 (빠름):**

```python
# GOOD: 독립적인 작업을 병렬 실행
import asyncio

async def process_node_optimized(state: AgentState):
    # 병렬 실행
    user_context, relevant_docs, recent_history = await asyncio.gather(
        load_user_context(state["user_id"]),
        vector_search(state["query"]),
        load_conversation_history(state["thread_id"])
    )
    
    # 총 시간: max(300ms, 400ms, 200ms) = 400ms
    # 개선: 55% 단축 (900ms → 400ms)
    
    return {
        "context": user_context,
        "docs": relevant_docs,
        "history": recent_history
    }
```

### 4.3 조건부 실행 (불필요한 노드 스킵)

**스마트 라우팅으로 불필요한 노드 제거:**

```python
from langgraph.graph import StateGraph, END

# 조건 함수
def should_retrieve(state: AgentState) -> str:
    """RAG가 필요한지 판단"""
    query = state["messages"][-1].content
    
    # 간단한 질문은 RAG 스킵
    simple_patterns = ["안녕", "감사", "hi", "hello", "thanks"]
    if any(pattern in query.lower() for pattern in simple_patterns):
        return "skip_retrieval"
    
    # 캐시 확인
    cached = check_cache(query)
    if cached:
        return "use_cache"
    
    return "do_retrieval"

# 그래프에 조건부 엣지 추가
workflow = StateGraph(AgentState)
workflow.add_node("classify", classify_query)
workflow.add_node("retrieve", retrieve_docs)
workflow.add_node("use_cache", load_from_cache)
workflow.add_node("generate", generate_response)

workflow.set_entry_point("classify")

# 조건부 라우팅
workflow.add_conditional_edges(
    "classify",
    should_retrieve,
    {
        "skip_retrieval": "generate",  # RAG 없이 바로 생성
        "use_cache": "use_cache",      # 캐시 사용
        "do_retrieval": "retrieve"     # 정상 RAG 플로우
    }
)

workflow.add_edge("retrieve", "generate")
workflow.add_edge("use_cache", "generate")
workflow.add_edge("generate", END)
```

**성능 개선:**

```python
# Case 1: 간단한 인사 (RAG 스킵)
# Before: classify(50ms) + retrieve(400ms) + generate(800ms) = 1250ms
# After:  classify(50ms) + generate(800ms) = 850ms
# 개선: 32% 단축

# Case 2: 캐시된 쿼리
# Before: 1250ms
# After:  classify(50ms) + cache(20ms) + generate(200ms) = 270ms
# 개선: 78% 단축
```

### 4.4 Checkpoint 최적화

**Redis 기반 Checkpoint 최적화:**

```python
from langgraph.checkpoint.redis import RedisSaver
import redis.asyncio as redis
import pickle
import gzip

class OptimizedRedisSaver(RedisSaver):
    """최적화된 Redis Checkpoint Saver"""
    
    def __init__(self, redis_client: redis.Redis):
        super().__init__(redis_client)
        self.compression_threshold = 1024  # 1KB 이상만 압축
    
    async def aput(self, config, checkpoint, metadata):
        """Checkpoint 저장 (압축 + 비동기)"""
        thread_id = config["configurable"]["thread_id"]
        key = f"checkpoint:{thread_id}"
        
        # 직렬화
        data = pickle.dumps(checkpoint)
        
        # 압축 (1KB 이상일 때만)
        if len(data) > self.compression_threshold:
            data = gzip.compress(data, compresslevel=6)
            key += ":compressed"
        
        # 비동기 저장 (TTL 설정)
        await self.redis_client.setex(key, 3600, data)  # 1시간
        
        # 메타데이터도 저장
        await self.redis_client.hset(
            f"checkpoint_meta:{thread_id}",
            mapping={
                "created_at": metadata.get("created_at"),
                "size": len(data),
                "compressed": len(data) > self.compression_threshold
            }
        )
    
    async def aget(self, config):
        """Checkpoint 로드 (압축 해제 + 비동기)"""
        thread_id = config["configurable"]["thread_id"]
        
        # 압축된 데이터 확인
        compressed_key = f"checkpoint:{thread_id}:compressed"
        normal_key = f"checkpoint:{thread_id}"
        
        data = await self.redis_client.get(compressed_key)
        if data:
            # 압축 해제
            data = gzip.decompress(data)
        else:
            data = await self.redis_client.get(normal_key)
        
        if not data:
            return None
        
        # 역직렬화
        checkpoint = pickle.loads(data)
        return checkpoint

# 사용
redis_client = redis.Redis(host='localhost', port=6379)
checkpointer = OptimizedRedisSaver(redis_client)
app = workflow.compile(checkpointer=checkpointer)
```

**메모리 절감 효과:**

```python
# Before: 비압축
checkpoint_size = 4.5 MB

# After: gzip 압축
compressed_size = 850 KB  # 81% 감소

# Redis 메모리 절약: 100개 세션 기준
# Before: 4.5 MB × 100 = 450 MB
# After:  850 KB × 100 = 85 MB
# 절약: 365 MB (81%)
```

### 4.5 상태 크기 최소화

**❌ 불필요한 데이터를 상태에 저장:**

```python
# BAD: 모든 것을 상태에 저장
class AgentState(TypedDict):
    messages: list  # 전체 메시지 히스토리 (수백 개)
    all_retrieved_docs: list  # 모든 검색 문서 (수 MB)
    raw_embeddings: list  # 원본 임베딩 (불필요)
    intermediate_results: list  # 중간 결과 전부
    debug_info: dict  # 디버그 정보 (프로덕션에 불필요)
```

**✅ 필수 데이터만 상태에 저장:**

```python
# GOOD: 필요한 최소한의 데이터만
from typing import TypedDict, Annotated
import operator

class OptimizedAgentState(TypedDict):
    # 최근 N개 메시지만 유지
    messages: Annotated[list, operator.add]
    
    # 문서 ID만 저장 (전체 내용 제외)
    doc_ids: list[str]
    
    # 최종 응답만
    response: str
    
    # 메타데이터
    user_id: str
    thread_id: str

# 메시지 제한
def limit_messages(messages: list, max_messages: int = 10):
    """최근 N개 메시지만 유지"""
    return messages[-max_messages:]

async def generate_node(state: OptimizedAgentState):
    # 메시지 개수 제한
    limited_messages = limit_messages(state["messages"])
    
    # 문서는 ID로만 참조 (필요 시 Redis에서 로드)
    docs = await load_docs_by_ids(state["doc_ids"])
    
    response = await llm.ainvoke(limited_messages, context=docs)
    return {"response": response}
```

**메모리 절감:**

```python
# Before: 전체 데이터 저장
state_size = {
    "messages": 2.5 MB,      # 전체 히스토리
    "docs": 3.8 MB,          # 전체 문서 내용
    "embeddings": 1.2 MB,    # 임베딩
    "debug": 0.5 MB          # 디버그 정보
}
total = 8.0 MB

# After: 필수 데이터만
optimized_size = {
    "messages": 150 KB,      # 최근 10개만
    "doc_ids": 5 KB,         # ID만
    "response": 50 KB        # 최종 응답만
}
optimized_total = 205 KB

# 개선: 97.4% 감소 (8.0 MB → 205 KB)
```

### 4.6 LLM 호출 최적화

**스트리밍 + 조기 종료:**

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def generate_with_streaming(messages: list, max_tokens: int = 500):
    """스트리밍으로 응답 생성 + 조기 종료"""
    collected_messages = []
    
    stream = await client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=max_tokens,
        stream=True,  # 스트리밍 활성화
        temperature=0.7
    )
    
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            collected_messages.append(content)
            
            # 조기 종료 조건 (예: 충분한 답변)
            full_text = "".join(collected_messages)
            if len(full_text) > 200 and full_text.endswith((".", "!", "?")):
                # 더 이상 생성하지 않고 종료
                break
            
            # 실시간으로 청크 반환 (클라이언트로)
            yield content
    
    return "".join(collected_messages)
```

**배치 처리 (여러 요청 동시 처리):**

```python
async def process_batch(queries: list[str]) -> list[str]:
    """여러 쿼리를 배치로 처리"""
    # 병렬로 LLM 호출
    tasks = [
        client.chat.completions.create(
            model="gpt-3.5-turbo",  # 빠른 모델 사용
            messages=[{"role": "user", "content": q}],
            max_tokens=100
        )
        for q in queries
    ]
    
    responses = await asyncio.gather(*tasks)
    return [r.choices[0].message.content for r in responses]

# 사용 예시
queries = ["질문 1", "질문 2", "질문 3"]
results = await process_batch(queries)  # 병렬 처리

# Before: 순차 처리
# Time: 800ms × 3 = 2400ms

# After: 병렬 처리
# Time: max(800ms) = 800ms
# 개선: 66% 단축
```

### 4.7 그래프 구조 최적화

**복잡한 그래프 vs 단순한 그래프:**

```python
# ❌ 너무 복잡한 그래프 (불필요한 노드)
workflow = StateGraph(AgentState)
workflow.add_node("input_validation", validate_input)      # 50ms
workflow.add_node("preprocessing", preprocess)             # 30ms
workflow.add_node("intent_classification", classify)       # 100ms
workflow.add_node("entity_extraction", extract)            # 80ms
workflow.add_node("context_loading", load_context)         # 200ms
workflow.add_node("retrieval", retrieve)                   # 400ms
workflow.add_node("reranking", rerank)                     # 150ms
workflow.add_node("synthesis", synthesize)                 # 100ms
workflow.add_node("generation", generate)                  # 800ms
workflow.add_node("postprocessing", postprocess)           # 50ms
workflow.add_node("validation", validate_output)           # 40ms

# 총 시간: 2000ms+

# ✅ 단순하고 효율적인 그래프
workflow = StateGraph(AgentState)
workflow.add_node("prepare", prepare_context)   # 통합: 280ms
workflow.add_node("retrieve", smart_retrieve)   # 통합: 450ms
workflow.add_node("generate", generate)         # 800ms

# 총 시간: 1530ms
# 개선: 23% 단축
```

### 4.8 실전 예제: 최적화된 LangGraph 앱

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.redis import RedisSaver
import redis.asyncio as redis
from typing import TypedDict, Annotated, Literal
import operator
import asyncio

# 최적화된 상태 정의
class OptimizedState(TypedDict):
    messages: Annotated[list, operator.add]
    query: str
    doc_ids: list[str]
    response: str
    cache_key: str

# 노드 1: 병렬 준비
async def prepare_node(state: OptimizedState):
    """컨텍스트 준비 (병렬 실행)"""
    query = state["messages"][-1].content
    
    # 병렬 실행: 캐시 확인 + 임베딩 생성
    cache_result, embedding = await asyncio.gather(
        check_query_cache(query),
        generate_embedding_cached(query)  # 임베딩도 캐싱
    )
    
    if cache_result:
        return {
            "response": cache_result["response"],
            "cache_key": cache_result["key"]
        }
    
    return {"query": query, "embedding": embedding}

# 노드 2: 스마트 검색
async def retrieve_node(state: OptimizedState):
    """조건부 검색 (필요시에만)"""
    if state.get("response"):  # 캐시 히트 시 스킵
        return {}
    
    # 효율적인 검색 (k=3만)
    doc_ids = await vector_db.search_ids(
        state["embedding"],
        k=3,
        use_index=True  # HNSW 인덱스 사용
    )
    
    return {"doc_ids": doc_ids}

# 노드 3: 스트리밍 생성
async def generate_node(state: OptimizedState):
    """스트리밍 생성"""
    if state.get("response"):  # 캐시 히트 시 스킵
        return {}
    
    # 문서 로드 (ID만 전달받았으므로)
    docs = await load_docs_by_ids(state["doc_ids"])
    
    # 스트리밍 생성
    response = await generate_with_streaming(
        state["messages"],
        context=docs,
        max_tokens=500
    )
    
    # 캐시 저장 (백그라운드)
    asyncio.create_task(save_to_cache(state["query"], response))
    
    return {"response": response}

# 조건 함수
def route_after_prepare(state: OptimizedState) -> Literal["generate", "retrieve"]:
    """캐시 히트 여부에 따라 라우팅"""
    if state.get("response"):
        return "generate"  # 캐시 히트: 바로 응답
    return "retrieve"  # 캐시 미스: 검색 필요

# 그래프 구성
workflow = StateGraph(OptimizedState)
workflow.add_node("prepare", prepare_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generate_node)

workflow.set_entry_point("prepare")
workflow.add_conditional_edges(
    "prepare",
    route_after_prepare,
    {"retrieve": "retrieve", "generate": "generate"}
)
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)

# 최적화된 Checkpoint
redis_client = redis.Redis(host='localhost', port=6379)
checkpointer = OptimizedRedisSaver(redis_client)

app = workflow.compile(checkpointer=checkpointer)
```

**성능 비교:**

```python
# Before: 비최적화
{
    "avg_time": "2.45s",
    "p95_time": "3.2s",
    "cache_miss": "2.8s",
    "memory": "3.8 GB"
}

# After: 최적화
{
    "avg_time": "0.85s",      # 65% 개선
    "p95_time": "1.1s",       # 66% 개선
    "cache_hit": "0.25s",     # 91% 개선
    "cache_miss": "0.95s",    # 66% 개선
    "memory": "1.2 GB"        # 68% 감소
}
```

다음 섹션에서는 Redis Checkpoint 최적화를 심화하여 다루겠습니다.

---

## 5. Redis Checkpoint 최적화

### 5.1 파이프라이닝으로 네트워크 왕복 횟수 줄이기

**❌ 개별 명령 (느림):**

```python
# BAD: 4번의 네트워크 왕복
async def save_conversation(thread_id: str, messages: list, metadata: dict):
    await redis_client.set(f"messages:{thread_id}", json.dumps(messages))
    await redis_client.set(f"metadata:{thread_id}", json.dumps(metadata))
    await redis_client.incr(f"msg_count:{thread_id}")
    await redis_client.expire(f"messages:{thread_id}", 3600)
    
    # 총 레이턴시: 4 × 10ms = 40ms
```

**✅ 파이프라이닝 (빠름):**

```python
# GOOD: 1번의 네트워크 왕복
async def save_conversation_optimized(thread_id: str, messages: list, metadata: dict):
    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.set(f"messages:{thread_id}", json.dumps(messages))
        pipe.set(f"metadata:{thread_id}", json.dumps(metadata))
        pipe.incr(f"msg_count:{thread_id}")
        pipe.expire(f"messages:{thread_id}", 3600)
        await pipe.execute()
    
    # 총 레이턴시: 1 × 10ms = 10ms
    # 개선: 75% 단축
```

### 5.2 데이터 압축

```python
import gzip
import pickle
from typing import Any

class CompressedRedisClient:
    def __init__(self, redis_client):
        self.client = redis_client
        self.compression_threshold = 1024  # 1KB
    
    async def set_compressed(self, key: str, value: Any, ex: int = None):
        """압축하여 저장"""
        # 직렬화
        data = pickle.dumps(value)
        original_size = len(data)
        
        # 압축 (1KB 이상만)
        if original_size > self.compression_threshold:
            compressed = gzip.compress(data, compresslevel=6)
            compression_ratio = len(compressed) / original_size
            
            # 압축 효과가 있을 때만 압축 데이터 저장
            if compression_ratio < 0.9:
                await self.client.set(f"{key}:c", compressed, ex=ex)
                return {
                    "compressed": True,
                    "original": original_size,
                    "final": len(compressed),
                    "ratio": compression_ratio
                }
        
        # 압축하지 않음
        await self.client.set(key, data, ex=ex)
        return {"compressed": False, "size": original_size}
    
    async def get_compressed(self, key: str) -> Any:
        """압축 해제하여 로드"""
        # 압축된 데이터 확인
        data = await self.client.get(f"{key}:c")
        if data:
            # 압축 해제
            data = gzip.decompress(data)
        else:
            # 일반 데이터
            data = await self.client.get(key)
        
        if not data:
            return None
        
        return pickle.loads(data)

# 사용 예시
compressed_client = CompressedRedisClient(redis_client)

# 저장
state = {"messages": [...], "context": "..."}  # 4.5 MB
result = await compressed_client.set_compressed("checkpoint:123", state, ex=3600)
print(result)  # {'compressed': True, 'original': 4718592, 'final': 856000, 'ratio': 0.18}

# 로드
loaded_state = await compressed_client.get_compressed("checkpoint:123")
```

**압축 효과:**

```
Checkpoint 데이터: 4.5 MB
  ├─ 메시지 히스토리: 2.8 MB
  ├─ 컨텍스트: 1.5 MB
  └─ 메타데이터: 0.2 MB

압축 후 (gzip level 6):
  총 크기: 850 KB (81% 감소)
  압축 시간: 15ms
  해제 시간: 8ms

메모리 절약: 100개 세션 기준
  Before: 450 MB
  After: 85 MB (81% 절약)
```

### 5.3 TTL 전략 최적화

```python
class SmartTTLManager:
    """사용 빈도에 따른 TTL 관리"""
    
    def __init__(self, redis_client):
        self.client = redis_client
        self.base_ttl = 3600  # 1시간
        self.max_ttl = 86400  # 24시간
    
    async def set_with_smart_ttl(self, key: str, value: Any, access_count: int = 0):
        """접근 빈도에 따라 TTL 조정"""
        # 접근 빈도가 높으면 TTL 연장
        if access_count > 10:
            ttl = self.max_ttl  # 24시간
        elif access_count > 5:
            ttl = self.base_ttl * 4  # 4시간
        elif access_count > 2:
            ttl = self.base_ttl * 2  # 2시간
        else:
            ttl = self.base_ttl  # 1시간
        
        await self.client.set(key, value, ex=ttl)
        
        # 접근 횟수 기록
        await self.client.incr(f"{key}:access_count")
        await self.client.expire(f"{key}:access_count", ttl)
    
    async def get_and_update_ttl(self, key: str):
        """로드 시 TTL 갱신"""
        # 데이터 로드
        value = await self.client.get(key)
        
        if value:
            # 접근 횟수 증가
            access_count = await self.client.incr(f"{key}:access_count")
            
            # TTL 갱신 (자주 사용되는 데이터)
            if access_count > 5:
                await self.client.expire(key, self.max_ttl)
        
        return value
```

### 5.4 배치 로드/저장

```python
async def batch_load_checkpoints(thread_ids: list[str]) -> dict:
    """여러 checkpoint를 한 번에 로드"""
    async with redis_client.pipeline(transaction=False) as pipe:
        for thread_id in thread_ids:
            pipe.get(f"checkpoint:{thread_id}")
        
        results = await pipe.execute()
    
    return {
        thread_id: pickle.loads(data) if data else None
        for thread_id, data in zip(thread_ids, results)
    }

# 사용 예시
thread_ids = ["thread_1", "thread_2", "thread_3"]
checkpoints = await batch_load_checkpoints(thread_ids)

# Before: 순차 로드
# Time: 3 × 15ms = 45ms

# After: 배치 로드
# Time: 1 × 15ms = 15ms
# 개선: 66% 단축
```

---

## 6. Vector DB & RAG 최적화

### 6.1 임베딩 캐싱

```python
class EmbeddingCache:
    """임베딩 캐싱 레이어"""
    
    def __init__(self, redis_client, ttl: int = 86400):
        self.redis = redis_client
        self.ttl = ttl
    
    def _get_cache_key(self, text: str, model: str) -> str:
        """캐시 키 생성"""
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"embedding:{model}:{text_hash}"
    
    async def get_embedding(self, text: str, model: str = "text-embedding-ada-002"):
        """캐시된 임베딩 조회 또는 생성"""
        cache_key = self._get_cache_key(text, model)
        
        # 캐시 확인
        cached = await self.redis.get(cache_key)
        if cached:
            return pickle.loads(cached)
        
        # 캐시 미스: 임베딩 생성
        embedding = await openai_client.embeddings.create(
            input=text,
            model=model
        )
        
        vector = embedding.data[0].embedding
        
        # 캐싱 (24시간)
        await self.redis.setex(cache_key, self.ttl, pickle.dumps(vector))
        
        return vector

# 사용 예시
embedding_cache = EmbeddingCache(redis_client)

# 첫 요청: OpenAI API 호출 (150ms)
embedding1 = await embedding_cache.get_embedding("사용자 질문")

# 같은 질문: 캐시에서 로드 (5ms)
embedding2 = await embedding_cache.get_embedding("사용자 질문")

# 개선: 96% 단축 (150ms → 5ms)
```

### 6.2 Vector 검색 최적화

**HNSW 인덱스 활용 (Qdrant 예시):**

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, SearchParams

# Qdrant 클라이언트
qdrant = QdrantClient(host="localhost", port=6333)

# 컬렉션 생성 (HNSW 인덱스)
qdrant.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(
        size=1536,  # OpenAI embedding 차원
        distance=Distance.COSINE
    ),
    hnsw_config={
        "m": 16,  # 연결 수 (높을수록 정확하지만 느림)
        "ef_construct": 100,  # 구축 시 탐색 범위
    }
)

async def optimized_vector_search(
    query_embedding: list[float],
    k: int = 3,
    score_threshold: float = 0.7
):
    """최적화된 Vector 검색"""
    results = qdrant.search(
        collection_name="documents",
        query_vector=query_embedding,
        limit=k,
        search_params=SearchParams(
            hnsw_ef=64,  # 검색 시 탐색 범위 (낮을수록 빠름)
            exact=False  # 근사 검색 (빠름)
        ),
        score_threshold=score_threshold,  # 임계값 이하 제외
        with_payload=False,  # 메타데이터만 (전체 내용 제외)
        with_vectors=False   # 벡터 제외
    )
    
    # 필요한 문서만 별도로 로드
    doc_ids = [hit.id for hit in results]
    documents = await load_docs_by_ids(doc_ids)
    
    return documents

# 성능 비교
"""
Before (전체 스캔):
  검색 시간: 600ms
  메모리: 2.5 GB 로드

After (HNSW + 페이로드 제외):
  검색 시간: 85ms (85% 단축)
  메모리: 50 MB 로드 (98% 감소)
"""
```

### 6.3 청크 크기 최적화

```python
def optimize_chunk_size(text: str, chunk_size: int = 512, overlap: int = 50):
    """최적화된 청크 분할"""
    # 작은 청크 (512 토큰): 빠른 검색, 정확한 매칭
    # 큰 청크 (2048 토큰): 느린 검색, 컨텍스트 풍부
    
    # 토큰화 (대략적)
    tokens = text.split()
    
    chunks = []
    for i in range(0, len(tokens), chunk_size - overlap):
        chunk = " ".join(tokens[i:i + chunk_size])
        chunks.append(chunk)
    
    return chunks

# 청크 크기별 성능
"""
Chunk Size: 256 tokens
  - 검색 속도: 매우 빠름 (40ms)
  - 정확도: 중간
  - 컨텍스트: 부족

Chunk Size: 512 tokens ✅ 권장
  - 검색 속도: 빠름 (85ms)
  - 정확도: 높음
  - 컨텍스트: 충분

Chunk Size: 2048 tokens
  - 검색 속도: 느림 (250ms)
  - 정확도: 높음
  - 컨텍스트: 풍부 (과도)
"""
```

### 6.4 하이브리드 검색

```python
async def hybrid_search(
    query: str,
    k: int = 5
) -> list[dict]:
    """Vector + Keyword 하이브리드 검색"""
    # 병렬 실행: Vector 검색 + 키워드 검색
    vector_results, keyword_results = await asyncio.gather(
        vector_search(query, k=10),
        keyword_search(query, k=10)
    )
    
    # 점수 기반 병합 (Reciprocal Rank Fusion)
    combined = {}
    
    for rank, doc in enumerate(vector_results):
        doc_id = doc["id"]
        combined[doc_id] = combined.get(doc_id, 0) + 1 / (rank + 60)
    
    for rank, doc in enumerate(keyword_results):
        doc_id = doc["id"]
        combined[doc_id] = combined.get(doc_id, 0) + 1 / (rank + 60)
    
    # 상위 k개 반환
    sorted_docs = sorted(combined.items(), key=lambda x: x[1], reverse=True)
    top_doc_ids = [doc_id for doc_id, score in sorted_docs[:k]]
    
    return await load_docs_by_ids(top_doc_ids)
```

---

## 7. Streaming 응답 최적화

### 7.1 백프레셔 처리

```python
from asyncio import Queue

async def streaming_with_backpressure(
    messages: list,
    max_queue_size: int = 10
):
    """백프레셔가 적용된 스트리밍"""
    queue = Queue(maxsize=max_queue_size)
    
    async def producer():
        """LLM 응답 생성 (프로듀서)"""
        async for chunk in llm_stream(messages):
            # 큐가 가득 차면 대기 (백프레셔)
            await queue.put(chunk)
        
        # 종료 신호
        await queue.put(None)
    
    async def consumer():
        """클라이언트로 전송 (컨슈머)"""
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            
            yield f"data: {json.dumps(chunk)}\n\n"
    
    # 프로듀서와 컨슈머 동시 실행
    producer_task = asyncio.create_task(producer())
    
    async for data in consumer():
        yield data
    
    await producer_task
```

### 7.2 버퍼 최적화

```python
class StreamingBuffer:
    """스트리밍 버퍼"""
    
    def __init__(self, min_buffer_size: int = 10):
        self.buffer = []
        self.min_buffer_size = min_buffer_size
    
    async def add(self, chunk: str):
        """청크 추가"""
        self.buffer.append(chunk)
        
        # 버퍼가 최소 크기에 도달하면 플러시
        if len(self.buffer) >= self.min_buffer_size:
            return await self.flush()
        
        return None
    
    async def flush(self):
        """버퍼 플러시"""
        if not self.buffer:
            return None
        
        combined = "".join(self.buffer)
        self.buffer = []
        return combined

async def buffered_streaming(messages: list):
    """버퍼링된 스트리밍"""
    buffer = StreamingBuffer(min_buffer_size=10)
    
    async for chunk in llm_stream(messages):
        result = await buffer.add(chunk)
        
        if result:
            yield f"data: {result}\n\n"
    
    # 남은 버퍼 플러시
    final = await buffer.flush()
    if final:
        yield f"data: {final}\n\n"

# 성능 개선
"""
Before (청크마다 전송):
  - 청크 수: 500개
  - 네트워크 왕복: 500회
  - 오버헤드: 높음

After (버퍼링):
  - 청크 수: 50개 (10개씩 묶음)
  - 네트워크 왕복: 50회
  - 오버헤드: 90% 감소
"""
```

---

## 8. MSA 레벨 최적화

### 8.1 서비스 간 통신 최적화

```python
# gRPC로 서비스 간 통신 (HTTP REST보다 빠름)
import grpc
from concurrent import futures

# Protobuf 정의 (embedding_service.proto)
"""
syntax = "proto3";

service EmbeddingService {
  rpc GetEmbedding(EmbeddingRequest) returns (EmbeddingResponse);
  rpc BatchGetEmbeddings(BatchEmbeddingRequest) returns (BatchEmbeddingResponse);
}

message EmbeddingRequest {
  string text = 1;
  string model = 2;
}

message EmbeddingResponse {
  repeated float vector = 1;
}
"""

# gRPC 서버
class EmbeddingServicer:
    async def GetEmbedding(self, request, context):
        embedding = await generate_embedding(request.text, request.model)
        return EmbeddingResponse(vector=embedding)

# gRPC 클라이언트
async def call_embedding_service_grpc(text: str):
    async with grpc.aio.insecure_channel('embedding-service:50051') as channel:
        stub = EmbeddingServiceStub(channel)
        response = await stub.GetEmbedding(EmbeddingRequest(text=text))
        return list(response.vector)

# 성능 비교
"""
HTTP REST:
  - 레이턴시: 25ms
  - 오버헤드: JSON 직렬화

gRPC:
  - 레이턴시: 8ms (68% 단축)
  - 오버헤드: Protobuf (바이너리)
"""
```

### 8.2 로드 밸런싱

```python
from random import choice

class LoadBalancer:
    """간단한 라운드 로빈 로드 밸런서"""
    
    def __init__(self, endpoints: list[str]):
        self.endpoints = endpoints
        self.current = 0
    
    def get_next_endpoint(self) -> str:
        """다음 엔드포인트 선택"""
        endpoint = self.endpoints[self.current]
        self.current = (self.current + 1) % len(self.endpoints)
        return endpoint

# 사용
balancer = LoadBalancer([
    "http://llm-service-1:8000",
    "http://llm-service-2:8000",
    "http://llm-service-3:8000"
])

async def call_llm_service(prompt: str):
    endpoint = balancer.get_next_endpoint()
    response = await httpx_client.post(f"{endpoint}/generate", json={"prompt": prompt})
    return response.json()
```

### 8.3 서킷 브레이커

```python
from datetime import datetime, timedelta

class CircuitBreaker:
    """서킷 브레이커 패턴"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        """서킷 브레이커를 통한 호출"""
        # OPEN 상태: 빠른 실패
        if self.state == "OPEN":
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            
            # 성공 시 리셋
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failures = 0
            
            return result
        
        except Exception as e:
            self.failures += 1
            self.last_failure_time = datetime.now()
            
            # 임계값 초과 시 OPEN
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
            
            raise e

# 사용
circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=30)

async def call_external_api_with_circuit_breaker(data):
    return await circuit_breaker.call(external_api_call, data)
```

---

## 9. 모니터링 및 프로파일링

### 9.1 Prometheus 메트릭

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# 메트릭 정의
request_count = Counter('api_requests_total', 'Total API requests', ['endpoint', 'status'])
request_duration = Histogram('api_request_duration_seconds', 'Request duration', ['endpoint'])
active_connections = Gauge('active_connections', 'Active connections')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    active_connections.inc()
    
    try:
        response = await call_next(request)
        status = response.status_code
    except Exception as e:
        status = 500
        raise
    finally:
        duration = time.time() - start_time
        request_duration.labels(endpoint=request.url.path).observe(duration)
        request_count.labels(endpoint=request.url.path, status=status).inc()
        active_connections.dec()
    
    return response
```

### 9.2 분산 트레이싱 (OpenTelemetry)

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# Tracer 설정
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)

trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# 사용
async def process_request(query: str):
    with tracer.start_as_current_span("process_request"):
        with tracer.start_as_current_span("embedding_generation"):
            embedding = await generate_embedding(query)
        
        with tracer.start_as_current_span("vector_search"):
            docs = await vector_search(embedding)
        
        with tracer.start_as_current_span("llm_generation"):
            response = await llm_generate(docs)
        
        return response
```

---

## 10. 결론 및 최적화 체크리스트

### 10.1 핵심 요약

**적용된 최적화 기법:**

| 레이어 | 최적화 | 개선 효과 |
|--------|--------|----------|
| FastAPI | 비동기 I/O, 커넥션 풀 | 25-30% |
| FastAPI | 응답 캐싱, 압축 | 40-80% |
| LangGraph | 노드 병렬 실행 | 30-40% |
| LangGraph | 조건부 실행, 상태 최소화 | 20-30% |
| Redis | 파이프라이닝, 압축 | 75-80% |
| Vector DB | HNSW 인덱스, 임베딩 캐싱 | 85-96% |
| Streaming | 백프레셔, 버퍼링 | 90% |
| MSA | gRPC, 로드 밸런싱 | 68% |

**종합 성능 개선:**

```python
# Before (최적화 전)
{
    "TTFT (First Token)": "2.5s",
    "P95 Latency": "3.2s",
    "Throughput": "200 req/s",
    "Memory": "3.8 GB per instance"
}

# After (최적화 후)
{
    "TTFT (First Token)": "450ms",    # 82% 개선 ⬇️
    "P95 Latency": "850ms",           # 73% 개선 ⬇️
    "Throughput": "950 req/s",        # 375% 증가 ⬆️
    "Memory": "1.1 GB per instance"   # 71% 감소 ⬇️
}

# 목표 달성도
- ✅ TTFT < 500ms: 달성 (450ms)
- ✅ Throughput > 800 req/s: 달성 (950 req/s)
- ✅ Memory < 2GB: 달성 (1.1 GB)
```

### 10.2 단계별 적용 가이드

**Week 1-2: Quick Wins (즉시 적용 가능)**

```python
quick_wins_checklist = [
    "✅ Redis 동기 → 비동기 전환",
    "✅ Vector 검색 k값 조정 (10 → 3)",
    "✅ 불필요한 로깅 제거",
    "✅ Gzip 압축 활성화",
    "✅ Uvicorn Worker 수 증가",
    "✅ 임베딩 캐싱 (Redis)",
]

# 예상 개선: 30-40%
```

**Week 3-4: 중급 최적화**

```python
intermediate_checklist = [
    "✅ LangGraph 노드 병렬화",
    "✅ Redis 파이프라이닝",
    "✅ Checkpoint 압축",
    "✅ 조건부 RAG (간단한 질문 스킵)",
    "✅ 커넥션 풀 최적화",
    "✅ 백그라운드 작업 활용",
]

# 예상 추가 개선: 30-40%
```

**Week 5-6: 고급 최적화**

```python
advanced_checklist = [
    "✅ Vector DB HNSW 인덱스 튜닝",
    "✅ 하이브리드 검색 구현",
    "✅ gRPC 도입",
    "✅ 서킷 브레이커 패턴",
    "✅ 분산 트레이싱",
    "✅ 메트릭 대시보드",
]

# 예상 추가 개선: 20-30%
```

### 10.3 최종 체크리스트

```python
final_checklist = {
    "FastAPI": {
        "비동기 I/O": "✅",
        "커넥션 풀": "✅",
        "응답 캐싱": "✅",
        "미들웨어 최적화": "✅",
        "Gzip 압축": "✅",
        "Worker 설정": "✅"
    },
    "LangGraph": {
        "노드 병렬 실행": "✅",
        "조건부 라우팅": "✅",
        "상태 크기 최소화": "✅",
        "Checkpoint 압축": "✅",
        "스마트 캐싱": "✅"
    },
    "Redis": {
        "비동기 클라이언트": "✅",
        "파이프라이닝": "✅",
        "데이터 압축": "✅",
        "TTL 최적화": "✅",
        "배치 작업": "✅"
    },
    "Vector DB": {
        "HNSW 인덱스": "✅",
        "임베딩 캐싱": "✅",
        "청크 크기 최적화": "✅",
        "하이브리드 검색": "✅"
    },
    "Streaming": {
        "백프레셔": "✅",
        "버퍼링": "✅",
        "조기 종료": "✅"
    },
    "MSA": {
        "gRPC": "✅",
        "로드 밸런싱": "✅",
        "서킷 브레이커": "✅"
    },
    "모니터링": {
        "Prometheus": "✅",
        "분산 트레이싱": "✅",
        "대시보드": "✅"
    }
}
```

### 10.4 참고 자료

**공식 문서:**

- [FastAPI Performance](https://fastapi.tiangolo.com/deployment/server-workers/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Redis Performance Optimization](https://redis.io/docs/management/optimization/)
- [Qdrant HNSW Index](https://qdrant.tech/documentation/indexing/)

**유용한 도구:**

```python
monitoring_tools = [
    "Prometheus + Grafana",
    "Jaeger (분산 트레이싱)",
    "cProfile (Python 프로파일링)",
    "memory_profiler",
    "py-spy (프로덕션 프로파일링)"
]
```

**베스트 프랙티스:**

1. **측정 우선**: 항상 프로파일링부터 시작
2. **점진적 적용**: Quick Wins → 중급 → 고급 순서로
3. **A/B 테스트**: 최적화 전후 성능 비교
4. **모니터링 필수**: 실시간 메트릭 추적
5. **문서화**: 적용한 최적화 기록 유지

---

## 마치며

FastAPI + LangGraph 기반 MSA LLM Streaming API의 성능을 **80% 이상 개선**하는 종합적인 최적화 방법을 살펴보았습니다.

**핵심 포인트:**

- 🚀 **비동기 I/O**: 모든 I/O를 비동기로 전환
- 💾 **캐싱**: Redis를 활용한 다층 캐싱 전략
- 📦 **압축**: Checkpoint 및 네트워크 전송 압축
- 🔍 **인덱싱**: Vector DB HNSW 인덱스 활용
- ⚡ **병렬 실행**: 독립적인 작업 병렬화
- 📊 **모니터링**: 지속적인 성능 추적

이제 여러분의 LLM API 성능을 획기적으로 향상시켜보세요! 🎉

**질문이나 피드백**은 댓글로 남겨주세요! 😊

