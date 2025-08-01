---
layout: post
title: "Litestar 완전 입문 가이드: FastAPI 대안 고성능 Python 웹 프레임워크 시작하기"
date: 2025-08-01 10:00:00 +0900
categories: [Python, Web Framework, Backend, API]
tags: [Litestar, Python, FastAPI, ASGI, REST API, Web Framework, Backend Development, Async, Pydantic, SQLAlchemy]
---

FastAPI의 강력한 대안을 찾고 계신가요? Litestar는 현대적이고 고성능인 Python ASGI 웹 프레임워크로, 타입 안전성과 개발자 경험을 최우선으로 설계되었습니다. 이 글에서는 Litestar를 처음 접하는 개발자를 위해 기초부터 실제 애플리케이션 구축까지 단계별로 알아보겠습니다.

## 🌟 Litestar란 무엇인가?

### Litestar의 주요 특징

**Litestar**는 2023년에 등장한 비교적 새로운 Python 웹 프레임워크로, FastAPI와 유사하지만 몇 가지 독특한 장점을 가지고 있습니다:

- **🚀 고성능**: ASGI 기반으로 비동기 처리에 최적화
- **🔒 타입 안전성**: 강력한 타입 힌트와 런타임 검증
- **📚 풍부한 기능**: 의존성 주입, 미들웨어, 가드 등 내장
- **🛠️ 개발자 친화적**: 직관적인 API와 자동 문서 생성
- **🔧 유연성**: 플러그인 시스템으로 확장 가능

### FastAPI vs Litestar 비교

| 특징 | FastAPI | Litestar |
|------|---------|----------|
| 성능 | 매우 빠름 | 더 빠름 |
| 타입 안전성 | 좋음 | 매우 좋음 |
| 학습 곡선 | 완만함 | 중간 |
| 생태계 | 성숙함 | 성장 중 |
| 의존성 주입 | 기본적 | 고급 |
| 플러그인 시스템 | 제한적 | 강력함 |

## 🛠️ 개발 환경 설정

### 1. 가상환경 생성 및 Litestar 설치

```bash
# 가상환경 생성
python -m venv litestar-tutorial
source litestar-tutorial/bin/activate  # Linux/Mac
# litestar-tutorial\Scripts\activate  # Windows

# 기본 Litestar 설치
pip install litestar

# 전체 기능을 위한 설치 (권장)
pip install 'litestar[standard]'

# 개발에 필요한 추가 패키지
pip install uvicorn python-multipart
```

### 2. 프로젝트 구조 생성

```bash
mkdir litestar-tutorial
cd litestar-tutorial

# 기본 프로젝트 구조
mkdir -p {app,tests,docs}
touch app/__init__.py
touch app/main.py
touch requirements.txt
```

```text
# requirements.txt
litestar[standard]==2.8.3
uvicorn[standard]==0.23.2
python-multipart==0.0.6
```

## 🚀 첫 번째 Litestar 애플리케이션

### 1. Hello World 만들기

```python
# app/main.py
from litestar import Litestar, get

@get("/")
async def hello_world() -> dict[str, str]:
    """기본 인사 엔드포인트"""
    return {"message": "Hello, Litestar!"}

@get("/hello/{name:str}")
async def hello_name(name: str) -> dict[str, str]:
    """개인화된 인사 엔드포인트"""
    return {"message": f"Hello, {name}!"}

# Litestar 애플리케이션 생성
app = Litestar(
    route_handlers=[hello_world, hello_name],
    debug=True  # 개발 모드
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### 2. 애플리케이션 실행

```bash
# 방법 1: Python으로 직접 실행
python app/main.py

# 방법 2: uvicorn으로 실행 (권장)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

브라우저에서 `http://localhost:8000`을 열면 `{"message": "Hello, Litestar!"}`를 확인할 수 있습니다.

## 📊 HTTP 메서드와 라우팅

### 1. 다양한 HTTP 메서드 사용

