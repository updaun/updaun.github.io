---
layout: post
title: "Django Ninja로 구현하는 Workspace 기반 Multi-tenancy 인증 시스템"
date: 2026-01-21 09:00:00 +0900
categories: [Django, Authentication, Multi-tenancy]
tags: [django, django-ninja, multi-tenancy, authentication, workspace, saas]
description: "workspace:username 패턴을 활용한 멀티 테넌트 인증 시스템 설계 및 구현 가이드"
image: "/assets/img/posts/2026-01-21-django-ninja-workspace-based-multi-tenancy-authentication.webp"
---

## Multi-tenancy란 무엇인가?

Multi-tenancy(멀티 테넌시)는 하나의 소프트웨어 인스턴스가 여러 개의 독립적인 사용자 그룹(테넌트)을 서비스하는 아키텍처 패턴입니다. Slack, Notion, GitHub Organizations처럼 `workspace:username` 형태로 사용자를 식별하는 방식이 대표적인 예입니다. 이 패턴의 가장 큰 장점은 각 워크스페이스마다 동일한 username을 사용할 수 있다는 것입니다. 예를 들어, `company-a:john`과 `company-b:john`은 완전히 다른 사용자로 취급되어 각 워크스페이스 내에서 독립적으로 관리됩니다. 이는 대규모 SaaS 애플리케이션에서 데이터 격리(data isolation)와 리소스 관리를 효율적으로 수행할 수 있게 해주는 핵심 아키텍처입니다.

## 데이터베이스 모델 설계

Workspace 기반 인증 시스템의 핵심은 Workspace와 User 간의 관계를 올바르게 모델링하는 것입니다. 먼저 Workspace 모델은 각 테넌트를 대표하며 고유한 slug나 ID를 가집니다. User 모델은 기존 Django의 AbstractUser를 확장하되, username의 unique 제약 조건을 제거하고 대신 `(workspace, username)` 조합을 unique하게 설정해야 합니다. 이를 통해 서로 다른 워크스페이스에서 동일한 username을 사용할 수 있게 됩니다. 또한 사용자는 여러 워크스페이스에 속할 수 있으므로 WorkspaceMembership 같은 중간 모델을 통해 역할(role)과 권한을 관리하는 것이 일반적입니다.

```python
# models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid

class Workspace(models.Model):
    """워크스페이스(테넌트) 모델"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True, max_length=50)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'workspaces'
        
    def __str__(self):
        return self.name


class WorkspaceUserManager(BaseUserManager):
    """커스텀 사용자 매니저"""
    
    def create_user(self, workspace, username, email, password=None, **extra_fields):
        if not workspace:
            raise ValueError('Workspace is required')
        if not username:
            raise ValueError('Username is required')
        
        email = self.normalize_email(email)
        user = self.model(
            workspace=workspace,
            username=username,
            email=email,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user


class WorkspaceUser(AbstractBaseUser, PermissionsMixin):
    """워크스페이스 스코프 사용자 모델"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='users'
    )
    username = models.CharField(max_length=150)
    email = models.EmailField()
    full_name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = WorkspaceUserManager()
    
    USERNAME_FIELD = 'email'  # 로그인 시 사용
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'workspace_users'
        unique_together = [['workspace', 'username']]  # 핵심: 워크스페이스별 username 유니크
        indexes = [
            models.Index(fields=['workspace', 'username']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.workspace.slug}:{self.username}"
    
    @property
    def full_identifier(self):
        """workspace:username 형태의 전체 식별자"""
        return f"{self.workspace.slug}:{self.username}"


class WorkspaceRole(models.TextChoices):
    """워크스페이스 내 역할"""
    OWNER = 'owner', 'Owner'
    ADMIN = 'admin', 'Admin'
    MEMBER = 'member', 'Member'
    GUEST = 'guest', 'Guest'


class WorkspaceMembership(models.Model):
    """사용자와 워크스페이스 간의 멤버십 (다대다 관계)"""
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    user = models.ForeignKey(WorkspaceUser, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=20,
        choices=WorkspaceRole.choices,
        default=WorkspaceRole.MEMBER
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'workspace_memberships'
        unique_together = [['workspace', 'user']]
```

