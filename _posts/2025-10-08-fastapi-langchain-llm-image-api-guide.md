---
layout: post
title: "FastAPI + LangChain으로 LLM 이미지 질문 API 구축하기: 완전 가이드"
date: 2025-10-08 10:00:00 +0900
categories: [FastAPI, LangChain, LLM, Computer-Vision]
tags: [FastAPI, LangChain, OpenAI, GPT-4V, Vision, API-Design, Python, Machine-Learning]
author: "updaun"
image: "/assets/img/posts/2025-10-08-fastapi-langchain-llm-image-api-guide.webp"
---

멀티모달 AI의 발전으로 이미지를 이해하고 분석할 수 있는 LLM이 등장했습니다. 이 글에서는 FastAPI와 LangChain을 활용하여 이미지에 대해 질문하고 답변을 받을 수 있는 강력한 API를 단계별로 구축하는 방법을 알아보겠습니다.

## 🎯 프로젝트 개요

### 목표
- 이미지 업로드 및 질문 처리가 가능한 REST API 구축
- GPT-4V 또는 다른 멀티모달 LLM 활용
- 확장 가능하고 유지보수가 용이한 아키텍처 설계
- 에러 처리 및 로깅 시스템 구현

### 기술 스택
- **FastAPI**: 고성능 웹 프레임워크
- **LangChain**: LLM 통합 및 체인 관리
- **OpenAI GPT-4V**: 멀티모달 언어 모델
- **Pydantic**: 데이터 검증 및 직렬화
- **Pillow**: 이미지 처리
- **python-multipart**: 파일 업로드 처리

## 📋 Step 1: 프로젝트 설정 및 의존성 설치

### 1.1 프로젝트 구조 생성

```bash
mkdir fastapi-llm-image-api
cd fastapi-llm-image-api

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 프로젝트 구조 생성
mkdir -p {app/{api,core,models,services,utils},uploads,logs}
touch app/__init__.py app/api/__init__.py app/core/__init__.py
touch app/models/__init__.py app/services/__init__.py app/utils/__init__.py
```

### 1.2 필요한 패키지 설치

```bash
# requirements.txt 생성
cat > requirements.txt << EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
langchain==0.0.350
langchain-openai==0.0.2
python-multipart==0.0.6
pillow==10.1.0
pydantic==2.5.0
python-dotenv==1.0.0
aiofiles==23.2.1
httpx==0.25.2
pytest==7.4.3
pytest-asyncio==0.21.1
EOF

# 패키지 설치
pip install -r requirements.txt
```

### 1.3 환경 변수 설정

```bash
# .env 파일 생성
cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,bmp,webp
LOG_LEVEL=INFO
EOF
```

## 📋 Step 2: 핵심 설정 및 모델 정의

### 2.1 설정 관리자 구현

```python
# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # API 설정
    app_name: str = "FastAPI LLM Image API"
    debug: bool = False
    version: str = "1.0.0"
    
    # OpenAI 설정
    openai_api_key: str
    
    # 파일 업로드 설정
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = ["jpg", "jpeg", "png", "gif", "bmp", "webp"]
    upload_path: str = "uploads"
    
    # 로깅 설정
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    class Config:
        env_file = ".env"

settings = Settings()

# 업로드 디렉토리 생성
os.makedirs(settings.upload_path, exist_ok=True)
os.makedirs("logs", exist_ok=True)
```

### 2.2 Pydantic 모델 정의

```python
# app/models/schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import base64

class ImageAnalysisRequest(BaseModel):
    """이미지 분석 요청 모델"""
    question: str = Field(..., min_length=1, max_length=1000, description="이미지에 대한 질문")
    image_base64: Optional[str] = Field(None, description="Base64 인코딩된 이미지")
    
    @validator('question')
    def validate_question(cls, v):
        if not v.strip():
            raise ValueError("질문은 비어있을 수 없습니다")
        return v.strip()

class ImageAnalysisResponse(BaseModel):
    """이미지 분석 응답 모델"""
    success: bool
    answer: str
    confidence: Optional[float] = None
    processing_time: float
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    success: bool = False
    error: str
    error_code: str
    timestamp: datetime

class HealthCheck(BaseModel):
    """헬스체크 응답 모델"""
    status: str
    timestamp: datetime
    version: str
```

