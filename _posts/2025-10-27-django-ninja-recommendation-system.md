---
layout: post
title: "Django Ninja로 구축하는 지능형 추천시스템 - 협업 필터링부터 딥러닝까지"
subtitle: "실시간 개인화 추천 엔진 완벽 구현 가이드"
date: 2025-10-27 10:00:00 +0900
background: '/img/posts/django-ninja-recommendation-bg.jpg'
categories: [Django, MachineLearning, AI]
tags: [django-ninja, recommendation-system, collaborative-filtering, machine-learning, personalization, fastapi]
---

# 🤖 Django Ninja로 구축하는 지능형 추천시스템

현대 서비스에서 **개인화 추천**은 사용자 경험과 비즈니스 성과를 결정하는 핵심 요소입니다. Netflix의 영화 추천, Amazon의 상품 추천, Spotify의 음악 추천 등 모든 성공한 플랫폼은 강력한 추천 엔진을 보유하고 있죠.

이번 포스트에서는 **Django Ninja**를 기반으로 **실무에서 바로 사용할 수 있는 추천시스템**을 구축해보겠습니다. 기본적인 협업 필터링부터 최신 딥러닝 기법까지 단계별로 구현해보겠습니다.

## 🎯 구현할 추천시스템 기능

- **협업 필터링** (User-Based, Item-Based)
- **콘텐츠 기반 필터링** (Content-Based Filtering)
- **하이브리드 추천** (Multiple Algorithms)
- **실시간 추천** (Real-time Recommendations)
- **A/B 테스트** 지원
- **추천 성과 분석** (CTR, Conversion Rate)
- **콜드 스타트 문제** 해결

---

## 📊 1. 추천시스템 기초 설계

먼저 추천시스템의 핵심 개념과 아키텍처를 이해하고 프로젝트 구조를 설계해보겠습니다.

### 1.1 추천시스템 유형별 특징

```python
# docs/recommendation_types.py
"""
추천시스템 주요 유형과 특징

1. 협업 필터링 (Collaborative Filtering)
   - User-Based CF: 비슷한 사용자들이 좋아한 아이템 추천
   - Item-Based CF: 사용자가 좋아한 아이템과 유사한 아이템 추천
   
   장점: 도메인 지식 불필요, 의외성(Serendipity) 제공
   단점: 콜드 스타트 문제, 희소성 문제, 확장성 이슈

2. 콘텐츠 기반 필터링 (Content-Based Filtering)
   - 아이템의 속성/특징을 분석하여 유사 아이템 추천
   
   장점: 콜드 스타트 문제 해결, 투명한 추천 이유
   단점: 과적합, 다양성 부족, 도메인 지식 필요

3. 하이브리드 (Hybrid)
   - 여러 방법을 조합하여 각각의 단점 보완
   
   방식: Weighted, Switching, Cascade, Mixed, Feature Combination
"""

class RecommendationStrategy:
    """추천 전략 인터페이스"""
    
    def recommend(self, user_id: int, num_recommendations: int = 10) -> List[Dict]:
        raise NotImplementedError
    
    def explain(self, user_id: int, item_id: int) -> Dict:
        """추천 이유 설명"""
        raise NotImplementedError
    
    def get_performance_metrics(self) -> Dict:
        """추천 성과 지표"""
        raise NotImplementedError
```

### 1.2 프로젝트 구조 설정

```bash
# requirements.txt
django==4.2.7
django-ninja==1.0.1
numpy==1.24.3
pandas==2.0.3
scikit-learn==1.3.0
scipy==1.11.1
redis==5.0.1
celery==5.3.4

# 추천 알고리즘용
surprise==1.1.3
implicit==0.7.2
lightfm==1.17

# 딥러닝 (선택사항)
torch==2.0.1
sentence-transformers==2.2.2

# 데이터 처리
sqlalchemy==2.0.19
psycopg2-binary==2.9.9

# 모니터링
prometheus-client==0.17.1
```

```python
# config/settings/base.py
from pathlib import Path
from decouple import config

# 추천시스템 설정
RECOMMENDATION_SETTINGS = {
    # 기본 설정
    'DEFAULT_ALGORITHM': 'collaborative_filtering',
    'DEFAULT_NUM_RECOMMENDATIONS': 10,
    'MAX_RECOMMENDATIONS': 50,
    
    # 성능 설정
    'BATCH_SIZE': 1000,
    'CACHE_TTL': 3600,  # 1시간
    'MODEL_UPDATE_INTERVAL': 86400,  # 24시간
    
    # 알고리즘별 파라미터
    'COLLABORATIVE_FILTERING': {
        'similarity_metric': 'cosine',
        'min_interactions': 5,
        'n_neighbors': 50,
    },
    
    'CONTENT_BASED': {
        'feature_weights': {
            'category': 0.3,
            'brand': 0.2,
            'price_range': 0.1,
            'description': 0.4,
        }
    },
    
    # A/B 테스트 설정
    'AB_TEST': {
        'enabled': True,
        'test_ratio': 0.1,  # 10% 사용자가 테스트 그룹
    }
}

# Redis 설정 (캐싱용)
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'ninja',
    'django_extensions',
    'django_redis',
    
    # Local apps
    'apps.accounts',
    'apps.products',
    'apps.recommendations',  # 새로 생성
    'apps.analytics',        # 새로 생성
]
```

### 1.3 프로젝트 디렉토리 구조

```
recommendation_system/
├── apps/
│   ├── recommendations/
│   │   ├── models.py              # 추천 관련 모델
│   │   ├── algorithms/            # 추천 알고리즘들
│   │   │   ├── collaborative.py   # 협업 필터링
│   │   │   ├── content_based.py   # 콘텐츠 기반
│   │   │   ├── hybrid.py          # 하이브리드
│   │   │   └── deep_learning.py   # 딥러닝 기반
│   │   ├── services.py            # 추천 서비스 로직
│   │   ├── api.py                 # Django Ninja API
│   │   ├── tasks.py               # Celery 비동기 작업
│   │   ├── schemas.py             # Pydantic 스키마
│   │   └── utils/                 # 유틸리티 함수들
│   │       ├── metrics.py         # 성과 측정
│   │       ├── data_processor.py  # 데이터 전처리
│   │       └── cache_manager.py   # 캐시 관리
│   ├── products/
│   │   └── models.py              # 상품 모델
│   ├── accounts/
│   │   └── models.py              # 사용자 모델
│   └── analytics/
│       ├── models.py              # 분석 데이터 모델
│       └── services.py            # 분석 서비스
├── ml_models/                     # 훈련된 모델 저장
├── data/                          # 데이터 파일들
└── notebooks/                     # 주피터 노트북 (실험용)
```

---

## 🏗️ 2. 데이터 모델 및 스키마 설계

추천시스템의 핵심이 되는 데이터 모델들을 설계해보겠습니다.

### 2.1 기본 엔티티 모델

```python
# apps/products/models.py
from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from model_utils.models import TimeStampedModel

class Category(TimeStampedModel):
    """상품 카테고리"""
    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    level = models.IntegerField(default=0)
    
    def __str__(self):
        return self.name

class Brand(TimeStampedModel):
    """브랜드"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class Product(TimeStampedModel):
    """상품"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products')
    
    # 가격 정보
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # 추천시스템용 메타데이터
    tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    attributes = models.JSONField(default=dict, blank=True)  # 색상, 사이즈, 소재 등
    
    # 통계 정보
    view_count = models.IntegerField(default=0)
    purchase_count = models.IntegerField(default=0)
    rating_sum = models.IntegerField(default=0)
    rating_count = models.IntegerField(default=0)
    
    # 상품 상태
    is_active = models.BooleanField(default=True)
    stock_quantity = models.IntegerField(default=0)
    
    class Meta:
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['price']),
            models.Index(fields=['view_count']),
            models.Index(fields=['purchase_count']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def average_rating(self):
        if self.rating_count > 0:
            return self.rating_sum / self.rating_count
        return 0
    
    @property
    def discount_rate(self):
        if self.original_price:
            return (self.original_price - self.price) / self.original_price * 100
        return 0

# apps/accounts/models.py
class UserProfile(TimeStampedModel):
    """사용자 프로필 확장"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # 인구통계학적 정보
    age_range = models.CharField(max_length=20, blank=True)  # 20-29, 30-39 등
    gender = models.CharField(max_length=10, blank=True)
    location = models.CharField(max_length=100, blank=True)
    
    # 선호도 정보
    preferred_categories = models.ManyToManyField(Category, blank=True)
    preferred_brands = models.ManyToManyField(Brand, blank=True)
    preferred_price_range = models.JSONField(default=dict, blank=True)  # min, max
    
    # 행동 패턴
    shopping_frequency = models.CharField(max_length=20, blank=True)  # weekly, monthly 등
    preferred_shopping_time = models.CharField(max_length=20, blank=True)  # morning, evening 등
    
    # 개인화 설정
    recommendation_enabled = models.BooleanField(default=True)
    email_recommendations = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username} Profile"
```

### 2.2 상호작용 및 추천 모델

```python
# apps/recommendations/models.py
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from model_utils.models import TimeStampedModel
from model_utils import Choices

class InteractionType(models.TextChoices):
    """상호작용 유형"""
    VIEW = 'view', '조회'
    LIKE = 'like', '좋아요'
    CART = 'cart', '장바구니 추가'
    PURCHASE = 'purchase', '구매'
    RATING = 'rating', '평점'
    REVIEW = 'review', '리뷰'
    SHARE = 'share', '공유'
    BOOKMARK = 'bookmark', '북마크'

class UserInteraction(TimeStampedModel):
    """사용자-아이템 상호작용"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interactions')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='interactions')
    
    interaction_type = models.CharField(max_length=20, choices=InteractionType.choices)
    value = models.FloatField(null=True, blank=True)  # 평점, 구매 수량 등
    
    # 컨텍스트 정보
    session_id = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=20, blank=True)  # mobile, desktop, tablet
    source = models.CharField(max_length=50, blank=True)  # search, recommendation, category_browse
    
    # 위치 정보
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'interaction_type', 'created']),
            models.Index(fields=['product', 'interaction_type', 'created']),
            models.Index(fields=['user', 'product', 'interaction_type']),
            models.Index(fields=['session_id']),
            models.Index(fields=['created']),
        ]
        unique_together = [
            ('user', 'product', 'interaction_type', 'created'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.interaction_type}"

class RecommendationAlgorithm(TimeStampedModel):
    """추천 알고리즘 정보"""
    name = models.CharField(max_length=100, unique=True)
    version = models.CharField(max_length=20)
    description = models.TextField()
    
    # 설정 및 파라미터
    parameters = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    
    # 성능 지표
    precision = models.FloatField(null=True, blank=True)
    recall = models.FloatField(null=True, blank=True)
    f1_score = models.FloatField(null=True, blank=True)
    coverage = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} v{self.version}"

class RecommendationRequest(TimeStampedModel):
    """추천 요청 로그"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendation_requests')
    algorithm = models.ForeignKey(RecommendationAlgorithm, on_delete=models.CASCADE)
    
    # 요청 정보
    num_requested = models.IntegerField(default=10)
    context = models.JSONField(default=dict)  # 추천 컨텍스트 (페이지, 시간 등)
    
    # 응답 정보
    num_returned = models.IntegerField(default=0)
    response_time_ms = models.IntegerField(default=0)
    
    # 성과 추적
    impressions = models.IntegerField(default=0)  # 노출 수
    clicks = models.IntegerField(default=0)       # 클릭 수
    conversions = models.IntegerField(default=0)   # 전환 수
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'created']),
            models.Index(fields=['algorithm', 'created']),
        ]

class RecommendationResult(TimeStampedModel):
    """추천 결과"""
    request = models.ForeignKey(RecommendationRequest, on_delete=models.CASCADE, related_name='results')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    
    # 추천 정보
    rank = models.IntegerField()  # 추천 순위
    score = models.FloatField()   # 추천 점수
    explanation = models.JSONField(default=dict)  # 추천 이유
    
    # 성과 추적
    was_viewed = models.BooleanField(default=False)
    was_clicked = models.BooleanField(default=False)
    was_purchased = models.BooleanField(default=False)
    
    # 피드백
    user_feedback = models.CharField(max_length=20, blank=True)  # like, dislike, not_interested
    
    class Meta:
        indexes = [
            models.Index(fields=['request', 'rank']),
            models.Index(fields=['product']),
        ]
        unique_together = [('request', 'product')]
    
    def __str__(self):
        return f"Recommendation #{self.rank}: {self.product.name}"

class UserSimilarity(TimeStampedModel):
    """사용자 간 유사도 (협업 필터링용)"""
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='similarities_as_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='similarities_as_user2')
    
    similarity_score = models.FloatField()
    algorithm = models.CharField(max_length=50)  # cosine, pearson, jaccard 등
    
    # 계산 메타데이터
    common_items_count = models.IntegerField(default=0)
    last_calculated = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user1', 'similarity_score']),
            models.Index(fields=['user2', 'similarity_score']),
        ]
        unique_together = [('user1', 'user2', 'algorithm')]
    
    def __str__(self):
        return f"{self.user1.username} - {self.user2.username}: {self.similarity_score:.3f}"

class ItemSimilarity(TimeStampedModel):
    """아이템 간 유사도"""
    item1 = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='similarities_as_item1')
    item2 = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='similarities_as_item2')
    
    similarity_score = models.FloatField()
    algorithm = models.CharField(max_length=50)  # content, collaborative, hybrid
    
    # 유사도 구성 요소별 점수
    category_similarity = models.FloatField(default=0)
    brand_similarity = models.FloatField(default=0)
    price_similarity = models.FloatField(default=0)
    feature_similarity = models.FloatField(default=0)
    
    last_calculated = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['item1', 'similarity_score']),
            models.Index(fields=['item2', 'similarity_score']),
        ]
        unique_together = [('item1', 'item2', 'algorithm')]

class RecommendationCache(TimeStampedModel):
    """추천 결과 캐시"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    algorithm = models.ForeignKey(RecommendationAlgorithm, on_delete=models.CASCADE)
    
    # 캐시 키와 데이터
    cache_key = models.CharField(max_length=200, unique=True)
    recommendations = models.JSONField()  # 추천 결과 JSON
    
    # 캐시 관리
    expires_at = models.DateTimeField()
    hit_count = models.IntegerField(default=0)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'algorithm']),
            models.Index(fields=['expires_at']),
        ]
```

### 2.3 Pydantic 스키마 정의

