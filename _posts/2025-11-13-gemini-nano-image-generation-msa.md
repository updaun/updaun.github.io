---
layout: post
title: "FastAPI와 Google Gemini로 AI 프로필 사진 생성 서비스 구축하기"
date: 2025-11-13 09:00:00 +0900
categories: [FastAPI, AI, GCP]
tags: [fastapi, gemini, google-cloud, image-generation, ai-profile, python, async]
description: "Express로 작성된 AI 프로필 사진 생성 서비스를 FastAPI로 마이그레이션하며 배우는 실전 백엔드 개발. Google Gemini API 연동부터 GCP 배포까지."
image: "/assets/img/posts/2025-11-13-gemini-nano-image-generation-msa.webp"
---

## 1. 서론

### 1.1 프로젝트 개요

사용자가 업로드한 일반 셀카를 Google Gemini AI를 활용하여 전문가급 프로필 사진으로 변환하는 서비스를 FastAPI로 구축합니다.

**원본 프로젝트:**
- GitHub: [youtube-jocoding/app-in-toss-ai-photo-studio-example](https://github.com/youtube-jocoding/app-in-toss-ai-photo-studio-example)
- 기술 스택: Express.js (Node.js)
- 우리의 목표: FastAPI (Python)로 마이그레이션

**비즈니스 시나리오:**
```
1. 사용자가 셀카 업로드
   ↓
2. 이미지 압축 및 검증 (1MB 이하, 512x512)
   ↓
3. Google Gemini 2.5 Flash Image 모델로 전송
   ↓
4. AI가 전문 스튜디오 프로필 사진으로 변환
   ↓
5. Base64 이미지 URL 반환
```

**왜 FastAPI로 전환하는가?**

| Express (Node.js) | FastAPI (Python) |
|-------------------|------------------|
| JavaScript 비동기 처리 | Python의 async/await |
| Busboy로 파일 파싱 | 내장 File 업로드 |
| 수동 타입 체크 | Pydantic 자동 검증 |
| Swagger 수동 설정 | 자동 OpenAPI 문서 |
| npm 의존성 관리 | Poetry/pip |

### 1.2 시스템 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                 클라이언트                           │
│  (React/토스 인앱) - 이미지 업로드                   │
└────────────────┬────────────────────────────────────┘
                 │ POST /api/generate
                 │ Content-Type: multipart/form-data
                 ↓
┌─────────────────────────────────────────────────────┐
│              FastAPI 백엔드                          │
│  ┌──────────────────────────────────────────────┐  │
│  │  Endpoint: /api/generate                     │  │
│  │  - 파일 검증 (10MB, MIME 타입)              │  │
│  │  - 이미지 리사이징                           │  │
│  └────────────┬─────────────────────────────────┘  │
│               │                                      │
│  ┌────────────▼─────────────────────────────────┐  │
│  │  Gemini Client Service                       │  │
│  │  - google-genai SDK                          │  │
│  │  - 프롬프트 엔지니어링                        │  │
│  │  - 스트리밍 응답 처리                         │  │
│  └────────────┬─────────────────────────────────┘  │
└───────────────┼──────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────────────────┐
│         Google Gemini 2.5 Flash Image               │
│  - 3:4 비율 세로형 프로필 사진                       │
│  - 프로 스튜디오 퀄리티 변환                          │
└─────────────────────────────────────────────────────┘
```

### 1.3 핵심 기능

**1) 이미지 업로드 & 검증**
- Content-Type: `multipart/form-data`
- 최대 크기: 10MB
- 허용 형식: JPEG, PNG, WebP
- 자동 MIME 타입 검증

**2) AI 프로필 변환**
- Google Gemini 2.5 Flash Image 모델
- 프롬프트: 전문 스튜디오 프로필 사진
- 3:4 세로 비율
- 고품질 85mm f/1.8 렌즈 효과

**3) 응답 형식**
- Base64 Data URI
- JSON 응답
- 에러 핸들링

### 1.4 기술 스택

**Backend Framework:**
```python
FastAPI 0.104.0       # 고성능 비동기 웹 프레임워크
Uvicorn 0.24.0        # ASGI 서버
Pydantic 2.5.0        # 데이터 검증
python-multipart      # 파일 업로드
```

**AI & Cloud:**
```python
google-genai 0.3.0    # Gemini SDK
Pillow 10.1.0         # 이미지 처리
```

**개발 도구:**
```python
pytest 7.4.0          # 테스트
httpx 0.25.0          # HTTP 클라이언트
black 23.11.0         # 코드 포맷팅
```

**배포:**
```
Google Cloud Functions (2nd gen)
또는 Cloud Run
Docker
```

### 1.5 프로젝트 구조

```
ai-profile-service/
├── main.py                    # FastAPI 앱
├── requirements.txt           # 의존성
├── .env                       # 환경 변수
├── app/
│   ├── __init__.py
│   ├── config.py             # 설정
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py        # Pydantic 모델
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini_client.py  # Gemini API 클라이언트
│   │   └── image_processor.py # 이미지 처리
│   ├── routers/
│   │   ├── __init__.py
│   │   └── generate.py       # API 엔드포인트
│   └── utils/
│       ├── __init__.py
│       ├── exceptions.py     # 커스텀 예외
│       └── validators.py     # 검증 함수
├── tests/
│   ├── __init__.py
│   ├── test_generate.py
│   └── test_gemini.py
├── Dockerfile
└── README.md
```

### 1.6 Express vs FastAPI 코드 비교

**Express (원본):**
```javascript
// index.js
const express = require('express');
const Busboy = require('busboy');

app.post('/api/generate', async (req, res) => {
  const busboy = Busboy({ headers: req.headers });
  let fileBuffer;
  
  busboy.on('file', (fieldname, file) => {
    const chunks = [];
    file.on('data', chunk => chunks.push(chunk));
    file.on('end', () => {
      fileBuffer = Buffer.concat(chunks);
    });
  });
  
  busboy.on('finish', async () => {
    const imageUrl = await generateProfile(fileBuffer);
    res.json({ success: true, imageUrl });
  });
  
  req.pipe(busboy);
});
```

**FastAPI (우리가 만들 것):**
```python
# main.py
from fastapi import FastAPI, File, UploadFile
from app.services.gemini_client import GeminiClient

app = FastAPI()

@app.post("/api/generate")
async def generate_profile(image: UploadFile = File(...)):
    # 자동 파일 검증
    content = await image.read()
    
    # Gemini AI 호출
    gemini = GeminiClient()
    image_url = await gemini.generate_profile(content)
    
    return {"success": True, "imageUrl": image_url}
```

**차이점:**
- ✅ FastAPI는 파일 업로드 내장 지원
- ✅ 자동 타입 검증 (Pydantic)
- ✅ 비동기 처리 간편화
- ✅ 자동 API 문서 생성

### 1.7 이 글에서 다룰 내용

1. ✅ **환경 설정** - GCP, Gemini API 키
2. ✅ **FastAPI 프로젝트 구조** - 모듈화
3. ✅ **파일 업로드 처리** - 검증, MIME 타입
4. ✅ **Gemini AI 연동** - SDK, 프롬프트
5. ✅ **에러 핸들링** - 커스텀 예외
6. ✅ **테스트** - pytest
7. ✅ **Docker 배포** - Dockerfile
8. ✅ **GCP 배포** - Cloud Functions/Run

시작하겠습니다! 🚀

## 2. Google Cloud 프로젝트 설정 및 Gemini API 활성화

### 2.1 Google Cloud 프로젝트 생성

**1) Google Cloud Console 접속**

```bash
# 브라우저에서 접속
https://console.cloud.google.com/

# Google 계정으로 로그인
# 무료 체험판 사용 시 $300 크레딧 제공
```

**2) 새 프로젝트 생성**

```
1. 상단의 프로젝트 선택 드롭다운 클릭
2. "새 프로젝트" 선택
3. 프로젝트 정보 입력:
   - 프로젝트 이름: ai-profile-generator
   - 조직: (선택사항)
   - 위치: (선택사항)
4. "만들기" 클릭
5. 프로젝트 생성 완료 후 선택
```

**3) 프로젝트 ID 확인**

프로젝트 대시보드에서 **프로젝트 ID**를 확인하고 메모합니다.
- 예: `ai-profile-generator-123456`
- 이 ID는 나중에 API 설정에 사용됩니다.

### 2.2 결제 계정 설정 (필수)

⚠️ **중요**: Gemini API를 사용하려면 결제 계정이 활성화되어야 합니다.

```
1. 왼쪽 메뉴 → "결제"
2. "결제 계정 연결" 클릭
3. 결제 정보 입력:
   - 신용카드/체크카드 정보
   - 주소 정보
4. 무료 체험판 활성화 ($300 크레딧)
```

**무료 할당량:**
- Gemini 2.5 Flash: 분당 15 요청
- 일일 1,000 요청 (무료 체험 시)
- 초과 시 과금 발생

### 2.3 Gemini API 활성화

**1) API 라이브러리 접속**

```
1. 왼쪽 메뉴 → "API 및 서비스" → "라이브러리"
2. 검색창에 "Generative Language API" 입력
3. "Generative Language API" 선택
4. "사용 설정" 클릭
```

**2) API 활성화 확인**

```
1. "API 및 서비스" → "대시보드"
2. "Generative Language API"가 활성화되어 있는지 확인
```

### 2.4 Google AI Studio에서 API 키 발급

**1) Google AI Studio 접속**

```bash
# 브라우저에서 접속
https://aistudio.google.com/

# 동일한 Google 계정으로 로그인
```

**2) API 키 생성**

```
1. 왼쪽 메뉴에서 "Get API Key" 클릭
2. "Create API Key" 버튼 클릭
3. 프로젝트 선택:
   - 앞서 생성한 "ai-profile-generator" 선택
   - 또는 "Create API key in new project" 선택
4. API 키 생성 완료
```

**3) API 키 복사 및 저장**

```
생성된 API 키: AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

⚠️ 중요 보안 사항:
- API 키를 GitHub 등 공개 저장소에 업로드 금지
- 환경 변수로 관리
- .gitignore에 .env 파일 추가
- 정기적으로 키 교체
```

### 2.5 API 키 권한 설정 (보안 강화)

**1) API 키 제한 설정**

```
1. Google Cloud Console → "API 및 서비스" → "사용자 인증 정보"
2. 생성된 API 키 클릭
3. "API 제한사항" 섹션:
   - "키 제한" 선택
   - "Generative Language API" 체크
4. "애플리케이션 제한사항" (선택사항):
   - IP 주소 제한
   - HTTP 리퍼러 제한
5. "저장" 클릭
```

**2) 할당량 확인**

```
1. "API 및 서비스" → "할당량"
2. "Generative Language API" 검색
3. 현재 사용량 및 한도 확인
4. 필요 시 할당량 증가 요청
```

### 2.6 테스트 요청으로 API 키 검증

**1) curl로 간단 테스트**

```bash
# API 키가 정상적으로 작동하는지 확인
curl "https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_API_KEY"

# 성공 시 사용 가능한 모델 리스트 반환:
# {
#   "models": [
#     {
#       "name": "models/gemini-2.5-flash",
#       "displayName": "Gemini 2.5 Flash",
#       ...
#     }
#   ]
# }
```

**2) Python으로 테스트**

```bash
# google-genai 패키지 설치
pip install google-genai

# 테스트 스크립트 실행
python << 'EOF'
from google import genai

client = genai.Client(api_key="YOUR_API_KEY")

# 사용 가능한 모델 조회
for model in client.models.list():
    if "flash" in model.name.lower():
        print(f"✅ {model.name}: {model.display_name}")
EOF
```

**예상 출력:**
```
✅ models/gemini-2.5-flash: Gemini 2.5 Flash
✅ models/gemini-2.5-flash-image: Gemini 2.5 Flash Image
```

⚠️ **중요**: API 키를 안전하게 보관하세요!

### 2.7 프로젝트 초기화

```bash
# 프로젝트 디렉토리 생성
mkdir ai-profile-service
cd ai-profile-service

# Python 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 기본 구조 생성
mkdir -p app/{models,services,routers,utils} tests

# __init__.py 파일 생성
touch app/__init__.py
touch app/models/__init__.py
touch app/services/__init__.py
touch app/routers/__init__.py
touch app/utils/__init__.py
touch tests/__init__.py
```

### 2.8 의존성 설치

```bash
# requirements.txt
cat > requirements.txt << 'EOF'
# FastAPI
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Pydantic
pydantic==2.5.0
pydantic-settings==2.1.0

# Google Gemini
google-genai==0.3.0

# 이미지 처리
Pillow==10.1.0

# 유틸리티
python-dotenv==1.0.0
httpx==0.25.2

# 개발
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
ruff==0.1.6
EOF

# 설치
pip install -r requirements.txt
```

### 2.9 환경 변수 설정

```bash
# .env
cat > .env << 'EOF'
# Gemini API
GEMINI_API_KEY=AIzaSy_your_api_key_here
GEMINI_MODEL=gemini-2.5-flash-image

# 서버
HOST=0.0.0.0
PORT=8000
DEBUG=True

# 파일 업로드 제한
MAX_FILE_SIZE=10485760  # 10MB in bytes
ALLOWED_MIME_TYPES=image/jpeg,image/png,image/webp

# CORS
ALLOWED_ORIGINS=http://localhost:5173,https://ai-photo-studio.apps.tossmini.com
EOF
```

### 2.10 설정 파일 작성

```python
# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # Gemini API
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash-image"
    
    # 서버
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # 파일 업로드
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_mime_types: list[str] = [
        "image/jpeg",
        "image/png",
        "image/webp"
    ]
    
    # CORS
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "https://ai-photo-studio.apps.tossmini.com"
    ]
    
    # Gemini 설정
    gemini_aspect_ratio: str = "3:4"  # 세로형 프로필
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스"""
    return Settings()
```

## 3. FastAPI 앱 & 파일 업로드 구현

### 3.1 Pydantic 스키마 정의

```python
# app/models/schemas.py
from pydantic import BaseModel, Field
from typing import Optional

class GenerateResponse(BaseModel):
    """이미지 생성 응답"""
    success: bool
    image_url: Optional[str] = None
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "image_url": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
            }
        }

class HealthResponse(BaseModel):
    """헬스 체크 응답"""
    status: str = "ok"
    version: str = "1.0.0"
```

### 3.2 커스텀 예외 정의

```python
# app/utils/exceptions.py
from fastapi import HTTPException, status

class ImageValidationError(HTTPException):
    """이미지 검증 실패"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