```python
# app/routes.py
from litestar import delete, get, patch, post, put
from typing import Dict, Any

# 사용자 데이터 저장용 (실제 프로젝트에서는 데이터베이스 사용)
users_db: Dict[int, Dict[str, Any]] = {}
next_user_id = 1

@get("/users")
async def get_users() -> Dict[str, Any]:
    """모든 사용자 조회"""
    return {"users": list(users_db.values()), "count": len(users_db)}

@get("/users/{user_id:int}")
async def get_user(user_id: int) -> Dict[str, Any]:
    """특정 사용자 조회"""
    if user_id not in users_db:
        from litestar.exceptions import NotFoundException
        raise NotFoundException(detail=f"User {user_id} not found")
    
    return {"user": users_db[user_id]}

@post("/users")
async def create_user(data: Dict[str, Any]) -> Dict[str, Any]:
    """새 사용자 생성"""
    global next_user_id
    
    user = {
        "id": next_user_id,
        "name": data.get("name"),
        "email": data.get("email"),
        "age": data.get("age")
    }
    
    users_db[next_user_id] = user
    user_id = next_user_id
    next_user_id += 1
    
    return {"message": "User created", "user": user}

@put("/users/{user_id:int}")
async def update_user(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """사용자 정보 전체 업데이트"""
    if user_id not in users_db:
        from litestar.exceptions import NotFoundException
        raise NotFoundException(detail=f"User {user_id} not found")
    
    users_db[user_id].update(data)
    return {"message": "User updated", "user": users_db[user_id]}

@patch("/users/{user_id:int}")
async def partial_update_user(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """사용자 정보 부분 업데이트"""
    if user_id not in users_db:
        from litestar.exceptions import NotFoundException
        raise NotFoundException(detail=f"User {user_id} not found")
    
    # 제공된 필드만 업데이트
    for key, value in data.items():
        if key in users_db[user_id]:
            users_db[user_id][key] = value
    
    return {"message": "User partially updated", "user": users_db[user_id]}

@delete("/users/{user_id:int}")
async def delete_user(user_id: int) -> Dict[str, str]:
    """사용자 삭제"""
    if user_id not in users_db:
        from litestar.exceptions import NotFoundException
        raise NotFoundException(detail=f"User {user_id} not found")
    
    del users_db[user_id]
    return {"message": f"User {user_id} deleted"}
```

### 2. 라우트 그룹화와 컨트롤러

```python
# app/controllers/user_controller.py
from litestar import Controller, delete, get, patch, post, put
from typing import Dict, Any

class UserController(Controller):
    """사용자 관련 엔드포인트를 그룹화하는 컨트롤러"""
    
    path = "/users"  # 기본 경로
    tags = ["users"]  # OpenAPI 태그
    
    # 컨트롤러 레벨 의존성이나 가드를 여기서 정의 가능
    
    @get("/")
    async def list_users(self) -> Dict[str, Any]:
        """모든 사용자 목록 조회"""
        # 실제 구현은 위의 get_users와 동일
        return {"users": [], "message": "User list"}
    
    @get("/{user_id:int}")
    async def get_user_by_id(self, user_id: int) -> Dict[str, Any]:
        """ID로 사용자 조회"""
        return {"user_id": user_id, "message": "User details"}
    
    @post("/")
    async def create_new_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """새 사용자 생성"""
        return {"message": "User created", "data": data}
    
    @put("/{user_id:int}")
    async def update_existing_user(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """사용자 정보 업데이트"""
        return {"user_id": user_id, "message": "User updated", "data": data}
    
    @delete("/{user_id:int}")
    async def remove_user(self, user_id: int) -> Dict[str, str]:
        """사용자 삭제"""
        return {"message": f"User {user_id} deleted"}
```

## 📝 Pydantic 모델과 데이터 검증

### 1. 데이터 모델 정의

```python
# app/models.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """사용자 기본 모델"""
    name: str = Field(..., min_length=2, max_length=50, description="사용자 이름")
    email: EmailStr = Field(..., description="이메일 주소")
    age: int = Field(..., ge=0, le=150, description="나이")

class UserCreate(UserBase):
    """사용자 생성 모델"""
    password: str = Field(..., min_length=8, description="비밀번호 (최소 8자)")

class UserUpdate(BaseModel):
    """사용자 업데이트 모델 (모든 필드 선택적)"""
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    email: Optional[EmailStr] = None
    age: Optional[int] = Field(None, ge=0, le=150)

class User(UserBase):
    """사용자 응답 모델"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True  # ORM 모델에서 데이터 로드 허용

class UserResponse(BaseModel):
    """API 응답 모델"""
    success: bool = True
    message: str
    data: Optional[User] = None

class UserListResponse(BaseModel):
    """사용자 목록 응답 모델"""
    success: bool = True
    message: str
    data: list[User]
    total: int
    page: int
    per_page: int
```

### 2. 모델을 사용한 엔드포인트

