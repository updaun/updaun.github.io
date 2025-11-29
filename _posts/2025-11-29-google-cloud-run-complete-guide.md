---
layout: post
title: "Google Cloud Run 완벽 가이드 - 기초부터 배포 자동화까지"
categories: [Cloud, DevOps]
tags: [google-cloud-run, gcp, serverless, docker, cicd, deployment, cloud-native, kubernetes]
date: 2025-11-29 09:00:00 +0900
---

## 1. Cloud Run 소개 및 핵심 개념

### 1.1 Cloud Run이란?

**Google Cloud Run**은 구글이 제공하는 완전 관리형 서버리스 컨테이너 플랫폼입니다. 개발자가 인프라 관리 없이 컨테이너화된 애플리케이션을 자동으로 확장하여 실행할 수 있게 해줍니다.

**핵심 특징:**
```yaml
특징:
  서버리스: 인프라 관리 불필요 (서버 프로비저닝, 패치, 확장 자동화)
  컨테이너 기반: Docker 이미지만 있으면 모든 언어/프레임워크 지원
  자동 스케일링: 
    - 요청이 없으면 0으로 축소 (비용 절감)
    - 트래픽 급증 시 자동 확장 (최대 1000 인스턴스)
  완전 관리형: Kubernetes 기반이지만 클러스터 관리 불필요
  빠른 배포: 코드 변경 후 수 초 내 배포
  HTTP(S) 엔드포인트: 자동으로 HTTPS URL 제공

과금:
  - 요청 수 기반 (월 200만 요청 무료)
  - CPU/메모리 사용 시간 기반 (요청 처리 중만 과금)
  - 트래픽 비용 (아웃바운드)
  - 무료 티어: 월 180만 vCPU-초, 360만 GiB-초
```

### 1.2 Cloud Run vs 다른 서비스 비교

```python
# 비교표
COMPARISON = {
    "Cloud Run": {
        "관리 수준": "완전 관리형",
        "확장성": "자동 (0 → 1000)",
        "비용": "사용량 기반 (매우 저렴)",
        "배포 속도": "매우 빠름 (초 단위)",
        "제약사항": "요청당 최대 60분 타임아웃",
        "적합한 경우": [
            "웹 API/서비스",
            "마이크로서비스",
            "이벤트 기반 처리",
            "간헐적 트래픽"
        ]
    },
    
    "Cloud Functions": {
        "관리 수준": "완전 관리형",
        "확장성": "자동",
        "비용": "실행 시간 기반",
        "배포 속도": "빠름",
        "제약사항": "단일 함수, 타임아웃 9분",
        "적합한 경우": [
            "간단한 이벤트 처리",
            "Webhook",
            "작은 단위 작업"
        ]
    },
    
    "GKE (Kubernetes Engine)": {
        "관리 수준": "부분 관리형",
        "확장성": "수동/자동 설정",
        "비용": "노드 상시 실행 (비쌈)",
        "배포 속도": "보통",
        "제약사항": "클러스터 관리 필요",
        "적합한 경우": [
            "복잡한 마이크로서비스",
            "상시 실행 필요",
            "세밀한 제어 필요"
        ]
    },
    
    "App Engine": {
        "관리 수준": "완전 관리형",
        "확장성": "자동",
        "비용": "인스턴스 시간 기반",
        "배포 속도": "느림 (분 단위)",
        "제약사항": "특정 언어/런타임만 지원",
        "적합한 경우": [
            "전통적인 웹앱",
            "장기 실행 서비스"
        ]
    },
    
    "Compute Engine (VM)": {
        "관리 수준": "직접 관리",
        "확장성": "수동",
        "비용": "VM 상시 실행",
        "배포 속도": "느림",
        "제약사항": "모든 관리 직접",
        "적합한 경우": [
            "레거시 앱",
            "완전한 제어 필요"
        ]
    }
}

# Cloud Run 선택 기준
def should_use_cloud_run():
    """
    Cloud Run을 선택해야 하는 경우:
    
    ✅ 좋은 경우:
    - HTTP 요청 기반 워크로드
    - 트래픽이 간헐적 (비용 절감)
    - 빠른 배포/반복 개발 필요
    - 컨테이너로 패키징 가능
    - 자동 스케일링 필요
    
    ❌ 적합하지 않은 경우:
    - WebSocket 장시간 연결 (60분 제한)
    - 대용량 파일 처리 (메모리 제한)
    - GPU 필요
    - 상태 유지 필요 (Stateful)
    - 매우 낮은 레이턴시 필요 (콜드 스타트 있음)
    """
    pass
```

### 1.3 아키텍처 이해

```
┌─────────────────────────────────────────────────────────────┐
│                     Google Cloud Run                         │
│                                                               │
│  ┌─────────────┐      ┌──────────────────────────────┐      │
│  │   Request   │──────▶│  Load Balancer (Global)      │      │
│  │   (HTTPS)   │      │  - Auto HTTPS                 │      │
│  └─────────────┘      │  - CDN Integration            │      │
│                        └──────────┬───────────────────┘      │
│                                   │                          │
│                        ┌──────────▼───────────────────┐      │
│                        │   Auto Scaler                │      │
│                        │   - Min: 0 instances         │      │
│                        │   - Max: 1000 instances      │      │
│                        └──────────┬───────────────────┘      │
│                                   │                          │
│                    ┌──────────────┼──────────────┐           │
│                    │              │              │           │
│         ┌──────────▼────┐  ┌─────▼──────┐  ┌───▼──────┐    │
│         │  Container 1  │  │Container 2 │  │Container N│    │
│         │  (Your App)   │  │ (Your App) │  │ (Your App)│    │
│         │               │  │            │  │           │    │
│         │  - CPU: 1-4   │  │            │  │           │    │
│         │  - Mem: 4GB   │  │            │  │           │    │
│         │  - Port: 8080 │  │            │  │           │    │
│         └───────────────┘  └────────────┘  └───────────┘    │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │           Knative (Kubernetes 기반)                     │  │
│  │  - Request Routing                                     │  │
│  │  - Auto Scaling                                        │  │
│  │  - Traffic Splitting (Blue/Green, Canary)             │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

연동 가능한 GCP 서비스:
├── Cloud SQL (데이터베이스)
├── Cloud Storage (파일 저장)
├── Secret Manager (비밀 정보)
├── Cloud Tasks (비동기 작업)
├── Pub/Sub (메시징)
├── Cloud Logging (로그)
└── Cloud Monitoring (모니터링)
```

**핵심 개념:**

1. **Revision (리비전)**
   - 서비스의 불변 스냅샷
   - 각 배포마다 새 리비전 생성
   - 이전 리비전으로 롤백 가능
   - 트래픽 분할 가능 (A/B 테스트)

2. **Service (서비스)**
   - 여러 리비전의 컬렉션
   - URL 엔드포인트 제공
   - 트래픽 라우팅 관리

3. **Container Instance (컨테이너 인스턴스)**
   - 실제 실행되는 컨테이너
   - 요청 처리 중에만 CPU 할당
   - 동시성: 한 인스턴스가 여러 요청 처리 가능 (기본 80)

4. **Cold Start (콜드 스타트)**
   - 인스턴스가 0일 때 첫 요청 시 컨테이너 시작 시간
   - 최소 인스턴스 설정으로 방지 가능 (비용 증가)

---

## 2. 시작하기 - 첫 번째 Cloud Run 서비스

### 2.1 GCP 프로젝트 설정

```bash
# 1. gcloud CLI 설치 (macOS)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# 2. gcloud 초기화
gcloud init

# 3. 프로젝트 생성
gcloud projects create my-cloudrun-project --name="My Cloud Run Project"

# 4. 프로젝트 선택
gcloud config set project my-cloudrun-project

# 5. 필수 API 활성화
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  artifactregistry.googleapis.com

# 6. 리전 설정 (서울)
gcloud config set run/region asia-northeast3

# 7. 현재 설정 확인
gcloud config list
```

### 2.2 간단한 Python Flask 앱 생성

```python
# app.py
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def hello():
    """기본 엔드포인트"""
    return jsonify({
        "message": "Hello from Cloud Run!",
        "service": os.environ.get('K_SERVICE', 'unknown'),
        "revision": os.environ.get('K_REVISION', 'unknown'),
        "configuration": os.environ.get('K_CONFIGURATION', 'unknown')
    })

@app.route('/health')
def health():
    """헬스 체크"""
    return jsonify({"status": "healthy"}), 200

@app.route('/api/data')
def get_data():
    """샘플 데이터 반환"""
    return jsonify({
        "items": [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"}
        ]
    })

if __name__ == '__main__':
    # Cloud Run은 PORT 환경변수 제공
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
```