```python
# apps/recommendations/schemas.py
from ninja import Schema, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import validator

class InteractionCreateSchema(Schema):
    """상호작용 생성 스키마"""
    product_id: int
    interaction_type: str = Field(..., description="상호작용 유형 (view, like, cart, purchase 등)")
    value: Optional[float] = Field(None, description="상호작용 값 (평점, 수량 등)")
    context: Optional[Dict[str, Any]] = Field(None, description="컨텍스트 정보")
    
    @validator('interaction_type')
    def validate_interaction_type(cls, v):
        allowed_types = ['view', 'like', 'cart', 'purchase', 'rating', 'review', 'share', 'bookmark']
        if v not in allowed_types:
            raise ValueError(f'Invalid interaction type. Must be one of: {allowed_types}')
        return v

class ProductBasicSchema(Schema):
    """기본 상품 정보 스키마"""
    id: int
    name: str
    price: float
    image_url: Optional[str] = None
    category_name: str
    brand_name: str
    average_rating: float
    view_count: int

class RecommendationItemSchema(Schema):
    """추천 아이템 스키마"""
    product: ProductBasicSchema
    score: float = Field(..., description="추천 점수")
    rank: int = Field(..., description="추천 순위")
    explanation: Optional[Dict[str, Any]] = Field(None, description="추천 이유")
    
    class Config:
        from_attributes = True

class RecommendationRequestSchema(Schema):
    """추천 요청 스키마"""
    algorithm: Optional[str] = Field('hybrid', description="추천 알고리즘")
    num_recommendations: int = Field(10, ge=1, le=50, description="추천 개수")
    context: Optional[Dict[str, Any]] = Field(None, description="추천 컨텍스트")
    include_explanation: bool = Field(False, description="추천 이유 포함 여부")
    
    @validator('algorithm')
    def validate_algorithm(cls, v):
        allowed_algorithms = ['collaborative', 'content_based', 'hybrid', 'popular', 'random']
        if v not in allowed_algorithms:
            raise ValueError(f'Invalid algorithm. Must be one of: {allowed_algorithms}')
        return v

class RecommendationResponseSchema(Schema):
    """추천 응답 스키마"""
    recommendations: List[RecommendationItemSchema]
    algorithm_used: str
    total_count: int
    response_time_ms: int
    request_id: str = Field(..., description="요청 ID (추적용)")
    
    # 메타 정보
    user_profile: Optional[Dict[str, Any]] = None
    diversification_applied: bool = False
    cache_hit: bool = False

class SimilarItemsSchema(Schema):
    """유사 아이템 스키마"""
    target_product_id: int
    similar_items: List[RecommendationItemSchema]
    similarity_type: str = Field(..., description="유사도 계산 방법")

class UserFeedbackSchema(Schema):
    """사용자 피드백 스키마"""
    recommendation_id: int
    feedback_type: str = Field(..., description="피드백 유형 (like, dislike, not_interested)")
    reason: Optional[str] = Field(None, description="피드백 이유")
    
    @validator('feedback_type')
    def validate_feedback_type(cls, v):
        allowed_types = ['like', 'dislike', 'not_interested', 'inappropriate']
        if v not in allowed_types:
            raise ValueError(f'Invalid feedback type. Must be one of: {allowed_types}')
        return v

class RecommendationAnalyticsSchema(Schema):
    """추천 분석 스키마"""
    algorithm: str
    period: str  # daily, weekly, monthly
    metrics: Dict[str, float] = Field(..., description="성과 지표")
    
    # 주요 메트릭
    click_through_rate: float
    conversion_rate: float
    coverage: float
    diversity: float
    novelty: float

class PersonalizationSettingsSchema(Schema):
    """개인화 설정 스키마"""
    recommendation_enabled: bool = True
    preferred_categories: List[int] = []
    preferred_brands: List[int] = []
    price_range: Optional[Dict[str, float]] = None
    exclude_categories: List[int] = []
    diversity_preference: float = Field(0.5, ge=0, le=1, description="다양성 선호도 (0=안전, 1=다양)")

class ExplainableRecommendationSchema(Schema):
    """설명 가능한 추천 스키마"""
    product: ProductBasicSchema
    score: float
    explanation: Dict[str, Any] = Field(..., description="상세 추천 이유")
    
    # 설명 구성 요소
    primary_reason: str = Field(..., description="주요 추천 이유")
    secondary_reasons: List[str] = Field([], description="부차적 추천 이유들")
    confidence_score: float = Field(..., ge=0, le=1, description="추천 신뢰도")
```

---

## 🤝 3. 협업 필터링 알고리즘 구현

사용자 행동 패턴을 기반으로 한 협업 필터링을 구현해보겠습니다. User-Based와 Item-Based 두 가지 방식을 모두 구현합니다.

### 3.1 데이터 전처리 및 유틸리티

```python
# apps/recommendations/utils/data_processor.py
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity, pairwise_distances
from sklearn.preprocessing import StandardScaler
from django.core.cache import cache
from django.db.models import Count, Avg, F
from apps.recommendations.models import UserInteraction
from apps.products.models import Product
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class InteractionMatrixBuilder:
    """사용자-아이템 상호작용 매트릭스 생성"""
    
    def __init__(self):
        self.interaction_weights = {
            'view': 1.0,
            'like': 2.0,
            'cart': 3.0,
            'purchase': 5.0,
            'rating': 4.0,
            'review': 3.0,
            'share': 2.0,
            'bookmark': 2.5,
        }
    
    def build_matrix(self, min_interactions: int = 5, time_decay: bool = True) -> Tuple[csr_matrix, Dict, Dict]:
        """상호작용 매트릭스 생성"""
        logger.info("Building user-item interaction matrix...")
        
        # 상호작용 데이터 조회
        interactions_qs = UserInteraction.objects.select_related('user', 'product').filter(
            product__is_active=True
        ).values(
            'user_id', 'product_id', 'interaction_type', 'created', 'value'
        )
        
        # 판다스 DataFrame으로 변환
        df = pd.DataFrame(interactions_qs)
        
        if df.empty:
            logger.warning("No interactions found")
            return csr_matrix((0, 0)), {}, {}
        
        # 가중치 적용
        df['weight'] = df['interaction_type'].map(self.interaction_weights).fillna(1.0)
        
        # 평점의 경우 실제 값 사용
        rating_mask = df['interaction_type'] == 'rating'
        df.loc[rating_mask, 'weight'] = df.loc[rating_mask, 'value'].fillna(3.0)
        
        # 시간 가중치 적용 (최근 상호작용일수록 높은 가중치)
        if time_decay:
            df['days_ago'] = (pd.Timestamp.now() - pd.to_datetime(df['created'])).dt.days
            df['time_weight'] = np.exp(-df['days_ago'] / 30)  # 30일 기준 지수 감소
            df['weight'] *= df['time_weight']
        
        # 사용자/아이템별 상호작용 수 계산
        user_interactions = df.groupby('user_id').size()
        item_interactions = df.groupby('product_id').size()
        
        # 최소 상호작용 수 필터링
        valid_users = user_interactions[user_interactions >= min_interactions].index
        valid_items = item_interactions[item_interactions >= min_interactions].index
        
        df_filtered = df[
            df['user_id'].isin(valid_users) & 
            df['product_id'].isin(valid_items)
        ]
        
        if df_filtered.empty:
            logger.warning("No valid interactions after filtering")
            return csr_matrix((0, 0)), {}, {}
        
        # 사용자/아이템 집계 (중복 상호작용 합계)
        interaction_matrix_df = df_filtered.groupby(['user_id', 'product_id'])['weight'].sum().reset_index()
        
        # 인덱스 매핑 생성
        unique_users = sorted(interaction_matrix_df['user_id'].unique())
        unique_items = sorted(interaction_matrix_df['product_id'].unique())
        
        user_to_idx = {user_id: idx for idx, user_id in enumerate(unique_users)}
        item_to_idx = {item_id: idx for idx, item_id in enumerate(unique_items)}
        
        # 희소 행렬 생성
        row_indices = [user_to_idx[user_id] for user_id in interaction_matrix_df['user_id']]
        col_indices = [item_to_idx[item_id] for item_id in interaction_matrix_df['product_id']]
        data = interaction_matrix_df['weight'].values
        
        matrix = csr_matrix(
            (data, (row_indices, col_indices)), 
            shape=(len(unique_users), len(unique_items))
        )
        
        logger.info(f"Built matrix: {matrix.shape[0]} users x {matrix.shape[1]} items, density: {matrix.nnz / (matrix.shape[0] * matrix.shape[1]):.4f}")
        
        return matrix, user_to_idx, item_to_idx
    
    def normalize_matrix(self, matrix: csr_matrix, method: str = 'user') -> csr_matrix:
        """매트릭스 정규화"""
        if method == 'user':
            # 사용자별 정규화 (각 사용자의 평균 선호도 제거)
            user_means = np.array(matrix.mean(axis=1)).flatten()
            user_means[user_means == 0] = 0  # 0으로 나누기 방지
            
            # 행렬에서 사용자 평균 차감
            normalized = matrix.copy().astype(float)
            for i in range(matrix.shape[0]):
                if user_means[i] > 0:
                    normalized.data[normalized.indptr[i]:normalized.indptr[i+1]] -= user_means[i]
            
            return normalized
        
        elif method == 'item':
            # 아이템별 정규화
            item_means = np.array(matrix.mean(axis=0)).flatten()
            normalized = matrix.copy().astype(float)
            
            for j in range(matrix.shape[1]):
                if item_means[j] > 0:
                    col_data = normalized.getcol(j).data
                    col_data -= item_means[j]
            
            return normalized
        
        return matrix

class SimilarityCalculator:
    """유사도 계산 클래스"""
    
    @staticmethod
    def cosine_similarity_sparse(matrix: csr_matrix, top_k: int = 50) -> csr_matrix:
        """희소 행렬 코사인 유사도 계산"""
        # 정규화
        matrix_norm = matrix.copy()
        matrix_norm.data = matrix_norm.data / np.sqrt(np.array(matrix_norm.power(2).sum(axis=1)).flatten())
        matrix_norm.data = np.nan_to_num(matrix_norm.data)
        
        # 유사도 계산
        similarity = matrix_norm @ matrix_norm.T
        
        # Top-K만 유지 (메모리 효율성)
        if top_k < similarity.shape[0]:
            similarity = SimilarityCalculator._keep_top_k(similarity, top_k)
        
        return similarity
    
    @staticmethod
    def _keep_top_k(similarity_matrix: csr_matrix, k: int) -> csr_matrix:
        """각 행에서 상위 K개 유사도만 유지"""
        for i in range(similarity_matrix.shape[0]):
            row_start = similarity_matrix.indptr[i]
            row_end = similarity_matrix.indptr[i + 1]
            
            if row_end - row_start > k:
                # 현재 행의 데이터
                row_data = similarity_matrix.data[row_start:row_end]
                row_indices = similarity_matrix.indices[row_start:row_end]
                
                # 상위 k개 인덱스 찾기
                top_k_idx = np.argpartition(row_data, -k)[-k:]
                
                # 상위 k개만 유지
                similarity_matrix.data[row_start:row_end] = 0
                similarity_matrix.indices[row_start:row_end] = 0
                
                for idx in top_k_idx:
                    similarity_matrix.data[row_start + idx] = row_data[idx]
                    similarity_matrix.indices[row_start + idx] = row_indices[idx]
        
        similarity_matrix.eliminate_zeros()
        return similarity_matrix
    
    @staticmethod
    def pearson_correlation(matrix: csr_matrix) -> np.ndarray:
        """피어슨 상관계수 계산"""
        # 희소 행렬을 밀집 행렬로 변환 (작은 데이터셋용)
        dense_matrix = matrix.toarray()
        
        # 각 사용자의 평균 계산 (0이 아닌 값들만)
        user_means = []
        for i in range(dense_matrix.shape[0]):
            non_zero_mask = dense_matrix[i] != 0
            if np.sum(non_zero_mask) > 0:
                user_means.append(np.mean(dense_matrix[i][non_zero_mask]))
            else:
                user_means.append(0)
        
        user_means = np.array(user_means)
        
        # 피어슨 상관계수 계산
        correlation_matrix = np.zeros((matrix.shape[0], matrix.shape[0]))
        
        for i in range(matrix.shape[0]):
            for j in range(i, matrix.shape[0]):
                # 공통 아이템 찾기
                common_items = (dense_matrix[i] != 0) & (dense_matrix[j] != 0)
                
                if np.sum(common_items) > 1:  # 최소 2개 공통 아이템 필요
                    user_i_ratings = dense_matrix[i][common_items] - user_means[i]
                    user_j_ratings = dense_matrix[j][common_items] - user_means[j]
                    
                    numerator = np.sum(user_i_ratings * user_j_ratings)
                    denominator = np.sqrt(np.sum(user_i_ratings**2) * np.sum(user_j_ratings**2))
                    
                    if denominator > 0:
                        correlation = numerator / denominator
                        correlation_matrix[i, j] = correlation_matrix[j, i] = correlation
        
        return correlation_matrix
```

### 3.2 User-Based 협업 필터링

