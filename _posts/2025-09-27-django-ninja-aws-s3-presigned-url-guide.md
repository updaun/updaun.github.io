---
layout: post
title: "Django Ninja와 AWS S3 Presigned URL로 안전한 이미지 업로드 시스템 구축하기"
date: 2025-09-27 14:00:00 +0900
categories: [Web Development, Backend, AWS]
tags: [django, django-ninja, aws s3, presigned url, image upload, cloud storage, security]
description: "Django Ninja와 AWS S3 Presigned URL을 활용하여 안전하고 효율적인 이미지 업로드 및 관리 시스템을 구축하는 방법을 알아봅니다. 직접 업로드, 보안, 성능 최적화까지 실무에서 바로 사용할 수 있는 완전한 가이드입니다."
author: "updaun"
image: "/assets/img/posts/2025-09-27-django-ninja-aws-s3-presigned-url-guide.webp"
---

## 개요

웹 애플리케이션에서 이미지 업로드는 핵심 기능 중 하나입니다. 하지만 전통적인 서버 업로드 방식은 서버 리소스 사용량이 많고, 확장성에 한계가 있습니다. AWS S3 Presigned URL을 활용하면 클라이언트가 직접 S3에 업로드하면서도 보안을 유지할 수 있습니다.

## Presigned URL의 장점

### 1. 서버 리소스 절약
- **직접 업로드**: 클라이언트가 S3로 직접 업로드
- **대역폭 절약**: 서버를 거치지 않아 네트워크 비용 절감
- **동시 업로드**: 여러 파일을 동시에 처리 가능

### 2. 보안성
- **임시 권한**: 제한된 시간 동안만 유효
- **특정 버킷/경로**: 지정된 위치에만 업로드 가능
- **파일 크기 제한**: 업로드 정책으로 크기 제한

### 3. 성능 향상
- **CDN 활용**: CloudFront와 연동으로 전 세계 빠른 업로드
- **병렬 처리**: 다중 파트 업로드 지원
- **지연 시간 감소**: 클라이언트와 가장 가까운 엣지 로케이션 활용

## 프로젝트 설정

### 1. 의존성 설치

```bash
# 가상환경 생성 및 활성화
python -m venv s3_upload_env
source s3_upload_env/bin/activate

# 필수 패키지 설치
pip install django django-ninja boto3 python-decouple pillow python-magic

# requirements.txt 생성
pip freeze > requirements.txt
```

### 2. AWS 설정

```python
# settings.py
import os
from decouple import config

# AWS 설정
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='ap-northeast-2')
AWS_S3_CUSTOM_DOMAIN = config('AWS_S3_CUSTOM_DOMAIN', default=None)

# S3 설정
AWS_DEFAULT_ACL = None
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

# 미디어 파일 설정
if AWS_S3_CUSTOM_DOMAIN:
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
else:
    MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/"

# Presigned URL 설정
PRESIGNED_URL_EXPIRATION = config('PRESIGNED_URL_EXPIRATION', default=3600, cast=int)  # 1시간
MAX_UPLOAD_SIZE = config('MAX_UPLOAD_SIZE', default=10*1024*1024, cast=int)  # 10MB
```

### 3. 환경변수 설정

```bash
# .env
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=ap-northeast-2
AWS_S3_CUSTOM_DOMAIN=your-cloudfront-domain.com
PRESIGNED_URL_EXPIRATION=3600
MAX_UPLOAD_SIZE=10485760
```

## 데이터 모델 설계

### 1. 이미지 관리 모델

```python
# images/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
import uuid
import os

class ImageCategory(models.Model):
    """이미지 카테고리"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    max_file_size = models.PositiveIntegerField(default=10*1024*1024)  # 10MB
    allowed_extensions = models.JSONField(default=list)  # ['jpg', 'jpeg', 'png', 'webp']
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class ImageUpload(models.Model):
    """이미지 업로드 관리"""
    
    class UploadStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        UPLOADING = 'uploading', 'Uploading'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        DELETED = 'deleted', 'Deleted'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='image_uploads')
    category = models.ForeignKey(ImageCategory, on_delete=models.CASCADE, related_name='images')
    
    # 파일 정보
    original_filename = models.CharField(max_length=255)
    file_key = models.CharField(max_length=500, unique=True)  # S3 객체 키
    file_size = models.PositiveIntegerField(null=True, blank=True)
    content_type = models.CharField(max_length=100)
    
    # 이미지 메타데이터
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    
    # 업로드 상태
    status = models.CharField(max_length=20, choices=UploadStatus.choices, default=UploadStatus.PENDING)
    upload_started_at = models.DateTimeField(null=True, blank=True)
    upload_completed_at = models.DateTimeField(null=True, blank=True)
    
    # 메타데이터
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    alt_text = models.CharField(max_length=200, blank=True)
    tags = models.JSONField(default=list, blank=True)
    
    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.original_filename} ({self.status})"
    
    @property
    def url(self):
        """이미지 URL 반환"""
        from django.conf import settings
        return f"{settings.MEDIA_URL}{self.file_key}"
    
    @property
    def file_extension(self):
        """파일 확장자 반환"""
        return os.path.splitext(self.original_filename)[1].lower()

class ImageVariant(models.Model):
    """이미지 변형 버전 (썸네일, 리사이즈 등)"""
    
    class VariantType(models.TextChoices):
        THUMBNAIL = 'thumbnail', 'Thumbnail'
        SMALL = 'small', 'Small'
        MEDIUM = 'medium', 'Medium'
        LARGE = 'large', 'Large'
        WEBP = 'webp', 'WebP'
    
    original_image = models.ForeignKey(ImageUpload, on_delete=models.CASCADE, related_name='variants')
    variant_type = models.CharField(max_length=20, choices=VariantType.choices)
    file_key = models.CharField(max_length=500)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    file_size = models.PositiveIntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['original_image', 'variant_type']
    
    @property
    def url(self):
        from django.conf import settings
        return f"{settings.MEDIA_URL}{self.file_key}"
```