## 📋 Step 3: LangChain 서비스 구현

### 3.1 이미지 처리 유틸리티

```python
# app/utils/image_utils.py
from PIL import Image
import base64
import io
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    """이미지 처리 유틸리티 클래스"""
    
    @staticmethod
    def validate_image(file_content: bytes, max_size: int) -> Tuple[bool, Optional[str]]:
        """이미지 파일 검증"""
        try:
            if len(file_content) > max_size:
                return False, f"파일 크기가 너무 큽니다. 최대 {max_size // 1024 // 1024}MB까지 허용됩니다."
            
            # PIL로 이미지 열기 시도
            image = Image.open(io.BytesIO(file_content))
            image.verify()  # 이미지 무결성 검증
            
            return True, None
            
        except Exception as e:
            logger.error(f"이미지 검증 실패: {e}")
            return False, "유효하지 않은 이미지 파일입니다."
    
    @staticmethod
    def resize_image(image_content: bytes, max_width: int = 1024, max_height: int = 1024) -> bytes:
        """이미지 크기 조정"""
        try:
            image = Image.open(io.BytesIO(image_content))
            
            # RGBA 이미지를 RGB로 변환 (JPEG 저장을 위해)
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # 크기 조정
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # 바이트로 변환
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"이미지 크기 조정 실패: {e}")
            raise
    
    @staticmethod
    def image_to_base64(image_content: bytes) -> str:
        """이미지를 base64로 인코딩"""
        return base64.b64encode(image_content).decode('utf-8')
```

### 3.2 LangChain LLM 서비스

```python
# app/services/llm_service.py
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from langchain.callbacks import get_openai_callback
import logging
import time
from typing import Dict, Any, Optional
import base64

logger = logging.getLogger(__name__)

class LLMImageService:
    """LLM을 활용한 이미지 분석 서비스"""
    
    def __init__(self, api_key: str, model_name: str = "gpt-4-vision-preview"):
        self.model = ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            max_tokens=500,
            temperature=0.1
        )
    
    async def analyze_image(self, image_base64: str, question: str) -> Dict[str, Any]:
        """이미지 분석 수행"""
        start_time = time.time()
        
        try:
            # 메시지 구성
            message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": f"다음 이미지를 보고 질문에 답해주세요: {question}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            )
            
            # LLM 호출
            with get_openai_callback() as cb:
                response = await self.model.ainvoke([message])
                
            processing_time = time.time() - start_time
            
            return {
                "answer": response.content,
                "processing_time": processing_time,
                "token_usage": {
                    "total_tokens": cb.total_tokens,
                    "prompt_tokens": cb.prompt_tokens,
                    "completion_tokens": cb.completion_tokens,
                    "total_cost": cb.total_cost
                }
            }
            
        except Exception as e:
            logger.error(f"LLM 분석 실패: {e}")
            raise
    
    async def analyze_image_with_context(
        self, 
        image_base64: str, 
        question: str, 
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """컨텍스트를 포함한 이미지 분석"""
        start_time = time.time()
        
        try:
            # 컨텍스트가 있는 경우 질문에 포함
            enhanced_question = question
            if context:
                enhanced_question = f"컨텍스트: {context}\n\n질문: {question}"
            
            message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": f"""다음 이미지를 분석하고 질문에 대해 상세히 답변해주세요.

{enhanced_question}

답변 시 다음 사항을 고려해주세요:
1. 이미지에서 관찰되는 주요 요소들
2. 질문과 관련된 구체적인 정보
3. 가능한 한 정확하고 유용한 답변 제공"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            )
            
            with get_openai_callback() as cb:
                response = await self.model.ainvoke([message])
                
            processing_time = time.time() - start_time
            
            return {
                "answer": response.content,
                "processing_time": processing_time,
                "token_usage": {
                    "total_tokens": cb.total_tokens,
                    "prompt_tokens": cb.prompt_tokens,
                    "completion_tokens": cb.completion_tokens,
                    "total_cost": cb.total_cost
                }
            }
            
        except Exception as e:
            logger.error(f"컨텍스트 기반 LLM 분석 실패: {e}")
            raise
```

## 📋 Step 4: FastAPI 라우터 구현

### 4.1 에러 핸들러 및 미들웨어

