---
layout: post
title: "FastAPI + YOLOv10 객체 탐지 API를 Railway에 배포하기: 완벽 가이드"
date: 2025-08-05 10:00:00 +0900
categories: [FastAPI, YOLOv10, Deployment, Railway]
tags: [FastAPI, YOLOv10, Railway, Docker, Computer Vision, Object Detection, Python, API, Cloud Deployment]
---

컴퓨터 비전 애플리케이션을 클라우드에 배포하는 것은 복잡할 수 있지만, FastAPI와 YOLOv10의 조합으로 Railway에 배포하면 간단하고 효율적인 객체 탐지 API를 만들 수 있습니다. 이 글에서는 처음부터 끝까지 전체 과정을 단계별로 설명하겠습니다.

## 🎯 프로젝트 개요

### 구현할 기능
- YOLOv10을 사용한 실시간 객체 탐지
- FastAPI 기반의 REST API
- 이미지 업로드 및 탐지 결과 반환
- Railway 플랫폼을 통한 클라우드 배포

### 기술 스택
```
┌─────────────────┐    HTTP API    ┌──────────────────┐
│   Frontend      │  ←──────────→  │    FastAPI       │
│   (Client)      │                │   + YOLOv10      │
├─────────────────┤                ├──────────────────┤
│ • Web UI        │                │ • Object         │
│ • Mobile App    │                │   Detection      │
│ • API Client    │                │ • Image Process  │
└─────────────────┘                └──────────────────┘
                                           │
                                           ▼
                                   ┌──────────────────┐
                                   │    Railway       │
                                   │   (Cloud)        │
                                   └──────────────────┘
```

## 🛠️ 1. 프로젝트 설정 및 환경 구성

### 프로젝트 구조
```
fastapi-yolov10-api/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── yolo_model.py
│   ├── routers/
│   │   ├── __init__.py
│   │   └── detection.py
│   └── utils/
│       ├── __init__.py
│       └── image_processing.py
├── requirements.txt
├── Dockerfile
├── railway.toml
└── README.md
```

### requirements.txt 작성
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
pillow==10.1.0
opencv-python-headless==4.8.1.78
numpy==1.24.3
torch==2.1.1
torchvision==0.16.1
ultralytics==8.0.206
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

## 🧠 2. YOLOv10 모델 구현

### models/yolo_model.py
```python
import torch
from ultralytics import YOLO
import numpy as np
from PIL import Image
import io
import cv2
from typing import List, Dict, Any

class YOLOv10Detector:
    def __init__(self, model_path: str = "yolov10n.pt"):
        """
        YOLOv10 탐지기 초기화
        
        Args:
            model_path: YOLOv10 모델 파일 경로
        """
        self.model = YOLO(model_path)
        self.model_path = model_path
        
    def detect_objects(self, image: Image.Image, confidence: float = 0.5) -> Dict[str, Any]:
        """
        이미지에서 객체 탐지 수행
        
        Args:
            image: PIL Image 객체
            confidence: 신뢰도 임계값
            
        Returns:
            탐지 결과 딕셔너리
        """
        try:
            # PIL Image를 numpy array로 변환
            img_array = np.array(image)
            
            # BGR로 변환 (OpenCV 형식)
            if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # YOLOv10으로 추론 실행
            results = self.model(img_array, conf=confidence)
            
            # 결과 파싱
            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        detection = {
                            "class_id": int(box.cls.item()),
                            "class_name": self.model.names[int(box.cls.item())],
                            "confidence": float(box.conf.item()),
                            "bbox": {
                                "x1": float(box.xyxy[0][0].item()),
                                "y1": float(box.xyxy[0][1].item()),
                                "x2": float(box.xyxy[0][2].item()),
                                "y2": float(box.xyxy[0][3].item())
                            }
                        }
                        detections.append(detection)
            
            return {
                "success": True,
                "detections": detections,
                "count": len(detections),
                "image_size": {
                    "width": image.width,
                    "height": image.height
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "detections": [],
                "count": 0
            }
    
    def draw_detections(self, image: Image.Image, detections: List[Dict]) -> Image.Image:
        """
        탐지 결과를 이미지에 그리기
        
        Args:
            image: 원본 PIL Image
            detections: 탐지 결과 리스트
            
        Returns:
            탐지 결과가 그려진 PIL Image
        """
        img_array = np.array(image)
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        for detection in detections:
            bbox = detection["bbox"]
            class_name = detection["class_name"]
            confidence = detection["confidence"]
            
            # 바운딩 박스 그리기
            cv2.rectangle(
                img_array,
                (int(bbox["x1"]), int(bbox["y1"])),
                (int(bbox["x2"]), int(bbox["y2"])),
                (0, 255, 0),
                2
            )
            
            # 클래스명과 신뢰도 텍스트 추가
            label = f"{class_name}: {confidence:.2f}"
            cv2.putText(
                img_array,
                label,
                (int(bbox["x1"]), int(bbox["y1"]) - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )
        
        # BGR을 RGB로 변환하여 PIL Image로 반환
        img_array = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
        return Image.fromarray(img_array)

# 전역 모델 인스턴스
detector = None

def get_detector() -> YOLOv10Detector:
    """YOLOv10 탐지기 인스턴스 반환 (싱글톤 패턴)"""
    global detector
    if detector is None:
        detector = YOLOv10Detector()
    return detector
```