```python
# apps/recommendations/algorithms/collaborative.py
import numpy as np
from scipy.sparse import csr_matrix
from django.core.cache import cache
from django.contrib.auth.models import User
from apps.products.models import Product
from apps.recommendations.utils.data_processor import InteractionMatrixBuilder, SimilarityCalculator
from apps.recommendations.models import UserSimilarity, RecommendationAlgorithm
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class UserBasedCollaborativeFiltering:
    """사용자 기반 협업 필터링"""
    
    def __init__(self, min_interactions: int = 5, similarity_threshold: float = 0.1, n_neighbors: int = 50):
        self.min_interactions = min_interactions
        self.similarity_threshold = similarity_threshold
        self.n_neighbors = n_neighbors
        self.matrix_builder = InteractionMatrixBuilder()
        
        # 캐시 키
        self.matrix_cache_key = "cf_user_matrix"
        self.similarity_cache_key = "cf_user_similarity"
    
    def train(self, force_rebuild: bool = False) -> bool:
        """모델 훈련 (사용자 유사도 계산)"""
        logger.info("Starting User-Based CF training...")
        
        # 캐시 확인
        if not force_rebuild and cache.get(self.matrix_cache_key):
            logger.info("Using cached interaction matrix")
            return True
        
        try:
            # 상호작용 매트릭스 구성
            matrix, user_to_idx, item_to_idx = self.matrix_builder.build_matrix(
                min_interactions=self.min_interactions
            )
            
            if matrix.shape[0] == 0:
                logger.error("Empty interaction matrix")
                return False
            
            # 매트릭스 정규화
            normalized_matrix = self.matrix_builder.normalize_matrix(matrix, method='user')
            
            # 사용자 간 유사도 계산
            user_similarity = SimilarityCalculator.cosine_similarity_sparse(
                normalized_matrix, top_k=self.n_neighbors
            )
            
            # 캐시에 저장
            cache_data = {
                'matrix': matrix,
                'normalized_matrix': normalized_matrix,
                'user_similarity': user_similarity,
                'user_to_idx': user_to_idx,
                'item_to_idx': item_to_idx
            }
            
            cache.set(self.matrix_cache_key, cache_data, timeout=3600*24)  # 24시간
            
            # 데이터베이스에 유사도 저장 (상위 유사 사용자들만)
            self._save_similarities_to_db(user_similarity, user_to_idx)
            
            logger.info(f"User-Based CF training completed. Matrix shape: {matrix.shape}")
            return True
            
        except Exception as e:
            logger.error(f"Error in User-Based CF training: {str(e)}")
            return False
    
    def _save_similarities_to_db(self, similarity_matrix: csr_matrix, user_to_idx: Dict[int, int]):
        """유사도를 데이터베이스에 저장"""
        idx_to_user = {idx: user_id for user_id, idx in user_to_idx.items()}
        
        # 기존 유사도 삭제
        UserSimilarity.objects.filter(algorithm='user_based_cf').delete()
        
        similarities_to_create = []
        
        for i in range(similarity_matrix.shape[0]):
            user_id = idx_to_user[i]
            
            # 현재 사용자와 유사한 사용자들 찾기
            row_start = similarity_matrix.indptr[i]
            row_end = similarity_matrix.indptr[i + 1]
            
            similar_indices = similarity_matrix.indices[row_start:row_end]
            similarity_scores = similarity_matrix.data[row_start:row_end]
            
            for j, score in zip(similar_indices, similarity_scores):
                if i != j and score > self.similarity_threshold:
                    similar_user_id = idx_to_user[j]
                    
                    similarities_to_create.append(
                        UserSimilarity(
                            user1_id=user_id,
                            user2_id=similar_user_id,
                            similarity_score=float(score),
                            algorithm='user_based_cf'
                        )
                    )
        
        # 벌크 생성 (배치 크기로 분할)
        batch_size = 1000
        for i in range(0, len(similarities_to_create), batch_size):
            batch = similarities_to_create[i:i + batch_size]
            UserSimilarity.objects.bulk_create(batch, ignore_conflicts=True)
        
        logger.info(f"Saved {len(similarities_to_create)} user similarities to database")
    
    def recommend(self, user_id: int, num_recommendations: int = 10, exclude_purchased: bool = True) -> List[Dict]:
        """사용자에게 추천"""
        cache_data = cache.get(self.matrix_cache_key)
        if not cache_data:
            logger.warning("No cached matrix found, training required")
            if not self.train():
                return []
            cache_data = cache.get(self.matrix_cache_key)
        
        matrix = cache_data['matrix']
        user_similarity = cache_data['user_similarity']
        user_to_idx = cache_data['user_to_idx']
        item_to_idx = cache_data['item_to_idx']
        
        # 사용자 인덱스 확인
        if user_id not in user_to_idx:
            logger.warning(f"User {user_id} not found in training data")
            return self._get_fallback_recommendations(user_id, num_recommendations)
        
        user_idx = user_to_idx[user_id]
        
        # 사용자의 기존 상호작용 가져오기
        user_interactions = matrix[user_idx].toarray().flatten()
        
        # 유사한 사용자들 찾기
        user_similarities = user_similarity[user_idx].toarray().flatten()
        similar_users = np.argsort(user_similarities)[::-1]
        
        # 추천 점수 계산
        recommendation_scores = np.zeros(matrix.shape[1])
        total_similarity = 0
        
        for similar_user_idx in similar_users[:self.n_neighbors]:
            if user_similarities[similar_user_idx] <= 0:
                break
            
            similar_user_interactions = matrix[similar_user_idx].toarray().flatten()
            similarity_score = user_similarities[similar_user_idx]
            
            # 가중 평균으로 점수 계산
            recommendation_scores += similarity_score * similar_user_interactions
            total_similarity += similarity_score
        
        if total_similarity > 0:
            recommendation_scores /= total_similarity
        
        # 이미 상호작용한 아이템 제외
        recommendation_scores[user_interactions > 0] = 0
        
        # 상위 추천 아이템 선택
        top_items = np.argsort(recommendation_scores)[::-1][:num_recommendations * 2]
        
        # 실제 추천 결과 생성
        idx_to_item = {idx: item_id for item_id, idx in item_to_idx.items()}
        recommendations = []
        
        for item_idx in top_items:
            if len(recommendations) >= num_recommendations:
                break
            
            score = recommendation_scores[item_idx]
            if score <= 0:
                continue
            
            item_id = idx_to_item[item_idx]
            
            # 상품 정보 가져오기
            try:
                product = Product.objects.get(id=item_id, is_active=True)
                recommendations.append({
                    'product_id': item_id,
                    'product': product,
                    'score': float(score),
                    'algorithm': 'user_based_cf',
                    'explanation': self._generate_explanation(user_id, item_id, user_similarities, similar_users)
                })
            except Product.DoesNotExist:
                continue
        
        return recommendations
    
    def _generate_explanation(self, user_id: int, item_id: int, user_similarities: np.ndarray, similar_users: np.ndarray) -> Dict:
        """추천 이유 생성"""
        # 이 아이템을 좋아한 유사 사용자들 찾기
        cache_data = cache.get(self.matrix_cache_key)
        matrix = cache_data['matrix']
        user_to_idx = cache_data['user_to_idx']
        item_to_idx = cache_data['item_to_idx']
        
        item_idx = item_to_idx.get(item_id, -1)
        if item_idx == -1:
            return {'reason': 'Similar users liked this item'}
        
        # 이 아이템에 상호작용한 유사 사용자들
        similar_users_who_liked = []
        
        for similar_user_idx in similar_users[:10]:  # 상위 10명만 확인
            similarity_score = user_similarities[similar_user_idx]
            if similarity_score > 0 and matrix[similar_user_idx, item_idx] > 0:
                similar_users_who_liked.append(similarity_score)
        
        return {
            'reason': 'Similar users liked this item',
            'similar_users_count': len(similar_users_who_liked),
            'avg_similarity': float(np.mean(similar_users_who_liked)) if similar_users_who_liked else 0,
            'confidence': min(len(similar_users_who_liked) / 10.0, 1.0)
        }
    
    def _get_fallback_recommendations(self, user_id: int, num_recommendations: int) -> List[Dict]:
        """폴백 추천 (인기도 기반)"""
        popular_products = Product.objects.filter(
            is_active=True
        ).order_by('-purchase_count', '-view_count')[:num_recommendations]
        
        recommendations = []
        for i, product in enumerate(popular_products):
            recommendations.append({
                'product_id': product.id,
                'product': product,
                'score': 1.0 - (i * 0.1),  # 순위 기반 점수
                'algorithm': 'popularity_fallback',
                'explanation': {'reason': 'Popular item (fallback)'}
            })
        
        return recommendations
    
    def get_similar_users(self, user_id: int, num_users: int = 10) -> List[Dict]:
        """유사한 사용자 조회"""
        similarities = UserSimilarity.objects.filter(
            user1_id=user_id,
            algorithm='user_based_cf'
        ).order_by('-similarity_score')[:num_users]
        
        similar_users = []
        for sim in similarities:
            similar_users.append({
                'user_id': sim.user2_id,
                'user': sim.user2,
                'similarity_score': sim.similarity_score,
                'common_items': sim.common_items_count
            })
        
        return similar_users
```

### 3.3 Item-Based 협업 필터링

```python
# apps/recommendations/algorithms/collaborative.py에 추가

class ItemBasedCollaborativeFiltering:
    """아이템 기반 협업 필터링"""
    
    def __init__(self, min_interactions: int = 5, similarity_threshold: float = 0.1, n_neighbors: int = 20):
        self.min_interactions = min_interactions
        self.similarity_threshold = similarity_threshold
        self.n_neighbors = n_neighbors
        self.matrix_builder = InteractionMatrixBuilder()
        
        self.matrix_cache_key = "cf_item_matrix"
    
    def train(self, force_rebuild: bool = False) -> bool:
        """모델 훈련 (아이템 유사도 계산)"""
        logger.info("Starting Item-Based CF training...")
        
        try:
            # 상호작용 매트릭스 구성
            matrix, user_to_idx, item_to_idx = self.matrix_builder.build_matrix(
                min_interactions=self.min_interactions
            )
            
            if matrix.shape[1] == 0:
                logger.error("Empty item matrix")
                return False
            
            # 아이템-사용자 매트릭스로 전치
            item_matrix = matrix.T
            
            # 아이템별 정규화
            normalized_matrix = self.matrix_builder.normalize_matrix(item_matrix, method='user')
            
            # 아이템 간 유사도 계산
            item_similarity = SimilarityCalculator.cosine_similarity_sparse(
                normalized_matrix, top_k=self.n_neighbors
            )
            
            # 캐시에 저장
            cache_data = {
                'user_matrix': matrix,
                'item_matrix': item_matrix,
                'item_similarity': item_similarity,
                'user_to_idx': user_to_idx,
                'item_to_idx': item_to_idx
            }
            
            cache.set(self.matrix_cache_key, cache_data, timeout=3600*24)
            
            # 아이템 유사도 DB 저장
            self._save_item_similarities_to_db(item_similarity, item_to_idx)
            
            logger.info(f"Item-Based CF training completed. Items: {item_matrix.shape[0]}")
            return True
            
        except Exception as e:
            logger.error(f"Error in Item-Based CF training: {str(e)}")
            return False
    
    def recommend(self, user_id: int, num_recommendations: int = 10) -> List[Dict]:
        """아이템 기반 추천"""
        cache_data = cache.get(self.matrix_cache_key)
        if not cache_data:
            if not self.train():
                return []
            cache_data = cache.get(self.matrix_cache_key)
        
        user_matrix = cache_data['user_matrix']
        item_similarity = cache_data['item_similarity']
        user_to_idx = cache_data['user_to_idx']
        item_to_idx = cache_data['item_to_idx']
        
        if user_id not in user_to_idx:
            return self._get_fallback_recommendations(user_id, num_recommendations)
        
        user_idx = user_to_idx[user_id]
        user_interactions = user_matrix[user_idx].toarray().flatten()
        
        # 사용자가 상호작용한 아이템들
        interacted_items = np.where(user_interactions > 0)[0]
        
        if len(interacted_items) == 0:
            return self._get_fallback_recommendations(user_id, num_recommendations)
        
        # 추천 점수 계산
        recommendation_scores = np.zeros(len(item_to_idx))
        
        for item_idx in interacted_items:
            user_rating = user_interactions[item_idx]
            
            # 이 아이템과 유사한 아이템들 찾기
            similar_items_row = item_similarity[item_idx]
            similar_indices = similar_items_row.indices
            similarity_scores = similar_items_row.data
            
            for similar_item_idx, similarity_score in zip(similar_indices, similarity_scores):
                if similar_item_idx != item_idx:  # 자기 자신 제외
                    recommendation_scores[similar_item_idx] += user_rating * similarity_score
        
        # 이미 상호작용한 아이템 제외
        recommendation_scores[interacted_items] = 0
        
        # 상위 추천 선택
        top_items = np.argsort(recommendation_scores)[::-1][:num_recommendations]
        
        # 결과 생성
        idx_to_item = {idx: item_id for item_id, idx in item_to_idx.items()}
        recommendations = []
        
        for item_idx in top_items:
            score = recommendation_scores[item_idx]
            if score <= 0:
                continue
            
            item_id = idx_to_item[item_idx]
            
            try:
                product = Product.objects.get(id=item_id, is_active=True)
                recommendations.append({
                    'product_id': item_id,
                    'product': product,
                    'score': float(score),
                    'algorithm': 'item_based_cf',
                    'explanation': self._generate_item_explanation(user_id, item_id, interacted_items, item_similarity, item_to_idx)
                })
            except Product.DoesNotExist:
                continue
        
        return recommendations
    
    def get_similar_items(self, item_id: int, num_items: int = 10) -> List[Dict]:
        """유사 아이템 조회"""
        from apps.recommendations.models import ItemSimilarity
        
        similarities = ItemSimilarity.objects.filter(
            item1_id=item_id,
            algorithm='item_based_cf'
        ).select_related('item2').order_by('-similarity_score')[:num_items]
        
        similar_items = []
        for sim in similarities:
            similar_items.append({
                'product_id': sim.item2_id,
                'product': sim.item2,
                'similarity_score': sim.similarity_score,
                'explanation': {
                    'category_similarity': sim.category_similarity,
                    'brand_similarity': sim.brand_similarity,
                    'feature_similarity': sim.feature_similarity
                }
            })
        
        return similar_items
    
    def _save_item_similarities_to_db(self, similarity_matrix: csr_matrix, item_to_idx: Dict[int, int]):
        """아이템 유사도를 데이터베이스에 저장"""
        from apps.recommendations.models import ItemSimilarity
        
        idx_to_item = {idx: item_id for item_id, idx in item_to_idx.items()}
        
        # 기존 유사도 삭제
        ItemSimilarity.objects.filter(algorithm='item_based_cf').delete()
        
        similarities_to_create = []
        
        for i in range(similarity_matrix.shape[0]):
            item_id = idx_to_item[i]
            
            row_start = similarity_matrix.indptr[i]
            row_end = similarity_matrix.indptr[i + 1]
            
            similar_indices = similarity_matrix.indices[row_start:row_end]
            similarity_scores = similarity_matrix.data[row_start:row_end]
            
            for j, score in zip(similar_indices, similarity_scores):
                if i != j and score > self.similarity_threshold:
                    similar_item_id = idx_to_item[j]
                    
                    similarities_to_create.append(
                        ItemSimilarity(
                            item1_id=item_id,
                            item2_id=similar_item_id,
                            similarity_score=float(score),
                            algorithm='item_based_cf'
                        )
                    )
        
        # 벌크 생성
        batch_size = 1000
        for i in range(0, len(similarities_to_create), batch_size):
            batch = similarities_to_create[i:i + batch_size]
            ItemSimilarity.objects.bulk_create(batch, ignore_conflicts=True)
    
    def _generate_item_explanation(self, user_id: int, recommended_item_id: int, 
                                 interacted_items: np.ndarray, item_similarity: csr_matrix, 
                                 item_to_idx: Dict[int, int]) -> Dict:
        """아이템 기반 추천 이유 생성"""
        # 추천 아이템과 가장 유사한 사용자 상호작용 아이템 찾기
        recommended_idx = item_to_idx.get(recommended_item_id, -1)
        if recommended_idx == -1:
            return {'reason': 'Similar to items you liked'}
        
        similar_interacted_items = []
        
        for interacted_idx in interacted_items:
            # 유사도 행렬에서 유사도 확인
            similarity_row = item_similarity[interacted_idx]
            
            # 추천 아이템과의 유사도 찾기
            item_position = np.where(similarity_row.indices == recommended_idx)[0]
            if len(item_position) > 0:
                similarity_score = similarity_row.data[item_position[0]]
                idx_to_item = {idx: item_id for item_id, idx in item_to_idx.items()}
                interacted_item_id = idx_to_item[interacted_idx]
                
                similar_interacted_items.append({
                    'item_id': interacted_item_id,
                    'similarity': similarity_score
                })
        
        # 가장 유사한 아이템들 정렬
        similar_interacted_items.sort(key=lambda x: x['similarity'], reverse=True)
        
        return {
            'reason': 'Similar to items you liked',
            'based_on_items': similar_interacted_items[:3],  # 상위 3개
            'similarity_count': len(similar_interacted_items)
        }
    
    def _get_fallback_recommendations(self, user_id: int, num_recommendations: int) -> List[Dict]:
        """폴백 추천"""
        popular_products = Product.objects.filter(
            is_active=True
        ).order_by('-purchase_count')[:num_recommendations]
        
        return [{
            'product_id': product.id,
            'product': product,
            'score': 1.0,
            'algorithm': 'popularity_fallback',
            'explanation': {'reason': 'Popular item'}
        } for product in popular_products]
```

---

## 📊 4. 콘텐츠 기반 필터링 구현

상품의 속성과 특징을 분석하여 사용자 선호도에 맞는 유사한 상품을 추천하는 콘텐츠 기반 필터링을 구현합니다.

### 4.1 특징 추출 및 벡터화

