---
layout: post
title: "OpenCV 이미지 전처리: 문서 스캐너 구현으로 배우는 실무 기법"
date: 2025-09-02
categories: [Computer Vision, OpenCV, Python]
tags: [opencv, image-processing, document-scanner, preprocessing, python, computer-vision]
image: /assets/images/thumbnails/opencv-image-preprocessing.jpg
excerpt: "OpenCV를 활용한 이미지 전처리 기법들을 실제 문서 스캐너 구현을 통해 학습해보세요. 에지 검출, 윤곽선 추출, 원근 변환부터 고급 향상 기법까지 다룹니다."
---

# OpenCV 이미지 전처리: 문서 스캐너 구현으로 배우는 실무 기법

이미지 전처리는 컴퓨터 비전의 핵심 기술 중 하나입니다. 오늘은 실제 문서 스캐너를 구현하면서 다양한 이미지 전처리 기법들을 학습해보겠습니다.

## 목차
1. [이미지 전처리의 중요성](#이미지-전처리의-중요성)
2. [기본 전처리 파이프라인](#기본-전처리-파이프라인)
3. [에지 검출과 윤곽선 추출](#에지-검출과-윤곽선-추출)
4. [원근 변환과 기하학적 보정](#원근-변환과-기하학적-보정)
5. [이미지 향상 기법](#이미지-향상-기법)
6. [실무 프로젝트: 문서 스캐너 구현](#실무-프로젝트-문서-스캐너-구현)
7. [성능 최적화와 품질 검증](#성능-최적화와-품질-검증)

## 이미지 전처리의 중요성

이미지 전처리는 원본 데이터에서 유용한 정보를 추출하고 노이즈를 제거하여 후속 처리의 정확도를 높이는 과정입니다.

### 주요 목적
- **노이즈 제거**: 촬영 환경으로 인한 잡음 제거
- **특징 강화**: 중요한 특징들을 더욱 명확하게 만듦
- **정규화**: 일관된 형태로 데이터 변환
- **데이터 압축**: 불필요한 정보 제거로 처리 속도 향상

## 기본 전처리 파이프라인

### 1. 이미지 크기 조정

```python
def resize_image(img, max_side=1500):
    """이미지 크기를 적절히 조정"""
    h, w = img.shape[:2]
    if max(h, w) > max_side:
        scale_factor = max_side / max(h, w)
        new_w = int(w * scale_factor)
        new_h = int(h * scale_factor)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return img
```

### 2. 컬러 공간 변환

```python
def convert_color_space(img, target='GRAY'):
    """다양한 컬러 공간으로 변환"""
    if target == 'GRAY':
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    elif target == 'HSV':
        return cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    elif target == 'LAB':
        return cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    return img
```

### 3. 노이즈 제거

```python
def denoise_image(img, method='gaussian'):
    """다양한 방법으로 노이즈 제거"""
    if method == 'gaussian':
        return cv2.GaussianBlur(img, (5, 5), 0)
    elif method == 'median':
        return cv2.medianBlur(img, 5)
    elif method == 'bilateral':
        return cv2.bilateralFilter(img, 9, 75, 75)
    return img
```

## 에지 검출과 윤곽선 추출

### 적응적 Canny 에지 검출

```python
def adaptive_canny(gray_img):
    """적응적 임계값을 사용한 Canny 에지 검출"""
    # 중앙값을 기준으로 임계값 계산
    median_val = np.median(gray_img)
    lower_threshold = int(max(0, 0.67 * median_val))
    upper_threshold = int(min(255, 1.33 * median_val))
    
    # Canny 에지 검출
    edges = cv2.Canny(gray_img, lower_threshold, upper_threshold)
    
    # 모폴로지 연산으로 에지 정리
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=1)
    edges = cv2.erode(edges, kernel, iterations=1)
    
    return edges
```

### 윤곽선 검출과 필터링

```python
def find_document_contours(edges, img_shape, min_area_ratio=0.1):
    """문서 윤곽선 검출"""
    # 윤곽선 찾기
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    # 면적 순으로 정렬
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    
    image_area = img_shape[0] * img_shape[1]
    
    for contour in contours[:10]:  # 상위 10개만 검사
        # 윤곽선 근사
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        # 사각형 형태인지 확인
        if len(approx) == 4:
            # 면적 비율 확인
            contour_area = cv2.contourArea(contour)
            area_ratio = contour_area / image_area
            
            if area_ratio >= min_area_ratio:
                return approx.reshape(4, 2), area_ratio
    
    return None, 0
```

## 원근 변환과 기하학적 보정

### 네 점 정렬

```python
def order_points(pts):
    """네 점을 일정한 순서로 정렬 (좌상, 우상, 우하, 좌하)"""
    rect = np.zeros((4, 2), dtype="float32")
    
    # 합계를 이용한 좌상단, 우하단 찾기
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # 좌상단
    rect[2] = pts[np.argmax(s)]  # 우하단
    
    # 차이를 이용한 우상단, 좌하단 찾기
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # 우상단
    rect[3] = pts[np.argmax(diff)]  # 좌하단
    
    return rect
```

### 원근 변환

```python
def four_point_transform(img, pts):
    """네 점을 이용한 원근 변환"""
    # 점들을 정렬
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    
    # 새로운 이미지의 너비와 높이 계산
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
    
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    
    # 목적지 좌표 설정
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]
    ], dtype="float32")
    
    # 변환 행렬 계산 및 적용
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, M, (maxWidth, maxHeight))
    
    return warped
```

## 이미지 향상 기법

### 1. CLAHE (Contrast Limited Adaptive Histogram Equalization)

```python
def enhance_with_clahe(img):
    """CLAHE를 이용한 이미지 향상"""
    # LAB 컬러 공간으로 변환
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # L 채널에 CLAHE 적용
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    
    # 다시 합치고 BGR로 변환
    lab = cv2.merge((l, a, b))
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    return enhanced
```

### 2. 샤프닝 필터

```python
def sharpen_image(img):
    """샤프닝 필터 적용"""
    # 샤프닝 커널
    kernel = np.array([[-1, -1, -1],
                      [-1,  9, -1],
                      [-1, -1, -1]])
    
    sharpened = cv2.filter2D(img, -1, kernel)
    return sharpened
```

### 3. 언샤프 마스킹

```python
def unsharp_mask(img, strength=1.5, blur_size=5):
    """언샤프 마스킹을 이용한 이미지 선명화"""
    # 가우시안 블러 적용
    blurred = cv2.GaussianBlur(img, (blur_size, blur_size), 0)
    
    # 언샤프 마스크 생성
    mask = cv2.subtract(img, blurred)
    
    # 원본에 마스크 추가
    sharpened = cv2.addWeighted(img, 1 + strength, mask, strength, 0)
    
    return sharpened
```

## 실무 프로젝트: 문서 스캐너 구현

### 완전한 문서 스캐너 클래스

```python
import cv2
import numpy as np
from pathlib import Path

class DocumentScanner:
    def __init__(self, max_side=1500, min_area_ratio=0.3):
        self.max_side = max_side
        self.min_area_ratio = min_area_ratio
    
    def preprocess(self, img):
        """이미지 전처리"""
        # 크기 조정
        resized = self._resize_image(img)
        
        # 그레이스케일 변환
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        
        # 노이즈 제거
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        
        return resized, denoised
    
    def detect_document(self, gray_img, original_img):
        """문서 영역 검출"""
        # 에지 검출
        edges = self._adaptive_canny(gray_img)
        
        # 윤곽선 찾기
        corners, area_ratio = self._find_document_contours(
            edges, gray_img.shape
        )
        
        return corners, area_ratio
    
    def extract_document(self, img, corners):
        """문서 영역 추출 및 보정"""
        if corners is None:
            return img
        
        # 원근 변환
        warped = self._four_point_transform(img, corners)
        
        return warped
    
    def enhance_document(self, img, method='clahe'):
        """문서 이미지 향상"""
        if method == 'clahe':
            return self._enhance_with_clahe(img)
        elif method == 'sharpen':
            return self._sharpen_image(img)
        elif method == 'unsharp':
            return self._unsharp_mask(img)
        
        return img
    
    def scan(self, img, enhancement='clahe'):
        """전체 스캔 프로세스"""
        # 1. 전처리
        processed_img, gray = self.preprocess(img)
        
        # 2. 문서 검출
        corners, area_ratio = self.detect_document(gray, processed_img)
        
        # 3. 문서 추출
        extracted = self.extract_document(processed_img, corners)
        
        # 4. 이미지 향상
        enhanced = self.enhance_document(extracted, enhancement)
        
        detection_success = corners is not None
        
        return enhanced, detection_success, area_ratio
```

### 배치 처리 스크립트

```python
def batch_process_documents(input_folder, output_folder):
    """폴더 내 모든 이미지를 배치 처리"""
    scanner = DocumentScanner(max_side=1600, min_area_ratio=0.2)
    
    # 지원하는 이미지 확장자
    extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
    
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(exist_ok=True)
    
    image_files = []
    for ext in extensions:
        image_files.extend(input_path.glob(f'*{ext}'))
        image_files.extend(input_path.glob(f'*{ext.upper()}'))
    
    results = {'success': 0, 'failed': 0, 'total': len(image_files)}
    
    for img_file in image_files:
        print(f"처리 중: {img_file.name}")
        
        # 이미지 로드
        img = cv2.imread(str(img_file))
        if img is None:
            print(f"  ❌ 이미지 로드 실패")
            results['failed'] += 1
            continue
        
        try:
            # 스캔 실행
            result, success, area_ratio = scanner.scan(img)
            
            # 결과 저장
            output_file = output_path / f"scanned_{img_file.stem}.jpg"
            cv2.imwrite(str(output_file), result)
            
            print(f"  ✅ 성공 (검출: {success}, 면적: {area_ratio:.1%})")
            results['success'] += 1
            
        except Exception as e:
            print(f"  ❌ 오류: {e}")
            results['failed'] += 1
    
    # 결과 요약
    success_rate = (results['success'] / results['total']) * 100
    print(f"\n=== 처리 결과 ===")
    print(f"총 파일: {results['total']}개")
    print(f"성공: {results['success']}개")
    print(f"실패: {results['failed']}개")
    print(f"성공률: {success_rate:.1f}%")
```

## 성능 최적화와 품질 검증

### 1. 처리 시간 최적화

```python
import time
from functools import wraps

def measure_time(func):
    """함수 실행 시간 측정 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} 실행 시간: {end_time - start_time:.3f}초")
        return result
    return wrapper

class OptimizedDocumentScanner(DocumentScanner):
    @measure_time
    def scan(self, img, enhancement='clahe'):
        """시간 측정이 포함된 스캔"""
        return super().scan(img, enhancement)
    
    def batch_scan_parallel(self, image_files, num_workers=4):
        """멀티프로세싱을 이용한 병렬 처리"""
        from concurrent.futures import ProcessPoolExecutor
        
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(self._process_single_file, file) 
                      for file in image_files]
            
            results = []
            for future in futures:
                try:
                    results.append(future.result())
                except Exception as e:
                    print(f"처리 오류: {e}")
                    results.append(None)
        
        return results
```

### 2. 품질 검증 메트릭

```python
def calculate_image_quality_metrics(original, processed):
    """이미지 품질 메트릭 계산"""
    # PSNR (Peak Signal-to-Noise Ratio)
    mse = np.mean((original - processed) ** 2)
    if mse == 0:
        psnr = float('inf')
    else:
        max_pixel = 255.0
        psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
    
    # SSIM (Structural Similarity Index)
    from skimage.metrics import structural_similarity as ssim
    ssim_score = ssim(original, processed, multichannel=True)
    
    # 샤프니스 측정 (라플라시안 분산)
    gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    return {
        'psnr': psnr,
        'ssim': ssim_score,
        'sharpness': sharpness
    }
```

### 3. 자동 품질 평가

```python
def evaluate_scan_quality(img, corners, area_ratio):
    """스캔 품질 자동 평가"""
    score = 0
    feedback = []
    
    # 1. 면적 비율 평가 (40점)
    if area_ratio >= 0.7:
        score += 40
        feedback.append("✅ 문서 영역이 충분히 큽니다")
    elif area_ratio >= 0.4:
        score += 25
        feedback.append("⚠️ 문서 영역이 적당합니다")
    else:
        score += 10
        feedback.append("❌ 문서 영역이 너무 작습니다")
    
    # 2. 모서리 검출 평가 (30점)
    if corners is not None:
        score += 30
        feedback.append("✅ 문서 모서리가 정확히 검출되었습니다")
    else:
        feedback.append("❌ 문서 모서리 검출에 실패했습니다")
    
    # 3. 이미지 선명도 평가 (30점)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    if sharpness > 500:
        score += 30
        feedback.append("✅ 이미지가 매우 선명합니다")
    elif sharpness > 100:
        score += 20
        feedback.append("⚠️ 이미지가 적당히 선명합니다")
    else:
        score += 5
        feedback.append("❌ 이미지가 흐릿합니다")
    
    # 등급 계산
    if score >= 90:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    else:
        grade = "D"
    
    return {
        'score': score,
        'grade': grade,
        'feedback': feedback
    }
```

## 실제 사용 예시

```python
def main():
    """메인 실행 함수"""
    # 스캐너 초기화
    scanner = OptimizedDocumentScanner(
        max_side=1600, 
        min_area_ratio=0.3
    )
    
    # 단일 이미지 처리
    img_path = "sample_document.jpg"
    img = cv2.imread(img_path)
    
    if img is not None:
        # 스캔 실행
        result, success, area_ratio = scanner.scan(img)
        
        # 품질 평가
        quality = evaluate_scan_quality(result, None, area_ratio)
        
        print(f"스캔 성공: {success}")
        print(f"면적 비율: {area_ratio:.1%}")
        print(f"품질 점수: {quality['score']}/100 ({quality['grade']})")
        
        for feedback in quality['feedback']:
            print(f"  {feedback}")
        
        # 결과 저장
        cv2.imwrite("scanned_document.jpg", result)
        
    # 배치 처리
    batch_process_documents("input_folder", "output_folder")

if __name__ == "__main__":
    main()
```

## 마무리

이미지 전처리는 컴퓨터 비전 프로젝트의 성공을 좌우하는 핵심 기술입니다. 이번 포스트에서 다룬 기법들을 정리하면:

### 핵심 포인트
1. **적응적 전처리**: 이미지 특성에 따라 매개변수를 자동 조정
2. **다단계 검증**: 면적, 모양, 품질을 단계적으로 검증
3. **사용자 경험**: 자동 실패 시 수동 모드 제공
4. **성능 최적화**: 병렬 처리와 효율적인 알고리즘 활용
5. **품질 평가**: 객관적 메트릭을 통한 결과 검증

### 활용 분야
- 문서 디지털화
- OCR 전처리
- 의료 영상 분석
- 산업 검사 시스템
- 모바일 앱 개발

실제 프로젝트에서는 데이터의 특성과 요구사항에 따라 이러한 기법들을 선택적으로 조합하여 사용하는 것이 중요합니다. 지속적인 테스트와 개선을 통해 더 나은 결과를 얻을 수 있습니다.

다음 포스트에서는 딥러닝을 활용한 고급 이미지 전처리 기법들을 다뤄보겠습니다!

---

*이 포스트가 도움이 되셨다면 댓글과 공유 부탁드립니다. 궁금한 점이나 추가하고 싶은 내용이 있으시면 언제든 말씀해 주세요!*