### utils/image_processing.py
```python
from PIL import Image
import io
from typing import Optional
import base64

def validate_image(file_content: bytes) -> Optional[Image.Image]:
    """
    이미지 파일 유효성 검사 및 PIL Image 객체 반환
    
    Args:
        file_content: 이미지 파일 바이트 데이터
        
    Returns:
        PIL Image 객체 또는 None
    """
    try:
        image = Image.open(io.BytesIO(file_content))
        
        # RGBA를 RGB로 변환 (투명도 제거)
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
            
        return image
    except Exception:
        return None

def resize_image(image: Image.Image, max_size: int = 1024) -> Image.Image:
    """
    이미지 크기 조정 (최대 크기 제한)
    
    Args:
        image: PIL Image 객체
        max_size: 최대 크기 (픽셀)
        
    Returns:
        크기 조정된 PIL Image 객체
    """
    width, height = image.size
    
    if max(width, height) > max_size:
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    return image

def image_to_base64(image: Image.Image, format: str = "JPEG") -> str:
    """
    PIL Image를 base64 문자열로 변환
    
    Args:
        image: PIL Image 객체
        format: 이미지 포맷 (JPEG, PNG 등)
        
    Returns:
        base64 인코딩된 이미지 문자열
    """
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/{format.lower()};base64,{img_str}"
```

## 🚀 3. FastAPI 애플리케이션 구현

