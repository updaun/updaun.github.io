# .env 파일 관리 및 웹 이미지 자동 매칭 시스템

환경변수를 `.env` 파일로 관리하여 API 키와 설정을 안전하고 편리하게 관리할 수 있습니다.

## 📁 파일 구조

```
updaun.github.io/
├── .env                           # 환경변수 설정 파일 (실제 사용)
├── .env.example                   # 환경변수 템플릿 파일
├── env_loader.py                  # 환경변수 로더 유틸리티
├── simple_web_image_matcher.py    # 간단한 이미지 매칭 (API 키 불필요)
├── web_image_matcher.py           # 고급 이미지 매칭 (API 키 필요)
├── image_matcher_manager.py       # 통합 관리 도구
└── setup_web_image_matcher.py     # 설치 및 설정 가이드
```

## 🚀 빠른 시작

### 1. 통합 관리 도구 실행 (권장)
```bash
python3 image_matcher_manager.py
```

### 2. 직접 실행
```bash
# 환경 설정 확인
python3 env_loader.py

# 간단한 이미지 매칭 (API 키 불필요)
python3 simple_web_image_matcher.py --recent 5

# 고급 이미지 매칭 (API 키 필요)
python3 web_image_matcher.py --recent 5
```

## ⚙️ 환경변수 설정

### .env 파일 생성
```bash
# .env.example을 .env로 복사
cp .env.example .env

# .env 파일 편집
nano .env  # 또는 code .env
```

### .env 파일 내용 예시
```env
# API 키 설정
UNSPLASH_ACCESS_KEY=your_unsplash_access_key_here
PEXELS_API_KEY=your_pexels_api_key_here
PIXABAY_API_KEY=your_pixabay_api_key_here

# 이미지 설정
IMAGE_QUALITY=85      # WebP 품질 (0-100)
IMAGE_WIDTH=1200      # 이미지 너비
IMAGE_HEIGHT=630      # 이미지 높이

# 캐시 설정
CACHE_EXPIRES_DAYS=7  # 캐시 만료 일수
```

## 🔑 API 키 발급

### Unsplash API (고품질 사진)
- **URL**: https://unsplash.com/developers
- **제한**: 시간당 50회 (무료)
- **특징**: 전문 사진작가의 고품질 이미지

1. Unsplash 계정 생성/로그인
2. "Your apps" 페이지로 이동
3. "New Application" 클릭
4. 애플리케이션 정보 입력
5. Access Key 복사하여 .env에 설정

### Pexels API (무료 스톡 사진)
- **URL**: https://www.pexels.com/api/
- **제한**: 시간당 200회 (무료)
- **특징**: 상업적 사용 가능한 무료 이미지

1. Pexels 계정 생성/로그인
2. API 페이지로 이동
3. "Your API Key" 확인
4. API Key 복사하여 .env에 설정

### Pixabay API (다양한 이미지)
- **URL**: https://pixabay.com/api/docs/
- **제한**: 시간당 5,000회 (무료)
- **특징**: 다양한 카테고리의 이미지

1. Pixabay 계정 생성/로그인
2. API 문서 페이지로 이동
3. API Key 확인
4. API Key 복사하여 .env에 설정

## 📋 사용법

### 1. 통합 관리 도구 (권장)
```bash
python3 image_matcher_manager.py
```

메뉴에서 선택:
- `1`: 환경 설정 확인
- `2`: .env 파일 편집
- `3`: 간단한 이미지 매칭 실행
- `4`: 고급 이미지 매칭 실행
- `5`: 최근 포스트 처리
- `6`: 모든 포스트 처리
- `7`: 특정 포스트 처리
- `8`: API 키 설정 가이드

### 2. 직접 명령어 실행