## Django Ninja 인증 백엔드 구현

Django Ninja에서 workspace 기반 인증을 구현하려면 커스텀 authentication 클래스를 만들어야 합니다. 표준 Django 인증은 username이 전역적으로 유니크하다고 가정하지만, 우리는 `workspace:username` 조합으로 사용자를 찾아야 합니다. 로그인 요청 시 클라이언트는 workspace slug, username, password를 함께 제공해야 하며, 서버는 해당 workspace 내에서 username을 조회합니다. 인증이 성공하면 JWT 토큰이나 세션에 workspace 정보도 함께 저장하여 이후 요청에서 컨텍스트를 유지합니다. 이 방식은 사용자가 여러 워크스페이스에 속할 경우 각 워크스페이스별로 별도의 세션을 유지할 수 있게 해줍니다.

```python
# auth.py
from ninja.security import HttpBearer
from django.contrib.auth import authenticate
from django.contrib.auth.backends import BaseBackend
from .models import WorkspaceUser, Workspace
import jwt
from datetime import datetime, timedelta
from django.conf import settings


class WorkspaceAuthBackend(BaseBackend):
    """워크스페이스 기반 인증 백엔드"""
    
    def authenticate(self, request, workspace_slug=None, username=None, password=None):
        try:
            workspace = Workspace.objects.get(slug=workspace_slug)
            user = WorkspaceUser.objects.get(
                workspace=workspace,
                username=username
            )
            
            if user.check_password(password) and user.is_active:
                return user
        except (Workspace.DoesNotExist, WorkspaceUser.DoesNotExist):
            return None
        
        return None
    
    def get_user(self, user_id):
        try:
            return WorkspaceUser.objects.get(pk=user_id)
        except WorkspaceUser.DoesNotExist:
            return None


class WorkspaceJWTAuth(HttpBearer):
    """JWT 기반 워크스페이스 인증"""
    
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            
            user_id = payload.get('user_id')
            workspace_id = payload.get('workspace_id')
            
            user = WorkspaceUser.objects.select_related('workspace').get(
                id=user_id,
                workspace_id=workspace_id,
                is_active=True
            )
            
            # request에 workspace 컨텍스트 추가
            request.workspace = user.workspace
            return user
            
        except (jwt.InvalidTokenError, WorkspaceUser.DoesNotExist):
            return None


def create_access_token(user: WorkspaceUser) -> str:
    """JWT 액세스 토큰 생성"""
    payload = {
        'user_id': str(user.id),
        'workspace_id': str(user.workspace.id),
        'username': user.username,
        'workspace_slug': user.workspace.slug,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
```

## API 엔드포인트 구현

Django Ninja로 workspace 기반 인증 API를 구축할 때는 로그인, 회원가입, 사용자 정보 조회 등의 엔드포인트를 구현해야 합니다. 로그인 엔드포인트는 workspace slug, username, password를 받아 해당 워크스페이스 컨텍스트에서 인증을 수행하고 JWT 토큰을 반환합니다. 회원가입의 경우 기존 워크스페이스에 가입하는 경우와 새로운 워크스페이스를 생성하는 경우를 구분해야 합니다. 모든 보호된 엔드포인트는 `WorkspaceJWTAuth`를 사용하여 인증하며, 자동으로 request 객체에 현재 워크스페이스 컨텍스트가 주입됩니다. 이를 통해 각 API 호출이 올바른 워크스페이스 범위 내에서만 데이터에 접근할 수 있도록 보장합니다.

