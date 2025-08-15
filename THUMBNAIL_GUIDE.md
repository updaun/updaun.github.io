# 자동 썸네일 생성기 사용 가이드

포스트 키워드를 활용해서 연관된 썸네일 이미지를 자동으로 생성하는 도구입니다.

## 주요 기능

- 📝 포스트의 카테고리, 태그, 제목을 분석하여 관련 키워드 추출
- 🎨 키워드 기반 이미지 검색 (Unsplash API 사용)
- 🖼️ 이미지 다운로드 실패 시 자동으로 폴백 이미지 생성
- 🎯 기술 분야별 맞춤형 색상 스키마 적용
- 🌏 한글 텍스트 완벽 지원
- 📐 1200x630 크기로 최적화된 웹용 썸네일

## 설치 및 설정

### 1. Python 가상환경 활성화
```bash
source .venv/bin/activate  # 이미 설정되어 있음
```

### 2. 필요한 패키지 확인
```bash
pip list | grep -E "(Pillow|requests|PyYAML)"
```

## 사용법

### 현재 편집 중인 포스트 썸네일 생성
```bash
python auto_thumbnail_generator.py --current
# 또는
python auto_thumbnail_generator.py -c
```

### 특정 포스트 썸네일 생성
```bash
python auto_thumbnail_generator.py --post 2025-08-14-example-post.md
# 또는
python auto_thumbnail_generator.py -p 2025-08-14-example-post.md
```

### 최근 N일간의 포스트 일괄 처리
```bash
python auto_thumbnail_generator.py --recent 7    # 최근 7일
python auto_thumbnail_generator.py --recent 30   # 최근 30일
# 또는
python auto_thumbnail_generator.py -r 7
```

### 모든 옵션 확인
```bash
python auto_thumbnail_generator.py --help
```

## 색상 스키마

기술 분야별로 최적화된 색상 스키마가 자동으로 적용됩니다:

| 기술 분야 | 주요 색상 | 적용 키워드 |
|-----------|-----------|-------------|
| **AWS** | 오렌지/다크그레이 | aws, ec2, s3, lambda, rds |
| **Python** | 블루/옐로우 | python, django, flask, fastapi |
| **Django** | 그린/다크그린 | django |
| **AI/ML** | 퍼플/시안 | ai, yolo, opencv, tensorflow |
| **기본** | 블루/그레이 | 기타 모든 주제 |

## 출력 파일

- **위치**: `assets/img/posts/`
- **형식**: WebP (고품질, 작은 파일 크기)
- **크기**: 1200×630 (소셜 미디어 최적화)
- **명명규칙**: `포스트파일명.webp`

## 키워드 매핑

### 영어 키워드
- aws → cloud computing, amazon web services
- python → programming, coding, software development
- django → web development, backend programming
- ai → artificial intelligence, machine learning

### 한글 키워드 (자동 번역)
- 가이드 → tutorial, learning, education
- 분석 → data analysis, research
- 최적화 → performance tuning, optimization
- 아키텍처 → software architecture, system design

## 캐시 시스템

- **키워드 캐시**: `.thumbnail_cache/keyword_cache.json`
- **이미지 캐시**: `.thumbnail_cache/image_cache.json`
- **캐시 유효기간**: 24시간

캐시를 초기화하려면:
```bash
rm -rf .thumbnail_cache/
```

## 문제 해결

### 한글이 깨지는 경우
스크립트가 자동으로 시스템의 한글 폰트를 찾아 사용합니다:
1. AppleSDGothicNeo (macOS 기본)
2. NanumGothic (추가 설치 폰트)
3. Malgun Gothic (Windows)

### 이미지 다운로드 실패
Unsplash API가 사용 불가능한 경우 자동으로 폴백 이미지를 생성합니다.
- 기술 분야별 색상 스키마 적용
- 그라데이션 배경
- 장식적 요소 추가

### 썸네일이 덮어쓰기되지 않는 경우
기존 썸네일을 삭제 후 재실행:
```bash
rm assets/img/posts/파일명.webp
python auto_thumbnail_generator.py --current
```

## 포스트에 썸네일 적용

생성된 썸네일을 포스트에 적용하려면 포스트 YAML front matter에 추가:

```yaml
---
title: "포스트 제목"
categories: [Django, Python]
tags: [django, api, tdd]
image: /assets/img/posts/2025-08-14-example-post.webp
---
```

## 자동화 (선택사항)

### Git Hook으로 자동 실행
`.git/hooks/pre-commit` 파일에 추가:
```bash
#!/bin/bash
python auto_thumbnail_generator.py --recent 1
git add assets/img/posts/
```

### GitHub Actions로 자동 실행
`.github/workflows/thumbnails.yml`:
```yaml
name: Auto Generate Thumbnails
on:
  push:
    paths:
      - '_posts/*.md'
jobs:
  thumbnails:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Generate thumbnails
        run: |
          pip install Pillow requests PyYAML
          python auto_thumbnail_generator.py --recent 1
      - name: Commit thumbnails
        run: |
          git add assets/img/posts/
          git commit -m "Auto-generate thumbnails" || exit 0
          git push
```

## 고급 사용법

### 커스텀 키워드 매핑 추가
`.thumbnail_cache/keyword_cache.json` 파일을 편집하여 새로운 키워드 매핑을 추가할 수 있습니다.

### 색상 스키마 커스터마이징
스크립트 내의 `color_schemes` 딕셔너리를 수정하여 새로운 색상 조합을 추가할 수 있습니다.

## 성능 최적화

- 캐시 시스템으로 중복 작업 방지
- WebP 포맷으로 파일 크기 최소화
- 이미지 처리 최적화로 빠른 생성 속도

## 지원하는 포스트 형식

```yaml
---
title: "포스트 제목"
date: 2025-08-14
categories: [Technology, Programming]
tags: [python, django, aws, api]
---

포스트 내용...
```

이 도구로 블로그 포스트마다 일관되고 전문적인 썸네일을 자동으로 생성하세요! 🎨✨