## S3 서비스 클래스 구현

### 1. S3 클라이언트 및 Presigned URL 생성

```python
# images/services.py
import boto3
import magic
from botocore.exceptions import ClientError, NoCredentialsError
from django.conf import settings
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import os

class S3ImageService:
    """AWS S3 이미지 관리 서비스"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        self.expiration = settings.PRESIGNED_URL_EXPIRATION
    
    def generate_file_key(self, user_id: int, category: str, filename: str) -> str:
        """S3 객체 키 생성"""
        file_extension = os.path.splitext(filename)[1].lower()
        unique_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y/%m/%d')
        
        return f"images/{category}/{user_id}/{timestamp}/{unique_id}{file_extension}"
    
    def get_presigned_upload_url(
        self, 
        file_key: str, 
        content_type: str,
        file_size: int,
        max_file_size: int = None
    ) -> Dict[str, Any]:
        """업로드용 Presigned URL 생성"""
        
        max_size = max_file_size or settings.MAX_UPLOAD_SIZE
        
        # 업로드 정책 설정
        conditions = [
            {'bucket': self.bucket_name},
            {'key': file_key},
            {'Content-Type': content_type},
            ['content-length-range', 1, max_size],
        ]
        
        # ACL 설정 (선택사항)
        fields = {
            'Content-Type': content_type,
        }
        
        try:
            response = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=file_key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=self.expiration
            )
            
            return {
                'success': True,
                'data': {
                    'url': response['url'],
                    'fields': response['fields'],
                    'file_key': file_key,
                    'expires_at': datetime.now() + timedelta(seconds=self.expiration)
                }
            }
            
        except (ClientError, NoCredentialsError) as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_presigned_download_url(self, file_key: str, expires_in: int = 3600) -> str:
        """다운로드용 Presigned URL 생성"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {e}")
    
    def check_file_exists(self, file_key: str) -> bool:
        """S3에서 파일 존재 여부 확인"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except ClientError:
            return False
    
    def get_file_metadata(self, file_key: str) -> Optional[Dict[str, Any]]:
        """S3 파일 메타데이터 조회"""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)
            return {
                'size': response.get('ContentLength'),
                'content_type': response.get('ContentType'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag'),
                'metadata': response.get('Metadata', {})
            }
        except ClientError:
            return None
    
    def delete_file(self, file_key: str) -> bool:
        """S3에서 파일 삭제"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except ClientError as e:
            print(f"Failed to delete file {file_key}: {e}")
            return False
    
    def copy_file(self, source_key: str, destination_key: str) -> bool:
        """S3 내에서 파일 복사"""
        try:
            copy_source = {'Bucket': self.bucket_name, 'Key': source_key}
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=destination_key
            )
            return True
        except ClientError as e:
            print(f"Failed to copy file: {e}")
            return False
    
    def list_files(self, prefix: str, max_keys: int = 1000) -> List[Dict[str, Any]]:
        """특정 prefix로 시작하는 파일 목록 조회"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag']
                })
            
            return files
        except ClientError as e:
            print(f"Failed to list files: {e}")
            return []

class ImageProcessor:
    """이미지 처리 서비스"""
    
    ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
    ALLOWED_MIME_TYPES = [
        'image/jpeg', 'image/png', 'image/webp', 'image/gif'
    ]
    
    @staticmethod
    def validate_image_file(filename: str, content_type: str) -> Dict[str, Any]:
        """이미지 파일 유효성 검사"""
        errors = []
        
        # 확장자 검사
        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension not in ImageProcessor.ALLOWED_EXTENSIONS:
            errors.append(f"Unsupported file extension: {file_extension}")
        
        # MIME 타입 검사
        if content_type not in ImageProcessor.ALLOWED_MIME_TYPES:
            errors.append(f"Unsupported content type: {content_type}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'extension': file_extension,
            'content_type': content_type
        }
    
    @staticmethod
    def get_image_dimensions_from_url(url: str) -> tuple:
        """URL에서 이미지 크기 정보 추출"""
        try:
            import requests
            from PIL import Image
            from io import BytesIO
            
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            image = Image.open(BytesIO(response.content))
            return image.size  # (width, height)
            
        except Exception as e:
            print(f"Failed to get image dimensions: {e}")
            return (0, 0)
```

