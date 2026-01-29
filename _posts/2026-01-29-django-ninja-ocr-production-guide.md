---
layout: post
title: "Django Ninja로 OCR 서비스 구축 - Upstage API를 활용한 프로덕션 가이드"
date: 2026-01-29
categories: django
author: updaun
image: "/assets/img/posts/2026-01-29-django-ninja-ocr-production-guide.webp"
---

# Django Ninja로 OCR 서비스 구축 - Upstage API를 활용한 프로덕션 가이드

문서 자동화가 필수가 된 시대에 OCR(광학 문자 인식) 서비스는 계약서, 영수증, 신분증, 사업자등록증 등 다양한 문서를 디지털화하는 핵심 기술입니다. 특히 한국어 문서는 복잡한 레이아웃과 세로쓰기, 혼용된 영문과 숫자로 인해 일반 OCR 엔진의 정확도가 떨어지는 경우가 많습니다. 이 글에서는 Django Ninja를 기반으로 한국어 OCR에 최적화된 Upstage Document OCR API를 통합하고, 대용량 문서 처리, 비동기 워크플로우, 보안, 에러 핸들링까지 실서비스에 필요한 모든 요소를 단계별로 구현합니다. 단순한 API 호출 예제를 넘어, 프로덕션 환경에서 안정적으로 운영할 수 있는 아키텍처와 구체적인 코드를 제공합니다.

## 한국어 OCR 서비스 선택 기준과 Upstage의 강점

프로덕션 OCR 서비스를 선택할 때는 한국어 정확도, 레이아웃 분석 능력, API 안정성, 가격 정책, 문서 타입별 특화 모델 지원 여부를 종합적으로 고려해야 합니다. Google Cloud Vision OCR과 AWS Textract는 글로벌 표준이지만 한국어 특유의 복잡한 테이블 구조나 혼합 레이아웃 처리에서 정확도가 떨어지는 경우가 있습니다. Naver Clova OCR은 국내 문서에 강하지만 커스터마이징 옵션이 제한적입니다. Upstage Document OCR은 Solar LLM 기반으로 한국어 문맥 이해가 뛰어나며, 신분증·명함·계약서 등 문서 타입별 최적화 모델을 제공하고, JSON 구조화된 결과를 반환해 후처리가 간편합니다. 특히 테이블 셀 병합, 다단 레이아ウ웃, 세로쓰기 인식률이 우수하고, Base64 인코딩과 URL 업로드 모두 지원하며, Confidence Score와 Bounding Box 정보를 함께 제공해 추가 검증 로직 구현이 용이합니다.

## 아키텍처 설계와 요청 흐름

안정적인 OCR 서비스는 동기·비동기 처리를 분리하고, 파일 업로드와 OCR 처리를 독립적으로 관리하며, 결과 저장과 알림을 자동화해야 합니다. 클라이언트는 먼저 Django Ninja의 업로드 엔드포인트에 이미지나 PDF를 전송하고, 서버는 파일 크기·형식·악성 코드 여부를 검증한 후 S3나 MinIO 같은 객체 스토리지에 저장합니다. 이후 OCR 작업을 Celery 큐에 등록하고 클라이언트에게 `job_id`를 즉시 반환해 사용자 경험을 확보합니다. Celery 워커는 업로드된 파일 경로를 받아 Upstage API를 호출하고, 추출된 텍스트와 메타데이터를 PostgreSQL이나 MongoDB에 저장하며, 완료 시 Webhook이나 WebSocket으로 클라이언트에 통지합니다. 실시간 처리가 필요하면 작은 이미지에 한해 동기 엔드포인트를 별도로 제공하되, 타임아웃(예: 10초)을 설정해 스레드 블로킹을 방지합니다. 이 구조는 대량 배치 처리와 실시간 요청을 모두 수용하며, 워커 스케일 아웃으로 처리량을 유연하게 조절할 수 있습니다.

## 의존성 설치와 환경 설정

프로덕션 환경에서 필요한 핵심 패키지는 다음과 같습니다.

```bash
pip install django-ninja uvicorn[standard] httpx celery redis boto3 python-magic pillow python-dotenv
```

- `django-ninja`: FastAPI 스타일의 API 프레임워크
- `httpx`: 비동기 HTTP 클라이언트로 Upstage API 호출
- `celery`+`redis`: 비동기 작업 큐와 브로커
- `boto3`: AWS S3 파일 업로드/다운로드
- `python-magic`: MIME 타입 검증
- `pillow`: 이미지 전처리 (회전, 리사이징 등)

`settings.py`에 환경 변수를 추가합니다.

```python
# settings.py
import os
from dotenv import load_dotenv

load_dotenv()

# Upstage API 설정
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
UPSTAGE_OCR_ENDPOINT = "https://api.upstage.ai/v1/document-ai/ocr"

# S3 설정
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "ocr-documents")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "ap-northeast-2")

# Celery 설정
CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5분 타임아웃

# 파일 업로드 제한
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff'}
```

`.env` 파일에는 실제 자격 증명을 저장합니다.