```python
# requirements.txt
Flask==3.0.0
gunicorn==21.2.0
```

### 2.3 Dockerfile 작성

```dockerfile
# Dockerfile
# Multi-stage build로 이미지 크기 최적화

# Stage 1: Build
FROM python:3.11-slim as builder

WORKDIR /app

# 의존성 먼저 복사 (캐시 활용)
COPY requirements.txt .

# 가상환경에 설치
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# builder에서 설치된 패키지 복사
COPY --from=builder /root/.local /root/.local

# 애플리케이션 코드 복사
COPY app.py .

# PATH 설정
ENV PATH=/root/.local/bin:$PATH

# 비root 유저로 실행 (보안)
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Cloud Run은 PORT 환경변수 제공
ENV PORT=8080

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# gunicorn으로 실행 (production)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
```

**Dockerfile 최적화 포인트:**

```dockerfile
# ✅ 좋은 예: Multi-stage build
FROM python:3.11-slim as builder
# ... 빌드
FROM python:3.11-slim
COPY --from=builder ...

# ❌ 나쁜 예: 불필요한 파일 포함
FROM python:3.11  # full 이미지 (900MB)
COPY . .  # 모든 파일 복사 (.git, tests 등)

# ✅ 레이어 캐싱 활용
COPY requirements.txt .  # 먼저 복사
RUN pip install -r requirements.txt
COPY . .  # 코드는 나중에

# ❌ 캐시 무효화
COPY . .  # 코드 변경마다 재설치
RUN pip install -r requirements.txt

# ✅ .dockerignore 사용
# .dockerignore 파일:
__pycache__
*.pyc
.git
.env
tests/
README.md
```

```bash
# .dockerignore
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.git
.gitignore
.dockerignore
Dockerfile
README.md
tests/
.pytest_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/
.env
.env.local
```

### 2.4 로컬 테스트

```bash
# 1. Docker 빌드
docker build -t my-cloud-run-app .

# 2. 로컬 실행
docker run -p 8080:8080 \
  -e PORT=8080 \
  my-cloud-run-app

# 3. 테스트
curl http://localhost:8080
curl http://localhost:8080/health

# 4. 중지
docker stop $(docker ps -q --filter ancestor=my-cloud-run-app)
```

### 2.5 Cloud Run에 배포 (gcloud 명령어)

```bash
# 방법 1: 소스 코드에서 직접 배포 (Cloud Build 사용)
gcloud run deploy my-service \
  --source . \
  --region=asia-northeast3 \
  --allow-unauthenticated

# 방법 2: Docker 이미지 빌드 후 배포
# 2-1. Artifact Registry에 이미지 푸시
gcloud builds submit \
  --tag gcr.io/my-cloudrun-project/my-app

# 2-2. Cloud Run에 배포
gcloud run deploy my-service \
  --image gcr.io/my-cloudrun-project/my-app \
  --platform managed \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --concurrency 80

# 배포 완료 후 URL 출력
# Service [my-service] revision [my-service-00001-abc] has been deployed and is serving 100 percent of traffic.
# Service URL: https://my-service-xxxx-an.a.run.app
```

**주요 옵션 설명:**

```yaml
배포 옵션:
  --source: 소스 코드 디렉토리 (Dockerfile 자동 감지)
  --image: 컨테이너 이미지 경로
  --region: 배포 리전 (asia-northeast3=서울)
  --platform: managed (완전 관리형) / gke (GKE 클러스터)
  
인증:
  --allow-unauthenticated: 공개 접근 허용
  --no-allow-unauthenticated: 인증 필요 (기본값)
  
리소스:
  --memory: 메모리 (128Mi ~ 32Gi)
  --cpu: CPU (0.08 ~ 8)
  --timeout: 요청 타임아웃 (최대 3600초)
  
스케일링:
  --min-instances: 최소 인스턴스 (콜드 스타트 방지)
  --max-instances: 최대 인스턴스 (비용 제한)
  --concurrency: 인스턴스당 동시 요청 수 (1~1000)
  
환경변수:
  --set-env-vars: KEY1=value1,KEY2=value2
  --set-secrets: SECRET_NAME=secret_name:latest
  
네트워크:
  --vpc-connector: VPC 연결 (Cloud SQL 등)
  --ingress: all(모든 트래픽) / internal(VPC만) / internal-and-cloud-load-balancing
```

---

## 3. 심화 기능 - 환경변수, Secret, VPC 연동

### 3.1 환경변수 및 Secret 관리

```bash
# 1. Secret Manager에 비밀 정보 저장
echo -n "my-database-password" | gcloud secrets create db-password \
  --data-file=- \
  --replication-policy="automatic"

echo -n "sk-1234567890abcdef" | gcloud secrets create openai-api-key \
  --data-file=-

# 2. Cloud Run 서비스 계정에 권한 부여
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud secrets add-iam-policy-binding db-password \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 3. Cloud Run 배포 시 환경변수 및 Secret 설정
gcloud run deploy my-service \
  --image gcr.io/my-cloudrun-project/my-app \
  --region asia-northeast3 \
  --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=info" \
  --set-secrets="DB_PASSWORD=db-password:latest,OPENAI_API_KEY=openai-api-key:latest" \
  --allow-unauthenticated
```

**애플리케이션에서 사용:**

```python
# app.py
import os
from google.cloud import secretmanager

# 방법 1: Cloud Run이 자동으로 주입한 Secret (권장)
db_password = os.environ.get('DB_PASSWORD')
openai_api_key = os.environ.get('OPENAI_API_KEY')

# 방법 2: Secret Manager 직접 호출
def access_secret(secret_id, version_id="latest"):
    """
    Secret Manager에서 직접 가져오기
    (Cloud Run 환경변수 사용이 더 간단함)
    """
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.environ.get('GCP_PROJECT')
    
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    
    return response.payload.data.decode('UTF-8')

# 환경변수 사용 예
@app.route('/db-test')
def test_database():
    """데이터베이스 연결 테스트"""
    import psycopg2
    
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        database=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD')  # Secret에서 주입
    )
    
    return jsonify({"status": "connected"})
```

### 3.2 Cloud SQL 연동 (PostgreSQL)

```bash
# 1. Cloud SQL 인스턴스 생성
gcloud sql instances create my-postgres \
  --database-version=POSTGRES_15 \
  --cpu=1 \
  --memory=3840MB \
  --region=asia-northeast3 \
  --root-password="your-root-password"

# 2. 데이터베이스 생성
gcloud sql databases create mydb \
  --instance=my-postgres

# 3. 사용자 생성
gcloud sql users create myuser \
  --instance=my-postgres \
  --password="user-password"

# 4. Cloud Run에서 Cloud SQL 연결 설정
gcloud run deploy my-service \
  --image gcr.io/my-cloudrun-project/my-app \
  --region asia-northeast3 \
  --add-cloudsql-instances=my-cloudrun-project:asia-northeast3:my-postgres \
  --set-env-vars="DB_HOST=/cloudsql/my-cloudrun-project:asia-northeast3:my-postgres" \
  --set-env-vars="DB_NAME=mydb,DB_USER=myuser" \
  --set-secrets="DB_PASSWORD=db-password:latest"
```

**Cloud SQL 연결 코드 (Unix Socket 사용):**

```python
# db.py
import os
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

def get_db_connection():
    """
    Cloud SQL 연결 (Unix Socket)
    
    Cloud Run은 Cloud SQL Proxy를 자동으로 제공
    Unix Socket: /cloudsql/PROJECT:REGION:INSTANCE
    """
    
    # Cloud SQL 연결 정보
    db_user = os.environ.get('DB_USER')
    db_pass = os.environ.get('DB_PASSWORD')
    db_name = os.environ.get('DB_NAME')
    db_socket = os.environ.get('DB_HOST')  # /cloudsql/...
    
    # Unix Socket 연결 (Cloud Run)
    if db_socket.startswith('/cloudsql/'):
        db_config = {
            'pool_size': 5,
            'max_overflow': 2,
            'pool_timeout': 30,
            'pool_recycle': 1800,
        }
        
        pool = sqlalchemy.create_engine(
            sqlalchemy.engine.url.URL.create(
                drivername='postgresql+pg8000',
                username=db_user,
                password=db_pass,
                database=db_name,
                query={'unix_sock': f'{db_socket}/.s.PGSQL.5432'}
            ),
            **db_config
        )
    else:
        # TCP 연결 (로컬 개발)
        pool = create_engine(
            f'postgresql+pg8000://{db_user}:{db_pass}@{db_socket}:5432/{db_name}',
            poolclass=NullPool
        )
    
    return pool

# 사용 예
from sqlalchemy.orm import sessionmaker

engine = get_db_connection()
Session = sessionmaker(bind=engine)

@app.route('/users')
def get_users():
    """사용자 목록 조회"""
    session = Session()
    
    try:
        result = session.execute('SELECT * FROM users LIMIT 10')
        users = [dict(row) for row in result]
        return jsonify(users)
    finally:
        session.close()
```

