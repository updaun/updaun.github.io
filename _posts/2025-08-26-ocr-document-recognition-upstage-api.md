---
layout: post
title: "OCR 기술과 Upstage Document OCR API 활용법"
date: 2025-08-26
categories: [AI, OCR, API]
tags: [ocr, upstage, document-recognition, image-processing, api]
---

## OCR이란?

OCR(Optical Character Recognition, 광학 문자 인식)은 이미지나 스캔된 문서에서 텍스트를 자동으로 인식하고 추출하는 기술입니다. 종이 문서를 디지털화하거나, 이미지 속 텍스트를 편집 가능한 형태로 변환할 때 필수적인 기술입니다.

## OCR의 주요 활용 분야

### 1. 문서 디지털화
- 종이 문서의 전자화
- 고문서 및 아카이브 자료 보존
- 법률 문서 관리 시스템

### 2. 자동화 업무 프로세스
- 영수증 및 청구서 처리
- 신분증 정보 추출
- 계약서 데이터 추출

### 3. 모바일 애플리케이션
- 텍스트 번역 앱
- 명함 정보 추출
- 실시간 문서 스캔

## Upstage Document OCR API 소개

Upstage는 한국의 AI 기업으로, 고성능 OCR API를 제공합니다. 특히 한국어 문서 처리에 뛰어난 성능을 보입니다.

### 주요 특징
- **높은 정확도**: 한국어 문서에 최적화된 인식 성능
- **다양한 문서 형태 지원**: PDF, 이미지 파일 등
- **구조화된 출력**: JSON 형태의 체계적인 결과 제공
- **RESTful API**: 간단한 HTTP 요청으로 이용 가능

## Upstage OCR API 사용법

### 1. API 키 발급

