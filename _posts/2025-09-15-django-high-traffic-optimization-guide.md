---
layout: post
title: "Django 대용량 트래픽 처리 완전 가이드: 초당 10만 요청을 감당하는 아키텍처"
date: 2025-09-15 14:00:00 +0900
categories: [Django, Performance, Scalability, Architecture]
tags: [Django, High Traffic, Performance Optimization, Scalability, Load Balancing, Caching, Database Optimization, ASGI, Microservices]
image: "/assets/img/posts/2025-09-15-django-high-traffic-optimization-guide.webp"
---

Django로 구축한 서비스가 성장하면서 **대용량 트래픽**을 처리해야 하는 상황에 직면하게 됩니다. 초당 수천, 수만 건의 요청을 안정적으로 처리하면서도 빠른 응답 시간을 유지하는 것은 쉽지 않은 도전입니다. 이 글에서는 Django 애플리케이션을 **대용량 트래픽에 최적화**하는 종합적인 전략을 실전 중심으로 다루겠습니다.

## 🎯 대용량 트래픽 처리의 핵심 원칙

### 성능 목표 설정

실제 대용량 서비스에서 목표로 하는 성능 지표들을 살펴보겠습니다.

```python
# 성능 목표 예시
PERFORMANCE_TARGETS = {
    '응답_시간': {
        'P95': '200ms',  # 95%의 요청이 200ms 이내 응답
        'P99': '500ms',  # 99%의 요청이 500ms 이내 응답
        '평균': '100ms'   # 평균 응답 시간
    },
    '처리량': {
        '초당_요청수': 50000,  # 50K RPS
        '일일_요청수': 4_000_000_000,  # 40억 요청/일
        '동시_사용자': 100000  # 10만 동시 사용자
    },
    '가용성': {
        'SLA': '99.9%',  # 연간 8.76시간 다운타임
        'MTTR': '5분',   # 평균 복구 시간
        'MTBF': '30일'   # 평균 장애 간격
    },
    '리소스': {
        'CPU_사용률': '70%',  # 평균 CPU 사용률
        '메모리_사용률': '80%',  # 평균 메모리 사용률
        'DB_커넥션풀': '80%'   # DB 연결 사용률
    }
}
```

### 확장성 패턴 이해

```python
# 확장성의 두 가지 방향
SCALABILITY_PATTERNS = {
    '수직적_확장': {
        '설명': 'Scale Up - 서버 사양 업그레이드',
        '장점': ['구현 단순', '데이터 일관성'],
        '단점': ['비용 증가', '물리적 한계'],
        '적용_예': 'CPU/메모리 증설, SSD 업그레이드'
    },
    '수평적_확장': {
        '설명': 'Scale Out - 서버 대수 증가',
        '장점': ['무제한 확장', '장애 격리'],
        '단점': ['복잡성 증가', '데이터 동기화'],
        '적용_예': '로드 밸런서, 마이크로서비스'
    }
}
```

## 🏗️ 아키텍처 최적화 전략

### 1. ASGI vs WSGI: 비동기 처리의 위력

```python
# WSGI 기반 전통적 구조
# gunicorn settings.py
bind = "0.0.0.0:8000"
workers = 16  # CPU 코어 수 * 2
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
keepalive = 2
timeout = 30

# 동시 처리 가능 요청: 16 * 1 = 16개 (블로킹 I/O)

# ASGI 기반 비동기 구조
# uvicorn settings
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "myproject.asgi:application",
        host="0.0.0.0",
        port=8000,
        workers=4,  # CPU 코어 수
        loop="uvloop",  # 고성능 이벤트 루프
        http="httptools",  # 고성능 HTTP 파서
        access_log=False,  # 운영환경에서는 비활성화
        server_header=False
    )

# 동시 처리 가능 요청: 수천 개 (비블로킹 I/O)
```

### 2. Django 설정 최적화

```python
# settings/production.py
import os
from .base import *

# 보안 설정
DEBUG = False
ALLOWED_HOSTS = ['*.yourdomain.com', 'yourdomain.com']
SECRET_KEY = os.environ['SECRET_KEY']

# 데이터베이스 최적화
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_HOST'],
        'PORT': os.environ['DB_PORT'],
        'CONN_MAX_AGE': 600,  # 연결 재사용
        'OPTIONS': {
            'MAX_CONNS': 20,  # 최대 연결 수
            'connect_timeout': 10,
            'options': '-c default_transaction_isolation=read_committed'
        }
    },
    # 읽기 전용 복제본
    'read_replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_READONLY_USER'],
        'PASSWORD': os.environ['DB_READONLY_PASSWORD'],
        'HOST': os.environ['DB_READONLY_HOST'],
        'PORT': os.environ['DB_PORT'],
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'MAX_CONNS': 30,
            'connect_timeout': 10,
        }
    }
}

# 데이터베이스 라우팅
DATABASE_ROUTERS = ['myproject.routers.DatabaseRouter']

# 캐시 설정
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{os.environ['REDIS_HOST']}:6379/0",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'TIMEOUT': 300,
        'KEY_PREFIX': 'myproject',
        'VERSION': 1,
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{os.environ['REDIS_HOST']}:6379/1",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 30},
        },
        'TIMEOUT': 86400,  # 24시간
    }
}

# 세션 최적화
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'
SESSION_COOKIE_AGE = 86400  # 24시간
SESSION_SAVE_EVERY_REQUEST = False  # 성능 최적화

# 정적 파일 최적화
STATIC_URL = f"https://{os.environ['CDN_DOMAIN']}/static/"
MEDIA_URL = f"https://{os.environ['CDN_DOMAIN']}/media/"

# 압축 및 최적화
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

## 🗄️ 데이터베이스 최적화 전략

데이터베이스는 대용량 트래픽 처리에서 가장 중요한 병목점 중 하나입니다. 효과적인 데이터베이스 최적화를 통해 성능을 극적으로 향상시킬 수 있습니다.

### 1. 데이터베이스 라우팅과 읽기 복제본 활용

```python
# myproject/routers.py
class DatabaseRouter:
    """
    읽기/쓰기 분산을 위한 데이터베이스 라우터
    읽기 작업은 복제본으로, 쓰기 작업은 마스터로 라우팅
    """
    
    READ_ONLY_MODELS = {
        'analytics', 'reports', 'logs'  # 읽기 전용 모델들
    }
    
    def db_for_read(self, model, **hints):
        """읽기 작업 라우팅"""
        
        # 특정 모델은 항상 읽기 전용 DB 사용
        if model._meta.app_label in self.READ_ONLY_MODELS:
            return 'read_replica'
        
        # 현재 스레드가 트랜잭션 중이면 마스터 DB 사용
        from django.db import transaction
        if transaction.get_connection().in_atomic_block:
            return 'default'
        
        # 일반적인 읽기 작업은 복제본으로
        return 'read_replica'
    
    def db_for_write(self, model, **hints):
        """쓰기 작업은 항상 마스터 DB"""
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """관계 허용 여부"""
        db_set = {'default', 'read_replica'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """마이그레이션 허용 여부"""
        return db == 'default'

# 수동 데이터베이스 선택을 위한 매니저
class ReadOnlyManager(models.Manager):
    """읽기 전용 매니저"""
    
    def get_queryset(self):
        return super().get_queryset().using('read_replica')

class OptimizedQueryManager(models.Manager):
    """최적화된 쿼리 매니저"""
    
    def get_queryset(self):
        return super().get_queryset().select_related().prefetch_related()
    
    def high_traffic_filter(self, **kwargs):
        """대용량 트래픽용 필터"""
        return self.get_queryset().filter(**kwargs).only(
            'id', 'name', 'status'  # 필요한 필드만 조회
        )
    
    def with_cache(self, cache_key, timeout=300):
        """캐시와 함께 조회"""
        from django.core.cache import cache
        
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        result = list(self.get_queryset())
        cache.set(cache_key, result, timeout)
        return result

# 모델 예제
class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='active', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = models.Manager()  # 기본 매니저
    readonly = ReadOnlyManager()  # 읽기 전용 매니저
    optimized = OptimizedQueryManager()  # 최적화된 매니저
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at']),  # 복합 인덱스
            models.Index(fields=['category', 'price']),
            models.Index(fields=['-created_at']),  # 정렬용 인덱스
        ]
        db_table = 'products'
```

### 2. 연결 풀링과 커넥션 최적화

```python
# PostgreSQL 연결 풀 최적화
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_HOST'],
        'PORT': os.environ['DB_PORT'],
        'CONN_MAX_AGE': 600,  # 10분간 연결 재사용
        'OPTIONS': {
            'MAX_CONNS': 20,  # 프로세스당 최대 연결 수
            'MIN_CONNS': 5,   # 최소 연결 수 유지
            'connect_timeout': 10,
            'options': '-c default_transaction_isolation=read_committed'
        },
        'TEST': {
            'NAME': 'test_' + os.environ['DB_NAME'],
        }
    }
}

# 커스텀 데이터베이스 래퍼
class DatabaseConnectionManager:
    """데이터베이스 연결 관리"""
    
    def __init__(self):
        self.connection_stats = {
            'total_queries': 0,
            'slow_queries': 0,
            'connection_errors': 0,
            'active_connections': 0
        }
    
    def execute_query(self, sql, params=None, using='default'):
        """쿼리 실행 with 모니터링"""
        import time
        from django.db import connections
        
        start_time = time.time()
        
        try:
            connection = connections[using]
            with connection.cursor() as cursor:
                cursor.execute(sql, params or [])
                result = cursor.fetchall()
            
            execution_time = time.time() - start_time
            self.connection_stats['total_queries'] += 1
            
            # 느린 쿼리 감지
            if execution_time > 1.0:
                self.connection_stats['slow_queries'] += 1
                self.log_slow_query(sql, execution_time, params)
            
            return result
            
        except Exception as e:
            self.connection_stats['connection_errors'] += 1
            raise e
    
    def log_slow_query(self, sql, execution_time, params):
        """느린 쿼리 로깅"""
        import logging
        logger = logging.getLogger('slow_queries')
        
        logger.warning(f"Slow query detected: {execution_time:.3f}s")
        logger.warning(f"SQL: {sql}")
        logger.warning(f"Params: {params}")
    
    def get_connection_stats(self):
        """연결 통계 반환"""
        return self.connection_stats

