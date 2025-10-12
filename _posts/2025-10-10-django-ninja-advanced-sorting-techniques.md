---
layout: post
title: "Django Ninja List API 정렬 고도화: 동적 정렬과 복합 정렬 완벽 가이드"
date: 2025-10-10 15:00:00 +0900
categories: [Django, API, Django-Ninja]
tags: [Django, Django-Ninja, API, Sorting, Pagination, Performance, Backend]
author: "updaun"
image: "/assets/img/posts/2025-10-10-django-ninja-advanced-sorting-techniques.webp"
---

Django Ninja에서 List API의 정렬 기능을 고도화하는 방법을 살펴보겠습니다. 단순한 정렬부터 복합 정렬, 동적 정렬, 성능 최적화까지 실무에서 바로 활용할 수 있는 기법들을 다룹니다.

## 🎯 Django Ninja 정렬의 핵심 개념

Django Ninja는 FastAPI에서 영감을 받은 고성능 Django REST API 프레임워크입니다. 정렬 기능의 핵심은:

- **Query Parameter 기반**: URL 파라미터로 정렬 조건 전달
- **Type Safety**: Pydantic 스키마를 통한 타입 안전성
- **유연성**: 다양한 정렬 패턴 지원
- **성능**: 데이터베이스 레벨에서의 효율적인 정렬

## 📚 기본 정렬 구현

### 1. 간단한 단일 필드 정렬

```python
from ninja import NinjaAPI, Query
from django.shortcuts import get_list_or_404
from typing import List, Optional
from enum import Enum

api = NinjaAPI()

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

class ProductSortField(str, Enum):
    NAME = "name"
    PRICE = "price"
    CREATED_AT = "created_at"
    RATING = "rating"

@api.get("/products", response=List[ProductSchema])
def list_products(
    request,
    sort_by: Optional[ProductSortField] = Query(ProductSortField.CREATED_AT),
    sort_order: Optional[SortOrder] = Query(SortOrder.DESC)
):
    """기본 정렬이 적용된 상품 목록 조회"""
    
    # 정렬 필드 결정
    order_field = sort_by.value
    if sort_order == SortOrder.DESC:
        order_field = f"-{order_field}"
    
    products = Product.objects.all().order_by(order_field)
    return products
```

### 2. 스키마 기반 정렬 파라미터

```python
from ninja import Schema
from typing import Optional

class ProductListParams(Schema):
    """상품 목록 조회 파라미터"""
    page: Optional[int] = 1
    page_size: Optional[int] = 20
    sort_by: Optional[ProductSortField] = ProductSortField.CREATED_AT
    sort_order: Optional[SortOrder] = SortOrder.DESC
    search: Optional[str] = None
    category_id: Optional[int] = None

@api.get("/products/advanced", response=List[ProductSchema])
def list_products_advanced(request, params: ProductListParams = Query(...)):
    """고급 파라미터를 사용한 상품 목록 조회"""
    
    queryset = Product.objects.all()
    
    # 검색 필터
    if params.search:
        queryset = queryset.filter(
            Q(name__icontains=params.search) |
            Q(description__icontains=params.search)
        )
    
    # 카테고리 필터
    if params.category_id:
        queryset = queryset.filter(category_id=params.category_id)
    
    # 정렬 적용
    order_field = params.sort_by.value
    if params.sort_order == SortOrder.DESC:
        order_field = f"-{order_field}"
    
    queryset = queryset.order_by(order_field)
    
    # 페이지네이션
    start = (params.page - 1) * params.page_size
    end = start + params.page_size
    
    return queryset[start:end]
```

## 🔧 복합 정렬 구현

### 1. 다중 필드 정렬

