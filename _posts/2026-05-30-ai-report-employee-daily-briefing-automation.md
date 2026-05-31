---
layout: post
title: "AI Report 직원 만들기 — 웹 검색으로 정보를 모아 매일 정해진 시간에 보고하기"
date: 2026-05-30
categories: [cursor, ai, automation]
tags: [cursor, ai-agent, automation, daily-report, web-search, mcp, serpapi, productivity, briefing]
author: updaun
image: "https://pub-f5c290ac8b834bddbdf454a2a01e3a9b.r2.dev/assets/img/posts/2026-05-30-ai-report-employee-daily-briefing-automation.webp"
description: "AI가 웹 검색으로 필요한 정보를 찾아 매일 같은 시간에 브리핑하는 'Report 직원'을 Cursor Automations, /loop, Django+Celery 세 가지 경로로 만드는 실전 가이드입니다."
excerpt: "매일 아침 같은 질문을 반복하지 마세요. '무엇을 찾을지', '어떻게 검증할지', '언제 어디로 보낼지'만 정의하면 AI Report 직원이 대신 조사하고 요약해 옵니다. 웹 검색을 적극 쓰는 설계가 핵심입니다."
---

# AI Report 직원 만들기 — 웹 검색으로 정보를 모아 매일 정해진 시간에 보고하기

개발자·창업자·마케터에게 반복되는 아침 루틴이 하나 있습니다.

> "경쟁사 뭐 올렸지?"  
> "우리 키워드 순위 변했나?"  
> "어제 나온 Django/AI 관련 뉴스 뭐 있지?"  
> "GitHub 이슈·Slack에서 내가 놓친 게 있나?"

이걸 **사람이 매일 30~60분** 쓰는 대신, **AI Report 직원**에게 맡기는 구조를 만들 수 있습니다. 핵심은 단순합니다.

1. **무엇을 찾을지** — 관심 주제·키워드·경쟁사·내부 지표를 명시한다.  
2. **어떻게 검증할지** — LLM 기억이 아니라 **웹 검색·API·MCP**로 최신 근거를 수집한다.  
3. **언제 어디로 보낼지** — cron·Automations·Celery Beat로 **같은 시간·같은 형식**으로 배달한다.

이 글은 [AI 직원 고용하기](/2026/04/11/ai-agent-as-employee-hiring-guide/)에서 다룬 "Agent = 목표 + 도구 + 자율 실행" 개념을, **정보 수집·요약·정기 보고**에 특화한 **Report 직원** 한 명을 실제로 세팅하는 방법입니다.

> 프롬프트 설계 원칙은 [ESC Prompting](/2026/05/28/esc-equalizer-socratic-chain-prompting/)과 [프롬프트 엔지니어링 가이드](/2026/04/09/ai-prompt-engineering-for-developers-guide/)를 함께 보면 Report 품질이 올라갑니다.

---

## 0. 결론부터: Report 직원의 3대 구성요소

| 구성요소 | 역할 | 실패하면 생기는 일 |
|---|---|---|
| **Brief (업무 정의서)** | 찾을 주제, 제외할 노이즈, 출력 형식 | 매일 다른 형식의 잡담형 요약 |
| **Research Stack (조사 도구)** | Web Search, SerpAPI, MCP, 내부 API | 2024년 지식으로 쓴 "그럴듯한 환각" |
| **Delivery (배달·스케줄)** | Slack, 이메일, Notion, cron | 조사는 되는데 사람이 못 봄 |

**가장 흔한 실수**는 ChatGPT에 "매일 뉴스 알려줘"라고만 말하는 것입니다. 그건 **챗봇**이지 **직원**이 아닙니다. Report 직원은 **스케줄**, **도구 사용 권한**, **고정된 보고서 템플릿**이 있어야 합니다.

---

## 1. AI Report 직원 vs 일반 AI 챗봇

