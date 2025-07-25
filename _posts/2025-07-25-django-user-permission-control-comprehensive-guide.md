---
layout: post
title: "Django User 권한 제어 완벽 가이드: django-ninja 데코레이터와 동기/비동기 방식"
date: 2025-07-25 10:00:00 +0900
categories: [Django, Python, Web Development, API]
tags: [Django, Python, Django-Ninja, Authentication, Authorization, Permission, Decorator, Async, API]
---

Django에서 사용자 권한을 제어하는 것은 웹 애플리케이션 보안의 핵심입니다. 이 글에서는 Django의 기본 권한 시스템부터 django-ninja를 활용한 API 권한 제어까지, 동기와 비동기 방식을 모두 포함하여 완벽하게 다루어보겠습니다.

## 📊 Django 권한 시스템 개요

### 1. Django 기본 권한 구조

Django는 다음과 같은 권한 구조를 제공합니다:

```python
# models.py
from django.contrib.auth.models import User, Permission, Group
from django.contrib.contenttypes.models import ContentType

# 기본 권한 종류
# - add_<modelname>: 모델 생성 권한
# - change_<modelname>: 모델 수정 권한  
# - delete_<modelname>: 모델 삭제 권한
# - view_<modelname>: 모델 조회 권한
```

### 2. 커스텀 권한 정의

```python
# models.py
from django.db import models
from django.contrib.auth.models import User

class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        permissions = [
            ("can_publish", "Can publish article"),
            ("can_feature", "Can feature article"),
            ("can_moderate", "Can moderate comments"),
        ]
```

## 🛡️ Django 기본 권한 제어 방법

### 1. 함수 기반 뷰 (FBV) 권한 제어

```python
# views.py
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404

@login_required
def profile_view(request):
    """로그인된 사용자만 접근 가능"""
    return render(request, 'profile.html')

@permission_required('blog.add_article')
def create_article(request):
    """Article 생성 권한이 있는 사용자만 접근 가능"""
    if request.method == 'POST':
        # 게시글 생성 로직
        pass
    return render(request, 'create_article.html')

@permission_required(['blog.change_article', 'blog.can_publish'])
def publish_article(request, article_id):
    """여러 권한을 동시에 요구"""
    article = get_object_or_404(Article, id=article_id)
    # 발행 로직
    return render(request, 'article_published.html')

def is_article_author(user):
    """커스텀 권한 확인 함수"""
    def check_author(request, article_id):
        article = get_object_or_404(Article, id=article_id)
        return article.author == user
    return check_author

@user_passes_test(lambda user: user.is_staff)
def admin_only_view(request):
    """스태프만 접근 가능"""
    return render(request, 'admin_dashboard.html')
```

### 2. 클래스 기반 뷰 (CBV) 권한 제어

```python
# views.py
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView

class ArticleListView(LoginRequiredMixin, ListView):
    """로그인된 사용자만 게시글 목록 조회 가능"""
    model = Article
    template_name = 'article_list.html'
    login_url = '/login/'

class ArticleCreateView(PermissionRequiredMixin, CreateView):
    """게시글 생성 권한이 있는 사용자만 접근"""
    model = Article
    fields = ['title', 'content']
    permission_required = 'blog.add_article'
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

class ArticleUpdateView(UserPassesTestMixin, UpdateView):
    """게시글 작성자만 수정 가능"""
    model = Article
    fields = ['title', 'content']
    
    def test_func(self):
        article = self.get_object()
        return self.request.user == article.author

class StaffOnlyView(UserPassesTestMixin, ListView):
    """스태프만 접근 가능한 뷰"""
    model = Article
    
    def test_func(self):
        return self.request.user.is_staff
```

## 🚀 Django-Ninja API 권한 제어

### 1. 기본 인증 설정

```python
# auth.py
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from ninja.security import HttpBearer
from ninja import NinjaAPI
from typing import Optional

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            # JWT 토큰 검증 또는 세션 기반 인증
            user = User.objects.get(auth_token=token)
            return user
        except User.DoesNotExist:
            return None

# API 인스턴스 생성
api = NinjaAPI(auth=AuthBearer())
```

### 2. 동기 방식 권한 데코레이터