```python
from typing import List as TypingList

class MultiSortField(Schema):
    """다중 정렬 필드 정의"""
    field: ProductSortField
    order: SortOrder = SortOrder.ASC

class AdvancedProductListParams(Schema):
    """고급 상품 목록 파라미터"""
    page: Optional[int] = 1
    page_size: Optional[int] = 20
    sort_fields: Optional[TypingList[MultiSortField]] = []
    search: Optional[str] = None

@api.post("/products/multi-sort", response=List[ProductSchema])
def list_products_multi_sort(request, params: AdvancedProductListParams):
    """다중 필드 정렬을 지원하는 상품 목록"""
    
    queryset = Product.objects.all()
    
    # 검색 적용
    if params.search:
        queryset = queryset.filter(
            Q(name__icontains=params.search) |
            Q(description__icontains=params.search)
        )
    
    # 다중 정렬 적용
    if params.sort_fields:
        order_fields = []
        for sort_field in params.sort_fields:
            field_name = sort_field.field.value
            if sort_field.order == SortOrder.DESC:
                field_name = f"-{field_name}"
            order_fields.append(field_name)
        
        queryset = queryset.order_by(*order_fields)
    else:
        # 기본 정렬
        queryset = queryset.order_by("-created_at")
    
    # 페이지네이션
    start = (params.page - 1) * params.page_size
    end = start + params.page_size
    
    return queryset[start:end]

# 사용 예제 (클라이언트 요청)
"""
POST /api/products/multi-sort
{
    "sort_fields": [
        {"field": "category", "order": "asc"},
        {"field": "price", "order": "desc"},
        {"field": "name", "order": "asc"}
    ],
    "page": 1,
    "page_size": 20
}
"""
```

### 2. 문자열 기반 다중 정렬

```python
import re
from typing import Optional

def parse_sort_string(sort_string: str) -> List[str]:
    """정렬 문자열을 파싱하여 Django ORM 정렬 필드로 변환
    
    예: "name,-price,created_at" -> ["name", "-price", "created_at"]
    """
    if not sort_string:
        return ["-created_at"]  # 기본 정렬
    
    # 허용된 정렬 필드 정의
    allowed_fields = {
        'name', 'price', 'created_at', 'updated_at', 
        'rating', 'category', 'stock_quantity'
    }
    
    sort_fields = []
    for field in sort_string.split(','):
        field = field.strip()
        
        # 내림차순 처리
        if field.startswith('-'):
            clean_field = field[1:]
            if clean_field in allowed_fields:
                sort_fields.append(field)
        else:
            if field in allowed_fields:
                sort_fields.append(field)
    
    return sort_fields if sort_fields else ["-created_at"]

@api.get("/products/string-sort", response=List[ProductSchema])
def list_products_string_sort(
    request,
    sort: Optional[str] = Query(None, description="정렬 필드 (예: name,-price,created_at)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """문자열 기반 다중 정렬 상품 목록"""
    
    queryset = Product.objects.all()
    
    # 정렬 적용
    sort_fields = parse_sort_string(sort)
    queryset = queryset.order_by(*sort_fields)
    
    # 페이지네이션
    start = (page - 1) * page_size
    end = start + page_size
    
    return queryset[start:end]
```

## 🚀 동적 정렬 시스템

### 1. 설정 기반 정렬 필드 관리