```python
# app/controllers/user_controller_v2.py
from litestar import Controller, delete, get, patch, post, put
from litestar.params import Parameter
from litestar.pagination import OffsetPagination
from .models import User, UserCreate, UserUpdate, UserResponse, UserListResponse
from typing import Annotated

class UserControllerV2(Controller):
    """Pydantic 모델을 사용하는 개선된 사용자 컨트롤러"""
    
    path = "/api/v2/users"
    tags = ["users-v2"]
    
    @get("/")
    async def get_users(
        self,
        page: Annotated[int, Parameter(description="페이지 번호", ge=1)] = 1,
        per_page: Annotated[int, Parameter(description="페이지당 항목 수", ge=1, le=100)] = 10
    ) -> UserListResponse:
        """페이지네이션이 적용된 사용자 목록 조회"""
        
        # 실제로는 데이터베이스에서 조회
        users = []  # 여기에 실제 사용자 데이터
        total = len(users)
        
        return UserListResponse(
            message="Users retrieved successfully",
            data=users,
            total=total,
            page=page,
            per_page=per_page
        )
    
    @get("/{user_id:int}")
    async def get_user(self, user_id: int) -> UserResponse:
        """특정 사용자 조회"""
        # 실제로는 데이터베이스에서 조회
        # user = get_user_from_db(user_id)
        
        from litestar.exceptions import NotFoundException
        raise NotFoundException(detail=f"User {user_id} not found")
    
    @post("/")
    async def create_user(self, data: UserCreate) -> UserResponse:
        """새 사용자 생성"""
        # 비밀번호 해싱, 데이터베이스 저장 등의 로직
        
        # 예시 응답
        user_data = {
            "id": 1,
            "name": data.name,
            "email": data.email,
            "age": data.age,
            "created_at": "2025-08-01T10:00:00",
            "updated_at": "2025-08-01T10:00:00"
        }
        
        return UserResponse(
            message="User created successfully",
            data=User(**user_data)
        )
    
    @put("/{user_id:int}")
    async def update_user(self, user_id: int, data: UserUpdate) -> UserResponse:
        """사용자 정보 업데이트"""
        # 업데이트 로직 구현
        
        return UserResponse(
            message="User updated successfully"
        )
    
    @delete("/{user_id:int}")
    async def delete_user(self, user_id: int) -> UserResponse:
        """사용자 삭제"""
        # 삭제 로직 구현
        
        return UserResponse(
            message="User deleted successfully"
        )
```

## 🔧 의존성 주입 (Dependency Injection)

### 1. 기본 의존성 주입

```python
# app/dependencies.py
from litestar import Request
from typing import Dict, Any

def get_current_user(request: Request) -> Dict[str, Any]:
    """현재 사용자 정보를 가져오는 의존성"""
    # 실제로는 JWT 토큰 검증 등의 로직
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        from litestar.exceptions import NotAuthorizedException
        raise NotAuthorizedException(detail="Authentication required")
    
    # 토큰 검증 로직 (예시)
    token = auth_header.split(" ")[1]
    if token == "valid_token":
        return {"id": 1, "username": "testuser", "email": "test@example.com"}
    
    from litestar.exceptions import NotAuthorizedException
    raise NotAuthorizedException(detail="Invalid token")

def get_database_session():
    """데이터베이스 세션을 제공하는 의존성"""
    # 실제로는 SQLAlchemy 세션 등
    class MockDB:
        def query(self, table):
            return []
        
        def close(self):
            pass
    
    db = MockDB()
    try:
        yield db
    finally:
        db.close()

# 캐시 의존성
class CacheService:
    def __init__(self):
        self._cache = {}
    
    def get(self, key: str):
        return self._cache.get(key)
    
    def set(self, key: str, value: Any, ttl: int = 300):
        self._cache[key] = value
        # 실제로는 TTL 로직 구현

def get_cache_service() -> CacheService:
    """캐시 서비스 의존성"""
    return CacheService()
```

### 2. 의존성을 사용하는 엔드포인트

```python
# app/controllers/protected_controller.py
from litestar import Controller, Provide, get, post
from litestar.di import Provide
from ..dependencies import get_current_user, get_database_session, get_cache_service
from typing import Dict, Any

class ProtectedController(Controller):
    """인증이 필요한 엔드포인트들"""
    
    path = "/api/protected"
    tags = ["protected"]
    
    # 컨트롤러 레벨 의존성 (모든 엔드포인트에 적용)
    dependencies = {
        "current_user": Provide(get_current_user),
        "cache": Provide(get_cache_service)
    }
    
    @get("/profile")
    async def get_profile(self, current_user: Dict[str, Any]) -> Dict[str, Any]:
        """현재 사용자 프로필 조회"""
        return {
            "message": "Profile retrieved",
            "user": current_user
        }
    
    @get("/data")
    async def get_user_data(
        self, 
        current_user: Dict[str, Any],
        db_session = Provide(get_database_session),
        cache = Provide(get_cache_service)
    ) -> Dict[str, Any]:
        """캐시된 사용자 데이터 조회"""
        
        cache_key = f"user_data_{current_user['id']}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return {"message": "Data from cache", "data": cached_data}
        
        # 데이터베이스에서 조회
        data = db_session.query("user_data")
        
        # 캐시에 저장
        cache.set(cache_key, data, ttl=600)
        
        return {"message": "Data from database", "data": data}
    
    @post("/action")
    async def perform_action(
        self, 
        current_user: Dict[str, Any],
        request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """사용자 액션 수행"""
        return {
            "message": "Action performed",
            "user": current_user["username"],
            "action": request_data
        }
```

