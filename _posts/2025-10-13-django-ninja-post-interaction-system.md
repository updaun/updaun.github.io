---
layout: post
title: "Django Ninja 게시물 상호작용 시스템: 조회수, 좋아요, 댓글 및 고급 정렬 구현 가이드"
date: 2025-10-13 10:00:00 +0900
categories: [Django, Django-Ninja, Python, Web Development]
tags: [Django, Django-Ninja, API, Backend, Database, ORM, Async, Performance]
author: "updaun"
image: "/assets/img/posts/2025-10-13-django-ninja-post-interaction-system.webp"
---

Django Ninja를 사용하여 현대적인 게시물 상호작용 시스템을 구현하는 방법을 알아보겠습니다. 조회수, 좋아요, 댓글 기능과 함께 인기순, 최신순, 업데이트순 정렬까지 완벽하게 구현해보겠습니다.

## 📊 시스템 개요

### 핵심 기능
- **조회수 시스템**: 중복 방지와 성능 최적화
- **좋아요 시스템**: 토글 기능과 실시간 카운트
- **댓글 시스템**: 계층형 댓글과 업데이트 추적
- **고급 정렬**: 다양한 기준의 동적 정렬

### 아키텍처 특징
- 비동기 처리로 성능 최적화
- Redis 캐싱으로 실시간 응답
- 데이터베이스 최적화된 쿼리
- RESTful API 설계

## 🏗️ 모델 설계

### 게시물 모델

```python
# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import F, Count, Avg
import uuid

class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    
    # 상호작용 필드
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    
    # 시간 필드
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_comment_at = models.DateTimeField(null=True, blank=True)
    
    # 정렬을 위한 계산 필드
    popularity_score = models.FloatField(default=0.0)  # 인기도 점수
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['-last_comment_at']),
            models.Index(fields=['-popularity_score']),
            models.Index(fields=['-view_count']),
            models.Index(fields=['-like_count']),
        ]
    
    def calculate_popularity_score(self):
        """인기도 점수 계산 (Reddit-style algorithm)"""
        import math
        from datetime import timedelta
        
        # 기본 점수 (좋아요 - 싫어요)
        score = self.like_count
        
        # 시간에 따른 가중치 (최근 게시물일수록 높은 점수)
        age_hours = (timezone.now() - self.created_at).total_seconds() / 3600
        time_decay = max(0, 1 - age_hours / (24 * 7))  # 1주일 후 0
        
        # 댓글과 조회수 가중치
        engagement_score = (self.comment_count * 2) + (self.view_count * 0.1)
        
        # 최종 점수 계산
        final_score = (score + engagement_score) * time_decay
        
        return max(0, final_score)
    
    def update_popularity_score(self):
        """인기도 점수 업데이트"""
        self.popularity_score = self.calculate_popularity_score()
        self.save(update_fields=['popularity_score'])

class PostView(models.Model):
    """조회수 중복 방지를 위한 모델"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['post', 'user'], ['post', 'ip_address']]
        indexes = [
            models.Index(fields=['post', 'viewed_at']),
        ]

class PostLike(models.Model):
    """좋아요 시스템"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['post', 'user']
        indexes = [
            models.Index(fields=['post', 'created_at']),
        ]

class Comment(models.Model):
    """댓글 시스템 (계층형 구조)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'created_at']),
            models.Index(fields=['parent']),
        ]
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        if is_new and not self.is_deleted:
            # 게시물의 댓글 수와 마지막 댓글 시간 업데이트
            self.post.comment_count = F('comment_count') + 1
            self.post.last_comment_at = self.created_at
            self.post.save(update_fields=['comment_count', 'last_comment_at'])
            
            # 인기도 점수 업데이트
            self.post.update_popularity_score()
```

## 🔧 Pydantic 스키마

