---
layout: post
title: "FastAPI와 Neon PostgreSQL로 Raw SQL 기반 API 개발하기"
date: 2025-10-01 10:00:00 +0900
categories: [Web Development, Backend, Database]
tags: [fastapi, neon, postgresql, raw-sql, database, api, python, asyncio]
description: "FastAPI와 클라우드 PostgreSQL 서비스인 Neon을 연동하여 Raw SQL을 사용한 고성능 API를 개발하는 완전한 가이드입니다. ORM 없이 순수 SQL로 데이터베이스를 다루는 방법을 배워보세요."
author: "updaun"
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-10-01-fastapi-neon-postgres-raw-sql-guide.webp"
---

## 개요

FastAPI는 현대적이고 빠른 Python 웹 프레임워크이며, Neon은 서버리스 PostgreSQL 플랫폼입니다. 이 두 기술을 조합하여 Raw SQL을 사용한 고성능 API를 개발하는 방법을 알아보겠습니다. ORM을 사용하지 않고 순수 SQL로 데이터베이스를 다루면서도 안전하고 효율적인 애플리케이션을 구축해보겠습니다.

## Neon PostgreSQL의 장점

### 1. 서버리스 아키텍처
- **자동 스케일링**: 트래픽에 따른 자동 확장/축소
- **콜드 스타트**: 사용하지 않을 때 자동 일시정지
- **무제한 브랜치**: Git처럼 데이터베이스 브랜치 생성

### 2. 개발자 친화적
- **빠른 설정**: 몇 분 내 데이터베이스 구축
- **Git 연동**: 브랜치별 데이터베이스 환경
- **백업 자동화**: 시점 복구 지원

### 3. 비용 효율성
- **종량제**: 사용한 만큼만 과금
- **무료 티어**: 개발/테스트용 무료 제공
- **투명한 가격**: 예측 가능한 비용 구조

## Raw SQL 사용의 이점

### 1. 성능 최적화
- **직접적인 쿼리 제어**: 정확한 SQL 실행
- **인덱스 활용**: 최적화된 쿼리 작성
- **복잡한 조인**: 고급 SQL 기능 활용

### 2. 유연성
- **PostgreSQL 특화 기능**: JSON, 배열, 풀텍스트 검색
- **저장 프로시저**: 비즈니스 로직을 DB에서 처리
- **커스텀 함수**: 특별한 요구사항 대응

### 3. 투명성
- **명확한 쿼리**: 실행되는 SQL을 정확히 파악
- **디버깅 용이**: 쿼리 성능 분석 가능
- **학습 효과**: SQL 실력 향상

## 프로젝트 설정

### 1. Neon 데이터베이스 설정

