---
layout: post
title: "AWS S3 vs Cloudflare R2 완벽 비교 - Presigned URL로 이미지 업로드하기"
date: 2025-11-19
categories: [AWS, Cloudflare, Cloud Storage]
tags: [S3, R2, Cloudflare, Object Storage, Presigned URL, Image Upload, Cost Optimization]
image: "/assets/img/posts/2025-11-19-aws-s3-vs-cloudflare-r2-comparison.webp"
---

# AWS S3 vs Cloudflare R2 완벽 비교 - Presigned URL로 이미지 업로드하기

클라우드 스토리지를 선택할 때 AWS S3가 업계 표준이지만, Cloudflare R2는 **이그레스 비용 0원**이라는 파격적인 가격 정책으로 주목받고 있습니다. 이번 포스트에서는 두 서비스를 심층 비교하고, Cloudflare R2에서 Presigned URL을 활용한 이미지 업로드 구현 방법을 실습해보겠습니다.

## 목차
1. [AWS S3 vs Cloudflare R2 개요](#1-aws-s3-vs-cloudflare-r2-개요)
2. [비용 비교 분석](#2-비용-비교-분석)
3. [성능 및 기능 비교](#3-성능-및-기능-비교)
4. [Cloudflare R2 시작하기](#4-cloudflare-r2-시작하기)
5. [Presigned URL 개념](#5-presigned-url-개념)
6. [R2 Presigned URL 구현 - 백엔드](#6-r2-presigned-url-구현---백엔드)
7. [R2 Presigned URL 구현 - 프론트엔드](#7-r2-presigned-url-구현---프론트엔드)
8. [프로덕션 고려사항](#8-프로덕션-고려사항)
9. [결론 및 선택 가이드](#9-결론-및-선택-가이드)

---

## 1. AWS S3 vs Cloudflare R2 개요

### 1.1 AWS S3 (Simple Storage Service)

**출시:** 2006년  
**위치:** AWS 글로벌 리전

AWS S3는 객체 스토리지의 사실상 표준(de facto standard)입니다.

**주요 특징:**
- ✅ 99.999999999% (11 nines) 내구성
- ✅ 26개 이상의 리전 선택 가능
- ✅ 방대한 AWS 생태계 통합
- ✅ 성숙한 기능 세트 (버전 관리, 라이프사이클, 복제 등)
- ❌ 이그레스(다운로드) 비용 발생

**대표 사용 사례:**
```
- 정적 웹사이트 호스팅
- 데이터 백업 및 아카이빙
- 빅데이터 분석 (Athena, EMR 연동)
- CDN 원본 스토리지 (CloudFront)
- 미디어 파일 스트리밍
```

### 1.2 Cloudflare R2

**출시:** 2022년  
**위치:** Cloudflare 글로벌 네트워크

Cloudflare R2는 "S3 호환 API + 이그레스 비용 0원"으로 차별화됩니다.

**주요 특징:**
- ✅ **이그레스 비용 0원** 🎉
- ✅ S3 호환 API (코드 마이그레이션 쉬움)
- ✅ Cloudflare 네트워크 통합 (Workers, CDN)
- ✅ 자동 글로벌 복제
- ❌ S3 대비 기능 제한적 (아직 성장 중)
- ❌ 리전 선택 불가 (자동 분산)

**대표 사용 사례:**
```
- 대용량 파일 배포 (동영상, 이미지)
- CDN과 통합된 미디어 서빙
- 공개 파일 저장소
- 이그레스 비용 절감이 필수인 경우
```

### 1.3 핵심 차이점 요약

| 항목 | AWS S3 | Cloudflare R2 |
|------|--------|---------------|
| **스토리지 비용** | $0.023/GB/월 | $0.015/GB/월 |
| **이그레스 비용** | $0.09/GB | **$0** 🎉 |
| **API 호환성** | S3 API | S3 호환 API |
| **리전 선택** | ✅ 26개 리전 | ❌ 자동 분산 |
| **내구성** | 11 nines | 11 nines |
| **CDN 통합** | CloudFront 별도 | 기본 포함 |
| **버전 관리** | ✅ | ✅ (베타) |
| **라이프사이클** | ✅ | ⏳ 개발 중 |
| **성숙도** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

**결론:** 대용량 다운로드가 많으면 R2, AWS 생태계 의존성이 높으면 S3

---

## 2. 비용 비교 분석

### 2.1 실제 비용 시뮬레이션

**시나리오: 블로그 이미지 스토리지**

```
조건:
- 스토리지: 100GB
- 업로드: 10GB/월
- 다운로드: 500GB/월
- API 요청: 100만건/월
```

#### AWS S3 비용 계산

```python
# 스토리지 비용
storage_cost = 100 * 0.023  # $2.30

# PUT 요청 비용 (업로드)
put_requests = 10_000  # 10GB = 10,000개 파일 (1MB 가정)
put_cost = (put_requests / 1000) * 0.005  # $0.05

# GET 요청 비용 (다운로드)
get_requests = 500_000  # 500GB = 500,000개 파일
get_cost = (get_requests / 1000) * 0.0004  # $0.20

# 이그레스 비용 (다운로드 데이터 전송)
egress_cost = 500 * 0.09  # $45.00 🔥

# 총합
total_s3 = storage_cost + put_cost + get_cost + egress_cost
print(f"AWS S3 월 비용: ${total_s3:.2f}")
# 출력: AWS S3 월 비용: $47.55
```

#### Cloudflare R2 비용 계산

```python
# 스토리지 비용
storage_cost = 100 * 0.015  # $1.50

# Class A 요청 (PUT, LIST)
class_a_requests = 10_000
class_a_cost = (class_a_requests / 1_000_000) * 4.50  # $0.045

# Class B 요청 (GET, HEAD)
class_b_requests = 500_000
class_b_cost = (class_b_requests / 1_000_000) * 0.36  # $0.18

# 이그레스 비용
egress_cost = 0  # $0.00 🎉

# 총합
total_r2 = storage_cost + class_a_cost + class_b_cost + egress_cost
print(f"Cloudflare R2 월 비용: ${total_r2:.2f}")
# 출력: Cloudflare R2 월 비용: $1.73
```

**결과:**
```
AWS S3:         $47.55/월
Cloudflare R2:  $1.73/월

💰 절감액: $45.82/월 (96.4% 절감!)
💰 연간 절감: $549.84
```

### 2.2 다양한 시나리오별 비용

**1) 소규모 프로젝트 (10GB 스토리지, 50GB 다운로드)**

| 항목 | S3 | R2 | 절감 |
|------|----|----|------|
| 스토리지 | $0.23 | $0.15 | $0.08 |
| 이그레스 | $4.50 | $0.00 | $4.50 |
| API | $0.05 | $0.02 | $0.03 |
| **총합** | **$4.78** | **$0.17** | **$4.61 (96%)** |

**2) 중규모 프로젝트 (500GB 스토리지, 2TB 다운로드)**

| 항목 | S3 | R2 | 절감 |
|------|----|----|------|
| 스토리지 | $11.50 | $7.50 | $4.00 |
| 이그레스 | $184.32 | $0.00 | $184.32 |
| API | $1.00 | $0.50 | $0.50 |
| **총합** | **$196.82** | **$8.00** | **$188.82 (96%)** |

**3) 대규모 프로젝트 (10TB 스토리지, 100TB 다운로드)**

| 항목 | S3 | R2 | 절감 |
|------|----|----|------|
| 스토리지 | $235.52 | $153.60 | $81.92 |
| 이그레스 | $8,192.00 | $0.00 | $8,192.00 |
| API | $50.00 | $20.00 | $30.00 |
| **총합** | **$8,477.52** | **$173.60** | **$8,303.92 (98%)** |

### 2.3 숨겨진 비용 고려사항

**AWS S3 추가 비용:**
```
✅ CloudFront CDN 사용 시: 별도 비용 ($0.085/GB)
✅ S3 Transfer Acceleration: +$0.04/GB
✅ S3 Intelligent-Tiering: +$0.0025/1000 objects
✅ Cross-Region Replication: +$0.02/GB
```

**Cloudflare R2 무료 티어:**
```
🎁 매월 무료:
- 스토리지: 10GB
- Class A 요청: 100만건
- Class B 요청: 1000만건
```

**실제 비용 예시 (스타트업):**

```python
# 1년 운영 비용 비교

# AWS S3 + CloudFront
s3_storage = 200 * 0.023 * 12  # $55.20
s3_egress = 0  # CloudFront 사용
cloudfront_cost = 1000 * 0.085 * 12  # $1,020.00
aws_total = s3_storage + cloudfront_cost
print(f"AWS 연간 비용: ${aws_total:.2f}")
# 출력: AWS 연간 비용: $1,075.20

# Cloudflare R2 (CDN 포함)
r2_storage = 200 * 0.015 * 12  # $36.00
r2_egress = 0  # 무료
r2_total = r2_storage
print(f"R2 연간 비용: ${r2_total:.2f}")
# 출력: R2 연간 비용: $36.00

print(f"💰 연간 절감: ${aws_total - r2_total:.2f}")
# 출력: 💰 연간 절감: $1,039.20
```

---

## 3. 성능 및 기능 비교

### 3.1 성능 벤치마크

**업로드 속도 테스트 (100MB 파일)**

```bash
# AWS S3 (ap-northeast-2, Seoul)
$ time aws s3 cp test.jpg s3://my-bucket/
# 평균: 2.3초

# Cloudflare R2 (자동 분산)
$ time aws s3 cp test.jpg s3://my-r2-bucket/ --endpoint-url=https://account-id.r2.cloudflarestorage.com
# 평균: 1.8초
```

**다운로드 속도 테스트 (100MB 파일)**

```bash
# AWS S3 (직접 다운로드)
$ time curl -O https://my-bucket.s3.amazonaws.com/test.jpg
# 평균: 3.1초

# AWS S3 + CloudFront
$ time curl -O https://d111111abcdef8.cloudfront.net/test.jpg
# 평균: 1.2초

# Cloudflare R2 (공개 버킷)
$ time curl -O https://pub-xxxxx.r2.dev/test.jpg
# 평균: 1.0초 ⚡
```

**결과:**
- 업로드: R2가 약간 빠름 (Cloudflare 네트워크 최적화)
- 다운로드: R2 ≈ S3+CloudFront (둘 다 CDN 활용)

### 3.2 기능 비교표

| 기능 | AWS S3 | Cloudflare R2 | 비고 |
|------|--------|---------------|------|
| **객체 버전 관리** | ✅ | ✅ (베타) | R2는 제한적 |
| **라이프사이클 정책** | ✅ | ⏳ | 개발 중 |
| **서버 측 암호화** | ✅ SSE-S3, SSE-KMS | ✅ 자동 | R2는 항상 암호화 |
| **객체 잠금** | ✅ | ❌ | 규제 준수 필요 시 S3 |
| **이벤트 알림** | ✅ SNS, SQS, Lambda | ✅ Workers | R2는 Workers 통합 |
| **정적 웹 호스팅** | ✅ | ✅ | 비슷한 기능 |
| **CORS 설정** | ✅ | ✅ | 동일 |
| **Presigned URL** | ✅ | ✅ | 둘 다 지원 |
| **멀티파트 업로드** | ✅ 5GB+ | ✅ 5GB+ | 동일 |
| **최대 객체 크기** | 5TB | 5TB | 동일 |
| **배치 작업** | ✅ | ❌ | S3만 지원 |
| **복제** | ✅ CRR, SRR | ✅ 자동 글로벌 | R2는 자동 |

### 3.3 API 호환성

**S3 SDK를 그대로 사용 가능 (R2)**

```python
import boto3

# AWS S3 설정
s3_client = boto3.client(
    's3',
    region_name='ap-northeast-2'
)

# Cloudflare R2 설정 (엔드포인트만 변경)
r2_client = boto3.client(
    's3',
    endpoint_url='https://account-id.r2.cloudflarestorage.com',
    aws_access_key_id='r2_access_key_id',
    aws_secret_access_key='r2_secret_access_key',
    region_name='auto'  # R2는 자동
)

# 동일한 API 사용
s3_client.upload_file('test.jpg', 'my-s3-bucket', 'test.jpg')
r2_client.upload_file('test.jpg', 'my-r2-bucket', 'test.jpg')
```

**지원되는 S3 API (R2):**

```
✅ 지원:
- GetObject, PutObject, DeleteObject
- ListObjects, ListObjectsV2
- HeadObject, CopyObject
- CreateMultipartUpload, UploadPart, CompleteMultipartUpload
- GetBucketCors, PutBucketCors
- Presigned URLs

❌ 미지원:
- Bucket ACLs (Public Access Block)
- Glacier 스토리지 클래스
- S3 Select
- Bucket Policies (일부 제한)
```

### 3.4 글로벌 분산 및 레이턴시

**AWS S3:**
```
리전 선택 필요
→ 사용자와 리전 간 거리에 따라 레이턴시 차이
→ CloudFront로 보완 (추가 비용)

예시:
- 서울 리전: 한국 사용자 50ms, 미국 사용자 200ms
- 버지니아 리전: 미국 사용자 50ms, 한국 사용자 250ms
```

**Cloudflare R2:**
```
자동 글로벌 복제
→ 300개 이상의 엣지 위치
→ 사용자와 가장 가까운 위치에서 서빙
→ CDN 기본 포함

예시:
- 전 세계 어디서든 평균 50-100ms
```

---

## 4. Cloudflare R2 시작하기

### 4.1 계정 설정 및 버킷 생성

**Step 1: Cloudflare 계정 생성**

```bash
# 1. https://dash.cloudflare.com/ 접속
# 2. 계정 생성 (무료)
# 3. R2 메뉴로 이동
```

**Step 2: R2 활성화**

```
Dashboard → R2 Object Storage → Enable R2
```

무료 티어가 자동으로 적용됩니다:
- 스토리지: 10GB/월
- Class A 요청: 100만건/월
- Class B 요청: 1000만건/월

**Step 3: 버킷 생성**

```bash
# Cloudflare Dashboard에서:
R2 → Create Bucket

버킷 이름: my-images-bucket
위치: 자동 (Automatic)
```

**CLI로 생성 (선택사항):**

```bash
# Wrangler CLI 설치
npm install -g wrangler

# Cloudflare 로그인
wrangler login

# 버킷 생성
wrangler r2 bucket create my-images-bucket

# 버킷 목록 확인
wrangler r2 bucket list
```

### 4.2 API 토큰 생성

**Step 1: R2 API 토큰 생성**

```
Dashboard → R2 → Manage R2 API Tokens → Create API Token
```

**권한 설정:**
```
Type: R2 Token
Permissions:
  ✅ Object Read & Write
  ✅ Bucket Read
Bucket: my-images-bucket (특정 버킷만 접근)
TTL: Never expires (또는 원하는 기간)
```

**생성 결과:**

```json
{
  "access_key_id": "abcdef1234567890abcdef1234567890",
  "secret_access_key": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
  "endpoint": "https://1a2b3c4d5e6f7g8h.r2.cloudflarestorage.com"
}
```

⚠️ **주의:** `secret_access_key`는 한 번만 표시되므로 안전하게 보관하세요!

### 4.3 환경 변수 설정

**프로젝트에 환경 변수 추가:**

```bash
# .env
R2_ACCOUNT_ID=1a2b3c4d5e6f7g8h
R2_ACCESS_KEY_ID=abcdef1234567890abcdef1234567890
R2_SECRET_ACCESS_KEY=1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd
R2_BUCKET_NAME=my-images-bucket
R2_PUBLIC_URL=https://pub-1234567890abcdef.r2.dev
```

**.env.example 추가 (Git에 커밋):**

```bash
# .env.example
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key_id
R2_SECRET_ACCESS_KEY=your_secret_access_key
R2_BUCKET_NAME=your_bucket_name
R2_PUBLIC_URL=your_public_url
```

**.gitignore에 추가:**

```bash
# .gitignore
.env
.env.local
```

### 4.4 공개 버킷 설정 (선택사항)

이미지를 공개적으로 접근 가능하게 하려면:

```
Dashboard → R2 → my-images-bucket → Settings → Public Access

Enable Public Access:
  ✅ Allow Access
  
Custom Domain (선택):
  예: images.yourdomain.com
  
또는 R2.dev 서브도메인 사용:
  예: https://pub-1234567890abcdef.r2.dev
```

**CORS 설정:**

```json
[
  {
    "AllowedOrigins": ["https://yourdomain.com", "http://localhost:3000"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

Dashboard → R2 → my-images-bucket → Settings → CORS Policy

### 4.5 SDK 설치 및 기본 설정

**Node.js (백엔드):**

```bash
npm install @aws-sdk/client-s3 @aws-sdk/s3-request-presigner
```

**Python (백엔드):**

```bash
pip install boto3
```

**기본 클라이언트 설정:**

**Node.js:**

```typescript
// lib/r2.ts
import { S3Client } from '@aws-sdk/client-s3';

export const r2Client = new S3Client({
  region: 'auto',
  endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: {
    accessKeyId: process.env.R2_ACCESS_KEY_ID!,
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
  },
});

export const BUCKET_NAME = process.env.R2_BUCKET_NAME!;
export const PUBLIC_URL = process.env.R2_PUBLIC_URL!;
```

**Python:**

```python
# config/r2.py
import os
import boto3
from botocore.client import Config

def get_r2_client():
    return boto3.client(
        's3',
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
        config=Config(signature_version='s3v4'),
        region_name='auto'
    )

BUCKET_NAME = os.getenv('R2_BUCKET_NAME')
PUBLIC_URL = os.getenv('R2_PUBLIC_URL')
```

---

## 5. Presigned URL 개념

### 5.1 Presigned URL이란?

**정의:**  
Presigned URL은 **임시로 서명된 URL**로, AWS/R2 자격 증명 없이도 특정 시간 동안 객체에 접근할 수 있게 합니다.

**일반 업로드 vs Presigned URL:**

```
❌ 일반 업로드 (서버 경유):
Client → [File] → Backend Server → R2
문제: 서버 대역폭 낭비, 속도 느림

✅ Presigned URL (직접 업로드):
Client → [Request URL] → Backend
Client → [File] → R2 (직접 업로드)
장점: 빠름, 서버 부하 없음
```

### 5.2 Presigned URL 동작 원리

**플로우:**

```
1. Client: "이미지 업로드할 URL 주세요"
   └─> Backend API: POST /api/upload/presigned-url

2. Backend: Presigned URL 생성
   └─> 파일명, 타입, 크기 검증
   └─> R2에 PUT용 Presigned URL 요청
   └─> 서명된 URL 생성 (유효기간: 5분)

3. Backend → Client: Presigned URL 반환
   {
     "uploadUrl": "https://...?X-Amz-Signature=...",
     "key": "uploads/user123/image.jpg",
     "publicUrl": "https://pub-xxx.r2.dev/uploads/user123/image.jpg"
   }

4. Client: Presigned URL로 직접 업로드
   └─> PUT https://...?X-Amz-Signature=...
   └─> Request Body: [이미지 파일]

5. R2: 업로드 완료
   └─> 서명 검증 (유효기간, 권한 체크)
   └─> 파일 저장
   └─> 200 OK

6. Client: 업로드 성공 확인
   └─> Backend API: POST /api/upload/confirm
   └─> DB에 이미지 메타데이터 저장
```

### 5.3 Presigned URL의 장점

**1) 서버 부하 감소**

```
전통 방식:
  1000명이 10MB 이미지 업로드
  → 서버 트래픽: 10GB
  → 서버 → R2: 10GB
  → 총: 20GB 대역폭 사용

Presigned URL:
  1000명이 10MB 이미지 업로드
  → 서버 트래픽: 1000 * 200B (URL만) = 0.2MB
  → 클라이언트 → R2: 10GB (직접)
  → 총: 10GB 대역폭 사용
  
💰 서버 비용 50% 절감!
```

**2) 업로드 속도 향상**

```
전통 방식:
  Client (서울) → Server (서울) → R2 (글로벌)
  레이턴시: 50ms + 100ms = 150ms

Presigned URL:
  Client (서울) → R2 (가까운 엣지)
  레이턴시: 50ms
  
⚡ 3배 빠름!
```

**3) 보안**

```
✅ 임시 URL (5분 후 만료)
✅ 서명 검증 (변조 방지)
✅ 특정 파일만 접근 (key 지정)
✅ 서버 자격 증명 노출 없음
```

### 5.4 Presigned URL 보안 고려사항

**1) 만료 시간 설정**

```typescript
// ❌ 너무 긴 만료 시간
const url = await getSignedUrl(r2Client, command, { expiresIn: 86400 }); // 24시간

// ✅ 적절한 만료 시간
const url = await getSignedUrl(r2Client, command, { expiresIn: 300 }); // 5분
```

**2) 파일 타입 검증**

```typescript
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

if (!ALLOWED_TYPES.includes(contentType)) {
  throw new Error('Invalid file type');
}
```

**3) 파일 크기 제한**

```typescript
const MAX_SIZE = 10 * 1024 * 1024; // 10MB

if (fileSize > MAX_SIZE) {
  throw new Error('File too large');
}
```

**4) 사용자 인증**

```typescript
// ✅ 로그인한 사용자만 Presigned URL 발급
if (!session.user) {
  return res.status(401).json({ error: 'Unauthorized' });
}

// 사용자별 디렉토리
const key = `uploads/${session.user.id}/${filename}`;
```

**5) Rate Limiting**

```typescript
// 1분에 10개 업로드 제한
const rateLimit = {
  windowMs: 60 * 1000,
  max: 10,
};
```

---

## 6. R2 Presigned URL 구현 - 백엔드

### 6.1 Node.js + Express 구현

**프로젝트 구조:**

```
backend/
├── src/
│   ├── routes/
│   │   └── upload.ts
│   ├── controllers/
│   │   └── uploadController.ts
│   ├── lib/
│   │   └── r2.ts
│   ├── middleware/
│   │   ├── auth.ts
│   │   └── rateLimit.ts
│   └── app.ts
├── .env
└── package.json
```

**1) R2 클라이언트 설정 (lib/r2.ts)**

```typescript
import { S3Client } from '@aws-sdk/client-s3';

if (!process.env.R2_ACCOUNT_ID || !process.env.R2_ACCESS_KEY_ID || !process.env.R2_SECRET_ACCESS_KEY) {
  throw new Error('Missing R2 environment variables');
}

export const r2Client = new S3Client({
  region: 'auto',
  endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: {
    accessKeyId: process.env.R2_ACCESS_KEY_ID,
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY,
  },
});

export const BUCKET_NAME = process.env.R2_BUCKET_NAME!;
export const PUBLIC_URL = process.env.R2_PUBLIC_URL!;

// 허용 파일 타입
export const ALLOWED_IMAGE_TYPES = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/gif',
  'image/svg+xml',
] as const;

// 최대 파일 크기 (10MB)
export const MAX_FILE_SIZE = 10 * 1024 * 1024;
```

**2) 업로드 컨트롤러 (controllers/uploadController.ts)**

```typescript
import { Request, Response } from 'express';
import { PutObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import { r2Client, BUCKET_NAME, PUBLIC_URL, ALLOWED_IMAGE_TYPES, MAX_FILE_SIZE } from '../lib/r2';
import crypto from 'crypto';
import path from 'path';

interface PresignedUrlRequest {
  filename: string;
  contentType: string;
  fileSize: number;
}

export const generatePresignedUrl = async (req: Request, res: Response) => {
  try {
    const { filename, contentType, fileSize }: PresignedUrlRequest = req.body;
    const userId = req.user?.id; // 인증 미들웨어에서 주입

    // 1. 입력 검증
    if (!filename || !contentType || !fileSize) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // 2. 파일 타입 검증
    if (!ALLOWED_IMAGE_TYPES.includes(contentType as any)) {
      return res.status(400).json({ 
        error: 'Invalid file type',
        allowed: ALLOWED_IMAGE_TYPES 
      });
    }

    // 3. 파일 크기 검증
    if (fileSize > MAX_FILE_SIZE) {
      return res.status(400).json({ 
        error: 'File too large',
        maxSize: MAX_FILE_SIZE,
        receivedSize: fileSize
      });
    }

    // 4. 안전한 파일명 생성
    const ext = path.extname(filename);
    const timestamp = Date.now();
    const randomString = crypto.randomBytes(8).toString('hex');
    const safeFilename = `${timestamp}-${randomString}${ext}`;

    // 5. S3 키 생성 (사용자별 디렉토리)
    const key = `uploads/${userId}/${safeFilename}`;

    // 6. Presigned URL 생성
    const command = new PutObjectCommand({
      Bucket: BUCKET_NAME,
      Key: key,
      ContentType: contentType,
      ContentLength: fileSize,
      // 메타데이터 추가 (선택사항)
      Metadata: {
        'original-filename': filename,
        'uploaded-by': userId,
        'upload-timestamp': timestamp.toString(),
      },
    });

    const uploadUrl = await getSignedUrl(r2Client, command, {
      expiresIn: 300, // 5분
    });

    // 7. 공개 URL 생성
    const publicUrl = `${PUBLIC_URL}/${key}`;

    // 8. 응답
    res.json({
      uploadUrl,
      key,
      publicUrl,
      expiresIn: 300,
    });

  } catch (error) {
    console.error('Presigned URL generation error:', error);
    res.status(500).json({ error: 'Failed to generate upload URL' });
  }
};

// 업로드 확인 (DB 저장)
export const confirmUpload = async (req: Request, res: Response) => {
  try {
    const { key, originalFilename } = req.body;
    const userId = req.user?.id;

    // DB에 이미지 메타데이터 저장
    // await db.images.create({
    //   userId,
    //   key,
    //   originalFilename,
    //   url: `${PUBLIC_URL}/${key}`,
    //   uploadedAt: new Date(),
    // });

    res.json({ success: true, key });
  } catch (error) {
    console.error('Upload confirmation error:', error);
    res.status(500).json({ error: 'Failed to confirm upload' });
  }
};
```

**3) 라우터 (routes/upload.ts)**

```typescript
import express from 'express';
import { generatePresignedUrl, confirmUpload } from '../controllers/uploadController';
import { authenticateUser } from '../middleware/auth';
import { uploadRateLimit } from '../middleware/rateLimit';

const router = express.Router();

// Presigned URL 발급 (인증 필요 + Rate Limit)
router.post(
  '/presigned-url',
  authenticateUser,
  uploadRateLimit,
  generatePresignedUrl
);

// 업로드 확인
router.post(
  '/confirm',
  authenticateUser,
  confirmUpload
);

export default router;
```

**4) 인증 미들웨어 (middleware/auth.ts)**

```typescript
import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';

export const authenticateUser = (req: Request, res: Response, next: NextFunction) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');

    if (!token) {
      return res.status(401).json({ error: 'No token provided' });
    }

    const decoded = jwt.verify(token, process.env.JWT_SECRET!) as { userId: string };
    req.user = { id: decoded.userId };
    
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};
```

**5) Rate Limit 미들웨어 (middleware/rateLimit.ts)**

```typescript
import rateLimit from 'express-rate-limit';

export const uploadRateLimit = rateLimit({
  windowMs: 60 * 1000, // 1분
  max: 10, // 최대 10개 요청
  message: 'Too many upload requests, please try again later',
  standardHeaders: true,
  legacyHeaders: false,
});
```

**6) Express 앱 설정 (app.ts)**

```typescript
import express from 'express';
import cors from 'cors';
import uploadRoutes from './routes/upload';

const app = express();

// 미들웨어
app.use(cors({
  origin: process.env.FRONTEND_URL || 'http://localhost:3000',
  credentials: true,
}));
app.use(express.json());

// 라우트
app.use('/api/upload', uploadRoutes);

// 에러 핸들러
app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
});

const PORT = process.env.PORT || 4000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

### 6.2 Python + Django 구현

**프로젝트 구조:**

```
backend/
├── config/
│   ├── settings.py
│   └── r2.py
├── apps/
│   └── uploads/
│       ├── views.py
│       ├── serializers.py
│       ├── models.py
│       └── urls.py
└── requirements.txt
```

**1) R2 클라이언트 설정 (config/r2.py)**

```python
import os
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

# 환경 변수 검증
required_vars = ['R2_ACCOUNT_ID', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY', 'R2_BUCKET_NAME']
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f'Missing required environment variable: {var}')

def get_r2_client():
    """R2 클라이언트 생성"""
    return boto3.client(
        's3',
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
        config=Config(signature_version='s3v4'),
        region_name='auto'
    )

BUCKET_NAME = os.getenv('R2_BUCKET_NAME')
PUBLIC_URL = os.getenv('R2_PUBLIC_URL')

# 허용 파일 타입
ALLOWED_IMAGE_TYPES = [
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
    'image/svg+xml',
]

# 최대 파일 크기 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024
```

**2) 시리얼라이저 (apps/uploads/serializers.py)**

```python
from rest_framework import serializers
from config.r2 import ALLOWED_IMAGE_TYPES, MAX_FILE_SIZE

class PresignedUrlRequestSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=255)
    content_type = serializers.CharField(max_length=100)
    file_size = serializers.IntegerField()

    def validate_content_type(self, value):
        if value not in ALLOWED_IMAGE_TYPES:
            raise serializers.ValidationError(
                f'Invalid file type. Allowed types: {", ".join(ALLOWED_IMAGE_TYPES)}'
            )
        return value

    def validate_file_size(self, value):
        if value > MAX_FILE_SIZE:
            raise serializers.ValidationError(
                f'File too large. Maximum size: {MAX_FILE_SIZE} bytes'
            )
        return value

class PresignedUrlResponseSerializer(serializers.Serializer):
    upload_url = serializers.URLField()
    key = serializers.CharField()
    public_url = serializers.URLField()
    expires_in = serializers.IntegerField()

class UploadConfirmSerializer(serializers.Serializer):
    key = serializers.CharField()
    original_filename = serializers.CharField()
```

**3) 뷰 (apps/uploads/views.py)**

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle

from config.r2 import get_r2_client, BUCKET_NAME, PUBLIC_URL
from .serializers import (
    PresignedUrlRequestSerializer,
    PresignedUrlResponseSerializer,
    UploadConfirmSerializer
)

import os
import hashlib
import time
from pathlib import Path

class UploadRateThrottle(UserRateThrottle):
    rate = '10/min'  # 1분에 10개

class GeneratePresignedUrlView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UploadRateThrottle]

    def post(self, request):
        # 1. 입력 검증
        serializer = PresignedUrlRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        filename = serializer.validated_data['filename']
        content_type = serializer.validated_data['content_type']
        file_size = serializer.validated_data['file_size']
        user_id = str(request.user.id)

        try:
            # 2. 안전한 파일명 생성
            ext = Path(filename).suffix
            timestamp = int(time.time() * 1000)
            random_hash = hashlib.md5(f"{user_id}{timestamp}".encode()).hexdigest()[:8]
            safe_filename = f"{timestamp}-{random_hash}{ext}"

            # 3. S3 키 생성
            key = f"uploads/{user_id}/{safe_filename}"

            # 4. Presigned URL 생성
            r2_client = get_r2_client()
            upload_url = r2_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': BUCKET_NAME,
                    'Key': key,
                    'ContentType': content_type,
                    'ContentLength': file_size,
                    'Metadata': {
                        'original-filename': filename,
                        'uploaded-by': user_id,
                        'upload-timestamp': str(timestamp),
                    }
                },
                ExpiresIn=300  # 5분
            )

            # 5. 공개 URL
            public_url = f"{PUBLIC_URL}/{key}"

            # 6. 응답
            response_data = {
                'upload_url': upload_url,
                'key': key,
                'public_url': public_url,
                'expires_in': 300,
            }

            response_serializer = PresignedUrlResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Presigned URL generation error: {e}")
            return Response(
                {'error': 'Failed to generate upload URL'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ConfirmUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UploadConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        key = serializer.validated_data['key']
        original_filename = serializer.validated_data['original_filename']
        user_id = request.user.id

        try:
            # DB에 이미지 메타데이터 저장
            # Image.objects.create(
            #     user_id=user_id,
            #     key=key,
            #     original_filename=original_filename,
            #     url=f"{PUBLIC_URL}/{key}",
            # )

            return Response({'success': True, 'key': key}, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Upload confirmation error: {e}")
            return Response(
                {'error': 'Failed to confirm upload'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
```

**4) URL 설정 (apps/uploads/urls.py)**

```python
from django.urls import path
from .views import GeneratePresignedUrlView, ConfirmUploadView

urlpatterns = [
    path('presigned-url/', GeneratePresignedUrlView.as_view(), name='presigned-url'),
    path('confirm/', ConfirmUploadView.as_view(), name='confirm-upload'),
]
```

**5) 메인 URL 설정 (config/urls.py)**

```python
from django.urls import path, include

urlpatterns = [
    # ...
    path('api/upload/', include('apps.uploads.urls')),
]
```

**6) Requirements (requirements.txt)**

```
Django==5.0.0
djangorestframework==3.14.0
boto3==1.34.0
python-dotenv==1.0.0
django-cors-headers==4.3.1
```

---

## 7. R2 Presigned URL 구현 - 프론트엔드

### 7.1 React + TypeScript 구현

**프로젝트 구조:**

```
frontend/
├── components/
│   ├── ImageUpload.tsx
│   └── ImageGallery.tsx
├── hooks/
│   └── useImageUpload.ts
├── services/
│   └── uploadService.ts
├── types/
│   └── upload.ts
└── utils/
    └── fileValidation.ts
```

**1) 타입 정의 (types/upload.ts)**

```typescript
export interface PresignedUrlRequest {
  filename: string;
  contentType: string;
  fileSize: number;
}

export interface PresignedUrlResponse {
  uploadUrl: string;
  key: string;
  publicUrl: string;
  expiresIn: number;
}

export interface UploadConfirmRequest {
  key: string;
  originalFilename: string;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface UploadedImage {
  id: string;
  url: string;
  originalFilename: string;
  uploadedAt: string;
}
```

**2) 파일 검증 유틸 (utils/fileValidation.ts)**

```typescript
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
const MAX_SIZE = 10 * 1024 * 1024; // 10MB

export const validateImageFile = (file: File): { valid: boolean; error?: string } => {
  // 파일 타입 검증
  if (!ALLOWED_TYPES.includes(file.type)) {
    return {
      valid: false,
      error: `Invalid file type. Allowed: ${ALLOWED_TYPES.join(', ')}`,
    };
  }

  // 파일 크기 검증
  if (file.size > MAX_SIZE) {
    return {
      valid: false,
      error: `File too large. Max size: ${MAX_SIZE / 1024 / 1024}MB`,
    };
  }

  return { valid: true };
};

export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
};
```

**3) 업로드 서비스 (services/uploadService.ts)**

```typescript
import axios from 'axios';
import {
  PresignedUrlRequest,
  PresignedUrlResponse,
  UploadConfirmRequest,
  UploadProgress,
} from '../types/upload';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000';

// Axios 인스턴스 (인증 토큰 자동 포함)
const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const uploadService = {
  /**
   * 1단계: Presigned URL 요청
   */
  async getPresignedUrl(request: PresignedUrlRequest): Promise<PresignedUrlResponse> {
    const response = await apiClient.post<PresignedUrlResponse>(
      '/api/upload/presigned-url',
      request
    );
    return response.data;
  },

  /**
   * 2단계: R2에 직접 업로드
   */
  async uploadToR2(
    file: File,
    uploadUrl: string,
    onProgress?: (progress: UploadProgress) => void
  ): Promise<void> {
    await axios.put(uploadUrl, file, {
      headers: {
        'Content-Type': file.type,
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentage = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress({
            loaded: progressEvent.loaded,
            total: progressEvent.total,
            percentage,
          });
        }
      },
    });
  },

  /**
   * 3단계: 업로드 확인 (DB 저장)
   */
  async confirmUpload(request: UploadConfirmRequest): Promise<void> {
    await apiClient.post('/api/upload/confirm', request);
  },

  /**
   * 전체 업로드 플로우
   */
  async uploadImage(
    file: File,
    onProgress?: (progress: UploadProgress) => void
  ): Promise<PresignedUrlResponse> {
    // 1. Presigned URL 요청
    const presignedData = await this.getPresignedUrl({
      filename: file.name,
      contentType: file.type,
      fileSize: file.size,
    });

    // 2. R2에 직접 업로드
    await this.uploadToR2(file, presignedData.uploadUrl, onProgress);

    // 3. 업로드 확인
    await this.confirmUpload({
      key: presignedData.key,
      originalFilename: file.name,
    });

    return presignedData;
  },
};
```

**4) 커스텀 훅 (hooks/useImageUpload.ts)**

```typescript
import { useState, useCallback } from 'react';
import { uploadService } from '../services/uploadService';
import { validateImageFile } from '../utils/fileValidation';
import { PresignedUrlResponse, UploadProgress } from '../types/upload';

export const useImageUpload = () => {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadedImage, setUploadedImage] = useState<PresignedUrlResponse | null>(null);

  const uploadImage = useCallback(async (file: File) => {
    // 초기화
    setUploading(true);
    setError(null);
    setProgress(null);
    setUploadedImage(null);

    try {
      // 1. 파일 검증
      const validation = validateImageFile(file);
      if (!validation.valid) {
        throw new Error(validation.error);
      }

      // 2. 업로드 실행
      const result = await uploadService.uploadImage(file, setProgress);

      // 3. 성공
      setUploadedImage(result);
      return result;

    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Upload failed';
      setError(errorMessage);
      throw err;

    } finally {
      setUploading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setUploading(false);
    setProgress(null);
    setError(null);
    setUploadedImage(null);
  }, []);

  return {
    uploadImage,
    uploading,
    progress,
    error,
    uploadedImage,
    reset,
  };
};
```

**5) 이미지 업로드 컴포넌트 (components/ImageUpload.tsx)**

```typescript
'use client';

import React, { useRef, useState } from 'react';
import { useImageUpload } from '../hooks/useImageUpload';
import { formatFileSize } from '../utils/fileValidation';

export const ImageUpload: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const { uploadImage, uploading, progress, error, uploadedImage, reset } = useImageUpload();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 미리보기 생성
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleUpload = async () => {
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;

    try {
      await uploadImage(file);
      alert('업로드 성공!');
    } catch (err) {
      console.error('Upload failed:', err);
    }
  };

  const handleReset = () => {
    reset();
    setPreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-4">이미지 업로드</h2>

      {/* 파일 선택 */}
      <div className="mb-4">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          onChange={handleFileChange}
          disabled={uploading}
          className="block w-full text-sm text-gray-500
            file:mr-4 file:py-2 file:px-4
            file:rounded-full file:border-0
            file:text-sm file:font-semibold
            file:bg-blue-50 file:text-blue-700
            hover:file:bg-blue-100
            disabled:opacity-50"
        />
      </div>

      {/* 미리보기 */}
      {preview && (
        <div className="mb-4">
          <img
            src={preview}
            alt="Preview"
            className="w-full h-48 object-cover rounded-lg"
          />
        </div>
      )}

      {/* 업로드 진행률 */}
      {uploading && progress && (
        <div className="mb-4">
          <div className="flex justify-between mb-1">
            <span className="text-sm font-medium text-blue-700">업로드 중...</span>
            <span className="text-sm font-medium text-blue-700">{progress.percentage}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
              style={{ width: `${progress.percentage}%` }}
            ></div>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            {formatFileSize(progress.loaded)} / {formatFileSize(progress.total)}
          </p>
        </div>
      )}

      {/* 에러 메시지 */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* 업로드 성공 */}
      {uploadedImage && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-600 mb-2">✅ 업로드 성공!</p>
          <div className="flex items-center space-x-2">
            <img
              src={uploadedImage.publicUrl}
              alt="Uploaded"
              className="w-16 h-16 object-cover rounded"
            />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-gray-500 truncate">
                {uploadedImage.key}
              </p>
              <a
                href={uploadedImage.publicUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:underline"
              >
                이미지 보기 →
              </a>
            </div>
          </div>
        </div>
      )}

      {/* 버튼 */}
      <div className="flex space-x-2">
        <button
          onClick={handleUpload}
          disabled={!preview || uploading}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg
            hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
            transition-colors font-medium"
        >
          {uploading ? '업로드 중...' : '업로드'}
        </button>
        <button
          onClick={handleReset}
          disabled={uploading}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg
            hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed
            transition-colors font-medium"
        >
          초기화
        </button>
      </div>
    </div>
  );
};
```

### 7.2 드래그 앤 드롭 업로드

**고급 업로드 컴포넌트 (components/DragDropUpload.tsx)**

```typescript
'use client';

import React, { useState, useCallback } from 'react';
import { useImageUpload } from '../hooks/useImageUpload';
import { validateImageFile, formatFileSize } from '../utils/fileValidation';

export const DragDropUpload: React.FC = () => {
  const [isDragging, setIsDragging] = useState(false);
  const { uploadImage, uploading, progress, error, uploadedImage } = useImageUpload();

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const file = e.dataTransfer.files[0];
      if (!file) return;

      // 파일 검증
      const validation = validateImageFile(file);
      if (!validation.valid) {
        alert(validation.error);
        return;
      }

      // 업로드
      try {
        await uploadImage(file);
      } catch (err) {
        console.error('Upload failed:', err);
      }
    },
    [uploadImage]
  );

  const handleFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      try {
        await uploadImage(file);
      } catch (err) {
        console.error('Upload failed:', err);
      }
    },
    [uploadImage]
  );

  return (
    <div className="max-w-2xl mx-auto p-6">
      {/* 드래그 앤 드롭 영역 */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          border-2 border-dashed rounded-lg p-12 text-center
          transition-colors duration-200
          ${isDragging 
            ? 'border-blue-500 bg-blue-50' 
            : 'border-gray-300 bg-gray-50'
          }
          ${uploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
      >
        {!uploading && !uploadedImage && (
          <>
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              stroke="currentColor"
              fill="none"
              viewBox="0 0 48 48"
            >
              <path
                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <p className="mt-4 text-sm text-gray-600">
              드래그 앤 드롭으로 이미지 업로드
            </p>
            <p className="mt-1 text-xs text-gray-500">
              또는 클릭하여 파일 선택
            </p>
            <p className="mt-2 text-xs text-gray-400">
              PNG, JPG, WEBP, GIF (최대 10MB)
            </p>
            <input
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              disabled={uploading}
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="mt-4 inline-block px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700"
            >
              파일 선택
            </label>
          </>
        )}

        {/* 업로드 중 */}
        {uploading && progress && (
          <div>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-sm text-gray-600">업로드 중... {progress.percentage}%</p>
            <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${progress.percentage}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* 업로드 완료 */}
        {uploadedImage && (
          <div>
            <img
              src={uploadedImage.publicUrl}
              alt="Uploaded"
              className="mx-auto max-h-64 rounded-lg"
            />
            <p className="mt-4 text-sm text-green-600">✅ 업로드 완료!</p>
            <a
              href={uploadedImage.publicUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-block text-sm text-blue-600 hover:underline"
            >
              이미지 보기 →
            </a>
          </div>
        )}
      </div>

      {/* 에러 */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
    </div>
  );
};
```

### 7.3 다중 이미지 업로드

```typescript
'use client';

import React, { useState, useCallback } from 'react';
import { uploadService } from '../services/uploadService';
import { validateImageFile, formatFileSize } from '../utils/fileValidation';
import { PresignedUrlResponse } from '../types/upload';

interface UploadItem {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  result?: PresignedUrlResponse;
  error?: string;
}

export const MultiImageUpload: React.FC = () => {
  const [uploadItems, setUploadItems] = useState<UploadItem[]>([]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    
    const newItems: UploadItem[] = files.map((file) => ({
      id: `${Date.now()}-${Math.random()}`,
      file,
      status: 'pending',
      progress: 0,
    }));

    setUploadItems((prev) => [...prev, ...newItems]);
  }, []);

  const uploadSingleItem = useCallback(async (item: UploadItem) => {
    // 검증
    const validation = validateImageFile(item.file);
    if (!validation.valid) {
      setUploadItems((prev) =>
        prev.map((i) =>
          i.id === item.id
            ? { ...i, status: 'error', error: validation.error }
            : i
        )
      );
      return;
    }

    // 업로드 시작
    setUploadItems((prev) =>
      prev.map((i) => (i.id === item.id ? { ...i, status: 'uploading' } : i))
    );

    try {
      const result = await uploadService.uploadImage(item.file, (progress) => {
        setUploadItems((prev) =>
          prev.map((i) =>
            i.id === item.id ? { ...i, progress: progress.percentage } : i
          )
        );
      });

      setUploadItems((prev) =>
        prev.map((i) =>
          i.id === item.id ? { ...i, status: 'success', result } : i
        )
      );
    } catch (error: any) {
      setUploadItems((prev) =>
        prev.map((i) =>
          i.id === item.id
            ? { ...i, status: 'error', error: error.message }
            : i
        )
      );
    }
  }, []);

  const handleUploadAll = useCallback(async () => {
    const pendingItems = uploadItems.filter((item) => item.status === 'pending');
    
    // 병렬 업로드 (최대 3개씩)
    for (let i = 0; i < pendingItems.length; i += 3) {
      const batch = pendingItems.slice(i, i + 3);
      await Promise.all(batch.map(uploadSingleItem));
    }
  }, [uploadItems, uploadSingleItem]);

  const handleRemove = useCallback((id: string) => {
    setUploadItems((prev) => prev.filter((item) => item.id !== id));
  }, []);

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-4">다중 이미지 업로드</h2>

      {/* 파일 선택 */}
      <div className="mb-6">
        <input
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileSelect}
          className="block w-full text-sm"
          id="multi-upload"
        />
        <label
          htmlFor="multi-upload"
          className="mt-2 inline-block px-4 py-2 bg-blue-600 text-white rounded cursor-pointer hover:bg-blue-700"
        >
          파일 선택
        </label>
      </div>

      {/* 업로드 버튼 */}
      {uploadItems.length > 0 && (
        <button
          onClick={handleUploadAll}
          disabled={!uploadItems.some((item) => item.status === 'pending')}
          className="mb-4 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
        >
          전체 업로드 ({uploadItems.filter((i) => i.status === 'pending').length}개)
        </button>
      )}

      {/* 업로드 목록 */}
      <div className="space-y-4">
        {uploadItems.map((item) => (
          <div
            key={item.id}
            className="flex items-center space-x-4 p-4 border rounded-lg"
          >
            {/* 미리보기 */}
            <img
              src={URL.createObjectURL(item.file)}
              alt={item.file.name}
              className="w-16 h-16 object-cover rounded"
            />

            {/* 정보 */}
            <div className="flex-1">
              <p className="text-sm font-medium">{item.file.name}</p>
              <p className="text-xs text-gray-500">{formatFileSize(item.file.size)}</p>

              {/* 진행률 */}
              {item.status === 'uploading' && (
                <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{ width: `${item.progress}%` }}
                  ></div>
                </div>
              )}

              {/* 상태 */}
              {item.status === 'success' && (
                <p className="text-xs text-green-600 mt-1">✅ 완료</p>
              )}
              {item.status === 'error' && (
                <p className="text-xs text-red-600 mt-1">❌ {item.error}</p>
              )}
            </div>

            {/* 제거 버튼 */}
            <button
              onClick={() => handleRemove(item.id)}
              className="text-red-600 hover:text-red-800"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## 8. 프로덕션 고려사항

### 8.1 이미지 최적화

**1) 클라이언트 측 이미지 압축**

```typescript
// utils/imageCompression.ts
import imageCompression from 'browser-image-compression';

export const compressImage = async (file: File): Promise<File> => {
  const options = {
    maxSizeMB: 1,          // 최대 1MB
    maxWidthOrHeight: 1920, // 최대 1920px
    useWebWorker: true,     // 웹 워커 사용 (성능 향상)
  };

  try {
    const compressedFile = await imageCompression(file, options);
    console.log(`압축 전: ${file.size / 1024 / 1024}MB → 압축 후: ${compressedFile.size / 1024 / 1024}MB`);
    return compressedFile;
  } catch (error) {
    console.error('압축 실패:', error);
    return file; // 실패 시 원본 반환
  }
};

// 사용
const handleUpload = async (file: File) => {
  const compressed = await compressImage(file);
  await uploadService.uploadImage(compressed);
};
```

**2) WebP 변환 (Cloudflare Workers)**

```typescript
// workers/image-transform.ts
export default {
  async fetch(request: Request, env: any): Promise<Response> {
    const url = new URL(request.url);
    const imageKey = url.pathname.slice(1);

    // R2에서 이미지 가져오기
    const object = await env.MY_BUCKET.get(imageKey);
    if (!object) {
      return new Response('Not found', { status: 404 });
    }

    // Accept 헤더 확인
    const accept = request.headers.get('Accept') || '';
    const supportsWebP = accept.includes('image/webp');

    if (supportsWebP && !imageKey.endsWith('.webp')) {
      // WebP로 변환 (Cloudflare Image Resizing 사용)
      return fetch(`https://your-domain.com/cdn-cgi/image/format=webp/${imageKey}`);
    }

    // 원본 반환
    return new Response(object.body, {
      headers: {
        'Content-Type': object.httpMetadata?.contentType || 'application/octet-stream',
        'Cache-Control': 'public, max-age=31536000',
      },
    });
  },
};
```

### 8.2 보안 강화

**1) 이미지 바이러스 스캔 (ClamAV)**

```python
# backend/utils/virus_scan.py
import clamd
import tempfile