```python
# api.py
from ninja import NinjaAPI, Schema
from ninja.errors import HttpError
from django.db import transaction
from .models import Workspace, WorkspaceUser, WorkspaceMembership, WorkspaceRole
from .auth import WorkspaceJWTAuth, WorkspaceAuthBackend, create_access_token

api = NinjaAPI()
auth = WorkspaceJWTAuth()


# Request/Response 스키마
class LoginRequest(Schema):
    workspace_slug: str
    username: str
    password: str


class SignupRequest(Schema):
    workspace_slug: str  # 새 워크스페이스 또는 기존 워크스페이스
    username: str
    email: str
    password: str
    full_name: str = ""
    create_workspace: bool = False  # True면 새 워크스페이스 생성


class AuthResponse(Schema):
    access_token: str
    user: dict
    workspace: dict


class UserResponse(Schema):
    id: str
    username: str
    email: str
    full_name: str
    workspace_slug: str
    full_identifier: str


# 인증 엔드포인트
@api.post("/auth/login", response=AuthResponse, auth=None)
def login(request, payload: LoginRequest):
    """워크스페이스 기반 로그인"""
    backend = WorkspaceAuthBackend()
    user = backend.authenticate(
        request,
        workspace_slug=payload.workspace_slug,
        username=payload.username,
        password=payload.password
    )
    
    if not user:
        raise HttpError(401, "Invalid credentials")
    
    token = create_access_token(user)
    
    return {
        "access_token": token,
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
        },
        "workspace": {
            "id": str(user.workspace.id),
            "slug": user.workspace.slug,
            "name": user.workspace.name,
        }
    }


@api.post("/auth/signup", response=AuthResponse, auth=None)
@transaction.atomic
def signup(request, payload: SignupRequest):
    """워크스페이스 기반 회원가입"""
    
    # 워크스페이스 처리
    if payload.create_workspace:
        # 새 워크스페이스 생성
        if Workspace.objects.filter(slug=payload.workspace_slug).exists():
            raise HttpError(400, "Workspace slug already exists")
        
        workspace = Workspace.objects.create(
            slug=payload.workspace_slug,
            name=payload.workspace_slug.replace('-', ' ').title()
        )
        role = WorkspaceRole.OWNER
    else:
        # 기존 워크스페이스에 가입
        try:
            workspace = Workspace.objects.get(slug=payload.workspace_slug)
        except Workspace.DoesNotExist:
            raise HttpError(404, "Workspace not found")
        role = WorkspaceRole.MEMBER
    
    # 같은 워크스페이스에 동일한 username이 있는지 확인
    if WorkspaceUser.objects.filter(
        workspace=workspace,
        username=payload.username
    ).exists():
        raise HttpError(400, "Username already exists in this workspace")
    
    # 사용자 생성
    user = WorkspaceUser.objects.create_user(
        workspace=workspace,
        username=payload.username,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name
    )
    
    # 멤버십 생성
    WorkspaceMembership.objects.create(
        workspace=workspace,
        user=user,
        role=role
    )
    
    token = create_access_token(user)
    
    return {
        "access_token": token,
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
        },
        "workspace": {
            "id": str(workspace.id),
            "slug": workspace.slug,
            "name": workspace.name,
        }
    }


@api.get("/auth/me", response=UserResponse, auth=auth)
def get_current_user(request):
    """현재 로그인한 사용자 정보"""
    user = request.auth
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "workspace_slug": user.workspace.slug,
        "full_identifier": user.full_identifier,
    }


@api.get("/workspaces/{workspace_slug}/users", auth=auth)
def list_workspace_users(request, workspace_slug: str):
    """워크스페이스 내 사용자 목록"""
    # 요청한 사용자가 해당 워크스페이스에 속하는지 확인
    if request.auth.workspace.slug != workspace_slug:
        raise HttpError(403, "Access denied to this workspace")
    
    users = WorkspaceUser.objects.filter(
        workspace__slug=workspace_slug
    ).select_related('workspace')
    
    return [
        {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "full_identifier": user.full_identifier,
        }
        for user in users
    ]
```

## 클라이언트 사용 예시

