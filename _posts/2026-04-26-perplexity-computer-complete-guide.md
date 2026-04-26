---
layout: post
title: "Perplexity Computer 완전 가이드 - 자동화할 수 있는 모든 것"
date: 2026-04-26
categories: ai-tools
author: updaun
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-04-26-perplexity-computer-complete-guide.webp"
---

# Perplexity Computer 완전 가이드 - 자동화할 수 있는 모든 것

AI 에이전트가 단순한 채팅봇을 넘어 **실제 업무를 수행하는 디지털 워커**로 진화하고 있습니다. 2026년 2월 Perplexity가 공개한 **Perplexity Computer**는 그 진화의 정점에 있습니다. 이 포스트에서는 Perplexity Computer가 무엇인지, 어떤 기능을 제공하는지, 그리고 실제로 무엇을 자동화할 수 있는지 정리합니다.

---

## Perplexity Computer란?

**Perplexity Computer**는 단일 AI 모델이 아닌, **여러 최전선 AI 모델을 오케스트레이션하는 범용 디지털 워커 시스템**입니다.

기존 AI 도구와의 가장 큰 차이는 다음과 같습니다:

| 기존 AI 채팅 | Perplexity Computer |
|---|---|
| 질문에 답을 줌 | 전체 워크플로우를 직접 실행 |
| 단일 모델 | 멀티 모델 오케스트레이션 |
| 한 번의 응답으로 끝 | 수시간~수개월 지속 실행 가능 |
| 사람이 결과를 가져다 씀 | 결과물을 직접 전달 |

### 내부 아키텍처

Perplexity Computer는 현재 다음 모델들을 작업 유형에 따라 자동으로 배분합니다:

- **Opus 4.6** - 핵심 추론 엔진
- **Gemini** - 딥 리서치 및 서브에이전트 생성
- **Nano Banana** - 이미지 생성
- **Veo 3.1** - 영상 제작
- **Grok** - 경량 고속 작업
- **ChatGPT 5.2** - 장문 컨텍스트 처리 및 광범위한 검색

> 어떤 모델을 쓸지 신경 쓸 필요가 없습니다. Computer가 작업에 가장 적합한 모델을 자동 선택합니다.

---

## 핵심 기능 5가지

### 1. 멀티 에이전트 병렬 실행

하나의 목표를 받으면 Computer는 이를 **여러 서브태스크로 분해**하고, 각 서브태스크에 전용 에이전트를 생성해 병렬로 실행합니다.

```
목표: "경쟁사 3곳의 가격 정책을 분석해서 보고서로 만들어줘"

├── 에이전트 A: 경쟁사 A 웹사이트 크롤링 + 가격 정보 추출
├── 에이전트 B: 경쟁사 B 가격 페이지 분석
├── 에이전트 C: 경쟁사 C 최신 공지 및 블로그 리서치
└── 오케스트레이터: 결과 취합 → Word/PDF 보고서 생성
```

모든 에이전트는 **독립된 샌드박스 환경**에서 실행되며, 실제 파일시스템과 브라우저에 접근할 수 있습니다.

---

### 2. 400개 이상의 커넥터 연동

Perplexity Computer는 주요 SaaS 도구들과 직접 연동됩니다:

- **협업**: Slack, Notion, Google Workspace, Microsoft 365
- **데이터**: Snowflake, Google Analytics, Airtable
- **결제/금융**: Plaid, Stripe
- **개발**: GitHub, Jira, Linear
- **마케팅**: HubSpot, GoHighLevel

단순히 데이터를 읽는 수준이 아니라, **메시지를 보내고, 파일을 생성하고, 데이터를 업데이트**하는 액션까지 수행합니다.

---

### 3. Personal Computer - 로컬 환경 통합

2026년 4월 출시된 **Personal Computer**는 Perplexity Computer를 사용자의 **맥 로컬 환경**으로 확장합니다.

- 로컬 파일, 네이티브 앱, 웹을 하나의 오케스트레이션 시스템으로 통합
- **Mac mini에서 24/7 상시 실행** 가능 (휴대폰으로 원격 지시)
- `CMD + CMD` 단축키로 어디서든 즉시 호출
- iMessage, 이메일, 로컬 앱을 가로질러 작업 수행