def scan_file(file_content: bytes) -> bool:
    """
    파일 바이러스 스캔
    Returns: True if safe, False if virus detected
    """
    try:
        # ClamAV 연결
        cd = clamd.ClamdUnixSocket()
        
        # 임시 파일로 스캔
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(file_content)
            tmp.flush()
            result = cd.scan(tmp.name)
        
        # 결과 확인
        if result is None:
            return True  # 안전
        
        return False  # 바이러스 감지
    
    except Exception as e:
        print(f"Virus scan error: {e}")
        return False  # 안전하지 않음으로 간주
```

**2) 이미지 메타데이터 제거 (EXIF)**

```python
from PIL import Image
import io

def remove_exif(image_bytes: bytes) -> bytes:
    """이미지 EXIF 데이터 제거"""
    image = Image.open(io.BytesIO(image_bytes))
    
    # EXIF 없는 새 이미지 생성
    data = list(image.getdata())
    image_without_exif = Image.new(image.mode, image.size)
    image_without_exif.putdata(data)
    
    # 바이트로 변환
    output = io.BytesIO()
    image_without_exif.save(output, format=image.format)
    return output.getvalue()
```

**3) Content Security Policy (CSP)**

```typescript
// Next.js middleware
import { NextResponse } from 'next/server';

export function middleware(request: Request) {
  const response = NextResponse.next();

  response.headers.set(
    'Content-Security-Policy',
    "default-src 'self'; img-src 'self' https://pub-*.r2.dev; script-src 'self' 'unsafe-inline';"
  );

  return response;
}
```

### 8.3 성능 최적화

**1) 이미지 CDN 캐싱**

```
Cloudflare R2 공개 버킷 → 자동 CDN 캐싱
Cache-Control: public, max-age=31536000 (1년)

