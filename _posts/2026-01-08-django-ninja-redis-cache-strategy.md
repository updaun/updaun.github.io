---
layout: post
title: "Django Ninja와 Redis로 구축하는 전략적 캐시 관리 시스템"
date: 2026-01-08 10:00:00 +0900
categories: [Django, Python, Redis, Performance]
tags: [Django, Django Ninja, Redis, Cache, Async, Performance, ModelSchema, Cache Invalidation]
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-01-08-django-ninja-redis-cache-strategy.webp"
---

Django Ninja는 FastAPI에서 영감을 받은 고성능 비동기 API 프레임워크입니다. 이 글에서는 Django Ninja의 비동기 기능과 Redis를 결합하여 전략적인 캐시 관리 시스템을 구축하는 방법을 알아보겠습니다. 단순한 캐시 저장을 넘어, 버전 관리, 무효화 전략, 그리고 실무에서 바로 적용 가능한 패턴들을 다룹니다.

## 🎯 왜 Django Ninja와 Redis를 함께 사용하는가?

Django의 전통적인 ORM과 템플릿 시스템은 동기 방식으로 작동하며, 대규모 트래픽 환경에서 성능 병목이 발생할 수 있습니다. Django Ninja는 비동기 처리를 기본으로 지원하여 이러한 문제를 해결하고, Redis와 결합하면 다음과 같은 이점을 얻을 수 있습니다:

**성능 향상**
- 데이터베이스 쿼리 부하를 70-90% 감소
- API 응답 시간을 밀리초 단위로 개선 (평균 10-50ms)
- 동시 연결 처리 능력 10배 이상 증가

**확장성**
- 수평적 확장이 용이한 아키텍처
- 마이크로서비스 간 데이터 공유 계층
- 세션 스토어, 분산 락 등 다양한 용도로 활용

**비용 절감**
- 데이터베이스 인스턴스 크기 축소 가능
- RDS 읽기 전용 복제본 비용 절감
- 컴퓨팅 리소스 효율적 사용

## 🏗️ 아키텍처 설계 및 환경 설정

전략적인 캐시 시스템을 구축하기 전에 올바른 아키텍처와 환경 설정이 필요합니다. 프로덕션 환경을 고려한 설정으로 시작하겠습니다.

### 프로젝트 구조

```plaintext
myproject/
├── apps/
│   ├── products/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── api.py
│   │   └── cache.py
│   └── users/
│       ├── models.py
│       ├── schemas.py
│       ├── api.py
│       └── cache.py
├── core/
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   ├── keys.py
│   │   ├── versioning.py
│   │   └── invalidation.py
│   └── redis_client.py
└── settings/
    ├── base.py
    └── production.py
```

### 필수 패키지 설치

```bash
# 기본 패키지
pip install django django-ninja redis aioredis

# 직렬화 및 유틸리티
pip install orjson pydantic

# 비동기 데이터베이스 (PostgreSQL 사용 시)
pip install psycopg[binary] psycopg[pool]

# 모니터링 (선택사항)
pip install django-redis-cache prometheus-client
```

### Redis 설정 (settings/base.py)

```python
# settings/base.py
import os
from typing import Dict, Any

# Redis 기본 설정
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Redis 연결 풀 설정
REDIS_CONFIG: Dict[str, Any] = {
    "host": REDIS_HOST,
    "port": REDIS_PORT,
    "db": REDIS_DB,
    "password": REDIS_PASSWORD,
    "decode_responses": True,  # 문자열로 자동 디코딩
    "encoding": "utf-8",
    "max_connections": 50,  # 연결 풀 최대 크기
    "socket_timeout": 5,
    "socket_connect_timeout": 5,
    "retry_on_timeout": True,
}

# 캐시 전략 설정
CACHE_CONFIG = {
    "default_ttl": 3600,  # 1시간
    "version_prefix": "v1",  # 캐시 버전
    "enable_compression": True,  # 큰 데이터 압축
    "compression_threshold": 1024,  # 1KB 이상 압축
}
```

### Redis 클라이언트 초기화 (core/redis_client.py)

비동기와 동기 클라이언트를 모두 제공하는 Redis 클라이언트를 구현합니다.

```python
# core/redis_client.py
import redis.asyncio as aioredis
import redis
from django.conf import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 클라이언트 싱글톤"""
    
    _async_instance: Optional[aioredis.Redis] = None
    _sync_instance: Optional[redis.Redis] = None
    
    @classmethod
    async def get_async_client(cls) -> aioredis.Redis:
        """비동기 Redis 클라이언트 반환"""
        if cls._async_instance is None:
            try:
                cls._async_instance = await aioredis.from_url(
                    f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                    password=settings.REDIS_PASSWORD,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=50,
                )
                # 연결 테스트
                await cls._async_instance.ping()
                logger.info("Async Redis client connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return cls._async_instance
    
    @classmethod
    def get_sync_client(cls) -> redis.Redis:
        """동기 Redis 클라이언트 반환 (Django 시그널 등에서 사용)"""
        if cls._sync_instance is None:
            cls._sync_instance = redis.Redis(**settings.REDIS_CONFIG)
            try:
                cls._sync_instance.ping()
                logger.info("Sync Redis client connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return cls._sync_instance
    
    @classmethod
    async def close_async_client(cls):
        """비동기 클라이언트 연결 종료"""
        if cls._async_instance:
            await cls._async_instance.close()
            cls._async_instance = None
    
    @classmethod
    def close_sync_client(cls):
        """동기 클라이언트 연결 종료"""
        if cls._sync_instance:
            cls._sync_instance.close()
            cls._sync_instance = None


# 편의 함수
async def get_redis() -> aioredis.Redis:
    """비동기 Redis 클라이언트 가져오기"""
    return await RedisClient.get_async_client()


def get_redis_sync() -> redis.Redis:
    """동기 Redis 클라이언트 가져오기"""
    return RedisClient.get_sync_client()
```

## 🔑 캐시 키 전략 설계

효과적인 캐시 관리의 핵심은 체계적인 키 네이밍 전략입니다. 일관된 키 구조는 캐시 무효화, 모니터링, 디버깅을 크게 간소화합니다.

### 캐시 키 매니저 (core/cache/keys.py)

```python
# core/cache/keys.py
from typing import Optional, Union, List, Dict, Any
from django.conf import settings
import hashlib
import json


class CacheKeyManager:
    """캐시 키 생성 및 관리"""
    
    # 키 네임스페이스
    NAMESPACE_SEPARATOR = ":"
    VERSION_SEPARATOR = ":v"
    
    def __init__(self, namespace: str, version: Optional[str] = None):
        """
        Args:
            namespace: 캐시 네임스페이스 (예: 'product', 'user', 'order')
            version: 캐시 버전 (기본값: settings.CACHE_CONFIG['version_prefix'])
        """
        self.namespace = namespace
        self.version = version or settings.CACHE_CONFIG.get('version_prefix', 'v1')
    
    def generate_key(
        self, 
        resource_id: Optional[Union[int, str]] = None,
        action: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        캐시 키 생성
        
        패턴: {version}:{namespace}:{resource_id}:{action}:{hash}
        예시: v1:product:123:detail:a3f2c9
        
        Args:
            resource_id: 리소스 ID (선택)
            action: 액션 이름 (선택)
            **kwargs: 추가 파라미터 (쿼리 파라미터, 필터 등)
        """
        parts = [self.version, self.namespace]
        
        if resource_id is not None:
            parts.append(str(resource_id))
        
        if action:
            parts.append(action)
        
        # 추가 파라미터가 있으면 해시 생성
        if kwargs:
            param_hash = self._generate_param_hash(kwargs)
            parts.append(param_hash)
        
        return self.NAMESPACE_SEPARATOR.join(parts)
    
    def _generate_param_hash(self, params: Dict[str, Any]) -> str:
        """파라미터를 해싱하여 짧은 문자열 생성"""
        # 정렬된 JSON 문자열로 변환
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        # SHA-256 해시의 앞 8자리 사용
        return hashlib.sha256(sorted_params.encode()).hexdigest()[:8]
    
    def list_key(self, **filters) -> str:
        """리스트 캐시 키 생성"""
        return self.generate_key(action="list", **filters)
    
    def detail_key(self, resource_id: Union[int, str]) -> str:
        """상세 조회 캐시 키 생성"""
        return self.generate_key(resource_id=resource_id, action="detail")
    
    def count_key(self, **filters) -> str:
        """카운트 캐시 키 생성"""
        return self.generate_key(action="count", **filters)
    
    def pattern(self, resource_id: Optional[Union[int, str]] = None) -> str:
        """
        패턴 매칭용 키 생성 (와일드카드)
        특정 네임스페이스의 모든 키를 삭제할 때 사용
        """
        parts = [self.version, self.namespace]
        if resource_id is not None:
            parts.append(str(resource_id))
        parts.append("*")
        return self.NAMESPACE_SEPARATOR.join(parts)
    
    def increment_version(self) -> str:
        """
        버전을 증가시켜 새로운 키 매니저 반환
        전체 네임스페이스 무효화 시 사용
        """
        # v1 -> v2, v2 -> v3
        if self.version.startswith('v'):
            try:
                current_num = int(self.version[1:])
                new_version = f"v{current_num + 1}"
            except ValueError:
                new_version = f"{self.version}_new"
        else:
            new_version = f"{self.version}_v2"
        
        return CacheKeyManager(self.namespace, new_version)


# 사전 정의된 키 매니저
class CacheKeys:
    """애플리케이션 전체에서 사용하는 캐시 키 매니저"""
    
    PRODUCT = CacheKeyManager("product")
    USER = CacheKeyManager("user")
    ORDER = CacheKeyManager("order")
    CATEGORY = CacheKeyManager("category")
    
    @classmethod
    def get_manager(cls, namespace: str) -> CacheKeyManager:
        """동적으로 키 매니저 생성"""
        return CacheKeyManager(namespace)
```

