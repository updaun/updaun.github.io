---
layout: post
title: "Django Ninja로 체험단 플랫폼 구축하기: 완전 가이드"
date: 2025-08-19 10:00:00 +0900
categories: [Django, API, Web Development]
tags: [Django, Django-Ninja, FastAPI, REST API, Backend, Database, ORM, Authentication, Project Management]
---

체험단 플랫폼은 현대 마케팅에서 중요한 역할을 하는 서비스입니다. 이 글에서는 Django Ninja를 사용해 체험단 사이트를 구축하는 전 과정을 다루겠습니다. Project(체험공고)와 ProjectUser(참여자) 모델을 중심으로 실용적인 API 서비스를 만들어보겠습니다.

## 🏗️ 프로젝트 개요

### 주요 기능
- **체험공고 관리**: 기업이 체험단 모집 공고를 등록, 수정, 삭제
- **참여자 관리**: 사용자가 체험단에 신청하고 진행 상태 추적
- **인증 시스템**: JWT 기반 사용자 인증
- **관리자 기능**: 체험단 승인/거절 및 전체 현황 관리

### 기술 스택
- **Backend**: Django + Django Ninja
- **Database**: PostgreSQL (개발 시 SQLite)
- **Authentication**: Django JWT
- **API Documentation**: Automatic Swagger/OpenAPI

## 🚀 프로젝트 설정

### 1. 가상환경 및 의존성 설치

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 필수 패키지 설치
pip install django django-ninja python-decouple django-cors-headers pillow
pip install psycopg2-binary  # PostgreSQL 사용 시
```

### 2. Django 프로젝트 초기화

```bash
django-admin startproject experience_platform
cd experience_platform
python manage.py startapp core
python manage.py startapp projects
python manage.py startapp users
```

### 3. 설정 파일 구성

**settings.py**
```python
import os
from decouple import config

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'core',
    'projects',
    'users',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'experience_platform.urls'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='experience_platform'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='password'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# CORS 설정
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

## 📊 모델 설계

### Project 모델 (체험공고)

