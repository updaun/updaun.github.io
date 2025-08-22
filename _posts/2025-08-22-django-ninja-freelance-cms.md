---
layout: post
title: "Django-Ninja로 외주사이트 관리 CMS 구축하기"
date: 2025-08-22 10:00:00 +0900
categories: [Django, CMS, Freelancing]
tags: [django, ninja, cms, freelancing, project-management, rest-api]
excerpt: "Django-Ninja를 활용하여 외주 프로젝트와 클라이언트를 효율적으로 관리할 수 있는 CMS 시스템을 구축하는 방법을 알아봅시다."
---

## 개요

프리랜서나 소규모 개발팀이 늘어나면서 외주 프로젝트를 체계적으로 관리할 수 있는 시스템의 필요성이 증가하고 있습니다. 이번 포스트에서는 **Django-Ninja**를 활용하여 외주사이트 관리를 위한 CMS(Content Management System)를 구축하는 방법을 살펴보겠습니다.

## 시스템 요구사항

### 핵심 기능
- **프로젝트 관리**: 외주 프로젝트 등록, 진행상황 추적
- **클라이언트 관리**: 고객 정보, 연락처, 계약 이력
- **견적 관리**: 견적서 생성, 승인 프로세스
- **일정 관리**: 프로젝트 마일스톤, 데드라인 추적
- **파일 관리**: 프로젝트 관련 문서, 이미지 업로드
- **결제 관리**: 청구서 발행, 결제 상태 추적
- **대시보드**: 프로젝트 현황 시각화

## 프로젝트 설정

### 1. 패키지 설치

```bash
pip install django django-ninja pillow python-decouple django-extensions
pip install djangorestframework-simplejwt python-multipart
pip install celery redis  # 백그라운드 작업용 (선택사항)
```

### 2. Django 프로젝트 생성

```bash
django-admin startproject freelance_cms
cd freelance_cms
python manage.py startapp core
python manage.py startapp projects
python manage.py startapp clients
python manage.py startapp billing
```

### 3. Django-Ninja 설정

```python
# freelance_cms/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from ninja import NinjaAPI
from ninja.security import django_auth

from projects.api import router as projects_router
from clients.api import router as clients_router
from billing.api import router as billing_router
from core.api import router as core_router

api = NinjaAPI(
    title="Freelance CMS API",
    version="1.0.0",
    description="외주사이트 관리를 위한 CMS API"
)

# API 라우터 등록
api.add_router("projects/", projects_router, tags=["Projects"])
api.add_router("clients/", clients_router, tags=["Clients"])
api.add_router("billing/", billing_router, tags=["Billing"])
api.add_router("", core_router, tags=["Core"])

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

## 데이터 모델 설계

### 1. 클라이언트 모델

```python
# clients/models.py
from django.db import models
from django.contrib.auth.models import User
import uuid

class Client(models.Model):
    """클라이언트 모델"""
    CLIENT_TYPES = [
        ('individual', '개인'),
        ('company', '회사'),
        ('startup', '스타트업'),
        ('agency', '에이전시'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=200, verbose_name="클라이언트명")
    client_type = models.CharField(max_length=20, choices=CLIENT_TYPES, default='individual')
    
    # 연락처 정보
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    
    # 주소 정보
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='대한민국')
    
    # 비즈니스 정보
    company_registration = models.CharField(max_length=50, blank=True, verbose_name="사업자등록번호")
    industry = models.CharField(max_length=100, blank=True, verbose_name="업종")
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # 관계 설정
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, verbose_name="메모")
    
    def __str__(self):
        return self.name
    
    @property
    def total_projects(self):
        return self.projects.count()
    
    @property
    def active_projects(self):
        return self.projects.filter(status__in=['in_progress', 'planning']).count()

class ClientContact(models.Model):
    """클라이언트 담당자"""
    client = models.ForeignKey(Client, related_name='contacts', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    is_primary = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.name} ({self.client.name})"
```

### 2. 프로젝트 모델

```python
# projects/models.py
from django.db import models
from django.contrib.auth.models import User
from clients.models import Client
import uuid
from decimal import Decimal