# 전역 데이터베이스 매니저
db_manager = DatabaseConnectionManager()
```

### 3. 인덱스 최적화와 쿼리 성능 향상

```python
# 인덱스 전략
class IndexOptimizedModel(models.Model):
    """인덱스 최적화된 모델 예제"""
    
    # 기본 필드들
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending')
    ])
    category_id = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            # 1. 단일 필드 인덱스
            models.Index(fields=['status']),
            models.Index(fields=['category_id']),
            models.Index(fields=['-created_at']),  # 내림차순 정렬용
            
            # 2. 복합 인덱스 (순서 중요!)
            models.Index(fields=['status', 'category_id']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['category_id', 'price']),
            
            # 3. 부분 인덱스 (PostgreSQL)
            models.Index(
                fields=['name'],
                name='idx_active_products_name',
                condition=models.Q(status='active')
            ),
        ]

# 쿼리 최적화 유틸리티
class QueryOptimizer:
    """쿼리 최적화 도구"""
    
    @staticmethod
    def optimize_select_related(queryset, depth=2):
        """자동으로 select_related 최적화"""
        model = queryset.model
        select_fields = []
        
        for field in model._meta.get_fields():
            if hasattr(field, 'related_model') and depth > 0:
                if field.one_to_one or field.many_to_one:
                    select_fields.append(field.name)
        
        return queryset.select_related(*select_fields)
    
    @staticmethod
    def bulk_create_optimized(model_class, objects, batch_size=1000):
        """최적화된 bulk_create"""
        
        # 배치 단위로 처리
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            model_class.objects.bulk_create(
                batch,
                batch_size=batch_size,
                ignore_conflicts=True  # 중복 무시
            )

# 사용 예제
def get_products_optimized():
    """최적화된 상품 조회"""
    
    queryset = Product.objects.all()
    
    # 자동 최적화 적용
    queryset = QueryOptimizer.optimize_select_related(queryset)
    
    # 필요한 필드만 선택
    queryset = queryset.only('id', 'name', 'price', 'status')
    
    # 조건 최적화
    queryset = queryset.filter(
        status='active'
    ).order_by('-created_at')
    
    return queryset[:100]  # 페이지네이션
```

## 🎯 캐싱 전략: 성능의 핵심

캐싱은 대용량 트래픽 처리에서 가장 즉각적이고 효과적인 성능 향상 방법입니다. Django는 다양한 레벨의 캐싱을 지원합니다.

### 1. 다층 캐싱 아키텍처

```python
# 캐싱 계층 구조
CACHING_LAYERS = {
    'L1_Browser': {
        'location': 'Client Browser',
        'ttl': '1 hour',
        'scope': 'Static assets, API responses'
    },
    'L2_CDN': {
        'location': 'CloudFlare/AWS CloudFront',
        'ttl': '24 hours',
        'scope': 'Static files, Public content'
    },
    'L3_Reverse_Proxy': {
        'location': 'Nginx/Varnish',
        'ttl': '10 minutes',
        'scope': 'Full page cache'
    },
    'L4_Application': {
        'location': 'Django Cache Framework',
        'ttl': '5 minutes',
        'scope': 'View cache, Template fragments'
    },
    'L5_Database': {
        'location': 'Redis/Memcached',
        'ttl': '1 hour',
        'scope': 'Query results, Session data'
    }
}

# Redis 클러스터 설정
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': [
            f"redis://{os.environ['REDIS_NODE1']}:6379/0",
            f"redis://{os.environ['REDIS_NODE2']}:6379/0",
            f"redis://{os.environ['REDIS_NODE3']}:6379/0",
        ],
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.ShardClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
                'retry_on_timeout': True,
            },
            'SERIALIZER': 'django_redis.serializers.msgpack.MSGPackSerializer',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'TIMEOUT': 300,
        'KEY_PREFIX': 'myproject',
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{os.environ['REDIS_SESSION']}:6379/1",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50},
        },
        'TIMEOUT': 86400,
    },
    'long_term': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{os.environ['REDIS_LONGTERM']}:6379/2",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 30},
        },
        'TIMEOUT': 3600,  # 1시간
    }
}
```

### 2. 스마트 캐싱 매니저

```python
import hashlib
import pickle
import time
from django.core.cache import cache, caches
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
import logging

logger = logging.getLogger(__name__)

class SmartCacheManager:
    """지능형 캐싱 관리자"""
    
    def __init__(self):
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        self.cache_strategies = {
            'hot_data': {'timeout': 60, 'alias': 'default'},
            'warm_data': {'timeout': 300, 'alias': 'default'},
            'cold_data': {'timeout': 3600, 'alias': 'long_term'},
            'session_data': {'timeout': 86400, 'alias': 'sessions'}
        }
    
    def generate_cache_key(self, prefix, *args, **kwargs):
        """캐시 키 생성"""
        key_data = f"{prefix}:{':'.join(map(str, args))}:{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_cached_data(self, cache_key, strategy='warm_data'):
        """캐시된 데이터 조회"""
        cache_config = self.cache_strategies.get(strategy, self.cache_strategies['warm_data'])
        cache_instance = caches[cache_config['alias']]
        
        try:
            data = cache_instance.get(cache_key)
            if data is not None:
                self.cache_stats['hits'] += 1
                return data
            else:
                self.cache_stats['misses'] += 1
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.cache_stats['misses'] += 1
            return None
    
    def set_cached_data(self, cache_key, data, strategy='warm_data'):
        """데이터 캐싱"""
        cache_config = self.cache_strategies.get(strategy, self.cache_strategies['warm_data'])
        cache_instance = caches[cache_config['alias']]
        
        try:
            cache_instance.set(cache_key, data, cache_config['timeout'])
            self.cache_stats['sets'] += 1
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete_cached_data(self, cache_key, strategy='warm_data'):
        """캐시 삭제"""
        cache_config = self.cache_strategies.get(strategy, self.cache_strategies['warm_data'])
        cache_instance = caches[cache_config['alias']]
        
        try:
            cache_instance.delete(cache_key)
            self.cache_stats['deletes'] += 1
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def cached_function(self, timeout=300, strategy='warm_data', key_prefix=None):
        """함수 결과 캐싱 데코레이터"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # 캐시 키 생성
                if key_prefix:
                    cache_key = self.generate_cache_key(key_prefix, func.__name__, *args, **kwargs)
                else:
                    cache_key = self.generate_cache_key(func.__module__, func.__name__, *args, **kwargs)
                
                # 캐시에서 확인
                cached_result = self.get_cached_data(cache_key, strategy)
                if cached_result is not None:
                    return cached_result
                
                # 함수 실행
                result = func(*args, **kwargs)
                
                # 결과 캐싱
                self.set_cached_data(cache_key, result, strategy)
                
                return result
            return wrapper
        return decorator
    
    def invalidate_pattern(self, pattern):
        """패턴 매칭으로 캐시 무효화"""
        from django_redis import get_redis_connection
        
        for alias in ['default', 'long_term', 'sessions']:
            try:
                redis_conn = get_redis_connection(alias)
                for key in redis_conn.scan_iter(match=pattern):
                    redis_conn.delete(key)
            except Exception as e:
                logger.error(f"Pattern invalidation error for {alias}: {e}")
    
    def get_cache_statistics(self):
        """캐시 통계 반환"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hit_rate': f"{hit_rate:.2f}%",
            'total_requests': total_requests,
            **self.cache_stats
        }

# 전역 캐시 매니저
cache_manager = SmartCacheManager()
```

### 3. 뷰 레벨 캐싱

```python
from django.views.generic import ListView, DetailView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers, vary_on_cookie

# 페이지 전체 캐싱
@method_decorator(cache_page(60 * 5), name='dispatch')  # 5분 캐싱
@method_decorator(vary_on_headers('User-Agent', 'Accept-Language'), name='dispatch')
class ProductListView(ListView):
    """상품 목록 뷰 (전체 페이지 캐싱)"""
    
    model = Product
    template_name = 'products/list.html'
    paginate_by = 20
    
    def get_queryset(self):
        # 이미 캐싱되므로 복잡한 쿼리도 OK
        return Product.objects.select_related('category').prefetch_related('tags').filter(
            status='active'
        ).order_by('-created_at')

# 조건부 캐싱
class ConditionalCacheView(DetailView):
    """조건부 캐싱 뷰"""
    
    model = Product
    template_name = 'products/detail.html'
    
    @cache_manager.cached_function(timeout=600, strategy='warm_data', key_prefix='product_detail')
    def get_object(self):
        """객체 조회 (캐싱됨)"""
        return super().get_object()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 사용자별 다른 데이터는 별도 처리
        if self.request.user.is_authenticated:
            context['user_favorites'] = self.get_user_favorites()
            context['recommendations'] = self.get_recommendations()
        
        return context
    
    @cache_manager.cached_function(timeout=1800, strategy='cold_data')
    def get_recommendations(self):
        """추천 상품 (30분 캐싱)"""
        return Product.objects.filter(
            category=self.object.category
        ).exclude(
            id=self.object.id
        ).order_by('?')[:5]

# API 응답 캐싱
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.cache import cache

