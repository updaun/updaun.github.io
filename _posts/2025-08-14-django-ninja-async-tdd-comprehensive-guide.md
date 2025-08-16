---
layout: post
title: "Django Ninja TestClient로 TDD 완전 가이드: 체계적인 API 테스트 전략"
date: 2025-08-14 10:00:00 +0900
categories: [Django, Testing, Async, API]
tags: [Django-Ninja, TDD, TestClient, AsyncTestClient, Testing, Python, API, Unit Test, Integration Test, Django, Performance, Async]
image: "/assets/img/posts/2025-08-14-django-ninja-async-tdd-comprehensive-guide.webp"
---

Django Ninja로 비동기 API를 개발하면서 테스트 작성에 어려움을 겪고 계신가요? 이 글에서는 Django Ninja의 TestClient와 AsyncTestClient를 활용한 TDD(Test-Driven Development) 방법론을 단계별로 알아보겠습니다. 동기/비동기 테스트의 장단점부터 세분화된 테스트 전략까지 실무에서 바로 적용할 수 있는 방법들을 다루겠습니다.

## 🚀 Django Ninja 비동기 TDD 개요

### TDD란 무엇인가?

TDD(Test-Driven Development)는 **테스트를 먼저 작성하고, 테스트를 통과하는 최소한의 코드를 구현한 후, 리팩토링하는** 개발 방법론입니다.

**TDD 사이클:**
1. **Red**: 실패하는 테스트 작성
2. **Green**: 테스트를 통과하는 최소한의 코드 작성
3. **Refactor**: 코드 개선 및 최적화

### Django Ninja에서 비동기 테스트의 중요성

```python
# Django Ninja 비동기 API 예제
from ninja import NinjaAPI
from django.http import HttpResponse
import asyncio

api = NinjaAPI()

@api.get("/users/{user_id}")
async def get_user(request, user_id: int):
    # 비동기 데이터베이스 조회
    user = await User.objects.aget(id=user_id)
    # 외부 API 호출
    profile_data = await fetch_external_profile(user.email)
    
    return {
        "user": user,
        "profile": profile_data
    }
```

**비동기 API의 특징:**
- 동시 처리 능력 향상
- I/O 대기 시간 최적화
- 외부 API 호출 시 논블로킹
- 높은 처리량(throughput) 달성

이러한 비동기 API를 제대로 테스트하려면 **AsyncTestClient**가 필요합니다.

## 📋 환경 설정 및 기본 구조

### 필요한 패키지 설치

```bash
pip install django
pip install django-ninja
pip install asgiref
pip install pytest  # AsyncTestClient 사용 시 권장
pip install pytest-django
pip install pytest-asyncio
```

### 프로젝트 구조

```
myproject/
├── myproject/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── asgi.py
├── apps/
│   ├── users/
│   │   ├── models.py
│   │   ├── api.py
│   │   └── tests.py
│   └── posts/
│       ├── models.py
│       ├── api.py
│       └── tests.py
└── manage.py
```

### 기본 설정 파일

**Django settings.py**
```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.users',
    'apps.posts',
]

# 테스트 설정
if 'test' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
```

**메인 urls.py**
```python
# myproject/urls.py
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from apps.users.api import router as users_router
from apps.posts.api import router as posts_router

api = NinjaAPI()
api.add_router("/users/", users_router)
api.add_router("/posts/", posts_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
```

## 🔧 TestClient vs AsyncTestClient 비교

### 1. TestClient (동기 테스트)

**장점:**
- Django의 기본 테스트 시스템과 완벽 통합
- 설정이 간단하고 직관적
- 대부분의 API 테스트에 충분
- 빠른 테스트 실행

**단점:**
- 비동기 뷰의 실제 동작을 테스트하지 못함
- 외부 API 호출의 동시성 테스트 불가
- 실제 성능 특성을 검증하기 어려움

```python
# TestClient 예제 (동기)
from django.test import TestCase
from ninja.testing import TestClient
from ninja import NinjaAPI
from .api import router
from .models import User

class TestUserAPISync(TestCase):
    
    def setUp(self):
        api = NinjaAPI()
        api.add_router("/users/", router)
        self.client = TestClient(api)
    
    def test_get_user_list(self):
        """동기 테스트 - 간단하고 빠름"""
        User.objects.create(username="user1", email="user1@test.com")
        
        response = self.client.get("/users/")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
```

### 2. AsyncTestClient (비동기 테스트)

**장점:**
- 실제 비동기 동작을 정확히 테스트
- 동시성과 성능 특성 검증 가능
- 외부 API 호출의 실제 비동기 동작 테스트
- 실제 운영 환경과 유사한 테스트

**단점:**
- 설정이 복잡
- 테스트 실행 시간이 길어질 수 있음
- pytest와 pytest-asyncio 의존성 필요

```python
# AsyncTestClient 예제 (비동기)
import pytest
from ninja.testing import TestAsyncClient
from ninja import NinjaAPI
from .api import router
from .models import User

@pytest.mark.asyncio
class TestUserAPIAsync:
    
    def setup_method(self):
        api = NinjaAPI()
        api.add_router("/users/", router)
        self.client = TestAsyncClient(api)
    
    async def test_get_user_list_async(self):
        """비동기 테스트 - 실제 비동기 동작 검증"""
        await User.objects.acreate(username="user1", email="user1@test.com")
        
        response = await self.client.get("/users/")
        
        assert response.status_code == 200
        assert len(response.json()) == 1
```

## 🚀 AsyncTestClient의 핵심 장점

### 1. 실제 비동기 동작 검증