class ProjectCategory(models.Model):
    """프로젝트 카테고리"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff')  # 헥스 컬러
    
    def __str__(self):
        return self.name

class Project(models.Model):
    """프로젝트 모델"""
    STATUS_CHOICES = [
        ('inquiry', '문의'),
        ('quote_sent', '견적 발송'),
        ('negotiation', '협상 중'),
        ('contract_signed', '계약 체결'),
        ('planning', '기획'),
        ('in_progress', '진행 중'),
        ('testing', '테스트'),
        ('completed', '완료'),
        ('on_hold', '보류'),
        ('cancelled', '취소'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', '낮음'),
        ('medium', '보통'),
        ('high', '높음'),
        ('urgent', '긴급'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = models.CharField(max_length=300, verbose_name="프로젝트명")
    client = models.ForeignKey(Client, related_name='projects', on_delete=models.CASCADE)
    category = models.ForeignKey(ProjectCategory, on_delete=models.SET_NULL, null=True)
    
    # 프로젝트 정보
    description = models.TextField(verbose_name="프로젝트 설명")
    requirements = models.TextField(blank=True, verbose_name="요구사항")
    deliverables = models.TextField(blank=True, verbose_name="결과물")
    
    # 상태 및 우선순위
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inquiry')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # 일정
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    estimated_hours = models.PositiveIntegerField(default=0, verbose_name="예상 작업시간")
    
    # 금액
    budget_min = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="최소 예산")
    budget_max = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="최대 예산")
    final_price = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, verbose_name="최종 금액")
    
    # 담당자
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="담당자")
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, related_name='created_projects', on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"{self.title} ({self.client.name})"
    
    @property
    def progress_percentage(self):
        """프로젝트 진행률 계산"""
        if self.status == 'completed':
            return 100
        elif self.status in ['inquiry', 'quote_sent']:
            return 0
        elif self.status in ['negotiation', 'contract_signed']:
            return 10
        elif self.status == 'planning':
            return 20
        elif self.status == 'in_progress':
            completed_tasks = self.tasks.filter(is_completed=True).count()
            total_tasks = self.tasks.count()
            if total_tasks > 0:
                return int((completed_tasks / total_tasks) * 80) + 20  # 20% 기본 + 80% 작업 완료율
            return 30
        elif self.status == 'testing':
            return 90
        return 0

class ProjectTask(models.Model):
    """프로젝트 작업"""
    project = models.ForeignKey(Project, related_name='tasks', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # 일정
    due_date = models.DateField(null=True, blank=True)
    estimated_hours = models.PositiveIntegerField(default=0)
    actual_hours = models.PositiveIntegerField(default=0)
    
    # 상태
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # 순서
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"{self.project.title} - {self.title}"

class ProjectFile(models.Model):
    """프로젝트 파일"""
    FILE_TYPES = [
        ('document', '문서'),
        ('image', '이미지'),
        ('design', '디자인'),
        ('code', '코드'),
        ('other', '기타'),
    ]
    
    project = models.ForeignKey(Project, related_name='files', on_delete=models.CASCADE)
    file = models.FileField(upload_to='projects/%Y/%m/')
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, default='document')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
```

### 3. 견적/청구 모델

```python
# billing/models.py
from django.db import models
from django.contrib.auth.models import User
from projects.models import Project
from clients.models import Client
import uuid
from decimal import Decimal

class Quote(models.Model):
    """견적서"""
    STATUS_CHOICES = [
        ('draft', '임시저장'),
        ('sent', '발송됨'),
        ('viewed', '열람됨'),
        ('accepted', '승인됨'),
        ('rejected', '거절됨'),
        ('expired', '만료됨'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    quote_number = models.CharField(max_length=50, unique=True)
    
    # 관련 객체
    project = models.ForeignKey(Project, related_name='quotes', on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    
    # 견적 정보
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    
    # 금액
    subtotal = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)  # 세율 (%)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    
    # 상태 및 일정
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    valid_until = models.DateField(verbose_name="유효기간")
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # 발송/승인 정보
    sent_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        # 세금 및 총액 계산
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total_amount = self.subtotal + self.tax_amount
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"견적서 {self.quote_number} - {self.client.name}"

class QuoteItem(models.Model):
    """견적 항목"""
    quote = models.ForeignKey(Quote, related_name='items', on_delete=models.CASCADE)
    description = models.CharField(max_length=300)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=0)
    
    order = models.PositiveIntegerField(default=0)
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        
        # 견적서 합계 업데이트
        self.quote.subtotal = sum(item.total_price for item in self.quote.items.all())
        self.quote.save()
    
    class Meta:
        ordering = ['order']

class Invoice(models.Model):
    """청구서"""
    STATUS_CHOICES = [
        ('draft', '임시저장'),
        ('sent', '발송됨'),
        ('paid', '결제완료'),
        ('overdue', '연체'),
        ('cancelled', '취소됨'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    invoice_number = models.CharField(max_length=50, unique=True)
    
    # 관련 객체
    project = models.ForeignKey(Project, related_name='invoices', on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    quote = models.ForeignKey(Quote, on_delete=models.SET_NULL, null=True, blank=True)
    
    # 청구 정보
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    
    # 금액
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    
    # 일정
    issue_date = models.DateField()
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    
    # 상태
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    @property
    def remaining_amount(self):
        return self.amount - self.paid_amount
    
    @property
    def is_fully_paid(self):
        return self.paid_amount >= self.amount
    
    def __str__(self):
        return f"청구서 {self.invoice_number} - {self.client.name}"
```

## API 구현

### 1. 프로젝트 API

```python
# projects/api.py
from ninja import Router, Schema, Form, File
from ninja.files import UploadedFile
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from typing import List, Optional
from datetime import datetime, date

from .models import Project, ProjectCategory, ProjectTask, ProjectFile
from clients.models import Client

router = Router()

# 스키마 정의
class ProjectCategorySchema(Schema):
    id: int
    name: str
    description: str
    color: str

class ProjectSchema(Schema):
    id: str
    title: str
    client_id: str
    client_name: str
    category: Optional[ProjectCategorySchema]
    description: str
    status: str
    priority: str
    start_date: Optional[date]
    end_date: Optional[date]
    budget_min: int
    budget_max: int
    final_price: Optional[int]
    progress_percentage: int
    created_at: datetime
    
    @staticmethod
    def resolve_client_name(obj):
        return obj.client.name

class ProjectCreateSchema(Schema):
    title: str
    client_id: str
    category_id: Optional[int]
    description: str
    requirements: Optional[str] = ""
    deliverables: Optional[str] = ""
    priority: str = "medium"
    start_date: Optional[date]
    end_date: Optional[date]
    budget_min: int = 0
    budget_max: int = 0
    estimated_hours: int = 0

class ProjectUpdateSchema(Schema):
    title: Optional[str]
    status: Optional[str]
    priority: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    final_price: Optional[int]
    description: Optional[str]
    requirements: Optional[str]
    deliverables: Optional[str]

class TaskSchema(Schema):
    id: int
    title: str
    description: str
    due_date: Optional[date]
    estimated_hours: int
    actual_hours: int
    is_completed: bool
    order: int

class TaskCreateSchema(Schema):
    title: str
    description: Optional[str] = ""
    due_date: Optional[date]
    estimated_hours: int = 0
    order: int = 0

@router.get("/", response=List[ProjectSchema])
def list_projects(request, status: Optional[str] = None, client_id: Optional[str] = None):
    """프로젝트 목록 조회"""
    projects = Project.objects.select_related('client', 'category').all()
    
    if status:
        projects = projects.filter(status=status)
    if client_id:
        projects = projects.filter(client_id=client_id)
    
    return projects.order_by('-created_at')

@router.post("/", response=ProjectSchema)
def create_project(request, payload: ProjectCreateSchema):
    """새 프로젝트 생성"""
    client = get_object_or_404(Client, id=payload.client_id)
    
    project_data = payload.dict()
    project_data.pop('client_id')
    project_data.pop('category_id', None)
    
    project = Project.objects.create(
        client=client,
        category_id=payload.category_id,
        created_by=request.user if request.user.is_authenticated else None,
        **project_data
    )
    
    return project

@router.get("/{project_id}", response=ProjectSchema)
def get_project(request, project_id: str):
    """프로젝트 상세 조회"""
    return get_object_or_404(Project, id=project_id)

@router.put("/{project_id}", response=ProjectSchema)
def update_project(request, project_id: str, payload: ProjectUpdateSchema):
    """프로젝트 수정"""
    project = get_object_or_404(Project, id=project_id)
    
    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(project, attr, value)
    
    project.save()
    return project

@router.delete("/{project_id}")
def delete_project(request, project_id: str):
    """프로젝트 삭제"""
    project = get_object_or_404(Project, id=project_id)
    project.delete()
    return {"message": "프로젝트가 삭제되었습니다."}

# 작업 관리
@router.get("/{project_id}/tasks", response=List[TaskSchema])
def list_project_tasks(request, project_id: str):
    """프로젝트 작업 목록"""
    project = get_object_or_404(Project, id=project_id)
    return project.tasks.all()

@router.post("/{project_id}/tasks", response=TaskSchema)
def create_task(request, project_id: str, payload: TaskCreateSchema):
    """새 작업 생성"""
    project = get_object_or_404(Project, id=project_id)
    
    task = ProjectTask.objects.create(
        project=project,
        **payload.dict()
    )
    return task

@router.put("/tasks/{task_id}", response=TaskSchema)
def update_task(request, task_id: int, payload: TaskCreateSchema):
    """작업 수정"""
    task = get_object_or_404(ProjectTask, id=task_id)
    
    for attr, value in payload.dict().items():
        setattr(task, attr, value)
    
    if payload.dict().get('is_completed') and not task.completed_at:
        task.completed_at = datetime.now()
    
    task.save()
    return task

# 파일 업로드
@router.post("/{project_id}/files")
def upload_file(request, project_id: str, file: UploadedFile = File(...), file_type: str = Form('document'), description: str = Form("")):
    """프로젝트 파일 업로드"""
    project = get_object_or_404(Project, id=project_id)
    
    project_file = ProjectFile.objects.create(
        project=project,
        file=file,
        file_type=file_type,
        name=file.name,
        description=description,
        uploaded_by=request.user if request.user.is_authenticated else None
    )
    
    return {
        "id": project_file.id,
        "name": project_file.name,
        "file_url": project_file.file.url,
        "file_type": project_file.file_type
    }

@router.get("/{project_id}/files")
def list_project_files(request, project_id: str):
    """프로젝트 파일 목록"""
    project = get_object_or_404(Project, id=project_id)
    
    files = []
    for file in project.files.all():
        files.append({
            "id": file.id,
            "name": file.name,
            "file_url": file.file.url,
            "file_type": file.file_type,
            "description": file.description,
            "uploaded_at": file.uploaded_at
        })
    
    return files

# 프로젝트 통계
@router.get("/{project_id}/stats")
def get_project_stats(request, project_id: str):
    """프로젝트 통계"""
    project = get_object_or_404(Project, id=project_id)
    
    tasks = project.tasks.all()
    completed_tasks = tasks.filter(is_completed=True)
    
    stats = {
        "total_tasks": tasks.count(),
        "completed_tasks": completed_tasks.count(),
        "remaining_tasks": tasks.filter(is_completed=False).count(),
        "progress_percentage": project.progress_percentage,
        "estimated_hours": sum(task.estimated_hours for task in tasks),
        "actual_hours": sum(task.actual_hours for task in tasks),
        "total_files": project.files.count(),
        "quotes_count": project.quotes.count(),
        "invoices_count": project.invoices.count(),
    }
    
    return stats
```

### 2. 클라이언트 API

```python
# clients/api.py
from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from typing import List, Optional
from datetime import datetime

from .models import Client, ClientContact

router = Router()

class ClientContactSchema(Schema):
    id: int
    name: str
    position: str
    email: str
    phone: str
    is_primary: bool

class ClientSchema(Schema):
    id: str
    name: str
    client_type: str
    email: str
    phone: str
    website: str
    industry: str
    is_active: bool
    total_projects: int
    active_projects: int
    contacts: List[ClientContactSchema]
    created_at: datetime

class ClientCreateSchema(Schema):
    name: str
    client_type: str = "individual"
    email: str
    phone: Optional[str] = ""
    website: Optional[str] = ""
    address: Optional[str] = ""
    city: Optional[str] = ""
    industry: Optional[str] = ""
    company_registration: Optional[str] = ""
    notes: Optional[str] = ""

@router.get("/", response=List[ClientSchema])
def list_clients(request, is_active: bool = True):
    """클라이언트 목록 조회"""
    clients = Client.objects.filter(is_active=is_active).prefetch_related('contacts')
    return clients.order_by('-created_at')

@router.post("/", response=ClientSchema)
def create_client(request, payload: ClientCreateSchema):
    """새 클라이언트 생성"""
    client = Client.objects.create(
        **payload.dict(),
        created_by=request.user if request.user.is_authenticated else None
    )
    return client

@router.get("/{client_id}", response=ClientSchema)
def get_client(request, client_id: str):
    """클라이언트 상세 조회"""
    return get_object_or_404(Client, id=client_id)

@router.put("/{client_id}", response=ClientSchema)
def update_client(request, client_id: str, payload: ClientCreateSchema):
    """클라이언트 수정"""
    client = get_object_or_404(Client, id=client_id)
    
    for attr, value in payload.dict().items():
        setattr(client, attr, value)
    
    client.save()
    return client

@router.delete("/{client_id}")
def delete_client(request, client_id: str):
    """클라이언트 삭제 (비활성화)"""
    client = get_object_or_404(Client, id=client_id)
    client.is_active = False
    client.save()
    return {"message": "클라이언트가 비활성화되었습니다."}

# 담당자 관리
@router.post("/{client_id}/contacts", response=ClientContactSchema)
def add_contact(request, client_id: str, payload: ClientContactSchema):
    """클라이언트 담당자 추가"""
    client = get_object_or_404(Client, id=client_id)
    
    # 기본 담당자 설정 시 다른 담당자들의 기본 설정 해제
    if payload.is_primary:
        client.contacts.update(is_primary=False)
    
    contact = ClientContact.objects.create(
        client=client,
        **payload.dict()
    )
    return contact

@router.get("/{client_id}/projects")
def get_client_projects(request, client_id: str):
    """클라이언트 프로젝트 목록"""
    client = get_object_or_404(Client, id=client_id)
    projects = client.projects.all().order_by('-created_at')
    
    return [
        {
            "id": str(project.id),
            "title": project.title,
            "status": project.status,
            "progress_percentage": project.progress_percentage,
            "start_date": project.start_date,
            "end_date": project.end_date,
            "final_price": project.final_price,
        }
        for project in projects
    ]
```

### 3. 견적/청구 API

```python
# billing/api.py
from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

from .models import Quote, QuoteItem, Invoice
from projects.models import Project
from clients.models import Client

router = Router()

class QuoteItemSchema(Schema):
    id: Optional[int]
    description: str
    quantity: int
    unit_price: int
    total_price: int
    order: int

class QuoteSchema(Schema):
    id: str
    quote_number: str
    title: str
    client_name: str
    project_title: str
    status: str
    subtotal: int
    tax_rate: float
    tax_amount: int
    total_amount: int
    valid_until: date
    items: List[QuoteItemSchema]
    created_at: datetime
    
    @staticmethod
    def resolve_client_name(obj):
        return obj.client.name
    
    @staticmethod
    def resolve_project_title(obj):
        return obj.project.title

class QuoteCreateSchema(Schema):
    project_id: str
    title: str
    description: Optional[str] = ""
    valid_until: date
    tax_rate: float = 10.0
    items: List[QuoteItemSchema]

@router.get("/quotes/", response=List[QuoteSchema])
def list_quotes(request, status: Optional[str] = None, client_id: Optional[str] = None):
    """견적서 목록 조회"""
    quotes = Quote.objects.select_related('client', 'project').prefetch_related('items')
    
    if status:
        quotes = quotes.filter(status=status)
    if client_id:
        quotes = quotes.filter(client_id=client_id)
    
    return quotes.order_by('-created_at')

@router.post("/quotes/", response=QuoteSchema)
def create_quote(request, payload: QuoteCreateSchema):
    """견적서 생성"""
    project = get_object_or_404(Project, id=payload.project_id)
    
    # 견적서 번호 생성 (예: Q-2025-001)
    import datetime
    year = datetime.datetime.now().year
    last_quote = Quote.objects.filter(quote_number__startswith=f'Q-{year}').order_by('-created_at').first()
    if last_quote:
        last_num = int(last_quote.quote_number.split('-')[2])
        new_num = last_num + 1
    else:
        new_num = 1
    
    quote_number = f'Q-{year}-{new_num:03d}'
    
    quote = Quote.objects.create(
        quote_number=quote_number,
        project=project,
        client=project.client,
        title=payload.title,
        description=payload.description,
        valid_until=payload.valid_until,
        tax_rate=payload.tax_rate,
        created_by=request.user if request.user.is_authenticated else None
    )
    
    # 견적 항목 생성
    for item_data in payload.items:
        QuoteItem.objects.create(
            quote=quote,
            description=item_data.description,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            order=item_data.order
        )
    
    return quote

@router.get("/quotes/{quote_id}", response=QuoteSchema)
def get_quote(request, quote_id: str):
    """견적서 상세 조회"""
    return get_object_or_404(Quote, id=quote_id)

@router.put("/quotes/{quote_id}/status")
def update_quote_status(request, quote_id: str, status: str):
    """견적서 상태 변경"""
    quote = get_object_or_404(Quote, id=quote_id)
    quote.status = status
    
    if status == 'sent':
        quote.sent_at = datetime.now()
    elif status in ['accepted', 'rejected']:
        quote.responded_at = datetime.now()
    
    quote.save()
    return {"message": f"견적서 상태가 {status}로 변경되었습니다."}

# 청구서 관리
class InvoiceSchema(Schema):
    id: str
    invoice_number: str
    title: str
    client_name: str
    project_title: str
    amount: int
    paid_amount: int
    remaining_amount: int
    issue_date: date
    due_date: date
    paid_date: Optional[date]
    status: str
    created_at: datetime
    
    @staticmethod
    def resolve_client_name(obj):
        return obj.client.name
    
    @staticmethod
    def resolve_project_title(obj):
        return obj.project.title

class InvoiceCreateSchema(Schema):
    project_id: str
    title: str
    description: Optional[str] = ""
    amount: int
    issue_date: date
    due_date: date
    quote_id: Optional[str]

@router.get("/invoices/", response=List[InvoiceSchema])
def list_invoices(request, status: Optional[str] = None, client_id: Optional[str] = None):
    """청구서 목록 조회"""
    invoices = Invoice.objects.select_related('client', 'project')
    
    if status:
        invoices = invoices.filter(status=status)
    if client_id:
        invoices = invoices.filter(client_id=client_id)
    
    return invoices.order_by('-created_at')

@router.post("/invoices/", response=InvoiceSchema)
def create_invoice(request, payload: InvoiceCreateSchema):
    """청구서 생성"""
    project = get_object_or_404(Project, id=payload.project_id)
    quote = None
    if payload.quote_id:
        quote = get_object_or_404(Quote, id=payload.quote_id)
    
    # 청구서 번호 생성
    import datetime
    year = datetime.datetime.now().year
    last_invoice = Invoice.objects.filter(invoice_number__startswith=f'I-{year}').order_by('-created_at').first()
    if last_invoice:
        last_num = int(last_invoice.invoice_number.split('-')[2])
        new_num = last_num + 1
    else:
        new_num = 1
    
    invoice_number = f'I-{year}-{new_num:03d}'
    
    invoice = Invoice.objects.create(
        invoice_number=invoice_number,
        project=project,
        client=project.client,
        quote=quote,
        title=payload.title,
        description=payload.description,
        amount=payload.amount,
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        created_by=request.user if request.user.is_authenticated else None
    )
    
    return invoice

@router.put("/invoices/{invoice_id}/payment")
def record_payment(request, invoice_id: str, paid_amount: int, paid_date: date):
    """결제 기록"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    invoice.paid_amount = paid_amount
    invoice.paid_date = paid_date
    
    if invoice.is_fully_paid:
        invoice.status = 'paid'
    
    invoice.save()
    return {"message": "결제가 기록되었습니다.", "remaining_amount": invoice.remaining_amount}
