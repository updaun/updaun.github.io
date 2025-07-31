---
layout: post
title: "Django에서 YOLO v10 연동 완전 가이드: 실시간 객체 탐지 웹 애플리케이션 구축하기"
date: 2025-07-31 10:00:00 +0900
categories: [Django, Computer Vision, AI, Machine Learning]
tags: [Django, YOLO, YOLOv10, Computer Vision, Object Detection, AI, Machine Learning, OpenCV, PIL, Real-time, Web Application]
---

웹 개발과 컴퓨터 비전 기술을 결합하여 실시간 객체 탐지 애플리케이션을 만들어보고 싶으신가요? 이 글에서는 Django 프레임워크와 최신 YOLO v10 모델을 연동하여 강력한 실시간 객체 탐지 웹 애플리케이션을 구축하는 과정을 단계별로 자세히 알아보겠습니다.

## 🎯 프로젝트 개요 및 목표

### 구현할 기능들
- 이미지 업로드를 통한 객체 탐지
- 실시간 웹캠 객체 탐지
- 탐지 결과 시각화 및 저장
- RESTful API를 통한 객체 탐지 서비스
- 관리자 페이지를 통한 탐지 기록 관리

### 기술 스택
- **Backend**: Django 4.2+
- **AI Model**: YOLO v10 (Ultralytics)
- **Image Processing**: OpenCV, PIL
- **Frontend**: HTML5, JavaScript, Bootstrap
- **Database**: SQLite/PostgreSQL
- **Additional**: Celery (비동기 처리), Redis (캐싱)

## 🛠️ 환경 설정 및 프로젝트 초기화

### 1. 가상환경 생성 및 패키지 설치

먼저 프로젝트를 위한 가상환경을 생성하고 필요한 패키지들을 설치하겠습니다.

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Linux/Mac)
source venv/bin/activate

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 필수 패키지 설치
pip install django==4.2.4
pip install ultralytics
pip install opencv-python
pip install Pillow
pip install numpy
pip install torch torchvision
pip install celery redis
pip install django-cors-headers
pip install djangorestframework
```

### 2. Django 프로젝트 생성

```bash
# Django 프로젝트 생성
django-admin startproject yolo_detection_project
cd yolo_detection_project

# 객체 탐지 앱 생성
python manage.py startapp object_detection
```

### 3. requirements.txt 생성

```text
Django==4.2.4
ultralytics==8.0.196
opencv-python==4.8.0.76
Pillow==10.0.0
numpy==1.24.3
torch==2.0.1
torchvision==0.15.2
celery==5.3.1
redis==4.6.0
django-cors-headers==4.2.0
djangorestframework==3.14.0
python-multipart==0.0.6
```

## ⚙️ Django 설정 구성

### 1. settings.py 기본 설정

```python
# settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 보안 설정
SECRET_KEY = 'your-secret-key-here'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# 앱 등록
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'object_detection',
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

ROOT_URLCONF = 'yolo_detection_project.urls'

# 템플릿 설정
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# 데이터베이스 설정
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 미디어 파일 설정
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 정적 파일 설정
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# YOLO 모델 설정
YOLO_MODEL_PATH = BASE_DIR / 'models' / 'yolov10n.pt'
DETECTION_CONFIDENCE = 0.25
DETECTION_IOU_THRESHOLD = 0.45

# Celery 설정 (비동기 처리용)
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# REST Framework 설정
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ]
}

# CORS 설정
CORS_ALLOW_ALL_ORIGINS = True  # 개발환경에서만 사용
```

## 📊 Django 모델 정의

### 1. 객체 탐지 결과를 저장할 모델 생성

```python
# object_detection/models.py
from django.db import models
from django.contrib.auth.models import User
import json