```python
# schemas.py
from ninja import Schema
from pydantic import Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum

class SortOrder(str, Enum):
    LATEST = "latest"          # 최신순
    POPULAR = "popular"        # 인기순
    MOST_VIEWED = "most_viewed"  # 조회수순
    MOST_LIKED = "most_liked"    # 좋아요순
    RECENTLY_UPDATED = "recently_updated"  # 최근 업데이트순

class PostCreateSchema(Schema):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)

class PostUpdateSchema(Schema):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)

class CommentCreateSchema(Schema):
    content: str = Field(..., min_length=1)
    parent_id: Optional[str] = None

class CommentSchema(Schema):
    id: str
    content: str
    author: str
    created_at: datetime
    updated_at: datetime
    replies_count: int
    
    @staticmethod
    def resolve_author(obj):
        return obj.author.username
    
    @staticmethod
    def resolve_replies_count(obj):
        return obj.replies.filter(is_deleted=False).count()

class PostSchema(Schema):
    id: str
    title: str
    content: str
    author: str
    view_count: int
    like_count: int
    comment_count: int
    popularity_score: float
    created_at: datetime
    updated_at: datetime
    last_comment_at: Optional[datetime]
    is_liked: Optional[bool] = None  # 현재 사용자의 좋아요 여부
    
    @staticmethod
    def resolve_author(obj):
        return obj.author.username

class PostListSchema(Schema):
    id: str
    title: str
    author: str
    view_count: int
    like_count: int
    comment_count: int
    created_at: datetime
    last_comment_at: Optional[datetime]
    is_liked: Optional[bool] = None

class PostDetailSchema(PostSchema):
    comments: List[CommentSchema] = []

class PaginatedPostResponse(Schema):
    items: List[PostListSchema]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool

class PostStatsSchema(Schema):
    view_count: int
    like_count: int
    comment_count: int
    is_liked: bool
```

## 🚀 API 구현

### 서비스 레이어