캐시 무효화:
- 파일명에 타임스탬프 포함 (cache busting)
- 예: image-1234567890.jpg
```

**2) Lazy Loading**

```typescript
// components/OptimizedImage.tsx
import Image from 'next/image';

export const OptimizedImage: React.FC<{ src: string; alt: string }> = ({ src, alt }) => {
  return (
    <Image
      src={src}
      alt={alt}
      width={800}
      height={600}
      loading="lazy"  // 지연 로딩
      placeholder="blur"  // 블러 플레이스홀더
      blurDataURL="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    />
  );
};
```

**3) Progressive JPEG**

```python
from PIL import Image

def save_progressive_jpeg(image_path: str, output_path: str):
    """Progressive JPEG로 저장"""
    img = Image.open(image_path)
    img.save(output_path, 'JPEG', quality=85, optimize=True, progressive=True)
```

### 8.4 모니터링 및 로깅

**1) 업로드 로깅**

```python
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def log_upload(user_id: str, key: str, file_size: int, success: bool):
    """업로드 로그 기록"""
    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'key': key,
        'file_size': file_size,
        'success': success,
    }
    
    if success:
        logger.info(f"Upload successful: {log_data}")
    else:
        logger.error(f"Upload failed: {log_data}")
```

**2) 에러 추적 (Sentry)**

```typescript
import * as Sentry from '@sentry/nextjs';