먼저 [Neon Console](https://console.neon.tech)에서 프로젝트를 생성합니다.

```bash
# 1. Neon Console에 로그인
# 2. 새 프로젝트 생성
# 3. 데이터베이스 이름: fastapi_blog
# 4. 리전 선택: Asia Pacific (Tokyo) - ap-southeast-1
# 5. PostgreSQL 버전: 15 (최신 안정 버전)
```

### 2. 환경 설정

```bash
# 가상환경 생성
python -m venv fastapi_neon_env
source fastapi_neon_env/bin/activate  # Linux/Mac
# fastapi_neon_env\Scripts\activate  # Windows

# 필수 패키지 설치
pip install fastapi uvicorn
pip install asyncpg  # PostgreSQL 비동기 드라이버
pip install python-decouple  # 환경변수 관리
pip install pydantic[email]  # 데이터 검증
pip install python-jose[cryptography]  # JWT 토큰
pip install passlib[bcrypt]  # 비밀번호 해싱
pip install python-multipart  # 파일 업로드
pip install aiofiles  # 비동기 파일 처리

# 개발 도구
pip install pytest pytest-asyncio  # 테스트
pip install black isort  # 코드 포맷팅
pip install httpx  # HTTP 클라이언트 (테스트용)

# requirements.txt 생성
pip freeze > requirements.txt
```

### 3. 프로젝트 구조

```
fastapi_neon_project/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 앱 메인
│   ├── database.py          # 데이터베이스 연결
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic 스키마
│   ├── api/
│   │   ├── __init__.py
│   │   ├── users.py         # 사용자 관련 엔드포인트
│   │   ├── posts.py         # 게시글 관련 엔드포인트
│   │   └── auth.py          # 인증 관련 엔드포인트
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # 설정
│   │   ├── security.py      # 보안 관련
│   │   └── dependencies.py  # 의존성 주입
│   └── sql/
│       ├── __init__.py
│       ├── users.py         # 사용자 SQL 쿼리
│       ├── posts.py         # 게시글 SQL 쿼리
│       └── migrations.py    # 스키마 마이그레이션
├── tests/
├── .env
├── .gitignore
└── requirements.txt
```

### 4. 환경 변수 설정

```bash
# .env
# Neon PostgreSQL 연결 정보
DATABASE_URL=postgresql://username:password@ep-xxx-xxx.ap-southeast-1.aws.neon.tech/fastapi_blog?sslmode=require

# 애플리케이션 설정
SECRET_KEY=your-secret-key-here-make-it-long-and-random
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 환경 설정
ENVIRONMENT=development
DEBUG=True

# API 설정
API_V1_STR=/api/v1
PROJECT_NAME=FastAPI Neon Blog
VERSION=1.0.0
```

## 데이터베이스 연결 설정

### 1. 데이터베이스 연결 매니저

```python
# app/database.py
import asyncpg
import asyncio
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """데이터베이스 연결 관리자"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False
    
    async def initialize(self):
        """데이터베이스 풀 초기화"""
        if self._initialized:
            return
        
        try:
            # 연결 풀 생성
            self.pool = await asyncpg.create_pool(
                dsn=settings.DATABASE_URL,
                min_size=5,
                max_size=20,
                max_queries=50000,
                max_inactive_connection_lifetime=300,  # 5분
                timeout=60,
                command_timeout=60
            )
            
            # 연결 테스트
            async with self.pool.acquire() as conn:
                await conn.execute('SELECT 1')
                logger.info("✅ 데이터베이스 연결 성공")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"❌ 데이터베이스 연결 실패: {e}")
            raise
    
    async def close(self):
        """데이터베이스 풀 종료"""
        if self.pool:
            await self.pool.close()
            logger.info("📁 데이터베이스 연결 종료")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """데이터베이스 연결 컨텍스트 매니저"""
        if not self.pool:
            raise RuntimeError("데이터베이스가 초기화되지 않았습니다")
        
        async with self.pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                logger.error(f"데이터베이스 오류: {e}")
                raise
    
    @asynccontextmanager
    async def get_transaction(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """트랜잭션 컨텍스트 매니저"""
        async with self.get_connection() as conn:
            async with conn.transaction():
                yield conn

# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()

# 의존성 주입용 함수
async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """데이터베이스 연결 의존성"""
    async with db_manager.get_connection() as conn:
        yield conn

async def get_db_transaction() -> AsyncGenerator[asyncpg.Connection, None]:
    """트랜잭션 데이터베이스 연결 의존성"""
    async with db_manager.get_transaction() as conn:
        yield conn
```

### 2. 설정 관리

```python
# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import secrets

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 프로젝트 정보
    PROJECT_NAME: str = Field(default="FastAPI Neon Blog", description="프로젝트 이름")
    VERSION: str = Field(default="1.0.0", description="API 버전")
    API_V1_STR: str = Field(default="/api/v1", description="API v1 접두사")
    
    # 환경 설정
    ENVIRONMENT: str = Field(default="development", description="실행 환경")
    DEBUG: bool = Field(default=False, description="디버그 모드")
    
    # 데이터베이스 설정
    DATABASE_URL: str = Field(..., description="PostgreSQL 연결 URL")
    
    # 보안 설정
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32), description="JWT 비밀 키")
    ALGORITHM: str = Field(default="HS256", description="JWT 알고리즘")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="액세스 토큰 만료 시간(분)")
    
    # CORS 설정
    BACKEND_CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="허용된 CORS 출처"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### 3. 보안 설정

```python
# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """액세스 토큰 생성"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """토큰 검증"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
```

## 데이터베이스 스키마 및 마이그레이션

### 1. 스키마 정의

```python
# app/sql/migrations.py
import asyncpg
import logging
from typing import List

logger = logging.getLogger(__name__)

class Migration:
    """데이터베이스 마이그레이션"""
    
    def __init__(self, connection: asyncpg.Connection):
        self.conn = connection
    
    async def create_tables(self):
        """테이블 생성"""
        
        # 사용자 테이블
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                full_name VARCHAR(100),
                hashed_password VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                is_superuser BOOLEAN DEFAULT FALSE,
                avatar_url TEXT,
                bio TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 카테고리 테이블
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                slug VARCHAR(100) UNIQUE NOT NULL,
                description TEXT,
                color VARCHAR(7) DEFAULT '#6c757d',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 게시글 테이블
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id SERIAL PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                slug VARCHAR(200) UNIQUE NOT NULL,
                content TEXT NOT NULL,
                excerpt TEXT,
                thumbnail_url TEXT,
                author_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                is_published BOOLEAN DEFAULT FALSE,
                is_featured BOOLEAN DEFAULT FALSE,
                view_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0,
                published_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 태그 테이블
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                slug VARCHAR(50) UNIQUE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 게시글-태그 관계 테이블
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS post_tags (
                id SERIAL PRIMARY KEY,
                post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
                tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
                UNIQUE(post_id, tag_id)
            )
        """)
        
        # 댓글 테이블
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                author_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
                parent_id INTEGER REFERENCES comments(id) ON DELETE CASCADE,
                is_deleted BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 좋아요 테이블
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS post_likes (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, post_id)
            )
        """)
        
        logger.info("✅ 테이블 생성 완료")
    
    async def create_indexes(self):
        """인덱스 생성"""
        
        indexes = [
            # 사용자 테이블 인덱스
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
            "CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)",
            
            # 게시글 테이블 인덱스
            "CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author_id)",
            "CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category_id)",
            "CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(is_published)",
            "CREATE INDEX IF NOT EXISTS idx_posts_featured ON posts(is_featured)",
            "CREATE INDEX IF NOT EXISTS idx_posts_slug ON posts(slug)",
            "CREATE INDEX IF NOT EXISTS idx_posts_published_at ON posts(published_at)",
            "CREATE INDEX IF NOT EXISTS idx_posts_view_count ON posts(view_count)",
            
            # 댓글 테이블 인덱스
            "CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id)",
            "CREATE INDEX IF NOT EXISTS idx_comments_author ON comments(author_id)",
            "CREATE INDEX IF NOT EXISTS idx_comments_parent ON comments(parent_id)",
            
            # 관계 테이블 인덱스
            "CREATE INDEX IF NOT EXISTS idx_post_tags_post ON post_tags(post_id)",
            "CREATE INDEX IF NOT EXISTS idx_post_tags_tag ON post_tags(tag_id)",
            "CREATE INDEX IF NOT EXISTS idx_post_likes_post ON post_likes(post_id)",
            "CREATE INDEX IF NOT EXISTS idx_post_likes_user ON post_likes(user_id)",
        ]
        
        for index_sql in indexes:
            await self.conn.execute(index_sql)
        
        logger.info("✅ 인덱스 생성 완료")
    
    async def create_functions(self):
        """PostgreSQL 함수 생성"""
        
        # 게시글 검색 함수
        await self.conn.execute("""
            CREATE OR REPLACE FUNCTION search_posts(
                search_term TEXT,
                category_filter INTEGER DEFAULT NULL,
                limit_count INTEGER DEFAULT 20,
                offset_count INTEGER DEFAULT 0
            )
            RETURNS TABLE(
                id INTEGER,
                title VARCHAR(200),
                slug VARCHAR(200),
                excerpt TEXT,
                thumbnail_url TEXT,
                author_name VARCHAR(100),
                category_name VARCHAR(100),
                view_count INTEGER,
                like_count INTEGER,
                published_at TIMESTAMP WITH TIME ZONE,
                rank REAL
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    p.id,
                    p.title,
                    p.slug,
                    p.excerpt,
                    p.thumbnail_url,
                    u.full_name as author_name,
                    c.name as category_name,
                    p.view_count,
                    p.like_count,
                    p.published_at,
                    ts_rank(
                        to_tsvector('korean', p.title || ' ' || COALESCE(p.excerpt, '') || ' ' || p.content),
                        plainto_tsquery('korean', search_term)
                    ) as rank
                FROM posts p
                LEFT JOIN users u ON p.author_id = u.id
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.is_published = TRUE
                AND (
                    category_filter IS NULL 
                    OR p.category_id = category_filter
                )
                AND (
                    to_tsvector('korean', p.title || ' ' || COALESCE(p.excerpt, '') || ' ' || p.content) 
                    @@ plainto_tsquery('korean', search_term)
                )
                ORDER BY rank DESC, p.published_at DESC
                LIMIT limit_count OFFSET offset_count;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        # 인기 게시글 조회 함수
        await self.conn.execute("""
            CREATE OR REPLACE FUNCTION get_popular_posts(
                days_back INTEGER DEFAULT 30,
                limit_count INTEGER DEFAULT 10
            )
            RETURNS TABLE(
                id INTEGER,
                title VARCHAR(200),
                slug VARCHAR(200),
                excerpt TEXT,
                thumbnail_url TEXT,
                author_name VARCHAR(100),
                category_name VARCHAR(100),
                view_count INTEGER,
                like_count INTEGER,
                published_at TIMESTAMP WITH TIME ZONE,
                popularity_score NUMERIC
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    p.id,
                    p.title,
                    p.slug,
                    p.excerpt,
                    p.thumbnail_url,
                    u.full_name as author_name,
                    c.name as category_name,
                    p.view_count,
                    p.like_count,
                    p.published_at,
                    (
                        (p.view_count * 0.3) + 
                        (p.like_count * 0.7) + 
                        (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - p.published_at)) / 86400.0 * -0.1)
                    ) as popularity_score
                FROM posts p
                LEFT JOIN users u ON p.author_id = u.id
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.is_published = TRUE
                AND p.published_at > CURRENT_TIMESTAMP - INTERVAL '%s days' 
                ORDER BY popularity_score DESC
                LIMIT limit_count;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        # 업데이트 시간 트리거 함수
        await self.conn.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        logger.info("✅ PostgreSQL 함수 생성 완료")
    
    async def create_triggers(self):
        """트리거 생성"""
        
        # 업데이트 시간 자동 갱신 트리거
        triggers = [
            "DROP TRIGGER IF EXISTS update_users_updated_at ON users",
            "CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
            
            "DROP TRIGGER IF EXISTS update_posts_updated_at ON posts",
            "CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
            
            "DROP TRIGGER IF EXISTS update_comments_updated_at ON comments",
            "CREATE TRIGGER update_comments_updated_at BEFORE UPDATE ON comments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
        ]
        
        for trigger_sql in triggers:
            await self.conn.execute(trigger_sql)
        
        logger.info("✅ 트리거 생성 완료")
    
    async def insert_sample_data(self):
        """샘플 데이터 삽입"""
        
        # 기본 카테고리 삽입
        await self.conn.execute("""
            INSERT INTO categories (name, slug, description, color) VALUES
            ('기술', 'tech', '프로그래밍 및 기술 관련 포스트', '#007bff'),
            ('튜토리얼', 'tutorial', '단계별 가이드 및 튜토리얼', '#28a745'),
            ('리뷰', 'review', '제품 및 서비스 리뷰', '#ffc107'),
            ('일반', 'general', '일반적인 주제의 포스트', '#6c757d')
            ON CONFLICT (slug) DO NOTHING
        """)
        
        # 기본 태그 삽입
        await self.conn.execute("""
            INSERT INTO tags (name, slug) VALUES
            ('Python', 'python'),
            ('FastAPI', 'fastapi'),
            ('PostgreSQL', 'postgresql'),
            ('API', 'api'),
            ('Database', 'database'),
            ('Web Development', 'web-development'),
            ('Backend', 'backend'),
            ('Tutorial', 'tutorial')
            ON CONFLICT (slug) DO NOTHING
        """)
        
        logger.info("✅ 샘플 데이터 삽입 완료")
    
    async def run_all_migrations(self):
        """모든 마이그레이션 실행"""
        try:
            await self.create_tables()
            await self.create_indexes()
            await self.create_functions()
            await self.create_triggers()
            await self.insert_sample_data()
            logger.info("🎉 모든 마이그레이션 완료")
        except Exception as e:
            logger.error(f"❌ 마이그레이션 실패: {e}")
            raise
```

## Pydantic 스키마 정의

### 1. 데이터 모델 스키마

```python
# app/models/schemas.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
import re

# 기본 응답 스키마
class BaseResponse(BaseModel):
    """기본 API 응답"""
    success: bool = True
    message: str = "Operation successful"
    data: Optional[dict] = None

class PaginatedResponse(BaseModel):
    """페이지네이션 응답"""
    items: List[dict]
    total: int
    page: int
    size: int
    pages: int

# 사용자 관련 스키마
class UserBase(BaseModel):
    """사용자 기본 스키마"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('사용자명은 영문, 숫자, 언더스코어만 사용 가능합니다')
        return v

class UserCreate(UserBase):
    """사용자 생성 스키마"""
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('비밀번호는 최소 하나의 영문자를 포함해야 합니다')
        if not re.search(r'\d', v):
            raise ValueError('비밀번호는 최소 하나의 숫자를 포함해야 합니다')
        return v

class UserUpdate(BaseModel):
    """사용자 수정 스키마"""
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None

class UserResponse(UserBase):
    """사용자 응답 스키마"""
    id: int
    is_active: bool
    avatar_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserProfile(UserResponse):
    """사용자 프로필 스키마"""
    post_count: int = 0
    comment_count: int = 0
    like_count: int = 0

# 인증 관련 스키마
class UserLogin(BaseModel):
    """로그인 스키마"""
    username: str
    password: str

class Token(BaseModel):
    """토큰 응답 스키마"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    """토큰 데이터 스키마"""
    user_id: Optional[int] = None

# 카테고리 관련 스키마
class CategoryBase(BaseModel):
    """카테고리 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: str = Field(default='#6c757d', regex=r'^#[0-9A-Fa-f]{6}$')