class FileTooLargeError(HTTPException):
    """파일 크기 초과"""
    def __init__(self, max_size: int):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {max_size / 1024 / 1024:.1f}MB"
        )

class UnsupportedFileTypeError(HTTPException):
    """지원하지 않는 파일 형식"""
    def __init__(self, mime_type: str, allowed_types: list[str]):
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {mime_type}. Allowed: {', '.join(allowed_types)}"
        )

class GeminiAPIError(HTTPException):
    """Gemini API 오류"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI generation failed: {detail}"
        )
```

### 3.3 파일 검증 유틸리티

```python
# app/utils/validators.py
from fastapi import UploadFile
from app.config import get_settings
from app.utils.exceptions import (
    FileTooLargeError,
    UnsupportedFileTypeError,
    ImageValidationError
)
import imghdr
from io import BytesIO

settings = get_settings()

async def validate_image_file(file: UploadFile) -> bytes:
    """
    업로드된 이미지 파일 검증
    
    Args:
        file: 업로드된 파일
        
    Returns:
        bytes: 검증된 파일 내용
        
    Raises:
        FileTooLargeError: 파일 크기 초과
        UnsupportedFileTypeError: 지원하지 않는 파일 형식
        ImageValidationError: 기타 검증 실패
    """
    # 파일 읽기
    content = await file.read()
    
    # 1. 크기 검증
    if len(content) > settings.max_file_size:
        raise FileTooLargeError(settings.max_file_size)
    
    # 2. MIME 타입 검증
    if file.content_type not in settings.allowed_mime_types:
        raise UnsupportedFileTypeError(
            file.content_type,
            settings.allowed_mime_types
        )
    
    # 3. 실제 이미지 형식 검증 (헤더 확인)
    image_type = imghdr.what(None, h=content)
    if image_type not in ['jpeg', 'png', 'webp']:
        raise ImageValidationError(
            "File is not a valid image. Please upload JPEG, PNG, or WebP."
        )
    
    # 4. 파일이 비어있지 않은지 확인
    if len(content) == 0:
        raise ImageValidationError("Uploaded file is empty")
    
    return content
```

### 3.4 Gemini 클라이언트 구현

```python
# app/services/gemini_client.py
from google import genai
from google.genai.types import GenerateContentConfig, ImageConfig
from app.config import get_settings
from app.utils.exceptions import GeminiAPIError
import base64
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

# AI 프롬프트 (원본과 동일)
PROFILE_PROMPT = """Transform the provided selfie into an ultra-realistic, high-end professional corporate headshot taken in a premium photography studio.
The subject's facial features, proportions, and natural identity must be perfectly preserved with lifelike accuracy.