```python
# app/core/exceptions.py
from fastapi import HTTPException
from typing import Any, Dict, Optional

class ImageProcessingError(HTTPException):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)

class LLMServiceError(HTTPException):
    def __init__(self, detail: str, status_code: int = 500):
        super().__init__(status_code=status_code, detail=detail)

class FileTooLargeError(ImageProcessingError):
    def __init__(self, max_size: int):
        super().__init__(f"파일 크기가 너무 큽니다. 최대 {max_size // 1024 // 1024}MB까지 허용됩니다.")

class InvalidImageError(ImageProcessingError):
    def __init__(self, detail: str = "유효하지 않은 이미지 파일입니다."):
        super().__init__(detail)
```

### 4.2 메인 API 라우터

```python
# app/api/image_analysis.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
import aiofiles
import os
from datetime import datetime
from typing import Optional
import logging

from app.models.schemas import ImageAnalysisResponse, ErrorResponse
from app.services.llm_service import LLMImageService
from app.utils.image_utils import ImageProcessor
from app.core.config import settings
from app.core.exceptions import ImageProcessingError, LLMServiceError

router = APIRouter()
logger = logging.getLogger(__name__)

# LLM 서비스 인스턴스 생성
llm_service = LLMImageService(api_key=settings.openai_api_key)

@router.post("/analyze", response_model=ImageAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(..., description="분석할 이미지 파일"),
    question: str = Form(..., description="이미지에 대한 질문")
):
    """이미지 업로드 및 질문 분석 API"""
    start_time = datetime.now()
    
    try:
        # 파일 확장자 검증
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in settings.allowed_extensions:
            raise ImageProcessingError(
                f"지원하지 않는 파일 형식입니다. 허용된 형식: {', '.join(settings.allowed_extensions)}"
            )
        
        # 파일 내용 읽기
        file_content = await file.read()
        
        # 파일 크기 및 유효성 검증
        is_valid, error_msg = ImageProcessor.validate_image(file_content, settings.max_file_size)
        if not is_valid:
            raise ImageProcessingError(error_msg)
        
        # 이미지 크기 조정
        processed_image = ImageProcessor.resize_image(file_content)
        
        # Base64 인코딩
        image_base64 = ImageProcessor.image_to_base64(processed_image)
        
        # LLM 분석 수행
        result = await llm_service.analyze_image(image_base64, question)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ImageAnalysisResponse(
            success=True,
            answer=result["answer"],
            processing_time=processing_time,
            timestamp=datetime.now(),
            metadata={
                "file_name": file.filename,
                "file_size": len(file_content),
                "token_usage": result.get("token_usage")
            }
        )
        
    except ImageProcessingError as e:
        logger.error(f"이미지 처리 에러: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"예상치 못한 에러: {str(e)}")
        raise LLMServiceError("이미지 분석 중 오류가 발생했습니다.")

@router.post("/analyze-with-context", response_model=ImageAnalysisResponse)
async def analyze_image_with_context(
    file: UploadFile = File(..., description="분석할 이미지 파일"),
    question: str = Form(..., description="이미지에 대한 질문"),
    context: Optional[str] = Form(None, description="추가 컨텍스트 정보")
):
    """컨텍스트를 포함한 이미지 분석 API"""
    start_time = datetime.now()
    
    try:
        # 기본 검증 로직 (위와 동일)
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in settings.allowed_extensions:
            raise ImageProcessingError(
                f"지원하지 않는 파일 형식입니다. 허용된 형식: {', '.join(settings.allowed_extensions)}"
            )
        
        file_content = await file.read()
        is_valid, error_msg = ImageProcessor.validate_image(file_content, settings.max_file_size)
        if not is_valid:
            raise ImageProcessingError(error_msg)
        
        processed_image = ImageProcessor.resize_image(file_content)
        image_base64 = ImageProcessor.image_to_base64(processed_image)
        
        # 컨텍스트 포함 분석
        result = await llm_service.analyze_image_with_context(image_base64, question, context)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ImageAnalysisResponse(
            success=True,
            answer=result["answer"],
            processing_time=processing_time,
            timestamp=datetime.now(),
            metadata={
                "file_name": file.filename,
                "file_size": len(file_content),
                "context_provided": context is not None,
                "token_usage": result.get("token_usage")
            }
        )
        
    except ImageProcessingError as e:
        logger.error(f"이미지 처리 에러: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"예상치 못한 에러: {str(e)}")
        raise LLMServiceError("이미지 분석 중 오류가 발생했습니다.")
```

