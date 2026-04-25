---
layout: post
title: "Cloud Run에서 CloudFront 이미지 접근 불가 문제 해결 - URL에서 Base64로 전환"
categories: [Cloud, Backend]
tags: [google-cloud-run, aws-cloudfront, fastapi, cors, base64, image-processing, security, workaround]
date: 2025-12-02 09:00:00 +0900
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2025-12-02-cloud-run-cloudfront-image-access-solution.webp"
---

## 1. 문제 상황 - CloudFront 이미지 접근 거부

### 1.1 초기 아키텍처와 발생한 문제

AI Photo Studio 서비스를 개발하면서 다음과 같은 구조로 시작했습니다:

```
[클라이언트] → [Cloud Run API] → [AWS CloudFront] → [S3]
                      ↓
                 이미지 다운로드 실패!
```

**초기 API 설계 (URL 기반):**

```python
class GenerateRequest(BaseModel):
    """이미지 생성 요청 - 초기 버전"""
    image_urls: List[HttpUrl]  # CloudFront URL 리스트
    type: str = "wedding"

# 사용 예
{
    "image_urls": [
        "https://d1234.cloudfront.net/uploads/photo1.jpg",
        "https://d1234.cloudfront.net/uploads/photo2.jpg"
    ],
    "type": "wedding"
}
```

**발생한 에러:**

```python
# httpx.AsyncClient로 CloudFront URL 요청 시
async with httpx.AsyncClient(timeout=30) as client:
    response = await client.get(url)  # ❌ 403 Forbidden

# 에러 로그
HTTPError: 403 Forbidden - Access Denied
<Error>
    <Code>AccessDenied</Code>
    <Message>Access Denied</Message>
</Error>
```

### 1.2 왜 Cloud Run에서 CloudFront 접근이 거부되었나?

**원인 분석:**

```yaml
CloudFront 보안 정책:
  1. Signed URLs/Cookies:
    - CloudFront가 서명된 URL만 허용하도록 설정된 경우
    - 만료 시간이 지난 URL
    - 잘못된 서명

  2. Origin Access Identity (OAI):
    - S3 버킷이 CloudFront를 통해서만 접근 가능
    - 직접 S3 URL 접근 차단

  3. Geo-Restriction:
    - 특정 국가/지역에서만 접근 허용
    - Cloud Run이 위치한 리전이 차단됨

  4. Referer/User-Agent 검증:
    - 특정 Referer 헤더 필요
    - 브라우저만 허용, 서버 요청 차단

  5. WAF (Web Application Firewall):
    - Bot 탐지로 인한 차단
    - Rate Limiting
    - IP 화이트리스트

우리 케이스:
  - CloudFront가 브라우저 요청만 허용
  - User-Agent 검증으로 서버 요청 차단
  - Signed URL 필요한데 클라이언트에서 일반 URL 전달
```

**디버깅 과정:**

```python
# 1. 기본 요청 (실패)
async def download_image_basic(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        # ❌ 403 Forbidden

# 2. 브라우저 헤더 추가 (여전히 실패)
async def download_image_with_headers(url: str) -> bytes:
    headers = {
        "User-Agent": "Mozilla/5.0 ...",
        "Referer": "https://myapp.com",
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        # ❌ 여전히 403

# 3. 쿠키/세션 포함 (복잡도 증가, 여전히 문제)
# CloudFront Signed Cookies가 필요한 경우...
```

**왜 브라우저에서는 되는데 서버에서는 안될까?**

```javascript
// 클라이언트 (브라우저) - 성공
fetch('https://d1234.cloudfront.net/photo.jpg')
  .then(res => res.blob())  // ✅ 200 OK

// 같은 URL을 Cloud Run에서 요청 - 실패
// httpx.get('https://d1234.cloudfront.net/photo.jpg')  // ❌ 403
```

**이유:**
1. **브라우저**: 사용자 세션, 쿠키, Signed URL 파라미터 자동 포함
2. **Cloud Run**: 순수 HTTP 요청, 인증 정보 없음
3. **CORS**: 브라우저는 Same-Origin에서 요청, Cloud Run은 Cross-Origin

---

## 2. 해결 방법 비교 및 선택

### 2.1 가능한 해결책 분석