### 3.3 VPC Connector 설정 (Private IP 접근)

```bash
# 1. VPC 네트워크 생성 (이미 있으면 생략)
gcloud compute networks create my-vpc \
  --subnet-mode=custom

# 2. 서브넷 생성
gcloud compute networks subnets create my-subnet \
  --network=my-vpc \
  --region=asia-northeast3 \
  --range=10.0.0.0/24

# 3. Serverless VPC Connector 생성
gcloud compute networks vpc-access connectors create my-connector \
  --region=asia-northeast3 \
  --subnet=my-subnet \
  --min-instances=2 \
  --max-instances=10

# 4. Cloud Run에 VPC Connector 연결
gcloud run deploy my-service \
  --image gcr.io/my-cloudrun-project/my-app \
  --region asia-northeast3 \
  --vpc-connector=my-connector \
  --vpc-egress=private-ranges-only  # private IP만 VPC 통과
  # 또는 --vpc-egress=all-traffic  # 모든 트래픽 VPC 통과

# 5. 방화벽 규칙 설정 (필요 시)
gcloud compute firewall-rules create allow-cloud-run \
  --network=my-vpc \
  --allow=tcp:5432 \
  --source-ranges=10.0.0.0/24
```

**사용 사례:**

```python
# VPC 내부 리소스 접근
import requests

@app.route('/internal-api')
def call_internal_api():
    """
    VPC 내부 Private IP로 접근
    
    예: GCE VM, GKE, Cloud SQL (Private IP)
    """
    
    # Private IP (VPC 내부)
    internal_service_url = "http://10.0.0.10:8080/api"
    
    response = requests.get(internal_service_url)
    
    return jsonify(response.json())
```

### 3.4 Cloud Storage 연동

```python
# storage_handler.py
from google.cloud import storage
import os

class CloudStorageHandler:
    """Cloud Storage 파일 처리"""
    
    def __init__(self):
        self.client = storage.Client()
        self.bucket_name = os.environ.get('GCS_BUCKET_NAME')
        self.bucket = self.client.bucket(self.bucket_name)
    
    def upload_file(self, file_data, destination_blob_name):
        """파일 업로드"""
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_string(
            file_data,
            content_type='application/octet-stream'
        )
        
        # 공개 URL 생성
        blob.make_public()
        return blob.public_url
    
    def download_file(self, source_blob_name):
        """파일 다운로드"""
        blob = self.bucket.blob(source_blob_name)
        return blob.download_as_bytes()
    
    def generate_signed_url(self, blob_name, expiration=3600):
        """Signed URL 생성 (임시 접근)"""
        from datetime import timedelta
        
        blob = self.bucket.blob(blob_name)
        
        url = blob.generate_signed_url(
            version='v4',
            expiration=timedelta(seconds=expiration),
            method='GET'
        )
        
        return url

# app.py에서 사용
from flask import request, send_file
from io import BytesIO

storage_handler = CloudStorageHandler()

@app.route('/upload', methods=['POST'])
def upload():
    """파일 업로드"""
    file = request.files['file']
    
    if file:
        filename = file.filename
        file_data = file.read()
        
        # Cloud Storage에 업로드
        url = storage_handler.upload_file(file_data, filename)
        
        return jsonify({"url": url}), 201

@app.route('/download/<filename>')
def download(filename):
    """파일 다운로드"""
    file_data = storage_handler.download_file(filename)
    
    return send_file(
        BytesIO(file_data),
        download_name=filename,
        as_attachment=True
    )

@app.route('/signed-url/<filename>')
def get_signed_url(filename):
    """임시 다운로드 URL"""
    url = storage_handler.generate_signed_url(filename)
    return jsonify({"url": url})
```

```bash
# Cloud Run에 GCS 권한 부여
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')

# Storage Object Viewer 권한
gcloud projects add-iam-policy-binding $(gcloud config get-value project) \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

# 배포
gcloud run deploy my-service \
  --image gcr.io/my-cloudrun-project/my-app \
  --set-env-vars="GCS_BUCKET_NAME=my-bucket"
```

---

## 4. 트래픽 관리 및 배포 전략

### 4.1 Blue/Green 배포

```bash
# 1. 현재 서비스 (Blue) 배포
gcloud run deploy my-service \
  --image gcr.io/my-cloudrun-project/my-app:v1.0 \
  --tag blue \
  --no-traffic  # 트래픽 받지 않음

# 2. 새 버전 (Green) 배포
gcloud run deploy my-service \
  --image gcr.io/my-cloudrun-project/my-app:v2.0 \
  --tag green \
  --no-traffic

# 3. Green 버전 테스트 (태그 URL로 접근)
# https://green---my-service-xxxx.run.app

# 4. 트래픽 100% Green으로 전환
gcloud run services update-traffic my-service \
  --to-revisions green=100

# 5. 롤백이 필요하면 Blue로 전환
gcloud run services update-traffic my-service \
  --to-revisions blue=100
```

### 4.2 Canary 배포 (점진적 배포)

```bash
# 1. 현재 버전 (v1)에 90% 트래픽
gcloud run deploy my-service \
  --image gcr.io/my-cloudrun-project/my-app:v1.0 \
  --tag stable

# 2. 새 버전 (v2) 배포 (10% 트래픽)
gcloud run deploy my-service \
  --image gcr.io/my-cloudrun-project/my-app:v2.0 \
  --tag canary \
  --no-traffic

# 3. Canary에 10% 트래픽 할당
gcloud run services update-traffic my-service \
  --to-revisions stable=90,canary=10

# 4. 모니터링 후 점진적 증가
gcloud run services update-traffic my-service \
  --to-revisions stable=50,canary=50

# 5. 문제 없으면 100% 전환
gcloud run services update-traffic my-service \
  --to-revisions canary=100

# 6. 이전 리비전 삭제
gcloud run revisions delete my-service-00001-stable
```

**자동화된 Canary 배포 스크립트:**

```bash
#!/bin/bash
# canary_deploy.sh

set -e

SERVICE_NAME="my-service"
NEW_IMAGE="$1"
CANARY_PERCENT="$2"

if [ -z "$NEW_IMAGE" ] || [ -z "$CANARY_PERCENT" ]; then
  echo "Usage: ./canary_deploy.sh IMAGE CANARY_PERCENT"
  echo "Example: ./canary_deploy.sh gcr.io/project/app:v2 10"
  exit 1
fi

echo "🚀 Deploying canary version..."

# 새 리비전 배포 (트래픽 없음)
gcloud run deploy $SERVICE_NAME \
  --image $NEW_IMAGE \
  --tag canary \
  --no-traffic \
  --quiet

# 현재 stable 리비전 찾기
STABLE_REVISION=$(gcloud run services describe $SERVICE_NAME \
  --format='value(status.traffic[0].revisionName)')

echo "📊 Stable revision: $STABLE_REVISION"

# Canary 리비전 찾기
CANARY_REVISION=$(gcloud run revisions list \
  --service=$SERVICE_NAME \
  --filter="metadata.labels.cloud.googleapis.com/location=canary" \
  --format='value(metadata.name)' \
  --limit=1)

echo "🐤 Canary revision: $CANARY_REVISION"

# 트래픽 분할
STABLE_PERCENT=$((100 - CANARY_PERCENT))

echo "🔀 Traffic split: Stable $STABLE_PERCENT% | Canary $CANARY_PERCENT%"

gcloud run services update-traffic $SERVICE_NAME \
  --to-revisions $STABLE_REVISION=$STABLE_PERCENT,$CANARY_REVISION=$CANARY_PERCENT \
  --quiet

echo "✅ Canary deployment complete!"
echo "Monitor metrics and run: ./canary_promote.sh to promote"
```

### 4.3 A/B 테스트

```bash
# 헤더 기반 라우팅 (Cloud Run은 직접 지원 안함, Load Balancer 필요)
# 대안: 애플리케이션 레벨에서 처리

# 1. 두 버전 배포
gcloud run deploy my-service \
  --image gcr.io/my-cloudrun-project/my-app:variant-a \
  --tag variant-a \
  --no-traffic

gcloud run deploy my-service \
  --image gcr.io/my-cloudrun-project/my-app:variant-b \
  --tag variant-b \
  --no-traffic

# 2. 50:50 트래픽 분할
gcloud run services update-traffic my-service \
  --to-revisions variant-a=50,variant-b=50
```