class CategoryCreate(CategoryBase):
    """카테고리 생성 스키마"""
    slug: str = Field(..., min_length=1, max_length=100)
    
    @validator('slug')
    def validate_slug(cls, v):
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('슬러그는 소문자, 숫자, 하이픈만 사용 가능합니다')
        return v

class CategoryResponse(CategoryBase):
    """카테고리 응답 스키마"""
    id: int
    slug: str
    post_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True

# 태그 관련 스키마
class TagBase(BaseModel):
    """태그 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=50)

class TagCreate(TagBase):
    """태그 생성 스키마"""
    slug: str = Field(..., min_length=1, max_length=50)

class TagResponse(TagBase):
    """태그 응답 스키마"""
    id: int
    slug: str
    post_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True

# 게시글 관련 스키마
class PostBase(BaseModel):
    """게시글 기본 스키마"""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    excerpt: Optional[str] = Field(None, max_length=500)
    thumbnail_url: Optional[str] = None
    category_id: Optional[int] = None
    is_featured: bool = False

class PostCreate(PostBase):
    """게시글 생성 스키마"""
    slug: str = Field(..., min_length=1, max_length=200)
    tag_ids: List[int] = []
    
    @validator('slug')
    def validate_slug(cls, v):
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('슬러그는 소문자, 숫자, 하이픈만 사용 가능합니다')
        return v

class PostUpdate(BaseModel):
    """게시글 수정 스키마"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    excerpt: Optional[str] = Field(None, max_length=500)
    thumbnail_url: Optional[str] = None
    category_id: Optional[int] = None
    is_featured: Optional[bool] = None
    tag_ids: Optional[List[int]] = None

class PostResponse(PostBase):
    """게시글 응답 스키마"""
    id: int
    slug: str
    author: UserResponse
    category: Optional[CategoryResponse] = None
    tags: List[TagResponse] = []
    is_published: bool
    view_count: int
    like_count: int
    comment_count: int = 0
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PostSummary(BaseModel):
    """게시글 요약 스키마"""
    id: int
    title: str
    slug: str
    excerpt: Optional[str] = None
    thumbnail_url: Optional[str] = None
    author_name: str
    category_name: Optional[str] = None
    view_count: int
    like_count: int
    published_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# 댓글 관련 스키마
class CommentBase(BaseModel):
    """댓글 기본 스키마"""
    content: str = Field(..., min_length=1, max_length=1000)

class CommentCreate(CommentBase):
    """댓글 생성 스키마"""
    post_id: int
    parent_id: Optional[int] = None

class CommentUpdate(BaseModel):
    """댓글 수정 스키마"""
    content: str = Field(..., min_length=1, max_length=1000)

class CommentResponse(CommentBase):
    """댓글 응답 스키마"""
    id: int
    author: UserResponse
    parent_id: Optional[int] = None
    replies: List['CommentResponse'] = []
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# 순환 참조 해결
CommentResponse.model_rebuild()

# 검색 관련 스키마
class SearchRequest(BaseModel):
    """검색 요청 스키마"""
    query: str = Field(..., min_length=1, max_length=100)
    category_id: Optional[int] = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

class SearchResponse(BaseModel):
    """검색 응답 스키마"""
    query: str
    results: List[PostSummary]
    total: int
    page: int
    size: int
    pages: int

# 통계 관련 스키마
class PostStats(BaseModel):
    """게시글 통계 스키마"""
    total_posts: int
    published_posts: int
    draft_posts: int
    total_views: int
    total_likes: int
    total_comments: int

class UserStats(BaseModel):
    """사용자 통계 스키마"""
    total_users: int
    active_users: int
    new_users_this_month: int

## Raw SQL 쿼리 모듈

### 1. 사용자 관련 SQL

```python
# app/sql/users.py
import asyncpg
from typing import Optional, List, Dict, Any
from app.core.security import get_password_hash, verify_password
import logging

logger = logging.getLogger(__name__)

class UserSQL:
    """사용자 관련 SQL 쿼리"""
    
    @staticmethod
    async def create_user(
        conn: asyncpg.Connection,
        username: str,
        email: str,
        hashed_password: str,
        full_name: Optional[str] = None,
        bio: Optional[str] = None
    ) -> Dict[str, Any]:
        """사용자 생성"""
        
        query = """
            INSERT INTO users (username, email, hashed_password, full_name, bio)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, username, email, full_name, bio, is_active, 
                     avatar_url, created_at, updated_at
        """
        
        try:
            row = await conn.fetchrow(
                query, username, email, hashed_password, full_name, bio
            )
            return dict(row) if row else None
            
        except asyncpg.UniqueViolationError as e:
            if 'username' in str(e):
                raise ValueError("이미 사용 중인 사용자명입니다")
            elif 'email' in str(e):
                raise ValueError("이미 사용 중인 이메일입니다")
            else:
                raise ValueError("중복된 데이터가 있습니다")
    
    @staticmethod
    async def get_user_by_id(conn: asyncpg.Connection, user_id: int) -> Optional[Dict[str, Any]]:
        """ID로 사용자 조회"""
        
        query = """
            SELECT id, username, email, full_name, bio, is_active, is_superuser,
                   avatar_url, created_at, updated_at
            FROM users
            WHERE id = $1 AND is_active = TRUE
        """
        
        row = await conn.fetchrow(query, user_id)
        return dict(row) if row else None
    
    @staticmethod
    async def get_user_by_username(conn: asyncpg.Connection, username: str) -> Optional[Dict[str, Any]]:
        """사용자명으로 사용자 조회 (로그인용)"""
        
        query = """
            SELECT id, username, email, full_name, hashed_password, 
                   is_active, is_superuser, avatar_url
            FROM users
            WHERE username = $1 AND is_active = TRUE
        """
        
        row = await conn.fetchrow(query, username)
        return dict(row) if row else None
    
    @staticmethod
    async def get_user_by_email(conn: asyncpg.Connection, email: str) -> Optional[Dict[str, Any]]:
        """이메일로 사용자 조회"""
        
        query = """
            SELECT id, username, email, full_name, is_active, is_superuser, avatar_url
            FROM users
            WHERE email = $1 AND is_active = TRUE
        """
        
        row = await conn.fetchrow(query, email)
        return dict(row) if row else None
    
    @staticmethod
    async def update_user(
        conn: asyncpg.Connection,
        user_id: int,
        **update_data
    ) -> Optional[Dict[str, Any]]:
        """사용자 정보 수정"""
        
        # 동적 쿼리 생성
        set_clauses = []
        values = []
        param_count = 1
        
        for field, value in update_data.items():
            if value is not None:
                set_clauses.append(f"{field} = ${param_count}")
                values.append(value)
                param_count += 1
        
        if not set_clauses:
            return None
        
        query = f"""
            UPDATE users 
            SET {', '.join(set_clauses)}
            WHERE id = ${param_count} AND is_active = TRUE
            RETURNING id, username, email, full_name, bio, is_active,
                     avatar_url, created_at, updated_at
        """
        
        values.append(user_id)
        
        row = await conn.fetchrow(query, *values)
        return dict(row) if row else None
    
    @staticmethod
    async def get_user_profile(conn: asyncpg.Connection, user_id: int) -> Optional[Dict[str, Any]]:
        """사용자 프로필 조회 (통계 포함)"""
        
        query = """
            SELECT 
                u.id, u.username, u.email, u.full_name, u.bio, 
                u.is_active, u.avatar_url, u.created_at,
                COUNT(DISTINCT p.id) as post_count,
                COUNT(DISTINCT c.id) as comment_count,
                COUNT(DISTINCT pl.id) as like_count
            FROM users u
            LEFT JOIN posts p ON u.id = p.author_id AND p.is_published = TRUE
            LEFT JOIN comments c ON u.id = c.author_id AND c.is_deleted = FALSE
            LEFT JOIN post_likes pl ON u.id = pl.user_id
            WHERE u.id = $1 AND u.is_active = TRUE
            GROUP BY u.id, u.username, u.email, u.full_name, u.bio, 
                     u.is_active, u.avatar_url, u.created_at
        """
        
        row = await conn.fetchrow(query, user_id)
        return dict(row) if row else None
    
    @staticmethod
    async def get_users_list(
        conn: asyncpg.Connection,
        limit: int = 20,
        offset: int = 0,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """사용자 목록 조회"""
        
        params = []
        where_clauses = ["is_active = TRUE"]
        param_count = 1
        
        if search:
            where_clauses.append(f"""
                (username ILIKE ${param_count} OR 
                 full_name ILIKE ${param_count} OR 
                 email ILIKE ${param_count})
            """)
            params.append(f"%{search}%")
            param_count += 1
        
        query = f"""
            SELECT 
                u.id, u.username, u.email, u.full_name, u.bio,
                u.avatar_url, u.created_at,
                COUNT(DISTINCT p.id) as post_count
            FROM users u
            LEFT JOIN posts p ON u.id = p.author_id AND p.is_published = TRUE
            WHERE {' AND '.join(where_clauses)}
            GROUP BY u.id, u.username, u.email, u.full_name, u.bio,
                     u.avatar_url, u.created_at
            ORDER BY u.created_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        
        params.extend([limit, offset])
        
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]
    
    @staticmethod
    async def get_users_count(
        conn: asyncpg.Connection,
        search: Optional[str] = None
    ) -> int:
        """사용자 총 개수 조회"""
        
        params = []
        where_clauses = ["is_active = TRUE"]
        param_count = 1
        
        if search:
            where_clauses.append(f"""
                (username ILIKE ${param_count} OR 
                 full_name ILIKE ${param_count} OR 
                 email ILIKE ${param_count})
            """)
            params.append(f"%{search}%")
        
        query = f"""
            SELECT COUNT(*) as total
            FROM users
            WHERE {' AND '.join(where_clauses)}
        """
        
        row = await conn.fetchrow(query, *params)
        return row['total'] if row else 0
    
    @staticmethod
    async def authenticate_user(
        conn: asyncpg.Connection,
        username: str,
        password: str
    ) -> Optional[Dict[str, Any]]:
        """사용자 인증"""
        
        user = await UserSQL.get_user_by_username(conn, username)
        if not user:
            return None
        
        if not verify_password(password, user['hashed_password']):
            return None
        
        # 비밀번호 정보 제거
        user.pop('hashed_password', None)
        return user
```