```python
# projects/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from PIL import Image
import os

class ProjectCategory(models.TextChoices):
    FOOD = 'food', '식품/음료'
    BEAUTY = 'beauty', '뷰티/코스메틱'
    FASHION = 'fashion', '패션/의류'
    TECH = 'tech', '디지털/가전'
    LIFESTYLE = 'lifestyle', '생활용품'
    BOOK = 'book', '도서/문화'
    TRAVEL = 'travel', '여행/레저'
    OTHER = 'other', '기타'

class ProjectStatus(models.TextChoices):
    DRAFT = 'draft', '작성중'
    RECRUITING = 'recruiting', '모집중'
    SELECTION = 'selection', '선발중'
    ONGOING = 'ongoing', '진행중'
    REVIEW = 'review', '리뷰작성중'
    COMPLETED = 'completed', '완료'
    CANCELLED = 'cancelled', '취소'

class Project(models.Model):
    # 기본 정보
    title = models.CharField(max_length=200, verbose_name="체험단 제목")
    description = models.TextField(verbose_name="상세 설명")
    category = models.CharField(
        max_length=20,
        choices=ProjectCategory.choices,
        default=ProjectCategory.OTHER,
        verbose_name="카테고리"
    )
    
    # 이미지
    main_image = models.ImageField(
        upload_to='projects/main/',
        null=True,
        blank=True,
        verbose_name="메인 이미지"
    )
    detail_images = models.JSONField(
        default=list,
        blank=True,
        verbose_name="상세 이미지 URL 목록"
    )
    
    # 모집 정보
    recruit_count = models.PositiveIntegerField(verbose_name="모집 인원")
    current_count = models.PositiveIntegerField(default=0, verbose_name="현재 신청자 수")
    
    # 일정
    recruit_start_date = models.DateTimeField(verbose_name="모집 시작일")
    recruit_end_date = models.DateTimeField(verbose_name="모집 마감일")
    experience_start_date = models.DateTimeField(verbose_name="체험 시작일")
    experience_end_date = models.DateTimeField(verbose_name="체험 종료일")
    review_deadline = models.DateTimeField(verbose_name="리뷰 작성 마감일")
    
    # 조건
    required_conditions = models.JSONField(
        default=list,
        blank=True,
        help_text="예: ['성별', '연령대', '거주지역', '관심분야']",
        verbose_name="참여 조건"
    )
    
    # 제공 혜택
    benefits = models.JSONField(
        default=list,
        blank=True,
        help_text="예: ['상품 무료 제공', '배송비 무료', '추가 할인 혜택']",
        verbose_name="제공 혜택"
    )
    
    # 상태 관리
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.DRAFT,
        verbose_name="진행 상태"
    )
    
    # 관계
    company = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_projects',
        verbose_name="기업 계정"
    )
    participants = models.ManyToManyField(
        User,
        through='ProjectUser',
        related_name='participating_projects',
        verbose_name="참여자들"
    )
    
    # 메타 정보
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    # SEO 및 검색
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name="태그"
    )
    view_count = models.PositiveIntegerField(default=0, verbose_name="조회수")
    
    class Meta:
        verbose_name = "체험 프로젝트"
        verbose_name_plural = "체험 프로젝트들"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'category']),
            models.Index(fields=['recruit_end_date']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    @property
    def is_recruiting(self):
        """현재 모집 중인지 확인"""
        now = timezone.now()
        return (self.status == ProjectStatus.RECRUITING and 
                self.recruit_start_date <= now <= self.recruit_end_date)
    
    @property
    def is_full(self):
        """모집 인원이 가득 찼는지 확인"""
        return self.current_count >= self.recruit_count
    
    @property
    def remaining_days(self):
        """모집 마감까지 남은 일수"""
        if self.recruit_end_date:
            remaining = self.recruit_end_date - timezone.now()
            return max(0, remaining.days)
        return 0
    
    def save(self, *args, **kwargs):
        # 이미지 최적화
        if self.main_image:
            self._optimize_image(self.main_image)
        super().save(*args, **kwargs)
    
    def _optimize_image(self, image_field):
        """이미지 크기 최적화"""
        if image_field and hasattr(image_field, 'path'):
            img = Image.open(image_field.path)
            if img.width > 1200 or img.height > 800:
                img.thumbnail((1200, 800), Image.Resampling.LANCZOS)
                img.save(image_field.path, optimize=True, quality=85)
```

### ProjectUser 모델 (참여자)

