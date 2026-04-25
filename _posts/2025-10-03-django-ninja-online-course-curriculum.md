---
layout: post
title: "Django Ninja 온라인 강의 커리큘럼 - 초보자부터 중급자까지 체계적인 학습 로드맵"
date: 2025-10-03 10:00:00 +0900
categories: [Education, Web Development, Backend]
tags: [django-ninja, curriculum, online-course, education, api-development, learning-path]
description: "Django Ninja를 처음 배우는 초보자부터 실무에서 활용할 수 있는 중급자까지, 체계적이고 실무 중심의 온라인 강의 커리큘럼을 제안합니다. 프로젝트 기반 학습과 단계별 난이도 조절로 효과적인 학습 경험을 제공합니다."
author: "updaun"
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-10-03-django-ninja-online-course-curriculum.webp"
---

## 개요

Django Ninja는 FastAPI에서 영감을 받은 현대적인 Django REST API 프레임워크입니다. 하지만 체계적인 학습 자료가 부족한 상황에서, 많은 개발자들이 어떻게 시작해야 할지 막막해합니다. 이 포스트에서는 초보자부터 중급자까지를 위한 완벽한 Django Ninja 온라인 강의 커리큘럼을 제안합니다.

## 강의 커리큘럼 설계 원칙

### 1. 학습자 중심 설계
- **단계별 난이도 조절**: 쉬운 것부터 복잡한 것까지
- **실무 중심 프로젝트**: 포트폴리오로 활용 가능한 결과물
- **즉시 피드백**: 각 단계마다 동작하는 코드 제공

### 2. 실무 역량 개발
- **현업 적용 가능한 기술**: 실제 서비스에서 사용하는 패턴
- **베스트 프랙티스**: 코드 품질과 유지보수성 고려
- **문제 해결 능력**: 디버깅과 트러블슈팅 방법

### 3. 지속 가능한 학습
- **반복 학습**: 핵심 개념의 점진적 심화
- **커뮤니티 연결**: 학습자 간 상호작용 및 질의응답
- **최신 트렌드 반영**: 업계 동향과 신기술 소개

## 전체 커리큘럼 구조

### 📚 **총 강의 시간**: 약 40-50시간 (16주 과정)
### 🎯 **학습 목표**: 실무에서 Django Ninja를 활용한 API 개발 능력 습득
### 💼 **최종 결과물**: 3개의 완성된 프로젝트 포트폴리오

---

## 🏁 Module 1: Django Ninja 시작하기 (초보자 레벨)
**소요 시간**: 6-8시간 (2주)

### Week 1: 기초 환경 설정 및 첫 API 만들기

#### Lesson 1.1: Django Ninja 소개 및 환경 설정 (1시간)
- **학습 목표**: Django Ninja의 특징과 장점 이해
- **실습 내용**:
  ```bash
  # 가상환경 설정
  python -m venv django_ninja_env
  source django_ninja_env/bin/activate
  
  # 패키지 설치
  pip install django django-ninja
  
  # 프로젝트 생성
  django-admin startproject ninja_tutorial
  cd ninja_tutorial
  python manage.py startapp api
  ```

- **핵심 개념**:
  - Django Ninja vs Django REST Framework 비교
  - FastAPI와의 유사점 및 차이점
  - 타입 힌트의 중요성

#### Lesson 1.2: 첫 번째 API 엔드포인트 생성 (1.5시간)
- **학습 목표**: 기본적인 GET/POST API 작성법 습득
- **실습 내용**:
  ```python
  # api/api.py
  from ninja import NinjaAPI
  from ninja import Schema
  from typing import List
  
  api = NinjaAPI()
  
  class MessageSchema(Schema):
      content: str
      author: str
  
  @api.get("/hello")
  def hello(request):
      return {"message": "Hello Django Ninja!"}
  
  @api.get("/messages", response=List[MessageSchema])
  def list_messages(request):
      return [
          {"content": "첫 번째 메시지", "author": "김개발"},
          {"content": "두 번째 메시지", "author": "이백엔드"}
      ]
  ```

- **핵심 개념**:
  - NinjaAPI 클래스 사용법
  - Schema를 이용한 응답 타입 정의
  - 자동 문서 생성 확인 (/docs)