```python
import pytest
import asyncio
from ninja.testing import TestAsyncClient
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
class TestAsyncBehavior:
    
    async def test_concurrent_external_api_calls(self):
        """동시 외부 API 호출 테스트"""
        # 여러 사용자의 프로필을 동시에 가져오는 API
        users = [
            await User.objects.acreate(username=f"user{i}", email=f"user{i}@test.com")
            for i in range(5)
        ]
        
        # 외부 API 호출을 모킹
        with patch('apps.users.api.fetch_external_profile', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"bio": "Test bio"}
            
            # 동시에 여러 사용자 프로필 요청
            start_time = asyncio.get_event_loop().time()
            
            tasks = [
                self.client.get(f"/users/{user.id}/profile")
                for user in users
            ]
            responses = await asyncio.gather(*tasks)
            
            end_time = asyncio.get_event_loop().time()
            
            # 모든 요청이 성공했는지 확인
            for response in responses:
                assert response.status_code == 200
            
            # 비동기 처리로 인한 시간 절약 확인
            # 동기 처리라면 5 * 0.1초 = 0.5초, 비동기라면 0.1초 정도
            assert end_time - start_time < 0.2
            
            # 외부 API가 5번 호출되었는지 확인
            assert mock_fetch.call_count == 5

    async def test_database_async_operations(self):
        """비동기 데이터베이스 작업 테스트"""
        # 대량 데이터 비동기 생성
        user_data_list = [
            {"username": f"bulk_user_{i}", "email": f"bulk_{i}@test.com"}
            for i in range(100)
        ]
        
        start_time = asyncio.get_event_loop().time()
        
        # 비동기로 대량 사용자 생성
        response = await self.client.post("/users/bulk-create-async", json={
            "users": user_data_list
        })
        
        end_time = asyncio.get_event_loop().time()
        
        assert response.status_code == 201
        assert response.json()["created_count"] == 100
        
        # 비동기 처리가 동기보다 빠른지 확인
        assert end_time - start_time < 1.0  # 1초 이내
```

### 2. 실제 성능 특성 측정

```python
@pytest.mark.asyncio
async def test_performance_under_load(self):
    """부하 상황에서의 성능 테스트"""
    # 테스트 데이터 준비
    user = await User.objects.acreate(username="loadtest", email="load@test.com")
    
    # 동시에 100개의 요청 발생
    async def make_request():
        return await self.client.get(f"/users/{user.id}")
    
    start_time = asyncio.get_event_loop().time()
    
    # 100개 동시 요청
    tasks = [make_request() for _ in range(100)]
    responses = await asyncio.gather(*tasks)
    
    end_time = asyncio.get_event_loop().time()
    
    # 모든 요청이 성공했는지 확인
    success_count = sum(1 for r in responses if r.status_code == 200)
    assert success_count == 100
    
    # 평균 응답 시간 계산
    total_time = end_time - start_time
    avg_response_time = total_time / 100
    
    # 비동기 처리로 인한 효율성 확인
    assert avg_response_time < 0.01  # 평균 10ms 이하
    assert total_time < 2.0  # 전체 처리 시간 2초 이하

@pytest.mark.asyncio
async def test_memory_efficiency(self):
    """메모리 효율성 테스트"""
    import tracemalloc
    
    tracemalloc.start()
    
    # 메모리 사용량 측정하며 대량 요청 처리
    tasks = []
    for i in range(1000):
        user = await User.objects.acreate(username=f"mem_user_{i}")
        task = self.client.get(f"/users/{user.id}")
        tasks.append(task)
    
    # 모든 요청 동시 실행
    responses = await asyncio.gather(*tasks)
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # 메모리 사용량이 합리적인 범위 내인지 확인
    assert peak < 50 * 1024 * 1024  # 50MB 이하
    
    # 모든 요청이 성공했는지 확인
    assert len([r for r in responses if r.status_code == 200]) == 1000
```

### 3. 복잡한 비동기 워크플로우 테스트

```python
@pytest.mark.asyncio
async def test_complex_async_workflow(self):
    """복잡한 비동기 워크플로우 테스트"""
    # 시나리오: 사용자 생성 → 외부 API 연동 → 알림 발송 → 로그 기록
    
    with patch('apps.users.api.send_welcome_email', new_callable=AsyncMock) as mock_email, \
         patch('apps.users.api.log_user_creation', new_callable=AsyncMock) as mock_log, \
         patch('apps.users.api.sync_with_external_service', new_callable=AsyncMock) as mock_sync:
        
        # 각 비동기 작업이 성공하도록 설정
        mock_email.return_value = {"status": "sent"}
        mock_log.return_value = {"logged": True}
        mock_sync.return_value = {"synced": True}
        
        # 사용자 생성 (복잡한 비동기 워크플로우 트리거)
        user_data = {
            "username": "complex_user",
            "email": "complex@test.com",
            "trigger_full_workflow": True
        }
        
        start_time = asyncio.get_event_loop().time()
        response = await self.client.post("/users/", json=user_data)
        end_time = asyncio.get_event_loop().time()
        
        # 응답 확인
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "complex_user"
        assert data["workflow_status"] == "completed"
        
        # 모든 비동기 작업이 호출되었는지 확인
        mock_email.assert_called_once()
        mock_log.assert_called_once()
        mock_sync.assert_called_once()
        
        # 비동기 처리로 인한 빠른 완료 확인
        assert end_time - start_time < 0.5

@pytest.mark.asyncio
async def test_error_handling_in_async_chain(self):
    """비동기 체인에서의 오류 처리 테스트"""
    with patch('apps.users.api.external_validation', new_callable=AsyncMock) as mock_validation:
        # 외부 검증이 실패하도록 설정
        mock_validation.side_effect = Exception("Validation service unavailable")
        
        user_data = {
            "username": "error_test_user",
            "email": "error@test.com",
            "require_external_validation": True
        }
        
        response = await self.client.post("/users/", json=user_data)
        
        # 오류가 적절히 처리되었는지 확인
        assert response.status_code == 422
        error_data = response.json()
        assert "validation_error" in error_data
        
        # 사용자가 생성되지 않았는지 확인
        assert not await User.objects.filter(username="error_test_user").aexists()
```

### 4. 실시간 기능 테스트