## Pydantic 스키마 정의

### 1. 요청/응답 스키마

```python
# images/schemas.py
from ninja import Schema, Field
from pydantic import validator, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

# 카테고리 스키마
class ImageCategorySchema(Schema):
    id: int
    name: str
    description: str
    max_file_size: int
    allowed_extensions: List[str]
    is_active: bool

# 업로드 요청 스키마
class PresignedUrlRequestSchema(Schema):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str
    file_size: int = Field(gt=0)
    category_id: int
    
    @validator('filename')
    def validate_filename(cls, v):
        if not v or v.strip() == '':
            raise ValueError('Filename cannot be empty')
        
        # 금지된 문자 확인
        forbidden_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        if any(char in v for char in forbidden_chars):
            raise ValueError('Filename contains forbidden characters')
        
        return v.strip()
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = [
            'image/jpeg', 'image/png', 'image/webp', 'image/gif'
        ]
        if v not in allowed_types:
            raise ValueError(f'Content type must be one of: {", ".join(allowed_types)}')
        return v

class PresignedUrlResponseSchema(Schema):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# 이미지 업로드 완료 스키마
class ImageUploadCompleteSchema(Schema):
    image_id: uuid.UUID
    title: Optional[str] = None
    description: Optional[str] = None
    alt_text: Optional[str] = None
    tags: Optional[List[str]] = None

# 이미지 정보 스키마
class ImageUploadSchema(Schema):
    id: uuid.UUID
    original_filename: str
    file_key: str
    file_size: Optional[int]
    content_type: str
    width: Optional[int]
    height: Optional[int]
    status: str
    title: str
    description: str
    alt_text: str
    tags: List[str]
    url: str
    created_at: datetime
    category: ImageCategorySchema

class ImageUploadListSchema(Schema):
    id: uuid.UUID
    original_filename: str
    status: str
    title: str
    url: str
    created_at: datetime
    category_name: str = Field(alias="category.name")

# 이미지 변형 스키마
class ImageVariantSchema(Schema):
    variant_type: str
    url: str
    width: int
    height: int
    file_size: int

# 이미지 업데이트 스키마
class ImageUpdateSchema(Schema):
    title: Optional[str] = None
    description: Optional[str] = None
    alt_text: Optional[str] = None
    tags: Optional[List[str]] = None

# 검색 및 필터 스키마
class ImageFilterSchema(Schema):
    category_id: Optional[int] = None
    status: Optional[str] = None
    search: Optional[str] = None
    tags: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

# 통계 스키마
class ImageStatsSchema(Schema):
    total_images: int
    total_size: int
    by_category: List[Dict[str, Any]]
    by_status: List[Dict[str, Any]]
    recent_uploads: List[ImageUploadListSchema]
```

## API 엔드포인트 구현

### 1. 메인 API 라우터