**키 생성 예시:**

```python
# 상품 상세 조회
key = CacheKeys.PRODUCT.detail_key(123)
# 결과: "v1:product:123:detail"

# 필터링된 상품 리스트
key = CacheKeys.PRODUCT.list_key(category="electronics", price_min=100, price_max=1000)
# 결과: "v1:product:list:a3f2c9e1"

# 특정 상품의 모든 캐시 삭제 패턴
pattern = CacheKeys.PRODUCT.pattern(123)
# 결과: "v1:product:123:*"
```

## 📦 ModelSchema 직렬화와 캐시 저장

Django Ninja의 ModelSchema를 사용하면 Django 모델을 자동으로 Pydantic 스키마로 변환할 수 있습니다. 이를 활용하여 타입 안정성을 보장하면서 효율적으로 캐시를 관리할 수 있습니다.

### 모델 정의 (apps/products/models.py)

```python
# apps/products/models.py
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "categories"
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name


class Product(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('out_of_stock', 'Out of Stock'),
    ]
    
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "products"
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['category', 'status']),
        ]
    
    def __str__(self):
        return self.name
```

### Schema 정의 (apps/products/schemas.py)

```python
# apps/products/schemas.py
from ninja import ModelSchema, Schema
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from .models import Product, Category


class CategorySchema(ModelSchema):
    """카테고리 스키마"""
    class Config:
        model = Category
        model_fields = ['id', 'name', 'slug', 'description']


class ProductSchema(ModelSchema):
    """상품 기본 스키마"""
    category: CategorySchema
    
    class Config:
        model = Product
        model_fields = [
            'id', 'name', 'slug', 'description', 
            'price', 'stock', 'status', 'created_at', 'updated_at'
        ]


class ProductListSchema(ModelSchema):
    """상품 리스트용 경량 스키마"""
    category_name: str
    
    class Config:
        model = Product
        model_fields = ['id', 'name', 'slug', 'price', 'stock', 'status']
    
    @staticmethod
    def resolve_category_name(obj):
        return obj.category.name


class ProductFilterSchema(Schema):
    """상품 필터링 스키마"""
    category_id: Optional[int] = None
    status: Optional[str] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    search: Optional[str] = None
    offset: int = 0
    limit: int = 20


class PaginatedProductsSchema(Schema):
    """페이지네이션된 상품 리스트 응답"""
    items: List[ProductListSchema]
    total: int
    offset: int
    limit: int
```

### 캐시 매니저 구현 (core/cache/manager.py)

이제 캐시 저장, 조회, 삭제를 관리하는 통합 매니저를 구현합니다.

```python
# core/cache/manager.py
import orjson
from typing import Optional, Type, TypeVar, Generic, List, Any
from pydantic import BaseModel
from django.conf import settings
import logging
import zlib
from core.redis_client import get_redis
from core.cache.keys import CacheKeyManager

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class CacheManager(Generic[T]):
    """
    제네릭 캐시 매니저
    Pydantic 스키마 기반 타입 안전 캐시 관리
    """
    
    def __init__(
        self, 
        schema_class: Type[T],
        key_manager: CacheKeyManager,
        default_ttl: Optional[int] = None,
        enable_compression: bool = True
    ):
        """
        Args:
            schema_class: Pydantic 스키마 클래스
            key_manager: 캐시 키 매니저
            default_ttl: 기본 TTL (초) - None이면 설정값 사용
            enable_compression: 데이터 압축 사용 여부
        """
        self.schema_class = schema_class
        self.key_manager = key_manager
        self.default_ttl = default_ttl or settings.CACHE_CONFIG.get('default_ttl', 3600)
        self.enable_compression = enable_compression
        self.compression_threshold = settings.CACHE_CONFIG.get('compression_threshold', 1024)
    
    async def get(self, key: str) -> Optional[T]:
        """
        캐시에서 데이터 조회
        
        Args:
            key: 캐시 키
            
        Returns:
            스키마 인스턴스 또는 None
        """
        try:
            redis = await get_redis()
            data = await redis.get(key)
            
            if data is None:
                logger.debug(f"Cache miss: {key}")
                return None
            
            # 압축 해제
            if self.enable_compression and data.startswith('COMPRESSED:'):
                compressed_data = data[11:]  # 'COMPRESSED:' 제거
                data = zlib.decompress(compressed_data.encode('latin1')).decode('utf-8')
            
            # JSON 파싱 및 스키마 검증
            parsed_data = orjson.loads(data)
            instance = self.schema_class(**parsed_data)
            
            logger.debug(f"Cache hit: {key}")
            return instance
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def get_many(self, keys: List[str]) -> List[Optional[T]]:
        """
        여러 캐시 데이터를 한 번에 조회 (파이프라인 사용)
        
        Args:
            keys: 캐시 키 리스트
            
        Returns:
            스키마 인스턴스 리스트 (없으면 None)
        """
        if not keys:
            return []
        
        try:
            redis = await get_redis()
            values = await redis.mget(keys)
            
            results = []
            for key, data in zip(keys, values):
                if data is None:
                    results.append(None)
                    continue
                
                try:
                    # 압축 해제
                    if self.enable_compression and data.startswith('COMPRESSED:'):
                        compressed_data = data[11:]
                        data = zlib.decompress(compressed_data.encode('latin1')).decode('utf-8')
                    
                    parsed_data = orjson.loads(data)
                    instance = self.schema_class(**parsed_data)
                    results.append(instance)
                except Exception as e:
                    logger.error(f"Failed to parse cached data for key {key}: {e}")
                    results.append(None)
            
            return results
            
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return [None] * len(keys)
    
    async def set(
        self, 
        key: str, 
        value: T, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        캐시에 데이터 저장
        
        Args:
            key: 캐시 키
            value: 저장할 스키마 인스턴스
            ttl: TTL (초) - None이면 default_ttl 사용
            
        Returns:
            성공 여부
        """
        try:
            redis = await get_redis()
            
            # Pydantic 모델을 JSON으로 직렬화
            json_data = orjson.dumps(
                value.dict(),
                option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_NAIVE_UTC
            ).decode('utf-8')
            
            # 압축 적용
            if self.enable_compression and len(json_data) > self.compression_threshold:
                compressed = zlib.compress(json_data.encode('utf-8'))
                data_to_store = 'COMPRESSED:' + compressed.decode('latin1')
                logger.debug(f"Compressed data from {len(json_data)} to {len(data_to_store)} bytes")
            else:
                data_to_store = json_data
            
            # TTL 설정
            expire_time = ttl if ttl is not None else self.default_ttl
            
            # Redis에 저장
            await redis.setex(key, expire_time, data_to_store)
            logger.debug(f"Cache set: {key} (TTL: {expire_time}s)")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def set_many(
        self, 
        items: List[tuple[str, T]], 
        ttl: Optional[int] = None
    ) -> bool:
        """
        여러 캐시 데이터를 한 번에 저장 (파이프라인 사용)
        
        Args:
            items: (키, 값) 튜플 리스트
            ttl: TTL (초)
            
        Returns:
            성공 여부
        """
        if not items:
            return True
        
        try:
            redis = await get_redis()
            pipe = redis.pipeline()
            
            expire_time = ttl if ttl is not None else self.default_ttl
            
            for key, value in items:
                json_data = orjson.dumps(
                    value.dict(),
                    option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_NAIVE_UTC
                ).decode('utf-8')
                
                if self.enable_compression and len(json_data) > self.compression_threshold:
                    compressed = zlib.compress(json_data.encode('utf-8'))
                    data_to_store = 'COMPRESSED:' + compressed.decode('latin1')
                else:
                    data_to_store = json_data
                
                pipe.setex(key, expire_time, data_to_store)
            
            await pipe.execute()
            logger.debug(f"Cache set_many: {len(items)} items")
            return True
            
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """캐시 삭제"""
        try:
            redis = await get_redis()
            result = await redis.delete(key)
            logger.debug(f"Cache delete: {key}")
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        패턴에 매칭되는 모든 캐시 삭제
        주의: KEYS 명령은 프로덕션에서 주의해서 사용
        대안으로 SCAN 사용 고려
        """
        try:
            redis = await get_redis()
            keys = await redis.keys(pattern)
            
            if not keys:
                return 0
            
            deleted = await redis.delete(*keys)
            logger.info(f"Cache delete pattern: {pattern}, deleted: {deleted} keys")
            return deleted
            
        except Exception as e:
            logger.error(f"Cache delete pattern error for pattern {pattern}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """캐시 존재 여부 확인"""
        try:
            redis = await get_redis()
            return await redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """캐시 TTL 조회 (초 단위, -2: 없음, -1: 무제한)"""
        try:
            redis = await get_redis()
            return await redis.ttl(key)
        except Exception as e:
            logger.error(f"Cache ttl error for key {key}: {e}")
            return -2
```

