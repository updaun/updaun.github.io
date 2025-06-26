---
layout: post
title: "AWS SAA 실전 문제 풀이 및 분석 - 빅데이터 분석 아키텍처 설계"
date: 2025-06-26
categories: aws-saa
author: updaun
---

# AWS SAA 실전 문제 풀이 및 분석 - 빅데이터 분석 아키텍처 설계

AWS Solutions Architect Associate(SAA) 시험에서 자주 출제되는 빅데이터 및 데이터 분석 아키텍처 문제를 풀어보고 상세히 분석해보겠습니다. 이번 포스트에서는 Kinesis, EMR, Athena, QuickSight 등 AWS 데이터 분석 서비스를 활용한 실전 문제를 다룹니다.

## 📝 실전 문제

**문제**: 한 미디어 회사가 실시간 로그 데이터와 대용량 배치 데이터를 분석하여 대시보드로 시각화하려고 합니다. 요구사항은 다음과 같습니다:

- **실시간 데이터 수집**: 수백만 건/일 로그 스트림 처리
- **배치 데이터 처리**: 대용량 CSV/JSON 파일의 ETL
- **저비용 저장소**: 장기 보관 및 쿼리 최적화
- **SQL 기반 분석**: 개발자가 SQL로 데이터 분석
- **대시보드 시각화**: 실시간/배치 데이터 모두 시각화
- **확장성/유연성**: 데이터량 증가에 따른 자동 확장

가장 적합한 AWS 아키텍처 조합은?

**A)** EC2 + RDS + CloudWatch Logs + Tableau

**B)** Kinesis Data Streams + Kinesis Data Firehose + S3 + Glue + Athena + QuickSight

**C)** Redshift Spectrum + Lambda + S3 + CloudFormation

**D)** EMR + DynamoDB + S3 + CloudTrail

## 🎯 정답 및 해설

### 정답: B

**Kinesis Data Streams + Kinesis Data Firehose + S3 + Glue + Athena + QuickSight**

### 상세 분석

#### 1. 요구사항별 서비스 매핑

| 요구사항 | 서비스 | 설명 |
|----------|--------|------|
| 실시간 수집 | Kinesis Data Streams | 초당 수천 TPS 스트림 처리 |
| 실시간 적재 | Kinesis Data Firehose | S3로 자동 적재, 변환 지원 |
| 배치 ETL | Glue | 서버리스 ETL, 크롤러, 스케줄링 |
| 저장소 | S3 | 저비용, 무제한, 데이터 레이크 |
| SQL 분석 | Athena | S3 데이터에 직접 SQL 쿼리 |
| 시각화 | QuickSight | 실시간/배치 대시보드 |

## 🚀 아키텍처 상세 설계

### 1. 실시간 로그 수집 및 적재

#### Kinesis Data Streams
- 초당 수천 TPS의 로그 이벤트 수집
- Shard 단위로 자동 확장

#### Kinesis Data Firehose
- 실시간 스트림을 S3로 자동 적재
- 데이터 변환(압축, 파싱, 포맷 변경) 지원
- 실패 데이터는 S3에 별도 저장

#### S3 버킷 구조 예시
```
s3://media-analytics-logs/
  ├── raw/
  │    └── 2025/06/26/logs-raw-001.json
  ├── processed/
  │    └── 2025/06/26/logs-processed-001.parquet
  └── batch/
       └── 2025/06/26/batch-data.csv
```

### 2. 배치 데이터 ETL

#### AWS Glue
- Glue Crawler로 S3 데이터 자동 스키마 추출
- Glue Job으로 CSV/JSON → Parquet 변환, 정제, 집계
- ETL 결과를 S3 processed/에 저장

#### Glue Job 예시 (PySpark)
```python
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

glueContext = GlueContext(SparkContext.getOrCreate())

# 데이터 로드
datasource = glueContext.create_dynamic_frame.from_catalog(
    database = "media_analytics_db",
    table_name = "raw_logs"
)

# 데이터 정제 및 변환
transformed = ApplyMapping.apply(
    frame = datasource,
    mappings = [
        ("timestamp", "string", "event_time", "timestamp"),
        ("user_id", "string", "user_id", "string"),
        ("action", "string", "action", "string"),
        ("value", "int", "value", "int")
    ]
)

# Parquet 포맷으로 저장
glueContext.write_dynamic_frame.from_options(
    frame = transformed,
    connection_type = "s3",
    connection_options = {"path": "s3://media-analytics-logs/processed/"},
    format = "parquet"
)
```

### 3. SQL 분석 및 대시보드

#### Athena
- S3의 Parquet/CSV/JSON 데이터에 직접 SQL 쿼리
- Glue Data Catalog와 연동, 테이블 자동 인식
- 예시 쿼리:
```sql
SELECT action, COUNT(*) as cnt
FROM processed_logs
WHERE event_time BETWEEN date '2025-06-25' AND date '2025-06-26'
GROUP BY action
ORDER BY cnt DESC;
```

#### QuickSight
- Athena 쿼리 결과를 데이터셋으로 연결
- 실시간/배치 데이터 모두 대시보드로 시각화
- 사용자별, 기간별, 액션별 분석

### 4. 확장성/비용 최적화
- Kinesis Shard, Glue Job, Athena 쿼리 모두 사용량 기반 과금
- S3 Intelligent-Tiering, Parquet 포맷으로 저장 비용 절감
- Glue Trigger/Workflow로 ETL 자동화