```python
# decorators.py
from functools import wraps
from ninja.errors import HttpError
from django.contrib.auth.models import Permission
from typing import List, Callable, Any

def require_permissions(*permission_codes: str):
    """권한 확인 데코레이터 (동기 방식)"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.auth
            if not user or not user.is_authenticated:
                raise HttpError(401, "Authentication required")
            
            # 권한 확인
            for perm_code in permission_codes:
                if not user.has_perm(perm_code):
                    raise HttpError(403, f"Permission denied: {perm_code}")
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

def require_staff(func: Callable) -> Callable:
    """스태프 권한 확인 데코레이터"""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.auth
        if not user or not user.is_staff:
            raise HttpError(403, "Staff permission required")
        return func(request, *args, **kwargs)
    return wrapper

def require_superuser(func: Callable) -> Callable:
    """슈퍼유저 권한 확인 데코레이터"""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.auth
        if not user or not user.is_superuser:
            raise HttpError(403, "Superuser permission required")
        return func(request, *args, **kwargs)
    return wrapper

def require_owner_or_staff(model_class, id_field: str = 'id'):
    """소유자 또는 스태프만 접근 가능한 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.auth
            if not user or not user.is_authenticated:
                raise HttpError(401, "Authentication required")
            
            # 스태프는 무조건 허용
            if user.is_staff:
                return func(request, *args, **kwargs)
            
            # 객체 소유자 확인
            object_id = kwargs.get(id_field)
            if object_id:
                try:
                    obj = model_class.objects.get(id=object_id)
                    if hasattr(obj, 'author') and obj.author == user:
                        return func(request, *args, **kwargs)
                    elif hasattr(obj, 'user') and obj.user == user:
                        return func(request, *args, **kwargs)
                except model_class.DoesNotExist:
                    raise HttpError(404, "Object not found")
            
            raise HttpError(403, "Permission denied")
        return wrapper
    return decorator
```

### 3. 비동기 방식 권한 데코레이터

```python
# async_decorators.py
import asyncio
from functools import wraps
from ninja.errors import HttpError
from django.contrib.auth.models import User
from asgiref.sync import sync_to_async
from typing import Callable, Any

def async_require_permissions(*permission_codes: str):
    """비동기 권한 확인 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            user = request.auth
            if not user or not user.is_authenticated:
                raise HttpError(401, "Authentication required")
            
            # 비동기 권한 확인
            for perm_code in permission_codes:
                has_permission = await sync_to_async(user.has_perm)(perm_code)
                if not has_permission:
                    raise HttpError(403, f"Permission denied: {perm_code}")
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def async_require_staff(func: Callable) -> Callable:
    """비동기 스태프 권한 확인 데코레이터"""
    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        user = request.auth
        if not user or not user.is_staff:
            raise HttpError(403, "Staff permission required")
        return await func(request, *args, **kwargs)
    return wrapper

def async_require_owner_or_staff(model_class, id_field: str = 'id'):
    """비동기 소유자 또는 스태프 권한 확인 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            user = request.auth
            if not user or not user.is_authenticated:
                raise HttpError(401, "Authentication required")
            
            # 스태프는 무조건 허용
            if user.is_staff:
                return await func(request, *args, **kwargs)
            
            # 비동기 객체 소유자 확인
            object_id = kwargs.get(id_field)
            if object_id:
                try:
                    obj = await sync_to_async(model_class.objects.get)(id=object_id)
                    if hasattr(obj, 'author') and obj.author == user:
                        return await func(request, *args, **kwargs)
                    elif hasattr(obj, 'user') and obj.user == user:
                        return await func(request, *args, **kwargs)
                except model_class.DoesNotExist:
                    raise HttpError(404, "Object not found")
            
            raise HttpError(403, "Permission denied")
        return wrapper
    return decorator

def async_rate_limit(max_requests: int, time_window: int = 60):
    """비동기 요청 제한 데코레이터"""
    request_counts = {}
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            user = request.auth
            if not user:
                raise HttpError(401, "Authentication required")
            
            import time
            current_time = time.time()
            user_id = user.id
            
            # 요청 기록 정리 (시간 윈도우 초과 항목 제거)
            if user_id in request_counts:
                request_counts[user_id] = [
                    timestamp for timestamp in request_counts[user_id]
                    if current_time - timestamp < time_window
                ]
            else:
                request_counts[user_id] = []
            
            # 요청 제한 확인
            if len(request_counts[user_id]) >= max_requests:
                raise HttpError(429, "Rate limit exceeded")
            
            # 현재 요청 기록
            request_counts[user_id].append(current_time)
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
```