클라이언트 애플리케이션에서 workspace 기반 인증 API를 사용하는 방법은 간단합니다. 로그인 시 사용자는 소속된 워크스페이스 slug를 선택하거나 입력하고, username과 password를 함께 제공합니다. 서버로부터 받은 JWT 토큰은 로컬 스토리지나 쿠키에 저장하고, 이후 모든 API 요청의 Authorization 헤더에 포함시킵니다. 프론트엔드에서는 사용자가 여러 워크스페이스에 속한 경우 워크스페이스 전환 기능을 제공할 수 있으며, 이 경우 각 워크스페이스별로 별도의 토큰을 관리해야 합니다. 로그인 폼은 일반적으로 `workspace.example.com` 같은 서브도메인이나 `/login?workspace=acme` 같은 쿼리 파라미터로 워크스페이스를 미리 식별할 수 있습니다.

```javascript
// 프론트엔드 JavaScript 예시

// 1. 새 워크스페이스 생성 + 회원가입
async function createWorkspaceAndSignup(workspaceSlug, username, email, password) {
    const response = await fetch('/api/auth/signup', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            workspace_slug: workspaceSlug,
            username: username,
            email: email,
            password: password,
            full_name: '',
            create_workspace: true
        })
    });
    
    if (!response.ok) {
        throw new Error('Signup failed');
    }
    
    const data = await response.json();
    
    // 토큰 저장
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('workspace_slug', data.workspace.slug);
    localStorage.setItem('username', data.user.username);
    
    return data;
}

// 2. 기존 워크스페이스에 로그인
async function login(workspaceSlug, username, password) {
    const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            workspace_slug: workspaceSlug,
            username: username,
            password: password
        })
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
    }
    
    const data = await response.json();
    
    // 토큰 저장
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('workspace_slug', data.workspace.slug);
    
    return data;
}

// 3. 인증이 필요한 API 호출
async function getCurrentUser() {
    const token = localStorage.getItem('access_token');
    
    const response = await fetch('/api/auth/me', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
        }
    });
    
    if (!response.ok) {
        throw new Error('Failed to fetch user');
    }
    
    return await response.json();
}

// 4. 워크스페이스 사용자 목록 조회
async function getWorkspaceUsers(workspaceSlug) {
    const token = localStorage.getItem('access_token');
    
    const response = await fetch(`/api/workspaces/${workspaceSlug}/users`, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
        }
    });
    
    if (!response.ok) {
        throw new Error('Failed to fetch workspace users');
    }
    
    return await response.json();
}

// 사용 예시
(async () => {
    try {
        // 로그인
        const authData = await login('acme-corp', 'john', 'password123');
        console.log('Logged in:', authData.user.username);
        console.log('Workspace:', authData.workspace.name);
        
        // 현재 사용자 정보
        const currentUser = await getCurrentUser();
        console.log('Full identifier:', currentUser.full_identifier); // "acme-corp:john"
        
        // 같은 워크스페이스의 다른 사용자들
        const users = await getWorkspaceUsers('acme-corp');
        console.log('Workspace users:', users);
        
    } catch (error) {
        console.error('Error:', error.message);
    }
})();
```

## 보안 고려사항

Workspace 기반 multi-tenancy 시스템에서 가장 중요한 것은 데이터 격리(data isolation)입니다. 모든 데이터베이스 쿼리는 반드시 현재 워크스페이스로 필터링되어야 하며, 실수로 다른 워크스페이스의 데이터에 접근하는 것을 방지해야 합니다. Django 미들웨어나 컨텍스트 매니저를 사용하여 현재 워크스페이스를 thread-local 변수에 저장하고, 모든 쿼리에 자동으로 적용하는 것이 좋습니다. JWT 토큰에는 반드시 workspace_id를 포함시켜 토큰 재사용 공격을 방지해야 하며, 사용자가 워크스페이스를 전환할 때는 새로운 토큰을 발급받아야 합니다. 또한 CORS 설정, Rate Limiting, SQL Injection 방지 등 일반적인 웹 보안 원칙도 철저히 적용해야 합니다.