### 3. 애플리케이션에 의존성 등록

```python
# app/main.py (업데이트된 버전)
from litestar import Litestar
from litestar.di import Provide

from .controllers.user_controller import UserController
from .controllers.user_controller_v2 import UserControllerV2
from .controllers.protected_controller import ProtectedController
from .dependencies import get_cache_service

# 전역 의존성 설정
app = Litestar(
    route_handlers=[
        UserController,
        UserControllerV2,
        ProtectedController
    ],
    dependencies={
        "global_cache": Provide(get_cache_service)  # 모든 곳에서 사용 가능
    },
    debug=True
)
```

## 🛡️ 미들웨어와 가드

### 1. 커스텀 미들웨어 구현

```python
# app/middleware.py
from litestar.middleware.base import AbstractMiddleware
from litestar.types import ASGIApp, Receive, Scope, Send
from litestar import Request, Response
import time
import logging

logger = logging.getLogger(__name__)

class LoggingMiddleware(AbstractMiddleware):
    """요청/응답 로깅 미들웨어"""
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive, send)
        start_time = time.time()
        
        # 요청 로깅
        logger.info(f"[REQUEST] {request.method} {request.url}")
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                process_time = time.time() - start_time
                status_code = message["status"]
                logger.info(f"[RESPONSE] {status_code} - {process_time:.3f}s")
            await send(message)
        
        await self.app(scope, receive, send_wrapper)

class CORSMiddleware(AbstractMiddleware):
    """CORS 처리 미들웨어"""
    
    def __init__(self, app: ASGIApp, allow_origins: list[str] = None):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive, send)
        
        # Preflight 요청 처리
        if request.method == "OPTIONS":
            response = Response(status_code=200)
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            await response(scope, receive, send)
            return
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                message["headers"].append([b"access-control-allow-origin", b"*"])
            await send(message)
        
        await self.app(scope, receive, send_wrapper)

class RateLimitMiddleware(AbstractMiddleware):
    """간단한 비율 제한 미들웨어"""
    
    def __init__(self, app: ASGIApp, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # 실제로는 Redis 등 사용
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive, send)
        client_ip = request.client.host if request.client else "unknown"
        
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # 오래된 요청 기록 정리
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip] 
                if req_time > window_start
            ]
        else:
            self.requests[client_ip] = []
        
        # 비율 제한 확인
        if len(self.requests[client_ip]) >= self.max_requests:
            from litestar.exceptions import TooManyRequestsException
            response = Response(
                content={"error": "Too many requests"},
                status_code=429
            )
            await response(scope, receive, send)
            return
        
        # 현재 요청 기록
        self.requests[client_ip].append(current_time)
        
        await self.app(scope, receive, send)
```

### 2. 가드 (Guards) 구현

```python
# app/guards.py
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.handlers.base import BaseRouteHandler
from typing import Dict, Any

def authentication_guard(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
    """인증 가드 - 유효한 토큰이 있는지 확인"""
    auth_header = connection.headers.get("authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise NotAuthorizedException(detail="Authentication required")
    
    token = auth_header.split(" ")[1]
    
    # 토큰 검증 로직 (예시)
    if token != "valid_token":
        raise NotAuthorizedException(detail="Invalid authentication token")

def admin_guard(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
    """관리자 권한 가드"""
    # 먼저 인증 확인
    authentication_guard(connection, route_handler)
    
    # 사용자 권한 확인 (실제로는 JWT에서 추출)
    auth_header = connection.headers.get("authorization")
    token = auth_header.split(" ")[1]
    
    # 예시: 특정 토큰만 관리자로 인정
    if token != "admin_token":
        raise PermissionDeniedException(detail="Admin privileges required")

def api_key_guard(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
    """API 키 가드"""
    api_key = connection.headers.get("x-api-key")
    
    if not api_key:
        raise NotAuthorizedException(detail="API key required")
    
    # API 키 검증 (실제로는 데이터베이스에서)
    valid_keys = ["test-api-key-123", "production-key-456"]
    
    if api_key not in valid_keys:
        raise NotAuthorizedException(detail="Invalid API key")

def rate_limit_guard(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
    """비율 제한 가드 (미들웨어와 별도로 특정 엔드포인트용)"""
    # 실제로는 더 정교한 로직 구현
    user_id = connection.headers.get("x-user-id")
    
    if not user_id:
        raise NotAuthorizedException(detail="User identification required")
    
    # 비율 제한 로직...
    pass
```

### 3. 가드를 적용한 컨트롤러