```python
# images/api.py
from ninja import Router, Query, File, UploadedFile
from ninja.pagination import paginate, PageNumberPagination
from ninja.responses import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count, Sum
from typing import List, Optional
from datetime import datetime

from .models import ImageCategory, ImageUpload, ImageVariant
from .services import S3ImageService, ImageProcessor
from .schemas import (
    ImageCategorySchema, PresignedUrlRequestSchema, PresignedUrlResponseSchema,
    ImageUploadCompleteSchema, ImageUploadSchema, ImageUploadListSchema,
    ImageVariantSchema, ImageUpdateSchema, ImageFilterSchema, ImageStatsSchema
)

router = Router()
s3_service = S3ImageService()
image_processor = ImageProcessor()

# 카테고리 관리
@router.get("/categories", response=List[ImageCategorySchema])
def list_categories(request):
    """이미지 카테고리 목록 조회"""
    return ImageCategory.objects.filter(is_active=True)

# Presigned URL 생성
@router.post("/presigned-url", response=PresignedUrlResponseSchema)
@login_required
def get_presigned_upload_url(request, payload: PresignedUrlRequestSchema):
    """업로드용 Presigned URL 생성"""
    
    # 카테고리 확인
    category = get_object_or_404(ImageCategory, id=payload.category_id, is_active=True)
    
    # 파일 유효성 검사
    validation = image_processor.validate_image_file(
        payload.filename, 
        payload.content_type
    )
    
    if not validation['valid']:
        return PresignedUrlResponseSchema(
            success=False,
            error="; ".join(validation['errors'])
        )
    
    # 파일 크기 검사
    if payload.file_size > category.max_file_size:
        return PresignedUrlResponseSchema(
            success=False,
            error=f"File size exceeds limit ({category.max_file_size} bytes)"
        )
    
    # 확장자 검사
    file_extension = validation['extension'].lstrip('.')
    if file_extension not in category.allowed_extensions:
        return PresignedUrlResponseSchema(
            success=False,
            error=f"File extension '{file_extension}' not allowed"
        )
    
    # S3 키 생성
    file_key = s3_service.generate_file_key(
        request.user.id,
        category.name.lower(),
        payload.filename
    )
    
    # 데이터베이스에 레코드 생성
    image_upload = ImageUpload.objects.create(
        user=request.user,
        category=category,
        original_filename=payload.filename,
        file_key=file_key,
        file_size=payload.file_size,
        content_type=payload.content_type,
        status=ImageUpload.UploadStatus.PENDING
    )
    
    # Presigned URL 생성
    presigned_response = s3_service.get_presigned_upload_url(
        file_key=file_key,
        content_type=payload.content_type,
        file_size=payload.file_size,
        max_file_size=category.max_file_size
    )
    
    if presigned_response['success']:
        # 업로드 시작 시간 기록
        image_upload.upload_started_at = datetime.now()
        image_upload.status = ImageUpload.UploadStatus.UPLOADING
        image_upload.save()
        
        # 응답에 이미지 ID 추가
        presigned_response['data']['image_id'] = str(image_upload.id)
        
        return PresignedUrlResponseSchema(
            success=True,
            data=presigned_response['data']
        )
    else:
        # 실패 시 레코드 삭제
        image_upload.delete()
        
        return PresignedUrlResponseSchema(
            success=False,
            error=presigned_response['error']
        )

# 업로드 완료 처리
@router.post("/upload-complete/{image_id}", response=ImageUploadSchema)
@login_required
@transaction.atomic
def complete_image_upload(request, image_id: str, payload: ImageUploadCompleteSchema):
    """이미지 업로드 완료 처리"""
    
    image_upload = get_object_or_404(
        ImageUpload,
        id=image_id,
        user=request.user,
        status=ImageUpload.UploadStatus.UPLOADING
    )
    
    # S3에서 파일 존재 확인
    if not s3_service.check_file_exists(image_upload.file_key):
        return Response(
            {"error": "File not found in S3"},
            status=400
        )
    
    # S3에서 실제 파일 메타데이터 조회
    file_metadata = s3_service.get_file_metadata(image_upload.file_key)
    if file_metadata:
        image_upload.file_size = file_metadata['size']
        
        # 이미지 크기 정보 추출
        try:
            width, height = image_processor.get_image_dimensions_from_url(image_upload.url)
            image_upload.width = width
            image_upload.height = height
        except Exception as e:
            print(f"Failed to get image dimensions: {e}")
    
    # 업로드 정보 업데이트
    image_upload.status = ImageUpload.UploadStatus.COMPLETED
    image_upload.upload_completed_at = datetime.now()
    image_upload.title = payload.title or ""
    image_upload.description = payload.description or ""
    image_upload.alt_text = payload.alt_text or ""
    image_upload.tags = payload.tags or []
    
    image_upload.save()
    
    return image_upload

# 이미지 목록 조회
@router.get("/", response=List[ImageUploadListSchema])
@paginate(PageNumberPagination, page_size=20)
@login_required
def list_images(request, filters: ImageFilterSchema = Query(...)):
    """이미지 목록 조회"""
    
    queryset = ImageUpload.objects.select_related('category').filter(
        user=request.user,
        status__in=[ImageUpload.UploadStatus.COMPLETED]
    ).order_by('-created_at')
    
    # 필터 적용
    if filters.category_id:
        queryset = queryset.filter(category_id=filters.category_id)
    
    if filters.status:
        queryset = queryset.filter(status=filters.status)
    
    if filters.search:
        queryset = queryset.filter(
            Q(title__icontains=filters.search) |
            Q(description__icontains=filters.search) |
            Q(original_filename__icontains=filters.search)
        )
    
    if filters.tags:
        for tag in filters.tags:
            queryset = queryset.filter(tags__icontains=tag)
    
    if filters.date_from:
        queryset = queryset.filter(created_at__gte=filters.date_from)
    
    if filters.date_to:
        queryset = queryset.filter(created_at__lte=filters.date_to)
    
    return queryset

# 특정 이미지 조회
@router.get("/{image_id}", response=ImageUploadSchema)
@login_required
def get_image(request, image_id: str):
    """특정 이미지 상세 조회"""
    
    image = get_object_or_404(
        ImageUpload.objects.select_related('category'),
        id=image_id,
        user=request.user
    )
    
    return image

# 이미지 정보 업데이트
@router.put("/{image_id}", response=ImageUploadSchema)
@login_required
def update_image(request, image_id: str, payload: ImageUpdateSchema):
    """이미지 정보 업데이트"""
    
    image = get_object_or_404(
        ImageUpload,
        id=image_id,
        user=request.user
    )
    
    # 정보 업데이트
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(image, field, value)
    
    image.save()
    return image

# 이미지 삭제
@router.delete("/{image_id}")
@login_required
@transaction.atomic
def delete_image(request, image_id: str):
    """이미지 삭제"""
    
    image = get_object_or_404(
        ImageUpload,
        id=image_id,
        user=request.user
    )
    
    # S3에서 원본 파일 삭제
    s3_service.delete_file(image.file_key)
    
    # 변형 이미지들도 삭제
    for variant in image.variants.all():
        s3_service.delete_file(variant.file_key)
    
    # 데이터베이스에서 삭제
    image.delete()
    
    return {"message": "Image deleted successfully"}

# 이미지 변형 생성
@router.post("/{image_id}/variants")
@login_required
def create_image_variants(request, image_id: str):
    """이미지 변형 버전 생성 (썸네일, 리사이즈 등)"""
    
    image = get_object_or_404(
        ImageUpload,
        id=image_id,
        user=request.user,
        status=ImageUpload.UploadStatus.COMPLETED
    )
    
    # 여기서 이미지 리사이징 작업을 Celery 태스크로 처리
    from .tasks import create_image_variants_task
    create_image_variants_task.delay(str(image.id))
    
    return {"message": "Image variant creation started"}

# 이미지 변형 목록
@router.get("/{image_id}/variants", response=List[ImageVariantSchema])
@login_required
def list_image_variants(request, image_id: str):
    """이미지 변형 목록 조회"""
    
    image = get_object_or_404(
        ImageUpload,
        id=image_id,
        user=request.user
    )
    
    return image.variants.all()

# 이미지 통계
@router.get("/stats/overview", response=ImageStatsSchema)
@login_required
def get_image_stats(request):
    """이미지 업로드 통계"""
    
    user_images = ImageUpload.objects.filter(user=request.user)
    
    # 기본 통계
    total_images = user_images.count()
    total_size = user_images.aggregate(Sum('file_size'))['file_size__sum'] or 0
    
    # 카테고리별 통계
    by_category = list(user_images.values('category__name').annotate(
        count=Count('id'),
        total_size=Sum('file_size')
    ).order_by('-count'))
    
    # 상태별 통계
    by_status = list(user_images.values('status').annotate(
        count=Count('id')
    ).order_by('-count'))
    
    # 최근 업로드
    recent_uploads = user_images.select_related('category').filter(
        status=ImageUpload.UploadStatus.COMPLETED
    ).order_by('-created_at')[:5]
    
    return {
        "total_images": total_images,
        "total_size": total_size,
        "by_category": by_category,
        "by_status": by_status,
        "recent_uploads": list(recent_uploads)
    }

# 업로드 진행 상황 확인
@router.get("/upload-status/{image_id}")
@login_required
def get_upload_status(request, image_id: str):
    """업로드 진행 상황 확인"""
    
    image = get_object_or_404(
        ImageUpload,
        id=image_id,
        user=request.user
    )
    
    # S3에서 파일 존재 여부 확인
    file_exists = s3_service.check_file_exists(image.file_key)
    
    return {
        "image_id": str(image.id),
        "status": image.status,
        "file_exists_in_s3": file_exists,
        "upload_started_at": image.upload_started_at,
        "upload_completed_at": image.upload_completed_at,
    }
```