---

### 4. Slack 네이티브 통합

Perplexity Computer는 Slack에서 **@Computer**를 태그하는 것만으로 사용 가능합니다.

- 채널 내 공개 작업: 팀 전체가 컨텍스트를 공유하며 협업
- DM 작업: 개인 초안 작성, 빠른 리서치
- MCP 커넥터를 통해 Slack 워크스페이스 지식 검색 가능
- Slack Marketplace에서 바로 설치 가능

> Perplexity 내부에서만 사용했을 때 첫 4주 동안 300명 직원이 **160만 달러 상당의 업무**를 처리했습니다.

---

### 5. 도메인 전문 지식 모듈 (Agent Skills)

단순 범용 AI가 아닌, 특정 도메인에 특화된 **전문 지식 모듈**을 로드하는 구조입니다.

현재 제공 중인 예시:
- **세금 모듈**: IRS 최신 규정 기반 미국 연방세 신고서 초안 작성, 전문가가 작성한 신고서 검토, 세금 대시보드 자동 구축
- 향후 금융, 법률, 의료 등 다양한 도메인으로 확장 예정

---

## 실제 활용 예시 8가지

### 예시 1. 일간 리서치 리포트 자동화

**시나리오**: 매일 오전 특정 키워드의 뉴스를 수집해 요약 보고서를 Slack에 전송

```
프롬프트:
"매일 오전 9시에 'AI 에이전트', 'LLM 최신 동향' 키워드로
최신 뉴스 5건을 수집하고, 각 기사를 3줄로 요약해서
#ai-news Slack 채널에 게시해줘."
```

**Computer 동작 과정**:
1. Gemini 서브에이전트 → 웹 크롤링 및 뉴스 검색
2. Opus 4.6 → 요약 및 분류
3. Slack 커넥터 → 지정 채널에 포맷에 맞게 게시

---

### 예시 2. 경쟁사 모니터링 자동화

**시나리오**: 경쟁사의 가격 변동, 신규 기능 출시, 채용 공고를 주간으로 트래킹

```
프롬프트:
"매주 월요일에 [경쟁사 A], [경쟁사 B], [경쟁사 C]의
공식 웹사이트, 블로그, LinkedIn, 채용 공고를 분석해서
'가격 변동', '신규 기능', '채용 트렌드' 섹션으로 구성된
Google Docs 보고서를 작성하고 팀 이메일로 공유해줘."
```

---

### 예시 3. Downloads 폴더 자동 정리 (Personal Computer)

**시나리오**: 어지럽게 쌓인 로컬 Downloads 폴더를 프로젝트별로 자동 분류

```
Mac에서 CMD + CMD → Computer 호출

"Downloads 폴더의 파일들을 분석해서
프로젝트, 날짜, 파일 유형을 기준으로
의미 있는 폴더 구조로 재정리해줘."
```

**Computer 동작**:
- 파일명, 내용, 생성일 분석
- 프로젝트별 폴더 자동 생성
- 파일 이동 전 미리보기 제공 (가역적 액션)

---

### 예시 4. 영업 콜 요약 자동화

**시나리오**: 영업 팀의 미팅 녹화본을 자동 분석해 담당자에게 보고

```
Slack에서 @Computer에게:

"GoHighLevel에서 이번 주 영업 미팅 녹화본을 찾아서
각 콜의 고객 이름, 주요 니즈, 다음 액션 아이템을 정리하고
영업 매니저에게 Slack DM으로 요약 보고서를 보내줘."
```

---

### 예시 5. OKR 킥오프 덱 자동 생성

**시나리오**: 분기 전략 문서와 이전 OKR 결과를 토대로 발표 자료 자동 제작

```
Slack에서 @Computer에게:

"2026년 Q1 OKR 결과 파일과 Q2 전략 문서를 읽어서
Q2 OKR 킥오프 발표용 Google Slides를 만들어줘.
이전 달성률과 다음 분기 목표, 팀별 KR을 포함해줘."
```

---

### 예시 6. 세금 신고서 초안 자동화

**시나리오**: 미국 연방세 신고서 초안을 AI가 직접 작성