## 🔧 Django-Ninja API 엔드포인트 구현

### 1. 동기 방식 API 엔드포인트

```python
# api.py
from ninja import NinjaAPI, Schema
from django.shortcuts import get_object_or_404
from typing import List
from .models import Article
from .decorators import require_permissions, require_staff, require_owner_or_staff

api = NinjaAPI()

class ArticleSchema(Schema):
    id: int
    title: str
    content: str
    author_id: int

class ArticleCreateSchema(Schema):
    title: str
    content: str

@api.get("/articles", response=List[ArticleSchema])
@require_permissions("blog.view_article")
def list_articles(request):
    """게시글 목록 조회 (view 권한 필요)"""
    articles = Article.objects.all()
    return articles

@api.post("/articles", response=ArticleSchema)
@require_permissions("blog.add_article")
def create_article(request, data: ArticleCreateSchema):
    """게시글 생성 (add 권한 필요)"""
    article = Article.objects.create(
        title=data.title,
        content=data.content,
        author=request.auth
    )
    return article

@api.put("/articles/{article_id}", response=ArticleSchema)
@require_owner_or_staff(Article, 'article_id')
def update_article(request, article_id: int, data: ArticleCreateSchema):
    """게시글 수정 (소유자 또는 스태프만 가능)"""
    article = get_object_or_404(Article, id=article_id)
    article.title = data.title
    article.content = data.content
    article.save()
    return article

@api.delete("/articles/{article_id}")
@require_permissions("blog.delete_article")
def delete_article(request, article_id: int):
    """게시글 삭제 (delete 권한 필요)"""
    article = get_object_or_404(Article, id=article_id)
    article.delete()
    return {"success": True}

@api.get("/admin/articles", response=List[ArticleSchema])
@require_staff
def admin_list_articles(request):
    """관리자용 게시글 목록 (스태프만 접근 가능)"""
    articles = Article.objects.all().select_related('author')
    return articles

@api.post("/articles/{article_id}/publish")
@require_permissions("blog.can_publish")
def publish_article(request, article_id: int):
    """게시글 발행 (커스텀 권한 필요)"""
    article = get_object_or_404(Article, id=article_id)
    article.is_published = True
    article.save()
    return {"success": True, "message": "Article published"}
```

### 2. 비동기 방식 API 엔드포인트

```python
# async_api.py
from ninja import NinjaAPI, Schema
from asgiref.sync import sync_to_async
from typing import List
from .models import Article
from .async_decorators import async_require_permissions, async_require_staff
from .async_decorators import async_require_owner_or_staff, async_rate_limit

async_api = NinjaAPI()

@async_api.get("/articles", response=List[ArticleSchema])
@async_require_permissions("blog.view_article")
@async_rate_limit(max_requests=100, time_window=60)  # 분당 100회 제한
async def async_list_articles(request):
    """비동기 게시글 목록 조회"""
    articles = await sync_to_async(list)(
        Article.objects.all().select_related('author')
    )
    return articles

@async_api.post("/articles", response=ArticleSchema)
@async_require_permissions("blog.add_article")
@async_rate_limit(max_requests=10, time_window=60)  # 분당 10회 제한
async def async_create_article(request, data: ArticleCreateSchema):
    """비동기 게시글 생성"""
    article = await sync_to_async(Article.objects.create)(
        title=data.title,
        content=data.content,
        author=request.auth
    )
    return article

@async_api.put("/articles/{article_id}", response=ArticleSchema)
@async_require_owner_or_staff(Article, 'article_id')
async def async_update_article(request, article_id: int, data: ArticleCreateSchema):
    """비동기 게시글 수정"""
    try:
        article = await sync_to_async(Article.objects.get)(id=article_id)
    except Article.DoesNotExist:
        raise HttpError(404, "Article not found")
    
    article.title = data.title
    article.content = data.content
    await sync_to_async(article.save)()
    return article

@async_api.delete("/articles/{article_id}")
@async_require_permissions("blog.delete_article")
async def async_delete_article(request, article_id: int):
    """비동기 게시글 삭제"""
    try:
        article = await sync_to_async(Article.objects.get)(id=article_id)
        await sync_to_async(article.delete)()
        return {"success": True}
    except Article.DoesNotExist:
        raise HttpError(404, "Article not found")

@async_api.get("/admin/statistics")
@async_require_staff
@async_rate_limit(max_requests=50, time_window=60)
async def async_admin_statistics(request):
    """비동기 관리자 통계 (스태프만 접근)"""
    total_articles = await sync_to_async(Article.objects.count)()
    published_articles = await sync_to_async(
        Article.objects.filter(is_published=True).count
    )()
    
    return {
        "total_articles": total_articles,
        "published_articles": published_articles,
        "draft_articles": total_articles - published_articles
    }
```