| 구분 | AI 챗봇 | AI Report 직원 |
|---|---|---|
| 실행 | 내가 열 때만 | **정해진 시간에 자동 실행** |
| 정보원 | 대화 + 모델 학습 데이터 | **웹 검색·API·DB** |
| 출력 | 자유 형식 | **고정 템플릿** (섹션·길이·우선순위) |
| 검증 | 없음 | **출처 URL·날짜·중복 제거** |
| 비용 | 대화당 | 실행당 (토큰 + 검색 API) |

Report 직원이 잘 맞는 업무:

- **산업·기술 동향** — "Django 6.x", "Cursor changelog", "국내 스마트팜 정책"
- **경쟁·시장** — 경쟁사 블로그, Product Hunt, 키워드 순위
- **운영 지표** — GA 주간 비교 ([GA 주간 리포트 서비스](/2026/03/12/django-ninja-google-analytics-weekly-report-service/) 참고)
- **개인 생산성** — 캘린더·이메일·Slack 하이라이트 (MCP/커넥터 연동)

Report 직원에 맞지 않는 업무:

- 법률·투자 **최종 판단**
- 출처 없이 "확실하다"고 단정해야 하는 **의료·안전** 정보
- **실시간** 트레이딩·장중 호가 (지연·환각 리스크)

---

## 2. 구현 경로 비교 — 무엇을 쓸지 고르기

2026년 기준, Report 직원을 만드는 대표 경로는 아래 네 가지입니다.

| 경로 | 적합한 사람 | 장점 | 단점 |
|---|---|---|---|
| **Cursor Automations** (no-repo) | Cursor 구독자, 코드 없이 빠르게 | 클라우드 cron, MCP·Slack 내장, 레포 불필요 | Cursor 사용량 과금, 커스텀 파이프라인 제한 |
| **Cursor `/loop`** | IDE 안에서 프로토타입·개발 중 모니터링 | 즉시 테스트, 로컬 파일 접근 | **세션이 열려 있어야** 실행 |
| **Claude Code Routines** | Claude Code Desktop/CLI 사용자 | 클라우드 스케줄, `/schedule` 대화형 설정 | Anthropic 생태계에 종속 |
| **Django Ninja + Celery Beat** | 직접 서비스로 운영하고 싶을 때 | 완전 통제, DB·히스토리·다중 사용자 | 구축·운영 비용 |

**추천 순서**: Cursor 사용자라면 **Automations로 MVP → 품질이 검증되면 Django로 제품화**.  
이미 [n8n 워크플로우](/2026/03/03/n8n-workflow-automation-guide/)를 쓰고 있다면, n8n cron + HTTP 노드 + LLM 노드 조합도 같은 패턴입니다.

---

## 3. 경로 A — Cursor Automations으로 Report 직원 고용 (가장 빠른 MVP)

2026년 5월, Cursor는 **Automations**로 클라우드 에이전트를 cron·Slack·GitHub 이벤트 등에 연결할 수 있게 했습니다. 특히 **no-repo 자동화**는 코드 저장소 없이 **외부 시스템 감시 + 요약 보고**에 맞습니다.