class CachedAPIView(APIView):
    """캐시된 API 뷰"""
    
    def get(self, request, *args, **kwargs):
        # 캐시 키 생성 (사용자, 매개변수 포함)
        cache_key = f"api_response:{request.user.id}:{request.GET.urlencode()}"
        
        # 캐시 확인
        cached_response = cache.get(cache_key)
        if cached_response:
            return Response(cached_response)
        
        # 데이터 생성
        data = self.generate_response_data()
        
        # 응답 캐싱 (5분)
        cache.set(cache_key, data, 300)
        
        return Response(data)
    
    def generate_response_data(self):
        """응답 데이터 생성"""
        return {
            'products': list(Product.objects.values('id', 'name', 'price')[:100]),
            'timestamp': time.time()
        }
```

### 4. 템플릿 프래그먼트 캐싱

{% raw %}
```html
<!-- templates/products/detail.html -->
{% load cache %}

<div class="product-detail">
    <!-- 기본 상품 정보 (자주 변경되지 않음) -->
    {% cache 3600 product_basic product.id %}
    <div class="product-info">
        <h1>{{ product.name }}</h1>
        <p class="price">${{ product.price }}</p>
        <div class="description">{{ product.description }}</div>
    </div>
    {% endcache %}
    
    <!-- 리뷰 섹션 (중간 정도 캐싱) -->
    {% cache 600 product_reviews product.id %}
    <div class="reviews">
        <h3>고객 리뷰</h3>
        {% for review in product.reviews.all %}
            <div class="review">
                <div class="rating">{{ review.rating }}★</div>
                <p>{{ review.comment }}</p>
            </div>
        {% endfor %}
    </div>
    {% endcache %}
    
    <!-- 사용자별 데이터 (캐싱하지 않음) -->
    <div class="user-actions">
        {% if user.is_authenticated %}
            <button class="add-to-cart">장바구니 담기</button>
            <button class="add-to-wishlist">찜하기</button>
        {% endif %}
    </div>
    
    <!-- 관련 상품 (긴 캐싱) -->
    {% cache 1800 related_products product.category.id %}
    <div class="related-products">
        <h3>관련 상품</h3>
        {% for related in related_products %}
            <div class="product-item">
                <a href="{{ related.get_absolute_url }}">{{ related.name }}</a>
            </div>
        {% endfor %}
    </div>
    {% endcache %}
</div>
```
{% endraw %}

### 5. 캐시 무효화 전략

```python
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)

class CacheInvalidationManager:
    """캐시 무효화 관리자"""
    
    @staticmethod
    def invalidate_product_cache(product_id):
        """상품 관련 캐시 무효화"""
        patterns = [
            f"*product_detail*{product_id}*",
            f"*product_list*",
            f"*api_response*",
            f"*product_basic*{product_id}*",
            f"*product_reviews*{product_id}*"
        ]
        
        for pattern in patterns:
            cache_manager.invalidate_pattern(pattern)
        
        logger.info(f"Invalidated cache for product {product_id}")
    
    @staticmethod
    def invalidate_category_cache(category_id):
        """카테고리 관련 캐시 무효화"""
        patterns = [
            f"*category*{category_id}*",
            f"*related_products*{category_id}*",
            f"*product_list*"
        ]
        
        for pattern in patterns:
            cache_manager.invalidate_pattern(pattern)
        
        logger.info(f"Invalidated cache for category {category_id}")

# 시그널 기반 캐시 무효화
@receiver(post_save, sender=Product)
def invalidate_product_cache_on_save(sender, instance, created, **kwargs):
    """상품 저장 시 캐시 무효화"""
    CacheInvalidationManager.invalidate_product_cache(instance.id)
    
    if instance.category:
        CacheInvalidationManager.invalidate_category_cache(instance.category.id)

@receiver(post_delete, sender=Product)
def invalidate_product_cache_on_delete(sender, instance, **kwargs):
    """상품 삭제 시 캐시 무효화"""
    CacheInvalidationManager.invalidate_product_cache(instance.id)
    
    if instance.category:
        CacheInvalidationManager.invalidate_category_cache(instance.category.id)

# 배치 캐시 갱신
class CacheWarmupManager:
    """캐시 예열 관리자"""
    
    @staticmethod
    def warmup_popular_products():
        """인기 상품 캐시 예열"""
        popular_products = Product.objects.filter(
            status='active'
        ).order_by('-view_count')[:100]
        
        for product in popular_products:
            # 미리 캐시에 로드
            cache_key = cache_manager.generate_cache_key('product_detail', product.id)
            cache_manager.set_cached_data(
                cache_key, 
                product, 
                strategy='hot_data'
            )
        
        logger.info(f"Warmed up cache for {len(popular_products)} popular products")
    
    @staticmethod
    def warmup_categories():
        """카테고리 캐시 예열"""
        categories = Category.objects.all()
        
        for category in categories:
            # 카테고리별 상품 미리 로드
            cache_key = cache_manager.generate_cache_key('category_products', category.id)
            products = list(category.products.filter(status='active')[:20])
            cache_manager.set_cached_data(
                cache_key,
                products,
                strategy='warm_data'
            )
        
        logger.info(f"Warmed up cache for {len(categories)} categories")

# Celery 태스크로 예열 실행
from celery import shared_task

@shared_task
def warmup_cache_periodic():
    """주기적 캐시 예열"""
    CacheWarmupManager.warmup_popular_products()
    CacheWarmupManager.warmup_categories()
    return "Cache warmup completed"
```

## ⚡ 비동기 처리와 큐 시스템

대용량 트래픽에서는 무거운 작업을 백그라운드로 처리하여 응답 시간을 최소화해야 합니다. Celery와 Redis를 활용한 비동기 처리 전략을 살펴보겠습니다.

### 1. Celery 최적화 설정

```python
# celery_app.py
import os
from celery import Celery
from django.conf import settings

# Django 설정 모듈 지정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings.production')

app = Celery('myproject')

# Django 설정에서 Celery 설정 로드
app.config_from_object('django.conf:settings', namespace='CELERY')

# 고성능 설정
app.conf.update(
    # 브로커 설정
    broker_url='redis://redis-cluster:6379/0',
    result_backend='redis://redis-cluster:6379/0',
    
    # 성능 최적화
    task_serializer='msgpack',
    result_serializer='msgpack',
    accept_content=['msgpack', 'json'],
    result_expires=3600,  # 1시간 후 결과 만료
    
    # 워커 최적화
    worker_prefetch_multiplier=4,  # 동시 처리 태스크 수
    worker_max_tasks_per_child=1000,  # 메모리 누수 방지
    worker_disable_rate_limits=True,  # 속도 제한 비활성화
    
    # 라우팅 설정
    task_routes={
        'myproject.tasks.send_email': {'queue': 'email'},
        'myproject.tasks.process_image': {'queue': 'media'},
        'myproject.tasks.generate_report': {'queue': 'reports'},
        'myproject.tasks.cleanup_data': {'queue': 'maintenance'},
    },
    
    # 큐별 우선순위 설정
    task_default_queue='default',
    task_queue_max_priority=10,
    task_default_priority=5,
    
    # 모니터링 설정
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# 자동으로 태스크 발견
app.autodiscover_tasks()

# 시작 시 설정 출력
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """주기적 태스크 설정"""
    
    # 캐시 예열 (매 10분)
    sender.add_periodic_task(
        600.0,
        warmup_cache_periodic.s(),
        name='cache_warmup'
    )
    
    # 성능 통계 수집 (매 5분)
    sender.add_periodic_task(
        300.0,
        collect_performance_stats.s(),
        name='performance_stats'
    )
    
    # 데이터 정리 (매일 새벽 2시)
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        cleanup_old_data.s(),
        name='daily_cleanup'
    )
```

### 2. 태스크 우선순위와 분산 처리

```python
# tasks.py
from celery import shared_task, group, chain, chord
from celery.exceptions import Retry
from django.core.mail import send_mail
from django.core.cache import cache
import logging
import time

logger = logging.getLogger(__name__)

# 우선순위별 태스크 정의
@shared_task(bind=True, priority=9, max_retries=3)  # 높은 우선순위
def send_critical_notification(self, user_id, message):
    """중요한 알림 발송 (즉시 처리)"""
    try:
        user = User.objects.get(id=user_id)
        
        # 이메일 발송
        send_mail(
            subject='중요 알림',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )
        
        # SMS 발송 (외부 API)
        send_sms_notification(user.phone, message)
        
        logger.info(f"Critical notification sent to user {user_id}")
        return f"Notification sent to {user.email}"
        
    except Exception as exc:
        logger.error(f"Failed to send critical notification: {exc}")
        
        # 재시도 전략
        if self.request.retries < self.max_retries:
            # 지수 백오프
            countdown = 2 ** self.request.retries
            raise self.retry(countdown=countdown, exc=exc)
        else:
            # 최종 실패 처리
            handle_notification_failure(user_id, message, str(exc))
            raise exc

@shared_task(priority=5)  # 일반 우선순위
def process_user_action(user_id, action_type, action_data):
    """사용자 액션 처리"""
    try:
        user = User.objects.get(id=user_id)
        
        if action_type == 'purchase':
            process_purchase(user, action_data)
        elif action_type == 'review':
            process_review(user, action_data)
        elif action_type == 'wishlist':
            process_wishlist(user, action_data)
        
        # 통계 업데이트
        update_user_statistics.delay(user_id)
        
        logger.info(f"Processed {action_type} for user {user_id}")
        
    except Exception as exc:
        logger.error(f"Failed to process user action: {exc}")
        raise exc

@shared_task(priority=2)  # 낮은 우선순위
def generate_analytics_report(report_type, date_range):
    """분석 보고서 생성 (배치 처리)"""
    try:
        start_time = time.time()
        
        if report_type == 'sales':
            data = generate_sales_report(date_range)
        elif report_type == 'user_behavior':
            data = generate_user_behavior_report(date_range)
        elif report_type == 'performance':
            data = generate_performance_report(date_range)
        
        # 보고서 저장
        report = Report.objects.create(
            type=report_type,
            data=data,
            generation_time=time.time() - start_time
        )
        
        # 관련자들에게 알림
        notify_report_completion.delay(report.id)
        
        logger.info(f"Generated {report_type} report in {report.generation_time:.2f}s")
        return report.id
        
    except Exception as exc:
        logger.error(f"Failed to generate report: {exc}")
        raise exc