## 🔐 고급 권한 제어 패턴

### 1. 역할 기반 액세스 제어 (RBAC)

```python
# rbac.py
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from functools import wraps
from ninja.errors import HttpError

class RoleManager:
    """역할 기반 권한 관리 클래스"""
    
    @staticmethod
    def create_roles():
        """기본 역할들 생성"""
        # 에디터 역할
        editor_group, created = Group.objects.get_or_create(name='Editor')
        if created:
            editor_permissions = [
                'blog.add_article',
                'blog.change_article',
                'blog.view_article',
            ]
            for perm_code in editor_permissions:
                app_label, codename = perm_code.split('.')
                permission = Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename
                )
                editor_group.permissions.add(permission)
        
        # 모더레이터 역할
        moderator_group, created = Group.objects.get_or_create(name='Moderator')
        if created:
            moderator_permissions = [
                'blog.add_article',
                'blog.change_article',
                'blog.delete_article',
                'blog.view_article',
                'blog.can_moderate',
            ]
            for perm_code in moderator_permissions:
                app_label, codename = perm_code.split('.')
                permission = Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename
                )
                moderator_group.permissions.add(permission)
        
        # 퍼블리셔 역할
        publisher_group, created = Group.objects.get_or_create(name='Publisher')
        if created:
            publisher_permissions = [
                'blog.add_article',
                'blog.change_article',
                'blog.view_article',
                'blog.can_publish',
                'blog.can_feature',
            ]
            for perm_code in publisher_permissions:
                app_label, codename = perm_code.split('.')
                permission = Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename
                )
                publisher_group.permissions.add(permission)

def require_role(*role_names: str):
    """역할 기반 권한 확인 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.auth
            if not user or not user.is_authenticated:
                raise HttpError(401, "Authentication required")
            
            user_groups = user.groups.values_list('name', flat=True)
            
            # 슈퍼유저는 모든 역할 허용
            if user.is_superuser:
                return func(request, *args, **kwargs)
            
            # 요구되는 역할 중 하나라도 있으면 허용
            if any(role in user_groups for role in role_names):
                return func(request, *args, **kwargs)
            
            raise HttpError(403, f"Required roles: {', '.join(role_names)}")
        return wrapper
    return decorator

# 사용 예시
@api.post("/articles/{article_id}/moderate")
@require_role("Moderator", "Publisher")
def moderate_article(request, article_id: int):
    """모더레이터 또는 퍼블리셔만 접근 가능"""
    article = get_object_or_404(Article, id=article_id)
    # 모더레이션 로직
    return {"success": True}
```

### 2. 객체 수준 권한 제어

```python
# object_permissions.py
from django.contrib.auth.models import User
from ninja.errors import HttpError
from functools import wraps

class ObjectPermissionChecker:
    """객체 수준 권한 확인 클래스"""
    
    @staticmethod
    def can_edit_article(user: User, article: Article) -> bool:
        """게시글 편집 권한 확인"""
        if user.is_superuser:
            return True
        if user == article.author:
            return True
        if user.groups.filter(name__in=['Moderator', 'Publisher']).exists():
            return True
        return False
    
    @staticmethod
    def can_delete_article(user: User, article: Article) -> bool:
        """게시글 삭제 권한 확인"""
        if user.is_superuser:
            return True
        if user == article.author and user.has_perm('blog.delete_article'):
            return True
        if user.groups.filter(name='Moderator').exists():
            return True
        return False
    
    @staticmethod
    def can_publish_article(user: User, article: Article) -> bool:
        """게시글 발행 권한 확인"""
        if user.is_superuser:
            return True
        if user.groups.filter(name='Publisher').exists():
            return True
        return False

def check_object_permission(permission_func, model_class, id_field='id'):
    """객체 수준 권한 확인 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.auth
            if not user or not user.is_authenticated:
                raise HttpError(401, "Authentication required")
            
            object_id = kwargs.get(id_field)
            if object_id:
                try:
                    obj = model_class.objects.get(id=object_id)
                    if not permission_func(user, obj):
                        raise HttpError(403, "Object permission denied")
                except model_class.DoesNotExist:
                    raise HttpError(404, "Object not found")
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

# 사용 예시
@api.put("/articles/{article_id}")
@check_object_permission(
    ObjectPermissionChecker.can_edit_article, 
    Article, 
    'article_id'
)
def update_article_with_object_permission(request, article_id: int, data: ArticleCreateSchema):
    """객체 수준 권한으로 게시글 수정"""
    article = get_object_or_404(Article, id=article_id)
    article.title = data.title
    article.content = data.content
    article.save()
    return article
```