Replace casual clothing with a modern, dark-colored business suit in a tailored fit, featuring subtle fabric texture.
The background should be a seamless, luxurious deep classic blue studio backdrop with gentle falloff lighting that enhances depth.
Use a soft, cinematic three-point lighting setup—key, fill, and rim lights balanced to create smooth highlights, natural shadows, and flattering contours.
The image should be captured from the chest up, in vertical orientation, as if taken with a full-frame DSLR camera using an 85mm f/1.8 portrait lens.
Ensure the eyes are tack-sharp with a shallow depth of field and elegant bokeh.

Maintain natural skin tone and texture, with fine detail visible under professional lighting.
The overall impression should be confident, sophisticated, and approachable—suitable for executive or corporate use."""

class GeminiClient:
    """Google Gemini AI 클라이언트"""
    
    def __init__(self):
        """클라이언트 초기화"""
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
    
    async def generate_profile(self, image_bytes: bytes) -> str:
        """
        프로필 이미지 생성
        
        Args:
            image_bytes: 원본 이미지 바이너리
            
        Returns:
            str: Data URI 형식의 생성된 이미지
            
        Raises:
            GeminiAPIError: 생성 실패
        """
        try:
            # 1. 요청 데이터 구성
            contents = [
                {
                    "role": "user",
                    "parts": [
                        {"text": PROFILE_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": base64.b64encode(image_bytes).decode()
                            }
                        }
                    ]
                }
            ]
            
            # 2. 생성 설정
            config = GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=ImageConfig(
                    aspect_ratio=settings.gemini_aspect_ratio
                )
            )
            
            # 3. 스트리밍 요청
            logger.info(f"Requesting profile generation with model: {self.model}")
            
            response = self.client.models.generate_content_stream(
                model=self.model,
                config=config,
                contents=contents
            )
            
            # 4. 스트리밍 응답 처리
            for chunk in response:
                if not chunk.candidates:
                    continue
                
                candidate = chunk.candidates[0]
                if not candidate.content or not candidate.content.parts:
                    continue
                
                part = candidate.content.parts[0]
                if hasattr(part, 'inline_data') and part.inline_data:
                    # 이미지 데이터 추출
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    image_data = part.inline_data.data
                    
                    # Base64 인코딩 (이미 인코딩되어 있으면 그대로)
                    if isinstance(image_data, bytes):
                        b64_data = base64.b64encode(image_data).decode()
                    else:
                        b64_data = image_data
                    
                    data_uri = f"data:{mime_type};base64,{b64_data}"
                    logger.info("Profile image generated successfully")
                    return data_uri
            
            raise GeminiAPIError("No image generated in response")
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise GeminiAPIError(str(e))
```

### 3.5 API 엔드포인트 구현

```python
# app/routers/generate.py
from fastapi import APIRouter, File, UploadFile, Depends
from app.models.schemas import GenerateResponse, HealthResponse
from app.services.gemini_client import GeminiClient
from app.utils.validators import validate_image_file
from app.utils.exceptions import GeminiAPIError
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/generate", response_model=GenerateResponse)
async def generate_profile(
    image: UploadFile = File(..., description="Profile image to transform")
):
    """
    AI 프로필 이미지 생성
    
    - **image**: JPEG, PNG, WebP 이미지 파일 (최대 10MB)
    
    Returns:
        - **success**: 성공 여부
        - **image_url**: Base64 Data URI 형식의 생성된 이미지
    """
    try:
        # 1. 파일 검증
        logger.info(f"Validating uploaded file: {image.filename}")
        image_content = await validate_image_file(image)
        
        # 2. Gemini AI로 프로필 생성
        logger.info("Generating profile with Gemini AI")
        gemini = GeminiClient()
        image_url = await gemini.generate_profile(image_content)
        
        # 3. 성공 응답
        return GenerateResponse(
            success=True,
            image_url=image_url
        )
        
    except (GeminiAPIError, Exception) as e:
        logger.error(f"Generation failed: {str(e)}")
        # 에러도 구조화된 응답으로 반환
        return GenerateResponse(
            success=False,
            error=str(e)
        )

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스 체크 엔드포인트"""
    return HealthResponse()
```

### 3.6 메인 앱 구성

```python
# main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import get_settings
from app.routers import generate
import logging
import sys

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)
settings = get_settings()

# FastAPI 앱 생성
app = FastAPI(
    title="AI Profile Generator",
    description="Transform selfies into professional profile photos using Google Gemini",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(
    generate.router,
    prefix="/api",
    tags=["Image Generation"]
)

# 전역 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """처리되지 않은 예외 핸들러"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error"
        }
    )

# 시작 이벤트
@app.on_event("startup")
async def startup_event():
    """앱 시작 시 실행"""
    logger.info("Starting AI Profile Generator API")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Allowed origins: {settings.allowed_origins}")

# 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 실행"""
    logger.info("Shutting down AI Profile Generator API")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
```

### 3.7 로컬 실행 및 테스트

```bash
# 서버 실행
python main.py

# 또는 uvicorn 직접 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# API 문서 확인
# http://localhost:8000/docs

# 헬스 체크
curl http://localhost:8000/api/health

# 이미지 업로드 테스트
curl -X POST http://localhost:8000/api/generate \
  -F "image=@test_photo.jpg" \
  -H "Accept: application/json"
```

## 4. 테스트 & Docker 컨테이너화

### 4.1 테스트 코드 작성

**1) pytest 설정**

```python
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
```

**2) 기본 테스트 코드**

```python
# tests/test_generate.py
import pytest
from fastapi.testclient import TestClient
from main import app
from io import BytesIO
from PIL import Image

client = TestClient(app)

def create_test_image(size=(512, 512), format='JPEG') -> BytesIO:
    """테스트용 이미지 생성"""
    img = Image.new('RGB', size, color='blue')
    img_bytes = BytesIO()
    img.save(img_bytes, format=format)
    img_bytes.seek(0)
    return img_bytes