#### Lesson 1.3: 요청 데이터 처리 및 유효성 검사 (1.5시간)
- **학습 목표**: 다양한 요청 데이터 타입 처리 방법 학습
- **실습 내용**:
  ```python
  from ninja import Schema
  from typing import Optional
  from datetime import datetime
  
  class CreateUserSchema(Schema):
      username: str
      email: str
      age: Optional[int] = None
      is_active: bool = True
  
  class UserResponseSchema(Schema):
      id: int
      username: str
      email: str
      created_at: datetime
  
  @api.post("/users", response=UserResponseSchema)
  def create_user(request, user_data: CreateUserSchema):
      # 유효성 검사는 자동으로 처리됨
      return {
          "id": 1,
          "username": user_data.username,
          "email": user_data.email,
          "created_at": datetime.now()
      }
  
  @api.get("/users/{user_id}")
  def get_user(request, user_id: int):
      return {"id": user_id, "username": f"user_{user_id}"}
  ```

- **핵심 개념**:
  - Path Parameters vs Query Parameters
  - 요청/응답 스키마 분리
  - 자동 데이터 유효성 검사

### Week 2: 데이터베이스 연동 및 CRUD 구현

#### Lesson 2.1: Django 모델과 Django Ninja 연동 (2시간)
- **학습 목표**: Django ORM과 Django Ninja 통합 사용법
- **실습 내용**:
  ```python
  # models.py
  from django.db import models
  
  class Category(models.Model):
      name = models.CharField(max_length=100)
      description = models.TextField(blank=True)
      created_at = models.DateTimeField(auto_now_add=True)
      
      def __str__(self):
          return self.name
  
  class Post(models.Model):
      title = models.CharField(max_length=200)
      content = models.TextField()
      category = models.ForeignKey(Category, on_delete=models.CASCADE)
      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)
      
      def __str__(self):
          return self.title
  
  # schemas.py
  from ninja import Schema, ModelSchema
  from .models import Post, Category
  
  class CategorySchema(ModelSchema):
      class Config:
          model = Category
          model_fields = "__all__"
  
  class PostCreateSchema(Schema):
      title: str
      content: str
      category_id: int
  
  class PostSchema(ModelSchema):
      category: CategorySchema
      
      class Config:
          model = Post
          model_fields = "__all__"
  ```

- **핵심 개념**:
  - ModelSchema vs 일반 Schema
  - 외래키 관계 처리
  - 중첩된 스키마 구조

#### Lesson 2.2: 완전한 CRUD API 구현 (2시간)
- **학습 목표**: Create, Read, Update, Delete 전체 구현
- **실습 내용**:
  ```python
  from django.shortcuts import get_object_or_404
  from ninja import Router
  from typing import List
  
  router = Router()
  
  # Create
  @router.post("/posts", response=PostSchema)
  def create_post(request, post_data: PostCreateSchema):
      category = get_object_or_404(Category, id=post_data.category_id)
      post = Post.objects.create(
          title=post_data.title,
          content=post_data.content,
          category=category
      )
      return post
  
  # Read (List)
  @router.get("/posts", response=List[PostSchema])
  def list_posts(request, category_id: int = None):
      posts = Post.objects.select_related('category')
      if category_id:
          posts = posts.filter(category_id=category_id)
      return posts
  
  # Read (Detail)
  @router.get("/posts/{post_id}", response=PostSchema)
  def get_post(request, post_id: int):
      return get_object_or_404(Post, id=post_id)
  
  # Update
  @router.put("/posts/{post_id}", response=PostSchema)
  def update_post(request, post_id: int, post_data: PostCreateSchema):
      post = get_object_or_404(Post, id=post_id)
      post.title = post_data.title
      post.content = post_data.content
      post.category_id = post_data.category_id
      post.save()
      return post
  
  # Delete
  @router.delete("/posts/{post_id}")
  def delete_post(request, post_id: int):
      post = get_object_or_404(Post, id=post_id)
      post.delete()
      return {"success": True}
  ```

- **핵심 개념**:
  - Router를 이용한 API 구조화
  - select_related() 최적화
  - 에러 처리 및 404 응답

---

## 🚀 Module 2: 중간 레벨 기능 구현 (중급자 레벨)
**소요 시간**: 12-15시간 (4주)

### Week 3-4: 인증 및 권한 관리