**애플리케이션 레벨 A/B 테스트:**

```python
# ab_test.py
import random
import hashlib

class ABTestManager:
    """A/B 테스트 관리"""
    
    def __init__(self):
        self.experiments = {
            'new_ui': {
                'variants': ['control', 'variant_a'],
                'traffic_split': [50, 50]  # 50:50
            },
            'recommendation_algo': {
                'variants': ['old_algo', 'new_algo'],
                'traffic_split': [70, 30]  # 70:30
            }
        }
    
    def get_variant(self, experiment_name, user_id):
        """
        사용자별 일관된 variant 할당
        
        같은 사용자는 항상 같은 variant
        """
        if experiment_name not in self.experiments:
            return None
        
        exp = self.experiments[experiment_name]
        variants = exp['variants']
        traffic_split = exp['traffic_split']
        
        # 사용자 ID 해싱 (일관성)
        hash_value = int(hashlib.md5(
            f"{experiment_name}:{user_id}".encode()
        ).hexdigest(), 16)
        
        # 0-99 범위로 정규화
        bucket = hash_value % 100
        
        # 트래픽 분할에 따라 variant 선택
        cumulative = 0
        for i, split in enumerate(traffic_split):
            cumulative += split
            if bucket < cumulative:
                return variants[i]
        
        return variants[-1]

# app.py에서 사용
ab_manager = ABTestManager()

@app.route('/recommend')
def recommend():
    """추천 API (A/B 테스트)"""
    user_id = request.args.get('user_id')
    
    # A/B 테스트 variant 결정
    variant = ab_manager.get_variant('recommendation_algo', user_id)
    
    if variant == 'new_algo':
        # 새 알고리즘
        recommendations = new_recommendation_algorithm(user_id)
    else:
        # 기존 알고리즘
        recommendations = old_recommendation_algorithm(user_id)
    
    # 로깅 (분석용)
    log_ab_test_event(user_id, 'recommendation_algo', variant)
    
    return jsonify({
        'recommendations': recommendations,
        'variant': variant  # 클라이언트 추적용
    })
```

---

## 5. deploy.sh를 활용한 배포 자동화

### 5.1 기본 deploy.sh 스크립트

```bash
#!/bin/bash
# deploy.sh - Cloud Run 배포 자동화 스크립트

set -e  # 에러 발생 시 스크립트 중단
set -o pipefail  # 파이프라인 에러 감지

# =====================================
# 설정 변수
# =====================================

# 프로젝트 정보
PROJECT_ID="${GCP_PROJECT_ID:-my-cloudrun-project}"
REGION="${GCP_REGION:-asia-northeast3}"
SERVICE_NAME="${SERVICE_NAME:-my-service}"

# 이미지 정보
IMAGE_NAME="${IMAGE_NAME:-my-app}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
IMAGE_REGISTRY="${IMAGE_REGISTRY:-gcr.io}"
IMAGE_URL="${IMAGE_REGISTRY}/${PROJECT_ID}/${IMAGE_NAME}:${IMAGE_TAG}"

# Cloud Run 설정
MEMORY="${MEMORY:-512Mi}"
CPU="${CPU:-1}"
MAX_INSTANCES="${MAX_INSTANCES:-10}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
CONCURRENCY="${CONCURRENCY:-80}"
TIMEOUT="${TIMEOUT:-300}"
ALLOW_UNAUTHENTICATED="${ALLOW_UNAUTHENTICATED:-true}"

# 환경변수 파일
ENV_FILE="${ENV_FILE:-.env.production}"

# =====================================
# 색상 출력
# =====================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

function log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

function log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

function log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =====================================
# 전처리 검증
# =====================================

function check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # gcloud CLI 확인
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed"
        exit 1
    fi
    
    # Docker 확인
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # 프로젝트 설정 확인
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
        log_warning "Setting project to $PROJECT_ID"
        gcloud config set project "$PROJECT_ID"
    fi
    
    log_success "All prerequisites met"
}

# =====================================
# Docker 이미지 빌드
# =====================================

function build_image() {
    log_info "Building Docker image: $IMAGE_URL"
    
    # Docker Buildx 사용 (멀티 플랫폼)
    docker buildx build \
        --platform linux/amd64 \
        -t "$IMAGE_URL" \
        -t "${IMAGE_REGISTRY}/${PROJECT_ID}/${IMAGE_NAME}:latest" \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg VCS_REF="$(git rev-parse HEAD)" \
        --build-arg VERSION="$IMAGE_TAG" \
        .
    
    log_success "Image built successfully"
}

# =====================================
# 이미지 푸시
# =====================================

function push_image() {
    log_info "Pushing image to $IMAGE_REGISTRY..."
    
    # Docker 인증 설정
    gcloud auth configure-docker "$IMAGE_REGISTRY" --quiet
    
    # 이미지 푸시
    docker push "$IMAGE_URL"
    docker push "${IMAGE_REGISTRY}/${PROJECT_ID}/${IMAGE_NAME}:latest"
    
    log_success "Image pushed successfully"
}

# =====================================
# Cloud Build 사용 (대안)
# =====================================

function build_with_cloud_build() {
    log_info "Building with Cloud Build..."
    
    gcloud builds submit \
        --tag "$IMAGE_URL" \
        --timeout=10m \
        .
    
    log_success "Cloud Build completed"
}

# =====================================
# 환경변수 로드
# =====================================

function load_env_vars() {
    if [ -f "$ENV_FILE" ]; then
        log_info "Loading environment variables from $ENV_FILE"
        
        # .env 파일을 gcloud 형식으로 변환
        ENV_VARS=$(grep -v '^#' "$ENV_FILE" | grep -v '^$' | tr '\n' ',' | sed 's/,$//')
        
        log_success "Environment variables loaded"
    else
        log_warning "Environment file $ENV_FILE not found"
        ENV_VARS=""
    fi
}

# =====================================
# Cloud Run 배포
# =====================================

function deploy_to_cloud_run() {
    log_info "Deploying to Cloud Run..."
    
    # 배포 명령어 구성
    DEPLOY_CMD="gcloud run deploy $SERVICE_NAME \
        --image $IMAGE_URL \
        --platform managed \
        --region $REGION \
        --memory $MEMORY \
        --cpu $CPU \
        --max-instances $MAX_INSTANCES \
        --min-instances $MIN_INSTANCES \
        --concurrency $CONCURRENCY \
        --timeout $TIMEOUT \
        --quiet"
    
    # 환경변수 추가
    if [ -n "$ENV_VARS" ]; then
        DEPLOY_CMD="$DEPLOY_CMD --set-env-vars=$ENV_VARS"
    fi
    
    # 인증 설정
    if [ "$ALLOW_UNAUTHENTICATED" = "true" ]; then
        DEPLOY_CMD="$DEPLOY_CMD --allow-unauthenticated"
    else
        DEPLOY_CMD="$DEPLOY_CMD --no-allow-unauthenticated"
    fi
    
    # VPC Connector (선택적)
    if [ -n "$VPC_CONNECTOR" ]; then
        DEPLOY_CMD="$DEPLOY_CMD --vpc-connector=$VPC_CONNECTOR"
    fi
    
    # Cloud SQL (선택적)
    if [ -n "$CLOUD_SQL_INSTANCES" ]; then
        DEPLOY_CMD="$DEPLOY_CMD --add-cloudsql-instances=$CLOUD_SQL_INSTANCES"
    fi
    
    # Secret Manager (선택적)
    if [ -n "$SECRETS" ]; then
        DEPLOY_CMD="$DEPLOY_CMD --set-secrets=$SECRETS"
    fi
    
    # 배포 실행
    eval "$DEPLOY_CMD"
    
    log_success "Deployment completed"
}

# =====================================
# 배포 확인
# =====================================

function verify_deployment() {
    log_info "Verifying deployment..."
    
    # 서비스 URL 가져오기
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region "$REGION" \
        --format 'value(status.url)')
    
    if [ -z "$SERVICE_URL" ]; then
        log_error "Failed to get service URL"
        exit 1
    fi
    
    log_success "Service URL: $SERVICE_URL"
    
    # 헬스 체크
    log_info "Running health check..."
    
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/health" || echo "000")
    
    if [ "$HTTP_STATUS" = "200" ]; then
        log_success "Health check passed (HTTP $HTTP_STATUS)"
    else
        log_error "Health check failed (HTTP $HTTP_STATUS)"
        exit 1
    fi
}

# =====================================
# 롤백 함수
# =====================================

function rollback() {
    log_warning "Rolling back to previous revision..."
    
    # 이전 리비전 찾기
    PREVIOUS_REVISION=$(gcloud run revisions list \
        --service="$SERVICE_NAME" \
        --region="$REGION" \
        --format='value(metadata.name)' \
        --limit=2 \
        | tail -n 1)
    
    if [ -z "$PREVIOUS_REVISION" ]; then
        log_error "No previous revision found"
        exit 1
    fi
    
    # 트래픽 100% 이전 리비전으로
    gcloud run services update-traffic "$SERVICE_NAME" \
        --region="$REGION" \
        --to-revisions "$PREVIOUS_REVISION=100" \
        --quiet
    
    log_success "Rolled back to $PREVIOUS_REVISION"
}

# =====================================
# 메인 실행
# =====================================

function main() {
    log_info "Starting deployment process..."
    log_info "Project: $PROJECT_ID"
    log_info "Service: $SERVICE_NAME"
    log_info "Image: $IMAGE_URL"
    
    # 전처리
    check_prerequisites
    
    # 빌드 방법 선택
    if [ "${USE_CLOUD_BUILD:-false}" = "true" ]; then
        build_with_cloud_build
    else
        build_image
        push_image
    fi
    
    # 환경변수 로드
    load_env_vars
    
    # 배포
    deploy_to_cloud_run
    
    # 검증
    verify_deployment
    
    log_success "🎉 Deployment completed successfully!"
}

# =====================================
# 에러 핸들링
# =====================================

function cleanup_on_error() {
    log_error "Deployment failed!"
    
    # 선택적 롤백
    if [ "${AUTO_ROLLBACK:-false}" = "true" ]; then
        rollback
    fi
}

trap cleanup_on_error ERR

# =====================================
# 스크립트 실행
# =====================================

# 인자 처리
case "${1:-deploy}" in
    deploy)
        main
        ;;
    rollback)
        rollback
        ;;
    verify)
        verify_deployment
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|verify}"
        exit 1
        ;;
esac
```