```python
@pytest.mark.asyncio
async def test_websocket_integration(self):
    """WebSocket과의 통합 테스트"""
    # WebSocket 연결 시뮬레이션
    websocket_messages = []
    
    async def mock_websocket_send(message):
        websocket_messages.append(message)
    
    with patch('apps.users.api.send_websocket_notification', side_effect=mock_websocket_send):
        # 사용자 상태 변경 (실시간 알림 트리거)
        user = await User.objects.acreate(username="ws_user", email="ws@test.com")
        
        response = await self.client.patch(f"/users/{user.id}/status", json={
            "status": "online"
        })
        
        assert response.status_code == 200
        
        # WebSocket 메시지가 발송되었는지 확인
        assert len(websocket_messages) == 1
        assert websocket_messages[0]["type"] == "user_status_change"
        assert websocket_messages[0]["user_id"] == user.id

@pytest.mark.asyncio 
async def test_streaming_response(self):
    """스트리밍 응답 테스트"""
    # 대용량 데이터 스트리밍 API 테스트
    response = await self.client.get("/users/export-stream")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-ndjson"
    
    # 스트리밍 데이터 검증
    lines = response.content.decode().strip().split('\n')
    assert len(lines) > 0
    
    # 각 라인이 유효한 JSON인지 확인
    import json
    for line in lines:
        data = json.loads(line)
        assert "username" in data
        assert "email" in data
```

## 💡 AsyncTestClient 사용 시기

**AsyncTestClient를 사용해야 하는 경우:**

1. **비동기 뷰 함수를 테스트할 때**
2. **외부 API 호출이 포함된 워크플로우**
3. **동시성이 중요한 기능**
4. **실제 성능 특성을 검증해야 할 때**
5. **WebSocket이나 스트리밍 응답 테스트**

**TestClient만으로 충분한 경우:**

1. **단순한 CRUD 작업**
2. **빠른 유닛 테스트**
3. **비즈니스 로직 검증**
4. **입력 유효성 검사**

## 🔧 TestClient 기본 사용법 (동기 테스트)

### 1. 기본 GET 요청 테스트

```python
# apps/users/tests.py
from django.test import TestCase
from ninja.testing import TestClient
from ninja import NinjaAPI
from .api import router
from .models import User

class TestUserAPI(TestCase):
    
    def setUp(self):
        """테스트 클라이언트 설정"""
        api = NinjaAPI()
        api.add_router("/users/", router)
        self.client = TestClient(api)
    
    def test_get_user_list(self):
        """사용자 목록 조회 테스트"""
        # Given: 테스트 데이터 생성
        User.objects.create(username="user1", email="user1@test.com")
        User.objects.create(username="user2", email="user2@test.com")
        
        # When: API 호출
        response = self.client.get("/users/")
        
        # Then: 응답 검증
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["username"], "user1")

    def test_get_user_detail(self):
        """특정 사용자 조회 테스트"""
        # Given
        user = User.objects.create(
            username="testuser", 
            email="test@example.com"
        )
        
        # When
        response = self.client.get(f"/users/{user.id}")
        
        # Then
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["username"], "testuser")
        self.assertEqual(data["email"], "test@example.com")
        
    def test_get_user_not_found(self):
        """존재하지 않는 사용자 조회 테스트"""
        # When
        response = self.client.get("/users/999")
        
        # Then
        self.assertEqual(response.status_code, 404)
```

### 2. POST 요청과 데이터 검증

```python
def test_create_user(self):
    """사용자 생성 테스트"""
    # Given
    user_data = {
        "username": "newuser",
        "email": "newuser@test.com",
        "password": "securepassword123"
    }
    
    # When
    response = self.client.post("/users/", json=user_data)
    
    # Then
    self.assertEqual(response.status_code, 201)
    data = response.json()
    self.assertEqual(data["username"], "newuser")
    self.assertNotIn("password", data)  # 패스워드는 응답에 포함되지 않아야 함
    
    # 데이터베이스 검증
    user = User.objects.get(username="newuser")
    self.assertEqual(user.email, "newuser@test.com")

def test_create_user_validation_error(self):
    """사용자 생성 시 유효성 검증 오류 테스트"""
    # Given: 잘못된 데이터
    invalid_data = {
        "username": "",  # 빈 사용자명
        "email": "invalid-email",  # 잘못된 이메일 형식
    }
    
    # When
    response = self.client.post("/users/", json=invalid_data)
    
    # Then
    self.assertEqual(response.status_code, 422)
    errors = response.json()["detail"]
    self.assertTrue(any("username" in str(error) for error in errors))
    self.assertTrue(any("email" in str(error) for error in errors))

def test_update_user(self):
    """사용자 정보 수정 테스트"""
    # Given
    user = User.objects.create(
        username="updateuser",
        email="update@test.com"
    )
    update_data = {
        "first_name": "Updated",
        "last_name": "Name"
    }
    
    # When
    response = self.client.patch(f"/users/{user.id}", json=update_data)
    
    # Then
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertEqual(data["first_name"], "Updated")
    self.assertEqual(data["last_name"], "Name")
    
    # 데이터베이스 검증
    user.refresh_from_db()
    self.assertEqual(user.first_name, "Updated")

def test_delete_user(self):
    """사용자 삭제 테스트"""
    # Given
    user = User.objects.create(
        username="deleteuser",
        email="delete@test.com"
    )
    
    # When
    response = self.client.delete(f"/users/{user.id}")
    
    # Then
    self.assertEqual(response.status_code, 200)
    
    # 데이터베이스에서 삭제 확인
    with self.assertRaises(User.DoesNotExist):
        User.objects.get(id=user.id)
```

### 3. 외부 API 모킹과 비동기 테스트

```python
from unittest.mock import patch, MagicMock

def test_user_with_external_data(self):
    """외부 API 호출이 포함된 사용자 조회 테스트"""
    # Given
    user = User.objects.create(
        username="testuser", 
        email="test@example.com"
    )
    
    # Mock 외부 API 응답
    mock_external_data = {
        "profile_image": "https://example.com/profile.jpg",
        "bio": "Test user bio"
    }
    
    # When
    with patch('apps.users.api.fetch_external_profile') as mock_fetch:
        mock_fetch.return_value = mock_external_data
        
        response = self.client.get(f"/users/{user.id}/profile")
    
    # Then
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertEqual(data["profile"]["bio"], "Test user bio")
    mock_fetch.assert_called_once_with(user.email)

def test_user_profile_external_api_error(self):
    """외부 API 오류 처리 테스트"""
    # Given
    user = User.objects.create(
        username="testuser",
        email="test@example.com"
    )
    
    # When
    with patch('apps.users.api.fetch_external_profile') as mock_fetch:
        mock_fetch.side_effect = Exception("External API Error")
        
        response = self.client.get(f"/users/{user.id}/profile")
    
    # Then
    self.assertEqual(response.status_code, 500)
    data = response.json()
    self.assertIn("error", data)
```