```python
# services.py
from django.db import transaction
from django.db.models import F, Count, Q, Prefetch
from django.core.cache import cache
from django.contrib.auth.models import User
from django.utils import timezone
from typing import Optional, Tuple
import asyncio
from asgiref.sync import sync_to_async
from .models import Post, PostView, PostLike, Comment
from .schemas import SortOrder

class PostService:
    @staticmethod
    async def get_client_ip(request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    @sync_to_async
    def increment_view_count(post_id: str, user: Optional[User], ip_address: str) -> bool:
        """조회수 증가 (중복 방지)"""
        try:
            post = Post.objects.get(id=post_id)
            
            # 캐시 키로 중복 체크
            cache_key = f"post_view_{post_id}_{user.id if user else ip_address}"
            if cache.get(cache_key):
                return False
            
            with transaction.atomic():
                # 데이터베이스 레벨에서 중복 체크
                view_created = False
                if user:
                    _, view_created = PostView.objects.get_or_create(
                        post=post, user=user,
                        defaults={'ip_address': ip_address}
                    )
                else:
                    _, view_created = PostView.objects.get_or_create(
                        post=post, ip_address=ip_address
                    )
                
                if view_created:
                    # 조회수 증가
                    Post.objects.filter(id=post_id).update(
                        view_count=F('view_count') + 1
                    )
                    
                    # 캐시에 24시간 동안 저장
                    cache.set(cache_key, True, 86400)
                    
                    # 인기도 점수 업데이트
                    post.refresh_from_db()
                    post.update_popularity_score()
                    
                    return True
                    
        except Post.DoesNotExist:
            pass
        
        return False
    
    @staticmethod
    @sync_to_async
    def toggle_like(post_id: str, user: User) -> Tuple[bool, int]:
        """좋아요 토글"""
        try:
            post = Post.objects.get(id=post_id)
            
            with transaction.atomic():
                like, created = PostLike.objects.get_or_create(
                    post=post, user=user
                )
                
                if created:
                    # 좋아요 추가
                    Post.objects.filter(id=post_id).update(
                        like_count=F('like_count') + 1
                    )
                    is_liked = True
                else:
                    # 좋아요 제거
                    like.delete()
                    Post.objects.filter(id=post_id).update(
                        like_count=F('like_count') - 1
                    )
                    is_liked = False
                
                # 업데이트된 좋아요 수 가져오기
                post.refresh_from_db()
                like_count = post.like_count
                
                # 인기도 점수 업데이트
                post.update_popularity_score()
                
                return is_liked, like_count
                
        except Post.DoesNotExist:
            raise ValueError("Post not found")
    
    @staticmethod
    @sync_to_async
    def create_comment(post_id: str, user: User, content: str, parent_id: Optional[str] = None) -> Comment:
        """댓글 생성"""
        try:
            post = Post.objects.get(id=post_id)
            parent = None
            
            if parent_id:
                parent = Comment.objects.get(id=parent_id, post=post)
            
            with transaction.atomic():
                comment = Comment.objects.create(
                    post=post,
                    parent=parent,
                    author=user,
                    content=content
                )
                
                return comment
                
        except (Post.DoesNotExist, Comment.DoesNotExist):
            raise ValueError("Post or parent comment not found")
    
    @staticmethod
    def get_posts_queryset(sort_order: SortOrder, user: Optional[User] = None):
        """정렬된 게시물 쿼리셋"""
        queryset = Post.objects.select_related('author')
        
        # 사용자별 좋아요 정보 추가
        if user and user.is_authenticated:
            queryset = queryset.prefetch_related(
                Prefetch(
                    'likes',
                    queryset=PostLike.objects.filter(user=user),
                    to_attr='user_likes'
                )
            )
        
        # 정렬 적용
        if sort_order == SortOrder.LATEST:
            queryset = queryset.order_by('-created_at')
        elif sort_order == SortOrder.POPULAR:
            queryset = queryset.order_by('-popularity_score', '-created_at')
        elif sort_order == SortOrder.MOST_VIEWED:
            queryset = queryset.order_by('-view_count', '-created_at')
        elif sort_order == SortOrder.MOST_LIKED:
            queryset = queryset.order_by('-like_count', '-created_at')
        elif sort_order == SortOrder.RECENTLY_UPDATED:
            queryset = queryset.order_by('-last_comment_at', '-updated_at')
        
        return queryset
    
    @staticmethod
    def add_user_interaction_info(posts, user: Optional[User]):
        """게시물에 사용자 상호작용 정보 추가"""
        if not user or not user.is_authenticated:
            return posts
        
        for post in posts:
            # 좋아요 여부 확인
            post.is_liked = bool(getattr(post, 'user_likes', []))
        
        return posts

class CommentService:
    @staticmethod
    @sync_to_async
    def get_post_comments(post_id: str) -> List[Comment]:
        """게시물의 댓글 목록 (계층형)"""
        comments = Comment.objects.filter(
            post_id=post_id,
            is_deleted=False,
            parent__isnull=True  # 최상위 댓글만
        ).select_related('author').prefetch_related(
            Prefetch(
                'replies',
                queryset=Comment.objects.filter(is_deleted=False).select_related('author'),
                to_attr='reply_list'
            )
        ).order_by('created_at')
        
        return list(comments)
```

### API 엔드포인트