```python
from django.conf import settings
from typing import Dict, Any

class SortFieldConfig:
    """정렬 필드 설정 관리"""
    
    # 정렬 필드 매핑 (API 필드명 -> DB 필드명)
    FIELD_MAPPING = {
        'name': 'name',
        'price': 'price',
        'rating': 'average_rating',
        'popularity': 'view_count',
        'newest': 'created_at',
        'category': 'category__name',
        'brand': 'brand__name',
        'discount': 'discount_percentage',
    }
    
    # 정렬 필드별 추가 설정
    FIELD_CONFIG = {
        'rating': {
            'requires_annotation': True,
            'annotation': 'average_rating',
            'queryset_method': 'annotate_average_rating'
        },
        'popularity': {
            'requires_annotation': True,
            'annotation': 'view_count',
            'queryset_method': 'annotate_view_count'
        }
    }
    
    @classmethod
    def get_db_field(cls, api_field: str) -> str:
        """API 필드명을 DB 필드명으로 변환"""
        return cls.FIELD_MAPPING.get(api_field, api_field)
    
    @classmethod
    def requires_annotation(cls, field: str) -> bool:
        """필드가 어노테이션을 필요로 하는지 확인"""
        return cls.FIELD_CONFIG.get(field, {}).get('requires_annotation', False)
    
    @classmethod
    def get_queryset_method(cls, field: str) -> str:
        """필드에 필요한 쿼리셋 메서드 반환"""
        return cls.FIELD_CONFIG.get(field, {}).get('queryset_method')

class DynamicSortMixin:
    """동적 정렬을 위한 믹스인"""
    
    def apply_sorting(self, queryset, sort_fields: List[str]):
        """정렬 필드 목록을 쿼리셋에 적용"""
        
        # 어노테이션이 필요한 필드들 처리
        annotated_queryset = self._apply_annotations(queryset, sort_fields)
        
        # 정렬 필드 변환
        db_sort_fields = []
        for field in sort_fields:
            is_desc = field.startswith('-')
            clean_field = field[1:] if is_desc else field
            
            db_field = SortFieldConfig.get_db_field(clean_field)
            if is_desc:
                db_field = f"-{db_field}"
            
            db_sort_fields.append(db_field)
        
        return annotated_queryset.order_by(*db_sort_fields)
    
    def _apply_annotations(self, queryset, sort_fields: List[str]):
        """필요한 어노테이션들을 쿼리셋에 적용"""
        annotated_queryset = queryset
        
        for field in sort_fields:
            clean_field = field.lstrip('-')
            
            if SortFieldConfig.requires_annotation(clean_field):
                method_name = SortFieldConfig.get_queryset_method(clean_field)
                if hasattr(annotated_queryset, method_name):
                    annotated_queryset = getattr(annotated_queryset, method_name)()
        
        return annotated_queryset

@api.get("/products/dynamic", response=List[ProductSchema])
def list_products_dynamic(
    request,
    sort: Optional[str] = Query("newest", description="정렬 방식"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """동적 정렬을 지원하는 상품 목록"""
    
    mixin = DynamicSortMixin()
    queryset = Product.objects.all()
    
    # 정렬 문자열 파싱
    sort_fields = parse_sort_string(sort)
    
    # 동적 정렬 적용
    sorted_queryset = mixin.apply_sorting(queryset, sort_fields)
    
    # 페이지네이션
    start = (page - 1) * page_size
    end = start + page_size
    
    return sorted_queryset[start:end]
```

### 2. 쿼리셋 매니저 확장

```python
from django.db import models
from django.db.models import Avg, Count, F

class ProductQuerySet(models.QuerySet):
    """확장된 상품 쿼리셋"""
    
    def annotate_average_rating(self):
        """평균 평점 어노테이션 추가"""
        return self.annotate(
            average_rating=Avg('reviews__rating')
        )
    
    def annotate_view_count(self):
        """조회수 어노테이션 추가"""
        return self.annotate(
            view_count=Count('product_views')
        )
    
    def annotate_review_count(self):
        """리뷰 수 어노테이션 추가"""
        return self.annotate(
            review_count=Count('reviews')
        )
    
    def annotate_discount_amount(self):
        """할인 금액 어노테이션 추가"""
        return self.annotate(
            discount_amount=F('price') * F('discount_percentage') / 100
        )
    
    def with_sorting_annotations(self):
        """모든 정렬 관련 어노테이션 한번에 추가"""
        return (self
                .annotate_average_rating()
                .annotate_view_count()
                .annotate_review_count()
                .annotate_discount_amount())

class ProductManager(models.Manager):
    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db)
    
    def annotate_average_rating(self):
        return self.get_queryset().annotate_average_rating()
    
    def annotate_view_count(self):
        return self.get_queryset().annotate_view_count()
    
    def with_sorting_annotations(self):
        return self.get_queryset().with_sorting_annotations()

# 모델에 적용
class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = ProductManager()
```

## 🎨 고급 정렬 패턴

### 1. 조건부 정렬