### 3. 조건부 권한 제어

```python
# conditional_permissions.py
from datetime import datetime, timedelta
from ninja.errors import HttpError
from functools import wraps

def time_based_permission(start_hour: int = 9, end_hour: int = 18):
    """시간 기반 권한 제어 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            current_hour = datetime.now().hour
            if not (start_hour <= current_hour < end_hour):
                raise HttpError(403, f"Access allowed only between {start_hour}:00 and {end_hour}:00")
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

def ip_based_permission(allowed_ips: list):
    """IP 기반 권한 제어 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            client_ip = request.META.get('REMOTE_ADDR')
            if client_ip not in allowed_ips:
                raise HttpError(403, f"Access denied from IP: {client_ip}")
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

def user_status_permission(required_status: str):
    """사용자 상태 기반 권한 제어"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.auth
            if not user or not user.is_authenticated:
                raise HttpError(401, "Authentication required")
            
            # 사용자 프로필에서 상태 확인 (가정)
            if hasattr(user, 'profile') and user.profile.status != required_status:
                raise HttpError(403, f"Required status: {required_status}")
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

# 조건부 권한 조합 예시
@api.post("/admin/critical-operation")
@require_staff
@time_based_permission(start_hour=9, end_hour=17)  # 업무시간에만 허용
@ip_based_permission(['192.168.1.100', '10.0.0.50'])  # 특정 IP에서만 허용
def critical_admin_operation(request):
    """중요한 관리자 작업 (복합 권한 제어)"""
    # 중요한 작업 수행
    return {"success": True, "message": "Critical operation completed"}
```

## 📋 URL 설정 및 통합

```python
# urls.py
from django.urls import path
from ninja import NinjaAPI
from .api import api
from .async_api import async_api

# 메인 API 라우터
main_api = NinjaAPI(title="Blog API", version="1.0.0")

# 동기 API 추가
main_api.add_router("/sync", api)

# 비동기 API 추가  
main_api.add_router("/async", async_api)

urlpatterns = [
    path("api/", main_api.urls),
]
```

## 🧪 테스트 코드

```python
# tests.py
from django.test import TestCase
from django.contrib.auth.models import User, Group, Permission
from ninja.testing import TestClient
from .api import api
from .models import Article

class APIPermissionTestCase(TestCase):
    def setUp(self):
        # 테스트 사용자 생성
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.staff_user = User.objects.create_user(
            username='staffuser',
            password='testpass',
            is_staff=True
        )
        
        # 권한 설정
        permission = Permission.objects.get(codename='add_article')
        self.user.user_permissions.add(permission)
        
        # 테스트 클라이언트
        self.client = TestClient(api)
    
    def test_create_article_with_permission(self):
        """권한이 있는 사용자의 게시글 생성 테스트"""
        response = self.client.post(
            "/articles",
            json={"title": "Test Article", "content": "Test content"},
            auth=self.user
        )
        self.assertEqual(response.status_code, 200)
    
    def test_create_article_without_permission(self):
        """권한이 없는 사용자의 게시글 생성 테스트"""
        unauthorized_user = User.objects.create_user(
            username='noauth',
            password='testpass'
        )
        response = self.client.post(
            "/articles",
            json={"title": "Test Article", "content": "Test content"},
            auth=unauthorized_user
        )
        self.assertEqual(response.status_code, 403)
    
    def test_staff_only_endpoint(self):
        """스태프 전용 엔드포인트 테스트"""
        response = self.client.get("/admin/articles", auth=self.staff_user)
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get("/admin/articles", auth=self.user)
        self.assertEqual(response.status_code, 403)
```