```python
# app/controllers/admin_controller.py
from litestar import Controller, get, post, delete
from litestar.params import Parameter
from ..guards import admin_guard, api_key_guard
from typing import Dict, Any, Annotated

class AdminController(Controller):
    """관리자 전용 엔드포인트"""
    
    path = "/api/admin"
    tags = ["admin"]
    guards = [admin_guard]  # 모든 엔드포인트에 관리자 가드 적용
    
    @get("/users")
    async def get_all_users_admin(self) -> Dict[str, Any]:
        """관리자용 모든 사용자 조회"""
        return {
            "message": "All users (admin view)",
            "users": [],
            "total": 0
        }
    
    @delete("/users/{user_id:int}")
    async def delete_user_admin(self, user_id: int) -> Dict[str, str]:
        """관리자용 사용자 삭제"""
        return {"message": f"User {user_id} deleted by admin"}
    
    @get("/stats", guards=[api_key_guard])  # 추가 가드 적용
    async def get_system_stats(self) -> Dict[str, Any]:
        """시스템 통계 (API 키도 필요)"""
        return {
            "total_users": 100,
            "active_sessions": 25,
            "server_uptime": "5 days",
            "memory_usage": "2.1 GB"
        }
    
    @post("/maintenance")
    async def toggle_maintenance_mode(
        self,
        enabled: Annotated[bool, Parameter(description="유지보수 모드 활성화 여부")]
    ) -> Dict[str, Any]:
        """유지보수 모드 토글"""
        return {
            "message": f"Maintenance mode {'enabled' if enabled else 'disabled'}",
            "maintenance_mode": enabled
        }
```

## 📚 데이터베이스 연동 (SQLAlchemy)

### 1. SQLAlchemy 설정

```python
# app/database.py
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from datetime import datetime
import os

# 데이터베이스 URL (환경변수에서 가져오거나 기본값 사용)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./litestar_tutorial.db")

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    echo=True,  # SQL 쿼리 로깅 (개발 시에만)
    pool_pre_ping=True  # 연결 상태 확인
)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스
Base = declarative_base()

# 데이터베이스 세션 의존성
def get_db_session() -> Session:
    """데이터베이스 세션을 생성하고 반환"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 데이터베이스 모델
class UserModel(Base):
    """사용자 데이터베이스 모델"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    age = Column(Integer, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class PostModel(Base):
    """게시글 데이터베이스 모델"""
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, nullable=False, index=True)  # 실제로는 ForeignKey 사용
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 테이블 생성
def create_tables():
    """데이터베이스 테이블 생성"""
    Base.metadata.create_all(bind=engine)

# 개발용 샘플 데이터 생성
def create_sample_data():
    """개발용 샘플 데이터 생성"""
    db = SessionLocal()
    try:
        # 사용자가 이미 있는지 확인
        existing_user = db.query(UserModel).filter(UserModel.email == "test@example.com").first()
        if not existing_user:
            sample_user = UserModel(
                name="Test User",
                email="test@example.com",
                age=25,
                password_hash="hashed_password_here"
            )
            db.add(sample_user)
            db.commit()
            
            # 샘플 게시글
            sample_post = PostModel(
                title="Welcome to Litestar!",
                content="This is a sample post created with Litestar and SQLAlchemy.",
                author_id=sample_user.id
            )
            db.add(sample_post)
            db.commit()
            
            print("Sample data created successfully!")
    finally:
        db.close()
```

### 2. 데이터베이스를 사용하는 서비스 레이어

```python
# app/services/user_service.py
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ..database import UserModel
from ..models import UserCreate, UserUpdate, User
from typing import Optional, List
import hashlib

class UserService:
    """사용자 관련 비즈니스 로직"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def hash_password(self, password: str) -> str:
        """비밀번호 해싱 (실제로는 bcrypt 등 사용)"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def get_user_by_id(self, user_id: int) -> Optional[UserModel]:
        """ID로 사용자 조회"""
        return self.db.query(UserModel).filter(UserModel.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        """이메일로 사용자 조회"""
        return self.db.query(UserModel).filter(UserModel.email == email).first()
    
    def get_users(self, skip: int = 0, limit: int = 100) -> List[UserModel]:
        """사용자 목록 조회 (페이지네이션)"""
        return self.db.query(UserModel).offset(skip).limit(limit).all()
    
    def search_users(self, query: str) -> List[UserModel]:
        """사용자 검색"""
        search_pattern = f"%{query}%"
        return self.db.query(UserModel).filter(
            or_(
                UserModel.name.ilike(search_pattern),
                UserModel.email.ilike(search_pattern)
            )
        ).all()
    
    def create_user(self, user_data: UserCreate) -> UserModel:
        """새 사용자 생성"""
        # 이메일 중복 확인
        existing_user = self.get_user_by_email(user_data.email)
        if existing_user:
            raise ValueError("Email already registered")
        
        # 새 사용자 생성
        db_user = UserModel(
            name=user_data.name,
            email=user_data.email,
            age=user_data.age,
            password_hash=self.hash_password(user_data.password)
        )
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        return db_user
    
    def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[UserModel]:
        """사용자 정보 업데이트"""
        db_user = self.get_user_by_id(user_id)
        if not db_user:
            return None
        
        # 업데이트할 필드만 수정
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        self.db.commit()
        self.db.refresh(db_user)
        
        return db_user
    
    def delete_user(self, user_id: int) -> bool:
        """사용자 삭제"""
        db_user = self.get_user_by_id(user_id)
        if not db_user:
            return False
        
        self.db.delete(db_user)
        self.db.commit()
        
        return True
    
    def get_user_count(self) -> int:
        """전체 사용자 수"""
        return self.db.query(UserModel).count()
```