공식 문서: [Cursor Automations](https://cursor.com/docs/cloud-agent/automations)  
블로그 소개: [Build agents that run automatically](https://cursor.com/blog/automations)

### 3.1 설정 5단계

1. Cursor 대시보드 또는 Agents 창 → **Automations** → **Create**
2. **Trigger**: Scheduled → 매일 원하는 시간 (또는 cron, 예: `0 8 * * 1-5` = 평일 08:00)
3. **Repository**: **No repository** — 정보 수집·보고만 할 때
4. **Tools**: Web Search(또는 MCP), **Send to Slack** / 이메일 / Webhook
5. **Prompt**: 아래 Brief 템플릿 붙여넣기 → **Run Now**로 테스트 → 저장

### 3.2 Report 직원 Brief (프롬프트) 템플릿

```text
# Role
You are my AI Report employee. Your job is research + synthesis, not chat.

# Schedule context
Report for: {YYYY-MM-DD}, timezone Asia/Seoul.
Audience: backend developer running Django/Next.js side projects and a tech blog.

# Research rules (MANDATORY)
1. Use web search aggressively for EVERY factual claim. Do NOT rely on training data for news, versions, or pricing.
2. Prefer sources from the last 7 days unless I ask for historical context.
3. For each bullet, include: headline, 1-sentence insight, source URL, published date (if available).
4. Deduplicate overlapping stories. Skip press-release fluff without substance.
5. If search is inconclusive, say "확인 불가" — never invent.

# Topics (search each separately)
- Cursor IDE: changelog, Automations, pricing (last 7 days)
- Django / Python backend: security advisories, LTS news
- AI dev tools: Claude Code, Copilot agent updates
- Competitors / references: {경쟁사 A}, {경쟁사 B} — product or blog posts
- Optional internal: summarize if MCP {analytics/slack} is connected

# Output format (Korean, fixed sections)
## 🔴 오늘 꼭 볼 것 (max 3)
## 📰 업계·도구 동향 (max 5)
## 🎯 내 프로젝트에 영향 (max 3, actionable)
## 📎 출처 목록 (URL only, no duplicates)
## ⏱️ 다음 리포트 제안 (1 line: what to add/remove)

Keep total length under 800 words.
```

### 3.3 MCP로 "내부 정보"까지 합치기

웹 검색만으로는 **내 GA 숫자, Slack 스레드, Linear 이슈**를 못 봅니다. Automations에 MCP 서버를 연결하면 Report 직원이 **공개 웹 + 내부 도구**를 한 번에 조사합니다.

| MCP / 커넥터 | Report에 쓰는 방법 |
|---|---|
| Google Analytics | 어제 대비 트래픽·전환 변화 |
| Slack | `#dev` 채널 하이라이트 |
| Linear / GitHub | 열린 P0 이슈, 어제 머지된 PR |
| SerpAPI / Brave Search | 키워드·뉴스 정밀 검색 ([SerpAPI 가이드](/2026/04/28/serpapi-complete-guide/)) |

Cursor [개발자 꿀팁](/2026/05/29/cursor-developer-tips-community-collection/)에서 다룬 것처럼, MCP는 **Report 직원의 "눈과 손"**입니다. Rules 파일에 "항상 URL 인용" 같은 헌법을 두면 품질이 안정됩니다.

### 3.4 비용 감각

no-repo 일일 리포트(입력 ~50K 토큰, 출력 ~2K)는 Composer 계열 기준 **월 $1 미만** 수준으로 잡히는 경우가 많습니다(2026년 5월 Cursor Automations 요금 구조 기준, 실제 사용량·모델에 따라 변동). **Run Now**로 하루치 품질을 본 뒤 cron을 켜세요.

---

## 4. 경로 B — Cursor `/loop`으로 프로토타입·개발 중 브리핑

IDE 세션 안에서 **"매일 8시"가 아니라 "5분마다 배포 상태 확인"** 같은 반복 조사가 필요할 때는 **`/loop`** 가 맞습니다.

```text
/loop 1d 오늘 날짜 기준으로 Cursor·Django·AI 도구 뉴스를 웹 검색해 요약하고,
출처 URL 포함한 5줄 브리핑을 이 채팅에 남겨줘.
```

`/loop` 특성:

- **세션 스코프** — 새 채팅을 열면 루프가 끊김
- PC·Cursor가 켜져 있어야 함
- 개발 중 **프롬프트·주제 튜닝**에 최적

Automations로 넘기기 전에 `/loop 1d`로 **일주일치 샘플**을 모아 Brief를 다듬는 워크플로를 추천합니다.

---

## 5. 경로 C — Django Ninja + Celery Beat으로 "진짜" Report 서비스

팀·고객에게 Report를 **제품**으로 제공하거나, **히스토리·알림·다중 구독**이 필요하면 자체 서비스가 낫습니다. 이 블로그의 스택(Django Ninja, Celery, Redis)과 잘 맞습니다.

### 5.1 아키텍처

```text
[Celery Beat cron 08:00 KST]
        ↓
[generate_daily_report_task]
        ↓
┌───────────────────────────────────────┐
│ 1. ReportProfile DB에서 주제·키워드 로드 │
│ 2. SerpAPI / Tavily로 웹 검색 (병렬)    │
│ 3. LLM: dedupe + 섹션별 요약 + JSON     │
│ 4. ReportSnapshot DB 저장               │
│ 5. Slack / Email / Webhook 발송         │
└───────────────────────────────────────┘
```

Celery Beat 설정 패턴은 [Celery Beat 가이드](/2026/03/24/django-ninja-celery-beat-complete-guide/)의 `daily-statistics` 예시와 동일합니다.

### 5.2 핵심 코드 스케치

```python
# reports/tasks.py
from celery import shared_task
from datetime import date
import httpx
from openai import OpenAI

client = OpenAI()

SEARCH_QUERIES = [
    "Django security advisory site:djangoproject.com",
    "Cursor IDE changelog 2026",
    "AI coding agent automation news",
]


def web_search(query: str, num: int = 5) -> list[dict]:
    """SerpAPI 등 검색 API — LLM 환각 방지용 1차 근거."""
    resp = httpx.get(
        "https://serpapi.com/search.json",
        params={"engine": "google", "q": query, "api_key": settings.SERPAPI_KEY, "num": num},
        timeout=30,
    )
    resp.raise_for_status()
    return [
        {"title": r.get("title"), "link": r.get("link"), "snippet": r.get("snippet")}
        for r in resp.json().get("organic_results", [])
    ]


@shared_task(name="reports.generate_daily_report")
def generate_daily_report(profile_id: int):
    profile = ReportProfile.objects.get(pk=profile_id)
    raw_hits = []
    for q in profile.queries:
        raw_hits.extend(web_search(q))

    prompt = f"""
    You are an AI Report employee. Synthesize the search results below.
    Rules: cite URLs, Korean output, skip duplicates, flag uncertainty.
    Template sections: {profile.template_sections}
    Search results: {raw_hits[:40]}
    """
    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    body = completion.choices[0].message.content

    snapshot = ReportSnapshot.objects.create(
        profile=profile,
        report_date=date.today(),
        body_markdown=body,
        raw_sources=raw_hits,
    )
    send_slack(profile.slack_webhook_url, body)
    return snapshot.id
```

```python
# config/celery.py — beat schedule 예시
app.conf.beat_schedule = {
    "daily-ai-report-08am": {
        "task": "reports.generate_daily_report",
        "schedule": crontab(hour=8, minute=0),  # Celery timezone 설정 확인
        "args": (1,),  # profile_id
    },
}
```

**왜 SerpAPI(또는 Tavily)를 끼우나**: LLM에게 "검색해"만 시키면 도구 호출이 빠지거나 구식 정보를 씁니다. **검색 API → 구조화된 결과 → LLM 요약** 2단계가 Report 직원의 표준 패턴입니다.

---

## 6. Report 품질을 올리는 프롬프트·운영 팁

### 6.1 웹 검색을 "적극" 쓰게 만드는 문장

Brief에 아래 문장을 **항상** 넣으세요.

```text
Before writing each section, run at least one targeted web search.
If you did not search, do not write that section.
Training data cutoff is NOT a valid source for version numbers, pricing, or news.
```

### 6.2 ESC Prompting을 Report에 적용

| ESC 단계 | Report 직원 적용 |
|---|---|
| **Equalizer** | "800자 이하, 섹션 4개 고정, 불릿만" |
| **Socratic** | "내 프로젝트에 왜 중요한지 한 줄" 자문 |
| **Chain** | 검색 → 중복 제거 → 우선순위 → 최종 템플릿 |

### 6.3 사람 20% 검토 루틴

AI Report 직원도 **80/20**이 안전합니다.

- 🔴 섹션만 사람이 2분 스캔
- 틀린 URL·날짜가 보이면 Brief에 **금지 출처·선호 출처** 추가
- 한 달에 한 번 **주제·키워드** 정리 (Report 직원 "성과 평가")

### 6.4 실패 패턴 체크리스트

| 증상 | 원인 | 수정 |
|---|---|---|
| 매일 비슷한 뉴스 | 검색 쿼리가 너무 넓음 | 쿼리를 5~10개로 쪼개기 |
| 옛날 버전 번호 | 검색 생략 | Mandatory search 규칙 강화 |
| 너무 김 | Equalizer 없음 | 글자 수·불릿 수 상한 |
| Slack만 안 옴 | Tool 미선택 | Automations Tools 재확인 |

---

## 7. Claude Code Routines — Cursor 대안 한 줄 비교

Claude Code 사용자라면 **Routines**(`claude.ai/code/routines`)나 Desktop **Scheduled tasks**로 같은 Report 직원을 만들 수 있습니다. `/schedule weekday industry briefing at 8:30am`처럼 대화형으로 cron을 잡고, MCP 커넥터로 캘린더·Slack을 붙이는 패턴입니다.

| | Cursor Automations | Claude Routines |
|---|---|---|
| 클라우드 스케줄 | ✅ cron | ✅ (최소 1시간 간격 등 제약 확인) |
| no-repo 보고 | ✅ | ✅ |
| IDE `/loop` | ✅ | ✅ (세션 스코프) |
| Django 코드베이스와 통합 | MCP / webhook | MCP / webhook |

**도구는 하나만 고르면 됩니다.** Report 직원의 본질은 **Brief + Research Stack + Delivery**이지 IDE 브랜드가 아닙니다.

---

## 8. 7일 롤아웃 플랜

| Day | 할 일 |
|---|---|
| 1 | 관심 주제 5~10개, 제외 키워드, 출력 템플릿 초안 |
| 2 | `/loop 1d` 또는 **Run Now**로 3회 테스트 |
| 3 | 출처·날짜 누락 수정, Brief 강화 |
| 4 | Slack/이메일 배달 연결 |
| 5 | cron Automations 또는 Celery Beat 활성화 |
| 6~7 | 아침 2분 검토 → Brief 미세 조정 |

---

## 9. 정리 — Report 직원은 "더 똑똑한 챗봇"이 아니다

AI Report 직원은 **매일 같은 시간에, 같은 형식으로, 검색 근거와 함께** 조사 결과를 가져오는 **역할이 고정된 Agent**입니다.

1. **Brief**로 무엇을 찾을지 명시하고  
2. **웹 검색·MCP·API**로 최신성을 확보하며  
3. **Automations / Celery / Routines**로 사람 개입 없이 배달한다  

Cursor만 쓴다면 **Automations(no-repo) + Run Now 검증 + 평일 cron**이 가장 빠른 첫 고용입니다. Report가 비즈니스가 되면 [GA 주간 리포트](/2026/03/12/django-ninja-google-analytics-weekly-report-service/)처럼 Django 파이프라인으로 옮기면 됩니다.

---

## 참고 자료

- [Cursor Automations 공식 문서](https://cursor.com/docs/cloud-agent/automations)
- [Cursor — Build agents that run automatically](https://cursor.com/blog/automations)
- [Claude Code — Automate work with routines](https://code.claude.com/docs/en/routines)
- [Claude Code — Run prompts on a schedule (`/loop`)](https://code.claude.com/docs/en/scheduled-tasks)

---

## 관련 글

- [AI 직원 고용하기: Agent로 팀 자동화](/2026/04/11/ai-agent-as-employee-hiring-guide/)
- [Cursor 개발자 꿀팁 모음 2026](/2026/05/29/cursor-developer-tips-community-collection/)
- [SerpAPI 완전 가이드](/2026/04/28/serpapi-complete-guide/)
- [Django Ninja + Celery Beat 가이드](/2026/03/24/django-ninja-celery-beat-complete-guide/)
- [n8n 워크플로우 자동화](/2026/03/03/n8n-workflow-automation-guide/)
- [ESC Prompting](/2026/05/28/esc-equalizer-socratic-chain-prompting/)