```bash
# .env
UPSTAGE_API_KEY=your_upstage_api_key_here
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_STORAGE_BUCKET_NAME=my-ocr-bucket
REDIS_URL=redis://localhost:6379/0
```

## 파일 업로드와 유효성 검증

보안과 안정성을 위해 파일 업로드 단계에서 크기, 타입, 악성 코드 여부를 철저히 검증해야 합니다. Django Ninja의 `UploadedFile` 타입과 Python-magic을 사용해 MIME 타입을 실제 파일 내용 기반으로 확인하고, 화이트리스트 방식으로 허용된 확장자만 처리합니다.

```python
# ocr/api.py
from ninja import NinjaAPI, File, UploadedFile, Schema
from ninja.errors import HttpError
import magic
import hashlib
import uuid
from django.conf import settings

api = NinjaAPI(title="OCR Service API", version="1.0.0")

class UploadResponse(Schema):
    job_id: str
    message: str

def validate_file(file: UploadedFile) -> None:
    """파일 유효성 검증"""
    # 파일 크기 체크
    if file.size > settings.MAX_UPLOAD_SIZE:
        raise HttpError(400, f"파일 크기는 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB를 초과할 수 없습니다.")
    
    # MIME 타입 체크 (실제 파일 내용 기반)
    file_content = file.read()
    file.seek(0)  # 포인터 리셋
    mime = magic.from_buffer(file_content, mime=True)
    
    allowed_mimes = {
        'image/png', 'image/jpeg', 'image/tiff',
        'application/pdf'
    }
    if mime not in allowed_mimes:
        raise HttpError(400, f"지원하지 않는 파일 형식입니다: {mime}")
    
    # 파일 확장자 체크
    extension = file.name.split('.')[-1].lower()
    if extension not in settings.ALLOWED_EXTENSIONS:
        raise HttpError(400, f"허용되지 않은 확장자입니다: {extension}")

@api.post("/upload", response=UploadResponse)
def upload_document(request, file: UploadedFile = File(...)):
    """문서 업로드 및 OCR 작업 생성"""
    try:
        # 파일 검증
        validate_file(file)
        
        # 고유 Job ID 생성
        job_id = str(uuid.uuid4())
        
        # 파일 해시 생성 (중복 체크용)
        file_content = file.read()
        file.seek(0)
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # S3에 업로드 (다음 섹션에서 구현)
        s3_key = f"uploads/{job_id}/{file.name}"
        upload_to_s3(file, s3_key)
        
        # Celery 작업 큐에 등록 (다음 섹션에서 구현)
        from .tasks import process_ocr
        process_ocr.delay(job_id, s3_key, file_hash)
        
        return {
            "job_id": job_id,
            "message": "문서가 업로드되었습니다. OCR 처리가 시작됩니다."
        }
    
    except HttpError:
        raise
    except Exception as e:
        raise HttpError(500, f"업로드 중 오류가 발생했습니다: {str(e)}")
```

이 코드는 파일 시그니처를 확인해 확장자 위조를 방지하고, 해시를 생성해 중복 업로드를 추적하며, 예외를 명확하게 분류해 클라이언트에게 적절한 에러 메시지를 제공합니다.

## S3 업로드와 객체 관리

업로드된 파일을 S3에 안전하게 저장하고, 만료 시간이 있는 Presigned URL을 생성해 접근을 제어합니다. Boto3를 사용해 멀티파트 업로드를 지원하고, 서버리스 라이프사이클 정책으로 오래된 파일을 자동 삭제합니다.

```python
# ocr/storage.py
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)

def upload_to_s3(file, s3_key: str) -> str:
    """S3에 파일 업로드하고 키 반환"""
    try:
        s3_client.upload_fileobj(
            file,
            settings.AWS_STORAGE_BUCKET_NAME,
            s3_key,
            ExtraArgs={
                'ContentType': file.content_type,
                'ServerSideEncryption': 'AES256',  # 서버 사이드 암호화
                'Metadata': {
                    'original_name': file.name
                }
            }
        )
        logger.info(f"파일 업로드 성공: s3://{settings.AWS_STORAGE_BUCKET_NAME}/{s3_key}")
        return s3_key
    except ClientError as e:
        logger.error(f"S3 업로드 실패: {e}")
        raise

def generate_presigned_url(s3_key: str, expiration: int = 3600) -> str:
    """Presigned URL 생성 (기본 1시간)"""
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': s3_key
            },
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        logger.error(f"Presigned URL 생성 실패: {e}")
        return None

def download_from_s3(s3_key: str) -> bytes:
    """S3에서 파일 다운로드"""
    try:
        response = s3_client.get_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=s3_key
        )
        return response['Body'].read()
    except ClientError as e:
        logger.error(f"S3 다운로드 실패: {e}")
        raise
```

S3 버킷에는 다음과 같은 라이프사이클 정책을 설정해 30일 이상 된 파일을 자동으로 삭제합니다.

```json
{
  "Rules": [
    {
      "Id": "DeleteOldOCRFiles",
      "Status": "Enabled",
      "Prefix": "uploads/",
      "Expiration": {
        "Days": 30
      }
    }
  ]
}
```