### 3. 데이터베이스를 사용하는 컨트롤러

```python
# app/controllers/db_user_controller.py
from litestar import Controller, get, post, put, delete, Provide
from litestar.params import Parameter
from litestar.exceptions import NotFoundException, ValidationException
from sqlalchemy.orm import Session
from typing import Annotated, List

from ..database import get_db_session, UserModel
from ..services.user_service import UserService
from ..models import User, UserCreate, UserUpdate, UserResponse, UserListResponse

class DatabaseUserController(Controller):
    """데이터베이스를 사용하는 사용자 컨트롤러"""
    
    path = "/api/v3/users"
    tags = ["users-v3"]
    
    dependencies = {
        "db": Provide(get_db_session),
    }
    
    @get("/")
    async def list_users(
        self,
        db: Session,
        page: Annotated[int, Parameter(description="페이지 번호", ge=1)] = 1,
        per_page: Annotated[int, Parameter(description="페이지당 항목 수", ge=1, le=100)] = 10,
        search: Annotated[str, Parameter(description="검색 쿼리")] = None
    ) -> UserListResponse:
        """사용자 목록 조회 (검색 기능 포함)"""
        
        user_service = UserService(db)
        
        if search:
            users = user_service.search_users(search)
            total = len(users)
            # 간단한 페이지네이션
            start = (page - 1) * per_page
            end = start + per_page
            users = users[start:end]
        else:
            skip = (page - 1) * per_page
            users = user_service.get_users(skip=skip, limit=per_page)
            total = user_service.get_user_count()
        
        # Pydantic 모델로 변환
        user_list = [
            User(
                id=user.id,
                name=user.name,
                email=user.email,
                age=user.age,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            for user in users
        ]
        
        return UserListResponse(
            message="Users retrieved successfully",
            data=user_list,
            total=total,
            page=page,
            per_page=per_page
        )
    
    @get("/{user_id:int}")
    async def get_user(self, user_id: int, db: Session) -> UserResponse:
        """특정 사용자 조회"""
        user_service = UserService(db)
        db_user = user_service.get_user_by_id(user_id)
        
        if not db_user:
            raise NotFoundException(detail=f"User {user_id} not found")
        
        user = User(
            id=db_user.id,
            name=db_user.name,
            email=db_user.email,
            age=db_user.age,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )
        
        return UserResponse(
            message="User retrieved successfully",
            data=user
        )
    
    @post("/")
    async def create_user(self, data: UserCreate, db: Session) -> UserResponse:
        """새 사용자 생성"""
        user_service = UserService(db)
        
        try:
            db_user = user_service.create_user(data)
        except ValueError as e:
            raise ValidationException(detail=str(e))
        
        user = User(
            id=db_user.id,
            name=db_user.name,
            email=db_user.email,
            age=db_user.age,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )
        
        return UserResponse(
            message="User created successfully",
            data=user
        )
    
    @put("/{user_id:int}")
    async def update_user(self, user_id: int, data: UserUpdate, db: Session) -> UserResponse:
        """사용자 정보 업데이트"""
        user_service = UserService(db)
        db_user = user_service.update_user(user_id, data)
        
        if not db_user:
            raise NotFoundException(detail=f"User {user_id} not found")
        
        user = User(
            id=db_user.id,
            name=db_user.name,
            email=db_user.email,
            age=db_user.age,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )
        
        return UserResponse(
            message="User updated successfully",
            data=user
        )
    
    @delete("/{user_id:int}")
    async def delete_user(self, user_id: int, db: Session) -> UserResponse:
        """사용자 삭제"""
        user_service = UserService(db)
        if not success:
            raise NotFoundException(detail=f"User {user_id} not found")
        
        return UserResponse(
            message="User deleted successfully"
        )
```

## 🔧 예외 처리와 에러 핸들링

### 1. 커스텀 예외 정의