```python
class ConditionalSortParams(Schema):
    """조건부 정렬 파라미터"""
    primary_sort: ProductSortField = ProductSortField.CREATED_AT
    primary_order: SortOrder = SortOrder.DESC
    secondary_sort: Optional[ProductSortField] = None
    secondary_order: Optional[SortOrder] = SortOrder.ASC
    category_id: Optional[int] = None
    price_range: Optional[str] = None  # "100-500" 형태

@api.get("/products/conditional", response=List[ProductSchema])
def list_products_conditional(request, params: ConditionalSortParams = Query(...)):
    """조건에 따른 동적 정렬"""
    
    queryset = Product.objects.all()
    
    # 카테고리별 다른 정렬 로직
    if params.category_id:
        category = get_object_or_404(Category, id=params.category_id)
        
        # 전자제품 카테고리는 가격순이 기본
        if category.slug == 'electronics':
            if params.primary_sort == ProductSortField.CREATED_AT:
                params.primary_sort = ProductSortField.PRICE
        
        # 의류 카테고리는 인기순이 기본
        elif category.slug == 'clothing':
            if params.primary_sort == ProductSortField.CREATED_AT:
                params.primary_sort = ProductSortField.RATING
        
        queryset = queryset.filter(category_id=params.category_id)
    
    # 가격 범위 필터
    if params.price_range:
        try:
            min_price, max_price = map(int, params.price_range.split('-'))
            queryset = queryset.filter(price__gte=min_price, price__lte=max_price)
        except ValueError:
            pass
    
    # 정렬 필드 구성
    sort_fields = []
    
    # 주 정렬
    primary_field = params.primary_sort.value
    if params.primary_order == SortOrder.DESC:
        primary_field = f"-{primary_field}"
    sort_fields.append(primary_field)
    
    # 보조 정렬
    if params.secondary_sort:
        secondary_field = params.secondary_sort.value
        if params.secondary_order == SortOrder.DESC:
            secondary_field = f"-{secondary_field}"
        sort_fields.append(secondary_field)
    
    # 최종 정렬 (동점자 처리)
    sort_fields.append('-created_at')
    
    return queryset.order_by(*sort_fields)
```

### 2. 가중치 기반 정렬

```python
from django.db.models import Case, When, Value, IntegerField

class WeightedSortParams(Schema):
    """가중치 기반 정렬 파라미터"""
    user_preferences: Optional[List[str]] = []  # ['electronics', 'books']
    trending: Optional[bool] = False
    personalized: Optional[bool] = False

@api.get("/products/weighted", response=List[ProductSchema])
def list_products_weighted(request, params: WeightedSortParams = Query(...)):
    """가중치 기반 개인화 정렬"""
    
    queryset = Product.objects.all()
    
    # 기본 어노테이션
    queryset = queryset.annotate(
        rating_score=Avg('reviews__rating'),
        view_score=Count('product_views'),
        recent_score=Case(
            When(created_at__gte=timezone.now() - timedelta(days=7), 
                 then=Value(3)),
            When(created_at__gte=timezone.now() - timedelta(days=30), 
                 then=Value(2)),
            default=Value(1),
            output_field=IntegerField()
        )
    )
    
    # 사용자 선호도 가중치
    if params.user_preferences:
        preference_weight = Case(
            *[When(category__slug=pref, then=Value(5)) 
              for pref in params.user_preferences],
            default=Value(1),
            output_field=IntegerField()
        )
        queryset = queryset.annotate(preference_score=preference_weight)
    else:
        queryset = queryset.annotate(preference_score=Value(1))
    
    # 트렌딩 가중치
    if params.trending:
        trending_weight = Case(
            When(product_views__created_at__gte=timezone.now() - timedelta(days=1),
                 then=Value(3)),
            default=Value(1),
            output_field=IntegerField()
        )
        queryset = queryset.annotate(trending_score=trending_weight)
    else:
        queryset = queryset.annotate(trending_score=Value(1))
    
    # 종합 점수 계산
    queryset = queryset.annotate(
        total_score=(
            F('rating_score') * 0.3 +
            F('view_score') * 0.2 +
            F('recent_score') * 0.2 +
            F('preference_score') * 0.2 +
            F('trending_score') * 0.1
        )
    )
    
    return queryset.order_by('-total_score', '-created_at')
```