## 비동기 태스크 처리

### 1. Celery 태스크

```python
# images/tasks.py
from celery import shared_task
from django.conf import settings
from PIL import Image
import boto3
from io import BytesIO
import requests

@shared_task
def create_image_variants_task(image_id: str):
    """이미지 변형 버전 생성 (비동기)"""
    
    from .models import ImageUpload, ImageVariant
    from .services import S3ImageService
    
    try:
        image = ImageUpload.objects.get(id=image_id)
        s3_service = S3ImageService()
        
        # 원본 이미지 다운로드
        original_url = s3_service.get_presigned_download_url(image.file_key)
        response = requests.get(original_url)
        original_image = Image.open(BytesIO(response.content))
        
        # 다양한 크기의 변형 생성
        variants = [
            ('thumbnail', 150, 150),
            ('small', 300, 300),
            ('medium', 600, 600),
            ('large', 1200, 1200),
        ]
        
        for variant_type, max_width, max_height in variants:
            # 비율 유지하며 리사이즈
            img_copy = original_image.copy()
            img_copy.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # WebP 형식으로 변환
            buffer = BytesIO()
            img_copy.save(buffer, format='WEBP', quality=85, optimize=True)
            buffer.seek(0)
            
            # S3에 업로드
            variant_key = f"{image.file_key.rsplit('.', 1)[0]}_{variant_type}.webp"
            
            s3_service.s3_client.upload_fileobj(
                buffer,
                s3_service.bucket_name,
                variant_key,
                ExtraArgs={
                    'ContentType': 'image/webp',
                    'CacheControl': 'max-age=31536000',  # 1년
                }
            )
            
            # 데이터베이스에 변형 정보 저장
            ImageVariant.objects.update_or_create(
                original_image=image,
                variant_type=variant_type,
                defaults={
                    'file_key': variant_key,
                    'width': img_copy.width,
                    'height': img_copy.height,
                    'file_size': buffer.tell(),
                }
            )
        
        print(f"Successfully created variants for image {image_id}")
        
    except Exception as e:
        print(f"Failed to create variants for image {image_id}: {e}")

@shared_task
def cleanup_orphaned_uploads():
    """고아 업로드 파일 정리"""
    
    from .models import ImageUpload
    from .services import S3ImageService
    from datetime import datetime, timedelta
    
    # 24시간 이상 된 PENDING 상태 파일들 정리
    cutoff_time = datetime.now() - timedelta(hours=24)
    
    orphaned_uploads = ImageUpload.objects.filter(
        status__in=[ImageUpload.UploadStatus.PENDING, ImageUpload.UploadStatus.UPLOADING],
        created_at__lt=cutoff_time
    )
    
    s3_service = S3ImageService()
    
    for upload in orphaned_uploads:
        # S3에서 파일 삭제 시도
        s3_service.delete_file(upload.file_key)
        
        # 데이터베이스에서 레코드 삭제
        upload.delete()
        
        print(f"Cleaned up orphaned upload: {upload.id}")

@shared_task
def generate_image_metadata(image_id: str):
    """이미지 메타데이터 생성"""
    
    from .models import ImageUpload
    from .services import S3ImageService
    import exifread
    
    try:
        image = ImageUpload.objects.get(id=image_id)
        s3_service = S3ImageService()
        
        # 이미지 다운로드
        presigned_url = s3_service.get_presigned_download_url(image.file_key)
        response = requests.get(presigned_url)
        
        # EXIF 데이터 추출
        tags = exifread.process_file(BytesIO(response.content))
        
        metadata = {}
        for tag in tags.keys():
            if tag not in ('JPEGThumbnail', 'TIFFThumbnail'):
                metadata[tag] = str(tags[tag])
        
        # 메타데이터를 JSON 필드에 저장
        # 추후 ImageUpload 모델에 metadata = models.JSONField() 추가 필요
        
        print(f"Generated metadata for image {image_id}")
        
    except Exception as e:
        print(f"Failed to generate metadata for image {image_id}: {e}")
```