### 2. 게시글 관련 SQL

```python
# app/sql/posts.py
import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PostSQL:
    """게시글 관련 SQL 쿼리"""
    
    @staticmethod
    async def create_post(
        conn: asyncpg.Connection,
        title: str,
        slug: str,
        content: str,
        author_id: int,
        excerpt: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        category_id: Optional[int] = None,
        is_featured: bool = False,
        tag_ids: List[int] = None
    ) -> Dict[str, Any]:
        """게시글 생성"""
        
        try:
            # 트랜잭션 시작
            async with conn.transaction():
                # 게시글 생성
                post_query = """
                    INSERT INTO posts (title, slug, content, excerpt, thumbnail_url, 
                                     author_id, category_id, is_featured)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING id, title, slug, content, excerpt, thumbnail_url,
                             author_id, category_id, is_published, is_featured,
                             view_count, like_count, created_at, updated_at
                """
                
                post_row = await conn.fetchrow(
                    post_query, title, slug, content, excerpt, thumbnail_url,
                    author_id, category_id, is_featured
                )
                
                post_data = dict(post_row)
                
                # 태그 연결
                if tag_ids:
                    tag_query = """
                        INSERT INTO post_tags (post_id, tag_id)
                        SELECT $1, unnest($2::int[])
                        ON CONFLICT (post_id, tag_id) DO NOTHING
                    """
                    await conn.execute(tag_query, post_data['id'], tag_ids)
                
                return post_data
                
        except asyncpg.UniqueViolationError:
            raise ValueError("이미 사용 중인 슬러그입니다")
    
    @staticmethod
    async def get_post_by_id(
        conn: asyncpg.Connection,
        post_id: int,
        include_unpublished: bool = False
    ) -> Optional[Dict[str, Any]]:
        """ID로 게시글 조회"""
        
        query = """
            SELECT 
                p.id, p.title, p.slug, p.content, p.excerpt, p.thumbnail_url,
                p.is_published, p.is_featured, p.view_count, p.like_count,
                p.published_at, p.created_at, p.updated_at,
                
                -- 작성자 정보
                u.id as author_id, u.username as author_username, 
                u.full_name as author_name, u.avatar_url as author_avatar,
                
                -- 카테고리 정보
                c.id as category_id, c.name as category_name, 
                c.slug as category_slug, c.color as category_color,
                
                -- 댓글 수
                (SELECT COUNT(*) FROM comments WHERE post_id = p.id AND is_deleted = FALSE) as comment_count
                
            FROM posts p
            LEFT JOIN users u ON p.author_id = u.id
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.id = $1
        """
        
        if not include_unpublished:
            query += " AND p.is_published = TRUE"
        
        row = await conn.fetchrow(query, post_id)
        if not row:
            return None
        
        post_data = dict(row)
        
        # 태그 정보 추가
        tag_query = """
            SELECT t.id, t.name, t.slug
            FROM tags t
            JOIN post_tags pt ON t.id = pt.tag_id
            WHERE pt.post_id = $1
            ORDER BY t.name
        """
        
        tag_rows = await conn.fetch(tag_query, post_id)
        post_data['tags'] = [dict(tag) for tag in tag_rows]
        
        return post_data
    
    @staticmethod
    async def get_post_by_slug(
        conn: asyncpg.Connection,
        slug: str,
        include_unpublished: bool = False
    ) -> Optional[Dict[str, Any]]:
        """슬러그로 게시글 조회"""
        
        query = """
            SELECT 
                p.id, p.title, p.slug, p.content, p.excerpt, p.thumbnail_url,
                p.is_published, p.is_featured, p.view_count, p.like_count,
                p.published_at, p.created_at, p.updated_at,
                
                u.id as author_id, u.username as author_username, 
                u.full_name as author_name, u.avatar_url as author_avatar,
                
                c.id as category_id, c.name as category_name, 
                c.slug as category_slug, c.color as category_color,
                
                (SELECT COUNT(*) FROM comments WHERE post_id = p.id AND is_deleted = FALSE) as comment_count
                
            FROM posts p
            LEFT JOIN users u ON p.author_id = u.id
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.slug = $1
        """
        
        if not include_unpublished:
            query += " AND p.is_published = TRUE"
        
        row = await conn.fetchrow(query, slug)
        if not row:
            return None
        
        post_data = dict(row)
        
        # 태그 정보 추가
        tag_query = """
            SELECT t.id, t.name, t.slug
            FROM tags t
            JOIN post_tags pt ON t.id = pt.tag_id
            WHERE pt.post_id = $1
            ORDER BY t.name
        """
        
        tag_rows = await conn.fetch(tag_query, post_data['id'])
        post_data['tags'] = [dict(tag) for tag in tag_rows]
        
        return post_data
    
    @staticmethod
    async def get_posts_list(
        conn: asyncpg.Connection,
        limit: int = 20,
        offset: int = 0,
        category_id: Optional[int] = None,
        author_id: Optional[int] = None,
        is_featured: Optional[bool] = None,
        include_unpublished: bool = False,
        order_by: str = 'created_at',
        order_direction: str = 'DESC'
    ) -> List[Dict[str, Any]]:
        """게시글 목록 조회"""
        
        params = []
        where_clauses = []
        param_count = 1
        
        if not include_unpublished:
            where_clauses.append("p.is_published = TRUE")
        
        if category_id:
            where_clauses.append(f"p.category_id = ${param_count}")
            params.append(category_id)
            param_count += 1
        
        if author_id:
            where_clauses.append(f"p.author_id = ${param_count}")
            params.append(author_id)
            param_count += 1
        
        if is_featured is not None:
            where_clauses.append(f"p.is_featured = ${param_count}")
            params.append(is_featured)
            param_count += 1
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # 정렬 컬럼 검증
        allowed_order_cols = ['created_at', 'published_at', 'view_count', 'like_count', 'title']
        if order_by not in allowed_order_cols:
            order_by = 'created_at'
        
        if order_direction.upper() not in ['ASC', 'DESC']:
            order_direction = 'DESC'
        
        query = f"""
            SELECT 
                p.id, p.title, p.slug, p.excerpt, p.thumbnail_url,
                p.is_published, p.is_featured, p.view_count, p.like_count,
                p.published_at, p.created_at,
                
                u.username as author_username, u.full_name as author_name,
                u.avatar_url as author_avatar,
                
                c.name as category_name, c.slug as category_slug, c.color as category_color,
                
                (SELECT COUNT(*) FROM comments WHERE post_id = p.id AND is_deleted = FALSE) as comment_count
                
            FROM posts p
            LEFT JOIN users u ON p.author_id = u.id
            LEFT JOIN categories c ON p.category_id = c.id
            {where_clause}
            ORDER BY p.{order_by} {order_direction}
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        
        params.extend([limit, offset])
        
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]
    
    @staticmethod
    async def get_posts_count(
        conn: asyncpg.Connection,
        category_id: Optional[int] = None,
        author_id: Optional[int] = None,
        is_featured: Optional[bool] = None,
        include_unpublished: bool = False
    ) -> int:
        """게시글 총 개수 조회"""
        
        params = []
        where_clauses = []
        param_count = 1
        
        if not include_unpublished:
            where_clauses.append("is_published = TRUE")
        
        if category_id:
            where_clauses.append(f"category_id = ${param_count}")
            params.append(category_id)
            param_count += 1
        
        if author_id:
            where_clauses.append(f"author_id = ${param_count}")
            params.append(author_id)
            param_count += 1
        
        if is_featured is not None:
            where_clauses.append(f"is_featured = ${param_count}")
            params.append(is_featured)
            param_count += 1
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
            SELECT COUNT(*) as total
            FROM posts
            {where_clause}
        """
        
        row = await conn.fetchrow(query, *params)
        return row['total'] if row else 0
    
    @staticmethod
    async def update_post(
        conn: asyncpg.Connection,
        post_id: int,
        author_id: int,
        **update_data
    ) -> Optional[Dict[str, Any]]:
        """게시글 수정"""
        
        try:
            async with conn.transaction():
                # 소유자 확인
                owner_check = await conn.fetchval(
                    "SELECT author_id FROM posts WHERE id = $1", post_id
                )
                if owner_check != author_id:
                    raise ValueError("게시글 수정 권한이 없습니다")
                
                # 태그 정보 분리
                tag_ids = update_data.pop('tag_ids', None)
                
                # 동적 쿼리 생성
                set_clauses = []
                values = []
                param_count = 1
                
                for field, value in update_data.items():
                    if value is not None:
                        set_clauses.append(f"{field} = ${param_count}")
                        values.append(value)
                        param_count += 1
                
                if set_clauses:
                    query = f"""
                        UPDATE posts 
                        SET {', '.join(set_clauses)}
                        WHERE id = ${param_count}
                        RETURNING id, title, slug, content, excerpt, thumbnail_url,
                                 author_id, category_id, is_published, is_featured,
                                 view_count, like_count, published_at, created_at, updated_at
                    """
                    
                    values.append(post_id)
                    post_row = await conn.fetchrow(query, *values)
                    post_data = dict(post_row) if post_row else None
                else:
                    # 변경사항이 없으면 기존 데이터 반환
                    post_data = await PostSQL.get_post_by_id(conn, post_id, include_unpublished=True)
                
                # 태그 업데이트
                if tag_ids is not None:
                    # 기존 태그 삭제
                    await conn.execute(
                        "DELETE FROM post_tags WHERE post_id = $1", post_id
                    )
                    
                    # 새 태그 추가
                    if tag_ids:
                        await conn.execute(
                            "INSERT INTO post_tags (post_id, tag_id) SELECT $1, unnest($2::int[])",
                            post_id, tag_ids
                        )
                
                return post_data
                
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"게시글 수정 실패: {e}")
            raise ValueError("게시글 수정에 실패했습니다")
    
    @staticmethod
    async def delete_post(
        conn: asyncpg.Connection,
        post_id: int,
        author_id: int
    ) -> bool:
        """게시글 삭제 (소프트 삭제)"""
        
        try:
            # 소유자 확인
            owner_check = await conn.fetchval(
                "SELECT author_id FROM posts WHERE id = $1", post_id
            )
            if owner_check != author_id:
                raise ValueError("게시글 삭제 권한이 없습니다")
            
            # 실제로는 is_published를 FALSE로 변경 (소프트 삭제)
            result = await conn.execute(
                "UPDATE posts SET is_published = FALSE WHERE id = $1", post_id
            )
            
            return result == "UPDATE 1"
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"게시글 삭제 실패: {e}")
            return False
    
    @staticmethod
    async def publish_post(
        conn: asyncpg.Connection,
        post_id: int,
        author_id: int
    ) -> Optional[Dict[str, Any]]:
        """게시글 발행"""
        
        try:
            # 소유자 확인
            owner_check = await conn.fetchval(
                "SELECT author_id FROM posts WHERE id = $1", post_id
            )
            if owner_check != author_id:
                raise ValueError("게시글 발행 권한이 없습니다")
            
            query = """
                UPDATE posts 
                SET is_published = TRUE, published_at = CURRENT_TIMESTAMP
                WHERE id = $1 AND is_published = FALSE
                RETURNING id, title, slug, published_at
            """
            
            row = await conn.fetchrow(query, post_id)
            return dict(row) if row else None
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"게시글 발행 실패: {e}")
            return None
    
    @staticmethod
    async def increment_view_count(
        conn: asyncpg.Connection,
        post_id: int
    ) -> bool:
        """조회수 증가"""
        
        try:
            result = await conn.execute(
                "UPDATE posts SET view_count = view_count + 1 WHERE id = $1 AND is_published = TRUE",
                post_id
            )
            return result == "UPDATE 1"
        except Exception as e:
            logger.error(f"조회수 증가 실패: {e}")
            return False
    
    @staticmethod
    async def search_posts(
        conn: asyncpg.Connection,
        search_term: str,
        category_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """게시글 검색 (PostgreSQL 함수 사용)"""
        
        try:
            query = "SELECT * FROM search_posts($1, $2, $3, $4)"
            rows = await conn.fetch(query, search_term, category_id, limit, offset)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"게시글 검색 실패: {e}")
            return []
    
    @staticmethod
    async def get_popular_posts(
        conn: asyncpg.Connection,
        days_back: int = 30,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """인기 게시글 조회 (PostgreSQL 함수 사용)"""
        
        try:
            query = "SELECT * FROM get_popular_posts($1, $2)"
            rows = await conn.fetch(query, days_back, limit)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"인기 게시글 조회 실패: {e}")
            return []
    
    @staticmethod
    async def toggle_like_post(
        conn: asyncpg.Connection,
        post_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """게시글 좋아요 토글"""
        
        try:
            async with conn.transaction():
                # 기존 좋아요 확인
                existing_like = await conn.fetchval(
                    "SELECT id FROM post_likes WHERE post_id = $1 AND user_id = $2",
                    post_id, user_id
                )
                
                if existing_like:
                    # 좋아요 취소
                    await conn.execute(
                        "DELETE FROM post_likes WHERE post_id = $1 AND user_id = $2",
                        post_id, user_id
                    )
                    await conn.execute(
                        "UPDATE posts SET like_count = like_count - 1 WHERE id = $1",
                        post_id
                    )
                    liked = False
                else:
                    # 좋아요 추가
                    await conn.execute(
                        "INSERT INTO post_likes (post_id, user_id) VALUES ($1, $2)",
                        post_id, user_id
                    )
                    await conn.execute(
                        "UPDATE posts SET like_count = like_count + 1 WHERE id = $1",
                        post_id
                    )
                    liked = True
                
                # 현재 좋아요 수 조회
                like_count = await conn.fetchval(
                    "SELECT like_count FROM posts WHERE id = $1", post_id
                )
                
                return {
                    "liked": liked,
                    "like_count": like_count
                }
                
        except Exception as e:
            logger.error(f"좋아요 토글 실패: {e}")
            raise ValueError("좋아요 처리에 실패했습니다")
```