class DetectionSession(models.Model):
    """탐지 세션 정보를 저장하는 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Session {self.session_id} - {self.created_at}"

class ImageDetection(models.Model):
    """이미지 객체 탐지 결과를 저장하는 모델"""
    session = models.ForeignKey(DetectionSession, on_delete=models.CASCADE, related_name='detections')
    original_image = models.ImageField(upload_to='original_images/')
    processed_image = models.ImageField(upload_to='processed_images/', null=True, blank=True)
    
    # 탐지 메타데이터
    detection_count = models.IntegerField(default=0)
    confidence_threshold = models.FloatField(default=0.25)
    processing_time = models.FloatField(null=True, blank=True)  # 초 단위
    
    # 탐지 결과 JSON 저장
    detection_results = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Detection {self.id} - {self.detection_count} objects"
    
    def get_detected_classes(self):
        """탐지된 클래스 목록 반환"""
        if not self.detection_results.get('detections'):
            return []
        
        classes = []
        for detection in self.detection_results['detections']:
            class_name = detection.get('class_name')
            if class_name and class_name not in classes:
                classes.append(class_name)
        return classes
    
    def get_highest_confidence(self):
        """가장 높은 신뢰도 점수 반환"""
        if not self.detection_results.get('detections'):
            return 0.0
        
        confidences = [det.get('confidence', 0.0) for det in self.detection_results['detections']]
        return max(confidences) if confidences else 0.0

class DetectedObject(models.Model):
    """개별 탐지된 객체 정보"""
    image_detection = models.ForeignKey(ImageDetection, on_delete=models.CASCADE, related_name='objects')
    class_name = models.CharField(max_length=100)
    confidence = models.FloatField()
    
    # 바운딩 박스 좌표 (YOLO 형식: 정규화된 좌표)
    x_center = models.FloatField()
    y_center = models.FloatField()
    width = models.FloatField()
    height = models.FloatField()
    
    # 실제 픽셀 좌표 (시각화용)
    x_min = models.IntegerField()
    y_min = models.IntegerField()
    x_max = models.IntegerField()
    y_max = models.IntegerField()
    
    def __str__(self):
        return f"{self.class_name} ({self.confidence:.2f})"
```

### 2. 마이그레이션 실행

```bash
# 마이그레이션 파일 생성
python manage.py makemigrations object_detection

# 마이그레이션 실행
python manage.py migrate
```

## 🧠 YOLO v10 핵심 연동 로직

### 1. YOLO 모델 관리 클래스 생성

```python
# object_detection/yolo_detector.py
import cv2
import numpy as np
from ultralytics import YOLO
from PIL import Image
import time
import logging
from django.conf import settings
from typing import List, Dict, Tuple, Optional
import os

logger = logging.getLogger(__name__)

class YOLODetector:
    """YOLO v10 모델을 관리하는 클래스"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        YOLO 탐지기 초기화
        
        Args:
            model_path: YOLO 모델 파일 경로
        """
        self.model_path = model_path or getattr(settings, 'YOLO_MODEL_PATH', 'yolov10n.pt')
        self.confidence_threshold = getattr(settings, 'DETECTION_CONFIDENCE', 0.25)
        self.iou_threshold = getattr(settings, 'DETECTION_IOU_THRESHOLD', 0.45)
        
        self._model = None
        self._load_model()
    
    def _load_model(self):
        """YOLO 모델 로드"""
        try:
            # 모델 파일이 존재하지 않으면 자동 다운로드
            if not os.path.exists(self.model_path):
                logger.info(f"Model not found at {self.model_path}. Downloading...")
                # Ultralytics가 자동으로 모델을 다운로드함
                self._model = YOLO('yolov10n.pt')
            else:
                self._model = YOLO(self.model_path)
            
            logger.info(f"YOLO model loaded successfully from {self.model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {str(e)}")
            raise RuntimeError(f"YOLO model loading failed: {str(e)}")
    
    def detect_objects(self, image_path: str) -> Dict:
        """
        이미지에서 객체 탐지 수행
        
        Args:
            image_path: 탐지할 이미지 파일 경로
            
        Returns:
            탐지 결과 딕셔너리
        """
        start_time = time.time()
        
        try:
            # 이미지 로드
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image from {image_path}")
            
            # YOLO 추론 실행
            results = self._model(
                image,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                verbose=False
            )
            
            # 결과 파싱
            detection_results = self._parse_results(results[0], image.shape)
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'processing_time': processing_time,
                'image_shape': image.shape,
                'detection_count': len(detection_results),
                'detections': detection_results
            }
            
        except Exception as e:
            logger.error(f"Object detection failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def _parse_results(self, result, image_shape: Tuple[int, int, int]) -> List[Dict]:
        """
        YOLO 결과를 파싱하여 표준 형식으로 변환
        
        Args:
            result: YOLO 추론 결과
            image_shape: 이미지 크기 (height, width, channels)
            
        Returns:
            탐지된 객체들의 리스트
        """
        detections = []
        height, width = image_shape[:2]
        
        if result.boxes is not None:
            boxes = result.boxes.cpu().numpy()
            
            for i, box in enumerate(boxes.data):
                x1, y1, x2, y2, confidence, class_id = box
                
                # 클래스 이름 가져오기
                class_name = self._model.names[int(class_id)]
                
                # 바운딩 박스 좌표 정규화 (YOLO 형식)
                x_center = (x1 + x2) / 2 / width
                y_center = (y1 + y2) / 2 / height
                box_width = (x2 - x1) / width
                box_height = (y2 - y1) / height
                
                detection = {
                    'class_id': int(class_id),
                    'class_name': class_name,
                    'confidence': float(confidence),
                    'bbox_normalized': {
                        'x_center': float(x_center),
                        'y_center': float(y_center),
                        'width': float(box_width),
                        'height': float(box_height)
                    },
                    'bbox_pixels': {
                        'x_min': int(x1),
                        'y_min': int(y1),
                        'x_max': int(x2),
                        'y_max': int(y2)
                    }
                }
                
                detections.append(detection)
        
        return detections
    
    def draw_detections(self, image_path: str, detections: List[Dict], 
                       output_path: str) -> bool:
        """
        탐지 결과를 이미지에 그려서 저장
        
        Args:
            image_path: 원본 이미지 경로
            detections: 탐지 결과 리스트
            output_path: 결과 이미지 저장 경로
            
        Returns:
            성공 여부
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                return False
            
            # 각 탐지 결과를 이미지에 그리기
            for detection in detections:
                bbox = detection['bbox_pixels']
                class_name = detection['class_name']
                confidence = detection['confidence']
                
                # 바운딩 박스 그리기
                cv2.rectangle(
                    image,
                    (bbox['x_min'], bbox['y_min']),
                    (bbox['x_max'], bbox['y_max']),
                    (0, 255, 0),  # 녹색
                    2
                )
                
                # 레이블 텍스트
                label = f"{class_name}: {confidence:.2f}"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                
                # 레이블 배경 그리기
                cv2.rectangle(
                    image,
                    (bbox['x_min'], bbox['y_min'] - label_size[1] - 10),
                    (bbox['x_min'] + label_size[0], bbox['y_min']),
                    (0, 255, 0),
                    -1
                )
                
                # 레이블 텍스트 그리기
                cv2.putText(
                    image,
                    label,
                    (bbox['x_min'], bbox['y_min'] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 0),
                    2
                )
            
            # 결과 이미지 저장
            success = cv2.imwrite(output_path, image)
            return success
            
        except Exception as e:
            logger.error(f"Failed to draw detections: {str(e)}")
            return False

# 전역 탐지기 인스턴스 (싱글톤 패턴)
_detector_instance = None