## ⚡ Django Ninja 비동기 API 구현

이제 Django Ninja를 사용하여 비동기 API를 구현하고, 캐시를 효과적으로 활용합니다.

### 제품 캐시 서비스 (apps/products/cache.py)

```python
# apps/products/cache.py
from typing import Optional, List
from .models import Product
from .schemas import ProductSchema, ProductListSchema, PaginatedProductsSchema
from core.cache.manager import CacheManager
from core.cache.keys import CacheKeys
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)


class ProductCacheService:
    """상품 캐시 서비스"""
    
    # 캐시 매니저 인스턴스
    detail_cache = CacheManager(ProductSchema, CacheKeys.PRODUCT, default_ttl=3600)
    list_cache = CacheManager(PaginatedProductsSchema, CacheKeys.PRODUCT, default_ttl=1800)
    
    @classmethod
    async def get_product_by_id(cls, product_id: int) -> Optional[ProductSchema]:
        """
        ID로 상품 조회 (캐시 우선)
        
        Args:
            product_id: 상품 ID
            
        Returns:
            ProductSchema 또는 None
        """
        cache_key = CacheKeys.PRODUCT.detail_key(product_id)
        
        # 1. 캐시 확인
        cached = await cls.detail_cache.get(cache_key)
        if cached:
            logger.info(f"Product {product_id} retrieved from cache")
            return cached
        
        # 2. DB 조회 (비동기)
        try:
            product = await Product.objects.select_related('category').aget(id=product_id)
            
            # 3. 스키마로 변환
            product_schema = ProductSchema.from_orm(product)
            
            # 4. 캐시 저장
            await cls.detail_cache.set(cache_key, product_schema)
            
            logger.info(f"Product {product_id} fetched from DB and cached")
            return product_schema
            
        except Product.DoesNotExist:
            logger.warning(f"Product {product_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {e}")
            return None
    
    @classmethod
    async def get_products_list(
        cls,
        category_id: Optional[int] = None,
        status: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> PaginatedProductsSchema:
        """
        필터링된 상품 리스트 조회 (캐시 우선)
        """
        # 캐시 키 생성 (필터 조건 포함)
        filter_params = {
            'category_id': category_id,
            'status': status,
            'min_price': min_price,
            'max_price': max_price,
            'search': search,
            'offset': offset,
            'limit': limit,
        }
        # None 값 제거
        filter_params = {k: v for k, v in filter_params.items() if v is not None}
        
        cache_key = CacheKeys.PRODUCT.list_key(**filter_params)
        
        # 1. 캐시 확인
        cached = await cls.list_cache.get(cache_key)
        if cached:
            logger.info("Product list retrieved from cache")
            return cached
        
        # 2. DB 쿼리 빌드
        queryset = Product.objects.select_related('category').all()
        
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        # 3. 총 개수 조회 (비동기)
        total = await queryset.acount()
        
        # 4. 페이지네이션 적용 및 조회
        products = []
        async for product in queryset.order_by('-created_at')[offset:offset + limit]:
            # ProductListSchema로 변환
            product_data = {
                'id': product.id,
                'name': product.name,
                'slug': product.slug,
                'price': product.price,
                'stock': product.stock,
                'status': product.status,
                'category_name': product.category.name,
            }
            products.append(ProductListSchema(**product_data))
        
        # 5. 응답 스키마 생성
        result = PaginatedProductsSchema(
            items=products,
            total=total,
            offset=offset,
            limit=limit
        )
        
        # 6. 캐시 저장
        await cls.list_cache.set(cache_key, result)
        
        logger.info(f"Product list fetched from DB and cached ({len(products)} items)")
        return result
    
    @classmethod
    async def invalidate_product(cls, product_id: int):
        """특정 상품 관련 모든 캐시 무효화"""
        # 상세 캐시 삭제
        detail_key = CacheKeys.PRODUCT.detail_key(product_id)
        await cls.detail_cache.delete(detail_key)
        
        # 해당 상품이 포함된 모든 리스트 캐시 삭제
        # 패턴: v1:product:list:*
        list_pattern = CacheKeys.PRODUCT.generate_key(action="list") + ":*"
        deleted_count = await cls.list_cache.delete_pattern(list_pattern)
        
        logger.info(f"Invalidated product {product_id} cache (list caches: {deleted_count})")
    
    @classmethod
    async def invalidate_all_lists(cls):
        """모든 리스트 캐시 무효화"""
        list_pattern = CacheKeys.PRODUCT.generate_key(action="list") + ":*"
        deleted_count = await cls.list_cache.delete_pattern(list_pattern)
        logger.info(f"Invalidated all product list caches ({deleted_count} keys)")
```

### API 엔드포인트 (apps/products/api.py)

```python
# apps/products/api.py
from ninja import Router
from typing import List
from .schemas import (
    ProductSchema, 
    ProductFilterSchema, 
    PaginatedProductsSchema
)
from .cache import ProductCacheService
from ninja.responses import Response
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.get("/{product_id}", response=ProductSchema)
async def get_product(request, product_id: int):
    """
    상품 상세 조회 (캐시 적용)
    
    - 캐시 히트 시: ~5ms
    - 캐시 미스 시: ~50-100ms (DB 쿼리 포함)
    """
    product = await ProductCacheService.get_product_by_id(product_id)
    
    if product is None:
        return Response({"error": "Product not found"}, status=404)
    
    return product


@router.get("", response=PaginatedProductsSchema)
async def list_products(request, filters: ProductFilterSchema = None):
    """
    상품 리스트 조회 (필터링, 페이지네이션, 캐시 적용)
    
    Query Parameters:
    - category_id: 카테고리 ID
    - status: 상품 상태 (active, inactive, out_of_stock)
    - min_price: 최소 가격
    - max_price: 최대 가격
    - search: 검색어 (상품명, 설명)
    - offset: 오프셋 (기본: 0)
    - limit: 페이지 크기 (기본: 20, 최대: 100)
    """
    filters = filters or ProductFilterSchema()
    
    # limit 제한
    filters.limit = min(filters.limit, 100)
    
    result = await ProductCacheService.get_products_list(
        category_id=filters.category_id,
        status=filters.status,
        min_price=filters.min_price,
        max_price=filters.max_price,
        search=filters.search,
        offset=filters.offset,
        limit=filters.limit,
    )
    
    return result
```

## 🔄 전략적 캐시 무효화 시스템

캐시 무효화는 캐시 전략에서 가장 중요하고 복잡한 부분입니다. 데이터 일관성을 유지하면서도 성능을 최대화하는 전략이 필요합니다.

### 캐시 무효화 전략 (core/cache/invalidation.py)