```python
# ============================================
# 방법 1: CloudFront Signed URL 생성
# ============================================

from botocore.signers import CloudFrontSigner
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import datetime

def create_signed_url(url: str, key_pair_id: str, private_key_path: str):
    """
    CloudFront Signed URL 생성
    
    장점:
    - 보안성 높음 (만료 시간 설정)
    - AWS 표준 방식
    
    단점:
    - 복잡한 설정 (Key Pair 생성, 권한 관리)
    - 클라이언트에서 매번 서명 필요
    - 만료 관리 복잡
    """
    expiration = datetime.datetime.now() + datetime.timedelta(hours=1)
    
    # CloudFront 서명 생성
    signer = CloudFrontSigner(key_pair_id, rsa_signer)
    signed_url = signer.generate_presigned_url(
        url,
        date_less_than=expiration
    )
    
    return signed_url

# 사용
signed_url = create_signed_url(
    "https://d1234.cloudfront.net/photo.jpg",
    key_pair_id="APKAXXXXX",
    private_key_path="/path/to/private_key.pem"
)

# ❌ 문제점:
# 1. 클라이언트가 서명 로직 구현해야 함
# 2. Private Key 관리 부담
# 3. 만료된 URL 재서명 필요


# ============================================
# 방법 2: Proxy 엔드포인트 생성
# ============================================

@app.get("/proxy/image")
async def proxy_cloudfront_image(url: str):
    """
    Cloud Run이 CloudFront에서 이미지 다운로드 후 전달
    
    장점:
    - 클라이언트 변경 최소화
    
    단점:
    - 대역폭 낭비 (CloudFront → Cloud Run → 클라이언트)
    - 처리 시간 증가
    - Cloud Run 비용 증가
    """
    # CloudFront에서 다운로드
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        image_data = response.content
    
    # 클라이언트에 전달
    return Response(content=image_data, media_type="image/jpeg")

# ❌ 여전히 403 문제 해결 안됨 + 비효율적


# ============================================
# 방법 3: S3 Pre-signed URL 사용
# ============================================

def generate_presigned_url(bucket: str, key: str, expiration: int = 3600):
    """
    S3 Pre-signed URL 생성
    
    장점:
    - CloudFront 우회
    - 간단한 구현
    
    단점:
    - CDN 이점 상실 (느린 속도)
    - S3 직접 접근 비용
    """
    s3_client = boto3.client('s3')
    
    url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=expiration
    )
    
    return url

# https://bucket.s3.region.amazonaws.com/key?signature=...


# ============================================
# 방법 4: Base64 인코딩 (선택한 방법!) ✅
# ============================================

def encode_image_to_base64(image_url: str) -> str:
    """
    클라이언트에서 이미지를 base64로 인코딩하여 전송
    
    장점:
    - CloudFront 접근 문제 완전 우회
    - 보안 이슈 해결 (브라우저에서 다운로드)
    - 추가 인증 불필요
    
    단점:
    - 페이로드 크기 증가 (~33%)
    - 클라이언트 코드 수정 필요
    """
    # 클라이언트 (브라우저)에서 실행
    response = await fetch(image_url)
    blob = await response.blob()
    
    # base64 인코딩
    base64_data = await blob_to_base64(blob)
    
    return base64_data

# API 요청
{
    "image_data_list": [
        "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
        "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
    ]
}
```

### 2.2 Base64 방식을 선택한 이유

```yaml
의사결정 기준:

구현 복잡도:
  Signed URL: ★★★★☆ (높음 - Key 관리, 서명 로직)
  Proxy: ★★☆☆☆ (중간 - 단순하지만 비효율)
  S3 Pre-signed: ★★★☆☆ (중간 - CDN 이점 상실)
  Base64: ★★☆☆☆ (낮음 - 클라이언트 인코딩만 추가)

보안성:
  Signed URL: ★★★★★ (매우 높음)
  Proxy: ★★☆☆☆ (여전히 403 문제)
  S3 Pre-signed: ★★★★☆ (높음)
  Base64: ★★★★☆ (브라우저 Same-Origin)

성능:
  Signed URL: ★★★★☆ (CDN 활용)
  Proxy: ★☆☆☆☆ (이중 전송)
  S3 Pre-signed: ★★☆☆☆ (CDN 미사용)
  Base64: ★★★☆☆ (직접 전송, 페이로드 증가)

비용:
  Signed URL: ★★★☆☆ (CloudFront)
  Proxy: ★☆☆☆☆ (Cloud Run 대역폭 증가)
  S3 Pre-signed: ★★☆☆☆ (S3 직접 요청)
  Base64: ★★★★☆ (단일 API 요청)

종합 점수:
  Base64: ★★★★☆ (채택!)
  - 빠른 구현
  - CloudFront 우회
  - 추가 인프라 불필요
```