### 3. 카테고리 및 태그 관련 SQL

```python
# app/sql/categories.py
import asyncpg
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class CategorySQL:
    """카테고리 관련 SQL 쿼리"""
    
    @staticmethod
    async def create_category(
        conn: asyncpg.Connection,
        name: str,
        slug: str,
        description: Optional[str] = None,
        color: str = '#6c757d'
    ) -> Dict[str, Any]:
        """카테고리 생성"""
        
        query = """
            INSERT INTO categories (name, slug, description, color)
            VALUES ($1, $2, $3, $4)
            RETURNING id, name, slug, description, color, created_at
        """
        
        try:
            row = await conn.fetchrow(query, name, slug, description, color)
            return dict(row) if row else None
        except asyncpg.UniqueViolationError:
            raise ValueError("이미 사용 중인 카테고리 이름 또는 슬러그입니다")
    
    @staticmethod
    async def get_category_by_id(conn: asyncpg.Connection, category_id: int) -> Optional[Dict[str, Any]]:
        """ID로 카테고리 조회"""
        
        query = """
            SELECT 
                c.id, c.name, c.slug, c.description, c.color, c.created_at,
                COUNT(p.id) as post_count
            FROM categories c
            LEFT JOIN posts p ON c.id = p.category_id AND p.is_published = TRUE
            WHERE c.id = $1
            GROUP BY c.id, c.name, c.slug, c.description, c.color, c.created_at
        """
        
        row = await conn.fetchrow(query, category_id)
        return dict(row) if row else None
    
    @staticmethod
    async def get_category_by_slug(conn: asyncpg.Connection, slug: str) -> Optional[Dict[str, Any]]:
        """슬러그로 카테고리 조회"""
        
        query = """
            SELECT 
                c.id, c.name, c.slug, c.description, c.color, c.created_at,
                COUNT(p.id) as post_count
            FROM categories c
            LEFT JOIN posts p ON c.id = p.category_id AND p.is_published = TRUE
            WHERE c.slug = $1
            GROUP BY c.id, c.name, c.slug, c.description, c.color, c.created_at
        """
        
        row = await conn.fetchrow(query, slug)
        return dict(row) if row else None
    
    @staticmethod
    async def get_categories_list(conn: asyncpg.Connection) -> List[Dict[str, Any]]:
        """모든 카테고리 조회"""
        
        query = """
            SELECT 
                c.id, c.name, c.slug, c.description, c.color, c.created_at,
                COUNT(p.id) as post_count
            FROM categories c
            LEFT JOIN posts p ON c.id = p.category_id AND p.is_published = TRUE
            GROUP BY c.id, c.name, c.slug, c.description, c.color, c.created_at
            ORDER BY c.name
        """
        
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
    
    @staticmethod
    async def update_category(
        conn: asyncpg.Connection,
        category_id: int,
        **update_data
    ) -> Optional[Dict[str, Any]]:
        """카테고리 수정"""
        
        set_clauses = []
        values = []
        param_count = 1
        
        for field, value in update_data.items():
            if value is not None:
                set_clauses.append(f"{field} = ${param_count}")
                values.append(value)
                param_count += 1
        
        if not set_clauses:
            return None
        
        query = f"""
            UPDATE categories 
            SET {', '.join(set_clauses)}
            WHERE id = ${param_count}
            RETURNING id, name, slug, description, color, created_at
        """
        
        values.append(category_id)
        
        try:
            row = await conn.fetchrow(query, *values)
            return dict(row) if row else None
        except asyncpg.UniqueViolationError:
            raise ValueError("이미 사용 중인 카테고리 이름 또는 슬러그입니다")
    
    @staticmethod
    async def delete_category(conn: asyncpg.Connection, category_id: int) -> bool:
        """카테고리 삭제"""
        
        try:
            # 해당 카테고리를 사용하는 게시글의 카테고리를 NULL로 변경
            await conn.execute(
                "UPDATE posts SET category_id = NULL WHERE category_id = $1",
                category_id
            )
            
            # 카테고리 삭제
            result = await conn.execute(
                "DELETE FROM categories WHERE id = $1", category_id
            )
            
            return result == "DELETE 1"
        except Exception as e:
            logger.error(f"카테고리 삭제 실패: {e}")
            return False

class TagSQL:
    """태그 관련 SQL 쿼리"""
    
    @staticmethod
    async def create_tag(
        conn: asyncpg.Connection,
        name: str,
        slug: str
    ) -> Dict[str, Any]:
        """태그 생성"""
        
        query = """
            INSERT INTO tags (name, slug)
            VALUES ($1, $2)
            RETURNING id, name, slug, created_at
        """
        
        try:
            row = await conn.fetchrow(query, name, slug)
            return dict(row) if row else None
        except asyncpg.UniqueViolationError:
            raise ValueError("이미 사용 중인 태그 이름 또는 슬러그입니다")
    
    @staticmethod
    async def get_tag_by_id(conn: asyncpg.Connection, tag_id: int) -> Optional[Dict[str, Any]]:
        """ID로 태그 조회"""
        
        query = """
            SELECT 
                t.id, t.name, t.slug, t.created_at,
                COUNT(pt.post_id) as post_count
            FROM tags t
            LEFT JOIN post_tags pt ON t.id = pt.tag_id
            LEFT JOIN posts p ON pt.post_id = p.id AND p.is_published = TRUE
            WHERE t.id = $1
            GROUP BY t.id, t.name, t.slug, t.created_at
        """
        
        row = await conn.fetchrow(query, tag_id)
        return dict(row) if row else None
    
    @staticmethod
    async def get_tag_by_slug(conn: asyncpg.Connection, slug: str) -> Optional[Dict[str, Any]]:
        """슬러그로 태그 조회"""
        
        query = """
            SELECT 
                t.id, t.name, t.slug, t.created_at,
                COUNT(pt.post_id) as post_count
            FROM tags t
            LEFT JOIN post_tags pt ON t.id = pt.tag_id
            LEFT JOIN posts p ON pt.post_id = p.id AND p.is_published = TRUE
            WHERE t.slug = $1
            GROUP BY t.id, t.name, t.slug, t.created_at
        """
        
        row = await conn.fetchrow(query, slug)
        return dict(row) if row else None
    
    @staticmethod
    async def get_tags_list(
        conn: asyncpg.Connection,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """태그 목록 조회"""
        
        query = """
            SELECT 
                t.id, t.name, t.slug, t.created_at,
                COUNT(pt.post_id) as post_count
            FROM tags t
            LEFT JOIN post_tags pt ON t.id = pt.tag_id
            LEFT JOIN posts p ON pt.post_id = p.id AND p.is_published = TRUE
            GROUP BY t.id, t.name, t.slug, t.created_at
            ORDER BY post_count DESC, t.name
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
    
    @staticmethod
    async def get_or_create_tags(
        conn: asyncpg.Connection,
        tag_names: List[str]
    ) -> List[Dict[str, Any]]:
        """태그 조회 또는 생성"""
        
        tags = []
        
        for tag_name in tag_names:
            # 태그 조회
            existing_tag = await conn.fetchrow(
                "SELECT id, name, slug FROM tags WHERE name = $1", tag_name
            )
            
            if existing_tag:
                tags.append(dict(existing_tag))
            else:
                # 새 태그 생성
                slug = tag_name.lower().replace(' ', '-')
                try:
                    new_tag = await conn.fetchrow(
                        "INSERT INTO tags (name, slug) VALUES ($1, $2) RETURNING id, name, slug",
                        tag_name, slug
                    )
                    tags.append(dict(new_tag))
                except asyncpg.UniqueViolationError:
                    # 동시성 문제로 이미 생성된 경우 다시 조회
                    existing_tag = await conn.fetchrow(
                        "SELECT id, name, slug FROM tags WHERE name = $1", tag_name
                    )
                    if existing_tag:
                        tags.append(dict(existing_tag))
        
        return tags
    
    @staticmethod
    async def delete_tag(conn: asyncpg.Connection, tag_id: int) -> bool:
        """태그 삭제"""
        
        try:
            async with conn.transaction():
                # 게시글-태그 관계 삭제
                await conn.execute(
                    "DELETE FROM post_tags WHERE tag_id = $1", tag_id
                )
                
                # 태그 삭제
                result = await conn.execute(
                    "DELETE FROM tags WHERE id = $1", tag_id
                )
                
                return result == "DELETE 1"
        except Exception as e:
            logger.error(f"태그 삭제 실패: {e}")
            return False
```