## 🎯 성능 최적화 팁

### 1. 권한 확인 캐싱

```python
# cached_permissions.py
from django.core.cache import cache
from functools import wraps

def cached_permission_check(cache_timeout: int = 300):
    """권한 확인 결과 캐싱 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.auth
            if not user:
                raise HttpError(401, "Authentication required")
            
            # 캐시 키 생성
            cache_key = f"perm_{user.id}_{func.__name__}_{hash(str(args))}"
            
            # 캐시에서 권한 확인 결과 조회
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                if cached_result == 'allowed':
                    return func(request, *args, **kwargs)
                else:
                    raise HttpError(403, "Permission denied (cached)")
            
            # 권한 확인 로직 실행
            try:
                result = func(request, *args, **kwargs)
                cache.set(cache_key, 'allowed', cache_timeout)
                return result
            except HttpError as e:
                if e.status_code == 403:
                    cache.set(cache_key, 'denied', cache_timeout)
                raise
        return wrapper
    return decorator
```

### 2. 배치 권한 확인

```python
# batch_permissions.py
from django.contrib.auth.models import User
from typing import List, Dict

class BatchPermissionChecker:
    """배치 권한 확인 클래스"""
    
    @staticmethod
    def check_multiple_permissions(user: User, permission_codes: List[str]) -> Dict[str, bool]:
        """여러 권한을 한번에 확인"""
        results = {}
        user_permissions = user.get_all_permissions()
        
        for perm_code in permission_codes:
            results[perm_code] = perm_code in user_permissions
        
        return results
    
    @staticmethod
    def filter_objects_by_permission(user: User, objects: List, permission_func):
        """권한에 따라 객체 목록 필터링"""
        allowed_objects = []
        for obj in objects:
            if permission_func(user, obj):
                allowed_objects.append(obj)
        return allowed_objects
```

## 🚨 보안 고려사항

### 1. 권한 상승 공격 방지

```python
# security.py
from ninja.errors import HttpError
from functools import wraps

def prevent_privilege_escalation(func):
    """권한 상승 공격 방지 데코레이터"""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.auth
        if not user:
            raise HttpError(401, "Authentication required")
        
        # 요청 데이터에서 권한 관련 필드 검사
        if hasattr(request, 'json') and request.json:
            dangerous_fields = ['is_superuser', 'is_staff', 'user_permissions', 'groups']
            for field in dangerous_fields:
                if field in request.json:
                    raise HttpError(400, f"Modifying '{field}' is not allowed")
        
        return func(request, *args, **kwargs)
    return wrapper
```

### 2. 세션 무결성 검사

```python
# session_security.py
import time
from ninja.errors import HttpError

def check_session_integrity(max_age: int = 3600):
    """세션 무결성 검사 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.auth
            if not user:
                raise HttpError(401, "Authentication required")
            
            # 세션 만료 시간 확인
            last_activity = request.session.get('last_activity')
            if last_activity:
                if time.time() - last_activity > max_age:
                    raise HttpError(401, "Session expired")
            
            # 현재 시간으로 갱신
            request.session['last_activity'] = time.time()
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
```

## 📊 결론

Django에서 사용자 권한을 제어하는 방법은 다양하며, 프로젝트의 요구사항에 따라 적절한 방식을 선택해야 합니다:

### 주요 포인트

1. **기본 권한 시스템**: Django의 내장 권한 시스템을 활용한 기본적인 권한 제어
2. **django-ninja 데코레이터**: API 엔드포인트에 특화된 권한 제어 방식
3. **동기 vs 비동기**: 성능과 확장성을 고려한 적절한 방식 선택
4. **고급 패턴**: RBAC, 객체 수준 권한, 조건부 권한 등 복잡한 요구사항 대응
5. **성능 최적화**: 캐싱과 배치 처리를 통한 성능 향상
6. **보안 강화**: 권한 상승 공격 방지와 세션 보안 고려

### 권장사항

- **소규모 프로젝트**: Django 기본 권한 시스템 + 간단한 데코레이터
- **중규모 프로젝트**: RBAC + django-ninja 데코레이터 조합
- **대규모 프로젝트**: 비동기 방식 + 캐싱 + 고급 보안 기능

적절한 권한 제어 시스템을 구축하여 안전하고 확장 가능한 Django 애플리케이션을 개발하시기 바랍니다! 🛡️