## 프론트엔드 연동 예시

### 1. JavaScript 클라이언트

```javascript
// static/js/image-upload.js
class ImageUploader {
    constructor(apiBaseUrl, authToken) {
        this.apiBaseUrl = apiBaseUrl;
        this.authToken = authToken;
    }
    
    async uploadImage(file, categoryId, metadata = {}) {
        try {
            // 1. Presigned URL 요청
            const presignedResponse = await this.getPresignedUrl(file, categoryId);
            
            if (!presignedResponse.success) {
                throw new Error(presignedResponse.error);
            }
            
            const { url, fields, image_id } = presignedResponse.data;
            
            // 2. S3에 직접 업로드
            const uploadResult = await this.uploadToS3(file, url, fields);
            
            if (!uploadResult.success) {
                throw new Error('Failed to upload to S3');
            }
            
            // 3. 업로드 완료 알림
            const completeResult = await this.completeUpload(image_id, metadata);
            
            return {
                success: true,
                image: completeResult
            };
            
        } catch (error) {
            console.error('Upload failed:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }
    
    async getPresignedUrl(file, categoryId) {
        const response = await fetch(`${this.apiBaseUrl}/images/presigned-url`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.authToken}`
            },
            body: JSON.stringify({
                filename: file.name,
                content_type: file.type,
                file_size: file.size,
                category_id: categoryId
            })
        });
        
        return await response.json();
    }
    
    async uploadToS3(file, url, fields) {
        const formData = new FormData();
        
        // S3 필드 추가
        Object.keys(fields).forEach(key => {
            formData.append(key, fields[key]);
        });
        
        // 파일 추가 (마지막에 추가해야 함)
        formData.append('file', file);
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData
            });
            
            return {
                success: response.ok,
                status: response.status
            };
            
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }
    
    async completeUpload(imageId, metadata) {
        const response = await fetch(`${this.apiBaseUrl}/images/upload-complete/${imageId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.authToken}`
            },
            body: JSON.stringify({
                image_id: imageId,
                title: metadata.title || '',
                description: metadata.description || '',
                alt_text: metadata.alt_text || '',
                tags: metadata.tags || []
            })
        });
        
        return await response.json();
    }
    
    // 진행률 표시가 가능한 업로드
    async uploadWithProgress(file, categoryId, metadata = {}, onProgress = null) {
        try {
            const presignedResponse = await this.getPresignedUrl(file, categoryId);
            
            if (!presignedResponse.success) {
                throw new Error(presignedResponse.error);
            }
            
            const { url, fields, image_id } = presignedResponse.data;
            
            // XMLHttpRequest를 사용한 진행률 추적
            const uploadResult = await this.uploadToS3WithProgress(
                file, url, fields, onProgress
            );
            
            if (!uploadResult.success) {
                throw new Error('Failed to upload to S3');
            }
            
            const completeResult = await this.completeUpload(image_id, metadata);
            
            return {
                success: true,
                image: completeResult
            };
            
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }
    
    uploadToS3WithProgress(file, url, fields, onProgress) {
        return new Promise((resolve, reject) => {
            const formData = new FormData();
            
            Object.keys(fields).forEach(key => {
                formData.append(key, fields[key]);
            });
            formData.append('file', file);
            
            const xhr = new XMLHttpRequest();
            
            xhr.upload.addEventListener('progress', (event) => {
                if (event.lengthComputable && onProgress) {
                    const percentComplete = (event.loaded / event.total) * 100;
                    onProgress(percentComplete);
                }
            });
            
            xhr.addEventListener('load', () => {
                if (xhr.status === 204) {
                    resolve({ success: true });
                } else {
                    reject(new Error(`Upload failed with status: ${xhr.status}`));
                }
            });
            
            xhr.addEventListener('error', () => {
                reject(new Error('Upload failed'));
            });
            
            xhr.open('POST', url);
            xhr.send(formData);
        });
    }
}