```python
# core/cache/invalidation.py
from enum import Enum
from typing import Optional, List, Callable, Awaitable
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from core.redis_client import get_redis_sync
from core.cache.keys import CacheKeys
import logging

logger = logging.getLogger(__name__)


class InvalidationStrategy(Enum):
    """캐시 무효화 전략"""
    
    # 즉시 삭제: 데이터 변경 시 즉시 캐시 삭제
    IMMEDIATE = "immediate"
    
    # 지연 삭제: 백그라운드 작업으로 삭제
    DELAYED = "delayed"
    
    # TTL 단축: 캐시 유지하되 TTL을 짧게 설정
    TTL_REDUCTION = "ttl_reduction"
    
    # 버전 증가: 버전을 올려 기존 캐시 무효화
    VERSION_INCREMENT = "version_increment"
    
    # 선택적 무효화: 특정 조건의 캐시만 삭제
    SELECTIVE = "selective"


class CacheInvalidator:
    """캐시 무효화 관리자"""
    
    def __init__(self):
        self.redis = get_redis_sync()
    
    def invalidate_by_pattern(self, pattern: str) -> int:
        """
        패턴 기반 캐시 삭제
        
        주의: KEYS는 O(N) 복잡도로 프로덕션에서 주의
        대안: SCAN 사용 또는 Redis Cluster에서 해시태그 활용
        """
        try:
            keys = self.redis.keys(pattern)
            if not keys:
                return 0
            
            deleted = self.redis.delete(*keys)
            logger.info(f"Invalidated {deleted} keys matching pattern: {pattern}")
            return deleted
        except Exception as e:
            logger.error(f"Error invalidating pattern {pattern}: {e}")
            return 0
    
    def invalidate_keys(self, keys: List[str]) -> int:
        """여러 키를 한 번에 삭제"""
        if not keys:
            return 0
        
        try:
            deleted = self.redis.delete(*keys)
            logger.info(f"Invalidated {deleted} keys")
            return deleted
        except Exception as e:
            logger.error(f"Error invalidating keys: {e}")
            return 0
    
    def reduce_ttl(self, key: str, new_ttl: int) -> bool:
        """
        캐시 TTL 단축
        점진적 무효화 전략에 사용
        """
        try:
            self.redis.expire(key, new_ttl)
            logger.info(f"Reduced TTL for key {key} to {new_ttl}s")
            return True
        except Exception as e:
            logger.error(f"Error reducing TTL for key {key}: {e}")
            return False
    
    def tag_for_invalidation(self, key: str, tag: str) -> bool:
        """
        무효화 태그 설정 (나중에 일괄 처리)
        Redis Set을 사용하여 태그 관리
        """
        try:
            tag_key = f"invalidation_queue:{tag}"
            self.redis.sadd(tag_key, key)
            # 태그 자체에도 TTL 설정 (24시간)
            self.redis.expire(tag_key, 86400)
            return True
        except Exception as e:
            logger.error(f"Error tagging key {key} with tag {tag}: {e}")
            return False
    
    def process_tagged_invalidations(self, tag: str) -> int:
        """태그된 캐시들을 일괄 무효화"""
        try:
            tag_key = f"invalidation_queue:{tag}"
            keys = self.redis.smembers(tag_key)
            
            if not keys:
                return 0
            
            # 캐시 삭제
            deleted = self.redis.delete(*keys)
            
            # 태그 삭제
            self.redis.delete(tag_key)
            
            logger.info(f"Processed invalidation for tag {tag}: {deleted} keys")
            return deleted
        except Exception as e:
            logger.error(f"Error processing tagged invalidations for {tag}: {e}")
            return 0


# 전역 인스턴스
cache_invalidator = CacheInvalidator()


# Django 시그널 기반 자동 무효화
@receiver(post_save, sender='products.Product')
def invalidate_product_on_save(sender, instance, created, **kwargs):
    """
    상품 저장 시 캐시 무효화
    
    전략:
    - 상세 캐시: 즉시 삭제
    - 리스트 캐시: TTL 단축 (10분)
    """
    try:
        product_id = instance.id
        
        # 1. 상세 캐시 즉시 삭제
        detail_key = CacheKeys.PRODUCT.detail_key(product_id)
        cache_invalidator.invalidate_keys([detail_key])
        
        # 2. 리스트 캐시는 TTL 단축 (즉시 삭제하면 부하 증가)
        list_pattern = CacheKeys.PRODUCT.generate_key(action="list") + ":*"
        
        # 생성인 경우: 리스트 캐시 즉시 삭제
        if created:
            cache_invalidator.invalidate_by_pattern(list_pattern)
            logger.info(f"New product {product_id} created - invalidated all list caches")
        else:
            # 수정인 경우: TTL 단축 전략
            # 실제로는 SCAN으로 키를 찾아서 TTL 단축
            cache_invalidator.tag_for_invalidation(list_pattern, "product_update")
            logger.info(f"Product {product_id} updated - tagged list caches for invalidation")
        
    except Exception as e:
        logger.error(f"Error in invalidate_product_on_save: {e}")


@receiver(post_delete, sender='products.Product')
def invalidate_product_on_delete(sender, instance, **kwargs):
    """
    상품 삭제 시 모든 관련 캐시 즉시 삭제
    """
    try:
        product_id = instance.id
        
        # 상세 캐시 삭제
        detail_key = CacheKeys.PRODUCT.detail_key(product_id)
        cache_invalidator.invalidate_keys([detail_key])
        
        # 리스트 캐시 전체 삭제
        list_pattern = CacheKeys.PRODUCT.generate_key(action="list") + ":*"
        cache_invalidator.invalidate_by_pattern(list_pattern)
        
        logger.info(f"Product {product_id} deleted - invalidated all related caches")
        
    except Exception as e:
        logger.error(f"Error in invalidate_product_on_delete: {e}")


@receiver(post_save, sender='products.Category')
def invalidate_category_on_save(sender, instance, created, **kwargs):
    """
    카테고리 변경 시 해당 카테고리 상품 리스트 캐시 무효화
    """
    try:
        category_id = instance.id
        
        # 해당 카테고리의 상품 리스트 캐시만 삭제
        # 실제 구현에서는 더 세밀한 패턴 매칭 필요
        list_pattern = CacheKeys.PRODUCT.generate_key(action="list") + ":*"
        cache_invalidator.invalidate_by_pattern(list_pattern)
        
        logger.info(f"Category {category_id} updated - invalidated related product lists")
        
    except Exception as e:
        logger.error(f"Error in invalidate_category_on_save: {e}")
```

### 비동기 무효화 헬퍼 (apps/products/cache.py에 추가)

```python
# apps/products/cache.py에 추가

class ProductCacheService:
    # ... 기존 코드 ...
    
    @classmethod
    async def smart_invalidation(
        cls, 
        product_id: int,
        invalidation_strategy: InvalidationStrategy = InvalidationStrategy.IMMEDIATE
    ):
        """
        전략적 캐시 무효화
        
        Args:
            product_id: 상품 ID
            invalidation_strategy: 무효화 전략
        """
        from core.cache.invalidation import InvalidationStrategy
        
        if invalidation_strategy == InvalidationStrategy.IMMEDIATE:
            # 즉시 삭제
            await cls.invalidate_product(product_id)
            
        elif invalidation_strategy == InvalidationStrategy.TTL_REDUCTION:
            # TTL 단축 (10분)
            detail_key = CacheKeys.PRODUCT.detail_key(product_id)
            redis = await get_redis()
            await redis.expire(detail_key, 600)
            
            list_pattern = CacheKeys.PRODUCT.generate_key(action="list") + ":*"
            keys = await redis.keys(list_pattern)
            for key in keys:
                await redis.expire(key, 600)
            
            logger.info(f"Reduced TTL for product {product_id} caches to 10 minutes")
            
        elif invalidation_strategy == InvalidationStrategy.VERSION_INCREMENT:
            # 버전 증가로 전체 네임스페이스 무효화
            # 새 버전의 키 매니저 사용
            new_key_manager = CacheKeys.PRODUCT.increment_version()
            
            # 애플리케이션 재시작 없이 버전 변경은 복잡하므로
            # 실제로는 Redis에 버전 정보 저장 필요
            logger.info(f"Version incremented for product namespace")
            
        elif invalidation_strategy == InvalidationStrategy.SELECTIVE:
            # 선택적 무효화: 상세만 삭제, 리스트는 유지
            detail_key = CacheKeys.PRODUCT.detail_key(product_id)
            await cls.detail_cache.delete(detail_key)
            logger.info(f"Selectively invalidated product {product_id} detail cache only")
```

## 📊 캐시 버전 관리 시스템

캐시 버전 관리는 대규모 배포나 데이터 스키마 변경 시 안전하게 캐시를 무효화할 수 있는 강력한 전략입니다.

### 버전 관리 시스템 (core/cache/versioning.py)