```python
# projects/models.py (계속)

class ApplicationStatus(models.TextChoices):
    PENDING = 'pending', '신청완료'
    REVIEWING = 'reviewing', '검토중'
    ACCEPTED = 'accepted', '선발완료'
    REJECTED = 'rejected', '선발탈락'
    PARTICIPATING = 'participating', '체험중'
    REVIEW_REQUIRED = 'review_required', '리뷰작성필요'
    COMPLETED = 'completed', '체험완료'
    CANCELLED = 'cancelled', '신청취소'

class ProjectUser(models.Model):
    # 관계
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name="프로젝트"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name="사용자"
    )
    
    # 신청 정보
    application_message = models.TextField(
        max_length=1000,
        verbose_name="신청 메시지",
        help_text="자신을 어필할 수 있는 내용을 작성해주세요"
    )
    additional_info = models.JSONField(
        default=dict,
        blank=True,
        help_text="추가 정보 (연령, 성별, 거주지 등)",
        verbose_name="추가 정보"
    )
    
    # 상태 관리
    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
        verbose_name="신청 상태"
    )
    
    # 날짜 정보
    applied_at = models.DateTimeField(auto_now_add=True, verbose_name="신청일")
    status_updated_at = models.DateTimeField(auto_now=True, verbose_name="상태 업데이트일")
    selected_at = models.DateTimeField(null=True, blank=True, verbose_name="선발일")
    
    # 관리자 메모
    admin_note = models.TextField(
        blank=True,
        verbose_name="관리자 메모",
        help_text="선발/탈락 사유 등"
    )
    
    # 평가 점수 (선발 시 참고용)
    score = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="평가 점수",
        help_text="1-100점 사이"
    )
    
    # 체험 후 정보
    review_submitted = models.BooleanField(default=False, verbose_name="리뷰 제출 완료")
    review_url = models.URLField(
        blank=True,
        verbose_name="리뷰 URL",
        help_text="블로그, SNS 등 리뷰 링크"
    )
    
    class Meta:
        verbose_name = "프로젝트 참여자"
        verbose_name_plural = "프로젝트 참여자들"
        unique_together = ['project', 'user']  # 한 프로젝트에 한 번만 신청 가능
        ordering = ['-applied_at']
        indexes = [
            models.Index(fields=['status', 'applied_at']),
            models.Index(fields=['project', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.project.title} ({self.get_status_display()})"
    
    @property
    def can_cancel(self):
        """신청 취소 가능 여부"""
        return self.status in [ApplicationStatus.PENDING, ApplicationStatus.REVIEWING]
    
    @property
    def is_selected(self):
        """선발 여부"""
        return self.status in [
            ApplicationStatus.ACCEPTED,
            ApplicationStatus.PARTICIPATING,
            ApplicationStatus.REVIEW_REQUIRED,
            ApplicationStatus.COMPLETED
        ]
    
    def save(self, *args, **kwargs):
        # 상태 변경 시 선발일 자동 설정
        if self.status == ApplicationStatus.ACCEPTED and not self.selected_at:
            self.selected_at = timezone.now()
        
        # 선발 시 프로젝트 참여자 수 증가
        if self.pk is None and self.status == ApplicationStatus.ACCEPTED:
            self.project.current_count = models.F('current_count') + 1
            self.project.save()
        
        super().save(*args, **kwargs)

# 추가 모델들
class ProjectImage(models.Model):
    """프로젝트 상세 이미지"""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='projects/details/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']

class ProjectReview(models.Model):
    """체험단 리뷰"""
    project_user = models.OneToOneField(
        ProjectUser,
        on_delete=models.CASCADE,
        related_name='review'
    )
    rating = models.PositiveIntegerField(
        choices=[(i, f"{i}점") for i in range(1, 6)],
        verbose_name="별점"
    )
    content = models.TextField(verbose_name="리뷰 내용")
    images = models.JSONField(default=list, blank=True, verbose_name="리뷰 이미지")
    external_url = models.URLField(blank=True, verbose_name="외부 리뷰 링크")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "체험 리뷰"
        verbose_name_plural = "체험 리뷰들"
```

## 🔧 Django Ninja API 구현

### 1. 스키마 정의