```python
# api.py
from ninja import Router, Query
from ninja.pagination import paginate, PageNumberPagination
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from typing import List
import asyncio

from .models import Post, Comment
from .schemas import *
from .services import PostService, CommentService

router = Router()

@router.get("/posts", response=PaginatedPostResponse)
@paginate(PageNumberPagination, page_size=20)
async def list_posts(
    request,
    sort: SortOrder = Query(SortOrder.LATEST, description="정렬 기준"),
):
    """게시물 목록 조회"""
    user = request.user if hasattr(request, 'user') else None
    
    # 쿼리셋 생성
    queryset = PostService.get_posts_queryset(sort, user)
    
    # 동기 함수를 비동기로 실행
    posts = await asyncio.get_event_loop().run_in_executor(
        None, lambda: list(queryset)
    )
    
    # 사용자 상호작용 정보 추가
    posts = PostService.add_user_interaction_info(posts, user)
    
    return posts

@router.get("/posts/{post_id}", response=PostDetailSchema)
async def get_post(request, post_id: str):
    """게시물 상세 조회"""
    user = request.user if hasattr(request, 'user') else None
    
    # 게시물 조회
    post = await asyncio.get_event_loop().run_in_executor(
        None, lambda: get_object_or_404(
            Post.objects.select_related('author'), 
            id=post_id
        )
    )
    
    # 조회수 증가
    ip_address = await PostService.get_client_ip(request)
    await PostService.increment_view_count(post_id, user, ip_address)
    
    # 댓글 목록 조회
    comments = await CommentService.get_post_comments(post_id)
    
    # 사용자 좋아요 정보 추가
    if user and user.is_authenticated:
        post.is_liked = await asyncio.get_event_loop().run_in_executor(
            None, lambda: post.likes.filter(user=user).exists()
        )
    
    # 응답 데이터 구성
    post_data = PostDetailSchema.from_orm(post)
    post_data.comments = [CommentSchema.from_orm(comment) for comment in comments]
    
    return post_data

@router.post("/posts", response=PostSchema)
async def create_post(request, data: PostCreateSchema):
    """게시물 생성"""
    user = request.user
    
    post = await asyncio.get_event_loop().run_in_executor(
        None, lambda: Post.objects.create(
            title=data.title,
            content=data.content,
            author=user
        )
    )
    
    return PostSchema.from_orm(post)

@router.put("/posts/{post_id}", response=PostSchema)
async def update_post(request, post_id: str, data: PostUpdateSchema):
    """게시물 수정"""
    user = request.user
    
    post = await asyncio.get_event_loop().run_in_executor(
        None, lambda: get_object_or_404(Post, id=post_id, author=user)
    )
    
    # 수정 내용 적용
    update_fields = []
    if data.title is not None:
        post.title = data.title
        update_fields.append('title')
    if data.content is not None:
        post.content = data.content
        update_fields.append('content')
    
    if update_fields:
        update_fields.append('updated_at')
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: post.save(update_fields=update_fields)
        )
    
    return PostSchema.from_orm(post)

@router.post("/posts/{post_id}/like", response=PostStatsSchema)
async def toggle_post_like(request, post_id: str):
    """게시물 좋아요 토글"""
    user = request.user
    
    try:
        is_liked, like_count = await PostService.toggle_like(post_id, user)
        
        # 현재 게시물 정보 조회
        post = await asyncio.get_event_loop().run_in_executor(
            None, lambda: get_object_or_404(Post, id=post_id)
        )
        
        return PostStatsSchema(
            view_count=post.view_count,
            like_count=like_count,
            comment_count=post.comment_count,
            is_liked=is_liked
        )
    except ValueError as e:
        return {"error": str(e)}, 404

@router.post("/posts/{post_id}/comments", response=CommentSchema)
async def create_comment(request, post_id: str, data: CommentCreateSchema):
    """댓글 생성"""
    user = request.user
    
    try:
        comment = await PostService.create_comment(
            post_id, user, data.content, data.parent_id
        )
        return CommentSchema.from_orm(comment)
    except ValueError as e:
        return {"error": str(e)}, 404

@router.get("/posts/{post_id}/comments", response=List[CommentSchema])
async def get_post_comments(request, post_id: str):
    """게시물 댓글 목록"""
    comments = await CommentService.get_post_comments(post_id)
    return [CommentSchema.from_orm(comment) for comment in comments]

@router.get("/posts/{post_id}/stats", response=PostStatsSchema)
async def get_post_stats(request, post_id: str):
    """게시물 통계 정보"""
    user = request.user
    
    post = await asyncio.get_event_loop().run_in_executor(
        None, lambda: get_object_or_404(Post, id=post_id)
    )
    
    is_liked = False
    if user and user.is_authenticated:
        is_liked = await asyncio.get_event_loop().run_in_executor(
            None, lambda: post.likes.filter(user=user).exists()
        )
    
    return PostStatsSchema(
        view_count=post.view_count,
        like_count=post.like_count,
        comment_count=post.comment_count,
        is_liked=is_liked
    )
```

## ⚡ 성능 최적화

### 1. 캐싱 전략