#### 간단한 이미지 매칭 (API 키 불필요)
```bash
# 최근 5개 포스트 (기본값)
python3 simple_web_image_matcher.py

# 최근 10개 포스트
python3 simple_web_image_matcher.py --recent 10

# 모든 포스트
python3 simple_web_image_matcher.py --all

# 특정 포스트
python3 simple_web_image_matcher.py 2025-09-20-chrome-extension-guide.md
```

#### 고급 이미지 매칭 (API 키 필요)
```bash
# 최근 5개 포스트
python3 web_image_matcher.py --recent 5

# 최근 30일 포스트
python3 web_image_matcher.py --recent 30

# 모든 포스트
python3 web_image_matcher.py --all

# 특정 포스트
python3 web_image_matcher.py 2025-09-20-chrome-extension-guide.md
```

## 🎨 이미지 소스

### 간단한 버전 (API 키 불필요)
- ✅ **기술 테마 이미지**: 키워드별 맞춤 색상과 디자인
- ✅ **Unsplash Source**: 고품질 무료 이미지 컬렉션
- ✅ **Lorem Picsum**: 랜덤 고품질 이미지
- ✅ **커스텀 생성**: 모든 다운로드 실패 시 자동 생성

### 고급 버전 (API 키 필요)
- 🔑 **Unsplash API**: 키워드 기반 정확한 검색
- 🔑 **Pexels API**: 상업적 사용 가능한 이미지
- 🔑 **Pixabay API**: 다양한 카테고리 이미지
- ✅ **무료 소스**: API 키 없어도 작동

## 🔧 설정 옵션

### 이미지 설정
```env
IMAGE_QUALITY=85      # WebP 압축 품질 (0-100)
IMAGE_WIDTH=1200      # 썸네일 너비 (픽셀)
IMAGE_HEIGHT=630      # 썸네일 높이 (픽셀)
```

### 캐시 설정
```env
CACHE_EXPIRES_DAYS=7  # API 응답 캐시 만료 일수
```

## 🔍 키워드 추출

시스템이 자동으로 추출하는 키워드:
- 📄 **제목**: 포스트 제목에서 기술 용어 추출
- 🏷️ **카테고리**: YAML front matter의 categories
- 🔖 **태그**: YAML front matter의 tags
- 📝 **본문**: 기술 관련 키워드 패턴 매칭

## 📊 처리 결과

생성되는 파일:
- 📸 **이미지**: `assets/img/posts/{post_name}.webp`
- 📋 **메타데이터**: `assets/img/posts/{post_name}.json` (고급 버전)
- 💾 **캐시**: `.thumbnail_cache/web_image_cache.json`

## 🚨 문제 해결

### 환경변수 로드 실패
```bash
# 환경 상태 확인
python3 env_loader.py

# .env 파일 존재 확인
ls -la .env*
```

### API 키 설정 문제
```bash
# API 키 확인
python3 -c "from env_loader import get_env_loader; get_env_loader().print_status()"
```

### 의존성 패키지 설치
```bash
pip install Pillow requests PyYAML
```

### 권한 문제
```bash
# 실행 권한 부여
chmod +x *.py
```

## 💡 사용 팁

1. **API 키 우선순위**: Unsplash > Pexels > Pixabay 순으로 시도
2. **캐시 활용**: 동일 키워드는 7일간 캐시되어 API 요청 절약
3. **배치 처리**: 여러 포스트 처리 시 API 제한 고려하여 자동 대기
4. **폴백 시스템**: API 실패 시 자동으로 무료 소스로 전환
5. **품질 설정**: IMAGE_QUALITY를 높이면 파일 크기 증가, 품질 향상

## 📈 성능 최적화

- ⚡ **캐시 시스템**: API 응답 캐시로 속도 향상
- 🔄 **비동기 처리**: 여러 소스 동시 검색
- 📦 **WebP 압축**: 최적화된 이미지 포맷
- 🎯 **스마트 크롭**: 비율 유지하며 중앙 크롭

이제 `.env` 파일로 모든 설정을 안전하고 편리하게 관리할 수 있습니다! 🎉