## API 엔드포인트 구현

### 1. 인증 관련 API

```python
# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import timedelta
import asyncpg

from app.models.schemas import UserLogin, Token, UserCreate, UserResponse, BaseResponse
from app.database import get_db
from app.sql.users import UserSQL
from app.core.security import create_access_token, verify_token, get_password_hash
from app.core.config import settings

router = APIRouter()
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: asyncpg.Connection = Depends(get_db)
) -> dict:
    """현재 사용자 인증"""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증에 실패했습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception
        
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    
    user = await UserSQL.get_user_by_id(db, user_id=int(user_id))
    if user is None:
        raise credentials_exception
    
    return user

@router.post("/register", response_model=BaseResponse)
async def register_user(
    user_data: UserCreate,
    db: asyncpg.Connection = Depends(get_db)
):
    """사용자 회원가입"""
    
    try:
        # 비밀번호 해싱
        hashed_password = get_password_hash(user_data.password)
        
        # 사용자 생성
        user = await UserSQL.create_user(
            db,
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            bio=user_data.bio
        )
        
        return BaseResponse(
            success=True,
            message="회원가입이 완료되었습니다",
            data={"user_id": user["id"], "username": user["username"]}
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 처리 중 오류가 발생했습니다"
        )

@router.post("/login", response_model=Token)
async def login_user(
    login_data: UserLogin,
    db: asyncpg.Connection = Depends(get_db)
):
    """사용자 로그인"""
    
    try:
        # 사용자 인증
        user = await UserSQL.authenticate_user(
            db, login_data.username, login_data.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="잘못된 사용자명 또는 비밀번호입니다",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 액세스 토큰 생성
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user["id"])}, expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 처리 중 오류가 발생했습니다"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user)
):
    """현재 사용자 정보 조회"""
    return UserResponse(**current_user)

@router.post("/logout", response_model=BaseResponse)
async def logout_user():
    """사용자 로그아웃"""
    # JWT는 서버에서 무효화할 수 없으므로 클라이언트에서 토큰 삭제 안내
    return BaseResponse(
        success=True,
        message="로그아웃되었습니다. 클라이언트에서 토큰을 삭제해주세요."
    )

### 2. 게시글 관련 API

```python
# app/api/posts.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
import asyncpg

from app.models.schemas import (
    PostCreate, PostUpdate, PostResponse, PostSummary, 
    BaseResponse, PaginatedResponse, SearchRequest, SearchResponse
)
from app.database import get_db
from app.sql.posts import PostSQL
from app.sql.categories import TagSQL
from app.api.auth import get_current_user

router = APIRouter()

@router.post("/", response_model=BaseResponse)
async def create_post(
    post_data: PostCreate,
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """게시글 생성"""
    
    try:
        post = await PostSQL.create_post(
            db,
            title=post_data.title,
            slug=post_data.slug,
            content=post_data.content,
            author_id=current_user["id"],
            excerpt=post_data.excerpt,
            thumbnail_url=post_data.thumbnail_url,
            category_id=post_data.category_id,
            is_featured=post_data.is_featured,
            tag_ids=post_data.tag_ids
        )
        
        return BaseResponse(
            success=True,
            message="게시글이 생성되었습니다",
            data={"post_id": post["id"], "slug": post["slug"]}
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 생성 중 오류가 발생했습니다"
        )

@router.get("/", response_model=PaginatedResponse)
async def get_posts_list(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = Query(None),
    author_id: Optional[int] = Query(None),
    is_featured: Optional[bool] = Query(None),
    order_by: str = Query("created_at", regex="^(created_at|published_at|view_count|like_count|title)$"),
    order_direction: str = Query("DESC", regex="^(ASC|DESC)$"),
    db: asyncpg.Connection = Depends(get_db)
):
    """게시글 목록 조회"""
    
    try:
        offset = (page - 1) * size
        
        # 게시글 목록 조회
        posts = await PostSQL.get_posts_list(
            db,
            limit=size,
            offset=offset,
            category_id=category_id,
            author_id=author_id,
            is_featured=is_featured,
            order_by=order_by,
            order_direction=order_direction
        )
        
        # 총 개수 조회
        total = await PostSQL.get_posts_count(
            db,
            category_id=category_id,
            author_id=author_id,
            is_featured=is_featured
        )
        
        return PaginatedResponse(
            items=posts,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 목록 조회 중 오류가 발생했습니다"
        )

@router.get("/popular", response_model=List[PostSummary])
async def get_popular_posts(
    days_back: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    db: asyncpg.Connection = Depends(get_db)
):
    """인기 게시글 조회"""
    
    try:
        posts = await PostSQL.get_popular_posts(db, days_back, limit)
        return [PostSummary(**post) for post in posts]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="인기 게시글 조회 중 오류가 발생했습니다"
        )