## 📊 다양한 테스트 전략

### 1. 전체 테스트 (Full Test Suite)

Django의 기본 테스트 러너를 사용하여 전체 프로젝트의 테스트를 실행합니다.

```bash
# 모든 테스트 실행
python manage.py test

# 특정 앱의 모든 테스트
python manage.py test apps.users

# 상세한 출력과 함께 실행
python manage.py test --verbosity=2

# 병렬 실행
python manage.py test --parallel

# 빠른 실행 (데이터베이스 보존)
python manage.py test --keepdb
```

**전체 테스트 설정 예제:**
```python
# tests.py (프로젝트 루트)
from django.test import TestCase
from ninja.testing import TestClient
from ninja import NinjaAPI
from apps.users.api import router as users_router
from apps.posts.api import router as posts_router

class TestFullAPIIntegration(TestCase):
    
    def setUp(self):
        """통합 테스트를 위한 API 설정"""
        api = NinjaAPI()
        api.add_router("/users/", users_router)
        api.add_router("/posts/", posts_router)
        self.client = TestClient(api)
    
    def test_complete_user_workflow(self):
        """사용자 생성부터 삭제까지 전체 워크플로우 테스트"""
        # 1. 사용자 생성
        user_data = {
            "username": "workflowuser",
            "email": "workflow@test.com",
            "password": "password123"
        }
        create_response = self.client.post("/users/", json=user_data)
        self.assertEqual(create_response.status_code, 201)
        user_id = create_response.json()["id"]
        
        # 2. 사용자 조회
        get_response = self.client.get(f"/users/{user_id}")
        self.assertEqual(get_response.status_code, 200)
        
        # 3. 사용자 수정
        update_data = {"first_name": "Updated"}
        update_response = self.client.patch(f"/users/{user_id}", json=update_data)
        self.assertEqual(update_response.status_code, 200)
        
        # 4. 포스트 생성
        post_data = {
            "title": "Test Post",
            "content": "Test content",
            "author_id": user_id
        }
        post_response = self.client.post("/posts/", json=post_data)
        self.assertEqual(post_response.status_code, 201)
        
        # 5. 사용자 삭제
        delete_response = self.client.delete(f"/users/{user_id}")
        self.assertEqual(delete_response.status_code, 200)
        
    def test_api_error_handling(self):
        """API 오류 처리 통합 테스트"""
        # 존재하지 않는 사용자 조회
        response = self.client.get("/users/99999")
        self.assertEqual(response.status_code, 404)
        
        # 잘못된 데이터로 사용자 생성
        invalid_data = {"username": ""}
        response = self.client.post("/users/", json=invalid_data)
        self.assertEqual(response.status_code, 422)
```

### 2. 앱별 테스트 (App-Level Testing)

각 Django 앱별로 독립적인 테스트를 실행합니다.

```bash
# 특정 앱의 테스트만 실행
python manage.py test apps.users
python manage.py test apps.posts

# 특정 테스트 클래스
python manage.py test apps.users.tests.TestUserAPI

# 특정 테스트 메서드
python manage.py test apps.users.tests.TestUserAPI.test_create_user
```

**앱별 테스트 구성 예제:**
```python
# apps/users/tests.py
from django.test import TestCase
from ninja.testing import TestClient
from ninja import NinjaAPI
from .api import router
from .models import User

class TestUserBusinessLogic(TestCase):
    
    def setUp(self):
        api = NinjaAPI()
        api.add_router("/users/", router)
        self.client = TestClient(api)
    
    def test_user_activation_workflow(self):
        """사용자 활성화 비즈니스 로직 테스트"""
        # Given
        user = User.objects.create(
            username="inactiveuser",
            email="inactive@test.com",
            is_active=False
        )
        
        # When
        activation_response = self.client.post(
            f"/users/{user.id}/activate",
            json={"activation_code": "123456"}
        )
        
        # Then
        self.assertEqual(activation_response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
    
    def test_user_search_functionality(self):
        """사용자 검색 기능 테스트"""
        # Given
        User.objects.create(username="john_doe", email="john@test.com")
        User.objects.create(username="jane_smith", email="jane@test.com")
        User.objects.create(username="bob_wilson", email="bob@test.com")
        
        # When
        search_response = self.client.get("/users/search?q=john")
        
        # Then
        self.assertEqual(search_response.status_code, 200)
        results = search_response.json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["username"], "john_doe")

# apps/posts/tests.py
from django.test import TestCase
from ninja.testing import TestClient
from ninja import NinjaAPI
from .api import router
from .models import Post
from apps.users.models import User

class TestPostOperations(TestCase):
    
    def setUp(self):
        api = NinjaAPI()
        api.add_router("/posts/", router)
        self.client = TestClient(api)
        
        # 테스트용 사용자 생성
        self.user = User.objects.create(
            username="author", 
            email="author@test.com"
        )
    
    def test_post_like_system(self):
        """포스트 좋아요 시스템 테스트"""
        # Given
        post = Post.objects.create(
            title="Test Post",
            content="Test content",
            author=self.user
        )
        
        # When
        like_response = self.client.post(f"/posts/{post.id}/like")
        
        # Then
        self.assertEqual(like_response.status_code, 200)
        data = like_response.json()
        self.assertEqual(data["likes_count"], 1)
        
    def test_post_comment_system(self):
        """포스트 댓글 시스템 테스트"""
        # Given
        post = Post.objects.create(
            title="Test Post",
            content="Test content",
            author=self.user
        )
        comment_data = {
            "content": "Great post!",
            "author_id": self.user.id
        }
        
        # When
        comment_response = self.client.post(
            f"/posts/{post.id}/comments", 
            json=comment_data
        )
        
        # Then
        self.assertEqual(comment_response.status_code, 201)
        data = comment_response.json()
        self.assertEqual(data["content"], "Great post!")
```

### 3. 클래스별/메서드별 테스트 (Specific Testing)