```python
# app/exceptions.py
from litestar.exceptions import LitestarException
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

class UserNotFoundException(LitestarException):
    """사용자를 찾을 수 없을 때 발생하는 예외"""
    status_code = HTTP_404_NOT_FOUND
    detail = "User not found"

class EmailAlreadyExistsException(LitestarException):
    """이메일이 이미 존재할 때 발생하는 예외"""
    status_code = HTTP_409_CONFLICT
    detail = "Email already exists"

class InvalidDataException(LitestarException):
    """잘못된 데이터가 제공될 때 발생하는 예외"""
    status_code = HTTP_400_BAD_REQUEST
    detail = "Invalid data provided"

class BusinessLogicException(LitestarException):
    """비즈니스 로직 에러"""
    status_code = HTTP_400_BAD_REQUEST
    
    def __init__(self, detail: str, status_code: int = HTTP_400_BAD_REQUEST):
        super().__init__(detail)
        self.status_code = status_code
```

### 2. 전역 예외 핸들러

```python
# app/exception_handlers.py
from litestar import Request, Response
from litestar.exceptions import ValidationException, NotFoundException
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def validation_exception_handler(request: Request, exc: ValidationException) -> Response:
    """입력 검증 예외 핸들러"""
    return Response(
        content={
            "error": "Validation Error",
            "detail": exc.detail,
            "status_code": exc.status_code
        },
        status_code=exc.status_code
    )

def not_found_exception_handler(request: Request, exc: NotFoundException) -> Response:
    """404 예외 핸들러"""
    return Response(
        content={
            "error": "Not Found",
            "detail": exc.detail,
            "path": str(request.url)
        },
        status_code=exc.status_code
    )

def generic_exception_handler(request: Request, exc: Exception) -> Response:
    """일반 예외 핸들러"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    
    return Response(
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred",
            "status_code": HTTP_500_INTERNAL_SERVER_ERROR
        },
        status_code=HTTP_500_INTERNAL_SERVER_ERROR
    )

def business_logic_exception_handler(request: Request, exc: Exception) -> Response:
    """비즈니스 로직 예외 핸들러"""
    from .exceptions import BusinessLogicException
    
    if isinstance(exc, BusinessLogicException):
        return Response(
            content={
                "error": "Business Logic Error",
                "detail": exc.detail,
                "status_code": exc.status_code
            },
            status_code=exc.status_code
        )
    
    return generic_exception_handler(request, exc)
```

## 📄 파일 업로드와 정적 파일 처리

### 1. 파일 업로드 핸들러

```python
# app/controllers/file_controller.py
from litestar import Controller, post, get
from litestar.datastructures import UploadFile
from litestar.params import Body
from litestar.exceptions import ValidationException
from litestar.response import File
from typing import List, Optional
import os
import uuid
from pathlib import Path

class FileController(Controller):
    """파일 업로드 및 다운로드"""
    
    path = "/api/files"
    tags = ["files"]
    
    def __init__(self):
        # 업로드 디렉토리 설정
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)
        
        # 허용된 파일 확장자
        self.allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".txt", ".docx"}
        self.max_file_size = 10 * 1024 * 1024  # 10MB
    
    def validate_file(self, file: UploadFile) -> None:
        """파일 검증"""
        # 파일 크기 확인
        if file.size > self.max_file_size:
            raise ValidationException(detail="File size too large (max 10MB)")
        
        # 파일 확장자 확인
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in self.allowed_extensions:
            raise ValidationException(
                detail=f"File type not allowed. Allowed: {', '.join(self.allowed_extensions)}"
            )
    
    @post("/upload")
    async def upload_file(self, file: UploadFile = Body()) -> dict:
        """단일 파일 업로드"""
        self.validate_file(file)
        
        # 고유한 파일명 생성
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = self.upload_dir / unique_filename
        
        # 파일 저장
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        return {
            "message": "File uploaded successfully",
            "filename": unique_filename,
            "original_filename": file.filename,
            "size": file.size,
            "content_type": file.content_type
        }
    
    @post("/upload-multiple")
    async def upload_multiple_files(self, files: List[UploadFile] = Body()) -> dict:
        """다중 파일 업로드"""
        if len(files) > 5:
            raise ValidationException(detail="Too many files (max 5)")
        
        uploaded_files = []
        
        for file in files:
            self.validate_file(file)
            
            # 고유한 파일명 생성
            file_extension = Path(file.filename).suffix
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = self.upload_dir / unique_filename
            
            # 파일 저장
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            uploaded_files.append({
                "filename": unique_filename,
                "original_filename": file.filename,
                "size": file.size,
                "content_type": file.content_type
            })
        
        return {
            "message": f"{len(uploaded_files)} files uploaded successfully",
            "files": uploaded_files
        }
    
    @get("/download/{filename:str}")
    async def download_file(self, filename: str) -> File:
        """파일 다운로드"""
        file_path = self.upload_dir / filename
        
        if not file_path.exists():
            from litestar.exceptions import NotFoundException
            raise NotFoundException(detail="File not found")
        
        return File(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream"
        )
    
    @get("/list")
    async def list_files(self) -> dict:
        """업로드된 파일 목록"""
        files = []
        
        for file_path in self.upload_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime
                })
        
        return {
            "message": "File list retrieved",
            "files": files,
            "total": len(files)
        }
```