```python
# apps/recommendations/algorithms/content_based.py
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, MultiLabelBinarizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from django.core.cache import cache
from django.db.models import Q
from apps.products.models import Product, Category, Brand
from apps.recommendations.models import UserInteraction
from typing import Dict, List, Tuple, Optional, Any
import re
import logging

logger = logging.getLogger(__name__)

class ProductFeatureExtractor:
    """상품 특징 추출기"""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.8
        )
        self.scaler = StandardScaler()
        self.mlb_tags = MultiLabelBinarizer()
        self.feature_weights = {
            'category': 0.3,
            'brand': 0.2,
            'price': 0.1,
            'description': 0.25,
            'tags': 0.15
        }
    
    def extract_features(self, products_queryset=None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """상품들의 특징을 추출하여 벡터화"""
        logger.info("Extracting product features...")
        
        if products_queryset is None:
            products_queryset = Product.objects.filter(is_active=True).select_related('category', 'brand')
        
        products = list(products_queryset)
        if not products:
            return np.array([]), {}
        
        # 특징별 데이터 준비
        feature_data = {
            'product_ids': [p.id for p in products],
            'categories': [p.category.name if p.category else '' for p in products],
            'brands': [p.brand.name if p.brand else '' for p in products],
            'prices': [float(p.price) for p in products],
            'descriptions': [self._clean_text(p.description) for p in products],
            'names': [self._clean_text(p.name) for p in products],
            'tags': [p.tags for p in products]
        }
        
        # 1. 카테고리 특징
        category_features = self._encode_categories(feature_data['categories'])
        
        # 2. 브랜드 특징
        brand_features = self._encode_brands(feature_data['brands'])
        
        # 3. 가격 특징
        price_features = self._encode_prices(feature_data['prices'])
        
        # 4. 텍스트 특징 (제품명 + 설명)
        text_data = [f"{name} {desc}" for name, desc in zip(feature_data['names'], feature_data['descriptions'])]
        text_features = self._encode_text(text_data)
        
        # 5. 태그 특징
        tag_features = self._encode_tags(feature_data['tags'])
        
        # 특징 결합
        all_features = []
        feature_info = {
            'product_ids': feature_data['product_ids'],
            'feature_names': [],
            'feature_ranges': {}
        }
        
        start_idx = 0
        
        # 카테고리 특징 추가
        if category_features.size > 0:
            weighted_category = category_features * self.feature_weights['category']
            all_features.append(weighted_category)
            end_idx = start_idx + category_features.shape[1]
            feature_info['feature_ranges']['category'] = (start_idx, end_idx)
            start_idx = end_idx
        
        # 브랜드 특징 추가
        if brand_features.size > 0:
            weighted_brand = brand_features * self.feature_weights['brand']
            all_features.append(weighted_brand)
            end_idx = start_idx + brand_features.shape[1]
            feature_info['feature_ranges']['brand'] = (start_idx, end_idx)
            start_idx = end_idx
        
        # 가격 특징 추가
        if price_features.size > 0:
            weighted_price = price_features * self.feature_weights['price']
            all_features.append(weighted_price)
            end_idx = start_idx + price_features.shape[1]
            feature_info['feature_ranges']['price'] = (start_idx, end_idx)
            start_idx = end_idx
        
        # 텍스트 특징 추가
        if text_features.size > 0:
            weighted_text = text_features * self.feature_weights['description']
            all_features.append(weighted_text)
            end_idx = start_idx + text_features.shape[1]
            feature_info['feature_ranges']['description'] = (start_idx, end_idx)
            start_idx = end_idx
        
        # 태그 특징 추가
        if tag_features.size > 0:
            weighted_tags = tag_features * self.feature_weights['tags']
            all_features.append(weighted_tags)
            end_idx = start_idx + tag_features.shape[1]
            feature_info['feature_ranges']['tags'] = (start_idx, end_idx)
            start_idx = end_idx
        
        # 최종 특징 매트릭스
        if all_features:
            combined_features = np.hstack(all_features)
        else:
            combined_features = np.array([])
        
        logger.info(f"Feature extraction completed. Shape: {combined_features.shape}")
        return combined_features, feature_info
    
    def _clean_text(self, text: str) -> str:
        """텍스트 전처리"""
        if not text:
            return ""
        
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)
        # 특수문자 정규화
        text = re.sub(r'[^\w\s]', ' ', text)
        # 공백 정규화
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip().lower()
    
    def _encode_categories(self, categories: List[str]) -> np.ndarray:
        """카테고리 원핫 인코딩"""
        from sklearn.preprocessing import LabelEncoder, OneHotEncoder
        
        if not categories:
            return np.array([])
        
        # 빈 문자열 처리
        categories = [cat if cat else 'unknown' for cat in categories]
        
        le = LabelEncoder()
        encoded_categories = le.fit_transform(categories)
        
        ohe = OneHotEncoder(sparse_output=False)
        onehot_categories = ohe.fit_transform(encoded_categories.reshape(-1, 1))
        
        return onehot_categories
    
    def _encode_brands(self, brands: List[str]) -> np.ndarray:
        """브랜드 원핫 인코딩"""
        from sklearn.preprocessing import LabelEncoder, OneHotEncoder
        
        if not brands:
            return np.array([])
        
        brands = [brand if brand else 'unknown' for brand in brands]
        
        le = LabelEncoder()
        encoded_brands = le.fit_transform(brands)
        
        ohe = OneHotEncoder(sparse_output=False)
        onehot_brands = ohe.fit_transform(encoded_brands.reshape(-1, 1))
        
        return onehot_brands
    
    def _encode_prices(self, prices: List[float]) -> np.ndarray:
        """가격 특징 인코딩"""
        if not prices:
            return np.array([])
        
        prices_array = np.array(prices).reshape(-1, 1)
        
        # 가격 구간별 특징 생성
        price_ranges = [
            (0, 50000),      # 저가
            (50000, 100000), # 중저가  
            (100000, 200000),# 중가
            (200000, 500000),# 중고가
            (500000, float('inf'))  # 고가
        ]
        
        price_features = np.zeros((len(prices), len(price_ranges)))
        
        for i, price in enumerate(prices):
            for j, (min_price, max_price) in enumerate(price_ranges):
                if min_price <= price < max_price:
                    price_features[i, j] = 1
                    break
        
        # 정규화된 가격도 추가
        normalized_prices = self.scaler.fit_transform(prices_array)
        
        return np.hstack([price_features, normalized_prices])
    
    def _encode_text(self, texts: List[str]) -> np.ndarray:
        """텍스트 TF-IDF 인코딩"""
        if not texts or all(not text for text in texts):
            return np.array([])
        
        # 빈 텍스트 처리
        texts = [text if text else 'no description' for text in texts]
        
        try:
            tfidf_features = self.tfidf_vectorizer.fit_transform(texts)
            
            # 차원 축소 (선택사항)
            if tfidf_features.shape[1] > 100:
                svd = TruncatedSVD(n_components=100, random_state=42)
                tfidf_features = svd.fit_transform(tfidf_features)
            else:
                tfidf_features = tfidf_features.toarray()
            
            return tfidf_features
            
        except ValueError as e:
            logger.error(f"Error in text encoding: {str(e)}")
            return np.zeros((len(texts), 1))
    
    def _encode_tags(self, tags_list: List[List[str]]) -> np.ndarray:
        """태그 멀티레이블 인코딩"""
        if not tags_list:
            return np.array([])
        
        # 빈 태그 리스트 처리
        tags_list = [tags if tags else [] for tags in tags_list]
        
        try:
            tag_features = self.mlb_tags.fit_transform(tags_list)
            return tag_features
        except ValueError:
            return np.zeros((len(tags_list), 1))

class UserProfileBuilder:
    """사용자 프로필 생성기"""
    
    def __init__(self, feature_extractor: ProductFeatureExtractor):
        self.feature_extractor = feature_extractor
        
        # 상호작용 가중치
        self.interaction_weights = {
            'view': 1.0,
            'like': 3.0,
            'cart': 4.0,
            'purchase': 5.0,
            'rating': 4.0,
            'bookmark': 2.0
        }
    
    def build_user_profile(self, user_id: int, feature_matrix: np.ndarray, 
                          feature_info: Dict[str, Any]) -> Optional[np.ndarray]:
        """사용자 선호도 프로필 생성"""
        # 사용자 상호작용 데이터 조회
        interactions = UserInteraction.objects.filter(
            user_id=user_id,
            product__is_active=True
        ).select_related('product').order_by('-created')[:100]  # 최근 100개
        
        if not interactions:
            return None
        
        # 상호작용한 상품들의 특징 가져오기
        product_ids = feature_info['product_ids']
        user_product_indices = []
        weights = []
        
        for interaction in interactions:
            try:
                product_idx = product_ids.index(interaction.product_id)
                user_product_indices.append(product_idx)
                
                # 상호작용 가중치 계산
                base_weight = self.interaction_weights.get(interaction.interaction_type, 1.0)
                
                # 평점이 있는 경우 반영
                if interaction.interaction_type == 'rating' and interaction.value:
                    rating_weight = interaction.value / 5.0  # 5점 만점을 1점 만점으로 정규화
                    base_weight *= rating_weight
                
                # 시간 가중치 (최근일수록 높은 가중치)
                days_ago = (timezone.now() - interaction.created).days
                time_weight = np.exp(-days_ago / 30)  # 30일 기준 지수 감소
                
                final_weight = base_weight * time_weight
                weights.append(final_weight)
                
            except (ValueError, IndexError):
                continue
        
        if not user_product_indices:
            return None
        
        # 가중 평균으로 사용자 프로필 생성
        user_features = feature_matrix[user_product_indices]
        weights_array = np.array(weights).reshape(-1, 1)
        
        # 가중 평균 계산
        weighted_features = user_features * weights_array
        user_profile = np.sum(weighted_features, axis=0) / np.sum(weights_array)
        
        return user_profile
    
    def build_user_category_preference(self, user_id: int) -> Dict[str, float]:
        """사용자 카테고리 선호도 분석"""
        interactions = UserInteraction.objects.filter(
            user_id=user_id,
            product__is_active=True
        ).select_related('product__category').values(
            'product__category__name', 'interaction_type'
        )
        
        category_scores = {}
        
        for interaction in interactions:
            category = interaction['product__category__name'] or 'unknown'
            weight = self.interaction_weights.get(interaction['interaction_type'], 1.0)
            
            if category in category_scores:
                category_scores[category] += weight
            else:
                category_scores[category] = weight
        
        # 정규화
        if category_scores:
            total_score = sum(category_scores.values())
            category_scores = {k: v/total_score for k, v in category_scores.items()}
        
        return category_scores

class ContentBasedRecommender:
    """콘텐츠 기반 추천기"""
    
    def __init__(self):
        self.feature_extractor = ProductFeatureExtractor()
        self.user_profile_builder = UserProfileBuilder(self.feature_extractor)
        self.cache_timeout = 3600 * 6  # 6시간
    
    def train(self, force_rebuild: bool = False) -> bool:
        """특징 매트릭스 구축"""
        cache_key = "content_based_features"
        
        if not force_rebuild and cache.get(cache_key):
            logger.info("Using cached feature matrix")
            return True
        
        try:
            logger.info("Building content-based feature matrix...")
            
            # 활성 상품들의 특징 추출
            products_qs = Product.objects.filter(is_active=True).select_related('category', 'brand')
            feature_matrix, feature_info = self.feature_extractor.extract_features(products_qs)
            
            if feature_matrix.size == 0:
                logger.error("Empty feature matrix")
                return False
            
            # 상품 간 유사도 계산
            similarity_matrix = cosine_similarity(feature_matrix)
            
            # 캐시에 저장
            cache_data = {
                'feature_matrix': feature_matrix,
                'feature_info': feature_info,
                'similarity_matrix': similarity_matrix
            }
            
            cache.set(cache_key, cache_data, timeout=self.cache_timeout)
            
            logger.info(f"Content-based training completed. Feature matrix shape: {feature_matrix.shape}")
            return True
            
        except Exception as e:
            logger.error(f"Error in content-based training: {str(e)}")
            return False
    
    def recommend(self, user_id: int, num_recommendations: int = 10, 
                 diversity_factor: float = 0.3) -> List[Dict]:
        """콘텐츠 기반 추천"""
        cache_key = "content_based_features"
        cache_data = cache.get(cache_key)
        
        if not cache_data:
            if not self.train():
                return self._get_fallback_recommendations(user_id, num_recommendations)
            cache_data = cache.get(cache_key)
        
        feature_matrix = cache_data['feature_matrix']
        feature_info = cache_data['feature_info']
        similarity_matrix = cache_data['similarity_matrix']
        
        # 사용자 프로필 구축
        user_profile = self.user_profile_builder.build_user_profile(
            user_id, feature_matrix, feature_info
        )
        
        if user_profile is None:
            return self._get_fallback_recommendations(user_id, num_recommendations)
        
        # 사용자 프로필과 각 상품 간의 유사도 계산
        product_similarities = cosine_similarity([user_profile], feature_matrix)[0]
        
        # 사용자가 이미 상호작용한 상품들 제외
        interacted_products = set(
            UserInteraction.objects.filter(user_id=user_id)
            .values_list('product_id', flat=True)
        )
        
        # 추천 점수 계산
        recommendations = []
        product_ids = feature_info['product_ids']
        
        for i, similarity_score in enumerate(product_similarities):
            product_id = product_ids[i]
            
            if product_id in interacted_products:
                continue
            
            try:
                product = Product.objects.get(id=product_id, is_active=True)
                
                # 다양성 요소 추가
                diversified_score = self._apply_diversity(
                    similarity_score, product, recommendations, diversity_factor
                )
                
                recommendations.append({
                    'product_id': product_id,
                    'product': product,
                    'score': float(diversified_score),
                    'similarity_score': float(similarity_score),
                    'algorithm': 'content_based',
                    'explanation': self._generate_explanation(user_id, product, user_profile, feature_matrix[i], feature_info)
                })
                
            except Product.DoesNotExist:
                continue
        
        # 점수순으로 정렬하여 상위 추천 반환
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations[:num_recommendations]
    
    def get_similar_products(self, product_id: int, num_recommendations: int = 10) -> List[Dict]:
        """특정 상품과 유사한 상품들 추천"""
        cache_key = "content_based_features"
        cache_data = cache.get(cache_key)
        
        if not cache_data:
            if not self.train():
                return []
            cache_data = cache.get(cache_key)
        
        feature_info = cache_data['feature_info']
        similarity_matrix = cache_data['similarity_matrix']
        
        try:
            product_idx = feature_info['product_ids'].index(product_id)
        except ValueError:
            logger.warning(f"Product {product_id} not found in feature matrix")
            return []
        
        # 유사도 점수 가져오기
        similarities = similarity_matrix[product_idx]
        
        # 자기 자신 제외하고 정렬
        similar_indices = np.argsort(similarities)[::-1]
        
        recommendations = []
        for idx in similar_indices:
            if len(recommendations) >= num_recommendations:
                break
            
            if idx == product_idx:  # 자기 자신 제외
                continue
            
            similar_product_id = feature_info['product_ids'][idx]
            similarity_score = similarities[idx]
            
            try:
                product = Product.objects.get(id=similar_product_id, is_active=True)
                recommendations.append({
                    'product_id': similar_product_id,
                    'product': product,
                    'score': float(similarity_score),
                    'algorithm': 'content_based_similar',
                    'explanation': {'reason': 'Similar product features'}
                })
            except Product.DoesNotExist:
                continue
        
        return recommendations
    
    def _apply_diversity(self, base_score: float, product: Product, 
                        existing_recommendations: List[Dict], diversity_factor: float) -> float:
        """다양성 요소를 적용하여 점수 조정"""
        if not existing_recommendations or diversity_factor == 0:
            return base_score
        
        # 기존 추천들과의 카테고리/브랜드 중복도 계산
        category_penalty = 0
        brand_penalty = 0
        
        existing_categories = [rec['product'].category_id for rec in existing_recommendations]
        existing_brands = [rec['product'].brand_id for rec in existing_recommendations]
        
        # 카테고리 중복 패널티
        category_count = existing_categories.count(product.category_id)
        category_penalty = category_count * diversity_factor * 0.2
        
        # 브랜드 중복 패널티
        brand_count = existing_brands.count(product.brand_id)
        brand_penalty = brand_count * diversity_factor * 0.1
        
        # 최종 점수 계산 (패널티 적용)
        diversified_score = base_score * (1 - category_penalty - brand_penalty)
        return max(diversified_score, 0)  # 음수 방지
    
    def _generate_explanation(self, user_id: int, product: Product, 
                            user_profile: np.ndarray, product_features: np.ndarray,
                            feature_info: Dict[str, Any]) -> Dict:
        """추천 이유 생성"""
        explanations = []
        
        # 사용자 카테고리 선호도
        category_prefs = self.user_profile_builder.build_user_category_preference(user_id)
        
        if product.category and product.category.name in category_prefs:
            pref_score = category_prefs[product.category.name]
            if pref_score > 0.2:  # 20% 이상 선호하는 경우
                explanations.append(f"You often browse {product.category.name} category")
        
        # 특징별 유사도 분석
        feature_ranges = feature_info.get('feature_ranges', {})
        
        for feature_name, (start, end) in feature_ranges.items():
            if feature_name in ['category', 'brand']:
                user_feature_part = user_profile[start:end]
                product_feature_part = product_features[start:end]
                
                similarity = cosine_similarity([user_feature_part], [product_feature_part])[0][0]
                
                if similarity > 0.7:  # 높은 유사도
                    if feature_name == 'brand':
                        explanations.append(f"You like {product.brand.name} brand")
                    elif feature_name == 'category':
                        explanations.append(f"Matches your {product.category.name} preferences")
        
        return {
            'primary_reason': explanations[0] if explanations else "Based on your preferences",
            'all_reasons': explanations,
            'match_score': float(cosine_similarity([user_profile], [product_features])[0][0])
        }
    
    def _get_fallback_recommendations(self, user_id: int, num_recommendations: int) -> List[Dict]:
        """폴백 추천 (인기 상품)"""
        popular_products = Product.objects.filter(
            is_active=True
        ).order_by('-view_count', '-purchase_count')[:num_recommendations]
        
        return [{
            'product_id': product.id,
            'product': product,
            'score': 1.0,
            'algorithm': 'popularity_fallback',
            'explanation': {'reason': 'Popular product'}
        } for product in popular_products]
```