```python
# cache.py
from django.core.cache import cache
from django.conf import settings
import json

class PostCacheManager:
    @staticmethod
    def get_post_cache_key(post_id: str, user_id: str = None) -> str:
        """게시물 캐시 키 생성"""
        return f"post:{post_id}:{user_id or 'anonymous'}"
    
    @staticmethod
    def get_posts_list_cache_key(sort_order: str, page: int, user_id: str = None) -> str:
        """게시물 목록 캐시 키 생성"""
        return f"posts_list:{sort_order}:{page}:{user_id or 'anonymous'}"
    
    @staticmethod
    def cache_post(post_id: str, post_data: dict, user_id: str = None, timeout: int = 300):
        """게시물 캐시 저장"""
        cache_key = PostCacheManager.get_post_cache_key(post_id, user_id)
        cache.set(cache_key, json.dumps(post_data), timeout)
    
    @staticmethod
    def get_cached_post(post_id: str, user_id: str = None) -> dict:
        """캐시된 게시물 조회"""
        cache_key = PostCacheManager.get_post_cache_key(post_id, user_id)
        cached_data = cache.get(cache_key)
        return json.loads(cached_data) if cached_data else None
    
    @staticmethod
    def invalidate_post_cache(post_id: str):
        """게시물 캐시 무효화"""
        # 모든 사용자의 캐시 무효화는 비효율적이므로
        # 버전 기반 캐시 무효화 사용
        cache.delete_many([
            f"post:{post_id}:*",
            "posts_list:*"
        ])
```

### 2. 데이터베이스 최적화

```python
# optimization.py
from django.db.models import Count, Avg, F, Q, Case, When, IntegerField
from django.db.models.functions import Coalesce
from datetime import timedelta
from django.utils import timezone

class PostQueryOptimizer:
    @staticmethod
    def get_optimized_posts_queryset(sort_order: str, user=None):
        """최적화된 게시물 쿼리셋"""
        queryset = Post.objects.select_related('author').annotate(
            # 댓글 수 계산 (실시간)
            actual_comment_count=Count('comments', filter=Q(comments__is_deleted=False)),
            # 좋아요 수 계산 (실시간)
            actual_like_count=Count('likes'),
            # 최근 활동 점수
            recent_activity_score=Case(
                When(
                    last_comment_at__gte=timezone.now() - timedelta(days=1),
                    then=F('comment_count') * 10
                ),
                When(
                    last_comment_at__gte=timezone.now() - timedelta(days=7),
                    then=F('comment_count') * 5
                ),
                default=F('comment_count'),
                output_field=IntegerField()
            )
        )
        
        # 사용자별 좋아요 정보 (서브쿼리 사용)
        if user and user.is_authenticated:
            queryset = queryset.annotate(
                user_liked=Count(
                    'likes', 
                    filter=Q(likes__user=user)
                )
            )
        
        return queryset
    
    @staticmethod
    def get_trending_posts(hours: int = 24):
        """트렌딩 게시물 (지정된 시간 내 인기 게시물)"""
        time_threshold = timezone.now() - timedelta(hours=hours)
        
        return Post.objects.filter(
            created_at__gte=time_threshold
        ).annotate(
            trend_score=F('like_count') * 3 + F('comment_count') * 2 + F('view_count') * 0.1
        ).order_by('-trend_score')[:10]

    @staticmethod
    def bulk_update_popularity_scores():
        """인기도 점수 일괄 업데이트 (Celery 작업용)"""
        posts = Post.objects.all()
        
        for post in posts:
            post.popularity_score = post.calculate_popularity_score()
        
        Post.objects.bulk_update(posts, ['popularity_score'])
```

### 3. Celery 비동기 작업

```python
# tasks.py
from celery import shared_task
from django.db.models import F
from .models import Post
from .optimization import PostQueryOptimizer

@shared_task
def update_popularity_scores():
    """인기도 점수 정기 업데이트"""
    PostQueryOptimizer.bulk_update_popularity_scores()
    return "Popularity scores updated"

@shared_task
def update_post_stats(post_id: str):
    """게시물 통계 업데이트"""
    try:
        post = Post.objects.get(id=post_id)
        
        # 실제 카운트와 동기화
        actual_comment_count = post.comments.filter(is_deleted=False).count()
        actual_like_count = post.likes.count()
        
        post.comment_count = actual_comment_count
        post.like_count = actual_like_count
        post.save(update_fields=['comment_count', 'like_count'])
        
        # 인기도 점수 업데이트
        post.update_popularity_score()
        
    except Post.DoesNotExist:
        pass

@shared_task
def cleanup_old_views():
    """오래된 조회 기록 정리"""
    from datetime import timedelta
    from django.utils import timezone
    from .models import PostView
    
    # 30일 이전 조회 기록 삭제
    cutoff_date = timezone.now() - timedelta(days=30)
    PostView.objects.filter(viewed_at__lt=cutoff_date).delete()
```