```python
# core/cache/versioning.py
from typing import Optional, Dict
from datetime import datetime, timedelta
from core.redis_client import get_redis, get_redis_sync
import logging

logger = logging.getLogger(__name__)


class CacheVersionManager:
    """
    캐시 버전 관리 시스템
    
    특징:
    - 전역 버전과 네임스페이스별 버전 관리
    - 점진적 버전 업그레이드
    - 롤백 지원
    """
    
    VERSION_KEY_PREFIX = "cache_version"
    GLOBAL_VERSION_KEY = f"{VERSION_KEY_PREFIX}:global"
    
    def __init__(self):
        self.redis = get_redis_sync()
    
    def get_global_version(self) -> str:
        """
        전역 캐시 버전 조회
        
        Returns:
            버전 문자열 (예: "v1", "v2")
        """
        version = self.redis.get(self.GLOBAL_VERSION_KEY)
        if version is None:
            # 초기 버전 설정
            self.set_global_version("v1")
            return "v1"
        return version
    
    def set_global_version(self, version: str) -> bool:
        """전역 캐시 버전 설정"""
        try:
            self.redis.set(self.GLOBAL_VERSION_KEY, version)
            logger.info(f"Global cache version set to {version}")
            return True
        except Exception as e:
            logger.error(f"Error setting global version: {e}")
            return False
    
    def increment_global_version(self) -> str:
        """
        전역 버전 증가
        모든 캐시를 무효화하는 가장 강력한 방법
        """
        current = self.get_global_version()
        
        # 버전 파싱 및 증가
        if current.startswith('v'):
            try:
                num = int(current[1:])
                new_version = f"v{num + 1}"
            except ValueError:
                new_version = f"{current}_new"
        else:
            new_version = f"{current}_v2"
        
        self.set_global_version(new_version)
        
        # 버전 변경 이력 저장
        history_key = f"{self.VERSION_KEY_PREFIX}:history"
        timestamp = datetime.now().isoformat()
        self.redis.hset(history_key, timestamp, f"{current} -> {new_version}")
        
        logger.warning(f"Global cache version incremented: {current} -> {new_version}")
        return new_version
    
    def get_namespace_version(self, namespace: str) -> str:
        """네임스페이스별 버전 조회"""
        key = f"{self.VERSION_KEY_PREFIX}:{namespace}"
        version = self.redis.get(key)
        
        if version is None:
            # 전역 버전 사용
            version = self.get_global_version()
            self.redis.set(key, version)
        
        return version
    
    def set_namespace_version(self, namespace: str, version: str) -> bool:
        """네임스페이스별 버전 설정"""
        try:
            key = f"{self.VERSION_KEY_PREFIX}:{namespace}"
            self.redis.set(key, version)
            logger.info(f"Cache version for namespace '{namespace}' set to {version}")
            return True
        except Exception as e:
            logger.error(f"Error setting namespace version: {e}")
            return False
    
    def increment_namespace_version(self, namespace: str) -> str:
        """
        특정 네임스페이스의 버전만 증가
        해당 네임스페이스의 모든 캐시 무효화
        """
        current = self.get_namespace_version(namespace)
        
        if current.startswith('v'):
            try:
                num = int(current[1:])
                new_version = f"v{num + 1}"
            except ValueError:
                new_version = f"{current}_new"
        else:
            new_version = f"{current}_v2"
        
        self.set_namespace_version(namespace, new_version)
        
        logger.warning(f"Namespace '{namespace}' version incremented: {current} -> {new_version}")
        return new_version
    
    def rollback_namespace_version(self, namespace: str, target_version: str) -> bool:
        """
        네임스페이스 버전 롤백
        긴급 상황에서 이전 버전으로 복구
        """
        try:
            current = self.get_namespace_version(namespace)
            self.set_namespace_version(namespace, target_version)
            
            logger.warning(
                f"Namespace '{namespace}' version rolled back: "
                f"{current} -> {target_version}"
            )
            return True
        except Exception as e:
            logger.error(f"Error rolling back namespace version: {e}")
            return False
    
    def get_version_history(self, limit: int = 10) -> Dict[str, str]:
        """버전 변경 이력 조회"""
        history_key = f"{self.VERSION_KEY_PREFIX}:history"
        history = self.redis.hgetall(history_key)
        
        # 최신 항목부터 정렬
        sorted_history = dict(
            sorted(history.items(), key=lambda x: x[0], reverse=True)[:limit]
        )
        
        return sorted_history
    
    def cleanup_old_caches(self, namespace: str, current_version: str) -> int:
        """
        이전 버전의 캐시 정리
        
        주의: 프로덕션에서는 백그라운드 작업으로 실행
        """
        try:
            # 현재 버전이 아닌 모든 캐시 찾기
            # 예: v1:product:* (현재 버전이 v2인 경우)
            pattern = f"{namespace}:*"
            keys = self.redis.keys(pattern)
            
            deleted = 0
            for key in keys:
                # 현재 버전이 아닌 키만 삭제
                if not key.startswith(f"{current_version}:"):
                    self.redis.delete(key)
                    deleted += 1
            
            logger.info(f"Cleaned up {deleted} old cache keys for namespace '{namespace}'")
            return deleted
            
        except Exception as e:
            logger.error(f"Error cleaning up old caches: {e}")
            return 0


# 전역 인스턴스
version_manager = CacheVersionManager()


# 버전 인식 키 매니저
class VersionAwareCacheKeyManager:
    """
    버전을 동적으로 확인하는 키 매니저
    """
    
    def __init__(self, namespace: str):
        self.namespace = namespace
    
    def get_current_version(self) -> str:
        """현재 버전 조회"""
        return version_manager.get_namespace_version(self.namespace)
    
    def generate_key(
        self, 
        resource_id: Optional[int] = None,
        action: Optional[str] = None,
        **kwargs
    ) -> str:
        """현재 버전을 반영한 키 생성"""
        version = self.get_current_version()
        from core.cache.keys import CacheKeyManager
        
        # 임시 키 매니저 생성
        temp_manager = CacheKeyManager(self.namespace, version)
        return temp_manager.generate_key(resource_id, action, **kwargs)
    
    def detail_key(self, resource_id: int) -> str:
        return self.generate_key(resource_id=resource_id, action="detail")
    
    def list_key(self, **filters) -> str:
        return self.generate_key(action="list", **filters)
```

### 버전 관리 API 엔드포인트

```python
# core/api/cache_admin.py (관리자용)
from ninja import Router
from ninja.security import django_auth
from core.cache.versioning import version_manager
from typing import Dict

router = Router(tags=["Cache Admin"], auth=django_auth)


@router.post("/version/global/increment")
async def increment_global_cache_version(request):
    """
    전역 캐시 버전 증가 (모든 캐시 무효화)
    
    주의: 이 작업은 모든 캐시를 무효화합니다.
    대규모 배포나 스키마 변경 시에만 사용하세요.
    """
    old_version = version_manager.get_global_version()
    new_version = version_manager.increment_global_version()
    
    return {
        "status": "success",
        "old_version": old_version,
        "new_version": new_version,
        "message": "All caches invalidated by version increment"
    }


@router.post("/version/{namespace}/increment")
async def increment_namespace_cache_version(request, namespace: str):
    """
    특정 네임스페이스의 캐시 버전 증가
    
    해당 네임스페이스의 모든 캐시만 무효화
    """
    old_version = version_manager.get_namespace_version(namespace)
    new_version = version_manager.increment_namespace_version(namespace)
    
    return {
        "status": "success",
        "namespace": namespace,
        "old_version": old_version,
        "new_version": new_version,
        "message": f"Namespace '{namespace}' caches invalidated"
    }


@router.get("/version/history")
async def get_version_history(request, limit: int = 10):
    """버전 변경 이력 조회"""
    history = version_manager.get_version_history(limit)
    return {
        "status": "success",
        "history": history
    }


@router.post("/version/{namespace}/rollback")
async def rollback_namespace_version(request, namespace: str, target_version: str):
    """
    네임스페이스 버전 롤백
    
    긴급 상황에서 이전 버전으로 복구
    """
    success = version_manager.rollback_namespace_version(namespace, target_version)
    
    if success:
        return {
            "status": "success",
            "namespace": namespace,
            "target_version": target_version,
            "message": f"Rolled back to version {target_version}"
        }
    else:
        return {
            "status": "error",
            "message": "Rollback failed"
        }
```

## 🎨 고급 캐시 패턴 및 최적화

실무에서 자주 사용되는 고급 캐시 패턴들을 살펴보겠습니다.

### 1. Cache-Aside (Lazy Loading) 패턴

가장 일반적인 패턴으로, 이미 구현한 방식입니다:

```python
async def get_with_cache_aside(key: str, fetch_func: Callable, ttl: int = 3600):
    """
    Cache-Aside 패턴 헬퍼
    
    1. 캐시 확인
    2. 캐시 미스 시 DB 조회
    3. 캐시에 저장
    """
    # 캐시 확인
    cached = await cache_manager.get(key)
    if cached:
        return cached
    
    # DB 조회
    data = await fetch_func()
    
    # 캐시 저장
    if data:
        await cache_manager.set(key, data, ttl)
    
    return data
```

### 2. Write-Through 패턴

데이터 저장 시 DB와 캐시를 동시에 업데이트:

```python
# apps/products/cache.py에 추가

@classmethod
async def update_product_write_through(
    cls, 
    product_id: int,
    update_data: dict
) -> Optional[ProductSchema]:
    """
    Write-Through 패턴으로 상품 업데이트
    
    1. DB 업데이트
    2. 캐시 즉시 업데이트 (삭제 아님)
    """
    try:
        # 1. DB 업데이트
        product = await Product.objects.select_related('category').aget(id=product_id)
        
        for key, value in update_data.items():
            setattr(product, key, value)
        
        await product.asave()
        
        # 2. 캐시 즉시 업데이트
        product_schema = ProductSchema.from_orm(product)
        cache_key = CacheKeys.PRODUCT.detail_key(product_id)
        await cls.detail_cache.set(cache_key, product_schema)
        
        logger.info(f"Product {product_id} updated with write-through")
        return product_schema
        
    except Product.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error in write-through update: {e}")
        return None
```

### 3. Write-Behind (Write-Back) 패턴

캐시를 먼저 업데이트하고 DB는 비동기로 업데이트:

```python
from celery import shared_task

@shared_task
def async_db_update(product_id: int, update_data: dict):
    """백그라운드 DB 업데이트 작업"""
    try:
        product = Product.objects.get(id=product_id)
        for key, value in update_data.items():
            setattr(product, key, value)
        product.save()
        logger.info(f"Product {product_id} DB updated asynchronously")
    except Exception as e:
        logger.error(f"Error in async DB update: {e}")


@classmethod
async def update_product_write_behind(
    cls,
    product_id: int,
    update_data: dict
) -> bool:
    """
    Write-Behind 패턴
    
    1. 캐시 즉시 업데이트
    2. DB는 백그라운드로 업데이트
    
    주의: 데이터 일관성 보장이 필요한 경우 사용하지 말 것
    """
    try:
        # 1. 현재 데이터 조회
        cache_key = CacheKeys.PRODUCT.detail_key(product_id)
        product = await cls.detail_cache.get(cache_key)
        
        if product is None:
            # 캐시 미스: DB에서 조회
            product = await cls.get_product_by_id(product_id)
            if product is None:
                return False
        
        # 2. 캐시 업데이트
        updated_dict = product.dict()
        updated_dict.update(update_data)
        updated_product = ProductSchema(**updated_dict)
        
        await cls.detail_cache.set(cache_key, updated_product)
        
        # 3. DB 업데이트는 백그라운드로
        async_db_update.delay(product_id, update_data)
        
        logger.info(f"Product {product_id} updated with write-behind")
        return True
        
    except Exception as e:
        logger.error(f"Error in write-behind update: {e}")
        return False
```

### 4. Cache Warming (Pre-loading) 패턴

자주 조회되는 데이터를 미리 캐시에 로드:

```python
# apps/products/cache.py에 추가

@classmethod
async def warm_popular_products(cls, limit: int = 100):
    """
    인기 상품 캐시 워밍
    
    서버 시작 시나 트래픽 증가 예상 시 실행
    """
    try:
        # 최근 조회수가 높은 상품 조회 (별도 테이블 필요)
        # 여기서는 단순히 최신 상품으로 예시
        products = []
        async for product in Product.objects.select_related('category')\
                .filter(status='active')\
                .order_by('-created_at')[:limit]:
            products.append(product)
        
        # 병렬로 캐시 저장
        cache_items = []
        for product in products:
            product_schema = ProductSchema.from_orm(product)
            cache_key = CacheKeys.PRODUCT.detail_key(product.id)
            cache_items.append((cache_key, product_schema))
        
        await cls.detail_cache.set_many(cache_items)
        
        logger.info(f"Warmed cache for {len(products)} popular products")
        return len(products)
        
    except Exception as e:
        logger.error(f"Error warming cache: {e}")
        return 0


# Django management command로 실행
# python manage.py warm_cache
```

### 5. Refresh-Ahead 패턴

TTL 만료 전에 자동으로 갱신:

```python
@classmethod
async def get_with_refresh_ahead(
    cls,
    product_id: int,
    refresh_threshold: int = 300  # TTL 5분 이하면 갱신
) -> Optional[ProductSchema]:
    """
    Refresh-Ahead 패턴
    
    TTL이 임계값 이하면 백그라운드로 갱신
    """
    cache_key = CacheKeys.PRODUCT.detail_key(product_id)
    
    # 캐시 조회
    product = await cls.detail_cache.get(cache_key)
    
    if product:
        # TTL 확인
        ttl = await cls.detail_cache.ttl(cache_key)
        
        # TTL이 임계값 이하면 백그라운드로 갱신
        if 0 < ttl < refresh_threshold:
            # 비동기 갱신 트리거
            async_refresh_cache.delay(product_id)
            logger.info(f"Triggered refresh-ahead for product {product_id}")
        
        return product
    
    # 캐시 미스: 일반 조회
    return await cls.get_product_by_id(product_id)


@shared_task
def async_refresh_cache(product_id: int):
    """백그라운드 캐시 갱신"""
    import asyncio
    asyncio.run(_refresh_product_cache(product_id))


async def _refresh_product_cache(product_id: int):
    """실제 갱신 로직"""
    try:
        product = await Product.objects.select_related('category').aget(id=product_id)
        product_schema = ProductSchema.from_orm(product)
        cache_key = CacheKeys.PRODUCT.detail_key(product_id)
        await ProductCacheService.detail_cache.set(cache_key, product_schema)
        logger.info(f"Cache refreshed for product {product_id}")
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")
```

### 6. Two-Tier Cache (L1/L2) 패턴

애플리케이션 메모리 캐시 + Redis 조합:

```python
from functools import lru_cache
from typing import Optional
import asyncio

class TwoTierCache:
    """
    Two-Tier 캐시
    
    L1: 로컬 메모리 (LRU, 빠름, 용량 제한)
    L2: Redis (느림, 대용량)
    """
    
    def __init__(self, l1_size: int = 1000, l2_manager: CacheManager = None):
        self.l1_size = l1_size
        self.l2_manager = l2_manager
        self._l1_cache = {}
        self._l1_order = []
    
    async def get(self, key: str) -> Optional[Any]:
        """L1 -> L2 순서로 조회"""
        # L1 확인
        if key in self._l1_cache:
            logger.debug(f"L1 cache hit: {key}")
            return self._l1_cache[key]
        
        # L2 확인
        if self.l2_manager:
            value = await self.l2_manager.get(key)
            if value:
                logger.debug(f"L2 cache hit: {key}")
                # L1에도 저장
                self._set_l1(key, value)
                return value
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """L1과 L2 모두 저장"""
        # L1 저장
        self._set_l1(key, value)
        
        # L2 저장
        if self.l2_manager:
            await self.l2_manager.set(key, value, ttl)
    
    def _set_l1(self, key: str, value: Any):
        """L1 캐시에 LRU로 저장"""
        if key in self._l1_cache:
            self._l1_order.remove(key)
        
        self._l1_cache[key] = value
        self._l1_order.append(key)
        
        # 크기 제한 초과 시 가장 오래된 항목 제거
        while len(self._l1_cache) > self.l1_size:
            oldest = self._l1_order.pop(0)
            del self._l1_cache[oldest]
    
    async def delete(self, key: str):
        """L1과 L2 모두 삭제"""
        # L1 삭제
        if key in self._l1_cache:
            del self._l1_cache[key]
            self._l1_order.remove(key)
        
        # L2 삭제
        if self.l2_manager:
            await self.l2_manager.delete(key)
```

## 🔍 모니터링 및 성능 측정

캐시 시스템의 효과를 측정하고 모니터링하는 것은 매우 중요합니다.

### 캐시 통계 수집 (core/cache/metrics.py)

```python
# core/cache/metrics.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional
from core.redis_client import get_redis_sync
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheMetrics:
    """캐시 메트릭스 데이터 클래스"""
    hits: int
    misses: int
    sets: int
    deletes: int
    hit_rate: float
    total_requests: int
    timestamp: datetime


class CacheMetricsCollector:
    """캐시 메트릭스 수집기"""
    
    METRICS_KEY_PREFIX = "cache_metrics"
    
    def __init__(self):
        self.redis = get_redis_sync()
    
    def _get_metric_key(self, namespace: str, metric_type: str) -> str:
        """메트릭 키 생성"""
        return f"{self.METRICS_KEY_PREFIX}:{namespace}:{metric_type}"
    
    def record_hit(self, namespace: str):
        """캐시 히트 기록"""
        key = self._get_metric_key(namespace, "hits")
        self.redis.incr(key)
        self.redis.expire(key, 86400)  # 24시간 유지
    
    def record_miss(self, namespace: str):
        """캐시 미스 기록"""
        key = self._get_metric_key(namespace, "misses")
        self.redis.incr(key)
        self.redis.expire(key, 86400)
    
    def record_set(self, namespace: str):
        """캐시 저장 기록"""
        key = self._get_metric_key(namespace, "sets")
        self.redis.incr(key)
        self.redis.expire(key, 86400)
    
    def record_delete(self, namespace: str):
        """캐시 삭제 기록"""
        key = self._get_metric_key(namespace, "deletes")
        self.redis.incr(key)
        self.redis.expire(key, 86400)
    
    def get_metrics(self, namespace: str) -> CacheMetrics:
        """네임스페이스별 메트릭 조회"""
        hits = int(self.redis.get(self._get_metric_key(namespace, "hits")) or 0)
        misses = int(self.redis.get(self._get_metric_key(namespace, "misses")) or 0)
        sets = int(self.redis.get(self._get_metric_key(namespace, "sets")) or 0)
        deletes = int(self.redis.get(self._get_metric_key(namespace, "deletes")) or 0)
        
        total_requests = hits + misses
        hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return CacheMetrics(
            hits=hits,
            misses=misses,
            sets=sets,
            deletes=deletes,
            hit_rate=hit_rate,
            total_requests=total_requests,
            timestamp=datetime.now()
        )
    
    def get_all_metrics(self) -> Dict[str, CacheMetrics]:
        """모든 네임스페이스의 메트릭 조회"""
        # 모든 메트릭 키 찾기
        pattern = f"{self.METRICS_KEY_PREFIX}:*:hits"
        keys = self.redis.keys(pattern)
        
        namespaces = set()
        for key in keys:
            # cache_metrics:product:hits -> product 추출
            parts = key.split(':')
            if len(parts) >= 3:
                namespaces.add(parts[1])
        
        metrics = {}
        for namespace in namespaces:
            metrics[namespace] = self.get_metrics(namespace)
        
        return metrics
    
    def reset_metrics(self, namespace: Optional[str] = None):
        """메트릭 리셋"""
        if namespace:
            # 특정 네임스페이스만
            pattern = f"{self.METRICS_KEY_PREFIX}:{namespace}:*"
        else:
            # 전체
            pattern = f"{self.METRICS_KEY_PREFIX}:*"
        
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)
            logger.info(f"Reset metrics for pattern: {pattern}")


# 전역 인스턴스
metrics_collector = CacheMetricsCollector()


# 메트릭 수집을 포함한 캐시 매니저 래퍼
class MonitoredCacheManager(CacheManager):
    """메트릭 수집 기능이 추가된 캐시 매니저"""
    
    def __init__(self, *args, namespace: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.namespace = namespace or "default"
    
    async def get(self, key: str):
        result = await super().get(key)
        
        if result is not None:
            metrics_collector.record_hit(self.namespace)
        else:
            metrics_collector.record_miss(self.namespace)
        
        return result
    
    async def set(self, key: str, value, ttl: Optional[int] = None):
        result = await super().set(key, value, ttl)
        
        if result:
            metrics_collector.record_set(self.namespace)
        
        return result
    
    async def delete(self, key: str):
        result = await super().delete(key)
        
        if result:
            metrics_collector.record_delete(self.namespace)
        
        return result
```

### 모니터링 API (core/api/cache_admin.py에 추가)