### 4.2 고급 특징 엔지니어링

```python
# apps/recommendations/algorithms/advanced_features.py
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sentence_transformers import SentenceTransformer
import torch
from typing import Dict, List, Tuple, Optional
from apps.products.models import Product
import logging

logger = logging.getLogger(__name__)

class AdvancedFeatureExtractor:
    """고급 특징 추출기"""
    
    def __init__(self):
        self.sentence_transformer = None
        self.price_clusterer = KMeans(n_clusters=5, random_state=42)
        self.popularity_scaler = StandardScaler()
        
    def _load_sentence_transformer(self):
        """Sentence Transformer 모델 로드 (지연 로딩)"""
        if self.sentence_transformer is None:
            try:
                self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Sentence Transformer model loaded")
            except Exception as e:
                logger.error(f"Failed to load Sentence Transformer: {str(e)}")
                self.sentence_transformer = None
    
    def extract_semantic_features(self, products: List[Product]) -> Optional[np.ndarray]:
        """의미적 특징 추출 (Sentence Embeddings)"""
        self._load_sentence_transformer()
        
        if self.sentence_transformer is None:
            return None
        
        try:
            # 상품명과 설명을 결합한 텍스트
            texts = []
            for product in products:
                text = f"{product.name} {product.description}"
                texts.append(text[:512])  # 토큰 길이 제한
            
            # 임베딩 생성
            embeddings = self.sentence_transformer.encode(
                texts, 
                show_progress_bar=True,
                batch_size=32
            )
            
            logger.info(f"Generated semantic embeddings: {embeddings.shape}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error in semantic feature extraction: {str(e)}")
            return None
    
    def extract_behavioral_features(self, products: List[Product]) -> np.ndarray:
        """행동 기반 특징 추출"""
        features = []
        
        for product in products:
            # 인기도 지표
            view_count = product.view_count
            purchase_count = product.purchase_count
            rating_count = product.rating_count
            average_rating = product.average_rating
            
            # CTR (Click Through Rate) 추정
            ctr = purchase_count / max(view_count, 1)
            
            # 전환율 (Conversion Rate)
            conversion_rate = purchase_count / max(view_count, 1)
            
            # 평점 신뢰도 (많은 평점을 받을수록 신뢰도 높음)
            rating_reliability = min(rating_count / 100, 1.0)
            
            # 상품 수명 (생성일로부터 경과 시간)
            age_days = (timezone.now() - product.created).days
            age_normalized = min(age_days / 365, 1.0)  # 1년 기준 정규화
            
            features.append([
                view_count,
                purchase_count,
                rating_count,
                average_rating,
                ctr,
                conversion_rate,
                rating_reliability,
                age_normalized
            ])
        
        features_array = np.array(features)
        
        # 정규화
        normalized_features = self.popularity_scaler.fit_transform(features_array)
        
        return normalized_features
    
    def extract_price_clustering_features(self, products: List[Product]) -> np.ndarray:
        """가격 클러스터링 특징"""
        prices = np.array([float(product.price) for product in products]).reshape(-1, 1)
        
        # 가격대별 클러스터링
        price_clusters = self.price_clusterer.fit_predict(prices)
        
        # 원핫 인코딩
        cluster_features = np.zeros((len(products), self.price_clusterer.n_clusters))
        for i, cluster in enumerate(price_clusters):
            cluster_features[i, cluster] = 1
        
        # 가격 통계 특징 추가
        price_stats = []
        for price in prices.flatten():
            # 가격 분위수
            percentile_25 = np.percentile(prices, 25)
            percentile_50 = np.percentile(prices, 50)
            percentile_75 = np.percentile(prices, 75)
            
            price_features = [
                1 if price <= percentile_25 else 0,  # 저가
                1 if percentile_25 < price <= percentile_50 else 0,  # 중저가
                1 if percentile_50 < price <= percentile_75 else 0,  # 중고가
                1 if price > percentile_75 else 0,  # 고가
            ]
            price_stats.append(price_features)
        
        price_stats_array = np.array(price_stats)
        
        # 클러스터 특징과 통계 특징 결합
        return np.hstack([cluster_features, price_stats_array])
    
    def extract_temporal_features(self, products: List[Product]) -> np.ndarray:
        """시간적 특징 추출"""
        features = []
        
        for product in products:
            # 계절성 특징 (상품 생성 월)
            created_month = product.created.month
            season_features = [0, 0, 0, 0]  # 봄, 여름, 가을, 겨울
            
            if created_month in [3, 4, 5]:
                season_features[0] = 1  # 봄
            elif created_month in [6, 7, 8]:
                season_features[1] = 1  # 여름
            elif created_month in [9, 10, 11]:
                season_features[2] = 1  # 가을
            else:
                season_features[3] = 1  # 겨울
            
            # 요일 특징 (상품 생성 요일)
            created_weekday = product.created.weekday()
            weekday_features = [0] * 7
            weekday_features[created_weekday] = 1
            
            # 트렌드 특징
            # 최근 생성된 상품일수록 높은 트렌드 점수
            days_since_creation = (timezone.now() - product.created).days
            trend_score = max(0, 1 - days_since_creation / 365)  # 1년 기준
            
            all_features = season_features + weekday_features + [trend_score]
            features.append(all_features)
        
        return np.array(features)

class MultiModalFeatureFusion:
    """다중 모달 특징 융합"""
    
    def __init__(self, fusion_method: str = 'concatenation'):
        self.fusion_method = fusion_method
        self.feature_weights = {
            'semantic': 0.3,
            'behavioral': 0.25,
            'price': 0.2,
            'temporal': 0.15,
            'categorical': 0.1
        }
    
    def fuse_features(self, feature_dict: Dict[str, np.ndarray]) -> np.ndarray:
        """여러 특징들을 융합"""
        if self.fusion_method == 'concatenation':
            return self._concatenate_features(feature_dict)
        elif self.fusion_method == 'weighted_sum':
            return self._weighted_sum_features(feature_dict)
        elif self.fusion_method == 'attention':
            return self._attention_fusion(feature_dict)
        else:
            raise ValueError(f"Unknown fusion method: {self.fusion_method}")
    
    def _concatenate_features(self, feature_dict: Dict[str, np.ndarray]) -> np.ndarray:
        """단순 연결"""
        features_list = []
        
        for feature_name, features in feature_dict.items():
            if features is not None and features.size > 0:
                # 가중치 적용
                weight = self.feature_weights.get(feature_name, 1.0)
                weighted_features = features * weight
                features_list.append(weighted_features)
        
        if features_list:
            return np.hstack(features_list)
        else:
            return np.array([])
    
    def _weighted_sum_features(self, feature_dict: Dict[str, np.ndarray]) -> np.ndarray:
        """가중 합"""
        # 모든 특징의 차원을 맞춘 후 가중 평균
        target_dim = max(f.shape[1] for f in feature_dict.values() if f is not None)
        
        weighted_sum = None
        total_weight = 0
        
        for feature_name, features in feature_dict.items():
            if features is None:
                continue
            
            weight = self.feature_weights.get(feature_name, 1.0)
            
            # 차원 맞추기 (패딩 또는 차원 축소)
            if features.shape[1] < target_dim:
                padded_features = np.pad(
                    features, 
                    ((0, 0), (0, target_dim - features.shape[1])), 
                    'constant'
                )
            elif features.shape[1] > target_dim:
                padded_features = features[:, :target_dim]
            else:
                padded_features = features
            
            if weighted_sum is None:
                weighted_sum = weight * padded_features
            else:
                weighted_sum += weight * padded_features
            
            total_weight += weight
        
        if weighted_sum is not None and total_weight > 0:
            return weighted_sum / total_weight
        else:
            return np.array([])
    
    def _attention_fusion(self, feature_dict: Dict[str, np.ndarray]) -> np.ndarray:
        """어텐션 기반 융합 (간단한 버전)"""
        # 각 특징의 중요도를 동적으로 계산
        features_list = []
        attention_weights = []
        
        for feature_name, features in feature_dict.items():
            if features is None:
                continue
            
            # 특징의 분산을 기반으로 중요도 계산
            feature_variance = np.var(features, axis=0).mean()
            attention_weight = np.exp(feature_variance) / (1 + np.exp(feature_variance))
            
            features_list.append(features)
            attention_weights.append(attention_weight)
        
        if not features_list:
            return np.array([])
        
        # 어텐션 가중치 정규화
        attention_weights = np.array(attention_weights)
        attention_weights = attention_weights / attention_weights.sum()
        
        # 가중 연결
        weighted_features = []
        for features, weight in zip(features_list, attention_weights):
            weighted_features.append(features * weight)
        
        return np.hstack(weighted_features)
```

---

## 🔀 5. 하이브리드 추천 시스템 구현

여러 추천 알고리즘을 조합하여 각각의 장점을 살리고 단점을 보완하는 하이브리드 시스템을 구현합니다.

### 5.1 하이브리드 전략 매니저