## 📱 프론트엔드 통합

### JavaScript 클라이언트 예제

```javascript
// post-client.js
class PostAPIClient {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
    }
    
    async getPosts(sortOrder = 'latest', page = 1) {
        const response = await fetch(
            `${this.baseURL}/posts?sort=${sortOrder}&page=${page}`
        );
        return response.json();
    }
    
    async getPost(postId) {
        const response = await fetch(`${this.baseURL}/posts/${postId}`);
        return response.json();
    }
    
    async toggleLike(postId) {
        const response = await fetch(`${this.baseURL}/posts/${postId}/like`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            }
        });
        return response.json();
    }
    
    async addComment(postId, content, parentId = null) {
        const response = await fetch(`${this.baseURL}/posts/${postId}/comments`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                content: content,
                parent_id: parentId
            })
        });
        return response.json();
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
}

// 사용 예제
const postClient = new PostAPIClient();

// 좋아요 토글
document.addEventListener('click', async (e) => {
    if (e.target.classList.contains('like-button')) {
        const postId = e.target.dataset.postId;
        const result = await postClient.toggleLike(postId);
        
        // UI 업데이트
        e.target.textContent = result.is_liked ? '❤️' : '🤍';
        e.target.parentElement.querySelector('.like-count').textContent = result.like_count;
    }
});

// 정렬 변경
document.querySelector('#sort-select').addEventListener('change', async (e) => {
    const sortOrder = e.target.value;
    const posts = await postClient.getPosts(sortOrder);
    updatePostsList(posts);
});
```

## 🧪 테스트 코드

```python
# tests.py
import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from .models import Post, PostLike, Comment
from .services import PostService

class PostInteractionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        self.post = Post.objects.create(
            title='Test Post',
            content='Test content',
            author=self.user
        )
    
    def test_post_creation(self):
        """게시물 생성 테스트"""
        data = {
            'title': 'New Post',
            'content': 'New content'
        }
        response = self.client.post('/api/posts', data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Post.objects.count(), 2)
    
    def test_like_toggle(self):
        """좋아요 토글 테스트"""
        # 좋아요 추가
        response = self.client.post(f'/api/posts/{self.post.id}/like')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['is_liked'])
        
        # 좋아요 제거
        response = self.client.post(f'/api/posts/{self.post.id}/like')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_liked'])
    
    def test_comment_creation(self):
        """댓글 생성 테스트"""
        data = {'content': 'Test comment'}
        response = self.client.post(f'/api/posts/{self.post.id}/comments', data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Comment.objects.count(), 1)
    
    def test_view_count_increment(self):
        """조회수 증가 테스트"""
        initial_views = self.post.view_count
        response = self.client.get(f'/api/posts/{self.post.id}')
        self.assertEqual(response.status_code, 200)
        
        self.post.refresh_from_db()
        self.assertEqual(self.post.view_count, initial_views + 1)
    
    def test_sorting(self):
        """정렬 기능 테스트"""
        # 추가 게시물 생성
        post2 = Post.objects.create(
            title='Popular Post',
            content='Popular content',
            author=self.user,
            like_count=10,
            view_count=100
        )
        
        # 인기순 정렬 테스트
        response = self.client.get('/api/posts?sort=popular')
        posts = response.json()['items']
        self.assertEqual(posts[0]['id'], str(post2.id))

@pytest.mark.asyncio
class AsyncPostServiceTest:
    async def test_async_like_toggle(self):
        """비동기 좋아요 토글 테스트"""
        user = User.objects.create_user(username='testuser', password='test')
        post = Post.objects.create(title='Test', content='Test', author=user)
        
        # 좋아요 추가
        is_liked, like_count = await PostService.toggle_like(str(post.id), user)
        assert is_liked is True
        assert like_count == 1
        
        # 좋아요 제거
        is_liked, like_count = await PostService.toggle_like(str(post.id), user)
        assert is_liked is False
        assert like_count == 0
```