## Upstage OCR API 클라이언트 구현

Upstage Document OCR API는 Base64 인코딩된 이미지나 URL을 받아 텍스트, 바운딩 박스, 신뢰도를 JSON으로 반환합니다. httpx를 사용한 비동기 클라이언트로 타임아웃과 재시도 로직을 구현합니다.

```python
# ocr/upstage_client.py
import httpx
import base64
from typing import Dict, Any
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class UpstageOCRClient:
    def __init__(self):
        self.api_key = settings.UPSTAGE_API_KEY
        self.endpoint = settings.UPSTAGE_OCR_ENDPOINT
        self.timeout = httpx.Timeout(30.0, connect=10.0)
        
    async def process_document(
        self, 
        image_data: bytes = None,
        image_url: str = None,
        document_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Upstage OCR API 호출
        
        Args:
            image_data: 이미지 바이트 데이터 (Base64로 인코딩됨)
            image_url: 이미지 URL (image_data와 둘 중 하나 필수)
            document_type: 문서 타입 (general, id_card, business_card, receipt 등)
        
        Returns:
            OCR 결과 딕셔너리
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 페이로드 구성
        payload = {"document_type": document_type}
        
        if image_data:
            encoded = base64.b64encode(image_data).decode('utf-8')
            payload["image"] = encoded
        elif image_url:
            payload["image_url"] = image_url
        else:
            raise ValueError("image_data 또는 image_url 중 하나는 필수입니다.")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()
        
        except httpx.TimeoutException:
            logger.error("Upstage API 타임아웃")
            raise Exception("OCR 처리 시간 초과")
        
        except httpx.HTTPStatusError as e:
            logger.error(f"Upstage API 에러: {e.response.status_code} - {e.response.text}")
            raise Exception(f"OCR API 에러: {e.response.status_code}")
        
        except Exception as e:
            logger.error(f"OCR 처리 중 예외 발생: {str(e)}")
            raise
    
    def parse_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """OCR 결과 파싱 및 후처리"""
        pages = result.get("pages", [])
        
        extracted_data = {
            "full_text": "",
            "pages": [],
            "total_confidence": 0.0
        }
        
        for page in pages:
            page_text = []
            page_confidence = []
            
            for element in page.get("elements", []):
                text = element.get("text", "")
                confidence = element.get("confidence", 0.0)
                bbox = element.get("bounding_box", {})
                
                page_text.append(text)
                page_confidence.append(confidence)
            
            page_full_text = " ".join(page_text)
            avg_confidence = sum(page_confidence) / len(page_confidence) if page_confidence else 0.0
            
            extracted_data["pages"].append({
                "page_number": page.get("page", 1),
                "text": page_full_text,
                "confidence": avg_confidence
            })
            
            extracted_data["full_text"] += page_full_text + "\n"
        
        # 전체 평균 신뢰도 계산
        if extracted_data["pages"]:
            extracted_data["total_confidence"] = sum(
                p["confidence"] for p in extracted_data["pages"]
            ) / len(extracted_data["pages"])
        
        return extracted_data
```

이 클라이언트는 Base64와 URL 모두 지원하고, 문서 타입별 최적화된 모델을 선택할 수 있으며, 신뢰도 점수를 계산해 품질 검증에 활용할 수 있습니다.

## Celery 비동기 작업 구현

OCR 처리는 수 초에서 수십 초가 걸리므로 Celery로 백그라운드 작업화하고, 결과를 데이터베이스에 저장하며, 실패 시 자동 재시도합니다.

```python
# ocr/tasks.py
from celery import shared_task
from .upstage_client import UpstageOCRClient
from .storage import download_from_s3, generate_presigned_url
from .models import OCRJob
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_ocr(self, job_id: str, s3_key: str, file_hash: str):
    """OCR 처리 Celery 태스크"""
    try:
        # Job 상태 업데이트
        job = OCRJob.objects.get(job_id=job_id)
        job.status = 'processing'
        job.save()
        
        # S3에서 파일 다운로드
        logger.info(f"S3에서 파일 다운로드: {s3_key}")
        image_data = download_from_s3(s3_key)
        
        # Upstage OCR 처리
        logger.info(f"OCR 처리 시작: {job_id}")
        client = UpstageOCRClient()
        
        # 비동기 함수를 동기로 실행 (Celery 워커 내부)
        import asyncio
        raw_result = asyncio.run(
            client.process_document(image_data=image_data)
        )
        
        # 결과 파싱
        parsed_result = client.parse_result(raw_result)
        
        # 신뢰도 체크
        if parsed_result["total_confidence"] < 0.7:
            logger.warning(f"낮은 신뢰도 감지: {parsed_result['total_confidence']}")
        
        # DB에 결과 저장
        job.status = 'completed'
        job.extracted_text = parsed_result["full_text"]
        job.confidence_score = parsed_result["total_confidence"]
        job.raw_result = raw_result
        job.save()
        
        logger.info(f"OCR 처리 완료: {job_id}")
        
        # Webhook 통지 (있는 경우)
        if job.webhook_url:
            send_webhook_notification.delay(job_id)
        
        return {
            "job_id": job_id,
            "status": "completed",
            "confidence": parsed_result["total_confidence"]
        }
    
    except OCRJob.DoesNotExist:
        logger.error(f"Job을 찾을 수 없음: {job_id}")
        raise
    
    except Exception as e:
        logger.error(f"OCR 처리 실패: {job_id} - {str(e)}")
        
        # Job 상태 업데이트
        try:
            job = OCRJob.objects.get(job_id=job_id)
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
        except:
            pass
        
        # 재시도
        raise self.retry(exc=e)

@shared_task
def send_webhook_notification(job_id: str):
    """Webhook 통지 전송"""
    import httpx
    
    try:
        job = OCRJob.objects.get(job_id=job_id)
        
        if not job.webhook_url:
            return
        
        payload = {
            "job_id": job.job_id,
            "status": job.status,
            "extracted_text": job.extracted_text,
            "confidence_score": job.confidence_score
        }
        
        with httpx.Client(timeout=10.0) as client:
            response = client.post(job.webhook_url, json=payload)
            response.raise_for_status()
        
        logger.info(f"Webhook 전송 성공: {job_id}")
    
    except Exception as e:
        logger.error(f"Webhook 전송 실패: {job_id} - {str(e)}")
```