def test_health_check():
    """헬스 체크 테스트"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_generate_profile_success():
    """프로필 생성 성공 테스트"""
    img = create_test_image()
    response = client.post(
        "/api/generate",
        files={"image": ("test.jpg", img, "image/jpeg")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "image_url" in data
    assert data["image_url"].startswith("data:image/")

def test_generate_profile_no_file():
    """파일 없이 요청"""
    response = client.post("/api/generate")
    assert response.status_code == 422  # Unprocessable Entity

def test_generate_profile_invalid_file_type():
    """잘못된 파일 형식"""
    response = client.post(
        "/api/generate",
        files={"image": ("test.txt", b"not an image", "text/plain")}
    )
    assert response.status_code == 415

def test_generate_profile_file_too_large():
    """파일 크기 초과 테스트"""
    # 11MB 이미지 생성 (제한: 10MB)
    large_img = create_test_image(size=(4000, 4000))
    response = client.post(
        "/api/generate",
        files={"image": ("large.jpg", large_img, "image/jpeg")}
    )
    assert response.status_code == 413  # Request Entity Too Large

def test_generate_profile_empty_file():
    """빈 파일 업로드"""
    response = client.post(
        "/api/generate",
        files={"image": ("empty.jpg", b"", "image/jpeg")}
    )
    assert response.status_code == 400
```

**3) 테스트 실행**

```bash
# 전체 테스트 실행
pytest tests/ -v

# 커버리지와 함께 실행
pytest tests/ --cov=app --cov-report=html

# 특정 테스트만 실행
pytest tests/test_generate.py::test_health_check -v
```

### 4.2 Dockerfile 작성

**1) 프로덕션용 Dockerfile**

```dockerfile
# Dockerfile
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY . .

# 비root 사용자 생성 (보안)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# 포트 노출
EXPOSE 8000

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health')"

# 서버 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

**2) .dockerignore 파일**

```bash
# .dockerignore
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.gitignore
.mypy_cache
.pytest_cache
.hypothesis
tests/
*.md
Dockerfile
.dockerignore
```

**3) Docker Compose 설정 (개발용)**

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - DEBUG=True
    volumes:
      - ./app:/app/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4.3 Docker 빌드 및 실행

**1) 이미지 빌드**

```bash
# 이미지 빌드
docker build -t ai-profile-generator:latest .

# 빌드 캐시 없이 빌드
docker build --no-cache -t ai-profile-generator:latest .

# 멀티 플랫폼 빌드 (M1/M2 Mac)
docker buildx build --platform linux/amd64,linux/arm64 -t ai-profile-generator:latest .
```

**2) 컨테이너 실행**

```bash
# 기본 실행
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=your_api_key \
  ai-profile-generator:latest

# 백그라운드 실행
docker run -d \
  --name ai-profile-api \
  -p 8000:8000 \
  -e GEMINI_API_KEY=your_api_key \
  ai-profile-generator:latest

# 환경 변수 파일 사용
docker run -p 8000:8000 \
  --env-file .env \
  ai-profile-generator:latest

# 로그 확인
docker logs -f ai-profile-api

# 컨테이너 중지
docker stop ai-profile-api

# 컨테이너 삭제
docker rm ai-profile-api
```

**3) Docker Compose로 실행**

```bash
# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 중지
docker-compose down

# 볼륨 포함 완전 삭제
docker-compose down -v
```

### 4.4 Docker 이미지 최적화

**1) 멀티 스테이지 빌드**

```dockerfile
# Dockerfile.optimized
# 빌드 스테이지
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libjpeg-dev zlib1g-dev

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 실행 스테이지
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libjpeg62-turbo && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**2) 이미지 크기 비교**

```bash
# 일반 빌드
docker build -t ai-profile:normal -f Dockerfile .
docker images ai-profile:normal

# 최적화 빌드
docker build -t ai-profile:optimized -f Dockerfile.optimized .
docker images ai-profile:optimized

# 예상 결과:
# normal:     ~500MB
# optimized:  ~200MB
```

## 5. 프로덕션 고려사항

### 5.1 성능 최적화

**1) Uvicorn 워커 설정**

```bash
# 단일 워커 (개발)
uvicorn main:app --host 0.0.0.0 --port 8000

# 멀티 워커 (프로덕션)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Gunicorn + Uvicorn (권장)
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

**2) 요청 타임아웃 설정**

```python
# app/config.py 수정
class Settings(BaseSettings):
    # 추가 설정
    request_timeout: int = 90  # 90초
    gemini_timeout: int = 60   # Gemini API 타임아웃
```

**3) 동시성 제한**

```python
# app/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# main.py에 적용
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 엔드포인트에 제한 적용
@app.post("/api/generate")
@limiter.limit("10/minute")  # 분당 10회 제한
async def generate_profile(...):
    ...
```

### 5.2 보안 강화

**1) HTTPS 강제**

```python
# main.py
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

if not settings.debug:
    app.add_middleware(HTTPSRedirectMiddleware)
```

**2) API 키 검증 미들웨어**

```python
# app/middleware/auth.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 헬스 체크는 제외
        if request.url.path == "/api/health":
            return await call_next(request)
        
        # API 키 검증 (선택사항)
        api_key = request.headers.get("X-API-Key")
        if api_key != settings.api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        return await call_next(request)
```

**3) 입력 데이터 sanitization**

```python
# app/utils/sanitizers.py
import re
from PIL import Image
from io import BytesIO

def sanitize_filename(filename: str) -> str:
    """파일명 sanitize"""
    # 위험한 문자 제거
    return re.sub(r'[^\w\-_.]', '', filename)

def validate_image_content(content: bytes) -> bool:
    """이미지 내용 검증"""
    try:
        img = Image.open(BytesIO(content))
        img.verify()  # 이미지 무결성 확인
        return True
    except Exception:
        return False
```

### 5.3 모니터링 & 로깅

**1) 구조화된 로깅**

```python
# app/utils/logger.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# main.py에서 사용
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.root.addHandler(handler)
```

**2) 요청/응답 로깅**

```python
# app/middleware/logging.py
import time
from fastapi import Request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # 요청 로깅
    logger.info(f"Request: {request.method} {request.url.path}")
    
    # 응답 처리
    response = await call_next(request)
    
    # 응답 시간 로깅
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} ({process_time:.2f}s)")
    
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

**3) 에러 추적**

```python
# requirements.txt에 추가
# sentry-sdk[fastapi]==1.40.0

# main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

if not settings.debug:
    sentry_sdk.init(
        dsn="https://your-sentry-dsn",
        integrations=[FastApiIntegration()],
        traces_sample_rate=1.0,
    )
```

### 5.4 비용 최적화

**1) Gemini API 사용량 추적**

```python
# app/services/gemini_client.py
import time
from collections import defaultdict

class UsageTracker:
    def __init__(self):
        self.requests = defaultdict(int)
        self.start_time = time.time()
    
    def track_request(self, model: str):
        self.requests[model] += 1
    
    def get_stats(self):
        elapsed = time.time() - self.start_time
        return {
            "requests": dict(self.requests),
            "elapsed_seconds": elapsed,
            "requests_per_minute": sum(self.requests.values()) / (elapsed / 60)
        }

usage_tracker = UsageTracker()

# generate_profile 메서드에서
async def generate_profile(self, image_bytes: bytes) -> str:
    usage_tracker.track_request(self.model)
    # ... 기존 코드
```

**2) 이미지 캐싱 (선택사항)**

```python
# app/utils/cache.py
from functools import lru_cache
import hashlib

def get_image_hash(image_bytes: bytes) -> str:
    """이미지 해시 생성"""
    return hashlib.sha256(image_bytes).hexdigest()

# Redis 캐싱 예시
from redis import Redis

redis_client = Redis(host='localhost', port=6379, db=0)

async def get_cached_result(image_hash: str) -> str:
    """캐시에서 결과 조회"""
    return redis_client.get(f"profile:{image_hash}")

async def cache_result(image_hash: str, result: str, ttl: int = 3600):
    """결과 캐싱 (1시간)"""
    redis_client.setex(f"profile:{image_hash}", ttl, result)
```

### 5.5 배포 체크리스트

**프로덕션 배포 전 확인사항:**

```markdown
## 환경 설정
- [ ] .env 파일에 프로덕션 API 키 설정
- [ ] DEBUG=False 설정
- [ ] ALLOWED_ORIGINS 프로덕션 도메인 설정
- [ ] API 키 권한 제한 설정

## 보안
- [ ] HTTPS 활성화
- [ ] CORS 설정 확인
- [ ] Rate limiting 설정
- [ ] 파일 업로드 제한 확인 (10MB)
- [ ] API 키를 환경 변수로 관리

## 성능
- [ ] Uvicorn 워커 수 설정 (CPU 코어 수 고려)
- [ ] 타임아웃 설정 (90초)
- [ ] 헬스 체크 엔드포인트 동작 확인

## 모니터링
- [ ] 로깅 설정 확인
- [ ] 에러 추적 설정 (Sentry)
- [ ] 메트릭 수집 설정

## 테스트
- [ ] 전체 테스트 통과 (pytest)
- [ ] 부하 테스트 완료
- [ ] 에러 시나리오 테스트

## Docker
- [ ] 이미지 빌드 성공
- [ ] 컨테이너 정상 실행
- [ ] 헬스 체크 동작 확인
```

## 6. 결론

### 6.1 Express vs FastAPI 최종 비교

| 측면 | Express (원본) | FastAPI (구현) |
|------|---------------|---------------|
| 코드 라인 수 | ~400 lines | ~300 lines |
| 파일 업로드 | Busboy (복잡) | 내장 (간단) |
| 타입 안정성 | 수동 검증 | Pydantic 자동 |
| API 문서 | 수동 작성 | 자동 생성 |
| 비동기 처리 | Promise/async | async/await |
| 개발 속도 | 중간 | 빠름 |
| 성능 | 좋음 | 매우 좋음 |

### 6.2 핵심 구현 사항

✅ **FastAPI 기반 백엔드**
- 자동 데이터 검증 (Pydantic)
- OpenAPI 문서 자동 생성 (http://localhost:8000/docs)
- 비동기 파일 처리

✅ **Google Gemini 연동**
- google-genai SDK
- 스트리밍 응답 처리
- 전문가급 프로필 변환 (3:4 비율)

✅ **프로덕션 준비**
- 에러 핸들링 (400, 413, 415, 500)
- 구조화된 로깅
- Docker 컨테이너화
- 성능 최적화 (멀티 워커)

✅ **보안**
- MIME 타입 검증
- 파일 크기 제한 (10MB)
- CORS 설정
- API 키 보호

### 6.3 프로젝트 구조 요약

```
ai-profile-service/
├── main.py                 # FastAPI 앱 (100줄)
├── app/
│   ├── config.py          # 설정 (50줄)
│   ├── models/schemas.py  # Pydantic 모델 (30줄)
│   ├── services/
│   │   └── gemini_client.py  # Gemini 클라이언트 (80줄)
│   ├── routers/
│   │   └── generate.py    # API 엔드포인트 (60줄)
│   └── utils/
│       ├── exceptions.py  # 커스텀 예외 (40줄)
│       └── validators.py  # 검증 함수 (50줄)
├── tests/                 # 테스트 코드
├── Dockerfile            # 컨테이너화
└── requirements.txt      # 의존성

총 코드: ~410줄 (Express 대비 유사)
복잡도: 낮음 (모듈화로 유지보수 용이)
```

### 6.4 성능 지표

**벤치마크 결과 (예상):**

| 지표 | Express | FastAPI |
|------|---------|---------|
| 요청 처리 시간 | ~3.5초 | ~3.2초 |
| 동시 요청 처리 | 10 req/s | 15 req/s |
| 메모리 사용량 | ~150MB | ~120MB |
| Docker 이미지 | ~500MB | ~200MB (최적화) |

### 6.5 확장 가능성

**단기 확장:**
- 이미지 히스토리 저장 (SQLite/PostgreSQL)
- 사용자 인증 (JWT)
- 배치 처리 (여러 이미지 동시)

**장기 확장:**
- 실시간 진행상황 (WebSocket)
- 다양한 스타일 옵션 (비즈니스/캐주얼/아티스틱)
- 얼굴 인식 및 자동 크롭
- 배경 제거 및 교체
- 마이크로서비스 아키텍처 (API Gateway + 여러 서비스)

### 6.6 학습 포인트

이 프로젝트를 통해 배운 것:

1. **FastAPI 핵심 개념**
   - Pydantic 모델을 활용한 자동 검증
   - 비동기 파일 업로드 처리
   - 자동 API 문서 생성

2. **Google Gemini API**
   - 이미지 생성 모델 사용법
   - 스트리밍 응답 처리
   - 프롬프트 엔지니어링

3. **프로덕션 개발**
   - 에러 핸들링 전략
   - 보안 모범 사례
   - Docker 컨테이너화
   - 성능 최적화

4. **Node.js → Python 마이그레이션**
   - Express 패턴을 FastAPI로 변환
   - 비동기 처리 차이점
   - 생태계 차이점

### 6.7 참고 자료

**공식 문서:**
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Google Gemini API](https://ai.google.dev/docs)
- [Pydantic 문서](https://docs.pydantic.dev/)
- [Uvicorn 문서](https://www.uvicorn.org/)

**원본 프로젝트:**
- [Express 버전 코드](https://github.com/youtube-jocoding/app-in-toss-ai-photo-studio-example)

**추가 학습:**
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
- [Python AsyncIO](https://docs.python.org/3/library/asyncio.html)

---

축하합니다! Express에서 FastAPI로 성공적으로 마이그레이션했습니다! 🎉

이제 `python main.py`로 서버를 실행하고 http://localhost:8000/docs에서 API를 테스트해보세요!

### 1.1 프로젝트 개요

Google의 Gemini Nano 모델을 활용한 이미지 생성 서비스를 마이크로서비스 아키텍처(MSA)로 구축하는 실전 가이드입니다.

**프로젝트 목표:**
- 🎨 Gemini Nano를 활용한 AI 이미지 생성
- 🏗️ 확장 가능한 MSA 구조
- ⚡ FastAPI 기반 고성능 API
- ☁️ Google Cloud Platform 완전 활용
- 🐳 Docker & Kubernetes 배포
- 📊 실시간 모니터링 및 로깅

**비즈니스 시나리오:**

여러 프로젝트에서 AI 이미지 생성 기능이 필요할 때, 각 프로젝트마다 개별 구현하는 대신 독립적인 마이크로서비스로 분리하여:
- 코드 재사용성 증대
- 독립적인 스케일링
- 다른 서비스에 영향 없이 업데이트
- API를 통한 간단한 통합

### 1.2 마이크로서비스 아키텍처 (MSA)란?

**모놀리식 vs MSA:**

```
[ 모놀리식 (Monolithic) ]
┌─────────────────────────────┐
│  Single Application         │
│  ┌───────┐ ┌──────┐        │
│  │  UI   │ │ Auth │        │
│  ├───────┤ ├──────┤        │
│  │ Logic │ │ Image│        │
│  ├───────┤ ├──────┤        │
│  │  DB   │ │ File │        │
│  └───────┘ └──────┘        │
└─────────────────────────────┘

문제점:
- 한 기능 수정 시 전체 배포
- 스케일링 어려움
- 기술 스택 제약
- 장애 시 전체 다운

[ 마이크로서비스 (MSA) ]
┌──────────┐   ┌──────────┐   ┌──────────┐
│ Gateway  │───│  Auth    │   │  Image   │
│ Service  │   │ Service  │   │ Service  │
└──────────┘   └──────────┘   └──────────┘
      │              │               │
      └──────────────┴───────────────┘
                     │
           ┌──────────────────┐
           │  Storage Service │
           └──────────────────┘

장점:
- 독립적인 배포
- 서비스별 스케일링
- 기술 스택 자유
- 장애 격리
```

### 1.3 시스템 아키텍처

우리가 구축할 MSA 구조:

```
                    [ 클라이언트 ]
                          ↓
                  ┌───────────────┐
                  │ API Gateway   │  FastAPI
                  │ (포트 8000)   │  - 인증
                  └───────────────┘  - 라우팅
                          ↓          - Rate Limit
        ┌─────────────────┴─────────────────┐
        ↓                                    ↓
┌───────────────┐                  ┌───────────────┐
│ Image Gen     │                  │ Storage       │
│ Service       │                  │ Service       │
│ (포트 8001)   │──────────────→  │ (포트 8002)   │
│               │  이미지 저장     │               │
│ - Gemini API  │                  │ - GCS Upload  │
│ - 프롬프트 처리│                  │ - 이미지 조회 │
└───────────────┘                  └───────────────┘
        ↓                                    ↓
┌───────────────┐                  ┌───────────────┐
│ Gemini Nano   │                  │ Google Cloud  │
│ API (GCP)     │                  │ Storage       │
└───────────────┘                  └───────────────┘

[ 공통 인프라 ]
- Cloud Pub/Sub (비동기 메시징)
- Cloud SQL (메타데이터)
- Cloud Logging (로그 수집)
- Cloud Monitoring (메트릭)
- Secret Manager (API 키 관리)
```

### 1.4 기술 스택

**Backend Framework:**
```python
- FastAPI 0.104.0  # 고성능 비동기 웹 프레임워크
- Pydantic 2.5.0   # 데이터 검증
- Uvicorn 0.24.0   # ASGI 서버
```

**Google Cloud Services:**
```
- Vertex AI (Gemini Nano API)
- Cloud Storage (이미지 저장)
- Cloud Pub/Sub (메시지 큐)
- Cloud SQL (PostgreSQL)
- Cloud Logging & Monitoring
- Secret Manager
- Google Kubernetes Engine (GKE)
```

**인프라:**
```
- Docker 24.0
- Kubernetes 1.28
- Nginx (Ingress)
- Redis (캐싱)
```

**개발 도구:**
```python
- Poetry (패키지 관리)
- Pytest (테스트)
- Black (코드 포맷팅)
- Ruff (린팅)
```

### 1.5 주요 기능

**1) API Gateway (게이트웨이 서비스)**
- JWT 기반 인증
- API 라우팅 및 프록시
- Rate Limiting (요청 제한)
- 로깅 및 모니터링
- CORS 설정

**2) Image Generation Service (이미지 생성 서비스)**
- Gemini Nano API 연동
- 텍스트 → 이미지 생성
- 프롬프트 최적화
- 배치 생성 지원
- 비동기 처리

**3) Storage Service (스토리지 서비스)**
- Google Cloud Storage 업로드
- 이미지 메타데이터 관리
- 이미지 조회 및 다운로드
- CDN 연동
- 썸네일 생성

**4) 공통 기능**
- 헬스 체크
- 메트릭 수집
- 분산 트레이싱
- 에러 핸들링

### 1.6 프로젝트 구조 미리보기

```
image-generation-msa/
├── docker-compose.yml
├── kubernetes/
│   ├── gateway-deployment.yaml
│   ├── image-service-deployment.yaml
│   ├── storage-service-deployment.yaml
│   └── ingress.yaml
├── services/
│   ├── gateway/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── routers/
│   │   │   ├── middleware/
│   │   │   └── config.py
│   │   └── tests/
│   ├── image_service/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── services/
│   │   │   │   └── gemini_client.py
│   │   │   └── models/
│   │   └── tests/
│   └── storage_service/
│       ├── Dockerfile
│       ├── pyproject.toml
│       ├── app/
│       │   ├── main.py
│       │   ├── services/
│       │   │   └── gcs_client.py
│       │   └── models/
│       └── tests/
├── shared/
│   ├── auth.py
│   ├── logging.py
│   └── models.py
└── README.md
```

### 1.7 예상 비용 (GCP)

**개발 환경 (월):**
```
- Gemini Nano API: $0 (무료 티어 포함)
- Cloud Storage: ~$0.50 (1GB)
- Cloud Run / GKE: ~$20-50
- Cloud SQL: ~$10 (db-f1-micro)
- 기타 서비스: ~$5
총: $35-65/month
```

**프로덕션 환경 (예상):**
```
- Gemini API: 사용량 기반 (~$100-500)
- GKE Cluster: ~$200-500
- Cloud Storage: ~$5-20
- Load Balancer: ~$20
- Cloud SQL: ~$50-100
총: $375-1,140/month
```

### 1.8 이 글에서 다룰 내용

각 단계를 실제 코드와 함께 구현합니다:

1. ✅ **GCP 설정** - 프로젝트, API, 인증
2. ✅ **MSA 프로젝트 구조** - 디렉토리, 공통 모듈
3. ✅ **API Gateway** - 라우팅, 인증, Rate Limit
4. ✅ **Image Generation Service** - Gemini Nano 연동
5. ✅ **Storage Service** - GCS 업로드/조회
6. ✅ **서비스 간 통신** - HTTP/gRPC, Pub/Sub
7. ✅ **Docker 컨테이너화** - Dockerfile, docker-compose
8. ✅ **Kubernetes 배포** - GKE, Deployment, Service
9. ✅ **모니터링** - Logging, Monitoring
10. ✅ **테스트** - 통합 테스트, 부하 테스트

**실습 결과물:**
- 완전히 작동하는 MSA 시스템
- 프로덕션 준비 완료 코드
- Kubernetes 배포 설정
- CI/CD 파이프라인

시작하겠습니다! 🚀

## 2. GCP 설정 및 Gemini API 준비

### 2.1 Google Cloud Platform 프로젝트 생성

**1) GCP 콘솔 접속**

[Google Cloud Console](https://console.cloud.google.com) 접속 및 로그인

```
1. https://console.cloud.google.com 접속
2. 좌측 상단 프로젝트 선택 드롭다운
3. "새 프로젝트" 클릭
```

**2) 프로젝트 설정**

```
프로젝트 이름: image-generation-msa
프로젝트 ID: image-gen-msa-123456 (전역 고유)
조직: (선택사항)
위치: (선택사항)
```

**3) 결제 계정 연결**

```
1. 탐색 메뉴 → 결제
2. 결제 계정 연결
3. 무료 크레딧 $300 사용 가능 (신규 사용자)
```

⚠️ **중요**: 실습 후 리소스를 삭제하여 불필요한 과금을 방지하세요!

### 2.2 필수 API 활성화

**1) gcloud CLI 설치**

```bash
# macOS
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Ubuntu/Debian
sudo apt-get install google-cloud-sdk

# Windows
# https://cloud.google.com/sdk/docs/install 에서 설치 프로그램 다운로드

# 인증
gcloud init
gcloud auth login

# 프로젝트 설정
gcloud config set project image-gen-msa-123456
```

**2) 필요한 API 활성화**

```bash
# Vertex AI (Gemini API)
gcloud services enable aiplatform.googleapis.com

# Cloud Storage
gcloud services enable storage-api.googleapis.com
gcloud services enable storage.googleapis.com

# Cloud Pub/Sub
gcloud services enable pubsub.googleapis.com

# Cloud SQL
gcloud services enable sqladmin.googleapis.com

# Container Registry
gcloud services enable containerregistry.googleapis.com

# Kubernetes Engine
gcloud services enable container.googleapis.com

# Cloud Logging & Monitoring
gcloud services enable logging.googleapis.com
gcloud services enable monitoring.googleapis.com

# Secret Manager
gcloud services enable secretmanager.googleapis.com

# 모든 API 한 번에 활성화
gcloud services enable \
  aiplatform.googleapis.com \
  storage-api.googleapis.com \
  storage.googleapis.com \
  pubsub.googleapis.com \
  sqladmin.googleapis.com \
  containerregistry.googleapis.com \
  container.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  secretmanager.googleapis.com
```

API 활성화 확인:

```bash
gcloud services list --enabled
```

### 2.3 서비스 계정 및 인증 키 생성

**1) 서비스 계정 생성**

```bash
# 서비스 계정 생성
gcloud iam service-accounts create image-gen-sa \
  --display-name="Image Generation Service Account" \
  --description="Service account for image generation MSA"

# 프로젝트 ID 환경 변수
PROJECT_ID=$(gcloud config get-value project)

# 서비스 계정 이메일
SERVICE_ACCOUNT="image-gen-sa@${PROJECT_ID}.iam.gserviceaccount.com"
```

**2) IAM 권한 부여**

```bash
# Vertex AI 사용 권한
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/aiplatform.user"

# Cloud Storage 관리 권한
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/storage.admin"

# Pub/Sub 게시/구독 권한
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/pubsub.editor"

# Cloud SQL 클라이언트 권한
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/cloudsql.client"

# Secret Manager 접근 권한
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

# Logging 쓰기 권한
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/logging.logWriter"
```

**3) 인증 키 다운로드**

```bash
# 키 파일 생성
gcloud iam service-accounts keys create ~/gcp-key.json \
  --iam-account=$SERVICE_ACCOUNT

# 환경 변수 설정
export GOOGLE_APPLICATION_CREDENTIALS=~/gcp-key.json

# .bashrc 또는 .zshrc에 추가
echo 'export GOOGLE_APPLICATION_CREDENTIALS=~/gcp-key.json' >> ~/.bashrc
```

⚠️ **보안 주의**: 키 파일을 절대 Git에 커밋하지 마세요!

```bash
# .gitignore에 추가
echo "gcp-key.json" >> .gitignore
echo "*.json" >> .gitignore
echo "!package.json" >> .gitignore
```

### 2.4 Gemini API 설정

**1) Vertex AI API 확인**

```bash
# API 활성화 확인
gcloud services list --enabled | grep aiplatform
```

**2) Gemini 모델 사용 가능 확인**

```bash
# 사용 가능한 모델 목록 조회
gcloud ai models list \
  --region=us-central1 \
  --filter="displayName:gemini"
```

**3) Python SDK 설치 및 테스트**

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Vertex AI SDK 설치
pip install google-cloud-aiplatform google-cloud-storage

# 테스트 스크립트 작성
cat > test_gemini.py << 'EOF'
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

# 프로젝트 초기화
PROJECT_ID = "image-gen-msa-123456"  # 본인의 프로젝트 ID
LOCATION = "us-central1"

vertexai.init(project=PROJECT_ID, location=LOCATION)

# Gemini 이미지 생성 모델
model = ImageGenerationModel.from_pretrained("imagegeneration@006")

# 테스트 이미지 생성
response = model.generate_images(
    prompt="A beautiful sunset over the ocean with sailboats",
    number_of_images=1,
)

# 결과 출력
for i, image in enumerate(response.images):
    print(f"Image {i+1} generated successfully")
    image.save(f"test_image_{i+1}.png")

print("✅ Gemini API 테스트 성공!")
EOF

# 실행
python test_gemini.py
```

### 2.5 Cloud Storage 버킷 생성

**1) 버킷 생성**

```bash
# 버킷 이름 (전역 고유)
BUCKET_NAME="${PROJECT_ID}-images"

# 버킷 생성 (멀티 리전)
gcloud storage buckets create gs://${BUCKET_NAME} \
  --location=us \
  --uniform-bucket-level-access

# 또는 단일 리전 (비용 절감)
gcloud storage buckets create gs://${BUCKET_NAME} \
  --location=us-central1 \
  --uniform-bucket-level-access
```

**2) CORS 설정 (웹에서 직접 액세스 시)**

```bash
# cors.json 생성
cat > cors.json << 'EOF'
[
  {
    "origin": ["*"],
    "method": ["GET", "HEAD", "PUT", "POST"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
EOF

# CORS 적용
gcloud storage buckets update gs://${BUCKET_NAME} --cors-file=cors.json
```

**3) 버킷 권한 설정**

```bash
# 공개 읽기 (선택사항 - 이미지 공개 시)
gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
  --member=allUsers \
  --role=roles/storage.objectViewer

# 또는 서비스 계정만 접근
gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role=roles/storage.admin
```

### 2.6 Cloud Pub/Sub 토픽 생성

비동기 이미지 생성을 위한 메시지 큐:

```bash
# 토픽 생성
gcloud pubsub topics create image-generation-requests
gcloud pubsub topics create image-generation-results

# 구독 생성
gcloud pubsub subscriptions create image-gen-sub \
  --topic=image-generation-requests \
  --ack-deadline=60

gcloud pubsub subscriptions create image-result-sub \
  --topic=image-generation-results \
  --ack-deadline=30
```

### 2.7 Cloud SQL 인스턴스 생성 (메타데이터 저장)

**1) PostgreSQL 인스턴스 생성**

```bash
# 인스턴스 생성 (개발용)
gcloud sql instances create image-gen-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=your-secure-password

# 프로덕션용 (권장)
gcloud sql instances create image-gen-db-prod \
  --database-version=POSTGRES_15 \
  --tier=db-n1-standard-2 \
  --region=us-central1 \
  --availability-type=REGIONAL \
  --backup \
  --root-password=your-very-secure-password
```

**2) 데이터베이스 생성**

```bash
# 데이터베이스 생성
gcloud sql databases create imagedb \
  --instance=image-gen-db

# 사용자 생성
gcloud sql users create appuser \
  --instance=image-gen-db \
  --password=app-user-password
```

**3) 연결 확인**

```bash
# Cloud SQL Proxy 설치
wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy
chmod +x cloud_sql_proxy

# 인스턴스 연결 정보
INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe image-gen-db \
  --format="value(connectionName)")

# 프록시 실행
./cloud_sql_proxy -instances=${INSTANCE_CONNECTION_NAME}=tcp:5432 &

# psql로 연결 테스트
psql "host=127.0.0.1 port=5432 dbname=imagedb user=appuser password=app-user-password"
```

### 2.8 Secret Manager에 비밀 저장

```bash
# API 키 저장
echo -n "your-gemini-api-key" | \
  gcloud secrets create gemini-api-key --data-file=-

# 데이터베이스 비밀번호
echo -n "app-user-password" | \
  gcloud secrets create db-password --data-file=-

# JWT 시크릿
openssl rand -base64 32 | \
  gcloud secrets create jwt-secret --data-file=-

# 비밀 접근 권한 부여
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding db-password \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

### 2.9 환경 변수 정리

로컬 개발용 `.env` 파일:

```bash
# .env
# GCP 설정
GCP_PROJECT_ID=image-gen-msa-123456
GCP_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=./gcp-key.json

# Gemini API
GEMINI_MODEL=imagegeneration@006

# Cloud Storage
GCS_BUCKET_NAME=image-gen-msa-123456-images

# Cloud SQL
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=imagedb
DB_USER=appuser
DB_PASSWORD=app-user-password

# Pub/Sub
PUBSUB_TOPIC_REQUESTS=image-generation-requests
PUBSUB_TOPIC_RESULTS=image-generation-results

# 서비스 URL (로컬)
GATEWAY_URL=http://localhost:8000
IMAGE_SERVICE_URL=http://localhost:8001
STORAGE_SERVICE_URL=http://localhost:8002

# JWT
JWT_SECRET=your-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600

# Redis
REDIS_URL=redis://localhost:6379

# 로깅
LOG_LEVEL=INFO
```

### 2.10 비용 모니터링 설정

**1) 예산 알림 설정**

```bash
# 예산 생성 (월 $50)
gcloud billing budgets create \
  --billing-account=YOUR-BILLING-ACCOUNT-ID \
  --display-name="Image Gen MSA Budget" \
  --budget-amount=50 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

**2) 비용 대시보드 확인**

GCP Console → 결제 → 비용 관리

GCP 설정이 완료되었습니다! 다음 섹션에서는 MSA 프로젝트 구조를 설계하겠습니다.

## 3. MSA 프로젝트 구조 설계

### 3.1 전체 디렉토리 구조

```bash
# 프로젝트 생성
mkdir image-generation-msa
cd image-generation-msa

# 디렉토리 구조 생성
mkdir -p services/{gateway,image_service,storage_service}/{app,tests}
mkdir -p shared kubernetes scripts
```

완성된 구조:

```
image-generation-msa/
├── .env
├── .gitignore
├── docker-compose.yml
├── README.md
├── services/
│   ├── gateway/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── routers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── images.py
│   │   │   │   └── health.py
│   │   │   ├── middleware/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py
│   │   │   │   └── rate_limit.py
│   │   │   └── models/
│   │   │       └── __init__.py
│   │   └── tests/
│   ├── image_service/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   └── gemini_client.py
│   │   │   └── models/
│   │   │       ├── __init__.py
│   │   │       └── schemas.py
│   │   └── tests/
│   └── storage_service/
│       ├── Dockerfile
│       ├── pyproject.toml
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── config.py
│       │   ├── services/
│       │   │   ├── __init__.py
│       │   │   └── gcs_client.py
│       │   └── models/
│       │       ├── __init__.py
│       │       └── schemas.py
│       └── tests/
├── shared/
│   ├── __init__.py
│   ├── auth.py
│   ├── logging_config.py
│   ├── exceptions.py
│   └── models.py
└── kubernetes/
    ├── gateway-deployment.yaml
    ├── image-service-deployment.yaml
    ├── storage-service-deployment.yaml
    ├── ingress.yaml
    └── configmap.yaml
```

### 3.2 공통 모듈 (shared)

```python
# shared/models.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ImageStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    num_images: int = Field(default=1, ge=1, le=4)
    size: str = Field(default="1024x1024")
    style: Optional[str] = None
    negative_prompt: Optional[str] = None

class ImageGenerationResponse(BaseModel):
    task_id: str
    status: ImageStatus
    images: List[str] = []
    created_at: datetime
    completed_at: Optional[datetime] = None

# shared/logging_config.py
import logging
from google.cloud import logging as cloud_logging

def setup_logging(service_name: str):
    """Cloud Logging 설정"""
    client = cloud_logging.Client()
    client.setup_logging()
    
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)
    return logger

# shared/auth.py
from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## 4. API Gateway 구현

### 4.1 Gateway 서비스 구조

```python
# services/gateway/pyproject.toml
[tool.poetry]
name = "gateway"
version = "0.1.0"
description = "API Gateway for Image Generation MSA"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
httpx = "^0.25.0"
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
redis = "^5.0.0"

# services/gateway/app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from contextlib import asynccontextmanager

from .routers import images, health
from .middleware.rate_limit import RateLimitMiddleware
from ..shared.logging_config import setup_logging

logger = setup_logging("gateway")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행"""
    app.state.http_client = httpx.AsyncClient()
    logger.info("Gateway service started")
    yield
    await app.state.http_client.aclose()
    logger.info("Gateway service stopped")

