# SEO 최적화 가이드

## 포스트 작성시 Front Matter 예시

```yaml
---
layout: post
title: "AWS EC2 완전 정복 가이드"
description: "AWS EC2 인스턴스의 모든 것을 다루는 완전한 가이드입니다. 인스턴스 타입, 보안, 네트워킹까지"
date: 2025-07-05 10:00:00 +0900
categories: [aws-saa]
tags: [AWS, EC2, 클라우드, 인프라]
author: updaun
image: /assets/img/aws-ec2-guide.png # 대표 이미지 (옵션)
excerpt: "AWS EC2의 기본 개념부터 고급 설정까지, SAA 시험 준비를 위한 핵심 내용을 정리했습니다."
---
```

## 추가된 SEO 기능들

1. **Sitemap 자동 생성**: `jekyll-sitemap` 플러그인으로 `/sitemap.xml` 자동 생성
2. **Robots.txt**: 검색엔진 크롤러 가이드
3. **구조화된 데이터**: JSON-LD 형식으로 Google에게 콘텐츠 정보 제공
4. **Meta 태그**: description, keywords, author 등 SEO 핵심 요소
5. **Open Graph**: 소셜 미디어 공유시 미리보기 최적화

## 권장사항

1. **이미지 최적화**: 모든 이미지에 alt 텍스트 추가
2. **내부 링크**: 관련 포스트끼리 연결
3. **카테고리 활용**: 체계적인 분류로 사용자 경험 향상
4. **정기적인 업데이트**: 최신 정보로 유지

## 빌드 및 확인

```bash
bundle install
bundle exec jekyll serve
```

사이트 빌드 후 다음 URL들을 확인하세요:
- `/sitemap.xml`
- `/robots.txt`
- `/feed.xml`