## 📋 Step 5: 메인 애플리케이션 및 설정

### 5.1 로깅 설정

```python
# app/core/logging.py
import logging
import sys
from pathlib import Path
from app.core.config import settings

def setup_logging():
    """로깅 설정"""
    # 로그 디렉토리 생성
    log_file = Path(settings.log_file)
    log_file.parent.mkdir(exist_ok=True)
    
    # 로깅 포맷
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 기본 로깅 설정
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=log_format,
        handlers=[
            logging.FileHandler(settings.log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
```

### 5.2 메인 애플리케이션

```python
# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import ImageProcessingError, LLMServiceError
from app.api import image_analysis
from app.models.schemas import HealthCheck, ErrorResponse

# 로깅 설정
setup_logging()
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="FastAPI와 LangChain을 활용한 LLM 이미지 질문 API",
    debug=settings.debug
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
app.include_router(image_analysis.router, prefix="/api/v1/image", tags=["Image Analysis"])

# 전역 예외 핸들러
@app.exception_handler(ImageProcessingError)
async def image_processing_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            error_code="IMAGE_PROCESSING_ERROR",
            timestamp=datetime.now()
        ).dict()
    )

@app.exception_handler(LLMServiceError)
async def llm_service_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            error_code="LLM_SERVICE_ERROR",
            timestamp=datetime.now()
        ).dict()
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"예상치 못한 에러: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="내부 서버 오류가 발생했습니다.",
            error_code="INTERNAL_SERVER_ERROR",
            timestamp=datetime.now()
        ).dict()
    )

# 헬스체크 엔드포인트
@app.get("/health", response_model=HealthCheck)
async def health_check():
    """API 헬스체크"""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now(),
        version=settings.version
    )

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "FastAPI LLM Image API",
        "version": settings.version,
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
```

## 📋 Step 6: 테스트 코드 작성

### 6.1 단위 테스트

```python
# tests/test_image_utils.py
import pytest
import io
from PIL import Image
from app.utils.image_utils import ImageProcessor

class TestImageProcessor:
    
    def create_test_image(self, format="JPEG", size=(100, 100)):
        """테스트용 이미지 생성"""
        image = Image.new('RGB', size, color='red')
        img_bytes = io.BytesIO()
        image.save(img_bytes, format=format)
        return img_bytes.getvalue()
    
    def test_validate_image_success(self):
        """유효한 이미지 검증 테스트"""
        image_content = self.create_test_image()
        is_valid, error = ImageProcessor.validate_image(image_content, 10 * 1024 * 1024)
        assert is_valid is True
        assert error is None
    
    def test_validate_image_too_large(self):
        """큰 이미지 검증 테스트"""
        image_content = self.create_test_image()
        is_valid, error = ImageProcessor.validate_image(image_content, 100)  # 100 bytes 제한
        assert is_valid is False
        assert "파일 크기가 너무 큽니다" in error
    
    def test_resize_image(self):
        """이미지 크기 조정 테스트"""
        original_image = self.create_test_image(size=(2000, 2000))
        resized_image = ImageProcessor.resize_image(original_image, 1024, 1024)
        
        # 크기가 줄어들었는지 확인
        assert len(resized_image) < len(original_image)
        
        # 이미지가 여전히 유효한지 확인
        resized_pil = Image.open(io.BytesIO(resized_image))
        assert resized_pil.size[0] <= 1024
        assert resized_pil.size[1] <= 1024
```

### 6.2 통합 테스트

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
import io
from PIL import Image

client = TestClient(app)