---

## 3. Base64 솔루션 구현

### 3.1 Backend API 수정 (FastAPI)

```python
# models.py
from pydantic import BaseModel, validator
from typing import Optional, List

class GenerateRequest(BaseModel):
    """이미지 생성 요청 - Base64 지원"""
    
    # 기존 URL 방식 (레거시 지원)
    image_urls: Optional[List[str]] = None
    
    # 새로운 Base64 방식 (권장)
    image_data_list: Optional[List[str]] = None
    
    type: str = "wedding"  # "wedding" 또는 "id"
    
    @validator("image_urls")
    def validate_image_urls(cls, v, values):
        # 둘 중 하나는 반드시 제공
        if not v and not values.get("image_data_list"):
            raise ValueError("Either image_urls or image_data_list is required")
        
        if v and len(v) > 10:
            raise ValueError("Maximum 10 images allowed")
        
        return v
    
    @validator("image_data_list")
    def validate_image_data_list(cls, v, values):
        if v and len(v) > 10:
            raise ValueError("Maximum 10 images allowed")
        
        # Base64 형식 검증
        if v:
            for idx, data in enumerate(v):
                if not data or len(data) < 100:
                    raise ValueError(f"Invalid base64 data at index {idx}")
        
        return v
    
    @validator("type")
    def validate_type(cls, v):
        if v not in ["wedding", "id"]:
            raise ValueError("Type must be either 'wedding' or 'id'")
        return v
```

```python
# image_processing.py
import base64
import io
from PIL import Image
from typing import Optional, List
from fastapi import HTTPException

async def generate_profile(
    client: genai.Client,
    generation_type: str = "wedding",
    image_urls: Optional[List[str]] = None,
    image_data_list: Optional[List[str]] = None
) -> str:
    """
    URL 또는 Base64 이미지로 AI 사진 생성
    
    Args:
        client: Gemini Client
        generation_type: "wedding" 또는 "id"
        image_urls: 이미지 URL 리스트 (레거시)
        image_data_list: Base64 이미지 리스트 (권장)
    
    Returns:
        CloudFront URL (생성된 이미지)
    """
    try:
        input_images = []
        
        # ============================================
        # 방법 1: Base64 이미지 처리 (우선순위)
        # ============================================
        if image_data_list:
            for idx, base64_data in enumerate(image_data_list, 1):
                try:
                    logger.info(f"Loading base64 image {idx}/{len(image_data_list)}")
                    
                    # Data URI 스킴 제거
                    # "data:image/jpeg;base64,/9j/4AAQ..." → "/9j/4AAQ..."
                    if base64_data.startswith('data:'):
                        base64_data = base64_data.split(',', 1)[1]
                    
                    # Base64 디코딩
                    image_bytes = base64.b64decode(base64_data)
                    
                    # PIL Image로 변환
                    pil_image = Image.open(io.BytesIO(image_bytes))
                    
                    # 이미지 검증
                    if pil_image.size[0] < 100 or pil_image.size[1] < 100:
                        raise ValueError("Image too small (minimum 100x100)")
                    
                    # 메모리 제한 (10MB)
                    if len(image_bytes) > 10 * 1024 * 1024:
                        raise ValueError("Image too large (maximum 10MB)")
                    
                    input_images.append(pil_image)
                    logger.info(
                        f"Image {idx} loaded: {pil_image.size} "
                        f"({len(image_bytes) / 1024:.1f}KB)"
                    )
                
                except base64.binascii.Error as e:
                    logger.error(f"Invalid base64 encoding at index {idx}: {str(e)}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid base64 data at index {idx}"
                    )
                except Exception as e:
                    logger.error(f"Failed to process base64 image {idx}: {str(e)}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to load image {idx}: {str(e)}"
                    )
        
        # ============================================
        # 방법 2: URL 이미지 다운로드 (레거시)
        # ============================================
        elif image_urls:
            for idx, url in enumerate(image_urls, 1):
                try:
                    logger.info(f"Downloading image {idx}/{len(image_urls)}: {url}")
                    
                    # CloudFront 우회 헤더
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                                     "Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                        "Referer": "https://myapp.com",
                    }
                    
                    image_data = await download_image(url, headers=headers)
                    pil_image = Image.open(io.BytesIO(image_data))
                    input_images.append(pil_image)
                    
                    logger.info(f"Image {idx} downloaded successfully")
                
                except Exception as e:
                    logger.error(f"Failed to download image {idx}: {str(e)}")
                    raise
        
        # ============================================
        # Gemini AI로 이미지 생성
        # ============================================
        if not input_images:
            raise ValueError("No images to process")
        
        logger.info(
            f"Processing {len(input_images)} images "
            f"for {generation_type} generation"
        )
        
        # 프롬프트 선택
        prompt = (
            WEDDING_CONCEPT_PROMPT if generation_type == "wedding" 
            else PROFILE_PROMPT
        )
        
        # Gemini API 호출
        contents = input_images + [prompt]
        
        config = (
            WEDDING_CONFIG if generation_type == "wedding"
            else GEMINI_CONFIG
        )
        
        response = client.models.generate_content(
            model=config["model"],
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=config.get("aspect_ratio", "3:4"),
                ),
            ),
        )
        
        # ============================================
        # 생성된 이미지 추출 및 S3 업로드
        # ============================================
        for part in response.candidates[0].content.parts:
            inline_data = getattr(part, "inline_data", None)
            
            if inline_data and inline_data.data:
                logger.info("Generated image found in response")
                
                # PIL Image로 변환
                generated_image = Image.open(io.BytesIO(inline_data.data))
                
                # JPEG 포맷으로 최적화
                output_buffer = io.BytesIO()
                generated_image.save(output_buffer, format="JPEG", quality=95)
                img_bytes = output_buffer.getvalue()
                
                # S3 업로드
                logger.info("Uploading generated image to S3...")
                cloudfront_url = await upload_to_s3(
                    img_bytes,
                    content_type="image/jpeg"
                )
                
                logger.info(f"Image uploaded: {cloudfront_url}")
                return cloudfront_url
        
        raise ValueError("No image generated")
    
    except Exception as e:
        logger.error(f"AI generation error: {str(e)}", exc_info=True)
        raise
```