```
Perplexity Computer에서 "Navigate my taxes" 선택 후:

"작년도 W-2, 1099-DIV, 주택담보대출 이자 서류를
업로드할게. IRS 공식 양식 기준으로 연방세 신고서 초안을
작성하고, 내가 놓쳤을 수 있는 공제 항목도 알려줘."
```

**Computer 동작**:
- 최신 IRS 세금 모듈 로드
- 문서 분석 및 소득/공제 항목 추출
- 공식 IRS 양식에 맞게 신고서 초안 작성
- 오류 및 미청구 공제 항목 플래그 처리

---

### 예시 7. 제안서 팩트체크 및 법적 리스크 검토

**시나리오**: 파트너십 제안서를 받았을 때 빠른 1차 검토 자동화

```
Slack에서 @Computer에게:
파일 첨부 후:

"이 파트너십 제안서를 검토해서:
1. 통계 수치 팩트체크
2. 법적으로 리스크가 있는 조항 표시
3. 수정 제안이 포함된 Word 파일로 돌려줘."
```

---

### 예시 8. 할 일 목록 자동 실행 (Personal Computer)

**시나리오**: Notes 앱에 적어둔 to-do 목록을 Computer가 직접 처리

```
Mac에서 CMD + CMD → Computer 호출:

"Notes 앱의 오늘 할 일 목록을 읽고,
처리할 수 있는 항목들을 직접 완료해줘."
```

**Computer 동작 예시**:
- "김철수에게 미팅 확인 이메일 보내기" → 이메일 자동 작성 및 발송
- "AWS 비용 보고서 다운로드" → 브라우저로 AWS 콘솔 접속, 다운로드
- "팀 Notion 업데이트" → Notion API 통해 해당 페이지 갱신

---

## 보안과 제어

AI가 내 파일과 앱에 접근한다는 점에서 보안은 핵심 우려사항입니다. Perplexity Computer는 다음 원칙을 따릅니다:

- **샌드박스 격리**: 모든 태스크는 독립된 격리 환경에서 실행
- **가역적 액션**: 실행 전 미리보기 제공, 되돌리기 가능
- **감사 로그**: 모든 액션은 기록되어 추적 가능
- **민감 액션 체크인**: 중요한 결정이 필요할 때 사용자에게 확인 요청
- **1Password 통합**: 자격증명은 암호화된 비밀번호 관리자를 통해 안전하게 처리

---

## 이용 방법 및 요금

| 플랜 | Computer 이용 여부 |
|---|---|
| Perplexity Free / Pro | ❌ |
| **Perplexity Max** | ✅ (웹 Computer + Personal Computer) |
| Perplexity Enterprise Max | ✅ (Enterprise Computer) |

- **웹 버전**: [perplexity.ai](https://perplexity.ai) 접속 후 Computer 탭 선택
- **Slack 통합**: [Slack Marketplace에서 설치](https://perplexityai.slack.com/marketplace/A07NV1D07QT-perplexity-computer)
- **Personal Computer (Mac)**: [다운로드 페이지](https://www.perplexity.ai/personal-computer)에서 설치 (Max 구독자 우선 롤아웃 중)

---

## 마치며

Perplexity Computer는 단순히 "더 똑똑한 검색엔진"이 아닙니다. 출시 2주 만에 Max 구독자들의 **9,100만 달러 상당의 업무**를 처리했고, 엔터프라이즈에서는 누적 **7억 7,600만 달러**의 노동 동등 가치를 만들어냈다고 Perplexity는 밝혔습니다.

AI가 단순 조언을 넘어 **직접 실행하는 시대**가 열렸습니다. 지금 당장 반복적으로 수동으로 처리하고 있는 업무가 있다면, Perplexity Computer에게 맡겨볼 적기입니다.

---

**참고 링크**
- [Introducing Perplexity Computer](https://www.perplexity.ai/hub/blog/introducing-perplexity-computer)
- [Personal Computer is here](https://www.perplexity.ai/hub/blog/personal-computer-is-here)
- [Computer in Slack](https://www.perplexity.ai/hub/blog/computer-in-slack-from-shared-context-to-finished-work)
- [Introducing Computer for Taxes](https://www.perplexity.ai/hub/blog/introducing-computer-for-taxes)