```

## 대시보드 API

```python
# core/api.py
from ninja import Router, Schema
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import timedelta, datetime
from typing import Dict, Any

from projects.models import Project
from clients.models import Client
from billing.models import Quote, Invoice

router = Router()

class DashboardStats(Schema):
    projects: Dict[str, Any]
    clients: Dict[str, Any]
    revenue: Dict[str, Any]
    recent_activity: list

@router.get("/dashboard", response=DashboardStats)
def get_dashboard_stats(request):
    """대시보드 통계"""
    
    # 날짜 범위 설정
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    
    # 프로젝트 통계
    projects_stats = {
        "total": Project.objects.count(),
        "active": Project.objects.filter(status__in=['in_progress', 'planning']).count(),
        "completed_this_month": Project.objects.filter(
            status='completed',
            updated_at__gte=thirty_days_ago
        ).count(),
        "by_status": dict(
            Project.objects.values('status').annotate(count=Count('id')).values_list('status', 'count')
        ),
        "avg_progress": Project.objects.filter(
            status__in=['in_progress', 'planning']
        ).aggregate(avg_progress=Avg('progress_percentage'))['avg_progress'] or 0
    }
    
    # 클라이언트 통계
    clients_stats = {
        "total": Client.objects.filter(is_active=True).count(),
        "new_this_month": Client.objects.filter(
            created_at__gte=thirty_days_ago
        ).count(),
        "with_active_projects": Client.objects.filter(
            projects__status__in=['in_progress', 'planning']
        ).distinct().count()
    }
    
    # 수익 통계
    revenue_stats = {
        "total_quotes": Quote.objects.aggregate(total=Sum('total_amount'))['total'] or 0,
        "accepted_quotes": Quote.objects.filter(status='accepted').aggregate(
            total=Sum('total_amount')
        )['total'] or 0,
        "total_invoiced": Invoice.objects.aggregate(total=Sum('amount'))['total'] or 0,
        "total_paid": Invoice.objects.aggregate(total=Sum('paid_amount'))['total'] or 0,
        "pending_payments": Invoice.objects.filter(
            status__in=['sent']
        ).aggregate(total=Sum('amount'))['total'] or 0,
        "this_month_revenue": Invoice.objects.filter(
            paid_date__gte=thirty_days_ago
        ).aggregate(total=Sum('paid_amount'))['total'] or 0
    }
    
    # 최근 활동
    recent_projects = Project.objects.order_by('-updated_at')[:5]
    recent_quotes = Quote.objects.order_by('-created_at')[:3]
    recent_invoices = Invoice.objects.order_by('-created_at')[:3]
    
    recent_activity = []
    
    for project in recent_projects:
        recent_activity.append({
            "type": "project",
            "title": f"프로젝트 업데이트: {project.title}",
            "date": project.updated_at,
            "status": project.status
        })
    
    for quote in recent_quotes:
        recent_activity.append({
            "type": "quote",
            "title": f"견적서 생성: {quote.title}",
            "date": quote.created_at,
            "status": quote.status
        })
    
    for invoice in recent_invoices:
        recent_activity.append({
            "type": "invoice",
            "title": f"청구서 발행: {invoice.title}",
            "date": invoice.created_at,
            "status": invoice.status
        })
    
    # 날짜순 정렬
    recent_activity.sort(key=lambda x: x['date'], reverse=True)
    recent_activity = recent_activity[:10]  # 최근 10개만
    
    return DashboardStats(
        projects=projects_stats,
        clients=clients_stats,
        revenue=revenue_stats,
        recent_activity=recent_activity
    )

