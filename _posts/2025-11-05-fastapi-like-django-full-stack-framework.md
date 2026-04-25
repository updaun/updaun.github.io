---
layout: post
title: "FastAPI를 Django처럼 사용하기: Full-Stack 프레임워크로 확장하는 방법"
date: 2025-11-05 10:00:00 +0900
categories: [Python, FastAPI, Django]
tags: [FastAPI, Django, ORM, SQLAlchemy, Jinja2, Migration, Admin, Authentication, Full-Stack]
description: "FastAPI를 Django처럼 풀스택 프레임워크로 확장하는 방법을 살펴봅니다. ORM, 템플릿, 마이그레이션, Admin 패널, 인증 시스템까지 Django의 핵심 기능들을 FastAPI에서 구현하는 완전한 가이드입니다."
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-11-05-fastapi-like-django-full-stack-framework.webp"
---

# FastAPI를 Django처럼 사용하기: Full-Stack 프레임워크로 확장

FastAPI는 빠른 API 개발에 최적화된 프레임워크이지만, Django처럼 풀스택 웹 애플리케이션 개발에도 충분히 활용할 수 있습니다. 이 포스트에서는 FastAPI에 Django의 핵심 기능들을 접목하여 완전한 웹 애플리케이션을 구축하는 방법을 알아보겠습니다.

## 🎯 학습 목표

- Django와 FastAPI의 철학적 차이 이해
- SQLAlchemy로 Django ORM 수준의 데이터베이스 관리
- Jinja2로 Django 템플릿 엔진 대체
- Alembic으로 Django Migrations 구현
- FastAPI Admin으로 Django Admin 패널 구축
- 인증 및 세션 관리 시스템 구현

---

## 🤔 1. Django vs FastAPI: 철학적 차이와 접근 방식

### 1.1 프레임워크 철학 비교

```python
# Django의 철학: "Batteries Included"
"""
Django는 웹 개발에 필요한 모든 것을 기본 제공:
- ORM (Object-Relational Mapping)
- Admin 패널
- Authentication 시스템
- Form 처리
- 템플릿 엔진
- Migration 시스템
- 보안 기능 (CSRF, XSS 방지)
"""

# FastAPI의 철학: "Minimalist & Modern"
"""
FastAPI는 API 개발에 집중하고 나머지는 선택:
- 빠른 성능 (Starlette 기반)
- 자동 문서화 (OpenAPI/Swagger)
- 타입 힌팅 기반 검증 (Pydantic)
- 비동기 지원
- 필요한 기능은 외부 라이브러리 조합
"""
```

### 1.2 Feature 비교표

| 기능 | Django | FastAPI | FastAPI + Extensions |
|------|--------|---------|---------------------|
| **ORM** | ✅ Django ORM | ❌ 기본 없음 | ✅ SQLAlchemy |
| **Admin** | ✅ 기본 제공 | ❌ 기본 없음 | ✅ FastAPI Admin, SQLAdmin |
| **Authentication** | ✅ 기본 제공 | ❌ 기본 없음 | ✅ FastAPI Users, OAuth2 |
| **Templates** | ✅ Django Templates | ❌ 기본 없음 | ✅ Jinja2 |
| **Migrations** | ✅ Django Migrations | ❌ 기본 없음 | ✅ Alembic |
| **Forms** | ✅ Django Forms | ❌ 기본 없음 | ✅ WTForms, Pydantic |
| **성능** | ⚡ 동기 | ⚡⚡⚡ 비동기 | ⚡⚡⚡ 비동기 |
| **API 문서** | ❌ 별도 설정 필요 | ✅ 자동 생성 | ✅ 자동 생성 |

---

## 🗄️ 2. SQLAlchemy: Django ORM 수준의 데이터베이스 관리

### 2.1 프로젝트 구조 설정

```bash
# 프로젝트 구조
fastapi-django-like/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 앱
│   ├── config.py            # 설정 (Django settings.py 같은 역할)
│   ├── database.py          # 데이터베이스 연결
│   ├── models/              # Django models와 동일
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── post.py
│   ├── schemas/             # Pydantic 스키마 (Django Forms/Serializers)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── post.py
│   ├── crud/                # Django ORM 쿼리 로직
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── post.py
│   ├── api/                 # Django views와 비슷
│   │   ├── __init__.py
│   │   ├── users.py
│   │   └── posts.py
│   ├── templates/           # Django templates
│   │   ├── base.html
│   │   └── index.html
│   └── static/              # Django static files
│       ├── css/
│       └── js/
├── alembic/                 # Django migrations
│   └── versions/
├── requirements.txt
└── alembic.ini
```