# 병렬 처리 패턴
@shared_task
def process_bulk_data(data_chunks):
    """대량 데이터 병렬 처리"""
    
    # 데이터를 청크로 분할하여 병렬 처리
    job = group(
        process_data_chunk.s(chunk) for chunk in data_chunks
    )
    
    result = job.apply_async()
    
    # 모든 청크 처리 완료 대기
    processed_data = result.get()
    
    # 결과 병합
    merged_result = merge_processed_data(processed_data)
    
    return merged_result

@shared_task
def process_data_chunk(chunk):
    """데이터 청크 처리"""
    processed_items = []
    
    for item in chunk:
        try:
            processed_item = complex_data_processing(item)
            processed_items.append(processed_item)
        except Exception as e:
            logger.error(f"Failed to process item {item}: {e}")
    
    return processed_items

# 파이프라인 처리 패턴
@shared_task
def image_processing_pipeline(image_id):
    """이미지 처리 파이프라인"""
    
    # 체인 방식으로 순차 처리
    pipeline = chain(
        validate_image.s(image_id),
        resize_image.s(),
        apply_watermark.s(),
        generate_thumbnails.s(),
        upload_to_cdn.s(),
        update_database.s()
    )
    
    return pipeline.apply_async()

@shared_task
def validate_image(image_id):
    """이미지 검증"""
    image = Image.objects.get(id=image_id)
    
    if not is_valid_image(image.file):
        raise ValueError("Invalid image format")
    
    return image_id

@shared_task
def resize_image(image_id):
    """이미지 리사이즈"""
    image = Image.objects.get(id=image_id)
    
    resized_path = resize_image_file(image.file.path)
    image.resized_file = resized_path
    image.save()
    
    return image_id

# 조건부 처리 패턴
@shared_task
def smart_notification_dispatch(notification_data):
    """스마트 알림 발송"""
    
    user_id = notification_data['user_id']
    message = notification_data['message']
    urgency = notification_data.get('urgency', 'normal')
    
    # 사용자 선호도 확인
    user_preferences = get_user_notification_preferences(user_id)
    
    # 발송 방법 결정
    notification_methods = []
    
    if urgency == 'critical':
        notification_methods = ['email', 'sms', 'push']
    elif urgency == 'high':
        notification_methods = ['email', 'push']
    else:
        notification_methods = ['email']
    
    # 선호도에 따라 필터링
    filtered_methods = [
        method for method in notification_methods
        if user_preferences.get(method, True)
    ]
    
    # 병렬로 발송
    job = group(
        send_notification_by_method.s(user_id, message, method)
        for method in filtered_methods
    )
    
    return job.apply_async()

@shared_task
def send_notification_by_method(user_id, message, method):
    """특정 방법으로 알림 발송"""
    try:
        if method == 'email':
            return send_email_notification(user_id, message)
        elif method == 'sms':
            return send_sms_notification(user_id, message)
        elif method == 'push':
            return send_push_notification(user_id, message)
    except Exception as e:
        logger.error(f"Failed to send {method} notification: {e}")
        raise e
```

### 3. 큐 모니터링과 관리

```python
# monitoring.py
from celery import current_app
from django.core.management.base import BaseCommand
import redis
import json
import time

class CeleryMonitor:
    """Celery 모니터링 클래스"""
    
    def __init__(self):
        self.app = current_app
        self.redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)
    
    def get_queue_lengths(self):
        """큐별 대기 중인 태스크 수"""
        queues = ['default', 'email', 'media', 'reports', 'maintenance']
        queue_lengths = {}
        
        for queue in queues:
            length = self.redis_client.llen(f"celery_{queue}")
            queue_lengths[queue] = length
        
        return queue_lengths
    
    def get_active_workers(self):
        """활성 워커 정보"""
        inspect = self.app.control.inspect()
        
        try:
            active = inspect.active() or {}
            stats = inspect.stats() or {}
            
            worker_info = {}
            for worker_name, worker_stats in stats.items():
                worker_info[worker_name] = {
                    'active_tasks': len(active.get(worker_name, [])),
                    'total_tasks': worker_stats.get('total', {}),
                    'pool_processes': worker_stats.get('pool', {}).get('processes'),
                    'rusage': worker_stats.get('rusage', {})
                }
            
            return worker_info
            
        except Exception as e:
            logger.error(f"Failed to get worker info: {e}")
            return {}
    
    def get_failed_tasks(self, limit=10):
        """실패한 태스크 목록"""
        failed_tasks = []
        
        # Redis에서 실패한 태스크 조회
        failed_keys = self.redis_client.keys("celery-task-meta-*")
        
        for key in failed_keys[:limit]:
            try:
                task_data = self.redis_client.get(key)
                if task_data:
                    task_info = json.loads(task_data)
                    if task_info.get('status') == 'FAILURE':
                        failed_tasks.append({
                            'task_id': key.decode().split('-')[-1],
                            'result': task_info.get('result'),
                            'traceback': task_info.get('traceback')
                        })
            except Exception as e:
                continue
        
        return failed_tasks
    
    def get_performance_metrics(self):
        """성능 메트릭"""
        queue_lengths = self.get_queue_lengths()
        worker_info = self.get_active_workers()
        failed_tasks = self.get_failed_tasks()
        
        # 총 대기 태스크 수
        total_pending = sum(queue_lengths.values())
        
        # 총 활성 워커 수
        total_workers = len(worker_info)
        
        # 총 활성 태스크 수
        total_active_tasks = sum(
            info['active_tasks'] for info in worker_info.values()
        )
        
        return {
            'queue_lengths': queue_lengths,
            'total_pending_tasks': total_pending,
            'total_workers': total_workers,
            'total_active_tasks': total_active_tasks,
            'failed_tasks_count': len(failed_tasks),
            'worker_details': worker_info,
            'timestamp': time.time()
        }

# 자동 스케일링
class CeleryAutoScaler:
    """Celery 워커 자동 스케일링"""
    
    def __init__(self):
        self.monitor = CeleryMonitor()
        self.scaling_rules = {
            'scale_up_threshold': 100,    # 대기 태스크 100개 이상 시 스케일 업
            'scale_down_threshold': 10,   # 대기 태스크 10개 이하 시 스케일 다운
            'max_workers': 20,            # 최대 워커 수
            'min_workers': 3,             # 최소 워커 수
            'scale_up_count': 2,          # 한 번에 추가할 워커 수
            'scale_down_count': 1         # 한 번에 제거할 워커 수
        }
    
    def should_scale_up(self, metrics):
        """스케일 업 필요 여부 판단"""
        return (
            metrics['total_pending_tasks'] > self.scaling_rules['scale_up_threshold'] and
            metrics['total_workers'] < self.scaling_rules['max_workers']
        )
    
    def should_scale_down(self, metrics):
        """스케일 다운 필요 여부 판단"""
        return (
            metrics['total_pending_tasks'] < self.scaling_rules['scale_down_threshold'] and
            metrics['total_workers'] > self.scaling_rules['min_workers']
        )
    
    def execute_scaling(self):
        """스케일링 실행"""
        metrics = self.monitor.get_performance_metrics()
        
        if self.should_scale_up(metrics):
            self.scale_up()
        elif self.should_scale_down(metrics):
            self.scale_down()
    
    def scale_up(self):
        """워커 수 증가"""
        # Kubernetes, Docker Swarm 등과 연동
        logger.info("Scaling up Celery workers")
        # kubectl scale deployment celery-worker --replicas=+2
    
    def scale_down(self):
        """워커 수 감소"""
        logger.info("Scaling down Celery workers")
        # kubectl scale deployment celery-worker --replicas=-1

# 관리 명령어
class Command(BaseCommand):
    """Celery 모니터링 명령어"""
    
    def add_arguments(self, parser):
        parser.add_argument('--action', choices=['status', 'autoscale'], default='status')
        parser.add_argument('--interval', type=int, default=30)
    
    def handle(self, *args, **options):
        monitor = CeleryMonitor()
        autoscaler = CeleryAutoScaler()
        
        if options['action'] == 'status':
            self.show_status(monitor)
        elif options['action'] == 'autoscale':
            self.run_autoscaler(autoscaler, options['interval'])
    
    def show_status(self, monitor):
        """상태 표시"""
        metrics = monitor.get_performance_metrics()
        
        self.stdout.write("=== Celery Status ===")
        self.stdout.write(f"Total pending tasks: {metrics['total_pending_tasks']}")
        self.stdout.write(f"Active workers: {metrics['total_workers']}")
        self.stdout.write(f"Active tasks: {metrics['total_active_tasks']}")
        self.stdout.write(f"Failed tasks: {metrics['failed_tasks_count']}")
        
        self.stdout.write("\n=== Queue Lengths ===")
        for queue, length in metrics['queue_lengths'].items():
            self.stdout.write(f"{queue}: {length}")
    
    def run_autoscaler(self, autoscaler, interval):
        """자동 스케일러 실행"""
        self.stdout.write(f"Starting autoscaler with {interval}s interval")
        
        while True:
            try:
                autoscaler.execute_scaling()
                time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write("Autoscaler stopped")
                break
            except Exception as e:
                self.stderr.write(f"Autoscaler error: {e}")
                time.sleep(interval)
```

---

## 5. 모니터링 및 성능 측정

대용량 트래픽을 처리하는 Django 애플리케이션에서는 실시간 모니터링과 성능 측정이 필수입니다. 문제가 발생하기 전에 미리 감지하고 대응할 수 있는 모니터링 시스템을 구축해야 합니다.

### 1. Django APM(Application Performance Monitoring)

#### Django Debug Toolbar와 Silk를 활용한 프로파일링

```python
# settings/development.py
INSTALLED_APPS = [
    # ... 다른 앱들
    'debug_toolbar',
    'silk',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'silk.middleware.SilkyMiddleware',
    # ... 다른 미들웨어들
]