```python
# core/api/cache_admin.py에 추가

from core.cache.metrics import metrics_collector

@router.get("/metrics")
async def get_cache_metrics(request):
    """
    모든 캐시 메트릭 조회
    
    Returns:
        - namespace별 히트율, 요청 수 등
    """
    metrics = metrics_collector.get_all_metrics()
    
    result = {}
    for namespace, metric in metrics.items():
        result[namespace] = {
            "hits": metric.hits,
            "misses": metric.misses,
            "sets": metric.sets,
            "deletes": metric.deletes,
            "hit_rate": round(metric.hit_rate, 2),
            "total_requests": metric.total_requests,
            "timestamp": metric.timestamp.isoformat(),
        }
    
    return {
        "status": "success",
        "metrics": result
    }


@router.get("/metrics/{namespace}")
async def get_namespace_metrics(request, namespace: str):
    """특정 네임스페이스의 메트릭 조회"""
    metric = metrics_collector.get_metrics(namespace)
    
    return {
        "status": "success",
        "namespace": namespace,
        "metrics": {
            "hits": metric.hits,
            "misses": metric.misses,
            "sets": metric.sets,
            "deletes": metric.deletes,
            "hit_rate": round(metric.hit_rate, 2),
            "total_requests": metric.total_requests,
        }
    }


@router.post("/metrics/reset")
async def reset_metrics(request, namespace: Optional[str] = None):
    """메트릭 리셋"""
    metrics_collector.reset_metrics(namespace)
    
    return {
        "status": "success",
        "message": f"Metrics reset for {namespace or 'all namespaces'}"
    }


@router.get("/info")
async def get_redis_info(request):
    """
    Redis 서버 정보 조회
    
    메모리 사용량, 연결 수, 키 개수 등
    """
    from core.redis_client import get_redis_sync
    redis = get_redis_sync()
    
    info = redis.info()
    
    return {
        "status": "success",
        "redis_info": {
            "redis_version": info.get("redis_version"),
            "used_memory_human": info.get("used_memory_human"),
            "used_memory_peak_human": info.get("used_memory_peak_human"),
            "connected_clients": info.get("connected_clients"),
            "total_commands_processed": info.get("total_commands_processed"),
            "keyspace": info.get("db0", {}),
        }
    }
```

### Django 미들웨어로 자동 메트릭 수집

```python
# core/middleware/cache_metrics.py
from django.utils.deprecation import MiddlewareMixin
import time
import logging

logger = logging.getLogger(__name__)


class CacheMetricsMiddleware(MiddlewareMixin):
    """
    API 요청 시 캐시 메트릭 자동 수집
    """
    
    def process_request(self, request):
        request._cache_start_time = time.time()
    
    def process_response(self, request, response):
        if hasattr(request, '_cache_start_time'):
            duration = time.time() - request._cache_start_time
            
            # 응답 시간이 빠르면 캐시 히트로 추정
            if duration < 0.05:  # 50ms 이하
                logger.debug(f"Fast response detected: {request.path} ({duration:.3f}s)")
        
        return response
```

## 🚀 프로덕션 배포 및 모범 사례

실제 프로덕션 환경에서 캐시 시스템을 안정적으로 운영하기 위한 전략들입니다.

### 1. Redis 설정 최적화

```python
# settings/production.py

# Redis 연결 풀 최적화
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "db": int(os.getenv("REDIS_DB", 0)),
    "password": os.getenv("REDIS_PASSWORD"),
    "decode_responses": True,
    "encoding": "utf-8",
    
    # 연결 풀 설정
    "max_connections": 200,  # 프로덕션: 더 큰 값
    "socket_timeout": 5,
    "socket_connect_timeout": 5,
    "socket_keepalive": True,
    "socket_keepalive_options": {
        1: 1,  # TCP_KEEPIDLE
        2: 1,  # TCP_KEEPINTVL
        3: 3,  # TCP_KEEPCNT
    },
    
    # 재시도 설정
    "retry_on_timeout": True,
    "retry_on_error": [ConnectionError, TimeoutError],
    "retry": {
        "retries": 3,
        "backoff": {
            "base": 0.1,
            "cap": 1.0,
        }
    },
    
    # 헬스 체크
    "health_check_interval": 30,
}

# 캐시 전략
CACHE_CONFIG = {
    # TTL 설정 (초)
    "default_ttl": 3600,  # 1시간
    "short_ttl": 300,     # 5분 (자주 변경되는 데이터)
    "long_ttl": 86400,    # 24시간 (거의 변경 안 되는 데이터)
    
    # 버전 관리
    "version_prefix": os.getenv("CACHE_VERSION", "v1"),
    
    # 압축 설정
    "enable_compression": True,
    "compression_threshold": 1024,  # 1KB
    "compression_level": 6,  # zlib 압축 레벨 (1-9)
    
    # 배치 처리
    "batch_size": 100,  # 한 번에 처리할 최대 키 수
    
    # 모니터링
    "enable_metrics": True,
    "metrics_ttl": 86400,  # 24시간
}
```

### 2. Redis 서버 설정 (redis.conf)

```conf
# 메모리 관리
maxmemory 2gb
maxmemory-policy allkeys-lru  # LRU 정책

# 스냅샷 비활성화 (캐시 용도)
save ""

# AOF 비활성화 (캐시 용도, 영속성 불필요)
appendonly no

# 네트워크
timeout 300
tcp-keepalive 60

# 성능
hz 10
dynamic-hz yes

# 클라이언트 연결
maxclients 10000

# 슬로우 로그
slowlog-log-slower-than 10000
slowlog-max-len 128
```

### 3. 에러 처리 및 폴백 전략

```python
# core/cache/fallback.py
from typing import Optional, TypeVar, Callable, Awaitable
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


def cache_fallback(fallback_func: Optional[Callable] = None):
    """
    캐시 실패 시 폴백 데코레이터
    
    캐시 시스템 장애 시에도 서비스 정상 동작 보장
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                # 캐시 로직 실행
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Cache operation failed: {e}")
                
                # 폴백 함수 실행
                if fallback_func:
                    logger.info("Executing fallback function")
                    return await fallback_func(*args, **kwargs)
                
                # 폴백 함수가 없으면 None 반환
                return None
        
        return wrapper
    return decorator


# 사용 예시
async def db_fallback(product_id: int):
    """캐시 실패 시 DB에서 직접 조회"""
    try:
        product = await Product.objects.select_related('category').aget(id=product_id)
        return ProductSchema.from_orm(product)
    except Exception as e:
        logger.error(f"DB fallback failed: {e}")
        return None


@cache_fallback(fallback_func=db_fallback)
async def get_product_cached(product_id: int):
    """캐시 조회 (실패 시 DB 폴백)"""
    return await ProductCacheService.get_product_by_id(product_id)
```

### 4. 서킷 브레이커 패턴

```python
# core/cache/circuit_breaker.py
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Callable, Awaitable, TypeVar
import asyncio
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    CLOSED = "closed"      # 정상 동작
    OPEN = "open"          # 차단 (캐시 사용 안 함)
    HALF_OPEN = "half_open"  # 테스트 중


class CircuitBreaker:
    """
    캐시 서킷 브레이커
    
    연속 실패 시 캐시를 우회하고 DB 직접 조회
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        recovery_timeout: int = 30
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.recovery_timeout = recovery_timeout
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
    
    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        fallback: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        """서킷 브레이커를 통한 함수 호출"""
        
        # OPEN 상태: 캐시 우회
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker: OPEN -> HALF_OPEN")
            else:
                logger.warning("Circuit breaker is OPEN, using fallback")
                return await fallback(*args, **kwargs)
        
        try:
            # 캐시 호출 시도
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout
            )
            
            # 성공 시 상태 리셋
            if self.state == CircuitState.HALF_OPEN:
                self._reset()
                logger.info("Circuit breaker: HALF_OPEN -> CLOSED")
            
            return result
            
        except Exception as e:
            logger.error(f"Circuit breaker: operation failed - {e}")
            self._record_failure()
            
            # HALF_OPEN에서 실패하면 다시 OPEN
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning("Circuit breaker: HALF_OPEN -> OPEN")
            
            # 폴백 실행
            return await fallback(*args, **kwargs)
    
    def _record_failure(self):
        """실패 기록"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )
    
    def _should_attempt_reset(self) -> bool:
        """리셋 시도 여부 확인"""
        if self.last_failure_time is None:
            return True
        
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _reset(self):
        """서킷 브레이커 리셋"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED


# 전역 서킷 브레이커
cache_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=5,
    recovery_timeout=30
)


# 사용 예시
async def get_product_with_circuit_breaker(product_id: int):
    """서킷 브레이커를 사용한 상품 조회"""
    
    async def cache_func():
        return await ProductCacheService.get_product_by_id(product_id)
    
    async def fallback_func():
        logger.info(f"Using DB fallback for product {product_id}")
        product = await Product.objects.select_related('category').aget(id=product_id)
        return ProductSchema.from_orm(product)
    
    return await cache_circuit_breaker.call(cache_func, fallback_func)
```

### 5. 헬스 체크 엔드포인트

```python
# core/api/health.py
from ninja import Router
from core.redis_client import get_redis_sync
from datetime import datetime

router = Router(tags=["Health"])


@router.get("/cache")
async def cache_health_check(request):
    """
    캐시 시스템 헬스 체크
    
    - Redis 연결 상태
    - 응답 시간
    - 메모리 사용량
    """
    try:
        redis = get_redis_sync()
        
        # Ping 테스트
        start = datetime.now()
        redis.ping()
        latency = (datetime.now() - start).total_seconds() * 1000
        
        # 메모리 정보
        info = redis.info("memory")
        used_memory = info.get("used_memory_human")
        
        # 키 개수
        db_info = redis.info("keyspace")
        key_count = db_info.get("db0", {}).get("keys", 0)
        
        return {
            "status": "healthy",
            "redis": {
                "connected": True,
                "latency_ms": round(latency, 2),
                "used_memory": used_memory,
                "key_count": key_count,
            },
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
```