## 🔧 설정 및 배포

### settings.py 추가 설정

```python
# settings.py 추가 설정

# 캐시 설정
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Celery 설정
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'
CELERY_BEAT_SCHEDULE = {
    'update-popularity-scores': {
        'task': 'posts.tasks.update_popularity_scores',
        'schedule': 300.0,  # 5분마다 실행
    },
    'cleanup-old-views': {
        'task': 'posts.tasks.cleanup_old_views',
        'schedule': 86400.0,  # 24시간마다 실행
    },
}

# 데이터베이스 인덱스 최적화
DATABASE_CONNECTION_POOL_SIZE = 20
DATABASE_CONNECTION_MAX_AGE = 300
```

### Docker 배포 설정

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "project.asgi:application"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://user:pass@db:5432/dbname
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: dbname
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
  
  celery:
    build: .
    command: celery -A project worker -l info
    depends_on:
      - db
      - redis
  
  celery-beat:
    build: .
    command: celery -A project beat -l info
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
```

## 📈 모니터링 및 분석

```python
# monitoring.py
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class PostAnalytics:
    @staticmethod
    def get_engagement_metrics(days: int = 7):
        """참여도 지표 분석"""
        since = timezone.now() - timedelta(days=days)
        
        metrics = {
            'total_posts': Post.objects.filter(created_at__gte=since).count(),
            'total_views': Post.objects.filter(created_at__gte=since).aggregate(
                total=models.Sum('view_count')
            )['total'] or 0,
            'total_likes': Post.objects.filter(created_at__gte=since).aggregate(
                total=models.Sum('like_count')
            )['total'] or 0,
            'total_comments': Comment.objects.filter(
                created_at__gte=since,
                is_deleted=False
            ).count(),
            'avg_engagement': Post.objects.filter(created_at__gte=since).aggregate(
                avg=Avg(
                    models.F('view_count') + 
                    models.F('like_count') * 10 + 
                    models.F('comment_count') * 5
                )
            )['avg'] or 0
        }
        
        logger.info(f"Engagement metrics for last {days} days: {metrics}")
        return metrics
    
    @staticmethod
    def get_top_performing_posts(limit: int = 10):
        """상위 성과 게시물"""
        return Post.objects.annotate(
            engagement_score=models.F('view_count') + 
                           models.F('like_count') * 10 + 
                           models.F('comment_count') * 5
        ).order_by('-engagement_score')[:limit]
```

## 🎯 마무리

이번 포스트에서는 Django Ninja를 사용하여 완전한 게시물 상호작용 시스템을 구현하는 방법을 알아봤습니다. 주요 특징들을 정리하면:

### ✅ 구현된 기능
- **조회수 시스템**: 중복 방지와 IP/사용자 기반 추적
- **좋아요 시스템**: 실시간 토글과 카운트 업데이트
- **댓글 시스템**: 계층형 구조와 업데이트 추적
- **고급 정렬**: 인기순, 최신순, 업데이트순 등

### 🚀 성능 최적화
- Redis 캐싱으로 중복 조회 방지
- 데이터베이스 인덱스 최적화
- 비동기 처리로 응답 속도 향상
- Celery를 통한 백그라운드 작업

### 🔧 확장성 고려사항
- 마이크로서비스 아키텍처 준비
- 수평 확장 가능한 설계
- 모니터링과 분석 기능 내장
- Docker를 통한 컨테이너 배포

이 시스템을 기반으로 더욱 복잡한 소셜 기능들을 추가할 수 있으며, 실제 프로덕션 환경에서도 안정적으로 동작할 수 있습니다.

> 💡 **다음 단계**: 실시간 알림 시스템, 추천 알고리즘, 콘텐츠 검색 기능 등을 추가하여 더욱 완성도 높은 플랫폼을 만들어보세요!