# Debug Toolbar 설정
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

# Silk 설정
SILKY_PYTHON_PROFILER = True
SILKY_PYTHON_PROFILER_BINARY = True
SILKY_AUTHENTICATION = True
SILKY_AUTHORISATION = True
SILKY_META = True
```

#### 커스텀 성능 미들웨어

```python
# middleware/performance.py
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.db import connection
from django.core.cache import cache

logger = logging.getLogger('performance')

class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """요청별 성능 모니터링 미들웨어"""
    
    def process_request(self, request):
        request._start_time = time.time()
        request._db_queries_start = len(connection.queries)
        
    def process_response(self, request, response):
        # 응답 시간 계산
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            
            # DB 쿼리 수 계산
            db_queries_count = len(connection.queries) - getattr(request, '_db_queries_start', 0)
            
            # 응답 크기 계산
            content_length = len(response.content) if hasattr(response, 'content') else 0
            
            # 로깅
            log_data = {
                'method': request.method,
                'path': request.path,
                'duration': duration * 1000,  # ms 단위
                'status_code': response.status_code,
                'db_queries': db_queries_count,
                'content_length': content_length,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip': self.get_client_ip(request),
            }
            
            # 성능 임계값 검사
            if duration > 1.0:  # 1초 이상
                logger.warning(f"Slow request: {log_data}")
            elif db_queries_count > 10:  # 10개 이상 쿼리
                logger.warning(f"N+1 query detected: {log_data}")
            else:
                logger.info(f"Request processed: {log_data}")
            
            # 메트릭 수집
            self.collect_metrics(log_data)
            
        return response
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def collect_metrics(self, log_data):
        """메트릭 수집 및 저장"""
        # Redis를 사용한 실시간 메트릭 수집
        cache_key = f"metrics:{int(time.time() // 60)}"  # 분 단위
        
        try:
            current_metrics = cache.get(cache_key, {})
            current_metrics.setdefault('request_count', 0)
            current_metrics.setdefault('total_duration', 0)
            current_metrics.setdefault('slow_requests', 0)
            current_metrics.setdefault('status_codes', {})
            
            current_metrics['request_count'] += 1
            current_metrics['total_duration'] += log_data['duration']
            
            if log_data['duration'] > 1000:  # 1초 이상
                current_metrics['slow_requests'] += 1
            
            status_code = str(log_data['status_code'])
            current_metrics['status_codes'].setdefault(status_code, 0)
            current_metrics['status_codes'][status_code] += 1
            
            cache.set(cache_key, current_metrics, 300)  # 5분 캐시
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
```

### 2. 데이터베이스 모니터링

#### PostgreSQL 성능 모니터링

```python
# monitoring/database.py
import psycopg2
from django.db import connection
from django.conf import settings
import logging

logger = logging.getLogger('db_monitor')