class TestImageAnalysisAPI:
    
    def create_test_image_file(self):
        """테스트용 이미지 파일 생성"""
        image = Image.new('RGB', (100, 100), color='blue')
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes
    
    def test_health_check(self):
        """헬스체크 테스트"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_analyze_image_success(self):
        """이미지 분석 성공 테스트"""
        image_file = self.create_test_image_file()
        
        response = client.post(
            "/api/v1/image/analyze",
            files={"file": ("test.jpg", image_file, "image/jpeg")},
            data={"question": "이 이미지에 무엇이 보이나요?"}
        )
        
        # OpenAI API 키가 설정되지 않은 경우 스킵
        if response.status_code == 500:
            pytest.skip("OpenAI API 키가 설정되지 않음")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "answer" in data
    
    def test_analyze_image_invalid_format(self):
        """잘못된 형식 파일 테스트"""
        response = client.post(
            "/api/v1/image/analyze",
            files={"file": ("test.txt", io.StringIO("not an image"), "text/plain")},
            data={"question": "이 이미지에 무엇이 보이나요?"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
```

## 📋 Step 7: 실행 및 배포

### 7.1 로컬 실행

```bash
# 개발 서버 실행
python -m app.main

# 또는 uvicorn 직접 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7.2 Docker 배포

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  fastapi-llm-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    restart: unless-stopped
```

### 7.3 API 테스트

```bash
# 헬스체크
curl -X GET "http://localhost:8000/health"

# 이미지 분석 테스트
curl -X POST "http://localhost:8000/api/v1/image/analyze" \
  -F "file=@test_image.jpg" \
  -F "question=이 이미지에서 무엇을 볼 수 있나요?"
```

## 🚀 추가 기능 구현 아이디어

### 1. 캐싱 시스템
```python
# Redis를 활용한 결과 캐싱
import redis
import hashlib
import json

class CacheService:
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url)
    
    def generate_cache_key(self, image_base64: str, question: str) -> str:
        """캐시 키 생성"""
        content = f"{image_base64}:{question}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get_cached_result(self, cache_key: str) -> Optional[Dict]:
        """캐시된 결과 조회"""
        try:
            cached = self.redis_client.get(cache_key)
            return json.loads(cached) if cached else None
        except Exception:
            return None
    
    async def cache_result(self, cache_key: str, result: Dict, ttl: int = 3600):
        """결과 캐싱"""
        try:
            self.redis_client.setex(cache_key, ttl, json.dumps(result))
        except Exception:
            pass  # 캐싱 실패는 무시
```

### 2. 배치 처리 지원
```python
# 여러 이미지 동시 처리
@router.post("/analyze-batch")
async def analyze_batch_images(
    files: List[UploadFile] = File(...),
    questions: List[str] = Form(...)
):
    """배치 이미지 분석"""
    tasks = []
    for file, question in zip(files, questions):
        task = analyze_single_image(file, question)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {"results": results}
```

### 3. 스트리밍 응답
```python
# 실시간 응답 스트리밍
from fastapi.responses import StreamingResponse

@router.post("/analyze-stream")
async def analyze_image_stream(file: UploadFile, question: str):
    """스트리밍 응답으로 이미지 분석"""
    async def generate_response():
        # 이미지 처리
        yield "data: {'status': 'processing_image'}\n\n"
        
        # LLM 호출 및 스트리밍
        yield "data: {'status': 'analyzing'}\n\n"
        
        # 최종 결과
        yield f"data: {json.dumps(result)}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain"
    )
```

## 🛡️ 보안 및 최적화 고려사항

### 1. 보안 강화
- API 키 관리 및 인증 시스템 구현
- 파일 업로드 보안 검증 강화
- Rate limiting 적용
- Input sanitization

### 2. 성능 최적화
- 이미지 압축 및 최적화
- 비동기 처리 활용
- 커넥션 풀링
- 메모리 사용량 모니터링

### 3. 모니터링 및 로깅
- Prometheus 메트릭 수집
- 구조화된 로깅
- 에러 추적 시스템
- 성능 모니터링

## 📝 마무리

이 가이드를 통해 FastAPI와 LangChain을 활용한 강력한 이미지 질문 API를 구축했습니다. 핵심 포인트는 다음과 같습니다:

1. **모듈화된 아키텍처**: 각 기능별로 분리된 구조로 유지보수성 향상
2. **견고한 에러 처리**: 다양한 예외 상황에 대한 적절한 처리
3. **확장 가능한 설계**: 새로운 기능 추가가 용이한 구조
4. **테스트 코드**: 안정적인 서비스 운영을 위한 테스트 환경

이제 여러분만의 창의적인 이미지 분석 서비스를 구축해보세요! 🎯