### 5.2 환경별 설정 파일

```bash
# .env.production
# Production 환경변수

ENVIRONMENT=production
LOG_LEVEL=info
DEBUG=false

# 데이터베이스
DB_HOST=/cloudsql/my-project:asia-northeast3:my-postgres
DB_NAME=mydb
DB_USER=myuser
# DB_PASSWORD는 Secret Manager 사용

# API Keys (Secret Manager 권장)
# OPENAI_API_KEY는 Secret Manager 사용

# 외부 서비스
REDIS_URL=redis://10.0.0.5:6379
SENTRY_DSN=https://xxxx@sentry.io/yyyy

# 기능 플래그
FEATURE_NEW_UI=true
FEATURE_EXPERIMENTAL=false
```

```bash
# .env.staging
ENVIRONMENT=staging
LOG_LEVEL=debug
DEBUG=true

DB_HOST=/cloudsql/my-project:asia-northeast3:my-postgres-staging
DB_NAME=mydb_staging
DB_USER=myuser_staging
```

```bash
# deploy.config.sh
# 배포 설정 (deploy.sh에서 source)

# 프로덕션 설정
if [ "$ENVIRONMENT" = "production" ]; then
    PROJECT_ID="my-production-project"
    SERVICE_NAME="my-service"
    REGION="asia-northeast3"
    
    MEMORY="1Gi"
    CPU="2"
    MAX_INSTANCES="50"
    MIN_INSTANCES="2"  # 콜드 스타트 방지
    
    CLOUD_SQL_INSTANCES="my-production-project:asia-northeast3:my-postgres"
    SECRETS="DB_PASSWORD=db-password:latest,OPENAI_API_KEY=openai-key:latest"
    
    ENV_FILE=".env.production"
fi

# 스테이징 설정
if [ "$ENVIRONMENT" = "staging" ]; then
    PROJECT_ID="my-staging-project"
    SERVICE_NAME="my-service-staging"
    REGION="asia-northeast3"
    
    MEMORY="512Mi"
    CPU="1"
    MAX_INSTANCES="5"
    MIN_INSTANCES="0"
    
    ENV_FILE=".env.staging"
fi
```

### 5.3 고급 deploy.sh - CI/CD 통합

```bash
#!/bin/bash
# deploy-advanced.sh - CI/CD 통합 배포 스크립트

set -euo pipefail

# =====================================
# 설정 로드
# =====================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/deploy.config.sh"

# =====================================
# Slack 알림
# =====================================

function send_slack_notification() {
    local message="$1"
    local color="${2:-#36a64f}"  # 기본 녹색
    
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"text\": \"$message\",
                    \"fields\": [
                        {\"title\": \"Service\", \"value\": \"$SERVICE_NAME\", \"short\": true},
                        {\"title\": \"Environment\", \"value\": \"$ENVIRONMENT\", \"short\": true},
                        {\"title\": \"Image\", \"value\": \"$IMAGE_TAG\", \"short\": false}
                    ]
                }]
            }" \
            --silent --output /dev/null
    fi
}

# =====================================
# 데이터베이스 마이그레이션
# =====================================

function run_migrations() {
    log_info "Running database migrations..."
    
    # Cloud Run Jobs로 마이그레이션 실행
    gcloud run jobs create migrate-job-$(date +%s) \
        --image "$IMAGE_URL" \
        --region "$REGION" \
        --set-env-vars="RUN_MIGRATIONS=true" \
        --add-cloudsql-instances="$CLOUD_SQL_INSTANCES" \
        --set-secrets="$SECRETS" \
        --execute-now \
        --wait
    
    log_success "Migrations completed"
}

# =====================================
# 스모크 테스트
# =====================================

function run_smoke_tests() {
    local service_url="$1"
    
    log_info "Running smoke tests..."
    
    # 기본 엔드포인트 테스트
    local endpoints=(
        "/health"
        "/api/status"
        "/"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local url="${service_url}${endpoint}"
        local status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
        
        if [[ "$status" =~ ^2[0-9]{2}$ ]]; then
            log_success "✓ $endpoint (HTTP $status)"
        else
            log_error "✗ $endpoint (HTTP $status)"
            return 1
        fi
    done
    
    log_success "All smoke tests passed"
}

# =====================================
# Canary 배포
# =====================================

function deploy_canary() {
    log_info "Starting canary deployment..."
    
    # 새 리비전 배포 (트래픽 없음)
    gcloud run deploy "$SERVICE_NAME" \
        --image "$IMAGE_URL" \
        --platform managed \
        --region "$REGION" \
        --tag canary \
        --no-traffic \
        --quiet
    
    # Canary URL 가져오기
    CANARY_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region "$REGION" \
        --format 'value(status.traffic[?tag=="canary"].url)')
    
    log_info "Canary URL: $CANARY_URL"
    
    # Canary 테스트
    run_smoke_tests "$CANARY_URL"
    
    # 10% 트래픽 할당
    log_info "Routing 10% traffic to canary..."
    
    local stable_revision=$(gcloud run revisions list \
        --service="$SERVICE_NAME" \
        --region="$REGION" \
        --filter="status.traffic[0].percent>0" \
        --format='value(metadata.name)' \
        --limit=1)
    
    local canary_revision=$(gcloud run revisions list \
        --service="$SERVICE_NAME" \
        --region="$REGION" \
        --filter="metadata.labels.\"cloud.googleapis.com/location\"=canary" \
        --format='value(metadata.name)' \
        --limit=1)
    
    gcloud run services update-traffic "$SERVICE_NAME" \
        --region="$REGION" \
        --to-revisions "${stable_revision}=90,${canary_revision}=10" \
        --quiet
    
    log_success "Canary deployment completed (10% traffic)"
    
    # 모니터링 대기
    log_info "Monitoring canary for 5 minutes..."
    sleep 300
    
    # 에러율 확인 (간단한 예시)
    local error_rate=$(check_error_rate "$canary_revision")
    
    if (( $(echo "$error_rate < 1.0" | bc -l) )); then
        log_success "Error rate acceptable ($error_rate%)"
        promote_canary
    else
        log_error "Error rate too high ($error_rate%)"
        rollback
        return 1
    fi
}

function promote_canary() {
    log_info "Promoting canary to 100% traffic..."
    
    local canary_revision=$(gcloud run revisions list \
        --service="$SERVICE_NAME" \
        --region="$REGION" \
        --filter="metadata.labels.\"cloud.googleapis.com/location\"=canary" \
        --format='value(metadata.name)' \
        --limit=1)
    
    gcloud run services update-traffic "$SERVICE_NAME" \
        --region="$REGION" \
        --to-revisions "${canary_revision}=100" \
        --quiet
    
    log_success "Canary promoted successfully"
}

function check_error_rate(revision_name) {
    # Cloud Monitoring API로 에러율 확인
    # 실제 구현은 프로젝트에 맞게 조정
    
    local query="resource.type=\"cloud_run_revision\"
    resource.labels.service_name=\"$SERVICE_NAME\"
    resource.labels.revision_name=\"$revision_name\"
    metric.type=\"run.googleapis.com/request_count\"
    metric.labels.response_code_class!=\"2xx\""
    
    # gcloud monitoring 명령어 또는 API 호출
    # 여기서는 예시로 0.5% 반환
    echo "0.5"
}

# =====================================
# 배포 메트릭 기록
# =====================================

function record_deployment_metrics() {
    log_info "Recording deployment metrics..."
    
    local deploy_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # BigQuery에 배포 기록 저장 (선택적)
    if [ -n "${BIGQUERY_DATASET:-}" ]; then
        echo "{
            \"deploy_time\": \"$deploy_time\",
            \"service\": \"$SERVICE_NAME\",
            \"image_tag\": \"$IMAGE_TAG\",
            \"environment\": \"$ENVIRONMENT\",
            \"deployer\": \"${USER:-unknown}\"
        }" | bq insert "${BIGQUERY_DATASET}.deployments"
    fi
}

# =====================================
# 메인 실행 (고급)
# =====================================

function main_advanced() {
    log_info "🚀 Starting advanced deployment..."
    
    # Slack 알림
    send_slack_notification "🚀 Deployment started for $SERVICE_NAME" "#0000FF"
    
    # 전처리
    check_prerequisites
    
    # 빌드
    if [ "${USE_CLOUD_BUILD:-true}" = "true" ]; then
        build_with_cloud_build
    else
        build_image
        push_image
    fi
    
    # 마이그레이션 (선택적)
    if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
        run_migrations
    fi
    
    # Canary 배포 여부
    if [ "${CANARY_DEPLOY:-false}" = "true" ]; then
        deploy_canary
    else
        load_env_vars
        deploy_to_cloud_run
        verify_deployment
    fi
    
    # 메트릭 기록
    record_deployment_metrics
    
    # 성공 알림
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region "$REGION" \
        --format 'value(status.url)')
    
    send_slack_notification "✅ Deployment successful!\nURL: $SERVICE_URL" "#36a64f"
    
    log_success "🎉 Advanced deployment completed!"
}

# 에러 시 알림
trap 'send_slack_notification "❌ Deployment failed!" "#FF0000"' ERR

# 실행
main_advanced
```