#### Lesson 3.1: JWT 기반 인증 시스템 구현 (3시간)
- **학습 목표**: JWT를 이용한 인증 시스템 구축
- **실습 내용**:
  ```python
  # authentication.py
  from ninja.security import HttpBearer
  from django.contrib.auth import authenticate
  from django.contrib.auth.models import User
  import jwt
  from datetime import datetime, timedelta
  from django.conf import settings
  
  class JWTAuth(HttpBearer):
      def authenticate(self, request, token):
          try:
              payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
              user = User.objects.get(id=payload['user_id'])
              return user
          except (jwt.InvalidTokenError, User.DoesNotExist):
              return None
  
  # auth API
  @api.post("/auth/login")
  def login(request, credentials: LoginSchema):
      user = authenticate(
          username=credentials.username,
          password=credentials.password
      )
      if user:
          token = jwt.encode({
              'user_id': user.id,
              'exp': datetime.utcnow() + timedelta(days=7)
          }, settings.SECRET_KEY, algorithm='HS256')
          return {"token": token, "user_id": user.id}
      return {"error": "Invalid credentials"}
  
  # 보호된 엔드포인트
  @api.get("/protected", auth=JWTAuth())
  def protected_view(request):
      return {"message": f"Hello {request.auth.username}!"}
  ```

- **핵심 개념**:
  - HttpBearer 클래스 상속
  - JWT 토큰 생성 및 검증
  - 인증이 필요한 API 보호

#### Lesson 3.2: 역할 기반 권한 시스템 (2시간)
- **학습 목표**: 사용자 역할에 따른 API 접근 제어
- **실습 내용**:
  ```python
  from functools import wraps
  from ninja import Router
  from django.http import HttpResponse
  
  def require_permission(permission_name: str):
      def decorator(func):
          @wraps(func)
          def wrapper(request, *args, **kwargs):
              if not request.auth:
                  return HttpResponse("Unauthorized", status=401)
              
              if not request.auth.has_perm(permission_name):
                  return HttpResponse("Forbidden", status=403)
              
              return func(request, *args, **kwargs)
          return wrapper
      return decorator
  
  # 관리자 전용 API
  @api.get("/admin/users", auth=JWTAuth())
  @require_permission('auth.view_user')
  def list_all_users(request):
      users = User.objects.all()
      return [{"id": u.id, "username": u.username} for u in users]
  ```

### Week 5-6: 고급 기능 및 최적화

#### Lesson 4.1: 파일 업로드 및 처리 (2시간)
- **학습 목표**: 이미지 및 파일 업로드 API 구현
- **실습 내용**:
  ```python
  from ninja import File, UploadedFile
  from django.core.files.storage import default_storage
  from PIL import Image
  import uuid
  
  @api.post("/upload/image")
  def upload_image(request, file: UploadedFile = File(...)):
      # 파일 유효성 검사
      if not file.content_type.startswith('image/'):
          return {"error": "이미지 파일만 업로드 가능합니다"}
      
      # 파일 크기 제한 (5MB)
      if file.size > 5 * 1024 * 1024:
          return {"error": "파일 크기는 5MB 이하여야 합니다"}
      
      # 고유한 파일명 생성
      file_extension = file.name.split('.')[-1]
      unique_filename = f"{uuid.uuid4()}.{file_extension}"
      
      # 파일 저장
      file_path = default_storage.save(f"uploads/{unique_filename}", file)
      
      # 썸네일 생성
      with Image.open(file) as img:
          img.thumbnail((300, 300))
          thumbnail_path = f"uploads/thumbnails/{unique_filename}"
          img.save(default_storage.path(thumbnail_path))
      
      return {
          "filename": unique_filename,
          "url": default_storage.url(file_path),
          "thumbnail_url": default_storage.url(thumbnail_path)
      }
  ```