app = FastAPI(
    title="Image Generation Gateway",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting
app.add_middleware(RateLimitMiddleware)

# 라우터 등록
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(images.router, prefix="/api/v1/images", tags=["images"])

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# services/gateway/app/routers/images.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
import httpx

from ...shared.auth import verify_token
from ...shared.models import ImageGenerationRequest, ImageGenerationResponse

router = APIRouter()

IMAGE_SERVICE_URL = "http://image-service:8001"
STORAGE_SERVICE_URL = "http://storage-service:8002"

@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(
    request: ImageGenerationRequest,
    current_user: dict = Depends(verify_token)
):
    """이미지 생성 요청"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{IMAGE_SERVICE_URL}/generate",
            json=request.dict(),
            timeout=300.0
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        return response.json()

@router.get("/{task_id}")
async def get_image_status(
    task_id: str,
    current_user: dict = Depends(verify_token)
):
    """이미지 생성 상태 조회"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{IMAGE_SERVICE_URL}/status/{task_id}")
        
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return response.json()
```

## 5. Image Generation Service 구현

```python
# services/image_service/app/services/gemini_client.py
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from typing import List
import asyncio
from concurrent.futures import ThreadPoolExecutor

class GeminiImageGenerator:
    def __init__(self, project_id: str, location: str):
        vertexai.init(project=project_id, location=location)
        self.model = ImageGenerationModel.from_pretrained("imagegeneration@006")
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def generate_images(
        self,
        prompt: str,
        num_images: int = 1,
        negative_prompt: str = None
    ) -> List[bytes]:
        """비동기 이미지 생성"""
        loop = asyncio.get_event_loop()
        
        def _generate():
            response = self.model.generate_images(
                prompt=prompt,
                number_of_images=num_images,
                negative_prompt=negative_prompt,
            )
            return [img._pil_image for img in response.images]
        
        images = await loop.run_in_executor(self.executor, _generate)
        return images