### 2.2 데이터베이스 설정 (Django settings.py 스타일)

```python
# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Django settings.py와 유사한 설정 관리"""
    
    # 기본 설정
    APP_NAME: str = "FastAPI Django-Like"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-here"
    
    # 데이터베이스 설정 (Django DATABASES와 유사)
    DATABASE_URL: str = "postgresql://user:password@localhost/dbname"
    # SQLite: "sqlite:///./app.db"
    # MySQL: "mysql+pymysql://user:password@localhost/dbname"
    
    # CORS 설정 (Django CORS_ALLOWED_ORIGINS와 유사)
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]
    
    # 인증 설정
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 미디어/정적 파일 설정
    MEDIA_URL: str = "/media/"
    STATIC_URL: str = "/static/"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
```

```python
# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Django의 데이터베이스 연결과 유사
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Django DEBUG=True와 유사한 SQL 로깅
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Django models.Model과 유사한 Base 클래스
Base = declarative_base()

# Django의 get_db() 패턴
def get_db():
    """
    Django의 request.db나 connection과 유사한 역할
    의존성 주입으로 사용
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 2.3 모델 정의 (Django models.py 스타일)

```python
# app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
import bcrypt

class User(Base):
    """Django User 모델과 유사한 구조"""
    __tablename__ = "users"
    
    # Django의 AutoField와 유사
    id = Column(Integer, primary_key=True, index=True)
    
    # Django CharField와 유사
    username = Column(String(150), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    
    # Django의 암호화된 비밀번호 필드
    hashed_password = Column(String(255), nullable=False)
    
    # Django BooleanField
    is_active = Column(Boolean, default=True)
    is_staff = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    
    # Django TextField
    bio = Column(Text, nullable=True)
    
    # Django DateTimeField with auto_now_add
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Django DateTimeField with auto_now
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Django의 related_name과 유사한 relationship
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(username='{self.username}')>"
    
    # Django 모델 메서드와 유사
    def set_password(self, password: str):
        """Django의 set_password()와 동일"""
        self.hashed_password = bcrypt.hashpw(
            password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """Django의 check_password()와 동일"""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.hashed_password.encode('utf-8')
        )
    
    @property
    def full_name(self):
        """Django의 @property와 동일"""
        return self.username

class UserProfile(Base):
    """Django OneToOneField 예시"""
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    avatar_url = Column(String(500))
    phone = Column(String(20))
    address = Column(Text)
    
    # Django의 OneToOneField와 유사
    user = relationship("User", backref="profile", uselist=False)
```

```python
# app/models/post.py
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

# Django ManyToManyField를 위한 중간 테이블
post_tags = Table(
    'post_tags',
    Base.metadata,
    Column('post_id', Integer, ForeignKey('posts.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

class Post(Base):
    """Django Post 모델 예시"""
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(250), unique=True, index=True)
    content = Column(Text, nullable=False)
    excerpt = Column(Text)
    
    # Django ForeignKey
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    
    is_published = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    
    # Django auto_now_add, auto_now
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    # Django relationships
    author = relationship("User", back_populates="posts")
    category = relationship("Category", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    
    # Django ManyToManyField
    tags = relationship("Tag", secondary=post_tags, back_populates="posts")
    
    def __repr__(self):
        return f"<Post(title='{self.title}')>"
    
    # Django의 save() 메서드와 유사한 로직
    def publish(self):
        """포스트 발행"""
        from datetime import datetime
        self.is_published = True
        self.published_at = datetime.utcnow()

class Category(Base):
    """Django Category 모델"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(150), unique=True, index=True)
    description = Column(Text)
    
    # Django related_name
    posts = relationship("Post", back_populates="category")

class Tag(Base):
    """Django Tag 모델"""
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    
    # Django ManyToManyField의 역참조
    posts = relationship("Post", secondary=post_tags, back_populates="tags")

class Comment(Base):
    """Django Comment 모델"""
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    post = relationship("Post", back_populates="comments")
    author = relationship("User")
```

### 2.4 CRUD 패턴 (Django ORM 쿼리 스타일)

```python
# app/crud/user.py
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List
from ..models.user import User
from ..schemas.user import UserCreate, UserUpdate

class UserCRUD:
    """Django ORM 스타일의 CRUD 작업"""
    
    @staticmethod
    def get(db: Session, user_id: int) -> Optional[User]:
        """Django의 Model.objects.get()과 유사"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        """Django의 User.objects.get(username=username)"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Django의 User.objects.get(email=email)"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def filter(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None,
        is_staff: Optional[bool] = None
    ) -> List[User]:
        """Django의 User.objects.filter()와 유사"""
        query = db.query(User)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        if is_staff is not None:
            query = query.filter(User.is_staff == is_staff)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def search(db: Session, search_term: str) -> List[User]:
        """Django의 Q 객체를 사용한 복잡한 쿼리"""
        return db.query(User).filter(
            or_(
                User.username.ilike(f"%{search_term}%"),
                User.email.ilike(f"%{search_term}%"),
                User.bio.ilike(f"%{search_term}%")
            )
        ).all()
    
    @staticmethod
    def create(db: Session, user_data: UserCreate) -> User:
        """Django의 User.objects.create()와 유사"""
        user = User(
            username=user_data.username,
            email=user_data.email
        )
        user.set_password(user_data.password)
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def update(db: Session, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Django의 user.save()와 유사"""
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return None
        
        update_data = user_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "password":
                user.set_password(value)
            else:
                setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def delete(db: Session, user_id: int) -> bool:
        """Django의 user.delete()와 유사"""
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return False
        
        db.delete(user)
        db.commit()
        return True
    
    @staticmethod
    def get_or_create(db: Session, username: str, email: str) -> tuple[User, bool]:
        """Django의 get_or_create()와 동일"""
        user = db.query(User).filter(User.username == username).first()
        
        if user:
            return user, False
        
        user = User(username=username, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, True

# 사용 예시 (Django ORM과 매우 유사)
"""
# Django
user = User.objects.get(id=1)
users = User.objects.filter(is_active=True)
user, created = User.objects.get_or_create(username="john")

# FastAPI + SQLAlchemy
user = UserCRUD.get(db, user_id=1)
users = UserCRUD.filter(db, is_active=True)
user, created = UserCRUD.get_or_create(db, username="john", email="john@example.com")
"""
```

```python
# app/crud/post.py
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from datetime import datetime
from ..models.post import Post, Category, Tag

class PostCRUD:
    """Django ORM 스타일의 Post CRUD"""
    
    @staticmethod
    def get_published(db: Session, skip: int = 0, limit: int = 10) -> List[Post]:
        """Django의 Post.objects.filter(is_published=True).select_related()"""
        return db.query(Post).options(
            joinedload(Post.author),
            joinedload(Post.category)
        ).filter(
            Post.is_published == True
        ).order_by(
            Post.published_at.desc()
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Optional[Post]:
        """Django의 Post.objects.get(slug=slug)"""
        return db.query(Post).options(
            joinedload(Post.author),
            joinedload(Post.category),
            joinedload(Post.tags)
        ).filter(Post.slug == slug).first()
    
    @staticmethod
    def get_by_author(db: Session, author_id: int) -> List[Post]:
        """Django의 Post.objects.filter(author_id=author_id)"""
        return db.query(Post).filter(
            Post.author_id == author_id
        ).order_by(Post.created_at.desc()).all()
    
    @staticmethod
    def get_by_category(db: Session, category_id: int) -> List[Post]:
        """Django의 Post.objects.filter(category_id=category_id)"""
        return db.query(Post).filter(
            Post.category_id == category_id,
            Post.is_published == True
        ).all()
    
    @staticmethod
    def increment_view_count(db: Session, post_id: int):
        """Django의 F() 표현식과 유사한 업데이트"""
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            post.view_count += 1
            db.commit()
    
    @staticmethod
    def publish_post(db: Session, post_id: int) -> Optional[Post]:
        """포스트 발행 (비즈니스 로직)"""
        post = db.query(Post).filter(Post.id == post_id).first()
        if post:
            post.publish()
            db.commit()
            db.refresh(post)
        return post
```

---

## 📝 3. Jinja2 템플릿: Django Templates 대체

### 3.1 템플릿 엔진 설정

```python
# app/main.py
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title="FastAPI Django-Like App")

# Django의 STATIC_URL과 유사
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Django의 TEMPLATES 설정과 유사
templates = Jinja2Templates(directory="app/templates")

# Django의 템플릿 컨텍스트 프로세서와 유사한 기능
def get_template_context(request: Request) -> dict:
    """모든 템플릿에 전달될 기본 컨텍스트"""
    return {
        "request": request,
        "app_name": "FastAPI Django-Like",
        "debug": settings.DEBUG,
        "user": getattr(request.state, "user", None)
    }

@app.get("/")
async def home(request: Request):
    """Django의 render() 함수와 유사"""
    context = get_template_context(request)
    context.update({
        "title": "Home Page",
        "posts": []  # 실제로는 DB에서 조회
    })
    return templates.TemplateResponse("index.html", context)
```

### 3.2 템플릿 파일 (Django 템플릿과 거의 동일)

{% raw %}
```html
<!-- app/templates/base.html -->
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ app_name }}{% endblock %}</title>
    
    <!-- Django의 {% load static %}과 유사 -->
    <link rel="stylesheet" href="{{ url_for('static', path='css/style.css') }}">
    
    {% block extra_head %}{% endblock %}
</head>
<body>
    <nav class="navbar">
        <div class="container">
            <a href="/" class="brand">{{ app_name }}</a>
            <ul class="nav-links">
                {% if user %}
                    <li><a href="/posts">Posts</a></li>
                    <li><a href="/profile">Profile</a></li>
                    <li><a href="/logout">Logout</a></li>
                {% else %}
                    <li><a href="/login">Login</a></li>
                    <li><a href="/register">Register</a></li>
                {% endif %}
            </ul>
        </div>
    </nav>
    
    <main class="container">
        {% block content %}{% endblock %}
    </main>
    
    <footer>
        <div class="container">
            <p>&copy; 2025 {{ app_name }}. All rights reserved.</p>
        </div>
    </footer>
    
    <script src="{{ url_for('static', path='js/main.js') }}"></script>
    {% block extra_scripts %}{% endblock %}
</body>
</html>
```
{% endraw %}

{% raw %}
```html
<!-- app/templates/posts/list.html -->
{% extends "base.html" %}

{% block title %}Posts - {{ app_name }}{% endblock %}

{% block content %}
<div class="posts-container">
    <h1>Latest Posts</h1>
    
    {% if posts %}
        {% for post in posts %}
        <article class="post-card">
            <h2>
                <a href="{{ url_for('get_post', slug=post.slug) }}">
                    {{ post.title }}
                </a>
            </h2>
            
            <div class="post-meta">
                <span class="author">By {{ post.author.username }}</span>
                <span class="date">{{ post.created_at.strftime('%Y-%m-%d') }}</span>
                <span class="views">{{ post.view_count }} views</span>
            </div>
            
            <p class="excerpt">{{ post.excerpt }}</p>
            
            {% if post.tags %}
            <div class="tags">
                {% for tag in post.tags %}
                    <span class="tag">{{ tag.name }}</span>
                {% endfor %}
            </div>
            {% endif %}
        </article>
        {% endfor %}
        
        <!-- Django 페이지네이션과 유사 -->
        <div class="pagination">
            {% if page > 1 %}
                <a href="?page={{ page - 1 }}">Previous</a>
            {% endif %}
            
            <span>Page {{ page }} of {{ total_pages }}</span>
            
            {% if page < total_pages %}
                <a href="?page={{ page + 1 }}">Next</a>
            {% endif %}
        </div>
    {% else %}
        <p>No posts available.</p>
    {% endif %}
</div>
{% endblock %}
```
{% endraw %}

### 3.3 뷰 함수 (Django views와 유사)

```python
# app/api/posts.py
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..crud.post import PostCRUD
from ..templates import templates

router = APIRouter()

@router.get("/posts", response_class=HTMLResponse)
async def list_posts(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db)
):
    """Django의 ListView와 유사"""
    per_page = 10
    skip = (page - 1) * per_page
    
    posts = PostCRUD.get_published(db, skip=skip, limit=per_page)
    total_posts = db.query(Post).filter(Post.is_published == True).count()
    total_pages = (total_posts + per_page - 1) // per_page
    
    context = {
        "request": request,
        "posts": posts,
        "page": page,
        "total_pages": total_pages
    }
    
    return templates.TemplateResponse("posts/list.html", context)

@router.get("/posts/{slug}", response_class=HTMLResponse)
async def get_post(
    request: Request,
    slug: str,
    db: Session = Depends(get_db)
):
    """Django의 DetailView와 유사"""
    post = PostCRUD.get_by_slug(db, slug=slug)
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # 조회수 증가 (Django의 post-save signal과 유사)
    PostCRUD.increment_view_count(db, post.id)
    
    context = {
        "request": request,
        "post": post
    }
    
    return templates.TemplateResponse("posts/detail.html", context)
```

---

## 🔄 4. Alembic: Django Migrations 구현

### 4.1 Alembic 설정

```bash
# Alembic 초기화 (Django의 python manage.py makemigrations와 유사)
alembic init alembic
```

```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.database import Base
from app.config import settings

# Django의 INSTALLED_APPS처럼 모든 모델 import
from app.models.user import User, UserProfile
from app.models.post import Post, Category, Tag, Comment

# Alembic Config 객체
config = context.config

# Django settings와 연결
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Django models.py처럼 metadata 연결
target_metadata = Base.metadata

def run_migrations_offline():
    """Django의 --fake 마이그레이션과 유사"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """실제 마이그레이션 실행"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 4.2 마이그레이션 명령어 (Django와 비교)

```bash
# Django makemigrations와 유사
alembic revision --autogenerate -m "Create user table"

# Django migrate와 유사
alembic upgrade head

# Django migrate app_name migration_name과 유사
alembic upgrade <revision>

# Django showmigrations와 유사
alembic history

# Django migrate app_name zero와 유사
alembic downgrade base

# 특정 마이그레이션으로 롤백
alembic downgrade -1
```

### 4.3 마이그레이션 파일 예시

```python
# alembic/versions/001_create_user_table.py
"""Create user table

Revision ID: 001
Revises: 
Create Date: 2025-11-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# Django의 Migration class와 유사
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Django의 Migration.operations와 유사"""
    # Django: migrations.CreateModel()
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=150), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_staff', sa.Boolean(), nullable=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Django: migrations.AddIndex()
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

def downgrade():
    """Django의 역방향 마이그레이션과 동일"""
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')
```

---

## 👤 5. 인증 시스템: Django Authentication 구현

### 5.1 JWT 기반 인증 (Django Session 대체)

```python
# app/auth.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .database import get_db
from .models.user import User
from .config import settings

# Django의 PASSWORD_HASHERS와 유사
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Django의 LOGIN_URL과 유사
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Django의 SECRET_KEY 사용
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Django의 check_password()와 동일"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Django의 make_password()와 동일"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWT 토큰 생성 (Django session 대체)"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Django의 request.user와 유사"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Django의 @login_required와 유사"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Django의 @user_passes_test(lambda u: u.is_superuser)와 유사"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required"
        )
    return current_user

def require_staff(current_user: User = Depends(get_current_user)) -> User:
    """Django의 @staff_member_required와 유사"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required"
        )
    return current_user
```

### 5.2 인증 API 엔드포인트

```python
# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from ..database import get_db
from ..schemas.user import UserCreate, UserResponse, Token
from ..crud.user import UserCRUD
from ..auth import (
    verify_password,
    create_access_token,
    get_current_active_user,
    get_password_hash
)
from ..config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Django의 UserCreationForm과 유사한 회원가입"""
    
    # 중복 체크
    if UserCRUD.get_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    if UserCRUD.get_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 사용자 생성
    user = UserCRUD.create(db, user_data)
    return user

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Django의 authenticate()와 login()과 유사"""
    
    # 사용자 인증
    user = UserCRUD.get_by_username(db, form_data.username)
    
    if not user or not user.check_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # 토큰 생성 (Django session 대체)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_active_user)):
    """Django의 request.user와 유사"""
    return current_user

@router.post("/logout")
def logout(current_user: User = Depends(get_current_active_user)):
    """Django의 logout() - 클라이언트에서 토큰 삭제"""
    # JWT는 상태가 없으므로 클라이언트에서 토큰 삭제
    # Redis 등을 사용하여 토큰 블랙리스트 구현 가능
    return {"message": "Successfully logged out"}
```

---

## 🎨 6. Admin 패널: Django Admin 대체

### 6.1 SQLAdmin 사용

```python
# app/admin.py
from sqladmin import Admin, ModelView
from .database import engine
from .models.user import User
from .models.post import Post, Category, Tag

# Django admin.site와 유사
admin = Admin(app, engine)

class UserAdmin(ModelView, model=User):
    """Django의 UserAdmin과 유사"""
    column_list = [User.id, User.username, User.email, User.is_active, User.is_staff]
    column_searchable_list = [User.username, User.email]
    column_sortable_list = [User.id, User.username, User.created_at]
    column_filters = [User.is_active, User.is_staff, User.is_superuser]
    
    # Django의 list_display와 유사
    column_labels = {
        "id": "ID",
        "username": "Username",
        "email": "Email",
        "is_active": "Active",
        "is_staff": "Staff Status"
    }
    
    # Django의 readonly_fields와 유사
    form_excluded_columns = [User.hashed_password, User.created_at]
    
    # Django의 list_per_page와 유사
    page_size = 25

class PostAdmin(ModelView, model=Post):
    """Django의 PostAdmin과 유사"""
    column_list = [
        Post.id, Post.title, Post.author, Post.category, 
        Post.is_published, Post.created_at
    ]
    column_searchable_list = [Post.title, Post.content]
    column_sortable_list = [Post.id, Post.title, Post.created_at, Post.view_count]
    column_filters = [Post.is_published, Post.category, Post.author]
    
    # Django의 prepopulated_fields와 유사한 기능
    form_args = {
        "slug": {
            "description": "URL-friendly version of the title"
        }
    }

class CategoryAdmin(ModelView, model=Category):
    """Django의 CategoryAdmin과 유사"""
    column_list = [Category.id, Category.name, Category.slug]
    column_searchable_list = [Category.name]

class TagAdmin(ModelView, model=Tag):
    """Django의 TagAdmin과 유사"""
    column_list = [Tag.id, Tag.name]
    column_searchable_list = [Tag.name]

# Django의 admin.site.register()와 유사
admin.add_view(UserAdmin)
admin.add_view(PostAdmin)
admin.add_view(CategoryAdmin)
admin.add_view(TagAdmin)
```

### 6.2 커스텀 Admin 액션

```python
# app/admin_custom.py
from sqladmin import action
from sqlalchemy.orm import Session

class PostAdminCustom(PostAdmin):
    """Django의 admin actions와 유사한 커스텀 액션"""
    
    @action(
        name="publish_selected",
        label="Publish selected posts",
        confirmation_message="Are you sure you want to publish selected posts?",
        add_in_detail=True,
        add_in_list=True,
    )
    async def publish_posts(self, request):
        """Django의 admin action과 동일한 방식"""
        # 선택된 포스트들을 발행
        pks = request.query_params.get("pks", "").split(",")
        
        async with self.session_maker() as session:
            for pk in pks:
                post = await session.get(Post, int(pk))
                if post:
                    post.publish()
            await session.commit()
        
        return {"message": f"Published {len(pks)} posts"}
```

---

## 🔌 7. 미들웨어와 시그널: Django 패턴 구현

### 7.1 미들웨어

```python
# app/middleware.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger(__name__)

class TimingMiddleware(BaseHTTPMiddleware):
    """Django의 미들웨어와 유사한 요청 처리 시간 측정"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        logger.info(f"{request.method} {request.url.path} - {process_time:.3f}s")
        
        return response

class UserMiddleware(BaseHTTPMiddleware):
    """Django의 AuthenticationMiddleware와 유사"""
    
    async def dispatch(self, request: Request, call_next):
        # 토큰에서 사용자 정보 추출 (선택적)
        token = request.headers.get("Authorization")
        
        if token:
            try:
                # 토큰 검증 및 사용자 정보 추가
                # request.state.user = user
                pass
            except Exception:
                pass
        
        response = await call_next(request)
        return response

# app/main.py에서 등록
app.add_middleware(TimingMiddleware)
app.add_middleware(UserMiddleware)
```

### 7.2 이벤트/시그널 시스템

```python
# app/signals.py
from typing import Callable, Dict, List

# Django signals와 유사한 이벤트 시스템
class Signal:
    """Django의 Signal class와 유사"""
    
    def __init__(self):
        self.receivers: List[Callable] = []
    
    def connect(self, receiver: Callable):
        """Django의 signal.connect()와 동일"""
        self.receivers.append(receiver)
    
    def send(self, sender, **kwargs):
        """Django의 signal.send()와 동일"""
        for receiver in self.receivers:
            receiver(sender, **kwargs)

# Django의 pre_save, post_save와 유사
post_save = Signal()
pre_save = Signal()
post_delete = Signal()

# 시그널 리시버 예시
def send_welcome_email(sender, instance, created, **kwargs):
    """Django의 @receiver 데코레이터와 유사"""
    if created and isinstance(instance, User):
        print(f"Sending welcome email to {instance.email}")

def update_post_count(sender, instance, **kwargs):
    """포스트 생성 시 작가의 포스트 수 업데이트"""
    if isinstance(instance, Post):
        print(f"Updating post count for author {instance.author.username}")

# 시그널 연결
post_save.connect(send_welcome_email)
post_save.connect(update_post_count)

# CRUD에서 시그널 발송
def create_user_with_signal(db: Session, user_data):
    user = User(**user_data)
    
    # pre_save 시그널
    pre_save.send(sender=User, instance=user, created=True)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # post_save 시그널
    post_save.send(sender=User, instance=user, created=True)
    
    return user
```

---

## 📋 결론 및 비교 요약

### 🎯 Django vs FastAPI + Extensions

| 항목 | Django | FastAPI + Extensions | 비고 |
|------|--------|---------------------|------|
| **학습 곡선** | 중간 | 높음 | FastAPI는 여러 라이브러리 조합 필요 |
| **개발 속도** | 빠름 | 중간 | Django는 기본 제공이 많아 빠름 |
| **성능** | 좋음 | 우수 | FastAPI는 비동기로 더 빠름 |
| **유연성** | 낮음 | 높음 | FastAPI는 원하는 대로 조합 가능 |
| **API 문서** | 수동 | 자동 | FastAPI의 강력한 장점 |
| **타입 안정성** | 낮음 | 높음 | FastAPI는 Pydantic 기반 |

### 🚀 언제 무엇을 선택할까?

**Django를 선택해야 할 때:**
- 빠른 프로토타입 개발이 필요할 때
- Admin 패널이 중요한 CMS나 백오피스 시스템
- 전통적인 서버 사이드 렌더링 웹사이트
- 팀이 Django에 익숙할 때

**FastAPI를 선택해야 할 때:**
- 고성능 API가 필요할 때
- 마이크로서비스 아키텍처
- 비동기 처리가 중요한 시스템
- 최신 Python 기능 활용하고 싶을 때
- 타입 안정성이 중요할 때

### 🛠️ 하이브리드 접근

```python
# 두 프레임워크의 장점을 모두 활용
"""
1. Django를 메인 프레임워크로 사용하면서 FastAPI를 API 레이어로 추가
   - Django: Admin, ORM, Migrations, Authentication
   - FastAPI: 고성능 REST API 엔드포인트

2. FastAPI를 메인으로 사용하되 Django의 장점을 도입
   - FastAPI: 메인 애플리케이션
   - SQLAlchemy: ORM (Django ORM 패턴 적용)
   - Alembic: Migrations
   - SQLAdmin: Admin 패널
"""
```

### 💡 Best Practices

1. **프로젝트 구조**: Django의 앱 구조를 FastAPI에도 적용
2. **ORM 패턴**: SQLAlchemy를 Django ORM 스타일로 사용
3. **의존성 주입**: FastAPI의 강력한 DI 시스템 활용
4. **타입 힌팅**: 모든 곳에 타입 힌팅 적용
5. **문서화**: FastAPI의 자동 문서화 활용
6. **테스팅**: pytest + FastAPI TestClient 조합

FastAPI를 Django처럼 사용하는 것은 충분히 가능하며, 각 프레임워크의 장점을 결합하면 강력하고 유연한 웹 애플리케이션을 만들 수 있습니다! 🚀

---

### 🏷️ 태그
`FastAPI` `Django` `SQLAlchemy` `ORM` `Alembic` `Migrations` `Admin` `Authentication` `Full-Stack` `Python` `웹개발`