### routers/detection.py
```python
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
import time

from ..models.yolo_model import get_detector
from ..utils.image_processing import validate_image, resize_image, image_to_base64

router = APIRouter(prefix="/api/v1", tags=["Object Detection"])

@router.post("/detect")
async def detect_objects(
    file: UploadFile = File(...),
    confidence: float = Query(0.5, ge=0.1, le=1.0, description="신뢰도 임계값"),
    draw_boxes: bool = Query(True, description="탐지 결과를 이미지에 그릴지 여부"),
    max_size: int = Query(1024, ge=512, le=2048, description="이미지 최대 크기")
):
    """
    이미지에서 객체 탐지 수행
    
    Args:
        file: 업로드할 이미지 파일
        confidence: 탐지 신뢰도 임계값 (0.1 ~ 1.0)
        draw_boxes: 탐지 결과를 이미지에 그릴지 여부
        max_size: 처리할 이미지의 최대 크기
        
    Returns:
        탐지 결과 JSON
    """
    start_time = time.time()
    
    # 파일 타입 검증
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")
    
    try:
        # 이미지 읽기 및 검증
        file_content = await file.read()
        image = validate_image(file_content)
        
        if image is None:
            raise HTTPException(status_code=400, detail="유효하지 않은 이미지 파일입니다.")
        
        # 이미지 크기 조정
        image = resize_image(image, max_size)
        
        # 객체 탐지 수행
        detector = get_detector()
        detection_result = detector.detect_objects(image, confidence)
        
        if not detection_result["success"]:
            raise HTTPException(status_code=500, detail=f"탐지 실패: {detection_result['error']}")
        
        # 응답 데이터 구성
        response_data = {
            "success": True,
            "filename": file.filename,
            "processing_time": round(time.time() - start_time, 3),
            "detections": detection_result["detections"],
            "detection_count": detection_result["count"],
            "image_info": detection_result["image_size"],
            "parameters": {
                "confidence_threshold": confidence,
                "max_image_size": max_size
            }
        }
        
        # 탐지 결과가 그려진 이미지 추가 (옵션)
        if draw_boxes and detection_result["detections"]:
            annotated_image = detector.draw_detections(image, detection_result["detections"])
            response_data["annotated_image"] = image_to_base64(annotated_image)
        
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

@router.get("/health")
async def health_check():
    """API 상태 확인"""
    try:
        detector = get_detector()
        return {
            "status": "healthy",
            "model_loaded": detector is not None,
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

@router.get("/model-info")
async def get_model_info():
    """모델 정보 반환"""
    try:
        detector = get_detector()
        return {
            "model_path": detector.model_path,
            "class_names": list(detector.model.names.values()),
            "class_count": len(detector.model.names)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 정보 조회 실패: {str(e)}")
```

### main.py
```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import uvicorn
import os

from .routers import detection
from .models.yolo_model import get_detector

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 코드"""
    # 시작 시: 모델 로드
    print("🚀 FastAPI 서버 시작 중...")
    try:
        detector = get_detector()
        print("✅ YOLOv10 모델 로드 완료")
    except Exception as e:
        print(f"❌ 모델 로드 실패: {e}")
        raise
    
    yield
    
    # 종료 시: 정리 작업
    print("🛑 FastAPI 서버 종료 중...")

# FastAPI 앱 생성
app = FastAPI(
    title="YOLOv10 Object Detection API",
    description="FastAPI와 YOLOv10을 사용한 객체 탐지 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(detection.router)

@app.get("/", response_class=HTMLResponse)
async def root():
    """메인 페이지"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>YOLOv10 Object Detection API</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .container { text-align: center; }
            .upload-area { border: 2px dashed #ccc; padding: 40px; margin: 20px 0; }
            .result { margin-top: 20px; text-align: left; }
            img { max-width: 100%; height: auto; margin: 10px 0; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
            button:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 YOLOv10 Object Detection API</h1>
            <p>이미지를 업로드하여 객체 탐지를 수행하세요.</p>
            
            <div class="upload-area">
                <input type="file" id="fileInput" accept="image/*" style="display: none;">
                <button onclick="document.getElementById('fileInput').click()">이미지 선택</button>
                <button onclick="detectObjects()" id="detectBtn" disabled>객체 탐지</button>
            </div>
            
            <div id="result" class="result"></div>
        </div>

        <script>
            let selectedFile = null;
            
            document.getElementById('fileInput').addEventListener('change', function(e) {
                selectedFile = e.target.files[0];
                document.getElementById('detectBtn').disabled = !selectedFile;
                if (selectedFile) {
                    document.querySelector('.upload-area').innerHTML += 
                        `<p>선택된 파일: ${selectedFile.name}</p>`;
                }
            });
            
            async function detectObjects() {
                if (!selectedFile) return;
                
                const formData = new FormData();
                formData.append('file', selectedFile);
                formData.append('confidence', '0.5');
                formData.append('draw_boxes', 'true');
                
                document.getElementById('result').innerHTML = '<p>탐지 중...</p>';
                
                try {
                    const response = await fetch('/api/v1/detect', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        let html = `
                            <h3>탐지 결과</h3>
                            <p>탐지된 객체 수: ${result.detection_count}</p>
                            <p>처리 시간: ${result.processing_time}초</p>
                        `;
                        
                        if (result.annotated_image) {
                            html += `<img src="${result.annotated_image}" alt="탐지 결과">`;
                        }
                        
                        if (result.detections.length > 0) {
                            html += '<h4>탐지된 객체:</h4><ul>';
                            result.detections.forEach(det => {
                                html += `<li>${det.class_name} (신뢰도: ${det.confidence.toFixed(3)})</li>`;
                            });
                            html += '</ul>';
                        }
                        
                        document.getElementById('result').innerHTML = html;
                    } else {
                        document.getElementById('result').innerHTML = '<p>탐지 실패</p>';
                    }
                } catch (error) {
                    document.getElementById('result').innerHTML = `<p>오류: ${error.message}</p>`;
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
```