```python
# projects/schemas.py
from ninja import Schema, ModelSchema
from datetime import datetime
from typing import List, Optional, Dict, Any
from .models import Project, ProjectUser, ProjectCategory, ProjectStatus, ApplicationStatus

# 공통 스키마
class MessageSchema(Schema):
    message: str
    success: bool = True

class PaginationSchema(Schema):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[Any]

# Project 관련 스키마
class ProjectCreateSchema(Schema):
    title: str
    description: str
    category: ProjectCategory
    recruit_count: int
    recruit_start_date: datetime
    recruit_end_date: datetime
    experience_start_date: datetime
    experience_end_date: datetime
    review_deadline: datetime
    required_conditions: List[str] = []
    benefits: List[str] = []
    tags: List[str] = []

class ProjectUpdateSchema(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ProjectCategory] = None
    recruit_count: Optional[int] = None
    recruit_start_date: Optional[datetime] = None
    recruit_end_date: Optional[datetime] = None
    experience_start_date: Optional[datetime] = None
    experience_end_date: Optional[datetime] = None
    review_deadline: Optional[datetime] = None
    required_conditions: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    status: Optional[ProjectStatus] = None

class ProjectListSchema(ModelSchema):
    remaining_days: int
    is_recruiting: bool
    is_full: bool
    company_name: str
    
    class Config:
        model = Project
        model_fields = [
            'id', 'title', 'category', 'recruit_count', 'current_count',
            'recruit_end_date', 'status', 'main_image', 'tags', 'view_count'
        ]
    
    @staticmethod
    def resolve_company_name(obj):
        return obj.company.username
    
    @staticmethod
    def resolve_remaining_days(obj):
        return obj.remaining_days
    
    @staticmethod
    def resolve_is_recruiting(obj):
        return obj.is_recruiting
    
    @staticmethod
    def resolve_is_full(obj):
        return obj.is_full

class ProjectDetailSchema(ModelSchema):
    remaining_days: int
    is_recruiting: bool
    is_full: bool
    company_name: str
    application_count: int
    
    class Config:
        model = Project
        model_fields = '__all__'
    
    @staticmethod
    def resolve_company_name(obj):
        return obj.company.username
    
    @staticmethod
    def resolve_remaining_days(obj):
        return obj.remaining_days
    
    @staticmethod
    def resolve_is_recruiting(obj):
        return obj.is_recruiting
    
    @staticmethod
    def resolve_is_full(obj):
        return obj.is_full
    
    @staticmethod
    def resolve_application_count(obj):
        return obj.applications.count()

# ProjectUser 관련 스키마
class ProjectApplicationSchema(Schema):
    application_message: str
    additional_info: Dict[str, Any] = {}

class ProjectUserSchema(ModelSchema):
    user_name: str
    project_title: str
    
    class Config:
        model = ProjectUser
        model_fields = [
            'id', 'application_message', 'status', 'applied_at',
            'status_updated_at', 'selected_at', 'score'
        ]
    
    @staticmethod
    def resolve_user_name(obj):
        return obj.user.username
    
    @staticmethod
    def resolve_project_title(obj):
        return obj.project.title

class ApplicationUpdateSchema(Schema):
    status: ApplicationStatus
    admin_note: Optional[str] = None
    score: Optional[int] = None

# 필터링 스키마
class ProjectFilterSchema(Schema):
    category: Optional[ProjectCategory] = None
    status: Optional[ProjectStatus] = None
    search: Optional[str] = None
    ordering: Optional[str] = None
    page: int = 1
    page_size: int = 20
```

### 2. API 엔드포인트 구현