try {
  await uploadService.uploadImage(file);
} catch (error) {
  Sentry.captureException(error, {
    tags: {
      section: 'image-upload',
    },
    extra: {
      filename: file.name,
      fileSize: file.size,
    },
  });
  throw error;
}
```

---

## 9. 결론 및 선택 가이드

### 9.1 언제 AWS S3를 선택해야 하나?

**✅ S3가 적합한 경우:**

1. **AWS 생태계 의존성**
   ```
   - Lambda, EC2, RDS와 긴밀한 통합 필요
   - AWS Organization으로 멀티 계정 관리
   - CloudFormation/CDK로 인프라 관리
   ```

2. **규제 준수 (Compliance)**
   ```
   - HIPAA, PCI-DSS 인증 필요
   - 특정 리전에 데이터 저장 필수
   - Object Lock (WORM) 필요
   ```

3. **고급 기능 필요**
   ```
   - S3 Select (SQL 쿼리)
   - Glacier (아카이빙)
   - Batch Operations
   - Replication (CRR, SRR)
   ```

4. **이미 AWS 고객**
   ```
   - Reserved Capacity로 할인
   - AWS Support 계약 보유
   - Savings Plans 활용
   ```

### 9.2 언제 Cloudflare R2를 선택해야 하나?

**✅ R2가 적합한 경우:**

1. **이그레스 비용이 큰 경우**
   ```
   - 대용량 파일 배포 (동영상, 이미지)
   - 다운로드 트래픽 >> 스토리지 용량
   - CDN 비용 절감 목표
   
   예: 1TB 스토리지, 10TB 다운로드
   S3 + CloudFront: ~$1,000/월
   R2: ~$15/월 (98.5% 절감!)
   ```

2. **글로벌 서비스**
   ```
   - 전 세계 사용자 대상
   - 자동 엣지 복제 필요
   - 낮은 레이턴시 요구
   ```

3. **Cloudflare 생태계 활용**
   ```
   - Workers로 커스텀 로직
   - Pages로 정적 사이트
   - Images로 이미지 변환
   ```

4. **스타트업/사이드 프로젝트**
   ```
   - 무료 티어 활용 (10GB)
   - 초기 비용 최소화
   - 빠른 프로토타입
   ```

### 9.3 비용 기반 의사결정 가이드

**시나리오별 추천:**

```
📊 소규모 (< 100GB, < 500GB 다운로드/월):
→ R2 추천 (무료 티어 활용)