#### Lesson 4.2: 페이지네이션 및 필터링 (2시간)
- **학습 목표**: 대용량 데이터 효율적 처리
- **실습 내용**:
  ```python
  from ninja.pagination import paginate, PageNumberPagination
  from ninja import Query
  from typing import Optional
  
  class PostFilter(Schema):
      category_id: Optional[int] = None
      search: Optional[str] = None
      created_after: Optional[datetime] = None
  
  @api.get("/posts", response=List[PostSchema])
  @paginate(PageNumberPagination, page_size=10)
  def list_posts_paginated(request, filters: PostFilter = Query(...)):
      posts = Post.objects.select_related('category')
      
      # 필터링 적용
      if filters.category_id:
          posts = posts.filter(category_id=filters.category_id)
      
      if filters.search:
          posts = posts.filter(
              Q(title__icontains=filters.search) |
              Q(content__icontains=filters.search)
          )
      
      if filters.created_after:
          posts = posts.filter(created_at__gte=filters.created_after)
      
      return posts.order_by('-created_at')
  ```

#### Lesson 4.3: 캐싱 및 성능 최적화 (3시간)
- **학습 목표**: Redis 캐싱과 데이터베이스 최적화
- **실습 내용**:
  ```python
  from django.core.cache import cache
  from django.db.models import Prefetch
  import json
  
  @api.get("/posts/{post_id}/cached", response=PostSchema)
  def get_cached_post(request, post_id: int):
      # 캐시에서 먼저 확인
      cache_key = f"post_{post_id}"
      cached_post = cache.get(cache_key)
      
      if cached_post:
          return json.loads(cached_post)
      
      # 캐시 미스시 DB에서 조회
      post = get_object_or_404(
          Post.objects.select_related('category'),
          id=post_id
      )
      
      # 캐시에 저장 (1시간)
      cache.set(cache_key, json.dumps(PostSchema.from_orm(post).dict()), 3600)
      
      return post
  
  # N+1 쿼리 문제 해결
  @api.get("/categories/with-posts", response=List[CategoryWithPostsSchema])
  def categories_with_posts(request):
      categories = Category.objects.prefetch_related(
          Prefetch(
              'post_set',
              queryset=Post.objects.select_related('category')
          )
      ).all()
      
      return categories
  ```

---

## 🏆 Module 3: 실전 프로젝트 개발 (고급 레벨)
**소요 시간**: 20-25시간 (8주)

### Week 7-10: 전자상거래 API 프로젝트

#### Project 1: E-Commerce REST API (10시간)
- **프로젝트 목표**: 실무급 전자상거래 백엔드 API 개발
- **주요 기능**:
  ```python
  # 주요 모델 구조
  class Product(models.Model):
      name = models.CharField(max_length=200)
      description = models.TextField()
      price = models.DecimalField(max_digits=10, decimal_places=2)
      stock_quantity = models.PositiveIntegerField()
      category = models.ForeignKey(Category, on_delete=models.CASCADE)
      images = models.ManyToManyField('ProductImage')
      is_active = models.BooleanField(default=True)
  
  class Order(models.Model):
      user = models.ForeignKey(User, on_delete=models.CASCADE)
      status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES)
      total_amount = models.DecimalField(max_digits=10, decimal_places=2)
      created_at = models.DateTimeField(auto_now_add=True)
  
  class OrderItem(models.Model):
      order = models.ForeignKey(Order, on_delete=models.CASCADE)
      product = models.ForeignKey(Product, on_delete=models.CASCADE)
      quantity = models.PositiveIntegerField()
      unit_price = models.DecimalField(max_digits=10, decimal_places=2)
  ```

- **구현할 API 엔드포인트**:
  - 상품 목록/상세 조회 (필터링, 검색, 정렬)
  - 장바구니 관리
  - 주문 생성 및 관리
  - 결제 처리 (가상 결제)
  - 재고 관리
  - 주문 내역 조회

#### 핵심 학습 포인트:
- **트랜잭션 처리**: 주문 생성시 재고 차감
- **동시성 제어**: 재고 부족 방지
- **비즈니스 로직**: 할인, 쿠폰, 적립금
- **외부 API 연동**: 결제 게이트웨이 모킹

### Week 11-12: 소셜 미디어 API 프로젝트

#### Project 2: Social Media Platform API (8시간)
- **프로젝트 목표**: 실시간 소셜 기능이 포함된 API 개발
- **주요 기능**:
  ```python
  # WebSocket을 이용한 실시간 기능
  from channels.generic.websocket import AsyncWebsocketConsumer
  import json
  
  class NotificationConsumer(AsyncWebsocketConsumer):
      async def connect(self):
          self.user = self.scope["user"]
          self.room_group_name = f'notifications_{self.user.id}'
          
          await self.channel_layer.group_add(
              self.room_group_name,
              self.channel_name
          )
          await self.accept()
  
      async def receive(self, text_data):
          data = json.loads(text_data)
          # 실시간 알림 처리
  ```

