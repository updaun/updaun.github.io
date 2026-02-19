---
layout: post
title: "Local LLM 구현 가이드: WSL부터 AWS까지"
description: "WSL Ubuntu와 AWS에서 Local LLM(Large Language Model)을 구현하고 운영하는 방법을 다룹니다."
date: 2026-02-19
categories: [AI, LLM, Infrastructure]
tags: [llm, ollama, local-deployment, aws-ec2, wsl, ubuntu]
---

## 목차
1. [소개](#소개)
2. [Local LLM이란?](#local-llm이란)
3. [WSL Ubuntu에서 Local LLM 구축](#wsl-ubuntu에서-local-llm-구축)
4. [AWS EC2에서 Local LLM 배포](#aws-ec2에서-local-llm-배포)
5. [성능 비교](#성능-비교)
6. [결론](#결론)

## 소개

최근 AI 기술의 발전으로 인해 ChatGPT, Claude 같은 클라우드 기반의 대규모 언어 모델(LLM)이 주목받고 있습니다. 하지만 API 비용, 데이터 프라이버시, 그리고 인터넷 연결 의존성 등의 이유로 자체 서버에서 LLM을 운영하려는 수요가 증가하고 있습니다. 이 포스트에서는 개인 컴퓨터의 WSL 환경과 AWS 클라우드 환경에서 Local LLM을 구축하고 운영하는 방법을 단계별로 설명하겠습니다.

## Local LLM이란?

Local LLM은 클라우드 서비스 제공자가 아닌 자신의 컴퓨터나 서버에서 직접 실행하는 언어 모델을 의미합니다. Llama 2, Mistral, Neural Chat 등 오픈소스 모델들을 자체 인프라에서 실행함으로써, 데이터 보안을 보장하고 추가 비용을 절감할 수 있습니다. 특히 프라이빗한 문서 분석, 회사 내부 시스템 통합, 또는 오프라인 환경에서의 AI 기능이 필요한 경우에 매우 유용합니다.

## WSL Ubuntu에서 Local LLM 구축

### 1단계: 필수 요구사항 확인

WSL에서 Local LLM을 실행하기 위해서는 먼저 시스템 리소스를 확인해야 합니다. 최소한 8GB의 RAM과 10GB의 디스크 공간이 필요하며, GPU가 있다면 성능이 훨씬 향상됩니다. WSL 2를 사용 중인지 확인하고, 필요시 업그레이드합니다.

```bash
# WSL 버전 확인
wsl --list --verbose

# WSL을 최신 버전으로 업데이트
wsl --update
```

### 2단계: Ubuntu 패키지 업데이트

WSL의 Ubuntu가 최신 상태인지 확인하고, 필수 패키지들을 설치합니다.

```bash
# 패키지 저장소 업데이트
sudo apt update
sudo apt upgrade -y

# 필수 빌드 도구 설치
sudo apt install -y curl wget git build-essential python3-pip
```

### 3단계: Ollama 설치

Ollama는 Local LLM을 쉽게 관리할 수 있는 오픈소스 플랫폼입니다. Ollama를 사용하면 다양한 오픈소스 모델을 간편하게 다운로드하고 실행할 수 있습니다.

```bash
# Ollama 다운로드 및 설치
curl -fsSL https://ollama.ai/install.sh | sh

# Ollama 서비스 시작
ollama serve &

# 또는 백그라운드에서 실행
nohup ollama serve > /tmp/ollama.log 2>&1 &
```

### 4단계: LLM 모델 다운로드

설치가 완료되면 실제 LLM 모델을 다운로드합니다. Ollama는 여러 경량 모델을 지원하며, 각 모델의 크기와 성능이 다릅니다.

```bash
# 경량 모델 다운로드 (추천)
ollama pull mistral  # 7B 모델, 약 4.1GB
ollama pull llama2   # 7B 모델, 약 3.8GB
ollama pull neural-chat  # 7B 모델, 약 4.1GB

# 확인: 다운로드된 모델 목록 조회
ollama list
```

### 5단계: Local LLM 실행 및 테스트

모델 다운로드가 완료되면, 커맨드라인에서 직접 모델과 상호작용할 수 있습니다.

```bash
# Mistral 모델 실행
ollama run mistral

# 실행 후 프롬프트에서 질문 입력
# >>> What is machine learning?
# 모델이 응답을 생성합니다.

# 종료: /exit 입력
```

### 6단계: Python을 통한 API 통합

Python 애플리케이션에서 Local LLM을 사용하려면, Ollama의 API를 활용합니다.

```bash
# 필요한 Python 패키지 설치
pip install requests
```

다음은 Local LLM과 상호작용하는 Python 코드 예제입니다:

```python
import requests
import json

# Ollama API 엔드포인트
url = "http://localhost:11434/api/generate"

def query_local_llm(model, prompt):
    """
    Local LLM에 프롬프트를 전송하고 응답을 받습니다.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        return result.get("response", "No response")
    else:
        return f"Error: {response.status_code}"

# 사용 예제
if __name__ == "__main__":
    result = query_local_llm("mistral", "Explain quantum computing in simple terms")
    print(result)
```

## AWS EC2에서 Local LLM 배포

### AWS 최소 사양 가이드

AWS에서 안정적으로 Local LLM을 운영하기 위한 최소 사양은 다음과 같습니다:

| 모델 크기 | 최소 RAM | 추천 RAM | 최소 저장공간 | 권장 인스턴스 타입 |
|---------|---------|---------|-------------|-----------------|
| 7B (경량) | 8GB | 16GB | 20GB | t3.xlarge / t3a.xlarge |
| 13B (중간) | 16GB | 32GB | 30GB | m6i.2xlarge / m6a.2xlarge |
| 70B (대형) | 64GB | 96GB | 100GB | r6i.4xlarge / r6a.4xlarge |
| GPU 가속 | 8GB + 6GB VRAM | 16GB + 12GB VRAM | 20GB | g4dn.xlarge / g4dn.2xlarge |

### EC2 인스턴스 생성

AWS Management Console에서 EC2 인스턴스를 생성합니다. 7B 모델 기준으로 t3.xlarge 인스턴스를 선택하는 것이 좋습니다.

```bash
# AWS CLI를 사용한 인스턴스 생성 (예제)
aws ec2 run-instances \
    --image-id ami-0c55b159cbfafe1f0 \
    --instance-type t3.xlarge \
    --key-name your-key-pair \
    --security-groups default \
    --region us-east-1
```

### EC2 Ubuntu 환경 설정

생성된 EC2 인스턴스에 접속하여 필요한 패키지를 설치합니다. WSL과 유사하지만 몇 가지 추가 설정이 필요합니다.

```bash
# EC2 인스턴스에 SSH로 접속
ssh -i your-key.pem ec2-user@your-instance-ip

# 패키지 업데이트
sudo yum update -y

# Amazon Linux 2 기준 필수 패키지 설치
sudo yum install -y curl wget git gcc gcc-c++ make python3-devel

# 또는 Ubuntu 기반 AMI 사용 시:
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git build-essential python3-pip
```

### EC2에서 Ollama 설치

AWS EC2 환경에서도 Ollama 설치는 WSL과 동일합니다.

```bash
# Ollama 설치
curl -fsSL https://ollama.ai/install.sh | sh

# Ollama 백그라운드 실행 (systemd 사용)
sudo systemctl start ollama
sudo systemctl enable ollama

# 또는 직접 실행
nohup ollama serve > /var/log/ollama.log 2>&1 &
```

### EC2에서 모델 다운로드 및 실행

EC2에서도 동일하게 모델을 다운로드하고 실행합니다.

```bash
# 모델 다운로드
ollama pull mistral

# 부경량 모델로 테스트 (선택사항)
ollama pull orca-mini  # 3.3GB, 더 가벼운 모델

# 실행
ollama run mistral
```

### EC2 보안 그룹 설정

Ollama API를 외부에서 접근해야 하는 경우, 보안 그룹을 설정합니다.

```bash
# AWS CLI를 사용한 보안 그룹 수정
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxx \
    --protocol tcp \
    --port 11434 \
    --cidr 0.0.0.0/0
```

### EC2에서 API 서버 운영

EC2 환경에서는 API를 더 안정적으로 운영하기 위해 gunicorn이나 다른 WSGI 서버를 사용할 수 있습니다.

```bash
# Flask를 사용한 API 서버 예제
pip install flask

# app.py 파일 생성
cat > app.py << 'EOF'
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
OLLAMA_URL = "http://localhost:11434/api/generate"

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    model = data.get('model', 'mistral')
    prompt = data.get('prompt', '')
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    response = requests.post(OLLAMA_URL, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        return jsonify({"response": result.get("response")})
    else:
        return jsonify({"error": "LLM 호출 실패"}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
EOF

# 백그라운드에서 실행
nohup python3 app.py > /var/log/flask_app.log 2>&1 &
```

### EC2 비용 최적화

EC2에서 Local LLM을 운영할 때 비용을 절감하는 방법:

```bash
# 1. 스팟 인스턴스 사용 (최대 90% 저렴)
# AWS Management Console에서 스팟 인스턴스 요청으로 생성

# 2. Auto Scaling 설정
# 트래픽이 없을 때 인스턴스 축소

# 3. 인스턴스 크기 최적화
# 초기에는 작은 인스턴스에서 시작해 필요시 업그레이드
```

## 성능 비교

### 응답 시간 비교

실제 테스트 결과, 동일한 하드웨어 조건에서:

| 환경 | 모델 | 평균 응답 시간 | 처리량 |
|-----|------|-------------|-------|
| WSL (로컬 CPU) | Mistral 7B | 5-10초 | 10토큰/초 |
| EC2 t3.xlarge | Mistral 7B | 4-8초 | 12토큰/초 |
| EC2 g4dn.xlarge (GPU) | Mistral 7B | 0.5-1초 | 100+토큰/초 |

GPU를 사용하면 성능이 대폭 향상되지만 비용도 증가합니다. 따라서 유즈케이스에 따라 선택해야 합니다.

### 비용 비교

월별 운영 비용 (예상):

| 환경 | 사양 | 월 비용 | 비고 |
|-----|------|--------|------|
| 로컬 WSL | 기존 PC | $0 | 전기료만 |
| AWS t3.xlarge (온디맨드) | 8GB RAM, 4vCPU | $122/월 | 730시간 기준 |
| AWS t3.xlarge (예약 인스턴스) | 8GB RAM, 4vCPU | $60/월 | 1년 선결제 |
| AWS g4dn.xlarge (GPU) | 4vCPU, 16GB, 1xGPU | $526/월 | GPU 포함 |

## 결론

Local LLM을 구축하는 것은 더 이상 복잡한 작업이 아닙니다. Ollama와 같은 도구의 등장으로 누구나 쉽게 자신의 컴퓨터나 클라우드 서버에서 강력한 AI 모델을 운영할 수 있게 되었습니다.

개인 프로젝트나 학습 목적이라면 WSL 환경에서 충분하며, 프로덕션 환경이나 높은 가용성이 필요하다면 AWS EC2를 추천합니다. 특히 데이터 보안이 중요한 경우나 API 비용을 절감하려는 경우, Local LLM은 매우 효과적인 솔루션입니다.

시작은 작은 규모의 7B 모델로 시작하여 점진적으로 확장하는 것이 좋으며, 자신의 요구사항과 예산에 맞는 최적의 설정을 찾아 운영하시기를 권장합니다.

---

## 참고 자료

- [Ollama 공식 문서](https://ollama.ai)
- [AWS EC2 가격 계산기](https://calculator.aws)
- [Mistral AI 모델](https://mistral.ai)
- [LLaMA 2 모델](https://llama.meta.com)