먼저 [Upstage Console](https://console.upstage.ai/)에서 계정을 생성하고 API 키를 발급받습니다.

### 2. Python으로 API 호출하기

```python
import requests
import base64
import json

# API 설정
API_URL = "https://api.upstage.ai/v1/document-ai/ocr"
API_KEY = "your_api_key_here"

def encode_image_to_base64(image_path):
    """이미지 파일을 base64로 인코딩"""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string

def extract_text_with_upstage_ocr(image_path):
    """Upstage OCR API를 사용하여 텍스트 추출"""
    
    # 이미지를 base64로 인코딩
    encoded_image = encode_image_to_base64(image_path)
    
    # API 요청 헤더
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # API 요청 데이터
    data = {
        "document": encoded_image
    }
    
    try:
        # API 호출
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"API 요청 오류: {e}")
        return None

# 사용 예제
if __name__ == "__main__":
    image_path = "sample_document.jpg"
    result = extract_text_with_upstage_ocr(image_path)
    
    if result:
        print("OCR 결과:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
```

### 3. cURL을 사용한 API 호출

```bash
# 이미지를 base64로 인코딩
IMAGE_BASE64=$(base64 -w 0 sample_document.jpg)

# API 호출
curl -X POST "https://api.upstage.ai/v1/document-ai/ocr" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "document": "'$IMAGE_BASE64'"
  }'
```

### 4. JavaScript/Node.js 예제

```javascript
const fs = require('fs');
const axios = require('axios');

async function extractTextWithUpstageOCR(imagePath) {
    try {
        // 이미지를 base64로 인코딩
        const imageBuffer = fs.readFileSync(imagePath);
        const encodedImage = imageBuffer.toString('base64');
        
        // API 요청
        const response = await axios.post('https://api.upstage.ai/v1/document-ai/ocr', {
            document: encodedImage
        }, {
            headers: {
                'Authorization': `Bearer ${process.env.UPSTAGE_API_KEY}`,
                'Content-Type': 'application/json'
            }
        });
        
        return response.data;
        
    } catch (error) {
        console.error('OCR API 오류:', error.response?.data || error.message);
        return null;
    }
}

// 사용 예제
extractTextWithUpstageOCR('sample_document.jpg')
    .then(result => {
        if (result) {
            console.log('OCR 결과:', JSON.stringify(result, null, 2));
        }
    });
```

## API 응답 형태

Upstage OCR API는 다음과 같은 구조화된 JSON 응답을 제공합니다:

```json
{
  "text": "전체 추출된 텍스트",
  "pages": [
    {
      "page": 1,
      "text": "페이지별 텍스트",
      "bboxes": [
        {
          "text": "개별 텍스트 블록",
          "coordinates": {
            "x": 100,
            "y": 200,
            "width": 300,
            "height": 50
          }
        }
      ]
    }
  ]
}
```

## 실전 활용 예제: 영수증 데이터 추출

```python
import re
from datetime import datetime

def parse_receipt_data(ocr_result):
    """OCR 결과에서 영수증 정보 파싱"""
    
    text = ocr_result.get('text', '')
    
    # 정규표현식으로 주요 정보 추출
    patterns = {
        'store_name': r'^([^\n]+)',  # 첫 번째 줄을 매장명으로 가정
        'total_amount': r'합계[:\s]*([0-9,]+)원?',
        'date': r'(\d{4}[-./]\d{2}[-./]\d{2})',
        'phone': r'(\d{3}-\d{3,4}-\d{4})'
    }
    
    parsed_data = {}
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            parsed_data[key] = match.group(1).strip()
    
    return parsed_data

# 사용 예제
def process_receipt_image(image_path):
    """영수증 이미지 처리 전체 프로세스"""
    
    # OCR 수행
    ocr_result = extract_text_with_upstage_ocr(image_path)
    
    if not ocr_result:
        return None
    
    # 데이터 파싱
    receipt_data = parse_receipt_data(ocr_result)
    
    print("=== 영수증 정보 ===")
    print(f"매장명: {receipt_data.get('store_name', '미확인')}")
    print(f"총 금액: {receipt_data.get('total_amount', '미확인')}원")
    print(f"날짜: {receipt_data.get('date', '미확인')}")
    print(f"전화번호: {receipt_data.get('phone', '미확인')}")
    
    return receipt_data

# 실행
receipt_info = process_receipt_image('receipt.jpg')
```

## OCR 정확도 향상 팁

### 1. 이미지 전처리
- **해상도 최적화**: 300 DPI 이상 권장
- **노이즈 제거**: 가우시안 블러 또는 미디언 필터 적용
- **대비 개선**: 히스토그램 평활화

```python
import cv2
import numpy as np

def preprocess_image(image_path):
    """OCR 정확도 향상을 위한 이미지 전처리"""
    
    # 이미지 로드
    img = cv2.imread(image_path)
    
    # 그레이스케일 변환
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 노이즈 제거
    denoised = cv2.medianBlur(gray, 3)
    
    # 대비 개선
    enhanced = cv2.equalizeHist(denoised)
    
    # 이진화
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 전처리된 이미지 저장
    processed_path = image_path.replace('.jpg', '_processed.jpg')
    cv2.imwrite(processed_path, binary)
    
    return processed_path
```

### 2. 문서 정렬 및 회전 보정
```python
def correct_skew(image_path):
    """문서 기울어짐 보정"""
    import cv2
    import numpy as np
    
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 엣지 검출
    edges = cv2.Canny(gray, 75, 200, apertureSize=3, L2gradient=True)
    
    # 직선 검출
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 30, minLineLength=20, maxLineGap=5)
    
    if lines is not None:
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            angles.append(angle)
        
        # 중간값으로 회전 각도 결정
        rotation_angle = np.median(angles)
        
        # 이미지 회전
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, rotation_angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC)
        
        corrected_path = image_path.replace('.jpg', '_corrected.jpg')
        cv2.imwrite(corrected_path, rotated)
        return corrected_path
    
    return image_path
```

## 에러 처리 및 모니터링

```python
import logging
from functools import wraps
import time

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_on_failure(max_retries=3, delay=1):
    """API 호출 실패 시 재시도 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"시도 {attempt + 1} 실패: {e}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay * (2 ** attempt))  # 지수적 백오프
            return None
        return wrapper
    return decorator

@retry_on_failure(max_retries=3)
def robust_ocr_extraction(image_path):
    """안정적인 OCR 추출 함수"""
    try:
        # 이미지 전처리
        processed_path = preprocess_image(image_path)
        
        # OCR 수행
        result = extract_text_with_upstage_ocr(processed_path)
        
        # 결과 검증
        if not result or not result.get('text'):
            raise ValueError("OCR 결과가 비어있습니다")
        
        logger.info(f"OCR 성공: {len(result['text'])} 문자 추출")
        return result
        
    except Exception as e:
        logger.error(f"OCR 처리 오류: {e}")
        raise

```

## 비용 최적화 전략

### 1. 이미지 크기 최적화
```python
def optimize_image_size(image_path, max_size=2048):
    """API 호출 비용 절약을 위한 이미지 크기 최적화"""
    import cv2
    
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    
    if max(h, w) > max_size:
        if h > w:
            new_h = max_size
            new_w = int(w * (max_size / h))
        else:
            new_w = max_size
            new_h = int(h * (max_size / w))
        
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        optimized_path = image_path.replace('.jpg', '_optimized.jpg')
        cv2.imwrite(optimized_path, resized, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return optimized_path
    
    return image_path
```

### 2. 캐싱 시스템
```python
import hashlib
import pickle
import os

class OCRCache:
    """OCR 결과 캐싱 시스템"""
    
    def __init__(self, cache_dir='./ocr_cache'):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_image_hash(self, image_path):
        """이미지 해시값 생성"""
        with open(image_path, 'rb') as f:
            content = f.read()
        return hashlib.md5(content).hexdigest()
    
    def get_cached_result(self, image_path):
        """캐시된 결과 조회"""
        image_hash = self._get_image_hash(image_path)
        cache_file = os.path.join(self.cache_dir, f"{image_hash}.pkl")
        
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None
    
    def cache_result(self, image_path, result):
        """결과 캐싱"""
        image_hash = self._get_image_hash(image_path)
        cache_file = os.path.join(self.cache_dir, f"{image_hash}.pkl")
        
        with open(cache_file, 'wb') as f:
            pickle.dump(result, f)

# 사용 예제
cache = OCRCache()

def cached_ocr_extraction(image_path):
    """캐시를 활용한 OCR 추출"""
    
    # 캐시 확인
    cached_result = cache.get_cached_result(image_path)
    if cached_result:
        logger.info("캐시된 결과 사용")
        return cached_result
    
    # OCR 수행
    result = extract_text_with_upstage_ocr(image_path)
    
    # 결과 캐싱
    if result:
        cache.cache_result(image_path, result)
    
    return result
```

## 결론

OCR 기술은 디지털 트랜스포메이션의 핵심 요소로, 다양한 업무 자동화에 활용되고 있습니다. Upstage OCR API는 특히 한국어 문서 처리에 뛰어난 성능을 제공하며, 간단한 API 호출만으로 고품질의 텍스트 추출이 가능합니다.

성공적인 OCR 시스템 구축을 위해서는:
- **이미지 전처리**를 통한 품질 개선
- **에러 처리** 및 **재시도 로직** 구현  
- **캐싱 시스템**을 통한 비용 최적화
- **모니터링**을 통한 성능 관리

이러한 요소들을 고려하여 안정적이고 효율적인 OCR 서비스를 구축할 수 있습니다.

---

*이 포스트가 도움이 되셨다면 댓글로 피드백을 남겨주세요. OCR 관련 궁금한 점이 있으시면 언제든 문의하세요!*