특정 테스트 클래스나 메서드만 실행하는 방법입니다.

```bash
# 특정 테스트 클래스 실행
python manage.py test apps.users.tests.TestUserAPI

# 특정 테스트 메서드 실행
python manage.py test apps.users.tests.TestUserAPI.test_create_user

# 패턴으로 테스트 실행
python manage.py test --pattern="*test_api*"

# 태그를 활용한 테스트 실행
python manage.py test --tag=unit
python manage.py test --tag=integration
```

### 4. 테스트 태그를 활용한 분류

Django의 테스트 태그 기능을 활용하여 테스트를 분류할 수 있습니다.

```python
from django.test import TestCase, tag
from ninja.testing import TestClient

class TestUserAPI(TestCase):
    
    @tag('unit', 'fast')
    def test_user_model_validation(self):
        """사용자 모델 유효성 검증 테스트 (빠른 단위 테스트)"""
        from .models import User
        
        user = User(username="testuser", email="test@example.com")
        self.assertTrue(user.clean())  # 유효성 검증 통과
        
    @tag('integration', 'api')
    def test_user_api_flow(self):
        """사용자 API 전체 흐름 테스트 (통합 테스트)"""
        # 사용자 생성 -> 조회 -> 수정 -> 삭제 전체 흐름
        user_data = {"username": "flowuser", "email": "flow@test.com"}
        
        # 생성
        create_response = self.client.post("/users/", json=user_data)
        self.assertEqual(create_response.status_code, 201)
        user_id = create_response.json()["id"]
        
        # 조회
        get_response = self.client.get(f"/users/{user_id}")
        self.assertEqual(get_response.status_code, 200)
        
        # 수정
        update_response = self.client.patch(
            f"/users/{user_id}", 
            json={"first_name": "Updated"}
        )
        self.assertEqual(update_response.status_code, 200)
        
        # 삭제
        delete_response = self.client.delete(f"/users/{user_id}")
        self.assertEqual(delete_response.status_code, 200)

    @tag('slow', 'performance')
    def test_bulk_user_operations(self):
        """대용량 사용자 처리 테스트 (느린 테스트)"""
        # 1000명의 사용자 생성 및 처리
        users = []
        for i in range(100):  # 테스트에서는 100명으로 축소
            user_data = {
                "username": f"user{i}",
                "email": f"user{i}@test.com"
            }
            response = self.client.post("/users/", json=user_data)
            self.assertEqual(response.status_code, 201)
            users.append(response.json())
        
        # 대량 조회 테스트
        response = self.client.get("/users/?limit=100")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 100)

    @tag('external', 'network')
    def test_external_api_integration(self):
        """외부 API 통합 테스트"""
        from unittest.mock import patch
        
        user = User.objects.create(username="extuser", email="ext@test.com")
        
        # 실제 외부 API 호출 시뮬레이션
        with patch('apps.users.api.fetch_external_profile') as mock_fetch:
            mock_fetch.return_value = {"status": "success"}
            
            response = self.client.get(f"/users/{user.id}/external-profile")
            self.assertEqual(response.status_code, 200)
```

**태그별 테스트 실행 예제:**
```bash
# 빠른 단위 테스트만 실행
python manage.py test --tag=unit --tag=fast

# 느린 테스트 제외하고 실행
python manage.py test --exclude-tag=slow

# API 관련 테스트만 실행
python manage.py test --tag=api

# 외부 서비스 의존성이 있는 테스트만 실행
python manage.py test --tag=external
```

## 🔍 고급 테스트 기법

### 1. 데이터베이스 트랜잭션 테스트

```python
from django.test import TestCase, TransactionTestCase
from django.db import transaction
from ninja.testing import TestClient

class TestDatabaseTransactions(TransactionTestCase):
    
    def setUp(self):
        from ninja import NinjaAPI
        from apps.users.api import router
        
        api = NinjaAPI()
        api.add_router("/users/", router)
        self.client = TestClient(api)
    
    def test_transaction_rollback(self):
        """트랜잭션 롤백 테스트"""
        from apps.users.models import User
        
        initial_count = User.objects.count()
        
        try:
            with transaction.atomic():
                # 사용자 생성
                User.objects.create(
                    username="user1", 
                    email="user1@test.com"
                )
                User.objects.create(
                    username="user2", 
                    email="user2@test.com"
                )
                
                # 의도적으로 예외 발생
                raise Exception("Test rollback")
                
        except Exception:
            pass
        
        # 롤백 확인
        final_count = User.objects.count()
        self.assertEqual(final_count, initial_count)
    
    def test_api_transaction_handling(self):
        """API에서 트랜잭션 처리 테스트"""
        # 잘못된 데이터로 사용자 생성 시도
        invalid_data = {
            "username": "testuser",
            "email": "invalid-email-format"
        }
        
        initial_count = User.objects.count()
        
        # API 호출
        response = self.client.post("/users/", json=invalid_data)
        self.assertEqual(response.status_code, 422)
        
        # 데이터베이스에 변경사항이 없는지 확인
        final_count = User.objects.count()
        self.assertEqual(final_count, initial_count)
```

### 2. 캐시 테스트

```python
from django.test import TestCase
from django.core.cache import cache
from ninja.testing import TestClient

class TestCacheIntegration(TestCase):
    
    def setUp(self):
        from ninja import NinjaAPI
        from apps.users.api import router
        
        api = NinjaAPI()
        api.add_router("/users/", router)
        self.client = TestClient(api)
        
        # 각 테스트 전에 캐시 초기화
        cache.clear()
    
    def test_cached_user_data(self):
        """캐시된 사용자 데이터 테스트"""
        from apps.users.models import User
        
        # Given
        user = User.objects.create(
            username="cacheduser", 
            email="cached@test.com"
        )
        
        # 첫 번째 요청 (캐시 생성)
        response1 = self.client.get(f"/users/{user.id}")
        self.assertEqual(response1.status_code, 200)
        
        # 캐시 확인
        cache_key = f"user_{user.id}"
        cached_data = cache.get(cache_key)
        self.assertIsNotNone(cached_data)
        
        # 두 번째 요청 (캐시 사용)
        response2 = self.client.get(f"/users/{user.id}")
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response1.json(), response2.json())
    
    def test_cache_invalidation(self):
        """캐시 무효화 테스트"""
        from apps.users.models import User
        
        # 사용자 생성 및 캐시
        user = User.objects.create(username="testuser", email="test@test.com")
        
        # 캐시 생성
        response1 = self.client.get(f"/users/{user.id}")
        self.assertEqual(response1.status_code, 200)
        
        # 사용자 정보 수정 (캐시 무효화 트리거)
        update_data = {"first_name": "Updated"}
        update_response = self.client.patch(f"/users/{user.id}", json=update_data)
        self.assertEqual(update_response.status_code, 200)
        
        # 캐시가 무효화되었는지 확인
        cache_key = f"user_{user.id}"
        cached_data = cache.get(cache_key)
        self.assertIsNone(cached_data)
        
        # 새로운 데이터로 응답하는지 확인
        response2 = self.client.get(f"/users/{user.id}")
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.json()["first_name"], "Updated")
```