### 5.4 Makefile로 간편화

```makefile
# Makefile
.PHONY: help build deploy deploy-staging deploy-prod rollback logs

# 기본 변수
PROJECT_ID ?= my-cloudrun-project
SERVICE_NAME ?= my-service
REGION ?= asia-northeast3

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker image locally
	docker build -t $(SERVICE_NAME):latest .

test: ## Run tests
	docker run --rm $(SERVICE_NAME):latest pytest

deploy-staging: ## Deploy to staging
	ENVIRONMENT=staging ./deploy.sh

deploy-prod: ## Deploy to production
	ENVIRONMENT=production ./deploy.sh

deploy-canary: ## Deploy with canary strategy
	CANARY_DEPLOY=true ENVIRONMENT=production ./deploy-advanced.sh

rollback: ## Rollback to previous revision
	./deploy.sh rollback

logs: ## Stream logs
	gcloud run services logs tail $(SERVICE_NAME) \
		--region=$(REGION) \
		--project=$(PROJECT_ID)

describe: ## Show service details
	gcloud run services describe $(SERVICE_NAME) \
		--region=$(REGION) \
		--project=$(PROJECT_ID)

revisions: ## List revisions
	gcloud run revisions list \
		--service=$(SERVICE_NAME) \
		--region=$(REGION) \
		--project=$(PROJECT_ID)

shell: ## Connect to service (debug)
	gcloud run services proxy $(SERVICE_NAME) \
		--region=$(REGION) \
		--project=$(PROJECT_ID)

clean: ## Clean up old revisions
	@echo "Cleaning up old revisions..."
	@gcloud run revisions list \
		--service=$(SERVICE_NAME) \
		--region=$(REGION) \
		--project=$(PROJECT_ID) \
		--format='value(metadata.name)' \
		| tail -n +6 \
		| xargs -I {} gcloud run revisions delete {} \
			--region=$(REGION) \
			--project=$(PROJECT_ID) \
			--quiet
```

**사용 예:**

```bash
# 도움말
make help

# 스테이징 배포
make deploy-staging

# 프로덕션 배포
make deploy-prod

# Canary 배포
make deploy-canary

# 롤백
make rollback

# 로그 확인
make logs
```

---

## 6. GitHub Actions CI/CD 파이프라인

### 6.1 기본 GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to Cloud Run

on:
  push:
    branches:
      - main  # main 브랜치 푸시 시 자동 배포
  pull_request:
    branches:
      - main  # PR 시 테스트만
  workflow_dispatch:  # 수동 실행 가능

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  SERVICE_NAME: my-service
  REGION: asia-northeast3

jobs:
  # =====================================
  # 테스트
  # =====================================
  test:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        run: |
          pytest tests/ --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  # =====================================
  # 빌드 및 배포
  # =====================================
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    permissions:
      contents: read
      id-token: write  # Workload Identity Federation
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1
      
      - name: Configure Docker
        run: |
          gcloud auth configure-docker
      
      - name: Build Docker image
        run: |
          docker build \
            -t gcr.io/${{ env.PROJECT_ID }}/${{ env.SERVICE_NAME }}:${{ github.sha }} \
            -t gcr.io/${{ env.PROJECT_ID }}/${{ env.SERVICE_NAME }}:latest \
            --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
            --build-arg VCS_REF=${{ github.sha }} \
            .
      
      - name: Push Docker image
        run: |
          docker push gcr.io/${{ env.PROJECT_ID }}/${{ env.SERVICE_NAME }}:${{ github.sha }}
          docker push gcr.io/${{ env.PROJECT_ID }}/${{ env.SERVICE_NAME }}:latest
      
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy ${{ env.SERVICE_NAME }} \
            --image gcr.io/${{ env.PROJECT_ID }}/${{ env.SERVICE_NAME }}:${{ github.sha }} \
            --region ${{ env.REGION }} \
            --platform managed \
            --allow-unauthenticated \
            --memory 512Mi \
            --cpu 1 \
            --max-instances 10 \
            --set-env-vars="COMMIT_SHA=${{ github.sha }}" \
            --quiet
      
      - name: Verify deployment
        run: |
          SERVICE_URL=$(gcloud run services describe ${{ env.SERVICE_NAME }} \
            --region ${{ env.REGION }} \
            --format 'value(status.url)')
          
          echo "Service URL: $SERVICE_URL"
          
          # Health check
          HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $SERVICE_URL/health)
          
          if [ "$HTTP_STATUS" != "200" ]; then
            echo "Health check failed with status $HTTP_STATUS"
            exit 1
          fi
          
          echo "Deployment verified successfully!"
      
      - name: Notify Slack
        if: always()
        uses: slackapi/slack-github-action@v1
        with:
          webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
          payload: |
            {
              "text": "${{ job.status == 'success' && '✅' || '❌' }} Deployment ${{ job.status }}",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Status:* ${{ job.status }}\n*Service:* ${{ env.SERVICE_NAME }}\n*Commit:* ${{ github.sha }}"
                  }
                }
              ]
            }
```

### 6.2 환경별 배포 (Staging / Production)

```yaml
# .github/workflows/deploy-multi-env.yml
name: Multi-Environment Deploy

on:
  push:
    branches:
      - develop  # Staging
      - main     # Production

jobs:
  deploy-staging:
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment: staging
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: google-github-actions/auth@v1
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.STAGING_SA }}
      
      - name: Deploy to Staging
        run: |
          gcloud run deploy my-service-staging \
            --source . \
            --region asia-northeast3 \
            --platform managed \
            --allow-unauthenticated \
            --set-env-vars="ENVIRONMENT=staging"

  deploy-production:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production  # GitHub Environment Protection 사용
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: google-github-actions/auth@v1
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.PROD_SA }}
      
      - name: Deploy to Production (Canary)
        run: |
          # 새 리비전 배포 (트래픽 없음)
          gcloud run deploy my-service \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/my-service:${{ github.sha }} \
            --region asia-northeast3 \
            --tag canary \
            --no-traffic
          
          # 10% Canary 트래픽
          gcloud run services update-traffic my-service \
            --to-tags canary=10 \
            --region asia-northeast3
      
      - name: Wait and monitor
        run: sleep 300  # 5분 대기
      
      - name: Promote Canary
        run: |
          gcloud run services update-traffic my-service \
            --to-tags canary=100 \
            --region asia-northeast3