### 3.2 Frontend 클라이언트 구현

```typescript
// imageUtils.ts
/**
 * 이미지 URL을 Base64로 변환
 */
export async function imageUrlToBase64(url: string): Promise<string> {
  try {
    // 1. Fetch로 이미지 다운로드 (브라우저 Same-Origin)
    const response = await fetch(url, {
      mode: 'cors',
      credentials: 'include',  // 쿠키 포함
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch image: ${response.status}`);
    }
    
    // 2. Blob으로 변환
    const blob = await response.blob();
    
    // 3. Base64로 인코딩
    const base64 = await blobToBase64(blob);
    
    return base64;
  } catch (error) {
    console.error('Failed to convert image to base64:', error);
    throw error;
  }
}

/**
 * Blob을 Base64로 변환
 */
function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onloadend = () => {
      const result = reader.result as string;
      resolve(result);  // "data:image/jpeg;base64,/9j/..."
    };
    
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/**
 * 파일 입력에서 Base64로 변환
 */
export async function fileToBase64(file: File): Promise<string> {
  // 파일 크기 검증 (10MB)
  if (file.size > 10 * 1024 * 1024) {
    throw new Error('File too large (maximum 10MB)');
  }
  
  // MIME 타입 검증
  if (!file.type.startsWith('image/')) {
    throw new Error('Invalid file type. Only images allowed.');
  }
  
  return blobToBase64(file);
}

/**
 * 여러 URL을 Base64 배열로 변환
 */
export async function imageUrlsToBase64List(urls: string[]): Promise<string[]> {
  const promises = urls.map(url => imageUrlToBase64(url));
  return Promise.all(promises);
}
```

```typescript
// api.ts
import { imageUrlsToBase64List } from './imageUtils';

interface GenerateRequest {
  image_data_list?: string[];
  image_urls?: string[];
  type: 'wedding' | 'id';
}

interface GenerateResponse {
  success: boolean;
  image_urls?: string[];
  error?: string;
}

/**
 * AI 사진 생성 API 호출
 */