## 🐳 4. Docker 컨테이너화

### Dockerfile
```dockerfile
# Python 3.11 slim 이미지 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 라이브러리 설치
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgthread-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python 종속성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# YOLOv10 모델 다운로드 (선택사항 - 런타임에 자동 다운로드됨)
# RUN python -c "from ultralytics import YOLO; YOLO('yolov10n.pt')"

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["python", "-m", "app.main"]
```

### .dockerignore
```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis

.DS_Store
.vscode
.idea
*.swp
*.swo

README.md
.gitignore
```

## 🚂 5. Railway 배포 설정

### railway.toml
```toml
[build]
builder = "DOCKERFILE"
dockerfile = "Dockerfile"

[deploy]
startCommand = "python -m app.main"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

[env]
PORT = "8000"
PYTHONPATH = "/app"
```

## 🌐 6. Railway 배포 과정

### 6.1 Railway 계정 설정
```bash
# Railway CLI 설치
npm install -g @railway/cli

# Railway 로그인
railway login

# 새 프로젝트 생성
railway new
```

### 6.2 환경 변수 설정
Railway 대시보드에서 다음 환경 변수를 설정합니다:

```env
PORT=8000
PYTHONPATH=/app
RAILWAY_STATIC_URL=your-app-url.railway.app
```

### 6.3 배포 실행
```bash
# Git 저장소 초기화 (필요한 경우)
git init
git add .
git commit -m "Initial commit"

# Railway 프로젝트와 연결
railway link

# 배포
railway up
```

## 🔧 7. 성능 최적화 및 모니터링

### 메모리 사용량 최적화
```python
# app/models/yolo_model.py에 추가
import gc
import torch

class YOLOv10Detector:
    def __init__(self, model_path: str = "yolov10n.pt"):
        # GPU 사용 가능 시 CUDA 사용
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = YOLO(model_path)
        self.model.to(self.device)
        
        # 메모리 효율성을 위한 설정
        if self.device == 'cuda':
            torch.cuda.empty_cache()
    
    def detect_objects(self, image, confidence=0.5):
        try:
            # 추론 실행
            with torch.no_grad():
                results = self.model(image, conf=confidence, device=self.device)
            
            # 메모리 정리
            if self.device == 'cuda':
                torch.cuda.empty_cache()
            gc.collect()
            
            # ... 나머지 코드
        except Exception as e:
            # 오류 발생 시 메모리 정리
            if self.device == 'cuda':
                torch.cuda.empty_cache()
            gc.collect()
            raise e
```

### 로깅 설정
```python
# main.py에 추가
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    return response
```

## 🧪 8. API 테스트