@router.get("/search", response_model=SearchResponse)
async def search_posts(
    q: str = Query(..., min_length=1, max_length=100),
    category_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: asyncpg.Connection = Depends(get_db)
):
    """게시글 검색"""
    
    try:
        offset = (page - 1) * size
        
        # 검색 실행
        search_results = await PostSQL.search_posts(
            db, q, category_id, size, offset
        )
        
        # PostSummary 스키마로 변환
        results = []
        for result in search_results:
            results.append(PostSummary(
                id=result["id"],
                title=result["title"],
                slug=result["slug"],
                excerpt=result["excerpt"],
                thumbnail_url=result["thumbnail_url"],
                author_name=result["author_name"],
                category_name=result["category_name"],
                view_count=result["view_count"],
                like_count=result["like_count"],
                published_at=result["published_at"]
            ))
        
        return SearchResponse(
            query=q,
            results=results,
            total=len(results),  # 실제로는 COUNT 쿼리로 정확한 총 개수 필요
            page=page,
            size=size,
            pages=1  # 실제로는 총 개수 기반으로 계산
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 검색 중 오류가 발생했습니다"
        )

@router.get("/{post_id}", response_model=PostResponse)
async def get_post_by_id(
    post_id: int,
    db: asyncpg.Connection = Depends(get_db)
):
    """ID로 게시글 조회"""
    
    try:
        post = await PostSQL.get_post_by_id(db, post_id)
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없습니다"
            )
        
        # 조회수 증가
        await PostSQL.increment_view_count(db, post_id)
        
        return PostResponse(**post)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 조회 중 오류가 발생했습니다"
        )

@router.get("/slug/{slug}", response_model=PostResponse)
async def get_post_by_slug(
    slug: str,
    db: asyncpg.Connection = Depends(get_db)
):
    """슬러그로 게시글 조회"""
    
    try:
        post = await PostSQL.get_post_by_slug(db, slug)
        
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없습니다"
            )
        
        # 조회수 증가
        await PostSQL.increment_view_count(db, post["id"])
        
        return PostResponse(**post)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 조회 중 오류가 발생했습니다"
        )

@router.put("/{post_id}", response_model=BaseResponse)
async def update_post(
    post_id: int,
    post_data: PostUpdate,
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """게시글 수정"""
    
    try:
        # None이 아닌 필드만 추출
        update_data = {k: v for k, v in post_data.dict().items() if v is not None}
        
        updated_post = await PostSQL.update_post(
            db, post_id, current_user["id"], **update_data
        )
        
        if not updated_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없거나 수정 권한이 없습니다"
            )
        
        return BaseResponse(
            success=True,
            message="게시글이 수정되었습니다",
            data={"post_id": updated_post["id"]}
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 수정 중 오류가 발생했습니다"
        )

@router.delete("/{post_id}", response_model=BaseResponse)
async def delete_post(
    post_id: int,
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """게시글 삭제"""
    
    try:
        success = await PostSQL.delete_post(db, post_id, current_user["id"])
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없거나 삭제 권한이 없습니다"
            )
        
        return BaseResponse(
            success=True,
            message="게시글이 삭제되었습니다"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 삭제 중 오류가 발생했습니다"
        )

@router.post("/{post_id}/publish", response_model=BaseResponse)
async def publish_post(
    post_id: int,
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """게시글 발행"""
    
    try:
        published_post = await PostSQL.publish_post(
            db, post_id, current_user["id"]
        )
        
        if not published_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="게시글을 찾을 수 없거나 발행 권한이 없습니다"
            )
        
        return BaseResponse(
            success=True,
            message="게시글이 발행되었습니다",
            data={
                "post_id": published_post["id"],
                "published_at": published_post["published_at"].isoformat()
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="게시글 발행 중 오류가 발생했습니다"
        )

@router.post("/{post_id}/like", response_model=BaseResponse)
async def toggle_like_post(
    post_id: int,
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """게시글 좋아요 토글"""
    
    try:
        result = await PostSQL.toggle_like_post(
            db, post_id, current_user["id"]
        )
        
        action = "좋아요" if result["liked"] else "좋아요 취소"
        
        return BaseResponse(
            success=True,
            message=f"게시글 {action}가 완료되었습니다",
            data=result
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="좋아요 처리 중 오류가 발생했습니다"
        )
```

### 3. 사용자 관련 API

```python
# app/api/users.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
import asyncpg

from app.models.schemas import (
    UserResponse, UserProfile, UserUpdate, BaseResponse, PaginatedResponse
)
from app.database import get_db
from app.sql.users import UserSQL
from app.api.auth import get_current_user

router = APIRouter()

@router.get("/", response_model=PaginatedResponse)
async def get_users_list(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, min_length=1, max_length=50),
    db: asyncpg.Connection = Depends(get_db)
):
    """사용자 목록 조회"""
    
    try:
        offset = (page - 1) * size
        
        users = await UserSQL.get_users_list(
            db, limit=size, offset=offset, search=search
        )
        
        total = await UserSQL.get_users_count(db, search=search)
        
        return PaginatedResponse(
            items=users,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 목록 조회 중 오류가 발생했습니다"
        )

@router.get("/{user_id}", response_model=UserProfile)
async def get_user_profile(
    user_id: int,
    db: asyncpg.Connection = Depends(get_db)
):
    """사용자 프로필 조회"""
    
    try:
        user = await UserSQL.get_user_profile(db, user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )
        
        return UserProfile(**user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 프로필 조회 중 오류가 발생했습니다"
        )

@router.put("/me", response_model=BaseResponse)
async def update_my_profile(
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """내 프로필 수정"""
    
    try:
        # None이 아닌 필드만 추출
        update_data = {k: v for k, v in user_data.dict().items() if v is not None}
        
        if not update_data:
            return BaseResponse(
                success=True,
                message="수정할 내용이 없습니다"
            )
        
        updated_user = await UserSQL.update_user(
            db, current_user["id"], **update_data
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )
        
        return BaseResponse(
            success=True,
            message="프로필이 수정되었습니다",
            data={"user_id": updated_user["id"]}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필 수정 중 오류가 발생했습니다"
        )
```

### 4. 카테고리 및 태그 API

```python
# app/api/categories.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import asyncpg

from app.models.schemas import CategoryCreate, CategoryResponse, BaseResponse
from app.database import get_db
from app.sql.categories import CategorySQL
from app.api.auth import get_current_user

router = APIRouter()

@router.post("/", response_model=BaseResponse)
async def create_category(
    category_data: CategoryCreate,
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """카테고리 생성 (관리자만)"""
    
    # 관리자 권한 확인 (실제로는 is_superuser 체크)
    if not current_user.get("is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="카테고리 생성 권한이 없습니다"
        )
    
    try:
        category = await CategorySQL.create_category(
            db,
            name=category_data.name,
            slug=category_data.slug,
            description=category_data.description,
            color=category_data.color
        )
        
        return BaseResponse(
            success=True,
            message="카테고리가 생성되었습니다",
            data={"category_id": category["id"]}
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="카테고리 생성 중 오류가 발생했습니다"
        )

@router.get("/", response_model=List[CategoryResponse])
async def get_categories_list(
    db: asyncpg.Connection = Depends(get_db)
):
    """카테고리 목록 조회"""
    
    try:
        categories = await CategorySQL.get_categories_list(db)
        return [CategoryResponse(**category) for category in categories]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="카테고리 목록 조회 중 오류가 발생했습니다"
        )

@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category_by_id(
    category_id: int,
    db: asyncpg.Connection = Depends(get_db)
):
    """ID로 카테고리 조회"""
    
    try:
        category = await CategorySQL.get_category_by_id(db, category_id)
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="카테고리를 찾을 수 없습니다"
            )
        
        return CategoryResponse(**category)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="카테고리 조회 중 오류가 발생했습니다"
        )

@router.get("/slug/{slug}", response_model=CategoryResponse)
async def get_category_by_slug(
    slug: str,
    db: asyncpg.Connection = Depends(get_db)
):
    """슬러그로 카테고리 조회"""
    
    try:
        category = await CategorySQL.get_category_by_slug(db, slug)
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="카테고리를 찾을 수 없습니다"
            )
        
        return CategoryResponse(**category)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="카테고리 조회 중 오류가 발생했습니다"
        )

# app/api/tags.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
import asyncpg

from app.models.schemas import TagCreate, TagResponse, BaseResponse
from app.database import get_db
from app.sql.categories import TagSQL
from app.api.auth import get_current_user

router = APIRouter()