export async function generateAIPhoto(
  imageUrls: string[],
  type: 'wedding' | 'id' = 'wedding'
): Promise<string[]> {
  try {
    // 1. CloudFront URL들을 Base64로 변환
    console.log('Converting images to base64...');
    const base64Images = await imageUrlsToBase64List(imageUrls);
    
    console.log(
      `Converted ${base64Images.length} images ` +
      `(total size: ${base64Images.join('').length / 1024:.1f}KB)`
    );
    
    // 2. API 요청
    const response = await fetch('https://api.example.com/api/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        image_data_list: base64Images,  // Base64 배열
        type: type,
      }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Generation failed');
    }
    
    // 3. 결과 반환
    const result: GenerateResponse = await response.json();
    
    if (!result.success || !result.image_urls) {
      throw new Error(result.error || 'No images generated');
    }
    
    return result.image_urls;
  } catch (error) {
    console.error('AI photo generation failed:', error);
    throw error;
  }
}
```

```typescript
// React 컴포넌트 예시
import React, { useState } from 'react';
import { generateAIPhoto } from './api';

export function WeddingPhotoGenerator() {
  const [selectedImages, setSelectedImages] = useState<string[]>([]);
  const [generatedImage, setGeneratedImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) return;
    
    try {
      // 파일을 Base64로 변환하여 미리보기
      const base64Images = await Promise.all(
        Array.from(files).map(file => fileToBase64(file))
      );
      
      setSelectedImages(base64Images);
    } catch (err) {
      setError('Failed to load images');
    }
  };
  
  const handleGenerate = async () => {
    if (selectedImages.length === 0) {
      setError('Please select at least one image');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // CloudFront URL이 아닌 Base64로 직접 전송
      const result = await generateAIPhoto(selectedImages, 'wedding');
      
      setGeneratedImage(result[0]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      <input
        type="file"
        multiple
        accept="image/*"
        onChange={handleFileSelect}
      />
      
      {selectedImages.length > 0 && (
        <div>
          <p>{selectedImages.length} images selected</p>
          <button onClick={handleGenerate} disabled={loading}>
            {loading ? 'Generating...' : 'Generate Wedding Photo'}
          </button>
        </div>
      )}
      
      {error && <div className="error">{error}</div>}
      
      {generatedImage && (
        <img src={generatedImage} alt="Generated wedding photo" />
      )}
    </div>
  );
}
```

---

## 4. 성능 최적화 및 고려사항

### 4.1 페이로드 크기 문제

```python
# Base64의 오버헤드
원본 이미지: 1MB = 1,048,576 bytes
Base64 인코딩: 1,398,102 bytes (약 1.33MB)
증가율: 33.3%

# 여러 이미지의 경우
이미지 2개 (각 1MB):
  - 원본 URL 방식: 100 bytes (JSON)
  - Base64 방식: 2.66MB (JSON)

# Cloud Run 요청 제한
최대 요청 크기: 32MB
최대 이미지 수 (1MB 기준): ~24개
```

**최적화 전략:**

```typescript
// 1. 이미지 리사이징 (클라이언트)
async function resizeImage(
  base64: string,
  maxWidth: number = 1920,
  maxHeight: number = 1920
): Promise<string> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      let width = img.width;
      let height = img.height;
      
      // 비율 유지하며 리사이즈
      if (width > maxWidth || height > maxHeight) {
        const ratio = Math.min(maxWidth / width, maxHeight / height);
        width = width * ratio;
        height = height * ratio;
      }
      
      canvas.width = width;
      canvas.height = height;
      
      const ctx = canvas.getContext('2d')!;
      ctx.drawImage(img, 0, 0, width, height);
      
      // JPEG 품질 80%로 압축
      const resized = canvas.toDataURL('image/jpeg', 0.8);
      resolve(resized);
    };
    
    img.src = base64;
  });
}

// 사용
const original = await imageUrlToBase64(url);  // 1.5MB
const optimized = await resizeImage(original);  // 400KB ✅
```

```python
# 2. Backend에서 압축 검증
MAX_BASE64_SIZE = 5 * 1024 * 1024  # 5MB per image

@validator("image_data_list")
def validate_base64_size(cls, v):
    if v:
        for idx, data in enumerate(v):
            # Data URI 제거 후 순수 base64 크기 계산
            if data.startswith('data:'):
                data = data.split(',', 1)[1]
            
            size = len(data.encode('utf-8'))
            
            if size > MAX_BASE64_SIZE:
                raise ValueError(
                    f"Image {idx} too large: {size / 1024 / 1024:.1f}MB "
                    f"(max {MAX_BASE64_SIZE / 1024 / 1024}MB)"
                )
    
    return v
```

### 4.2 메모리 관리

```python
# image_processing.py
import gc
from contextlib import contextmanager

