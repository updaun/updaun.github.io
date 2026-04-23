---
layout: post
title: "Claude Code 완전 입문 가이드 - 설치부터 실전 사용까지"
date: 2026-04-23
categories: ai-tools
author: updaun
---

# Claude Code 완전 입문 가이드 - 설치부터 실전 사용까지

AI 코딩 도구가 폭발적으로 성장하는 요즘, Anthropic이 만든 **Claude Code**가 개발자들 사이에서 주목받고 있습니다. 이 포스트는 Claude Code를 처음 접하는 분들을 위해 개념부터 실전 사용법까지 단계별로 알려드립니다.

---

## Claude Code란?

**Claude Code**는 Anthropic이 만든 AI 기반 코딩 어시스턴트입니다. 단순한 코드 자동완성 도구가 아니라, 여러분의 **전체 프로젝트를 이해하고 자율적으로 작업을 수행**하는 **에이전틱(agentic) 코딩 도구**입니다.

터미널, IDE(VS Code, JetBrains), 데스크탑 앱, 브라우저 등 다양한 환경에서 사용할 수 있으며, 핵심 기능은 다음과 같습니다:

- 프로젝트 코드베이스 전체를 분석하고 이해
- 파일을 직접 읽고 수정
- 셸 명령어 실행
- Git 작업 (커밋, 브랜치, PR 등)
- 버그 수정 및 기능 구현
- 테스트 코드 작성
- 코드 리뷰 및 리팩토링

---

## 사전 요건

Claude Code를 사용하려면 아래 중 하나가 필요합니다:

| 계정 종류 | 설명 |
|---|---|
| **Claude Pro / Max / Team / Enterprise** | 가장 추천하는 방법. claude.com 구독 계획 |
| **Anthropic Console (API)** | API 키 기반 선불 크레딧 방식 |
| **AWS Bedrock / Google Vertex AI** | 기업용 클라우드 제공자 |