### 3. 인증 테스트

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from ninja.testing import TestClient

User = get_user_model()

class TestAuthentication(TestCase):
    
    def setUp(self):
        from ninja import NinjaAPI
        from apps.users.api import router
        
        api = NinjaAPI()
        api.add_router("/users/", router)
        self.client = TestClient(api)
    
    def test_authenticated_endpoint(self):
        """인증이 필요한 엔드포인트 테스트"""
        # 사용자 생성
        user = User.objects.create_user(
            username="authuser",
            email="auth@test.com",
            password="testpass123"
        )
        
        # 로그인
        login_data = {
            "username": "authuser",
            "password": "testpass123"
        }
        login_response = self.client.post("/users/login", json=login_data)
        self.assertEqual(login_response.status_code, 200)
        
        # 토큰 추출
        token = login_response.json()["token"]
        
        # 인증 헤더 설정
        headers = {"Authorization": f"Bearer {token}"}
        
        # 인증된 요청
        response = self.client.get("/users/me", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "authuser")
        
    def test_unauthenticated_access(self):
        """인증되지 않은 접근 테스트"""
        # 인증되지 않은 요청
        response = self.client.get("/users/me")
        self.assertEqual(response.status_code, 401)
        
    def test_invalid_token(self):
        """잘못된 토큰 테스트"""
        # 잘못된 토큰으로 요청
        headers = {"Authorization": "Bearer invalid-token"}
        response = self.client.get("/users/me", headers=headers)
        self.assertEqual(response.status_code, 401)
        
    def test_permission_required(self):
        """권한이 필요한 엔드포인트 테스트"""
        # 일반 사용자 생성
        user = User.objects.create_user(
            username="normaluser",
            email="normal@test.com",
            password="testpass123"
        )
        
        # 관리자 사용자 생성
        admin_user = User.objects.create_user(
            username="adminuser",
            email="admin@test.com",
            password="testpass123",
            is_staff=True
        )
        
        # 일반 사용자로 관리자 전용 엔드포인트 접근
        login_response = self.client.post("/users/login", json={
            "username": "normaluser",
            "password": "testpass123"
        })
        user_token = login_response.json()["token"]
        
        response = self.client.get(
            "/users/admin/stats",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        self.assertEqual(response.status_code, 403)
        
        # 관리자로 접근
        admin_login_response = self.client.post("/users/login", json={
            "username": "adminuser",
            "password": "testpass123"
        })
        admin_token = admin_login_response.json()["token"]
        
        admin_response = self.client.get(
            "/users/admin/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(admin_response.status_code, 200)
```

## 📈 성능 테스트

### 1. 응답 시간 테스트

```python
import time
from django.test import TestCase
from ninja.testing import TestClient

class TestPerformance(TestCase):
    
    def setUp(self):
        from ninja import NinjaAPI
        from apps.users.api import router
        
        api = NinjaAPI()
        api.add_router("/users/", router)
        self.client = TestClient(api)
    
    def test_api_response_time(self):
        """API 응답 시간 테스트"""
        from apps.users.models import User
        
        # 테스트 데이터 생성
        user = User.objects.create(
            username="perfuser", 
            email="perf@test.com"
        )
        
        # 응답 시간 측정
        start_time = time.time()
        response = self.client.get(f"/users/{user.id}")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(response_time, 0.1)  # 100ms 이하
        
    def test_bulk_operation_performance(self):
        """대량 작업 성능 테스트"""
        from apps.users.models import User
        
        # 100명의 사용자 생성 시간 측정
        start_time = time.time()
        
        users_data = []
        for i in range(100):
            users_data.append({
                "username": f"perfuser{i}",
                "email": f"perfuser{i}@test.com"
            })
        
        # 대량 생성 API 호출
        response = self.client.post("/users/bulk-create", json={"users": users_data})
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        self.assertEqual(response.status_code, 201)
        self.assertLess(creation_time, 2.0)  # 2초 이하
        
        # 대량 조회 성능 테스트
        start_time = time.time()
        list_response = self.client.get("/users/?limit=100")
        end_time = time.time()
        
        query_time = end_time - start_time
        
        self.assertEqual(list_response.status_code, 200)
        self.assertLess(query_time, 0.5)  # 500ms 이하
        self.assertEqual(len(list_response.json()), 100)
```

### 2. 동시성 테스트

```python
import threading
import time
from django.test import TestCase
from ninja.testing import TestClient

class TestConcurrency(TestCase):
    
    def setUp(self):
        from ninja import NinjaAPI
        from apps.users.api import router
        
        api = NinjaAPI()
        api.add_router("/users/", router)
        self.client = TestClient(api)
    
    def test_concurrent_requests(self):
        """동시 요청 처리 테스트"""
        from apps.users.models import User
        
        # 테스트 사용자 생성
        user = User.objects.create(
            username="concurrentuser",
            email="concurrent@test.com"
        )
        
        results = []
        errors = []
        
        def make_request():
            try:
                response = self.client.get(f"/users/{user.id}")
                results.append(response.json())
            except Exception as e:
                errors.append(str(e))
        
        # 10개의 동시 요청 스레드 생성
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # 모든 스레드 시작
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        # 결과 검증
        self.assertEqual(len(errors), 0)  # 에러가 없어야 함
        self.assertEqual(len(results), 10)  # 모든 요청이 성공해야 함
        self.assertLess(end_time - start_time, 1.0)  # 1초 이내 완료
        
        # 모든 응답이 동일한 사용자 데이터인지 확인
        for result in results:
            self.assertEqual(result["username"], "concurrentuser")
    
    def test_race_condition_handling(self):
        """레이스 컨디션 처리 테스트"""
        from apps.users.models import User
        
        # 테스트 사용자 생성
        user = User.objects.create(
            username="raceuser",
            email="race@test.com",
            balance=1000  # 가상의 잔액 필드
        )
        
        results = []
        
        def update_balance():
            # 잔액 차감 시뮬레이션
            response = self.client.patch(
                f"/users/{user.id}/deduct-balance",
                json={"amount": 100}
            )
            results.append(response.status_code)
        
        # 동시에 5번의 잔액 차감 시도
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=update_balance)
            threads.append(thread)
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 모든 요청이 성공했는지 확인
        success_count = sum(1 for status in results if status == 200)
        
        # 레이스 컨디션이 적절히 처리되었는지 확인
        user.refresh_from_db()
        expected_balance = 1000 - (success_count * 100)
        self.assertEqual(user.balance, expected_balance)
```

## 🛠️ 실제 API 구현 예제

### 사용자 API (apps/users/api.py)

```python
from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from django.http import Http404
from .models import User
import asyncio

router = Router()

class UserSchema(Schema):
    id: int
    username: str
    email: str
    first_name: str = None
    last_name: str = None
    is_active: bool

class UserCreateSchema(Schema):
    username: str
    email: str
    password: str
    first_name: str = None
    last_name: str = None

class UserUpdateSchema(Schema):
    first_name: str = None
    last_name: str = None
    email: str = None

@router.get("/", response=list[UserSchema])
def list_users(request, limit: int = 10, offset: int = 0):
    """사용자 목록 조회"""
    users = User.objects.all()[offset:offset + limit]
    return [UserSchema.from_orm(user) for user in users]

@router.get("/{user_id}", response=UserSchema)
def get_user(request, user_id: int):
    """특정 사용자 조회"""
    try:
        user = User.objects.get(id=user_id)
        return UserSchema.from_orm(user)
    except User.DoesNotExist:
        raise Http404("User not found")

@router.post("/", response=UserSchema)
def create_user(request, data: UserCreateSchema):
    """사용자 생성"""
    user = User.objects.create(
        username=data.username,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name
    )
    if data.password:
        user.set_password(data.password)
        user.save()
    return UserSchema.from_orm(user)

@router.patch("/{user_id}", response=UserSchema)
def update_user(request, user_id: int, data: UserUpdateSchema):
    """사용자 정보 수정"""
    try:
        user = User.objects.get(id=user_id)
        
        if data.first_name is not None:
            user.first_name = data.first_name
        if data.last_name is not None:
            user.last_name = data.last_name
        if data.email is not None:
            user.email = data.email
            
        user.save()
        return UserSchema.from_orm(user)
    except User.DoesNotExist:
        raise Http404("User not found")

@router.delete("/{user_id}")
def delete_user(request, user_id: int):
    """사용자 삭제"""
    try:
        user = User.objects.get(id=user_id)
        user.delete()
        return {"message": "User deleted successfully"}
    except User.DoesNotExist:
        raise Http404("User not found")

# 외부 API 호출 시뮬레이션
def fetch_external_profile(email: str):
    """외부 프로필 API 호출 시뮬레이션"""
    import time
    time.sleep(0.1)  # 네트워크 지연 시뮬레이션
    return {
        "profile_image": f"https://api.example.com/profiles/{email}/image",
        "bio": f"Profile for {email}",
        "social_links": {
            "twitter": f"@{email.split('@')[0]}",
            "linkedin": f"linkedin.com/in/{email.split('@')[0]}"
        }
    }

@router.get("/{user_id}/profile")
def get_user_profile(request, user_id: int):
    """외부 데이터를 포함한 사용자 프로필 조회"""
    try:
        user = User.objects.get(id=user_id)
        profile_data = fetch_external_profile(user.email)
        
        return {
            "user": UserSchema.from_orm(user),
            "profile": profile_data
        }
    except User.DoesNotExist:
        raise Http404("User not found")
```

## 🚀 CI/CD 통합

### GitHub Actions 설정

```yaml
# .github/workflows/test.yml
name: Django Ninja Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
        
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        
    - name: Run unit tests
      run: |
        python manage.py test --tag=unit --verbosity=2
        
    - name: Run integration tests
      run: |
        python manage.py test --tag=integration --verbosity=2
        
    - name: Run performance tests
      run: |
        python manage.py test --tag=performance --verbosity=2
```

## 📊 테스트 모니터링 및 리포팅

### 커버리지 리포트

Django의 내장 테스트 커버리지 도구를 사용할 수 있습니다.

```bash
# coverage 패키지 설치
pip install coverage

# 커버리지와 함께 테스트 실행
coverage run --source='.' manage.py test

# HTML 리포트 생성
coverage html

# 터미널에서 커버리지 확인
coverage report

# 특정 임계값 설정
coverage report --fail-under=90
```

### 테스트 실행 시간 분석

```python
# test_utils.py
import time
import functools
from django.test import TestCase

def time_test(func):
    """테스트 실행 시간을 측정하는 데코레이터"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        result = func(self, *args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        
        if duration > 1.0:  # 1초 이상 걸리는 테스트 로깅
            print(f"\n⚠️  Slow test: {func.__name__} took {duration:.2f}s")
        
        return result
    return wrapper

# 사용 예제
class TestUserAPI(TestCase):
    
    @time_test
    def test_slow_operation(self):
        """느린 작업 테스트"""
        # 시간이 오래 걸리는 작업
        time.sleep(1.5)
        self.assertTrue(True)
```

## 🎯 모범 사례 및 팁

### 1. 테스트 데이터 관리

```python
# test_factories.py
from django.contrib.auth import get_user_model
from apps.posts.models import Post

User = get_user_model()

class TestDataFactory:
    """테스트 데이터 생성을 위한 팩토리 클래스"""
    
    @staticmethod
    def create_user(username=None, email=None, **kwargs):
        """테스트용 사용자 생성"""
        if not username:
            import uuid
            username = f"testuser_{uuid.uuid4().hex[:8]}"
        if not email:
            email = f"{username}@test.com"
            
        return User.objects.create(
            username=username,
            email=email,
            **kwargs
        )
    
    @staticmethod
    def create_post(author=None, title=None, **kwargs):
        """테스트용 포스트 생성"""
        if not author:
            author = TestDataFactory.create_user()
        if not title:
            import uuid
            title = f"Test Post {uuid.uuid4().hex[:8]}"
            
        return Post.objects.create(
            title=title,
            author=author,
            content="Test content",
            **kwargs
        )

# 테스트에서 사용
from django.test import TestCase

class TestUserAPI(TestCase):
    
    def test_with_factory(self):
        """팩토리를 사용한 테스트"""
        user = TestDataFactory.create_user(username="factoryuser")
        
        response = self.client.get(f"/users/{user.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "factoryuser")
        
    def test_with_multiple_users(self):
        """여러 사용자를 사용한 테스트"""
        users = [
            TestDataFactory.create_user() 
            for _ in range(5)
        ]
        
        response = self.client.get("/users/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 5)
```

### 2. 환경별 테스트 설정

```python
# settings/test.py
from .base import *
import sys

# 테스트용 데이터베이스
if 'test' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }

# 빠른 패스워드 해싱
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# 캐시 비활성화
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# 로깅 최소화
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    }
}

# 이메일 전송 비활성화
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'

# 미디어 파일 테스트 설정
MEDIA_ROOT = '/tmp/test_media'
```

### 3. 테스트 격리 및 정리

```python
from django.test import TestCase, TransactionTestCase
from django.core.cache import cache
from django.conf import settings
import tempfile
import shutil

class BaseTestCase(TestCase):
    """기본 테스트 케이스 클래스"""
    
    def setUp(self):
        """각 테스트 시작 전 설정"""
        # 캐시 초기화
        cache.clear()
        
        # 임시 미디어 디렉토리 생성
        self.temp_media_root = tempfile.mkdtemp()
        self.original_media_root = settings.MEDIA_ROOT
        settings.MEDIA_ROOT = self.temp_media_root
        
    def tearDown(self):
        """각 테스트 완료 후 정리"""
        # 임시 파일 정리
        if hasattr(self, 'temp_media_root'):
            shutil.rmtree(self.temp_media_root, ignore_errors=True)
            settings.MEDIA_ROOT = self.original_media_root
        
        # 캐시 정리
        cache.clear()

class TestUserAPI(BaseTestCase):
    """격리된 사용자 API 테스트"""
    
    def test_isolated_test(self):
        """격리된 테스트 예제"""
        # 이 테스트는 다른 테스트의 영향을 받지 않음
        user = TestDataFactory.create_user()
        
        response = self.client.get(f"/users/{user.id}")
        self.assertEqual(response.status_code, 200)

# 외부 서비스 모킹을 위한 믹스인
class MockExternalServicesMixin:
    """외부 서비스 모킹을 위한 믹스인"""
    
    def setUp(self):
        super().setUp()
        
        # 외부 API 모킹
        self.external_api_patcher = patch('apps.users.api.fetch_external_profile')
        self.mock_external_api = self.external_api_patcher.start()
        self.mock_external_api.return_value = {"bio": "Test bio"}
        
        # 이메일 전송 모킹
        self.email_patcher = patch('django.core.mail.send_mail')
        self.mock_send_mail = self.email_patcher.start()
        
    def tearDown(self):
        # 모킹 해제
        self.external_api_patcher.stop()
        self.email_patcher.stop()
        super().tearDown()

class TestUserAPIWithMocks(MockExternalServicesMixin, BaseTestCase):
    """외부 서비스 모킹이 포함된 테스트"""
    
    def test_with_external_api_mock(self):
        """외부 API 모킹 테스트"""
        user = TestDataFactory.create_user()
        
        response = self.client.get(f"/users/{user.id}/profile")
        self.assertEqual(response.status_code, 200)
        self.mock_external_api.assert_called_once()
```

## 🔚 결론

Django Ninja에서 TestClient와 AsyncTestClient를 활용한 TDD는 다음과 같은 이점을 제공합니다:

1. **신뢰성 높은 코드**: 테스트 우선 개발로 버그 감소
2. **유지보수성**: 리팩토링 시 안전성 보장
3. **문서화 효과**: 테스트가 API 사용법을 설명
4. **성능 검증**: AsyncTestClient로 실제 비동기 성능 특성 확인
5. **Django 통합**: Django의 기본 테스트 시스템과 완벽 통합

### 최적의 테스트 전략

**권장사항:**
- **기본 기능 테스트**: TestClient 사용 (빠르고 간단)
- **비동기 특성 테스트**: AsyncTestClient 사용 (정확한 검증)
- **성능 테스트**: AsyncTestClient 사용 (실제 동시성 측정)
- **CI/CD**: 두 가지 모두 활용하여 완전한 테스트 커버리지 확보

### 추천 개발 워크플로우

1. **Red**: 실패하는 테스트 작성
2. **Green**: 최소한의 구현으로 테스트 통과
3. **Refactor**: 코드 품질 개선
4. **Repeat**: 새로운 기능에 대해 반복

Django Ninja의 강력한 기능과 체계적인 테스트 전략을 결합하면, 확장 가능하고 안정적인 API를 구축할 수 있습니다. 

**TestClient와 AsyncTestClient를 적절히 조합하여 사용하면:**
- 개발 속도 향상 (TestClient로 빠른 피드백)
- 정확한 성능 검증 (AsyncTestClient로 실제 동작 확인)
- 완전한 테스트 커버리지 달성

이 가이드를 참고하여 여러분의 프로젝트에 맞는 최적의 테스트 전략을 개발해보세요!

---

*이 포스트가 도움이 되었다면 좋아요와 공유 부탁드립니다! Django Ninja 관련 질문이 있으시면 댓글로 남겨주세요.* 🚀