## 🚀 최종 애플리케이션 구성

### 1. 완전한 main.py

```python
# app/main.py
from litestar import Litestar, Request, Response
from litestar.config.cors import CORSConfig
from litestar.config.compression import CompressionConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.exceptions import ValidationException, NotFoundException
from litestar.static_files import create_static_files_router
from litestar.di import Provide
import logging

# 컨트롤러 임포트
from .controllers.user_controller import UserController
from .controllers.user_controller_v2 import UserControllerV2
from .controllers.db_user_controller import DatabaseUserController
from .controllers.protected_controller import ProtectedController
from .controllers.admin_controller import AdminController
from .controllers.file_controller import FileController

# 미들웨어와 의존성 임포트
from .middleware import LoggingMiddleware, RateLimitMiddleware
from .dependencies import get_cache_service
from .database import get_db_session, create_tables, create_sample_data
from .exception_handlers import (
    validation_exception_handler,
    not_found_exception_handler,
    generic_exception_handler
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# CORS 설정
cors_config = CORSConfig(
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    allow_credentials=True
)

# 압축 설정
compression_config = CompressionConfig(backend="gzip", gzip_compress_level=6)

# 정적 파일 라우터
static_files_router = create_static_files_router(
    path="/static",
    directories=["static"],
    name="static"
)

# Litestar 애플리케이션 생성
app = Litestar(
    # 라우트 핸들러
    route_handlers=[
        UserController,
        UserControllerV2,
        DatabaseUserController,
        ProtectedController,
        AdminController,
        FileController,
        static_files_router
    ],
    
    # 미들웨어
    middleware=[
        LoggingMiddleware,
        RateLimitMiddleware
    ],
    
    # 전역 의존성
    dependencies={
        "cache": Provide(get_cache_service),
        "db": Provide(get_db_session)
    },
    
    # 예외 핸들러
    exception_handlers={
        ValidationException: validation_exception_handler,
        NotFoundException: not_found_exception_handler,
        Exception: generic_exception_handler
    },
    
    # 설정
    cors_config=cors_config,
    compression_config=compression_config,
    
    # 개발 모드
    debug=True,
    
    # OpenAPI 설정
    openapi_config={
        "title": "Litestar Tutorial API",
        "version": "1.0.0",
        "description": "A comprehensive Litestar tutorial API",
        "contact": {
            "name": "Tutorial Author",
            "email": "author@example.com"
        }
    }
)

# 애플리케이션 시작 시 실행되는 이벤트
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    # 데이터베이스 테이블 생성
    create_tables()
    
    # 샘플 데이터 생성 (개발 모드에서만)
    if app.debug:
        create_sample_data()
    
    print("🚀 Litestar application started successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    print("👋 Litestar application shutting down...")

# 헬스체크 엔드포인트
@app.get("/health")
async def health_check() -> dict:
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "Litestar Tutorial API",
        "version": "1.0.0"
    }

# 개발 서버 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
```

## 🎯 마무리

이제 Litestar를 사용하여 완전한 웹 API를 구축하는 방법을 배웠습니다! 

### 🎉 완성된 기능들

- ✅ **기본 라우팅**: GET, POST, PUT, DELETE 엔드포인트
- ✅ **데이터 검증**: Pydantic 모델을 활용한 타입 안전성
- ✅ **의존성 주입**: 재사용 가능한 의존성 시스템
- ✅ **미들웨어**: 로깅, CORS, 비율 제한
- ✅ **가드**: 인증 및 권한 검사
- ✅ **데이터베이스**: SQLAlchemy를 활용한 ORM
- ✅ **파일 업로드**: 파일 처리 및 검증
- ✅ **예외 처리**: 체계적인 에러 핸들링
- ✅ **문서화**: 자동 OpenAPI 문서 생성

### 🚀 다음 학습 방향

1. **고급 기능**: WebSocket, 백그라운드 태스크, 캐싱
2. **보안**: JWT 인증, OAuth2, HTTPS
3. **성능 최적화**: 데이터베이스 최적화, 캐싱 전략
4. **모니터링**: 로깅, 메트릭, 헬스체크
5. **배포**: CI/CD, 컨테이너 오케스트레이션

Litestar는 강력하면서도 직관적인 프레임워크입니다. 이 튜토리얼을 바탕으로 더 복잡한 애플리케이션을 구축해보세요! 🌟

이제 첫 번째 부분이 완성되었습니다. 다음 단계를 계속 진행하겠습니다.
