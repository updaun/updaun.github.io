---
layout: post
title: "Dockerfile 완벽 가이드: 기초부터 실전 최적화까지"
date: 2025-12-19 09:00:00 +0900
categories: [DevOps, Docker, Container]
tags: [Docker, Dockerfile, Container, DevOps, Multi-stage, Best-Practices, Security, Optimization]
description: "Dockerfile 작성의 기본 개념부터 멀티스테이지 빌드, 보안 강화, 성능 최적화까지 실무에서 바로 적용 가능한 완벽 가이드"
image: "/assets/img/posts/2025-12-19-dockerfile-complete-guide-from-basics-to-advanced.webp"
---

## 목차

1. [소개 - Docker와 Dockerfile이란?](#1-소개---docker와-dockerfile이란)
2. [Dockerfile 기본 구조와 핵심 명령어](#2-dockerfile-기본-구조와-핵심-명령어)
3. [첫 번째 Dockerfile 작성하기](#3-첫-번째-dockerfile-작성하기)
4. [레이어 캐싱과 빌드 최적화](#4-레이어-캐싱과-빌드-최적화)
5. [멀티스테이지 빌드로 이미지 크기 줄이기](#5-멀티스테이지-빌드로-이미지-크기-줄이기)
6. [보안 강화 베스트 프랙티스](#6-보안-강화-베스트-프랙티스)
7. [실전 예제: 다양한 언어별 Dockerfile](#7-실전-예제-다양한-언어별-dockerfile)
8. [고급 기법과 성능 최적화](#8-고급-기법과-성능-최적화)
9. [디버깅과 트러블슈팅](#9-디버깅과-트러블슈팅)
10. [결론 및 체크리스트](#10-결론-및-체크리스트)

---

## 1. 소개 - Docker와 Dockerfile이란?

### 1.1 Docker의 등장 배경

"내 컴퓨터에서는 되는데요?"라는 말은 개발자들 사이에서 오랫동안 농담처럼 사용되어 왔습니다. 개발 환경과 프로덕션 환경의 불일치, 의존성 충돌, 운영체제 차이 등으로 인해 발생하는 문제들은 소프트웨어 배포의 가장 큰 골칫거리였습니다. Docker는 이러한 문제를 근본적으로 해결하기 위해 등장했습니다. 2013년 Solomon Hykes가 PyCon에서 발표한 이후, Docker는 컨테이너 기술을 대중화하며 현대 소프트웨어 개발의 표준이 되었습니다.

### 1.2 Dockerfile의 역할

Dockerfile은 Docker 이미지를 생성하기 위한 설계도입니다. 마치 레시피가 요리를 만드는 과정을 단계별로 기술하듯이, Dockerfile은 애플리케이션 실행 환경을 코드로 정의합니다. 베이스 이미지 선택, 파일 복사, 의존성 설치, 환경변수 설정 등 모든 과정이 명령어로 작성되어 있어, 누구나 동일한 환경을 재현할 수 있습니다. 이것이 바로 "Infrastructure as Code"의 핵심 개념입니다.

### 1.3 왜 Dockerfile을 잘 작성해야 하는가?

Dockerfile 작성 방법에 따라 이미지 크기가 수 GB에서 수십 MB로 줄어들 수 있으며, 빌드 시간도 몇 분에서 몇 초로 단축될 수 있습니다. 또한 잘못 작성된 Dockerfile은 보안 취약점을 만들거나 프로덕션에서 예상치 못한 오류를 발생시킬 수 있습니다. 본 가이드에서는 기초부터 시작하여 실무에서 바로 적용할 수 있는 최적화 기법까지 단계별로 다루겠습니다.

---

## 2. Dockerfile 기본 구조와 핵심 명령어

### 2.1 Dockerfile의 기본 구조

Dockerfile은 텍스트 파일로, 일반적으로 프로젝트 루트에 `Dockerfile`이라는 이름(확장자 없음)으로 저장됩니다. 각 줄은 하나의 명령어(instruction)로 시작하며, 위에서 아래로 순차적으로 실행됩니다. 주석은 `#`으로 시작합니다. 기본 구조는 다음과 같습니다:

```dockerfile
# 베이스 이미지 선택
FROM <이미지:태그>

# 메타데이터 추가
LABEL maintainer="your-email@example.com"

# 작업 디렉토리 설정
WORKDIR /app

# 파일 복사
COPY . .

# 명령 실행
RUN <명령어>

# 환경변수 설정
ENV KEY=VALUE

# 포트 노출
EXPOSE 8080

# 컨테이너 시작 명령
CMD ["executable", "param1", "param2"]
```

### 2.2 필수 명령어: FROM

`FROM`은 모든 Dockerfile의 시작점입니다. 베이스 이미지를 지정하며, 반드시 첫 번째 명령어여야 합니다(ARG 제외). 베이스 이미지는 Docker Hub 같은 레지스트리에서 가져옵니다:

```dockerfile
# 공식 이미지 사용
FROM python:3.11-slim

# 특정 버전 지정
FROM node:18.17.0-alpine

# 특정 플랫폼 지정
FROM --platform=linux/amd64 ubuntu:22.04

# 스크래치부터 시작 (최소 이미지)
FROM scratch
```

**베스트 프랙티스**: 항상 특정 버전 태그를 사용하세요. `latest` 태그는 예측 불가능한 동작을 야기할 수 있습니다. Alpine 기반 이미지는 크기가 작아 선호되지만, glibc 대신 musl을 사용하므로 호환성 문제가 있을 수 있습니다.

### 2.3 파일 추가: COPY vs ADD

`COPY`와 `ADD`는 모두 호스트에서 컨테이너로 파일을 복사하지만, `ADD`는 추가 기능(URL 다운로드, 압축 해제)을 제공합니다:

```dockerfile
# COPY: 단순 복사 (권장)
COPY requirements.txt .
COPY src/ /app/src/

# 소유권 변경과 함께 복사
COPY --chown=node:node package*.json ./

# ADD: URL 다운로드 가능
ADD https://example.com/file.tar.gz /tmp/

# ADD: 자동 압축 해제
ADD archive.tar.gz /app/
```

**베스트 프랙티스**: 명확성을 위해 `COPY`를 사용하고, 압축 해제가 필요한 경우에만 `ADD`를 사용하세요. URL 다운로드는 `RUN curl` 또는 `RUN wget`으로 명시적으로 수행하는 것이 좋습니다.

### 2.4 명령 실행: RUN

`RUN`은 이미지 빌드 중에 명령을 실행하고 그 결과를 새 레이어에 커밋합니다. 패키지 설치, 파일 생성 등에 사용됩니다:

```dockerfile
# Shell 형식 (sh -c로 실행)
RUN apt-get update && apt-get install -y curl

# Exec 형식 (셸 없이 직접 실행, 권장)
RUN ["apt-get", "update"]

# 여러 명령을 한 레이어로 결합
RUN apt-get update && \
    apt-get install -y \
        curl \
        vim \
        git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Python 예제
RUN pip install --no-cache-dir -r requirements.txt
```

**베스트 프랙티스**: 레이어 수를 줄이기 위해 관련 명령을 `&&`로 연결하세요. 캐시를 정리하여 이미지 크기를 줄이세요.

### 2.5 작업 디렉토리: WORKDIR

`WORKDIR`은 이후 명령어들이 실행될 작업 디렉토리를 설정합니다. 디렉토리가 없으면 자동으로 생성됩니다:

```dockerfile
# 작업 디렉토리 설정
WORKDIR /app

# 이제 모든 명령이 /app에서 실행됨
COPY . .
RUN npm install

# 하위 디렉토리로 이동 가능
WORKDIR /app/src
```

**베스트 프랙티스**: `RUN cd /app` 대신 `WORKDIR /app`을 사용하세요. `cd`는 해당 RUN 명령에만 적용되지만, WORKDIR은 이후 모든 명령에 영향을 줍니다.

### 2.6 환경변수: ENV vs ARG

`ENV`는 런타임 환경변수를, `ARG`는 빌드 타임 변수를 정의합니다:

```dockerfile
# 빌드 시에만 사용되는 변수
ARG NODE_VERSION=18
FROM node:${NODE_VERSION}

ARG BUILD_DATE
ARG VERSION=1.0.0

# 런타임에도 사용 가능한 환경변수
ENV NODE_ENV=production
ENV PORT=3000
ENV DATABASE_URL=postgresql://localhost:5432/db

# 여러 변수를 한 번에
ENV APP_HOME=/app \
    APP_USER=appuser \
    APP_GROUP=appgroup

# ARG를 ENV로 전달
ARG VERSION
ENV APP_VERSION=${VERSION}
```

**베스트 프랙티스**: 민감한 정보(비밀번호, API 키)는 ENV나 ARG로 하드코딩하지 마세요. Docker secrets이나 환경변수 주입을 사용하세요.

### 2.7 포트 노출: EXPOSE

`EXPOSE`는 컨테이너가 리스닝할 포트를 문서화합니다. 실제로 포트를 열지는 않으며, `docker run -p`로 매핑이 필요합니다:

```dockerfile
# 단일 포트
EXPOSE 8080

# 여러 포트
EXPOSE 80 443

# 프로토콜 지정
EXPOSE 8080/tcp
EXPOSE 8080/udp
```

### 2.8 컨테이너 시작: CMD vs ENTRYPOINT

`CMD`는 컨테이너 시작 시 실행될 기본 명령을, `ENTRYPOINT`는 항상 실행될 명령을 정의합니다:

```dockerfile
# CMD: 기본 명령 (docker run 시 오버라이드 가능)
CMD ["python", "app.py"]
CMD ["npm", "start"]

# ENTRYPOINT: 고정 명령
ENTRYPOINT ["python"]
CMD ["app.py"]  # ENTRYPOINT의 기본 파라미터

# Shell 형식 (권장하지 않음 - PID 1 문제)
CMD python app.py

# Exec 형식 (권장)
CMD ["python", "app.py"]
```

**차이점**: 
- `CMD`만 있으면: `docker run myimage other-command`가 CMD를 대체
- `ENTRYPOINT` + `CMD`: `docker run myimage other-arg`가 other-arg를 CMD 대신 ENTRYPOINT에 전달

```dockerfile
# 예제: 유연한 CLI 도구
ENTRYPOINT ["python", "cli.py"]
CMD ["--help"]

# docker run myimage → python cli.py --help
# docker run myimage --version → python cli.py --version
```

### 2.9 사용자 설정: USER

`USER`는 이후 명령을 실행할 사용자를 지정합니다. 보안을 위해 root가 아닌 사용자로 실행하는 것이 좋습니다:

```dockerfile
# 사용자 생성 및 전환
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 권한 설정
RUN chown -R appuser:appuser /app

# 사용자 전환
USER appuser

# 이후 명령은 appuser로 실행됨
CMD ["python", "app.py"]
```

### 2.10 헬스체크: HEALTHCHECK

`HEALTHCHECK`는 컨테이너의 상태를 주기적으로 확인합니다:

```dockerfile
# HTTP 엔드포인트 체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Python 스크립트 체크
HEALTHCHECK CMD python healthcheck.py

# 헬스체크 비활성화
HEALTHCHECK NONE
```

---

## 3. 첫 번째 Dockerfile 작성하기

### 3.1 간단한 Python Flask 애플리케이션

실제 작동하는 애플리케이션으로 시작해봅시다. 먼저 간단한 Flask 앱을 만들겠습니다:

```python
# app.py
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, Docker!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

```text
# requirements.txt
Flask==3.0.0
```

### 3.2 기본 Dockerfile 작성

위 애플리케이션을 위한 가장 기본적인 Dockerfile입니다:

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
```

### 3.3 이미지 빌드 및 실행

```bash
# 이미지 빌드
docker build -t my-flask-app:1.0 .

# 빌드 로그 확인
docker build -t my-flask-app:1.0 . --progress=plain

# 컨테이너 실행
docker run -p 5000:5000 my-flask-app:1.0

# 백그라운드 실행
docker run -d -p 5000:5000 --name flask-container my-flask-app:1.0

# 테스트
curl http://localhost:5000
```

### 3.4 Node.js Express 애플리케이션

이번에는 Node.js 애플리케이션을 컨테이너화해봅시다:

```javascript
// server.js
const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.get('/', (req, res) => {
    res.json({ message: 'Hello from Docker!' });
});

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
```

```json
{
  "name": "docker-express-app",
  "version": "1.0.0",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^4.18.2"
  }
}
```

### 3.5 Node.js용 Dockerfile

```dockerfile
# Dockerfile
FROM node:18-alpine

# 작업 디렉토리 설정
WORKDIR /usr/src/app

# package.json과 package-lock.json 복사
# 의존성만 먼저 복사하여 캐시 활용
COPY package*.json ./

# 의존성 설치
RUN npm ci --only=production

# 애플리케이션 소스 복사
COPY . .

# 포트 노출
EXPOSE 3000

# 비-root 사용자로 실행
USER node

# 애플리케이션 시작
CMD ["npm", "start"]
```

**주요 개선사항**:
- `npm ci`: npm install보다 빠르고 재현 가능한 빌드
- `--only=production`: devDependencies 제외
- `USER node`: Alpine 이미지에 내장된 node 사용자 활용
- package.json을 소스코드보다 먼저 복사하여 캐시 활용

### 3.6 Go 애플리케이션 (정적 바이너리)

Go는 정적 바이너리를 생성하므로 매우 작은 이미지를 만들 수 있습니다:

```go
// main.go
package main

import (
    "fmt"
    "log"
    "net/http"
)

func handler(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintf(w, "Hello from Go in Docker!")
}

func main() {
    http.HandleFunc("/", handler)
    log.Println("Server starting on :8080")
    log.Fatal(http.ListenAndServe(":8080", nil))
}
```

```dockerfile
# Dockerfile
FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.* ./
RUN go mod download

COPY . .

# 정적 바이너리 빌드
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main .

# 최종 이미지 (scratch 사용)
FROM scratch

COPY --from=builder /app/main /main

EXPOSE 8080

ENTRYPOINT ["/main"]
```

**결과**: 이미지 크기가 800MB+ (golang 이미지)에서 6MB 미만으로 감소합니다!

---

## 4. 레이어 캐싱과 빌드 최적화

### 4.1 Docker 레이어의 이해

Docker는 각 명령어를 별도의 레이어로 저장합니다. 레이어는 읽기 전용이며 재사용 가능합니다. Dockerfile이 변경되면 변경된 레이어부터 다시 빌드됩니다:

```
┌─────────────────────────────────┐
│  CMD ["python", "app.py"]       │  ← Layer 5
├─────────────────────────────────┤
│  COPY app.py .                  │  ← Layer 4 (소스코드 변경 시 여기부터 재빌드)
├─────────────────────────────────┤
│  RUN pip install -r req.txt     │  ← Layer 3 (의존성 캐시됨)
├─────────────────────────────────┤
│  COPY requirements.txt .        │  ← Layer 2
├─────────────────────────────────┤
│  FROM python:3.11-slim          │  ← Layer 1 (베이스 이미지)
└─────────────────────────────────┘
```

### 4.2 캐시 최적화 전략

**나쁜 예시** (캐시 활용 안 됨):
```dockerfile
FROM node:18-alpine
WORKDIR /app

# 모든 파일을 먼저 복사
COPY . .

# 의존성 설치
RUN npm install

CMD ["npm", "start"]
```

**문제점**: 소스코드가 변경될 때마다 `npm install`이 다시 실행됩니다.

**좋은 예시** (캐시 활용):
```dockerfile
FROM node:18-alpine
WORKDIR /app

# 의존성 파일만 먼저 복사
COPY package*.json ./

# 의존성 설치 (package.json이 변경되지 않으면 캐시됨)
RUN npm ci --only=production

# 그 다음 소스코드 복사
COPY . .

CMD ["npm", "start"]
```

### 4.3 .dockerignore로 불필요한 파일 제외

`.gitignore`처럼 `.dockerignore`로 빌드 컨텍스트에서 파일을 제외할 수 있습니다:

```text
# .dockerignore
node_modules
npm-debug.log
.git
.gitignore
.env
.vscode
.idea
*.md
.DS_Store
dist
coverage
.pytest_cache
__pycache__
*.pyc
```

**효과**: 빌드 컨텍스트 크기가 줄어 빌드 속도가 향상되고, 민감한 파일이 이미지에 포함되는 것을 방지합니다.

### 4.4 RUN 명령 결합으로 레이어 최소화

**비효율적**:
```dockerfile
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y vim
RUN apt-get install -y git
RUN apt-get clean
```

**효율적**:
```dockerfile
RUN apt-get update && \
    apt-get install -y \
        curl \
        vim \
        git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

**이점**: 
- 레이어 수 감소 (5개 → 1개)
- 이미지 크기 감소 (중간 레이어의 캐시 파일 제거)
- 빌드 속도 향상

### 4.5 BuildKit 활용

Docker BuildKit은 향상된 빌드 성능과 추가 기능을 제공합니다:

```bash
# BuildKit 활성화
export DOCKER_BUILDKIT=1

# 또는 빌드 시 직접 지정
DOCKER_BUILDKIT=1 docker build -t myapp .
```

**BuildKit 기능**:

```dockerfile
# 빌드 시크릿 (민감정보 노출 방지)
RUN --mount=type=secret,id=mysecret \
    cat /run/secrets/mysecret > /app/config

# 캐시 마운트 (pip, npm 캐시 재사용)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# SSH 마운트 (private 리포지토리 접근)
RUN --mount=type=ssh \
    git clone git@github.com:private/repo.git
```

사용 예시:
```bash
# 시크릿 전달
docker build --secret id=mysecret,src=./secret.txt -t myapp .

# SSH 키 전달
docker build --ssh default -t myapp .
```

---

## 5. 멀티스테이지 빌드로 이미지 크기 줄이기

### 5.1 멀티스테이지 빌드란?

멀티스테이지 빌드는 하나의 Dockerfile에서 여러 FROM 문을 사용하여 빌드와 실행 환경을 분리하는 기법입니다. 빌드에 필요한 도구들(컴파일러, 빌드 도구)은 최종 이미지에 포함되지 않아 이미지 크기를 획기적으로 줄일 수 있습니다. 2017년 Docker 17.05에서 도입된 이 기능은 현재 프로덕션 환경에서 표준으로 사용됩니다.

### 5.2 단일 스테이지 vs 멀티스테이지 비교

**단일 스테이지 (비효율적)**:
```dockerfile
FROM node:18
WORKDIR /app
COPY package*.json ./
RUN npm install  # devDependencies 포함
COPY . .
RUN npm run build  # 빌드 도구 필요
CMD ["node", "dist/server.js"]
```
결과 이미지 크기: ~1.2GB

**멀티스테이지 (효율적)**:
```dockerfile
# 1단계: 빌드 스테이지
FROM node:18 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# 2단계: 프로덕션 스테이지
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY --from=builder /app/dist ./dist
CMD ["node", "dist/server.js"]
```
결과 이미지 크기: ~180MB (85% 감소!)

### 5.3 실전 예제: React 애플리케이션

React 같은 프론트엔드 앱은 빌드 후 정적 파일만 필요하므로 멀티스테이지 빌드가 매우 효과적입니다:

```dockerfile
# 빌드 스테이지
FROM node:18-alpine AS builder

WORKDIR /app

# 의존성 설치
COPY package*.json ./
RUN npm ci

# 소스 복사 및 빌드
COPY . .
RUN npm run build

# 프로덕션 스테이지
FROM nginx:alpine

# Nginx 설정 복사 (선택사항)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 빌드된 파일만 복사
COPY --from=builder /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**이미지 크기 비교**:
- 단일 스테이지 (node 기반): ~1.1GB
- 멀티스테이지 (nginx:alpine 기반): ~25MB

### 5.4 Python 애플리케이션 멀티스테이지

Python의 경우 C 확장 모듈 컴파일 후 불필요한 빌드 도구를 제거할 수 있습니다:

```dockerfile
# 빌드 스테이지
FROM python:3.11 AS builder

WORKDIR /app

# 빌드 도구 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        make && \
    rm -rf /var/lib/apt/lists/*

# 의존성 설치
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 프로덕션 스테이지
FROM python:3.11-slim

WORKDIR /app

# 빌드 스테이지에서 설치된 패키지만 복사
COPY --from=builder /root/.local /root/.local

# PATH에 추가
ENV PATH=/root/.local/bin:$PATH

# 애플리케이션 코드 복사
COPY . .

# 비-root 사용자 생성
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

CMD ["python", "app.py"]
```

### 5.5 Go 애플리케이션 - Scratch 이미지 활용

Go는 정적 바이너리를 생성하므로 가장 작은 이미지를 만들 수 있습니다:

```dockerfile
# 빌드 스테이지
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 의존성 다운로드
COPY go.* ./
RUN go mod download

# 소스 복사 및 빌드
COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags='-w -s -extldflags "-static"' \
    -a \
    -o main .

# 최종 스테이지 (scratch: 빈 이미지)
FROM scratch

# CA 인증서 복사 (HTTPS 요청 시 필요)
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# 바이너리만 복사
COPY --from=builder /app/main /main

EXPOSE 8080

ENTRYPOINT ["/main"]
```

**결과**: 이미지 크기 ~6MB!

### 5.6 여러 스테이지를 활용한 복잡한 빌드

하나의 Dockerfile에서 여러 스테이지를 정의하고 선택적으로 사용할 수 있습니다:

```dockerfile
# 베이스 의존성 스테이지
FROM node:18-alpine AS base
WORKDIR /app
COPY package*.json ./
RUN npm ci

# 개발 스테이지
FROM base AS development
RUN npm install
COPY . .
CMD ["npm", "run", "dev"]

# 테스트 스테이지
FROM base AS test
RUN npm install
COPY . .
RUN npm run test

# 빌드 스테이지
FROM base AS builder
RUN npm install
COPY . .
RUN npm run build

# 프로덕션 스테이지
FROM node:18-alpine AS production
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY --from=builder /app/dist ./dist
USER node
CMD ["node", "dist/server.js"]
```

특정 스테이지만 빌드:
```bash
# 개발 이미지
docker build --target development -t myapp:dev .

# 테스트 실행
docker build --target test -t myapp:test .

# 프로덕션 이미지 (기본)
docker build -t myapp:prod .
```

### 5.7 외부 이미지에서 파일 복사

다른 이미지에서 파일을 가져올 수도 있습니다:

```dockerfile
# 공식 이미지에서 바이너리 가져오기
FROM golang:1.21 AS builder
WORKDIR /app
COPY . .
RUN go build -o myapp .

FROM alpine:latest

# 다른 이미지에서 파일 복사
COPY --from=builder /app/myapp /usr/local/bin/

# 공식 이미지에서 직접 복사
COPY --from=busybox:latest /bin/wget /usr/local/bin/wget

CMD ["myapp"]
```

---

## 6. 보안 강화 베스트 프랙티스

### 6.1 최소 권한 원칙: Non-root 사용자

컨테이너를 root 사용자로 실행하면 컨테이너가 탈취당했을 때 호스트 시스템까지 위험에 노출됩니다. 반드시 전용 사용자를 생성하세요:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 의존성 설치는 root로
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 전용 사용자 생성
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 appuser && \
    chown -R appuser:appuser /app

# 사용자 전환 (이후 모든 명령은 appuser로 실행)
USER appuser

# 애플리케이션 실행
CMD ["python", "app.py"]
```

**Alpine 이미지의 경우**:
```dockerfile
FROM python:3.11-alpine

# Alpine은 adduser 명령 사용
RUN addgroup -S appgroup && \
    adduser -S -G appgroup -u 1000 appuser

# 또는 내장 nobody 사용
USER nobody
```

### 6.2 민감한 정보 관리

**절대 하지 말아야 할 것**:
```dockerfile
# ❌ 나쁜 예시
ENV DATABASE_PASSWORD=supersecret123
ENV API_KEY=abc123xyz
```

**올바른 방법**:

```dockerfile
# 1. 런타임에 환경변수 주입
# Dockerfile에는 기본값만
ENV DATABASE_HOST=localhost
# docker run -e DATABASE_PASSWORD=secret myapp

# 2. Docker Secrets 사용 (Swarm/Kubernetes)
RUN --mount=type=secret,id=db_password \
    export DB_PASS=$(cat /run/secrets/db_password) && \
    # 설정 작업

# 3. BuildKit secrets
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm install
```

**.dockerignore로 민감 파일 제외**:
```text
.env
.env.local
.git
secrets/
*.key
*.pem
credentials.json
```

### 6.3 베이스 이미지 선택 전략

**1. 공식 이미지 사용**:
```dockerfile
# ✅ 좋음: 공식 이미지
FROM python:3.11-slim

# ❌ 나쁨: 출처 불명 이미지
FROM someuser/python
```

**2. 특정 버전 고정**:
```dockerfile
# ✅ 좋음: 정확한 버전
FROM node:18.17.0-alpine3.18

# ❌ 나쁨: latest 태그
FROM node:latest
```

**3. Digest를 사용한 불변 이미지**:
```dockerfile
# 가장 안전: SHA256 digest 사용
FROM node@sha256:a6c22f2ba8d88e...

# Digest 확인
docker pull node:18-alpine
docker inspect node:18-alpine | grep Digest
```

**4. 이미지 크기별 선택**:
```dockerfile
# Full (largest): 개발 편의성
FROM python:3.11
# Size: ~900MB

# Slim (recommended): 균형잡힌 선택
FROM python:3.11-slim
# Size: ~120MB

# Alpine (smallest): 최소 크기
FROM python:3.11-alpine
# Size: ~50MB
# 주의: musl libc 호환성 문제 가능
```

### 6.4 취약점 스캔

**Trivy로 이미지 스캔**:
```bash
# Trivy 설치
brew install trivy  # macOS
# or
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -

# 이미지 스캔
trivy image myapp:latest

# 심각도 필터링
trivy image --severity HIGH,CRITICAL myapp:latest

# CI/CD에서 실패 조건 설정
trivy image --exit-code 1 --severity CRITICAL myapp:latest
```

**Docker Scout 사용**:
```bash
# Docker Desktop에 내장
docker scout cves myapp:latest

# 추천사항 확인
docker scout recommendations myapp:latest
```

### 6.5 최소 권한 파일시스템

읽기 전용 파일시스템과 임시 디렉토리 볼륨 사용:

```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

# 임시 파일 디렉토리
RUN mkdir -p /app/tmp && \
    chown -R node:node /app

USER node

# 읽기 전용 루트, 쓰기 가능한 tmp
CMD ["node", "server.js"]
```

실행 시:
```bash
docker run --read-only --tmpfs /app/tmp:rw myapp
```

### 6.6 불필요한 패키지 제거

```dockerfile
FROM ubuntu:22.04

# 한 레이어에서 설치 및 정리
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates && \
    # 캐시 정리
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Alpine의 경우
FROM alpine:3.18
RUN apk add --no-cache \
        python3 \
        py3-pip && \
    rm -rf /var/cache/apk/*
```

### 6.7 COPY vs ADD - 보안 관점

```dockerfile
# ✅ COPY: 명확하고 안전
COPY app.py /app/

# ⚠️ ADD: URL 다운로드 시 보안 위험
ADD https://example.com/file.tar.gz /tmp/
# 대신 명시적으로:
RUN curl -o /tmp/file.tar.gz https://example.com/file.tar.gz && \
    sha256sum /tmp/file.tar.gz | grep "expected_hash" && \
    tar xzf /tmp/file.tar.gz && \
    rm /tmp/file.tar.gz
```

### 6.8 HEALTHCHECK로 컨테이너 상태 모니터링

```dockerfile
FROM node:18-alpine

WORKDIR /app
COPY . .
RUN npm ci --only=production

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD node healthcheck.js || exit 1

USER node
CMD ["node", "server.js"]
```

```javascript
// healthcheck.js
const http = require('http');

const options = {
    host: 'localhost',
    port: 3000,
    path: '/health',
    timeout: 2000
};

const request = http.request(options, (res) => {
    console.log(`STATUS: ${res.statusCode}`);
    process.exit(res.statusCode === 200 ? 0 : 1);
});

request.on('error', (err) => {
    console.error('ERROR:', err);
    process.exit(1);
});

request.end();
```

### 6.9 메타데이터와 LABEL

이미지에 메타데이터를 추가하여 추적 가능성 향상:

```dockerfile
FROM python:3.11-slim

LABEL maintainer="team@example.com"
LABEL version="1.0.0"
LABEL description="Production API Server"
LABEL org.opencontainers.image.source="https://github.com/user/repo"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${GIT_COMMIT}"

# 빌드 시:
# docker build \
#   --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
#   --build-arg GIT_COMMIT=$(git rev-parse HEAD) \
#   -t myapp .

WORKDIR /app
COPY . .
CMD ["python", "app.py"]
```

---

## 7. 실전 예제: 다양한 언어별 Dockerfile

### 7.1 Django 프로젝트 (Python)

프로덕션급 Django 애플리케이션을 위한 최적화된 Dockerfile:

```dockerfile
# 멀티스테이지 빌드
FROM python:3.11-slim AS builder

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        postgresql-client \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 프로덕션 스테이지
FROM python:3.11-slim

WORKDIR /app

# 런타임 의존성만 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

# 빌드 스테이지에서 Python 패키지 복사
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 애플리케이션 코드 복사
COPY . .

# 정적 파일 수집
RUN python manage.py collectstatic --noinput

# 비-root 사용자 생성
RUN useradd -m -u 1000 django && \
    chown -R django:django /app

USER django

# Gunicorn으로 실행
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "myproject.wsgi:application"]
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
    depends_on:
      - db
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=mydb
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

### 7.2 Next.js 애플리케이션 (React)

```dockerfile
# 의존성 스테이지
FROM node:18-alpine AS deps
WORKDIR /app

# 의존성 파일만 복사
COPY package.json package-lock.json ./
RUN npm ci

# 빌드 스테이지
FROM node:18-alpine AS builder
WORKDIR /app

# 의존성 복사
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 환경변수 설정
ENV NEXT_TELEMETRY_DISABLED 1
ENV NODE_ENV production

# 빌드 실행
RUN npm run build

# 프로덕션 스테이지
FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# 비-root 사용자
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# 필요한 파일만 복사
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
```

**next.config.js**:
```javascript
module.exports = {
  output: 'standalone',  // Dockerfile 최적화를 위해 필수
  experimental: {
    outputFileTracingRoot: path.join(__dirname, '../../'),
  },
}
```

### 7.3 Spring Boot 애플리케이션 (Java)

```dockerfile
# 빌드 스테이지
FROM gradle:8.5-jdk17 AS builder

WORKDIR /app

# Gradle 캐시 최적화
COPY build.gradle settings.gradle ./
COPY gradle ./gradle
RUN gradle dependencies --no-daemon

# 소스 코드 복사 및 빌드
COPY src ./src
RUN gradle bootJar --no-daemon

# 프로덕션 스테이지
FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

# 보안: 비-root 사용자
RUN addgroup -S spring && adduser -S spring -G spring
USER spring:spring

# JAR 파일 복사
COPY --from=builder /app/build/libs/*.jar app.jar

# 헬스체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/actuator/health || exit 1

EXPOSE 8080

# JVM 최적화 옵션
ENTRYPOINT ["java", \
    "-XX:+UseContainerSupport", \
    "-XX:MaxRAMPercentage=75.0", \
    "-Djava.security.egd=file:/dev/./urandom", \
    "-jar", "app.jar"]
```

### 7.4 .NET 애플리케이션 (C#)

```dockerfile
# SDK 이미지로 빌드
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

# 프로젝트 파일 복사 및 복원
COPY ["MyApp/MyApp.csproj", "MyApp/"]
RUN dotnet restore "MyApp/MyApp.csproj"

# 전체 소스 복사 및 빌드
COPY . .
WORKDIR "/src/MyApp"
RUN dotnet build "MyApp.csproj" -c Release -o /app/build

# 게시
FROM build AS publish
RUN dotnet publish "MyApp.csproj" -c Release -o /app/publish /p:UseAppHost=false

# 런타임 이미지 (작은 이미지)
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app

# 비-root 사용자
USER $APP_UID

COPY --from=publish /app/publish .

EXPOSE 8080

ENTRYPOINT ["dotnet", "MyApp.dll"]
```

### 7.5 Rust 애플리케이션

```dockerfile
# 빌드 스테이지
FROM rust:1.75-slim AS builder

WORKDIR /app

# 의존성만 먼저 빌드 (캐싱 활용)
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && \
    echo "fn main() {}" > src/main.rs && \
    cargo build --release && \
    rm -rf src

# 실제 소스 빌드
COPY . .
RUN touch src/main.rs && \
    cargo build --release

# 최종 스테이지
FROM debian:bookworm-slim

# 런타임 의존성
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 바이너리만 복사
COPY --from=builder /app/target/release/myapp /usr/local/bin/myapp

# 비-root 사용자
RUN useradd -m -u 1000 appuser
USER appuser

EXPOSE 8080

CMD ["myapp"]
```

### 7.6 Ruby on Rails

```dockerfile
# 베이스 이미지
FROM ruby:3.2-slim AS base

# 공통 의존성
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        nodejs \
        npm && \
    npm install -g yarn && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 스테이지
FROM base AS dependencies

COPY Gemfile Gemfile.lock ./
RUN bundle config set --local deployment 'true' && \
    bundle config set --local without 'development test' && \
    bundle install -j$(nproc)

COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile --production

# 애플리케이션 스테이지
FROM base

# 의존성 복사
COPY --from=dependencies /usr/local/bundle /usr/local/bundle
COPY --from=dependencies /app/node_modules ./node_modules

# 애플리케이션 코드
COPY . .

# 애셋 컴파일
RUN RAILS_ENV=production bundle exec rails assets:precompile

# 비-root 사용자
RUN useradd -m -u 1000 rails && \
    chown -R rails:rails /app

USER rails

EXPOSE 3000

CMD ["bundle", "exec", "puma", "-C", "config/puma.rb"]
```

---

## 8. 고급 기법과 성능 최적화

### 8.1 BuildKit 고급 기능

BuildKit은 Docker의 차세대 빌드 엔진으로 성능과 보안을 크게 향상시킵니다:

**캐시 마운트로 빌드 속도 향상**:
```dockerfile
# syntax=docker/dockerfile:1.4

FROM python:3.11-slim

WORKDIR /app

# pip 캐시를 마운트하여 재사용
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    pip install -r requirements.txt

COPY . .
CMD ["python", "app.py"]
```

**Node.js npm 캐시**:
```dockerfile
# syntax=docker/dockerfile:1.4

FROM node:18-alpine

WORKDIR /app

# npm 캐시 재사용
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=bind,source=package.json,target=package.json \
    --mount=type=bind,source=package-lock.json,target=package-lock.json \
    npm ci --prefer-offline --no-audit

COPY . .
CMD ["node", "server.js"]
```

**Secret 마운트로 보안 강화**:
```dockerfile
# syntax=docker/dockerfile:1.4

FROM node:18-alpine

WORKDIR /app

# Private npm 패키지 설치
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm install

COPY . .
CMD ["node", "server.js"]
```

빌드 시:
```bash
docker build --secret id=npmrc,src=$HOME/.npmrc -t myapp .
```

**SSH 마운트로 Private Git 리포지토리 접근**:
```dockerfile
# syntax=docker/dockerfile:1.4

FROM golang:1.21-alpine

WORKDIR /app

# SSH 키를 이미지에 남기지 않고 사용
RUN --mount=type=ssh \
    git clone git@github.com:private/repo.git

COPY . .
RUN go build -o app .

CMD ["./app"]
```

빌드 시:
```bash
docker build --ssh default -t myapp .
```

### 8.2 병렬 빌드로 속도 향상

여러 독립적인 단계를 병렬로 실행:

```dockerfile
# syntax=docker/dockerfile:1.4

FROM node:18-alpine AS base
WORKDIR /app
COPY package*.json ./

# 병렬 단계 1: 프론트엔드 빌드
FROM base AS frontend
RUN npm ci
COPY frontend ./frontend
RUN npm run build:frontend

# 병렬 단계 2: 백엔드 빌드
FROM base AS backend
RUN npm ci
COPY backend ./backend
RUN npm run build:backend

# 병렬 단계 3: 테스트 실행
FROM base AS tests
RUN npm ci --include=dev
COPY . .
RUN npm test

# 최종 스테이지: 모든 결과 결합
FROM node:18-alpine
WORKDIR /app
COPY --from=frontend /app/dist/frontend ./public
COPY --from=backend /app/dist/backend ./dist
COPY package*.json ./
RUN npm ci --only=production
CMD ["node", "dist/server.js"]
```

### 8.3 이미지 압축 및 최적화

**1. Alpine 기반 이미지 사용**:
```dockerfile
# 일반 이미지: ~900MB
FROM node:18
# Alpine 이미지: ~180MB
FROM node:18-alpine
```

**2. Distroless 이미지**:
```dockerfile
# 빌드 스테이지
FROM node:18 AS builder
WORKDIR /app
COPY . .
RUN npm install && npm run build

# Distroless (셸도 없음, 최고 보안)
FROM gcr.io/distroless/nodejs18-debian11
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
CMD ["dist/server.js"]
```

**3. Dive로 레이어 분석**:
```bash
# Dive 설치
brew install dive  # macOS
# or
wget https://github.com/wagoodman/dive/releases/download/v0.11.0/dive_0.11.0_linux_amd64.deb
sudo dpkg -i dive_0.11.0_linux_amd64.deb

# 이미지 분석
dive myapp:latest
```

### 8.4 ARG와 ENV를 활용한 동적 빌드

```dockerfile
# 빌드 타임 변수
ARG NODE_VERSION=18
ARG BUILD_DATE
ARG GIT_COMMIT
ARG VERSION=1.0.0

FROM node:${NODE_VERSION}-alpine

# 메타데이터
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.revision="${GIT_COMMIT}"

WORKDIR /app

# ARG를 ENV로 전달 (런타임에도 사용 가능)
ENV APP_VERSION=${VERSION}

COPY package*.json ./
RUN npm ci --only=production

COPY . .

CMD ["node", "server.js"]
```

빌드 스크립트:
```bash
#!/bin/bash

BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
GIT_COMMIT=$(git rev-parse --short HEAD)
VERSION=$(git describe --tags --always)

docker build \
  --build-arg NODE_VERSION=18 \
  --build-arg BUILD_DATE=$BUILD_DATE \
  --build-arg GIT_COMMIT=$GIT_COMMIT \
  --build-arg VERSION=$VERSION \
  -t myapp:$VERSION \
  -t myapp:latest \
  .
```

### 8.5 조건부 빌드

```dockerfile
# syntax=docker/dockerfile:1.4

FROM node:18-alpine

ARG ENVIRONMENT=production

WORKDIR /app

COPY package*.json ./

# 환경별 의존성 설치
RUN if [ "$ENVIRONMENT" = "development" ]; then \
        npm install; \
    else \
        npm ci --only=production; \
    fi

COPY . .

# 환경별 빌드
RUN if [ "$ENVIRONMENT" = "production" ]; then \
        npm run build; \
    fi

CMD ["node", "server.js"]
```

빌드:
```bash
# 프로덕션
docker build --build-arg ENVIRONMENT=production -t myapp:prod .

# 개발
docker build --build-arg ENVIRONMENT=development -t myapp:dev .
```

### 8.6 ONBUILD로 베이스 이미지 템플릿화

```dockerfile
# 베이스 이미지: base-nodejs
FROM node:18-alpine

WORKDIR /app

# 자식 이미지에서 실행될 명령어
ONBUILD COPY package*.json ./
ONBUILD RUN npm ci --only=production
ONBUILD COPY . .

CMD ["node", "server.js"]
```

자식 이미지:
```dockerfile
# 베이스 이미지만 지정
FROM mycompany/base-nodejs:latest

# ONBUILD 명령어들이 자동 실행됨
# 추가 설정만 작성
EXPOSE 3000
ENV NODE_ENV=production
```

### 8.7 Docker Compose로 개발 환경 구성

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: development  # 특정 스테이지 지정
      args:
        NODE_VERSION: 18
    ports:
      - "3000:3000"
    volumes:
      - .:/app  # 핫 리로드
      - /app/node_modules  # node_modules 보존
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
    depends_on:
      - db
      - redis
    command: npm run dev

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

멀티스테이지 개발/프로덕션:
```dockerfile
# 개발 스테이지
FROM node:18-alpine AS development
WORKDIR /app
COPY package*.json ./
RUN npm install  # devDependencies 포함
COPY . .
CMD ["npm", "run", "dev"]

# 프로덕션 스테이지
FROM node:18-alpine AS production
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
CMD ["node", "dist/server.js"]
```

---

## 9. 디버깅과 트러블슈팅

### 9.1 빌드 실패 디버깅

**빌드 과정 상세 로그**:
```bash
# 상세 빌드 로그
docker build --progress=plain --no-cache -t myapp .

# 특정 스테이지까지만 빌드
docker build --target builder -t myapp:debug .

# 실패한 레이어에서 셸 실행
docker run -it <실패한_레이어_ID> sh
```

**중간 레이어 검사**:
```bash
# 빌드 히스토리 확인
docker history myapp:latest

# 특정 레이어로 컨테이너 시작
docker run -it --rm <layer_id> sh
```

### 9.2 실행 중인 컨테이너 디버깅

```bash
# 컨테이너 로그 확인
docker logs <container_id>
docker logs -f --tail 100 <container_id>

# 실행 중인 컨테이너에 접속
docker exec -it <container_id> sh
docker exec -it <container_id> bash

# 컨테이너 상세 정보
docker inspect <container_id>

# 리소스 사용량 모니터링
docker stats <container_id>

# 프로세스 목록
docker top <container_id>
```

### 9.3 일반적인 문제와 해결책

**문제 1: "COPY failed" 오류**
```dockerfile
# ❌ 잘못됨
COPY src/ /app/

# ✅ 올바름: .dockerignore 확인
# .dockerignore에 src가 포함되어 있는지 확인
```

**문제 2: 캐시가 작동하지 않음**
```bash
# 캐시 무시하고 빌드
docker build --no-cache -t myapp .

# 특정 시점부터 캐시 무효화
docker build --build-arg CACHEBUST=$(date +%s) -t myapp .
```

**문제 3: 이미지 크기가 너무 큼**
```bash
# 레이어별 크기 확인
docker history --no-trunc myapp:latest

# Dive로 상세 분석
dive myapp:latest
```

**문제 4: 권한 문제**
```dockerfile
# 해결: 파일 소유권 설정
COPY --chown=appuser:appuser . /app

# 또는
RUN chown -R appuser:appuser /app
```

**문제 5: DNS 해결 실패**
```dockerfile
# 빌드 시 DNS 서버 지정
docker build --network=host -t myapp .

# 또는 daemon.json 설정
{
  "dns": ["8.8.8.8", "8.8.4.4"]
}
```

### 9.4 성능 프로파일링

```bash
# 빌드 시간 측정
time docker build -t myapp .

# BuildKit 빌드 추적
BUILDKIT_PROGRESS=plain docker build -t myapp . 2>&1 | tee build.log

# 각 레이어의 빌드 시간 분석
grep "duration" build.log
```

---

## 10. 결론 및 체크리스트

### 10.1 Dockerfile 베스트 프랙티스 체크리스트

**기본 원칙**:
- ✅ 특정 버전 태그 사용 (`node:18.17.0-alpine`, `latest` 금지)
- ✅ 공식 이미지 우선 사용
- ✅ Alpine 또는 Slim 이미지로 크기 최소화
- ✅ `.dockerignore` 파일 작성

**보안**:
- ✅ Non-root 사용자로 실행
- ✅ 민감한 정보를 ENV/ARG에 하드코딩하지 않음
- ✅ 정기적인 취약점 스캔 (Trivy, Docker Scout)
- ✅ 최소 권한 원칙 적용
- ✅ HEALTHCHECK 추가

**성능 최적화**:
- ✅ 멀티스테이지 빌드 사용
- ✅ 레이어 캐싱 최적화 (의존성 파일을 소스코드보다 먼저 COPY)
- ✅ RUN 명령 결합하여 레이어 수 최소화
- ✅ 빌드 캐시 정리 (`--no-cache-dir`, `apt-get clean`)
- ✅ BuildKit 활용

**구조와 가독성**:
- ✅ WORKDIR로 작업 디렉토리 명시
- ✅ LABEL로 메타데이터 추가
- ✅ 명확한 주석 작성
- ✅ 논리적인 명령어 순서
- ✅ Exec 형식 사용 (`["python", "app.py"]`)

**검증**:
```bash
# 1. 이미지 크기 확인
docker images myapp:latest

# 2. 취약점 스캔
trivy image myapp:latest

# 3. 레이어 분석
dive myapp:latest

# 4. 빌드 테스트
docker build -t myapp:test .

# 5. 실행 테스트
docker run --rm myapp:test
```

### 10.2 실전 템플릿

**Python (FastAPI/Django)**:
```dockerfile
# syntax=docker/dockerfile:1.4

FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY . .

RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Node.js (Express/NestJS)**:
```dockerfile
# syntax=docker/dockerfile:1.4

FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY --from=builder /app/dist ./dist

RUN addgroup -S appgroup && \
    adduser -S -G appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s \
    CMD node healthcheck.js || exit 1

CMD ["node", "dist/main.js"]
```

**Go**:
```dockerfile
# syntax=docker/dockerfile:1.4

FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.* ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o main .

FROM scratch

COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /app/main /main

EXPOSE 8080

ENTRYPOINT ["/main"]
```

### 10.3 CI/CD 통합 예제

**GitHub Actions**:
```yaml
name: Docker Build and Push

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true  # event_name 체크
          tags: ${{" steps.meta.outputs.tags "}}
          labels: ${{" steps.meta.outputs.labels "}}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            BUILD_DATE=2024-01-01
            GIT_COMMIT=${{" github.sha "}}
            VERSION=1.0.0

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.meta.outputs.version }}
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

**GitLab CI/CD**:
```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - deploy

variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: "/certs"
  IMAGE_TAG: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA

build:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - docker build 
        --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
        --build-arg GIT_COMMIT=$CI_COMMIT_SHORT_SHA
        --build-arg VERSION=$CI_COMMIT_TAG
        -t $IMAGE_TAG
        -t $CI_REGISTRY_IMAGE:latest
        .
    - docker push $IMAGE_TAG
    - docker push $CI_REGISTRY_IMAGE:latest
  only:
    - main
    - tags

security_scan:
  stage: test
  image: aquasec/trivy:latest
  script:
    - trivy image --severity HIGH,CRITICAL $IMAGE_TAG
  dependencies:
    - build
  only:
    - main
    - tags
```

### 10.4 핵심 요약

Dockerfile 작성은 단순히 이미지를 만드는 것을 넘어, **보안**, **성능**, **유지보수성**의 균형을 맞추는 작업입니다. 이 가이드에서 다룬 핵심 내용을 정리하면:

1. **기초**: FROM, COPY, RUN, CMD 등 기본 명령어의 정확한 이해
2. **최적화**: 레이어 캐싱과 멀티스테이지 빌드로 빌드 시간과 이미지 크기 최소화
3. **보안**: Non-root 사용자, 취약점 스캔, 민감정보 관리
4. **실전**: 언어별 특성을 고려한 최적화된 Dockerfile 작성
5. **고급**: BuildKit, 조건부 빌드, 동적 설정 활용

**다음 단계**:
- **학습**: Docker Compose, Kubernetes로 확장
- **실습**: 본인의 프로젝트에 멀티스테이지 빌드 적용
- **모니터링**: Prometheus, Grafana로 컨테이너 메트릭 수집
- **자동화**: CI/CD 파이프라인에 Docker 빌드 통합

### 10.5 유용한 리소스

**공식 문서**:
- [Dockerfile Reference](https://docs.docker.com/engine/reference/builder/)
- [Best practices for writing Dockerfiles](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [BuildKit Documentation](https://docs.docker.com/build/buildkit/)

**도구**:
- [Trivy](https://github.com/aquasecurity/trivy) - 취약점 스캐너
- [Dive](https://github.com/wagoodman/dive) - 이미지 레이어 분석
- [Hadolint](https://github.com/hadolint/hadolint) - Dockerfile 린터
- [Docker Scout](https://docs.docker.com/scout/) - 이미지 분석

**커뮤니티**:
- [Docker Official Images](https://github.com/docker-library/official-images)
- [Awesome Docker](https://github.com/veggiemonk/awesome-docker)

**마지막 팁**: Dockerfile은 한 번 작성하고 끝이 아닙니다. 정기적으로 베이스 이미지를 업데이트하고, 취약점을 스캔하며, 새로운 최적화 기법을 적용하세요. 작은 개선들이 모여 안정적이고 효율적인 컨테이너 환경을 만듭니다.

---

**관련 포스트**:
- Docker Compose 마스터 가이드
- Kubernetes 입문: Pod부터 Deployment까지
- CI/CD 파이프라인 구축 완벽 가이드
- 컨테이너 보안 베스트 프랙티스

이 가이드가 여러분의 Docker 여정에 도움이 되기를 바랍니다. 질문이나 피드백은 언제든 환영합니다! 🚀