```python
# apps/recommendations/algorithms/hybrid.py
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from django.core.cache import cache
from django.contrib.auth.models import User
from apps.recommendations.algorithms.collaborative import (
    UserBasedCollaborativeFiltering, 
    ItemBasedCollaborativeFiltering
)
from apps.recommendations.algorithms.content_based import ContentBasedRecommender
from apps.recommendations.models import UserInteraction, RecommendationRequest
from apps.products.models import Product
import logging

logger = logging.getLogger(__name__)

class HybridRecommendationStrategy:
    """하이브리드 추천 전략 인터페이스"""
    
    def combine_recommendations(self, recommendations_dict: Dict[str, List[Dict]], 
                             user_id: int, num_recommendations: int) -> List[Dict]:
        raise NotImplementedError

class WeightedHybridStrategy(HybridRecommendationStrategy):
    """가중치 기반 하이브리드"""
    
    def __init__(self, algorithm_weights: Dict[str, float] = None):
        self.algorithm_weights = algorithm_weights or {
            'collaborative_user': 0.4,
            'collaborative_item': 0.3,
            'content_based': 0.3
        }
    
    def combine_recommendations(self, recommendations_dict: Dict[str, List[Dict]], 
                             user_id: int, num_recommendations: int) -> List[Dict]:
        """가중 평균으로 추천 조합"""
        
        # 모든 추천된 상품들 수집
        all_products = {}
        
        for algorithm, recommendations in recommendations_dict.items():
            weight = self.algorithm_weights.get(algorithm, 0.1)
            
            for rec in recommendations:
                product_id = rec['product_id']
                
                if product_id not in all_products:
                    all_products[product_id] = {
                        'product_id': product_id,
                        'product': rec['product'],
                        'total_score': 0,
                        'algorithm_scores': {},
                        'explanations': []
                    }
                
                # 가중치 적용한 점수 합산
                weighted_score = rec['score'] * weight
                all_products[product_id]['total_score'] += weighted_score
                all_products[product_id]['algorithm_scores'][algorithm] = rec['score']
                
                # 설명 수집
                if 'explanation' in rec:
                    all_products[product_id]['explanations'].append({
                        'algorithm': algorithm,
                        'explanation': rec['explanation']
                    })
        
        # 점수순으로 정렬
        sorted_products = sorted(
            all_products.values(), 
            key=lambda x: x['total_score'], 
            reverse=True
        )
        
        # 최종 추천 결과 생성
        final_recommendations = []
        for i, product_data in enumerate(sorted_products[:num_recommendations]):
            final_recommendations.append({
                'product_id': product_data['product_id'],
                'product': product_data['product'],
                'score': product_data['total_score'],
                'rank': i + 1,
                'algorithm': 'weighted_hybrid',
                'algorithm_scores': product_data['algorithm_scores'],
                'explanation': self._generate_hybrid_explanation(product_data)
            })
        
        return final_recommendations
    
    def _generate_hybrid_explanation(self, product_data: Dict) -> Dict:
        """하이브리드 추천 설명 생성"""
        explanations = product_data['explanations']
        algorithm_scores = product_data['algorithm_scores']
        
        # 가장 높은 점수를 준 알고리즘 찾기
        best_algorithm = max(algorithm_scores, key=algorithm_scores.get)
        best_score = algorithm_scores[best_algorithm]
        
        # 주요 추천 이유 결정
        primary_reasons = []
        for exp_data in explanations:
            if exp_data['algorithm'] == best_algorithm:
                exp = exp_data['explanation']
                if isinstance(exp, dict):
                    primary_reasons.append(exp.get('primary_reason', 'Recommended by multiple algorithms'))
                else:
                    primary_reasons.append('Recommended by multiple algorithms')
        
        return {
            'primary_reason': primary_reasons[0] if primary_reasons else 'Recommended by multiple algorithms',
            'contributing_algorithms': list(algorithm_scores.keys()),
            'best_algorithm': best_algorithm,
            'confidence_score': min(best_score, 1.0),
            'consensus_score': len(algorithm_scores) / 3.0  # 3개 알고리즘 기준
        }

class SwitchingHybridStrategy(HybridRecommendationStrategy):
    """스위칭 기반 하이브리드 (상황에 따라 알고리즘 선택)"""
    
    def __init__(self):
        self.min_interactions_for_cf = 10
        self.min_products_for_content = 50
    
    def combine_recommendations(self, recommendations_dict: Dict[str, List[Dict]], 
                             user_id: int, num_recommendations: int) -> List[Dict]:
        """상황에 따라 최적 알고리즘 선택"""
        
        # 사용자 상황 분석
        user_context = self._analyze_user_context(user_id)
        
        # 알고리즘 선택 로직
        selected_algorithm = self._select_best_algorithm(user_context, recommendations_dict)
        
        logger.info(f"Switching strategy selected: {selected_algorithm} for user {user_id}")
        
        # 선택된 알고리즘의 추천 반환
        if selected_algorithm in recommendations_dict:
            recommendations = recommendations_dict[selected_algorithm][:num_recommendations]
            
            # 알고리즘 정보 추가
            for rec in recommendations:
                rec['algorithm'] = f'switching_{selected_algorithm}'
                if 'explanation' not in rec:
                    rec['explanation'] = {}
                rec['explanation']['selection_reason'] = f'Best algorithm for your profile: {selected_algorithm}'
            
            return recommendations
        
        # 폴백: 가중치 전략 사용
        weighted_strategy = WeightedHybridStrategy()
        return weighted_strategy.combine_recommendations(recommendations_dict, user_id, num_recommendations)
    
    def _analyze_user_context(self, user_id: int) -> Dict:
        """사용자 컨텍스트 분석"""
        # 사용자 상호작용 통계
        interactions_count = UserInteraction.objects.filter(user_id=user_id).count()
        
        # 상호작용 다양성 (서로 다른 상품 수)
        unique_products = UserInteraction.objects.filter(
            user_id=user_id
        ).values('product_id').distinct().count()
        
        # 최근 활동 (7일 이내)
        from django.utils import timezone
        from datetime import timedelta
        
        recent_interactions = UserInteraction.objects.filter(
            user_id=user_id,
            created__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # 사용자 프로필 완성도
        try:
            user = User.objects.get(id=user_id)
            profile_completeness = 0
            if hasattr(user, 'profile'):
                profile = user.profile
                if profile.preferred_categories.exists():
                    profile_completeness += 0.3
                if profile.preferred_brands.exists():
                    profile_completeness += 0.3
                if profile.preferred_price_range:
                    profile_completeness += 0.2
                if profile.age_range:
                    profile_completeness += 0.2
        except:
            profile_completeness = 0
        
        return {
            'interactions_count': interactions_count,
            'unique_products': unique_products,
            'recent_activity': recent_interactions,
            'profile_completeness': profile_completeness,
            'diversity_ratio': unique_products / max(interactions_count, 1)
        }
    
    def _select_best_algorithm(self, user_context: Dict, recommendations_dict: Dict) -> str:
        """최적 알고리즘 선택"""
        interactions_count = user_context['interactions_count']
        profile_completeness = user_context['profile_completeness']
        recent_activity = user_context['recent_activity']
        
        # 신규 사용자 (상호작용 부족)
        if interactions_count < self.min_interactions_for_cf:
            if profile_completeness > 0.5:
                return 'content_based'  # 프로필 정보가 있으면 콘텐츠 기반
            else:
                return 'popularity'  # 인기도 기반 폴백
        
        # 활발한 사용자
        elif interactions_count >= self.min_interactions_for_cf:
            # 최근 활동이 많으면 협업 필터링
            if recent_activity >= 3:
                return 'collaborative_user'
            else:
                return 'collaborative_item'
        
        # 중간 단계 사용자
        else:
            return 'content_based'

class CascadingHybridStrategy(HybridRecommendationStrategy):
    """캐스케이딩 하이브리드 (순차적 필터링)"""
    
    def __init__(self, cascade_order: List[str] = None, min_recommendations_per_stage: int = 5):
        self.cascade_order = cascade_order or [
            'collaborative_user',
            'collaborative_item', 
            'content_based'
        ]
        self.min_recommendations_per_stage = min_recommendations_per_stage
    
    def combine_recommendations(self, recommendations_dict: Dict[str, List[Dict]], 
                             user_id: int, num_recommendations: int) -> List[Dict]:
        """순차적으로 추천 생성"""
        
        final_recommendations = []
        used_product_ids = set()
        
        for algorithm in self.cascade_order:
            if algorithm not in recommendations_dict:
                continue
            
            # 현재 단계에서 필요한 추천 수
            needed = num_recommendations - len(final_recommendations)
            if needed <= 0:
                break
            
            # 이미 선택된 상품 제외하고 추천 추가
            algorithm_recommendations = recommendations_dict[algorithm]
            
            stage_count = 0
            for rec in algorithm_recommendations:
                if stage_count >= max(needed, self.min_recommendations_per_stage):
                    break
                
                product_id = rec['product_id']
                if product_id not in used_product_ids:
                    # 캐스케이딩 정보 추가
                    rec_copy = rec.copy()
                    rec_copy['algorithm'] = f'cascading_{algorithm}'
                    rec_copy['cascade_stage'] = len(final_recommendations) // self.min_recommendations_per_stage + 1
                    
                    final_recommendations.append(rec_copy)
                    used_product_ids.add(product_id)
                    stage_count += 1
        
        # 순위 재정렬
        for i, rec in enumerate(final_recommendations):
            rec['rank'] = i + 1
        
        return final_recommendations[:num_recommendations]

class MixedHybridStrategy(HybridRecommendationStrategy):
    """믹스드 하이브리드 (알고리즘별로 일정 비율 배분)"""
    
    def __init__(self, algorithm_ratios: Dict[str, float] = None):
        self.algorithm_ratios = algorithm_ratios or {
            'collaborative_user': 0.4,
            'collaborative_item': 0.3,
            'content_based': 0.3
        }
    
    def combine_recommendations(self, recommendations_dict: Dict[str, List[Dict]], 
                             user_id: int, num_recommendations: int) -> List[Dict]:
        """각 알고리즘에서 일정 비율로 추천 선택"""
        
        final_recommendations = []
        used_product_ids = set()
        
        # 각 알고리즘별 할당 개수 계산
        algorithm_allocations = {}
        remaining_slots = num_recommendations
        
        for algorithm, ratio in self.algorithm_ratios.items():
            if algorithm in recommendations_dict:
                allocated = int(num_recommendations * ratio)
                algorithm_allocations[algorithm] = allocated
                remaining_slots -= allocated
        
        # 남은 슬롯을 첫 번째 알고리즘에 할당
        if remaining_slots > 0 and algorithm_allocations:
            first_algorithm = next(iter(algorithm_allocations.keys()))
            algorithm_allocations[first_algorithm] += remaining_slots
        
        # 각 알고리즘에서 할당된 수만큼 추천 선택
        for algorithm, allocated_count in algorithm_allocations.items():
            if algorithm not in recommendations_dict:
                continue
            
            algorithm_recommendations = recommendations_dict[algorithm]
            added_count = 0
            
            for rec in algorithm_recommendations:
                if added_count >= allocated_count:
                    break
                
                product_id = rec['product_id']
                if product_id not in used_product_ids:
                    rec_copy = rec.copy()
                    rec_copy['algorithm'] = f'mixed_{algorithm}'
                    rec_copy['allocation_source'] = algorithm
                    
                    final_recommendations.append(rec_copy)
                    used_product_ids.add(product_id)
                    added_count += 1
        
        # 점수 기준으로 정렬 (선택사항)
        final_recommendations.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # 순위 재정렬
        for i, rec in enumerate(final_recommendations):
            rec['rank'] = i + 1
        
        return final_recommendations

class HybridRecommendationManager:
    """하이브리드 추천 관리자"""
    
    def __init__(self):
        self.collaborative_user = UserBasedCollaborativeFiltering()
        self.collaborative_item = ItemBasedCollaborativeFiltering()
        self.content_based = ContentBasedRecommender()
        
        # 하이브리드 전략들
        self.strategies = {
            'weighted': WeightedHybridStrategy(),
            'switching': SwitchingHybridStrategy(),
            'cascading': CascadingHybridStrategy(),
            'mixed': MixedHybridStrategy()
        }
        
        self.default_strategy = 'weighted'
    
    def recommend(self, user_id: int, num_recommendations: int = 10, 
                 strategy: str = None, context: Dict = None) -> List[Dict]:
        """하이브리드 추천 실행"""
        
        if strategy is None:
            strategy = self._select_optimal_strategy(user_id, context)
        
        logger.info(f"Using hybrid strategy: {strategy} for user {user_id}")
        
        try:
            # 각 알고리즘별 추천 생성
            recommendations_dict = {}
            
            # User-Based Collaborative Filtering
            try:
                cf_user_recs = self.collaborative_user.recommend(
                    user_id, num_recommendations * 2  # 더 많이 생성 후 필터링
                )
                if cf_user_recs:
                    recommendations_dict['collaborative_user'] = cf_user_recs
            except Exception as e:
                logger.error(f"User-based CF failed: {str(e)}")
            
            # Item-Based Collaborative Filtering  
            try:
                cf_item_recs = self.collaborative_item.recommend(
                    user_id, num_recommendations * 2
                )
                if cf_item_recs:
                    recommendations_dict['collaborative_item'] = cf_item_recs
            except Exception as e:
                logger.error(f"Item-based CF failed: {str(e)}")
            
            # Content-Based Filtering
            try:
                content_recs = self.content_based.recommend(
                    user_id, num_recommendations * 2
                )
                if content_recs:
                    recommendations_dict['content_based'] = content_recs
            except Exception as e:
                logger.error(f"Content-based filtering failed: {str(e)}")
            
            # 추천이 하나도 없으면 인기도 기반 폴백
            if not recommendations_dict:
                return self._get_popularity_recommendations(user_id, num_recommendations)
            
            # 선택된 전략으로 하이브리드 추천 생성
            hybrid_strategy = self.strategies.get(strategy, self.strategies[self.default_strategy])
            
            final_recommendations = hybrid_strategy.combine_recommendations(
                recommendations_dict, user_id, num_recommendations
            )
            
            # 다양성 증진 (선택사항)
            if context and context.get('diversity_boost', False):
                final_recommendations = self._apply_diversity_boost(final_recommendations)
            
            return final_recommendations
            
        except Exception as e:
            logger.error(f"Hybrid recommendation failed: {str(e)}")
            return self._get_popularity_recommendations(user_id, num_recommendations)
    
    def _select_optimal_strategy(self, user_id: int, context: Dict = None) -> str:
        """최적 하이브리드 전략 선택"""
        
        # 사용자 상호작용 수 확인
        interaction_count = UserInteraction.objects.filter(user_id=user_id).count()
        
        # A/B 테스트 그룹 확인
        ab_group = self._get_ab_test_group(user_id)
        
        # 컨텍스트 기반 선택
        if context:
            if context.get('exploration_mode', False):
                return 'mixed'  # 탐험 모드에서는 다양한 알고리즘 혼합
            elif context.get('precision_mode', False):
                return 'weighted'  # 정확도 우선시
        
        # 기본 선택 로직
        if interaction_count < 5:
            return 'cascading'  # 신규 사용자
        elif interaction_count < 20:
            return 'switching'  # 중간 사용자
        else:
            if ab_group == 'A':
                return 'weighted'
            else:
                return 'mixed'
    
    def _get_ab_test_group(self, user_id: int) -> str:
        """A/B 테스트 그룹 결정"""
        # 사용자 ID 기반 해시로 일관된 그룹 배정
        return 'A' if user_id % 2 == 0 else 'B'
    
    def _apply_diversity_boost(self, recommendations: List[Dict]) -> List[Dict]:
        """다양성 증진 적용"""
        if len(recommendations) <= 1:
            return recommendations
        
        # 카테고리/브랜드 다양성 확인
        categories = set()
        brands = set()
        diversified_recs = []
        
        for rec in recommendations:
            product = rec['product']
            category_id = product.category_id if product.category else None
            brand_id = product.brand_id if product.brand else None
            
            # 다양성 점수 계산
            diversity_bonus = 0
            
            if category_id not in categories:
                diversity_bonus += 0.1
                categories.add(category_id)
            
            if brand_id not in brands:
                diversity_bonus += 0.05
                brands.add(brand_id)
            
            # 점수에 다양성 보너스 추가
            rec['score'] += diversity_bonus
            diversified_recs.append(rec)
        
        # 새로운 점수로 재정렬
        diversified_recs.sort(key=lambda x: x['score'], reverse=True)
        
        # 순위 재설정
        for i, rec in enumerate(diversified_recs):
            rec['rank'] = i + 1
        
        return diversified_recs
    
    def _get_popularity_recommendations(self, user_id: int, num_recommendations: int) -> List[Dict]:
        """인기도 기반 폴백 추천"""
        popular_products = Product.objects.filter(
            is_active=True
        ).order_by('-purchase_count', '-view_count')[:num_recommendations]
        
        recommendations = []
        for i, product in enumerate(popular_products):
            recommendations.append({
                'product_id': product.id,
                'product': product,
                'score': 1.0 - (i * 0.05),  # 순위별 점수
                'rank': i + 1,
                'algorithm': 'popularity_fallback',
                'explanation': {
                    'primary_reason': 'Popular product',
                    'fallback_reason': 'Insufficient data for personalized recommendations'
                }
            })
        
        return recommendations
    
    def evaluate_strategy_performance(self, user_id: int, strategy: str, 
                                   recommendations: List[Dict]) -> Dict[str, float]:
        """전략 성과 평가"""
        
        # 실제 사용자 행동과 비교하여 성과 측정
        # (실제 구현에서는 A/B 테스트 결과나 오프라인 평가 데이터 사용)
        
        metrics = {
            'precision': 0.0,
            'recall': 0.0,
            'diversity': 0.0,
            'novelty': 0.0,
            'coverage': 0.0
        }
        
        if not recommendations:
            return metrics
        
        # 다양성 계산 (카테고리/브랜드 기준)
        categories = set(rec['product'].category_id for rec in recommendations if rec['product'].category)
        brands = set(rec['product'].brand_id for rec in recommendations if rec['product'].brand)
        
        metrics['diversity'] = (len(categories) + len(brands)) / (2 * len(recommendations))
        
        # 신규성 계산 (인기도 역수 기준)
        popularity_scores = [1.0 / max(rec['product'].view_count, 1) for rec in recommendations]
        metrics['novelty'] = np.mean(popularity_scores)
        
        # 커버리지 (전체 상품 대비 추천된 상품 비율)
        total_products = Product.objects.filter(is_active=True).count()
        metrics['coverage'] = len(recommendations) / max(total_products, 1)
        
        return metrics
```

### 5.2 실시간 추천 최적화