```python
# projects/api.py
from ninja import Router, Query, File
from ninja.files import UploadedFile
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from typing import List, Optional
from .models import Project, ProjectUser, ProjectCategory, ProjectStatus
from .schemas import (
    ProjectCreateSchema, ProjectUpdateSchema, ProjectListSchema,
    ProjectDetailSchema, ProjectApplicationSchema, ProjectUserSchema,
    ApplicationUpdateSchema, MessageSchema, ProjectFilterSchema
)

router = Router()

# 프로젝트 목록 조회 (필터링, 검색, 정렬 지원)
@router.get("/projects", response=List[ProjectListSchema])
def list_projects(request, filters: ProjectFilterSchema = Query(...)):
    queryset = Project.objects.select_related('company').prefetch_related('applications')
    
    # 필터링
    if filters.category:
        queryset = queryset.filter(category=filters.category)
    
    if filters.status:
        queryset = queryset.filter(status=filters.status)
    
    if filters.search:
        queryset = queryset.filter(
            Q(title__icontains=filters.search) |
            Q(description__icontains=filters.search) |
            Q(tags__icontains=filters.search)
        )
    
    # 정렬
    ordering_map = {
        'latest': '-created_at',
        'oldest': 'created_at',
        'deadline': 'recruit_end_date',
        'popular': '-view_count',
        'participants': '-current_count',
    }
    ordering = ordering_map.get(filters.ordering, '-created_at')
    queryset = queryset.order_by(ordering)
    
    # 페이지네이션
    paginator = Paginator(queryset, filters.page_size)
    page_obj = paginator.get_page(filters.page)
    
    return page_obj.object_list

# 프로젝트 상세 조회
@router.get("/projects/{int:project_id}", response=ProjectDetailSchema)
def get_project(request, project_id: int):
    project = get_object_or_404(
        Project.objects.select_related('company')
                      .prefetch_related('applications', 'images'),
        id=project_id
    )
    
    # 조회수 증가
    Project.objects.filter(id=project_id).update(view_count=models.F('view_count') + 1)
    
    return project

# 프로젝트 생성 (기업 계정만)
@router.post("/projects", response=ProjectDetailSchema)
def create_project(request, payload: ProjectCreateSchema):
    if not request.user.is_authenticated:
        return {"error": "로그인이 필요합니다"}, 401
    
    # 기업 계정 확인 로직 (예: 별도 프로필 모델 확인)
    if not hasattr(request.user, 'company_profile'):
        return {"error": "기업 계정만 프로젝트를 생성할 수 있습니다"}, 403
    
    project = Project.objects.create(
        company=request.user,
        **payload.dict()
    )
    return project

# 프로젝트 수정
@router.patch("/projects/{int:project_id}", response=ProjectDetailSchema)
def update_project(request, project_id: int, payload: ProjectUpdateSchema):
    project = get_object_or_404(Project, id=project_id, company=request.user)
    
    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(project, attr, value)
    
    project.save()
    return project

# 프로젝트 삭제
@router.delete("/projects/{int:project_id}", response=MessageSchema)
def delete_project(request, project_id: int):
    project = get_object_or_404(Project, id=project_id, company=request.user)
    project.delete()
    return {"message": "프로젝트가 삭제되었습니다"}

# 프로젝트 이미지 업로드
@router.post("/projects/{int:project_id}/images", response=MessageSchema)
def upload_project_image(request, project_id: int, file: UploadedFile = File(...)):
    project = get_object_or_404(Project, id=project_id, company=request.user)
    
    # 메인 이미지 업로드
    project.main_image = file
    project.save()
    
    return {"message": "이미지가 업로드되었습니다"}

# 체험단 신청
@router.post("/projects/{int:project_id}/apply", response=MessageSchema)
def apply_project(request, project_id: int, payload: ProjectApplicationSchema):
    if not request.user.is_authenticated:
        return {"error": "로그인이 필요합니다"}, 401
    
    project = get_object_or_404(Project, id=project_id)
    
    # 이미 신청했는지 확인
    if ProjectUser.objects.filter(project=project, user=request.user).exists():
        return {"error": "이미 신청한 프로젝트입니다"}, 400
    
    # 모집 기간 확인
    if not project.is_recruiting:
        return {"error": "모집 기간이 아닙니다"}, 400
    
    # 모집 인원 확인
    if project.is_full:
        return {"error": "모집 인원이 마감되었습니다"}, 400
    
    ProjectUser.objects.create(
        project=project,
        user=request.user,
        **payload.dict()
    )
    
    return {"message": "체험단 신청이 완료되었습니다"}

# 신청 취소
@router.delete("/projects/{int:project_id}/apply", response=MessageSchema)
def cancel_application(request, project_id: int):
    application = get_object_or_404(
        ProjectUser,
        project_id=project_id,
        user=request.user
    )
    
    if not application.can_cancel:
        return {"error": "취소할 수 없는 상태입니다"}, 400
    
    application.delete()
    return {"message": "신청이 취소되었습니다"}

# 내 신청 목록
@router.get("/my/applications", response=List[ProjectUserSchema])
def my_applications(request):
    if not request.user.is_authenticated:
        return {"error": "로그인이 필요합니다"}, 401
    
    applications = ProjectUser.objects.filter(user=request.user)\
                                     .select_related('project')\
                                     .order_by('-applied_at')
    return applications

# 프로젝트 신청자 목록 (기업용)
@router.get("/projects/{int:project_id}/applications", response=List[ProjectUserSchema])
def project_applications(request, project_id: int):
    project = get_object_or_404(Project, id=project_id, company=request.user)
    
    applications = ProjectUser.objects.filter(project=project)\
                                     .select_related('user')\
                                     .order_by('-applied_at')
    return applications

# 신청자 상태 변경 (기업용)
@router.patch("/applications/{int:application_id}", response=ProjectUserSchema)
def update_application(request, application_id: int, payload: ApplicationUpdateSchema):
    application = get_object_or_404(
        ProjectUser.objects.select_related('project'),
        id=application_id,
        project__company=request.user
    )
    
    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(application, attr, value)
    
    application.save()
    return application

# 프로젝트 통계 (기업용)
@router.get("/projects/{int:project_id}/stats")
def project_stats(request, project_id: int):
    project = get_object_or_404(Project, id=project_id, company=request.user)
    
    stats = ProjectUser.objects.filter(project=project).aggregate(
        total_applications=Count('id'),
        pending_count=Count('id', filter=Q(status='pending')),
        accepted_count=Count('id', filter=Q(status='accepted')),
        rejected_count=Count('id', filter=Q(status='rejected')),
    )
    
    return {
        "project_id": project_id,
        "project_title": project.title,
        "view_count": project.view_count,
        **stats
    }
```