@router.get("/stats/monthly")
def get_monthly_stats(request):
    """월별 통계"""
    # 최근 12개월 데이터
    months_data = []
    
    for i in range(12):
        month_start = (now - timedelta(days=30 * i)).replace(day=1)
        next_month = (month_start + timedelta(days=32)).replace(day=1)
        
        month_projects = Project.objects.filter(
            created_at__gte=month_start,
            created_at__lt=next_month
        ).count()
        
        month_revenue = Invoice.objects.filter(
            paid_date__gte=month_start,
            paid_date__lt=next_month
        ).aggregate(total=Sum('paid_amount'))['total'] or 0
        
        months_data.append({
            "month": month_start.strftime("%Y-%m"),
            "projects": month_projects,
            "revenue": month_revenue
        })
    
    return {"monthly_data": list(reversed(months_data))}
```

## 프론트엔드 연동 예제

### React 컴포넌트 예제

```javascript
// components/Dashboard.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Dashboard = () => {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchDashboardStats();
    }, []);

    const fetchDashboardStats = async () => {
        try {
            const response = await axios.get('/api/dashboard');
            setStats(response.data);
        } catch (error) {
            console.error('Dashboard stats fetch error:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div>Loading...</div>;
    if (!stats) return <div>데이터를 불러올 수 없습니다.</div>;

    return (
        <div className="dashboard">
            <h1>외주사이트 관리 대시보드</h1>
            
            {/* 통계 카드 */}
            <div className="stats-grid">
                <div className="stat-card">
                    <h3>전체 프로젝트</h3>
                    <p className="stat-number">{stats.projects.total}</p>
                    <p className="stat-change">
                        활성: {stats.projects.active}개
                    </p>
                </div>
                
                <div className="stat-card">
                    <h3>총 클라이언트</h3>
                    <p className="stat-number">{stats.clients.total}</p>
                    <p className="stat-change">
                        이번 달 신규: {stats.clients.new_this_month}개
                    </p>
                </div>
                
                <div className="stat-card">
                    <h3>총 수익</h3>
                    <p className="stat-number">
                        {stats.revenue.total_paid.toLocaleString()}원
                    </p>
                    <p className="stat-change">
                        이번 달: {stats.revenue.this_month_revenue.toLocaleString()}원
                    </p>
                </div>
                
                <div className="stat-card">
                    <h3>미결제 금액</h3>
                    <p className="stat-number">
                        {stats.revenue.pending_payments.toLocaleString()}원
                    </p>
                </div>
            </div>
            
            {/* 프로젝트 상태별 차트 */}
            <div className="chart-section">
                <h2>프로젝트 현황</h2>
                <div className="status-chart">
                    {Object.entries(stats.projects.by_status).map(([status, count]) => (
                        <div key={status} className="status-item">
                            <span className="status-label">{status}</span>
                            <span className="status-count">{count}</span>
                        </div>
                    ))}
                </div>
            </div>
            
            {/* 최근 활동 */}
            <div className="recent-activity">
                <h2>최근 활동</h2>
                <ul>
                    {stats.recent_activity.map((activity, index) => (
                        <li key={index} className={`activity-item ${activity.type}`}>
                            <span className="activity-title">{activity.title}</span>
                            <span className="activity-date">
                                {new Date(activity.date).toLocaleDateString()}
                            </span>
                            <span className={`activity-status ${activity.status}`}>
                                {activity.status}
                            </span>
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    );
};

export default Dashboard;
```

## 배포 및 운영

### 1. Docker 설정

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "freelance_cms.wsgi:application"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - media_volume:/app/media
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://user:password@db:5432/freelance_cms
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=freelance_cms
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:alpine

volumes:
  postgres_data:
  media_volume:
```

### 2. 환경 설정

```python
# settings.py
import os
from decouple import config

# 기본 설정
DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('SECRET_KEY', default='your-secret-key')

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# 데이터베이스
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='freelance_cms'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# 파일 업로드 설정
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 이메일 설정
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = True

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/freelance_cms.log',
            'maxBytes': 1024*1024*10,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 추가 기능 아이디어

### 1. 알림 시스템
- 프로젝트 마감일 알림
- 견적서 만료 알림
- 결제 지연 알림

### 2. 시간 추적
- 작업 시간 기록
- 시간당 요금 계산
- 생산성 분석

### 3. 보고서 생성
- 월별/분기별 수익 보고서
- 클라이언트별 수익 분석
- 프로젝트 성과 분석

### 4. 모바일 앱
- React Native로 모바일 버전
- 푸시 알림
- 오프라인 지원

## 결론

Django-Ninja를 활용한 외주사이트 관리 CMS는 다음과 같은 장점을 제공합니다:

### 🚀 **주요 장점**
1. **현대적인 API**: FastAPI와 유사한 직관적인 API 개발
2. **자동 문서화**: OpenAPI/Swagger 자동 생성
3. **타입 안전성**: Pydantic 스키마로 데이터 검증
4. **확장성**: Django 생태계의 모든 기능 활용 가능
5. **유연성**: 다양한 프론트엔드와 연동 가능

### 💼 **비즈니스 가치**
- 프로젝트 관리 효율성 증대
- 클라이언트 관계 체계적 관리
- 수익 및 비용 투명한 추적
- 업무 자동화를 통한 시간 절약

이러한 CMS 시스템을 통해 프리랜서나 소규모 개발팀이 더욱 전문적이고 체계적으로 외주 업무를 관리할 수 있을 것입니다. Django-Ninja의 현대적인 개발 방식과 Django의 안정성을 결합하여 확장 가능하고 유지보수가 쉬운 시스템을 구축할 수 있습니다! 🎯

---

*이 포스트가 도움이 되셨다면 GitHub에서 ⭐️를 눌러주세요!*