📊 중규모 (100GB-1TB, 1TB-10TB 다운로드/월):
→ R2 추천 (이그레스 비용 절감)

📊 대규모 (> 1TB, > 10TB 다운로드/월):
→ R2 강력 추천 (절감액 수천 달러)

📊 AWS 인프라 의존적:
→ S3 사용 (통합 비용 고려)

📊 규제 준수 필수:
→ S3 사용 (인증 보유)
```

### 9.4 마이그레이션 전략

**S3 → R2 마이그레이션:**

```bash
# 1. R2 버킷 생성
wrangler r2 bucket create my-new-bucket

# 2. rclone으로 데이터 복사
rclone copy s3:my-s3-bucket r2:my-new-bucket --progress

# 3. 점진적 전환
# - 새 업로드는 R2로
# - 기존 데이터는 점진적 마이그레이션
# - CloudFront → R2 public URL로 변경

# 4. S3 버킷 삭제 (완전 전환 후)
```

### 9.5 하이브리드 전략

**최적의 비용 효율:**

```
업로드 빈도 높음 + 다운로드 적음:
→ S3 (저렴한 스토리지 클래스: IA, Glacier)

업로드 적음 + 다운로드 많음:
→ R2 (이그레스 무료)

실전 예시:
- 원본 이미지: S3 Glacier (아카이브)
- 처리된 이미지: R2 (서빙)
- 로그 파일: S3 IA (분석용)
```

### 9.6 최종 체크리스트

**R2 도입 전 확인사항:**

```
□ S3 호환 API로 충분한가?
□ 특정 리전 선택이 불필요한가?
□ 이그레스 비용이 큰가?
□ AWS 락인을 피하고 싶은가?
□ Cloudflare 생태계를 활용할 의향이 있는가?