## ⚡ 성능 최적화

### 1. 인덱스 기반 최적화

```python
# models.py
class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    
    class Meta:
        # 복합 인덱스 설정
        indexes = [
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['price', '-created_at']),
            models.Index(fields=['-created_at', 'category']),
        ]
        
        # 기본 정렬
        ordering = ['-created_at']

# 성능 모니터링을 위한 데코레이터
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def monitor_query_performance(func):
    """쿼리 성능 모니터링 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        # Django 쿼리 카운터 초기화
        from django.db import connection
        initial_queries = len(connection.queries)
        
        result = func(*args, **kwargs)
        
        # 성능 메트릭 계산
        execution_time = time.time() - start_time
        query_count = len(connection.queries) - initial_queries
        
        logger.info(f"""
        Function: {func.__name__}
        Execution Time: {execution_time:.4f}s
        Query Count: {query_count}
        """)
        
        return result
    return wrapper

@api.get("/products/optimized", response=List[ProductSchema])
@monitor_query_performance
def list_products_optimized(
    request,
    sort: Optional[str] = Query("newest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """최적화된 상품 목록 조회"""
    
    # select_related와 prefetch_related 사용
    queryset = Product.objects.select_related(
        'category', 'brand'
    ).prefetch_related(
        'reviews'
    )
    
    # 정렬 최적화
    sort_fields = parse_sort_string(sort)
    
    # 인덱스를 활용한 정렬인지 확인
    optimized_sorts = {
        'newest': ['-created_at'],
        'price_low': ['price'],
        'price_high': ['-price'],
        'category': ['category__name', '-created_at']
    }
    
    if sort in optimized_sorts:
        queryset = queryset.order_by(*optimized_sorts[sort])
    else:
        queryset = queryset.order_by(*sort_fields)
    
    # 페이지네이션 (DB 레벨에서 제한)
    start = (page - 1) * page_size
    end = start + page_size
    
    return queryset[start:end]
```

### 2. 캐싱 전략

```python
from django.core.cache import cache
from django.utils.cache import make_template_fragment_key
import hashlib

class CachedSortingMixin:
    """캐싱이 적용된 정렬 믹스인"""
    
    CACHE_TIMEOUT = 300  # 5분
    
    def get_cache_key(self, sort_params: dict, filters: dict) -> str:
        """캐시 키 생성"""
        cache_data = {**sort_params, **filters}
        cache_string = str(sorted(cache_data.items()))
        return f"product_list_{hashlib.md5(cache_string.encode()).hexdigest()}"
    
    def get_cached_results(self, cache_key: str):
        """캐시된 결과 조회"""
        return cache.get(cache_key)
    
    def set_cache_results(self, cache_key: str, results, timeout=None):
        """결과를 캐시에 저장"""
        timeout = timeout or self.CACHE_TIMEOUT
        cache.set(cache_key, results, timeout)

@api.get("/products/cached", response=List[ProductSchema])
def list_products_cached(
    request,
    sort: Optional[str] = Query("newest"),
    category: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """캐싱이 적용된 상품 목록"""
    
    caching_mixin = CachedSortingMixin()
    
    # 캐시 키 생성
    sort_params = {"sort": sort, "page": page, "page_size": page_size}
    filters = {"category": category} if category else {}
    cache_key = caching_mixin.get_cache_key(sort_params, filters)
    
    # 캐시 조회
    cached_results = caching_mixin.get_cached_results(cache_key)
    if cached_results:
        return cached_results
    
    # 쿼리 실행
    queryset = Product.objects.all()
    
    if category:
        queryset = queryset.filter(category_id=category)
    
    sort_fields = parse_sort_string(sort)
    queryset = queryset.order_by(*sort_fields)
    
    start = (page - 1) * page_size
    end = start + page_size
    results = list(queryset[start:end])
    
    # 캐시 저장
    caching_mixin.set_cache_results(cache_key, results)
    
    return results
```