// 사용 예시
document.addEventListener('DOMContentLoaded', function() {
    const uploader = new ImageUploader('/api', 'your-jwt-token-here');
    const fileInput = document.getElementById('image-file');
    const uploadButton = document.getElementById('upload-button');
    const progressBar = document.getElementById('progress-bar');
    
    uploadButton.addEventListener('click', async function() {
        const file = fileInput.files[0];
        if (!file) {
            alert('Please select a file');
            return;
        }
        
        const metadata = {
            title: document.getElementById('image-title').value,
            description: document.getElementById('image-description').value,
            alt_text: document.getElementById('image-alt').value,
            tags: document.getElementById('image-tags').value.split(',').map(t => t.trim())
        };
        
        const result = await uploader.uploadWithProgress(
            file,
            1, // category_id
            metadata,
            (progress) => {
                progressBar.style.width = `${progress}%`;
                progressBar.textContent = `${Math.round(progress)}%`;
            }
        );
        
        if (result.success) {
            alert('Upload successful!');
            console.log('Uploaded image:', result.image);
        } else {
            alert(`Upload failed: ${result.error}`);
        }
    });
});
```

### 2. React 컴포넌트 예시

```jsx
// components/ImageUploader.jsx
import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

const ImageUploader = ({ categoryId, onUploadComplete }) => {
    const [uploading, setUploading] = useState(false);
    const [progress, setProgress] = useState(0);
    const [error, setError] = useState(null);
    
    const uploader = new ImageUploader('/api', localStorage.getItem('authToken'));
    
    const onDrop = useCallback(async (acceptedFiles) => {
        const file = acceptedFiles[0];
        if (!file) return;
        
        setUploading(true);
        setError(null);
        setProgress(0);
        
        const result = await uploader.uploadWithProgress(
            file,
            categoryId,
            {},
            (progressValue) => setProgress(progressValue)
        );
        
        setUploading(false);
        
        if (result.success) {
            onUploadComplete(result.image);
        } else {
            setError(result.error);
        }
    }, [categoryId, onUploadComplete]);
    
    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'image/*': ['.jpeg', '.jpg', '.png', '.webp', '.gif']
        },
        maxSize: 10 * 1024 * 1024, // 10MB
        multiple: false
    });
    
    return (
        <div className="image-uploader">
            <div 
                {...getRootProps()} 
                className={`dropzone ${isDragActive ? 'active' : ''} ${uploading ? 'uploading' : ''}`}
            >
                <input {...getInputProps()} />
                {uploading ? (
                    <div className="upload-progress">
                        <div className="progress-bar">
                            <div 
                                className="progress-fill" 
                                style={{ width: `${progress}%` }}
                            ></div>
                        </div>
                        <p>Uploading... {Math.round(progress)}%</p>
                    </div>
                ) : (
                    <div className="drop-message">
                        {isDragActive ? (
                            <p>Drop the image here...</p>
                        ) : (
                            <p>Drag & drop an image here, or click to select</p>
                        )}
                    </div>
                )}
            </div>
            
            {error && (
                <div className="error-message">
                    Error: {error}
                </div>
            )}
        </div>
    );
};

export default ImageUploader;
```

## 보안 고려사항

### 1. S3 버킷 정책

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowPresignedUploads",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::YOUR-ACCOUNT-ID:user/YOUR-IAM-USER"
            },
            "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl"
            ],
            "Resource": "arn:aws:s3:::your-bucket-name/images/*",
            "Condition": {
                "StringEquals": {
                    "s3:x-amz-acl": "private"
                },
                "NumericLessThan": {
                    "s3:content-length": 10485760
                }
            }
        },
        {
            "Sid": "AllowGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::your-bucket-name/images/*"
        }
    ]
}
```