5개 중 3개 이상 Yes → R2 추천!
```

**S3 유지 시 확인사항:**

```
□ AWS 생태계 의존도가 높은가?
□ 규제 준수 요구사항이 있는가?
□ S3 고유 기능이 필요한가?
□ 이미 AWS 대규모 할인을 받는가?
□ 운영팀이 AWS에 익숙한가?

5개 중 3개 이상 Yes → S3 유지!
```

---

## 요약

### 핵심 포인트

1. **비용 절감**: R2는 이그레스 비용 0원으로 대용량 파일 서빙에 최적 (98% 이상 절감 가능)
2. **Presigned URL**: 서버 부하 없이 클라이언트가 직접 업로드 (3배 빠름, 50% 비용 절감)
3. **S3 호환**: 기존 S3 코드를 엔드포인트만 변경하여 R2로 마이그레이션 가능
4. **선택 기준**: 
   - 이그레스 많음 + 글로벌 서비스 → R2
   - AWS 의존성 높음 + 규제 준수 → S3

### 실전 적용

```typescript
// 1. 환경 변수 설정
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=your_bucket

// 2. 백엔드: Presigned URL 발급
POST /api/upload/presigned-url
{ "filename": "image.jpg", "contentType": "image/jpeg", "fileSize": 1024000 }

// 3. 프론트엔드: R2에 직접 업로드
PUT <presigned_url>
Body: [이미지 파일]

// 4. 백엔드: 업로드 확인 (DB 저장)
POST /api/upload/confirm
{ "key": "uploads/user123/image.jpg", "originalFilename": "image.jpg" }
```

### 다음 단계

1. ✅ Cloudflare 계정 생성 및 R2 활성화
2. ✅ 무료 티어로 프로토타입 구현
3. ✅ Presigned URL 플로우 구현
4. ✅ 이미지 최적화 (압축, WebP) 적용
5. ✅ 프로덕션 배포 및 모니터링

**행복한 코딩 되세요!** 🚀💾

---

## 참고 자료

- [Cloudflare R2 공식 문서](https://developers.cloudflare.com/r2/)
- [AWS S3 공식 문서](https://docs.aws.amazon.com/s3/)
- [Presigned URL 가이드](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)
- [R2 가격 정보](https://developers.cloudflare.com/r2/pricing/)
- [S3 가격 계산기](https://calculator.aws/)