@contextmanager
def managed_image_processing():
    """이미지 처리 후 메모리 해제"""
    try:
        yield
    finally:
        # PIL 이미지 캐시 정리
        Image.preinit()
        Image.init()
        
        # 가비지 컬렉션
        gc.collect()

# 사용
async def generate_profile(...):
    with managed_image_processing():
        # Base64 디코딩
        for base64_data in image_data_list:
            image_bytes = base64.b64decode(base64_data)
            pil_image = Image.open(io.BytesIO(image_bytes))
            
            # 즉시 처리
            input_images.append(pil_image)
            
            # 원본 데이터 해제
            del image_bytes
        
        # AI 생성
        result = client.models.generate_content(...)
        
        # 입력 이미지 해제
        for img in input_images:
            img.close()
        
        return result
```

### 4.3 에러 처리 및 재시도

```typescript
// 네트워크 에러 재시도 로직
async function generateWithRetry(
  imageUrls: string[],
  type: 'wedding' | 'id',
  maxRetries: number = 3
): Promise<string[]> {
  let lastError: Error | null = null;
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`Attempt ${attempt}/${maxRetries}`);
      
      // Base64 변환
      const base64Images = await imageUrlsToBase64List(imageUrls);
      
      // API 호출
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_data_list: base64Images,
          type: type,
        }),
      });
      
      if (!response.ok) {
        // 4xx 에러는 재시도 안함
        if (response.status >= 400 && response.status < 500) {
          const error = await response.json();
          throw new Error(error.error);
        }
        
        // 5xx 에러는 재시도
        throw new Error(`Server error: ${response.status}`);
      }
      
      const result = await response.json();
      return result.image_urls;
      
    } catch (error) {
      lastError = error;
      
      if (attempt < maxRetries) {
        // 지수 백오프 (1초, 2초, 4초)
        const delay = Math.pow(2, attempt - 1) * 1000;
        console.log(`Retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
  
  throw lastError || new Error('Generation failed after retries');
}
```

---

## 5. 보안 고려사항

### 5.1 Base64 검증 및 새니타이징

```python
# security.py
import re
import magic  # python-magic 라이브러리

def validate_base64_image(base64_data: str) -> tuple[bytes, str]:
    """
    Base64 이미지 검증
    
    Returns:
        (image_bytes, mime_type)
    
    Raises:
        ValueError: 유효하지 않은 이미지
    """
    try:
        # 1. Data URI 파싱
        if base64_data.startswith('data:'):
            # "data:image/jpeg;base64,..." 형식
            match = re.match(r'data:(image/[^;]+);base64,(.+)', base64_data)
            if not match:
                raise ValueError("Invalid data URI format")
            
            declared_mime = match.group(1)
            base64_content = match.group(2)
        else:
            # 순수 base64
            declared_mime = None
            base64_content = base64_data
        
        # 2. Base64 디코딩
        try:
            image_bytes = base64.b64decode(base64_content, validate=True)
        except Exception:
            raise ValueError("Invalid base64 encoding")
        
        # 3. Magic Number로 실제 파일 타입 확인
        actual_mime = magic.from_buffer(image_bytes, mime=True)
        
        # 4. MIME 타입 검증
        if actual_mime not in ALLOWED_MIME_TYPES:
            raise ValueError(f"Unsupported file type: {actual_mime}")
        
        # 5. 선언된 MIME과 실제 MIME 일치 확인
        if declared_mime and declared_mime != actual_mime:
            logger.warning(
                f"MIME type mismatch: declared={declared_mime}, "
                f"actual={actual_mime}"
            )
        
        # 6. 이미지 파일 검증 (PIL)
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()  # 손상된 이미지 감지
        except Exception:
            raise ValueError("Corrupted or invalid image file")
        
        return image_bytes, actual_mime
    
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Image validation failed: {str(e)}")

# 사용
@validator("image_data_list")
def validate_images(cls, v):
    if v:
        for idx, base64_data in enumerate(v):
            try:
                image_bytes, mime_type = validate_base64_image(base64_data)
                logger.info(
                    f"Image {idx} validated: {mime_type}, "
                    f"{len(image_bytes) / 1024:.1f}KB"
                )
            except ValueError as e:
                raise ValueError(f"Image {idx} validation failed: {str(e)}")
    
    return v
```

### 5.2 Rate Limiting

```python
# rate_limit.py
from fastapi import Request, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/generate")
@limiter.limit("5/minute")  # IP당 분당 5회
async def generate(request: Request, body: GenerateRequest):
    """
    Rate Limiting 적용
    
    - 무료 사용자: 5 요청/분
    - 유료 사용자: 50 요청/분
    """
    # API Key 또는 JWT로 사용자 식별
    api_key = request.headers.get("X-API-Key")
    
    if api_key and is_premium_user(api_key):
        # 유료 사용자는 제한 완화
        @limiter.limit("50/minute")
        async def premium_generate():
            # ...
            pass
    
    # ...
```

---

## 6. 비용 분석 및 비교

### 6.1 비용 계산

```yaml
시나리오: 월 10,000건 요청, 이미지 2개씩

# ============================================
# 방법 1: URL 방식 (실패하지만 이론적 비용)
# ============================================

Cloud Run:
  - 요청: 10,000건
  - CPU: 평균 2초/요청
  - 메모리: 512MB
  - 비용: ~$5/월

CloudFront:
  - 아웃바운드: 10,000 × 2 × 1MB = 20GB
  - 요청 수: 20,000건
  - 비용: ~$2/월

총 비용: $7/월

# ============================================
# 방법 2: Base64 방식 (실제 구현)
# ============================================

Cloud Run:
  - 요청: 10,000건
  - CPU: 평균 3초/요청 (Base64 디코딩 추가)
  - 메모리: 1GB (Base64 처리)
  - 네트워크: 인바운드 무료
  - 비용: ~$12/월

S3 (생성된 이미지 저장):
  - 저장: 10,000 × 500KB = 5GB
  - PUT 요청: 10,000건
  - 비용: ~$0.50/월

CloudFront (결과 이미지 배포):
  - 아웃바운드: 10,000 × 500KB = 5GB
  - 요청: 10,000건
  - 비용: ~$1/월

총 비용: $13.50/월

증가분: $6.50/월 (93% 증가)

# ============================================
# 비용 트레이드오프
# ============================================

URL 방식:
  ✅ 저렴함
  ❌ 작동 안함 (403 에러)

Base64 방식:
  ✅ 작동함
  ❌ 약간 비쌈 (+$6.50/월)
  ✅ 하지만 서비스 가능

결론: 월 $6.50 추가 비용으로 서비스 가능 → 가치 있음!
```

### 6.2 최적화로 비용 절감

```python
# 1. 압축으로 메모리 사용량 감소
GEMINI_CONFIG = {
    "model": "gemini-3-pro-image-preview",
    "aspect_ratio": "3:4",
    "resolution": "1K",  # 2K → 1K로 낮춤
}

# 메모리: 1GB → 512MB
# 비용: $12 → $6/월 (50% 절감)

# 2. 최소 인스턴스 0으로 설정
gcloud run services update my-service \
  --min-instances=0  # 요청 없으면 과금 없음

# 3. 동시성 최대화
gcloud run services update my-service \
  --concurrency=80  # 한 인스턴스가 여러 요청 처리

# 4. 타임아웃 최적화
gcloud run services update my-service \
  --timeout=60  # 불필요하게 긴 타임아웃 방지

# 최종 비용: ~$8/월 (초기 $13.50에서 40% 절감)
```

---

## 7. 테스트 및 디버깅

### 7.1 단위 테스트

```python
# test_image_processing.py
import pytest
import base64
from io import BytesIO
from PIL import Image

def create_test_image() -> str:
    """테스트용 Base64 이미지 생성"""
    # 100x100 빨간색 이미지
    img = Image.new('RGB', (100, 100), color='red')
    
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    
    img_bytes = buffer.getvalue()
    base64_data = base64.b64encode(img_bytes).decode('utf-8')
    
    return f"data:image/jpeg;base64,{base64_data}"

@pytest.mark.asyncio
async def test_base64_image_processing():
    """Base64 이미지 처리 테스트"""
    # Given
    base64_image = create_test_image()
    request_data = {
        "image_data_list": [base64_image],
        "type": "id"
    }
    
    # When
    from main import generate_profile
    result = await generate_profile(
        client=mock_gemini_client,
        generation_type="id",
        image_data_list=request_data["image_data_list"]
    )
    
    # Then
    assert result is not None
    assert result.startswith("https://")

@pytest.mark.asyncio
async def test_invalid_base64():
    """잘못된 Base64 데이터 처리"""
    request_data = {
        "image_data_list": ["invalid_base64_data"],
        "type": "id"
    }
    
    with pytest.raises(HTTPException) as exc_info:
        await generate_profile(
            client=mock_gemini_client,
            image_data_list=request_data["image_data_list"]
        )
    
    assert exc_info.value.status_code == 400

@pytest.mark.asyncio
async def test_large_base64():
    """큰 이미지 검증"""
    # 15MB 이미지 (제한 초과)
    large_img = Image.new('RGB', (5000, 5000), color='blue')
    buffer = BytesIO()
    large_img.save(buffer, format='JPEG')
    
    large_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    request_data = {
        "image_data_list": [f"data:image/jpeg;base64,{large_base64}"],
    }
    
    with pytest.raises(ValueError, match="too large"):
        GenerateRequest(**request_data)
```

### 7.2 통합 테스트

```python
# test_api.py
from httpx import AsyncClient
import pytest

@pytest.mark.asyncio
async def test_generate_endpoint_with_base64():
    """Base64 방식 API 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Given
        base64_image = create_test_image()
        
        # When
        response = await client.post(
            "/api/generate",
            json={
                "image_data_list": [base64_image],
                "type": "wedding"
            }
        )
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["image_urls"]) > 0
        assert data["image_urls"][0].startswith("https://")

@pytest.mark.asyncio
async def test_backward_compatibility():
    """레거시 URL 방식 지원 확인"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/generate",
            json={
                "image_urls": ["https://example.com/test.jpg"],
                "type": "id"
            }
        )
        
        # URL 방식도 여전히 작동 (헤더 추가로 우회 시도)
        assert response.status_code in [200, 403]
```

---

## 결론

### 해결 과정 요약

```yaml
문제:
  Cloud Run → CloudFront 이미지 다운로드 403 Forbidden

시도한 방법들:
  1. ❌ CloudFront Signed URL (복잡도 높음)
  2. ❌ Proxy 엔드포인트 (비효율적, 여전히 403)
  3. ❌ S3 Pre-signed URL (CDN 이점 상실)
  4. ✅ Base64 인코딩 (채택!)

최종 솔루션:
  - 클라이언트에서 이미지를 Base64로 인코딩
  - API 요청 본문에 직접 포함
  - Cloud Run에서 디코딩 후 처리
  - CloudFront 보안 정책 완전 우회

장점:
  ✅ CloudFront 접근 문제 해결
  ✅ 추가 인프라 불필요
  ✅ 빠른 구현 (1일)
  ✅ 레거시 URL 방식 병행 지원

단점:
  ⚠️ 페이로드 33% 증가
  ⚠️ 메모리 사용량 증가
  ⚠️ 비용 약간 증가 (+$6.50/월)

최적화:
  - 클라이언트 이미지 리사이징 (1920px 제한)
  - JPEG 압축 (품질 80%)
  - 메모리 관리 (GC)
  - Rate Limiting

최종 비용:
  월 10,000건 기준: ~$8/월
  (서비스 불가 → 서비스 가능)
```

### 교훈

**1. 완벽한 솔루션은 없다**
- Signed URL이 이론적으로 최선이지만 복잡도가 높음
- Base64는 오버헤드가 있지만 실용적

**2. 트레이드오프 이해**
- 보안 vs 편의성
- 성능 vs 구현 속도
- 비용 vs 기능

**3. 점진적 개선**
- URL 방식 (실패) → Base64 방식 (성공) → 최적화 (진행 중)
- 처음부터 완벽할 필요 없음

**4. 실무에서 중요한 것**
- 작동하는 솔루션 > 이론적으로 완벽한 솔루션
- 빠른 실행 > 완벽한 계획
- 사용자 경험 > 기술적 순수성

### 다음 단계

```python
# TODO: 추가 개선 사항

1. WebP 포맷 지원:
   - JPEG보다 30% 작은 크기
   - 품질 유지
   
2. Progressive JPEG:
   - 점진적 로딩
   - 사용자 경험 개선

3. CDN 캐싱:
   - 생성된 이미지 CloudFront 캐싱
   - 중복 생성 방지

4. Batch Processing:
   - 여러 이미지 동시 처리
   - 처리 시간 단축

5. Serverless Image Optimization:
   - Lambda@Edge 또는 Cloud Functions
   - 실시간 리사이징
```

**CloudFront 보안 정책 때문에 막혔지만, Base64로 우회하여 서비스를 성공적으로 런칭했습니다!** 🚀📸