@router.post("/", response_model=BaseResponse)
async def create_tag(
    tag_data: TagCreate,
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """태그 생성"""
    
    try:
        tag = await TagSQL.create_tag(
            db, name=tag_data.name, slug=tag_data.slug
        )
        
        return BaseResponse(
            success=True,
            message="태그가 생성되었습니다",
            data={"tag_id": tag["id"]}
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="태그 생성 중 오류가 발생했습니다"
        )

@router.get("/", response_model=List[TagResponse])
async def get_tags_list(
    limit: Optional[int] = Query(None, ge=1, le=100),
    db: asyncpg.Connection = Depends(get_db)
):
    """태그 목록 조회"""
    
    try:
        tags = await TagSQL.get_tags_list(db, limit=limit)
        return [TagResponse(**tag) for tag in tags]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="태그 목록 조회 중 오류가 발생했습니다"
        )
```

## 메인 애플리케이션 설정

### 1. FastAPI 앱 구성

```python
# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import uvicorn

from app.core.config import settings
from app.database import db_manager
from app.sql.migrations import Migration
from app.api import auth, posts, users, categories, tags

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    
    # 시작 시
    logger.info("🚀 FastAPI 애플리케이션 시작")
    
    try:
        # 데이터베이스 초기화
        await db_manager.initialize()
        
        # 마이그레이션 실행
        async with db_manager.get_connection() as conn:
            migration = Migration(conn)
            await migration.run_all_migrations()
        
        logger.info("✅ 데이터베이스 초기화 완료")
        
    except Exception as e:
        logger.error(f"❌ 애플리케이션 시작 실패: {e}")
        raise
    
    yield
    
    # 종료 시
    logger.info("🛑 FastAPI 애플리케이션 종료")
    await db_manager.close()

# FastAPI 앱 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="FastAPI와 Neon PostgreSQL을 활용한 블로그 API",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 전역 예외 처리기
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리"""
    logger.error(f"예상치 못한 오류: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "서버 내부 오류가 발생했습니다",
            "detail": str(exc) if settings.DEBUG else "Internal Server Error"
        }
    )

# 라우터 등록
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["인증"]
)

app.include_router(
    posts.router,
    prefix=f"{settings.API_V1_STR}/posts",
    tags=["게시글"]
)

app.include_router(
    users.router,
    prefix=f"{settings.API_V1_STR}/users",
    tags=["사용자"]
)

app.include_router(
    categories.router,
    prefix=f"{settings.API_V1_STR}/categories",
    tags=["카테고리"]
)

app.include_router(
    tags.router,
    prefix=f"{settings.API_V1_STR}/tags",
    tags=["태그"]
)

# 루트 엔드포인트
@app.get("/")
async def root():
    """API 루트"""
    return {
        "message": "FastAPI Neon PostgreSQL Blog API",
        "version": settings.VERSION,
        "docs_url": "/docs" if settings.DEBUG else None
    }

# 헬스 체크 엔드포인트
@app.get("/health")
async def health_check():
    """헬스 체크"""
    try:
        async with db_manager.get_connection() as conn:
            await conn.execute('SELECT 1')
        
        return {
            "status": "healthy",
            "database": "connected",
            "version": settings.VERSION
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
```

### 2. 의존성 주입 설정

```python
# app/core/dependencies.py
from fastapi import Depends, HTTPException, status, Query
from typing import Optional
import asyncpg

from app.database import get_db
from app.sql.users import UserSQL
from app.api.auth import get_current_user

async def get_optional_current_user(
    db: asyncpg.Connection = Depends(get_db),
    authorization: Optional[str] = None
) -> Optional[dict]:
    """선택적 현재 사용자 (로그인하지 않아도 접근 가능)"""
    
    if not authorization:
        return None
    
    try:
        # Bearer 토큰 추출
        token = authorization.replace("Bearer ", "")
        # 토큰 검증 로직 (get_current_user와 유사)
        # ... 구현
        return None  # 실제 구현 필요
    except:
        return None

class CommonQueryParams:
    """공통 쿼리 파라미터"""
    
    def __init__(
        self,
        page: int = Query(1, ge=1, description="페이지 번호"),
        size: int = Query(20, ge=1, le=100, description="페이지 크기"),
        search: Optional[str] = Query(None, min_length=1, max_length=100, description="검색어")
    ):
        self.page = page
        self.size = size
        self.search = search
        self.offset = (page - 1) * size

async def verify_post_owner(
    post_id: int,
    current_user: dict = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
) -> dict:
    """게시글 소유자 확인"""
    
    post_author = await db.fetchval(
        "SELECT author_id FROM posts WHERE id = $1", post_id
    )
    
    if not post_author:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="게시글을 찾을 수 없습니다"
        )
    
    if post_author != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="게시글 수정 권한이 없습니다"
        )
    
    return current_user

async def verify_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """관리자 권한 확인"""
    
    if not current_user.get("is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다"
        )
    
    return current_user
```

## 실행 및 테스트

### 1. 애플리케이션 실행

```bash
# 개발 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 프로덕션 실행 (Gunicorn 사용)
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 2. API 테스트

```python
# tests/test_api.py
import pytest
import asyncio
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def client():
    """테스트 클라이언트"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """루트 엔드포인트 테스트"""
    response = await client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """헬스 체크 테스트"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_user_registration(client: AsyncClient):
    """사용자 회원가입 테스트"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }
    
    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

@pytest.mark.asyncio
async def test_user_login(client: AsyncClient):
    """사용자 로그인 테스트"""
    # 먼저 사용자 등록
    await test_user_registration(client)
    
    # 로그인 시도
    login_data = {
        "username": "testuser",
        "password": "testpassword123"
    }
    
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

# 테스트 실행
# pytest tests/ -v
```

### 3. 성능 최적화 팁

```python
# app/core/performance.py
import asyncio
from functools import wraps
import time
import logging

logger = logging.getLogger(__name__)

def measure_time(func_name: str = None):
    """실행 시간 측정 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            end_time = time.time()
            
            execution_time = end_time - start_time
            name = func_name or func.__name__
            
            if execution_time > 1.0:  # 1초 이상 걸리는 쿼리 로깅
                logger.warning(f"Slow query detected: {name} took {execution_time:.2f}s")
            else:
                logger.info(f"Query {name} took {execution_time:.3f}s")
            
            return result
        return wrapper
    return decorator

class ConnectionPool:
    """커넥션 풀 모니터링"""
    
    @staticmethod
    async def get_pool_status(pool):
        """풀 상태 조회"""
        return {
            "size": pool.get_size(),
            "min_size": pool.get_min_size(),
            "max_size": pool.get_max_size(),
            "idle_connections": pool.get_idle_size(),
            "used_connections": pool.get_size() - pool.get_idle_size()
        }
```

## 배포 및 운영

### 1. Docker 컨테이너

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY app/ app/

# 환경변수 설정
ENV PYTHONPATH=/app

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  fastapi-app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://username:password@ep-xxx.neon.tech/dbname
      - SECRET_KEY=your-secret-key
      - DEBUG=False
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

### 2. 환경별 설정

```python
# app/core/config.py (환경별 설정 추가)
import os
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class Settings(BaseSettings):
    # ... 기존 설정
    
    ENVIRONMENT: Environment = Field(default=Environment.DEVELOPMENT)
    
    # 환경별 설정
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == Environment.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION
    
    # 데이터베이스 설정 (환경별)
    @property
    def database_config(self) -> dict:
        base_config = {
            "min_size": 5,
            "max_size": 20,
            "timeout": 60,
        }
        
        if self.is_production:
            base_config.update({
                "min_size": 10,
                "max_size": 50,
                "timeout": 30,
            })
        
        return base_config
```

## 결론

이 가이드를 통해 FastAPI와 Neon PostgreSQL을 활용하여 Raw SQL 기반의 고성능 블로그 API를 구축하는 방법을 배웠습니다.

### 🎯 핵심 성과

1. **현대적 아키텍처**: 비동기 처리와 타입 힌트로 성능과 안정성 확보
2. **클라우드 네이티브**: Neon의 서버리스 특성을 활용한 확장 가능한 구조
3. **Raw SQL 활용**: ORM 없이도 안전하고 효율적인 데이터베이스 조작
4. **실용적 기능**: 검색, 페이지네이션, 좋아요 등 실제 서비스에 필요한 기능

### 💡 확장 가능한 기능

- **파일 업로드**: S3 연동으로 이미지 업로드 기능
- **실시간 알림**: WebSocket을 활용한 실시간 댓글/좋아요 알림
- **캐싱**: Redis를 활용한 조회수 캐싱 및 세션 관리
- **검색 개선**: Elasticsearch 연동으로 고급 검색 기능
- **API 문서화**: OpenAPI 스펙 자동 생성 및 커스터마이징

### 🔧 운영 고려사항

- **모니터링**: 성능 메트릭 수집 및 알림 설정
- **보안**: HTTPS, API 키 관리, SQL 인젝션 방지
- **백업**: 정기적인 데이터베이스 백업 및 복구 계획
- **스케일링**: 로드 밸런싱 및 수평 확장 전략

FastAPI와 Neon의 조합은 개발 속도와 운영 편의성을 모두 만족시키는 현대적인 백엔드 솔루션입니다! 🚀
```

다음 단계에서 나머지 API 엔드포인트와 메인 애플리케이션 설정을 완성하겠습니다.
```

다음 단계에서 SQL 쿼리 모듈과 API 엔드포인트를 구현하겠습니다. 계속 진행할까요?