## Django 모델 정의

OCR 작업의 상태와 결과를 추적하기 위한 모델을 정의합니다. PostgreSQL의 JSONField를 사용해 원본 API 응답을 저장하고, 인덱스를 최적화합니다.

```python
# ocr/models.py
from django.db import models
from django.utils import timezone
import uuid

class OCRJob(models.Model):
    STATUS_CHOICES = [
        ('pending', '대기 중'),
        ('processing', '처리 중'),
        ('completed', '완료'),
        ('failed', '실패'),
    ]
    
    job_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    
    # 파일 정보
    s3_key = models.CharField(max_length=500)
    file_hash = models.CharField(max_length=64, db_index=True)  # SHA-256
    original_filename = models.CharField(max_length=255)
    
    # OCR 결과
    extracted_text = models.TextField(blank=True, null=True)
    confidence_score = models.FloatField(null=True, blank=True)
    raw_result = models.JSONField(null=True, blank=True)  # 원본 API 응답
    
    # 에러 정보
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.IntegerField(default=0)
    
    # Webhook
    webhook_url = models.URLField(blank=True, null=True)
    
    # 사용자 정보 (선택)
    user_id = models.IntegerField(null=True, blank=True, db_index=True)
    
    class Meta:
        db_table = 'ocr_jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user_id', 'created_at']),
        ]
    
    def __str__(self):
        return f"OCRJob({self.job_id}) - {self.status}"
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    @property
    def processing_time(self):
        """처리 시간 계산 (초)"""
        if self.status == 'completed':
            return (self.updated_at - self.created_at).total_seconds()
        return None
```

마이그레이션을 생성하고 적용합니다.

```bash
python manage.py makemigrations
python manage.py migrate
```

## 작업 조회 및 결과 반환 API

클라이언트가 `job_id`로 작업 상태를 조회하고, 완료된 경우 추출된 텍스트와 신뢰도를 받을 수 있는 엔드포인트를 구현합니다.

```python
# ocr/api.py (계속)
from .models import OCRJob
from typing import Optional

class JobStatusResponse(Schema):
    job_id: str
    status: str
    created_at: str
    updated_at: str
    extracted_text: Optional[str] = None
    confidence_score: Optional[float] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None

@api.get("/jobs/{job_id}", response=JobStatusResponse)
def get_job_status(request, job_id: str):
    """OCR 작업 상태 조회"""
    try:
        job = OCRJob.objects.get(job_id=job_id)
        
        return {
            "job_id": str(job.job_id),
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "extracted_text": job.extracted_text if job.is_completed else None,
            "confidence_score": job.confidence_score,
            "error_message": job.error_message,
            "processing_time": job.processing_time
        }
    
    except OCRJob.DoesNotExist:
        raise HttpError(404, "작업을 찾을 수 없습니다.")

class JobListResponse(Schema):
    jobs: list[JobStatusResponse]
    total: int
    page: int
    page_size: int

@api.get("/jobs", response=JobListResponse)
def list_jobs(
    request, 
    page: int = 1, 
    page_size: int = 20,
    status: Optional[str] = None
):
    """OCR 작업 목록 조회 (페이지네이션)"""
    queryset = OCRJob.objects.all()
    
    if status:
        queryset = queryset.filter(status=status)
    
    # 사용자 필터링 (인증이 있는 경우)
    # if request.user.is_authenticated:
    #     queryset = queryset.filter(user_id=request.user.id)
    
    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    
    jobs = queryset[start:end]
    
    job_list = [
        {
            "job_id": str(job.job_id),
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "extracted_text": job.extracted_text if job.is_completed else None,
            "confidence_score": job.confidence_score,
            "error_message": job.error_message,
            "processing_time": job.processing_time
        }
        for job in jobs
    ]
    
    return {
        "jobs": job_list,
        "total": total,
        "page": page,
        "page_size": page_size
    }
```