```python
# middleware.py - 워크스페이스 컨텍스트 자동 관리
import threading
from django.utils.deprecation import MiddlewareMixin

_thread_locals = threading.local()


def get_current_workspace():
    """현재 스레드의 워크스페이스 반환"""
    return getattr(_thread_locals, 'workspace', None)


def set_current_workspace(workspace):
    """현재 스레드의 워크스페이스 설정"""
    _thread_locals.workspace = workspace


class WorkspaceMiddleware(MiddlewareMixin):
    """모든 요청에 워크스페이스 컨텍스트 추가"""
    
    def process_request(self, request):
        if hasattr(request, 'auth') and hasattr(request.auth, 'workspace'):
            set_current_workspace(request.auth.workspace)
        else:
            set_current_workspace(None)
    
    def process_response(self, request, response):
        set_current_workspace(None)
        return response


# managers.py - 워크스페이스 스코프 자동 적용
from django.db import models

class WorkspaceScopedManager(models.Manager):
    """워크스페이스로 자동 필터링하는 매니저"""
    
    def get_queryset(self):
        queryset = super().get_queryset()
        workspace = get_current_workspace()
        
        if workspace:
            return queryset.filter(workspace=workspace)
        return queryset


# 사용 예시: 모델에 적용
class Project(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    
    objects = WorkspaceScopedManager()  # 자동으로 현재 워크스페이스만 조회
    all_objects = models.Manager()  # 관리자용: 모든 워크스페이스 조회
    
    class Meta:
        db_table = 'projects'


# Rate Limiting 예시
from ninja import NinjaAPI
from functools import wraps
from django.core.cache import cache
from ninja.errors import HttpError

def rate_limit(max_requests: int = 100, window: int = 3600):
    """워크스페이스별 Rate Limiting 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if hasattr(request, 'auth') and request.auth:
                # 워크스페이스별로 rate limit 적용
                key = f"rate_limit:{request.auth.workspace.id}:{request.auth.id}"
                
                count = cache.get(key, 0)
                if count >= max_requests:
                    raise HttpError(429, "Too many requests")
                
                cache.set(key, count + 1, window)
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


# 사용 예시
@api.get("/projects", auth=auth)
@rate_limit(max_requests=100, window=3600)
def list_projects(request):
    """프로젝트 목록 (자동으로 현재 워크스페이스만 조회)"""
    projects = Project.objects.all()  # WorkspaceScopedManager가 자동 필터링
    return [{"id": p.id, "name": p.name} for p in projects]
```

## 테스트 전략

Multi-tenancy 시스템의 테스트에서 가장 중요한 것은 데이터 격리가 제대로 작동하는지 검증하는 것입니다. 각 테스트 케이스마다 최소 2개 이상의 워크스페이스를 생성하고, 한 워크스페이스의 사용자가 다른 워크스페이스의 데이터에 접근할 수 없음을 확인해야 합니다. pytest-django나 Django의 TestCase를 사용하여 fixture로 여러 워크스페이스와 사용자를 미리 생성하고, API 엔드포인트에 대한 권한 검증을 철저히 수행합니다. 또한 동일한 username이 서로 다른 워크스페이스에서 정상적으로 생성되고 독립적으로 인증되는지 테스트해야 합니다.