def get_detector() -> YOLODetector:
    """YOLO 탐지기 인스턴스 반환 (싱글톤)"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = YOLODetector()
    return _detector_instance
```

## 🌐 Django 뷰 및 API 구현

### 1. 이미지 업로드 및 탐지 뷰

```python
# object_detection/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import json
import uuid
import os
from datetime import datetime

from .models import DetectionSession, ImageDetection, DetectedObject
from .yolo_detector import get_detector
from .forms import ImageUploadForm

def index(request):
    """메인 페이지"""
    return render(request, 'object_detection/index.html')

def upload_image(request):
    """이미지 업로드 페이지"""
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # 세션 생성 또는 가져오기
            session_id = request.session.get('detection_session_id')
            if not session_id:
                session_id = str(uuid.uuid4())
                request.session['detection_session_id'] = session_id
            
            session, created = DetectionSession.objects.get_or_create(
                session_id=session_id,
                defaults={'user': request.user if request.user.is_authenticated else None}
            )
            
            # 이미지 저장
            uploaded_file = request.FILES['image']
            file_path = default_storage.save(
                f'original_images/{uuid.uuid4()}_{uploaded_file.name}',
                ContentFile(uploaded_file.read())
            )
            
            # 이미지 탐지 레코드 생성
            image_detection = ImageDetection.objects.create(
                session=session,
                original_image=file_path,
                confidence_threshold=form.cleaned_data.get('confidence', 0.25)
            )
            
            # 비동기로 탐지 수행 (Celery 사용)
            from .tasks import process_image_detection
            process_image_detection.delay(image_detection.id)
            
            messages.success(request, '이미지가 업로드되었습니다. 잠시 후 결과를 확인하세요.')
            return redirect('object_detection:detection_result', detection_id=image_detection.id)
    else:
        form = ImageUploadForm()
    
    return render(request, 'object_detection/upload.html', {'form': form})

def detection_result(request, detection_id):
    """탐지 결과 표시 페이지"""
    detection = get_object_or_404(ImageDetection, id=detection_id)
    
    # 세션 검증
    session_id = request.session.get('detection_session_id')
    if session_id != detection.session.session_id:
        messages.error(request, '접근 권한이 없습니다.')
        return redirect('object_detection:index')
    
    context = {
        'detection': detection,
        'detected_objects': detection.objects.all(),
        'detected_classes': detection.get_detected_classes(),
        'highest_confidence': detection.get_highest_confidence()
    }
    
    return render(request, 'object_detection/result.html', context)

def detection_history(request):
    """탐지 기록 페이지"""
    session_id = request.session.get('detection_session_id')
    if not session_id:
        return render(request, 'object_detection/history.html', {'detections': []})
    
    try:
        session = DetectionSession.objects.get(session_id=session_id)
        detections = session.detections.all()[:20]  # 최근 20개
    except DetectionSession.DoesNotExist:
        detections = []
    
    return render(request, 'object_detection/history.html', {'detections': detections})

# API 뷰들
@csrf_exempt
@require_http_methods(["POST"])
def api_detect_image(request):
    """API를 통한 이미지 객체 탐지"""
    try:
        if 'image' not in request.FILES:
            return JsonResponse({'error': 'No image file provided'}, status=400)
        
        uploaded_file = request.FILES['image']
        confidence = float(request.POST.get('confidence', 0.25))
        
        # 임시 파일 저장
        temp_path = default_storage.save(
            f'temp/{uuid.uuid4()}_{uploaded_file.name}',
            ContentFile(uploaded_file.read())
        )
        
        # 실제 파일 경로 가져오기
        full_path = default_storage.path(temp_path)
        
        # YOLO 탐지 수행
        detector = get_detector()
        detector.confidence_threshold = confidence
        results = detector.detect_objects(full_path)
        
        # 임시 파일 삭제
        default_storage.delete(temp_path)
        
        if results['success']:
            return JsonResponse({
                'success': True,
                'detection_count': results['detection_count'],
                'processing_time': results['processing_time'],
                'detections': results['detections']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': results.get('error', 'Unknown error occurred')
            }, status=500)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["GET"])
def api_detection_status(request, detection_id):
    """탐지 진행 상태 확인 API"""
    try:
        detection = ImageDetection.objects.get(id=detection_id)
        
        response_data = {
            'id': detection.id,
            'status': 'completed' if detection.detection_results else 'processing',
            'detection_count': detection.detection_count,
            'processing_time': detection.processing_time,
            'created_at': detection.created_at.isoformat()
        }
        
        if detection.detection_results:
            response_data['results'] = detection.detection_results
            
        return JsonResponse(response_data)
        
    except ImageDetection.DoesNotExist:
        return JsonResponse({'error': 'Detection not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def download_result_image(request, detection_id):
    """탐지 결과 이미지 다운로드"""
    detection = get_object_or_404(ImageDetection, id=detection_id)
    
    if not detection.processed_image:
        return HttpResponse('처리된 이미지가 없습니다.', status=404)
    
    # 파일 응답 생성
    response = HttpResponse(
        detection.processed_image.read(),
        content_type='image/jpeg'
    )
    response['Content-Disposition'] = f'attachment; filename="detection_result_{detection_id}.jpg"'
    
    return response
```

### 2. Django Forms 정의

```python
# object_detection/forms.py
from django import forms

class ImageUploadForm(forms.Form):
    """이미지 업로드 폼"""
    
    image = forms.ImageField(
        label='이미지 선택',
        help_text='JPG, PNG 형식의 이미지를 업로드하세요.',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    
    confidence = forms.FloatField(
        label='신뢰도 임계값',
        initial=0.25,
        min_value=0.01,
        max_value=1.0,
        help_text='0.01~1.0 사이의 값. 높을수록 더 확실한 객체만 탐지됩니다.',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        })
    )
    
    def clean_confidence(self):
        confidence = self.cleaned_data['confidence']
        if not 0.01 <= confidence <= 1.0:
            raise forms.ValidationError('신뢰도는 0.01과 1.0 사이의 값이어야 합니다.')
        return confidence
```

### 3. URL 설정

```python
# object_detection/urls.py
from django.urls import path
from . import views

app_name = 'object_detection'

urlpatterns = [
    # 웹 페이지
    path('', views.index, name='index'),
    path('upload/', views.upload_image, name='upload'),
    path('result/<int:detection_id>/', views.detection_result, name='detection_result'),
    path('history/', views.detection_history, name='history'),
    path('download/<int:detection_id>/', views.download_result_image, name='download_result'),
    
    # API 엔드포인트
    path('api/detect/', views.api_detect_image, name='api_detect'),
    path('api/status/<int:detection_id>/', views.api_detection_status, name='api_status'),
]
```

```python
# yolo_detection_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('object_detection.urls')),
]

# 개발 환경에서 미디어 파일 서빙
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

## ⚡ Celery를 활용한 비동기 처리

### 1. Celery 설정

```python
# yolo_detection_project/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Django 설정 모듈 지정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yolo_detection_project.settings')

app = Celery('yolo_detection_project')

# Django 설정에서 Celery 구성 로드
app.config_from_object('django.conf:settings', namespace='CELERY')

# 자동으로 task 발견
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
```

```python
# yolo_detection_project/__init__.py
from __future__ import absolute_import, unicode_literals

# Celery 앱이 Django와 함께 로드되도록 보장
from .celery import app as celery_app

__all__ = ('celery_app',)
```

### 2. 비동기 탐지 태스크

```python
# object_detection/tasks.py
from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import logging
import os
import uuid

from .models import ImageDetection, DetectedObject
from .yolo_detector import get_detector

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_image_detection(self, detection_id):
    """
    이미지 객체 탐지를 비동기로 처리하는 태스크
    
    Args:
        detection_id: ImageDetection 모델의 ID
    """
    try:
        # 탐지 레코드 가져오기
        detection = ImageDetection.objects.get(id=detection_id)
        
        # 원본 이미지 경로
        original_path = detection.original_image.path
        
        if not os.path.exists(original_path):
            raise FileNotFoundError(f"Original image not found: {original_path}")
        
        # YOLO 탐지 실행
        detector = get_detector()
        detector.confidence_threshold = detection.confidence_threshold
        
        results = detector.detect_objects(original_path)
        
        if not results['success']:
            raise Exception(f"Detection failed: {results.get('error', 'Unknown error')}")
        
        # 결과를 데이터베이스에 저장
        detection.detection_results = results
        detection.detection_count = results['detection_count']
        detection.processing_time = results['processing_time']
        
        # 개별 객체 레코드 생성
        for det_result in results['detections']:
            DetectedObject.objects.create(
                image_detection=detection,
                class_name=det_result['class_name'],
                confidence=det_result['confidence'],
                x_center=det_result['bbox_normalized']['x_center'],
                y_center=det_result['bbox_normalized']['y_center'],
                width=det_result['bbox_normalized']['width'],
                height=det_result['bbox_normalized']['height'],
                x_min=det_result['bbox_pixels']['x_min'],
                y_min=det_result['bbox_pixels']['y_min'],
                x_max=det_result['bbox_pixels']['x_max'],
                y_max=det_result['bbox_pixels']['y_max']
            )
        
        # 시각화된 이미지 생성
        if results['detections']:
            processed_filename = f"processed_{uuid.uuid4()}.jpg"
            processed_path = os.path.join('processed_images', processed_filename)
            full_processed_path = default_storage.path(processed_path)
            
            # 디렉토리 생성
            os.makedirs(os.path.dirname(full_processed_path), exist_ok=True)
            
            # 탐지 결과를 이미지에 그리기
            success = detector.draw_detections(
                original_path,
                results['detections'],
                full_processed_path
            )
            
            if success:
                detection.processed_image = processed_path
        
        detection.save()
        
        logger.info(f"Detection {detection_id} completed successfully. Found {results['detection_count']} objects.")
        
        return {
            'success': True,
            'detection_id': detection_id,
            'object_count': results['detection_count'],
            'processing_time': results['processing_time']
        }
        
    except ImageDetection.DoesNotExist:
        error_msg = f"ImageDetection with id {detection_id} not found"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}
        
    except Exception as e:
        error_msg = f"Error processing detection {detection_id}: {str(e)}"
        logger.error(error_msg)
        
        # 에러 상태를 데이터베이스에 기록
        try:
            detection = ImageDetection.objects.get(id=detection_id)
            detection.detection_results = {
                'success': False,
                'error': str(e),
                'detections': []
            }
            detection.save()
        except:
            pass
        
        return {'success': False, 'error': error_msg}

@shared_task
def cleanup_old_detections():
    """오래된 탐지 결과 정리 (주기적 실행용)"""
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    # 30일 이전 데이터 삭제
    cutoff_date = timezone.now() - timedelta(days=30)
    
    old_detections = ImageDetection.objects.filter(created_at__lt=cutoff_date)
    
    deleted_count = 0
    for detection in old_detections:
        # 관련 파일들 삭제
        if detection.original_image:
            default_storage.delete(detection.original_image.name)
        if detection.processed_image:
            default_storage.delete(detection.processed_image.name)
        
        detection.delete()
        deleted_count += 1
    
    logger.info(f"Cleaned up {deleted_count} old detection records")
    return deleted_count
```

## 🎨 Frontend 템플릿 구현

### 1. 기본 템플릿

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}YOLO 객체 탐지{% endblock %}</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <style>
        .detection-image {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .object-card {
            transition: transform 0.2s;
        }
        
        .object-card:hover {
            transform: translateY(-2px);
        }
        
        .confidence-bar {
            height: 8px;
            border-radius: 4px;
            background: linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #28a745 100%);
        }
        
        .loading-spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .progress-container {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1050;
            background: rgba(255, 255, 255, 0.9);
            padding: 10px;
            border-bottom: 1px solid #ddd;
            display: none;
        }
    </style>
</head>
<body>
    <!-- 진행 상태 표시 -->
    <div id="progressContainer" class="progress-container">
        <div class="container">
            <div class="d-flex align-items-center">
                <div class="loading-spinner me-2"></div>
                <span id="progressText">처리 중...</span>
            </div>
        </div>
    </div>

    <!-- 네비게이션 -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="{% url 'object_detection:index' %}">
                🎯 YOLO 객체 탐지
            </a>
            
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" 
                    data-bs-target="#navbarNav" aria-controls="navbarNav" 
                    aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{% url 'object_detection:index' %}">홈</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{% url 'object_detection:upload' %}">이미지 업로드</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{% url 'object_detection:history' %}">탐지 기록</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- 메시지 표시 -->
    {% if messages %}
        <div class="container mt-3">
            {% for message in messages %}
                <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
                    {{ message }}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            {% endfor %}
        </div>
    {% endif %}

    <!-- 메인 컨텐츠 -->
    <main class="container mt-4">
        {% block content %}
        {% endblock %}
    </main>

    <!-- Footer -->
    <footer class="bg-light mt-5 py-4">
        <div class="container">
            <div class="row">
                <div class="col-md-6">
                    <h6>YOLO v10 객체 탐지 시스템</h6>
                    <p class="text-muted">Django + YOLO v10을 활용한 실시간 객체 탐지 웹 애플리케이션</p>
                </div>
                <div class="col-md-6">
                    <h6>기술 스택</h6>
                    <p class="text-muted">Django, YOLO v10, OpenCV, Bootstrap, Celery</p>
                </div>
            </div>
        </div>
    </footer>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        // 진행 상태 표시 유틸리티
        function showProgress(text = '처리 중...') {
            document.getElementById('progressText').textContent = text;
            document.getElementById('progressContainer').style.display = 'block';
        }
        
        function hideProgress() {
            document.getElementById('progressContainer').style.display = 'none';
        }
        
        // 탐지 상태 폴링
        function pollDetectionStatus(detectionId, callback) {
            const pollInterval = setInterval(() => {
                fetch(`/api/status/${detectionId}/`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'completed') {
                            clearInterval(pollInterval);
                            hideProgress();
                            if (callback) callback(data);
                        }
                    })
                    .catch(error => {
                        console.error('Error polling status:', error);
                        clearInterval(pollInterval);
                        hideProgress();
                    });
            }, 2000); // 2초마다 확인
        }
    </script>
    
    {% block scripts %}
    {% endblock %}
</body>
</html>
```

### 2. 메인 페이지 템플릿

```html
<!-- templates/object_detection/index.html -->
{% extends 'base.html' %}

{% block title %}YOLO 객체 탐지 - 홈{% endblock %}

{% block content %}
<div class="row">
    <div class="col-lg-8 mx-auto text-center">
        <h1 class="display-4 mb-4">🎯 YOLO v10 객체 탐지</h1>
        <p class="lead mb-5">
            최신 YOLO v10 모델을 활용한 실시간 객체 탐지 웹 애플리케이션입니다. 
            이미지를 업로드하면 AI가 자동으로 객체를 인식하고 분석 결과를 제공합니다.
        </p>
        
        <div class="row mb-5">
            <div class="col-md-4 mb-3">
                <div class="card h-100">
                    <div class="card-body text-center">
                        <i class="bi bi-upload fs-1 text-primary mb-3"></i>
                        <h5 class="card-title">이미지 업로드</h5>
                        <p class="card-text">JPG, PNG 형식의 이미지를 업로드하여 객체 탐지를 수행합니다.</p>
                        <a href="{% url 'object_detection:upload' %}" class="btn btn-primary">
                            업로드하기
                        </a>
                    </div>
                </div>
            </div>
            
            <div class="col-md-4 mb-3">
                <div class="card h-100">
                    <div class="card-body text-center">
                        <i class="bi bi-eye fs-1 text-success mb-3"></i>
                        <h5 class="card-title">실시간 탐지</h5>
                        <p class="card-text">YOLO v10의 고성능 객체 탐지로 빠르고 정확한 결과를 확인하세요.</p>
                        <button class="btn btn-success" onclick="startWebcamDetection()">
                            웹캠 시작
                        </button>
                    </div>
                </div>
            </div>
            
            <div class="col-md-4 mb-3">
                <div class="card h-100">
                    <div class="card-body text-center">
                        <i class="bi bi-clock-history fs-1 text-info mb-3"></i>
                        <h5 class="card-title">탐지 기록</h5>
                        <p class="card-text">이전에 수행한 객체 탐지 결과들을 확인하고 관리할 수 있습니다.</p>
                        <a href="{% url 'object_detection:history' %}" class="btn btn-info">
                            기록 보기
                        </a>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 지원 객체 클래스 표시 -->
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">탐지 가능한 객체 클래스</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-3">
                        <strong>사람 & 동물</strong>
                        <ul class="list-unstyled mt-2">
                            <li>👤 person</li>
                            <li>🐕 dog</li>
                            <li>🐈 cat</li>
                            <li>🐎 horse</li>
                            <li>🐄 cow</li>
                        </ul>
                    </div>
                    <div class="col-md-3">
                        <strong>교통수단</strong>
                        <ul class="list-unstyled mt-2">
                            <li>🚗 car</li>
                            <li>🚛 truck</li>
                            <li>🚌 bus</li>
                            <li>🏍️ motorcycle</li>
                            <li>🚲 bicycle</li>
                        </ul>
                    </div>
                    <div class="col-md-3">
                        <strong>가구 & 물건</strong>
                        <ul class="list-unstyled mt-2">
                            <li>🪑 chair</li>
                            <li>🛋️ sofa</li>
                            <li>🛏️ bed</li>
                            <li>📺 tv</li>
                            <li>💻 laptop</li>
                        </ul>
                    </div>
                    <div class="col-md-3">
                        <strong>음식 & 기타</strong>
                        <ul class="list-unstyled mt-2">
                            <li>🍎 apple</li>
                            <li>🍌 banana</li>
                            <li>🍕 pizza</li>
                            <li>☂️ umbrella</li>
                            <li>⚽ sports ball</li>
                        </ul>
                    </div>
                </div>
                <p class="text-muted mt-3">
                    총 80개의 COCO 데이터셋 클래스를 지원합니다.
                </p>
            </div>
        </div>
    </div>
</div>

<!-- 웹캠 모달 -->
<div class="modal fade" id="webcamModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">실시간 웹캠 객체 탐지</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body text-center">
                <video id="webcamVideo" width="640" height="480" autoplay style="display: none;"></video>
                <canvas id="webcamCanvas" width="640" height="480"></canvas>
                <div id="webcamResults" class="mt-3"></div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">닫기</button>
                <button type="button" class="btn btn-primary" onclick="captureWebcamImage()">
                    📸 현재 화면 분석
                </button>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
let webcamStream = null;
let webcamVideo = null;
let webcamCanvas = null;
let webcamContext = null;

function startWebcamDetection() {
    webcamVideo = document.getElementById('webcamVideo');
    webcamCanvas = document.getElementById('webcamCanvas');
    webcamContext = webcamCanvas.getContext('2d');
    
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            webcamStream = stream;
            webcamVideo.srcObject = stream;
            webcamVideo.play();
            
            // 비디오가 로드되면 캔버스에 그리기 시작
            webcamVideo.addEventListener('loadedmetadata', () => {
                drawWebcamFrame();
            });
            
            // 모달 표시
            new bootstrap.Modal(document.getElementById('webcamModal')).show();
        })
        .catch(error => {
            console.error('웹캠 접근 오류:', error);
            alert('웹캠에 접근할 수 없습니다. 권한을 확인해주세요.');
        });
}

function drawWebcamFrame() {
    if (webcamVideo && webcamCanvas) {
        webcamContext.drawImage(webcamVideo, 0, 0, webcamCanvas.width, webcamCanvas.height);
        requestAnimationFrame(drawWebcamFrame);
    }
}

function captureWebcamImage() {
    if (!webcamCanvas) return;
    
    // 캔버스 이미지를 blob으로 변환
    webcamCanvas.toBlob(blob => {
        const formData = new FormData();
        formData.append('image', blob, 'webcam_capture.jpg');
        formData.append('confidence', '0.25');
        
        showProgress('웹캠 이미지 분석 중...');
        
        fetch('/api/detect/', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            hideProgress();
            if (data.success) {
                displayWebcamResults(data);
            } else {
                alert('분석 중 오류가 발생했습니다: ' + data.error);
            }
        })
        .catch(error => {
            hideProgress();
            console.error('분석 오류:', error);
            alert('분석 중 오류가 발생했습니다.');
        });
    }, 'image/jpeg', 0.8);
}

function displayWebcamResults(results) {
    const resultsDiv = document.getElementById('webcamResults');
    
    if (results.detection_count === 0) {
        resultsDiv.innerHTML = '<p class="text-muted">탐지된 객체가 없습니다.</p>';
        return;
    }
    
    let html = `<h6>탐지 결과: ${results.detection_count}개 객체</h6>`;
    html += '<div class="row">';
    
    results.detections.forEach(detection => {
        const confidence = (detection.confidence * 100).toFixed(1);
        html += `
            <div class="col-6 col-md-4 mb-2">
                <div class="card">
                    <div class="card-body p-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="fw-bold">${detection.class_name}</span>
                            <span class="badge bg-primary">${confidence}%</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    resultsDiv.innerHTML = html;
}

// 모달이 닫힐 때 웹캠 정리
document.getElementById('webcamModal').addEventListener('hidden.bs.modal', function () {
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        webcamStream = null;
    }
});
</script>
{% endblock %}
```

### 3. 이미지 업로드 템플릿

```html
<!-- templates/object_detection/upload.html -->
{% extends 'base.html' %}

{% block title %}이미지 업로드 - YOLO 객체 탐지{% endblock %}

{% block content %}
<div class="row">
    <div class="col-lg-8 mx-auto">
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">🖼️ 이미지 업로드 및 객체 탐지</h4>
            </div>
            <div class="card-body">
                <form method="post" enctype="multipart/form-data" id="uploadForm">
                    {% csrf_token %}
                    
                    <div class="mb-3">
                        {{ form.image.label_tag }}
                        {{ form.image }}
                        <div class="form-text">{{ form.image.help_text }}</div>
                        {% if form.image.errors %}
                            <div class="text-danger">
                                {% for error in form.image.errors %}
                                    <div>{{ error }}</div>
                                {% endfor %}
                            </div>
                        {% endif %}
                    </div>
                    
                    <div class="mb-3">
                        {{ form.confidence.label_tag }}
                        {{ form.confidence }}
                        <div class="form-text">{{ form.confidence.help_text }}</div>
                        {% if form.confidence.errors %}
                            <div class="text-danger">
                                {% for error in form.confidence.errors %}
                                    <div>{{ error }}</div>
                                {% endfor %}
                            </div>
                        {% endif %}
                    </div>
                    
                    <!-- 이미지 미리보기 -->
                    <div id="imagePreview" class="mb-3" style="display: none;">
                        <h6>미리보기:</h6>
                        <img id="previewImg" src="" alt="Preview" class="img-fluid detection-image">
                    </div>
                    
                    <div class="d-grid gap-2">
                        <button type="submit" class="btn btn-primary btn-lg" id="submitBtn">
                            🎯 객체 탐지 시작
                        </button>
                        <a href="{% url 'object_detection:index' %}" class="btn btn-outline-secondary">
                            취소
                        </a>
                    </div>
                </form>
            </div>
        </div>
        
        <!-- 사용 팁 -->
        <div class="card mt-4">
            <div class="card-header">
                <h5 class="mb-0">💡 사용 팁</h5>
            </div>
            <div class="card-body">
                <ul class="mb-0">
                    <li><strong>이미지 품질:</strong> 선명하고 밝은 이미지일수록 탐지 정확도가 높습니다.</li>
                    <li><strong>신뢰도 임계값:</strong> 낮게 설정하면 더 많은 객체를 탐지하지만 오탐이 증가할 수 있습니다.</li>
                    <li><strong>파일 크기:</strong> 너무 큰 이미지는 처리 시간이 오래 걸릴 수 있습니다.</li>
                    <li><strong>지원 형식:</strong> JPG, PNG, GIF 형식을 지원합니다.</li>
                </ul>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
// 이미지 미리보기
document.getElementById('id_image').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('previewImg').src = e.target.result;
            document.getElementById('imagePreview').style.display = 'block';
        };
        reader.readAsDataURL(file);
    } else {
        document.getElementById('imagePreview').style.display = 'none';
    }
});

// 폼 제출 시 진행 상태 표시
document.getElementById('uploadForm').addEventListener('submit', function(e) {
    const submitBtn = document.getElementById('submitBtn');
    const fileInput = document.getElementById('id_image');
    
    if (!fileInput.files.length) {
        e.preventDefault();
        alert('이미지를 선택해주세요.');
        return;
    }
    
    submitBtn.disabled = true;
    showProgress('이미지 업로드 및 분석 중...');
});
</script>
{% endblock %}
```

### 4. 탐지 결과 템플릿

```html
<!-- templates/object_detection/result.html -->
{% extends 'base.html' %}

{% block title %}탐지 결과 - YOLO 객체 탐지{% endblock %}

{% block content %}
<div class="row">
    <div class="col-12">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2>🎯 객체 탐지 결과</h2>
            <div>
                {% if detection.processed_image %}
                    <a href="{% url 'object_detection:download_result' detection.id %}" 
                       class="btn btn-success me-2">
                        📥 결과 이미지 다운로드
                    </a>
                {% endif %}
                <a href="{% url 'object_detection:upload' %}" class="btn btn-primary">
                    🔄 새로운 탐지
                </a>
            </div>
        </div>
    </div>
</div>

<!-- 탐지 상태가 처리 중인 경우 -->
{% if not detection.detection_results %}
<div id="processingStatus" class="text-center py-5">
    <div class="loading-spinner mx-auto mb-3" style="width: 50px; height: 50px;"></div>
    <h4>이미지 분석 중...</h4>
    <p class="text-muted">잠시만 기다려주세요. YOLO 모델이 이미지를 분석하고 있습니다.</p>
    <div class="progress mt-3" style="max-width: 400px; margin: 0 auto;">
        <div class="progress-bar progress-bar-striped progress-bar-animated" 
             role="progressbar" style="width: 100%"></div>
    </div>
</div>

<script>
// 처리 상태 폴링
pollDetectionStatus({{ detection.id }}, function(data) {
    location.reload(); // 완료되면 페이지 새로고침
});
</script>

{% else %}

<div class="row">
    <!-- 결과 요약 -->
    <div class="col-12 mb-4">
        <div class="row">
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h3 class="text-primary">{{ detection.detection_count }}</h3>
                        <p class="card-text">탐지된 객체 수</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h3 class="text-success">{{ highest_confidence|floatformat:1 }}%</h3>
                        <p class="card-text">최고 신뢰도</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h3 class="text-info">{{ detection.processing_time|floatformat:2 }}s</h3>
                        <p class="card-text">처리 시간</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h3 class="text-warning">{{ detected_classes|length }}</h3>
                        <p class="card-text">클래스 종류</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 이미지 비교 -->
    <div class="col-lg-6 mb-4">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">원본 이미지</h5>
            </div>
            <div class="card-body text-center">
                <img src="{{ detection.original_image.url }}" 
                     alt="Original Image" class="detection-image">
            </div>
        </div>
    </div>
    
    <div class="col-lg-6 mb-4">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">탐지 결과</h5>
            </div>
            <div class="card-body text-center">
                {% if detection.processed_image %}
                    <img src="{{ detection.processed_image.url }}" 
                         alt="Processed Image" class="detection-image">
                {% else %}
                    <div class="py-5 text-muted">
                        <i class="bi bi-image fs-1"></i>
                        <p>처리된 이미지가 없습니다.</p>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
    
    <!-- 탐지된 객체 목록 -->
    {% if detected_objects %}
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">탐지된 객체 상세 정보</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    {% for obj in detected_objects %}
                    <div class="col-lg-4 col-md-6 mb-3">
                        <div class="card object-card h-100">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <h6 class="card-title text-capitalize">{{ obj.class_name }}</h6>
                                    <span class="badge bg-primary">{{ obj.confidence|floatformat:1 }}%</span>
                                </div>
                                
                                <!-- 신뢰도 바 -->
                                <div class="confidence-bar mb-2">
                                    <div style="width: {{ obj.confidence|floatformat:0 }}%; height: 100%; 
                                                background: {% if obj.confidence > 0.7 %}#28a745{% elif obj.confidence > 0.4 %}#ffc107{% else %}#dc3545{% endif %};">
                                    </div>
                                </div>
                                
                                <!-- 바운딩 박스 정보 -->
                                <small class="text-muted">
                                    <div>위치: ({{ obj.x_min }}, {{ obj.y_min }})</div>
                                    <div>크기: {{ obj.x_max|add:"-obj.x_min" }} × {{ obj.y_max|add:"-obj.y_min" }}</div>
                                </small>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
    {% endif %}
    
    <!-- 클래스별 통계 차트 -->
    {% if detected_classes %}
    <div class="col-lg-6 mt-4">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">클래스별 탐지 수량</h5>
            </div>
            <div class="card-body">
                <canvas id="classChart" width="400" height="200"></canvas>
            </div>
        </div>
    </div>
    {% endif %}
    
    <!-- 신뢰도 분포 차트 -->
    {% if detected_objects %}
    <div class="col-lg-6 mt-4">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">신뢰도 분포</h5>
            </div>
            <div class="card-body">
                <canvas id="confidenceChart" width="400" height="200"></canvas>
            </div>
        </div>
    </div>
    {% endif %}
</div>

{% endif %}
{% endblock %}

{% block scripts %}
{% if detected_objects %}
<script>
// 클래스별 통계 차트
const classData = {};
{% for obj in detected_objects %}
    const className = '{{ obj.class_name }}';
    classData[className] = (classData[className] || 0) + 1;
{% endfor %}

if (Object.keys(classData).length > 0) {
    const classCtx = document.getElementById('classChart').getContext('2d');
    new Chart(classCtx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(classData),
            datasets: [{
                data: Object.values(classData),
                backgroundColor: [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
                    '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// 신뢰도 분포 차트
const confidenceRanges = {'0.0-0.3': 0, '0.3-0.5': 0, '0.5-0.7': 0, '0.7-0.9': 0, '0.9-1.0': 0};
{% for obj in detected_objects %}
    const conf = {{ obj.confidence }};
    if (conf < 0.3) confidenceRanges['0.0-0.3']++;
    else if (conf < 0.5) confidenceRanges['0.3-0.5']++;
    else if (conf < 0.7) confidenceRanges['0.5-0.7']++;
    else if (conf < 0.9) confidenceRanges['0.7-0.9']++;
    else confidenceRanges['0.9-1.0']++;
{% endfor %}

const confCtx = document.getElementById('confidenceChart').getContext('2d');
new Chart(confCtx, {
    type: 'bar',
    data: {
        labels: Object.keys(confidenceRanges),
        datasets: [{
            label: '객체 수',
            data: Object.values(confidenceRanges),
            backgroundColor: '#36A2EB',
            borderColor: '#36A2EB',
            borderWidth: 1
        }]
    },
    options: {
        responsive: true,
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    stepSize: 1
                }
            }
        },
        plugins: {
            legend: {
                display: false
            }
        }
    }
});
</script>
{% endif %}
{% endblock %}
```

## 🔧 Django 관리자 설정

### 1. Admin 인터페이스 구성

```python
# object_detection/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json

from .models import DetectionSession, ImageDetection, DetectedObject

@admin.register(DetectionSession)
class DetectionSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'detection_count', 'created_at', 'updated_at')
    list_filter = ('created_at', 'user')
    search_fields = ('session_id', 'user__username')
    readonly_fields = ('session_id', 'created_at', 'updated_at')
    
    def detection_count(self, obj):
        return obj.detections.count()
    detection_count.short_description = '탐지 수행 횟수'

class DetectedObjectInline(admin.TabularInline):
    model = DetectedObject
    extra = 0
    readonly_fields = ('class_name', 'confidence', 'x_center', 'y_center', 
                      'width', 'height', 'x_min', 'y_min', 'x_max', 'y_max')

@admin.register(ImageDetection)
class ImageDetectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'detection_count', 'processing_time', 
                   'confidence_threshold', 'image_preview', 'created_at')
    list_filter = ('created_at', 'detection_count', 'confidence_threshold')
    search_fields = ('session__session_id', 'session__user__username')
    readonly_fields = ('detection_results_display', 'created_at', 'image_preview', 
                      'processed_image_preview')
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('session', 'confidence_threshold', 'detection_count', 
                      'processing_time', 'created_at')
        }),
        ('이미지', {
            'fields': ('original_image', 'image_preview', 'processed_image', 
                      'processed_image_preview')
        }),
        ('탐지 결과', {
            'fields': ('detection_results_display',)
        }),
    )
    
    inlines = [DetectedObjectInline]
    
    def image_preview(self, obj):
        if obj.original_image:
            return format_html(
                '<img src="{}" style="max-width: 150px; max-height: 150px;" />',
                obj.original_image.url
            )
        return "이미지 없음"
    image_preview.short_description = '원본 이미지 미리보기'
    
    def processed_image_preview(self, obj):
        if obj.processed_image:
            return format_html(
                '<img src="{}" style="max-width: 150px; max-height: 150px;" />',
                obj.processed_image.url
            )
        return "처리된 이미지 없음"
    processed_image_preview.short_description = '처리된 이미지 미리보기'
    
    def detection_results_display(self, obj):
        if obj.detection_results:
            formatted_json = json.dumps(obj.detection_results, indent=2, ensure_ascii=False)
            return format_html('<pre>{}</pre>', formatted_json)
        return "결과 없음"
    detection_results_display.short_description = '탐지 결과 (JSON)'

@admin.register(DetectedObject)
class DetectedObjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'image_detection', 'class_name', 'confidence', 
                   'bbox_info', 'detection_date')
    list_filter = ('class_name', 'image_detection__created_at')
    search_fields = ('class_name', 'image_detection__session__session_id')
    readonly_fields = ('image_detection', 'class_name', 'confidence', 
                      'x_center', 'y_center', 'width', 'height',
                      'x_min', 'y_min', 'x_max', 'y_max')
    
    def bbox_info(self, obj):
        return f"({obj.x_min}, {obj.y_min}) - ({obj.x_max}, {obj.y_max})"
    bbox_info.short_description = '바운딩 박스'
    
    def detection_date(self, obj):
        return obj.image_detection.created_at
    detection_date.short_description = '탐지 날짜'
    detection_date.admin_order_field = 'image_detection__created_at'

# 관리자 사이트 커스터마이징
admin.site.site_header = 'YOLO 객체 탐지 관리'
admin.site.site_title = 'YOLO 관리'
admin.site.index_title = 'YOLO 객체 탐지 시스템 관리'
```

## 🚀 애플리케이션 실행 및 테스트

### 1. 개발 환경에서 실행하기

```bash
# 데이터베이스 마이그레이션
python manage.py makemigrations
python manage.py migrate

# 슈퍼유저 생성 (관리자 페이지 접근용)
python manage.py createsuperuser

# 정적 파일 수집
python manage.py collectstatic

# 개발 서버 시작
python manage.py runserver
```

### 2. Celery 워커 실행 (별도 터미널)

```bash
# Redis 서버 시작 (별도 터미널에서)
redis-server

# Celery 워커 시작 (개발 환경)
celery -A yolo_detection_project worker --loglevel=info

# Celery 모니터링 (선택사항)
celery -A yolo_detection_project flower
```

### 3. 테스트 이미지로 검증

```python
# test_detection.py - 간단한 테스트 스크립트
import os
import django

# Django 설정 초기화
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yolo_detection_project.settings')
django.setup()

from object_detection.yolo_detector import get_detector
import requests
from PIL import Image
import io

def test_yolo_detection():
    """YOLO 탐지 기능 테스트"""
    # 테스트용 이미지 다운로드
    test_image_url = "https://ultralytics.com/images/bus.jpg"
    response = requests.get(test_image_url)
    
    # 이미지 저장
    test_image_path = "test_image.jpg"
    with open(test_image_path, 'wb') as f:
        f.write(response.content)
    
    # YOLO 탐지 수행
    detector = get_detector()
    results = detector.detect_objects(test_image_path)
    
    print("=== YOLO 탐지 테스트 결과 ===")
    print(f"성공 여부: {results['success']}")
    print(f"탐지된 객체 수: {results.get('detection_count', 0)}")
    print(f"처리 시간: {results.get('processing_time', 0):.2f}초")
    
    if results['success'] and results.get('detections'):
        print("\n탐지된 객체들:")
        for i, detection in enumerate(results['detections'], 1):
            print(f"{i}. {detection['class_name']}: {detection['confidence']:.2f}")
    
    # 시각화된 결과 이미지 생성
    if results['success']:
        output_path = "test_result.jpg"
        success = detector.draw_detections(test_image_path, results['detections'], output_path)
        if success:
            print(f"\n결과 이미지가 저장되었습니다: {output_path}")
    
    # 테스트 파일 정리
    os.remove(test_image_path)

if __name__ == "__main__":
    test_yolo_detection()
```

## ⚡ 성능 최적화 가이드

### 1. YOLO 모델 최적화

```python
# object_detection/optimizations.py
import torch
from ultralytics import YOLO
import numpy as np
from django.conf import settings
from django.core.cache import cache
import hashlib

class OptimizedYOLODetector:
    """성능 최적화된 YOLO 탐지기"""
    
    def __init__(self, model_path=None):
        self.model_path = model_path or getattr(settings, 'YOLO_MODEL_PATH', 'yolov10n.pt')
        self.device = self._get_optimal_device()
        self.model = self._load_optimized_model()
        
    def _get_optimal_device(self):
        """최적의 디바이스 선택"""
        if torch.cuda.is_available():
            return 'cuda'
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return 'mps'  # Apple Silicon
        else:
            return 'cpu'
    
    def _load_optimized_model(self):
        """최적화된 모델 로드"""
        model = YOLO(self.model_path)
        
        # GPU 사용 시 반정밀도 모드 활성화
        if self.device == 'cuda':
            model.model.half()  # FP16 모드
            
        return model
    
    def detect_with_cache(self, image_path, confidence=0.25):
        """캐시를 활용한 탐지 (동일 이미지 재탐지 방지)"""
        # 이미지 해시 생성
        with open(image_path, 'rb') as f:
            image_hash = hashlib.md5(f.read()).hexdigest()
        
        cache_key = f"yolo_detection_{image_hash}_{confidence}"
        
        # 캐시에서 결과 확인
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # 새로운 탐지 수행
        results = self.detect_objects(image_path, confidence)
        
        # 성공한 결과만 캐시에 저장 (1시간)
        if results.get('success'):
            cache.set(cache_key, results, 3600)
        
        return results
    
    def batch_detect(self, image_paths, confidence=0.25):
        """배치 탐지 (여러 이미지 동시 처리)"""
        # 배치 크기 설정 (메모리에 따라 조정)
        batch_size = 4 if self.device == 'cuda' else 2
        
        results = []
        for i in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[i:i + batch_size]
            batch_results = self.model(
                batch_paths,
                conf=confidence,
                device=self.device,
                verbose=False
            )
            
            for j, result in enumerate(batch_results):
                parsed_result = self._parse_results(result, batch_paths[j])
                results.append(parsed_result)
        
        return results

# settings.py에 추가할 최적화 설정
"""
# 캐시 설정 (Redis 사용)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# YOLO 최적화 설정
YOLO_OPTIMIZATION = {
    'USE_CACHE': True,
    'BATCH_SIZE': 4,
    'MAX_IMAGE_SIZE': 1280,  # 최대 이미지 크기
    'ENABLE_TensorRT': False,  # TensorRT 최적화 (NVIDIA GPU)
}
"""
```

### 2. 이미지 전처리 최적화

```python
# object_detection/image_utils.py
from PIL import Image, ImageOps
import cv2
import numpy as np
from django.conf import settings

class ImageOptimizer:
    """이미지 전처리 최적화"""
    
    @staticmethod
    def optimize_for_detection(image_path, max_size=1280):
        """탐지용 이미지 최적화"""
        with Image.open(image_path) as img:
            # EXIF 정보 기반 자동 회전
            img = ImageOps.exif_transpose(img)
            
            # RGB 변환 (YOLO는 RGB 입력 필요)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 크기 조정 (비율 유지)
            original_size = img.size
            if max(original_size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # 임시 파일로 저장
            optimized_path = image_path.replace('.', '_optimized.')
            img.save(optimized_path, 'JPEG', quality=90, optimize=True)
            
            return optimized_path, img.size
    
    @staticmethod
    def preprocess_webcam_frame(frame, target_size=(640, 640)):
        """웹캠 프레임 전처리"""
        # 크기 조정
        resized = cv2.resize(frame, target_size)
        
        # 색공간 변환 (BGR to RGB)
        rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        return rgb_frame
```

### 3. 데이터베이스 최적화

```python
# object_detection/models.py 최적화된 버전에 추가
class ImageDetection(models.Model):
    # ... 기존 필드들 ...
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['detection_count']),
            models.Index(fields=['created_at']),
        ]

class DetectedObject(models.Model):
    # ... 기존 필드들 ...
    
    class Meta:
        indexes = [
            models.Index(fields=['class_name', 'confidence']),
            models.Index(fields=['image_detection', 'class_name']),
        ]
```

## 🌐 프로덕션 배포 가이드

### 1. Docker를 활용한 배포

```dockerfile
# Dockerfile
FROM python:3.9-slim

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 정적 파일 수집
RUN python manage.py collectstatic --noinput

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "yolo_detection_project.wsgi:application"]
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
      - DEBUG=False
      - SECRET_KEY=your-production-secret-key
    depends_on:
      - redis
      - db
    volumes:
      - media_volume:/app/media
      - static_volume:/app/staticfiles

  celery:
    build: .
    command: celery -A yolo_detection_project worker --loglevel=info
    depends_on:
      - redis
      - db
    volumes:
      - media_volume:/app/media

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: yolo_detection
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: your-db-password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    depends_on:
      - web

volumes:
  postgres_data:
  media_volume:
  static_volume:
```

### 2. 프로덕션 설정

```python
# settings/production.py
from .base import *
import os

DEBUG = False

ALLOWED_HOSTS = ['your-domain.com', '0.0.0.0']

# 데이터베이스 (PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'yolo_detection'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# 보안 설정
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/app/logs/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'object_detection': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Celery 프로덕션 설정
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_WORKER_CONCURRENCY = 2
CELERY_TASK_SOFT_TIME_LIMIT = 300  # 5분
CELERY_TASK_TIME_LIMIT = 600  # 10분
```

## 🎯 마무리 및 향후 개선 방향

### 구현 완료된 기능들
- ✅ Django 프로젝트 기본 설정
- ✅ YOLO v10 모델 연동
- ✅ 이미지 업로드 및 객체 탐지
- ✅ 실시간 웹캠 탐지
- ✅ 비동기 처리 (Celery)
- ✅ RESTful API
- ✅ 관리자 인터페이스
- ✅ 반응형 웹 UI
- ✅ 탐지 결과 시각화

### 추가 개선 가능한 기능들
1. **실시간 스트리밍**: WebRTC를 활용한 실시간 비디오 스트리밍 탐지
2. **사용자 인증**: 개인별 탐지 기록 관리
3. **커스텀 모델**: 특정 도메인에 특화된 모델 학습 및 적용
4. **API 키 관리**: 외부 서비스를 위한 API 키 시스템
5. **성능 모니터링**: 실시간 성능 지표 대시보드
6. **다중 모델 지원**: YOLO 외 다른 객체 탐지 모델 연동

이 가이드를 통해 Django와 YOLO v10을 성공적으로 연동하여 강력한 객체 탐지 웹 애플리케이션을 구축할 수 있습니다. 단계별로 천천히 따라하시면서 본인의 프로젝트 요구사항에 맞게 커스터마이징해보세요! 🚀