## 에러 핸들링과 재시도 전략

프로덕션에서는 네트워크 장애, API 레이트 리밋, 일시적 서비스 중단 등 다양한 에러 상황에 대응해야 합니다. Celery의 재시도 메커니즘과 지수 백오프를 사용해 안정성을 높입니다.

```python
# ocr/tasks.py (재시도 전략 강화)
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

@shared_task(
    bind=True,
    max_retries=5,
    autoretry_for=(httpx.TimeoutException, httpx.HTTPStatusError),
    retry_backoff=True,  # 지수 백오프 활성화
    retry_backoff_max=600,  # 최대 10분 대기
    retry_jitter=True  # 랜덤 지터 추가
)
def process_ocr_with_retry(self, job_id: str, s3_key: str, file_hash: str):
    """재시도 전략이 강화된 OCR 처리"""
    try:
        # 기존 process_ocr 로직과 동일
        job = OCRJob.objects.get(job_id=job_id)
        job.retry_count = self.request.retries
        job.save()
        
        # ... OCR 처리 로직 ...
        
    except MaxRetriesExceededError:
        logger.error(f"최대 재시도 횟수 초과: {job_id}")
        job = OCRJob.objects.get(job_id=job_id)
        job.status = 'failed'
        job.error_message = "최대 재시도 횟수를 초과했습니다."
        job.save()
        raise
    
    except Exception as e:
        # 재시도 불가능한 에러 (파일 없음, 잘못된 형식 등)
        if "not found" in str(e).lower() or "invalid" in str(e).lower():
            logger.error(f"재시도 불가능한 에러: {job_id} - {str(e)}")
            job = OCRJob.objects.get(job_id=job_id)
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
            raise  # 재시도하지 않음
        
        # 재시도 가능한 에러
        raise self.retry(exc=e)
```

글로벌 에러 핸들러를 추가해 일관된 에러 응답을 제공합니다.

```python
# ocr/api.py (에러 핸들러 추가)
from ninja.errors import ValidationError

@api.exception_handler(ValidationError)
def validation_error_handler(request, exc):
    return api.create_response(
        request,
        {"error": "입력 데이터가 유효하지 않습니다.", "details": exc.errors},
        status=422
    )

@api.exception_handler(HttpError)
def http_error_handler(request, exc):
    return api.create_response(
        request,
        {"error": str(exc)},
        status=exc.status_code
    )

@api.exception_handler(Exception)
def generic_error_handler(request, exc):
    logger.exception("예상치 못한 에러 발생")
    return api.create_response(
        request,
        {"error": "서버 내부 오류가 발생했습니다."},
        status=500
    )
```

## 성능 최적화와 캐싱 전략

동일한 문서가 반복 업로드되는 경우 OCR을 재실행하지 않고 캐시된 결과를 반환하면 비용과 시간을 절약할 수 있습니다. 파일 해시를 활용한 중복 제거 로직을 구현합니다.

```python
# ocr/api.py (중복 체크 로직 추가)
from django.core.cache import cache

@api.post("/upload", response=UploadResponse)
def upload_document(request, file: UploadedFile = File(...)):
    """문서 업로드 및 OCR 작업 생성 (중복 체크 포함)"""
    try:
        validate_file(file)
        
        # 파일 해시 생성
        file_content = file.read()
        file.seek(0)
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # 중복 체크 - 최근 처리된 동일 파일이 있는지 확인
        existing_job = OCRJob.objects.filter(
            file_hash=file_hash,
            status='completed'
        ).order_by('-created_at').first()
        
        if existing_job:
            logger.info(f"중복 파일 감지: {file_hash}, 기존 작업 반환: {existing_job.job_id}")
            return {
                "job_id": str(existing_job.job_id),
                "message": "동일한 파일이 이미 처리되었습니다. 기존 결과를 반환합니다."
            }
        
        # 새로운 작업 생성
        job_id = str(uuid.uuid4())
        s3_key = f"uploads/{job_id}/{file.name}"
        upload_to_s3(file, s3_key)
        
        # DB에 Job 레코드 생성
        OCRJob.objects.create(
            job_id=job_id,
            s3_key=s3_key,
            file_hash=file_hash,
            original_filename=file.name,
            status='pending'
        )
        
        # Celery 작업 시작
        from .tasks import process_ocr
        process_ocr.delay(job_id, s3_key, file_hash)
        
        return {
            "job_id": job_id,
            "message": "문서가 업로드되었습니다. OCR 처리가 시작됩니다."
        }
    
    except HttpError:
        raise
    except Exception as e:
        logger.exception("업로드 중 오류 발생")
        raise HttpError(500, f"업로드 중 오류가 발생했습니다: {str(e)}")
```

Redis 캐시를 사용해 자주 조회되는 작업 결과를 캐싱합니다.