### 3. 메인 API 라우터 설정

```python
# experience_platform/api.py
from ninja import NinjaAPI
from projects.api import router as projects_router

api = NinjaAPI(
    title="체험단 플랫폼 API",
    description="체험단 모집 및 참여자 관리 API",
    version="1.0.0",
    docs_url="/docs/",
)

# 프로젝트 관련 API
api.add_router("/api/", projects_router, tags=["Projects"])

# 인증 관련 API (추가 구현)
# api.add_router("/api/auth/", auth_router, tags=["Authentication"])
```

```python
# experience_platform/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', api.urls),  # API 엔드포인트
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

## 🔐 인증 시스템 구현

### JWT 인증 추가

```bash
pip install djangorestframework-simplejwt
```

```python
# users/authentication.py
from ninja.security import HttpBearer
from django.contrib.auth.models import User
from django.http import HttpRequest
import jwt
from django.conf import settings

class AuthBearer(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user = User.objects.get(id=payload['user_id'])
            return user
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
            return None

auth = AuthBearer()
```

```python
# users/api.py
from ninja import Router
from ninja.security import django_auth
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
import jwt
from datetime import datetime, timedelta
from django.conf import settings

router = Router()

@router.post("/login")
def login_user(request, username: str, password: str):
    user = authenticate(username=username, password=password)
    if user:
        payload = {
            'user_id': user.id,
            'username': user.username,
            'exp': datetime.utcnow() + timedelta(days=7)
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        return {
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }
        }
    return {"error": "Invalid credentials"}, 401

@router.post("/register")
def register_user(request, username: str, email: str, password: str):
    if User.objects.filter(username=username).exists():
        return {"error": "Username already exists"}, 400
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )
    
    return {
        "message": "User created successfully",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }
    }
```

## 🚀 배포 및 운영

### 1. Docker 설정

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
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
      - DB_NAME=experience_platform
      - DB_USER=postgres
      - DB_PASSWORD=password
      - DB_HOST=db
      - DB_PORT=5432
    depends_on:
      - db
    volumes:
      - ./media:/app/media

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=experience_platform
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### 2. 환경별 설정

```python
# settings/production.py
from .base import *
import os

DEBUG = False
ALLOWED_HOSTS = [os.getenv('DOMAIN', 'localhost')]

# 데이터베이스
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# 캐시 설정
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://redis:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# 파일 저장 (AWS S3)
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
```

### 3. 모니터링 설정

```python
# monitoring/middleware.py
import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('api_monitoring')

class APIMonitoringMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.start_time = time.time()
        
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            logger.info(f"{request.method} {request.path} - {response.status_code} - {duration:.3f}s")
        return response
```

## 📊 성능 최적화

### 1. 데이터베이스 최적화

```python
# projects/management/commands/optimize_db.py
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = '데이터베이스 최적화'
    
    def handle(self, *args, **options):
        # 인덱스 생성
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS 
                idx_project_status_recruit_date 
                ON projects_project(status, recruit_end_date);
            """)
            
            cursor.execute("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                idx_projectuser_compound
                ON projects_projectuser(project_id, status, applied_at);
            """)
        
        self.stdout.write(self.style.SUCCESS('데이터베이스 최적화 완료'))