```python
# tests/test_workspace_auth.py
import pytest
from django.test import TestCase
from ninja.testing import TestClient
from ..models import Workspace, WorkspaceUser
from ..api import api
from ..auth import create_access_token


@pytest.fixture
def workspaces(db):
    """테스트용 워크스페이스 생성"""
    workspace_a = Workspace.objects.create(slug='company-a', name='Company A')
    workspace_b = Workspace.objects.create(slug='company-b', name='Company B')
    return workspace_a, workspace_b


@pytest.fixture
def users(workspaces):
    """각 워크스페이스에 동일한 username으로 사용자 생성"""
    workspace_a, workspace_b = workspaces
    
    user_a = WorkspaceUser.objects.create_user(
        workspace=workspace_a,
        username='john',
        email='john@company-a.com',
        password='password123'
    )
    
    user_b = WorkspaceUser.objects.create_user(
        workspace=workspace_b,
        username='john',  # 같은 username
        email='john@company-b.com',
        password='password456'
    )
    
    return user_a, user_b


@pytest.mark.django_db
class TestWorkspaceAuth:
    """워크스페이스 인증 테스트"""
    
    def test_same_username_different_workspaces(self, users):
        """동일한 username이 다른 워크스페이스에 존재할 수 있음"""
        user_a, user_b = users
        
        assert user_a.username == user_b.username == 'john'
        assert user_a.workspace.slug == 'company-a'
        assert user_b.workspace.slug == 'company-b'
        assert user_a.id != user_b.id
    
    def test_login_with_correct_workspace(self, users):
        """올바른 워크스페이스로 로그인"""
        client = TestClient(api)
        
        response = client.post('/auth/login', json={
            'workspace_slug': 'company-a',
            'username': 'john',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data['user']['username'] == 'john'
        assert data['workspace']['slug'] == 'company-a'
        assert 'access_token' in data
    
    def test_login_with_wrong_workspace(self, users):
        """잘못된 워크스페이스로 로그인 시도"""
        client = TestClient(api)
        
        # company-a의 비밀번호로 company-b 로그인 시도
        response = client.post('/auth/login', json={
            'workspace_slug': 'company-b',
            'username': 'john',
            'password': 'password123'  # company-a의 비밀번호
        })
        
        assert response.status_code == 401
    
    def test_data_isolation(self, users):
        """데이터 격리: 다른 워크스페이스의 사용자 목록에 접근 불가"""
        user_a, user_b = users
        token_a = create_access_token(user_a)
        
        client = TestClient(api)
        
        # company-a 사용자가 company-b의 사용자 목록 조회 시도
        response = client.get(
            '/workspaces/company-b/users',
            headers={'Authorization': f'Bearer {token_a}'}
        )
        
        assert response.status_code == 403
    
    def test_workspace_users_list(self, workspaces):
        """워크스페이스 내 사용자 목록 조회"""
        workspace_a, _ = workspaces
        
        # 여러 사용자 생성
        for i in range(3):
            WorkspaceUser.objects.create_user(
                workspace=workspace_a,
                username=f'user{i}',
                email=f'user{i}@company-a.com',
                password='password'
            )
        
        user = WorkspaceUser.objects.get(workspace=workspace_a, username='user0')
        token = create_access_token(user)
        
        client = TestClient(api)
        response = client.get(
            '/workspaces/company-a/users',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        assert response.status_code == 200
        users_data = response.json()
        assert len(users_data) == 3
        
        # 모든 사용자가 company-a 워크스페이스에 속함
        for user_data in users_data:
            assert 'company-a' in user_data['full_identifier']


@pytest.mark.django_db
class TestWorkspaceSignup:
    """워크스페이스 회원가입 테스트"""
    
    def test_create_new_workspace(self):
        """새 워크스페이스 생성과 함께 회원가입"""
        client = TestClient(api)
        
        response = client.post('/auth/signup', json={
            'workspace_slug': 'new-company',
            'username': 'admin',
            'email': 'admin@new-company.com',
            'password': 'secure-password',
            'create_workspace': True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['workspace']['slug'] == 'new-company'
        assert data['user']['username'] == 'admin'
        
        # 워크스페이스와 사용자가 실제로 생성되었는지 확인
        workspace = Workspace.objects.get(slug='new-company')
        user = WorkspaceUser.objects.get(workspace=workspace, username='admin')
        assert user.email == 'admin@new-company.com'
    
    def test_join_existing_workspace(self, workspaces):
        """기존 워크스페이스에 가입"""
        client = TestClient(api)
        
        response = client.post('/auth/signup', json={
            'workspace_slug': 'company-a',
            'username': 'newuser',
            'email': 'newuser@company-a.com',
            'password': 'password',
            'create_workspace': False
        })
        
        assert response.status_code == 200
        
        # 사용자가 추가되었는지 확인
        workspace_a, _ = workspaces
        user = WorkspaceUser.objects.get(workspace=workspace_a, username='newuser')
        assert user.email == 'newuser@company-a.com'
    
    def test_duplicate_username_in_same_workspace(self, users):
        """같은 워크스페이스에 중복 username 생성 시도"""
        client = TestClient(api)
        
        response = client.post('/auth/signup', json={
            'workspace_slug': 'company-a',
            'username': 'john',  # 이미 존재
            'email': 'another@company-a.com',
            'password': 'password',
            'create_workspace': False
        })
        
        assert response.status_code == 400
```