```python
# ocr/api.py (캐시 적용)
CACHE_TIMEOUT = 3600  # 1시간

@api.get("/jobs/{job_id}", response=JobStatusResponse)
def get_job_status(request, job_id: str):
    """OCR 작업 상태 조회 (캐시 적용)"""
    cache_key = f"ocr_job:{job_id}"
    
    # 캐시 확인
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    try:
        job = OCRJob.objects.get(job_id=job_id)
        
        result = {
            "job_id": str(job.job_id),
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "extracted_text": job.extracted_text if job.is_completed else None,
            "confidence_score": job.confidence_score,
            "error_message": job.error_message,
            "processing_time": job.processing_time
        }
        
        # 완료된 작업만 캐시
        if job.is_completed:
            cache.set(cache_key, result, CACHE_TIMEOUT)
        
        return result
    
    except OCRJob.DoesNotExist:
        raise HttpError(404, "작업을 찾을 수 없습니다.")
```

## 모니터링과 로깅

프로덕션에서는 처리 시간, 에러율, API 응답 시간, 신뢰도 분포를 실시간으로 모니터링해야 합니다. Prometheus와 Grafana를 사용한 메트릭 수집 전략을 구현합니다.

```python
# ocr/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# 메트릭 정의
ocr_requests_total = Counter(
    'ocr_requests_total',
    'Total OCR requests',
    ['status']
)

ocr_processing_duration = Histogram(
    'ocr_processing_duration_seconds',
    'OCR processing duration',
    buckets=[1, 5, 10, 30, 60, 120, 300]
)

ocr_confidence_score = Histogram(
    'ocr_confidence_score',
    'OCR confidence score distribution',
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]
)

ocr_queue_length = Gauge(
    'ocr_queue_length',
    'Current OCR queue length'
)

# tasks.py에서 사용
@shared_task(bind=True, max_retries=3)
def process_ocr(self, job_id: str, s3_key: str, file_hash: str):
    start_time = time.time()
    
    try:
        # OCR 처리 로직...
        
        # 메트릭 기록
        duration = time.time() - start_time
        ocr_processing_duration.observe(duration)
        ocr_confidence_score.observe(parsed_result["total_confidence"])
        ocr_requests_total.labels(status='success').inc()
        
    except Exception as e:
        ocr_requests_total.labels(status='failed').inc()
        raise
```

구조화된 로깅을 위해 Python의 structlog를 사용합니다.

```python
# settings.py (로깅 설정)
import structlog

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': structlog.stdlib.ProcessorFormatter,
            'processor': structlog.processors.JSONRenderer(),
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/ocr.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'loggers': {
        'ocr': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

## Docker와 배포 설정

프로덕션 배포를 위한 Docker Compose 구성과 환경별 설정을 정리합니다. Nginx를 리버스 프록시로 사용하고, Celery 워커를 별도 컨테이너로 분리합니다.

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    command: uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --workers 4
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
      - redis

  celery_worker:
    build: .
    command: celery -A config worker -l info --concurrency=4
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - db
      - redis

  celery_beat:
    build: .
    command: celery -A config beat -l info
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - redis

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: ocr_db
      POSTGRES_USER: ocr_user
      POSTGRES_PASSWORD: ocr_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - web

volumes:
  postgres_data:
```

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# Static 파일 수집
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
```

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream django {
        server web:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;

        client_max_body_size 20M;

        location / {
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # 타임아웃 설정
            proxy_connect_timeout 300s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;
        }

        location /static/ {
            alias /app/staticfiles/;
        }
    }
}
```

## 보안 강화

API 키 보호, Rate Limiting, CORS 설정, 파일 암호화 등 보안 강화 전략을 구현합니다.

```python
# settings.py (보안 설정)
# CORS 설정
CORS_ALLOWED_ORIGINS = [
    "https://your-frontend.com",
]

# CSRF 설정
CSRF_TRUSTED_ORIGINS = [
    "https://your-domain.com",
]

# 보안 헤더
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS 강제 (프로덕션)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
```

Rate Limiting을 위해 django-ratelimit을 사용합니다.

```python
# ocr/api.py (Rate Limiting 추가)
from django_ratelimit.decorators import ratelimit
from ninja import NinjaAPI

api = NinjaAPI()

def rate_limit_key(request):
    """Rate limit 키 생성 (IP 또는 사용자 ID)"""
    if request.user.is_authenticated:
        return f"user:{request.user.id}"
    return request.META.get('REMOTE_ADDR', 'unknown')

@api.post("/upload", response=UploadResponse)
@ratelimit(key=rate_limit_key, rate='10/m', method='POST')
def upload_document(request, file: UploadedFile = File(...)):
    """문서 업로드 (분당 10회 제한)"""
    # 기존 로직...
    pass
```

민감한 문서를 위한 암호화 저장:

```python
# ocr/encryption.py
from cryptography.fernet import Fernet
from django.conf import settings
import base64

class DocumentEncryptor:
    def __init__(self):
        key = settings.ENCRYPTION_KEY.encode()
        self.cipher = Fernet(key)
    
    def encrypt_file(self, file_data: bytes) -> bytes:
        """파일 데이터 암호화"""
        return self.cipher.encrypt(file_data)
    
    def decrypt_file(self, encrypted_data: bytes) -> bytes:
        """파일 데이터 복호화"""
        return self.cipher.decrypt(encrypted_data)

# storage.py에서 사용
def upload_to_s3_encrypted(file, s3_key: str) -> str:
    """암호화하여 S3에 업로드"""
    encryptor = DocumentEncryptor()
    file_data = file.read()
    encrypted_data = encryptor.encrypt_file(file_data)
    
    # 암호화된 데이터 업로드
    from io import BytesIO
    encrypted_file = BytesIO(encrypted_data)
    
    s3_client.upload_fileobj(
        encrypted_file,
        settings.AWS_STORAGE_BUCKET_NAME,
        s3_key,
        ExtraArgs={
            'ServerSideEncryption': 'AES256',
            'Metadata': {'encrypted': 'true'}
        }
    )
    return s3_key
```

## 테스트 전략

단위 테스트, 통합 테스트, E2E 테스트를 작성해 코드 품질을 보장합니다. pytest와 pytest-django를 사용합니다.

```python
# tests/test_ocr_api.py
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, Mock
from ocr.models import OCRJob

@pytest.fixture
def sample_image():
    """테스트용 이미지 파일"""
    return SimpleUploadedFile(
        "test.png",
        b"fake image content",
        content_type="image/png"
    )

@pytest.mark.django_db
class TestOCRAPI:
    def test_upload_document_success(self, client, sample_image):
        """문서 업로드 성공 테스트"""
        with patch('ocr.api.upload_to_s3') as mock_s3, \
             patch('ocr.tasks.process_ocr.delay') as mock_task:
            
            response = client.post(
                '/api/upload',
                {'file': sample_image},
                format='multipart'
            )
            
            assert response.status_code == 200
            data = response.json()
            assert 'job_id' in data
            assert mock_s3.called
            assert mock_task.called
    
    def test_upload_invalid_file_type(self, client):
        """잘못된 파일 형식 업로드 테스트"""
        invalid_file = SimpleUploadedFile(
            "test.txt",
            b"text content",
            content_type="text/plain"
        )
        
        response = client.post(
            '/api/upload',
            {'file': invalid_file},
            format='multipart'
        )
        
        assert response.status_code == 400
    
    def test_get_job_status(self, client):
        """작업 상태 조회 테스트"""
        job = OCRJob.objects.create(
            s3_key="test/key",
            file_hash="abc123",
            original_filename="test.png",
            status="completed",
            extracted_text="테스트 텍스트",
            confidence_score=0.95
        )
        
        response = client.get(f'/api/jobs/{job.job_id}')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'completed'
        assert data['extracted_text'] == '테스트 텍스트'
        assert data['confidence_score'] == 0.95

@pytest.mark.django_db
class TestUpstageClient:
    @pytest.mark.asyncio
    async def test_process_document_success(self):
        """Upstage API 호출 성공 테스트"""
        from ocr.upstage_client import UpstageOCRClient
        
        client = UpstageOCRClient()
        
        mock_response = {
            "pages": [{
                "page": 1,
                "elements": [
                    {
                        "text": "테스트",
                        "confidence": 0.95,
                        "bounding_box": {}
                    }
                ]
            }]
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: mock_response
            )
            
            result = await client.process_document(
                image_data=b"fake image"
            )
            
            assert "pages" in result
            assert len(result["pages"]) == 1
```

## 실전 운영 팁과 문제 해결

프로덕션 환경에서 자주 발생하는 문제와 해결 방법을 정리합니다.

**1. 긴 처리 시간 해결**
- 이미지 전처리로 해상도 최적화 (3000px 이상은 리사이징)
- PDF는 페이지별로 분할 처리
- Celery 워커 수를 동적으로 스케일링

```python
# 이미지 전처리 예시
from PIL import Image
import io

def optimize_image(image_data: bytes, max_width: int = 3000) -> bytes:
    """이미지 최적화"""
    img = Image.open(io.BytesIO(image_data))
    
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)
    
    output = io.BytesIO()
    img.save(output, format='PNG', optimize=True)
    return output.getvalue()
```

**2. 낮은 신뢰도 문제**
- 이미지 품질 체크 (흐림, 노이즈, 기울기)
- 전처리: 이진화, 대비 향상, 회전 보정
- 실패 시 사용자에게 재촬영 요청

**3. 비용 최적화**
- 중복 파일 해시 체크로 불필요한 API 호출 제거
- 캐시 히트율 모니터링
- S3 Intelligent-Tiering으로 자동 비용 절감
- 낮은 우선순위 작업은 별도 큐로 분리

**4. 데이터베이스 성능**
- `file_hash`에 인덱스 설정
- 오래된 작업 정기적으로 아카이빙
- 읽기 복제본 사용

```python
# 오래된 작업 정리 Celery Beat 작업
from celery import shared_task
from datetime import timedelta
from django.utils import timezone

@shared_task
def cleanup_old_jobs():
    """30일 이상 된 완료/실패 작업 삭제"""
    threshold = timezone.now() - timedelta(days=30)
    
    deleted_count = OCRJob.objects.filter(
        created_at__lt=threshold,
        status__in=['completed', 'failed']
    ).delete()[0]
    
    logger.info(f"정리된 작업 수: {deleted_count}")
```