### 2. CORS 설정

```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "POST", "PUT"],
        "AllowedOrigins": ["https://yourdomain.com"],
        "ExposeHeaders": ["ETag"],
        "MaxAgeSeconds": 3000
    }
]
```

## 성능 최적화

### 1. CloudFront 설정

```python
# settings.py
AWS_S3_CUSTOM_DOMAIN = 'your-cloudfront-domain.cloudfront.net'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',  # 24시간
}

# 이미지별 캐시 설정
CLOUDFRONT_CACHE_BEHAVIORS = {
    'images/thumbnails/*': 'max-age=31536000',    # 1년
    'images/original/*': 'max-age=86400',         # 1일
}
```

### 2. 이미지 최적화

```python
# images/utils.py
from PIL import Image, ImageOpt
import pillow_heif

def optimize_image(image_data: bytes, format: str = 'WEBP', quality: int = 85) -> bytes:
    """이미지 최적화"""
    
    # HEIF 지원 등록
    pillow_heif.register_heif_opener()
    
    image = Image.open(BytesIO(image_data))
    
    # EXIF 정보 기반 회전 보정
    if hasattr(image, '_getexif'):
        exif = image._getexif()
        if exif is not None:
            orientation = exif.get(274)  # Orientation tag
            if orientation == 3:
                image = image.rotate(180, expand=True)
            elif orientation == 6:
                image = image.rotate(270, expand=True)
            elif orientation == 8:
                image = image.rotate(90, expand=True)
    
    # RGB 변환 (투명도 제거)
    if image.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'P':
            image = image.convert('RGBA')
        background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
        image = background
    
    # 최적화된 저장
    output = BytesIO()
    
    if format.upper() == 'WEBP':
        image.save(output, format='WEBP', quality=quality, optimize=True, method=6)
    elif format.upper() == 'JPEG':
        image.save(output, format='JPEG', quality=quality, optimize=True, progressive=True)
    else:
        image.save(output, format=format, optimize=True)
    
    return output.getvalue()
```

## 모니터링 및 로깅

### 1. 업로드 메트릭 수집

```python
# images/monitoring.py
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import ImageUpload

logger = logging.getLogger('image_uploads')

@receiver(post_save, sender=ImageUpload)
def log_image_upload(sender, instance, created, **kwargs):
    """이미지 업로드 로깅"""
    
    if created:
        logger.info(f"New image upload started: {instance.id}")
    elif instance.status == ImageUpload.UploadStatus.COMPLETED:
        logger.info(f"Image upload completed: {instance.id}, size: {instance.file_size}")
    elif instance.status == ImageUpload.UploadStatus.FAILED:
        logger.error(f"Image upload failed: {instance.id}")

@receiver(post_delete, sender=ImageUpload)
def log_image_deletion(sender, instance, **kwargs):
    """이미지 삭제 로깅"""
    logger.info(f"Image deleted: {instance.id}, original_filename: {instance.original_filename}")

# 성능 메트릭 수집
class ImageUploadMetrics:
    @staticmethod
    def record_upload_time(image_id: str, duration: float):
        """업로드 시간 기록"""
        # Prometheus, CloudWatch 등으로 메트릭 전송
        pass
    
    @staticmethod
    def record_file_size(file_size: int):
        """파일 크기 분포 기록"""
        pass
    
    @staticmethod  
    def record_error(error_type: str, error_message: str):
        """에러 발생 기록"""
        pass
```

## 결론

Django Ninja와 AWS S3 Presigned URL을 활용한 이미지 관리 시스템을 통해 다음과 같은 이점을 얻을 수 있습니다:

### 🎯 주요 장점

1. **성능 향상**: 클라이언트 직접 업로드로 서버 리소스 절약
2. **확장성**: S3의 무제한 스토리지와 글로벌 CDN 활용
3. **보안**: Presigned URL의 시간 제한과 정책 기반 접근 제어
4. **개발 생산성**: Django Ninja의 자동 문서화와 타입 힌트
5. **비용 효율성**: 서버 대역폭 비용 절감

### 💡 실무 적용 포인트

- **점진적 마이그레이션**: 기존 업로드 시스템과 병행 운영 가능
- **다양한 파일 형식**: 이미지 외 문서, 동영상 등으로 확장 가능
- **멀티파트 업로드**: 대용량 파일을 위한 분할 업로드 지원
- **실시간 알림**: WebSocket을 통한 업로드 진행 상황 실시간 업데이트

이 시스템은 소셜 미디어, 전자상거래, 콘텐츠 관리 등 다양한 웹 애플리케이션에서 활용할 수 있으며, AWS의 다른 서비스들과 연동하여 더욱 강력한 기능을 구현할 수 있습니다.