- **구현할 기능**:
  - 게시물 CRUD (이미지/동영상 업로드)
  - 팔로우/팔로잉 시스템
  - 좋아요/댓글 시스템
  - 실시간 알림
  - 피드 타임라인 생성
  - 해시태그 시스템

### Week 13-14: 고급 기능 및 배포

#### Lesson 5.1: 테스트 작성 및 CI/CD (4시간)
- **학습 목표**: 자동화된 테스트 및 배포 파이프라인 구축
- **실습 내용**:
  ```python
  # tests/test_posts_api.py
  from django.test import TestCase
  from ninja.testing import TestClient
  from django.contrib.auth.models import User
  from myapp.api import api
  
  class PostAPITestCase(TestCase):
      def setUp(self):
          self.client = TestClient(api)
          self.user = User.objects.create_user(
              username='testuser',
              password='testpass123'
          )
  
      def test_create_post_success(self):
          # JWT 토큰 생성
          token = self.get_jwt_token(self.user)
          
          response = self.client.post(
              "/posts",
              json={
                  "title": "테스트 제목",
                  "content": "테스트 내용",
                  "category_id": 1
              },
              headers={"Authorization": f"Bearer {token}"}
          )
          
          self.assertEqual(response.status_code, 201)
          self.assertEqual(response.json()["title"], "테스트 제목")
  
      def test_unauthorized_access(self):
          response = self.client.post("/posts", json={})
          self.assertEqual(response.status_code, 401)
  ```

#### Lesson 5.2: Docker 및 클라우드 배포 (3시간)
- **학습 목표**: Docker 컨테이너화 및 AWS/GCP 배포
- **실습 내용**:
  ```dockerfile
  # Dockerfile
  FROM python:3.11-slim
  
  WORKDIR /app
  
  # 의존성 설치
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  
  # 소스 코드 복사
  COPY . .
  
  # 정적 파일 수집
  RUN python manage.py collectstatic --noinput
  
  EXPOSE 8000
  
  CMD ["gunicorn", "--bind", "0.0.0.0:8000", "myproject.wsgi:application"]
  ```

---

## 📖 추가 학습 모듈 및 심화 과정

### Advanced Module 1: 마이크로서비스 아키텍처 (선택 과정)
**소요 시간**: 8-10시간 (3주)

#### Week 15: 서비스 분리 및 통신
- **API Gateway 패턴**
- **서비스 간 통신 (REST, gRPC)**
- **분산 트랜잭션 처리**
- **서비스 디스커버리**

### Advanced Module 2: 모니터링 및 로깅 (선택 과정)
**소요 시간**: 6-8시간 (2주)

#### Week 16: 운영 환경 관리
- **APM 도구 연동 (New Relic, DataDog)**
- **구조화된 로깅 (JSON 로그)**
- **메트릭 수집 및 알림**
- **성능 모니터링 및 최적화**

---

## 🎯 학습 성과 측정 및 평가

### 1. 프로젝트 기반 평가
- **포트폴리오 완성도**: 3개 프로젝트 완성
- **코드 품질**: PEP 8, 타입 힌트, 문서화
- **테스트 커버리지**: 80% 이상
- **성능 최적화**: 응답 시간, 동시 접속 처리

### 2. 실무 역량 평가
- **API 설계 능력**: RESTful 원칙 준수
- **보안 구현**: 인증/인가, 데이터 검증
- **에러 처리**: 예외 상황 대응
- **문서화**: 자동 생성 문서 활용

### 3. 최종 프로젝트 발표
- **기술 스택 설명**: 선택한 기술의 이유
- **아키텍처 설계**: 시스템 구조 및 확장성
- **문제 해결 과정**: 어려웠던 점과 해결 방법
- **향후 개선 계획**: 추가 기능 및 최적화 방안

---

## 💡 효과적인 학습을 위한 팁