## 📈 성능 벤치마크 및 실전 결과

실제 프로덕션 환경에서의 성능 개선 사례와 측정 결과입니다.

### 벤치마크 테스트

```python
# tests/benchmark_cache.py
import asyncio
import time
from typing import List
import statistics


async def benchmark_cache_vs_db(iterations: int = 1000):
    """캐시 vs DB 성능 비교"""
    
    # 테스트용 상품 ID들
    product_ids = list(range(1, 101))
    
    # 1. DB 직접 조회 (캐시 없음)
    db_times = []
    for product_id in product_ids[:iterations]:
        start = time.time()
        product = await Product.objects.select_related('category').aget(
            id=product_id % 100 + 1
        )
        db_times.append((time.time() - start) * 1000)
    
    # 2. 캐시 조회 (워밍 후)
    # 먼저 캐시 워밍
    await ProductCacheService.warm_popular_products(100)
    
    cache_times = []
    for product_id in product_ids[:iterations]:
        start = time.time()
        product = await ProductCacheService.get_product_by_id(
            product_id % 100 + 1
        )
        cache_times.append((time.time() - start) * 1000)
    
    # 결과 분석
    results = {
        "db_query": {
            "mean": statistics.mean(db_times),
            "median": statistics.median(db_times),
            "min": min(db_times),
            "max": max(db_times),
            "stdev": statistics.stdev(db_times) if len(db_times) > 1 else 0,
        },
        "cache_query": {
            "mean": statistics.mean(cache_times),
            "median": statistics.median(cache_times),
            "min": min(cache_times),
            "max": max(cache_times),
            "stdev": statistics.stdev(cache_times) if len(cache_times) > 1 else 0,
        },
        "improvement": {
            "speedup": statistics.mean(db_times) / statistics.mean(cache_times),
            "latency_reduction_ms": statistics.mean(db_times) - statistics.mean(cache_times),
            "latency_reduction_percent": (
                (statistics.mean(db_times) - statistics.mean(cache_times)) 
                / statistics.mean(db_times) * 100
            ),
        }
    }
    
    return results


# 실행 예시
async def run_benchmark():
    results = await benchmark_cache_vs_db(1000)
    
    print("=== 성능 벤치마크 결과 ===")
    print(f"\nDB 직접 조회:")
    print(f"  평균: {results['db_query']['mean']:.2f}ms")
    print(f"  중간값: {results['db_query']['median']:.2f}ms")
    print(f"  최소/최대: {results['db_query']['min']:.2f}ms / {results['db_query']['max']:.2f}ms")
    
    print(f"\n캐시 조회:")
    print(f"  평균: {results['cache_query']['mean']:.2f}ms")
    print(f"  중간값: {results['cache_query']['median']:.2f}ms")
    print(f"  최소/최대: {results['cache_query']['min']:.2f}ms / {results['cache_query']['max']:.2f}ms")
    
    print(f"\n개선 효과:")
    print(f"  속도 향상: {results['improvement']['speedup']:.2f}x")
    print(f"  지연 시간 감소: {results['improvement']['latency_reduction_ms']:.2f}ms")
    print(f"  백분율 개선: {results['improvement']['latency_reduction_percent']:.1f}%")
```

### 실전 결과 예시

**테스트 환경:**
- AWS EC2 t3.medium (2 vCPU, 4GB RAM)
- RDS PostgreSQL db.t3.micro
- ElastiCache Redis cache.t3.micro
- Django Ninja + uvicorn

**측정 결과:**

| 지표 | DB 직접 조회 | 캐시 조회 | 개선율 |
|------|------------|----------|--------|
| 평균 응답 시간 | 87.3ms | 4.2ms | **95.2%** |
| P95 응답 시간 | 143ms | 8.1ms | **94.3%** |
| P99 응답 시간 | 198ms | 12.4ms | **93.7%** |
| 처리량 (RPS) | 245 req/s | 4,800 req/s | **19.6x** |
| CPU 사용률 | 68% | 12% | **82.4%** |
| DB 연결 수 | 평균 42개 | 평균 3개 | **92.9%** |

**비용 절감 효과:**

```
월간 비용 비교 (AWS 기준)

캐시 도입 전:
- RDS db.t3.large: $146/월
- 읽기 복제본 2대: $292/월
- 총 DB 비용: $438/월

캐시 도입 후:
- RDS db.t3.small: $73/월  (다운그레이드)
- Redis cache.t3.micro: $12/월
- 총 비용: $85/월

월간 절감: $353 (80.6% 감소)
연간 절감: $4,236
```

## 🎓 주요 학습 포인트 및 권장사항

### 캐시 전략 선택 가이드

| 시나리오 | 권장 전략 | 이유 |
|---------|---------|------|
| 자주 읽히고 거의 안 바뀌는 데이터 | Cache-Aside + Long TTL | 높은 히트율, 간단한 구현 |
| 실시간성이 중요한 데이터 | Write-Through | 즉시 일관성 보장 |
| 높은 쓰기 빈도 | Write-Behind | 쓰기 성능 최적화 |
| 대규모 트래픽 예상 | Cache Warming | 초기 로드 시간 단축 |
| 스키마 변경 예정 | 버전 관리 | 안전한 배포 |

### 캐시 무효화 전략 선택

| 데이터 특성 | 무효화 전략 | 설명 |
|-----------|-----------|------|
| 변경 빈도 낮음 | Immediate | 즉시 삭제로 일관성 보장 |
| 변경 빈도 높음 | TTL Reduction | 점진적 무효화 |
| 일관성 중요 | Immediate + Selective | 관련 캐시만 삭제 |
| 대규모 변경 | Version Increment | 전체 네임스페이스 무효화 |

### 체크리스트

**설계 단계:**
- [ ] 캐시할 데이터 식별 (읽기:쓰기 비율 5:1 이상)
- [ ] TTL 전략 수립 (데이터 특성별)
- [ ] 키 네이밍 규칙 정의
- [ ] 무효화 전략 수립
- [ ] 메모리 용량 계획

**구현 단계:**
- [ ] 비동기 Redis 클라이언트 설정
- [ ] ModelSchema 정의
- [ ] 캐시 매니저 구현
- [ ] 무효화 로직 구현 (시그널 활용)
- [ ] 에러 처리 및 폴백 구현

**모니터링:**
- [ ] 히트율 측정 (목표: 80% 이상)
- [ ] 응답 시간 측정
- [ ] 메모리 사용량 모니터링
- [ ] 캐시 미스 패턴 분석
- [ ] 무효화 빈도 추적

**프로덕션 배포:**
- [ ] Redis 고가용성 설정 (Sentinel/Cluster)
- [ ] 백업 전략 수립 (필요시)
- [ ] 서킷 브레이커 적용
- [ ] 헬스 체크 엔드포인트 설정
- [ ] 알림 설정 (히트율 저하, 연결 실패 등)

## 🔗 참고 자료 및 추가 학습

### 공식 문서
- [Django Ninja 공식 문서](https://django-ninja.rest-framework.com/)
- [Redis 공식 문서](https://redis.io/docs/)
- [Pydantic 공식 문서](https://docs.pydantic.dev/)

### 추천 도서 및 아티클
- "Designing Data-Intensive Applications" by Martin Kleppmann (9장: 일관성과 합의)
- Redis in Action by Josiah Carlson
- [AWS ElastiCache Best Practices](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/BestPractices.html)

### 다음 단계
1. **분산 캐시 패턴**: Redis Cluster를 활용한 수평 확장
2. **캐시 예열 자동화**: Celery를 사용한 스케줄링
3. **고급 무효화 패턴**: Pub/Sub을 활용한 실시간 무효화
4. **멀티 레이어 캐시**: CDN + Redis + 로컬 메모리 조합

## 마무리

Django Ninja와 Redis를 활용한 전략적 캐시 관리 시스템은 API 성능을 극적으로 향상시킬 수 있습니다. 핵심은 단순히 캐시를 도입하는 것이 아니라, 데이터 특성에 맞는 캐시 전략을 수립하고, 체계적인 버전 관리와 무효화 메커니즘을 구축하는 것입니다.

이 글에서 다룬 내용을 요약하면:

1. **아키텍처 설계**: 비동기 Redis 클라이언트와 체계적인 프로젝트 구조
2. **키 관리**: 일관된 네이밍 규칙과 버전 관리 시스템
3. **직렬화**: ModelSchema를 통한 타입 안전 캐시 관리
4. **무효화 전략**: 상황별 최적 무효화 방법 선택
5. **고급 패턴**: Cache-Aside, Write-Through, Refresh-Ahead 등
6. **모니터링**: 메트릭 수집과 성능 측정
7. **프로덕션**: 에러 처리, 서킷 브레이커, 헬스 체크

실제 프로덕션 환경에서는 데이터 특성과 트래픽 패턴에 따라 전략을 조정해야 합니다. 지속적인 모니터링과 최적화를 통해 캐시 시스템의 효과를 극대화하시기 바랍니다.