### 테스트 스크립트 (test_api.py)
```python
import requests
import base64
from PIL import Image
import io

def test_detection_api(image_path: str, api_url: str = "http://localhost:8000"):
    """
    객체 탐지 API 테스트
    
    Args:
        image_path: 테스트할 이미지 파일 경로
        api_url: API 서버 URL
    """
    
    # 이미지 파일 읽기
    with open(image_path, 'rb') as f:
        files = {'file': f}
        params = {
            'confidence': 0.5,
            'draw_boxes': True,
            'max_size': 1024
        }
        
        response = requests.post(
            f"{api_url}/api/v1/detect",
            files=files,
            params=params
        )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 탐지 성공!")
        print(f"📊 탐지된 객체 수: {result['detection_count']}")
        print(f"⏱️ 처리 시간: {result['processing_time']}초")
        
        for i, detection in enumerate(result['detections']):
            print(f"🎯 객체 {i+1}: {detection['class_name']} "
                  f"(신뢰도: {detection['confidence']:.3f})")
        
        # 결과 이미지 저장 (있는 경우)
        if 'annotated_image' in result:
            img_data = result['annotated_image'].split(',')[1]
            img_bytes = base64.b64decode(img_data)
            img = Image.open(io.BytesIO(img_bytes))
            img.save('detection_result.jpg')
            print("💾 결과 이미지 저장: detection_result.jpg")
    
    else:
        print(f"❌ API 호출 실패: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    # 로컬 테스트
    test_detection_api("test_image.jpg", "http://localhost:8000")
    
    # Railway 배포 테스트 (URL을 실제 배포 URL로 변경)
    # test_detection_api("test_image.jpg", "https://your-app.railway.app")
```

### curl을 사용한 테스트
```bash
# 건강 상태 확인
curl -X GET "https://your-app.railway.app/api/v1/health"

# 객체 탐지 API 테스트
curl -X POST "https://your-app.railway.app/api/v1/detect" \
     -F "file=@test_image.jpg" \
     -F "confidence=0.5" \
     -F "draw_boxes=true"
```

## 📊 9. 모니터링 및 유지보수

### Railway 대시보드 모니터링
Railway 대시보드에서 다음 메트릭을 모니터링할 수 있습니다:

- **CPU 사용률**: YOLOv10 추론 중 높은 CPU 사용률 확인
- **메모리 사용량**: 모델 로딩 시 메모리 스파이크 모니터링
- **응답 시간**: API 응답 시간 추적
- **요청 수**: 트래픽 패턴 분석

### 로그 모니터링
```bash
# Railway CLI로 실시간 로그 확인
railway logs --follow

# 특정 시간대 로그 확인
railway logs --since 1h
```

## 🔒 10. 보안 및 최적화

### API 키 인증 추가
```python
# main.py에 추가
from fastapi import Header, HTTPException
import os

API_KEY = os.environ.get("API_KEY", "your-secret-api-key")

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

# 보호된 엔드포인트에 의존성 추가
@router.post("/detect")
async def detect_objects(
    api_key: str = Depends(verify_api_key),  # 추가
    file: UploadFile = File(...),
    # ... 나머지 매개변수
):
    # ... 기존 코드
```

### 요청 제한 (Rate Limiting)
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/detect")
@limiter.limit("10/minute")  # 분당 10회 제한
async def detect_objects(request: Request, ...):
    # ... 기존 코드
```

## 🎉 결론

FastAPI와 YOLOv10을 Railway에 배포하면 다음과 같은 이점을 얻을 수 있습니다:

### ✅ 장점
- **간편한 배포**: Railway의 Git 기반 자동 배포
- **확장성**: 트래픽에 따른 자동 스케일링
- **비용 효율성**: 사용량 기반 과금
- **높은 성능**: YOLOv10의 빠른 추론 속도
- **개발자 친화적**: FastAPI의 자동 문서화

### 🔄 추가 개선 방안
1. **캐싱**: Redis를 사용한 결과 캐싱
2. **배치 처리**: 여러 이미지 동시 처리
3. **웹소켓**: 실시간 비디오 스트림 처리
4. **모델 최적화**: TensorRT 또는 ONNX 변환
5. **CDN 연동**: 이미지 전송 최적화

이 가이드를 따라하면 견고하고 확장 가능한 객체 탐지 API를 성공적으로 배포할 수 있습니다. 프로덕션 환경에서는 추가적인 보안 조치와 모니터링을 고려하시기 바랍니다.

## 📚 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [YOLOv10 GitHub](https://github.com/THU-MIG/yolov10)
- [Railway 배포 가이드](https://docs.railway.app/)
- [Ultralytics YOLOv10 문서](https://docs.ultralytics.com/)