**5. 모니터링 대시보드**
Grafana에서 추적할 주요 지표:
- 시간당 처리량
- 평균 처리 시간
- 에러율 (전체, API별)
- 신뢰도 분포
- 큐 길이와 대기 시간
- S3 업로드/다운로드 속도

## 확장 가능한 기능 추가

실제 서비스에서 유용한 추가 기능들을 구현합니다.

**1. 배치 처리 API**

```python
@api.post("/batch-upload", response=list[UploadResponse])
def batch_upload(request, files: list[UploadedFile] = File(...)):
    """여러 문서 일괄 업로드"""
    results = []
    
    for file in files:
        try:
            validate_file(file)
            job_id = str(uuid.uuid4())
            s3_key = f"uploads/{job_id}/{file.name}"
            
            upload_to_s3(file, s3_key)
            
            OCRJob.objects.create(
                job_id=job_id,
                s3_key=s3_key,
                file_hash=hashlib.sha256(file.read()).hexdigest(),
                original_filename=file.name
            )
            file.seek(0)
            
            process_ocr.delay(job_id, s3_key, file_hash)
            
            results.append({
                "job_id": job_id,
                "message": f"{file.name} 업로드 완료"
            })
        except Exception as e:
            results.append({
                "job_id": None,
                "message": f"{file.name} 업로드 실패: {str(e)}"
            })
    
    return results
```

**2. 텍스트 검색 API**

```python
from django.db.models import Q

class SearchRequest(Schema):
    query: str
    limit: int = 10

@api.post("/search", response=list[JobStatusResponse])
def search_ocr_results(request, payload: SearchRequest):
    """추출된 텍스트 전문 검색"""
    jobs = OCRJob.objects.filter(
        Q(extracted_text__icontains=payload.query) &
        Q(status='completed')
    )[:payload.limit]
    
    return [
        {
            "job_id": str(job.job_id),
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "extracted_text": job.extracted_text[:200],  # 미리보기
            "confidence_score": job.confidence_score,
        }
        for job in jobs
    ]
```

**3. 문서 타입별 분류**

```python
def detect_document_type(extracted_text: str) -> str:
    """추출된 텍스트로 문서 타입 감지"""
    if any(keyword in extracted_text for keyword in ['주민등록증', '생년월일']):
        return 'id_card'
    elif '사업자등록번호' in extracted_text:
        return 'business_registration'
    elif any(keyword in extracted_text for keyword in ['영수증', '합계', '카드승인']):
        return 'receipt'
    elif '계약' in extracted_text:
        return 'contract'
    else:
        return 'general'

# tasks.py에서 사용
job.document_type = detect_document_type(parsed_result["full_text"])
job.save()
```

## 결론

Django Ninja와 Upstage Document OCR을 결합한 프로덕션급 OCR 서비스는 한국어 문서 처리에 최적화된 고성능 솔루션을 제공합니다. 이 글에서 다룬 아키텍처는 파일 업로드 검증부터 비동기 처리, 결과 캐싱, 에러 핸들링, 보안, 모니터링까지 실제 서비스 운영에 필요한 모든 요소를 포함합니다. Upstage API의 높은 한국어 인식률과 구조화된 JSON 응답은 계약서, 영수증, 신분증 등 다양한 문서 타입을 안정적으로 처리할 수 있게 해줍니다.

핵심은 동기·비동기 처리를 명확히 분리하고, Celery로 장시간 작업을 백그라운드화하며, 파일 해시 기반 중복 제거로 비용을 절감하는 것입니다. Redis 캐싱과 PostgreSQL 인덱싱으로 조회 성능을 최적화하고, Prometheus와 structlog로 실시간 메트릭과 구조화된 로그를 수집하면 장애 대응 시간을 크게 줄일 수 있습니다. Rate Limiting과 파일 암호화는 보안을 강화하고, Docker Compose로 일관된 환경을 유지하며, 자동 재시도와 지수 백오프로 일시적 장애에 견고하게 대응합니다.

이 아키텍처는 소규모 스타트업부터 대규모 엔터프라이즈까지 확장 가능하며, Celery 워커 수를 조절하고 Redis 클러스터를 구성하면 시간당 수만 건의 요청도 처리할 수 있습니다. 실제 운영에서는 이미지 품질 체크와 전처리를 추가하고, 신뢰도가 낮은 결과는 사람이 검증하는 하이브리드 파이프라인을 구축하면 정확도를 더욱 높일 수 있습니다. Django Ninja의 자동 API 문서화와 FastAPI 스타일 타입 힌트는 팀 협업과 유지보수를 용이하게 하며, Upstage의 지속적인 모델 개선은 별도 재학습 없이도 인식 성능을 향상시킵니다. 이제 이 가이드를 기반으로 안정적이고 확장 가능한 OCR 서비스를 구축하고, 비즈니스 요구사항에 맞게 커스터마이징할 수 있습니다.