> 처음 시작한다면 [claude.com/pricing](https://claude.com/pricing)에서 **Pro 플랜**을 구독하는 것이 가장 간편합니다.

---

## 설치 방법

### macOS / Linux / WSL

터미널을 열고 아래 명령어를 실행합니다:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

설치가 완료되면 `claude` 명령어가 자동으로 PATH에 등록됩니다. 설치 후에는 백그라운드에서 자동 업데이트가 이루어집니다.

### Windows (PowerShell)

PowerShell을 열고 실행합니다:

```powershell
irm https://claude.ai/install.ps1 | iex
```

> Windows 네이티브 환경에서는 [Git for Windows](https://git-scm.com/downloads/win)가 필요합니다. 먼저 설치해 두세요.

### Windows (CMD)

```cmd
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

### Linux 패키지 매니저 (apt / dnf / apk)

Debian, Fedora, RHEL, Alpine 계열 리눅스에서는 각 패키지 매니저로도 설치할 수 있습니다. 공식 문서 [Setup 페이지](https://code.claude.com/docs/en/setup#install-with-linux-package-managers)를 참고하세요.

---

## 로그인하기

설치 후 처음 `claude`를 실행하면 로그인을 요청합니다.

```bash
claude
```

터미널에서 자동으로 브라우저가 열리며 Anthropic 계정으로 로그인하면 됩니다. 로그인 정보는 기기에 저장되므로 이후에는 별도 로그인 없이 바로 사용할 수 있습니다.

나중에 계정을 전환하고 싶다면 Claude Code 내부에서 `/login` 명령어를 사용합니다.

---

## 첫 번째 세션 시작하기

프로젝트 디렉터리로 이동한 뒤 `claude`를 실행합니다:

```bash
cd /path/to/your/project
claude
```

Claude Code 환영 화면이 나타나면 준비 완료입니다. 이제 자연어로 원하는 작업을 입력하면 됩니다.

---

## 주요 사용 방법

### 1. 프로젝트 파악하기

처음 프로젝트에 투입됐을 때처럼 Claude Code에게 코드베이스를 설명해달라고 요청할 수 있습니다.

```
이 프로젝트가 무슨 일을 하는지 설명해줘
```

```
어떤 기술 스택을 사용하고 있어?
```

```
메인 엔트리 포인트는 어디야?
```

```
폴더 구조를 설명해줘
```

Claude Code는 파일을 직접 읽고 분석해서 답변해줍니다. 컨텍스트를 직접 붙여넣지 않아도 됩니다.

---

### 2. 코드 수정하기

자연어로 원하는 변경 사항을 요청하면 됩니다:

```
main 파일에 hello world 함수를 추가해줘
```

Claude Code가 작업을 수행할 때는 다음 순서로 진행됩니다:

1. 관련 파일을 찾아 분석
2. 변경 사항을 **미리 보여줌**
3. **승인을 요청**
4. 승인하면 파일 수정 실행

> 중요: Claude Code는 항상 파일을 수정하기 전에 **사용자 승인**을 요청합니다. 세션 중 "Accept all" 모드를 켜면 매번 확인 없이 자동 적용할 수도 있습니다.

---

### 3. 버그 수정하기

```
사용자가 빈 폼을 제출할 수 있는 버그가 있어 - 고쳐줘
```

```
user registration form에 입력값 유효성 검사를 추가해줘
```

Claude Code는 관련 코드를 찾아 컨텍스트를 이해하고, 해결책을 구현한 뒤 테스트까지 실행합니다.

---

### 4. Git 작업하기

Git 명령어를 외울 필요 없이 자연어로 요청하면 됩니다:

```
내가 수정한 파일이 뭐야?
```

```
변경사항을 설명력 있는 커밋 메시지로 커밋해줘
```

```
feature/login 이라는 브랜치를 새로 만들어줘
```

```
최근 5개 커밋을 보여줘
```

```
머지 충돌 해결하는 것 도와줘
```

---

### 5. 테스트 작성하기

```
calculator 함수들에 대한 유닛 테스트를 작성해줘
```

---

### 6. 리팩토링하기

```
authentication 모듈을 콜백 방식 대신 async/await로 리팩토링해줘
```

---

### 7. 문서 업데이트하기

```
README에 설치 방법을 업데이트해줘
```

---

### 8. 코드 리뷰 받기

```
내 변경사항을 리뷰하고 개선점을 제안해줘
```

---

## 필수 명령어 정리

| 명령어 | 설명 | 예시 |
|---|---|---|
| `claude` | 대화형 모드 시작 | `claude` |
| `claude "task"` | 일회성 작업 실행 후 종료 | `claude "빌드 에러 수정해줘"` |
| `claude -p "query"` | 단일 질의 후 즉시 종료 | `claude -p "이 함수 설명해줘"` |
| `claude -c` | 현재 디렉터리 최근 대화 이어서 시작 | `claude -c` |
| `claude -r` | 이전 대화 목록에서 선택해서 재개 | `claude -r` |
| `/clear` | 대화 기록 초기화 | `/clear` |
| `/help` | 사용 가능한 명령어 확인 | `/help` |
| `/login` | 계정 전환 | `/login` |
| `exit` 또는 `Ctrl+D` | Claude Code 종료 | `exit` |

---

## VS Code에서 사용하기

터미널 CLI 외에도 VS Code 확장으로 Claude Code를 사용할 수 있습니다.

VS Code 확장 마켓플레이스에서 **"Claude Code"**를 검색하여 설치하면, 에디터 패널 안에서 바로 Claude Code 대화창을 사용할 수 있습니다. 파일을 열어놓은 상태에서 컨텍스트가 자동으로 연결됩니다.

---

## 초보자를 위한 팁

### 구체적으로 요청하기

모호한 요청보다 구체적인 요청이 훨씬 좋은 결과를 냅니다.

```
# 애매한 요청
코드 고쳐줘

# 구체적인 요청
api/views.py의 login 함수에서 비밀번호가 틀렸을 때 에러 메시지를 한국어로 반환하도록 수정해줘
```

### 단계별로 요청하기

복잡한 작업은 한 번에 요청하기보다 여러 단계로 나눠서 요청하면 더 정확합니다.

```
1단계: 먼저 현재 인증 코드 구조를 설명해줘
2단계: JWT 토큰 방식으로 변경하는 계획을 세워줘
3단계: 계획에 따라 실제로 구현해줘
```

### Claude가 먼저 탐색하게 하기

바로 수정을 요청하기 전에 코드를 먼저 파악하게 하면 더 나은 결과를 얻을 수 있습니다.

```
수정하기 전에 먼저 관련 파일들을 분석해서 현재 구조를 설명해줘
```

### CLAUDE.md 파일 활용하기

프로젝트 루트에 `CLAUDE.md` 파일을 만들어두면 Claude Code가 세션마다 이 파일을 읽어 프로젝트 컨텍스트를 자동으로 파악합니다.

```markdown
# CLAUDE.md

## 프로젝트 개요
Django Ninja로 만든 REST API 백엔드입니다.

## 주요 규칙
- Python 3.12 사용
- 모든 API는 /api/v1/ 경로로 시작
- 에러 응답 형식: {"error": "메시지"}

## 자주 사용하는 명령어
- 서버 실행: python manage.py runserver
- 테스트: pytest
```

---

## 요금 안내

| 플랜 | 월 요금 | 특징 |
|---|---|---|
| **Claude Pro** | $20/월 | 개인 개발자에게 적합 |
| **Claude Max** | $100/월 ~ | 더 많은 사용량 |
| **Claude Team** | $25/인/월 | 팀 단위 사용 |
| **Console (API)** | 사용량 기반 | 직접 API 키 사용 |

> [공식 요금 페이지](https://claude.com/pricing)에서 최신 정보를 확인하세요. 요금은 변경될 수 있습니다.

---

## 자주 묻는 질문 (FAQ)

**Q. ChatGPT나 GitHub Copilot과 어떻게 다른가요?**

A. GitHub Copilot은 주로 코드 자동완성에 특화되어 있습니다. Claude Code는 프로젝트 전체를 이해하고 파일을 읽고 쓰며 명령어도 직접 실행하는 **에이전트** 방식입니다. 여러 파일에 걸친 복잡한 작업에 강점이 있습니다.

**Q. 보안이 걱정됩니다. 코드가 유출되지 않나요?**

A. 코드는 Claude Code가 작업을 처리하는 동안 Anthropic 서버로 전송됩니다. 기업 보안 정책에 따라 AWS Bedrock이나 Google Vertex AI를 통해 기업 환경에서 격리하여 사용하는 방법도 있습니다.

**Q. 인터넷이 없으면 사용할 수 없나요?**

A. 네, Claude Code는 클라우드 기반 서비스이므로 인터넷 연결이 필요합니다.

**Q. 어떤 언어를 지원하나요?**

A. Python, JavaScript, TypeScript, Java, Go, Rust, C/C++, Ruby 등 대부분의 프로그래밍 언어를 지원합니다.

---

## 마치며

Claude Code는 단순한 코드 자동완성 도구를 넘어, 개발자의 **페어 프로그래머**처럼 동작합니다. 처음에는 어색하게 느껴질 수 있지만, 자연어로 작업을 지시하고 결과를 검토하는 방식에 익숙해지면 생산성이 크게 향상됩니다.

핵심은 **Claude를 동료 개발자처럼 대하는 것**입니다. 달성하고자 하는 목표를 명확하게 설명하고, 결과를 검토하며 피드백을 주는 방식으로 협업하면 됩니다.

오늘 당장 설치해서 여러분의 프로젝트에 적용해보세요!

---

## 참고 자료

- [Claude Code 공식 문서](https://code.claude.com/docs/en/overview)
- [Quickstart 가이드](https://code.claude.com/docs/en/quickstart)
- [공통 워크플로우](https://code.claude.com/docs/en/common-workflows)
- [CLI 레퍼런스](https://code.claude.com/docs/en/cli-reference)
- [요금 안내](https://claude.com/pricing)