## 🧪 테스트 전략

### 1. 정렬 로직 테스트

```python
from django.test import TestCase
from django.urls import reverse
from ninja.testing import TestClient

class ProductSortingTestCase(TestCase):
    """상품 정렬 테스트"""
    
    def setUp(self):
        """테스트 데이터 준비"""
        self.client = TestClient(api)
        
        # 테스트 상품 생성
        self.products = [
            Product.objects.create(
                name=f"Product {i}",
                price=100 + i * 10,
                created_at=timezone.now() - timedelta(days=i)
            )
            for i in range(10)
        ]
    
    def test_price_ascending_sort(self):
        """가격 오름차순 정렬 테스트"""
        response = self.client.get("/products?sort=price&order=asc")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        prices = [product['price'] for product in data]
        self.assertEqual(prices, sorted(prices))
    
    def test_price_descending_sort(self):
        """가격 내림차순 정렬 테스트"""
        response = self.client.get("/products?sort=price&order=desc")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        prices = [product['price'] for product in data]
        self.assertEqual(prices, sorted(prices, reverse=True))
    
    def test_multi_field_sort(self):
        """다중 필드 정렬 테스트"""
        response = self.client.post("/products/multi-sort", json={
            "sort_fields": [
                {"field": "category", "order": "asc"},
                {"field": "price", "order": "desc"}
            ]
        })
        self.assertEqual(response.status_code, 200)
    
    def test_invalid_sort_field(self):
        """잘못된 정렬 필드 테스트"""
        response = self.client.get("/products?sort=invalid_field")
        # 기본 정렬로 폴백되어야 함
        self.assertEqual(response.status_code, 200)
    
    def test_performance_with_large_dataset(self):
        """대용량 데이터셋 성능 테스트"""
        # 대량 데이터 생성
        Product.objects.bulk_create([
            Product(name=f"Bulk Product {i}", price=i)
            for i in range(1000)
        ])
        
        start_time = time.time()
        response = self.client.get("/products/optimized?sort=price")
        execution_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(execution_time, 1.0)  # 1초 이내 응답
```

### 2. 통합 테스트

```python
class ProductListIntegrationTest(TestCase):
    """상품 목록 통합 테스트"""
    
    def test_complete_workflow(self):
        """전체 워크플로우 테스트"""
        # 1. 기본 목록 조회
        response = self.client.get("/products")
        self.assertEqual(response.status_code, 200)
        
        # 2. 정렬된 목록 조회
        response = self.client.get("/products?sort=price&order=desc")
        self.assertEqual(response.status_code, 200)
        
        # 3. 필터와 정렬 조합
        response = self.client.get("/products?category=1&sort=name")
        self.assertEqual(response.status_code, 200)
        
        # 4. 페이지네이션과 정렬 조합
        response = self.client.get("/products?sort=price&page=2&page_size=5")
        self.assertEqual(response.status_code, 200)
```

## 📊 실전 활용 예제

### 1. E-commerce 상품 목록

