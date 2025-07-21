# 새 포스트 작성 가이드

새로운 포스트를 작성할 때 다음 메타데이터 템플릿을 사용하세요:

```yaml
---
layout: post
title: "포스트 제목 (SEO 최적화된 제목, 60자 이내)"
date: 2025-01-17
last_modified_at: 2025-01-17 # 수정 날짜
author: updaun
categories: [카테고리1, 카테고리2] # 최대 2-3개
tags: [tag1, tag2, tag3, tag4, tag5] # 5-10개 권장
excerpt: "포스트 요약문 (160자 이내, 검색 결과에 표시됨)"
description: "상세한 포스트 설명 (meta description용)"
image: "/assets/img/posts/포스트이미지.jpg" # 소셜 공유용 이미지
image_alt: "이미지 설명" # 접근성을 위한 alt 텍스트
canonical_url: "" # 다른 곳에 먼저 게시된 경우
redirect_from: # 이전 URL에서 리다이렉트하는 경우
  - /old-url/
  - /another-old-url/
sitemap: true # 사이트맵에 포함 여부
search: true # 검색에 포함 여부
comments: true # 댓글 허용 여부
share: true # 소셜 공유 허용 여부
toc: true # 목차 자동 생성 여부
math: false # 수학 공식 사용 여부
mermaid: false # 다이어그램 사용 여부
related: true # 관련 포스트 표시 여부
# 추가 SEO 설정
seo:
  type: "BlogPosting"
  links: # 관련 링크
    - "https://example.com/related-article"
# FAQ가 있는 경우
faq:
  - question: "질문 1"
    answer: "답변 1"
  - question: "질문 2"
    answer: "답변 2"
---

포스트 내용을 여기에 작성하세요...
```

## SEO 최적화 체크리스트

### 제목 최적화
- [ ] 제목이 60자 이내인가?
- [ ] 주요 키워드가 포함되었는가?
- [ ] 클릭하고 싶은 제목인가?

### 메타 설명 최적화
- [ ] excerpt가 160자 이내인가?
- [ ] 포스트 내용을 잘 요약하고 있는가?
- [ ] 검색자의 의도에 부합하는가?

### 내용 최적화
- [ ] H1, H2, H3 태그를 적절히 사용했는가?
- [ ] 키워드가 자연스럽게 포함되었는가?
- [ ] 이미지에 alt 텍스트를 추가했는가?
- [ ] 내부 링크를 적절히 활용했는가?
- [ ] 외부 링크에 적절한 속성을 추가했는가?

### 기술적 SEO
- [ ] 카테고리와 태그를 적절히 설정했는가?
- [ ] 이미지 최적화를 했는가?
- [ ] 로딩 속도를 고려했는가?
- [ ] 모바일 친화적인가?

### 사용자 경험
- [ ] 읽기 쉬운 구조인가?
- [ ] 목차가 있는가?
- [ ] 관련 포스트 연결이 되어있는가?
- [ ] 소셜 공유 버튼이 있는가?