```

### 6.3 Workload Identity Federation 설정

```bash
# Workload Identity Federation 설정 (GitHub Actions용)

# 1. Workload Identity Pool 생성
gcloud iam workload-identity-pools create "github-pool" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# 2. Provider 생성
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# 3. Service Account 생성
gcloud iam service-accounts create github-actions-sa \
  --display-name="GitHub Actions Service Account"

# 4. Service Account에 권한 부여
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

# 5. Workload Identity 바인딩
gcloud iam service-accounts add-iam-policy-binding \
  github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/${GITHUB_REPO}"

# 6. GitHub Secrets에 추가할 값 확인
echo "WIF_PROVIDER: projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
echo "WIF_SERVICE_ACCOUNT: github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com"
```

---

## 7. 모니터링 및 로깅

### 7.1 Cloud Logging 설정

```python
# logging_config.py
import logging
import os
from google.cloud import logging as cloud_logging

def setup_logging():
    """
    Cloud Logging 설정
    
    로컬: 콘솔 출력
    Cloud Run: Structured Logging
    """
    
    # Cloud Run 환경 감지
    is_cloud_run = os.environ.get('K_SERVICE') is not None
    
    if is_cloud_run:
        # Cloud Logging 클라이언트
        client = cloud_logging.Client()
        client.setup_logging()
        
        # Structured Logging
        logging.basicConfig(
            level=logging.INFO,
            format='{"severity": "%(levelname)s", "message": "%(message)s", "timestamp": "%(asctime)s"}'
        )
    else:
        # 로컬 개발
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    return logging.getLogger(__name__)

logger = setup_logging()

# 사용 예
logger.info("Application started")
logger.error("Error occurred", extra={
    "user_id": 123,
    "request_id": "abc-123"
})
```

```python
# app.py에서 사용
from logging_config import logger

@app.before_request
def log_request():
    """요청 로깅"""
    logger.info("Incoming request", extra={
        "method": request.method,
        "path": request.path,
        "remote_addr": request.remote_addr,
        "user_agent": request.headers.get('User-Agent')
    })

@app.after_request
def log_response(response):
    """응답 로깅"""
    logger.info("Outgoing response", extra={
        "status_code": response.status_code,
        "content_length": response.content_length
    })
    return response
```

### 7.2 Cloud Monitoring (Metrics)

```python
# metrics.py
from google.cloud import monitoring_v3
import time
import os

class MetricsCollector:
    """커스텀 메트릭 수집"""
    
    def __init__(self):
        self.client = monitoring_v3.MetricServiceClient()
        self.project_id = os.environ.get('GCP_PROJECT')
        self.project_name = f"projects/{self.project_id}"
    
    def record_custom_metric(self, metric_type, value, labels=None):
        """
        커스텀 메트릭 기록
        
        Args:
            metric_type: 메트릭 타입 (예: 'api_requests')
            value: 값
            labels: 라벨 딕셔너리
        """
        series = monitoring_v3.TimeSeries()
        series.metric.type = f"custom.googleapis.com/{metric_type}"
        
        # 라벨 추가
        if labels:
            for key, val in labels.items():
                series.metric.labels[key] = str(val)
        
        # 리소스 타입
        series.resource.type = "cloud_run_revision"
        series.resource.labels["service_name"] = os.environ.get('K_SERVICE', 'unknown')
        series.resource.labels["revision_name"] = os.environ.get('K_REVISION', 'unknown')
        series.resource.labels["location"] = os.environ.get('REGION', 'asia-northeast3')
        
        # 데이터 포인트
        now = time.time()
        seconds = int(now)
        nanos = int((now - seconds) * 10 ** 9)
        
        interval = monitoring_v3.TimeInterval({
            "end_time": {"seconds": seconds, "nanos": nanos}
        })
        
        point = monitoring_v3.Point({
            "interval": interval,
            "value": {"double_value": value}
        })
        
        series.points = [point]
        
        # 전송
        self.client.create_time_series(
            name=self.project_name,
            time_series=[series]
        )

# 사용 예
metrics = MetricsCollector()

@app.route('/api/data')
def get_data():
    start_time = time.time()
    
    # 비즈니스 로직
    data = fetch_data()
    
    # 메트릭 기록
    elapsed = time.time() - start_time
    metrics.record_custom_metric(
        'api_request_duration',
        elapsed,
        labels={
            'endpoint': '/api/data',
            'status': 'success'
        }
    )
    
    return jsonify(data)
```

### 7.3 로그 조회 및 분석

```bash
# 최근 로그 확인
gcloud run services logs read my-service \
  --region=asia-northeast3 \
  --limit=50

# 실시간 로그 스트리밍
gcloud run services logs tail my-service \
  --region=asia-northeast3

# 에러 로그만 필터링
gcloud run services logs read my-service \
  --region=asia-northeast3 \
  --filter="severity>=ERROR" \
  --limit=100

# 특정 시간대 로그
gcloud run services logs read my-service \
  --region=asia-northeast3 \
  --filter='timestamp>="2025-11-29T00:00:00Z" AND timestamp<="2025-11-29T23:59:59Z"'

# JSON 형식으로 출력
gcloud run services logs read my-service \
  --region=asia-northeast3 \
  --format=json \
  --limit=10
```

### 7.4 알림 설정

```bash
# 1. 알림 채널 생성 (이메일)
gcloud alpha monitoring channels create \
  --display-name="DevOps Team Email" \
  --type=email \
  --channel-labels=email_address=devops@example.com

# 2. 알림 정책 생성 (에러율 높을 때)
cat > alert-policy.yaml << EOF
displayName: "High Error Rate Alert"
conditions:
  - displayName: "Error rate > 5%"
    conditionThreshold:
      filter: |
        resource.type="cloud_run_revision"
        metric.type="run.googleapis.com/request_count"
        metric.labels.response_code_class="5xx"
      comparison: COMPARISON_GT
      thresholdValue: 5
      duration: 60s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
notificationChannels:
  - projects/PROJECT_ID/notificationChannels/CHANNEL_ID
EOF

gcloud alpha monitoring policies create --policy-from-file=alert-policy.yaml
```

---

## 8. 성능 최적화 및 비용 관리

### 8.1 콜드 스타트 최적화

```dockerfile
# Dockerfile - 콜드 스타트 최적화

# 1. 경량 베이스 이미지 사용
FROM python:3.11-slim  # alpine도 가능하지만 호환성 이슈 주의

# 2. 멀티 스테이지 빌드
FROM python:3.11 as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH

# 3. 레이어 캐싱 최적화
# requirements.txt를 먼저 복사하여 변경 없으면 캐시 활용

# 4. 불필요한 파일 제외 (.dockerignore)
```

```python
# 애플리케이션 레벨 최적화

# 1. Lazy Loading (필요할 때만 import)
def expensive_import():
    import heavy_library  # 첫 요청에만 로딩
    return heavy_library

# 2. 전역 초기화 (컨테이너 재사용)
from google.cloud import storage

# 컨테이너 시작 시 한 번만 초기화
storage_client = storage.Client()

@app.route('/upload')
def upload():
    # storage_client 재사용 (빠름)
    bucket = storage_client.bucket('my-bucket')
    # ...

# 3. 연결 풀링
from sqlalchemy import create_engine

engine = create_engine(
    'postgresql://...',
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True  # 연결 유효성 확인
)
```

```bash
# Cloud Run 설정으로 콜드 스타트 줄이기

# 최소 인스턴스 설정 (항상 대기, 비용 증가)
gcloud run services update my-service \
  --min-instances=1 \
  --region=asia-northeast3

# CPU always allocated (요청 없을 때도 CPU 할당, 백그라운드 작업 가능)
gcloud run services update my-service \
  --cpu-throttling \
  --region=asia-northeast3
```

### 8.2 비용 최적화

```bash
# 비용 분석
gcloud billing accounts list
gcloud billing projects describe $PROJECT_ID

# Cloud Run 비용 확인
gcloud run services describe my-service \
  --region=asia-northeast3 \
  --format="table(
    status.traffic[0].revisionName,
    status.conditions[0].lastTransitionTime,
    spec.template.spec.containers[0].resources.limits
  )"