```python
class EcommerceProductListParams(Schema):
    """전자상거래 상품 목록 파라미터"""
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    rating_min: Optional[float] = None
    search: Optional[str] = None
    
    # 정렬 옵션
    sort_by: Optional[str] = "relevance"  # relevance, price, rating, newest
    sort_order: Optional[SortOrder] = SortOrder.DESC
    
    # 페이지네이션
    page: int = 1
    page_size: int = 24

@api.get("/ecommerce/products", response=PaginatedProductResponse)
def ecommerce_product_list(request, params: EcommerceProductListParams = Query(...)):
    """전자상거래용 고급 상품 목록"""
    
    queryset = Product.objects.select_related('category', 'brand')
    
    # 필터 적용
    if params.category_id:
        queryset = queryset.filter(category_id=params.category_id)
    
    if params.brand_id:
        queryset = queryset.filter(brand_id=params.brand_id)
    
    if params.min_price is not None:
        queryset = queryset.filter(price__gte=params.min_price)
    
    if params.max_price is not None:
        queryset = queryset.filter(price__lte=params.max_price)
    
    if params.search:
        queryset = queryset.filter(
            Q(name__icontains=params.search) |
            Q(description__icontains=params.search) |
            Q(category__name__icontains=params.search)
        )
    
    # 정렬 적용
    sort_mapping = {
        'relevance': ['-view_count', '-rating', '-created_at'],
        'price': ['price'] if params.sort_order == SortOrder.ASC else ['-price'],
        'rating': ['-rating', '-review_count'],
        'newest': ['-created_at'],
        'popularity': ['-view_count', '-created_at'],
        'name': ['name'] if params.sort_order == SortOrder.ASC else ['-name']
    }
    
    sort_fields = sort_mapping.get(params.sort_by, ['-created_at'])
    queryset = queryset.order_by(*sort_fields)
    
    # 페이지네이션
    total_count = queryset.count()
    start = (params.page - 1) * params.page_size
    end = start + params.page_size
    
    products = queryset[start:end]
    
    return {
        'items': products,
        'total': total_count,
        'page': params.page,
        'page_size': params.page_size,
        'total_pages': (total_count + params.page_size - 1) // params.page_size
    }
```

### 2. 검색 결과 관련성 정렬

```python
from django.contrib.postgres.search import SearchVector, SearchRank

@api.get("/products/search", response=List[ProductSchema])
def search_products(
    request,
    q: str = Query(..., description="검색어"),
    sort_by: Optional[str] = Query("relevance", description="정렬 방식"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """검색 결과 관련성 기반 정렬"""
    
    if not q:
        return []
    
    # PostgreSQL 전문 검색 사용
    search_vector = SearchVector('name', weight='A') + \
                   SearchVector('description', weight='B')
    
    queryset = Product.objects.annotate(
        search=search_vector,
        rank=SearchRank(search_vector, q)
    ).filter(search=q)
    
    # 정렬 방식에 따른 처리
    if sort_by == "relevance":
        queryset = queryset.order_by('-rank', '-created_at')
    elif sort_by == "price_low":
        queryset = queryset.order_by('price', '-rank')
    elif sort_by == "price_high":
        queryset = queryset.order_by('-price', '-rank')
    elif sort_by == "rating":
        queryset = queryset.order_by('-rating', '-rank')
    else:
        queryset = queryset.order_by('-rank')
    
    # 페이지네이션
    start = (page - 1) * page_size
    end = start + page_size
    
    return queryset[start:end]
```

## 🎯 마무리

Django Ninja에서 List API의 정렬을 고도화하는 핵심 포인트:

### ✅ 체크리스트

1. **기본 구조**
   - [ ] Query 파라미터 기반 정렬 구현
   - [ ] Enum을 활용한 타입 안전성 확보
   - [ ] 기본값 설정으로 사용성 향상

2. **고급 기능**
   - [ ] 다중 필드 정렬 지원
   - [ ] 동적 정렬 필드 관리
   - [ ] 조건부 정렬 로직

3. **성능 최적화**
   - [ ] 적절한 DB 인덱스 설정
   - [ ] 쿼리 최적화 (select_related, prefetch_related)
   - [ ] 캐싱 전략 적용

4. **사용자 경험**
   - [ ] 직관적인 API 설계
   - [ ] 개인화 정렬 지원
   - [ ] 검색 관련성 정렬

Django Ninja의 강력한 타입 시스템과 Django ORM의 유연성을 결합하여 사용자 친화적이면서도 성능이 뛰어난 정렬 API를 구축할 수 있습니다. 실제 서비스에 적용할 때는 사용자의 요구사항과 데이터 특성을 고려하여 적절한 정렬 전략을 선택하세요!

---

*이 포스트가 도움이 되셨다면 공유해주세요! Django Ninja나 API 설계에 대한 궁금한 점이 있으시면 댓글로 남겨주세요.*