```python
# apps/recommendations/services.py
from typing import Dict, List, Optional, Any
from django.core.cache import cache
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from apps.recommendations.algorithms.hybrid import HybridRecommendationManager
from apps.recommendations.models import (
    RecommendationRequest, RecommendationResult, 
    RecommendationAlgorithm, UserInteraction
)
import logging
import time
import hashlib

logger = logging.getLogger(__name__)

class RecommendationService:
    """추천 서비스 메인 클래스"""
    
    def __init__(self):
        self.hybrid_manager = HybridRecommendationManager()
        self.cache_timeout = 1800  # 30분
        self.max_cache_size = 1000
    
    def get_recommendations(self, user_id: int, num_recommendations: int = 10,
                          context: Dict = None, force_refresh: bool = False) -> Dict[str, Any]:
        """메인 추천 API"""
        
        start_time = time.time()
        
        try:
            # 캐시 키 생성
            cache_key = self._generate_cache_key(user_id, num_recommendations, context)
            
            # 캐시 확인
            if not force_refresh:
                cached_result = cache.get(cache_key)
                if cached_result:
                    logger.info(f"Cache hit for user {user_id}")
                    cached_result['cache_hit'] = True
                    cached_result['response_time_ms'] = int((time.time() - start_time) * 1000)
                    return cached_result
            
            # 사용자 컨텍스트 분석
            user_context = self._analyze_user_context(user_id, context)
            
            # 추천 생성
            recommendations = self.hybrid_manager.recommend(
                user_id=user_id,
                num_recommendations=num_recommendations,
                context=user_context
            )
            
            # 추천 요청 로깅
            request_id = self._log_recommendation_request(
                user_id, recommendations, user_context, start_time
            )
            
            # 결과 포맷팅
            result = {
                'recommendations': [
                    {
                        'product_id': rec['product_id'],
                        'product_name': rec['product'].name,
                        'product_price': float(rec['product'].price),
                        'product_image': getattr(rec['product'], 'image_url', ''),
                        'score': rec['score'],
                        'rank': rec['rank'],
                        'algorithm': rec['algorithm'],
                        'explanation': rec.get('explanation', {})
                    }
                    for rec in recommendations
                ],
                'total_count': len(recommendations),
                'algorithm_used': recommendations[0]['algorithm'] if recommendations else 'none',
                'request_id': request_id,
                'user_context': user_context,
                'cache_hit': False,
                'response_time_ms': int((time.time() - start_time) * 1000)
            }
            
            # 결과 캐싱
            cache.set(cache_key, result, timeout=self.cache_timeout)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in get_recommendations: {str(e)}")
            return {
                'recommendations': [],
                'total_count': 0,
                'algorithm_used': 'error',
                'request_id': '',
                'error': str(e),
                'response_time_ms': int((time.time() - start_time) * 1000)
            }
    
    def get_similar_products(self, product_id: int, num_recommendations: int = 10) -> List[Dict]:
        """유사 상품 추천"""
        
        cache_key = f"similar_products_{product_id}_{num_recommendations}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        try:
            # 콘텐츠 기반 유사 상품
            content_similar = self.hybrid_manager.content_based.get_similar_products(
                product_id, num_recommendations
            )
            
            # 협업 필터링 기반 유사 상품
            cf_similar = self.hybrid_manager.collaborative_item.get_similar_items(
                product_id, num_recommendations
            )
            
            # 두 결과 조합 (가중 평균)
            combined_results = self._combine_similar_products(content_similar, cf_similar)
            
            # 캐싱
            cache.set(cache_key, combined_results, timeout=3600)  # 1시간
            
            return combined_results
            
        except Exception as e:
            logger.error(f"Error in get_similar_products: {str(e)}")
            return []
    
    def update_user_interaction(self, user_id: int, product_id: int, 
                              interaction_type: str, value: float = None,
                              context: Dict = None) -> bool:
        """사용자 상호작용 업데이트"""
        
        try:
            # 상호작용 기록
            interaction = UserInteraction.objects.create(
                user_id=user_id,
                product_id=product_id,
                interaction_type=interaction_type,
                value=value,
                session_id=context.get('session_id', '') if context else '',
                device_type=context.get('device_type', '') if context else '',
                source=context.get('source', '') if context else ''
            )
            
            # 관련 캐시 무효화
            self._invalidate_user_cache(user_id)
            
            # 실시간 모델 업데이트 (백그라운드 작업)
            from apps.recommendations.tasks import update_user_profile
            update_user_profile.delay(user_id)
            
            logger.info(f"Interaction recorded: user={user_id}, product={product_id}, type={interaction_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording interaction: {str(e)}")
            return False
    
    def get_recommendation_explanation(self, user_id: int, product_id: int) -> Dict:
        """추천 이유 상세 설명"""
        
        try:
            # 최근 추천 결과에서 해당 상품 찾기
            recent_request = RecommendationRequest.objects.filter(
                user_id=user_id,
                created__gte=timezone.now() - timedelta(hours=1)
            ).first()
            
            if recent_request:
                result = RecommendationResult.objects.filter(
                    request=recent_request,
                    product_id=product_id
                ).first()
                
                if result:
                    return {
                        'explanation': result.explanation,
                        'score': result.score,
                        'rank': result.rank,
                        'algorithm_used': recent_request.algorithm.name if recent_request.algorithm else 'unknown'
                    }
            
            # 실시간 설명 생성 (캐시된 추천이 없는 경우)
            return self._generate_realtime_explanation(user_id, product_id)
            
        except Exception as e:
            logger.error(f"Error generating explanation: {str(e)}")
            return {'explanation': 'Unable to generate explanation'}
    
    def _generate_cache_key(self, user_id: int, num_recommendations: int, context: Dict = None) -> str:
        """캐시 키 생성"""
        key_parts = [f"rec_{user_id}_{num_recommendations}"]
        
        if context:
            # 컨텍스트를 정렬하여 일관된 키 생성
            context_str = '_'.join(f"{k}:{v}" for k, v in sorted(context.items()))
            key_parts.append(context_str)
        
        # 해시로 키 길이 제한
        key_string = '_'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _analyze_user_context(self, user_id: int, context: Dict = None) -> Dict:
        """사용자 컨텍스트 분석"""
        
        user_context = {
            'user_id': user_id,
            'timestamp': timezone.now().isoformat(),
        }
        
        # 외부 컨텍스트 추가
        if context:
            user_context.update(context)
        
        # 사용자 활동 패턴 분석
        recent_interactions = UserInteraction.objects.filter(
            user_id=user_id,
            created__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        user_context['recent_activity_level'] = 'high' if recent_interactions >= 10 else 'low'
        
        # 시간대 분석
        current_hour = timezone.now().hour
        if 6 <= current_hour < 12:
            user_context['time_segment'] = 'morning'
        elif 12 <= current_hour < 18:
            user_context['time_segment'] = 'afternoon'
        elif 18 <= current_hour < 22:
            user_context['time_segment'] = 'evening'
        else:
            user_context['time_segment'] = 'night'
        
        return user_context
    
    def _log_recommendation_request(self, user_id: int, recommendations: List[Dict],
                                  context: Dict, start_time: float) -> str:
        """추천 요청 로깅"""
        
        try:
            response_time = int((time.time() - start_time) * 1000)
            
            # 추천 요청 로그 생성
            request = RecommendationRequest.objects.create(
                user_id=user_id,
                num_requested=len(recommendations),
                num_returned=len(recommendations),
                response_time_ms=response_time,
                context=context
            )
            
            # 개별 추천 결과 로그
            results_to_create = []
            for rec in recommendations:
                results_to_create.append(
                    RecommendationResult(
                        request=request,
                        product_id=rec['product_id'],
                        rank=rec['rank'],
                        score=rec['score'],
                        explanation=rec.get('explanation', {})
                    )
                )
            
            # 벌크 생성
            RecommendationResult.objects.bulk_create(results_to_create)
            
            return str(request.id)
            
        except Exception as e:
            logger.error(f"Error logging recommendation request: {str(e)}")
            return ''
    
    def _combine_similar_products(self, content_similar: List[Dict], 
                                cf_similar: List[Dict]) -> List[Dict]:
        """유사 상품 결과 조합"""
        
        # 상품별 점수 합산
        product_scores = {}
        
        # 콘텐츠 기반 점수 (가중치 0.6)
        for item in content_similar:
            product_id = item['product_id']
            product_scores[product_id] = {
                'product': item['product'],
                'content_score': item['score'] * 0.6,
                'cf_score': 0
            }
        
        # 협업 필터링 점수 (가중치 0.4)
        for item in cf_similar:
            product_id = item['product_id']
            if product_id in product_scores:
                product_scores[product_id]['cf_score'] = item['similarity_score'] * 0.4
            else:
                product_scores[product_id] = {
                    'product': item['product'],
                    'content_score': 0,
                    'cf_score': item['similarity_score'] * 0.4
                }
        
        # 최종 점수 계산 및 정렬
        combined_results = []
        for product_id, scores in product_scores.items():
            total_score = scores['content_score'] + scores['cf_score']
            combined_results.append({
                'product_id': product_id,
                'product': scores['product'],
                'score': total_score,
                'algorithm': 'hybrid_similar'
            })
        
        # 점수순 정렬
        combined_results.sort(key=lambda x: x['score'], reverse=True)
        
        return combined_results
    
    def _invalidate_user_cache(self, user_id: int):
        """사용자 관련 캐시 무효화"""
        
        # 사용자별 캐시 패턴으로 삭제
        cache_patterns = [
            f"rec_{user_id}_*",
            f"user_profile_{user_id}",
            f"user_similarities_{user_id}_*"
        ]
        
        # Redis의 경우 패턴 매칭으로 삭제 가능
        # Django 기본 캐시의 경우 개별 키 관리 필요
        try:
            cache.delete_pattern(f"rec_{user_id}_*")
        except AttributeError:
            # 패턴 삭제를 지원하지 않는 캐시 백엔드
            pass
    
    def _generate_realtime_explanation(self, user_id: int, product_id: int) -> Dict:
        """실시간 추천 설명 생성"""
        
        try:
            # 사용자의 최근 상호작용 분석
            recent_interactions = UserInteraction.objects.filter(
                user_id=user_id
            ).select_related('product').order_by('-created')[:10]
            
            explanations = []
            
            # 유사한 상품 구매/조회 이력
            for interaction in recent_interactions:
                if interaction.product.category_id:
                    try:
                        target_product = Product.objects.get(id=product_id)
                        if (target_product.category_id == interaction.product.category_id):
                            explanations.append(f"Similar to {interaction.product.name} you viewed")
                            break
                    except Product.DoesNotExist:
                        pass
            
            return {
                'explanation': {
                    'primary_reason': explanations[0] if explanations else 'Recommended for you',
                    'confidence': 0.7,
                    'generated_realtime': True
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating realtime explanation: {str(e)}")
            return {'explanation': 'Unable to generate explanation'}
```

---

## 🎯 6. Django Ninja API 및 실시간 서비스

Django Ninja를 활용하여 고성능 추천 API를 구현하고 실시간 추천 서비스를 제공합니다.

### 6.1 Django Ninja API 구현

```python
# apps/recommendations/api.py
from ninja import NinjaAPI, Schema, Query
from ninja.security import HttpBearer
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.http import HttpRequest
from typing import List, Optional, Dict, Any
from datetime import datetime
from apps.recommendations.services import RecommendationService
from apps.recommendations.models import UserInteraction
from apps.products.models import Product
import logging

logger = logging.getLogger(__name__)

# API 인스턴스 생성
api = NinjaAPI(
    title="Recommendation Engine API",
    version="1.0.0",
    description="Advanced recommendation system powered by Django Ninja",
    docs_url="/recommendations/docs/"
)

# 인증 스키마
class AuthBearer(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str):
        try:
            # JWT 토큰 검증 로직 (실제 구현에서는 JWT 라이브러리 사용)
            # 여기서는 간단한 예시
            if token.startswith("user_"):
                user_id = int(token.split("_")[1])
                return User.objects.get(id=user_id)
        except:
            pass
        return None

auth = AuthBearer()

# 요청/응답 스키마
class RecommendationRequest(Schema):
    num_recommendations: int = 10
    strategy: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    force_refresh: bool = False
    diversity_boost: bool = False

class ProductSchema(Schema):
    id: int
    name: str
    price: float
    image_url: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    rating: Optional[float] = None

class RecommendationItemSchema(Schema):
    product_id: int
    product_name: str
    product_price: float
    product_image: Optional[str] = None
    score: float
    rank: int
    algorithm: str
    explanation: Dict[str, Any]

class RecommendationResponse(Schema):
    recommendations: List[RecommendationItemSchema]
    total_count: int
    algorithm_used: str
    request_id: str
    cache_hit: bool
    response_time_ms: int
    user_context: Optional[Dict[str, Any]] = None

class InteractionRequest(Schema):
    product_id: int
    interaction_type: str  # 'view', 'like', 'purchase', 'cart_add', 'share'
    value: Optional[float] = None
    session_id: Optional[str] = None
    device_type: Optional[str] = None
    source: Optional[str] = None

class InteractionResponse(Schema):
    success: bool
    message: str
    interaction_id: Optional[int] = None

class SimilarProductsResponse(Schema):
    products: List[RecommendationItemSchema]
    total_count: int
    reference_product_id: int

class ExplanationResponse(Schema):
    product_id: int
    explanation: Dict[str, Any]
    score: float
    algorithm_used: str

# 추천 서비스 인스턴스
recommendation_service = RecommendationService()

@api.post("/recommendations", response=RecommendationResponse, auth=auth)
def get_recommendations(request: HttpRequest, data: RecommendationRequest):
    """개인화된 추천 목록 조회"""
    
    user = request.auth
    
    try:
        # 컨텍스트 준비
        context = data.context or {}
        context.update({
            'diversity_boost': data.diversity_boost,
            'request_timestamp': datetime.now().isoformat(),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'ip_address': request.META.get('REMOTE_ADDR', '')
        })
        
        # 추천 생성
        result = recommendation_service.get_recommendations(
            user_id=user.id,
            num_recommendations=data.num_recommendations,
            context=context,
            force_refresh=data.force_refresh
        )
        
        # 응답 포맷팅
        return RecommendationResponse(
            recommendations=[
                RecommendationItemSchema(**rec) for rec in result['recommendations']
            ],
            total_count=result['total_count'],
            algorithm_used=result['algorithm_used'],
            request_id=result['request_id'],
            cache_hit=result.get('cache_hit', False),
            response_time_ms=result['response_time_ms'],
            user_context=result.get('user_context')
        )
        
    except Exception as e:
        logger.error(f"Error in get_recommendations API: {str(e)}")
        return RecommendationResponse(
            recommendations=[],
            total_count=0,
            algorithm_used="error",
            request_id="",
            cache_hit=False,
            response_time_ms=0
        )

@api.post("/interactions", response=InteractionResponse, auth=auth)
def record_interaction(request: HttpRequest, data: InteractionRequest):
    """사용자 상호작용 기록"""
    
    user = request.auth
    
    try:
        # 상호작용 컨텍스트 준비
        context = {
            'session_id': data.session_id,
            'device_type': data.device_type,
            'source': data.source,
            'timestamp': datetime.now().isoformat(),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'referer': request.META.get('HTTP_REFERER', '')
        }
        
        # 상호작용 기록
        success = recommendation_service.update_user_interaction(
            user_id=user.id,
            product_id=data.product_id,
            interaction_type=data.interaction_type,
            value=data.value,
            context=context
        )
        
        if success:
            # 최근 생성된 상호작용 ID 조회
            interaction = UserInteraction.objects.filter(
                user=user,
                product_id=data.product_id,
                interaction_type=data.interaction_type
            ).order_by('-created').first()
            
            return InteractionResponse(
                success=True,
                message="Interaction recorded successfully",
                interaction_id=interaction.id if interaction else None
            )
        else:
            return InteractionResponse(
                success=False,
                message="Failed to record interaction"
            )
            
    except Exception as e:
        logger.error(f"Error recording interaction: {str(e)}")
        return InteractionResponse(
            success=False,
            message=f"Error: {str(e)}"
        )

@api.get("/products/{product_id}/similar", response=SimilarProductsResponse)
def get_similar_products(request: HttpRequest, product_id: int, num_items: int = Query(10)):
    """유사 상품 추천"""
    
    try:
        # 상품 존재 확인
        product = get_object_or_404(Product, id=product_id)
        
        # 유사 상품 조회
        similar_products = recommendation_service.get_similar_products(
            product_id=product_id,
            num_recommendations=num_items
        )
        
        # 응답 포맷팅
        formatted_products = []
        for item in similar_products:
            formatted_products.append(
                RecommendationItemSchema(
                    product_id=item['product_id'],
                    product_name=item['product'].name,
                    product_price=float(item['product'].price),
                    product_image=getattr(item['product'], 'image_url', ''),
                    score=item['score'],
                    rank=len(formatted_products) + 1,
                    algorithm=item['algorithm'],
                    explanation={'similarity_reason': 'Product similarity based on features'}
                )
            )
        
        return SimilarProductsResponse(
            products=formatted_products,
            total_count=len(formatted_products),
            reference_product_id=product_id
        )
        
    except Exception as e:
        logger.error(f"Error getting similar products: {str(e)}")
        return SimilarProductsResponse(
            products=[],
            total_count=0,
            reference_product_id=product_id
        )

@api.get("/recommendations/{product_id}/explanation", response=ExplanationResponse, auth=auth)
def get_recommendation_explanation(request: HttpRequest, product_id: int):
    """추천 이유 상세 설명"""
    
    user = request.auth
    
    try:
        explanation = recommendation_service.get_recommendation_explanation(
            user_id=user.id,
            product_id=product_id
        )
        
        return ExplanationResponse(
            product_id=product_id,
            explanation=explanation.get('explanation', {}),
            score=explanation.get('score', 0.0),
            algorithm_used=explanation.get('algorithm_used', 'unknown')
        )
        
    except Exception as e:
        logger.error(f"Error getting explanation: {str(e)}")
        return ExplanationResponse(
            product_id=product_id,
            explanation={'error': str(e)},
            score=0.0,
            algorithm_used='error'
        )

@api.get("/users/stats", auth=auth)
def get_user_stats(request: HttpRequest):
    """사용자 추천 통계"""
    
    user = request.auth
    
    try:
        from django.db.models import Count, Avg
        from django.utils import timezone
        from datetime import timedelta
        
        # 최근 30일 통계
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        stats = {
            'total_interactions': UserInteraction.objects.filter(user=user).count(),
            'recent_interactions': UserInteraction.objects.filter(
                user=user, 
                created__gte=thirty_days_ago
            ).count(),
            'interaction_types': list(
                UserInteraction.objects.filter(user=user)
                .values('interaction_type')
                .annotate(count=Count('id'))
                .order_by('-count')
            ),
            'favorite_categories': [],  # 구현 필요
            'recommendation_accuracy': 0.75,  # 실제 계산 필요
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}")
        return {'error': str(e)}

# 관리자용 API
@api.get("/admin/algorithms/performance")
def get_algorithm_performance(request: HttpRequest):
    """알고리즘 성능 통계 (관리자용)"""
    
    # 실제 구현에서는 관리자 권한 체크 필요
    
    try:
        from django.db.models import Avg, Count
        from apps.recommendations.models import RecommendationRequest
        
        # 알고리즘별 성능 통계
        performance_stats = RecommendationRequest.objects.values(
            'algorithm__name'
        ).annotate(
            avg_response_time=Avg('response_time_ms'),
            total_requests=Count('id'),
            avg_returned=Avg('num_returned')
        ).order_by('-total_requests')
        
        return {
            'algorithm_performance': list(performance_stats),
            'total_requests': RecommendationRequest.objects.count(),
            'avg_response_time': RecommendationRequest.objects.aggregate(
                avg=Avg('response_time_ms')
            )['avg']
        }
        
    except Exception as e:
        logger.error(f"Error getting performance stats: {str(e)}")
        return {'error': str(e)}

@api.post("/admin/cache/clear")
def clear_recommendation_cache(request: HttpRequest):
    """추천 캐시 클리어 (관리자용)"""
    
    try:
        from django.core.cache import cache
        
        # 패턴 기반 캐시 삭제
        try:
            cache.delete_pattern("rec_*")
            cache.delete_pattern("similar_products_*")
            cache.delete_pattern("user_profile_*")
            return {'success': True, 'message': 'Cache cleared successfully'}
        except AttributeError:
            # 패턴 삭제를 지원하지 않는 캐시 백엔드
            cache.clear()
            return {'success': True, 'message': 'All cache cleared'}
            
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return {'success': False, 'error': str(e)}

# 헬스체크 엔드포인트
@api.get("/health")
def health_check(request: HttpRequest):
    """시스템 상태 확인"""
    
    try:
        from django.db import connection
        
        # 데이터베이스 연결 체크
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # 캐시 연결 체크
        from django.core.cache import cache
        cache.set('health_check', 'ok', 10)
        cache_status = cache.get('health_check') == 'ok'
        
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'ok',
            'cache': 'ok' if cache_status else 'error',
            'version': '1.0.0'
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }
```