### 1. 실습 중심 학습
```python
# 매 강의마다 실제로 코딩해보기
# 예제 코드를 그대로 따라하지 말고 변형해보기

# 나쁜 예: 단순 복사
@api.get("/users")
def get_users(request):
    return User.objects.all()

# 좋은 예: 자신만의 변형
@api.get("/active-users")
def get_active_users(request, last_login_days: int = 30):
    cutoff_date = timezone.now() - timedelta(days=last_login_days)
    return User.objects.filter(
        is_active=True,
        last_login__gte=cutoff_date
    ).order_by('-last_login')
```

### 2. 에러 중심 학습
- **의도적으로 에러 발생시키기**: 에러 메시지 이해
- **디버깅 습관 기르기**: print 대신 logging 사용
- **스택 오버플로우 활용**: 비슷한 문제 해결 사례 찾기

### 3. 커뮤니티 참여
- **GitHub 프로젝트 공유**: 코드 리뷰 요청
- **기술 블로그 작성**: 학습 내용 정리
- **오픈소스 기여**: Django Ninja 이슈 해결 참여

---

## 🛠️ 강의 제작 시 고려사항

### 1. 기술적 요구사항
- **개발 환경 통일**: Docker 기반 환경 제공
- **코드 버전 관리**: Git 브랜치별 진도 관리
- **자동 채점 시스템**: 과제 자동 검증
- **클라우드 IDE**: 환경 설정 부담 최소화

### 2. 교육적 고려사항
- **점진적 난이도 증가**: 이전 지식 기반 새 개념 도입
- **반복 학습**: 핵심 개념 여러 각도에서 설명
- **즉시 피드백**: 실시간 코드 실행 결과 확인
- **동료 학습**: 팀 프로젝트 및 코드 리뷰

### 3. 지원 시스템
- **Q&A 플랫폼**: 질문-답변 체계
- **멘토링 시스템**: 1:1 또는 소그룹 멘토링
- **스터디 그룹**: 지역별/레벨별 모임 지원
- **취업 연계**: 포트폴리오 기반 기업 연결

---

## 📈 강의 성공을 위한 마케팅 전략

### 1. 차별화 포인트
- **실무 중심**: 포트폴리오로 활용 가능한 프로젝트
- **최신 기술**: 업계 트렌드 반영
- **개인화**: 학습자 레벨에 맞춤 진도 조절
- **커뮤니티**: 지속적인 네트워킹 기회

### 2. 타겟 학습자
- **Django 경험자**: DRF에서 Django Ninja로 전환
- **FastAPI 사용자**: 유사한 개발 경험 활용
- **백엔드 개발자**: API 개발 역량 강화
- **풀스택 개발자**: 백엔드 전문성 향상

### 3. 수강료 전략
- **Early Bird 할인**: 론칭 초기 할인 혜택
- **단계별 구매**: 모듈별 개별 구매 옵션
- **구독 모델**: 월별 구독으로 부담 완화
- **기업 교육**: B2B 대상 맞춤 교육 과정

---

## 🎉 결론

Django Ninja는 현대적이고 효율적인 API 개발을 가능하게 하는 뛰어난 프레임워크입니다. 하지만 체계적인 학습 자료의 부족으로 많은 개발자들이 어려움을 겪고 있습니다. 

이 커리큘럼은 초보자부터 중급자까지 단계별로 학습할 수 있도록 설계되었으며, 실무에서 바로 활용할 수 있는 실전 프로젝트를 포함하고 있습니다. 특히 다음과 같은 특징을 가지고 있습니다:

### ✨ 핵심 특징

1. **실무 중심**: 포트폴리오로 활용 가능한 3개의 완성된 프로젝트
2. **점진적 학습**: 기초부터 고급까지 자연스러운 난이도 증가
3. **최신 기술**: 업계 표준과 베스트 프랙티스 반영
4. **종합적 접근**: 개발뿐만 아니라 테스트, 배포, 모니터링까지

### 🚀 기대 효과

- **취업 역량 강화**: 실무급 API 개발 능력 습득
- **포트폴리오 구축**: 깃허브에 공개 가능한 프로젝트 3개
- **네트워킹**: 동료 개발자들과의 지속적인 교류
- **업계 트렌드**: 최신 백엔드 개발 동향 파악

이 커리큘럼을 통해 Django Ninja 개발자로서 성장하고, 나아가 백엔드 개발 전문가로 발전할 수 있는 탄탄한 기초를 마련하시기 바랍니다. 🎯