```

### 2. 캐싱 전략

```python
# projects/views.py (캐싱 예시)
from django.core.cache import cache
from django.views.decorators.cache import cache_page
import hashlib

def get_projects_cache_key(filters):
    """프로젝트 목록 캐시 키 생성"""
    key_data = f"{filters.category}-{filters.status}-{filters.search}-{filters.ordering}"
    return f"projects_list_{hashlib.md5(key_data.encode()).hexdigest()}"

@router.get("/projects", response=List[ProjectListSchema])
def list_projects(request, filters: ProjectFilterSchema = Query(...)):
    # 캐시 키 생성
    cache_key = get_projects_cache_key(filters)
    
    # 캐시에서 조회
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # DB에서 조회
    queryset = Project.objects.select_related('company').prefetch_related('applications')
    # ... (이전 로직과 동일)
    
    # 캐시에 저장 (5분)
    cache.set(cache_key, result, 300)
    return result
```

## 🧪 테스트 코드

```python
# tests/test_projects.py
from django.test import TestCase
from django.contrib.auth.models import User
from ninja.testing import TestClient
from projects.models import Project, ProjectUser
from projects.api import router
from datetime import datetime, timedelta

class ProjectAPITestCase(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.company_user = User.objects.create_user(
            username='company',
            email='company@test.com',
            password='testpass123'
        )
        self.normal_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123'
        )
        
        self.project = Project.objects.create(
            title='테스트 체험단',
            description='테스트 설명',
            company=self.company_user,
            recruit_count=10,
            recruit_start_date=datetime.now(),
            recruit_end_date=datetime.now() + timedelta(days=7),
            experience_start_date=datetime.now() + timedelta(days=10),
            experience_end_date=datetime.now() + timedelta(days=20),
            review_deadline=datetime.now() + timedelta(days=30),
        )
    
    def test_list_projects(self):
        response = self.client.get('/projects')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
    
    def test_get_project_detail(self):
        response = self.client.get(f'/projects/{self.project.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['title'], '테스트 체험단')
    
    def test_apply_project(self):
        # 로그인 필요
        response = self.client.post(f'/projects/{self.project.id}/apply', {
            'application_message': '신청합니다!'
        })
        self.assertEqual(response.status_code, 401)
        
        # 로그인 후 신청
        self.client.force_authenticate(self.normal_user)
        response = self.client.post(f'/projects/{self.project.id}/apply', {
            'application_message': '신청합니다!'
        })
        self.assertEqual(response.status_code, 200)
        
        # 중복 신청 방지
        response = self.client.post(f'/projects/{self.project.id}/apply', {
            'application_message': '또 신청합니다!'
        })
        self.assertEqual(response.status_code, 400)
```

## 🎯 결론

Django Ninja를 사용한 체험단 플랫폼 구축을 통해 다음과 같은 이점을 얻을 수 있습니다:

### 주요 성과
1. **빠른 개발**: Django의 강력한 ORM과 Ninja의 직관적인 API 구문
2. **자동 문서화**: Swagger/OpenAPI 자동 생성으로 API 문서 관리 불필요
3. **타입 안정성**: Pydantic 스키마를 통한 데이터 검증
4. **확장성**: 마이크로서비스 아키텍처로 확장 가능

### 추가 개선 방안
- **알림 시스템**: Django Channels를 이용한 실시간 알림
- **결제 연동**: 토스페이먼츠, 카카오페이 등 결제 시스템
- **소셜 로그인**: OAuth2를 이용한 소셜 미디어 연동
- **관리자 대시보드**: 통계 및 분석 기능 강화

이러한 체험단 플랫폼은 브랜드 마케팅과 소비자 경험을 연결하는 중요한 역할을 하며, Django Ninja의 현대적인 API 개발 방식으로 효율적으로 구축할 수 있습니다.