## 실전 배포 팁

프로덕션 환경에서 workspace 기반 multi-tenancy를 배포할 때는 몇 가지 추가 고려사항이 있습니다. 첫째, 서브도메인 라우팅을 사용하면 사용자 경험이 크게 향상됩니다 - `acme.yourapp.com`, `techcorp.yourapp.com` 같은 방식으로 각 워크스페이스에 전용 도메인을 제공할 수 있습니다. 둘째, 데이터베이스 성능을 위해 workspace_id에 인덱스를 추가하고, 대규모 서비스의 경우 워크스페이스별로 데이터베이스를 분리하는 것도 고려할 수 있습니다. 셋째, 캐시 키에도 workspace_id를 포함시켜 데이터 격리를 유지해야 합니다. 마지막으로 모니터링과 로깅 시스템에서도 워크스페이스 정보를 함께 기록하여 문제 발생 시 빠르게 원인을 파악할 수 있도록 해야 합니다.

```python
# settings.py - 프로덕션 설정 예시

# 서브도메인 라우팅
ALLOWED_HOSTS = [
    '.yourapp.com',  # 모든 서브도메인 허용
    'yourapp.com',
]

# 데이터베이스 읽기 복제본 (대규모 서비스)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'yourapp_db',
        'HOST': 'primary-db.example.com',
        # ... 기타 설정
    },
    'read_replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'yourapp_db',
        'HOST': 'replica-db.example.com',
        # ... 기타 설정
    }
}

# 캐시 설정 (워크스페이스별 격리)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'yourapp',  # 워크스페이스 ID를 키에 포함시킬 것
    }
}

# 로깅 설정 (워크스페이스 정보 포함)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} workspace={workspace_id} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/yourapp/django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
}
```

```nginx
# nginx.conf - 서브도메인 라우팅 설정
server {
    listen 80;
    server_name ~^(?<workspace>.+)\.yourapp\.com$;
    
    location / {
        proxy_pass http://django_app;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Workspace-Slug $workspace;  # 워크스페이스 정보 전달
    }
}

# 메인 도메인
server {
    listen 80;
    server_name yourapp.com;
    
    location / {
        proxy_pass http://django_app;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 결론

Workspace 기반 multi-tenancy 인증 시스템은 현대적인 SaaS 애플리케이션의 필수 요소입니다. `workspace:username` 패턴을 통해 각 조직이나 팀이 독립적인 사용자 네임스페이스를 유지하면서도, 중앙화된 단일 애플리케이션으로 효율적인 관리가 가능합니다. Django Ninja를 사용하면 이러한 복잡한 인증 시스템을 타입 안전하고 깔끔한 API로 구현할 수 있습니다. 핵심은 데이터베이스 모델에서 `(workspace, username)` unique constraint를 설정하고, 모든 데이터 접근 시 워크스페이스 컨텍스트를 유지하며, 철저한 데이터 격리를 보장하는 것입니다. 이 글에서 다룬 패턴들을 기반으로 여러분만의 multi-tenant 애플리케이션을 구축해보시기 바랍니다.

## 참고 자료

- [Django Ninja 공식 문서](https://django-ninja.rest-framework.com/)
- [Django Multi-tenancy 패턴](https://docs.djangoproject.com/)
- [JWT 인증 베스트 프랙티스](https://jwt.io/introduction)
- [SaaS 아키텍처 가이드](https://aws.amazon.com/saas/)