# services/image_service/app/main.py
from fastapi import FastAPI
from .services.gemini_client import GeminiImageGenerator
from ..shared.models import ImageGenerationRequest, ImageGenerationResponse
import uuid
from datetime import datetime

app = FastAPI(title="Image Generation Service")

generator = GeminiImageGenerator(
    project_id="image-gen-msa-123456",
    location="us-central1"
)

@app.post("/generate", response_model=ImageGenerationResponse)
async def generate_images(request: ImageGenerationRequest):
    task_id = str(uuid.uuid4())
    
    try:
        images = await generator.generate_images(
            prompt=request.prompt,
            num_images=request.num_images,
            negative_prompt=request.negative_prompt
        )
        
        # Storage Service에 업로드 (다음 섹션)
        image_urls = await upload_images_to_storage(task_id, images)
        
        return ImageGenerationResponse(
            task_id=task_id,
            status="completed",
            images=image_urls,
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
    except Exception as e:
        return ImageGenerationResponse(
            task_id=task_id,
            status="failed",
            created_at=datetime.utcnow()
        )
```

## 6. Storage Service & Docker 컨테이너화

```python
# services/storage_service/app/services/gcs_client.py
from google.cloud import storage
from typing import BinaryIO
import uuid

class GCSStorageClient:
    def __init__(self, bucket_name: str):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
    
    def upload_image(self, image_data: bytes, filename: str = None) -> str:
        """이미지 업로드"""
        if not filename:
            filename = f"{uuid.uuid4()}.png"
        
        blob = self.bucket.blob(f"images/{filename}")
        blob.upload_from_string(image_data, content_type="image/png")
        
        return blob.public_url

# services/gateway/Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --no-dev

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# docker-compose.yml (루트)
version: '3.8'

services:
  gateway:
    build: ./services/gateway
    ports:
      - "8000:8000"
    environment:
      - IMAGE_SERVICE_URL=http://image-service:8001
      - STORAGE_SERVICE_URL=http://storage-service:8002
  
  image-service:
    build: ./services/image_service
    ports:
      - "8001:8001"
    environment:
      - GCP_PROJECT_ID=${GCP_PROJECT_ID}
      - GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json
    volumes:
      - ./gcp-key.json:/app/gcp-key.json
  
  storage-service:
    build: ./services/storage_service
    ports:
      - "8002:8002"
    environment:
      - GCS_BUCKET_NAME=${GCS_BUCKET_NAME}
```

## 7. Kubernetes 배포

```yaml
# kubernetes/gateway-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway
spec:
  replicas: 2
  selector:
    matchLabels:
      app: gateway
  template:
    metadata:
      labels:
        app: gateway
    spec:
      containers:
      - name: gateway
        image: gcr.io/image-gen-msa-123456/gateway:latest
        ports:
        - containerPort: 8000
        env:
        - name: IMAGE_SERVICE_URL
          value: "http://image-service:8001"
---
apiVersion: v1
kind: Service
metadata:
  name: gateway
spec:
  selector:
    app: gateway
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer

# GKE 클러스터 생성
gcloud container clusters create image-gen-cluster \
  --num-nodes=3 \
  --machine-type=n1-standard-2 \
  --region=us-central1

# Docker 이미지 빌드 및 푸시
docker build -t gcr.io/${PROJECT_ID}/gateway:latest ./services/gateway
docker push gcr.io/${PROJECT_ID}/gateway:latest

# 배포
kubectl apply -f kubernetes/
```

## 8. 결론

이 튜토리얼에서 구축한 시스템:

**완성된 기능:**
- ✅ FastAPI 기반 MSA 아키텍처
- ✅ Gemini Nano AI 이미지 생성
- ✅ Google Cloud Platform 완전 통합
- ✅ Docker 컨테이너화
- ✅ Kubernetes 배포 준비
- ✅ 프로덕션 수준의 보안 및 인증

**확장 가능성:**
- 이미지 편집 서비스 추가
- 비디오 생성 기능
- 실시간 스트리밍
- 다중 AI 모델 지원
- Auto-scaling 설정

**참고 자료:**
- [Google Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

축하합니다! 완전한 MSA 시스템을 구축했습니다! 🎉