class DatabaseMonitor:
    """데이터베이스 성능 모니터링"""
    
    def __init__(self):
        self.connection = connection
    
    def get_slow_queries(self, threshold_ms=1000):
        """느린 쿼리 조회"""
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    query,
                    calls,
                    total_time,
                    mean_time,
                    rows,
                    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                FROM pg_stat_statements 
                WHERE mean_time > %s
                ORDER BY total_time DESC
                LIMIT 20;
            """, [threshold_ms])
            
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            for query in results:
                logger.warning(f"Slow query detected: {query}")
            
            return results
    
    def get_connection_stats(self):
        """연결 통계 조회"""
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    datname,
                    numbackends,
                    xact_commit,
                    xact_rollback,
                    blks_read,
                    blks_hit,
                    temp_files,
                    temp_bytes,
                    deadlocks
                FROM pg_stat_database 
                WHERE datname = current_database();
            """)
            
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, cursor.fetchone()))
    
    def get_lock_info(self):
        """잠금 정보 조회"""
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    bl.pid AS blocked_pid,
                    bl.usename AS blocked_user,
                    bl.query AS blocked_query,
                    kl.pid AS blocking_pid,
                    kl.usename AS blocking_user,
                    kl.query AS blocking_query
                FROM pg_catalog.pg_locks bl
                JOIN pg_catalog.pg_stat_activity bl_act ON bl.pid = bl_act.pid
                JOIN pg_catalog.pg_locks kl ON bl.transactionid = kl.transactionid
                JOIN pg_catalog.pg_stat_activity kl_act ON kl.pid = kl_act.pid
                WHERE bl.granted = false AND kl.granted = true
                AND bl.pid != kl.pid;
            """)
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def analyze_query_performance(self):
        """쿼리 성능 분석"""
        stats = {
            'slow_queries': self.get_slow_queries(),
            'connection_stats': self.get_connection_stats(),
            'locks': self.get_lock_info(),
        }
        
        # 성능 임계값 검사
        conn_stats = stats['connection_stats']
        if conn_stats['numbackends'] > 100:
            logger.warning(f"High connection count: {conn_stats['numbackends']}")
        
        if conn_stats['deadlocks'] > 0:
            logger.error(f"Deadlocks detected: {conn_stats['deadlocks']}")
        
        return stats
```

### 3. Redis 모니터링

```python
# monitoring/redis_monitor.py
import redis
import json
import time
from django.core.cache import cache
from django.conf import settings

class RedisMonitor:
    """Redis 성능 모니터링"""
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(settings.CACHES['default']['LOCATION'])
    
    def get_info(self):
        """Redis 정보 조회"""
        info = self.redis_client.info()
        
        memory_usage = {
            'used_memory': info['used_memory'],
            'used_memory_human': info['used_memory_human'],
            'used_memory_peak': info['used_memory_peak'],
            'used_memory_peak_human': info['used_memory_peak_human'],
            'memory_fragmentation_ratio': info.get('mem_fragmentation_ratio', 0),
        }
        
        performance = {
            'connected_clients': info['connected_clients'],
            'total_commands_processed': info['total_commands_processed'],
            'instantaneous_ops_per_sec': info['instantaneous_ops_per_sec'],
            'keyspace_hits': info['keyspace_hits'],
            'keyspace_misses': info['keyspace_misses'],
            'expired_keys': info['expired_keys'],
            'evicted_keys': info['evicted_keys'],
        }
        
        # 히트율 계산
        if (info['keyspace_hits'] + info['keyspace_misses']) > 0:
            hit_rate = info['keyspace_hits'] / (info['keyspace_hits'] + info['keyspace_misses'])
            performance['hit_rate'] = hit_rate
        
        return {
            'memory': memory_usage,
            'performance': performance,
            'uptime': info['uptime_in_seconds'],
        }
    
    def get_slow_log(self, count=10):
        """느린 명령 로그 조회"""
        slow_commands = self.redis_client.slowlog_get(count)
        
        formatted_commands = []
        for cmd in slow_commands:
            formatted_commands.append({
                'id': cmd['id'],
                'start_time': cmd['start_time'],
                'duration': cmd['duration'],  # 마이크로초
                'command': ' '.join([arg.decode() if isinstance(arg, bytes) else str(arg) 
                                   for arg in cmd['command']]),
            })
        
        return formatted_commands
    
    def monitor_performance(self):
        """성능 모니터링 및 알림"""
        info = self.get_info()
        
        # 메모리 사용량 체크
        memory_usage_percent = (info['memory']['used_memory'] / 
                              (1024 * 1024 * 1024))  # GB 단위
        
        if memory_usage_percent > 0.8:  # 80% 이상
            logging.warning(f"High Redis memory usage: {memory_usage_percent:.2f}GB")
        
        # 히트율 체크
        hit_rate = info['performance'].get('hit_rate', 0)
        if hit_rate < 0.8:  # 80% 미만
            logging.warning(f"Low Redis hit rate: {hit_rate:.2%}")
        
        # 연결 수 체크
        connected_clients = info['performance']['connected_clients']
        if connected_clients > 1000:
            logging.warning(f"High Redis connection count: {connected_clients}")
        
        return info
```

### 4. 시스템 메트릭 수집

```python
# monitoring/system_metrics.py
import psutil
import platform
import json
from datetime import datetime
import logging

logger = logging.getLogger('system_metrics')

class SystemMetricsCollector:
    """시스템 메트릭 수집기"""
    
    def collect_cpu_metrics(self):
        """CPU 메트릭 수집"""
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        cpu_count = psutil.cpu_count()
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
        
        return {
            'cpu_percent_total': psutil.cpu_percent(),
            'cpu_percent_per_core': cpu_percent,
            'cpu_count': cpu_count,
            'load_average': {
                '1min': load_avg[0],
                '5min': load_avg[1],
                '15min': load_avg[2],
            }
        }
    
    def collect_memory_metrics(self):
        """메모리 메트릭 수집"""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'percent': memory.percent,
                'free': memory.free,
                'cached': getattr(memory, 'cached', 0),
                'buffers': getattr(memory, 'buffers', 0),
            },
            'swap': {
                'total': swap.total,
                'used': swap.used,
                'free': swap.free,
                'percent': swap.percent,
            }
        }
    
    def collect_disk_metrics(self):
        """디스크 메트릭 수집"""
        disk_usage = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        
        partitions = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partitions.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': (usage.used / usage.total) * 100,
                })
            except PermissionError:
                continue
        
        return {
            'root_disk': {
                'total': disk_usage.total,
                'used': disk_usage.used,
                'free': disk_usage.free,
                'percent': (disk_usage.used / disk_usage.total) * 100,
            },
            'partitions': partitions,
            'io_counters': {
                'read_bytes': disk_io.read_bytes if disk_io else 0,
                'write_bytes': disk_io.write_bytes if disk_io else 0,
                'read_count': disk_io.read_count if disk_io else 0,
                'write_count': disk_io.write_count if disk_io else 0,
            } if disk_io else {}
        }
    
    def collect_network_metrics(self):
        """네트워크 메트릭 수집"""
        net_io = psutil.net_io_counters()
        connections = len(psutil.net_connections())
        
        return {
            'io_counters': {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'errin': net_io.errin,
                'errout': net_io.errout,
                'dropin': net_io.dropin,
                'dropout': net_io.dropout,
            },
            'connections_count': connections,
        }
    
    def collect_process_metrics(self):
        """프로세스 메트릭 수집"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                proc_info = proc.info
                if proc_info['name'] in ['python', 'gunicorn', 'uwsgi', 'celery']:
                    processes.append({
                        'pid': proc_info['pid'],
                        'name': proc_info['name'],
                        'cpu_percent': proc_info['cpu_percent'],
                        'memory_percent': proc_info['memory_percent'],
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return processes
    
    def collect_all_metrics(self):
        """모든 메트릭 수집"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'hostname': platform.node(),
            'cpu': self.collect_cpu_metrics(),
            'memory': self.collect_memory_metrics(),
            'disk': self.collect_disk_metrics(),
            'network': self.collect_network_metrics(),
            'processes': self.collect_process_metrics(),
        }
        
        # 임계값 검사 및 알림
        self.check_thresholds(metrics)
        
        return metrics
    
    def check_thresholds(self, metrics):
        """임계값 검사"""
        # CPU 사용률 검사
        if metrics['cpu']['cpu_percent_total'] > 80:
            logger.warning(f"High CPU usage: {metrics['cpu']['cpu_percent_total']:.1f}%")
        
        # 메모리 사용률 검사
        if metrics['memory']['memory']['percent'] > 80:
            logger.warning(f"High memory usage: {metrics['memory']['memory']['percent']:.1f}%")
        
        # 디스크 사용률 검사
        if metrics['disk']['root_disk']['percent'] > 80:
            logger.warning(f"High disk usage: {metrics['disk']['root_disk']['percent']:.1f}%")
        
        # 로드 애버리지 검사
        cpu_count = metrics['cpu']['cpu_count']
        load_1min = metrics['cpu']['load_average']['1min']
        if load_1min > cpu_count * 0.8:
            logger.warning(f"High load average: {load_1min:.2f} (CPU count: {cpu_count})")
```

### 5. 알림 시스템

```python
# monitoring/alerts.py
import smtplib
import json
import requests
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from django.conf import settings
import logging

logger = logging.getLogger('alerts')

class AlertManager:
    """알림 관리자"""
    
    def __init__(self):
        self.email_config = getattr(settings, 'ALERT_EMAIL_CONFIG', {})
        self.slack_webhook = getattr(settings, 'SLACK_WEBHOOK_URL', None)
        self.discord_webhook = getattr(settings, 'DISCORD_WEBHOOK_URL', None)
    
    def send_email_alert(self, subject, message, recipients=None):
        """이메일 알림 발송"""
        if not self.email_config or not recipients:
            return False
        
        try:
            msg = MimeMultipart()
            msg['From'] = self.email_config['from_email']
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"[Django Alert] {subject}"
            
            msg.attach(MimeText(message, 'plain'))
            
            server = smtplib.SMTP(self.email_config['smtp_host'], 
                                 self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['username'], 
                        self.email_config['password'])
            
            text = msg.as_string()
            server.sendmail(self.email_config['from_email'], recipients, text)
            server.quit()
            
            logger.info(f"Email alert sent: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def send_slack_alert(self, message, channel=None):
        """Slack 알림 발송"""
        if not self.slack_webhook:
            return False
        
        try:
            payload = {
                'text': f"🚨 Django Alert: {message}",
                'username': 'Django Monitor',
                'icon_emoji': ':warning:',
            }
            
            if channel:
                payload['channel'] = channel
            
            response = requests.post(self.slack_webhook, 
                                   data=json.dumps(payload),
                                   headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                logger.info(f"Slack alert sent: {message}")
                return True
            else:
                logger.error(f"Failed to send Slack alert: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    def send_discord_alert(self, message):
        """Discord 알림 발송"""
        if not self.discord_webhook:
            return False
        
        try:
            payload = {
                'content': f"🚨 **Django Alert**\n{message}",
                'username': 'Django Monitor',
            }
            
            response = requests.post(self.discord_webhook, 
                                   data=json.dumps(payload),
                                   headers={'Content-Type': 'application/json'})
            
            if response.status_code == 204:
                logger.info(f"Discord alert sent: {message}")
                return True
            else:
                logger.error(f"Failed to send Discord alert: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
            return False
    
    def send_alert(self, level, subject, message, channels=None):
        """통합 알림 발송"""
        if not channels:
            channels = ['email', 'slack']
        
        success_count = 0
        
        if 'email' in channels and level in ['critical', 'error']:
            recipients = getattr(settings, 'ALERT_EMAIL_RECIPIENTS', [])
            if self.send_email_alert(subject, message, recipients):
                success_count += 1
        
        if 'slack' in channels:
            if self.send_slack_alert(f"{subject}\n{message}"):
                success_count += 1
        
        if 'discord' in channels:
            if self.send_discord_alert(f"**{subject}**\n{message}"):
                success_count += 1
        
        return success_count > 0

# monitoring/tasks.py (Celery 태스크)
from celery import shared_task
from .database import DatabaseMonitor
from .redis_monitor import RedisMonitor
from .system_metrics import SystemMetricsCollector
from .alerts import AlertManager

@shared_task
def collect_system_metrics():
    """시스템 메트릭 수집 태스크"""
    collector = SystemMetricsCollector()
    metrics = collector.collect_all_metrics()
    
    # 메트릭을 Redis에 저장
    from django.core.cache import cache
    cache_key = f"system_metrics:{int(time.time() // 60)}"
    cache.set(cache_key, metrics, 300)  # 5분 캐시
    
    return metrics

@shared_task
def monitor_database_performance():
    """데이터베이스 성능 모니터링 태스크"""
    monitor = DatabaseMonitor()
    stats = monitor.analyze_query_performance()
    
    alert_manager = AlertManager()
    
    # 느린 쿼리 알림
    if stats['slow_queries']:
        message = f"Detected {len(stats['slow_queries'])} slow queries"
        alert_manager.send_alert('warning', 'Slow Queries Detected', message)
    
    # 데드락 알림
    if stats['locks']:
        message = f"Detected {len(stats['locks'])} database locks"
        alert_manager.send_alert('critical', 'Database Locks Detected', message)
    
    return stats

@shared_task
def monitor_redis_performance():
    """Redis 성능 모니터링 태스크"""
    monitor = RedisMonitor()
    info = monitor.monitor_performance()
    
    return info
```

### 6. 모니터링 대시보드

```python
# views/monitoring.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
import json

@staff_member_required
def monitoring_dashboard(request):
    """모니터링 대시보드 API"""
    if request.method == 'GET':
        return render(request, 'monitoring/dashboard.html')
    
    # AJAX 요청 처리
    metric_type = request.GET.get('type', 'all')
    
    if metric_type == 'system':
        return JsonResponse(get_system_metrics())
    elif metric_type == 'database':
        return JsonResponse(get_database_metrics())
    elif metric_type == 'redis':
        return JsonResponse(get_redis_metrics())
    elif metric_type == 'application':
        return JsonResponse(get_application_metrics())
    else:
        return JsonResponse({
            'system': get_system_metrics(),
            'database': get_database_metrics(),
            'redis': get_redis_metrics(),
            'application': get_application_metrics(),
        })

def get_system_metrics():
    """시스템 메트릭 조회"""
    collector = SystemMetricsCollector()
    return collector.collect_all_metrics()

def get_database_metrics():
    """데이터베이스 메트릭 조회"""
    monitor = DatabaseMonitor()
    return monitor.analyze_query_performance()

def get_redis_metrics():
    """Redis 메트릭 조회"""
    monitor = RedisMonitor()
    return monitor.get_info()

def get_application_metrics():
    """애플리케이션 메트릭 조회"""
    # 최근 10분간의 메트릭 조회
    current_time = int(time.time() // 60)
    metrics = []
    
    for i in range(10):
        cache_key = f"metrics:{current_time - i}"
        metric = cache.get(cache_key)
        if metric:
            metric['timestamp'] = current_time - i
            metrics.append(metric)
    
    return {
        'recent_metrics': metrics,
        'total_requests': sum(m.get('request_count', 0) for m in metrics),
        'avg_response_time': sum(m.get('total_duration', 0) for m in metrics) / max(sum(m.get('request_count', 0) for m in metrics), 1),
        'slow_requests': sum(m.get('slow_requests', 0) for m in metrics),
    }
```

### 7. 설정 예시

```python
# settings/monitoring.py

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"level": "%(levelname)s", "time": "%(asctime)s", "module": "%(module)s", "message": "%(message)s"}',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/django.log',
            'maxBytes': 50 * 1024 * 1024,  # 50MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'performance': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/performance.log',
            'maxBytes': 100 * 1024 * 1024,  # 100MB
            'backupCount': 10,
            'formatter': 'json',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'performance': {
            'handlers': ['performance'],
            'level': 'INFO',
            'propagate': False,
        },
        'db_monitor': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# 알림 설정
ALERT_EMAIL_CONFIG = {
    'smtp_host': 'smtp.gmail.com',
    'smtp_port': 587,
    'username': 'your-email@gmail.com',
    'password': 'your-app-password',
    'from_email': 'alerts@yourcompany.com',
}

ALERT_EMAIL_RECIPIENTS = [
    'admin@yourcompany.com',
    'devops@yourcompany.com',
]

SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/YOUR/DISCORD/WEBHOOK'

# Celery 모니터링 태스크 스케줄
CELERY_BEAT_SCHEDULE = {
    'collect-system-metrics': {
        'task': 'monitoring.tasks.collect_system_metrics',
        'schedule': 60.0,  # 1분마다
    },
    'monitor-database': {
        'task': 'monitoring.tasks.monitor_database_performance',
        'schedule': 300.0,  # 5분마다
    },
    'monitor-redis': {
        'task': 'monitoring.tasks.monitor_redis_performance',
        'schedule': 180.0,  # 3분마다
    },
}
```

---

## 6. 실전 사례 및 모범 사례

이 섹션에서는 실제 대용량 트래픽을 처리하는 Django 서비스의 사례와 검증된 모범 사례들을 소개합니다.

### 1. 실제 사례: 대형 이커머스 플랫폼

#### 사례 개요
- **일일 활성 사용자**: 100만명
- **일일 주문 건수**: 5만건
- **피크 시간 동시 접속자**: 10만명
- **데이터베이스 크기**: 5TB+

#### 아키텍처 구성

```python
# 실제 적용된 설정 예시
# settings/production.py

# 1. ASGI 서버 구성
ASGI_APPLICATION = 'myapp.asgi.application'

# Daphne 설정 (docker-compose.yml에서)
"""
services:
  web:
    image: myapp:latest
    command: daphne -b 0.0.0.0 -p 8000 --access-log - myapp.asgi:application
    deploy:
      replicas: 12
      resources:
        limits:
          cpus: '2'
          memory: 4G
    environment:
      - DJANGO_SETTINGS_MODULE=myapp.settings.production
"""

# 2. 데이터베이스 설정
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ecommerce_main',
        'USER': 'django_user',
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': 'postgresql-master.internal',
        'PORT': '5432',
        'OPTIONS': {
            'MAX_CONNS': 20,
            'CONN_MAX_AGE': 300,
        },
        'TEST': {
            'NAME': 'test_ecommerce',
        }
    },
    'replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ecommerce_main',
        'USER': 'django_readonly',
        'PASSWORD': os.environ['DB_READONLY_PASSWORD'],
        'HOST': 'postgresql-replica.internal',
        'PORT': '5432',
        'OPTIONS': {
            'MAX_CONNS': 15,
            'CONN_MAX_AGE': 600,
        }
    },
    'analytics': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ecommerce_analytics',
        'USER': 'analytics_user',
        'PASSWORD': os.environ['ANALYTICS_DB_PASSWORD'],
        'HOST': 'postgresql-analytics.internal',
        'PORT': '5432',
        'OPTIONS': {
            'MAX_CONNS': 10,
        }
    }
}

# 3. 캐시 클러스터 설정
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': [
            'redis://redis-cluster-1.internal:6379/1',
            'redis://redis-cluster-2.internal:6379/1',
            'redis://redis-cluster-3.internal:6379/1',
        ],
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.ShardClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            }
        }
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis-sessions.internal:6379/2',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
            }
        }
    }
}

# 4. Celery 설정
CELERY_BROKER_URL = 'redis://redis-celery.internal:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis-celery.internal:6379/0'

CELERY_TASK_ROUTES = {
    'orders.tasks.process_payment': {'queue': 'high_priority'},
    'orders.tasks.send_confirmation_email': {'queue': 'email'},
    'analytics.tasks.update_metrics': {'queue': 'analytics'},
    'inventory.tasks.update_stock': {'queue': 'inventory'},
}

CELERY_WORKER_CONCURRENCY = 8
CELERY_WORKER_PREFETCH_MULTIPLIER = 2
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
```

#### 핵심 최적화 전략

```python
# 1. 스마트 캐싱 전략
# models/product.py
class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @cached_property
    def cache_key(self):
        return f"product:{self.id}:{self.updated_at.timestamp()}"
    
    def get_cached_data(self):
        """캐시된 상품 데이터 조회"""
        cached_data = cache.get(self.cache_key)
        if cached_data is None:
            cached_data = {
                'id': self.id,
                'name': self.name,
                'price': str(self.price),
                'stock': self.stock,
                'category_name': self.category.name,
                'image_urls': list(self.images.values_list('url', flat=True)),
                'average_rating': self.reviews.aggregate(
                    avg_rating=models.Avg('rating')
                )['avg_rating'] or 0,
                'review_count': self.reviews.count(),
            }
            # 상품 데이터는 6시간 캐시
            cache.set(self.cache_key, cached_data, 21600)
        return cached_data
    
    def invalidate_cache(self):
        """캐시 무효화"""
        cache.delete(self.cache_key)
        # 관련 카테고리 캐시도 무효화
        cache.delete(f"category_products:{self.category.id}")

# 2. 주문 처리 최적화
# services/order_service.py
class OrderService:
    """주문 처리 서비스"""
    
    @transaction.atomic
    def create_order(self, user, cart_items):
        """주문 생성"""
        # 1. 재고 확인 및 예약
        self._reserve_inventory(cart_items)
        
        # 2. 주문 생성
        order = Order.objects.create(
            user=user,
            status='PENDING',
            total_amount=self._calculate_total(cart_items)
        )
        
        # 3. 주문 항목 생성
        order_items = []
        for item in cart_items:
            order_items.append(OrderItem(
                order=order,
                product_id=item['product_id'],
                quantity=item['quantity'],
                price=item['price']
            ))
        OrderItem.objects.bulk_create(order_items)
        
        # 4. 비동기 후처리 작업
        from orders.tasks import process_order_async
        process_order_async.delay(order.id)
        
        return order
    
    def _reserve_inventory(self, cart_items):
        """재고 예약 (낙관적 잠금 사용)"""
        for item in cart_items:
            product = Product.objects.select_for_update().get(
                id=item['product_id']
            )
            
            if product.stock < item['quantity']:
                raise ValueError(f"Insufficient stock for {product.name}")
            
            # 재고 차감
            product.stock -= item['quantity']
            product.save(update_fields=['stock'])
            
            # 캐시 무효화
            product.invalidate_cache()

# 3. 검색 최적화
# services/search_service.py
class SearchService:
    """검색 서비스"""
    
    def search_products(self, query, filters=None, page=1, per_page=20):
        """상품 검색"""
        cache_key = self._get_search_cache_key(query, filters, page, per_page)
        
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Elasticsearch 또는 PostgreSQL 풀텍스트 검색
        if hasattr(settings, 'ELASTICSEARCH_DSL'):
            results = self._elasticsearch_search(query, filters, page, per_page)
        else:
            results = self._postgresql_search(query, filters, page, per_page)
        
        # 15분 캐시
        cache.set(cache_key, results, 900)
        return results
    
    def _postgresql_search(self, query, filters, page, per_page):
        """PostgreSQL 풀텍스트 검색"""
        from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
        
        search_vector = SearchVector('name', weight='A') + SearchVector('description', weight='B')
        search_query = SearchQuery(query)
        
        queryset = Product.objects.annotate(
            search=search_vector,
            rank=SearchRank(search_vector, search_query)
        ).filter(search=search_query)
        
        # 필터 적용
        if filters:
            if filters.get('category_id'):
                queryset = queryset.filter(category_id=filters['category_id'])
            if filters.get('price_min'):
                queryset = queryset.filter(price__gte=filters['price_min'])
            if filters.get('price_max'):
                queryset = queryset.filter(price__lte=filters['price_max'])
        
        # 정렬 및 페이징
        queryset = queryset.order_by('-rank', '-created_at')
        
        offset = (page - 1) * per_page
        products = list(queryset[offset:offset + per_page])
        total_count = queryset.count()
        
        return {
            'products': [product.get_cached_data() for product in products],
            'total_count': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_count + per_page - 1) // per_page,
        }
```

### 2. 성능 개선 사례

#### Before/After 비교

```python
# Before: 비효율적인 코드
def get_user_orders_bad(user_id):
    """비효율적인 주문 조회"""
    user = User.objects.get(id=user_id)  # N+1 문제
    orders = []
    
    for order in user.orders.all():  # 추가 쿼리
        order_data = {
            'id': order.id,
            'created_at': order.created_at,
            'total_amount': order.total_amount,
            'items': []
        }
        
        for item in order.items.all():  # N+1 문제
            product = item.product  # 추가 쿼리
            order_data['items'].append({
                'product_name': product.name,  # 추가 쿼리
                'quantity': item.quantity,
                'price': item.price,
            })
        
        orders.append(order_data)
    
    return orders

# After: 최적화된 코드
def get_user_orders_optimized(user_id):
    """최적화된 주문 조회"""
    # 캐시 확인
    cache_key = f"user_orders:{user_id}"
    cached_orders = cache.get(cache_key)
    if cached_orders:
        return cached_orders
    
    # 최적화된 쿼리 (한 번에 모든 데이터 조회)
    orders = Order.objects.filter(user_id=user_id).select_related('user').prefetch_related(
        'items__product'
    ).order_by('-created_at')
    
    # 데이터 변환
    orders_data = []
    for order in orders:
        order_data = {
            'id': order.id,
            'created_at': order.created_at.isoformat(),
            'total_amount': str(order.total_amount),
            'items': [
                {
                    'product_name': item.product.name,
                    'quantity': item.quantity,
                    'price': str(item.price),
                }
                for item in order.items.all()
            ]
        }
        orders_data.append(order_data)
    
    # 캐시 저장 (1시간)
    cache.set(cache_key, orders_data, 3600)
    return orders_data

# 성능 비교 결과:
# Before: 평균 2.5초, 150+ 쿼리
# After: 평균 0.1초, 2 쿼리
```

### 3. 모범 사례 체크리스트

#### 개발 단계

```python
# 코드 리뷰 체크리스트
PERFORMANCE_CHECKLIST = {
    'database': [
        'select_related() 또는 prefetch_related() 사용 확인',
        'bulk_create(), bulk_update() 활용',
        'only(), defer() 필요한 필드만 조회',
        'exists() vs count() 적절한 사용',
        'iterator() 대용량 데이터 처리',
        'F() 표현식으로 데이터베이스 레벨 연산',
        '인덱스 추가 검토',
        'explain() 쿼리 실행 계획 확인'
    ],
    'caching': [
        'view 레벨 캐싱 적용',
        'template fragment 캐싱',
        'low-level 캐시 API 활용',
        '캐시 TTL 설정 검토',
        '캐시 무효화 전략 구현',
        'cache_page 데코레이터 활용',
        'Vary 헤더 설정'
    ],
    'async': [
        '무거운 작업 Celery 태스크로 분리',
        '이메일/SMS 비동기 처리',
        '이미지 처리 백그라운드 작업',
        'API 호출 비동기 처리',
        '데이터 분석 배치 작업'
    ],
    'security': [
        'SQL injection 방지',
        'CSRF 토큰 검증',
        'XSS 방지',
        '인증/인가 로직 검증',
        '민감한 데이터 암호화',
        'rate limiting 적용'
    ]
}
```

#### 배포 단계

```bash
# 배포 전 성능 검증 스크립트
#!/bin/bash

echo "=== Django Performance Check ==="

# 1. 데이터베이스 연결 확인
echo "Checking database connections..."
python manage.py dbshell -c "SELECT COUNT(*) FROM pg_stat_activity;"

# 2. 캐시 연결 확인
echo "Checking cache connections..."
python manage.py shell -c "
from django.core.cache import cache
cache.set('test', 'ok', 10)
print('Cache test:', cache.get('test'))
"

# 3. Celery 워커 상태 확인
echo "Checking Celery workers..."
celery -A myapp inspect active

# 4. 정적 파일 수집
echo "Collecting static files..."
python manage.py collectstatic --noinput

# 5. 데이터베이스 마이그레이션 확인
echo "Checking migrations..."
python manage.py showmigrations --plan

# 6. 시스템 리소스 확인
echo "Checking system resources..."
free -h
df -h
```

#### 운영 단계

```python
# 운영 모니터링 대시보드
# management/commands/health_check.py
from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
import redis
import time

class Command(BaseCommand):
    help = 'Comprehensive health check'
    
    def handle(self, *args, **options):
        health_status = {
            'database': self.check_database(),
            'cache': self.check_cache(),
            'celery': self.check_celery(),
            'disk_space': self.check_disk_space(),
            'memory': self.check_memory(),
        }
        
        overall_status = all(health_status.values())
        
        self.stdout.write(f"Overall Health: {'✅ HEALTHY' if overall_status else '❌ UNHEALTHY'}")
        
        for component, status in health_status.items():
            icon = '✅' if status else '❌'
            self.stdout.write(f"{icon} {component.upper()}: {'OK' if status else 'FAIL'}")
        
        if not overall_status:
            exit(1)
    
    def check_database(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            self.stderr.write(f"Database check failed: {e}")
            return False
    
    def check_cache(self):
        try:
            cache.set('health_check', 'ok', 10)
            return cache.get('health_check') == 'ok'
        except Exception as e:
            self.stderr.write(f"Cache check failed: {e}")
            return False
    
    def check_celery(self):
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            active_workers = inspect.active()
            return bool(active_workers)
        except Exception as e:
            self.stderr.write(f"Celery check failed: {e}")
            return False
    
    def check_disk_space(self):
        import shutil
        try:
            total, used, free = shutil.disk_usage('/')
            free_percent = free / total * 100
            return free_percent > 10  # 10% 이상 여유 공간
        except Exception as e:
            self.stderr.write(f"Disk check failed: {e}")
            return False
    
    def check_memory(self):
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.percent < 90  # 90% 미만 사용률
        except Exception as e:
            self.stderr.write(f"Memory check failed: {e}")
            return False
```

### 4. 트러블슈팅 가이드

#### 일반적인 성능 문제와 해결책

```python
# 1. N+1 쿼리 문제 해결
# 문제: 리스트에서 관련 객체에 접근할 때 추가 쿼리 발생
def fix_n_plus_one():
    # ❌ 잘못된 방법
    posts = Post.objects.all()
    for post in posts:
        print(post.author.username)  # 각 post마다 author 쿼리 실행
    
    # ✅ 올바른 방법
    posts = Post.objects.select_related('author')
    for post in posts:
        print(post.author.username)  # 한 번의 JOIN 쿼리로 해결

# 2. 메모리 사용량 최적화
def optimize_memory_usage():
    # ❌ 큰 QuerySet을 메모리에 로드
    all_users = list(User.objects.all())
    
    # ✅ iterator() 사용으로 메모리 절약
    for user in User.objects.iterator(chunk_size=1000):
        process_user(user)

# 3. 캐시 미스 최소화
class OptimizedProductView:
    def get_product_data(self, product_id):
        # 다단계 캐시 전략
        
        # L1: 인메모리 캐시 (가장 빠름)
        cache_key = f"product:{product_id}"
        data = self.local_cache.get(cache_key)
        if data:
            return data
        
        # L2: Redis 캐시
        data = cache.get(cache_key)
        if data:
            self.local_cache.set(cache_key, data, 300)  # 5분 로컬 캐시
            return data
        
        # L3: 데이터베이스
        product = Product.objects.select_related('category').get(id=product_id)
        data = product.get_cached_data()
        
        # 캐시에 저장
        cache.set(cache_key, data, 3600)  # 1시간 Redis 캐시
        self.local_cache.set(cache_key, data, 300)  # 5분 로컬 캐시
        
        return data
```

### 5. 성능 측정 및 벤치마킹

```python
# performance/benchmarks.py
import time
import statistics
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
import concurrent.futures

class PerformanceBenchmark:
    """성능 벤치마킹 도구"""
    
    def __init__(self, iterations=100):
        self.iterations = iterations
        self.results = []
    
    def benchmark(self, func, *args, **kwargs):
        """함수 성능 측정"""
        times = []
        
        for _ in range(self.iterations):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                result = None
                success = False
                print(f"Error in benchmark: {e}")
            
            end_time = time.time()
            times.append(end_time - start_time)
        
        stats = {
            'iterations': self.iterations,
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'min': min(times),
            'max': max(times),
            'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
        }
        
        return stats
    
    def stress_test(self, func, concurrent_users=10, duration=60):
        """스트레스 테스트"""
        start_time = time.time()
        results = []
        
        def worker():
            worker_results = []
            while time.time() - start_time < duration:
                try:
                    start = time.time()
                    func()
                    end = time.time()
                    worker_results.append(end - start)
                except Exception as e:
                    worker_results.append(None)
            return worker_results
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(worker) for _ in range(concurrent_users)]
            
            for future in concurrent.futures.as_completed(futures):
                results.extend(future.result())
        
        successful_requests = [r for r in results if r is not None]
        failed_requests = len([r for r in results if r is None])
        
        return {
            'total_requests': len(results),
            'successful_requests': len(successful_requests),
            'failed_requests': failed_requests,
            'success_rate': len(successful_requests) / len(results) * 100,
            'avg_response_time': statistics.mean(successful_requests) if successful_requests else 0,
            'requests_per_second': len(successful_requests) / duration,
        }

# 사용 예시
benchmark = PerformanceBenchmark()

# API 엔드포인트 성능 측정
def test_api_performance():
    from django.test import Client
    client = Client()
    
    def api_call():
        response = client.get('/api/products/')
        return response.status_code == 200
    
    stats = benchmark.benchmark(api_call)
    print(f"API Performance: {stats['mean']:.3f}s average")

# 데이터베이스 쿼리 성능 측정
def test_query_performance():
    def query_test():
        return list(Product.objects.select_related('category')[:100])
    
    stats = benchmark.benchmark(query_test)
    print(f"Query Performance: {stats['mean']:.3f}s average")
```

## 결론

Django에서 대용량 트래픽을 효과적으로 처리하기 위해서는 다음과 같은 핵심 원칙들을 기억해야 합니다:

### 핵심 원칙

1. **측정 없이는 최적화 없다**: 항상 성능을 측정하고 병목점을 파악한 후 최적화를 진행하세요.

2. **점진적 개선**: 한 번에 모든 것을 바꾸려 하지 말고, 가장 큰 impact를 가진 부분부터 차례대로 개선하세요.

3. **캐싱은 필수**: 적절한 캐싱 전략은 성능 향상의 가장 확실한 방법입니다.

4. **데이터베이스 최적화**: N+1 쿼리 문제 해결과 적절한 인덱싱은 기본 중의 기본입니다.

5. **비동기 처리**: 무거운 작업은 반드시 백그라운드에서 처리하세요.

6. **모니터링과 알림**: 문제가 발생하기 전에 미리 감지할 수 있는 시스템을 구축하세요.

### 마지막 체크리스트

#### 🔍 개발 단계
- [ ] Django Debug Toolbar로 쿼리 최적화 확인
- [ ] select_related/prefetch_related 적용
- [ ] 캐싱 전략 수립
- [ ] 비동기 작업 분리
- [ ] 코드 리뷰에서 성능 체크

#### 🚀 배포 단계  
- [ ] 정적 파일 CDN 설정
- [ ] Gzip 압축 활성화
- [ ] ASGI 서버 설정
- [ ] 로드 밸런서 구성
- [ ] SSL 최적화

#### 📊 운영 단계
- [ ] 실시간 모니터링 시스템 운영
- [ ] 정기적인 성능 테스트
- [ ] 용량 계획 수립
- [ ] 장애 대응 매뉴얼 작성
- [ ] 백업 및 복구 전략 검증

Django는 적절한 최적화를 통해 충분히 대용량 트래픽을 처리할 수 있는 프레임워크입니다. 이 가이드에서 제시한 방법들을 단계적으로 적용하여 여러분의 서비스가 더 많은 사용자들에게 안정적으로 서비스를 제공할 수 있기를 바랍니다.

성능 최적화는 지속적인 과정입니다. 사용자가 늘어나고 서비스가 복잡해질수록 새로운 병목점이 나타날 수 있으므로, 항상 모니터링하고 개선해 나가는 자세가 중요합니다.

다음 섹션에서는 **실전 사례 및 결론**을 다루겠습니다.