### 6.2 실시간 추천 WebSocket 서비스

```python
# apps/recommendations/websocket.py
import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from apps.recommendations.services import RecommendationService
from apps.recommendations.models import UserInteraction

logger = logging.getLogger(__name__)

class RecommendationConsumer(AsyncWebsocketConsumer):
    """실시간 추천 WebSocket 컨슈머"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = None
        self.room_group_name = None
        self.recommendation_service = RecommendationService()
    
    async def connect(self):
        """WebSocket 연결"""
        
        try:
            # URL에서 사용자 ID 추출
            self.user_id = self.scope['url_route']['kwargs']['user_id']
            
            # 인증 확인 (실제 구현에서는 JWT 토큰 검증)
            user = await self.get_user(self.user_id)
            if not user:
                await self.close(code=4001)
                return
            
            # 그룹 이름 생성
            self.room_group_name = f"recommendations_{self.user_id}"
            
            # 그룹 참가
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            await self.accept()
            
            # 연결 확인 메시지 전송
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': f'Connected to recommendation stream for user {self.user_id}',
                'timestamp': self._get_timestamp()
            }))
            
            # 초기 추천 전송
            await self.send_initial_recommendations()
            
        except Exception as e:
            logger.error(f"WebSocket connection error: {str(e)}")
            await self.close(code=4000)
    
    async def disconnect(self, close_code):
        """WebSocket 연결 해제"""
        
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """클라이언트로부터 메시지 수신"""
        
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'get_recommendations':
                await self.handle_recommendation_request(data)
            
            elif message_type == 'record_interaction':
                await self.handle_interaction(data)
            
            elif message_type == 'get_similar_products':
                await self.handle_similar_products_request(data)
            
            else:
                await self.send_error("Unknown message type")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"WebSocket receive error: {str(e)}")
            await self.send_error(str(e))
    
    async def handle_recommendation_request(self, data):
        """추천 요청 처리"""
        
        try:
            num_recommendations = data.get('num_recommendations', 10)
            context = data.get('context', {})
            force_refresh = data.get('force_refresh', False)
            
            # 실시간 컨텍스트 추가
            context.update({
                'channel': 'websocket',
                'real_time': True,
                'session_type': 'streaming'
            })
            
            # 추천 생성 (비동기)
            recommendations = await self.get_recommendations_async(
                self.user_id, num_recommendations, context, force_refresh
            )
            
            # 클라이언트에 전송
            await self.send(text_data=json.dumps({
                'type': 'recommendations',
                'data': recommendations,
                'timestamp': self._get_timestamp()
            }))
            
        except Exception as e:
            await self.send_error(f"Recommendation error: {str(e)}")
    
    async def handle_interaction(self, data):
        """상호작용 기록 처리"""
        
        try:
            product_id = data.get('product_id')
            interaction_type = data.get('interaction_type')
            value = data.get('value')
            
            if not product_id or not interaction_type:
                await self.send_error("Missing product_id or interaction_type")
                return
            
            # 상호작용 기록 (비동기)
            success = await self.record_interaction_async(
                self.user_id, product_id, interaction_type, value
            )
            
            if success:
                await self.send(text_data=json.dumps({
                    'type': 'interaction_recorded',
                    'product_id': product_id,
                    'interaction_type': interaction_type,
                    'timestamp': self._get_timestamp()
                }))
                
                # 실시간 추천 업데이트 트리거
                await self.trigger_recommendation_update()
            else:
                await self.send_error("Failed to record interaction")
                
        except Exception as e:
            await self.send_error(f"Interaction error: {str(e)}")
    
    async def handle_similar_products_request(self, data):
        """유사 상품 요청 처리"""
        
        try:
            product_id = data.get('product_id')
            num_items = data.get('num_items', 10)
            
            if not product_id:
                await self.send_error("Missing product_id")
                return
            
            # 유사 상품 조회 (비동기)
            similar_products = await self.get_similar_products_async(product_id, num_items)
            
            await self.send(text_data=json.dumps({
                'type': 'similar_products',
                'product_id': product_id,
                'data': similar_products,
                'timestamp': self._get_timestamp()
            }))
            
        except Exception as e:
            await self.send_error(f"Similar products error: {str(e)}")
    
    async def send_initial_recommendations(self):
        """초기 추천 전송"""
        
        try:
            recommendations = await self.get_recommendations_async(self.user_id, 10)
            
            await self.send(text_data=json.dumps({
                'type': 'initial_recommendations',
                'data': recommendations,
                'timestamp': self._get_timestamp()
            }))
            
        except Exception as e:
            logger.error(f"Initial recommendations error: {str(e)}")
    
    async def trigger_recommendation_update(self):
        """추천 업데이트 트리거"""
        
        try:
            # 짧은 지연 후 업데이트된 추천 전송
            await asyncio.sleep(1)
            
            recommendations = await self.get_recommendations_async(
                self.user_id, 10, {'real_time_update': True}, force_refresh=True
            )
            
            await self.send(text_data=json.dumps({
                'type': 'recommendations_updated',
                'data': recommendations,
                'timestamp': self._get_timestamp()
            }))
            
        except Exception as e:
            logger.error(f"Recommendation update error: {str(e)}")
    
    async def send_error(self, message):
        """에러 메시지 전송"""
        
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': self._get_timestamp()
        }))
    
    def _get_timestamp(self):
        """현재 타임스탬프 반환"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    # 비동기 데이터베이스 작업
    @database_sync_to_async
    def get_user(self, user_id):
        """사용자 조회"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_recommendations_async(self, user_id, num_recommendations, context=None, force_refresh=False):
        """비동기 추천 조회"""
        return self.recommendation_service.get_recommendations(
            user_id=user_id,
            num_recommendations=num_recommendations,
            context=context or {},
            force_refresh=force_refresh
        )
    
    @database_sync_to_async
    def record_interaction_async(self, user_id, product_id, interaction_type, value=None):
        """비동기 상호작용 기록"""
        return self.recommendation_service.update_user_interaction(
            user_id=user_id,
            product_id=product_id,
            interaction_type=interaction_type,
            value=value,
            context={'channel': 'websocket'}
        )
    
    @database_sync_to_async
    def get_similar_products_async(self, product_id, num_items):
        """비동기 유사 상품 조회"""
        return self.recommendation_service.get_similar_products(
            product_id=product_id,
            num_recommendations=num_items
        )
    
    # 그룹 메시지 핸들러
    async def recommendation_update(self, event):
        """그룹으로부터 추천 업데이트 메시지 수신"""
        
        await self.send(text_data=json.dumps({
            'type': 'recommendation_update',
            'data': event['data'],
            'timestamp': self._get_timestamp()
        }))

# WebSocket 라우팅 설정
# apps/recommendations/routing.py
from django.urls import re_path
from . import websocket

websocket_urlpatterns = [
    re_path(r'ws/recommendations/(?P<user_id>\d+)/$', websocket.RecommendationConsumer.as_asgi()),
]
```

### 6.3 성능 최적화 및 모니터링

```python
# apps/recommendations/monitoring.py
import time
import logging
from functools import wraps
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from typing import Dict, Any, Callable
import json

logger = logging.getLogger(__name__)

class RecommendationMetrics:
    """추천 시스템 메트릭 수집기"""
    
    def __init__(self):
        self.metrics_cache_prefix = "metrics_"
        self.metrics_ttl = 3600  # 1시간
    
    def record_api_call(self, endpoint: str, response_time: float, 
                       status_code: int, user_id: int = None):
        """API 호출 메트릭 기록"""
        
        try:
            # 메트릭 키 생성
            timestamp = int(time.time())
            minute_bucket = timestamp // 60  # 1분 단위 버킷
            
            metrics_key = f"{self.metrics_cache_prefix}api_{endpoint}_{minute_bucket}"
            
            # 기존 메트릭 조회
            current_metrics = cache.get(metrics_key, {
                'calls': 0,
                'total_response_time': 0,
                'status_codes': {},
                'unique_users': set()
            })
            
            # 메트릭 업데이트
            current_metrics['calls'] += 1
            current_metrics['total_response_time'] += response_time
            current_metrics['status_codes'][status_code] = (
                current_metrics['status_codes'].get(status_code, 0) + 1
            )
            
            if user_id:
                current_metrics['unique_users'].add(user_id)
            
            # 캐시 저장
            cache.set(metrics_key, current_metrics, self.metrics_ttl)
            
        except Exception as e:
            logger.error(f"Error recording API metrics: {str(e)}")
    
    def record_algorithm_performance(self, algorithm: str, execution_time: float, 
                                   user_id: int, num_results: int, cache_hit: bool):
        """알고리즘 성능 메트릭 기록"""
        
        try:
            timestamp = int(time.time())
            hour_bucket = timestamp // 3600  # 1시간 단위
            
            metrics_key = f"{self.metrics_cache_prefix}algo_{algorithm}_{hour_bucket}"
            
            current_metrics = cache.get(metrics_key, {
                'executions': 0,
                'total_execution_time': 0,
                'cache_hits': 0,
                'total_results': 0,
                'unique_users': set()
            })
            
            current_metrics['executions'] += 1
            current_metrics['total_execution_time'] += execution_time
            current_metrics['total_results'] += num_results
            current_metrics['unique_users'].add(user_id)
            
            if cache_hit:
                current_metrics['cache_hits'] += 1
            
            cache.set(metrics_key, current_metrics, self.metrics_ttl * 24)  # 24시간 보관
            
        except Exception as e:
            logger.error(f"Error recording algorithm metrics: {str(e)}")
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """성능 요약 조회"""
        
        try:
            current_time = int(time.time())
            summary = {
                'api_performance': {},
                'algorithm_performance': {},
                'system_health': {}
            }
            
            # API 성능 집계
            for hour_offset in range(hours):
                hour_bucket = (current_time - (hour_offset * 3600)) // 3600
                
                # API 메트릭 패턴으로 검색 (실제 구현에서는 Redis SCAN 등 사용)
                # 여기서는 간단한 예시
                pass
            
            # 시스템 상태 확인
            summary['system_health'] = self._check_system_health()
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {str(e)}")
            return {}
    
    def _check_system_health(self) -> Dict[str, Any]:
        """시스템 상태 확인"""
        
        health = {
            'database': 'unknown',
            'cache': 'unknown',
            'memory_usage': 0,
            'active_connections': 0
        }
        
        try:
            # 데이터베이스 상태
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                health['database'] = 'healthy'
        except:
            health['database'] = 'unhealthy'
        
        try:
            # 캐시 상태
            cache.set('health_test', 'ok', 10)
            health['cache'] = 'healthy' if cache.get('health_test') == 'ok' else 'unhealthy'
        except:
            health['cache'] = 'unhealthy'
        
        # 활성 연결 수
        health['active_connections'] = len(connection.queries)
        
        return health

# 메트릭 수집기 인스턴스
metrics = RecommendationMetrics()

def track_performance(endpoint_name: str):
    """성능 추적 데코레이터"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                status_code = 200
                
                # 사용자 ID 추출 시도
                user_id = None
                if args and hasattr(args[0], 'auth') and args[0].auth:
                    user_id = args[0].auth.id
                
                return result
                
            except Exception as e:
                status_code = 500
                raise
                
            finally:
                execution_time = (time.time() - start_time) * 1000  # ms
                
                # 메트릭 기록
                metrics.record_api_call(
                    endpoint=endpoint_name,
                    response_time=execution_time,
                    status_code=status_code,
                    user_id=user_id
                )
        
        return wrapper
    return decorator

def track_algorithm(algorithm_name: str):
    """알고리즘 성능 추적 데코레이터"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            result = func(*args, **kwargs)
            
            execution_time = (time.time() - start_time) * 1000  # ms
            
            # 결과에서 메트릭 정보 추출
            num_results = len(result) if isinstance(result, list) else 0
            cache_hit = kwargs.get('cache_hit', False)
            user_id = kwargs.get('user_id', 0)
            
            # 메트릭 기록
            metrics.record_algorithm_performance(
                algorithm=algorithm_name,
                execution_time=execution_time,
                user_id=user_id,
                num_results=num_results,
                cache_hit=cache_hit
            )
            
            return result
        
        return wrapper
    return decorator

class RecommendationProfiler:
    """추천 시스템 프로파일러"""
    
    def __init__(self):
        self.active_profiles = {}
    
    def start_profile(self, profile_id: str, context: Dict = None):
        """프로파일링 시작"""
        
        self.active_profiles[profile_id] = {
            'start_time': time.time(),
            'context': context or {},
            'steps': []
        }
    
    def add_step(self, profile_id: str, step_name: str, duration: float = None):
        """프로파일링 단계 추가"""
        
        if profile_id in self.active_profiles:
            step_time = time.time()
            
            self.active_profiles[profile_id]['steps'].append({
                'name': step_name,
                'timestamp': step_time,
                'duration': duration
            })
    
    def end_profile(self, profile_id: str) -> Dict[str, Any]:
        """프로파일링 종료"""
        
        if profile_id not in self.active_profiles:
            return {}
        
        profile = self.active_profiles.pop(profile_id)
        total_time = time.time() - profile['start_time']
        
        return {
            'profile_id': profile_id,
            'total_time_ms': total_time * 1000,
            'context': profile['context'],
            'steps': profile['steps'],
            'steps_count': len(profile['steps'])
        }

# 전역 프로파일러 인스턴스
profiler = RecommendationProfiler()

# 모니터링 미들웨어
class RecommendationMonitoringMiddleware:
    """추천 API 모니터링 미들웨어"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # 추천 API 경로 확인
        if '/recommendations/' in request.path:
            start_time = time.time()
            
            response = self.get_response(request)
            
            # 응답 시간 계산
            response_time = (time.time() - start_time) * 1000
            
            # 메트릭 기록
            endpoint = self._extract_endpoint(request.path)
            user_id = getattr(request.user, 'id', None) if hasattr(request, 'user') else None
            
            metrics.record_api_call(
                endpoint=endpoint,
                response_time=response_time,
                status_code=response.status_code,
                user_id=user_id
            )
            
            # 응답 헤더에 성능 정보 추가
            response['X-Response-Time'] = f"{response_time:.2f}ms"
            
            return response
        
        return self.get_response(request)
    
    def _extract_endpoint(self, path: str) -> str:
        """경로에서 엔드포인트명 추출"""
        
        if '/recommendations' in path and path.endswith('/recommendations'):
            return 'get_recommendations'
        elif '/interactions' in path:
            return 'record_interaction'
        elif '/similar' in path:
            return 'get_similar_products'
        elif '/explanation' in path:
            return 'get_explanation'
        else:
            return 'unknown'
```

---

## 📊 7. A/B 테스트 및 성능 분석