## 🏗️ 완성된 빅데이터 분석 아키텍처

```
┌──────────────┐
│   사용자/앱   │
└──────┬───────┘
       │ 로그 이벤트
┌──────▼─────────────┐
│ Kinesis Data Streams │
└──────┬─────────────┘
       │ 실시간 스트림
┌──────▼─────────────┐
│ Kinesis Firehose     │
└──────┬─────────────┘
       │ S3 적재
┌──────▼─────────────┐
│        S3           │
├──────┬───────┬──────┤
│  raw │ batch │ processed │
└──────┴───────┴──────┘
       │
┌──────▼─────────────┐
│      Glue ETL      │
└──────┬─────────────┘
       │
┌──────▼─────────────┐
│     Athena         │
└──────┬─────────────┘
       │
┌──────▼─────────────┐
│   QuickSight       │
└────────────────────┘
```

## ❌ 다른 선택지가 부적절한 이유

### A) EC2 + RDS + CloudWatch Logs + Tableau
- **실시간 스트림 처리 불가**: EC2/RDS는 대규모 실시간 로그에 부적합
- **운영 오버헤드**: 서버 관리 필요, 확장성 한계
- **비용 증가**: 고정 인프라 비용

### C) Redshift Spectrum + Lambda + S3
- **실시간 스트림 부적합**: Redshift는 배치/쿼리 중심, 실시간 처리 한계
- **Lambda 한계**: 대용량 ETL/분석에 부적합

### D) EMR + DynamoDB + S3
- **EMR 비용/운영 부담**: 서버 클러스터 관리 필요
- **DynamoDB**: 로그/분석 데이터 저장에 비효율적
- **실시간 시각화**: QuickSight 연동 어려움

## 📊 성능 및 비용 최적화 전략

### 1. S3 비용 최적화
- **Intelligent-Tiering**: 장기 미사용 데이터 자동 저렴한 스토리지로 이동
- **Parquet 포맷**: 쿼리 비용/속도 최적화

### 2. Kinesis/Glue/Athena 비용 최적화
- **Kinesis Shard Auto-Scaling**: 트래픽에 따라 자동 확장/축소
- **Glue Job 예약/Trigger**: 불필요한 실행 방지
- **Athena 파티셔닝**: 쿼리 범위 축소로 비용 절감

### 3. QuickSight 비용 최적화
- **SPICE 엔진**: 쿼리 캐싱, 대시보드 응답속도 향상
- **사용자별 권한/요금제 관리**

## 🔧 모니터링 및 운영
- **CloudWatch Logs/Alarms**: Kinesis, Glue, Athena, S3 오류/지연 감지
- **CloudTrail**: 데이터 접근/변경 추적
- **Glue Job 실패 자동 알림**: SNS 연동

## 🎓 핵심 학습 포인트

1. **데이터 레이크 패턴**: S3 + Glue + Athena 조합
2. **실시간/배치 통합**: Kinesis + Firehose + Glue
3. **SQL 기반 분석**: Athena로 서버리스 쿼리
4. **시각화 자동화**: QuickSight 대시보드
5. **확장성/비용 최적화**: 서버리스, 사용량 기반 과금

## 💭 마무리

이 문제는 AWS SAA 시험에서 자주 출제되는 데이터 분석 아키텍처 설계의 대표적인 예시입니다. 실시간/배치 데이터 통합, 서버리스 ETL, SQL 분석, 대시보드까지 엔드투엔드로 설계하는 능력이 중요합니다.

데이터 분석 아키텍처 설계 시 고려사항:

1. **데이터 수집/적재**: 실시간/배치 모두 지원
2. **저장소 구조**: 데이터 레이크, 포맷, 파티셔닝
3. **ETL 자동화**: Glue, Lambda, Step Functions
4. **분석/시각화**: Athena, QuickSight
5. **비용/운영 최적화**: 서버리스, 자동화, 모니터링

다음 포스트에서는 AWS의 하이브리드/멀티클라우드 아키텍처 설계 문제를 다뤄보겠습니다.

---

**관련 포스트**:
- [AWS EC2 완벽 가이드]({% post_url 2025-06-19-aws-ec2-overview %})
- [AWS S3 기초 가이드]({% post_url 2025-06-19-aws-s3-basics %})
- [AWS SAA 자격증 공부 범위 총정리]({% post_url 2025-06-20-aws-saa-study-guide %})
- [AWS SAA 실전 문제 풀이 - Auto Scaling과 Load Balancer]({% post_url 2025-06-22-aws-saa-practice-problem-analysis %})
- [AWS SAA 실전 문제 풀이 - VPC 보안과 네트워크 ACL]({% post_url 2025-06-23-aws-saa-security-vpc-problem-analysis %})
- [AWS SAA 실전 문제 풀이 - 데이터베이스 성능 최적화]({% post_url 2025-06-24-aws-saa-database-performance-optimization %})
- [AWS SAA 실전 문제 풀이 - 서버리스 아키텍처]({% post_url 2025-06-25-aws-saa-serverless-event-driven-architecture %})

**태그**: #AWS #SAA #BigData #Kinesis #Glue #Athena #QuickSight #데이터레이크 #분석아키텍처