```

**비용 절감 전략:**

```yaml
최적화 방법:
  1. 최소 인스턴스 0으로 설정:
    - 트래픽 없으면 자동 축소
    - 간헐적 서비스에 적합
  
  2. 적절한 리소스 할당:
    - 과도한 메모리/CPU 방지
    - 실제 사용량 모니터링 후 조정
    
  3. 동시성 최대화:
    - concurrency 80 (기본값)
    - 한 인스턴스가 여러 요청 처리 → 인스턴스 수 감소
  
  4. 요청 타임아웃 최적화:
    - 불필요하게 긴 타임아웃 방지
    - 빠른 실패로 리소스 절약
  
  5. 리전 선택:
    - 가까운 리전 사용 (레이턴시 및 트래픽 비용 절감)
  
  6. CDN 활용:
    - 정적 파일은 Cloud CDN
    - Cloud Run은 동적 컨텐츠만
  
  7. 배치 작업은 Cloud Run Jobs:
    - 서비스 대신 Jobs 사용 (완료 후 종료)

비용 예시 (서울 리전):
  요청 수: 월 200만 무료, 이후 100만당 $0.40
  CPU: vCPU-초당 $0.00002400
  메모리: GiB-초당 $0.00000250
  
  예시 계산:
    - 512MB, 1 CPU
    - 월 100만 요청
    - 평균 응답시간 200ms
    
  비용:
    요청: 무료 (200만 이하)
    CPU: 1M * 0.2초 * $0.000024 = $4.80
    메모리: 1M * 0.2초 * 0.5GB * $0.0000025 = $0.25
    총: 약 $5/월
```

### 8.3 성능 모니터링

```python
# performance_monitoring.py
import time
from functools import wraps
from flask import request, g

def measure_performance(f):
    """요청 처리 시간 측정 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        result = f(*args, **kwargs)
        
        elapsed = time.time() - start_time
        
        # 로그 기록
        logger.info("Performance", extra={
            "endpoint": request.path,
            "method": request.method,
            "duration_ms": elapsed * 1000,
            "status_code": getattr(result, 'status_code', 200)
        })
        
        # 느린 요청 경고
        if elapsed > 1.0:  # 1초 이상
            logger.warning(f"Slow request: {request.path} took {elapsed:.2f}s")
        
        return result
    
    return decorated_function

# 사용
@app.route('/api/slow-endpoint')
@measure_performance
def slow_endpoint():
    # ...
    pass
```

---

## 9. 보안 및 인증

### 9.1 IAM 인증 (Private 서비스)

```bash
# 인증 필요한 서비스 배포
gcloud run deploy my-private-service \
  --image gcr.io/my-project/my-app \
  --region=asia-northeast3 \
  --no-allow-unauthenticated  # 인증 필수

# 특정 사용자에게 권한 부여
gcloud run services add-iam-policy-binding my-private-service \
  --region=asia-northeast3 \
  --member="user:john@example.com" \
  --role="roles/run.invoker"

# Service Account에 권한 부여
gcloud run services add-iam-policy-binding my-private-service \
  --region=asia-northeast3 \
  --member="serviceAccount:my-sa@project.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

```python
# 인증된 요청 보내기
import google.auth
import google.auth.transport.requests
import requests

def call_private_service(service_url):
    """
    IAM 인증으로 Private Cloud Run 호출
    """
    
    # 인증 정보 가져오기
    credentials, project = google.auth.default()
    
    # ID 토큰 요청
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    
    id_token = credentials.id_token
    
    # 요청
    headers = {
        'Authorization': f'Bearer {id_token}'
    }
    
    response = requests.get(service_url, headers=headers)
    
    return response.json()
```

### 9.2 API Key 인증

```python
# api_key_auth.py
from functools import wraps
from flask import request, jsonify
import os

def require_api_key(f):
    """API Key 검증 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        valid_api_key = os.environ.get('API_KEY')
        
        if not api_key or api_key != valid_api_key:
            return jsonify({"error": "Invalid API key"}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

# 사용
@app.route('/api/protected')
@require_api_key
def protected_endpoint():
    return jsonify({"message": "Access granted"})
```

### 9.3 CORS 설정

```python
# cors_config.py
from flask_cors import CORS

# 전체 허용 (개발 환경)
CORS(app)

# 특정 도메인만 허용 (프로덕션)
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://myapp.com",
            "https://www.myapp.com"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

---

## 10. 실전 예제 및 Best Practices

### 10.1 Django 애플리케이션 배포

```dockerfile
# Dockerfile (Django)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드
COPY . .

# Static 파일 수집
RUN python manage.py collectstatic --noinput

# 비root 유저
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# gunicorn 실행
CMD exec gunicorn myproject.wsgi:application \
    --bind :$PORT \
    --workers 2 \
    --threads 4 \
    --timeout 0 \
    --access-logfile - \
    --error-logfile -
```

```python
# settings.py (Django)
import os

# Cloud Run 환경 감지
IS_CLOUD_RUN = os.environ.get('K_SERVICE') is not None

if IS_CLOUD_RUN:
    DEBUG = False
    
    # Cloud SQL 연결
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': os.environ.get('DB_HOST'),
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
        }
    }
    
    # Cloud Storage for Static/Media
    DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
    GS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME')
    
    # Security
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    ALLOWED_HOSTS = ['.run.app', 'myapp.com']
```

### 10.2 FastAPI 애플리케이션

```python
# main.py (FastAPI)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import logging

app = FastAPI(title="My API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    logging.info(
        f"{request.method} {request.url.path} "
        f"completed in {duration:.3f}s "
        f"with status {response.status_code}"
    )
    
    return response

@app.get("/")
async def root():
    return {"message": "Hello from Cloud Run!"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

### 10.3 Best Practices 체크리스트

```yaml
배포 전 체크리스트:

□ 보안:
  - [ ] HTTPS only (자동 제공)
  - [ ] 환경변수로 Secret 관리 (코드에 하드코딩 금지)
  - [ ] Secret Manager 사용
  - [ ] IAM 최소 권한 원칙
  - [ ] API Key/인증 구현

□ 성능:
  - [ ] Docker 이미지 최적화 (멀티 스테이지, .dockerignore)
  - [ ] 연결 풀링 구현
  - [ ] 적절한 리소스 할당 (메모리/CPU)
  - [ ] 동시성 설정 최적화

□ 안정성:
  - [ ] 헬스 체크 엔드포인트 구현
  - [ ] Graceful shutdown
  - [ ] 에러 핸들링 및 로깅
  - [ ] 재시도 로직 (외부 API 호출)

□ 모니터링:
  - [ ] Structured logging
  - [ ] 커스텀 메트릭 수집
  - [ ] 알림 설정 (에러율, 레이턴시)
  - [ ] 대시보드 구성

□ 비용:
  - [ ] 최소 인스턴스 0 (필요 시만 증가)
  - [ ] 적절한 타임아웃 설정
  - [ ] 불필요한 리소스 정리
  - [ ] 예산 알림 설정

□ CI/CD:
  - [ ] 자동화된 테스트
  - [ ] Blue/Green 또는 Canary 배포
  - [ ] 롤백 계획
  - [ ] 배포 알림

□ 문서화:
  - [ ] README with deployment instructions
  - [ ] API 문서 (OpenAPI/Swagger)
  - [ ] 환경변수 목록
  - [ ] 트러블슈팅 가이드
```

---

## 결론

### 핵심 요약

**Cloud Run의 장점:**
1. **서버리스**: 인프라 관리 불필요, 자동 스케일링
2. **컨테이너 기반**: 모든 언어/프레임워크 지원
3. **비용 효율적**: 사용한 만큼만 과금, 무료 티어 제공
4. **빠른 배포**: 수 초 내 배포 가능
5. **완전 관리형**: 고가용성, 로드 밸런싱 자동 제공

**deploy.sh 자동화의 이점:**
- 일관된 배포 프로세스
- 사람의 실수 방지
- CI/CD 파이프라인 통합
- 환경별 설정 관리
- 롤백 자동화

### 다음 단계

1. **학습 로드맵:**
   - Cloud Run 기본 → Cloud SQL 연동 → VPC 네트워킹 → CI/CD 구축

2. **추가 탐구:**
   - Cloud Run Jobs (배치 작업)
   - gRPC 서비스
   - WebSocket 지원
   - Multi-region 배포

3. **추천 리소스:**
   - [Cloud Run 공식 문서](https://cloud.google.com/run/docs)
   - [Knative (기반 기술)](https://knative.dev/)
   - [Cloud Run Samples](https://github.com/GoogleCloudPlatform/cloud-run-samples)

**Happy Deploying! 🚀☁️**

